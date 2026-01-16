import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide",
    page_icon="🔴"
)

# --------------------------------------------------
# ESTILO (PRETO + VERMELHO)
# --------------------------------------------------
st.markdown("""
<style>
.main { background-color: #0e0e0e; }
h1, h2, h3 { color: #E30613; }
div[data-testid="metric-container"] {
    background-color: #1a1a1a;
    border: 1px solid #E30613;
    padding: 16px;
    border-radius: 12px;
}
section[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 2px solid #E30613;
}
.stButton > button {
    background-color: #E30613;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# LOGIN SIMPLES (st.secrets)
# --------------------------------------------------
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

# --------------------------------------------------
# GOOGLE SHEETS
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_google_sheet():
    sheet_id = "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
    gid = "2056973316"

    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?"
        f"gid={gid}&tqx=out:csv"
    )

    return pd.read_csv(url)

df = load_google_sheet()

# --------------------------------------------------
# TRATAMENTO DE DADOS
# --------------------------------------------------
df.columns = df.columns.str.strip()

# Datas
df["Térm previsto"] = pd.to_datetime(df["Térm previsto"], errors="coerce")
df["Data Início"] = pd.to_datetime(df["Data Início"], errors="coerce")

hoje = datetime.today()
prox_30_dias = hoje + timedelta(days=30)

# --------------------------------------------------
# KPIs
# --------------------------------------------------
headcount = len(df)

contratos_vencer = df[
    (df["Térm previsto"].notna()) &
    (df["Térm previsto"] >= hoje) &
    (df["Térm previsto"] <= prox_30_dias)
]

contratos_vencidos = df[
    (df["Térm previsto"].notna()) &
    (df["Térm previsto"] < hoje)
]

pj = len(df[df["Modelo de contrato"] == "PJ"])
clt = len(df[df["Modelo de contrato"] == "CLT"])
estagio = len(df[df["Modelo de contrato"] == "Estágio"])

# Média de admissões por mês
df_adm = df.dropna(subset=["Data de admissão"])
media_admissoes = (
    df_adm
    .groupby(df_adm["Data de admissão"].dt.to_period("M"))
    .size()
    .mean()
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
st.title("📊 Dashboard People — V4 Company")
st.markdown("---")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Headcount", headcount)
col2.metric("Contratos vencendo (30 dias)", len(contratos_vencer))
col3.metric("Contratos vencidos", len(contratos_vencidos))
col4.metric("PJ / CLT / Estágio", f"{pj} / {clt} / {estagio}")
col5.metric("Média admissões / mês", f"{media_admissoes:.1f}")

st.success("✅ Dashboard conectado ao Google Sheets com sucesso.")
