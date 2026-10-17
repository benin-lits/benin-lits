import streamlit as st
import psycopg2
import pandas as pd
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import urllib.parse

# --- CONFIG ---
st.set_page_config(page_title="Benin Lits - V5", layout="wide")

# --- CENTRES AVEC GPS + LITS + MOTS DE PASSE ---
CENTRES = {
    "CS COVE": {"lat": 7.216, "lon": 2.336, "lits_total": 0, "password": "cove123", "type": "CS", "whatsapp": ""},
    "CS ZAGNANADO": {"lat": 7.278, "lon": 2.482, "lits_total": 0, "password": "zagna123", "type": "CS", "whatsapp": ""},
    "CS OUINHI": {"lat": 7.05, "lon": 2.48, "lits_total": 0, "password": "ouinhi123", "type": "CS", "whatsapp": ""},
    "CS DJIDJA": {"lat": 7.34, "lon": 1.93, "lits_total": 0, "password": "djidja123", "type": "CS", "whatsapp": ""},
    "CS ABOMEY": {"lat": 7.182, "lon": 1.99, "lits_total": 0, "password": "abomey123", "type": "CS", "whatsapp": ""},
    "CHD Zou Abomey": {"lat": 7.182, "lon": 1.99, "lits_total": 50, "password": "chd123", "type": "CHD", "whatsapp": "22990000000"},
    "CNHU Cotonou": {"lat": 6.36, "lon": 2.42, "lits_total": 30, "password": "cnhu123", "type": "CNHU", "whatsapp": "22990000001"},
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(2*R*asin(sqrt(a)),1)

def get_conn():
    # Mets ton DATABASE_URL dans Streamlit Secrets -> DATABASE_URL
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# --- INIT TABLES ---
def init_db():
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS references (
            id SERIAL PRIMARY KEY,
            date TIMESTAMP DEFAULT NOW(),
            centre_origine TEXT, centre_dest TEXT,
            motif TEXT, age INT, sexe TEXT, details TEXT,
            distance_km FLOAT, statut TEXT DEFAULT 'en_cours',
            contre_issue TEXT, contre_diag TEXT, 
            contre_traitement TEXT, contre_reco TEXT,
            date_sortie TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lits (
            centre TEXT PRIMARY KEY, lits_total INT, lits_occupes INT DEFAULT 0
        );
        """)
        for nom, info in CENTRES.items():
            if info["lits_total"]>0:
                cur.execute("INSERT INTO lits (centre,lits_total,lits_occupes) VALUES (%s,%s,0) ON CONFLICT (centre) DO NOTHING", (nom, info["lits_total"]))
        conn.commit(); conn.close()
    except Exception as e:
        st.error(f"DB Error: {e}")
init_db()

# --- LOGIN ---
if "centre" not in st.session_state:
    st.title("🏥 Benin Lits - Connexion V5")
    centre_choisi = st.selectbox("Je suis le centre", list(CENTRES.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == CENTRES[centre_choisi]["password"]:
            st.session_state.centre = centre_choisi
            st.rerun()
        else:
            st.error("Mot de passe incorrect pour "+centre_choisi)
    st.stop()

centre_actuel = st.session_state.centre
info_actuel = CENTRES[centre_actuel]
st.sidebar.success(f"Connecté: {centre_actuel}")
if st.sidebar.button("Déconnexion"):
    del st.session_state.centre; st.rerun()

menu = st.sidebar.radio("Menu", ["Dashboard", "Nouvelle Référence", "Mes Réceptions", "Contre-références reçues"])
conn = get_conn()

# --- DASHBOARD ---
if menu == "Dashboard":
    st.subheader(f"Dashboard - {centre_actuel}")
    df_ref = pd.read_sql("SELECT * FROM references", conn)
    df_lits = pd.read_sql("SELECT * FROM lits", conn)
    
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Références", len(df_ref))
    c2.metric("En cours", len(df_ref[df_ref.statut=='en_cours']) if not df_ref.empty else 0)
    c3.metric("Contre-référées", len(df_ref[df_ref.statut=='contre_referee']) if not df_ref.empty else 0)
    
    if not df_ref.empty:
        st.write("### Répartition Motifs (Camembert)")
        st.bar_chart(df_ref["motif"].value_counts()) # Simple, remplace pie pour vitesse
        st.dataframe(df_ref.tail(10))
    
    st.write("### Lits")
    st.dataframe(df_lits)
    df_lits["dispo"] = df_lits["lits_total"] - df_lits["lits_occupes"]
    st.bar_chart(df_lits.set_index("centre")[["dispo","lits_occupes"]])

# --- NOUVELLE REFERENCE ---
elif menu == "Nouvelle Référence":
    if info_actuel["type"] != "CS":
        st.warning("Vous êtes CHD/CNHU, vous ne pouvez que recevoir.")
    else:
        st.subheader("Nouvelle Référence")
        dest = st.selectbox("Envoyer à", [c for c in CENTRES if CENTRES[c]["type"]!="CS"])
        motif = st.selectbox("Motif", ["Eclampsie","HPPI","HRP","Souffrance foetale","Dystocie","Autre"])
        age = st.number_input("Age", 0, 100, 24)
        sexe = st.selectbox("Sexe", ["Femme","Homme"])
        details = st.text_area("Détails (TA, HR, etc)", "TA 180/110, Convulsions")
        
        # Calcul distance
        lat1, lon1 = info_actuel["lat"], info_actuel["lon"]
        lat2, lon2 = CENTRES[dest]["lat"], CENTRES[dest]["lon"]
        dist = haversine(lat1, lon1, lat2, lon2)
        st.info(f"Distance calculée: {dist} km")
        
        if st.button("Envoyer Référence"):
            cur = conn.cursor()
            cur.execute("INSERT INTO references (centre_origine, centre_dest, motif, age, sexe, details, distance_km) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (centre_actuel, dest, motif, age, sexe, details, dist))
            cur.execute("UPDATE lits SET lits_occupes = lits_occupes + 1 WHERE centre=%s", (dest,))
            conn.commit()
            st.success(f"Envoyé à {dest} | {dist} km.")
            
            # WHATSAPP AUTO
            msg = f"🚨 NOUVELLE REFERENCE\nDe: {centre_actuel} -> {dest} ({dist}km)\nMotif: {motif}\nPatiente: {sexe} {age} ans\nDetails: {details}\nAcceptez sur: https://benin-lits-cpirlywgfkcfazybs6nn29.streamlit.app"
            wa_link = f"https://wa.me/{CENTRES[dest]['whatsapp']}?text={urllib.parse.quote(msg)}" if CENTRES[dest]['whatsapp'] else f"https://wa.me/?text={urllib.parse.quote(msg)}"
            st.markdown(f"[📲 Envoyer WhatsApp au {dest}]({wa_link})", unsafe_allow_html=True)

# --- MES RECEPTIONS ---
elif menu == "Mes Réceptions":
    st.subheader(f"Réceptions pour {centre_actuel}")
    df = pd.read_sql("SELECT * FROM references WHERE centre_dest=%s AND statut='en_cours' ORDER BY date DESC", conn, params=(centre_actuel,))
    if df.empty:
        st.info("Aucune référence en cours")
    else:
        for _, row in df.iterrows():
            with st.expander(f"#{row['id']} {row['motif']} - {row['sexe']} {row['age']} ans - De {row['centre_origine']} - {row['distance_km']} km"):
                st.write(f"Détails: {row['details']}")
                col1,col2 = st.columns(2)
                if col1.button(f"✅ Accepter {row['id']}", key=f"acc{row['id']}"):
                    cur = conn.cursor()
                    cur.execute
