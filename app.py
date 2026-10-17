import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Bénin LITS - Références", layout="wide")

# --- CONNEXION ---
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"] if "DATABASE_URL" in st.secrets else st.secrets["postgres"]["url"])

def get_data():
    conn = get_connection()
    df = pd.read_sql('SELECT * FROM "references" ORDER BY id DESC', conn)
    conn.close()
    return df

# --- MENU ---
menu = st.sidebar.radio("Menu", ["Nouvelle Référence", "Liste Références", "Saisie Issue (CHD/ZH)", "Dashboard"])

# 1. NOUVELLE REFERENCE
if menu == "Nouvelle Référence":
    st.title("📝 Nouvelle Référence")
    with st.form("ref_form"):
        col1,col2 = st.columns(2)
        with col1:
            centre_emetteur = st.text_input("Centre émetteur")
            motif = st.selectbox("Motif", ["Hémorragie","Pré-éclampsie/Eclampsie","Travail prolongé","Souffrance fœtale","Autre"])
            age = st.number_input("Âge", 14, 50)
        with col2:
            centre_receveur = st.selectbox("Centre receveur", ["CHD Mono","CHD Atacora","CHU-MEL","CHD Zou","CHD Ouémé","Autre"])
            gestite = st.text_input("Gestité/Parité")
            transport = st.selectbox("Transport", ["Ambulance","Moto","Véhicule perso"])
        
        if st.form_submit_button("Envoyer"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO "references" (centre_emetteur, centre_receveur, motif, age, gestite, transport, date_reference) VALUES (%s,%s,%s,%s,%s,%s,NOW())',
                        (centre_emetteur, centre_receveur, motif, age, gestite, transport))
            conn.commit()
            conn.close()
            st.success("Référence envoyée !")

# 2. LISTE
elif menu == "Liste Références":
    st.title("📋 Liste Références")
    df = get_data()
    st.dataframe(df, use_container_width=True)
    st.metric("TOTAL GENERAL", len(df))

# 3. SAISIE ISSUE - LE PLUS IMPORTANT V6.8
elif menu == "Saisie Issue (CHD/ZH)":
    st.title("🩺 Clôturer - Issue de la référence")
    st.info("Réservé au centre receveur (CHD/ZH) pour renseigner le devenir")
    
    df = get_data()
    if df.empty:
        st.warning("Aucune référence")
    else:
        # Liste des refs non clôturées
        df_non_clot = df[(df['issue_mere'].isna()) | (df['issue_mere'] == "")]
        st.write(f"{len(df_non_clot)} références en attente de clôture")
        
        id_ref = st.selectbox("Choisir ID à clôturer", df_non_clot['id'].tolist() if not df_non_clot.empty else [])
        
        if id_ref:
            ref = df[df['id']==id_ref].iloc[0]
            st.write(f"**Motif:** {ref['motif']} | **Centre:** {ref['centre_emetteur']} -> {ref['centre_receveur']}")
            
            c1,c2,c3 = st.columns(3)
            with c1:
                mere = st.selectbox("Mère", ["Vivante","Décédée","Sortie contre avis médical","Référée à nouveau","Évacuée"])
            with c2:
                acc = st.selectbox("Accouchement", ["Voie basse","Césarienne"])
            with c3:
                nn = st.selectbox("Nouveau-né", ["Vivant","Décédé","Mort-né"])
            
            if st.button("✅ Enregistrer l'issue", type="primary"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute('UPDATE "references" SET issue_mere=%s, issue_accouchement=%s, issue_nouveau_ne=%s, date_issue=NOW() WHERE id=%s',
                            (mere, acc, nn, id_ref))
                conn.commit()
                conn.close()
                st.success(f"Issue enregistrée pour référence {id_ref} !")
                st.balloons()

# 4. DASHBOARD V6.8 AVEC KPI ISSUES
elif menu == "Dashboard":
    st.title("📊 Dashboard V6.8")
    df = get_data()
    
    if df.empty:
        st.warning("Pas de données")
    else:
        total_general = len(df)
        st.metric("TOTAL GÉNÉRAL DES RÉFÉRENCES", total_general)
        st.divider()
        
        # Graph motifs
        if 'motif' in df.columns:
            motif_counts = df['motif'].value_counts().reset_index()
            motif_counts.columns = ['Motif','Effectif']
            fig1 = px.bar(motif_counts, x='Effectif', y='Motif', orientation='h', text='Effectif', title=f"Motifs de référence (Total {total_general})")
            fig1.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)
        
        st.divider()
        st.subheader("🩺 Issues - Devenir des patientes (Centre Receveur)")
        
        # Assurer colonnes
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne']:
            if col not in df.columns:
                df[col] = ""
        
        df_clot = df[df['issue_mere'].notna() & (df['issue_mere'] != "")].copy()
        
        if df_clot.empty:
            st.info("Aucune issue saisie pour le moment. Le CHD/ZH doit clôturer dans 'Saisie Issue'")
        else:
            st.write(f"**{len(df_clot)} références clôturées sur {total_general}** ({len(df_clot)/total_general*100:.1f}%)")
            
            # KPI Accouchement
            nb_vb = len(df_clot[df_clot['issue_accouchement'] == 'Voie basse'])
            nb_cesar = len(df_clot[df_clot['issue_accouchement'] == 'Césarienne'])
            total_acc = nb_vb + nb_cesar
            prop_cesar = nb_cesar/total_acc*100 if total_acc>0 else 0

            st.markdown("#### 🤰 Mode d'accouchement")
            k1,k2,k3 = st.columns(3)
            k1.metric("Voie basse", nb_vb)
            k2.metric("Césarienne", nb_cesar)
            k3.metric("Proportion Césarienne", f"{prop_cesar:.1f}%")
            
            fig_acc = px.pie(values=[nb_vb, nb_cesar], names=['Voie basse','Césarienne'], title="Répartition voie d'accouchement")
            st.plotly_chart(fig_acc, use_container_width=True)
            
            st.markdown("#### 👩 Mère")
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Vivante", len(df_clot[df_clot['issue_mere'] == 'Vivante']))
            m2.metric("Décédée", len(df_clot[df_clot['issue_mere'] == 'Décédée']))
            m3.metric("SCAM", len(df_clot[df_clot['issue_mere'] == 'Sortie contre avis médical']))
            m4.metric("Référée à nouveau", len(df_clot[df_clot['issue_mere'] == 'Référée à nouveau']))
            
            st.markdown("#### 👶 Nouveau-né")
            n1,n2,n3 = st.columns(3)
            n1.metric("Vivant", len(df_clot[df_clot['issue_nouveau_ne'] == 'Vivant']))
            n2.metric("Décédé", len(df_clot[df_clot['issue_nouveau_ne'] == 'Décédé']))
            n3.metric("Mort-né", len(df_clot[df_clot['issue_nouveau_ne'] == 'Mort-né']))
            
            # Tableau récap
            st.divider()
            st.dataframe(df_clot[['id','centre_emetteur','motif','issue_mere','issue_accouchement','issue_nouveau_ne','date_issue']], use_container_width=True)
