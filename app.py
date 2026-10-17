import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Bénin LITS - Références", layout="wide")

# --- CONNEXION ---
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

# --- SIDEBAR ---
st.sidebar.title("Bénin LITS")
menu = st.sidebar.radio("Navigation", ["Nouvelle Référence", "Liste Références", "Saisie Issue (CHD/ZH)", "Dashboard"])

df = get_data() if menu != "Nouvelle Référence" else pd.DataFrame()

# 1. NOUVELLE REFERENCE
if menu == "Nouvelle Référence":
    st.title("📝 Nouvelle Référence")
    with st.form("ref"):
        c1,c2 = st.columns(2)
        with c1:
            centre_em = st.text_input("Centre émetteur")
            motif = st.selectbox("Motif", ["Hémorragie","Pré-éclampsie/Eclampsie","Travail prolongé","Souffrance foetale","Rupture utérine","Autre"])
            age = st.number_input("Âge", 14, 50, 25)
        with c2:
            centre_rec = st.selectbox("Centre receveur", ["CHD Mono","CHD Atacora","CHU-MEL","CHD Zou","CHD Ouémé","CHD Plateau","Autre"])
            gestite = st.text_input("G/P")
            transport = st.selectbox("Transport", ["Ambulance","Moto","Véhicule perso"])
        submit = st.form_submit_button("Envoyer")
        if submit:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO "references" (centre_emetteur, centre_receveur, motif, age, gestite, transport, date_reference) VALUES (%s,%s,%s,%s,%s,%s,NOW())',
                        (centre_em, centre_rec, motif, age, gestite, transport))
            conn.commit()
            conn.close()
            st.success("Envoyée !")
            st.balloons()

# 2. LISTE
elif menu == "Liste Références":
    st.title(f"📋 Liste - TOTAL {len(df)}")
    st.dataframe(df, use_container_width=True)

# 3. SAISIE ISSUE
elif menu == "Saisie Issue (CHD/ZH)":
    st.title("🩺 Clôturer une référence - CHD/ZH")
    if df.empty:
        st.warning("Aucune donnée")
    else:
        # sécuriser colonnes
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne']:
            if col not in df.columns:
                df[col] = ""
        df_non = df[(df['issue_mere'].isna()) | (df['issue_mere']=="")]
        st.metric("En attente de clôture", len(df_non))
        id_ref = st.selectbox("ID à clôturer", df_non['id'].tolist() if not df_non.empty else [])
        if id_ref:
            row = df[df['id']==id_ref].iloc[0]
            st.info(f"Motif: {row['motif']} | De: {row['centre_emetteur']}")
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
                st.success(f"Issue {id_ref} enregistrée")

# 4. DASHBOARD V6.8 + TOTAL + ISSUES
elif menu == "Dashboard":
    st.title("📊 Dashboard V6.8")
    if df.empty:
        st.warning("Pas de données")
    else:
        st.metric("TOTAL GÉNÉRAL", len(df))
        # sécuriser
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne']:
            if col not in df.columns:
                df[col] = ""
        
        # Graph motifs
        if 'motif' in df.columns:
            counts = df['motif'].value_counts().reset_index()
            counts.columns = ['Motif','Effectif']
            fig = px.bar(counts, x='Effectif', y='Motif', orientation='h', text='Effectif', title=f"Motifs (Total {len(df)})")
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("🩺 Issues - Devenir")
        df_clot = df[df['issue_mere'].notna() & (df['issue_mere']!="")].copy()
        if df_clot.empty:
            st.info("Aucune issue saisie par CHD/ZH pour le moment")
        else:
            nb_vb = len(df_clot[df_clot['issue_accouchement']=='Voie basse'])
            nb_ces = len(df_clot[df_clot['issue_accouchement']=='Césarienne'])
            prop = nb_ces/(nb_vb+nb_ces)*100 if (nb_vb+nb_ces)>0 else 0
            a,b,c = st.columns(3)
            a.metric("Voie basse", nb_vb)
            b.metric("Césarienne", nb_ces)
            c.metric("% Césarienne", f"{prop:.1f}%")
            
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Mères Vivantes", len(df_clot[df_clot['issue_mere']=='Vivante']))
            m2.metric("Décédées", len(df_clot[df_clot['issue_mere']=='Décédée']))
            m3.metric("SCAM", len(df_clot[df_clot['issue_mere']=='Sortie contre avis médical']))
            m4.metric("Référée", len(df_clot[df_clot['issue_mere']=='Référée à nouveau']))
            
            n1,n2 = st.columns(2)
            n1.metric("NN Vivants", len(df_clot[df_clot['issue_nouveau_ne']=='Vivant']))
            n2.metric("NN Décédés", len(df_clot[df_clot['issue_nouveau_ne']=='Décédé']))
            
            fig2 = px.pie(df_clot, names='issue_accouchement', title="Voie d'accouchement")
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(df_clot[['id','motif','centre_emetteur','issue_mere','issue_accouchement','issue_nouveau_ne']], use_container_width=True)
