import streamlit as st

st.set_page_config(
    page_title="People em Desenvolvimento",
    layout="wide",
    page_icon="LOGO VERMELHO.png"
)

import bcrypt
import departamento_pessoal
import beneficios
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

@st.cache_data(ttl=600)
def load_google_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key("13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY")
    worksheet = sheet.get_worksheet(5)

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    return df

df = load_google_sheet()

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
# LOGIN
# ==============================
if not st.session_state.authenticated:

    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):

        users = st.secrets["users"]

        if usuario in users and verificar_senha(senha, users[usuario]["password"]):
            st.session_state.authenticated = True
            st.session_state.user_name = users[usuario]["name"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
   
# ==============================
# ÁREA AUTENTICADA
# ==============================
else:

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------
    st.sidebar.success(
        f"Bem-vindo(a), {st.session_state.get('user_name', 'Usuário')}"
    )

    pagina = st.sidebar.radio(
        "Menu",
        [
            "🏠 Início",
            "💼 Departamento Pessoal",
            "🎁 Benefícios"
        ]
    )

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    st.sidebar.divider()

    # --------------------------------------------------
    # PÁGINAS
    # --------------------------------------------------

    if pagina == "🏠 Início":

        # ---------------------------------------------------------
        # CABEÇALHO DA LANDING PAGE (CENTRALIZADO)
        # ---------------------------------------------------------
        
        # 1. Empurra o conteúdo para baixo (Ajuste a quantidade de <br> se quiser mais para baixo)
        st.markdown("<br><br><br>", unsafe_allow_html=True)
    
        # 2. Cria 3 colunas: [Vazio, CONTEÚDO NO MEIO, Vazio]
        # O [1, 2.5, 1] define a largura. O meio é mais largo.
        col_esq, col_centro, col_dir = st.columns([1, 2.5, 1])
    
        # 3. Desenha apenas na coluna do centro
        with col_centro:
            
            # Dentro do centro, dividimos de novo: [Logo] [Texto]
            c_logo, c_texto = st.columns([1, 3]) 
    
            with c_logo:
                st.image("LOGO VERMELHO.png", use_container_width=True) 
    
            with c_texto:
                # O 'padding-top' ajuda a alinhar o texto exatamente com o meio da imagem
                st.markdown("""
                    <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; padding-top: 20px;">
                        <h1 style="margin: 0; padding: 0; font-size: 3.5rem; line-height: 1.0;">Dashboard People</h1>
                        <span style="color: grey; font-size: 1.4rem; margin-top: 5px;">Bem-vindo ao sistema de gestão</span>
                    </div>
                """, unsafe_allow_html=True)
        
        # Linha divisória opcional (pode tirar se quiser limpar mais)
        st.markdown("<br><hr>", unsafe_allow_html=True)
        
    elif pagina == "💼 Departamento Pessoal":
        departamento_pessoal.render(df)
    
    elif pagina == "🎁 Benefícios":
        beneficios.render(df)

