import streamlit as st
import pandas as pd
import altair as alt
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
# ESTILO
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

.consulta-box {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 16px;
    border: 3px solid #E30613;
    margin-top: 20px;
    color: #000000;
}

.consulta-box h3 {
    color: #E30613;
}

.consulta-item {
    margin-bottom: 8px;
    font-size: 14px;
}

.consulta-label {
    font-weight: bold;
    color: #444;
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
# LOGIN
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
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?gid={gid}&tqx=out:csv"
    return pd.read_csv(url)

df = load_google_sheet()
df.columns = df.columns.str.strip()

# --------------------------------------------------
# DATAS
# --------------------------------------------------
df["Térm previsto_exibicao"] = df["Térm previsto"].astype(str)
df["Térm previsto"] = pd.to_datetime(df["Térm previsto"], errors="coerce")
df["Data Início"] = pd.to_datetime(df["Data Início"], errors="coerce")

df["Térm previsto_exibicao"] = df["Térm previsto"].dt.strftime("%d/%m/%Y").fillna(df["Térm previsto_exibicao"])
df["Data Início_exibicao"] = df["Data Início"].dt.strftime("%d/%m/%Y")

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

# --------------------------------------------------
# TOPO
# --------------------------------------------------
col_logo, col_title = st.columns([1, 6])

with col_logo:
    st.image("LOGO VERMELHO.png", width=120)

with col_title:
    st.markdown("<h1>Dashboard People</h1><h3 style='color:#ccc'>V4 Company</h3>", unsafe_allow_html=True)

st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headcount", headcount)
c2.metric("Contratos vencendo (30 dias)", len(contratos_vencer))
c3.metric("Contratos vencidos", len(contratos_vencidos))
c4.metric("PJ / CLT / Estágio", f"{pj} / {clt} / {estagio}")

st.markdown("---")

# --------------------------------------------------
# CONSULTA INDIVIDUAL (DESTAQUE)
# --------------------------------------------------
st.subheader("🔎 Consulta individual do investidor")

df_tabela = df.copy()

df_tabela["Término do contrato"] = df_tabela["Térm previsto_exibicao"]
df_tabela["Data de início"] = df_tabela["Data Início_exibicao"]

df_tabela = df_tabela.sort_values("Nome")

nomes = sorted(df_tabela["Nome"].dropna().unique())

nome_selecionado = st.selectbox(
    "Digite ou selecione o nome do investidor",
    options=nomes
)

resultado = df_tabela[df_tabela["Nome"] == nome_selecionado]

if not resultado.empty:
    dados = resultado.iloc[0]

    st.markdown("<div class='consulta-box'>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Nome:</span> {dados.get('Nome','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Email:</span> {dados.get('Email','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Modelo de contrato:</span> {dados.get('Modelo de contrato','')}</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Data início:</span> {dados.get('Data de início','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Término:</span> {dados.get('Término do contrato','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Centro de custo:</span> {dados.get('Centro de custo','')}</div>", unsafe_allow_html=True)

    with col_c:
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Unidade / Atuação:</span> {dados.get('Unidade/Atuação','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='consulta-item'><span class='consulta-label'>Benefícios:</span> {dados.get('Benefícios','')}</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# TABELA (ORDEM ALFABÉTICA)
# --------------------------------------------------
st.markdown("### 📋 Base de investidores")

busca = st.text_input("🔍 Buscar na tabela")

if busca:
    df_filtrado = df_tabela[
        df_tabela.astype(str)
        .apply(lambda x: x.str.contains(busca, case=False, na=False).any(), axis=1)
    ]
else:
    df_filtrado = df_tabela

df_filtrado = df_filtrado.sort_values("Nome")

st.dataframe(
    df_filtrado.drop(
        columns=["Térm previsto", "Térm previsto_exibicao", "Data Início", "Data Início_exibicao"],
        errors="ignore"
    ),
    use_container_width=True,
    hide_index=True
)
