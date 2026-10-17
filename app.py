import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Benin Lits", layout="wide")
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
except Exception as e:
  st.error(f"Erreur:{e}")

