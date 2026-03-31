import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
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

st.markdown("""
<style>
    :root { --kin-cream: #F5F2ED; --kin-black: #101010; --kin-gold: #B59461; }
    .stApp { background-color: var(--kin-cream); }
    .mesa-card { padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; margin-bottom: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; height: 3.8em; border: 1px solid rgba(0,0,0,0.05); font-size: 12px; line-height: 1.2; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px; padding: 10px; border: 1px solid #ddd; }
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
        return doc.to_dict() if doc.exists else {"logo_b64": "", "nombre": "KIN House"}
    except: return {"logo_b64": "", "nombre": "KIN House"}

brand = get_brand()

# ────────────────────────────────────────────────
# DIÁLOGOS EMERGENTES (POP-UPS)
# ────────────────────────────────────────────────
@st.dialog("Variante de Producto")
def pop_opciones(prod_name, price, opciones, doc_ref, data):
    st.write(f"Seleccione para: **{prod_name}**")
    cols = st.columns(2)
    for i, opt in enumerate(opciones):
        p_final = price
        if "+$" in opt:
            try: p_final += int(opt.split("+$")[-1])
            except: pass
        if cols[i % 2].button(opt, use_container_width=True):
            data["items"].append({"n": f"{prod_name} ({opt})", "p": p_final})
            data["total"] += p_final
            doc_ref.update({"items": data["items"], "total": data["total"]})
            st.rerun()

# ────────────────────────────────────────────────
# INTERFAZ POS
# ────────────────────────────────────────────────
with st.sidebar:
    if brand.get("logo_b64"):
        st.image(f"data:image/png;base64,{brand['logo_b64']}", use_container_width=True)
    menu_nav = st.sidebar.selectbox("MENÚ", ["🪑 Mesas", "💵 Caja", "📊 Reporte", "⚙️ Config"])
    st.divider()
    admin_pin = st.text_input("PIN Admin", type="password")
    is_admin = admin_pin == st.secrets.get("admin_pin", "2424")

if menu_nav == "🪑 Mesas":
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)

    if not caja:
        st.error("🛑 CAJA CERRADA")
    else:
        espacios = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Sillón 1", "Sillón 2", "Barra", "Llevar"]
        comandas_ab = {d.to_dict()["espacio"]: d.id for d in db.collection("comandas").where("estado", "==", "ABIERTA").stream() if "espacio" in d.to_dict()}

        m_cols = st.columns(4)
        for i, esp in enumerate(espacios):
            with m_cols[i % 4]:
                ocupada = esp in comandas_ab
                bg = "#E74C3C" if ocupada else "#2ECC71"
                st.markdown(f'<div class="mesa-card" style="background:{bg};">{esp}</div>', unsafe_allow_html=True)
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
                t1, t2, t3, t4, t5 = st.tabs(["Churros/Dulce", "Comida/Desayunos", "Café/Barra", "Bebidas/Helados", "Combos"])
                
                with t1: # CHURROS Y DULCE
                    st.caption("Churros Tradicionales & Rellenos")
                    c = st.columns(4)
                    if c[0].button("1 Pz\n$14"): pop_opciones("Churro Pz", 14, ["Azúcar", "Canela"], doc_ref, com_data)
                    if c[1].button("3 Pz\n$42"): pop_opciones("Churros(3)", 42, ["Azúcar", "Canela"], doc_ref, com_data)
                    if c[2].button("6 Pz\n$79"): pop_opciones("Churros(6)", 79, ["Azúcar", "Canela"], doc_ref, com_data)
                    if c[3].button("12 Pz\n$149"): pop_opciones("Churros(12)", 149, ["Azúcar", "Canela"], doc_ref, com_data)
                    
                    c2 = st.columns(3)
                    if c2[0].button("Relleno\n$35"): pop_opciones("Churro Relleno", 35, ["Cajeta", "Mazapán", "Nutella", "Chocolate", "Fresa", "Frutos Rojos", "Lechera"], doc_ref, com_data)
                    if c2[1].button("Sandwich Ch\n$75"): pop_opciones("Sandwich Churro", 75, ["Sencillo", "+$12 Topping"], doc_ref, com_data)
                    if c2[2].button("Split\n$99"): pop_opciones("Churro Split", 99, ["3 Bolas Helado"], doc_ref, com_data)
                    
                    st.caption("Waffles, Buñuelos & Postres")
                    c3 = st.columns(3)
                    if c3[0].button("Waffles\n$49/$65"): pop_opciones("Waffle", 49, ["Sencillo $49", "Topping $65"], doc_ref, com_data)
                    if c3[1].button("Buñuelos\n$49"): pop_opciones("Buñuelos", 49, ["Tradicional"], doc_ref, com_data)
                    if c3[2].button("Fresas Crema\n$75/$85"): pop_opciones("Fresas Crema", 75, ["12oz $75", "16oz $85"], doc_ref, com_data)

                with t2: # COMIDA Y DESAYUNOS
                    st.caption("Emparedados KIN & Smash Burger")
                    c = st.columns(3)
                    if c[0].button("Clásico\n$69"): pop_opciones("Emp. Clásico", 69, ["Jamón y Queso", "Combo +$45"], doc_ref, com_data)
                    if c[1].button("Ratatouille\n$79"): pop_opciones("Emp. Ratatouille", 79, ["3 Quesos", "Combo +$45"], doc_ref, com_data)
                    if c[2].button("Pamplona\n$89"): pop_opciones("Emp. Pamplona", 89, ["Salami/Chorizo", "Combo +$45"], doc_ref, com_data)
                    c2 = st.columns(3)
                    if c2[0].button("Napoli\n$99"): pop_opciones("Emp. Napoli", 99, ["Pollo/Ajo", "Combo +$45"], doc_ref, com_data)
                    if c2[1].button("Toscano\n$105"): pop_opciones("Emp. Toscano", 105, ["Boloñesa/Pollo", "Combo +$45"], doc_ref, com_data)
                    if c2[2].button("Smash Burger\n$99"): pop_opciones("KIN Smash", 99, ["Sencilla", "Doble +$29", "Combo +$45"], doc_ref, com_data)

                    st.caption("Desayunos (Incluyen Jugo/Fruta y Café)")
                    c3 = st.columns(3)
                    if c3[0].button("Chilaquiles\n$45/$129"): pop_opciones("Chilaquiles", 45, ["Express $45", "Normal $129", "+$10 Pollo"], doc_ref, com_data)
                    if c3[1].button("Enfrijoladas\n$129"): pop_opciones("Enfrijoladas", 129, ["Orden Completa"], doc_ref, com_data)
                    if c3[2].button("Molletes\n$99"): pop_opciones("Molletes", 99, ["Sencillos", "+$10 Chorizo"], doc_ref, com_data)
                    c4 = st.columns(2)
                    if c4[0].button("Sincronizadas\n$99"): pop_opciones("Sincronizadas", 99, ["Jamón/Queso"], doc_ref, com_data)
                    if c4[1].button("Hotcakes\n$99"): pop_opciones("Hotcakes", 99, ["Orden 3 pz", "+$35 Orden Extra"], doc_ref, com_data)

                with t3: # CAFÉ Y BARRA
                    st.caption("Cafetería Tradicional")
                    c = st.columns(3)
                    if c[0].button("Americano/Olla\n$45/$55"): pop_opciones("Café", 45, ["Amer. Ch $45", "Amer. Gr $55", "Olla Ch $45", "Olla Gr $55", "Chiapas $35", "Espresso $39"], doc_ref, com_data)
                    if c[1].button("Lechero/Mocha\n$65/$75"): pop_opciones("Lechero/Latte", 65, ["Chico $65", "Grande $75", "+$10 Leche Veg"], doc_ref, com_data)
                    if c[2].button("Capu/Matcha\n$65/$75"): pop_opciones("Capu/Matcha/Taro", 65, ["Chico $65", "Grande $75", "Horchata $65"], doc_ref, com_data)
                    
                    st.caption("Especialidades y Frappés")
                    c2 = st.columns(3)
                    if c2[0].button("Esp. Caliente\n$79"): pop_opciones("Esp. Caliente", 79, ["Dirty Chai", "Dirty Horchata", "Chocoreta", "Mexicano", "Crawnberry Mocha"], doc_ref, com_data)
                    if c2[1].button("Esp. Fría\n$89"): pop_opciones("Esp. Fría", 89, ["Dirty Chai", "Dirty Horchata", "Chocoreta", "Mexicano", "Crawnberry Mocha"], doc_ref, com_data)
                    if c2[2].button("Frappé\n$69/$79"): pop_opciones("Frappé", 69, ["Mocha", "Taro", "Cookies", "Matcha", "Horchata", "Chai"], doc_ref, com_data)

                with t4: # BEBIDAS Y HELADOS
                    st.caption("Bebidas Frías")
                    c = st.columns(3)
                    if c[0].button("Té/Lim\n$40/$45"): pop_opciones("Bebida Natural", 40, ["Nat. $40", "Min. $45"], doc_ref, com_data)
                    if c[1].button("Malteada\n$89/$115"): pop_opciones("Malteada", 89, ["Normal $89", "Grande $99", "Special $115"], doc_ref, com_data)
                    if c[2].button("Refresco/Agua\n$45"): pop_opciones("Embotellado", 45, ["Refresco $45", "Agua $30"], doc_ref, com_data)
                    
                    st.caption("Helados KIN House")
                    c2 = st.columns(3)
                    if c2[0].button("Suave\n$20/$35"): pop_opciones("Helado Suave", 20, ["Cono $20", "Sundae $35", "+$12 Topping"], doc_ref, com_data)
                    if c2[1].button("Yogurth\n$59/$75"): pop_opciones("Helado Yogurth", 59, ["Sencillo $59", "Doble $75", "+$25 Ilimitado"], doc_ref, com_data)
                    if c2[2].button("QUEEN/KING\n$90/$120"): pop_opciones("House Series", 90, ["QUEEN (Vainilla) $90", "KING (Yogurth) $120"], doc_ref, com_data)

                with t5: # COMBOS
                    st.caption("Promociones y Paquetes")
                    c = st.columns(2)
                    if c[0].button("Combos Tradición"): pop_opciones("Combo Tradición", 109, ["1 Choc + 3 Chur $109", "2 Choc + 6 Chur $229"], doc_ref, com_data)
                    if c[1].button("Combos Breakfast"): pop_opciones("Combo Desayuno", 89, ["Café + Sandwich $89", "2 Granizados $99"], doc_ref, com_data)

            with c_tick:
                st.markdown("### Ticket")
                for i, it in enumerate(com_data["items"]):
                    col_i, col_d = st.columns([4, 1])
                    col_i.write(f"**{it['n']}** {money(it['p'])}")
                    if col_d.button("🗑️", key=f"rm_{i}"):
                        com_data["total"] -= it["p"]; com_data["items"].pop(i)
                        doc_ref.update({"items": com_data["items"], "total": com_data["total"]}); st.rerun()
                st.divider(); st.subheader(f"Total: {money(com_data['total'])}")
                met = st.selectbox("Pago:", ["Efectivo", "Tarjeta", "Transferencia"])
                if st.button("COBRAR E IMPRIMIR", type="primary"):
                    db.collection("ventas").add({"total": com_data["total"], "metodo": met, "mesa": st.session_state.enom, "fecha": now_cdmx().isoformat(), "caja_id": caja["id"]})
                    # Script de impresión
                    items_html = "".join([f"<tr><td>{it['n']}</td><td align='right'>{money(it['p'])}</td></tr>" for it in com_data['items']])
                    logo_src = f"data:image/png;base64,{brand['logo_b64']}" if brand['logo_b64'] else ""
                    ticket_js = f"""<div style="width:260px; font-family:monospace; font-size:12px; color:black; padding:10px; background:white;">
                        <center>{f'<img src="{logo_src}" width="80"><br>' if logo_src else ""}<b>{brand['nombre']}</b><br>{now_cdmx().strftime('%d/%m/%Y %H:%M')}<br>Mesa: {st.session_state.enom}</center>
                        <hr><table>{items_html}</table><hr><div align="right"><b>TOTAL: {money(com_data['total'])}</b></div><br>
                        <center>¡Gracias! Mismo Sabor, Mismo Lugar</center></div><script>window.print();</script>"""
                    components.html(ticket_js, height=0)
                    doc_ref.update({"estado": "CERRADA"})
                    del st.session_state.cid; st.rerun()
                if st.button("Salir sin cerrar"): del st.session_state.cid; st.rerun()

elif menu_nav == "💵 Caja":
    st.header("Caja")
    caja_q = db.collection("cajas").where("estado", "==", "ABIERTA").limit(1).stream()
    caja = next((c.to_dict() | {"id": c.id} for c in caja_q), None)
    if not caja:
        f = st.number_input("Fondo Inicial", min_value=0.0); u = st.text_input("Usuario")
        if st.button("ABRIR CAJA"):
            db.collection("cajas").add({"monto_inicial": f, "usuario": u, "estado": "ABIERTA", "fecha": now_cdmx().isoformat()}); st.rerun()
    else:
        v_h = db.collection("ventas").where("caja_id", "==", caja["id"]).stream()
        total_v = sum([v.to_dict()["total"] for v in v_h])
        e_h = db.collection("egresos").where("caja_id", "==", caja["id"]).stream()
        total_e = sum([e.to_dict()["monto"] for e in e_h])
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas", money(total_v)); c2.metric("Egresos", f"-{money(total_e)}"); c3.metric("Efectivo Esperado", money(caja["monto_inicial"] + total_v - total_e))
        st.divider()
        with st.expander("💸 Gasto"):
            mot = st.text_input("Motivo"); mnt = st.number_input("Monto", min_value=0.0)
            if st.button("Guardar"): db.collection("egresos").add({"caja_id": caja["id"], "motivo": mot, "monto": mnt, "fecha": now_cdmx().isoformat()}); st.rerun()
        if st.button("CERRAR TURNO"): db.collection("cajas").document(caja["id"]).update({"estado": "CERRADA", "cierre": now_cdmx().isoformat()}); st.rerun()

elif menu_nav == "⚙️ Config":
    st.header("Configuración")
    with st.form("cfg"):
        nom = st.text_input("Nombre", value=brand.get("nombre"))
        f = st.file_uploader("Logo", type=["png", "jpg"])
        if st.form_submit_button("Guardar"):
            upd = {"nombre": nom}
            if f: upd["logo_b64"] = base64.b64encode(f.read()).decode()
            db.collection("config").document("branding").set(upd, merge=True); st.success("Guardado.")

elif menu_nav == "📊 Reporte" and is_admin:
    v_d = db.collection("ventas").order_by("fecha", direction=firestore.Query.DESCENDING).limit(100).stream()
    df = pd.DataFrame([v.to_dict() for v in v_d])
    if not df.empty: st.dataframe(df[["fecha", "mesa", "total", "metodo"]], use_container_width=True)
