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
# KIN HOUSE POS PRO — VERSION MEJORADA (ESTÉTICA Y CATÁLOGO DINÁMICO)
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
# FIREBASE INIT
# ---------------------------
@st.cache_resource
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
# SESSION STATE
# ---------------------------
def init_state():
    defaults = {
        "cid": None,
        "enom": None,
        "dialog_payload": None,
        "catalog": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ---------------------------
# STYLES (ESTÉTICA MEJORADA)
# ---------------------------
st.markdown(
    """
<style>
    :root {
        --kin-cream: #FAF8F5;
        --kin-black: #1A1A1A;
        --kin-gold: #C5A880;
        --kin-green: #27AE60;
        --kin-red: #E74C3C;
        --kin-blue: #2980B9;
        --kin-card: #FFFFFF;
        --kin-gray: #7F8C8D;
        --kin-border: #EAECEE;
    }

    .stApp {
        background-color: var(--kin-cream);
        font-family: 'Inter', sans-serif;
    }

    /* Tarjetas de Mesas */
    .mesa-card {
        padding: 20px 15px;
        border-radius: 16px;
        text-align: center;
        font-weight: 800;
        margin-bottom: 12px;
        color: white;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        font-size: 17px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .mesa-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 14px 28px rgba(0,0,0,0.12);
    }

    /* Tarjetas KPI y Ticket */
    .kpi-card, .ticket-box {
        background: var(--kin-card);
        border-radius: 18px;
        padding: 20px;
        border: 1px solid var(--kin-border);
        box-shadow: 0 8px 24px rgba(0,0,0,0.04);
    }

    .section-title {
        font-weight: 800;
        font-size: 20px;
        margin-top: 12px;
        margin-bottom: 12px;
        color: var(--kin-black);
        border-bottom: 2px solid var(--kin-gold);
        padding-bottom: 4px;
        display: inline-block;
    }

    /* Botones de menú */
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        font-weight: 700;
        min-height: 4em;
        border: 1px solid var(--kin-border);
        font-size: 13px;
        background-color: white;
        transition: all 0.2s ease;
        color: var(--kin-black);
    }

    .stButton > button:hover {
        border-color: var(--kin-gold);
        color: var(--kin-gold);
        background-color: #FFFAF0;
        box-shadow: 0 4px 12px rgba(197, 168, 128, 0.15);
    }
    
    /* Botones Primarios (Cobrar) */
    button[data-baseweb="button"][kind="primary"] {
        background-color: var(--kin-black) !important;
        color: white !important;
        border: none !important;
        font-size: 15px !important;
        letter-spacing: 0.5px;
    }
    button[data-baseweb="button"][kind="primary"]:hover {
        background-color: var(--kin-gold) !important;
        transform: scale(1.02);
    }

    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        padding-bottom: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 12px;
        padding: 12px 20px;
        border: 1px solid var(--kin-border);
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--kin-black) !important;
        color: white !important;
        border-color: var(--kin-black) !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


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
# CATÁLOGO DINÁMICO
# ---------------------------
CATALOG_DEFAULT = {
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
            {"name": "Chilaquiles Express", "base": 45, "options": ["Salsa Verde", "Salsa Roja", "Mixtos"]},
            {"name": "Chilaquiles Normales", "base": 129, "options": ["Salsa Verde", "Salsa Roja", "Mixtos"]},
            {"name": "Enfrijoladas", "base": 129, "options": ["Con Pollo", "Sencillas", "Con Huevo"]},
            {"name": "Molletes", "base": 99, "options": ["Sencillos", "Con Jamón", "Con Chorizo"]},
            {"name": "Sincronizadas", "base": 99, "options": ["Sencillas"]},
            {"name": "Orden de Hotcakes", "base": 99, "options": ["Sencillos", "Con Fruta +$15", "Con Tocino +$20"]},
        ],
    },
    "Café/Barra": {
        "Cafetería": [
            {"name": "Espresso", "base": 39, "options": ["Sencillo", "Doble $49"]},
            {"name": "Americano", "base": 45, "options": ["Chico $45", "Grande $55"]},
            {"name": "Café del día Chiapas", "base": 35, "options": ["Chico"]},
            {"name": "Café de olla", "base": 45, "options": ["Chico $45", "Grande $55"]},
            {"name": "Bebidas con leche", "base": 65, "options": {"mode": "builder", "sizes": [{"label": "Chico", "price": 65}, {"label": "Grande", "price": 75}], "flavors": ["Lechero", "Mocha", "Capuccino", "Latte", "Chai latte", "Matcha", "Taro", "Horchata", "Temporada"], "extras": [{"label": "Leche Entera", "price": 0}, {"label": "Leche Deslactosada", "price": 10}, {"label": "Leche Light", "price": 10}, {"label": "Leche Vegetal", "price": 15}]}},
            {"name": "Té / Limonada", "base": 40, "options": {"mode": "builder", "sizes": [{"label": "Chico", "price": 40}, {"label": "Grande", "price": 45}], "flavors": ["Té", "Limonada"], "extras": []}},
            {"name": "Frappé", "base": 69, "options": {"mode": "builder", "sizes": [{"label": "Chico", "price": 69}, {"label": "Grande", "price": 79}], "flavors": ["Matcha", "Horchata", "Chai", "Mocha", "Taro", "Temporada", "Cookies", "Café"], "extras": [{"label": "Leche Deslactosada", "price": 10}, {"label": "Leche Vegetal", "price": 15}]}},
        ],
        "Especialidad": [
            {"name": "Bebida de especialidad", "base": 79, "options": {"mode": "builder", "sizes": [{"label": "Caliente", "price": 79}, {"label": "Frío", "price": 89}], "flavors": ["Caramel Machiatto", "Dirty Chai", "Dirty Horchata", "Chocolate Mexicano", "Crawnberry Mocha Blanco", "Chocoreta"], "extras": [{"label": "Leche Entera", "price": 0}, {"label": "Leche Deslactosada", "price": 10}, {"label": "Leche Vegetal", "price": 15}]} }
        ],
    },
    "Bebidas/Helados": {
        "Bebidas frías": [
            {"name": "Malteada Normal", "base": 89, "options": ["Chica $89", "Grande $99"]},
            {"name": "Malteada Special (Espesa)", "base": 99, "options": ["Chica $99", "Grande $115"]},
            {"name": "Refresco", "base": 45, "options": ["Coca Cola", "Sprite", "Fanta"]},
            {"name": "Agua", "base": 30, "options": ["Natural", "Mineral"]},
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
            {"name": "2 chocolates grandes + 6 churros tradicionales", "base": 229, "options": {"mode": "builder", "sizes": [{"label": "Grande", "price": 229}], "flavors": ["Chocolate Suizo", "Chocolate Semi Amargo"], "extras": []}},
            {"name": "1 chocolate + 3 churros tradicionales", "base": 109, "options": {"mode": "builder", "sizes": [{"label": "Grande", "price": 109}], "flavors": ["Chocolate Suizo", "Chocolate Semi Amargo"], "extras": []}},
            {"name": "2 granizados", "base": 99, "options": ["Limón", "Fresa", "Mango"]},
            {"name": "Combo Café + Sandwich", "base": 89, "options": ["Café americano", "Latte +$10"]},
        ]
    },
}

def load_catalog():
    if st.session_state.catalog is None:
        try:
            doc = db.collection("config").document("catalog").get()
            if doc.exists:
                st.session_state.catalog = doc.to_dict().get("data", CATALOG_DEFAULT)
            else:
                db.collection("config").document("catalog").set({"data": CATALOG_DEFAULT})
                st.session_state.catalog = CATALOG_DEFAULT
        except Exception:
            st.session_state.catalog = CATALOG_DEFAULT
    return st.session_state.catalog

def save_catalog(new_catalog):
    st.session_state.catalog = new_catalog
    try:
        db.collection("config").document("catalog").set({"data": new_catalog})
        return True
    except Exception as e:
        st.error(f"Error guardando catálogo: {e}")
        return False

CATALOG = load_catalog()

# ---------------------------
# PRICE ENGINE
# ---------------------------
def infer_price(base_price: float, option_text: str) -> float:
    opt = str(option_text).strip()
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

def build_item_from_builder(prod_name: str, config: dict):
    sizes = config.get("sizes", [])
    flavors = config.get("flavors", [])
    extras = config.get("extras", [])

    size_labels = [x.get("label", "") for x in sizes] or ["Único"]
    selected_size = st.selectbox("Tamaño / tipo", size_labels, key=f"size_{prod_name}")
    selected_size_obj = next((x for x in sizes if x.get("label") == selected_size), {"label": selected_size, "price": config.get("base", 0)})

    selected_flavor = None
    if flavors:
        selected_flavor = st.selectbox("Sabor / variante", flavors, key=f"flavor_{prod_name}")

    selected_extras = []
    extra_total = 0
    if extras:
        st.markdown("**Adicionales (Leche, Toppings, etc.)**")
        extra_cols = st.columns(2)
        for i, extra in enumerate(extras):
            price_extra = extra.get('price', 0)
            label_disp = f"{extra.get('label')} (+{money(price_extra)})" if price_extra > 0 else f"{extra.get('label')}"
            checked = extra_cols[i % 2].checkbox(label_disp, key=f"extra_{prod_name}_{i}")
            if checked:
                selected_extras.append(extra.get("label"))
                extra_total += float(price_extra)

    final_price = float(selected_size_obj.get("price", config.get("base", 0))) + extra_total

    parts = [prod_name, selected_size_obj.get("label")]
    if selected_flavor:
        parts.append(selected_flavor)
    if selected_extras:
        parts.append(" / ".join(selected_extras))

    item_name = " · ".join([p for p in parts if p])
    return item_name, final_price


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
    base_price = payload["price"]
    options = payload["options"]
    doc_id = payload["doc_id"]

    st.markdown(f"### {prod_name}")
    st.markdown(f"**Precio base:** {money(base_price)}")

    order = load_order(doc_id)
    items = order.get("items", [])

    if isinstance(options, dict) and options.get("mode") == "builder":
        item_name, final_price = build_item_from_builder(prod_name, options)
    else:
        # Array simple
        if not options:
            options = ["Única"]
        selected_option = st.selectbox("Selecciona preparación u opción:", options, key=f"opt_{prod_name}")
        final_price = infer_price(base_price, selected_option)
        item_name = f"{prod_name} ({selected_option})"

    st.markdown("---")
    st.markdown(f"#### 💰 Total: <span style='color:var(--kin-green)'>{money(final_price)}</span>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    if col1.button("Agregar a la cuenta", use_container_width=True, type="primary"):
        items.append({
            "n": item_name,
            "p": final_price,
            "q": 1,
            "added_at": now_iso(),
        })
        total = calc_total(items)
        update_order(doc_id, items, total)
        st.session_state.dialog_payload = None
        st.rerun()

    if col2.button("Cancelar", use_container_width=True):
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

    st.markdown(f"## {brand.get('nombre', 'KIN House')}")
    st.caption(brand.get("slogan", "Mismo sabor, mismo lugar"))
    st.markdown("---")

    menu_nav = st.radio("MENÚ PRINCIPAL", ["🪑 Mesas", "💵 Caja", "📊 Reporte", "⚙️ Config"], label_visibility="collapsed")
    st.markdown("---")
    admin_pin = st.text_input("🔑 PIN Admin", type="password")
    is_admin = admin_pin == get_admin_pin()


# ============================================================
# VIEW: MESAS
# ============================================================
if menu_nav == "🪑 Mesas":
    st.title("🪑 Mesas y Zonas")
    cashbox = get_open_cashbox()

    if not cashbox:
        st.error("🛑 No hay caja abierta. Ve a la sección 'Caja' para iniciar el turno.")
        st.stop()

    spaces = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar"]
    open_orders = get_open_orders_by_space()

    cols = st.columns(4)
    for i, space in enumerate(spaces):
        with cols[i % 4]:
            occupied = space in open_orders
            bg = "var(--kin-red)" if occupied else "var(--kin-green)"
            st.markdown(f'<div class="mesa-card" style="background:{bg};">{space}</div>', unsafe_allow_html=True)
            if st.button(f"Abrir / Ver Cuenta", key=f"space_{space}"):
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

        st.markdown("---")
        st.subheader(f"📍 Atendiendo: **{st.session_state.enom}**")

        col_menu, col_ticket = st.columns([2.4, 1])

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
            st.markdown("### 🧾 Cuenta Actual")

            if not order_items:
                st.info("Aún no hay productos.")
            else:
                for idx, item in enumerate(order_items):
                    left, right = st.columns([4, 1])
                    qty = int(item.get("q", 1))
                    unit_price = float(item.get("p", 0))
                    line_total = qty * unit_price
                    left.markdown(f"**{item.get('n', 'Producto')}**<br><small style='color:gray'>x{qty} · {money(line_total)}</small>", unsafe_allow_html=True)

                    if right.button("🗑️", key=f"rm_{idx}"):
                        order_items.pop(idx)
                        new_total = calc_total(order_items)
                        update_order(st.session_state.cid, order_items, new_total)
                        st.rerun()

                st.markdown("<hr style='margin: 10px 0'>", unsafe_allow_html=True)

            st.subheader(f"Total: {money(order_total)}")

            payment_method = st.selectbox("Método de pago", ["Efectivo", "Tarjeta", "Transferencia"])
            cash_received = 0.0
            if payment_method == "Efectivo":
                cash_received = st.number_input("Efectivo Recibido", min_value=0.0, step=10.0)
                change = max(cash_received - order_total, 0)
                if cash_received > 0:
                    st.success(f"Cambio a entregar: **{money(change)}**")

            can_charge = order_total > 0 and (payment_method != "Efectivo" or cash_received >= order_total)

            sale_note = st.text_input("Nota / comentario (opcional)")

            if st.button("COBRAR E IMPRIMIR TICKET", type="primary", disabled=not can_charge):
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
                        <table width="100%" style="font-size:11px;">
                            <tr><th align="left">Prod</th><th>Cant</th><th align="right">Imp</th></tr>
                            {items_html}
                        </table>
                        <hr>
                        <div>MÉTODO: {payment_method}</div>
                        {recibido_html}
                        <div align="right" style="font-size:14px; margin-top:5px;"><b>TOTAL: {money(order_total)}</b></div>
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
                    st.success(f"Venta registrada con éxito: {sale_folio}")
                    st.rerun()

            if st.button("Guardar en espera y Salir"):
                close_ticket_session()
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# VIEW: CAJA
# ============================================================
elif menu_nav == "💵 Caja":
    st.title("💵 Gestión de Caja")
    cashbox = get_open_cashbox()

    if not cashbox:
        st.info("No hay ningún turno abierto actualmente.")
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.subheader("Abrir Nuevo Turno")
        c1, c2 = st.columns(2)
        initial_fund = c1.number_input("Fondo Inicial (Fondo de Caja)", min_value=0.0, step=100.0)
        cash_user = c2.text_input("Nombre del Cajero / Usuario")

        if st.button("ABRIR CAJA", type="primary"):
            if not cash_user.strip():
                st.warning("Ingresa el nombre del cajero para abrir la caja.")
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
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        sales_docs = list(db.collection("ventas").where("caja_id", "==", cashbox["id"]).stream())
        expenses_docs = list(db.collection("egresos").where("caja_id", "==", cashbox["id"]).stream())

        sales = [x.to_dict() for x in sales_docs]
        expenses = [x.to_dict() for x in expenses_docs]

        total_sales = sum(float(x.get("total", 0)) for x in sales)
        total_expenses = sum(float(x.get("monto", 0)) for x in expenses)
        expected_cash = float(cashbox.get("monto_inicial", 0)) + sum(float(x.get("recibido", x.get("total", 0))) - float(x.get("cambio", 0)) for x in sales if x.get("metodo") == "Efectivo") - total_expenses
        
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.write(f"**Cajero:** {cashbox.get('usuario', 'N/A')} | **Abierta desde:** {pd.to_datetime(cashbox.get('fecha')).strftime('%H:%M %d/%m/%Y')}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fondo inicial", money(cashbox.get("monto_inicial", 0)))
        c2.metric("Ventas Totales", money(total_sales))
        c3.metric("Egresos/Gastos", f"-{money(total_expenses)}")
        c4.metric("Efectivo Esperado", money(expected_cash))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("💸 Registrar Retiro o Gasto"):
            col1, col2 = st.columns([2, 1])
            expense_reason = col1.text_input("Motivo del gasto (Ej. Insumos, Retiro)")
            expense_amount = col2.number_input("Monto a retirar", min_value=0.0, step=10.0)
            if st.button("Guardar Gasto"):
                if not expense_reason.strip() or expense_amount <= 0:
                    st.warning("Completa el motivo y asegura que el monto sea mayor a 0.")
                else:
                    db.collection("egresos").add({
                        "caja_id": cashbox["id"],
                        "motivo": expense_reason.strip(),
                        "monto": expense_amount,
                        "fecha": now_iso(),
                    })
                    st.success("Gasto registrado.")
                    st.rerun()

        with st.expander("🧾 Detalle de Movimientos", expanded=True):
            if sales:
                df_sales = pd.DataFrame(sales)
                show_cols = [c for c in ["fecha", "folio", "mesa", "total", "metodo", "nota"] if c in df_sales.columns]
                st.markdown("**Ventas Realizadas**")
                st.dataframe(df_sales[show_cols], use_container_width=True, hide_index=True)
            else:
                st.info("No hay ventas registradas en este turno.")

            if expenses:
                df_exp = pd.DataFrame(expenses)
                show_cols = [c for c in ["fecha", "motivo", "monto"] if c in df_exp.columns]
                st.markdown("**Gastos / Retiros**")
                st.dataframe(df_exp[show_cols], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Corte de Caja")
        counted_cash = st.number_input("Efectivo Físico Contado", min_value=0.0, step=10.0)
        diff = counted_cash - expected_cash
        
        if diff == 0:
            st.success("La caja está cuadrada (Diferencia: $0)")
        elif diff < 0:
            st.error(f"Faltante en caja: {money(diff)}")
        else:
            st.warning(f"Sobrante en caja: {money(diff)}")

        if st.button("CERRAR TURNO", type="primary"):
            db.collection("cajas").document(cashbox["id"]).update({
                "estado": "CERRADA",
                "cierre": now_iso(),
                "efectivo_esperado": expected_cash,
                "efectivo_contado": counted_cash,
                "diferencia": diff,
            })
            close_ticket_session()
            st.success("Caja cerrada correctamente. Buen trabajo.")
            st.rerun()


# ============================================================
# VIEW: CONFIG & CATALOG ADMIN
# ============================================================
elif menu_nav == "⚙️ Config":
    st.title("⚙️ Configuración y Catálogo")

    if not is_admin:
        st.warning("🔒 Área Restringida. Ingresa el PIN de administrador en el menú lateral.")
        st.stop()

    tab_brand, tab_catalog = st.tabs(["🎨 Branding de Ticket", "📦 Gestión de Menú (Catálogo)"])

    with tab_brand:
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.subheader("Identidad del Negocio")
        with st.form("cfg_form"):
            brand_name = st.text_input("Nombre del negocio", value=brand.get("nombre", "KIN House"))
            slogan = st.text_input("Slogan", value=brand.get("slogan", "Mismo sabor, mismo lugar"))
            logo_file = st.file_uploader("Logo para Ticket", type=["png", "jpg", "jpeg"])

            if st.form_submit_button("Guardar Identidad", type="primary"):
                payload = {"nombre": brand_name.strip(), "slogan": slogan.strip()}
                if logo_file is not None:
                    payload["logo_b64"] = base64.b64encode(logo_file.read()).decode()
                db.collection("config").document("branding").set(payload, merge=True)
                st.success("Configuración guardada.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_catalog:
        st.info("💡 Aquí puedes agregar nuevas categorías, crear productos o editar sus precios y variantes.")
        
        cat_keys = list(CATALOG.keys())
        selected_cat = st.selectbox("1. Selecciona la Categoría Principal", cat_keys + ["+ Crear Nueva Categoría"])
        
        if selected_cat == "+ Crear Nueva Categoría":
            new_cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.button("Añadir Categoría"):
                if new_cat_name:
                    CATALOG[new_cat_name] = {}
                    save_catalog(CATALOG)
                    st.success("Categoría creada.")
                    st.rerun()
        else:
            sec_keys = list(CATALOG[selected_cat].keys())
            selected_sec = st.selectbox("2. Selecciona la Subsección", sec_keys + ["+ Crear Nueva Subsección"])
            
            if selected_sec == "+ Crear Nueva Subsección":
                new_sec_name = st.text_input("Nombre de la Nueva Subsección")
                if st.button("Añadir Subsección"):
                    if new_sec_name:
                        CATALOG[selected_cat][new_sec_name] = []
                        save_catalog(CATALOG)
                        st.success("Subsección creada.")
                        st.rerun()
            else:
                st.markdown("---")
                st.subheader(f"3. Productos en {selected_sec}")
                
                products = CATALOG[selected_cat][selected_sec]
                prod_names = [p["name"] for p in products]
                
                selected_prod_idx = st.selectbox(
                    "Selecciona producto a editar, o elige añadir uno nuevo:", 
                    ["+ AÑADIR NUEVO PRODUCTO"] + [f"Editar: {name}" for name in prod_names]
                )

                with st.form("product_form"):
                    if selected_prod_idx == "+ AÑADIR NUEVO PRODUCTO":
                        p_name = st.text_input("Nombre del Producto")
                        p_price = st.number_input("Precio Base ($)", min_value=0.0, step=1.0)
                        p_opts_str = st.text_area("Opciones (separadas por coma)", value="Sencillo", help="Ej. Salsa Verde, Salsa Roja, Con Huevo +$15")
                        
                        if st.form_submit_button("Crear Producto", type="primary"):
                            opts_list = [o.strip() for o in p_opts_str.split(",") if o.strip()]
                            new_prod = {"name": p_name, "base": p_price, "options": opts_list}
                            CATALOG[selected_cat][selected_sec].append(new_prod)
                            save_catalog(CATALOG)
                            st.success(f"Producto {p_name} creado exitosamente.")
                            st.rerun()
                    else:
                        idx = prod_names.index(selected_prod_idx.replace("Editar: ", ""))
                        current_prod = products[idx]
                        
                        p_name = st.text_input("Nombre del Producto", value=current_prod["name"])
                        p_price = st.number_input("Precio Base ($)", min_value=0.0, step=1.0, value=float(current_prod["base"]))
                        
                        is_builder = isinstance(current_prod["options"], dict)
                        if is_builder:
                            st.warning("Este producto usa el modo avanzado (builder). Por ahora, solo puedes editar su nombre y precio base desde aquí.")
                            if st.form_submit_button("Actualizar Producto"):
                                CATALOG[selected_cat][selected_sec][idx]["name"] = p_name
                                CATALOG[selected_cat][selected_sec][idx]["base"] = p_price
                                save_catalog(CATALOG)
                                st.success("Producto actualizado.")
                                st.rerun()
                        else:
                            opts_str = ", ".join(current_prod["options"])
                            p_opts_str = st.text_area("Opciones / Preparaciones (separadas por coma)", value=opts_str, help="Agrega modificadores. Ej: Deslactosada +$10, Entera")
                            
                            col_save, col_del = st.columns([3, 1])
                            btn_save = col_save.form_submit_button("Actualizar Producto", type="primary")
                            btn_del = col_del.form_submit_button("Eliminar Producto")

                            if btn_save:
                                opts_list = [o.strip() for o in p_opts_str.split(",") if o.strip()]
                                CATALOG[selected_cat][selected_sec][idx] = {
                                    "name": p_name, 
                                    "base": p_price, 
                                    "options": opts_list
                                }
                                save_catalog(CATALOG)
                                st.success("Producto actualizado.")
                                st.rerun()
                                
                            if btn_del:
                                CATALOG[selected_cat][selected_sec].pop(idx)
                                save_catalog(CATALOG)
                                st.warning("Producto eliminado.")
                                st.rerun()


# ============================================================
# VIEW: REPORTE
# ============================================================
elif menu_nav == "📊 Reporte":
    st.title("📊 Reporte de Ventas")

    if not is_admin:
        st.warning("🔒 Área Restringida. Ingresa el PIN de admin.")
        st.stop()

    sales_docs = list(db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).limit(500).stream())
    rows = [x.to_dict() for x in sales_docs]

    if not rows:
        st.info("Aún no hay ventas registradas en la base de datos.")
        st.stop()

    df = pd.DataFrame(rows)

    if "fecha" in df.columns:
        df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["dia"] = df["fecha_dt"].dt.date.astype(str)
    else:
        df["dia"] = "Sin fecha"

    methods = sorted(df["metodo"].dropna().unique().tolist()) if "metodo" in df.columns else []
    spaces = sorted(df["mesa"].dropna().unique().tolist()) if "mesa" in df.columns else []

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    method_filter = f1.multiselect("Filtrar por Método", methods, default=methods)
    space_filter = f2.multiselect("Filtrar por Mesa / Zona", spaces, default=spaces)
    day_filter = f3.selectbox("Ver información del día", ["Todos los días"] + sorted(df["dia"].dropna().unique().tolist(), reverse=True))
    st.markdown('</div>', unsafe_allow_html=True)

    filtered = df.copy()
    if method_filter:
        filtered = filtered[filtered["metodo"].isin(method_filter)]
    if space_filter:
        filtered = filtered[filtered["mesa"].isin(space_filter)]
    if day_filter != "Todos los días":
        filtered = filtered[filtered["dia"] == day_filter]

    total_sales = float(filtered["total"].sum()) if "total" in filtered.columns else 0
    total_tickets = int(len(filtered))
    avg_ticket = total_sales / total_tickets if total_tickets else 0

    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Ingresos Totales", money(total_sales))
    k2.metric("Tickets Emitidos", f"{total_tickets:,}")
    k3.metric("Ticket Promedio", money(avg_ticket))

    st.markdown("---")

    c_left, c_right = st.columns(2)
    with c_left:
        if "metodo" in filtered.columns:
            pay_summary = filtered.groupby("metodo", as_index=False)["total"].sum().sort_values("total", ascending=False)
            st.markdown("**Ventas por Método de Pago**")
            st.dataframe(pay_summary, use_container_width=True, hide_index=True)

    with c_right:
        if "mesa" in filtered.columns:
            space_summary = filtered.groupby("mesa", as_index=False)["total"].sum().sort_values("total", ascending=False)
            st.markdown("**Ventas por Mesa / Espacio**")
            st.dataframe(space_summary, use_container_width=True, hide_index=True)

    st.markdown("**Detalle de Todas las Ventas Filtradas**")
    show_cols = [c for c in ["fecha", "folio", "mesa", "total", "metodo", "nota"] if c in filtered.columns]
    st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Descargar Información a Excel/CSV",
        data=csv,
        file_name=f"kin_report_{now_cdmx().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        type="primary"
    )
