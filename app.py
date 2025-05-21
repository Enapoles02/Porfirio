import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="HELADOS BAHAMA 🍦", layout="wide")
st.title("HELADOS BAHAMA 🍦 — Test Firebase")

# Inicializar Firebase usando secrets TOML
try:
    creds = st.secrets["firebase_credentials"]
    cred = credentials.Certificate(dict(creds))
    firebase_admin.initialize_app(cred)
    st.success("✅ Firebase inicializado correctamente")
except Exception as e:
    st.error(f"❌ Error al inicializar Firebase: {e}")
    st.stop()

# Conectar a Firestore
try:
    db = firestore.client()
    collections = [col.id for col in db.collections()]
    st.write("📂 Colecciones disponibles en Firestore:", collections)
except Exception as e:
    st.error(f"❌ Error al acceder a Firestore: {e}")
