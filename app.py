import streamlit as st
import streamlit_authenticator as stauth
import json

# --------------------------------------------------
# CONFIGURAÇÃO INICIAL
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide"
)

# --------------------------------------------------
# AUTENTICAÇÃO (VERSÃO ESTÁVEL)
# --------------------------------------------------
# Converte secrets em dict Python mutável
config = json.loads(json.dumps(st.secrets["auth_config"]))

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

name, authentication_status, username = authenticator.login(
    "Login - Dashboard People V4",
    "main"
)

if authentication_status is False:
    st.error("Usuário ou senha inválidos")

elif authentication_status is None:
    st.warning("Digite seu usuário e senha")

elif authentication_status:

    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Bem-vindo(a), {name}")

    # --------------------------------------------------
    # DASHBOARD (PLACEHOLDER)
    # --------------------------------------------------
    st.title("📊 Dashboard People - V4 Company")
    st.markdown("---")

    st.success("Login realizado com sucesso 🔐")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Headcount Total", "—")
    col2.metric("% PJ vs CLT", "—")
    col3.metric("Média Salarial", "—")
    col4.metric("Total de Desligamentos", "—")

    st.markdown("### ✅ Infraestrutura concluída")
    st.write(
        """
        ✔ Login com usuário e senha  
        ✔ Secrets seguros  
        ✔ Streamlit Cloud estável  
        ✔ Pronto para Google Sheets  
        """
    )
