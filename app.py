import streamlit as st
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin

# Inicializar Firebase si no está inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")  # Asegúrate de subir tu clave JSON
    initialize_app(cred)
db = firestore.client()

# Función para registrar un usuario
def register_user(email, password, role="user"):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        st.error("El usuario ya existe.")
        return
    db.collection("users").add({
        "email": email,
        "password": password,
        "role": role,
        "points": 0,
        "small_ice_creams": 0,
        "medium_ice_creams": 0
    })
    st.success("Usuario registrado exitosamente. Ahora puedes iniciar sesión.")

# Registrar usuario admin
register_user("nao.martinez2102@gmail.com", "adminpass", role="admin")

# Función para autenticar usuarios
def authenticate_user(email, password):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_data = user.to_dict()
        if user_data["password"] == password:
            return user_data
    return None

# Función para actualizar puntos
def update_points(email, points):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        user_ref.update({"points": firestore.Increment(points)})

# Función para obtener puntos de un usuario
def get_user_points(email):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        return user.to_dict().get("points", 0)
    return 0

# Función para asignar helados
def assign_ice_cream(email, size):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        if size == "small":
            user_ref.update({"small_ice_creams": firestore.Increment(1)})
        elif size == "medium":
            user_ref.update({"medium_ice_creams": firestore.Increment(1)})

# Interfaz de la aplicación
st.title("🎉 Sistema de Recompensas - Helados Gratis 🍦")

# Selección de acción
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
            st.success(f"Bienvenido, {user['email']}! Tienes {user['points']} puntos.")
        else:
            st.error("Correo o contraseña incorrectos.")

# Verificar si el usuario está autenticado
if "user" in st.session_state:
    user = st.session_state["user"]
    st.write(f"Puntos actuales: {get_user_points(user['email'])}")
    
    # Si es Naomi (admin), permitir ver usuarios y asignar helados
    if user.get("role") == "admin":
        st.subheader("Administración de usuarios")
        users = db.collection("users").stream()
        for u in users:
            user_data = u.to_dict()
            st.write(f"Usuario: {user_data['email']} - Puntos: {user_data['points']}")
            size = st.selectbox(f"Tipo de helado para {user_data['email']}", ["small", "medium"], key=u.id)
            if st.button(f"Asignar helado a {user_data['email']}", key=u.id):
                assign_ice_cream(user_data['email'], size)
                st.success(f"Se ha asignado un helado {size} a {user_data['email']}.")
    
    # Sección de canje de helados
    st.subheader("Canjear puntos por helados")
    current_points = get_user_points(user["email"])
    st.write("Cada 100 puntos equivalen a 1 helado.")
    if st.button("Canjear Small (100 puntos)"):
        if current_points >= 100:
            update_points(user["email"], -100)
            assign_ice_cream(user["email"], "small")
            st.success("¡Has canjeado un helado pequeño! 🍦")
        else:
            st.error("No tienes suficientes puntos.")
    if st.button("Canjear Medium (200 puntos)"):
        if current_points >= 200:
            update_points(user["email"], -200)
            assign_ice_cream(user["email"], "medium")
            st.success("¡Has canjeado un helado mediano! 🍦")
        else:
            st.error("No tienes suficientes puntos.")

