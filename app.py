import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from pathlib import Path

# ——————————————————————————————————————————————————————————————————
# Configuración de la página
# ——————————————————————————————————————————————————————————————————
st.set_page_config(page_title="HELADOS BAHAMA 🍦", layout="wide")
st.title("HELADOS BAHAMA 🍦")
st.subheader("Dashboard de Recompensas (Firebase)")

# ——————————————————————————————————————————————————————————————————
# 1) Ruta al JSON de credenciales
# ——————————————————————————————————————————————————————————————————
CRED_PATH = Path("/mnt/data/sample-firebase-ai-app-f887d-firebase-adminsdk-fbsvc-5f84f61125.json")
if not CRED_PATH.exists():
    st.error(f"❌ No encontré el JSON de credenciales en:\n{CRED_PATH}")
    st.stop()

# ——————————————————————————————————————————————————————————————————
# 2) Inicializar Firebase
# ——————————————————————————————————————————————————————————————————
try:
    cred_dict = json.loads(CRED_PATH.read_text())
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    st.success("✅ Firebase inicializado correctamente")
except Exception as e:
    st.error(f"❌ Error al inicializar Firebase:\n{e}")
    st.stop()

# ——————————————————————————————————————————————————————————————————
# 3) Conectar a Firestore
# ——————————————————————————————————————————————————————————————————
try:
    db = firestore.client()
    st.success("✅ Cliente Firestore creado")
except Exception as e:
    st.error(f"❌ Error al conectar con Firestore:\n{e}")
    st.stop()

# ——————————————————————————————————————————————————————————————————
# 4) Prueba: listar colecciones
# ——————————————————————————————————————————————————————————————————
try:
    cols = [c.id for c in db.collections()]
    if cols:
        st.write("📂 Colecciones en tu Firestore:")
        for c in cols:
            st.write(f"- {c}")
    else:
        st.info("📂 No hay colecciones en este proyecto.")
except Exception as e:
    st.error(f"❌ Error listando colecciones:\n{e}")

# ——————————————————————————————————————————————————————————————————
# (A partir de aquí, inserta tu lógica de helados/estrellas, QR, etc.)
# ——————————————————————————————————————————————————————————————————
