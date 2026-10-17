import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Bénin LITS", layout="wide")

# ===== 5 CENTRES + LITS PAR CENTRE (ton ancienne base) =====
CENTRES = {
    "CNHU Cotonou": "cnhu2024",
    "CHD Zou Abomey": "zou2024",
    "CHD Mono": "mono2024",
    "CHD Atacora": "atacora2024",
    "CHD Ouémé": "oueme2024",
    "ADMIN": "admin2024"
}
# CONFIG LITS - modifie selon ta vraie capacité
LITS_PAR_CENTRE = {
    "CNHU Cotonou": 30,
    "CHD Zou Abomey": 25,
    "CHD Mono": 15,
    "CHD Atacora": 15,
    "CHD Ouémé": 20
}

def get_connection():
    try:
        if "DATABASE_URL" in st.secrets:
            return psycopg2.connect(st.secrets["DATABASE_URL"])
        else:
            return psycopg2.connect(st.secrets["postgres"]["url"])
    except:
        return psycopg2.connect(st.secrets["DATABASE_URL"])

def get_data():
    conn = get_connection()
    df = pd.read_sql('SELECT * FROM "references" ORDER BY id DESC', conn)
    conn.close()
    return df

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Bénin LITS - Connexion")
    centre = st.selectbox("Centre", list(CENTRES.keys()))
    mdp = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        pwd_ok = (mdp == CENTRES.get(centre))
        if "passwords" in st.secrets and centre in st.secrets["passwords"]:
            pwd_ok = (mdp == st.secrets["passwords"][centre])
        if pwd_ok:
            st.session_state.auth = True
            st.session_state.centre = centre
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

st.sidebar.write(f"✅ {st.session_state.centre}")
if st.sidebar.button("Déconnexion"):
    st.session_state.auth = False
    st.rerun()

st.sidebar.title("Bénin LITS")
menu = st.sidebar.radio("Navigation", ["Nouvelle Référence", "Liste Références", "Saisie Issue (CHD/ZH)", "Dashboard"])

if menu == "Nouvelle Référence":
    st.title("📝 Nouvelle Référence")
    with st.form("ref"):
        c1,c2 = st.columns(2)
        with c1:
            centre_em = st.text_input("Centre émetteur", value=st.session_state.centre if st.session_state.centre!="ADMIN" else "")
            motif = st.selectbox("Motif", ["Hémorragie","Pré-éclampsie","Eclampsie","HRP","HPPI","Travail prolongé","Souffrance foetale","Rupture utérine","Autre"])
            age = st.number_input("Âge", 14, 50, 25)
        with c2:
            centre_rec = st.selectbox("Centre receveur", list(LITS_PAR_CENTRE.keys()))
            gestite = st.text_input("G/P")
            transport = st.text_input("Distance km", "10")
        if st.form_submit_button("Envoyer"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO "references" (centre_emetteur, centre_receveur, motif, age, gestite, transport, date_reference) VALUES (%s,%s,%s,%s,%s,%s,NOW())',
                        (centre_em, centre_rec, motif, age, gestite, transport))
            conn.commit()
            conn.close()
            st.success("Envoyée !")

elif menu == "Liste Références":
    df = get_data()
    if st.session_state.centre != "ADMIN":
        df = df[(df['centre_emetteur']==st.session_state.centre) | (df['centre_receveur']==st.session_state.centre)]
    st.title(f"📋 Liste - TOTAL {len(df)}")
    st.dataframe(df, use_container_width=True)

elif menu == "Saisie Issue (CHD/ZH)":
    st.title("🩺 Clôturer - CHD/ZH")
    df = get_data()
    if df.empty:
        st.warning("Aucune donnée")
    else:
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne']:
            if col not in df.columns:
                df[col] = ""
        if st.session_state.centre != "ADMIN":
            df = df[df['centre_receveur']==st.session_state.centre]
        df_non = df[(df['issue_mere'].isna()) | (df['issue_mere']=="")]
        st.metric("En attente", len(df_non))
        id_ref = st.selectbox("ID", df_non['id'].tolist() if not df_non.empty else [])
        if id_ref:
            c1,c2,c3 = st.columns(3)
            with c1:
                mere = st.selectbox("Mère", ["Vivante","Décédée","Sortie contre avis médical","Référée à nouveau","Évacuée"])
            with c2:
                acc = st.selectbox("Accouchement", ["Voie basse","Césarienne"])
            with c3:
                nn = st.selectbox("Nouveau-né", ["Vivant","Décédé","Mort-né"])
            if st.button("✅ Enregistrer", type="primary"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute('UPDATE "references" SET issue_mere=%s, issue_accouchement=%s, issue_nouveau_ne=%s, date_issue=NOW() WHERE id=%s',
                            (mere, acc, nn, int(id_ref)))
                conn.commit()
                conn.close()
                st.success("Issue enregistrée")

# ========= DASHBOARD AVEC OCCUPATION PAR CENTRE EN HAUT =========
elif menu == "Dashboard":
    df = get_data()
    if df.empty:
        st.warning("Pas de données")
    else:
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne','date_reference','transport']:
            if col not in df.columns:
                df[col] = ""
        if st.session_state.centre != "ADMIN":
            df = df[(df['centre_emetteur']==st.session_state.centre) | (df['centre_receveur']==st.session_state.centre)]
        
        st.subheader("📅 Filtre par Date")
        c_d1, c_d2, c_d3 = st.columns(3)
        with c_d1:
            date_du = st.date_input("Du", datetime.now() - timedelta(days=30))
        with c_d2:
            date_au = st.date_input("Au", datetime.now())
        with c_d3:
            racc = st.selectbox("Raccourci", ["Personnalisé","7 jours","30 jours","Aujourd'hui"])
        if racc == "7 jours": date_du = datetime.now().date() - timedelta(days=7)
        elif racc == "30 jours": date_du = datetime.now().date() - timedelta(days=30)
        elif racc == "Aujourd'hui": date_du = datetime.now().date()
        
        try:
            df['date_reference'] = pd.to_datetime(df['date_reference'], errors='coerce')
            df_filtre = df[(df['date_reference'].dt.date >= date_du) & (df['date_reference'].dt.date <= date_au)].copy()
        except:
            df_filtre = df.copy()
        
        df_filtre['transport_num'] = pd.to_numeric(df_filtre['transport'], errors='coerce').fillna(0)
        
        # === CALCUL GLOBAL ===
        total_ref = len(df_filtre)
        total_lits_global = sum(LITS_PAR_CENTRE.values())
        lits_occupes_global = total_ref
        lits_dispo_global = total_lits_global - lits_occupes_global
        taux_global = (lits_occupes_global/total_lits_global*100) if total_lits_global>0 else 0
        cumul_dist_totale = df_filtre['transport_num'].sum()
        
        st.markdown("### 🏥 Vue Globale")
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("Total Réf", total_ref)
        k2.metric("Total Lits", total_lits_global)
        k3.metric("Lits Occupés", lits_occupes_global)
        k4.metric("Lits Dispo", lits_dispo_global)
        k5.metric("Taux Occupation", f"{taux_global:.1f} %")
        k6.metric("Distance totale", f"{cumul_dist_totale:.1f} km")
        
        # === NOUVEAU: PAR CENTRE - TOTAL, OCCUPES, DISPO, TAUX ===
        st.markdown("### 🛏️ Détail par Centre - Lits / Occupation / Taux")
        rows = []
        for centre_nom, capacite in LITS_PAR_CENTRE.items():
            occupes = len(df_filtre[df_filtre['centre_receveur']==centre_nom])
            dispo = capacite - occupes
            taux = (occupes/capacite*100) if capacite>0 else 0
            rows.append({
                "Centre": centre_nom,
                "Total Lits": capacite,
                "Occupés": occupes,
                "Disponible": dispo,
                "Taux %": round(taux,1),
                "Distance cumul km": round(df_filtre[df_filtre['centre_emetteur']==centre_nom]['transport_num'].sum(),1)
            })
        df_centres = pd.DataFrame(rows)
        st.dataframe(df_centres, use_container_width=True, hide_index=True)
        
        c1,c2 = st.columns(2)
        with c1:
            fig_occ = px.bar(df_centres, x='Centre', y='Occupés', color='Taux %', text='Occupés', title="Lits Occupés par Centre")
            st.plotly_chart(fig_occ, use_container_width=True)
        with c2:
            fig_taux = px.bar(df_centres, x='Centre', y='Taux', text='Taux', title="Taux Occupation par Centre",color='Taux')
