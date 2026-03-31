import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import base64
from zoneinfo import ZoneInfo

# ────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILO
# ────────────────────────────────────────────────
st.set_page_config(page_title="KIN House POS", layout="wide", page_icon="☀️")
CDMX_TZ = ZoneInfo("America/Mexico_City")

def now_cdmx(): return datetime.now(CDMX_TZ)
def money(n): return f"${float(n):,.0f}"

st.markdown("""
<style>
    :root { --kin-cream: #F5F2ED; --kin-black: #101010; --kin-gold: #B59461; }
    .stApp { background-color: var(--kin-cream); }
    .mesa-card { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 5px; color: white; border: 1px solid rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# FIREBASE & BRANDING
# ────────────────────────────────────────────────
if not firebase_admin._apps:
    fb_creds = dict(st.secrets["firebase_credentials"])
    cred = credentials.Certificate(fb_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_brand():
    try:
        doc = db.collection("config").document("branding").get()
        if doc.exists: return doc.to_dict()
    except: pass
    return {"logo_b64": "", "nombre": "KIN House"}

brand = get_brand()

with st.sidebar:
    if brand.get("logo_b64"):
        st.image(f"data:image/png;base64,{brand['logo_b64']}", use_container_width=True)
    else:
        st.title(brand.get("nombre", "KIN House"))
    st.divider()
    menu_nav = st.radio("SISTEMA", ["🪑 Mesas y Comandas", "💵 Caja y Egresos", "📊 Reporte", "⚙️ Configuración"])
    admin_pin = st.text_input("PIN Admin", type="password")
    is_admin = admin_pin == st.secrets.get("admin_pin", "2424")

# ────────────────────────────────────────────────
# MENÚ ACTUALIZADO (CON SABORES Y NUEVOS ITEMS)
# ────────────────────────────────────────────────
MENU_DATA = {
    "Churros Tradicionales": [
        {"n": "Churro Pieza", "p": 14, "opt": ["Azúcar", "Azúcar/Canela"]},
        {"n": "Churros (3 pzas)", "p": 42, "opt": ["Azúcar", "Azúcar/Canela"]},
        {"n": "Churros (6 pzas)", "p": 79, "opt": ["Azúcar", "Azúcar/Canela"]},
        {"n": "Churros (12 pzas)", "p": 149, "opt": ["Azúcar", "Azúcar/Canela"]}
    ],
    "Churros Rellenos": [
        {"n": "Churro Relleno", "p": 35, "rellenos": ["Cajeta", "Mazapán", "Chocolate", "Nutella", "Fresa", "Frutos Rojos", "Lechera", "Otro"]},
        {"n": "Sandwich de Churro", "p": 75},
        {"n": "Churro Split", "p": 99}
    ],
    "Desayunos & Comida": [
        {"n": "Huevo al Gusto", "p": 89, "nota_hint": "Ej. Estrellados, Jamón, Mexicana"},
        {"n": "Chilaquiles Express", "p": 45},
        {"n": "Chilaquiles Normal", "p": 129},
        {"n": "KIN Smash Burger", "p": 99},
        {"n": "Papas Locas Sencillas", "p": 35},
        {"n": "Papas Locas c/ Topping", "p": 45}
    ],
    "Bebidas": [
        {"n": "Americano G", "p": 55}, {"n": "Latte/Capuccino", "p": 65},
        {"n": "Frappé Mocha", "p": 69}, {"n": "Malteada Special", "p": 115}
    ]
}

# ────────────────────────────────────────────────
# PANTALLA: MESAS Y COMANDAS
# ────────────────────────────────────────────────
if menu_nav == "🪑 Mesas y Comandas":
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.error("🛑 CAJA CERRADA. Abre turno en 'Caja y Egresos'.")
    else:
        espacios = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar"]
        comandas_ab = {}
        docs = db.collection("comandas").where("estado", "==", "ABIERTA").stream()
        for d in docs:
            v = d.to_dict()
            if "espacio" in v: comandas_ab[v["espacio"]] = d.id

        m_cols = st.columns(4)
        for i, esp in enumerate(espacios):
            with m_cols[i % 4]:
                ocupada = esp in comandas_ab
                color = "#E74C3C" if ocupada else "#2ECC71"
                st.markdown(f'<div class="mesa-card" style="background:{color};">{esp}</div>', unsafe_allow_html=True)
                if ocupada:
                    if st.button(f"Ticket", key=f"v_{esp}"):
                        st.session_state.cid, st.session_state.enom = comandas_ab[esp], esp
                else:
                    if st.button(f"Abrir", key=f"n_{esp}"):
                        new = db.collection("comandas").add({"espacio": esp, "estado": "ABIERTA", "items": [], "total": 0, "caja_id": caja["id"], "fecha": now_cdmx().isoformat()})
                        st.session_state.cid, st.session_state.enom = new[1].id, esp
                        st.rerun()

        if "cid" in st.session_state:
            st.divider()
            doc_ref = db.collection("comandas").document(st.session_state.cid)
            data = doc_ref.get().to_dict()
            st.subheader(f"📝 {st.session_state.enom}")
            c_m, c_t = st.columns([2, 1])

            with c_m:
                ts = st.tabs(list(MENU_DATA.keys()))
                for i, cat in enumerate(MENU_DATA.keys()):
                    with ts[i]:
                        p_cols = st.columns(3)
                        for idx, prod in enumerate(MENU_DATA[cat]):
                            with p_cols[idx % 3]:
                                det = ""
                                if "opt" in prod:
                                    det = st.selectbox("Azúcar:", prod["opt"], key=f"opt_{cat}_{idx}")
                                if "rellenos" in prod:
                                    det = st.selectbox("Sabor:", prod["rellenos"], key=f"rel_{cat}_{idx}")
                                
                                nota = st.text_input("Nota:", key=f"nt_{cat}_{idx}", placeholder=prod.get("nota_hint", "Instrucciones..."))
                                
                                if st.button(f"{prod['n']}\n{money(prod['p'])}", key=f"add_{cat}_{idx}"):
                                    full_name = f"{prod['n']} ({det})" if det else prod['n']
                                    data["items"].append({"n": full_name, "p": prod["p"], "nota": nota})
                                    data["total"] += prod["p"]
                                    doc_ref.update({"items": data["items"], "total": data["total"]})
                                    st.rerun()

            with c_t:
                st.markdown("### Ticket")
                for i, it in enumerate(data["items"]):
                    r1, r2 = st.columns([4, 1])
                    r1.write(f"**{it['n']}** {money(it['p'])}\n*{it.get('nota','') or ''}*")
                    if r2.button("❌", key=f"del_{i}"):
                        data["total"] -= it["p"]
                        data["items"].pop(i)
                        doc_ref.update({"items": data["items"], "total": data["total"]})
                        st.rerun()
                st.divider()
                st.subheader(f"Total: {money(data['total'])}")
                metodo = st.selectbox("Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                if st.button("CERRAR CUENTA", type="primary"):
                    db.collection("ventas").add({"total": data["total"], "metodo": metodo, "mesa": st.session_state.enom, "fecha": now_cdmx().isoformat(), "caja_id": caja["id"]})
                    doc_ref.update({"estado": "CERRADA"})
                    del st.session_state.cid
                    st.rerun()
                if st.button("Salir"): del st.session_state.cid; st.rerun()

# ────────────────────────────────────────────────
# OTRAS PANTALLAS (CAJA / CONFIG)
# ────────────────────────────────────────────────
elif menu_nav == "💵 Caja y Egresos":
    st.header("Caja")
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)
    if not caja:
        fondo = st.number_input("Fondo Inicial", min_value=0.0)
        user = st.text_input("Usuario")
        if st.button("ABRIR CAJA"):
            db.collection("cajas").add({"monto_inicial": fondo, "usuario": user, "estado": "ABIERTA", "fecha": now_cdmx().isoformat()})
            st.rerun()
    else:
        st.success(f"Abierta por {caja['usuario']}")
        if st.button("CERRAR TURNO"):
            db.collection("cajas").document(caja["id"]).update({"estado": "CERRADA", "cierre": now_cdmx().isoformat()})
            st.rerun()

elif menu_nav == "⚙️ Configuración":
    st.header("Marca")
    with st.form("cfg"):
        nom = st.text_input("Nombre", value=brand.get("nombre"))
        f = st.file_uploader("Logo", type=["png", "jpg"])
        if st.form_submit_button("Guardar"):
            upd = {"nombre": nom}
            if f: upd["logo_b64"] = base64.b64encode(f.read()).decode()
            db.collection("config").document("branding").set(upd, merge=True)
            st.rerun()
