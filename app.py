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
    c4.metric("Distance Totale", f"{df_r['distance_km'].sum() if not df_r.empty else 0} km")
    colA,colB=st.columns(2)
    with colA:
        st.subheader("Répartition Motifs (Camembert)")
        if not df_r.empty:
            df_m=df_r['diagnostic'].value_counts()
            fig, ax=plt.subplots()
            ax.pie(df_m, labels=df_m.index, autopct='%1.1f%%')
            st.pyplot(fig)
    with colB:
        st.subheader("Lits")
        st.dataframe(df_c[['nom','lits_total','lits_occupes','dispo']], use_container_width=True)
        st.bar_chart(df_c.set_index('nom')['dispo'])
    st.divider()
    st.subheader("📄 Fiches Contre-Référence PDF")
    for _, row in df_r.iterrows():
        with st.expander(f"Fiche #{row['id']} - {row['diagnostic']} - {row['centre_depart']}->{row['centre_arrivee']} ({row['distance_km']} km)"):
            pdf=FPDF()
            pdf.add_page()
            pdf.set_font("Arial","B",16)
            pdf.cell(0,10,"FICHE CONTRE-REFERENCE",ln=True,align='C')
            pdf.ln(10)
            pdf.set_font("Arial","",12)
            pdf.multi_cell(0,8,f"Ref #{row['id']}\nDate: {row['date_heure']}\nPatiente: {row['sexe']} {row['age']} ans\nDiag: {row['diagnostic']}\nDe: {row['centre_depart']} Vers: {row['centre_arrivee']} ({row['distance_km']} km)\nDetails: {row['details']}\nStatut: {row['statut']}")
            pdf_bytes=pdf.output()
            st.download_button(f"Telecharger PDF #{row['id']}", data=pdf_bytes, file_name=f"fiche_{row['id']}.pdf", mime="application/pdf", key=f"dl{row['id']}")

elif page=="➕ Nouvelle Référence":
    st.title("➕ Nouvelle Référence")
    if "CS" not in st.session_state.centre:
        st.warning("Vous etes CHD/CNHU, vous ne pouvez que recevoir.")
        st.stop()
    conn=get_conn()
    df_dispo=pd.read_sql("SELECT nom, (lits_total - lits_occupes) as dispo FROM centres WHERE type!='CS' AND (lits_total - lits_occupes)>0",conn)
    st.info(f"Centre qui réfère : **{st.session_state.centre}**")
    with st.form("ref"):
        age=st.number_input("Age",0,100,24)
        sexe=st.selectbox("Sexe",["Femme","Homme"])
        diag=st.text_input("Motif","Eclampsie")
        if len(df_dispo)==0:
            st.error("Aucun lit dispo!")
            arr=None
        else:
            opts=[f"{r['nom']} ({r['dispo']} libres)" for _,r in df_dispo.iterrows()]
            lab=st.selectbox("Choisir le centre qui a un lit",opts)
            arr=lab.split(" (")[0]
        det=st.text_area("Details","Femme 24 ans, TA 180/110...")
        ok=st.form_submit_button("🚀 Envoyer")
        if ok and arr:
            dist=calc_dist(st.session_state.centre, arr)
            cur=conn.cursor()
            cur.execute('INSERT INTO "references" (age,sexe,diagnostic,centre_depart,centre_arrivee,details,distance_km) VALUES (%s,%s,%s,%s,%s,%s,%s)',(age,sexe,diag,st.session_state.centre,arr,det,dist))
            cur.execute("UPDATE centres SET lits_occupes=lits_occupes+1 WHERE nom=%s",(arr,))
            conn.commit()
            st.success(f"Envoyé à {arr} ! {dist} km.")
            st.balloons()
    conn.close()

else:
    st.title(f"📥 Réceptions pour {st.session_state.centre}")
    conn=get_conn()
    df=pd.read_sql(f'SELECT * FROM "references" WHERE centre_arrivee=\'{st.session_state.centre}\' ORDER BY date_heure DESC',conn)
    if df.empty:
        st.info("Aucune référence reçue")
    for _, row in df.iterrows():
        with st.container(border=True):
            st.markdown(f"**#{row['id']} {row['diagnostic']}** - {row['sexe']} {row['age']} ans - De {row['centre_depart']} - {row['distance_km']} km - **{row['statut']}**")
            st.write(row['details'])
            if row['statut']=='en_cours':
                c1,c2=st.columns(2)
                if c1.button(f"✅ Accepter {row['id']}",key=f"a{row['id']}"):
                    cur=conn.cursor()
                    cur.execute('UPDATE "references" SET statut=\'acceptee\' WHERE id=%s',(row['id'],))
                    conn.commit()
                    st.rerun()
                if c2.button(f"❌ Refuser {row['id']}",key=f"r{row['id']}"):
                    cur=conn.cursor()
                    cur.execute('UPDATE "references" SET statut=\'refusee\' WHERE id=%s',(row['id'],))
                    cur.execute("UPDATE centres SET lits_occupes=lits_occupes-1 WHERE nom=%s",(st.session_state.centre,))
                    conn.commit()
                    st.rerun()
    conn.close()
