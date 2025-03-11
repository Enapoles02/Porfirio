import streamlit as st
import qrcode
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from io import BytesIO
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# Inicializar Firebase si no está inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase_credentials"])
    initialize_app(cred)
db = firestore.client()

# Función para generar un QR
def generate_qr(data):
    qr = qrcode.make(data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# Función para escanear QR desde la cámara
def scan_qr_camera():
    cap = cv2.VideoCapture(0)
    scanned_email = None
    st.write("Escaneando... Apunta la cámara al QR")
    while scanned_email is None:
        ret, frame = cap.read()
        if not ret:
            break
        qr_codes = decode(frame)
        for qr in qr_codes:
            scanned_email = qr.data.decode('utf-8')
            break
        cv2.imshow("Escaneo QR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    return scanned_email

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
        "medium_ice_creams": 0,
        "stars": 0,
        "level": "Normal"
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

# Función para obtener información del usuario
def get_user_data(email):
    users_ref = db.collection("users").where("email", "==", email).stream()
    user_data = None
    for user in users_ref:
        user_data = user.to_dict()
        break  # Solo tomamos el primer usuario encontrado
    
    if not user_data:
        return {"email": email, "small_ice_creams": 0, "medium_ice_creams": 0, "stars": 0, "level": "Normal"}
    
    return user_data

# Función para actualizar el conteo de helados
def update_ice_cream_count(email, size, quantity):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        if size == "small":
            user_ref.update({"small_ice_creams": firestore.Increment(quantity)})
        elif size == "medium":
            user_ref.update({"medium_ice_creams": firestore.Increment(quantity)})

# Función para registrar estrellas
def add_stars(email, amount):
    stars_to_add = amount // 10
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        user_data = user.to_dict()
        new_star_count = user_data.get("stars", 0) + stars_to_add
        level = "Oro" if new_star_count >= 200 else "Normal"
        user_ref.update({"stars": new_star_count, "level": level})

# Función para canjear bebida gratis
def redeem_drink(email):
    users_ref = db.collection("users").where("email", "==", email).stream()
    for user in users_ref:
        user_ref = db.collection("users").document(user.id)
        user_data = user.to_dict()
        if user_data.get("level", "Normal") == "Oro" and user_data.get("stars", 0) >= 100:
            user_ref.update({"stars": firestore.Increment(-100)})
            st.success("¡Has canjeado una bebida gratis! ☕")

# Interfaz de la aplicación
st.title("HELADOS BAHAMA 🍦")
st.subheader("CHURRERÍA PORFIRIO ☕")

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
    
    st.write(f"Bienvenido, {email}")
    st.write(f"Nivel: {user_data.get('level', 'Normal')}")
    st.write(f"Estrellas: {user_data.get('stars', 0)} ⭐")
    
    qr_code = generate_qr(email)
    st.image(qr_code, caption="Tu código QR para recompensas")
    
    if user_data.get("level") == "Oro" and user_data.get("stars", 0) >= 100:
        if st.button("Canjear bebida gratis ☕"):
            redeem_drink(email)
    
    if email == "nao.martinez2102@gmail.com":
        st.subheader("Escanear QR desde la cámara para administrar usuario")
        if st.button("Escanear QR con cámara"):
            scanned_email = scan_qr_camera()
            if scanned_email:
                st.success(f"Correo escaneado: {scanned_email}")
            else:
                st.error("No se detectó un QR válido.")
