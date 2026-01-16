import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIGURAÇÃO ----------------
st.set_page_config(
    page_title="Dashboard People - V4 Company",
    layout="wide"
)

# ---------------- AUTH (SECRETS) ----------------
config = yaml.load(
    st.secrets["auth_config"],
    Loader=SafeLoader
)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

name, auth_status, username = authenticator.login("Login", "main")

if not auth_status:
    st.stop()

authenticator.logout("Logout", "sidebar")
st.sidebar.success(f"Bem-vindo(a), {name}")

# ---------------- GOOGLE SHEETS ----------------
@st.cache_data(ttl=300)
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
    ).worksheet("Ativos")

    df = pd.DataFrame(sheet.get_all_records())

    df["Remuneração"] = (
        df["Remuneração"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Remuneração"] = pd.to_numeric(df["Remuneração"], errors="coerce")

    df["Data de nascimento"] = pd.to_datetime(
        df["Data de nascimento"], errors="coerce"
    )
    df["Idade"] = (
        pd.Timestamp.today() - df["Data de nascimento"]
    ).dt.days // 365

    return df

df = load_data()

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filtros")

modelo = st.sidebar.multiselect(
    "Modelo de Contrato",
    df["Modelo de contrato"].dropna().unique(),
    df["Modelo de contrato"].dropna().unique()
)

senioridade = st.sidebar.multiselect(
    "Senioridade",
    df["Senioridade"].dropna().unique(),
    df["Senioridade"].dropna().unique()
)

df = df[
    df["Modelo de contrato"].isin(modelo) &
    df["Senioridade"].isin(senioridade)
]

if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.experimental_rerun()

# ---------------- DASHBOARD ----------------
st.title("📊 Dashboard People - V4 Company")

col1, col2, col3 = st.columns(3)
col1.metric("Headcount", len(df))
col2.metric(
    "Média Salarial",
    f"R$ {df['Remuneração'].mean():,.2f}"
)
col3.metric(
    "% PJ",
    f"{(df['Modelo de contrato'].value_counts(normalize=True).get('PJ', 0) * 100):.1f}%"
)

fig = px.pie(
    df,
    names="Modelo de contrato",
    title="Distribuição por Modelo de Contrato"
)
st.plotly_chart(fig, use_container_width=True)

fig2 = px.box(
    df,
    x="Senioridade",
    y="Remuneração",
    points="all",
    title="Senioridade vs Salário"
)
st.plotly_chart(fig2, use_container_width=True)
