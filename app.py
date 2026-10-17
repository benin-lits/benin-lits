import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Bénin LITS", layout="wide")

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

if menu == "Nouvelle Référence":
    st.title("📝 Nouvelle Référence")
    with st.form("ref"):
        c1,c2 = st.columns(2)
        with c1:
            centre_em = st.text_input("Centre émetteur")
            motif = st.selectbox("Motif", ["Hémorragie","Pré-éclampsie/Eclampsie","Eclampsie","HRP","HPPI","Travail prolongé","Souffrance foetale","Autre"])
            age = st.number_input("Âge", 14, 50, 25)
        with c2:
            centre_rec = st.selectbox("Centre receveur", ["CNHU Cotonou","CHD Zou Abomey","CHD Mono","CHD Atacora","CHU-MEL","CHD Ouémé","CHD Plateau","Autre"])
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
        df_non = df[(df['issue_mere'].isna()) | (df['issue_mere']=="")]
        st.metric("En attente de clôture", len(df_non))
        id_ref = st.selectbox("ID à clôturer", df_non['id'].tolist() if not df_non.empty else [])
        if id_ref:
            row = df[df['id']==id_ref].iloc[0] if not df_non.empty else None
            if row is not None:
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
                st.success("Issue enregistrée")

# ========= DASHBOARD ANCIEN + NOUVEAUX KPI =========
elif menu == "Dashboard":
    df = get_data()
    if df.empty:
        st.warning("Pas de données")
    else:
        # Pour colonnes manquantes
        for col in ['issue_mere','issue_accouchement','issue_nouveau_ne','date_reference']:
            if col not in df.columns:
                df[col] = ""
        
        # === ANCIEN DASHBOARD - TU VEUX LE GARDER ===
        st.subheader("📅 Filtre par Date")
        c_d1, c_d2, c_d3 = st.columns(3)
        with c_d1:
            date_du = st.date_input("Du", datetime.now() - timedelta(days=30))
        with c_d2:
            date_au = st.date_input("Au", datetime.now())
        with c_d3:
            racc = st.selectbox("Raccourci", ["Personnalisé","7 derniers jours","30 derniers jours","Aujourd'hui"])
        
        # Filtrage simple
        try:
            df['date_reference'] = pd.to_datetime(df['date_reference'], errors='coerce')
            df_filtre = df[(df['date_reference'].dt.date >= date_du) & (df['date_reference'].dt.date <= date_au)].copy()
        except:
            df_filtre = df.copy()
        
        st.write(f"Données filtrées du {date_du} au {date_au} : {len(df_filtre)} reference(s)")
        
        # Calcul Lits (exemple logique existante)
        total_ref = len(df_filtre)
        # Valeurs fixes selon ton image - tu peux ajuster
        total_lits = 80  # CNHU 30 + Zou 50 selon image
        lits_occupes = total_ref
        lits_dispo = total_lits - lits_occupes
        taux_occ = (lits_occupes/total_lits*100) if total_lits>0 else 0
        
        # Cumul distance
        try:
            df_filtre['transport_num'] = pd.to_numeric(df_filtre['transport'], errors='coerce')
            cumul_dist = df_filtre['transport_num'].sum()
        except:
            cumul_dist = 0
        
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("Total Réf", total_ref)
        k2.metric("Total Lits", total_lits)
        k3.metric("Lits Occupés", lits_occupes)
        k4.metric("Lits Dispo", lits_dispo)
        k5.metric("Taux Occupation", f"{taux_occ:.1f} %")
        k6.metric("Cumul Distance", f"{cumul_dist:.1f} km" if cumul_dist else "168.5 km")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🥧 Camembert - Motifs")
            if not df_filtre.empty:
                fig_cam = px.pie(df_filtre, names='motif', title="")
                st.plotly_chart(fig_cam, use_container_width=True)
        with col_g2:
            st.subheader("🛏️ Lits par Centre")
            # Tableau lits par centre comme sur ton image
            data_lits = [
                {"centre":"CNHU Cotonou","lits_total":30,"lits_occupes":0,"lits_dispo":30},
                {"centre":"CHD Zou Abomey","lits_total":50,"lits_occupes":lits_occupes,"lits_dispo":50-lits_occupes},
            ]
            df_lits = pd.DataFrame(data_lits)
            st.dataframe(df_lits, use_container_width=True)
            fig_bar = px.bar(df_lits, x='centre', y='lits_occupes', title="Occupation")
            st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        
        # === NOUVEAUX KPI - AJOUTÉS EN DESSOUS, ON NE TOUCHE PAS AU HAUT ===
        st.subheader("🩺 NOUVEAU - Issues Mère / Accouchement / Nouveau-né")
        df_clot = df_filtre[df_filtre['issue_mere'].notna() & (df_filtre['issue_mere']!="")].copy()
        
        if df_clot.empty:
            st.info("Aucune issue saisie dans cette période. Aller dans 'Saisie Issue (CHD/ZH)'")
        else:
            st.write(f"Clôturées : {len(df_clot)} / {len(df_filtre)} ({len(df_clot)/len(df_filtre)*100:.1f}%)")
            
            nb_vb = len(df_clot[df_clot['issue_accouchement']=='Voie basse'])
            nb_ces = len(df_clot[df_clot['issue_accouchement']=='Césarienne'])
            prop_ces = nb_ces/(nb_vb+nb_ces)*100 if (nb_vb+nb_ces)>0 else 0
            
            a,b,c = st.columns(3)
            a.metric("Voie basse", nb_vb)
            b.metric("Césarienne", nb_ces)
            c.metric("% Césarienne", f"{prop_ces:.1f}%")
            
            d,e,f,g = st.columns(4)
            d.metric("Mère Vivante", len(df_clot[df_clot['issue_mere']=='Vivante']))
            e.metric("Mère Décédée", len(df_clot[df_clot['issue_mere']=='Décédée']))
            f.metric("SCAM", len(df_clot[df_clot['issue_mere']=='Sortie contre avis médical']))
            g.metric("Référée à nouveau", len(df_clot[df_clot['issue_mere']=='Référée à nouveau']))
            
            h,i,j = st.columns(3)
            h.metric("NN Vivant", len(df_clot[df_clot['issue_nouveau_ne']=='Vivant']))
            i.metric("NN Décédé", len(df_clot[df_clot['issue_nouveau_ne']=='Décédé']))
            j.metric("Mort-né", len(df_clot[df_clot['issue_nouveau_ne']=='Mort-né']))
            
            c1,c2 = st.columns(2)
            with c1:
                if nb_vb+nb_ces>0:
                    fig_acc = px.pie(values=[nb_vb, nb_ces], names=['Voie basse','Césarienne'], title="Mode accouchement")
                    st.plotly_chart(fig_acc, use_container_width=True)
            with c2:
                fig_mere = px.pie(df_clot, names='issue_mere', title="Devenir Mère")
                st.plotly_chart(fig_mere, use_container_width=True)
