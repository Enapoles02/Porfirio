import streamlit as st
import json

try:
    firebase_creds = json.loads(json.dumps(st.secrets["firebase_credentials"]))
    st.write("✅ Firebase credentials loaded successfully!")
except Exception as e:
    st.error(f"❌ Error parsing Firebase credentials: {e}")
