import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, initialize_app

# Cargar credenciales desde Streamlit Secrets
firebase_config = st.secrets["firebase_credentials"]

# Inicializar Firebase si aún no está inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(firebase_config))
    initialize_app(cred)

st.success("✅ Firebase conectado exitosamente.")
