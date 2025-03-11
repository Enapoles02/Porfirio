import streamlit as st
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# Inicializar Firebase si no está inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase_credentials"])
    initialize_app(cred)
db = firestore.client()

# Función para registrar un usuario
def register_user(email, password):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        st.error("El usuario ya existe.")
        return
    db.collection("users").add({
        "email": email,
        "password": password,
        "role": "user",
        "small_ice_creams": 0,
        "medium_ice_creams": 0
    })
    st.success("Usuario registrado exitosamente. Ahora puedes iniciar sesión.")

# Función para autenticar usuarios
def authenticate_user(email, password):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_data = user.to_dict()
        if user_data["password"] == password:
            return user_data
    return None

# Función para actualizar el conteo de helados
def update_ice_cream_count(email, size, quantity):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        if size == "small":
            user_ref.update({"small_ice_creams": firestore.Increment(quantity)})
        elif size == "medium":
            user_ref.update({"medium_ice_creams": firestore.Increment(quantity)})

# Función para obtener información del usuario
def get_user_data(email):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        return user.to_dict()
    return None

# Función para manejar el canje de helado
def redeem_ice_cream(email, size):
    user_data = get_user_data(email)
    if user_data:
        total_ice_creams = user_data.get(f"{size}_ice_creams", 0)
        if total_ice_creams >= 5:
            users_ref = db.collection("users").where("email", "==", email).stream()
            for user in users_ref:
                user_ref = db.collection("users").document(user.id)
                user_ref.update({
                    f"{size}_ice_creams": firestore.Increment(-5),
                    "redemption_date": datetime.now().strftime("%Y-%m-%d"),
                    "expiration_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
                })
            return True
    return False

# Interfaz de la aplicación
st.title("🎉 Sistema de Recompensas - Helados Gratis 🍦")

if "user" not in st.session_state:
    menu = st.sidebar.selectbox("Selecciona una opción", ["Iniciar sesión", "Registrar usuario"])
    if menu == "Registrar usuario":
        st.subheader("Registro de usuario")
        new_email = st.text_input("Correo electrónico")
        new_password = st.text_input("Contraseña", type="password")
        if st.button("Registrar"):
            if new_email and new_password:
                register_user(new_email, new_password)
            else:
                st.error("Por favor, completa todos los campos.")

    if menu == "Iniciar sesión":
        st.subheader("Inicio de sesión")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            user = authenticate_user(email, password)
            if user:
                st.session_state["user"] = user
                st_autorefresh(interval=2000, key='refresh')
            else:
                st.error("Correo o contraseña incorrectos.")

else:
    user = st.session_state["user"]
    email = user["email"]
    user_data = get_user_data(email)
    
    small_ice_creams = user_data.get("small_ice_creams", 0)
    medium_ice_creams = user_data.get("medium_ice_creams", 0)
    
    st.write(f"Bienvenido, {email}")
    st.write("Helados pequeños:")
    st.write("".join(["🍦" if i < small_ice_creams else "⚪" for i in range(5)]))
    
    st.write("Helados medianos:")
    st.write("".join(["🍦" if i < medium_ice_creams else "⚪" for i in range(5)]))
    
    if small_ice_creams >= 5:
        if redeem_ice_cream(email, "small"):
            st.success("¡Has canjeado un helado pequeño! 🎉")
    if medium_ice_creams >= 5:
        if redeem_ice_cream(email, "medium"):
            st.success("¡Has canjeado un helado mediano! 🎉")

    if email == "nao.martinez2102@gmail.com":
        st.subheader("Administración de helados")
        target_email = st.text_input("Correo del usuario")
        size = st.selectbox("Tamaño del helado", ["small", "medium"])
        quantity = st.number_input("Cantidad", min_value=1, step=1)
        if st.button("Registrar helado comprado"):
            update_ice_cream_count(target_email, size, quantity)
            st.success(f"Se han registrado {quantity} helados {size} para {target_email}.")
