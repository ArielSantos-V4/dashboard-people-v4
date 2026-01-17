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
h1, h2, h3, h4 { color: #E30613; }
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
input[disabled] {
    color: white !important;
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
df = df.fillna("")

# --------------------------------------------------
# DATAS
# --------------------------------------------------
df["Térm previsto"] = pd.to_datetime(df["Térm previsto"], errors="coerce")
df["Data Início"] = pd.to_datetime(df["Data Início"], errors="coerce")

df["Térm previsto_exibicao"] = df["Térm previsto"].dt.strftime("%d/%m/%Y").fillna("")
df["Data Início_exibicao"] = df["Data Início"].dt.strftime("%d/%m/%Y").fillna("")

# --------------------------------------------------
# KPIs
# --------------------------------------------------
hoje = datetime.today()
prox_30_dias = hoje + timedelta(days=30)

headcount = len(df)
contratos_vencer = df[(df["Térm previsto"].notna()) & (df["Térm previsto"] <= prox_30_dias)]
contratos_vencidos = df[(df["Térm previsto"].notna()) & (df["Térm previsto"] < hoje)]

pj = len(df[df["Modelo de contrato"] == "PJ"])
clt = len(df[df["Modelo de contrato"] == "CLT"])
estagio = len(df[df["Modelo de contrato"] == "Estágio"])

df_adm = df[df["Data Início"].notna()]
media_admissoes = (
    df_adm.groupby(df_adm["Data Início"].dt.to_period("M")).size().mean()
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
    st.markdown("<h1>Dashboard People</h1><h3 style='color:#ccc;'>V4 Company</h3>", unsafe_allow_html=True)

st.markdown("---")

# --------------------------------------------------
# KPIs VISUAIS
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
            color=alt.Color("Modelo:N", scale=alt.Scale(range=["#E30613", "#B0000A", "#FF4C4C"])),
            tooltip=["Modelo", "Quantidade"]
        ),
        use_container_width=True
    )

with g2:
    st.subheader("📍 Local de atuação")
    local_df = df["Unidade/Atuação"].value_counts().reset_index()
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
    df_adm.assign(Mes=df_adm["Data Início"].dt.strftime("%b/%Y"))
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

df_consulta = df.copy().fillna("")
lista_nomes = sorted(df_consulta["Nome"].unique())

nome = st.selectbox("Selecione o investidor", [""] + lista_nomes)

def safe_val(linha, coluna):
    return linha[coluna] if coluna in linha else ""

def calcular_idade(data_nascimento):
    try:
        dn = pd.to_datetime(data_nascimento)
        hoje = date.today()
        return hoje.year - dn.year - ((hoje.month, hoje.day) < (dn.month, dn.day))
    except:
        return ""

def calcular_tempo_casa(data_inicio):
    try:
        di = pd.to_datetime(data_inicio)
        hoje = date.today()
        anos = hoje.year - di.year - ((hoje.month, hoje.day) < (di.month, di.day))
        meses = (hoje.month - di.month) % 12
        return f"{anos}a {meses}m"
    except:
        return ""

if nome:
    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]

    idade = calcular_idade(safe_val(linha, "Data de nascimento"))
    tempo_casa = calcular_tempo_casa(safe_val(linha, "Data Início"))

    col1, col2, col3 = st.columns([1.2, 1.2, 0.8])

    # ---------------- COLUNA 1 ----------------
    with col1:
        st.markdown("##### Dados principais")

        st.text_input("BP", safe_val(linha, "BP"), disabled=True)
        st.text_input("Matrícula", safe_val(linha, "Matrícula"), disabled=True)
        st.text_input("Situação", safe_val(linha, "Situação"), disabled=True)

        st.text_input("Data contrato", safe_val(linha, "Data Início_exibicao"), disabled=True)
        st.text_input("Término previsto", safe_val(linha, "Térm previsto_exibicao"), disabled=True)
        st.text_input("Modelo contrato", safe_val(linha, "Modelo de contrato"), disabled=True)

        st.text_input("Unidade", safe_val(linha, "Unidade/Atuação"), disabled=True)
        st.text_input("E-mail corporativo", safe_val(linha, "E-mail corporativo"), disabled=True)

        st.text_input("Tempo de casa", tempo_casa, disabled=True)

    # ---------------- COLUNA 2 ----------------
    with col2:
        st.markdown("##### Centro de custo")

        st.text_input("Centro de custo", safe_val(linha, "Centro de custo"), disabled=True)
        st.text_input("Descrição CC", safe_val(linha, "Descrição CC"), disabled=True)
        st.text_input("Senioridade", safe_val(linha, "Senioridade"), disabled=True)

        st.markdown("##### Dados pessoais")

        st.text_input("CPF", safe_val(linha, "CPF"), disabled=True)
        st.text_input("Data nascimento", safe_val(linha, "Data de nascimento"), disabled=True)
        st.text_input("Idade", idade, disabled=True)

        st.text_input("Escolaridade", safe_val(linha, "Escolaridade"), disabled=True)
        st.text_input("Telefone pessoal", safe_val(linha, "Telefone pessoal"), disabled=True)
        st.text_input("E-mail pessoal", safe_val(linha, "E-mail pessoal"), disabled=True)

    # ---------------- COLUNA 3 ----------------
    with col3:
        st.markdown("##### Benefícios")

        st.text_input("Situação plano", safe_val(linha, "Situação plano"), disabled=True)
        st.text_input("Operadora médico", safe_val(linha, "Operadora médico"), disabled=True)
        st.text_input("Carteirinha médico", safe_val(linha, "Carteirinha médico"), disabled=True)

        st.text_input("Operadora odonto", safe_val(linha, "Operadora odonto"), disabled=True)
        st.text_input("Carteirinha odonto", safe_val(linha, "Carteirinha odonto"), disabled=True)

        st.markdown("---")
        if safe_val(linha, "Link") != "":
            st.markdown(f"🔗 **[Abrir link]({linha['Link']})**", unsafe_allow_html=True)

# --------------------------------------------------
# TABELA
# --------------------------------------------------
st.markdown("### 📋 Base de investidores")

busca = st.text_input("🔍 Buscar na tabela")

df_tabela = df.copy()
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
