import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="People Dashboard",
    layout="wide"
)

# ===============================
# CONFIGURAÇÕES GOOGLE SHEETS
# ===============================
SHEET_ID = "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
GID = "2056973316"

@st.cache_data(ttl=300)
def load_google_sheet():
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
        f"?format=csv&gid={GID}"
    )
    df = pd.read_csv(url)
    return df

# ===============================
# LOAD DATA
# ===============================
df = load_google_sheet()

# ===============================
# TRATAMENTO DE DADOS
# ===============================
df.columns = df.columns.str.strip()

df["Térm previsto"] = pd.to_datetime(
    df["Térm previsto"],
    errors="coerce",
    dayfirst=True
)

hoje = datetime.today()
em_30_dias = hoje + timedelta(days=30)

# ===============================
# KPIs
# ===============================
headcount = len(df)

contratos_30_dias = df[
    (df["Térm previsto"] >= hoje) &
    (df["Térm previsto"] <= em_30_dias)
]

contratos_vencidos = df[
    df["Térm previsto"] < hoje
]

pj = len(df[df["Tipo de contrato"] == "PJ"])
clt = len(df[df["Tipo de contrato"] == "CLT"])
estagio = len(df[df["Tipo de contrato"] == "Estágio"])

# ===============================
# UI
# ===============================
st.title("📊 People Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("👥 Headcount Total", headcount)

with col2:
    st.metric("⏳ Contratos (próx. 30 dias)", len(contratos_30_dias))

with col3:
    st.metric("⚠️ Contratos Vencidos", len(contratos_vencidos))

with col4:
    st.metric("📎 PJ | CLT | Estágio", f"{pj} | {clt} | {estagio}")

st.divider()
st.subheader("📋 Base completa")

st.dataframe(
    df.sort_values("Térm previsto"),
    use_container_width=True
)
