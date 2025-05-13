import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

st.set_page_config(layout="centered")
st.title("🧪 Diagnóstico Completo Firebase")

# 0) Muestra TODO lo que hay en secrets
st.subheader("🔍 Contenido de st.secrets")
st.json(st.secrets)

# 1) Método A: secretos por campo
st.subheader("1️⃣ Intento con st.secrets['firebase_credentials']")
try:
    cred_dict = dict(st.secrets["firebase_credentials"])
    raw_key = cred_dict.get("private_key", "")
    # Normalize newlines
    if "\\n" in raw_key:
        cred_dict["private_key"] = raw_key.replace("\\n", "\n")
        st.info("🔄 Normalicé los \\n literales a saltos de línea reales")
    st.code("private_key repr:\n" + repr(cred_dict["private_key"][:150]) + " …", language="python")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, name="from_fields")
    st.success("✅ Inicializado con campos individuales (app name='from_fields')")
    db = firestore.client(firebase_admin.get_app("from_fields"))
    st.write("→ Colecciones:", [c.id for c in db.collections()])
except Exception as e:
    st.error(f"❌ Falla método A:\n{e}")

# 2) Método B: JSON blob
st.subheader("2️⃣ Intento con st.secrets['firebase_key_json']")
try:
    blob = st.secrets["firebase_key_json"]
    st.code("json blob repr:\n" + repr(blob[:150]) + " …", language="python")
    data = json.loads(blob)
    cred = credentials.Certificate(data)
    firebase_admin.initialize_app(cred, name="from_blob")
    st.success("✅ Inicializado con JSON blob (app name='from_blob')")
    db2 = firestore.client(firebase_admin.get_app("from_blob"))
    st.write("→ Colecciones:", [c.id for c in db2.collections()])
except Exception as e:
    st.error(f"❌ Falla método B:\n{e}")
