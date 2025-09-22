# Churrería Porfirio — App única (Streamlit)
# Navegación en tabs superiores: Inicio | Registro | Iniciar sesión | Pick Up | Pedir en mesa | Admin
# Funciones: Recompensas, Pedidos (ETA dinámico), Pago con Mercado Pago, Dashboard Admin, Pop-ups de promociones
# Autor: ChatGPT para Enrique (Kike)
# Dependencias: streamlit, firebase_admin, mercadopago (opcional pero recomendado para links de pago)
# Tiempo local: America/Mexico_City (CDMX)
# -------------------------------------------------------------

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Tuple
import random
import string

# Firebase
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------------------------------------------
# CONFIG BÁSICA
st.set_page_config(page_title="Churrería Porfirio", layout="wide")
st.title("🍩 Churrería Porfirio — Recompensas & Pedidos")
CDMX_TZ = ZoneInfo("America/Mexico_City")

# -------------------------------------------------------------
# FIREBASE INIT (usa secrets ya proporcionados)
try:
    creds = st.secrets["firebase_credentials"]
    cred = credentials.Certificate(dict(creds))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"❌ Firebase error: {e}")
    st.stop()

# -------------------------------------------------------------
# SESSION STATE
ss = st.session_state
if "usuario_actual" not in ss:
    ss.usuario_actual = None  # email del usuario logueado
if "cliente_confirmado" not in ss:
    ss.cliente_confirmado = None  # para admin al confirmar cliente
if "promo_shown" not in ss:
    ss.promo_shown = False
if "cart_pickup" not in ss:
    ss.cart_pickup = []  # [{menu_id, qty}]
if "cart_mesa" not in ss:
    ss.cart_mesa = []

# -------------------------------------------------------------
# MENÚ (lista fija inicial; luego podemos migrar a Firestore)
DEFAULT_MENU: List[Dict[str, Any]] = [
    {"id": "espresso", "name": "Espresso", "category": "Bebidas", "price": 45, "station": "barista", "prep_time": 180, "active": True},
    {"id": "americano", "name": "Americano", "category": "Bebidas", "price": 45, "station": "barista", "prep_time": 180, "active": True},
    {"id": "cafe_olla", "name": "Café de olla", "category": "Bebidas", "price": 50, "station": "barista", "prep_time": 240, "active": True},
    {"id": "capuccino", "name": "Capuccino", "category": "Bebidas", "price": 70, "station": "barista", "prep_time": 240, "active": True},
    {"id": "latte", "name": "Café Latte", "category": "Bebidas", "price": 70, "station": "barista", "prep_time": 240, "active": True},
    {"id": "chai_latte", "name": "Chai Latte", "category": "Bebidas", "price": 75, "station": "barista", "prep_time": 300, "active": True},
    {"id": "te", "name": "Té", "category": "Bebidas", "price": 45, "station": "barista", "prep_time": 180, "active": True},
    {"id": "granizado", "name": "Granizado", "category": "Bebidas", "price": 89, "station": "barista", "prep_time": 300, "active": True},
    {"id": "malteada_chica", "name": "Malteada (chica)", "category": "Bebidas", "price": 99, "station": "barista", "prep_time": 300, "active": True},
    {"id": "malteada_grande", "name": "Malteada (grande)", "category": "Bebidas", "price": 115, "station": "barista", "prep_time": 300, "active": True},
    {"id": "refresco", "name": "Refresco", "category": "Bebidas", "price": 45, "station": "barista", "prep_time": 30, "active": True},
    {"id": "agua", "name": "Agua", "category": "Bebidas", "price": 30, "station": "barista", "prep_time": 10, "active": True},
    {"id": "churros_3", "name": "Churros (3 pzas)", "category": "Churros", "price": 39, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "per_unit_type": "tradicional", "active": True},
    {"id": "churros_6", "name": "Churros (6 pzas)", "category": "Churros", "price": 69, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "per_unit_type": "tradicional", "active": True},
    {"id": "churros_12", "name": "Churros (12 pzas)", "category": "Churros", "price": 129, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "per_unit_type": "tradicional", "active": True},
    {"id": "relleno_1", "name": "Churro relleno (1 pza)", "category": "Churros", "price": 35, "station": "fryer", "prep_time": 180, "batch_capacity": 3, "per_unit_type": "relleno", "active": True},
    {"id": "relleno_3", "name": "Churro relleno (3 pzas)", "category": "Churros", "price": 99, "station": "fryer", "prep_time": 180, "batch_capacity": 3, "per_unit_type": "relleno", "active": True},
    {"id": "carlota", "name": "Carlota", "category": "Postres", "price": 75, "station": "fryer", "prep_time": 240, "batch_capacity": 1, "per_unit_type": "carlota", "active": True},
    {"id": "bunuelos_2", "name": "Buñuelos (2 pzas)", "category": "Postres", "price": 49, "station": "stock", "prep_time": 0, "active": True},
    {"id": "promo_recordando", "name": "Recordando viejos tiempos", "category": "Promoción", "price": 229, "station": "mix", "prep_time": 0, "active": True},
    {"id": "promo_dulce_dia", "name": "Empieza un dulce día", "category": "Promoción", "price": 69, "station": "mix", "prep_time": 0, "active": True},
    {"id": "promo_congelando", "name": "Congelando momentos", "category": "Promoción", "price": 99, "station": "mix", "prep_time": 0, "active": True},
]

MENU_INDEX: Dict[str, Dict[str, Any]] = {m['id']: m for m in DEFAULT_MENU}
FRYER_BASKETS = 2

# -------------------------------------------------------------
# UTILIDADES

def now_cdmx() -> datetime:
    return datetime.now(CDMX_TZ)


def money(n: float) -> str:
    return f"$ {n:,.0f}"


def generate_cliente_id(length: int = 5) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def log_action(action_type: str, usuario: str, detalle: str = "") -> None:
    try:
        db.collection("logs").add({
            "accion": action_type,
            "usuario": usuario,
            "detalle": detalle,
            "fecha": now_cdmx().isoformat()
        })
    except Exception as e:
        st.warning(f"⚠️ Error al guardar log: {e}")

# -------------------------------------------------------------
# USUARIOS (Recompensas)
# ... (todo tu código igual hasta la función show_promotions_popups)

# -------------------------------------------------------------
# POP-UPS DE PROMOCIONES (según hora CDMX)

def show_promotions_popups():
    hour = now_cdmx().hour
    if ss.promo_shown:
        return

    if 8 <= hour < 12:
        st.toast("☕ Recordando viejos tiempos: Churros + 1 litro de chocolate — $229")
        st.toast("🥐 Empieza un dulce día: Café de olla + Churro relleno — $69")
    elif 13 <= hour < 17:
        st.toast("❄️ Congelando momentos: 2 granizados — $99")

    ss.promo_shown = True

# -------------------------------------------------------------
# CÁLCULO DE CARGA Y ETA

def calc_station_work_seconds(items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Regresa (barista_seconds, fryer_seconds) para los ítems del pedido."""
    barista_total = 0
    fryer_batches_seconds = 0
    for it in items:
        item = MENU_INDEX.get(it['menu_id'])
        if not item:
            continue
        qty = int(it.get('qty', 1))
        station = item.get('station', 'barista')
        prep = int(item.get('prep_time', 180))
        if station == 'barista':
            barista_total += prep * qty  # aproximación serial
        elif station == 'fryer':
            cap = int(item.get('batch_capacity', 1))
            batches = -(-qty // cap)  # ceil
            rounds = -(-batches // FRYER_BASKETS)  # 2 canastillas paralelas
            fryer_batches_seconds += rounds * prep
        elif station == 'stock':
            fryer_batches_seconds += 0
        else:
            barista_total += prep * qty
    return barista_total, fryer_batches_seconds


def fetch_queue_load_seconds() -> Tuple[int, int]:
    barista_q = 0
    fryer_q = 0
    q = db.collection("orders").where("status", "in", ["RECEIVED", "IN_PROGRESS"]).stream()
    for d in q:
        o = d.to_dict()
        items = o.get('items', [])
        b, f = calc_station_work_seconds(items)
        barista_q += b
        fryer_q += f
    return barista_q, fryer_q


def estimate_eta_seconds(new_items: List[Dict[str, Any]]) -> int:
    q_barista, q_fryer = fetch_queue_load_seconds()
    b_new, f_new = calc_station_work_seconds(new_items)
    return max(q_barista + b_new, q_fryer + f_new)

# -------------------------------------------------------------
# PAGOS — Mercado Pago (usa token productivo de secrets)

def create_payment_link(total_amount: float, description: str = "Pedido Churrería Porfirio") -> str | None:
    access_token = st.secrets.get("mercadopago_access_token")
    if access_token:
        try:
            from mercadopago import SDK
            sdk = SDK(access_token)
            preference_data = {
                "items": [
                    {"title": description, "quantity": 1, "currency_id": "MXN", "unit_price": float(total_amount)}
                ],
                "back_urls": {
                    "success": "https://example.com/success",
                    "failure": "https://example.com/failure",
                    "pending": "https://example.com/pending",
                },
                "auto_return": "approved",
            }
            pref = sdk.preference().create(preference_data)
            return pref["response"].get("init_point") or pref["response"].get("sandbox_init_point")
        except Exception as e:
            st.warning(f"⚠️ No se pudo crear link de pago con Mercado Pago: {e}")
    return st.secrets.get("mp_payment_link")

# -------------------------------------------------------------
# UI — Carrito

def render_menu_picker(cart_key: str = "cart_pickup"):
    st.subheader("🧾 Menú")
    cat = st.selectbox(
    "Filtrar por categoría",
    options=["Todas"] + sorted({m['category'] for m in DEFAULT_MENU}),
    key=f"cat_select_{cart_key}"   # 👈 evita duplicados
)
    cols = st.columns(3)
    filtered = [m for m in DEFAULT_MENU if m.get("active") and (cat == "Todas" or m['category'] == cat)]
    for i, m in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(f"**{m['name']}**")
            st.caption(f"{m['category']} — {money(m['price'])}")
            qty = st.number_input("Cantidad", min_value=1, value=1, key=f"qty_{cart_key}_{m['id']}")
            if st.button("Agregar", key=f"add_{cart_key}_{m['id']}"):
                ss[cart_key].append({"menu_id": m['id'], "qty": int(qty)})
                st.toast(f"Agregado: {m['name']} x{qty}")


def render_cart_and_total(cart_key: str = "cart_pickup") -> Tuple[float, List[Dict[str, Any]]]:
    cart = ss[cart_key]
    st.subheader("🧺 Tu pedido")
    if not cart:
        st.info("Tu carrito está vacío.")
        return 0.0, []
    subtotal = 0.0
    new_cart: List[Dict[str, Any]] = []
    for i, it in enumerate(cart):
        item = MENU_INDEX.get(it['menu_id'])
        if not item:
            continue
        qty = int(it.get('qty', 1))
        price = float(item.get('price', 0))
        line = price * qty
        subtotal += line
        cols = st.columns([5,2,2,2])
        with cols[0]:
            st.write(f"**{item['name']}** — {money(price)}")
        with cols[1]:
            qty_new = st.number_input("Cant.", min_value=1, value=qty, key=f"cartqty_{cart_key}_{i}")
        with cols[2]:
            st.write(money(line))
        with cols[3]:
            if st.button("Quitar", key=f"rm_{cart_key}_{i}"):
                qty_new = 0
        if qty_new > 0:
            new_cart.append({"menu_id": it['menu_id'], "qty": int(qty_new)})
    ss[cart_key] = new_cart
    st.markdown(f"### Total: {money(subtotal)}")
    return subtotal, new_cart

# -------------------------------------------------------------
# PERSISTENCIA DE ÓRDENES

def persist_order(order: Dict[str, Any]) -> str | None:
    try:
        ref = db.collection("orders").add(order)
        return ref[1].id
    except Exception as e:
        st.error(f"❌ No se pudo guardar el pedido: {e}")
        return None

# -------------------------------------------------------------
# TABS SUPERIORES (sin sidebar)
show_promotions_popups()

(inicio_tab, registro_tab, login_tab, pickup_tab, mesa_tab, admin_tab) = st.tabs([
    "🏠 Inicio", "📝 Registro", "🔐 Iniciar sesión", "🚗 Pick Up", "🍽️ Pedir en mesa", "👑 Admin"
])

# -------------------- INICIO --------------------
with inicio_tab:
    st.subheader("Bienvenid@ a Churrería Porfirio")
    if ss.usuario_actual:
        user = get_user(ss.usuario_actual)
        if user:
            st.success(f"Hola, {user['email']}")
            show_user_summary(user)
    else:
        st.info("Inicia sesión o regístrate para acumular estrellas y helados.")

# -------------------- REGISTRO --------------------
with registro_tab:
    st.subheader("Registro de usuario")
    email = st.text_input("Correo electrónico", key="reg_email")
    password = st.text_input("Contraseña", type="password", key="reg_pwd")
    if st.button("Registrarse", key="btn_reg"):
        try:
            if get_user(email):
                st.error("❌ Este correo ya está registrado. Usa otro.")
            else:
                cliente_id = generate_cliente_id()
                data = {
                    "email": email,
                    "cliente_id": cliente_id,
                    "nivel": "green",
                    "estrellas": 0,
                    "helados": 0,
                    "canjear_helado": False,
                    "fecha_registro": now_cdmx().isoformat(),
                }
                save_user(email, data)
                st.success("✅ Usuario registrado con éxito")
                st.info(f"Tu número de cliente es: **{cliente_id}**")
        except Exception as e:
            st.error(f"Error al registrar: {e}")

# -------------------- INICIAR SESIÓN --------------------
with login_tab:
    st.subheader("Inicio de sesión")
    identifier = st.text_input("Correo o número de cliente", key="login_ident")
    password = st.text_input("Contraseña", type="password", key="login_pwd")
    if st.button("Iniciar sesión", key="btn_login"):
        user = get_user(identifier)
        if user:
            ss.usuario_actual = user['email']
            st.success(f"Bienvenido {user['email']}")
        else:
            st.error("Usuario no encontrado.")
    if ss.usuario_actual and st.button("Cerrar sesión"):
        ss.usuario_actual = None
        st.experimental_rerun()

# -------------------- PICK UP --------------------
with pickup_tab:
    st.subheader("🚗 Pedido para recoger (Pick Up)")
    render_menu_picker(cart_key="cart_pickup")
    total, items = render_cart_and_total(cart_key="cart_pickup")

    if items:
        eta_sec = estimate_eta_seconds([
            {"menu_id": it['menu_id'], "qty": int(it['qty'])} for it in items
        ])
        mins = max(1, eta_sec // 60)
        st.info(f"⏱️ Tiempo estimado de espera: **{mins} min** (en cola actual)")
        if st.button("Generar pedido y pagar", key="btn_pay_pickup"):
            # Crear link de pago
            pay_link = create_payment_link(total, description="Pedido Pick Up — Churrería Porfirio")
            order = {
                "type": "PICKUP",
                "mesa": None,
                "items": items,
                "totals": {"subtotal": total, "grand_total": total},
                "status": "RECEIVED",
                "payment": {"method": "MP_LINK", "status": "PENDING", "url": pay_link},
                "eta_seconds": int(eta_sec),
                "created_at": now_cdmx().isoformat(),
                "updated_at": now_cdmx().isoformat(),
                "user_email": ss.usuario_actual,
            }
            order_id = persist_order(order)
            if order_id:
                st.success(f"✅ Pedido creado. ID: {order_id}")
                if pay_link:
                    st.link_button("Pagar ahora con Mercado Pago", pay_link)
                ss.cart_pickup = []

# -------------------- PEDIR EN MESA --------------------
with mesa_tab:
    st.subheader("🍽️ Pedir desde tu mesa")
    mesa = st.text_input("Número de mesa", key="mesa_num")
    render_menu_picker(cart_key="cart_mesa")
    total_m, items_m = render_cart_and_total(cart_key="cart_mesa")

    if items_m and mesa:
        eta_sec_m = estimate_eta_seconds(items_m)
        mins_m = max(1, eta_sec_m // 60)
        st.info(f"⏱️ Tiempo estimado de espera: **{mins_m} min**")
        if st.button("Generar pedido (pagar ahora)", key="btn_pay_mesa"):
            pay_link = create_payment_link(total_m, description=f"Pedido Mesa {mesa} — Churrería Porfirio")
            order = {
                "type": "MESA",
                "mesa": mesa,
                "items": items_m,
                "totals": {"subtotal": total_m, "grand_total": total_m},
                "status": "RECEIVED",
                "payment": {"method": "MP_LINK", "status": "PENDING", "url": pay_link},
                "eta_seconds": int(eta_sec_m),
                "created_at": now_cdmx().isoformat(),
                "updated_at": now_cdmx().isoformat(),
                "user_email": ss.usuario_actual,
            }
            order_id = persist_order(order)
            if order_id:
                st.success(f"✅ Pedido creado. ID: {order_id}")
                if pay_link:
                    st.link_button("Pagar ahora con Mercado Pago", pay_link)
                ss.cart_mesa = []

# -------------------- ADMIN --------------------
with admin_tab:
    st.subheader("👑 Panel del Administrador")
    admin_data = st.secrets.get("admin_credentials", None)
    admin_email = st.text_input("Correo de Admin", key="ad_email")
    admin_pass = st.text_input("Contraseña Admin", type="password", key="ad_pwd")

    if admin_data and admin_email == admin_data["email"] and admin_pass == admin_data["password"]:
        st.success("Acceso autorizado como admin")

        # KPIs
        st.markdown("### Resumen del día")
        today = now_cdmx().date().isoformat()
        orders_today = [o.to_dict() for o in db.collection("orders").where("created_at", ">=", today).stream()]
        in_queue = [o for o in orders_today if o.get('status') in ("RECEIVED", "IN_PROGRESS")]
        ready = [o for o in orders_today if o.get('status') == "READY"]
        delivered = [o for o in orders_today if o.get('status') == "DELIVERED"]
        ingreso = sum(float(o.get('totals', {}).get('grand_total', 0)) for o in orders_today)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Pedidos hoy", len(orders_today))
        k2.metric("En cola", len(in_queue))
        k3.metric("Listos", len(ready))
        k4.metric("Ingresos (MXN)", money(ingreso))

        st.markdown("---")
        st.markdown("### Cola de pedidos")
        q = db.collection("orders").where("status", "in", ["RECEIVED", "IN_PROGRESS", "READY"]).stream()
        for d in q:
            o = d.to_dict()
            oid = d.id
            cols = st.columns([3,2,2,3,2])
            with cols[0]:
                st.write(f"**{oid[:6]}** — {o.get('type')} {(o.get('mesa') or '')}")
                st.caption(o.get('created_at',''))
            with cols[1]:
                st.write(money(o.get('totals',{}).get('grand_total',0)))
            with cols[2]:
                mins = max(1, int(o.get('eta_seconds',0))//60)
                st.write(f"ETA: {mins} min")
            with cols[3]:
                st.write(
                    ", ".join([f"{MENU_INDEX[it['menu_id']]['name']} x{it['qty']}" for it in o.get('items',[]) if it['menu_id'] in MENU_INDEX])
                )
            with cols[4]:
                new_status = st.selectbox("Estado", ["RECEIVED","IN_PROGRESS","READY","DELIVERED","CANCELLED"], index=["RECEIVED","IN_PROGRESS","READY","DELIVERED","CANCELLED"].index(o.get('status','RECEIVED')), key=f"sel_{oid}")
                if st.button("Guardar", key=f"save_{oid}"):
                    db.collection("orders").document(oid).update({"status": new_status, "updated_at": now_cdmx().isoformat()})
                    st.toast("✅ Estado actualizado")

        st.markdown("---")
        st.markdown("### Gestionar cliente (estrellas/helados)")
        tipo = st.radio("Tipo de recompensa", ["Churrería", "Helados"], horizontal=True)
        identificador_cliente = st.text_input("Correo o número del cliente", key="adm_ident")
        if st.button("Confirmar cliente", key="adm_confirm"):
            user_preview = get_user(identificador_cliente)
            if user_preview:
                ss.cliente_confirmado = identificador_cliente
                st.success(f"Cliente encontrado: {user_preview['email']}")
                show_user_summary(user_preview, is_admin_view=True)
            else:
                st.error("Cliente no encontrado.")

        if ss.cliente_confirmado:
            identificador_cliente = ss.cliente_confirmado
            if tipo == "Churrería":
                monto = st.number_input("Monto de compra ($MXN)", min_value=0, step=10)
                if st.button("Registrar compra", key="adm_compra"):
                    estrellas = int(monto / 10)
                    update_points(identificador_cliente, stars_add=estrellas)
                    user = get_user(identificador_cliente)
                    if user:
                        show_user_summary(user, is_admin_view=True)
            else:
                cantidad = st.number_input("Cantidad de helados", min_value=1, step=1)
                if st.button("Registrar consumo", key="adm_consumo"):
                    update_points(identificador_cliente, helados_add=int(cantidad))
                    user = get_user(identificador_cliente)
                    if user:
                        show_user_summary(user, is_admin_view=True)
                st.markdown("---")
                st.markdown("### Canjear helado directamente")
                if st.button("Canjear helado", key="adm_canj_helado"):
                    canjear_helado(identificador_cliente)
                    user = get_user(identificador_cliente)
                    if user:
                        show_user_summary(user, is_admin_view=True)

    else:
        st.error("Acceso denegado. Solo el admin puede ingresar.")
