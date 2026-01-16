import streamlit as st
import hashlib

# --------------------------------------------------
# CONFIGURAÇÃO INICIAL
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide"
)

# --------------------------------------------------
# FUNÇÕES
# --------------------------------------------------
def check_password(username, password):
    users = st.secrets["users"]

    if username not in users:
        return False, None

    stored_password = users[username]["password"]
    return password == stored_password, users[username]["name"]

# --------------------------------------------------
# LOGIN
# --------------------------------------------------
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
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.experimental_rerun()

st.title("📊 Dashboard People - V4 Company")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Headcount Total", "—")
col2.metric("% PJ vs CLT", "—")
col3.metric("Média Salarial", "—")
col4.metric("Total de Desligamentos", "—")

st.success("🎉 Login funcionando. Base pronta para conectar o Google Sheets.")
