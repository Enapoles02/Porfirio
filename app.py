import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
from zoneinfo import ZoneInfo

# ────────────────────────────────────────────────
# CONFIGURACIÓN BÁSICA
# ────────────────────────────────────────────────
st.set_page_config(page_title="KIN House - Sistema Pro", layout="wide", page_icon="☕")
CDMX_TZ = ZoneInfo("America/Mexico_City")

def now_cdmx(): return datetime.now(CDMX_TZ)
def money(n): return f"${float(n):,.2f}"

# Estilo KIN House (Minimalista / Premium)
st.markdown("""
<style>
    :root { --kin-cream: #F5F2ED; --kin-black: #101010; --kin-gold: #B59461; }
    .stApp { background-color: var(--kin-cream); }
    .mesa-card { 
        padding: 20px; border-radius: 15px; text-align: center; 
        font-weight: bold; border: 2px solid #ddd; transition: 0.3s;
    }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .sidebar-content { background-color: white !important; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# CONEXIÓN FIREBASE
# ────────────────────────────────────────────────
if not firebase_admin._apps:
    fb_creds = dict(st.secrets["firebase_credentials"])
    cred = credentials.Certificate(fb_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ────────────────────────────────────────────────
# BRANDING DINÁMICO (DESDE FIREBASE)
# ────────────────────────────────────────────────
def get_brand():
    doc = db.collection("config").document("branding").get()
    if doc.exists: return doc.to_dict()
    return {"logo": "https://via.placeholder.com/150", "nombre": "KIN House"}

brand = get_brand()

# ────────────────────────────────────────────────
# LÓGICA DE SESIÓN DE CAJA
# ────────────────────────────────────────────────
def get_active_box():
    q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    for s in q:
        d = s.to_dict(); d["id"] = s.id
        return d
    return None

caja = get_active_box()

# ────────────────────────────────────────────────
# NAVEGACIÓN Y ESTRUCTURA
# ────────────────────────────────────────────────
with st.sidebar:
    st.image(brand["logo"], width=150)
    st.title(brand["nombre"])
    menu = st.radio("SISTEMA", ["🪑 Mapa de Mesas", "🧑‍🍳 Comandas Activas", "💵 Caja y Egresos", "⚙️ Configuración"])
    st.divider()
    if caja:
        st.success(f"Caja: {caja['usuario']}\nFondo: {money(caja['monto_inicial'])}")
    else:
        st.error("CAJA CERRADA")

# ────────────────────────────────────────────────
# PANTALLA: CONFIGURACIÓN (LOGO Y NOMBRE)
# ────────────────────────────────────────────────
if menu == "⚙️ Configuración":
    st.header("Configuración de Marca")
    with st.form("brand_form"):
        nuevo_nom = st.text_input("Nombre del Negocio", value=brand["nombre"])
        nuevo_logo = st.text_input("URL del Logo (Imagen Directa)", value=brand["logo"])
        if st.form_submit_button("Guardar Cambios"):
            db.collection("config").document("branding").set({"nombre": nuevo_nom, "logo": nuevo_logo})
            st.success("Marca actualizada. Recarga la página.")

# ────────────────────────────────────────────────
# PANTALLA: MAPA DE MESAS (EL CORAZÓN DEL POS)
# ────────────────────────────────────────────────
elif menu == "🪑 Mapa de Mesas":
    if not caja:
        st.warning("⚠️ Abre caja para poder gestionar mesas.")
    else:
        st.header("Plano del Restaurante")
        
        # Definición de Mesas
        espacios = [
            {"id": "Mesa 1", "tipo": "Mesa"}, {"id": "Mesa 2", "tipo": "Mesa"},
            {"id": "Mesa 3", "tipo": "Mesa"}, {"id": "Mesa 4", "tipo": "Mesa"},
            {"id": "Sillón 1", "tipo": "Sillón"}, {"id": "Sillón 2", "tipo": "Sillón"},
            {"id": "Barra 1", "tipo": "Barra"}, {"id": "Barra 2", "tipo": "Barra"}
        ]
        
        # Obtener mesas ocupadas de Firebase
        mesas_db = db.collection("comandas").where("estado", "==", "ABIERTA").stream()
        ocupadas = {m.to_dict()["espacio_id"]: m.id for m in mesas_db}

        cols = st.columns(4)
        for i, esp in enumerate(espacios):
            with cols[i % 4]:
                is_busy = esp["id"] in ocupadas
                color = "#E74C3C" if is_busy else "#2ECC71"
                st.markdown(f"""
                <div style="background-color:{color}; color:white;" class="mesa-card">
                    {esp['id']}<br><small>{esp['tipo']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if is_busy:
                    if st.button(f"Gestionar {esp['id']}", key=f"btn_{esp['id']}"):
                        st.session_state.selected_comanda = ocupadas[esp["id"]]
                        st.session_state.selected_mesa_nom = esp["id"]
                        st.rerun()
                else:
                    if st.button(f"Abrir {esp['id']}", key=f"btn_{esp['id']}"):
                        new_id = db.collection("comandas").add({
                            "espacio_id": esp["id"],
                            "estado": "ABIERTA",
                            "items": [],
                            "total": 0,
                            "caja_id": caja["id"],
                            "apertura": now_cdmx().isoformat()
                        })[1].id
                        st.rerun()

    # Interfaz de Gestión de Mesa Seleccionada
    if "selected_comanda" in st.session_state:
        st.divider()
        st.subheader(f"📝 Comanda: {st.session_state.selected_mesa_nom}")
        doc_ref = db.collection("comandas").document(st.session_state.selected_comanda)
        comanda_data = doc_ref.get().to_dict()
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write("**Añadir a la cuenta:**")
            # Menú simplificado (Aquí puedes meter tu lista completa de precios)
            menu_items = [
                {"n": "Churro Tradicional", "p": 14}, {"n": "KIN Smash Burger", "p": 99},
                {"n": "Chilaquiles", "p": 129}, {"n": "Café Americano", "p": 55},
                {"n": "Frappé Matcha", "p": 69}, {"n": "Futbolito/Billar (min)", "p": 1}
            ]
            
            it_cols = st.columns(3)
            for j, item in enumerate(menu_items):
                with it_cols[j % 3]:
                    if st.button(f"{item['n']}\n{money(item['p'])}", key=f"menu_{j}"):
                        comanda_data["items"].append(item)
                        comanda_data["total"] += item["p"]
                        doc_ref.update({"items": comanda_data["items"], "total": comanda_data["total"]})
                        st.rerun()
        
        with c2:
            st.write("**Resumen de Cuenta:**")
            for idx, pi in enumerate(comanda_data["items"]):
                st.caption(f"{pi['n']} - {money(pi['p'])}")
            st.write(f"### Total: {money(comanda_data['total'])}")
            
            pago_metodo = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta", "Transferencia"])
            if st.button("CERRAR CUENTA Y LIBERAR MESA", type="primary"):
                # Registrar la venta final
                db.collection("ventas").add({
                    "total": comanda_data["total"],
                    "metodo": pago_metodo,
                    "mesa": st.session_state.selected_mesa_nom,
                    "fecha": now_cdmx().isoformat(),
                    "caja_id": caja["id"]
                })
                # Cerrar comanda
                doc_ref.update({"estado": "CERRADA", "metodo_pago": pago_metodo, "cierre": now_cdmx().isoformat()})
                del st.session_state.selected_comanda
                st.success("Venta registrada y mesa liberada.")
                st.rerun()
            
            if st.button("Cerrar Panel"):
                del st.session_state.selected_comanda
                st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: CAJA Y EGRESOS
# ────────────────────────────────────────────────
elif menu == "💵 Caja y Egresos":
    if not caja:
        st.subheader("Apertura de Turno")
        fondo = st.number_input("Fondo Inicial", min_value=0.0)
        user = st.text_input("Mesero/Encargado")
        if st.button("Abrir Turno"):
            db.collection("cajas").add({
                "estado": "ABIERTA", "usuario": user, "monto_inicial": fondo, "fecha": now_cdmx().isoformat()
            })
            st.rerun()
    else:
        st.header("Control de Caja")
        # Cálculos
        ventas_hoy = db.collection("ventas").where("caja_id", "==", caja["id"]).stream()
        total_v = sum([v.to_dict()["total"] for v in ventas_hoy])
        
        egresos_hoy = db.collection("egresos").where("caja_id", "==", caja["id"]).stream()
        total_e = sum([e.to_dict()["monto"] for e in egresos_hoy])
        
        esperado = caja["monto_inicial"] + total_v - total_e
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas Acumuladas", money(total_v))
        c2.metric("Egresos", f"-{money(total_e)}")
        c3.metric("Efectivo Esperado", money(esperado))
        
        st.divider()
        with st.expander("💸 Registrar Salida de Dinero (Egreso)"):
            motivo = st.text_input("Motivo")
            monto_eg = st.number_input("Monto", min_value=0.0)
            if st.button("Guardar Egreso"):
                db.collection("egresos").add({
                    "caja_id": caja["id"], "motivo": motivo, "monto": monto_eg, "fecha": now_cdmx().isoformat()
                })
                st.rerun()
        
        if st.button("CERRAR CAJA (FINALIZAR TURNO)"):
            db.collection("cajas").document(caja["id"]).update({
                "estado": "CERRADA", "total_ventas": total_v, "total_egresos": total_e, "cierre": now_cdmx().isoformat()
            })
            st.success("Turno cerrado con éxito.")
            st.rerun()
