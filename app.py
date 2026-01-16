import streamlit as st
import pandas as pd

# ======================================================
# CONFIGURAÇÃO VISUAL — V4 (PRETO + VERMELHO)
# ======================================================
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide",
    page_icon="🔴"
)

st.markdown("""
<style>
.main { background-color: #0E0E0E; color: #FFFFFF; }
section[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 2px solid #E30613;
}
section[data-testid="stSidebar"] * { color: #FFFFFF; }
div[data-testid="metric-container"] {
    background-color: #161616;
    border: 1px solid #E30613;
    padding: 18px;
    border-radius: 14px;
}
h1, h2, h3 { color: #E30613; }
label, p, span { color: #FFFFFF !important; }
.stButton > button {
    background-color: #E30613;
    color: white;
    border-radius: 10px;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# LOGIN
# ======================================================
def check_password(username, password):
    users = st.secrets["users"]
    if username not in users:
        return False, None
    if password == users[username]["password"]:
        return True, users[username]["name"]
    return False, None

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Login — Dashboard People V4")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        valid, name = check_password(username, password)
        if valid:
            st.session_state.authenticated = True
            st.session_state.user_name = name
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# ======================================================
# FUNÇÃO GOOGLE SHEETS
# ======================================================
@st.cache_data(ttl=300)
def load_google_sheet():
    sheet_id = "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
    sheet_name = "Ativos"

    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?"
        f"tqx=out:csv&sheet={sheet_name}"
    )

    df = pd.read_csv(url)
    return df

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# ======================================================
# DASHBOARD
# ======================================================
st.title("📊 Dashboard People — V4 Company")
st.markdown("---")

df = load_google_sheet()

# ---------------- KPIs ----------------
headcount = len(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("👥 Headcount Total", headcount)
col2.metric("% PJ vs CLT", "—")
col3.metric("💰 Média Salarial", "—")
col4.metric("🚪 Total de Desligamentos", "—")

st.markdown("---")

st.subheader("📋 Base de Colaboradores (Ativos)")
st.dataframe(df, use_container_width=True)
