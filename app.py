# --- MOT DE PASSE POUR RENDRE PRIVE ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Benin2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("🔒 Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Mot de passe", type="password", on_change=password_entered, key="password")
        st.error("Mot de passe incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- TON APP (corrigée sans warning) ---
st.set_page_config(page_title="Benin Lits", layout="wide")
st.title("🏥 Benin - Gestion des Lits")

DATABASE_URL = st.secrets["DATABASE_URL"]

def get_conn():
    return psycopg2.connect(DATABASE_URL)

try:
    conn = get_conn()
    st.success("Connecté à Neon ✅")

    centres = pd.read_sql("SELECT * FROM centres", conn)
    st.subheader("Centres")
    st.dataframe(centres, width='stretch')

    lits = pd.read_sql("SELECT * FROM lits", conn)
    st.subheader("Lits")
    st.dataframe(lits, width='stretch')

    conn.close()
except Exception as e:
    st.error(f"Erreur: {e}")
