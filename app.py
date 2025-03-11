import streamlit as st
import qrcode
import numpy as np
from io import BytesIO
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin
from datetime import datetime, timedelta
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import av

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

# Procesador de video para escanear QR en vivo sin OpenCV
class QRScanner(VideoTransformerBase):
    def __init__(self):
        self.scanned_email = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        return av.VideoFrame.from_ndarray(img, format="bgr24")

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
                db.collection("users").add({"email": new_email, "password": new_password, "stars": 0, "level": "Normal"})
                st.success("Usuario registrado exitosamente. Ahora puedes iniciar sesión.")
            else:
                st.error("Por favor, completa todos los campos.")

    if menu == "Iniciar sesión":
        st.subheader("Inicio de sesión")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            users_ref = db.collection("users").where("email", "==", email).stream()
            user = None
            for u in users_ref:
                user_data = u.to_dict()
                if user_data["password"] == password:
                    user = user_data
            if user:
                st.session_state["user"] = user
                st.experimental_rerun()
            else:
                st.error("Correo o contraseña incorrectos.")
else:
    user = st.session_state["user"]
    email = user["email"]
    
    st.write(f"Bienvenido, {email}")
    qr_code = generate_qr(email)
    st.image(qr_code, caption="Tu código QR para recompensas")

    if email == "nao.martinez2102@gmail.com":
        st.subheader("Escanear QR en vivo")
        ctx = webrtc_streamer(key="qr_scan", video_transformer_factory=QRScanner)
        st.info("La detección de QR aún no está implementada en este método.")
