import streamlit as st
from datetime import datetime

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

def gerar_docx_com_substituicoes(modelo_path, mapa_substituicoes):
    """
    Carrega um arquivo .docx, substitui as chaves conforme o mapa
    e retorna o arquivo em memória (BytesIO).
    """
    try:
        # Carrega o template
        doc = Document(modelo_path)
        
        # Substitui no corpo do texto
        for p in doc.paragraphs:
            for codigo, valor in mapa_substituicoes.items():
                if codigo in p.text:
                    p.text = p.text.replace(codigo, str(valor))
        
        # Substitui em tabelas (importante para o layout de VT)
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    for p in celula.paragraphs:
                        for codigo, valor in mapa_substituicoes.items():
                            if codigo in p.text:
                                p.text = p.text.replace(codigo, str(valor))
        
        # Salva o resultado em um objeto de bytes para o download do Streamlit
        conteudo_puro = BytesIO()
        doc.save(conteudo_puro)
        conteudo_puro.seek(0)
        return conteudo_puro
    except Exception as e:
        raise Exception(f"Erro ao manipular o arquivo Word: {e}")
        
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
        st.image("LOGO VERMELHO.png", width=100)
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
                <h3 style="color: #333; margin: 0;">👋 Bem-vindo ao Sistema Operacional do time C&B</h3>
                <p style="color: #666; margin-top: 5px;">Selecione um módulo no menu lateral para iniciar.</p>
            </div>
        """, unsafe_allow_html=True)
    
        # --- BLOCO DE ANIVERSARIANTES ULTRA COMPACTO (ALINHADO À ESQUERDA) ---
        if 'df_ativos' in locals() or 'df_ativos' in globals():
            hoje = datetime.now()
            
            df_niver = df_ativos.copy()
            df_niver['dt_nasc'] = pd.to_datetime(df_niver['Data de nascimento'], dayfirst=True, errors='coerce')
            df_niver = df_niver[df_niver['dt_nasc'].notna()]
            df_niver['dia'] = df_niver['dt_nasc'].dt.day
            df_niver['mes'] = df_niver['dt_nasc'].dt.month

            aniv_hoje = df_niver[(df_niver['dia'] == hoje.day) & (df_niver['mes'] == hoje.month)].to_dict('records')

            if aniv_hoje:
                if "idx_niver_land" not in st.session_state:
                    st.session_state.idx_niver_land = 0
                
                st.session_state.idx_niver_land = st.session_state.idx_niver_land % len(aniv_hoje)
                p = aniv_hoje[st.session_state.idx_niver_land]
                
                nome_p = p['Nome'].split()[0]
                nasc_p = p.get('Data de nascimento', '')
                foto_p = p.get('Foto', '')

                # Espaçamento para não grudar na mensagem de boas-vindas
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Criamos colunas: a primeira é pequena para o card, a segunda sobra para o futuro
                col_card, col_futuro = st.columns([0.8, 3.2])
                
                with col_card:
                    # Pegamos os dados
                    p = aniv_hoje[st.session_state.idx_niver_land]
                    nome_p = p['Nome'].split()[0]
                    nasc_p = p.get('Data de nascimento', '')
                    foto_p = p.get('Foto', '')
        
                    # 1. Quadrado Superior (HTML)
                    st.markdown(f"""
                        <div style="
                            border: 1px solid #ddd; 
                            border-radius: 10px 10px 0 0; 
                            padding: 15px; 
                            width: 250px; 
                            background-color: white;
                            border-bottom: none;
                            margin-bottom: 0px;
                        ">
                            <p style='margin: 0 0 14px 0; font-weight: bold; color: #E30613; font-size: 0.9rem; text-transform: uppercase;'>
                                🎂 Aniversariantes do dia
                            </p>
                            <div style="display: flex; align-items: center;">
                                <div style="margin-right: 25px;">
                                    {"<img src='" + foto_p + "' style='width:55px; height:55px; border-radius:9px; object-fit:cover;'>" if foto_p and str(foto_p).startswith("http") else "<div style='width:55px; height:55px; border-radius:9px; background-color:#78909c; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:20px;'>" + nome_p[0] + "</div>"}
                                </div>
                                <div>
                                    <p style='margin: 0; font-weight: bold; font-size: 1.1rem; line-height: 1.1;'>{nome_p}</p>
                                    <p style='margin: 0; font-size: 0.9rem; color: gray;'>📅 {nasc_p}</p>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        
                    # 2. Área do Botão (Encaixada perfeitamente)
                    if len(aniv_hoje) > 1:
                        # Criamos um container para o botão com a mesma largura do quadrado
                        with st.container():
                            st.markdown("""
                                <style>
                                    div[data-testid="stButton"] > button {
                                        width: 250px !important;
                                        border-radius: 0 0 10px 10px !important;
                                        border: 1px solid #ddd !important;
                                        border-top: 1px solid #eee !important;
                                        height: 35px !important;
                                        font-size: 0.5rem !important;
                                        margin-top: -16px !important;
                                    }
                                </style>
                            """, unsafe_allow_html=True)
                            
                            if st.button(f"Próximo ({st.session_state.idx_niver_land + 1}/{len(aniv_hoje)}) ➔", key="btn_niver_final_v4"):
                                st.session_state.idx_niver_land += 1
                                st.rerun()
        
    elif pagina == "💼 Departamento Pessoal":
        departamento_pessoal.render(df_ativos, df_desligados)
    
    elif pagina == "🎁 Benefícios":
        beneficios.render(df_ativos)
