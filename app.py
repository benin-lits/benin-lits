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

# --- DASHBOARD ---
st.title("🏥 Benin - Dashboard Lits")
DATABASE_URL = st.secrets["DATABASE_URL"]

def get_conn():
    return psycopg2.connect(DATABASE_URL)

try:
    conn = get_conn()
    
    # Données
    centres = pd.read_sql("SELECT * FROM centres", conn)
    lits = pd.read_sql("SELECT * FROM lits", conn)
    
    # Jointure
    df = pd.merge(lits, centres, left_on="centre_id", right_on="id", suffixes=('', '_centre'))
    
    # --- METRIQUES EN HAUT ---
    total_lits = df['total'].sum() if not df.empty else 0
    total_occupes = df['occupes'].sum() if not df.empty else 0
    total_dispo = total_lits - total_occupes
    taux = (total_occupes/total_lits*100) if total_lits >0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🛏️ Total Lits", total_lits)
    col2.metric("🔴 Occupés", total_occupes)
    col3.metric("🟢 Disponibles", total_dispo)
    col4.metric("📈 Taux Occupation", f"{taux:.1f}%")

    st.divider()

    # --- GRAPHIQUES ---
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("Par Centre")
        if not df.empty:
            st.bar_chart(df.set_index('nom')['total'])
    
    with colB:
        st.subheader("Par Département")
        if not df.empty:
            par_dep = df.groupby('departement')['total'].sum()
            st.bar_chart(par_dep)

    # --- TABLEAU DETAILLE ---
    st.subheader("Détail")
    st.dataframe(df[['nom','commune','departement','total','occupes']], use_container_width=True)

    # --- ALERTES ---
    pleins = df[df['total'] == df['occupes']]
    if not pleins.empty:
        st.warning(f"🚨 {len(pleins)} centre(s) complet(s): {', '.join(pleins['nom'].tolist())}")

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
