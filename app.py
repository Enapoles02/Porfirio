import streamlit as st
import qrcode
import numpy as np
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import av
from streamlit_autorefresh import st_autorefresh

# Inicializar Firebase si no está inicializado
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase_credentials"])  # Convertir AttrDict a dict
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Función para generar un QR
def generate_qr(data):
    qr = qrcode.make(data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# Función para generar la barra de progreso de estrellas
def generate_star_progress(stars, level):
    total_blocks = 10
    filled_stars = stars % 200 if level == "Green" else stars
    filled_blocks = min(total_blocks, filled_stars // 20)
    bar_color = "🟩" if level == "Green" else "🟨"
    star_bar = bar_color * filled_blocks + "⬜" * (total_blocks - filled_blocks)
    drink_emojis = "☕" * (filled_stars // 100)
    return f"<h3>Nivel: {level} | {star_bar} {drink_emojis}</h3>", filled_stars

# Función para generar la barra de progreso de helados
def generate_icecream_progress(helados):
    total_helados = 5
    filled_icecreams = min(total_helados, helados)
    icecream_bar = "🍦" * filled_icecreams + "⬜" * (total_helados - filled_icecreams)
    return f"<h3>{icecream_bar}</h3>"

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
                db.collection("users").add({"email": new_email, "password": new_password, "stars": 0, "level": "Green", "helados": 0})
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
                st_autorefresh(interval=3000, key='refresh')
            else:
                st.error("Correo o contraseña incorrectos.")
else:
    user = st.session_state["user"]
    email = user["email"]
    
    st.write(f"Bienvenido, {email}")

    if email != "nao.martinez2102@gmail.com":
        qr_code = generate_qr(email)
        st.image(qr_code, caption="Tu código QR para recompensas")
        star_bar, stars = generate_star_progress(user.get('stars', 0), user.get('level', 'Green'))
        st.markdown(star_bar, unsafe_allow_html=True)
        st.markdown(generate_icecream_progress(user.get('helados', 0)), unsafe_allow_html=True)
    
    if email == "nao.martinez2102@gmail.com":
        st.subheader("Escanear QR en vivo o ingresar correo manualmente")
        ctx = webrtc_streamer(key="qr_scan", video_transformer_factory=QRScanner)
        scanned_email = ctx.video_transformer.scanned_email if ctx.video_transformer else None
        manual_email = st.text_input("O ingresa el correo manualmente")
        selected_email = scanned_email if scanned_email else manual_email
        
        if selected_email:
            st.success(f"Correo seleccionado: {selected_email}")
            user_ref = db.collection("users").where("email", "==", selected_email).stream()
            selected_user = None
            for u in user_ref:
                selected_user = u.to_dict()
                user_doc = u.id
            
            if selected_user:
                st.subheader("Asignar recompensas")
                st.write("**Progreso de estrellas y helados:**")
                star_bar, stars = generate_star_progress(selected_user.get('stars', 0), selected_user.get('level', 'Green'))
                st.markdown(star_bar, unsafe_allow_html=True)
                st.markdown(generate_icecream_progress(selected_user.get('helados', 0)), unsafe_allow_html=True)
                
                purchase_amount = st.number_input("Monto de la compra (MXN)", min_value=0.0, step=0.1)
                add_helados = st.number_input("Añadir helados", min_value=0, step=1)
                calculated_stars = int(purchase_amount // 10)
                
                if st.button("Actualizar recompensas"):
                    new_stars = selected_user.get("stars", 0) + calculated_stars
                    new_helados = selected_user.get("helados", 0) + add_helados
                    if new_stars >= 200 and selected_user["level"] == "Green":
                        selected_user["level"] = "Oro"
                    db.collection("users").document(user_doc).update({"stars": new_stars, "helados": new_helados, "level": selected_user["level"]})
                    st.success("Recompensas actualizadas correctamente.")
                
                redeem_stars = st.number_input("Redimir bebidas", min_value=0, max_value=stars // 100, step=1)
                redeem_helados = st.number_input("Redimir helados", min_value=0, max_value=selected_user.get('helados', 0), step=1)
                
                if st.button("Redimir recompensa"):
                    db.collection("users").document(user_doc).update({"stars": selected_user["stars"] - (redeem_stars * 100), "helados": selected_user["helados"] - redeem_helados})
                    st.success("Recompensa redimida correctamente.")
            else:
                st.error("Usuario no encontrado en la base de datos.")
        else:
            st.info("Escanea un QR o ingresa el correo manualmente.")
