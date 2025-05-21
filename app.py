import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random
import string

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Churreria & Helados App", layout="wide")
st.title("🎉 Programa de Recompensas")

# -------------------- FIREBASE INIT --------------------
try:
    creds = st.secrets["firebase_credentials"]
    cred = credentials.Certificate(dict(creds))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"❌ Firebase error: {e}")
    st.stop()

# -------------------- SESSION STATE --------------------
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None
if "cliente_confirmado" not in st.session_state:
    st.session_state.cliente_confirmado = None

# -------------------- FUNCTIONS --------------------
def generate_cliente_id(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_user(identifier):
    doc = db.collection("usuarios").document(identifier).get()
    if doc.exists:
        return doc.to_dict()
    query = db.collection("usuarios").where("cliente_id", "==", identifier).limit(1).stream()
    for result in query:
        return result.to_dict()
    return None

def log_action(action_type, usuario, detalle=""):
    try:
        db.collection("logs").add({
            "accion": action_type,
            "usuario": usuario,
            "detalle": detalle,
            "fecha": datetime.now().isoformat()
        })
    except Exception as e:
        st.warning(f"⚠️ Error al guardar log: {e}")

def save_user(email, data):
    try:
        db.collection("usuarios").document(email).set(data)
        st.write(f"✅ Usuario guardado con email: {email}")
        log_action("registro", email)
    except Exception as e:
        st.error(f"❌ Error al guardar en Firestore: {e}")

def update_points(identifier, stars_add=0, helados_add=0):
    user = get_user(identifier)
    if not user:
        st.warning("Usuario no encontrado.")
        return
    user['estrellas'] += stars_add
    user['helados'] += helados_add
    recompensa_bebida = False

    if user['nivel'] == "green" and user['estrellas'] >= 200:
        user['nivel'] = "gold"
        user['estrellas'] = 0
        recompensa_bebida = True
    elif user['nivel'] == "gold":
        total_estrellas = user['estrellas']
        bebidas = total_estrellas // 100
        user['estrellas'] = total_estrellas % 100
        for _ in range(bebidas):
            recompensa_bebida = True
            log_action("recompensa", user['email'], "🎁 Bebida gratis por cada 100 estrellas en nivel oro")

    user['canjear_helado'] = user['helados'] >= 6
    save_user(user['email'], user)
    log_action("consumo", user['email'], f"+{stars_add} estrellas, +{helados_add} helados")

def canjear_helado(identifier):
    user = get_user(identifier)
    if not user:
        st.warning("Usuario no encontrado.")
        return
    if user['helados'] >= 6:
        user['helados'] -= 6
        user['canjear_helado'] = False
        save_user(user['email'], user)
        st.success("🎉 Helado canjeado exitosamente")
        log_action("canje", user['email'], "Canje de helado (6 helados)")
    else:
        st.warning("❌ No tiene suficientes helados para canjear")

def show_user_summary(user):
    st.markdown(f"**Correo:** {user['email']}")
    st.markdown(f"**Número de cliente:** {user.get('cliente_id', 'No asignado')}")
    st.markdown(f"**Nivel:** {'🥇 Gold' if user['nivel'] == 'gold' else '🥈 Green'}")
    progress_max = 100 if user['nivel'] == 'gold' else 200
    progress_value = min(user['estrellas'] / progress_max, 1.0)
    st.markdown("Estrellas acumuladas:")
    st.progress(progress_value, text=f"{user['estrellas']} / {progress_max}")
    st.markdown(f"**Helados acumulados:** 🍦 {user['helados']} / 6")
    if user['canjear_helado']:
        st.success("🎁 ¡Ya puede canjear un helado!")
        if st.button("Canjear helado ahora"):
            canjear_helado(user['email'])
    logs = db.collection("logs").where("usuario", "==", user['email']).where("accion", "==", "recompensa").stream()
    bebidas = sum(1 for log in logs)
    st.info(f"☕ Bebidas ganadas por nivel oro: {bebidas}")

# -------------------- NAVEGACIÓN --------------------
menu = ["Registro", "Iniciar sesión", "Admin"]
opcion = st.sidebar.selectbox("Selecciona una opción", menu)

if st.session_state.usuario_actual:
    user = get_user(st.session_state.usuario_actual)
    if user:
        st.success(f"Bienvenido {user['email']}")
        show_user_summary(user)
    st.stop()

if opcion == "Registro":
    st.subheader("Registro de usuario")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if st.button("Registrarse"):
        try:
            cliente_id = generate_cliente_id()
            data = {
                "email": email,
                "cliente_id": cliente_id,
                "nivel": "green",
                "estrellas": 0,
                "helados": 0,
                "canjear_helado": False,
                "fecha_registro": datetime.now().isoformat()
            }
            save_user(email, data)
            st.success("✅ Usuario registrado con éxito")
            st.info(f"Tu número de cliente es: {cliente_id}")
        except Exception as e:
            st.error(f"Error al registrar: {e}")

elif opcion == "Iniciar sesión":
    st.subheader("Inicio de sesión")
    identifier = st.text_input("Correo o número de cliente")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        user = get_user(identifier)
        if user:
            st.session_state.usuario_actual = user['email']
            st.rerun()
        else:
            st.error("Usuario no encontrado.")

elif opcion == "Admin":
    st.subheader("👑 Panel del Administrador")
    admin_data = st.secrets.get("admin_credentials", None)
    admin_email = st.text_input("Correo de Admin")
    admin_pass = st.text_input("Contraseña Admin", type="password")

    if admin_data and admin_email == admin_data["email"] and admin_pass == admin_data["password"]:
        st.success("Acceso autorizado como admin")

        tipo = st.radio("Tipo de recompensa", ["Churrería", "Helados"])
        identificador_cliente = st.text_input("Correo o número del cliente")
        if st.button("Confirmar cliente"):
            user_preview = get_user(identificador_cliente)
            if user_preview:
                st.session_state.cliente_confirmado = identificador_cliente
                st.success(f"Cliente encontrado: {user_preview['email']}")
                show_user_summary(user_preview)
            else:
                st.error("Cliente no encontrado.")

        if not st.session_state.cliente_confirmado:
            st.stop()

        identificador_cliente = st.session_state.cliente_confirmado

        if tipo == "Churrería":
            monto = st.number_input("Monto de compra ($MXN)", min_value=0, step=10)
            if st.button("Registrar compra"):
                estrellas = int(monto / 10)
                update_points(identificador_cliente, stars_add=estrellas)
                user = get_user(identificador_cliente)
                if user:
                    show_user_summary(user)

        elif tipo == "Helados":
            cantidad = st.number_input("Cantidad de helados", min_value=1, step=1)
            if st.button("Registrar consumo"):
                update_points(identificador_cliente, helados_add=int(cantidad))
                user = get_user(identificador_cliente)
                if user:
                    show_user_summary(user)

            st.markdown("---")
            st.markdown("### Canjear helado directamente")
            if st.button("Canjear helado"):
                canjear_helado(identificador_cliente)
                user = get_user(identificador_cliente)
                if user:
                    show_user_summary(user)
    else:
        st.error("Acceso denegado. Solo el admin puede ingresar.")
