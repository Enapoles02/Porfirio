import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Prueba Firebase", layout="centered")
st.title("🔌 Prueba de Conexión a Firebase")

# 1. Cargar credenciales desde secrets.toml
try:
    cred_dict = dict(st.secrets["firebase_credentials"])
    st.success("✅ Credenciales cargadas desde st.secrets")
except Exception as e:
    st.error(f"❌ No se pudieron cargar las credenciales: {e}")
    st.stop()

# 2. Inicializar Firebase (sólo una vez)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        st.success("✅ Firebase inicializado correctamente")
    except Exception as e:
        st.error(f"❌ Error al inicializar Firebase: {e}")
        st.stop()
else:
    st.info("ℹ️ Firebase ya estaba inicializado")

# 3. Conectar a Firestore y listar colecciones
try:
    db = firestore.client()
    st.success("✅ Cliente Firestore creado")
    
    # Prueba de lectura: listar colecciones existentes
    col_ids = [col.id for col in db.collections()]
    if col_ids:
        st.write("📂 Colecciones en tu Firestore:")
        for cid in col_ids:
            st.write(f"- {cid}")
    else:
        st.write("📂 No se encontraron colecciones en Firestore.")
    
    st.balloons()
    st.success("🎉 Conexión a Firestore exitosa")
except Exception as e:
    st.error(f"❌ Error al conectar con Firestore: {e}")
