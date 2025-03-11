import streamlit as st
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin

# Inicializar Firebase si no está inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")  # Asegúrate de subir tu clave JSON
    initialize_app(cred)
db = firestore.client()

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

# Interfaz de la aplicación
st.title("🎉 Sistema de Recompensas - Helados Gratis 🍦")

# Login
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
    
    # Si es Master User, permitir asignar puntos
    if user.get("role") == "master":
        st.subheader("Asignar puntos a usuarios")
        target_email = st.text_input("Correo del usuario a premiar")
        points_to_add = st.number_input("Puntos a agregar", min_value=1, step=1)
        if st.button("Agregar puntos"):
            update_points(target_email, points_to_add)
            st.success(f"{points_to_add} puntos agregados a {target_email}.")
    
    # Sección de canje de helados
    st.subheader("Canjear puntos por helados")
    if st.button("Canjear 10 puntos por un helado"):
        current_points = get_user_points(user["email"])
        if current_points >= 10:
            update_points(user["email"], -10)
            st.success("¡Has canjeado un helado! 🍦")
        else:
            st.error("No tienes suficientes puntos.")
