import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import base64
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components

# ────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILO KIN HOUSE (PREMIUM)
# ────────────────────────────────────────────────
st.set_page_config(page_title="KIN House POS Pro", layout="wide", page_icon="☀️")
CDMX_TZ = ZoneInfo("America/Mexico_City")

def now_cdmx(): return datetime.now(CDMX_TZ)
def money(n): return f"${float(n):,.0f}"

# CSS para Interfaz Táctil y Colores de Marca
st.markdown("""
<style>
    :root { --kin-cream: #F5F2ED; --kin-black: #101010; --kin-gold: #B59461; }
    .stApp { background-color: var(--kin-cream); }
    .mesa-card { padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; margin-bottom: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; height: 3.5em; border: 1px solid rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px; padding: 12px; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# FIREBASE & BRANDING (LOGO ATTACHMENT)
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

# ────────────────────────────────────────────────
# FUNCIÓN DE IMPRESIÓN (TICKET TÉRMICO)
# ────────────────────────────────────────────────
def imprimir_ticket(data, logo_b64, nombre_negocio, espacio):
    fecha = now_cdmx().strftime("%d/%m/%Y %H:%M")
    items_html = "".join([f"<tr><td style='text-align:left;'>{it['n']}</td><td style='text-align:right;'>{money(it['p'])}</td></tr>" for it in data['items']])
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""
    
    ticket_html = f"""
    <div id="tkt" style="width:260px; font-family:'Courier New'; font-size:12px; color:black; padding:10px; background:white;">
        <div style="text-align:center;">
            {f'<img src="{logo_src}" style="max-width:80px;">' if logo_b64 else ""}
            <h3 style="margin:5px 0;">{nombre_negocio}</h3>
            <p style="margin:2px;">{fecha} | {espacio}</p>
        </div>
        <hr style="border-top:1px dashed #000;">
        <table style="width:100%;">{items_html}</table>
        <hr style="border-top:1px dashed #000;">
        <div style="text-align:right; font-size:16px; font-weight:bold;">TOTAL: {money(data['total'])}</div>
        <div style="text-align:center; margin-top:15px;"><p>¡Gracias por tu visita!</p></div>
    </div>
    <script>window.print();</script>
    """
    components.html(ticket_html, height=0)

# ────────────────────────────────────────────────
# DIÁLOGOS EMERGENTES (POP-UPS)
# ────────────────────────────────────────────────
@st.dialog("Acabado del Churro")
def pop_churro_tradicional(prod_name, price, doc_ref, data):
    st.write(f"Selecciona el azúcar para: **{prod_name}**")
    opts = ["Azúcar", "Azúcar y Canela"]
    c1, c2 = st.columns(2)
    for i, opt in enumerate(opts):
        if [c1, c2][i].button(opt, use_container_width=True):
            data["items"].append({"n": f"{prod_name} ({opt})", "p": price})
            data["total"] += price
            doc_ref.update({"items": data["items"], "total": data["total"]})
            st.rerun()

@st.dialog("Sabor del Relleno")
def pop_churro_relleno(price, doc_ref, data):
    rellenos = ["Cajeta", "Mazapán", "Chocolate", "Nutella", "Fresa", "Frutos Rojos", "Lechera", "Otro"]
    cols = st.columns(3)
    for i, rel in enumerate(rellenos):
        if cols[i % 3].button(rel, use_container_width=True):
            data["items"].append({"n": f"Churro Relleno ({rel})", "p": price})
            data["total"] += price
            doc_ref.update({"items": data["items"], "total": data["total"]})
            st.rerun()

@st.dialog("Detalle de Comida")
def pop_nota_comida(prod_name, price, doc_ref, data):
    st.write(f"Instrucciones para: **{prod_name}**")
    nota = st.text_input("Nota (Ej. Sin cebolla, Estrellados, etc.)", label_visibility="collapsed")
    if st.button("Agregar a la Orden", type="primary"):
        data["items"].append({"n": prod_name, "p": price, "nota": nota})
        data["total"] += price
        doc_ref.update({"items": data["items"], "total": data["total"]})
        st.rerun()

# ────────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ────────────────────────────────────────────────
with st.sidebar:
    if brand.get("logo_b64"):
        st.image(f"data:image/png;base64,{brand['logo_b64']}", use_container_width=True)
    else: st.title(brand.get("nombre", "KIN House"))
    st.divider()
    menu_nav = st.radio("SISTEMA", ["🪑 Mesas y Orden", "💵 Caja y Egresos", "📊 Reporte", "⚙️ Configuración"])
    st.divider()
    admin_pin = st.text_input("PIN Admin", type="password")
    is_admin = admin_pin == st.secrets.get("admin_pin", "2424")

# ────────────────────────────────────────────────
# PANTALLA: MESAS Y COMANDAS
# ────────────────────────────────────────────────
if menu_nav == "🪑 Mesas y Orden":
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.error("🛑 CAJA CERRADA. Abre turno en el menú de Caja.")
    else:
        espacios = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar"]
        comandas_ab = {d.to_dict()["espacio"]: d.id for d in db.collection("comandas").where("estado", "==", "ABIERTA").stream() if "espacio" in d.to_dict()}

        m_cols = st.columns(4)
        for i, esp in enumerate(espacios):
            with m_cols[i % 4]:
                ocupada = esp in comandas_ab
                color = "#E74C3C" if ocupada else "#2ECC71"
                st.markdown(f'<div class="mesa-card" style="background:{color};">{esp}</div>', unsafe_allow_html=True)
                if st.button("Ver/Abrir", key=f"btn_{esp}"):
                    if not ocupada:
                        new = db.collection("comandas").add({"espacio": esp, "estado": "ABIERTA", "items": [], "total": 0, "caja_id": caja["id"], "fecha": now_cdmx().isoformat()})
                        st.session_state.cid, st.session_state.enom = new[1].id, esp
                    else:
                        st.session_state.cid, st.session_state.enom = comandas_ab[esp], esp
                    st.rerun()

        if "cid" in st.session_state:
            doc_ref = db.collection("comandas").document(st.session_state.cid)
            com_data = doc_ref.get().to_dict()
            st.divider()
            st.subheader(f"📍 {st.session_state.enom}")
            c_menu, c_tick = st.columns([2, 1])

            with c_menu:
                t1, t2, t3, t4 = st.tabs(["Churros", "Desayunos", "Bebidas", "Papas/Varios"])
                with t1:
                    c = st.columns(3)
                    if c[0].button("Churro Pz\n$14"): pop_churro_tradicional("Churro", 14, doc_ref, com_data)
                    if c[1].button("Churros(3)\n$42"): pop_churro_tradicional("Churros(3)", 42, doc_ref, com_data)
                    if c[2].button("RELLENO\n$35"): pop_churro_relleno(35, doc_ref, com_data)
                with t2:
                    c = st.columns(3)
                    if c[0].button("HUEVOS\n$89"): pop_nota_comida("Huevos al Gusto", 89, doc_ref, com_data)
                    if c[1].button("Burger\n$99"): pop_nota_comida("KIN Smash Burger", 99, doc_ref, com_data)
                    if c[2].button("Chilaquiles\n$129"): pop_nota_comida("Chilaquiles Normal", 129, doc_ref, com_data)
                with t4:
                    c = st.columns(2)
                    if c[0].button("Papas Locas\n$35"): pop_nota_comida("Papas Locas", 35, doc_ref, com_data)
                    if c[1].button("Papas Topping\n$45"): pop_nota_comida("Papas Locas c/ Topping", 45, doc_ref, com_data)

            with c_tick:
                st.markdown("### Resumen")
                for i, it in enumerate(com_data["items"]):
                    col_i, col_d = st.columns([4, 1])
                    col_i.write(f"**{it['n']}** {money(it['p'])}\n*{it.get('nota','') or ''}*")
                    if col_d.button("🗑️", key=f"rm_{i}"):
                        com_data["total"] -= it["p"]; com_data["items"].pop(i)
                        doc_ref.update({"items": com_data["items"], "total": com_data["total"]}); st.rerun()
                st.divider()
                st.subheader(f"Total: {money(com_data['total'])}")
                met = st.selectbox("Pago:", ["Efectivo", "Tarjeta", "Transfer"])
                if st.button("COBRAR E IMPRIMIR", type="primary"):
                    db.collection("ventas").add({"total": com_data["total"], "metodo": met, "mesa": st.session_state.enom, "fecha": now_cdmx().isoformat(), "caja_id": caja["id"]})
                    imprimir_ticket(com_data, brand["logo_b64"], brand["nombre"], st.session_state.enom)
                    doc_ref.update({"estado": "CERRADA"})
                    del st.session_state.cid; st.rerun()
                if st.button("Solo Imprimir Ticket"): imprimir_ticket(com_data, brand["logo_b64"], brand["nombre"], st.session_state.enom)
                if st.button("Cerrar Panel"): del st.session_state.cid; st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: CAJA Y EGRESOS
# ────────────────────────────────────────────────
elif menu_nav == "💵 Caja y Egresos":
    st.header("Control de Caja")
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.subheader("Apertura de Turno")
        fondo = st.number_input("Fondo Inicial", min_value=0.0)
        user = st.text_input("Usuario")
        if st.button("ABRIR CAJA"):
            db.collection("cajas").add({"monto_inicial": fondo, "usuario": user, "estado": "ABIERTA", "fecha": now_cdmx().isoformat()})
            st.rerun()
    else:
        v_h = db.collection("ventas").where("caja_id", "==", caja["id"]).stream()
        total_v = sum([v.to_dict()["total"] for v in v_h])
        e_h = db.collection("egresos").where("caja_id", "==", caja["id"]).stream()
        total_e = sum([e.to_dict()["monto"] for e in e_h])
        esp = caja["monto_inicial"] + total_v - total_e
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas", money(total_v)); c2.metric("Egresos", f"-{money(total_e)}"); c3.metric("Efectivo Esperado", money(esp))
        
        st.divider()
        with st.expander("💸 Registrar Gasto"):
            mot = st.text_input("Motivo"); mnt = st.number_input("Monto", min_value=0.0)
            if st.button("Guardar Egreso"):
                db.collection("egresos").add({"caja_id": caja["id"], "motivo": mot, "monto": mnt, "fecha": now_cdmx().isoformat()})
                st.rerun()
        if st.button("CERRAR TURNO", type="primary"):
            db.collection("cajas").document(caja["id"]).update({"estado": "CERRADA", "cierre": now_cdmx().isoformat()})
            st.rerun()

# ────────────────────────────────────────────────
# PANTALLA: CONFIGURACIÓN
# ────────────────────────────────────────────────
elif menu_nav == "⚙️ Configuración":
    st.header("Configuración de Marca")
    with st.form("cfg"):
        nom = st.text_input("Nombre del Negocio", value=brand.get("nombre"))
        file = st.file_uploader("Actualizar Logo", type=["png", "jpg"])
        if st.form_submit_button("Guardar"):
            upd = {"nombre": nom}
            if file: upd["logo_b64"] = base64.b64encode(file.read()).decode()
            db.collection("config").document("branding").set(upd, merge=True)
            st.success("Guardado. Refresca la página.")

# Reporte
elif menu_nav == "📊 Reporte":
    if is_admin:
        v_d = db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).limit(100).stream()
        df = pd.DataFrame([v.to_dict() for v in v_d])
        if not df.empty: st.dataframe(df[["fecha", "mesa", "total", "metodo"]], use_container_width=True)
    else: st.warning("Ingrese PIN de Admin.")
