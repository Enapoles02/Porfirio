# =============================================================================
# CHURRERÍA PORFIRIO - PARTE 1/2 (Base + Auth + Helpers + Menú + Rewards + Admin básico)
# ~1900 líneas - Estructura Drop24 + funcionalidades originales
# Para completar con Parte 2: pantallas de pedido + carrito + ETA + guardar
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
import hashlib
import secrets
from typing import Dict, Any, List, Tuple, Optional

# ────────────────────────────────────────────────
# CONFIGURACIÓN + BRANDING
# ────────────────────────────────────────────────
st.set_page_config(page_title="Churrería Porfirio", layout="wide", page_icon="🥖")

CDMX_TZ = ZoneInfo("America/Mexico_City")
APP_TITLE = "Churrería Porfirio — Recompensas & Pedidos"
LOGO_URL = "https://scontent.fmex39-1.fna.fbcdn.net/v/t39.30808-6/434309611_122124689540226950_3619993036029337305_n.jpg"

st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:center; margin-bottom:24px;">
    <img src="{LOGO_URL}" style="max-height:100px; border-radius:16px; box-shadow:0 6px 20px rgba(0,0,0,0.2);">
    <h1 style="margin:16px 0 6px 0; color:var(--blue-dark);">{APP_TITLE}</h1>
    <p style="color:var(--text-muted);">La churrería más grande de México 🇲🇽</p>
</div>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# FIREBASE
# ────────────────────────────────────────────────
if not firebase_admin._apps:
    creds = credentials.Certificate(dict(st.secrets["firebase_credentials"]))
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
    except:
        return "$0"

def generate_cliente_id(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except:
        return False

def log_action(action_type: str, usuario: str, detalle: str = ""):
    try:
        db.collection("logs").add({
            "accion": action_type,
            "usuario": usuario,
            "detalle": detalle,
            "fecha": now_cdmx().isoformat()
        })
    except:
        pass

# ────────────────────────────────────────────────
# MENÚ COMPLETO
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

FRYER_BASKETS = 2

# ────────────────────────────────────────────────
# REWARDS HELPERS
# ────────────────────────────────────────────────
def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    doc = db.collection("usuarios").document(identifier.lower()).get()
    if doc.exists:
        d = doc.to_dict() or {}
        d.setdefault("email", identifier.lower())
        return d
    q = db.collection("usuarios").where("cliente_id", "==", identifier.upper()).limit(1).stream()
    for r in q:
        d = r.to_dict() or {}
        d.setdefault("email", r.id)
        return d
    return None

def save_user(email: str, data: Dict[str, Any]):
    db.collection("usuarios").document(email.lower()).set(data, merge=True)

def reward_apply(user: Dict[str, Any], stars_add: int = 0, helados_add: int = 0) -> Dict[str, Any]:
    user["estrellas"] = int(user.get("estrellas", 0)) + stars_add
    user["helados"] = int(user.get("helados", 0)) + helados_add
    if user.get("nivel") == "green" and user["estrellas"] >= 200:
        user["nivel"] = "gold"
        user["estrellas"] = 0
        log_action("recompensa", user.get("email", ""), "Ascenso a GOLD")
    if user.get("nivel") == "gold":
        bebidas = user["estrellas"] // 100
        user["estrellas"] %= 100
        for _ in range(bebidas):
            log_action("recompensa", user.get("email", ""), "Bebida GOLD")
    user["canjear_helado"] = user["helados"] >= 6
    return user

def update_points(identifier: str, stars_add: int = 0, helados_add: int = 0, detalle: str = ""):
    user = get_user(identifier)
    if not user:
        return
    user = reward_apply(user, stars_add, helados_add)
    save_user(user["email"], user)
    if detalle:
        log_action("consumo", user["email"], detalle)

def canjear_helado(identifier: str):
    user = get_user(identifier)
    if not user or user["helados"] < 6:
        st.warning("No tienes suficientes helados")
        return
    user["helados"] -= 6
    user["canjear_helado"] = False
    save_user(user["email"], user)
    st.success("Helado canjeado")
    log_action("canje", user["email"], "Helado (6)")

# ────────────────────────────────────────────────
# ETA / COLAS
# ────────────────────────────────────────────────
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
            batches = -(-qty // cap)
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
            pin = st.text_input("PIN Admin", type="password", key="admin_pin")
            if pin == "2424":
                st.success("Modo Admin ON")
                st.button("Ir a Admin", on_click=lambda: setattr(st.session_state, "screen", "ADMIN"))
        if st.button("🚪 Cerrar Sesión", type="primary"):
            st.session_state.clear()
            st.rerun()

# ────────────────────────────────────────────────
# LOGIN
# ────────────────────────────────────────────────
if st.session_state.screen == "LOGIN":
    st.subheader("Iniciar Sesión")
    with st.form("login"):
        ident = st.text_input("Correo o ID Cliente")
        pw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            user = get_user(ident)
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

# ────────────────────────────────────────────────
# REGISTRO
# ────────────────────────────────────────────────
elif st.session_state.screen == "REGISTRO":
    st.subheader("Crear Cuenta")
    with st.form("registro"):
        col1, col2 = st.columns(2)
        email = col1.text_input("Correo electrónico")
        full_name = col2.text_input("Nombre completo")
        col3, col4 = st.columns(2)
        phone = col3.text_input("Teléfono (WhatsApp)")
        pw = col4.text_input("Contraseña", type="password")
        if st.form_submit_button("Crear", type="primary"):
            if len(pw) < 6:
                st.error("Contraseña corta")
            else:
                email_clean = email.lower().strip()
                if get_user(email_clean):
                    st.error("Correo ya registrado")
                else:
                    cid = generate_cliente_id()
                    data = {
                        "email": email_clean,
                        "password_hash": hash_password(pw),
                        "full_name": full_name,
                        "phone": phone,
                        "cliente_id": cid,
                        "estrellas": 0,
                        "helados": 0,
                        "nivel": "green",
                        "created_at": now_cdmx().isoformat()
                    }
                    save_user(email_clean, data)
                    st.success(f"Cuenta creada! ID cliente: {cid}")
                    st.session_state.screen = "LOGIN"
                    st.rerun()
    if st.button("Volver al login"):
        st.session_state.screen = "LOGIN"
        st.rerun()

# ────────────────────────────────────────────────
# HOME
# ────────────────────────────────────────────────
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

# ────────────────────────────────────────────────
# REWARDS
# ────────────────────────────────────────────────
elif st.session_state.screen == "REWARDS":
    st.subheader("🎖️ Mis Recompensas")
    user = get_user(st.session_state.username)
    if user:
        estrellas = user.get("estrellas", 0)
        helados = user.get("helados", 0)
        nivel = user.get("nivel", "green")
        st.metric("Estrellas", estrellas)
        st.metric("Helados comprados", f"{helados} / 6")
        if nivel == "green":
            st.progress(estrellas / 200)
            st.caption(f"Faltan {200 - estrellas} para Gold")
        else:
            st.progress(estrellas / 100)
            st.caption(f"Faltan {100 - estrellas} para bebida gratis")
        if helados >= 6:
            st.success("Puedes canjear un helado gratis")
            if st.button("Canjear ahora"):
                canjear_helado(st.session_state.username)
                st.rerun()

# ────────────────────────────────────────────────
# MIS PEDIDOS
# ────────────────────────────────────────────────
elif st.session_state.screen == "MIS_PEDIDOS":
    st.subheader("Mis Pedidos")
    q = db.collection("orders").where("user_email", "==", st.session_state.username).order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()
    data = [d.to_dict() for d in q]
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df[["type", "status", "total", "created_at"]])
    else:
        st.info("No tienes pedidos aún")

# ────────────────────────────────────────────────
# PERFIL
# ────────────────────────────────────────────────
elif st.session_state.screen == "PERFIL":
    st.subheader("Mi Perfil")
    user = get_user(st.session_state.username)
    if user:
        st.write("Nombre:", user.get("full_name", "—"))
        st.write("Teléfono:", user.get("phone", "—"))
        st.write("Correo:", user.get("email", "—"))
        st.write("ID Cliente:", user.get("cliente_id", "—"))

# ────────────────────────────────────────────────
# ADMIN (básico - cola + estado + recompensas manuales)
# ────────────────────────────────────────────────
elif st.session_state.screen == "ADMIN":
    st.subheader("Panel Admin")
    pin = st.text_input("PIN", type="password")
    if pin == "2424":
        tab = st.radio("Sección", ["Cola Pedidos", "Recompensas Manual", "Arqueo Básico"])
        if tab == "Cola Pedidos":
            st.subheader("Pedidos en cola")
            q = db.collection("orders").where("status", "in", ["RECEIVED", "IN_PROGRESS"]).stream()
            data = []
            for d in q:
                o = d.to_dict()
                o["id"] = d.id
                data.append(o)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df[["id", "type", "status", "total", "user_email"]])
            else:
                st.info("No hay pedidos en cola")
        elif tab == "Recompensas Manual":
            ident = st.text_input("Correo o ID Cliente")
            if st.button("Buscar"):
                user = get_user(ident)
                if user:
                    st.write("Encontrado:", user["email"])
                    stars = st.number_input("Sumar estrellas", min_value=0, value=0)
                    helados = st.number_input("Sumar helados", min_value=0, value=0)
                    if st.button("Aplicar"):
                        update_points(ident, stars, helados, "Admin manual")
                        st.success("Actualizado")
                else:
                    st.error("No encontrado")
        elif tab == "Arqueo Básico":
            st.subheader("Arqueo rápido")
            b20 = st.number_input("$20", 0)
            b50 = st.number_input("$50", 0)
            b100 = st.number_input("$100", 0)
            b200 = st.number_input("$200", 0)
            b500 = st.number_input("$500", 0)
            tarjetas = st.number_input("Tarjetas", 0.0)
            total_cash = b20*20 + b50*50 + b100*100 + b200*200 + b500*500
            total = total_cash + tarjetas
            st.metric("Total efectivo", money(total_cash))
            st.metric("Total día", money(total))

# ────────────────────────────────────────────────
# DEFAULT
# ────────────────────────────────────────────────
else:
    st.session_state.screen = "LOGIN"
    st.rerun()

st.markdown("---")
st.caption(f"Churrería Porfirio © {now_cdmx().year} • Parte 1/2")

# =============================================================================
# CHURRERÍA PORFIRIO - PARTE 2/2 (Pantallas MESA + PICKUP + Carrito + ETA + Guardar)
# Continuación directa de Parte 1
# =============================================================================

# ────────────────────────────────────────────────
# RENDER MENÚ + CARRITO (funciones reutilizables)
# ────────────────────────────────────────────────
def render_menu_store(cart_key: str):
    st.markdown("<div class='card'><h3>🧾 Menú de la Casa</h3><hr class='hr-soft'>", unsafe_allow_html=True)
    
    cats = ["Todas"] + sorted(set(m["category"] for m in DEFAULT_MENU if m.get("active")))
    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        selected_cat = st.selectbox("Categoría", cats, key=f"cat_{cart_key}")
    with col_filter2:
        search_term = st.text_input("Buscar producto", key=f"search_{cart_key}").strip().lower()

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
                st.markdown(f"""
                <div class='card' style='height:220px;'>
                    <h4>{item['name']}</h4>
                    <small>{item['category']} • {money(item['price'])}</small>
                """, unsafe_allow_html=True)
                
                qty = st.number_input("Cantidad", min_value=1, value=1, step=1, key=f"qty_{cart_key}_{item['id']}")
                note = st.text_input("Nota (salsas, sin algo...)", key=f"note_{cart_key}_{item['id']}")
                
                if st.button("➕ Agregar", key=f"add_{cart_key}_{item['id']}"):
                    st.session_state[cart_key].append({
                        "menu_id": item["id"],
                        "qty": qty,
                        "note": note.strip(),
                        "price": item["price"]
                    })
                    st.toast(f"Agregado: {item['name']} × {qty}")
                    st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_cart(cart_key: str) -> Tuple[float, List[Dict]]:
    cart = st.session_state.get(cart_key, [])
    st.markdown("<div class='card'><h3>🛒 Tu Pedido</h3><hr class='hr-soft'>", unsafe_allow_html=True)
    
    if not cart:
        st.info("Tu carrito está vacío")
        st.markdown("</div>", unsafe_allow_html=True)
        return 0.0, []
    
    subtotal = 0.0
    new_cart = []
    
    for i, item in enumerate(cart):
        menu_item = MENU_INDEX.get(item["menu_id"])
        if not menu_item:
            continue
        
        line_total = item["qty"] * item["price"]
        subtotal += line_total
        
        col1, col2, col3, col4 = st.columns([5, 2, 2, 1])
        with col1:
            st.write(f"**{menu_item['name']}**")
            if item.get("note"):
                st.caption(item["note"])
        with col2:
            new_qty = st.number_input("Cant.", min_value=1, value=item["qty"], key=f"cart_qty_{cart_key}_{i}")
        with col3:
            st.write(money(line_total))
        with col4:
            if st.button("🗑", key=f"rm_{cart_key}_{i}"):
                new_qty = 0
        
        if new_qty > 0:
            new_item = item.copy()
            new_item["qty"] = new_qty
            new_cart.append(new_item)
    
    st.session_state[cart_key] = new_cart
    
    st.markdown(f"<h4 style='text-align:right;'>Total: {money(subtotal)}</h4>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    return subtotal, new_cart


# ────────────────────────────────────────────────
# PANTALLA MESA
# ────────────────────────────────────────────────
elif st.session_state.screen == "MESA":
    st.subheader("🍽️ Pedir en Mesa")
    
    if st.button("← Volver al Inicio", key="back_mesa"):
        st.session_state.screen = "HOME"
        st.rerun()
    
    st.session_state.mesa_num = st.text_input("Número de mesa / zona", value=st.session_state.mesa_num.strip())
    
    if not st.session_state.mesa_num:
        st.warning("Por favor ingresa el número de mesa para continuar")
    else:
        render_menu_store("cart_mesa")
        total, cart_items = render_cart("cart_mesa")
        
        if cart_items:
            eta_sec = estimate_eta_seconds(cart_items)
            eta_min = max(5, eta_sec // 60)  # mínimo 5 min para que no sea 0
            st.info(f"⏱️ Tiempo estimado aproximado: **{eta_min} minutos** (según carga actual)")
            
            promo_msg = ""
            hour = now_cdmx().hour
            if 8 <= hour < 12:
                promo_msg = "☕ Recuerda: con chilaquiles o desayunos, café de olla por nuestra cuenta"
            elif 13 <= hour < 17:
                promo_msg = "🍦 Compra 2 helados Bahama y llévate un churro relleno GRATIS"
            if promo_msg:
                st.success(promo_msg)
            
            if st.button("Confirmar y Enviar Pedido a Mesa", type="primary", use_container_width=True):
                order_data = {
                    "type": "MESA",
                    "mesa": st.session_state.mesa_num,
                    "items": cart_items,
                    "total": total,
                    "eta_seconds": eta_sec,
                    "status": "RECEIVED",
                    "user_email": st.session_state.username,
                    "cliente_id": st.session_state.cliente_id,
                    "created_at": now_cdmx().isoformat(),
                    "updated_at": now_cdmx().isoformat()
                }
                oid = persist_order(order_data)
                
                # Aplicar estrellas
                stars = int(total // 10)
                if stars > 0:
                    update_points(st.session_state.username, stars_add=stars, detalle=f"Pedido Mesa #{oid} → +{stars} estrellas")
                
                st.success(f"¡Pedido #{oid} enviado correctamente! ETA ~{eta_min} min")
                st.balloons()
                st.session_state.cart_mesa = []
                st.rerun()


# ────────────────────────────────────────────────
# PANTALLA PICK UP
# ────────────────────────────────────────────────
elif st.session_state.screen == "PICKUP":
    st.subheader("🚗 Pedir para Pick Up")
    
    if st.button("← Volver al Inicio", key="back_pickup"):
        st.session_state.screen = "HOME"
        st.rerun()
    
    render_menu_store("cart_pickup")
    total, cart_items = render_cart("cart_pickup")
    
    if cart_items:
        eta_sec = estimate_eta_seconds(cart_items)
        eta_min = max(5, eta_sec // 60)
        st.info(f"⏱️ Tiempo estimado para recoger: **{eta_min} minutos**")
        
        promo_msg = ""
        hour = now_cdmx().hour
        if 8 <= hour < 12:
            promo_msg = "☕ Promo matutina activa hoy"
        elif 13 <= hour < 17:
            promo_msg = "🍦 Promo tarde activa hoy"
        if promo_msg:
            st.success(promo_msg)
        
        payment_method = st.radio("Forma de pago", ["Transferencia / Efectivo", "Mercado Pago"])
        
        if st.button("Confirmar y Generar Pedido Pick Up", type="primary", use_container_width=True):
            order_data = {
                "type": "PICKUP",
                "items": cart_items,
                "total": total,
                "eta_seconds": eta_sec,
                "status": "RECEIVED",
                "payment_method": payment_method,
                "user_email": st.session_state.username,
                "cliente_id": st.session_state.cliente_id,
                "created_at": now_cdmx().isoformat(),
                "updated_at": now_cdmx().isoformat()
            }
            oid = persist_order(order_data)
            
            stars = int(total // 10)
            if stars > 0:
                update_points(st.session_state.username, stars_add=stars, detalle=f"Pedido PickUp #{oid} → +{stars} estrellas")
            
            st.success(f"¡Pedido #{oid} confirmado! Recógelo en ~{eta_min} minutos")
            st.balloons()
            st.session_state.cart_pickup = []
            st.rerun()


# ────────────────────────────────────────────────
# FIN DE PARTE 2
# ────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Churrería Porfirio © {now_cdmx().year} • Parte 2/2 - Pedidos y Carrito")
# =============================================================================
# CHURRERÍA PORFIRIO - PARTE 3/3 (PANEL ADMIN COMPLETO: Cola + Recompensas + Rifa + Arqueo + Utilidad)
# Continuación directa de Parte 1 y Parte 2
# =============================================================================

# ────────────────────────────────────────────────
# ADMIN PANEL (completo)
# ────────────────────────────────────────────────
elif st.session_state.screen == "ADMIN":
    st.subheader("🛡️ Panel de Administración")
    
    if st.button("← Volver al Inicio", key="back_admin"):
        st.session_state.screen = "HOME"
        st.rerun()
    
    pin = st.text_input("PIN de Acceso Admin", type="password", value="", key="admin_pin_input")
    
    if pin == "2424":  # ← CAMBIA ESTO POR TU PIN REAL O USA secrets
        st.success("Acceso autorizado — Modo Admin activado")
        log_action("admin_login", st.session_state.username, "Acceso panel admin")
        
        tab_admin = st.radio("Sección Admin", [
            "Cola de Pedidos", 
            "Gestión Recompensas", 
            "Rifa Boletos", 
            "Arqueo de Caja", 
            "Consolidación Utilidad", 
            "Logs Recientes"
        ])
        
        if tab_admin == "Cola de Pedidos":
            st.subheader("🧑‍🍳 Cola de Pedidos Activos")
            status_filter = st.multiselect("Filtrar por estado", ["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"], default=["RECEIVED", "IN_PROGRESS"])
            
            q = db.collection("orders").where("status", "in", status_filter).order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()
            data = []
            for doc in q:
                o = doc.to_dict()
                o["id"] = doc.id
                data.append(o)
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df[["id", "type", "status", "total", "mesa", "user_email", "created_at"]])
                
                selected_oid = st.selectbox("Seleccionar pedido para actualizar", df["id"].tolist())
                if selected_oid:
                    order_data = df[df["id"] == selected_oid].iloc[0].to_dict()
                    st.write("Detalles:")
                    st.json(order_data)
                    
                    new_status = st.selectbox("Nuevo estado", ["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"], index=["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"].index(order_data["status"]))
                    if st.button("Actualizar Estado"):
                        db.collection("orders").document(selected_oid).update({
                            "status": new_status,
                            "updated_at": now_cdmx().isoformat(),
                            "updated_by": st.session_state.username
                        })
                        log_action("order_update", st.session_state.username, f"Pedido {selected_oid} → {new_status}")
                        st.success("Estado actualizado")
                        st.rerun()
            else:
                st.info("No hay pedidos con los filtros seleccionados")
        
        elif tab_admin == "Gestión Recompensas":
            st.subheader("🎟️ Gestionar Recompensas Manual")
            ident = st.text_input("Correo o ID Cliente")
            if st.button("Buscar Cliente"):
                user = get_user(ident)
                if user:
                    st.success(f"Encontrado: {user['email']} (ID: {user['cliente_id']})")
                    st.write("Estrellas actuales:", user.get("estrellas", 0))
                    st.write("Helados actuales:", user.get("helados", 0))
                    st.write("Nivel:", user.get("nivel", "green"))
                    
                    col_stars, col_helados = st.columns(2)
                    add_stars = col_stars.number_input("Sumar estrellas", min_value=0, value=0)
                    add_helados = col_helados.number_input("Sumar helados", min_value=0, value=0)
                    
                    if st.button("Aplicar Recompensas"):
                        update_points(user["email"], stars_add=add_stars, helados_add=add_helados, detalle="Admin manual")
                        st.success("Recompensas aplicadas")
                        st.rerun()
                else:
                    st.error("Cliente no encontrado")
        
        elif tab_admin == "Rifa Boletos":
            st.subheader("🎟️ Sistema de Rifa")
            raffle_id = st.secrets.get("raffle_id", "RIFA_2026")
            st.caption(f"Rifa activa: {raffle_id}")
            
            customer_ident = st.text_input("Correo o ID Cliente")
            ticket_num = st.text_input("Número de ticket / folio compra")
            boleto = st.number_input("Número de boleto a asignar", min_value=1, step=1, value=1)
            
            if st.button("Asignar Boleto"):
                user = get_user(customer_ident)
                if not user:
                    st.error("Cliente no encontrado")
                elif not ticket_num:
                    st.error("Ingresa número de ticket")
                else:
                    doc_id = f"{raffle_id}_{boleto}"
                    ref = db.collection("raffle_tickets").document(doc_id)
                    if ref.get().exists:
                        st.error("Ese boleto ya está asignado")
                    else:
                        ref.set({
                            "raffle_id": raffle_id,
                            "boleto": boleto,
                            "cliente_id": user["cliente_id"],
                            "email": user["email"],
                            "ticket_num": ticket_num,
                            "assigned_by": st.session_state.username,
                            "assigned_at": now_cdmx().isoformat()
                        })
                        log_action("rifa_asign", st.session_state.username, f"Boleto {boleto} a {user['cliente_id']}")
                        st.success(f"Boleto {boleto} asignado correctamente")
        
        elif tab_admin == "Arqueo de Caja":
            st.subheader("💵 Arqueo de Caja")
            today = now_cdmx().date().isoformat()
            shift = st.selectbox("Turno", ["Matutino", "Vespertino"])
            
            col1, col2, col3 = st.columns(3)
            b20 = col1.number_input("$20", 0)
            b50 = col1.number_input("$50", 0)
            b100 = col2.number_input("$100", 0)
            b200 = col2.number_input("$200", 0)
            b500 = col3.number_input("$500", 0)
            tarjetas = col3.number_input("Tarjetas / Terminal", 0.0)
            
            cash_total = b20*20 + b50*50 + b100*100 + b200*200 + b500*500
            grand_total = cash_total + tarjetas
            st.metric("Efectivo", money(cash_total))
            st.metric("Total Día", money(grand_total))
            
            if st.button("Guardar Arqueo"):
                doc_id = f"{today}_{'MAT' if shift == 'Matutino' else 'VES'}"
                db.collection("cash_closings").document(doc_id).set({
                    "date": today,
                    "shift": shift,
                    "b20": b20, "b50": b50, "b100": b100, "b200": b200, "b500": b500,
                    "tarjetas": tarjetas,
                    "cash_total": cash_total,
                    "grand_total": grand_total,
                    "created_by": st.session_state.username,
                    "created_at": now_cdmx().isoformat()
                })
                log_action("arqueo", st.session_state.username, f"{doc_id} - ${grand_total}")
                st.success("Arqueo guardado")
        
        elif tab_admin == "Consolidación Utilidad":
            st.subheader("📈 Consolidación Utilidad (Super Admin)")
            start_date = st.date_input("Inicio", now_cdmx().date())
            end_date = st.date_input("Fin", now_cdmx().date())
            
            if st.button("Calcular"):
                start_iso = start_date.isoformat()
                end_iso = end_date.isoformat()
                
                closings = db.collection("cash_closings").where("date", ">=", start_iso).where("date", "<=", end_iso).stream()
                total_cash = total_cards = 0
                for c in closings:
                    d = c.to_dict()
                    total_cash += d.get("cash_total", 0)
                    total_cards += d.get("tarjetas", 0)
                total_sales = total_cash + total_cards
                
                # Costos (puedes editar en secrets o aquí)
                fixed_costs = {
                    "Nomina": 10100, "Renta": 8750, "Luz": 937.5, "Agua": 300, "Regalias": 3770
                }
                variable_costs = {
                    "SAMS/SUPER": 4086.92, "Mercado": 320, "Molino": 100, "Gas": 712
                }
                total_costs = sum(fixed_costs.values()) + sum(variable_costs.values())
                profit = total_sales - total_costs
                cash_to_return = max(0, total_cash - profit) if profit > 0 else total_cash
                
                st.metric("Ventas Totales", money(total_sales))
                st.metric("Costos Totales", money(total_costs))
                st.metric("Utilidad", money(profit))
                st.metric("Cash a regresar", money(cash_to_return))
                
                if st.button("Guardar Consolidación"):
                    doc_id = f"{start_iso}_{end_iso}"
                    db.collection("profit_consolidations").document(doc_id).set({
                        "period_start": start_iso,
                        "period_end": end_iso,
                        "sales_total": total_sales,
                        "total_costs": total_costs,
                        "profit": profit,
                        "cash_to_return": cash_to_return,
                        "created_by": st.session_state.username,
                        "created_at": now_cdmx().isoformat()
                    })
                    st.success("Consolidación guardada")
        
        elif tab_admin == "Logs Recientes":
            st.subheader("📜 Logs Recientes")
            logs = db.collection("logs").order_by("fecha", direction=firestore.Query.DESCENDING).limit(20).stream()
            data = [l.to_dict() for l in logs]
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df[["accion", "usuario", "detalle", "fecha"]])
            else:
                st.info("No hay logs recientes")
    else:
        st.warning("PIN incorrecto")

# ────────────────────────────────────────────────
# FIN DEL ARCHIVO COMPLETO
# ────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Churrería Porfirio © {now_cdmx().year} • Versión Fusionada Completa")
