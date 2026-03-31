import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import uuid
import streamlit.components.v1 as components

# ============================================================
# KIN HOUSE POS PRO — VERSION MEJORADA
# ============================================================
# Mejoras principales:
# - Catálogo centralizado
# - Inicialización robusta de Firebase
# - Manejo consistente de estado en session_state
# - Validaciones para caja, ticket y cobro
# - Folio de venta y timestamp local CDMX
# - Cobro con efectivo, cálculo de cambio y validaciones
# - Reportes con KPIs, filtros y exportación CSV
# - Configuración protegida por PIN admin
# - Código más limpio y fácil de mantener
# ============================================================

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="KIN House POS Pro", layout="wide", page_icon="☀️")
CDMX_TZ = ZoneInfo("America/Mexico_City")


def now_cdmx() -> datetime:
    return datetime.now(CDMX_TZ)


def now_iso() -> str:
    return now_cdmx().isoformat()


def money(n) -> str:
    try:
        return f"${float(n):,.0f}"
    except Exception:
        return "$0"


# ---------------------------
# SESSION STATE
# ---------------------------
def init_state():
    defaults = {
        "cid": None,
        "enom": None,
        "dialog_payload": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------------------------
# STYLES
# ---------------------------
st.markdown(
    """
<style>
    :root {
        --kin-cream: #F5F2ED;
        --kin-black: #101010;
        --kin-gold: #B59461;
        --kin-green: #2ECC71;
        --kin-red: #E74C3C;
        --kin-blue: #2F80ED;
        --kin-card: #FFFFFF;
        --kin-gray: #666666;
    }

    .stApp {
        background-color: var(--kin-cream);
    }

    .mesa-card {
        padding: 15px;
        border-radius: 14px;
        text-align: center;
        font-weight: 700;
        margin-bottom: 10px;
        color: white;
        box-shadow: 0 8px 18px rgba(0,0,0,0.10);
        font-size: 16px;
    }

    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 4px 14px rgba(0,0,0,0.05);
    }

    .ticket-box {
        background: white;
        border-radius: 14px;
        padding: 14px;
        border: 1px solid rgba(0,0,0,0.08);
    }

    .section-title {
        font-weight: 800;
        font-size: 18px;
        margin-top: 6px;
        margin-bottom: 8px;
        color: var(--kin-black);
    }

    .muted {
        color: var(--kin-gray);
        font-size: 12px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 700;
        min-height: 3.6em;
        border: 1px solid rgba(0,0,0,0.06);
        font-size: 12px;
        line-height: 1.2;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #ddd;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------
# FIREBASE
# ---------------------------
def init_firebase():
    try:
        if not firebase_admin._apps:
            creds_obj = st.secrets["firebase_credentials"]
            fb_creds = creds_obj.to_dict() if hasattr(creds_obj, "to_dict") else dict(creds_obj)
            cred = credentials.Certificate(fb_creds)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Error al inicializar Firebase: {e}")
        st.stop()


db = init_firebase()


# ---------------------------
# DATA HELPERS
# ---------------------------
def get_brand() -> dict:
    try:
        doc = db.collection("config").document("branding").get()
        if doc.exists:
            data = doc.to_dict() or {}
            return {
                "logo_b64": data.get("logo_b64", ""),
                "nombre": data.get("nombre", "KIN House"),
                "slogan": data.get("slogan", "Mismo sabor, mismo lugar"),
            }
    except Exception:
        pass
    return {"logo_b64": "", "nombre": "KIN House", "slogan": "Mismo sabor, mismo lugar"}


brand = get_brand()


def get_admin_pin() -> str:
    return str(st.secrets.get("admin_pin", "2424"))


def get_open_cashbox():
    try:
        q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
        return next((d.to_dict() | {"id": d.id} for d in q), None)
    except Exception as e:
        st.error(f"No fue posible consultar la caja: {e}")
        return None


def get_open_orders_by_space() -> dict:
    data = {}
    try:
        for d in db.collection("comandas").where("estado", "==", "ABIERTA").stream():
            row = d.to_dict() or {}
            espacio = row.get("espacio")
            if espacio:
                data[espacio] = d.id
    except Exception as e:
        st.error(f"No fue posible cargar comandas: {e}")
    return data


def load_order(doc_id: str) -> dict:
    try:
        doc = db.collection("comandas").document(doc_id).get()
        if doc.exists:
            row = doc.to_dict() or {}
            row["id"] = doc.id
            row.setdefault("items", [])
            row.setdefault("total", 0)
            return row
    except Exception as e:
        st.error(f"No fue posible cargar la comanda: {e}")
    return {"id": doc_id, "items": [], "total": 0}


def update_order(doc_id: str, items: list, total: float):
    db.collection("comandas").document(doc_id).update({"items": items, "total": total, "updated_at": now_iso()})


def calc_total(items: list) -> float:
    return round(sum(float(x.get("p", 0)) * int(x.get("q", 1)) for x in items), 2)


def build_sale_folio() -> str:
    return f"KIN-{now_cdmx().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"


# ---------------------------
# CATÁLOGO
# ---------------------------
CATALOG = {
    "Churros/Dulce": {
        "Churros y Postres": [
            {"name": "Churro Pieza", "base": 14, "options": ["Tradicional"]},
            {"name": "Churros 3 Piezas", "base": 42, "options": ["Tradicional"]},
            {"name": "Churros 6 Piezas", "base": 79, "options": ["Tradicional"]},
            {"name": "Churros 12 Piezas", "base": 149, "options": ["Tradicional"]},
            {"name": "Buñuelos", "base": 49, "options": ["Tradicional"]},
            {"name": "Sandwich de Churro", "base": 75, "options": ["Sencillo"]},
            {"name": "Churro Split", "base": 99, "options": ["3 bolas de helado + 2 churros"]},
            {"name": "Waffle", "base": 49, "options": ["Sencillo + 1 salsa $49", "Con topping $65"]},
            {"name": "Fresas con crema", "base": 75, "options": ["12 oz · 1 topping $75", "16 oz · 2 toppings $85"]},
        ],
    },
    "Comida/Desayunos": {
        "KIN Smash Burger": [
            {"name": "KIN Smash Burger", "base": 99, "options": ["Sencilla $99", "Doble carne $128", "Combo +$45"]},
        ],
        "Emparedados KIN": [
            {"name": "Clásico", "base": 69, "options": ["Jamón y queso", "Combo +$45"]},
            {"name": "Ratatouille", "base": 79, "options": ["Tres quesos fundidos", "Combo +$45"]},
            {"name": "Pamplona", "base": 89, "options": ["Salami, chorizo Pamplona, jamón y queso", "Combo +$45"]},
            {"name": "Napoli", "base": 99, "options": ["Pollo, queso y ajo", "Combo +$45"]},
            {"name": "Toscano", "base": 105, "options": ["Pollo, salsa boloñesa y parmesano", "Combo +$45"]},
        ],
        "Desayunos": [
            {"name": "Chilaquiles Express", "base": 45, "options": ["Incluye jugo o fruta y café"]},
            {"name": "Chilaquiles Normales", "base": 129, "options": ["Incluye jugo o fruta y café"]},
            {"name": "Enfrijoladas", "base": 129, "options": ["Incluye jugo o fruta y café"]},
            {"name": "Molletes", "base": 99, "options": ["Incluye jugo o fruta y café"]},
            {"name": "Sincronizadas", "base": 99, "options": ["Incluye jugo o fruta y café"]},
            {"name": "Orden de Hotcakes", "base": 99, "options": ["Incluye jugo o fruta y café", "Añade orden extra de 3 hotcakes +$35"]},
            {"name": "Extra Hotcakes (3)", "base": 35, "options": ["Mazapán", "Cajeta", "Lechera", "Nutella", "Frutos rojos"]},
        ],
    },
    "Café/Barra": {
        "Cafetería": [
            {"name": "Espresso", "base": 39, "options": ["Sencillo"]},
            {"name": "Americano", "base": 45, "options": ["Chico $45", "Grande $55"]},
            {"name": "Café del día Chiapas", "base": 35, "options": ["Chico"]},
            {"name": "Café de olla", "base": 45, "options": ["Chico $45", "Grande $55"]},
            {"name": "Lechero/Mocha/Capuccino/Latte/Chai latte/Matcha/Taro/Horchata/Temporada", "base": 65, "options": ["Chico · Lechero $65", "Grande · Lechero $75", "Chico · Mocha $65", "Grande · Mocha $75", "Chico · Capuccino $65", "Grande · Capuccino $75", "Chico · Latte $65", "Grande · Latte $75", "Chico · Chai latte $65", "Grande · Chai latte $75", "Chico · Matcha $65", "Grande · Matcha $75", "Chico · Taro $65", "Grande · Taro $75", "Chico · Horchata $65", "Grande · Horchata $75", "Chico · Temporada $65", "Grande · Temporada $75", "+$10 Leche deslactosada", "+$10 Leche vegetal", "+$10 Leche light"]},
            {"name": "Té / Limonada", "base": 40, "options": ["Chico · Té $40", "Grande · Té $45", "Chica · Limonada $40", "Grande · Limonada $45"]},
            {"name": "Frappé", "base": 69, "options": ["Chico · Matcha $69", "Grande · Matcha $79", "Chico · Horchata $69", "Grande · Horchata $79", "Chico · Chai $69", "Grande · Chai $79", "Chico · Mocha $69", "Grande · Mocha $79", "Chico · Taro $69", "Grande · Taro $79", "Chico · Temporada $69", "Grande · Temporada $79", "Chico · Cookies $69", "Grande · Cookies $79", "Chico · Café $69", "Grande · Café $79"]},
        ],
        "Especialidad": [
            {"name": "Bebida de especialidad", "base": 79, "options": ["Caliente · Caramel Machiatto $79", "Frío · Caramel Machiatto $89", "Caliente · Dirty Chai $79", "Frío · Dirty Chai $89", "Caliente · Dirty Horchata $79", "Frío · Dirty Horchata $89", "Caliente · Chocolate Mexicano $79", "Frío · Chocolate Mexicano $89", "Caliente · Crawnberry Mocha Blanco $79", "Frío · Crawnberry Mocha Blanco $89", "Caliente · Chocoreta $79", "Frío · Chocoreta $89", "+$10 Leche deslactosada", "+$10 Leche vegetal", "+$10 Leche light"]}
        ],
    },
    "Bebidas/Helados": {
        "Bebidas frías": [
            {"name": "Malteada Normal", "base": 89, "options": ["Chica $89", "Grande $99"]},
            {"name": "Malteada Special (Espesa)", "base": 99, "options": ["Chica $99", "Grande $115"]},
            {"name": "Refresco", "base": 45, "options": ["Individual"]},
            {"name": "Agua", "base": 30, "options": ["Individual"]},
        ],
        "Helados": [
            {"name": "Helado Suave", "base": 20, "options": ["Cono $20", "Sundae $35", "Topping extra +$12"]},
            {"name": "Helado Yogurth", "base": 59, "options": ["Chico $59 · 1 topping y 1 salsa", "Grande $75 · 1 topping y 1 salsa", "Topping ilimitado +$25"]},
            {"name": "QUEEN House", "base": 90, "options": ["Vainilla en vaso · hasta 2 toppings"]},
            {"name": "KING House", "base": 120, "options": ["Yogurth en vaso · hasta 2 toppings"]},
        ],
    },
    "Combos": {
        "Promociones y combos": [
            {"name": "2 chocolates grandes + 6 churros tradicionales", "base": 229, "options": ["Combo"]},
            {"name": "1 chocolate + 3 churros tradicionales", "base": 109, "options": ["Combo"]},
            {"name": "2 granizados", "base": 99, "options": ["Combo"]},
            {"name": "Combo Café + Sandwich", "base": 89, "options": ["Café americano", "Latte +$10"]},
        ]
    },
}


def infer_price(base_price: float, option_text: str) -> float:
    opt = option_text.strip()
    if "+$" in opt:
        try:
            extra = float(opt.split("+$")[-1].split()[0])
            return base_price + extra
        except Exception:
            return base_price

    if "$" in opt:
        try:
            explicit = float(opt.split("$")[-1].split()[0])
            return explicit
        except Exception:
            return base_price

    return base_price


# ---------------------------
# DIALOG
# ---------------------------
@st.dialog("Variante de Producto")
def option_dialog():
    payload = st.session_state.get("dialog_payload")
    if not payload:
        st.warning("No hay producto seleccionado.")
        return

    prod_name = payload["prod_name"]
    price = payload["price"]
    options = payload["options"]
    doc_id = payload["doc_id"]

    st.write(f"Seleccione para: **{prod_name}**")
    cols = st.columns(2)

    order = load_order(doc_id)
    items = order.get("items", [])

    for i, opt in enumerate(options):
        final_price = infer_price(price, opt)
        if cols[i % 2].button(f"{opt}\n{money(final_price)}", key=f"opt_{prod_name}_{i}", use_container_width=True):
            items.append({
                "n": f"{prod_name} ({opt})",
                "p": final_price,
                "q": 1,
                "added_at": now_iso(),
            })
            total = calc_total(items)
            update_order(doc_id, items, total)
            st.session_state.dialog_payload = None
            st.rerun()

    if st.button("Cancelar", use_container_width=True):
        st.session_state.dialog_payload = None
        st.rerun()


# ---------------------------
# ORDER HELPERS
# ---------------------------
def open_new_order(space_name: str, cashbox_id: str):
    payload = {
        "espacio": space_name,
        "estado": "ABIERTA",
        "items": [],
        "total": 0,
        "caja_id": cashbox_id,
        "fecha": now_iso(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _, ref = db.collection("comandas").add(payload)
    st.session_state.cid = ref.id
    st.session_state.enom = space_name


def add_dialog_request(prod_name: str, price: float, options: list, doc_id: str):
    st.session_state.dialog_payload = {
        "prod_name": prod_name,
        "price": price,
        "options": options,
        "doc_id": doc_id,
    }
    option_dialog()


def close_ticket_session():
    st.session_state.cid = None
    st.session_state.enom = None
    st.session_state.dialog_payload = None


# ---------------------------
# UI HEADER / SIDEBAR
# ---------------------------
with st.sidebar:
    if brand.get("logo_b64"):
        st.image(f"data:image/png;base64,{brand['logo_b64']}", use_container_width=True)

    st.markdown(f"### {brand.get('nombre', 'KIN House')}")
    st.caption(brand.get("slogan", "Mismo sabor, mismo lugar"))

    menu_nav = st.selectbox("MENÚ", ["🪑 Mesas", "💵 Caja", "📊 Reporte", "⚙️ Config"])
    st.divider()
    admin_pin = st.text_input("PIN Admin", type="password")
    is_admin = admin_pin == get_admin_pin()


# ============================================================
# VIEW: MESAS
# ============================================================
if menu_nav == "🪑 Mesas":
    st.title("🪑 Mesas")
    cashbox = get_open_cashbox()

    if not cashbox:
        st.error("🛑 No hay caja abierta. Abre una caja para poder vender.")
        st.stop()

    spaces = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar"]
    open_orders = get_open_orders_by_space()

    cols = st.columns(4)
    for i, space in enumerate(spaces):
        with cols[i % 4]:
            occupied = space in open_orders
            bg = "#E74C3C" if occupied else "#2ECC71"
            st.markdown(f'<div class="mesa-card" style="background:{bg};">{space}</div>', unsafe_allow_html=True)
            if st.button("Ver / Abrir", key=f"space_{space}"):
                if occupied:
                    st.session_state.cid = open_orders[space]
                    st.session_state.enom = space
                else:
                    open_new_order(space, cashbox["id"])
                st.rerun()

    if st.session_state.cid:
        order = load_order(st.session_state.cid)
        order_items = order.get("items", [])
        order_total = calc_total(order_items)

        st.divider()
        st.subheader(f"📍 {st.session_state.enom}")

        col_menu, col_ticket = st.columns([2.2, 1])

        with col_menu:
            tabs = st.tabs(list(CATALOG.keys()))

            for tab_index, tab_name in enumerate(CATALOG.keys()):
                with tabs[tab_index]:
                    sections = CATALOG[tab_name]
                    for section_name, products in sections.items():
                        st.markdown(f'<div class="section-title">{section_name}</div>', unsafe_allow_html=True)
                        chunk_size = 3
                        for start in range(0, len(products), chunk_size):
                            row = products[start:start + chunk_size]
                            row_cols = st.columns(len(row))
                            for j, prod in enumerate(row):
                                label = f"{prod['name']}\n{money(prod['base'])}"
                                if row_cols[j].button(label, key=f"prod_{tab_name}_{section_name}_{prod['name']}"):
                                    add_dialog_request(prod["name"], prod["base"], prod["options"], st.session_state.cid)

        with col_ticket:
            st.markdown('<div class="ticket-box">', unsafe_allow_html=True)
            st.markdown("### Ticket")

            if not order_items:
                st.info("Aún no hay productos en esta comanda.")
            else:
                for idx, item in enumerate(order_items):
                    left, mid, right = st.columns([4, 1.5, 1])
                    left.write(f"**{item.get('n', 'Producto')}**")
                    qty = int(item.get("q", 1))
                    unit_price = float(item.get("p", 0))
                    line_total = qty * unit_price
                    mid.write(f"x{qty} · {money(line_total)}")

                    if right.button("🗑️", key=f"rm_{idx}"):
                        order_items.pop(idx)
                        new_total = calc_total(order_items)
                        update_order(st.session_state.cid, order_items, new_total)
                        st.rerun()

                st.divider()

            st.subheader(f"Total: {money(order_total)}")

            payment_method = st.selectbox("Método de pago", ["Efectivo", "Tarjeta", "Transferencia"])
            cash_received = 0.0
            if payment_method == "Efectivo":
                cash_received = st.number_input("Recibido", min_value=0.0, step=10.0)
                change = max(cash_received - order_total, 0)
                st.caption(f"Cambio: {money(change)}")

            can_charge = order_total > 0 and (payment_method != "Efectivo" or cash_received >= order_total)

            sale_note = st.text_input("Nota / comentario (opcional)")

            if st.button("COBRAR E IMPRIMIR", type="primary", disabled=not can_charge):
                if order_total <= 0:
                    st.warning("No puedes cobrar un ticket vacío.")
                else:
                    sale_folio = build_sale_folio()
                    sale_doc = {
                        "folio": sale_folio,
                        "total": order_total,
                        "metodo": payment_method,
                        "mesa": st.session_state.enom,
                        "fecha": now_iso(),
                        "caja_id": cashbox["id"],
                        "items": order_items,
                        "nota": sale_note,
                        "recibido": cash_received if payment_method == "Efectivo" else None,
                        "cambio": (cash_received - order_total) if payment_method == "Efectivo" else None,
                    }
                    db.collection("ventas").add(sale_doc)

                    logo_src = f"data:image/png;base64,{brand['logo_b64']}" if brand.get("logo_b64") else ""
                    items_html = "".join(
                        [
                            f"<tr><td>{x.get('n','')}</td><td align='center'>{x.get('q',1)}</td><td align='right'>{money(float(x.get('p',0))*int(x.get('q',1)))}</td></tr>"
                            for x in order_items
                        ]
                    )

                    recibido_html = f"<div>RECIBIDO: {money(cash_received)}</div><div>CAMBIO: {money(cash_received - order_total)}</div>" if payment_method == "Efectivo" else ""

                    ticket_html = f"""
                    <div style="width:280px; font-family:monospace; font-size:12px; color:black; padding:12px; background:white;">
                        <center>
                            {f'<img src="{logo_src}" width="90"><br>' if logo_src else ''}
                            <b>{brand.get('nombre','KIN House')}</b><br>
                            {brand.get('slogan','Mismo sabor, mismo lugar')}<br>
                            {now_cdmx().strftime('%d/%m/%Y %H:%M')}<br>
                            Folio: {sale_folio}<br>
                            Mesa: {st.session_state.enom}
                        </center>
                        <hr>
                        <table width="100%">
                            <tr><th align="left">Producto</th><th>Cant</th><th align="right">Imp</th></tr>
                            {items_html}
                        </table>
                        <hr>
                        <div>MÉTODO: {payment_method}</div>
                        {recibido_html}
                        <div align="right"><b>TOTAL: {money(order_total)}</b></div>
                        {f'<div>NOTA: {sale_note}</div>' if sale_note else ''}
                        <br>
                        <center>¡Gracias por tu compra!</center>
                    </div>
                    <script>
                        window.print();
                    </script>
                    """
                    components.html(ticket_html, height=0)

                    db.collection("comandas").document(st.session_state.cid).update({
                        "estado": "CERRADA",
                        "closed_at": now_iso(),
                        "venta_folio": sale_folio,
                        "total": order_total,
                    })
                    close_ticket_session()
                    st.success(f"Venta registrada: {sale_folio}")
                    st.rerun()

            if st.button("Salir sin cerrar comanda"):
                close_ticket_session()
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# VIEW: CAJA
# ============================================================
elif menu_nav == "💵 Caja":
    st.title("💵 Caja")
    cashbox = get_open_cashbox()

    if not cashbox:
        c1, c2 = st.columns(2)
        initial_fund = c1.number_input("Fondo Inicial", min_value=0.0, step=100.0)
        cash_user = c2.text_input("Usuario")

        if st.button("ABRIR CAJA", type="primary"):
            if not cash_user.strip():
                st.warning("Ingresa el nombre del usuario para abrir la caja.")
            else:
                db.collection("cajas").add({
                    "monto_inicial": initial_fund,
                    "usuario": cash_user.strip(),
                    "estado": "ABIERTA",
                    "fecha": now_iso(),
                    "created_at": now_iso(),
                })
                st.success("Caja abierta correctamente.")
                st.rerun()
    else:
        sales_docs = list(db.collection("ventas").where("caja_id", "==", cashbox["id"]).stream())
        expenses_docs = list(db.collection("egresos").where("caja_id", "==", cashbox["id"]).stream())

        sales = [x.to_dict() for x in sales_docs]
        expenses = [x.to_dict() for x in expenses_docs]

        total_sales = sum(float(x.get("total", 0)) for x in sales)
        total_expenses = sum(float(x.get("monto", 0)) for x in expenses)
        expected_cash = float(cashbox.get("monto_inicial", 0)) + total_sales - total_expenses

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fondo inicial", money(cashbox.get("monto_inicial", 0)))
        c2.metric("Ventas", money(total_sales))
        c3.metric("Egresos", f"-{money(total_expenses)}")
        c4.metric("Efectivo esperado", money(expected_cash))

        st.divider()

        with st.expander("💸 Registrar gasto"):
            col1, col2 = st.columns([2, 1])
            expense_reason = col1.text_input("Motivo")
            expense_amount = col2.number_input("Monto", min_value=0.0, step=10.0)
            if st.button("Guardar gasto"):
                if not expense_reason.strip() or expense_amount <= 0:
                    st.warning("Completa motivo y monto mayor a 0.")
                else:
                    db.collection("egresos").add({
                        "caja_id": cashbox["id"],
                        "motivo": expense_reason.strip(),
                        "monto": expense_amount,
                        "fecha": now_iso(),
                    })
                    st.success("Gasto registrado.")
                    st.rerun()

        with st.expander("🧾 Detalle de movimientos", expanded=True):
            if sales:
                df_sales = pd.DataFrame(sales)
                show_cols = [c for c in ["fecha", "folio", "mesa", "total", "metodo", "nota"] if c in df_sales.columns]
                st.markdown("**Ventas**")
                st.dataframe(df_sales[show_cols], use_container_width=True, hide_index=True)
            else:
                st.info("No hay ventas registradas en esta caja.")

            if expenses:
                df_exp = pd.DataFrame(expenses)
                show_cols = [c for c in ["fecha", "motivo", "monto"] if c in df_exp.columns]
                st.markdown("**Egresos**")
                st.dataframe(df_exp[show_cols], use_container_width=True, hide_index=True)

        counted_cash = st.number_input("Efectivo contado al cierre", min_value=0.0, step=10.0)
        diff = counted_cash - expected_cash
        st.caption(f"Diferencia contra esperado: {money(diff)}")

        if st.button("CERRAR TURNO", type="primary"):
            db.collection("cajas").document(cashbox["id"]).update({
                "estado": "CERRADA",
                "cierre": now_iso(),
                "efectivo_esperado": expected_cash,
                "efectivo_contado": counted_cash,
                "diferencia": diff,
            })
            close_ticket_session()
            st.success("Caja cerrada correctamente.")
            st.rerun()


# ============================================================
# VIEW: CONFIG
# ============================================================
elif menu_nav == "⚙️ Config":
    st.title("⚙️ Configuración")

    if not is_admin:
        st.warning("Ingresa el PIN de admin para modificar la configuración.")
        st.stop()

    with st.form("cfg_form"):
        brand_name = st.text_input("Nombre del negocio", value=brand.get("nombre", "KIN House"))
        slogan = st.text_input("Slogan", value=brand.get("slogan", "Mismo sabor, mismo lugar"))
        logo_file = st.file_uploader("Logo", type=["png", "jpg", "jpeg"])

        if st.form_submit_button("Guardar configuración"):
            payload = {"nombre": brand_name.strip(), "slogan": slogan.strip()}
            if logo_file is not None:
                payload["logo_b64"] = base64.b64encode(logo_file.read()).decode()
            db.collection("config").document("branding").set(payload, merge=True)
            st.success("Configuración guardada.")
            st.rerun()


# ============================================================
# VIEW: REPORTE
# ============================================================
elif menu_nav == "📊 Reporte":
    st.title("📊 Reporte")

    if not is_admin:
        st.warning("Ingresa el PIN de admin para ver reportes.")
        st.stop()

    sales_docs = list(db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).limit(500).stream())
    rows = [x.to_dict() for x in sales_docs]

    if not rows:
        st.info("No hay ventas registradas.")
        st.stop()

    df = pd.DataFrame(rows)

    if "fecha" in df.columns:
        df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["dia"] = df["fecha_dt"].dt.date.astype(str)
    else:
        df["dia"] = "Sin fecha"

    methods = sorted(df["metodo"].dropna().unique().tolist()) if "metodo" in df.columns else []
    spaces = sorted(df["mesa"].dropna().unique().tolist()) if "mesa" in df.columns else []

    f1, f2, f3 = st.columns(3)
    method_filter = f1.multiselect("Método", methods, default=methods)
    space_filter = f2.multiselect("Mesa / espacio", spaces, default=spaces)
    day_filter = f3.selectbox("Agrupar por día", ["Todos"] + sorted(df["dia"].dropna().unique().tolist(), reverse=True))

    filtered = df.copy()
    if method_filter:
        filtered = filtered[filtered["metodo"].isin(method_filter)]
    if space_filter:
        filtered = filtered[filtered["mesa"].isin(space_filter)]
    if day_filter != "Todos":
        filtered = filtered[filtered["dia"] == day_filter]

    total_sales = float(filtered["total"].sum()) if "total" in filtered.columns else 0
    total_tickets = int(len(filtered))
    avg_ticket = total_sales / total_tickets if total_tickets else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Ventas", money(total_sales))
    k2.metric("Tickets", f"{total_tickets:,}")
    k3.metric("Ticket promedio", money(avg_ticket))

    st.divider()

    if "metodo" in filtered.columns:
        pay_summary = filtered.groupby("metodo", as_index=False)["total"].sum().sort_values("total", ascending=False)
        st.markdown("**Ventas por método de pago**")
        st.dataframe(pay_summary, use_container_width=True, hide_index=True)

    if "mesa" in filtered.columns:
        space_summary = filtered.groupby("mesa", as_index=False)["total"].sum().sort_values("total", ascending=False)
        st.markdown("**Ventas por mesa / espacio**")
        st.dataframe(space_summary, use_container_width=True, hide_index=True)

    show_cols = [c for c in ["fecha", "folio", "mesa", "total", "metodo", "nota"] if c in filtered.columns]
    st.markdown("**Detalle**")
    st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Descargar CSV",
        data=csv,
        file_name=f"kin_report_{now_cdmx().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
