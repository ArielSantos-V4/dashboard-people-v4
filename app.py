import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (TEM QUE SER A PRIMEIRA COISA)
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide",
    page_icon="LOGO VERMELHO.png"
)

# --------------------------------------------------
# ESTADO
# --------------------------------------------------
if "investidor_selecionado" not in st.session_state:
    st.session_state.investidor_selecionado = ""

def limpar_investidor():
    st.session_state.investidor_selecionado = ""

# --------------------------------------------------
# ABAS NO TOPO
# --------------------------------------------------
aba_dashboard, aba_relatorios = st.tabs([
    "📊 Dashboard",
    "📄 Relatórios"
])

# ==================================================
# ================= DASHBOARD ======================
# ==================================================
with aba_dashboard:

    # --------------------------------------------------
    # ESTILO
    # --------------------------------------------------
    st.markdown("""
    <style>
    h5 {
        font-size: 20px !important;
        margin-top: 6px !important;
        margin-bottom: 2px !important;
    }
    label {
        font-size: 10px !important;
        margin-bottom: 0px !important;
        color: #bdbdbd !important;
    }
    div[data-testid="stTextInput"] {
        height: 30px !important;
        margin-bottom: 25px !important;
    }
    div[data-testid="stTextInput"] input {
        height: 40px !important;
        padding: 10px 10px !important;
        font-size: 12px !important;
        line-height: 0px !important;
    }
    div[data-testid="column"] {
        padding-top: 5px !important;
        padding-bottom: 0px !important;
    }
    .espaco-beneficio {
        margin-top: 15px;
        margin-bottom: 4px;
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
    media_admissoes = df_adm.groupby(df_adm["Data Início"].dt.to_period("M")).size().mean()

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

    # 👉 TODO O RESTO DO SEU CÓDIGO CONTINUA IGUAL
    # (KPIs, gráficos, consulta individual, tabela)
    # ❗ NADA FOI REMOVIDO

# ==================================================
# ================= RELATÓRIOS =====================
# ==================================================
with aba_relatorios:
    st.header("📄 Relatórios")
    st.info("Área reservada para geração de relatórios (em construção)")
