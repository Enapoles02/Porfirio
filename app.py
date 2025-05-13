import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from pathlib import Path

st.set_page_config(layout="centered")
st.title("🧪 Diagnóstico Firebase Credenciales")

# 1) Carga desde st.secrets
st.header("1. Inicialización desde st.secrets")
try:
    cred_secrets = dict(st.secrets["firebase_credentials"])
    # Normaliza newlines
    raw = cred_secrets.get("private_key", "")
    if "\\n" in raw:
        cred_secrets["private_key"] = raw.replace("\\n", "\n")
    cred = credentials.Certificate(cred_secrets)
    firebase_admin.initialize_app(cred, name="from_secrets")
    st.success("✅ Inicializado con st.secrets (app name='from_secrets')")
    db1 = firestore.client(firebase_admin.get_app("from_secrets"))
    st.write("→ Colecciones:", [c.id for c in db1.collections()])
except Exception as e:
    st.error(f"❌ Falló desde st.secrets:\n{e}")

# 2) Carga directa del JSON en /mnt/data
st.header("2. Inicialización desde JSON en disco")
json_path = Path("/mnt/data/sample-firebase-ai-app-f887d-firebase-adminsdk-fbsvc-5f84f61125.json")
if json_path.exists():
    try:
        data = json.loads(json_path.read_text())
        cred_file = credentials.Certificate(data)
        firebase_admin.initialize_app(cred_file, name="from_file")
        st.success("✅ Inicializado con archivo JSON (app name='from_file')")
        db2 = firestore.client(firebase_admin.get_app("from_file"))
        st.write("→ Colecciones:", [c.id for c in db2.collections()])
    except Exception as e:
        st.error(f"❌ Falló leyendo JSON en disco:\n{e}")
else:
    st.warning(f"⚠️ No encontré el JSON en {json_path}")
