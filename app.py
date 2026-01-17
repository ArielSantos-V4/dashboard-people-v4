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

/* =========================
   CONSULTA INDIVIDUAL — COMPACTAÇÃO REAL
   ========================= */

/* Títulos das seções */
h5 {
    font-size: 20px !important;
    margin-top: 6px !important;
    margin-bottom: 2px !important;
}

/* Label */
label {
    font-size: 10px !important;
    margin-bottom: 0px !important;
    color: #bdbdbd !important;
}

/* 🔥 CONTAINER DO INPUT (o retângulo) */
div[data-testid="stTextInput"] {
    height: 30px !important;
}

/* 🔥 INPUT REAL */
div[data-testid="stTextInput"] input {
    height: 40px !important;
    padding: 10px 10px !important;
    font-size: 12px !important;
    line-height: 0px !important; /* 👈 CENTRALIZA O TEXTO */
}

/* Remove espaço entre campos */
div[data-testid="stTextInput"] {
    margin-bottom: 25px !important;
}

/* Remove respiro extra das colunas */
div[data-testid="column"] {
    padding-top: 5px !important;
    padding-bottom: 0px !important;
}

/* Benefícios */
.espaco-beneficio {
    margin-top: 15px;
    margin-bottom: 4px;
}

</style>
""", unsafe_allow_html=True)
# --------------------------------------------------
# CAMPO COM BOTÃO COPIAR
# --------------------------------------------------
def campo_copia(label, valor):
    valor = "" if valor is None else str(valor)

    html = f"""
    <div style="margin-bottom:25px;">
        <label style="
            font-size:10px;
            color:#bdbdbd;
        ">{label}</label>

        <div style="
            background:#0e0e0e;
            border:1px solid #333;
            border-radius:6px;
            height:40px;
            display:flex;
            align-items:center;
            justify-content:space-between;
            padding:0 10px;
        ">
            <span style="font-size:12px; color:white;">{valor}</span>

            {""
            if valor == "" else f"""
            <button onclick="
                navigator.clipboard.writeText('{valor}');
                this.innerText='✔';
                setTimeout(()=>this.innerText='⧉',1000);
            "
            style="
                background:none;
                border:none;
                color:white;
                font-size:14px;
                cursor:pointer;
            ">⧉</button>
            """}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


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

df_consulta = df.fillna("")
lista_nomes = sorted(df_consulta["Nome"].unique())

nome = st.selectbox("Selecione o investidor", [""] + lista_nomes)

if nome:
    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]

    col1, col2, col3 = st.columns([3, 3, 2])

    # -------------------------
    # COLUNA 1 — PROFISSIONAL
    # -------------------------
    with col1:
        st.markdown("##### 📌 Dados profissionais")

        # BP / Matrícula / Situação
        bp = str(linha["BP"]).replace(".0", "")
        matricula = str(linha["Matrícula"]).replace(".0", "").zfill(6)

        a1, a2, a3 = st.columns(3)

with a1:
    campo_copia("BP", bp)

with a2:
    campo_copia("Matrícula", matricula)

with a3:
    campo_copia("Situação", linha["Situação"])


# Datas e contrato
a4, a5, a6 = st.columns(3)

with a4:
    campo_copia("Data início", linha["Data Início_exibicao"])

with a5:
    campo_copia("Término previsto", linha["Térm previsto_exibicao"])

with a6:
    campo_copia("Modelo contrato", linha["Modelo de contrato"])


# Início na V4 + Tempo de casa  ← ESTA LINHA TEM QUE ESTAR COLADA NA ESQUERDA
tempo_casa = ""

if linha["Data Início"] != "":
    delta = datetime.today() - pd.to_datetime(linha["Data Início"])
    anos = delta.days // 365
    meses = (delta.days % 365) // 30
    dias = (delta.days % 365) % 30
    tempo_casa = f"{anos} anos, {meses} meses e {dias} dias"

a7, a8 = st.columns([1, 2])

with a7:
    campo_copia("Início na V4", linha["Data Início_exibicao"])

with a8:
    campo_copia("Tempo de casa", tempo_casa)

        # Unidade maior / Modalidade menor
        a9, a10 = st.columns([3, 1])
        a9.text_input("Unidade / Atuação", linha["Unidade/Atuação"], disabled=True)
        a10.text_input("Modalidade PJ", linha["Modalidade PJ"], disabled=True)

        st.text_input("E-mail corporativo", linha["E-mail corporativo"], disabled=True)

        a11, a12 = st.columns(2)
        a11.text_input("CNPJ", linha["CNPJ"], disabled=True)
        a12.text_input("Razão social", linha["Razão social"], disabled=True)

        # Cargo maior / Remuneração menor
        a13, a14 = st.columns([3, 1])
        a13.text_input("Cargo", linha["Cargo"], disabled=True)
        a14.text_input("Remuneração", linha["Remuneração"], disabled=True)

        # CBO menor / Descrição maior
        a15, a16 = st.columns([1, 3])
        a15.text_input("CBO", linha["CBO"], disabled=True)
        a16.text_input("Descrição CBO", linha["Descrição CBO"], disabled=True)

    # -------------------------
    # COLUNA 2 — ADMIN / PESSOAL
    # -------------------------
    with col2:
        st.markdown("##### 🧾 Centro de custo")

        # Centro de custo (código menor / descrição maior)
        codigo_cc = str(linha["Código CC"]).replace(".0", "")

        b1, b2 = st.columns([1, 3])
        b1.text_input("Código CC", codigo_cc, disabled=True)
        b2.text_input("Descrição CC", linha["Descrição CC"], disabled=True)


        b3, b4 = st.columns(2)
        b3.text_input("Senioridade", linha["Senioridade"], disabled=True)
        b4.text_input("Conta contábil", linha["Conta contábil"], disabled=True)

        st.text_input("Liderança direta", linha["Liderança direta"], disabled=True)

        st.markdown("##### 👤 Dados pessoais")

        b5, b6, b7 = st.columns(3)
        b5.text_input("CPF", linha["CPF"], disabled=True)
        b6.text_input("Nascimento", linha["Data de nascimento"], disabled=True)

        idade = ""
        if linha["Data de nascimento"] != "":
            idade = int((datetime.today() - pd.to_datetime(linha["Data de nascimento"])).days / 365.25)
            idade = f"{idade} anos"
        b7.text_input("Idade", idade, disabled=True)

        b8, b9 = st.columns(2)
        b8.text_input("CEP", linha["CEP"], disabled=True)
        b9.text_input("Escolaridade", linha["Escolaridade"], disabled=True)

        st.text_input("Telefone pessoal", linha["Telefone pessoal"], disabled=True)
        st.text_input("E-mail pessoal", linha["E-mail pessoal"], disabled=True)

    # -------------------------
    # COLUNA 3 — FOTO / BENEFÍCIOS / LINK
    # -------------------------
    with col3:
        st.markdown("##### 🖼️ Foto")
        if linha["Foto"]:
            st.image(linha["Foto"], use_container_width=True)
        else:
            st.info("Sem foto")

        st.markdown("##### 🎁 Benefícios")
        st.text_input("Plano médico", linha["Operadora Médico"], disabled=True)
        st.text_input("Carteirinha médico", linha["Carteirinha médico"], disabled=True)

        st.markdown('<div class="espaco-beneficio"></div>', unsafe_allow_html=True)

        st.text_input("Plano odonto", linha["Operadora Odonto"], disabled=True)
        st.text_input("Carteirinha odonto", linha["Carteirinha odonto"], disabled=True)

        st.markdown("##### 🔗 Link")
        if linha["Link Drive"]:
            st.link_button("Abrir Drive", linha["Link Drive"])

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
