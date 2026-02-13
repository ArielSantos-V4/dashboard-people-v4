import streamlit as st

# Configuração da página deve ser SEMPRE o primeiro comando Streamlit
st.set_page_config(
    page_title="V4 People Hub",
    layout="wide",
    page_icon="LOGO VERMELHO.png"
)

import bcrypt
import departamento_pessoal
import beneficios
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ==============================
# CARREGAMENTO DE DADOS (ATUALIZADO)
# ==============================
@st.cache_data(ttl=600)
def load_google_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )

    client = gspread.authorize(creds)
    
    # Abre a planilha pelo ID
    sheet = client.open_by_key("13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY")
    
    # --- CARREGA ATIVOS (Pelo GID) ---
    # GID da aba Ativos que você passou
    worksheet_ativos = sheet.get_worksheet_by_id(2056973316)
    data_ativos = worksheet_ativos.get_all_records()
    df_ativos = pd.DataFrame(data_ativos)

    # --- CARREGA DESLIGADOS (Pelo GID) ---
    # GID da aba Desligados que você passou
    worksheet_desligados = sheet.get_worksheet_by_id(1422602176)
    data_desligados = worksheet_desligados.get_all_records()
    df_desligados = pd.DataFrame(data_desligados)

    # Retorna OS DOIS dataframes
    return df_ativos, df_desligados

# ==============================
# FUNÇÃO LOGIN
# ==============================
def verificar_senha(senha_digitada, senha_hash):
    return bcrypt.checkpw(
        senha_digitada.encode("utf-8"),
        senha_hash.encode("utf-8")
    )

# ==============================
# CONTROLE DE SESSÃO
# ==============================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ==============================
# TELA DE LOGIN
# ==============================
if not st.session_state.authenticated:

    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        # Verifica se existe a chave 'users' no secrets
        if "users" in st.secrets:
            users = st.secrets["users"]
            
            if usuario in users and verificar_senha(senha, users[usuario]["password"]):
                st.session_state.authenticated = True
                st.session_state.user_name = users[usuario]["name"]
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
        else:
            st.error("Erro de configuração: Usuários não encontrados nos Secrets.")
    
# ==============================
# ÁREA AUTENTICADA (SISTEMA)
# ==============================
else:
    # Carrega os dados APENAS se estiver logado (economiza recurso)
    with st.spinner("Carregando dados..."):
        try:
            df_ativos, df_desligados = load_google_sheet()
        except Exception as e:
            st.error(f"Erro ao conectar com a planilha: {e}")
            st.stop()

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------
    st.sidebar.success(
        f"Olá, {st.session_state.get('user_name', 'Usuário')}"
    )

    pagina = st.sidebar.radio(
        "Menu",
        [
            "🏠 Início",
            "💼 Departamento Pessoal",
            "🎁 Benefícios"
        ]
    )

    st.sidebar.divider()

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    # --------------------------------------------------
    # ROTEAMENTO DE PÁGINAS
    # --------------------------------------------------

    if pagina == "🏠 Início":
        st.markdown("""
            <div style="height:85vh;display:flex;flex-direction:column;
                        justify-content:center;align-items:center;">
                <h1 style="font-size:60px;">People em desenvolvimento</h1>
                <p style="font-size:22px;color:gray;">V4 Company</p>
            </div>
        """, unsafe_allow_html=True)
                
    elif pagina == "💼 Departamento Pessoal":
        # AQUI MUDOU: Passamos as DUAS tabelas
        departamento_pessoal.render(df_ativos, df_desligados)
    
    elif pagina == "🎁 Benefícios":
        # Benefícios geralmente usa só a base ativa
        beneficios.render(df_ativos)
