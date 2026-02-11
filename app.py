import streamlit as st
import bcrypt
import departamento_pessoal
import beneficios

st.set_page_config(
    page_title="People | V4 Company",
    layout="wide"
)

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

        st.markdown("""
            <div style="height:85vh;display:flex;flex-direction:column;
                        justify-content:center;align-items:center;">
                <h1 style="font-size:60px;">People</h1>
                <p style="font-size:22px;color:gray;">V4 Company</p>
            </div>
        """, unsafe_allow_html=True)

    elif pagina == "📁 Departamento Pessoal":
        departamento_pessoal.render()

    elif pagina == "🎁 Benefícios":
        beneficios.render()
