import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime

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

# -------------------- FUNCTIONS --------------------
def get_user(email):
    user_ref = db.collection("usuarios").document(email)
    return user_ref.get().to_dict()

def save_user(email, data):
    db.collection("usuarios").document(email).set(data)

def update_points(email, stars_add=0, helados_add=0):
    user = get_user(email)
    if not user:
        st.warning("Usuario no encontrado.")
        return
    user['estrellas'] += stars_add
    user['helados'] += helados_add
    user['nivel'] = "gold" if user['estrellas'] >= 200 else "green"
    user['canjear_helado'] = user['helados'] >= 6
    save_user(email, user)

def show_user_summary(user):
    st.markdown(f"**Correo:** {user['email']}")
    st.markdown(f"**Nivel:** {'🥇 Gold' if user['nivel'] == 'gold' else '🥈 Green'}")
    st.markdown(f"**Estrellas:** ⭐ {user['estrellas']} / 200")
    st.markdown(f"**Helados acumulados:** 🍦 {user['helados']} / 6")
    if user['canjear_helado']:
        st.success("🎁 ¡Ya puede canjear un helado!")

# -------------------- LOGIN --------------------
menu = ["Registro", "Iniciar sesión", "Admin"]
opcion = st.sidebar.selectbox("Selecciona una opción", menu)

if opcion == "Registro":
    st.subheader("Registro de usuario")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if st.button("Registrarse"):
        try:
            auth.create_user(email=email, password=password)
            save_user(email, {
                "email": email,
                "nivel": "green",
                "estrellas": 0,
                "helados": 0,
                "canjear_helado": False,
                "fecha_registro": datetime.now().isoformat()
            })
            st.success("✅ Usuario registrado con éxito")
        except Exception as e:
            st.error(f"Error al registrar: {e}")

elif opcion == "Iniciar sesión":
    st.subheader("Inicio de sesión")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        user = get_user(email)
        if user:
            st.success(f"Bienvenido {email}")
            show_user_summary(user)
        else:
            st.error("Usuario no encontrado.")

elif opcion == "Admin":
    st.subheader("👑 Panel del Administrador")
    admin_email = st.text_input("Correo de Admin")
    admin_pass = st.text_input("Contraseña Admin", type="password")

    admin_data = st.secrets["admin_credentials"]
    if admin_email == admin_data["email"] and admin_pass == admin_data["password"]:

        st.success("Acceso autorizado como admin")

        tipo = st.radio("Tipo de recompensa", ["Churrería", "Helados"])
        email_cliente = st.text_input("Correo del cliente")

        if tipo == "Churrería":
            monto = st.number_input("Monto de compra ($MXN)", min_value=0, step=10)
            if st.button("Registrar compra"): 
                estrellas = int(monto / 10)
                update_points(email_cliente, stars_add=estrellas)
                user = get_user(email_cliente)
                if user:
                    show_user_summary(user)

        elif tipo == "Helados":
            cantidad = st.number_input("Cantidad de helados", min_value=1, step=1)
            if st.button("Registrar consumo"):
                update_points(email_cliente, helados_add=int(cantidad))
                user = get_user(email_cliente)
                if user:
                    show_user_summary(user)
    else:
        st.error("Acceso denegado. Solo el admin puede ingresar.")
