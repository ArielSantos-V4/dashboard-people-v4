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

/* Fundo principal */
.main {
    background-color: #0E0E0E;
    color: #FFFFFF;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 2px solid #E30613;
}

/* Texto sidebar */
section[data-testid="stSidebar"] * {
    color: #FFFFFF;
}

/* Cards KPI */
div[data-testid="metric-container"] {
    background-color: #161616;
    border: 1px solid #E30613;
    padding: 18px;
    border-radius: 14px;
}

/* Títulos */
h1, h2, h3 {
    color: #E30613;
}

/* Texto geral */
label, p, span {
    color: #FFFFFF !important;
}

/* Botões */
.stButton > button {
    background-color: #E30613;
    color: white;
    border-radius: 10px;
    border: none;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #FFFFFF;
}

button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom: 3px solid #E30613;
}

</style>
""", unsafe_allow_html=True)

# ======================================================
# LOGIN SIMPLES (USUÁRIOS EM st.secrets)
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

# ---------------- LOGIN ----------------
if not st.session_state.authenticated:
    st.title("🔐 Login — Dashboard People V4")

    username = st.text_input("Usuário (email)")
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
# DASHBOARD
# ======================================================
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.title("📊 Dashboard People — V4 Company")
st.markdown("---")

# ---------------- KPIs ----------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("👥 Headcount Total", "—")
col2.metric("📑 % PJ vs CLT", "—")
col3.metric("💰 Média Salarial", "—")
col4.metric("🚪 Total de Desligamentos", "—")

st.markdown("---")

st.success("✅ Login funcionando | 🎨 Tema V4 aplicado | 📊 Pronto para Google Sheets")
