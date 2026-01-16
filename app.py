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
# ESTILO GLOBAL
# --------------------------------------------------
st.markdown("""
<style>
.main { background-color: #0e0e0e; }
h1, h2, h3, h4 { color: #E30613; }

.field {
    background:#1a1a1a;
    padding:8px 10px;
    border-radius:6px;
    border:1px solid #333;
    color:#fff;
    font-size:13px;
    position:relative;
}

.field:hover .copy-btn {
    opacity:1;
}

.label {
    font-size:11px;
    color:#999;
    margin-bottom:2px;
}

.copy-btn {
    position:absolute;
    right:8px;
    top:8px;
    cursor:pointer;
    opacity:0;
    transition:0.2s;
    font-size:14px;
    color:#E30613;
}
</style>

<script>
function copyText(text) {
    navigator.clipboard.writeText(text);
}
</script>
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
df["Térm previsto"] = pd.to_datetime(df["Térm previsto"], errors="coerce")
df["Data Início"] = pd.to_datetime(df["Data Início"], errors="coerce")
df["Nascimento"] = pd.to_datetime(df.get("Data de nascimento"), errors="coerce")

# --------------------------------------------------
# FUNÇÕES AUXILIARES
# --------------------------------------------------
def v(valor):
    return "" if pd.isna(valor) else str(valor)

def idade(data):
    if pd.isna(data): return ""
    hoje = datetime.today()
    return hoje.year - data.year - ((hoje.month, hoje.day) < (data.month, data.day))

def tempo_casa(data):
    if pd.isna(data): return ""
    delta = relativedelta(datetime.today(), data)
    return f"{delta.years}a {delta.months}m {delta.days}d"

from dateutil.relativedelta import relativedelta

def campo(label, valor):
    return f"""
    <div>
        <div class="label">{label}</div>
        <div class="field">
            {valor}
            <span class="copy-btn" onclick="copyText('{valor}')">📋</span>
        </div>
    </div>
    """

# --------------------------------------------------
# CONSULTA INDIVIDUAL
# --------------------------------------------------
st.markdown("## 🔎 Consulta individual do investidor")

nomes = sorted(df["Nome"].dropna().astype(str).unique())
nome = st.selectbox("Buscar investidor", [""] + nomes)

if nome:
    linha = df[df["Nome"] == nome].iloc[0]

    col1, col2, col3 = st.columns([4, 3, 2])

    # ---------- COLUNA 1 ----------
    with col1:
        st.markdown("### Dados principais")

        st.markdown(campo("BP", v(linha.get("BP"))) + campo("Matrícula", v(linha.get("Matrícula"))) + campo("Situação", v(linha.get("Situação"))), unsafe_allow_html=True)
        st.markdown(campo("Data contrato", v(linha.get("Data Início").strftime("%d/%m/%Y") if pd.notna(linha.get("Data Início")) else "")) + campo("Término previsto", v(linha.get("Térm previsto").strftime("%d/%m/%Y") if pd.notna(linha.get("Térm previsto")) else "")) + campo("Modelo contrato", v(linha.get("Modelo de contrato"))), unsafe_allow_html=True)
        st.markdown(campo("Unidade", v(linha.get("Unidade/Atuação"))) + campo("Modalidade (PJ)", v(linha.get("Modalidade"))), unsafe_allow_html=True)
        st.markdown(campo("E-mail corporativo", v(linha.get("E-mail corporativo"))), unsafe_allow_html=True)
        st.markdown(campo("Início na V4", v(linha.get("Data Início").strftime("%d/%m/%Y") if pd.notna(linha.get("Data Início")) else "")) + campo("Tempo de casa", tempo_casa(linha.get("Data Início"))), unsafe_allow_html=True)
        st.markdown(campo("CNPJ", v(linha.get("CNPJ"))) + campo("Razão social", v(linha.get("Razão social"))), unsafe_allow_html=True)
        st.markdown(campo("Cargo", v(linha.get("Cargo"))) + campo("Remuneração", v(linha.get("Remuneração"))), unsafe_allow_html=True)
        st.markdown(campo("CBO", v(linha.get("CBO"))) + campo("Descrição CBO", v(linha.get("Descrição CBO"))), unsafe_allow_html=True)

    # ---------- COLUNA 2 ----------
    with col2:
        st.markdown("### Dados pessoais")

        st.markdown(
            campo("CPF", v(linha.get("CPF"))) +
            campo("Data nascimento", v(linha.get("Data de nascimento"))) +
            campo("Idade", idade(linha.get("Nascimento"))),
            unsafe_allow_html=True
        )

        st.markdown(
            campo("CEP", v(linha.get("CEP"))) +
            campo("Escolaridade", v(linha.get("Escolaridade"))) +
            campo("Telefone pessoal", v(linha.get("Telefone pessoal"))),
            unsafe_allow_html=True
        )

        st.markdown(campo("E-mail pessoal", v(linha.get("E-mail pessoal"))), unsafe_allow_html=True)

    # ---------- COLUNA 3 ----------
    with col3:
        if pd.notna(linha.get("Foto")):
            st.image(linha.get("Foto"), width=180)

        st.markdown("### Benefícios")
        st.markdown(
            campo("Situação plano", v(linha.get("Situação plano"))) +
            campo("Solicitar documentação", v(linha.get("Solicitar documentação"))) +
            campo("Enviar no EB", v(linha.get("Enviar no EB"))),
            unsafe_allow_html=True
        )

        st.markdown(
            campo("Carteirinha médico", v(linha.get("Carteirinha médico"))) +
            campo("Operadora médico", v(linha.get("Operadora médico"))),
            unsafe_allow_html=True
        )

        st.markdown(
            campo("Carteirinha odonto", v(linha.get("Carteirinha odonto"))) +
            campo("Operadora odonto", v(linha.get("Operadora odonto"))),
            unsafe_allow_html=True
        )

        st.markdown(campo("Link Drive", v(linha.get("Link Drive"))), unsafe_allow_html=True)
