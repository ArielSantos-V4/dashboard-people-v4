import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# CONFIGURAÇÃO INICIAL
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard People | V4 Company",
    layout="wide"
)

# --------------------------------------------------
# AUTENTICAÇÃO
# --------------------------------------------------
config = st.secrets["auth_config"]

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

    st.info(
        "Login realizado com sucesso ✅  \n"
        "Próximo passo: conectar Google Sheets e construir os gráficos."
    )

    # KPIs (placeholders)
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Headcount Total", "—")
    col2.metric("% PJ vs CLT", "—")
    col3.metric("Média Salarial", "—")
    col4.metric("Total de Desligamentos", "—")


    st.markdown("### ✅ Estrutura pronta")
    st.write(
        """
        ✔ Autenticação segura  
        ✔ Secrets funcionando  
        ✔ Tema V4 aplicado  
        ✔ Base pronta para KPIs, gráficos e abas  
        """
    )
