import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="🔧 Debug Firebase", layout="centered")
st.title("🔧 Debug de Conexión Firebase")

# 1) Cargar credenciales brute-force
try:
    cred_dict = dict(st.secrets["firebase_credentials"])
    st.success("✅ Credenciales cargadas desde st.secrets")
except Exception as e:
    st.error(f"❌ No se pudieron cargar las credenciales: {e}")
    st.stop()

# 2) Mostrar repr de private_key para debug
raw_key = cred_dict.get("private_key", "")
st.markdown("**Raw `private_key` load repr:**")
st.code(repr(raw_key[:100]) + " … " + repr(raw_key[-100:]), language="python")

# 3) Normalizar newlines si vienen como '\\n'
if "\\n" in raw_key:
    st.info("ℹ️ Se han detectado barras-n literales; normalizando a saltos de línea reales.")
    raw_key = raw_key.replace("\\n", "\n")
    cred_dict["private_key"] = raw_key

# 4) Intentar inicializar Firebase
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

# 5) Conectar a Firestore y listar colecciones
try:
    db = firestore.client()
    st.success("✅ Cliente Firestore creado")

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
    st.error(f"❌ Error al conectar con Firestore: {e")
