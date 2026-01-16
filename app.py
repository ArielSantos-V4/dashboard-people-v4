import streamlit as st
import pandas as pd
from datetime import datetime

# ==================================================
# CONFIGURAÇÃO DA PÁGINA
# ==================================================
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide",
    page_icon="🔴"
)

# ==================================================
# ESTILO VISUAL (PRETO + VERMELHO)
# ==================================================
st.markdown("""
<style>
.main { background-color: #0E1117; color: white; }
section[data-testid="stSidebar"] { background-color: #161A23; }
h1, h2, h3 { color: #E30613; }

div[data-testid="metric-container"] {
    background-color: #161A23;
    border: 1px solid #E30613;
    padding: 16px;
    border-radius: 12px;
}

.stButton > button {
    background-color: #E30613;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# LOGIN
# ==================================================
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

# ==================================================
# GOOGLE SHEETS
# ==================================================
@st.cache_data
def load_google_sheet():
    url = (
        "https://docs.google.com/spreadsheets/d/"
        "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
        "/export?format=csv&gid=2056973316"
    )
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

df = load_google_sheet()

# ==================================================
# IDENTIFICAÇÃO DE COLUNAS
# ==================================================
def find_column_exact(name):
    for col in df.columns:
        if col.lower() == name.lower():
            return col
    return None

def find_column_contains(keywords):
    for col in df.columns:
        for key in keywords:
            if key in col.lower():
                return col
    return None

# 🔴 AJUSTE PRINCIPAL AQUI
col_termino = (
    find_column_exact("Térm previsto") or
    find_column_contains(["térm", "termino", "término", "fim"])
)

col_admissao = find_column_contains(["admiss"])
col_tipo = find_column_contains(["tipo", "contrato"])

# ==================================================
# CONVERSÃO DE DATAS
# ==================================================
if col_admissao:
    df[col_admissao] = pd.to_datetime(df[col_admissao], errors="coerce", dayfirst=True)

if col_termino:
    df[col_termino] = pd.to_datetime(df[col_termino], errors="coerce", dayfirst=True)

# ==================================================
# KPIs
# ==================================================
hoje = pd.Timestamp.today().normalize()

headcount = df.shape[0]

# Média de admissões por mês
if col_admissao:
    admissoes_mes = (
        df.dropna(subset=[col_admissao])
        .groupby(df[col_admissao].dt.to_period("M"))
        .size()
    )
    media_admissoes = round(admissoes_mes.mean(), 1)
else:
    media_admissoes = 0

# Contratos a vencer (30 dias)
if col_termino:
    contratos_vencer = df[
        (df[col_termino].notna()) &
        (df[col_termino] >= hoje) &
        (df[col_termino] <= hoje + pd.Timedelta(days=30))
    ].shape[0]

    contratos_vencidos = df[
        (df[col_termino].notna()) &
        (df[col_termino] < hoje)
    ].shape[0]
else:
    contratos_vencer = 0
    contratos_vencidos = 0

# ==================================================
# SIDEBAR
# ==================================================
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# ==================================================
# DASHBOARD
# ==================================================
st.title("📊 Dashboard People — V4 Company")
st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headcount Total", headcount)
c2.metric("Média de Admissões / Mês", media_admissoes)
c3.metric("Contratos a Vencer (30 dias)", contratos_vencer)
c4.metric("Contratos Vencidos", contratos_vencidos)

# ==================================================
# GRÁFICO PJ / CLT / ESTÁGIO
# ==================================================
st.markdown("## 📌 Distribuição por Tipo de Contrato")

if col_tipo:
    tipo_df = df[col_tipo].value_counts().reset_index()
    tipo_df.columns = ["Tipo de Contrato", "Quantidade"]
    tipo_df["Percentual (%)"] = round(
        tipo_df["Quantidade"] / tipo_df["Quantidade"].sum() * 100, 1
    )

    st.dataframe(tipo_df, use_container_width=True)
    st.bar_chart(
        tipo_df.set_index("Tipo de Contrato")["Quantidade"],
        use_container_width=True
    )
else:
    st.warning("Coluna de tipo de contrato não encontrada.")

st.success("✅ Dashboard People estável, contratos funcionando e pronto para evoluir.")
