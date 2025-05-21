import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random
import string

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Churreria & Helados App", layout="wide")
st.title("🎉 Programa de Recompensas")

# -------------------- FIREBASE INIT --------------------
try:
    creds = st.secrets["firebase_credentials"]
    cred = credentials.Certificate(dict(creds))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"❌ Firebase error: {e}")
    st.stop()

# -------------------- SESSION STATE --------------------
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

# -------------------- FUNCTIONS --------------------
def generate_cliente_id(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_user(identifier):
    doc = db.collection("usuarios").document(identifier).get()
    if doc.exists:
        return doc.to_dict()
    query = db.collection("usuarios").where("cliente_id", "==", identifier).limit(1).stream()
    for result in query:
        return result.to_dict()
    return None

def log_action(action_type, usuario, detalle=""):
    try:
        db.collection("logs").add({
            "accion": action_type,
            "usuario": usuario,
            "detalle": detalle,
            "fecha": datetime.now().isoformat()
        })
    except Exception as e:
        st.warning(f"⚠️ Error al guardar log: {e}")

def save_user(email, data):
    try:
        db.collection("usuarios").document(email).set(data)
        st.write(f"✅ Usuario guardado con email: {email}")
        log_action("registro", email)
    except Exception as e:
        st.error(f"❌ Error al guardar en Firestore: {e}")

def update_points(identifier, stars_add=0, helados_add=0):
    user = get_user(identifier)
    if not user:
        st.warning("Usuario no encontrado.")
        return
    user['estrellas'] += stars_add
    user['helados'] += helados_add
    recompensa_bebida = False

    if user['nivel'] == "green" and user['estrellas'] >= 200:
        user['nivel'] = "gold"
        user['estrellas'] = 0
        recompensa_bebida = True
    elif user['nivel'] == "gold":
        total_estrellas = user['estrellas']
        bebidas = total_estrellas // 100
        user['estrellas'] = total_estrellas % 100
        for _ in range(bebidas):
            recompensa_bebida = True
            log_action("recompensa", user['email'], "🎁 Bebida gratis por cada 100 estrellas en nivel oro")

    user['canjear_helado'] = user['helados'] >= 6
    save_user(user['email'], user)
    log_action("consumo", user['email'], f"+{stars_add} estrellas, +{helados_add} helados")

def canjear_helado(identifier):
    user = get_user(identifier)
    if not user:
        st.warning("Usuario no encontrado.")
        return
    if user['helados'] >= 6:
        user['helados'] -= 6
        user['canjear_helado'] = False
        save_user(user['email'], user)
        st.success("🎉 Helado canjeado exitosamente")
        log_action("canje", user['email'], "Canje de helado (6 helados)")
    else:
        st.warning("❌ No tiene suficientes helados para canjear")

def show_user_summary(user):
    st.markdown(f"**Correo:** {user['email']}")
    st.markdown(f"**Número de cliente:** {user.get('cliente_id', 'No asignado')}")
    st.markdown(f"**Nivel:** {'🥇 Gold' if user['nivel'] == 'gold' else '🥈 Green'}")
    progress_max = 100 if user['nivel'] == 'gold' else 200
    progress_value = min(user['estrellas'] / progress_max, 1.0)
    st.markdown("Estrellas acumuladas:")
    st.progress(progress_value, text=f"{user['estrellas']} / {progress_max}")
    st.markdown(f"**Helados acumulados:** 🍦 {user['helados']} / 6")
    if user['canjear_helado']:
        st.success("🎁 ¡Ya puede canjear un helado!")
        if st.button("Canjear helado ahora"):
            canjear_helado(user['email'])
