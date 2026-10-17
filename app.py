import streamlit as st, psycopg2, pandas as pd, math, matplotlib.pyplot as plt
from fpdf import FPDF

st.set_page_config(page_title="Bénin Référence V4", page_icon="🚨", layout="wide")

COORDS = {
    'CS COVE': (7.19, 2.34), 'CS ZAGNANADO': (7.21, 2.48),
    'CS OUINHI': (7.03, 2.33), 'CS DJIDJA': (7.34, 1.93),
    'CS ABOMEY': (7.18, 1.99), 'CNHU Cotonou': (6.36, 2.42),
    'CHD Zou Abomey': (7.18, 1.99)
}

def calc_dist(a,b):
    if a not in COORDS or b not in COORDS: return 0
    lat1,lon1=COORDS[a]; lat2,lon2=COORDS[b]; R=6371
    dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    x=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return round(R*2*math.asin(math.sqrt(x)),1)

DB_URL = st.secrets["DB_URL"]
def get_conn(): return psycopg2.connect(DB_URL)

if "auth" not in st.session_state:
    st.session_state.auth=False; st.session_state.centre=None

if not st.session_state.auth:
    st.title("🚨 Connexion - Système Référence Zou")
    conn=get_conn()
    df=pd.read_sql("SELECT nom FROM centres",conn)
    conn.close()
    centre_choisi=st.selectbox("Je suis le centre :", df['nom'])
    pwd=st.text_input(f"Mot de passe pour {centre_choisi}", type="password")
    if st.button("Se connecter"):
        conn=get_conn()
        cur=conn.cursor()
        cur.execute("SELECT password FROM centres WHERE nom=%s",(centre_choisi,))
        res=cur.fetchone()
        conn.close()
        if res and pwd==res[0]:
            st.session_state.auth=True
            st.session_state.centre=centre_choisi
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

st.sidebar.success(f"Connecté: {st.session_state.centre}")
if st.sidebar.button("Déconnexion"):
    st.session_state.auth=False
    st.session_state.centre=None
    st.rerun()

page = st.sidebar.radio("Menu", ["📊 Dashboard", "➕ Nouvelle Référence", "📥 Mes Réceptions"])

if page=="📊 Dashboard":
    st.title("📊 Dashboard V4")
    conn=get_conn()
    df_c=pd.read_sql("SELECT * FROM centres WHERE type!='CS'",conn)
    df_c['dispo']=df_c['lits_total']-df_c['lits_occupes']
    df_r=pd.read_sql('SELECT * FROM "references"',conn)
    conn.close()
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Patientes Référées", len(df_r))
    c2.metric("Lits Dispo", df_c['dispo'].sum())
    c3.metric("En cours", len(df_r[df_r['statut']=='en_cours']) if not df_r.empty else 0)
    c4.metric("Distance Totale", f"{df_r
