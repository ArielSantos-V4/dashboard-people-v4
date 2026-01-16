import streamlit as st
import pandas as pd

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide",
    page_icon="🔴"
)

# ==============================
# ESTILO VISUAL (PRETO + VERMELHO)
# ==============================
st.markdown("""
<style>
.main {
    background-color: #0E1117;
    color: white;
}

section[data-testid="stSidebar"] {
    background-color: #111827;
}

div[data-testid="metric-container"] {
    background-color: #161B22;
    border: 1px solid #E30613;
    padding: 16px;
    border-radius: 12px;
}

h1, h2, h3 {
    color: #E30613;
}

.stButton > button {
    background-color: #E30613;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# LOGIN SIMPLES
# ==============================
def check_password(username, password):
    users = st.secrets["users"]

    if username not in users:
        return False, None

    return password == users[username]["password"], users[username]["name"]

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

# ==============================
# SIDEBAR
# ==============================
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# ==============================
# CARREGAR GOOGLE SHEETS (COMO ESTAVA)
# ==============================
@st.cache_data
def load_google_sheet():
    url = "https://docs.google.com/spreadsheets/d/13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY/export?format=csv&gid=2056973316"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

df = load_google_sheet()

# ==============================
# KPIs BÁSICOS (SEM ALTERAÇÕES)
# ==============================
st.title("📊 Dashboard People - V4 Company")
st.markdown("---")

headcount = len(df)

if "Modelo de contrato" in df.columns:
    pj = df[df["Modelo de contrato"].str.contains("PJ", case=False, na=False)].shape[0]
    clt = df[df["Modelo de contrato"].str.contains("CLT", case=False, na=False)].shape[0]
else:
    pj, clt = 0, 0

col1, col2, col3 = st.columns(3)

col1.metric("Headcount Total", headcount)
col2.metric("PJs", pj)
col3.metric("CLTs", clt)

st.markdown("---")

st.dataframe(df, use_container_width=True)
