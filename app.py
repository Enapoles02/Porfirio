# =============================================================================
# CHURRERÍA PORFIRIO — APP ÚNICA (LOGIN + MENÚ + PEDIDOS + REWARDS + ADMIN)
# PowerApps-style screens via st.session_state.screen
# Timezone: America/Mexico_City
# =============================================================================

import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import string
import bcrypt
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional

# ────────────────────────────────────────────────
# CONFIG + BRANDING
# ────────────────────────────────────────────────
st.set_page_config(page_title="Churrería Porfirio", layout="wide", page_icon="🥖")

CDMX_TZ = ZoneInfo("America/Mexico_City")
APP_TITLE = "Churrería Porfirio — Recompensas & Pedidos"
LOGO_URL = "https://scontent.fmex39-1.fna.fbcdn.net/v/t39.30808-6/434309611_122124689540226950_3619993036029337305_n.jpg"

st.markdown(
    """
<style>
    :root {
        --blue-dark: #0A2E5D; --blue-main: #0F4C81; --blue-mid: #3F78B8;
        --blue-soft: #D6E6F5; --border: #B6CCE6; --text-main: #1F2937;
        --text-muted: #6B7280; --ok: #16A34A; --warn: #F59E0B; --bad: #DC2626;
    }
    .stApp { background: #FFFFFF !important; }
    .card {
        background: linear-gradient(90deg, var(--blue-main) 0%, var(--blue-mid) 28%, var(--blue-soft) 58%, white 100%) !important;
        border-radius: 18px; padding: 20px; box-shadow: 0 12px 28px rgba(10,46,93,0.20);
        border: 1px solid var(--border); margin-bottom: 20px; color: var(--text-main);
    }
    h1, h2, h3 { color: var(--blue-dark) !important; font-weight: 800; }
    .stButton > button {
        background: var(--blue-main) !important; color: white !important;
        border-radius: 12px; font-weight: 700; border: none; padding: 10px 16px;
    }
    .stButton > button:hover { background: var(--blue-dark) !important; }
    .badge {
        display: inline-block; padding: 4px 10px; border-radius: 999px;
        background: var(--blue-soft); color: var(--blue-dark); font-size: 0.85rem;
        border: 1px solid var(--border);
    }
    .reward-slot {
        display: inline-block; width: 48px; height: 48px; line-height: 44px;
        text-align: center; border-radius: 50%; border: 3px solid var(--blue-dark);
        margin: 4px; font-size: 22px; background: white;
    }
    .slot-filled { background: var(--blue-dark); color: white; border-color: white; }
    .hr-soft { border: none; height: 1px; background: var(--border); margin: 16px 0; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div style="text-align:center; margin-bottom:24px;">
    <img src="{LOGO_URL}" style="max-height:100px; border-radius:16px; box-shadow:0 6px 20px rgba(0,0,0,0.2);">
    <h1 style="margin:16px 0 6px 0; color:var(--blue-dark);">{APP_TITLE}</h1>
    <p style="color:var(--text-muted);">La churrería más grande de México 🇲🇽</p>
</div>
""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────
# FIREBASE
# ────────────────────────────────────────────────
def _secrets_dict(x):
    """Streamlit secrets puede venir como AttrDict; lo convertimos a dict nativo."""
    try:
        # AttrDict soporta .to_dict()
        return x.to_dict()
    except Exception:
        try:
            return dict(x)
        except Exception:
            return x

if not firebase_admin._apps:
    fb_creds = _secrets_dict(st.secrets["firebase_credentials"])
    cred = credentials.Certificate(fb_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def now_cdmx() -> datetime:
    return datetime.now(CDMX_TZ)

def money(n: float) -> str:
    try:
        return f"${float(n):,.0f}"
    except Exception:
        return "$0"

def generate_cliente_id(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def log_action(action_type: str, usuario: str, detalle: str = ""):
    try:
        db.collection("logs").add(
            {
                "accion": action_type,
                "usuario": usuario,
                "detalle": detalle,
                "fecha": now_cdmx().isoformat(),
            }
        )
    except Exception:
        pass

# ────────────────────────────────────────────────
# MENÚ
# ────────────────────────────────────────────────
DEFAULT_MENU = [
    {"id": "churro_3", "name": "Churros tradicionales (3 pzas)", "category": "Churros", "price": 49, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "active": True},
    {"id": "churro_6", "name": "Churros tradicionales (6 pzas)", "category": "Churros", "price": 79, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "active": True},
    {"id": "churro_12", "name": "Churros tradicionales (12 pzas)", "category": "Churros", "price": 149, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "active": True},
    {"id": "churro_relleno_1", "name": "Churro relleno (1 pza)", "category": "Rellenos", "price": 35, "station": "fryer", "prep_time": 210, "batch_capacity": 3, "active": True},
    {"id": "churro_relleno_3", "name": "Churros rellenos (3 pzas)", "category": "Rellenos", "price": 99, "station": "fryer", "prep_time": 210, "batch_capacity": 3, "active": True},
    {"id": "mini_churros", "name": "Mini churros (15 pzas)", "category": "Mini Churros", "price": 79, "station": "fryer", "prep_time": 240, "batch_capacity": 15, "active": True},
    {"id": "bunuelos", "name": "Buñuelos (2 pzas)", "category": "Postres", "price": 49, "station": "stock", "prep_time": 0, "active": True},
    {"id": "carlota", "name": "Carlota (fresa / vainilla / chocolate)", "category": "Postres", "price": 75, "station": "stock", "prep_time": 0, "active": True},
    {"id": "adelitas", "name": "Adelitas (queso / española / jamón y queso)", "category": "Antojitos", "price": 139, "station": "stock", "prep_time": 0, "active": True},
    {"id": "salsa_extra", "name": "Salsa extra (cajeta / chocolate / lechera)", "category": "Extras", "price": 15, "station": "stock", "prep_time": 0, "active": True},
    {"id": "chilaquiles", "name": "Chilaquiles (verde o roja) — incluye bebida 354 ml", "category": "Desayunos", "price": 149, "station": "stock", "prep_time": 480, "active": True, "includes_drink_354": True},
    {"id": "enchiladas", "name": "Enchiladas (verde o roja) — incluye bebida 354 ml", "category": "Desayunos", "price": 149, "station": "stock", "prep_time": 540, "active": True, "includes_drink_354": True},
    {"id": "enfrijoladas", "name": "Enfrijoladas — incluye bebida 354 ml", "category": "Desayunos", "price": 149, "station": "stock", "prep_time": 540, "active": True, "includes_drink_354": True},
    {"id": "molletes", "name": "Molletes — incluye bebida 354 ml", "category": "Desayunos", "price": 139, "station": "stock", "prep_time": 420, "active": True, "includes_drink_354": True},
    {"id": "sincronizadas", "name": "Sincronizadas — incluye bebida 354 ml", "category": "Desayunos", "price": 129, "station": "stock", "prep_time": 360, "active": True, "includes_drink_354": True},
    {"id": "promo_viejos_tiempos", "name": "Recordando viejos tiempos (1L chocolate + 6 churros)", "category": "Promociones", "price": 229, "station": "mix", "prep_time": 0, "active": True, "schedule": "08:00-12:00"},
    {"id": "promo_dulce_dia", "name": "Empieza un dulce día (café de olla + churro relleno)", "category": "Promociones", "price": 69, "station": "mix", "prep_time": 0, "active": True, "schedule": "08:00-12:00"},
    {"id": "promo_granizados", "name": "Congelando momentos (2 granizados 354 ml)", "category": "Promociones", "price": 99, "station": "mix", "prep_time": 0, "active": True, "schedule": "13:00-17:00"},
    {"id": "espresso", "name": "Espresso", "category": "Café", "price": 39, "station": "barista", "prep_time": 180, "active": True},
    {"id": "americano", "name": "Americano", "category": "Café", "price": 45, "station": "barista", "prep_time": 180, "active": True},
    {"id": "cafe_olla", "name": "Café de olla", "category": "Café", "price": 55, "station": "barista", "prep_time": 240, "active": True},
    {"id": "latte", "name": "Café Latte", "category": "Café", "price": 65, "station": "barista", "prep_time": 240, "active": True},
    {"id": "mocha", "name": "Mocha", "category": "Café", "price": 75, "station": "barista", "prep_time": 270, "active": True},
    {"id": "capuccino", "name": "Capuccino", "category": "Café", "price": 75, "station": "barista", "prep_time": 270, "active": True},
    {"id": "chai_latte", "name": "Chai Latte", "category": "Café", "price": 75, "station": "barista", "prep_time": 300, "active": True},
    {"id": "te_354", "name": "Té (354 ml)", "category": "Café", "price": 40, "station": "barista", "prep_time": 180, "active": True},
    {"id": "chocolate_354", "name": "Chocolate caliente 354 ml", "category": "Chocolate", "price": 79, "station": "barista", "prep_time": 240, "active": True},
    {"id": "chocolate_473", "name": "Chocolate caliente 473 ml", "category": "Chocolate", "price": 89, "station": "barista", "prep_time": 300, "active": True},
    {"id": "frappe_354", "name": "Frappe / Granizado 354 ml", "category": "Bebidas frías", "price": 79, "station": "cold", "prep_time": 240, "active": True},
    {"id": "frappe_473", "name": "Frappe / Granizado 473 ml", "category": "Bebidas frías", "price": 89, "station": "cold", "prep_time": 270, "active": True},
    {"id": "malteada_354", "name": "Malteada 354 ml", "category": "Bebidas frías", "price": 99, "station": "cold", "prep_time": 240, "active": True},
    {"id": "malteada_473", "name": "Malteada 473 ml", "category": "Bebidas frías", "price": 115, "station": "cold", "prep_time": 270, "active": True},
    {"id": "refresco_355", "name": "Refresco 355 ml", "category": "Bebidas", "price": 45, "station": "stock", "prep_time": 0, "active": True},
    {"id": "agua_500", "name": "Agua natural 500 ml", "category": "Bebidas", "price": 30, "station": "stock", "prep_time": 0, "active": True},
]

MENU_INDEX = {m["id"]: m for m in DEFAULT_MENU if m.get("active", True)}

# ────────────────────────────────────────────────
# REWARDS
# ────────────────────────────────────────────────
def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    # 1) Por email (doc id)
    doc = db.collection("usuarios").document(identifier.lower()).get()
    if doc.exists:
        d = doc.to_dict() or {}
        d.setdefault("email", identifier.lower())
        return d

    # 2) Por cliente_id
    q = db.collection("usuarios").where("cliente_id", "==", identifier.upper()).limit(1).stream()
    for r in q:
        d = r.to_dict() or {}
        d.setdefault("email", r.id)
        return d

    return None

def save_user(email: str, data: Dict[str, Any]):
    db.collection("usuarios").document(email.lower()).set(data, merge=True)

def reward_apply(user: Dict[str, Any], stars_add: int = 0, helados_add: int = 0) -> Dict[str, Any]:
    user["estrellas"] = int(user.get("estrellas", 0)) + int(stars_add)
    user["helados"] = int(user.get("helados", 0)) + int(helados_add)

    # Green -> Gold al llegar a 200 estrellas
    if user.get("nivel") == "green" and user["estrellas"] >= 200:
        user["nivel"] = "gold"
        user["estrellas"] = 0
        log_action("recompensa", user.get("email", ""), "Ascenso a GOLD")

    # Gold: cada 100 estrellas = bebida (log)
    if user.get("nivel") == "gold":
        bebidas = user["estrellas"] // 100
        user["estrellas"] %= 100
        for _ in range(int(bebidas)):
            log_action("recompensa", user.get("email", ""), "Bebida GOLD")

    user["canjear_helado"] = int(user.get("helados", 0)) >= 6
    return user

def update_points(identifier: str, stars_add: int = 0, helados_add: int = 0, detalle: str = ""):
    user = get_user(identifier)
    if not user:
        return
    user = reward_apply(user, stars_add=stars_add, helados_add=helados_add)
    save_user(user["email"], user)
    if detalle:
        log_action("consumo", user["email"], detalle)

def canjear_helado(identifier: str):
    user = get_user(identifier)
    if not user or int(user.get("helados", 0)) < 6:
        st.warning("No tienes suficientes helados")
        return
    user["helados"] = int(user.get("helados", 0)) - 6
    user["canjear_helado"] = False
    save_user(user["email"], user)
    st.success("Helado canjeado")
    log_action("canje", user["email"], "Helado (6)")

# ────────────────────────────────────────────────
# ETA / COLAS
# ────────────────────────────────────────────────
FRYER_BASKETS = 2  # canastas simultáneas
def calc_station_work_seconds(items: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    barista_total = fryer_total = cold_total = 0
    for it in items:
        item = MENU_INDEX.get(it.get("menu_id"))
        if not item:
            continue
        qty = int(it.get("qty", 1))
        station = item.get("station", "barista")
        prep = int(item.get("prep_time", 180))

        if station == "barista":
            barista_total += prep * qty
        elif station == "cold":
            cold_total += prep * qty
        elif station == "fryer":
            cap = int(item.get("batch_capacity", 6))
            batches = -(-qty // cap)           # ceil(qty/cap)
            rounds = -(-batches // FRYER_BASKETS)
            fryer_total += rounds * prep
        else:
            barista_total += prep * qty

    return barista_total, fryer_total, cold_total

def fetch_queue_load_seconds() -> Tuple[int, int, int]:
    barista_q = fryer_q = cold_q = 0
    q = db.collection("orders").where("status", "in", ["RECEIVED", "IN_PROGRESS"]).stream()
    for d in q:
        o = d.to_dict() or {}
        b, f, c = calc_station_work_seconds(o.get("items", []))
        barista_q += b
        fryer_q += f
        cold_q += c
    return barista_q, fryer_q, cold_q

def estimate_eta_seconds(new_items: List[Dict[str, Any]]) -> int:
    q_barista, q_fryer, q_cold = fetch_queue_load_seconds()
    b_new, f_new, c_new = calc_station_work_seconds(new_items)
    return int(max(q_barista + b_new, q_fryer + f_new, q_cold + c_new))

# ────────────────────────────────────────────────
# PERSIST ORDER
# ────────────────────────────────────────────────
def persist_order(order_data: Dict[str, Any]) -> str:
    """Guarda pedido en Firestore y regresa order_id."""
    oid = order_data.get("id") or uuid.uuid4().hex[:10].upper()
    order_data["id"] = oid
    order_data.setdefault("created_at", now_cdmx().isoformat())
    order_data.setdefault("updated_at", now_cdmx().isoformat())
    db.collection("orders").document(oid).set(order_data, merge=True)
    log_action("order_create", order_data.get("user_email", ""), f"Pedido {oid} ({order_data.get('type','')})")
    return oid

# ────────────────────────────────────────────────
# UI REUSABLES: MENU + CART
# ────────────────────────────────────────────────
def render_menu_store(cart_key: str):
    st.markdown("<div class='card'><h3>🧾 Menú de la Casa</h3><hr class='hr-soft'>", unsafe_allow_html=True)

    cats = ["Todas"] + sorted(set(m["category"] for m in DEFAULT_MENU if m.get("active")))
    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        selected_cat = st.selectbox("Categoría", cats, key=f"cat_{cart_key}")
    with col_filter2:
        search_term = st.text_input("Buscar producto", value="", key=f"search_{cart_key}").strip().lower()

    filtered_menu = [m for m in DEFAULT_MENU if m.get("active")]
    if selected_cat != "Todas":
        filtered_menu = [m for m in filtered_menu if m["category"] == selected_cat]
    if search_term:
        filtered_menu = [m for m in filtered_menu if search_term in m["name"].lower()]

    if not filtered_menu:
        st.info("No se encontraron productos")
    else:
        cols = st.columns(3)
        for idx, item in enumerate(filtered_menu):
            with cols[idx % 3]:
                st.markdown(
                    f"""
                    <div class='card' style='height:240px;'>
                        <h4 style="margin-bottom:6px;">{item['name']}</h4>
                        <small>{item['category']} • <b>{money(item['price'])}</b></small>
                        <hr class='hr-soft'>
                    """,
                    unsafe_allow_html=True,
                )

                qty = st.number_input(
                    "Cantidad", min_value=1, value=1, step=1, key=f"qty_{cart_key}_{item['id']}"
                )
                note = st.text_input(
                    "Nota (salsas, sin algo...)", value="", key=f"note_{cart_key}_{item['id']}"
                )

                if st.button("➕ Agregar", key=f"add_{cart_key}_{item['id']}"):
                    st.session_state[cart_key].append(
                        {
                            "menu_id": item["id"],
                            "qty": int(qty),
                            "note": note.strip(),
                            "price": float(item["price"]),
                        }
                    )
                    st.toast(f"Agregado: {item['name']} × {qty}")
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_cart(cart_key: str) -> Tuple[float, List[Dict[str, Any]]]:
    cart = st.session_state.get(cart_key, [])
    st.markdown("<div class='card'><h3>🛒 Tu Pedido</h3><hr class='hr-soft'>", unsafe_allow_html=True)

    if not cart:
        st.info("Tu carrito está vacío")
        st.markdown("</div>", unsafe_allow_html=True)
        return 0.0, []

    subtotal = 0.0
    new_cart = []

    for i, item in enumerate(cart):
        menu_item = MENU_INDEX.get(item.get("menu_id"))
        if not menu_item:
            continue

        qty0 = int(item.get("qty", 1))
        price0 = float(item.get("price", menu_item.get("price", 0)))
        line_total = qty0 * price0
        subtotal += line_total

        col1, col2, col3, col4 = st.columns([5, 2, 2, 1])
        with col1:
            st.write(f"**{menu_item['name']}**")
            if item.get("note"):
                st.caption(item["note"])
        with col2:
            new_qty = st.number_input("Cant.", min_value=1, value=qty0, step=1, key=f"cart_qty_{cart_key}_{i}")
        with col3:
            st.write(money(line_total))
        with col4:
            remove = st.button("🗑", key=f"rm_{cart_key}_{i}")

        if remove:
            continue

        if int(new_qty) > 0:
            new_item = item.copy()
            new_item["qty"] = int(new_qty)
            new_item["price"] = float(price0)
            new_cart.append(new_item)

    st.session_state[cart_key] = new_cart
    st.markdown(f"<h4 style='text-align:right;'>Total: {money(subtotal)}</h4>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return float(subtotal), new_cart

# ────────────────────────────────────────────────
# GLOBAL STATE
# ────────────────────────────────────────────────
if "screen" not in st.session_state:
    st.session_state.screen = "LOGIN"

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.username = None
    st.session_state.cliente_id = None

if "cart_mesa" not in st.session_state:
    st.session_state.cart_mesa = []
if "cart_pickup" not in st.session_state:
    st.session_state.cart_pickup = []
if "mesa_num" not in st.session_state:
    st.session_state.mesa_num = ""

# ────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────
if st.session_state.auth:
    with st.sidebar:
        st.title(f"🥖 {st.session_state.username}")
        st.caption(f"ID Cliente: {st.session_state.cliente_id or '—'}")
        st.markdown("---")

        st.button("🏠 Inicio", on_click=lambda: setattr(st.session_state, "screen", "HOME"))
        st.button("🍽️ Pedir en Mesa", on_click=lambda: setattr(st.session_state, "screen", "MESA"))
        st.button("🚗 Pick Up", on_click=lambda: setattr(st.session_state, "screen", "PICKUP"))
        st.button("🎁 Rewards", on_click=lambda: setattr(st.session_state, "screen", "REWARDS"))
        st.button("🧾 Mis Pedidos", on_click=lambda: setattr(st.session_state, "screen", "MIS_PEDIDOS"))
        st.button("👤 Mi Perfil", on_click=lambda: setattr(st.session_state, "screen", "PERFIL"))

        st.markdown("---")
        with st.expander("🛡️ Admin"):
            pin = st.text_input("PIN Admin", type="password", value="", key="admin_pin_sidebar")
            admin_pin = st.secrets.get("admin_pin", "2424")
            if pin == admin_pin:
                st.success("Modo Admin ON")
                st.button("Ir a Admin", on_click=lambda: setattr(st.session_state, "screen", "ADMIN"))

        if st.button("🚪 Cerrar Sesión", type="primary"):
            st.session_state.clear()
            st.rerun()

# ────────────────────────────────────────────────
# ROUTER DE PANTALLAS
# ────────────────────────────────────────────────
if st.session_state.screen == "LOGIN":
    st.subheader("Iniciar Sesión")

    with st.form("login"):
        ident = st.text_input("Correo o ID Cliente", value="")
        pw = st.text_input("Contraseña", value="", type="password")
        submit = st.form_submit_button("Entrar", type="primary")

    if submit:
        user = get_user(ident.strip())
        if user and verify_password(pw, user.get("password_hash", "")):
            st.session_state.auth = True
            st.session_state.username = user["email"]
            st.session_state.cliente_id = user.get("cliente_id")
            st.session_state.screen = "HOME"
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

    if st.button("¿Nuevo aquí? Regístrate"):
        st.session_state.screen = "REGISTRO"
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("¿Nuevo aquí? Regístrate"):
            st.session_state.screen = "REGISTRO"
            st.rerun()
    with c2:
        if st.button("Olvidé mi contraseña"):
            st.session_state.screen = "RESET_PASSWORD"
            st.rerun()

elif st.session_state.screen == "REGISTRO":
    st.subheader("Crear Cuenta")

    with st.form("registro"):
        col1, col2 = st.columns(2)
        email = col1.text_input("Correo electrónico", value="")
        full_name = col2.text_input("Nombre completo", value="")

        col3, col4 = st.columns(2)
        phone = col3.text_input("Teléfono (WhatsApp)", value="")
        pw = col4.text_input("Contraseña", value="", type="password")

        submit = st.form_submit_button("Crear", type="primary")

    if submit:
        if len(pw) < 6:
            st.error("Contraseña corta (mínimo 6)")
        else:
            email_clean = email.lower().strip()
            if not email_clean or "@" not in email_clean:
                st.error("Ingresa un correo válido")
            elif get_user(email_clean):
                st.error("Correo ya registrado")
            else:
                cid = generate_cliente_id()
                data = {
                    "email": email_clean,
                    "password_hash": hash_password(pw),
                    "full_name": full_name.strip(),
                    "phone": phone.strip(),
                    "cliente_id": cid,
                    "estrellas": 0,
                    "helados": 0,
                    "nivel": "green",
                    "created_at": now_cdmx().isoformat(),
                }
                save_user(email_clean, data)
                st.success(f"Cuenta creada ✅  ID cliente: {cid}")
                st.session_state.screen = "LOGIN"
                st.rerun()

    if st.button("Volver al login"):
        st.session_state.screen = "LOGIN"
        st.rerun()
elif st.session_state.screen == "RESET_PASSWORD":
    st.subheader("🔑 Restablecer contraseña")

    st.caption("Para seguridad, confirma tu correo y tu teléfono (WhatsApp) registrado. Luego defines una nueva contraseña.")

    email = st.text_input("Correo", value="", key="rp_email").strip().lower()
    phone = st.text_input("Teléfono (WhatsApp)", value="", key="rp_phone").strip()

    new_pw = st.text_input("Nueva contraseña", value="", type="password", key="rp_new_pw")
    new_pw2 = st.text_input("Confirmar nueva contraseña", value="", type="password", key="rp_new_pw2")

    colA, colB = st.columns([1,1])
    with colA:
        if st.button("✅ Restablecer", type="primary", use_container_width=True):
            if not email or "@" not in email:
                st.error("Ingresa un correo válido")
            elif not phone or len(phone) < 8:
                st.error("Ingresa tu teléfono")
            elif len(new_pw) < 6:
                st.error("La contraseña debe tener mínimo 6 caracteres")
            elif new_pw != new_pw2:
                st.error("Las contraseñas no coinciden")
            else:
                user = get_user(email)
                if not user:
                    st.error("No existe una cuenta con ese correo")
                else:
                    phone_db = (user.get("phone") or "").strip()

                    # Comparación “tolerante”: ignora espacios y +52
                    def norm_phone(x: str) -> str:
                        x = (x or "").strip().replace(" ", "").replace("-", "")
                        if x.startswith("+52"):
                            x = x[3:]
                        return x

                    if norm_phone(phone) != norm_phone(phone_db):
                        st.error("El teléfono no coincide con el registrado")
                        log_action("pwd_reset_failed", email, "Teléfono no coincide")
                    else:
                        save_user(email, {"password_hash": hash_password(new_pw)})
                        log_action("pwd_reset_done", email, "Reset por correo+tel")
                        st.success("Contraseña actualizada ✅ Ya puedes iniciar sesión.")
                        st.session_state.screen = "LOGIN"
                        st.rerun()

    with colB:
        if st.button("← Volver al login", use_container_width=True):
            st.session_state.screen = "LOGIN"
            st.rerun()


elif st.session_state.screen == "HOME":
    st.title("¡Bienvenid@ a Churrería Porfirio!")
    st.subheader("Elige cómo ordenar")

    c1, c2 = st.columns(2)
    c1.button("🍽️ Pedir en Mesa", type="primary", use_container_width=True, on_click=lambda: setattr(st.session_state, "screen", "MESA"))
    c2.button("🚗 Pick Up", type="primary", use_container_width=True, on_click=lambda: setattr(st.session_state, "screen", "PICKUP"))

    st.markdown("---")
    hour = now_cdmx().hour
    if 8 <= hour < 12:
        st.info("☕ Promo matutina activa: café + churro relleno con desayunos")
    elif 13 <= hour < 17:
        st.success("🍦 Promo tarde activa: 2 granizados por $99")

elif st.session_state.screen == "MESA":
    st.subheader("🍽️ Pedir en Mesa")

    if st.button("← Volver al Inicio", key="back_mesa"):
        st.session_state.screen = "HOME"
        st.rerun()

    st.session_state.mesa_num = st.text_input(
        "Número de mesa / zona", value=st.session_state.mesa_num.strip()
    )

    if not st.session_state.mesa_num.strip():
        st.warning("Por favor ingresa el número de mesa para continuar")
    else:
        render_menu_store("cart_mesa")
        total, cart_items = render_cart("cart_mesa")

        if cart_items:
            eta_sec = estimate_eta_seconds(cart_items)
            eta_min = max(5, int(eta_sec // 60))
            st.info(f"⏱️ Tiempo estimado aproximado: **{eta_min} minutos** (según carga actual)")

            promo_msg = ""
            hour = now_cdmx().hour
            if 8 <= hour < 12:
                promo_msg = "☕ Recuerda: con chilaquiles o desayunos, café de olla por nuestra cuenta"
            elif 13 <= hour < 17:
                promo_msg = "🍦 Promo tarde activa hoy"
            if promo_msg:
                st.success(promo_msg)

            if st.button("Confirmar y Enviar Pedido a Mesa", type="primary", use_container_width=True):
                order_data = {
                    "type": "MESA",
                    "mesa": st.session_state.mesa_num.strip(),
                    "items": cart_items,
                    "total": float(total),
                    "eta_seconds": int(eta_sec),
                    "status": "RECEIVED",
                    "user_email": st.session_state.username,
                    "cliente_id": st.session_state.cliente_id,
                    "created_at": now_cdmx().isoformat(),
                    "updated_at": now_cdmx().isoformat(),
                }
                oid = persist_order(order_data)

                stars = int(float(total) // 10)
                if stars > 0:
                    update_points(
                        st.session_state.username,
                        stars_add=stars,
                        detalle=f"Pedido Mesa #{oid} → +{stars} estrellas",
                    )

                st.success(f"¡Pedido #{oid} enviado correctamente! ETA ~{eta_min} min")
                st.balloons()
                st.session_state.cart_mesa = []
                st.rerun()

elif st.session_state.screen == "PICKUP":
    st.subheader("🚗 Pedir para Pick Up")

    if st.button("← Volver al Inicio", key="back_pickup"):
        st.session_state.screen = "HOME"
        st.rerun()

    render_menu_store("cart_pickup")
    total, cart_items = render_cart("cart_pickup")

    if cart_items:
        eta_sec = estimate_eta_seconds(cart_items)
        eta_min = max(5, int(eta_sec // 60))
        st.info(f"⏱️ Tiempo estimado para recoger: **{eta_min} minutos**")

        hour = now_cdmx().hour
        if 8 <= hour < 12:
            st.success("☕ Promo matutina activa hoy")
        elif 13 <= hour < 17:
            st.success("🍦 Promo tarde activa hoy")

        payment_method = st.radio("Forma de pago", ["Transferencia / Efectivo", "Mercado Pago"], index=0)

        if st.button("Confirmar y Generar Pedido Pick Up", type="primary", use_container_width=True):
            order_data = {
                "type": "PICKUP",
                "items": cart_items,
                "total": float(total),
                "eta_seconds": int(eta_sec),
                "status": "RECEIVED",
                "payment_method": payment_method,
                "user_email": st.session_state.username,
                "cliente_id": st.session_state.cliente_id,
                "created_at": now_cdmx().isoformat(),
                "updated_at": now_cdmx().isoformat(),
            }
            oid = persist_order(order_data)

            stars = int(float(total) // 10)
            if stars > 0:
                update_points(
                    st.session_state.username,
                    stars_add=stars,
                    detalle=f"Pedido PickUp #{oid} → +{stars} estrellas",
                )

            st.success(f"¡Pedido #{oid} confirmado! Recógelo en ~{eta_min} minutos")
            st.balloons()
            st.session_state.cart_pickup = []
            st.rerun()

elif st.session_state.screen == "REWARDS":
    st.subheader("🎖️ Mis Recompensas")
    user = get_user(st.session_state.username)

    if user:
        estrellas = int(user.get("estrellas", 0))
        helados = int(user.get("helados", 0))
        nivel = user.get("nivel", "green")

        c1, c2, c3 = st.columns(3)
        c1.metric("Estrellas", estrellas)
        c2.metric("Helados comprados", f"{helados} / 6")
        c3.metric("Nivel", "GOLD" if nivel == "gold" else "GREEN")

        if nivel == "green":
            st.progress(min(1.0, estrellas / 200))
            st.caption(f"Faltan {max(0, 200 - estrellas)} para Gold")
        else:
            st.progress(min(1.0, estrellas / 100))
            st.caption(f"Faltan {max(0, 100 - estrellas)} para bebida gratis (log)")

        if helados >= 6:
            st.success("Puedes canjear un helado gratis 🍦")
            if st.button("Canjear ahora"):
                canjear_helado(st.session_state.username)
                st.rerun()
    else:
        st.warning("No se pudo cargar tu perfil")

elif st.session_state.screen == "MIS_PEDIDOS":
    st.subheader("🧾 Mis Pedidos")

    q = (
        db.collection("orders")
        .where("user_email", "==", st.session_state.username)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
        .stream()
    )
    data = []
    for d in q:
        o = d.to_dict() or {}
        o["id"] = d.id
        data.append(o)

    if data:
        df = pd.DataFrame(data)
        cols = [c for c in ["id", "type", "status", "total", "mesa", "payment_method", "created_at"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.info("No tienes pedidos aún")

elif st.session_state.screen == "PERFIL":
    st.subheader("👤 Mi Perfil")
    user = get_user(st.session_state.username)
    if user:
        st.write("Nombre:", user.get("full_name", "—"))
        st.write("Teléfono:", user.get("phone", "—"))
        st.write("Correo:", user.get("email", "—"))
        st.write("ID Cliente:", user.get("cliente_id", "—"))
    else:
        st.warning("No se pudo cargar tu perfil")

elif st.session_state.screen == "ADMIN":
    st.subheader("🛡️ Panel de Administración")

    if st.button("← Volver al Inicio", key="back_admin"):
        st.session_state.screen = "HOME"
        st.rerun()

    admin_pin = st.secrets.get("admin_pin", "2424")
    pin = st.text_input("PIN de Acceso Admin", type="password", value="", key="admin_pin_input")

    if pin != admin_pin:
        st.warning("Ingresa el PIN para acceder")
    else:
        st.success("Acceso autorizado — Modo Admin activado")
        log_action("admin_login", st.session_state.username, "Acceso panel admin")

        tab_admin = st.radio(
            "Sección Admin",
            [
                "Cola de Pedidos",
                "Gestión Recompensas",
                "Rifa Boletos",
                "Arqueo de Caja",
                "Consolidación Utilidad",
                "Logs Recientes",
            ],
        )

        if tab_admin == "Cola de Pedidos":
            st.subheader("🧑‍🍳 Cola de Pedidos")
            status_filter = st.multiselect(
                "Filtrar por estado",
                ["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"],
                default=["RECEIVED", "IN_PROGRESS"],
            )

            q = (
                db.collection("orders")
                .where("status", "in", status_filter)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(80)
                .stream()
            )

            data = []
            for doc in q:
                o = doc.to_dict() or {}
                o["id"] = doc.id
                data.append(o)

            if not data:
                st.info("No hay pedidos con los filtros seleccionados")
            else:
                df = pd.DataFrame(data)
                cols = [c for c in ["id", "type", "status", "total", "mesa", "user_email", "created_at"] if c in df.columns]
                st.dataframe(df[cols], use_container_width=True)

                selected_oid = st.selectbox("Seleccionar pedido para actualizar", df["id"].tolist(), index=0)
                if selected_oid:
                    doc_ref = db.collection("orders").document(selected_oid)
                    snap = doc_ref.get()
                    if snap.exists:
                        order_data = snap.to_dict() or {}
                        order_data["id"] = selected_oid
                        st.write("Detalles:")
                        st.json(order_data)

                        status_list = ["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"]
                        curr = order_data.get("status", "RECEIVED")
                        idx = status_list.index(curr) if curr in status_list else 0
                        new_status = st.selectbox("Nuevo estado", status_list, index=idx)

                        if st.button("Actualizar Estado"):
                            doc_ref.update(
                                {
                                    "status": new_status,
                                    "updated_at": now_cdmx().isoformat(),
                                    "updated_by": st.session_state.username,
                                }
                            )
                            log_action("order_update", st.session_state.username, f"Pedido {selected_oid} → {new_status}")
                            st.success("Estado actualizado")
                            st.rerun()
                    else:
                        st.error("Pedido no encontrado")

        elif tab_admin == "Gestión Recompensas":
            st.subheader("🎟️ Gestionar Recompensas Manual")
            ident = st.text_input("Correo o ID Cliente", value="")
            user = None
            if st.button("Buscar Cliente"):
                user = get_user(ident.strip())
                st.session_state["_admin_user_found"] = user  # cache simple

            user = st.session_state.get("_admin_user_found")
            if user:
                st.success(f"Encontrado: {user.get('email')} (ID: {user.get('cliente_id')})")
                st.write("Estrellas actuales:", int(user.get("estrellas", 0)))
                st.write("Helados actuales:", int(user.get("helados", 0)))
                st.write("Nivel:", user.get("nivel", "green"))

                col_stars, col_helados = st.columns(2)
                add_stars = col_stars.number_input("Sumar estrellas", min_value=0, value=0, step=1)
                add_helados = col_helados.number_input("Sumar helados", min_value=0, value=0, step=1)

                if st.button("Aplicar Recompensas"):
                    update_points(user["email"], stars_add=int(add_stars), helados_add=int(add_helados), detalle="Admin manual")
                    st.success("Recompensas aplicadas")
                    st.session_state["_admin_user_found"] = get_user(user["email"])
                    st.rerun()
            else:
                st.info("Busca un cliente para editar recompensas")

        elif tab_admin == "Rifa Boletos":
            st.subheader("🎟️ Sistema de Rifa")
            raffle_id = st.secrets.get("raffle_id", "RIFA_2026")
            st.caption(f"Rifa activa: {raffle_id}")

            customer_ident = st.text_input("Correo o ID Cliente", value="")
            ticket_num = st.text_input("Número de ticket / folio compra", value="")
            boleto = st.number_input("Número de boleto a asignar", min_value=1, step=1, value=1)

            if st.button("Asignar Boleto"):
                user = get_user(customer_ident.strip())
                if not user:
                    st.error("Cliente no encontrado")
                elif not ticket_num.strip():
                    st.error("Ingresa número de ticket")
                else:
                    doc_id = f"{raffle_id}_{int(boleto)}"
                    ref = db.collection("raffle_tickets").document(doc_id)
                    if ref.get().exists:
                        st.error("Ese boleto ya está asignado")
                    else:
                        ref.set(
                            {
                                "raffle_id": raffle_id,
                                "boleto": int(boleto),
                                "cliente_id": user["cliente_id"],
                                "email": user["email"],
                                "ticket_num": ticket_num.strip(),
                                "assigned_by": st.session_state.username,
                                "assigned_at": now_cdmx().isoformat(),
                            }
                        )
                        log_action("rifa_asign", st.session_state.username, f"Boleto {int(boleto)} a {user['cliente_id']}")
                        st.success(f"Boleto {int(boleto)} asignado correctamente")

        elif tab_admin == "Arqueo de Caja":
            st.subheader("💵 Arqueo de Caja")
            today = now_cdmx().date().isoformat()
            shift = st.selectbox("Turno", ["Matutino", "Vespertino"], index=0)

            col1, col2, col3 = st.columns(3)
            b20 = col1.number_input("$20", min_value=0, value=0, step=1)
            b50 = col1.number_input("$50", min_value=0, value=0, step=1)
            b100 = col2.number_input("$100", min_value=0, value=0, step=1)
            b200 = col2.number_input("$200", min_value=0, value=0, step=1)
            b500 = col3.number_input("$500", min_value=0, value=0, step=1)
            tarjetas = col3.number_input("Tarjetas / Terminal", min_value=0.0, value=0.0, step=10.0)

            cash_total = b20 * 20 + b50 * 50 + b100 * 100 + b200 * 200 + b500 * 500
            grand_total = float(cash_total) + float(tarjetas)

            st.metric("Efectivo", money(cash_total))
            st.metric("Total Día", money(grand_total))

            if st.button("Guardar Arqueo"):
                doc_id = f"{today}_{'MAT' if shift == 'Matutino' else 'VES'}"
                db.collection("cash_closings").document(doc_id).set(
                    {
                        "date": today,
                        "shift": shift,
                        "b20": int(b20),
                        "b50": int(b50),
                        "b100": int(b100),
                        "b200": int(b200),
                        "b500": int(b500),
                        "tarjetas": float(tarjetas),
                        "cash_total": float(cash_total),
                        "grand_total": float(grand_total),
                        "created_by": st.session_state.username,
                        "created_at": now_cdmx().isoformat(),
                    }
                )
                log_action("arqueo", st.session_state.username, f"{doc_id} - {money(grand_total)}")
                st.success("Arqueo guardado")

        elif tab_admin == "Consolidación Utilidad":
            st.subheader("📈 Consolidación Utilidad")
            start_date = st.date_input("Inicio", value=now_cdmx().date())
            end_date = st.date_input("Fin", value=now_cdmx().date())

            if st.button("Calcular"):
                start_iso = start_date.isoformat()
                end_iso = end_date.isoformat()

                closings = (
                    db.collection("cash_closings")
                    .where("date", ">=", start_iso)
                    .where("date", "<=", end_iso)
                    .stream()
                )

                total_cash = 0.0
                total_cards = 0.0
                for c in closings:
                    d = c.to_dict() or {}
                    total_cash += float(d.get("cash_total", 0) or 0)
                    total_cards += float(d.get("tarjetas", 0) or 0)

                total_sales = total_cash + total_cards

                fixed_costs = {
                    "Nomina": 10100,
                    "Renta": 8750,
                    "Luz": 937.5,
                    "Agua": 300,
                    "Regalias": 3770,
                }
                variable_costs = {
                    "SAMS/SUPER": 4086.92,
                    "Mercado": 320,
                    "Molino": 100,
                    "Gas": 712,
                }

                total_costs = float(sum(fixed_costs.values()) + sum(variable_costs.values()))
                profit = float(total_sales - total_costs)
                cash_to_return = float(max(0.0, total_cash - profit)) if profit > 0 else float(total_cash)

                st.metric("Ventas Totales", money(total_sales))
                st.metric("Costos Totales", money(total_costs))
                st.metric("Utilidad", money(profit))
                st.metric("Cash a regresar", money(cash_to_return))

                if st.button("Guardar Consolidación"):
                    doc_id = f"{start_iso}_{end_iso}"
                    db.collection("profit_consolidations").document(doc_id).set(
                        {
                            "period_start": start_iso,
                            "period_end": end_iso,
                            "sales_total": float(total_sales),
                            "total_costs": float(total_costs),
                            "profit": float(profit),
                            "cash_to_return": float(cash_to_return),
                            "created_by": st.session_state.username,
                            "created_at": now_cdmx().isoformat(),
                        }
                    )
                    st.success("Consolidación guardada")

        elif tab_admin == "Logs Recientes":
            st.subheader("📜 Logs Recientes")
            logs = db.collection("logs").order_by("fecha", direction=firestore.Query.DESCENDING).limit(30).stream()
            data = [l.to_dict() for l in logs]
            if data:
                df = pd.DataFrame(data)
                cols = [c for c in ["accion", "usuario", "detalle", "fecha"] if c in df.columns]
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.info("No hay logs recientes")

else:
    # fallback seguro
    st.session_state.screen = "LOGIN"
    st.rerun()

st.markdown("---")
st.caption(f"Churrería Porfirio © {now_cdmx().year} • Versión Fusionada Completa")
