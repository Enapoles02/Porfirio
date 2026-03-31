import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import base64
from zoneinfo import ZoneInfo

# ────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILO KIN HOUSE
# ────────────────────────────────────────────────
st.set_page_config(page_title="KIN House POS", layout="wide", page_icon="☀️")
CDMX_TZ = ZoneInfo("America/Mexico_City")

def now_cdmx(): return datetime.now(CDMX_TZ)
def money(n): return f"${float(n):,.0f}"

st.markdown("""
<style>
    :root { --kin-cream: #F5F2ED; --kin-black: #101010; --kin-gold: #B59461; }
    .stApp { background-color: var(--kin-cream); }
    .mesa-card { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 5px; color: white; }
    .category-header { background-color: var(--kin-black); color: white; padding: 5px 15px; border-radius: 5px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# FIREBASE & BRANDING (ATTACHMENT LOGO)
# ────────────────────────────────────────────────
if not firebase_admin._apps:
    fb_creds = dict(st.secrets["firebase_credentials"])
    cred = credentials.Certificate(fb_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_brand():
    doc = db.collection("config").document("branding").get()
    return doc.to_dict() if doc.exists else {"logo_b64": "", "nombre": "KIN House"}

brand = get_brand()

# Sidebar con Logo
with st.sidebar:
    if brand["logo_b64"]:
        st.image(f"data:image/png;base64,{brand['logo_b64']}", use_container_width=True)
    else:
        st.title(brand["nombre"])
    menu_nav = st.radio("MENÚ PRINCIPAL", ["🪑 Comandas y Mesas", "📊 Reporte de Ventas", "💵 Caja y Egresos", "⚙️ Configuración"])

# ────────────────────────────────────────────────
# BASE DE DATOS DEL MENÚ (TU MENÚ REAL)
# ────────────────────────────────────────────────
MENU_DATA = {
    "Churros & Dulce": [
        {"n": "Churro Pieza", "p": 14}, {"n": "Churros (3 pzas)", "p": 42},
        {"n": "Churros (6 pzas)", "p": 79}, {"n": "Churros (12 pzas)", "p": 149},
        {"n": "Sandwich de Churro", "p": 75}, {"n": "Churro Split", "p": 99},
        {"n": "Waffle Sencillo", "p": 49}, {"n": "Waffle Topping", "p": 65},
        {"n": "Buñuelos", "p": 49}, {"n": "Fresas con Crema", "p": 75}
    ],
    "Bebidas Calientes": [
        {"n": "Espresso", "p": 39}, {"n": "Americano G", "p": 55},
        {"n": "Café de Olla G", "p": 55}, {"n": "Latte/Capuccino", "p": 65},
        {"n": "Chai/Matcha Latte", "p": 65}, {"n": "Chocolate Mexicano", "p": 79},
        {"n": "Dirty Chai", "p": 89}
    ],
    "Fríos & Frappés": [
        {"n": "Frappé Mocha/Taro", "p": 69}, {"n": "Frappé Matcha/Chai", "p": 69},
        {"n": "Limonada Natural", "p": 40}, {"n": "Malteada Normal", "p": 89},
        {"n": "Malteada Special", "p": 99}, {"n": "Refresco", "p": 45}
    ],
    "Comida & Brunch": [
        {"n": "Chilaquiles Express", "p": 45}, {"n": "Chilaquiles Normal", "p": 129},
        {"n": "Emparedado Clásico", "p": 69}, {"n": "Emparedado Napoli", "p": 99},
        {"n": "KIN Smash Burger", "p": 99}, {"n": "Sincronizadas", "p": 99},
        {"n": "Orden Hotcakes", "p": 99}, {"n": "Molletes", "p": 99}
    ],
    "Extras & Otros": [
        {"n": "Combo (+Refresco/Sabritas)", "p": 45}, {"n": "Extra Pollo", "p": 10},
        {"n": "Leche Especial", "p": 10}, {"n": "Topping Extra", "p": 12},
        {"n": "Futbolito/Billar (min)", "p": 1}
    ]
}

# ────────────────────────────────────────────────
# PANTALLA: CONFIGURACIÓN
# ────────────────────────────────────────────────
if menu_nav == "⚙️ Configuración":
    st.header("⚙️ Configuración del Sistema")
    with st.form("config_brand"):
        nom = st.text_input("Nombre del Negocio", value=brand["nombre"])
        file = st.file_uploader("Subir Logo (JPG/PNG)", type=["png", "jpg"])
        if st.form_submit_button("Actualizar Marca"):
            new_data = {"nombre": nom, "logo_b64": brand["logo_b64"]}
            if file:
                new_data["logo_b64"] = base64.b64encode(file.read()).decode()
            db.collection("config").document("branding").set(new_data)
            st.success("Marca actualizada.")
            st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: COMANDAS (POS)
# ────────────────────────────────────────────────
elif menu_nav == "🪑 Comandas y Mesas":
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.error("🛑 ABRE CAJA PARA OPERAR")
    else:
        # Layout de Mesas
        espacios = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar/Rápido"]
        comandas_abiertas = {c.to_dict()["espacio"]: c.id for c in db.collection("comandas").where("estado", "==", "ABIERTA").stream()}

        cols = st.columns(4)
        for i, esp in enumerate(espacios):
            with cols[i % 4]:
                ocupada = esp in comandas_abiertas
                color = "#E74C3C" if ocupada else "#2ECC71"
                st.markdown(f'<div class="mesa-card" style="background:{color};">{esp}</div>', unsafe_allow_html=True)
                
                if ocupada:
                    if st.button(f"Abrir Ticket", key=f"btn_{esp}"):
                        st.session_state.current_comanda = comandas_abiertas[esp]
                        st.session_state.current_espacio = esp
                else:
                    if st.button(f"Nueva Orden", key=f"btn_{esp}"):
                        new_id = db.collection("comandas").add({
                            "espacio": esp, "estado": "ABIERTA", "items": [], "total": 0,
                            "caja_id": caja["id"], "hora": now_cdmx().isoformat()
                        })[1].id
                        st.session_state.current_comanda = new_id
                        st.rerun()

        # --- PANEL DE VENTA ---
        if "current_comanda" in st.session_state:
            st.divider()
            doc_ref = db.collection("comandas").document(st.session_state.current_comanda)
            data = doc_ref.get().to_dict()
            
            st.subheader(f"📝 Comanda: {st.session_state.current_espacio}")
            col_menu, col_ticket = st.columns([2, 1])

            with col_menu:
                tabs = st.tabs(list(MENU_DATA.keys()))
                for i, cat in enumerate(MENU_DATA.keys()):
                    with tabs[i]:
                        m_cols = st.columns(3)
                        for idx, prod in enumerate(MENU_DATA[cat]):
                            with m_cols[idx % 3]:
                                if st.button(f"{prod['n']}\n{money(prod['p'])}", key=f"p_{cat}_{idx}"):
                                    data["items"].append(prod)
                                    data["total"] += prod["p"]
                                    doc_ref.update({"items": data["items"], "total": data["total"]})
                                    st.rerun()

            with col_ticket:
                st.markdown("### Resumen")
                for i, it in enumerate(data["items"]):
                    c1, c2 = st.columns([4, 1])
                    c1.caption(f"{it['n']} - {money(it['p'])}")
                    if c2.button("❌", key=f"del_{i}"):
                        data["total"] -= it["p"]
                        data["items"].pop(i)
                        doc_ref.update({"items": data["items"], "total": data["total"]})
                        st.rerun()
                
                st.markdown(f"## Total: {money(data['total'])}")
                metodo = st.selectbox("Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                if st.button("CERRAR CUENTA", type="primary"):
                    db.collection("ventas").add({
                        "total": data["total"], "metodo": metodo, "mesa": st.session_state.current_espacio,
                        "fecha": now_cdmx().isoformat(), "caja_id": caja["id"]
                    })
                    doc_ref.update({"estado": "CERRADA"})
                    del st.session_state.current_comanda
                    st.success("Cobrado.")
                    st.rerun()
                if st.button("Salir sin cerrar"):
                    del st.session_state.current_comanda
                    st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: CAJA
# ────────────────────────────────────────────────
elif menu_nav == "💵 Caja y Egresos":
    # [Aquí pones el código de apertura y arqueo de la versión anterior]
    st.write("Módulo de Arqueo y Egresos Activo.")
