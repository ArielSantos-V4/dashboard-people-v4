import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, date

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
# DATAS (TRATAMENTO DUPLO)
# --------------------------------------------------
df["Térm previsto_exibicao"] = df["Térm previsto"].astype(str)

df["Térm previsto"] = pd.to_datetime(df["Térm previsto"], errors="coerce")
df["Data Início"] = pd.to_datetime(df["Data Início"], errors="coerce")

df["Térm previsto_exibicao"] = (
    df["Térm previsto"]
    .dt.strftime("%d/%m/%Y")
    .fillna("")
)

df["Data Início_exibicao"] = df["Data Início"].dt.strftime("%d/%m/%Y").fillna("")

# --------------------------------------------------
# KPIs
# --------------------------------------------------
hoje = datetime.today()
prox_30_dias = hoje + timedelta(days=30)

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

df_adm = df.dropna(subset=["Data Início"])
media_admissoes = (
    df_adm
    .groupby(df_adm["Data Início"].dt.to_period("M"))
    .size()
    .mean()
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# --------------------------------------------------
# TOPO
# --------------------------------------------------
col_logo, col_title = st.columns([1, 6])

with col_logo:
    st.image("LOGO VERMELHO.png", width=120)

with col_title:
    st.markdown(
        "<h1>Dashboard People</h1><h3 style='color:#cccccc;'>V4 Company</h3>",
        unsafe_allow_html=True
    )

st.markdown("---")

# --------------------------------------------------
# KPIs
# --------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Headcount", headcount)
c2.metric("Contratos vencendo (30 dias)", len(contratos_vencer))
c3.metric("Contratos vencidos", len(contratos_vencidos))
c4.metric("PJ / CLT / Estágio", f"{pj} / {clt} / {estagio}")
c5.metric("Média admissões / mês", f"{media_admissoes:.1f}")

st.markdown("---")

# --------------------------------------------------
# GRÁFICOS
# --------------------------------------------------
g1, g2 = st.columns(2)

with g1:
    st.subheader("📃 Modelo de contrato")
    contrato_df = df["Modelo de contrato"].value_counts().reset_index()
    contrato_df.columns = ["Modelo", "Quantidade"]

    st.altair_chart(
        alt.Chart(contrato_df)
        .mark_arc(innerRadius=60)
        .encode(
            theta="Quantidade:Q",
            color=alt.Color(
                "Modelo:N",
                scale=alt.Scale(range=["#E30613", "#B0000A", "#FF4C4C"])
            ),
            tooltip=["Modelo", "Quantidade"]
        ),
        use_container_width=True
    )

with g2:
    st.subheader("📍 Local de atuação dos investidores")
    local_df = df["Unidade/Atuação"].dropna().value_counts().reset_index()
    local_df.columns = ["Local", "Quantidade"]

    st.altair_chart(
        alt.Chart(local_df)
        .mark_bar(color="#E30613")
        .encode(
            x=alt.X("Local:N", sort="-y", axis=alt.Axis(labelAngle=-30)),
            y="Quantidade:Q",
            tooltip=["Local", "Quantidade"]
        ),
        use_container_width=True
    )

# --------------------------------------------------
# ADMISSÕES
# --------------------------------------------------
st.subheader("📈 Admissões por mês")

adm_mes = (
    df_adm
    .assign(Mes=df_adm["Data Início"].dt.strftime("%b/%Y"))
    .groupby("Mes")
    .size()
    .reset_index(name="Quantidade")
)

st.altair_chart(
    alt.Chart(adm_mes)
    .mark_line(color="#E30613", point=True)
    .encode(x="Mes:N", y="Quantidade:Q", tooltip=["Mes", "Quantidade"]),
    use_container_width=True
)

# --------------------------------------------------
# CONSULTA INDIVIDUAL
# --------------------------------------------------
st.markdown("---")
st.subheader("🔎 Consulta individual do investidor")

df_consulta = df.fillna("")
lista_nomes = sorted(df_consulta["Nome"].unique())

nome = st.selectbox("Selecione o investidor", [""] + lista_nomes)

if nome:
    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Dados principais")
        st.text_input("BP", linha["BP"], disabled=True)
        st.text_input("Matrícula", linha["Matrícula"], disabled=True)
        st.text_input("Situação", linha["Situação"], disabled=True)
        st.text_input("Modelo de contrato", linha["Modelo de contrato"], disabled=True)
        st.text_input("Unidade de atuação", linha["Unidade/Atuação"], disabled=True)
        st.text_input("E-mail corporativo", linha["E-mail corporativo"], disabled=True)

    with col2:
        st.markdown("##### Dados pessoais")
        st.text_input("CPF", linha["CPF"], disabled=True)
        st.text_input("Nascimento", linha["Data de nascimento"], disabled=True)
        st.text_input("Escolaridade", linha["Escolaridade"], disabled=True)
        st.text_input("Telefone", linha["Telefone pessoal"], disabled=True)

# --------------------------------------------------
# TABELA
# --------------------------------------------------
st.markdown("### 📋 Base de investidores")

busca = st.text_input("🔍 Buscar na tabela")

df_tabela = df.copy()
df_tabela = df_tabela.fillna("")
df_tabela["Término do contrato"] = df_tabela["Térm previsto_exibicao"]
df_tabela["Data de início"] = df_tabela["Data Início_exibicao"]

if busca:
    df_tabela = df_tabela[
        df_tabela.astype(str)
        .apply(lambda x: x.str.contains(busca, case=False).any(), axis=1)
    ]

st.dataframe(
    df_tabela.drop(
        columns=["Térm previsto", "Térm previsto_exibicao", "Data Início", "Data Início_exibicao"],
        errors="ignore"
    ),
    use_container_width=True,
    hide_index=True
)
