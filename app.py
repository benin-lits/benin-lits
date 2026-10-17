import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px

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

st.sidebar.title("Bénin LITS")
menu = st.sidebar.radio("Navigation", ["Nouvelle Référence", "Liste Références", "Saisie Issue (CHD/ZH)", "Dashboard"])

# --- 1. NOUVELLE REF ---
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
        if st.form_submit_button("Envoyer"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO "references" (centre_emetteur, centre_receveur, motif, age, gestite, transport, date_reference) VALUES (%s,%s,%s,%s,%s,%s,NOW())',
                        (centre_em, centre_rec, motif, age, gestite, transport))
            conn.commit()
            conn.close()
            st.success("Envoyée !")

# --- 2. LISTE ---
elif menu == "Liste Références":
    df = get_data()
    st.title(f"📋 Liste - TOTAL {len(df)}")
    st.dataframe(df, use_container_width=True)

# --- 3. SAISIE ISSUE ---
elif menu == "Saisie Issue (CHD/ZH)":
    st.title("🩺 Clôturer - CHD/ZH")
    df = get_data()
    if df.empty:
        st.warning("Aucune donnée")
    else:
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne']:
            if col not in df.columns:
                df[col] = ""
        df_non = df[(df['issue_mere'].isna()) | (df['issue_mere']=="")]
        st.metric("En attente de clôture", len(df_non))
        id_ref = st.selectbox("ID à clôturer", df_non['id'].tolist() if not df_non.empty else [])
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

# --- 4. DASHBOARD = ANCIEN + NOUVEAUX KPI ---
elif menu == "Dashboard":
    df = get_data()
    if df.empty:
        st.warning("Pas de données")
    else:
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne']:
            if col not in df.columns:
                df[col] = ""
        
        # ===== ANCIEN DASHBOARD - ON GARDE TOUT =====
        st.title("📊 Dashboard")
        st.metric("TOTAL GÉNÉRAL DES RÉFÉRENCES", len(df))
        
        if 'motif' in df.columns:
            counts = df['motif'].value_counts().reset_index()
            counts.columns = ['Motif','Effectif']
            fig = px.bar(counts, x='Effectif', y='Motif', orientation='h', text='Effectif', title=f"Motifs (Total {len(df)})")
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        colA, colB = st.columns(2)
        with colA:
            if 'centre_emetteur' in df.columns:
                c = df['centre_emetteur'].value_counts().reset_index()
                c.columns = ['Centre','N']
                st.plotly_chart(px.bar(c, x='N', y='Centre', orientation='h', title="Par centre émetteur"), use_container_width=True)
        with colB:
            if 'centre_receveur' in df.columns:
                c = df['centre_receveur'].value_counts().reset_index()
                c.columns = ['Centre','N']
                st.plotly_chart(px.bar(c, x='N', y='Centre', orientation='h', title="Par centre receveur"), use_container_width=True)
        
        if 'transport' in df.columns:
            st.plotly_chart(px.pie(df, names='transport', title="Transport"), use_container_width=True)

        st.divider()
        
        # ===== NOUVEAUX KPI - AJOUTÉS EN DESSOUS =====
        st.subheader("🩺 NOUVEAU - Issues (Devenir après référence)")
        df_clot = df[df['issue_mere'].notna() & (df['issue_mere']!="")].copy()
        
        if df_clot.empty:
            st.info("Aucune issue saisie encore par le CHD/ZH. Utilisez le menu 'Saisie Issue'")
        else:
            st.write(f"**Taux de clôture: {len(df_clot)} / {len(df)} = {len(df_clot)/len(df)*100:.1f}%**")
            
            nb_vb = len(df_clot[df_clot['issue_accouchement']=='Voie basse'])
            nb_ces = len(df_clot[df_clot['issue_accouchement']=='Césarienne'])
            prop_ces = nb_ces/(nb_vb+nb_ces)*100 if (nb_vb+nb_ces)>0 else 0
            
            k1,k2,k3 = st.columns(3)
            k1.metric("Voie basse", nb_vb)
            k2.metric("Césarienne", nb_ces)
            k3.metric("Proportion Césarienne", f"{prop_ces:.1f}%")
            
            k4,k5,k6,k7 = st.columns(4)
            k4.metric("Mère Vivante", len(df_clot[df_clot['issue_mere']=='Vivante']))
            k5.metric("Mère Décédée", len(df_clot[df_clot['issue_mere']=='Décédée']))
            k6.metric("SCAM", len(df_clot[df_clot['issue_mere']=='Sortie contre avis médical']))
            k7.metric("Référée à nouveau", len(df_clot[df_clot['issue_mere']=='Référée à nouveau']))
            
            k8,k9,k10 = st.columns(3)
            k8.metric("NN Vivant", len(df_clot[df_clot['issue_nouveau_ne']=='Vivant']))
            k9.metric("NN Décédé", len(df_clot[df_clot['issue_nouveau_ne']=='Décédé']))
            k10.metric("Mort-né", len(df_clot[df_clot['issue_nouveau_ne']=='Mort-né']))
            
            c1,c2 = st.columns(2)
            with c1:
                fig_acc = px.pie(values=[nb_vb, nb_ces], names=['Voie basse','Césarienne'], title="Répartition accouchement")
                st.plotly_chart(fig_acc, use_container_width=True)
            with c2:
                fig_mere = px.pie(df_clot, names='issue_mere', title="Devenir Mère")
                st.plotly_chart(fig_mere, use_container_width=True)
