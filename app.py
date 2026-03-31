import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import base64
from zoneinfo import ZoneInfo

# ────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILO KIN HOUSE (PREMIUM)
# ────────────────────────────────────────────────
st.set_page_config(page_title="KIN House POS", layout="wide", page_icon="☀️")
CDMX_TZ = ZoneInfo("America/Mexico_City")

def now_cdmx(): return datetime.now(CDMX_TZ)
def money(n): return f"${float(n):,.0f}"

# Estilo Visual con colores de tu marca
st.markdown("""
<style>
    :root { --kin-cream: #F5F2ED; --kin-black: #101010; --kin-gold: #B59461; }
    .stApp { background-color: var(--kin-cream); }
    .mesa-card { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 5px; color: white; border: 1px solid rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #fff; border-radius: 5px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# FIREBASE & BRANDING (CARGA DE LOGO)
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

# Sidebar con Logo Dinámico
with st.sidebar:
    if brand.get("logo_b64"):
        st.image(f"data:image/png;base64,{brand['logo_b64']}", use_container_width=True)
    else:
        st.title(brand.get("nombre", "KIN House"))
    
    st.divider()
    menu_nav = st.radio("SISTEMA", ["🪑 Mesas y Comandas", "💵 Caja y Egresos", "📊 Reporte de Ventas", "⚙️ Configuración"])
    st.divider()
    
    # PIN de Admin rápido en sidebar
    admin_pin_input = st.text_input("PIN Admin", type="password")
    is_admin = admin_pin_input == st.secrets.get("admin_pin", "2424")

# ────────────────────────────────────────────────
# MENÚ REAL KIN HOUSE
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
    "Extras": [
        {"n": "Combo (+Ref/Sab)", "p": 45}, {"n": "Extra Pollo", "p": 10},
        {"n": "Leche Especial", "p": 10}, {"n": "Topping Extra", "p": 12},
        {"n": "Futbolito (min)", "p": 1}
    ]
}

# ────────────────────────────────────────────────
# PANTALLA: MESAS Y COMANDAS
# ────────────────────────────────────────────────
if menu_nav == "🪑 Mesas y Comandas":
    # 1. Buscar Caja Abierta
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.error("🛑 ERROR: NO HAY CAJA ABIERTA. Ve a 'Caja y Egresos' primero.")
    else:
        # Layout de Mesas
        espacios = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar/PickUp"]
        
        # OBTENCIÓN SEGURA DE COMANDAS (Evita KeyError: 'espacio')
        comandas_abiertas = {}
        try:
            docs = db.collection("comandas").where("estado", "==", "ABIERTA").stream()
            for d in docs:
                val = d.to_dict()
                esp_val = val.get("espacio")
                if esp_val:
                    comandas_abiertas[esp_val] = d.id
        except Exception as e:
            st.error(f"Error en DB: {e}")

        st.subheader("Mapa del Restaurante")
        m_cols = st.columns(4)
        for i, esp in enumerate(espacios):
            with m_cols[i % 4]:
                ocupada = esp in comandas_abiertas
                color = "#E74C3C" if ocupada else "#2ECC71"
                st.markdown(f'<div class="mesa-card" style="background:{color};">{esp}</div>', unsafe_allow_html=True)
                
                if ocupada:
                    if st.button(f"Abrir Ticket", key=f"btn_{esp}"):
                        st.session_state.com_id = comandas_abiertas[esp]
                        st.session_state.esp_nom = esp
                else:
                    if st.button(f"Nueva Orden", key=f"btn_{esp}"):
                        new_com = db.collection("comandas").add({
                            "espacio": esp, "estado": "ABIERTA", "items": [], "total": 0,
                            "caja_id": caja["id"], "fecha_apertura": now_cdmx().isoformat()
                        })
                        st.session_state.com_id = new_com[1].id
                        st.session_state.esp_nom = esp
                        st.rerun()

        # --- PANEL DE TOMA DE PEDIDO ---
        if "com_id" in st.session_state:
            st.divider()
            doc_ref = db.collection("comandas").document(st.session_state.com_id)
            try:
                com_data = doc_ref.get().to_dict()
                if not com_data: st.rerun()
            except: st.rerun()

            st.header(f"📝 Comanda: {st.session_state.esp_nom}")
            c_menu, c_tick = st.columns([2, 1])

            with c_menu:
                # Sistema de Menú por Tabs
                tabs = st.tabs(list(MENU_DATA.keys()))
                for i, cat in enumerate(MENU_DATA.keys()):
                    with tabs[i]:
                        p_cols = st.columns(3)
                        for idx, prod in enumerate(MENU_DATA[cat]):
                            with p_cols[idx % 3]:
                                nota_label = f"Nota_{cat}_{idx}"
                                nota = st.text_input("Nota", key=nota_label, placeholder="Ej. Sin hielos", label_visibility="collapsed")
                                if st.button(f"{prod['n']}\n{money(prod['p'])}", key=f"add_{cat}_{idx}"):
                                    nuevo_item = {"n": prod["n"], "p": prod["p"], "nota": nota}
                                    com_data["items"].append(nuevo_item)
                                    com_data["total"] += prod["p"]
                                    doc_ref.update({"items": com_data["items"], "total": com_data["total"]})
                                    st.rerun()

            with c_tick:
                st.markdown("### Resumen de Cuenta")
                if not com_data["items"]: st.write("Vacío...")
                for i, it in enumerate(com_data["items"]):
                    r1, r2 = st.columns([4, 1])
                    r1.write(f"**{it['n']}** {money(it['p'])}\n*{it.get('nota','') or ''}*")
                    if r2.button("🗑️", key=f"del_{i}"):
                        com_data["total"] -= it["p"]
                        com_data["items"].pop(i)
                        doc_ref.update({"items": com_data["items"], "total": com_data["total"]})
                        st.rerun()
                
                st.divider()
                st.subheader(f"Total: {money(com_data['total'])}")
                
                metodo_p = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
                if st.button("COBRAR Y CERRAR MESA", type="primary"):
                    # Guardar venta
                    db.collection("ventas").add({
                        "total": com_data["total"], "metodo": metodo_p, "mesa": st.session_state.esp_nom,
                        "fecha": now_cdmx().isoformat(), "caja_id": caja["id"]
                    })
                    # Cerrar comanda
                    doc_ref.update({"estado": "CERRADA", "cierre": now_cdmx().isoformat()})
                    del st.session_state.com_id
                    st.success("¡Cobrado!")
                    st.rerun()
                
                if st.button("Cerrar sin cobrar"):
                    del st.session_state.com_id
                    st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: CAJA Y EGRESOS
# ────────────────────────────────────────────────
elif menu_nav == "💵 Caja y Egresos":
    st.header("Gestión de Efectivo")
    
    # Verificar si hay caja abierta
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.subheader("Apertura de Turno")
        fondo = st.number_input("Monto Inicial", min_value=0.0, step=100.0)
        user = st.text_input("Quién abre caja?")
        if st.button("ABRIR CAJA"):
            db.collection("cajas").add({
                "monto_inicial": fondo, "usuario": user, "estado": "ABIERTA", "fecha_apertura": now_cdmx().isoformat()
            })
            st.rerun()
    else:
        st.success(f"Caja abierta por {caja['usuario']} con {money(caja['monto_inicial'])}")
        
        # Resumen Rápido
        ventas_h = db.collection("ventas").where("caja_id", "==", caja["id"]).stream()
        total_v = sum([v.to_dict()["total"] for v in ventas_h])
        
        egresos_h = db.collection("egresos").where("caja_id", "==", caja["id"]).stream()
        total_e = sum([e.to_dict()["monto"] for e in egresos_h])
        
        esperado = caja["monto_inicial"] + total_v - total_e
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas", money(total_v))
        c2.metric("Egresos", f"-{money(total_e)}")
        c3.metric("En Caja (Esperado)", money(esperado))
        
        st.divider()
        st.subheader("Registrar Egreso (Gasto)")
        motivo = st.text_input("Motivo del gasto")
        monto_eg = st.number_input("Monto", min_value=0.0)
        if st.button("Guardar Egreso"):
            db.collection("egresos").add({
                "caja_id": caja["id"], "motivo": motivo, "monto": monto_eg, "fecha": now_cdmx().isoformat()
            })
            st.rerun()
            
        if st.button("CERRAR CAJA Y TURNO", type="primary"):
            db.collection("cajas").document(caja["id"]).update({
                "estado": "CERRADA", "total_ventas": total_v, "total_egresos": total_e, "cierre": now_cdmx().isoformat()
            })
            st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: CONFIGURACIÓN
# ────────────────────────────────────────────────
elif menu_nav == "⚙️ Configuración":
    st.header("Configuración de KIN House")
    with st.form("brand_form"):
        nuevo_nom = st.text_input("Nombre de la Marca", value=brand.get("nombre", "KIN House"))
        file = st.file_uploader("Actualizar Logo (JPG/PNG)", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("Guardar"):
            upd = {"nombre": nuevo_nom}
            if file:
                upd["logo_b64"] = base64.b64encode(file.read()).decode()
            db.collection("config").document("branding").set(upd, merge=True)
            st.success("¡Configuración guardada! Recarga para ver cambios.")

# Reporte de Ventas Simple
elif menu_nav == "📊 Reporte de Ventas" and is_admin:
    st.header("Ventas Recientes")
    v_data = db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).limit(100).stream()
    df = pd.DataFrame([v.to_dict() for v in v_data])
    if not df.empty:
        st.dataframe(df[["fecha", "mesa", "total", "metodo"]], use_container_width=True)
    else:
        st.info("Aún no hay ventas registradas.")
