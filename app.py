import streamlit as st
import psycopg2
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import urllib.parse

st.set_page_config(page_title="Benin Lits - V5.1", layout="wide")

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
    R=6371
    dlat=radians(lat2-lat1); dlon=radians(lon2-lon1)
    a=sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(2*R*asin(sqrt(a)),1)

def get_conn():
    # Accepte DATABASE_URL ou DB_URL
    url = None
    if "DATABASE_URL" in st.secrets:
        url = st.secrets["DATABASE_URL"]
    elif "DB_URL" in st.secrets:
        url = st.secrets["DB_URL"]
    else:
        st.error("Ajoute DATABASE_URL dans Secrets"); st.stop()
    return psycopg2.connect(url)

def init_db():
    try:
        conn=get_conn(); cur=conn.cursor()
        # TABLE RENOMMEE benin_refs pour éviter le mot réservé
        cur.execute("""
        CREATE TABLE IF NOT EXISTS benin_refs (
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

if "centre" not in st.session_state:
    st.title("🏥 Benin Lits - Connexion V5.1")
    centre_choisi = st.selectbox("Je suis le centre", list(CENTRES.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == CENTRES[centre_choisi]["password"]:
            st.session_state.centre = centre_choisi; st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

centre_actuel = st.session_state.centre
info_actuel = CENTRES[centre_actuel]
st.sidebar.success(f"Connecté: {centre_actuel}")
if st.sidebar.button("Déconnexion"):
    del st.session_state.centre; st.rerun()

menu = st.sidebar.radio("Menu", ["Dashboard", "Nouvelle Référence", "Mes Réceptions", "Contre-références reçues"])
conn = get_conn()

if menu == "Dashboard":
    st.subheader(f"Dashboard - {centre_actuel}")
    df_ref = pd.read_sql("SELECT * FROM benin_refs", conn)
    df_lits = pd.read_sql("SELECT * FROM lits", conn)
    c1,c2,c3 = st.columns(3)
    c1.metric("Total", len(df_ref))
    c2.metric("En cours", len(df_ref[df_ref.statut=='en_cours']) if not df_ref.empty else 0)
    c3.metric("Contre-référées", len(df_ref[df_ref.statut=='contre_referee']) if not df_ref.empty else 0)
    if not df_ref.empty:
        st.bar_chart(df_ref["motif"].value_counts())
        st.dataframe(df_ref.tail(10))
    st.dataframe(df_lits)

elif menu == "Nouvelle Référence":
    if info_actuel["type"] != "CS":
        st.warning("Vous êtes CHD/CNHU, vous ne pouvez que recevoir.")
    else:
        st.subheader("Nouvelle Référence")
        dest = st.selectbox("Envoyer à", [c for c in CENTRES if CENTRES[c]["type"]!="CS"])
        motif = st.selectbox("Motif", ["Eclampsie","HPPI","HRP","Souffrance foetale","Dystocie","Autre"])
        age = st.number_input("Age", 0, 100, 24)
        sexe = st.selectbox("Sexe", ["Femme","Homme"])
        details = st.text_area("Détails", "TA 180/110, Convulsions")
        dist = haversine(info_actuel["lat"], info_actuel["lon"], CENTRES[dest]["lat"], CENTRES[dest]["lon"])
        st.info(f"Distance: {dist} km")
        if st.button("Envoyer Référence"):
            cur=conn.cursor()
            cur.execute("INSERT INTO benin_refs (centre_origine, centre_dest, motif, age, sexe, details, distance_km) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (centre_actuel, dest, motif, age, sexe, details, dist))
            cur.execute("UPDATE lits SET lits_occupes = lits_occupes + 1 WHERE centre=%s", (dest,))
            conn.commit()
            st.success(f"Envoyé à {dest}")
            msg = f"🚨 NOUVELLE REFERENCE De {centre_actuel} vers {dest} ({dist}km) Motif {motif} {sexe} {age}ans"
            st.markdown(f"[📲 Envoyer WhatsApp](https://wa.me/?text={urllib.parse.quote(msg)})")

elif menu == "Mes Réceptions":
    st.subheader(f"Réceptions pour {centre_actuel}")
    df = pd.read_sql("SELECT * FROM benin_refs WHERE centre_dest=%s AND statut='en_cours' ORDER BY date DESC", conn, params=(centre_actuel,))
    if df.empty:
        st.info("Aucune en cours")
    else:
        for _, row in df.iterrows():
            with st.expander(f"#{row['id']} {row['motif']} - De {row['centre_origine']} - {row['distance_km']} km"):
                st.write(row['details'])
                col1,col2 = st.columns(2)
                if col1.button(f"✅ Accepter {row['id']}", key=f"acc{row['id']}"):
                    cur=conn.cursor(); cur.execute("UPDATE benin_refs SET statut='accepte' WHERE id=%s", (row['id'],)); conn.commit(); st.rerun()
                if col2.button(f"❌ Refuser {row['id']}", key=f"ref{row['id']}"):
                    cur=conn.cursor(); cur.execute("UPDATE benin_refs SET statut='refuse' WHERE id=%s", (row['id'],)); cur.execute("UPDATE lits SET lits_occupes = GREATEST(lits_occupes-1,0) WHERE centre=%s", (centre_actuel,)); conn.commit(); st.rerun()
                st.divider()
                st.write("**📝 CONTRE-REFERENCE - Comment le centre qui a reçu va remplir**")
                issue = st.selectbox("Issue", ["Guérie","Décédée","Référée CNHU","Retour domicile"], key=f"iss{row['id']}")
                diag_final = st.text_input("Diagnostic final CHD", key=f"diag{row['id']}")
                traitement = st.text_area("Traitement réalisé", key=f"tr{row['id']}")
                reco = st.text_area("Recommandations pour le CS", key=f"reco{row['id']}")
                if st.button(f"📤 Envoyer Contre-référence {row['id']}", key=f"cr{row['id']}"):
                    cur=conn.cursor()
                    cur.execute("UPDATE benin_refs SET statut='contre_referee', contre_issue=%s, contre_diag=%s, contre_traitement=%s, contre_reco=%s, date_sortie=NOW() WHERE id=%s",
                                (issue, diag_final, traitement, reco, row['id']))
                    cur.execute("UPDATE lits SET lits_occupes = GREATEST(lits_occupes-1,0) WHERE centre=%s", (centre_actuel,))
                    conn.commit()
                    st.success(f"Contre-référence envoyée à {row['centre_origine']} !"); st.rerun()

elif menu == "Contre-références reçues":
    st.subheader(f"Contre-références reçues pour {centre_actuel}")
    df = pd.read_sql("SELECT * FROM benin_refs WHERE centre_origine=%s AND statut='contre_referee' ORDER BY date_sortie DESC", conn, params=(centre_actuel,))
    if df.empty:
        st.info("Aucune contre-référence")
    else:
        st.dataframe(df)

conn.close()
