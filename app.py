import streamlit as st
import streamlit_authenticator as stauth

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

# Copiando secrets para dict Python mutável (manual)
secrets_auth = st.secrets["auth_config"]

credentials = {
    "usernames": {
        user: {
            "name": data["name"],
            "email": data["email"],
            "password": data["password"],
        }
        for user, data in secrets_auth["credentials"]["usernames"].items()
    }
}

cookie = {
    "name": secrets_auth["cookie"]["name"],
    "key": secrets_auth["cookie"]["key"],
    "expiry_days": secrets_auth["cookie"]["expiry_days"],
}

authenticator = stauth.Authenticate(
    credentials,
    cookie["name"],
    cookie["key"],
    cookie["expiry_days"],
)

name, authentication_status, username = authenticator.login(
    "Login - Dashboard People V4",
    "sidebar"
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
        ✔ Autenticação segura  
        ✔ Secrets protegidos  
        ✔ Streamlit Cloud estável  
        ✔ Pronto para Google Sheets  
        """
    )
