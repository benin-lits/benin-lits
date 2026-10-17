import streamlit as st
import psycopg2
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import urllib.parse
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Benin Lits - V6.1 Filtre Date", layout="wide")

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
    st.title("🏥 Benin Lits V6.1")
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
    
    # --- FILTRE DATE ---
    st.write("### 📅 Filtre par Date")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        date_debut = st.date_input("Du", datetime.now() - timedelta(days=30))
    with col_f2:
        date_fin = st.date_input("Au", datetime.now())
    with col_f3:
        periode_rapide = st.selectbox("Raccourci", ["Personnalisé", "Aujourd'hui", "7 derniers jours", "Ce mois", "Tout"])

    if periode_rapide == "Aujourd'hui":
        date_debut = date_fin = datetime.now().date()
    elif periode_rapide == "7 derniers jours":
        date_debut = (datetime.now() - timedelta(days=7)).date()
    elif periode_rapide == "Ce mois":
        date_debut = datetime.now().replace(day=1).date()
    elif periode_rapide == "Tout":
        date_debut = datetime(2020,1,1).date()

    df_ref_all = pd.read_sql("SELECT * FROM benin_refs", conn)
    df_lits = pd.read_sql("SELECT * FROM lits", conn)
    
    # Filtrage
    if not df_ref_all.empty:
        df_ref_all['date_only'] = pd.to_datetime(df_ref_all['date']).dt.date
        df_ref = df_ref_all[(df_ref_all['date_only'] >= date_debut) & (df_ref_all['date_only'] <= date_fin)].copy()
    else:
        df_ref = df_ref_all

    st.caption(f"Données filtrées du {date_debut} au {date_fin} : {len(df_ref)} référence(s)")
    
    total_lits = df_lits["lits_total"].sum() if not df_lits.empty else 0
    total_occupes = df_lits["lits_occupes"].sum() if not df_lits.empty else 0
    total_dispo = total_lits - total_occupes
    taux_occ = round((total_occupes/total_lits*100) if total_lits>0 else 0, 1)
    cumul_dist_total = round(df_ref["distance_km"].sum() if not df_ref.empty else 0, 1)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Réf", len(df_ref))
    c2.metric("Total Lits", total_lits)
    c3.metric("Lits Occupés", total_occupes)
    c4.metric("Lits Dispo", total_dispo)
    c5.metric("Taux Occupation", f"{taux_occ} %")
    c6.metric("Cumul Distance", f"{cumul_dist_total} km")
    
    if df_ref.empty:
        st.info(f"Aucune donnée entre {date_debut} et {date_fin}")
    else:
        colA, colB = st.columns(2)
        with colA:
            st.write("### 🥧 Camembert - Motifs")
            motif_counts = df_ref["motif"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(motif_counts, labels=motif_counts.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        with colB:
            st.write("### 🛏️ Lits par Centre")
            df_lits["lits_dispo"] = df_lits["lits_total"] - df_lits["lits_occupes"]
            df_lits["taux_occ"] = round(df_lits["lits_occupes"]/df_lits["lits_total"]*100,1)
            st.dataframe(df_lits)
            st.bar_chart(df_lits.set_index("centre")[["lits_occupes","lits_dispo"]])

        st.write(f"### 📍 Cumul Distance par Centre ({date_debut} au {date_fin})")
        cumul_par_centre = df_ref.groupby("centre_origine")["distance_km"].agg(['count','sum']).reset_index()
        cumul_par_centre.columns = ["Centre", "Nb Références", "Cumul Distance (km)"]
        cumul_par_centre["Cumul Distance (km)"] = cumul_par_centre["Cumul Distance (km)"].round(1)
        st.dataframe(cumul_par_centre, use_container_width=True)
        st.bar_chart(cumul_par_centre.set_index("Centre")["Cumul Distance (km)"])

        st.write("### 📊 Détail Références Filtrées")
        st.dataframe(df_ref.sort_values("date", ascending=False))

    if st.button("🗑️ Vider données test"):
        cur=conn.cursor(); cur.execute("DELETE FROM benin_refs"); cur.execute("UPDATE lits SET lits_occupes=0"); conn.commit(); st.success("Vidé"); st.rerun()

elif menu == "Nouvelle Référence":
    st.subheader("Nouvelle Référence")
    dest = st.selectbox("Envoyer à", [c for c in CENTRES if CENTRES[c]["type"]!="CS"])
    motif = st.selectbox("Motif", ["Eclampsie","HPPI","HRP","Souffrance foetale","Dystocie","Autre"])
    age = st.number_input("Age", 0, 100, 24)
    sexe = st.selectbox("Sexe", ["Femme","Homme"])
    details = st.text_area("Détails", "TA 180/110, Convulsions")
    dist = haversine(CENTRES[centre_actuel]["lat"], CENTRES[centre_actuel]["lon"], CENTRES[dest]["lat"], CENTRES[dest]["lon"])
    st.info(f"Distance: {dist} km")
    if st.button("Envoyer"):
        cur=conn.cursor()
        cur.execute("INSERT INTO benin_refs (centre_origine, centre_dest, motif, age, sexe, details, distance_km) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (centre_actuel, dest, motif, age, sexe, details, dist))
        cur.execute("UPDATE lits SET lits_occupes = lits_occupes + 1 WHERE centre=%s", (dest,))
        conn.commit()
        st.success(f"Envoyé à {dest}")
        msg = f"🚨 REFERENCE: {centre_actuel}->{dest} ({dist}km) Motif:{motif} {sexe} {age}ans"
        st.markdown(f"[📲 WhatsApp](https://wa.me/?text={urllib.parse.quote(msg)})")

elif menu == "Mes Réceptions":
    st.subheader(f"Réceptions pour {centre_actuel}")
    df = pd.read_sql("SELECT * FROM benin_refs WHERE centre_dest=%s AND statut IN ('en_cours','accepte') ORDER BY date DESC", conn, params=(centre_actuel,))
    if df.empty: st.info("Aucune réception")
    else:
        for _, row in df.iterrows():
            with st.expander(f"#{row['id']} {row['motif']} de {row['centre_origine']} - {row['distance_km']}km"):
                st.write(f"{row['age']} / {row['sexe']} - {row['details']}")
                if row['statut']=='en_cours':
                    if st.button(f"✅ Accepter {row['id']}", key=f"acc{row['id']}"):
                        cur=conn.cursor(); cur.execute("UPDATE benin_refs SET statut='accepte' WHERE id=%s", (row['id'],)); conn.commit(); st.rerun()
                st.divider()
                st.write("**📝 Contre-référence**")
                issue = st.selectbox("Issue", ["Guérie","Décédée","Référée CNHU","Retour domicile"], key=f"iss{row['id']}")
                diag = st.text_input("Diag final", key=f"diag{row['id']}")
                trait = st.text_area("Traitement", key=f"tr{row['id']}")
                reco = st.text_area("Reco CS", key=f"reco{row['id']}")
                if st.button(f"📤 Envoyer CR {row['id']}", key=f"cr{row['id']}"):
                    cur=conn.cursor()
                    cur.execute("UPDATE benin_refs SET statut='contre_referee', contre_issue=%s, contre_diag=%s, contre_traitement=%s, contre_reco=%s, date_sortie=NOW() WHERE id=%s",
                                (issue, diag, trait, reco, row['id']))
                    cur.execute("UPDATE lits SET lits_occupes = GREATEST(lits_occupes-1,0) WHERE centre=%s", (centre_actuel,))
                    conn.commit(); st.success("Envoyée"); st.rerun()

elif menu == "Contre-références reçues":
    st.subheader(f"Contre-références pour {centre_actuel}")
    # Filtre date aussi ici
    d1 = st.date_input("Filtre du", datetime.now() - timedelta(days=30), key="cr_d1")
    d2 = st.date_input("Au", datetime.now(), key="cr_d2")
    df = pd.read_sql("SELECT * FROM benin_refs WHERE centre_origine=%s AND statut='contre_referee' ORDER BY date_sortie DESC", conn, params=(centre_actuel,))
    if not df.empty:
        df['date_sortie_only'] = pd.to_datetime(df['date_sortie']).dt.date
        df = df[(df['date_sortie_only'] >= d1) & (df['date_sortie_only'] <= d2)]
    if df.empty: st.info("Aucune")
    else: st.dataframe(df)

conn.close()
