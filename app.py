import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Benin Lits", layout="wide")

# --- MOT DE PASSE ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

def check_password():
    if st.session_state["password_correct"]:
        return True
    st.title("🔒 Benin - Gestion des Lits - Privé")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Entrer"):
        if pwd == "Benin2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    return False

if not check_password():
    st.stop()

# --- TON APP ---
st.title("🏥 Benin - Gestion des Lits")
DATABASE_URL = st.secrets["DATABASE_URL"]

def get_conn():
    return psycopg2.connect(DATABASE_URL)

try:
    conn = get_conn()
    st.success("Connecté à Neon ✅")
    centres = pd.read_sql("SELECT * FROM centres", conn)
    st.subheader("Centres")
    st.dataframe(centres, use_container_width=True)
    lits = pd.read_sql("SELECT * FROM lits", conn)
    st.subheader("Lits")
    st.dataframe(lits, use_container_width=True)
    conn.close()
except Exception as e:
    st.error(f"Erreur: {e}")
