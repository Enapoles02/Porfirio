import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import uuid
import json
import streamlit.components.v1 as components

# ============================================================
# KIN HOUSE POS PRO — v3.0
# Mejoras: estética refinada, catálogo completo, editor de
# productos con adicionales/variantes dinámicos
# ============================================================

st.set_page_config(page_title="KIN House POS", layout="wide", page_icon="☀️")
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
# ESTILOS
# ---------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --cream:   #FAF7F2;
    --sand:    #EDE8DF;
    --sienna:  #C4714A;
    --gold:    #B59461;
    --espresso:#2C1A0E;
    --bark:    #5C3D2E;
    --green:   #3A7D44;
    --red:     #C0392B;
    --blue:    #2471A3;
    --white:   #FFFFFF;
    --shadow:  rgba(44,26,14,0.10);
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: var(--espresso);
}

.stApp {
    background-color: var(--cream);
    background-image: radial-gradient(circle at 20% 10%, rgba(196,113,74,0.07) 0%, transparent 50%),
                      radial-gradient(circle at 80% 90%, rgba(181,148,97,0.07) 0%, transparent 50%);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--espresso) !important;
}
section[data-testid="stSidebar"] * {
    color: var(--cream) !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {
    color: rgba(250,247,242,0.6) !important;
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stTextInput > div > div > input {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: var(--cream) !important;
    border-radius: 8px !important;
}

/* Títulos */
h1 {
    font-family: 'Playfair Display', serif !important;
    font-weight: 900 !important;
    color: var(--espresso) !important;
    letter-spacing: -0.5px;
}
h2, h3 {
    font-family: 'Playfair Display', serif !important;
    font-weight: 700 !important;
    color: var(--bark) !important;
}

/* Tarjeta mesa */
.mesa-card {
    padding: 18px 12px 14px;
    border-radius: 16px;
    text-align: center;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 6px;
    color: white;
    box-shadow: 0 6px 20px var(--shadow);
    letter-spacing: 0.2px;
    transition: transform 0.15s;
}

/* Botones */
.stButton > button {
    width: 100%;
    border-radius: 10px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    min-height: 3.2em;
    border: 1.5px solid rgba(92,61,46,0.12) !important;
    background: var(--white) !important;
    color: var(--espresso) !important;
    font-size: 12px;
    line-height: 1.3;
    transition: all 0.15s ease;
    box-shadow: 0 2px 8px var(--shadow);
}
.stButton > button:hover {
    background: var(--sienna) !important;
    color: white !important;
    border-color: var(--sienna) !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(196,113,74,0.25);
}
.stButton > button[kind="primary"] {
    background: var(--sienna) !important;
    color: white !important;
    border-color: var(--sienna) !important;
    font-size: 13px;
    letter-spacing: 0.5px;
}
.stButton > button[kind="primary"]:hover {
    background: var(--bark) !important;
    border-color: var(--bark) !important;
}

/* Ticket box */
.ticket-box {
    background: var(--white);
    border-radius: 18px;
    padding: 18px 16px;
    border: 1px solid rgba(92,61,46,0.10);
    box-shadow: 0 8px 28px var(--shadow);
    position: sticky;
    top: 1rem;
}

/* Sección de catálogo */
.section-pill {
    display: inline-block;
    background: var(--sienna);
    color: white;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin: 14px 0 10px;
}

/* KPI cards */
.kpi-wrap {
    background: var(--white);
    border-radius: 16px;
    padding: 18px 20px;
    border: 1px solid rgba(92,61,46,0.08);
    box-shadow: 0 4px 16px var(--shadow);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: var(--sand);
    padding: 6px;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    padding: 8px 14px;
    border: none !important;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 13px;
    color: var(--bark);
}
.stTabs [aria-selected="true"] {
    background: var(--white) !important;
    color: var(--sienna) !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px var(--shadow);
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 10px !important;
    border: 1.5px solid rgba(92,61,46,0.15) !important;
    background: var(--white) !important;
}

/* Divider */
hr {
    border-color: rgba(92,61,46,0.10) !important;
}

/* Logo sidebar */
.sidebar-logo {
    text-align: center;
    padding: 20px 0 10px;
}
.sidebar-logo .brand-name {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 900;
    color: var(--cream);
    letter-spacing: 1px;
}
.sidebar-logo .brand-slogan {
    font-size: 11px;
    color: rgba(250,247,242,0.55);
    letter-spacing: 0.5px;
}

/* Product button label */
.prod-name { font-weight: 600; font-size: 12px; }
.prod-price { font-size: 11px; color: var(--sienna); }

/* Item row en ticket */
.item-name { font-size: 13px; font-weight: 500; line-height: 1.3; }
.item-price { font-size: 12px; color: var(--bark); }
</style>
""", unsafe_allow_html=True)


def init_firebase():
    try:
        if not firebase_admin._apps:
            creds_obj = st.secrets["firebase_credentials"]
            fb_creds = creds_obj.to_dict() if hasattr(creds_obj, "to_dict") else dict(creds_obj)
            cred = credentials.Certificate(fb_creds)

            firebase_admin.initialize_app(cred, {
                "storageBucket": st.secrets["firebase_credentials"]["firebase_storage_bucket"]
            })
        return firestore.client()
    except Exception as e:
        st.error(f"Error al inicializar Firebase: {e}")
        st.stop()


db = init_firebase()
bucket = storage.bucket(name=st.secrets["firebase_credentials"]["firebase_storage_bucket"])


# ---------------------------
# DATA HELPERS
# ---------------------------
def upload_logo_to_storage(file_bytes: bytes, filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else "png"
    content_type = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"

    blob = bucket.blob(f"branding/{uuid.uuid4()}.{ext}")
    blob.upload_from_string(file_bytes, content_type=content_type)
    blob.make_public()
    return blob.public_url


def get_brand() -> dict:
    try:
        doc = db.collection("config").document("branding").get()
        if doc.exists:
            data = doc.to_dict() or {}
            return {
                "logo_url": data.get("logo_url", ""),
                "nombre": data.get("nombre", "KIN House"),
                "slogan": data.get("slogan", "Mismo sabor, mismo lugar"),
            }
    except Exception:
        pass
    return {"logo_url": "", "nombre": "KIN House", "slogan": "Mismo sabor, mismo lugar"}


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
# CATÁLOGO — HELPERS FIRESTORE
# ---------------------------
def get_catalog_from_db() -> dict:
    """Lee el catálogo desde Firestore. Si no existe, siembra el catálogo base."""
    try:
        doc = db.collection("config").document("catalog").get()
        if doc.exists:
            return doc.to_dict() or {}
    except Exception:
        pass
    return {}


def save_catalog_to_db(catalog: dict):
    db.collection("config").document("catalog").set(catalog)


# ---------------------------
# CATÁLOGO BASE (semilla — precios del menú oficial KIN House)
# Fuente: menú impreso 2025
# ---------------------------
_LECHE_EXTRAS = [
    {"label": "Leche deslactosada", "price": 10},
    {"label": "Leche vegetal", "price": 10},
    {"label": "Leche light", "price": 10},
    {"label": "Jarabe / polvo extra", "price": 10},
    {"label": "Shot extra", "price": 12},
]
_SALSA_EXTRAS = [
    {"label": "Salsa verde", "price": 0},
    {"label": "Salsa roja", "price": 0},
]
_COMBO_DESAYUNO_EXTRA = 34   # Individual → Combo (+café y jugo/fruta)
_COMBO_SANDWICH_EXTRA = 50   # Individual → Combo (+papas y limonada)
_COMBO_BURGER_EXTRA   = 40

DEFAULT_CATALOG = {
    # ══════════════════════════════════════════════════
    # CHURROS & ANTOJOS
    # ══════════════════════════════════════════════════
    "🥐 Churros & Antojos": {

        "Churros Tradicionales": [
            {
                "name": "Churro Tradicional 1 pza", "base": 49,
                "description": "Churro clásico recién hecho",
                "variants": [{"label": "1 pieza", "extra": 0}],
                "extras": []
            },
            {
                "name": "Churros Tradicionales 3 pzas", "base": 79,
                "description": "",
                "variants": [{"label": "3 piezas", "extra": 0}],
                "extras": []
            },
            {
                "name": "Churros Tradicionales 3 pzas (bolsa)", "base": 149,
                "description": "Presentación en bolsa KIN · aprox 3 pzas grandes",
                "variants": [{"label": "Bolsa", "extra": 0}],
                "extras": []
            },
        ],

        "Churros Rellenos": [
            {
                "name": "Churro Relleno 1 pza", "base": 35,
                "description": "Relleno al gusto",
                "variants": [{"label": "1 pieza", "extra": 0}],
                "flavors": ["Cajeta", "Nutella", "Crema de avellana", "Temporada"],
                "extras": []
            },
            {
                "name": "Churros Rellenos 3 pzas", "base": 99,
                "description": "Rellenos al gusto",
                "variants": [{"label": "3 piezas", "extra": 0}],
                "flavors": ["Cajeta", "Nutella", "Crema de avellana", "Temporada"],
                "extras": []
            },
        ],

        "Churros Minis": [
            {
                "name": "Churros Minis", "base": 79,
                "description": "15 piezas en vaso KIN",
                "variants": [{"label": "15 piezas", "extra": 0}],
                "extras": []
            },
        ],

        "Antojos": [
            {
                "name": "Apapacho", "base": 75,
                "description": "1 pieza — dona rellena con crema",
                "variants": [{"label": "1 pieza", "extra": 0}],
                "extras": []
            },
            {
                "name": "Relleno de Dona", "base": 39,
                "description": "3 piezas mini de dona rellena",
                "variants": [{"label": "3 piezas", "extra": 0}],
                "extras": []
            },
            {
                "name": "Waffle", "base": 45,
                "description": "1 topping incluido · +$15 añade helado",
                "variants": [
                    {"label": "Solo (1 topping)", "extra": 0},
                    {"label": "Con helado (+$15)", "extra": 15},
                ],
                "extras": []
            },
            {
                "name": "Fresas con Crema", "base": 75,
                "description": "Con topping",
                "variants": [
                    {"label": "14 oz", "extra": 0},
                    {"label": "16 oz", "extra": 10},
                ],
                "extras": []
            },
        ],
    },

    # ══════════════════════════════════════════════════
    # BEBIDAS
    # ══════════════════════════════════════════════════
    "☕ Bebidas": {

        "Cafetería": [
            {
                "name": "Espresso", "base": 39,
                "description": "",
                "variants": [
                    {"label": "Sencillo", "extra": 0},
                    {"label": "Doble", "extra": 10},
                ],
                "extras": []
            },
            {
                "name": "Capuccino", "base": 65,
                "description": "Chico 12oz / Grande 14oz",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Latte", "base": 65,
                "description": "Chico 12oz / Grande 14oz",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Malteada", "base": 99,
                "description": "Normal 12oz · Special (espesa) 14oz",
                "variants": [
                    {"label": "Normal 12oz", "extra": 0},
                    {"label": "Special espesa 14oz", "extra": 16},
                ],
                "extras": []
            },
            {
                "name": "Frappé", "base": 65,
                "description": "Oreo, Chai, Chocolate, Horchata, Matcha y más · Crea tu bebida con jarabes/polvos +$10",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "flavors": ["Oreo", "Chai", "Chocolate", "Horchata", "Matcha", "Café", "Taro", "Cookies", "Temporada"],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Granizado", "base": 65,
                "description": "Fresa, Mango, Maracuyá, Mora Azul, Frutos rojos y más",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "flavors": ["Fresa", "Mango", "Maracuyá", "Mora Azul", "Frutos rojos", "Temporada"],
                "extras": [
                    {"label": "Con chamoy", "price": 0},
                    {"label": "Con chile", "price": 0},
                ]
            },
            {
                "name": "Limonada", "base": 55,
                "description": "Chico 12oz / Grande 14oz",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "flavors": ["Natural", "Jamaica", "Menta", "Fresa"],
                "extras": []
            },
            {
                "name": "Refresco / Agua Mineral", "base": 55,
                "description": "",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Grande", "extra": 10},
                ],
                "extras": []
            },
            {
                "name": "Agua Natural Embotellada", "base": 30,
                "description": "",
                "variants": [{"label": "500ml", "extra": 0}],
                "extras": []
            },
        ],

        "Signature ☕❄️": [
            {
                "name": "Chocolate", "base": 79,
                "description": "Caliente o frío · Signature KIN",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "flavors": ["Suizo", "Semi Amargo", "Mexicano"],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Mocha Nat / Blanco", "base": 79,
                "description": "Caliente o frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Caramel Macchiato", "base": 79,
                "description": "Caliente o frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Refresher's", "base": 69,
                "description": "Siempre frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "flavors": ["Mango", "Mora Azul", "Fresa"],
                "extras": []
            },
            {
                "name": "Temporada", "base": 79,
                "description": "Bebida de temporada KIN · Caliente o frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Té Chai", "base": 79,
                "description": "Caliente o frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Matcha", "base": 79,
                "description": "Caliente o frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
            {
                "name": "Taro", "base": 79,
                "description": "Caliente o frío",
                "variants": [
                    {"label": "Chico 12oz", "extra": 0},
                    {"label": "Grande 14oz", "extra": 10},
                ],
                "extras": _LECHE_EXTRAS
            },
        ],
    },

    # ══════════════════════════════════════════════════
    # COMIDA
    # ══════════════════════════════════════════════════
    "🍔 Comida": {

        "Smash Burger": [
            {
                "name": "Smash Burger Clásica", "base": 99,
                "description": "Hamburguesa 100% de res · aderezo de la casa",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_BURGER_EXTRA},
                ],
                "extras": []
            },
            {
                "name": "Smash Burger Doble ⭐", "base": 129,
                "description": "Doble carne 100% de res",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_BURGER_EXTRA},
                ],
                "extras": []
            },
            {
                "name": "Smash Burger Triple", "base": 159,
                "description": "Triple carne 100% de res",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_BURGER_EXTRA},
                ],
                "extras": []
            },
        ],

        "Emparedados KIN": [
            {
                "name": "Clásico", "base": 85,
                "description": "Jamón y queso",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_SANDWICH_EXTRA},
                ],
                "extras": []
            },
            {
                "name": "Ratatouille ⭐", "base": 95,
                "description": "Tres quesos fundidos",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_SANDWICH_EXTRA},
                ],
                "extras": []
            },
            {
                "name": "Pamplona ⭐", "base": 95,
                "description": "Salami + chorizo + jamón + queso",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_SANDWICH_EXTRA},
                ],
                "extras": []
            },
            {
                "name": "Napoli", "base": 105,
                "description": "Pollo + queso + salsa de ajo",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_SANDWICH_EXTRA},
                ],
                "extras": []
            },
            {
                "name": "Toscano", "base": 105,
                "description": "Pollo + boloñesa + parmesano",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ papas y limonada)", "extra": _COMBO_SANDWICH_EXTRA},
                ],
                "extras": []
            },
        ],
    },

    # ══════════════════════════════════════════════════
    # DESAYUNOS  —  TODO EL DÍA 8AM-10PM
    # ══════════════════════════════════════════════════
    "🍳 Desayunos": {

        "Clásicos Mexicanos": [
            {
                "name": "Chilaquiles ⭐", "base": 95,
                "description": "Rojos o verdes · incluyen pollo · Combo: + café y jugo o fruta",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": 44},
                ],
                "extras": _SALSA_EXTRAS + [{"label": "3 pzas Hotcakes o Waffle (+$45)", "price": 45}]
            },
            {
                "name": "Enchiladas", "base": 95,
                "description": "Rojas o verdes · incluyen pollo",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": 34},
                ],
                "extras": _SALSA_EXTRAS + [{"label": "3 pzas Hotcakes o Waffle (+$45)", "price": 45}]
            },
            {
                "name": "Enfrijoladas", "base": 95,
                "description": "Incluyen pollo",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": 34},
                ],
                "extras": [{"label": "3 pzas Hotcakes o Waffle (+$45)", "price": 45}]
            },
            {
                "name": "Molletes", "base": 75,
                "description": "",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": 24},
                ],
                "extras": _SALSA_EXTRAS + [
                    {"label": "Pico de gallo", "price": 0},
                    {"label": "3 pzas Hotcakes o Waffle (+$45)", "price": 45},
                ]
            },
            {
                "name": "Huevos al gusto", "base": 95,
                "description": "",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": 34},
                ],
                "flavors": ["Estrellados", "Revueltos", "A la mexicana", "Con jamón", "Con chorizo", "Con tocino"],
                "extras": _SALSA_EXTRAS + [{"label": "3 pzas Hotcakes o Waffle (+$45)", "price": 45}]
            },
            {
                "name": "Sincronizadas", "base": 75,
                "description": "",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": 24},
                ],
                "extras": _SALSA_EXTRAS + [{"label": "3 pzas Hotcakes o Waffle (+$45)", "price": 45}]
            },
        ],

        "American Break": [
            {
                "name": "Hot Cakes & Huevos al gusto ⭐", "base": 95,
                "description": "Fuera de México · Todo el día · +3 hotcakes o waffle por $45",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": _COMBO_DESAYUNO_EXTRA},
                ],
                "flavors": ["Huevos estrellados", "Huevos revueltos", "Huevos a la mexicana"],
                "extras": [
                    {"label": "Mazapán", "price": 0},
                    {"label": "Cajeta", "price": 0},
                    {"label": "Lechera", "price": 0},
                    {"label": "Nutella", "price": 0},
                    {"label": "Frutos rojos", "price": 0},
                    {"label": "3 pzas Hotcakes o Waffle extra (+$45)", "price": 45},
                ]
            },
            {
                "name": "Waffles & Huevos al gusto", "base": 95,
                "description": "Fuera de México · Todo el día",
                "variants": [
                    {"label": "Individual", "extra": 0},
                    {"label": "Combo (+ café y jugo o fruta)", "extra": _COMBO_DESAYUNO_EXTRA},
                ],
                "flavors": ["Huevos estrellados", "Huevos revueltos", "Huevos a la mexicana"],
                "extras": [
                    {"label": "3 pzas Hotcakes o Waffle extra (+$45)", "price": 45},
                ]
            },
        ],
    },

    # ══════════════════════════════════════════════════
    # MENÚ SECRETO
    # ══════════════════════════════════════════════════
    "🤫 Menú Secreto": {
        "Martes": [
            {
                "name": "Beignets de la Casa", "base": 79,
                "description": "Solo martes · Sujeto a disponibilidad · Con salsa cajeta",
                "variants": [{"label": "Porción", "extra": 0}],
                "extras": []
            },
        ],
    },
}


@st.cache_data(ttl=30)
def get_catalog() -> dict:
    db_cat = get_catalog_from_db()
    if db_cat:
        return db_cat
    return DEFAULT_CATALOG


def infer_price_from_variant(base: float, variant: dict) -> float:
    return float(base) + float(variant.get("extra", 0))


# ---------------------------
# DIALOG: AGREGAR PRODUCTO AL TICKET
# ---------------------------
@st.dialog("Personalizar pedido")
def option_dialog():
    payload = st.session_state.get("dialog_payload")
    if not payload:
        st.warning("No hay producto seleccionado.")
        return

    prod = payload["prod"]
    doc_id = payload["doc_id"]

    base = float(prod.get("base", 0))
    variants = prod.get("variants", [])
    flavors = prod.get("flavors", [])
    extras = prod.get("extras", [])
    description = prod.get("description", "")

    st.markdown(f"### {prod['name']}")
    if description:
        st.caption(description)

    order = load_order(doc_id)
    items = order.get("items", [])

    # Variant
    variant_labels = [v.get("label", "") for v in variants]
    if len(variants) > 1:
        selected_var_label = st.selectbox("Tamaño / tipo", variant_labels)
    elif variant_labels:
        selected_var_label = variant_labels[0]
        st.caption(f"Variante: {selected_var_label}")
    else:
        selected_var_label = "Único"

    selected_var = next((v for v in variants if v.get("label") == selected_var_label), {"label": selected_var_label, "extra": 0})
    running_price = infer_price_from_variant(base, selected_var)

    # Flavor
    selected_flavor = None
    if flavors:
        selected_flavor = st.selectbox("Sabor / variante", flavors)

    # Extras
    selected_extras = []
    extra_total = 0.0
    if extras:
        st.markdown("**Adicionales**")
        ecols = st.columns(2)
        for i, ex in enumerate(extras):
            lbl = ex.get("label", "")
            price_ex = float(ex.get("price", 0))
            suffix = f" (+{money(price_ex)})" if price_ex > 0 else ""
            if ecols[i % 2].checkbox(f"{lbl}{suffix}", key=f"ex_{prod['name']}_{i}"):
                selected_extras.append(lbl)
                extra_total += price_ex

    final_price = running_price + extra_total

    # Quantity
    qty = st.number_input("Cantidad", min_value=1, max_value=20, value=1, step=1)

    st.markdown(f"**Total: {money(final_price * qty)}**")

    c1, c2 = st.columns(2)
    if c1.button("➕ Agregar", type="primary", use_container_width=True):
        parts = [prod["name"], selected_var_label]
        if selected_flavor:
            parts.append(selected_flavor)
        if selected_extras:
            parts.extend(selected_extras)
        item_name = " · ".join([p for p in parts if p and p != "Único"])

        items.append({
            "n": item_name,
            "p": final_price,
            "q": qty,
            "added_at": now_iso(),
        })
        total = calc_total(items)
        update_order(doc_id, items, total)
        st.session_state.dialog_payload = None
        st.rerun()

    if c2.button("Cancelar", use_container_width=True):
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


def add_dialog_request(prod: dict, doc_id: str):
    st.session_state.dialog_payload = {"prod": prod, "doc_id": doc_id}
    option_dialog()


def close_ticket_session():
    st.session_state.cid = None
    st.session_state.enom = None
    st.session_state.dialog_payload = None


# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    if brand.get("logo_url"):
        st.markdown(f'<div class="sidebar-logo"><img src="{brand["logo_url"]}" style="width:80px;border-radius:12px;margin-bottom:10px;"></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="sidebar-logo"><div class="brand-name">{brand.get("nombre","KIN House")}</div><div class="brand-slogan">{brand.get("slogan","Mismo sabor, mismo lugar")}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    menu_nav = st.selectbox("NAVEGACIÓN", ["🪑 Mesas", "💵 Caja", "📊 Reporte", "🛒 Catálogo", "⚙️ Config"])
    st.markdown("---")
    admin_pin = st.text_input("PIN Admin", type="password")
    is_admin = admin_pin == get_admin_pin()
    if is_admin:
        st.success("✓ Admin activo")


# ============================================================
# VIEW: MESAS
# ============================================================
if menu_nav == "🪑 Mesas":
    st.title("☀️ Mesas")
    cashbox = get_open_cashbox()

    if not cashbox:
        st.error("🛑 No hay caja abierta. Ve a **Caja** para abrir turno.")
        st.stop()

    spaces = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar"]
    open_orders = get_open_orders_by_space()

    cols = st.columns(4)
    for i, space in enumerate(spaces):
        with cols[i % 4]:
            occupied = space in open_orders
            bg = "#C0392B" if occupied else "#3A7D44"
            badge = "● OCUPADO" if occupied else "○ LIBRE"
            st.markdown(
                f'<div class="mesa-card" style="background:{bg};">'
                f'<div style="font-size:11px;opacity:0.75;letter-spacing:1px;">{badge}</div>'
                f'<div style="font-size:15px;margin-top:4px;">{space}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button("Abrir / Ver", key=f"space_{space}"):
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

        catalog = get_catalog()
        col_menu, col_ticket = st.columns([2.3, 1])

        with col_menu:
            tabs = st.tabs(list(catalog.keys()))
            for tab_index, tab_name in enumerate(catalog.keys()):
                with tabs[tab_index]:
                    sections = catalog[tab_name]
                    for section_name, products in sections.items():
                        st.markdown(f'<span class="section-pill">{section_name}</span>', unsafe_allow_html=True)
                        chunk = 3
                        for start in range(0, len(products), chunk):
                            row = products[start:start + chunk]
                            rcols = st.columns(len(row))
                            for j, prod in enumerate(row):
                                label = f"{prod['name']}\n{money(prod['base'])}"
                                if rcols[j].button(label, key=f"p_{tab_name}_{section_name}_{prod['name']}_{start+j}"):
                                    add_dialog_request(prod, st.session_state.cid)

        with col_ticket:
            st.markdown('<div class="ticket-box">', unsafe_allow_html=True)
            st.markdown("### 🧾 Ticket")

            if not order_items:
                st.info("Aún no hay productos.")
            else:
                for idx, item in enumerate(order_items):
                    left, mid, right = st.columns([4, 1.5, 1])
                    left.markdown(f'<div class="item-name">{item.get("n","Producto")}</div>', unsafe_allow_html=True)
                    qty = int(item.get("q", 1))
                    unit_p = float(item.get("p", 0))
                    mid.markdown(f'<div class="item-price">x{qty} · {money(unit_p * qty)}</div>', unsafe_allow_html=True)
                    if right.button("✕", key=f"rm_{idx}"):
                        order_items.pop(idx)
                        update_order(st.session_state.cid, order_items, calc_total(order_items))
                        st.rerun()

                st.divider()

            st.subheader(f"Total: {money(order_total)}")

            payment_method = st.selectbox("Pago", ["Efectivo", "Tarjeta", "Transferencia"])
            cash_received = 0.0
            if payment_method == "Efectivo":
                cash_received = st.number_input("Recibido $", min_value=0.0, step=10.0)
                change = max(cash_received - order_total, 0)
                st.caption(f"💰 Cambio: **{money(change)}**")

            can_charge = order_total > 0 and (payment_method != "Efectivo" or cash_received >= order_total)
            sale_note = st.text_input("Nota (opcional)")

            if st.button("✅ COBRAR", type="primary", disabled=not can_charge):
                folio = build_sale_folio()
                sale_doc = {
                    "folio": folio,
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

                logo_src = brand.get("logo_url", "")
                items_html = "".join([
                    f"<tr><td>{x.get('n','')}</td><td align='center'>{x.get('q',1)}</td><td align='right'>${float(x.get('p',0))*int(x.get('q',1)):,.0f}</td></tr>"
                    for x in order_items
                ])
                recibido_html = f"<div>RECIBIDO: {money(cash_received)}</div><div>CAMBIO: {money(cash_received - order_total)}</div>" if payment_method == "Efectivo" else ""

                ticket_html = f"""
                <div id="tkt" style="width:280px;font-family:monospace;font-size:12px;color:#000;padding:12px;background:#fff;">
                    <center>
                        {f'<img src="{logo_src}" width="80"><br>' if logo_src else ''}
                        <b>{brand.get('nombre','KIN House')}</b><br>
                        {brand.get('slogan','')}<br>
                        {now_cdmx().strftime('%d/%m/%Y %H:%M')}<br>
                        Folio: {folio}<br>
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
                    <br><center>¡Gracias por tu visita!</center>
                </div>
                <script>window.print();</script>
                """
                components.html(ticket_html, height=0)

                db.collection("comandas").document(st.session_state.cid).update({
                    "estado": "CERRADA",
                    "closed_at": now_iso(),
                    "venta_folio": folio,
                    "total": order_total,
                })
                close_ticket_session()
                st.success(f"✅ Venta registrada: {folio}")
                st.rerun()

            if st.button("↩ Salir sin cerrar"):
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
        st.markdown("#### Abrir nuevo turno")
        c1, c2 = st.columns(2)
        initial_fund = c1.number_input("Fondo inicial", min_value=0.0, step=100.0)
        cash_user = c2.text_input("Nombre del cajero")
        if st.button("ABRIR CAJA", type="primary"):
            if not cash_user.strip():
                st.warning("Ingresa el nombre del cajero.")
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

        with st.expander("🧾 Movimientos del turno", expanded=True):
            if sales:
                df_sales = pd.DataFrame(sales)
                show = [c for c in ["fecha", "folio", "mesa", "total", "metodo", "nota"] if c in df_sales.columns]
                st.markdown("**Ventas**")
                st.dataframe(df_sales[show], use_container_width=True, hide_index=True)
            else:
                st.info("Sin ventas en este turno.")
            if expenses:
                df_exp = pd.DataFrame(expenses)
                show = [c for c in ["fecha", "motivo", "monto"] if c in df_exp.columns]
                st.markdown("**Egresos**")
                st.dataframe(df_exp[show], use_container_width=True, hide_index=True)

        counted_cash = st.number_input("Efectivo contado al cierre", min_value=0.0, step=10.0)
        diff = counted_cash - expected_cash
        st.caption(f"Diferencia: {money(diff)}")

        if st.button("🔒 CERRAR TURNO", type="primary"):
            db.collection("cajas").document(cashbox["id"]).update({
                "estado": "CERRADA",
                "cierre": now_iso(),
                "efectivo_esperado": expected_cash,
                "efectivo_contado": counted_cash,
                "diferencia": diff,
            })
            close_ticket_session()
            st.success("Turno cerrado correctamente.")
            st.rerun()


# ============================================================
# VIEW: CATÁLOGO — EDITOR DE PRODUCTOS
# ============================================================
elif menu_nav == "🛒 Catálogo":
    st.title("🛒 Catálogo de Productos")

    if not is_admin:
        st.warning("🔒 Ingresa el PIN de admin para editar el catálogo.")
        st.stop()

    catalog = get_catalog()

    # ---- SELECC. CATEGORÍA / SECCIÓN ----
    cat_keys = list(catalog.keys())
    st.markdown("### Seleccionar categoría y sección")
    cc1, cc2 = st.columns(2)
    sel_cat = cc1.selectbox("Categoría", cat_keys + ["➕ Nueva categoría"])
    
    if sel_cat == "➕ Nueva categoría":
        new_cat_name = cc2.text_input("Nombre de nueva categoría")
        if st.button("Crear categoría") and new_cat_name.strip():
            catalog[new_cat_name.strip()] = {}
            save_catalog_to_db(catalog)
            get_catalog.clear()
            st.success(f"Categoría '{new_cat_name.strip()}' creada.")
            st.rerun()
        st.stop()

    sections = catalog[sel_cat]
    sec_keys = list(sections.keys())
    sel_sec = cc1.selectbox("Sección", sec_keys + ["➕ Nueva sección"])

    if sel_sec == "➕ Nueva sección":
        new_sec_name = cc2.text_input("Nombre de nueva sección")
        if st.button("Crear sección") and new_sec_name.strip():
            catalog[sel_cat][new_sec_name.strip()] = []
            save_catalog_to_db(catalog)
            get_catalog.clear()
            st.success(f"Sección '{new_sec_name.strip()}' creada.")
            st.rerun()
        st.stop()

    products = sections[sel_sec]

    st.divider()

    # ---- LISTADO DE PRODUCTOS ----
    st.markdown(f"### Productos en **{sel_cat} › {sel_sec}**")

    st.markdown(f"### Productos en **{sel_cat} › {sel_sec}**")

    for idx, prod in enumerate(products):
        if not isinstance(prod, dict):
            st.error(f"Producto inválido en índice {idx}: {prod}")
            continue
    
        with st.expander(
            f"{'🟢' if prod.get('active', True) else '🔴'}  "
            f"{prod.get('name', 'Sin nombre')}  —  "
            f"{money(prod.get('base', 0))}"
        ):
            with st.form(key=f"edit_prod_{idx}"):
                pname = st.text_input("Nombre del producto", value=prod.get("name", ""), key=f"pn_{idx}")
                pcols = st.columns(2)
                pbase = pcols[0].number_input("Precio base $", value=float(prod.get("base", 0)), step=1.0, key=f"pb_{idx}")
                pdesc = pcols[1].text_input("Descripción corta (opcional)", value=prod.get("description", ""), key=f"pd_{idx}")

                st.markdown("**Variantes** *(tamaños, tipos)*")
                variants = prod.get("variants", [{"label": "Único", "extra": 0}])
                new_variants = []
                for vi, vr in enumerate(variants):
                    vc1, vc2, vc3 = st.columns([3, 1.5, 0.5])
                    vlbl = vc1.text_input("Etiqueta", value=vr.get("label", ""), key=f"vlbl_{idx}_{vi}")
                    vext = vc2.number_input("Extra $", value=float(vr.get("extra", 0)), step=1.0, key=f"vext_{idx}_{vi}")
                    keep = vc3.checkbox("✓", value=True, key=f"vkp_{idx}_{vi}")
                    if keep and vlbl.strip():
                        new_variants.append({"label": vlbl.strip(), "extra": vext})
                new_var_lbl = st.text_input("+ Nueva variante (etiqueta)", key=f"nvlbl_{idx}")
                new_var_ext = st.number_input("+ Nueva variante (extra $)", step=1.0, key=f"nvext_{idx}")

                st.markdown("**Sabores / opciones de selección** *(ej: salsa verde, sabor Taro)*")
                flavors = prod.get("flavors", [])
                flavors_raw = st.text_area("Sabores separados por coma", value=", ".join(flavors), key=f"flv_{idx}")

                st.markdown("**Adicionales** *(checkbox al ordenar)*")
                extras = prod.get("extras", [])
                new_extras = []
                for ei, ex in enumerate(extras):
                    ec1, ec2, ec3 = st.columns([3, 1.5, 0.5])
                    elbl = ec1.text_input("Adicional", value=ex.get("label", ""), key=f"elbl_{idx}_{ei}")
                    eprice = ec2.number_input("Precio $", value=float(ex.get("price", 0)), step=1.0, key=f"ep_{idx}_{ei}")
                    ekeep = ec3.checkbox("✓", value=True, key=f"ekp_{idx}_{ei}")
                    if ekeep and elbl.strip():
                        new_extras.append({"label": elbl.strip(), "price": eprice})
                new_ex_lbl = st.text_input("+ Nuevo adicional (nombre)", key=f"nelbl_{idx}")
                new_ex_price = st.number_input("+ Nuevo adicional (precio $)", step=1.0, key=f"nep_{idx}")

                sf1, sf2 = st.columns(2)
                if sf1.form_submit_button("💾 Guardar cambios", type="primary"):
                    if new_var_lbl.strip():
                        new_variants.append({"label": new_var_lbl.strip(), "extra": new_var_ext})
                    if new_ex_lbl.strip():
                        new_extras.append({"label": new_ex_lbl.strip(), "price": new_ex_price})
                    parsed_flavors = [f.strip() for f in flavors_raw.split(",") if f.strip()]
                    updated = {
                        "name": pname.strip(),
                        "base": pbase,
                        "description": pdesc.strip(),
                        "variants": new_variants if new_variants else [{"label": "Único", "extra": 0}],
                        "flavors": parsed_flavors,
                        "extras": new_extras,
                        "active": True,
                    }
                    catalog[sel_cat][sel_sec][idx] = updated
                    save_catalog_to_db(catalog)
                    get_catalog.clear()
                    st.success("Producto actualizado.")
                    st.rerun()

                if sf2.form_submit_button("🗑️ Eliminar producto"):
                    catalog[sel_cat][sel_sec].pop(idx)
                    save_catalog_to_db(catalog)
                    get_catalog.clear()
                    st.warning("Producto eliminado.")
                    st.rerun()

    # ---- AGREGAR PRODUCTO NUEVO ----
    st.divider()
    st.markdown("### ➕ Agregar nuevo producto")

    with st.form("new_prod_form"):
        np_cols = st.columns(2)
        np_name = np_cols[0].text_input("Nombre del producto *")
        np_base = np_cols[1].number_input("Precio base $", min_value=0.0, step=1.0)
        np_desc = st.text_input("Descripción corta (opcional)")

        st.markdown("**Variantes** *(separa con | · incluye el extra en $)*")
        np_variants_raw = st.text_area(
            "Ej: Chico|0, Grande|10, Combo|45",
            placeholder="Etiqueta|extra$, Etiqueta|extra$"
        )

        np_flavors_raw = st.text_input("Sabores / opciones (separados por coma)", placeholder="Salsa verde, Salsa roja, Sin salsa")
        np_extras_raw = st.text_area("Adicionales (nombre|precio, separados por coma)", placeholder="Leche deslactosada|10, Shot extra|12")

        if st.form_submit_button("➕ Agregar producto", type="primary"):
            if not np_name.strip():
                st.warning("El nombre es obligatorio.")
            else:
                parsed_variants = []
                for part in np_variants_raw.split(","):
                    part = part.strip()
                    if "|" in part:
                        lbl, ext = part.split("|", 1)
                        try:
                            parsed_variants.append({"label": lbl.strip(), "extra": float(ext.strip())})
                        except ValueError:
                            parsed_variants.append({"label": lbl.strip(), "extra": 0})
                    elif part:
                        parsed_variants.append({"label": part, "extra": 0})
                if not parsed_variants:
                    parsed_variants = [{"label": "Único", "extra": 0}]

                parsed_flavors = [f.strip() for f in np_flavors_raw.split(",") if f.strip()]

                parsed_extras = []
                for part in np_extras_raw.split(","):
                    part = part.strip()
                    if "|" in part:
                        lbl, price = part.split("|", 1)
                        try:
                            parsed_extras.append({"label": lbl.strip(), "price": float(price.strip())})
                        except ValueError:
                            parsed_extras.append({"label": lbl.strip(), "price": 0})
                    elif part:
                        parsed_extras.append({"label": part, "price": 0})

                new_prod = {
                    "name": np_name.strip(),
                    "base": np_base,
                    "description": np_desc.strip(),
                    "variants": parsed_variants,
                    "flavors": parsed_flavors,
                    "extras": parsed_extras,
                    "active": True,
                }
                catalog[sel_cat][sel_sec].append(new_prod)
                save_catalog_to_db(catalog)
                get_catalog.clear()
                st.success(f"Producto '{np_name.strip()}' agregado correctamente.")
                st.rerun()

    # ---- EXPORTAR / IMPORTAR JSON ----
    st.divider()
    with st.expander("🔧 Exportar / importar catálogo completo (JSON)"):
        st.download_button(
            "⬇️ Descargar catálogo JSON",
            data=json.dumps(catalog, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"kin_catalog_{now_cdmx().strftime('%Y%m%d')}.json",
            mime="application/json",
        )
        uploaded_json = st.file_uploader("Subir catálogo JSON", type=["json"])
        if uploaded_json and st.button("Importar catálogo"):
            try:
                new_cat = json.loads(uploaded_json.read().decode("utf-8"))
                save_catalog_to_db(new_cat)
                get_catalog.clear()
                st.success("Catálogo importado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al importar: {e}")


# ============================================================
# VIEW: REPORTE
# ============================================================
elif menu_nav == "📊 Reporte":
    st.title("📊 Reporte")

    if not is_admin:
        st.warning("🔒 Ingresa el PIN de admin para ver reportes.")
        st.stop()

    sales_docs = list(db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).limit(500).stream())
    rows = [x.to_dict() for x in sales_docs]

    if not rows:
        st.info("No hay ventas registradas aún.")
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
    method_filter = f1.multiselect("Método de pago", methods, default=methods)
    space_filter = f2.multiselect("Mesa / espacio", spaces, default=spaces)
    day_filter = f3.selectbox("Día", ["Todos"] + sorted(df["dia"].dropna().unique().tolist(), reverse=True))

    filtered = df.copy()
    if method_filter:
        filtered = filtered[filtered["metodo"].isin(method_filter)]
    if space_filter:
        filtered = filtered[filtered["mesa"].isin(space_filter)]
    if day_filter != "Todos":
        filtered = filtered[filtered["dia"] == day_filter]

    total_sales = float(filtered["total"].sum()) if "total" in filtered.columns else 0
    total_tickets = len(filtered)
    avg_ticket = total_sales / total_tickets if total_tickets else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Ventas totales", money(total_sales))
    k2.metric("🧾 Tickets", f"{total_tickets:,}")
    k3.metric("📊 Ticket promedio", money(avg_ticket))

    st.divider()

    if "metodo" in filtered.columns:
        pay_summary = filtered.groupby("metodo", as_index=False)["total"].sum().sort_values("total", ascending=False)
        st.markdown("**Por método de pago**")
        st.dataframe(pay_summary, use_container_width=True, hide_index=True)

    if "mesa" in filtered.columns:
        space_summary = filtered.groupby("mesa", as_index=False)["total"].sum().sort_values("total", ascending=False)
        st.markdown("**Por mesa / espacio**")
        st.dataframe(space_summary, use_container_width=True, hide_index=True)

    show_cols = [c for c in ["fecha", "folio", "mesa", "total", "metodo", "nota"] if c in filtered.columns]
    st.markdown("**Detalle de ventas**")
    st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Descargar CSV", data=csv, file_name=f"kin_report_{now_cdmx().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")


# ============================================================
# VIEW: CONFIG
# ============================================================
elif menu_nav == "⚙️ Config":
    st.title("⚙️ Configuración")

    if not is_admin:
        st.warning("🔒 Ingresa el PIN de admin para modificar la configuración.")
        st.stop()

    # ---- SECCIÓN LOGO ----
    st.markdown("### 🖼️ Logo del negocio")

    col_logo_preview, col_logo_upload = st.columns([1, 2])

    with col_logo_preview:
        if brand.get("logo_url"):
            st.markdown(
                f"""
                <div style="background:var(--espresso);border-radius:16px;padding:20px;text-align:center;">
                    <img src="{brand['logo_url']}"
                         style="max-width:140px;max-height:140px;border-radius:10px;object-fit:contain;">
                    <div style="color:rgba(250,247,242,0.6);font-size:11px;margin-top:8px;">Logo actual</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div style="background:var(--sand);border-radius:16px;padding:30px;text-align:center;border:2px dashed rgba(92,61,46,0.25);">
                    <div style="font-size:40px;">🏪</div>
                    <div style="font-size:12px;color:var(--bark);margin-top:8px;">Sin logo · sube uno abajo</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_logo_upload:
        st.caption("Sube un archivo PNG, JPG o JPEG. Recomendado: fondo transparente, mínimo 200×200 px.")
        logo_file = st.file_uploader(
            "Seleccionar imagen de logo",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )

        if logo_file is not None:
            raw = logo_file.read()
            preview_b64 = base64.b64encode(raw).decode()

            st.markdown(
                f"""
                <div style="background:var(--sand);border-radius:12px;padding:12px;text-align:center;margin-bottom:10px;">
                    <div style="font-size:11px;color:var(--bark);margin-bottom:6px;">Vista previa</div>
                    <img src="data:image/png;base64,{preview_b64}"
                         style="max-width:120px;max-height:120px;border-radius:8px;object-fit:contain;">
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("✅ Guardar este logo", type="primary"):
                logo_url = upload_logo_to_storage(raw, logo_file.name)
                db.collection("config").document("branding").set(
                    {"logo_url": logo_url},
                    merge=True
                )
                st.success("Logo guardado correctamente.")
                st.rerun()

        if brand.get("logo_url"):
            if st.button("🗑️ Eliminar logo actual"):
                db.collection("config").document("branding").set(
                    {"logo_url": ""},
                    merge=True
                )
                st.warning("Logo eliminado.")
                st.rerun()

    st.divider()

    # ---- NOMBRE Y SLOGAN ----
    st.markdown("### ✏️ Nombre y slogan")
    with st.form("cfg_brand_form"):
        brand_name = st.text_input("Nombre del negocio", value=brand.get("nombre", "KIN House"))
        slogan = st.text_input("Slogan", value=brand.get("slogan", "Mismo sabor, mismo lugar"))

        if st.form_submit_button("Guardar nombre y slogan", type="primary"):
            db.collection("config").document("branding").set(
                {
                    "nombre": brand_name.strip(),
                    "slogan": slogan.strip()
                },
                merge=True
            )
            st.success("Guardado correctamente.")
            st.rerun()

    st.divider()

    # ---- RESTAURAR CATÁLOGO ----
    st.markdown("### 🗄️ Catálogo base")
    st.caption("Restaura todos los productos del menú oficial de KIN House. Sobreescribirá el catálogo actual.")

    if st.button("🔄 Restaurar catálogo base", type="primary"):
        save_catalog_to_db(DEFAULT_CATALOG)
        get_catalog.clear()
        st.success("Catálogo restaurado correctamente.")
        st.rerun()
