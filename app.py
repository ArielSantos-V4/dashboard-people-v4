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
    worksheet_ativos = sheet.get_worksheet_by_id(2056973316)
    data_ativos = worksheet_ativos.get_all_records()
    df_ativos = pd.DataFrame(data_ativos)

    # --- CARREGA DESLIGADOS (Pelo GID) ---
    worksheet_desligados = sheet.get_worksheet_by_id(1422602176)
    data_desligados = worksheet_desligados.get_all_records()
    df_desligados = pd.DataFrame(data_desligados)

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

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("LOGO VERMELHO.png", width=150)
        st.markdown("### Acesso Restrito")

        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar", use_container_width=True):
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
    # Carrega os dados
    with st.spinner("Sincronizando dados com Google Sheets..."):
        try:
            df_ativos, df_desligados = load_google_sheet()
        except Exception as e:
            st.error(f"Erro ao conectar com a planilha: {e}")
            st.stop()

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------
    st.sidebar.image("LOGO VERMELHO.png", width=160)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    st.sidebar.success(f"Olá, {st.session_state.get('user_name', 'Gestor')}")

    pagina = st.sidebar.radio(
        "Navegação",
        [
            "🏠 Início",
            "💼 Departamento Pessoal",
            "🎁 Benefícios"
        ]
    )

    st.sidebar.markdown("---")
    
    # --- BOTÃO DE ATUALIZAR DADOS ---
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

    # --- BOTÃO DE LOGOUT ---
    if st.sidebar.button("Sair"):
        st.session_state.authenticated = False
        st.rerun()

    # --------------------------------------------------
    # ROTEAMENTO DE PÁGINAS
    # --------------------------------------------------

    if pagina == "🏠 Início":
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns([0.5, 4])
        with c1: st.image("LOGO VERMELHO.png", width=80)
        with c2: st.title("V4 People Hub")
        
        # MENSAGEM DE BOAS-VINDAS CUSTOMIZADA (SEM AZUL)
        st.markdown("""
            <div style="background-color: #fff; padding: 20px; border-left: 6px solid #E30613; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); border-radius: 5px;">
                <h3 style="color: #333; margin: 0;">👋 Bem-vindo ao Sistema Operacional de People</h3>
                <p style="color: #666; margin-top: 5px;">Selecione um módulo no menu lateral para iniciar.</p>
            </div>
        """, unsafe_allow_html=True)
                
    elif pagina == "💼 Departamento Pessoal":
        departamento_pessoal.render(df_ativos, df_desligados)
    
    elif pagina == "🎁 Benefícios":
        beneficios.render(df_ativos)
