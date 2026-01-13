# Churrería Porfirio — App única (Streamlit)
# Store profesional: Pedir en mesa | Pick Up | Recompensas | Admin (colas, status, puntos)
# Estilo azul talavera (inspirado en tu imagen)
# Autor: ChatGPT para Enrique (Kike)
# Requisitos: streamlit, firebase_admin
# Opcional: mercadopago (para links de pago)
# Timezone: America/Mexico_City

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Tuple, Optional
import random
import string
import hashlib
import secrets

import firebase_admin
from firebase_admin import credentials, firestore

# =========================
# CONFIG / BRAND
# =========================

st.markdown(
"""
<div class="header-logo">
  <img src="https://TU_URL_DEL_LOGO.png">
</div>
""",
unsafe_allow_html=True,
)


APP_TITLE = "Churrería Porfirio — Recompensas & Pedidos"
CDMX_TZ = ZoneInfo("America/Mexico_City")

# Paleta (talavera/azul) — ajustable
C_BLUE = "#1E4E9A"
C_BLUE_DARK = "#123A73"
C_BLUE_SOFT = "#EAF1FF"
C_TEXT = "#0F172A"
C_MUTED = "#64748B"
C_OK = "#16A34A"
C_WARN = "#F59E0B"
C_BAD = "#DC2626"
C_CARD = "#FFFFFF"
C_BORDER = "#D7E3FF"

st.set_page_config(page_title="Churrería Porfirio", layout="wide")

# =========================
# CSS — Talavera Marino (FINAL)
# =========================
st.markdown(
"""
<style>

/* =========================
   PALETA MARINA (Talavera)
   ========================= */
:root {
  --blue-dark: #0A2E5D;
  --blue-main: #0F4C81;
  --blue-mid:  #3F78B8;
  --blue-soft: #D6E6F5;
  --border:    #B6CCE6;
  --text-main: #1F2937;
  --text-muted:#6B7280;
}

/* =========================
   FONDO GENERAL BLANCO
   ========================= */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
main,
section.main {
  background: #FFFFFF !important;
}

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
  background: #FFFFFF !important;
}

[data-testid="stHeader"] {
  box-shadow: none !important;
}

/* =========================
   CONTENEDOR
   ========================= */
.block-container {
  padding-top: 1.4rem;
  padding-bottom: 2.5rem;
  max-width: 1200px;
}

/* =========================
   TIPOGRAFÍA
   ========================= */
h1, h2, h3, h4 {
  color: var(--text-main);
}

.small-muted {
  color: var(--text-muted);
  font-size: 0.92rem;
}

/* =========================
   BADGES
   ========================= */
.badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.82rem;
  border: 1px solid var(--border);
  background: var(--blue-soft);
  color: var(--blue-dark);
}

/* =========================
   CARDS (DEGRADADO MARINO)
   ========================= */
.card {
  background-color: #FFFFFF !important;
  background-image: linear-gradient(90deg,
    var(--blue-main) 0%,
    var(--blue-mid) 28%,
    var(--blue-soft) 58%,
    #FFFFFF 100%
  ) !important;

  border: 1px solid var(--border) !important;
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 12px 28px rgba(10,46,93,0.20) !important;
}



.card-title {
  font-weight: 800;
  font-size: 1.05rem;
  color: var(--text-main);
  margin-bottom: 4px;
}

.card-sub {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: 10px;
}

.card-price {
  font-weight: 900;
  color: var(--blue-dark);
  font-size: 1.05rem;
}

.hr-soft {
  height: 1px;
  background: var(--border);
  border: none;
  margin: 12px 0;
}

/* =========================
   BOTONES
   ========================= */
.stButton > button {
  border-radius: 14px;
  border: 1px solid var(--border);
  padding: 0.65rem 1rem;
  font-weight: 700;
  background: #FFFFFF;
  color: var(--blue-dark);
}

.stButton > button:hover {
  border-color: var(--blue-main);
  color: var(--blue-main);
}

/* Botón primario */
.primary-btn .stButton > button {
  background: var(--blue-main);
  color: #FFFFFF;
  border: 1px solid var(--blue-main);
}

.primary-btn .stButton > button:hover {
  background: var(--blue-dark);
  border-color: var(--blue-dark);
}

/* =========================
   INPUTS
   ========================= */
.stTextInput input,
.stNumberInput input,
.stSelectbox select {
  border-radius: 14px !important;
}

/* =========================
   TABS / SEGMENTED
   ========================= */
[data-baseweb="tab-list"] button {
  border-radius: 14px !important;
}

/* =========================
   HEADER LOGO
   ========================= */
.header-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 1.2rem;
}

.header-logo img {
  max-height: 90px;
}

/* =========================
   FOOTER BANNER
   ========================= */
.footer-banner {
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: center;
}

.footer-banner img {
  max-width: 100%;
  border-radius: 16px;
}

/* =========================
   OCULTAR FOOTER STREAMLIT
   ========================= */
footer {
  visibility: hidden;
}

</style>
""",
unsafe_allow_html=True,
)


# =========================
# HELPERS
# =========================

def now_cdmx() -> datetime:
    return datetime.now(CDMX_TZ)


def money(n: float) -> str:
    try:
        return f"$ {float(n):,.0f}"
    except Exception:
        return "$ 0"


def generate_cliente_id(length: int = 5) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _hash_password(password: str, salt: str) -> str:
    # PBKDF2 (sin librerías extra)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return dk.hex()


def make_password_record(password: str) -> Dict[str, str]:
    salt = secrets.token_hex(16)
    return {"salt": salt, "hash": _hash_password(password, salt)}


def verify_password(password: str, rec: Dict[str, str]) -> bool:
    if not rec or "salt" not in rec or "hash" not in rec:
        return False
    return _hash_password(password, rec["salt"]) == rec["hash"]


def log_action(db, action_type: str, usuario: str, detalle: str = "") -> None:
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
        # no bloqueamos la app por logs
        pass


# =========================
# FIREBASE INIT
# =========================
try:
    creds = st.secrets["firebase_credentials"]
    cred = credentials.Certificate(dict(creds))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"❌ Firebase error: {e}")
    st.stop()

# =========================
# SESSION STATE
# =========================
ss = st.session_state
ss.setdefault("usuario_actual", None)  # email
ss.setdefault("cliente_confirmado", None)
ss.setdefault("promo_shown", False)
ss.setdefault("cart_pickup", [])
ss.setdefault("cart_mesa", [])
ss.setdefault("mesa_actual", "")

# =========================
# MENÚ — basado en tus fotos
# (Incluye station + tiempos para ETA)
# =========================
# station:
#   - barista: café/bebidas
#   - fryer: churros
#   - cold: malteadas/frappes
#   - stock: listo

DEFAULT_MENU: List[Dict[str, Any]] = [
    # CHURROS
    {"id": "churro_3", "name": "Churros tradicionales (3 pzas)", "category": "Churros", "price": 49, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "active": True},
    {"id": "churro_6", "name": "Churros tradicionales (6 pzas)", "category": "Churros", "price": 79, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "active": True},
    {"id": "churro_12", "name": "Churros tradicionales (12 pzas)", "category": "Churros", "price": 149, "station": "fryer", "prep_time": 180, "batch_capacity": 6, "active": True},

    {"id": "churro_relleno_1", "name": "Churro relleno (1 pza)", "category": "Rellenos", "price": 35, "station": "fryer", "prep_time": 210, "batch_capacity": 3, "active": True},
    {"id": "churro_relleno_3", "name": "Churros rellenos (3 pzas)", "category": "Rellenos", "price": 99, "station": "fryer", "prep_time": 210, "batch_capacity": 3, "active": True},

    {"id": "mini_churros", "name": "Mini churros (15 pzas)", "category": "Mini Churros", "price": 79, "station": "fryer", "prep_time": 240, "batch_capacity": 15, "active": True},

    # POSTRES / SALADOS
    {"id": "bunuelos", "name": "Buñuelos (2 pzas)", "category": "Postres", "price": 49, "station": "stock", "prep_time": 0, "active": True},
    {"id": "carlota", "name": "Carlota (fresa / vainilla / chocolate)", "category": "Postres", "price": 75, "station": "stock", "prep_time": 0, "active": True},
    {"id": "adelitas", "name": "Adelitas (queso / española / jamón y queso)", "category": "Antojitos", "price": 139, "station": "stock", "prep_time": 0, "active": True},
    {"id": "salsa_extra", "name": "Salsa extra (cajeta / chocolate / lechera)", "category": "Extras", "price": 15, "station": "stock", "prep_time": 0, "active": True},

    # DESAYUNOS (incluye bebida 354 ml)
    {"id": "chilaquiles", "name": "Chilaquiles (verde o roja) — incluye bebida 354 ml", "category": "Desayunos", "price": 149, "station": "stock", "prep_time": 480, "active": True, "includes_drink_354": True},
    {"id": "enchiladas", "name": "Enchiladas (verde o roja) — incluye bebida 354 ml", "category": "Desayunos", "price": 149, "station": "stock", "prep_time": 540, "active": True, "includes_drink_354": True},
    {"id": "enfrijoladas", "name": "Enfrijoladas — incluye bebida 354 ml", "category": "Desayunos", "price": 149, "station": "stock", "prep_time": 540, "active": True, "includes_drink_354": True},
    {"id": "molletes", "name": "Molletes — incluye bebida 354 ml", "category": "Desayunos", "price": 139, "station": "stock", "prep_time": 420, "active": True, "includes_drink_354": True},
    {"id": "sincronizadas", "name": "Sincronizadas — incluye bebida 354 ml", "category": "Desayunos", "price": 129, "station": "stock", "prep_time": 360, "active": True, "includes_drink_354": True},

    # PROMOS (con horarios)
    {"id": "promo_viejos_tiempos", "name": "Recordando viejos tiempos (1L chocolate + 6 churros)", "category": "Promociones", "price": 229, "station": "mix", "prep_time": 0, "active": True, "schedule": "08:00-12:00"},
    {"id": "promo_dulce_dia", "name": "Empieza un dulce día (café de olla + churro relleno)", "category": "Promociones", "price": 69, "station": "mix", "prep_time": 0, "active": True, "schedule": "08:00-12:00"},
    {"id": "promo_granizados", "name": "Congelando momentos (2 granizados 354 ml)", "category": "Promociones", "price": 99, "station": "mix", "prep_time": 0, "active": True, "schedule": "13:00-17:00"},

    # CAFÉ
    {"id": "espresso", "name": "Espresso", "category": "Café", "price": 39, "station": "barista", "prep_time": 180, "active": True},
    {"id": "americano", "name": "Americano", "category": "Café", "price": 45, "station": "barista", "prep_time": 180, "active": True},
    {"id": "cafe_olla", "name": "Café de olla", "category": "Café", "price": 55, "station": "barista", "prep_time": 240, "active": True},

    {"id": "latte", "name": "Café Latte", "category": "Café", "price": 65, "station": "barista", "prep_time": 240, "active": True},
    {"id": "mocha", "name": "Mocha", "category": "Café", "price": 75, "station": "barista", "prep_time": 270, "active": True},
    {"id": "capuccino", "name": "Capuccino", "category": "Café", "price": 75, "station": "barista", "prep_time": 270, "active": True},
    {"id": "chai_latte", "name": "Chai Latte", "category": "Café", "price": 75, "station": "barista", "prep_time": 300, "active": True},

    {"id": "te_354", "name": "Té (354 ml)", "category": "Café", "price": 40, "station": "barista", "prep_time": 180, "active": True},

    # CHOCOLATE CALIENTE
    {"id": "chocolate_354", "name": "Chocolate caliente 354 ml", "category": "Chocolate", "price": 79, "station": "barista", "prep_time": 240, "active": True},
    {"id": "chocolate_473", "name": "Chocolate caliente 473 ml", "category": "Chocolate", "price": 89, "station": "barista", "prep_time": 300, "active": True},

    # FRAPPES / GRANIZADOS
    {"id": "frappe_354", "name": "Frappe / Granizado 354 ml", "category": "Bebidas frías", "price": 79, "station": "cold", "prep_time": 240, "active": True},
    {"id": "frappe_473", "name": "Frappe / Granizado 473 ml", "category": "Bebidas frías", "price": 89, "station": "cold", "prep_time": 270, "active": True},

    # MALTEADAS
    {"id": "malteada_354", "name": "Malteada 354 ml", "category": "Bebidas frías", "price": 99, "station": "cold", "prep_time": 240, "active": True},
    {"id": "malteada_473", "name": "Malteada 473 ml", "category": "Bebidas frías", "price": 115, "station": "cold", "prep_time": 270, "active": True},

    # OTRAS
    {"id": "refresco_355", "name": "Refresco 355 ml", "category": "Bebidas", "price": 45, "station": "stock", "prep_time": 0, "active": True},
    {"id": "agua_500", "name": "Agua natural 500 ml", "category": "Bebidas", "price": 30, "station": "stock", "prep_time": 0, "active": True},
]

# Sanitiza
DEFAULT_MENU = [m for m in DEFAULT_MENU if isinstance(m, dict) and "id" in m]
MENU_INDEX: Dict[str, Dict[str, Any]] = {m["id"]: m for m in DEFAULT_MENU}

FRYER_BASKETS = 2  # 2 canastillas

# =========================
# USUARIOS / REWARDS
# =========================

def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    # 1) Por doc id = email
    doc = db.collection("usuarios").document(identifier).get()
    if doc.exists:
        d = doc.to_dict() or {}
        d.setdefault("email", identifier)
        return d

    # 2) Por cliente_id
    query = db.collection("usuarios").where("cliente_id", "==", identifier).limit(1).stream()
    for r in query:
        d = r.to_dict() or {}
        d.setdefault("email", r.id)
        return d

    return None


def save_user(email: str, data: Dict[str, Any]) -> None:
    db.collection("usuarios").document(email).set(data)


def reward_apply(user: Dict[str, Any], stars_add: int = 0, helados_add: int = 0) -> Dict[str, Any]:
    user["estrellas"] = int(user.get("estrellas", 0)) + int(stars_add)
    user["helados"] = int(user.get("helados", 0)) + int(helados_add)

    # Nivel: green -> gold a 200
    if user.get("nivel") == "green" and user["estrellas"] >= 200:
        user["nivel"] = "gold"
        user["estrellas"] = 0
        log_action(db, "recompensa", user.get("email", ""), "Ascenso a GOLD por 200 estrellas")

    # Gold: cada 100 estrellas = bebida (log)
    if user.get("nivel") == "gold":
        bebidas = user["estrellas"] // 100
        user["estrellas"] = user["estrellas"] % 100
        if bebidas > 0:
            for _ in range(int(bebidas)):
                log_action(db, "recompensa", user.get("email", ""), "🎁 Bebida GOLD (100 estrellas)")

    user["canjear_helado"] = int(user.get("helados", 0)) >= 6
    return user


def update_points(identifier: str, stars_add: int = 0, helados_add: int = 0, detalle: str = "") -> None:
    user = get_user(identifier)
    if not user:
        st.warning("Usuario no encontrado.")
        return

    user = reward_apply(user, stars_add=stars_add, helados_add=helados_add)
    save_user(user["email"], user)

    if detalle:
        log_action(db, "consumo", user["email"], detalle)
    else:
        log_action(db, "consumo", user["email"], f"+{stars_add} estrellas, +{helados_add} helados")


def canjear_helado(identifier: str) -> None:
    user = get_user(identifier)
    if not user:
        st.warning("Usuario no encontrado.")
        return
    if int(user.get("helados", 0)) >= 6:
        user["helados"] = int(user.get("helados", 0)) - 6
        user["canjear_helado"] = False
        save_user(user["email"], user)
        st.success("🎉 Helado canjeado exitosamente")
        log_action(db, "canje", user["email"], "Helado (6)")
    else:
        st.warning("❌ No tiene suficientes helados")


def show_user_summary(user: Dict[str, Any]) -> None:
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='card-title'>Tu perfil</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='small-muted'>Correo</div><div><b>{user.get('email','')}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='small-muted'>Número de cliente</div><div><b>{user.get('cliente_id','No asignado')}</b></div>", unsafe_allow_html=True)

    nivel = user.get("nivel", "green")
    st.markdown(f"<div class='small-muted'>Nivel</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='badge'>{'🥇 Gold' if nivel=='gold' else '🥈 Green'}</div>",
        unsafe_allow_html=True,
    )

    progress_max = 100 if nivel == "gold" else 200
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.progress(min(float(user.get("estrellas", 0)) / progress_max, 1.0), text=f"{int(user.get('estrellas',0))} / {progress_max} estrellas")
    st.markdown(f"<div class='small-muted'>Helados acumulados</div><div><b>🍦 {int(user.get('helados',0))} / 6</b></div>", unsafe_allow_html=True)

    if user.get("canjear_helado"):
        st.success("🎁 ¡Puedes canjear un helado!")
        if st.button("Canjear helado ahora", key=f"canj_{user.get('email','')}"):
            canjear_helado(user.get("email", ""))

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# PROMOS (POP-UPS) — usando st.dialog
# =========================

def _goto(page_name: str):
    st.query_params["page"] = page_name
    st.rerun()


def show_promotions_popups():
    # Solo una vez por sesión
    if ss.promo_shown:
        return

    hour = now_cdmx().hour

    if 8 <= hour < 12:
        @st.dialog("☕ Recordando viejos tiempos")
        def _promo1():
            st.write("1 litro de chocolate (a elegir) + 6 churros tradicionales — **$229**")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👉 Pedir ahora (Pick Up)", key="promo1_pickup"):
                    _goto("Pick Up")
            with c2:
                if st.button("👉 Pedir en mesa", key="promo1_mesa"):
                    _goto("Mesa")
        _promo1()

        @st.dialog("🥐 Empieza un dulce día")
        def _promo2():
            st.write("Café de olla + 1 churro relleno — **$69**")
            if st.button("👉 Pedir ahora", key="promo2_pickup"):
                _goto("Pick Up")
        _promo2()

    elif 13 <= hour < 17:
        @st.dialog("❄️ Congelando momentos")
        def _promo3():
            st.write("Llévate 2 granizados de 354 ml — **$99**")
            if st.button("👉 Pedir ahora", key="promo3_pickup"):
                _goto("Pick Up")
        _promo3()

    ss.promo_shown = True


# =========================
# ETA / COLAS
# =========================

def calc_station_work_seconds(items: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    """Regresa (barista_seconds, fryer_seconds, cold_seconds)"""
    barista_total = 0
    fryer_total = 0
    cold_total = 0

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
            cap = int(item.get("batch_capacity", 1))
            batches = -(-qty // cap)  # ceil
            rounds = -(-batches // max(1, FRYER_BASKETS))
            fryer_total += rounds * prep
        else:
            barista_total += prep * qty

    return barista_total, fryer_total, cold_total


def fetch_queue_load_seconds() -> Tuple[int, int, int]:
    barista_q = fryer_q = cold_q = 0
    q = db.collection("orders").where("status", "in", ["RECEIVED", "IN_PROGRESS"]).stream()
    for d in q:
        o = d.to_dict() or {}
        items = o.get("items", [])
        b, f, c = calc_station_work_seconds(items)
        barista_q += b
        fryer_q += f
        cold_q += c
    return barista_q, fryer_q, cold_q


def estimate_eta_seconds(new_items: List[Dict[str, Any]]) -> int:
    q_barista, q_fryer, q_cold = fetch_queue_load_seconds()
    b_new, f_new, c_new = calc_station_work_seconds(new_items)
    # se prepara en paralelo por estaciones
    return int(max(q_barista + b_new, q_fryer + f_new, q_cold + c_new))


# =========================
# PAGOS — Mercado Pago (opcional)
# =========================

def create_payment_link(total_amount: float, description: str) -> Optional[str]:
    access_token = st.secrets.get("mercadopago_access_token")
    if access_token:
        try:
            from mercadopago import SDK

            sdk = SDK(access_token)
            preference_data = {
                "items": [
                    {
                        "title": description,
                        "quantity": 1,
                        "currency_id": "MXN",
                        "unit_price": float(total_amount),
                    }
                ],
                "auto_return": "approved",
            }
            pref = sdk.preference().create(preference_data)
            return pref["response"].get("init_point") or pref["response"].get("sandbox_init_point")
        except Exception as e:
            st.warning(f"⚠️ No se pudo crear link de pago con Mercado Pago: {e}")

    # fallback: link fijo si lo guardas en secrets
    return st.secrets.get("mp_payment_link")


# =========================
# UI — MENU / CART
# =========================

def _cart_add(cart_key: str, menu_id: str, qty: int, note: str = ""):
    if qty <= 0:
        return
    ss[cart_key].append({"menu_id": menu_id, "qty": int(qty), "note": note.strip()})


def render_menu_store(cart_key: str):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🧾 Menú</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-sub'>Elige productos y agrégalos al carrito.</div>", unsafe_allow_html=True)

    cats = ["Todas"] + sorted({m["category"] for m in DEFAULT_MENU if m.get("active")})
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        cat = st.selectbox("Filtrar por categoría", options=cats, key=f"cat_{cart_key}")
    with c2:
        only_promos = st.checkbox("Solo promos", value=False, key=f"promo_only_{cart_key}")
    with c3:
        search = st.text_input("Buscar", value="", key=f"search_{cart_key}")

    filtered = [m for m in DEFAULT_MENU if m.get("active")]
    if only_promos:
        filtered = [m for m in filtered if m.get("category") == "Promociones"]
    if cat != "Todas":
        filtered = [m for m in filtered if m.get("category") == cat]
    if search.strip():
        s = search.strip().lower()
        filtered = [m for m in filtered if s in m.get("name", "").lower()]

    st.markdown("<hr class='hr-soft' />", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, m in enumerate(filtered):
        with cols[i % 3]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='card-title'>{m['name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='card-sub'>{m['category']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='card-price'>{money(m['price'])}</div>", unsafe_allow_html=True)

            # Nota opcional (salsas, instrucciones)
            note = ""
            if m.get("includes_drink_354"):
                note = st.selectbox(
                    "Incluye bebida 354 ml",
                    options=["Café (Americano)", "Jugo"],
                    key=f"drink_{cart_key}_{m['id']}",
                )

            qty = st.number_input(
                "Cantidad",
                min_value=1,
                value=1,
                step=1,
                key=f"qty_{cart_key}_{m['id']}",
            )

            add_note = st.text_input("Nota (opcional)", value="", key=f"note_{cart_key}_{m['id']}")
            final_note = ""
            if m.get("includes_drink_354"):
                final_note = f"Bebida: {note}. {add_note}".strip()
            else:
                final_note = add_note.strip()

            if st.button("Agregar", key=f"add_{cart_key}_{m['id']}"):
                _cart_add(cart_key, m["id"], int(qty), final_note)
                st.toast(f"Agregado: {m['name']} x{qty}")

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_cart(cart_key: str) -> Tuple[float, List[Dict[str, Any]]]:
    cart = ss[cart_key]

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🧺 Tu pedido</div>", unsafe_allow_html=True)

    if not cart:
        st.info("Tu carrito está vacío.")
        st.markdown("</div>", unsafe_allow_html=True)
        return 0.0, []

    subtotal = 0.0
    new_cart: List[Dict[str, Any]] = []

    for i, it in enumerate(cart):
        item = MENU_INDEX.get(it.get("menu_id"))
        if not item:
            continue
        qty = int(it.get("qty", 1))
        price = float(item.get("price", 0))
        line = price * qty
        subtotal += line

        cols = st.columns([6, 2, 2, 2])
        with cols[0]:
            st.write(f"**{item['name']}**")
            if it.get("note"):
                st.caption(it.get("note"))
        with cols[1]:
            qty_new = st.number_input("Cant.", min_value=1, value=qty, key=f"cartqty_{cart_key}_{i}")
        with cols[2]:
            st.write(money(line))
        with cols[3]:
            rm = st.button("Quitar", key=f"rm_{cart_key}_{i}")

        if rm:
            qty_new = 0

        if qty_new > 0:
            new_cart.append({"menu_id": it["menu_id"], "qty": int(qty_new), "note": it.get("note", "")})

    ss[cart_key] = new_cart

    st.markdown("<hr class='hr-soft' />", unsafe_allow_html=True)
    st.markdown(f"### Total: {money(subtotal)}")

    st.markdown("</div>", unsafe_allow_html=True)

    return subtotal, new_cart


# =========================
# ORDERS
# =========================

def persist_order(order: Dict[str, Any]) -> Optional[str]:
    try:
        ref = db.collection("orders").add(order)
        return ref[1].id
    except Exception as e:
        st.error(f"❌ No se pudo guardar el pedido: {e}")
        return None


# =========================
# AUTH
# =========================

def ensure_user_fields(u: Dict[str, Any]) -> Dict[str, Any]:
    u.setdefault("nivel", "green")
    u.setdefault("estrellas", 0)
    u.setdefault("helados", 0)
    u.setdefault("canjear_helado", False)
    u.setdefault("cliente_id", u.get("cliente_id") or generate_cliente_id())
    return u


def ui_header():
    # Top header
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(f"## {APP_TITLE}")
        st.markdown("<div class='small-muted'>La churrería más grande de México (y la más deliciosa 😄)</div>", unsafe_allow_html=True)
    with c2:
        if ss.usuario_actual:
            u = get_user(ss.usuario_actual)
            if u:
                nivel = u.get("nivel", "green")
                st.markdown(
                    f"<div class='card'><div class='small-muted'>Sesión</div><div><b>{u.get('email','')}</b></div>"
                    f"<div style='margin-top:6px' class='badge'>{'🥇 Gold' if nivel=='gold' else '🥈 Green'}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<div class='card'><div class='small-muted'>Sesión</div><div><b>Invitado</b></div><div class='small-muted'>Inicia sesión para recompensas</div></div>",
                unsafe_allow_html=True,
            )


def get_page() -> str:
    return st.query_params.get("page", "Inicio")


def set_page(page: str):
    st.query_params["page"] = page


def nav_bar():
    page = get_page()
    pages = ["Inicio", "Registro", "Iniciar sesión", "Pick Up", "Mesa", "Admin"]

    # Nav horizontal (muy estable)
    choice = st.radio(
        "",
        options=pages,
        index=pages.index(page) if page in pages else 0,
        horizontal=True,
        label_visibility="collapsed",
    )
    if choice != page:
        set_page(choice)
        st.rerun()


# =========================
# ADMIN AUTH
# =========================

def is_admin_ok(email: str, password: str) -> bool:
    admin_data = st.secrets.get("admin_credentials")
    if not admin_data:
        return False
    return email == admin_data.get("email") and password == admin_data.get("password")


# =========================
# PAGES
# =========================

def page_inicio():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Bienvenid@</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='card-sub'>Ordena desde tu mesa, para recoger (Pick Up) y acumula recompensas.</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>🍽️ Pedir en mesa</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-sub'>Ideal si ya estás sentado.</div>", unsafe_allow_html=True)
        if st.button("Ir a Mesa"):
            set_page("Mesa")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>🚗 Pick Up</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-sub'>Pide y pasa por tu orden.</div>", unsafe_allow_html=True)
        if st.button("Ir a Pick Up"):
            set_page("Pick Up")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>⭐ Recompensas</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-sub'>Estrellas por tus compras + helados.</div>", unsafe_allow_html=True)
        if st.button("Ver mi perfil"):
            set_page("Iniciar sesión" if not ss.usuario_actual else "Inicio")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Perfil del usuario
    if ss.usuario_actual:
        u = get_user(ss.usuario_actual)
        if u:
            show_user_summary(u)


def page_registro():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>📝 Registro</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-sub'>Crea tu cuenta para acumular recompensas.</div>", unsafe_allow_html=True)

    email = st.text_input("Correo electrónico", key="reg_email")
    password = st.text_input("Contraseña", type="password", key="reg_pwd")

    with st.container():
        st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
        do = st.button("Crear cuenta", key="btn_reg")
        st.markdown("</div>", unsafe_allow_html=True)

    if do:
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            st.error("Ingresa un correo válido.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        if len(password) < 4:
            st.error("La contraseña debe tener al menos 4 caracteres.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        if get_user(email):
            st.error("❌ Este correo ya está registrado. Usa otro.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        cliente_id = generate_cliente_id()
        passrec = make_password_record(password)
        data = ensure_user_fields(
            {
                "email": email,
                "cliente_id": cliente_id,
                "password": passrec,
                "fecha_registro": now_cdmx().isoformat(),
            }
        )
        save_user(email, data)
        log_action(db, "registro", email, f"cliente_id={cliente_id}")
        st.success("✅ Usuario registrado con éxito")
        st.info(f"Tu número de cliente es: **{cliente_id}**")
        st.caption("Puedes iniciar sesión con tu correo o tu número de cliente.")

    st.markdown("</div>", unsafe_allow_html=True)


def page_login():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🔐 Iniciar sesión</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-sub'>Ingresa con tu correo o tu número de cliente.</div>", unsafe_allow_html=True)

    identifier = st.text_input("Correo o número de cliente", key="login_ident")
    password = st.text_input("Contraseña", type="password", key="login_pwd")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
        do = st.button("Iniciar sesión", key="btn_login")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        if ss.usuario_actual:
            if st.button("Cerrar sesión", key="btn_logout"):
                ss.usuario_actual = None
                st.success("Sesión cerrada")
                set_page("Inicio")
                st.rerun()

    if do:
        user = get_user((identifier or "").strip())
        if not user:
            st.error("Usuario no encontrado.")
        else:
            rec = user.get("password")
            if verify_password(password or "", rec or {}):
                ss.usuario_actual = user.get("email")
                st.success(f"Bienvenido {user.get('email','')}")
                log_action(db, "login", user.get("email", ""), "")
                set_page("Inicio")
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")

    st.markdown("</div>", unsafe_allow_html=True)


def page_pickup():
    st.markdown("### 🚗 Pick Up")
    c1, c2 = st.columns([3, 2])

    with c1:
        render_menu_store("cart_pickup")

    with c2:
        total, items = render_cart("cart_pickup")
        if items:
            eta_sec = estimate_eta_seconds(items)
            mins = max(1, int(eta_sec) // 60)
            st.info(f"⏱️ Tiempo estimado (cola actual): **{mins} min**")

            note = st.text_area("Notas para tu pedido (opcional)", value="", key="pickup_note")

            st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
            do = st.button("Generar pedido y pagar", key="btn_pay_pickup")
            st.markdown("</div>", unsafe_allow_html=True)

            if do:
                pay_link = create_payment_link(total, description="Pedido Pick Up — Churrería Porfirio")
                order = {
                    "type": "PICKUP",
                    "mesa": None,
                    "items": items,
                    "note": note.strip(),
                    "totals": {"subtotal": float(total), "grand_total": float(total)},
                    "status": "RECEIVED",
                    "payment": {"method": "MP_LINK", "status": "PENDING", "url": pay_link},
                    "eta_seconds": int(eta_sec),
                    "created_at": now_cdmx().isoformat(),
                    "updated_at": now_cdmx().isoformat(),
                    "user_email": ss.usuario_actual,
                }

                oid = persist_order(order)
                if oid:
                    st.success(f"✅ Pedido creado. ID: {oid}")
                    # Rewards: 1 estrella por cada $10
                    if ss.usuario_actual:
                        stars = int(float(total) // 10)
                        if stars > 0:
                            update_points(ss.usuario_actual, stars_add=stars, detalle=f"Compra PickUp {oid} — {stars} estrellas")

                    if pay_link:
                        st.link_button("Pagar ahora", pay_link)
                    else:
                        st.info("Pago: configura Mercado Pago en secrets para link automático.")

                    ss.cart_pickup = []


def page_mesa():
    st.markdown("### 🍽️ Pedir en mesa")

    top = st.columns([2, 3])
    with top[0]:
        ss.mesa_actual = st.text_input("Número de mesa", value=ss.mesa_actual, key="mesa_num")
    with top[1]:
        st.caption("Tip: si vas a usar tablets por mesa, aquí puedes prellenar el número.")

    c1, c2 = st.columns([3, 2])

    with c1:
        render_menu_store("cart_mesa")

    with c2:
        total, items = render_cart("cart_mesa")
        if items:
            if not ss.mesa_actual.strip():
                st.warning("Ingresa el número de mesa para continuar.")
                return

            eta_sec = estimate_eta_seconds(items)
            mins = max(1, int(eta_sec) // 60)
            st.info(f"⏱️ Tiempo estimado: **{mins} min**")

            pay_mode = st.selectbox(
                "¿Cómo pagas?",
                options=["Pagar ahora (Mercado Pago)", "Pagar en caja"],
                key="mesa_pay_mode",
            )
            note = st.text_area("Notas para tu pedido (opcional)", value="", key="mesa_note")

            st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
            do = st.button("Enviar pedido", key="btn_send_mesa")
            st.markdown("</div>", unsafe_allow_html=True)

            if do:
                pay_link = None
                pay_method = "CASHIER"
                pay_status = "PENDING"

                if pay_mode.startswith("Pagar ahora"):
                    pay_link = create_payment_link(total, description=f"Pedido Mesa {ss.mesa_actual} — Churrería Porfirio")
                    pay_method = "MP_LINK"

                order = {
                    "type": "MESA",
                    "mesa": ss.mesa_actual.strip(),
                    "items": items,
                    "note": note.strip(),
                    "totals": {"subtotal": float(total), "grand_total": float(total)},
                    "status": "RECEIVED",
                    "payment": {"method": pay_method, "status": pay_status, "url": pay_link},
                    "eta_seconds": int(eta_sec),
                    "created_at": now_cdmx().isoformat(),
                    "updated_at": now_cdmx().isoformat(),
                    "user_email": ss.usuario_actual,
                }

                oid = persist_order(order)
                if oid:
                    st.success(f"✅ Pedido enviado. ID: {oid}")

                    # Rewards: 1 estrella por cada $10
                    if ss.usuario_actual:
                        stars = int(float(total) // 10)
                        if stars > 0:
                            update_points(ss.usuario_actual, stars_add=stars, detalle=f"Compra Mesa {ss.mesa_actual} {oid} — {stars} estrellas")

                    if pay_link:
                        st.link_button("Pagar ahora", pay_link)
                    else:
                        st.info("Si pagas en caja, solo muestra tu número de pedido.")

                    ss.cart_mesa = []


def page_admin():
    st.markdown("### 👑 Admin")

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Acceso</div>", unsafe_allow_html=True)
    admin_email = st.text_input("Correo de Admin", key="ad_email")
    admin_pass = st.text_input("Contraseña Admin", type="password", key="ad_pwd")

    if not is_admin_ok(admin_email, admin_pass):
        st.error("Acceso denegado.")
        st.caption("Configura admin_credentials en secrets (email/password).")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.success("Acceso autorizado")
    st.markdown("</div>", unsafe_allow_html=True)

    # KPIs del día
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>📊 Resumen del día</div>", unsafe_allow_html=True)

    # Nota: consulta por created_at string ISO. Para producción real: guarda created_date (YYYY-MM-DD)
    today_prefix = now_cdmx().date().isoformat()
    orders_today = [o.to_dict() for o in db.collection("orders").stream() if (o.to_dict() or {}).get("created_at", "").startswith(today_prefix)]

    in_queue = [o for o in orders_today if o.get("status") in ("RECEIVED", "IN_PROGRESS")]
    ready = [o for o in orders_today if o.get("status") == "READY"]
    delivered = [o for o in orders_today if o.get("status") == "DELIVERED"]
    ingreso = sum(float(o.get("totals", {}).get("grand_total", 0) or 0) for o in orders_today)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Pedidos hoy", len(orders_today))
    k2.metric("En cola", len(in_queue))
    k3.metric("Listos", len(ready))
    k4.metric("Ingresos (MXN)", money(ingreso))

    st.markdown("</div>", unsafe_allow_html=True)

    # Cola
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🧑‍🍳 Cola de pedidos</div>", unsafe_allow_html=True)

    q = db.collection("orders").where("status", "in", ["RECEIVED", "IN_PROGRESS", "READY"]).stream()
    for d in q:
        o = d.to_dict() or {}
        oid = d.id

        items_txt = []
        for it in o.get("items", []):
            mid = it.get("menu_id")
            if mid in MENU_INDEX:
                nm = MENU_INDEX[mid]["name"]
                items_txt.append(f"{nm} x{it.get('qty',1)}")
        items_str = ", ".join(items_txt) if items_txt else "(sin items)"

        cols = st.columns([2, 2, 2, 4, 2])
        with cols[0]:
            st.write(f"**{oid[:6]}**")
            st.caption(o.get("type", "") + (f" · Mesa {o.get('mesa')}" if o.get("mesa") else ""))
        with cols[1]:
            st.write(money(o.get("totals", {}).get("grand_total", 0) or 0))
        with cols[2]:
            mins = max(1, int(o.get("eta_seconds", 0) or 0) // 60)
            st.write(f"ETA: {mins} min")
        with cols[3]:
            st.write(items_str)
            if o.get("note"):
                st.caption(o.get("note"))
        with cols[4]:
            statuses = ["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"]
            cur = o.get("status", "RECEIVED")
            idx = statuses.index(cur) if cur in statuses else 0
            new_status = st.selectbox("Estado", statuses, index=idx, key=f"sel_{oid}")
            if st.button("Guardar", key=f"save_{oid}"):
                db.collection("orders").document(oid).update({"status": new_status, "updated_at": now_cdmx().isoformat()})
                st.toast("✅ Estado actualizado")
                log_action(db, "order_status", admin_email, f"{oid} -> {new_status}")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Gestión de cliente
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🎟️ Gestionar recompensas</div>", unsafe_allow_html=True)

    tipo = st.radio("Tipo", ["Estrellas (por compra)", "Helados"], horizontal=True)
    identificador_cliente = st.text_input("Correo o número del cliente", key="adm_ident")

    if st.button("Confirmar cliente", key="adm_confirm"):
        u = get_user((identificador_cliente or "").strip())
        if u:
            ss.cliente_confirmado = u.get("email")
            st.success(f"Cliente encontrado: {u.get('email','')}")
        else:
            ss.cliente_confirmado = None
            st.error("Cliente no encontrado.")

    if ss.cliente_confirmado:
        u = get_user(ss.cliente_confirmado)
        if u:
            show_user_summary(u)

            if tipo.startswith("Estrellas"):
                monto = st.number_input("Monto de compra ($MXN)", min_value=0, step=10, key="adm_monto")
                if st.button("Registrar compra", key="adm_compra"):
                    stars = int(float(monto) // 10)
                    update_points(ss.cliente_confirmado, stars_add=stars, detalle=f"Compra manual admin: ${monto} -> {stars} estrellas")
                    st.success("✅ Compra registrada")
                    st.rerun()
            else:
                cantidad = st.number_input("Cantidad de helados", min_value=1, step=1, key="adm_helados")
                if st.button("Registrar helados", key="adm_add_helados"):
                    update_points(ss.cliente_confirmado, helados_add=int(cantidad), detalle=f"Helados manual admin: +{cantidad}")
                    st.success("✅ Helados registrados")
                    st.rerun()

                st.markdown("<hr class='hr-soft' />", unsafe_allow_html=True)
                if st.button("Canjear helado (6)", key="adm_canjear"):
                    canjear_helado(ss.cliente_confirmado)
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# APP RENDER
# =========================
ui_header()
nav_bar()

# promos
show_promotions_popups()

page = get_page()

if page == "Inicio":
    page_inicio()
elif page == "Registro":
    page_registro()
elif page == "Iniciar sesión":
    page_login()
elif page == "Pick Up":
    page_pickup()
elif page == "Mesa":
    page_mesa()
elif page == "Admin":
    page_admin()
else:
    page_inicio()
