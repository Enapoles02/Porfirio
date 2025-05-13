import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

st.set_page_config(page_title="HELADOS BAHAMA 🍦", layout="wide")
st.title("HELADOS BAHAMA 🍦 — Test Firebase")

# 1) Cargar el blob JSON de secrets
try:
    blob = st.secrets["firebase_key_json"]
    creds_dict = json.loads(blob)
    st.success("✅ JSON de credenciales cargado desde secrets")
except Exception as e:
    st.error(f"❌ No pude leer firebase_key_json: {e}")
    st.stop()

# 2) Inicializar Firebase
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
        st.success("✅ Firebase inicializado correctamente")
    except Exception as e:
        st.error(f"❌ Error al inicializar Firebase: {e}")
        st.stop()
else:
    st.info("ℹ️ Firebase ya estaba inicializado")

# 3) Conectar a Firestore y listar colecciones
try:
    db = firestore.client()
    cols = [c.id for c in db.collections()]
    st.write("📂 Colecciones en Firestore:", cols)
except Exception as e:
    st.error(f"❌ Error al conectar a Firestore: {e}")
    st.stop()
