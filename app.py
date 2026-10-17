import streamlit as st
import psycopg2
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import urllib.parse
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Benin Lits V6.3 Global+Filtre", layout="wide")

CENTRES = {
    "CS COVE": {"lat": 7.216, "lon": 2.336, "lits_total": 0, "password": "cove123", "type": "CS"},
    "CS ZAGNANADO": {"lat": 7.278, "lon": 2.482, "lits_total": 0, "password": "zagna123", "type": "CS"},
    "CS OUINHI": {"lat": 7.05, "lon": 2.48, "lits_total": 0, "password": "ouinhi123", "type": "CS"},
    "CS DJIDJA": {"lat": 7.34, "lon": 1.93, "lits_total": 0, "password": "djidja123", "type": "CS"},
    "CS ABOMEY": {"lat": 7.182, "lon": 1.99, "lits_total": 0, "password": "abomey123", "type": "CS"},
    "CHD Zou Abomey": {"lat": 7.182, "lon": 1.99, "lits_total": 50, "password": "chd123", "type": "CHD"},
    "CNHU Cotonou": {"lat": 6.36, "lon": 2.42, "lits_total": 30, "password": "cnhu123", "type": "CNHU"},
}

def haversine(lat1, lon1, lat2, lon2):
    R=6371; dlat=radians(lat2-lat1); dlon=radians(lon2-lon1)
    a=sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(2*R*asin(sqrt(a)),1)

def get_conn():
    url = st.secrets["DATABASE_URL"] if "DATABASE_URL" in st.secrets else st.secrets["DB_URL"]
    return psycopg2.connect(url)

def init_db():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS benin_refs (
        id SERIAL PRIMARY KEY, date TIMESTAMP DEFAULT NOW(),
        centre_origine TEXT, centre_dest TEXT, motif TEXT, age INT, sexe TEXT, details TEXT,
        distance_km FLOAT, statut TEXT DEFAULT 'en_cours',
        contre_issue TEXT, contre_diag TEXT, contre_traitement TEXT, contre_reco TEXT, date_sortie TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS lits (centre TEXT PRIMARY KEY, lits_total INT, lits_occupes INT DEFAULT 0);
    """)
    for nom, info in CENTRES.items():
        if info["lits_total"]>0:
            cur.execute("INSERT INTO lits (centre,lits_total,lits_occupes) VALUES (%s,%s,0) ON CONFLICT (centre) DO NOTHING", (nom, info["lits_total"]))
    conn.commit(); conn.close()
init_db()

if "centre" not in st.session_state:
    st.title("🏥 Benin Lits V6.3")
    c = st.selectbox("Je suis", list(CENTRES.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == CENTRES[c]["password"]:
            st.session_state.centre=c; st.rerun()
        else: st.error("Mot de passe incorrect")
    st.stop()

centre_actuel = st.session_state.centre
st.sidebar.success(f"Connecté: {centre_actuel}")
if st.sidebar.button("Déconnexion"): del st.session_state.centre; st.rerun()
menu = st.sidebar.radio("Menu", ["Dashboard", "Nouvelle Référence", "Mes Réceptions", "Contre-références reçues"])
conn = get_conn()

if menu == "Dashboard":
    st.subheader(f"Dashboard - {centre_actuel}")
    df_ref_all = pd.read_sql("SELECT * FROM benin_refs", conn)
    df_lits = pd.read_sql("SELECT * FROM lits", conn)

    # ===== POINT GLOBAL =====
    st.write("## 🌍 POINT GLOBAL - Tous centres, toutes dates")
    total_lits_g = df_lits["lits_total"].sum() if not df_lits.empty else 0
    total_occ_g = df_lits["lits_occupes"].sum() if not df_lits.empty else 0
    total_dispo_g = total_lits_g - total_occ_g
    taux_g = round((total_occ_g/total_lits_g*100) if total_lits_g>0 else 0,1)
    cumul_g = round(df_ref_all["distance_km"].sum() if not df_ref_all.empty else 0,1)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Réf", len(df_ref_all))
    c2.metric("Total Lits", total_lits_g)
    c3.metric("Lits Occupés", total_occ_g)
    c4.metric("Lits Dispo", total_dispo_g)
    c5.metric("Taux Occupation", f"{taux_g} %")
    c6.metric("Cumul Distance Total", f"{cumul_g} km")

    if not df_ref_all.empty:
        colA, colB = st.columns(2)
        with colA:
            st.write("### 🥧 Camembert Global - Motifs")
            motif_counts = df_ref_all["motif"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(motif_counts, labels=motif_counts.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        with colB:
            st.write("### 🛏️ Lits par Centre - Global")
            df_lits["lits_dispo"] = df_lits["lits_total"] - df_lits["lits_occupes"]
            df_lits["taux_occ"] = round(df_lits["lits_occupes"]/df_lits["lits_total"]*100,1)
            st.dataframe(df_lits)
        st.write("### 📍 Cumul Global par Centre")
        cumul_global = df_ref_all.groupby("centre_origine")["distance_km"].agg(['count','sum']).reset_index()
        cumul_global.columns = ["Centre", "Nb Réf", "Cumul km"]
        st.dataframe(cumul_global, use_container_width=True)

    st.divider()
    
    # ===== POINT FILTRE =====
    st.write("## 🔍 POINT FILTRÉ - Par Date / Centre / Niveau")
    f1,f2,f3,f4,f5 = st.columns(5)
    with f1: date_debut = st.date_input("Du", datetime.now() - timedelta(days=30), key="f_debut")
    with f2: date_fin = st.date_input("Au", datetime.now(), key="f_fin")
    with f3: niveau = st.selectbox("Niveau", ["Tous", "CS", "CHD", "CNHU"], key="f_niv")
    with f4: centre_filtre = st.selectbox("Centre Origine", ["Tous"] + list(CENTRES.keys()), key="f_centre")
    with f5: dest_filtre = st.selectbox("Destination", ["Tous"] + [c for c in CENTRES if CENTRES[c]["type"]!="CS"], key="f_dest")
    
    raccourci = st.selectbox("Raccourci", ["Personnalisé", "Aujourd'hui", "7 jours", "Ce mois", "Tout"], index=4)
    if raccourci == "Aujourd'hui": date_debut = date_fin = datetime.now().date()
    elif raccourci == "7 jours": date_debut = (datetime.now() - timedelta(days=7)).date()
    elif raccourci == "Ce mois": date_debut = datetime.now().replace(day=1).date()
    elif raccourci == "Tout": date_debut = datetime(2020,1,1).date()

    df_ref = df_ref_all.copy()
    if not df_ref.empty:
        df_ref['date_only'] = pd.to_datetime(df_ref['date']).dt.date
        df_ref = df_ref
