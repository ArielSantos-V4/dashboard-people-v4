import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

st.set_page_config(
    page_title="People Dashboard",
    layout="wide"
)

# ===============================
# GOOGLE SHEETS CONFIG
# ===============================
SHEET_ID = "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
SHEET_NAME = "Ativos"

@st.cache_data(ttl=300)
def load_google_sheet():
    sheet_name_encoded = urllib.parse.quote(SHEET_NAME)
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={sheet_name_encoded}"
    )
    return pd.read_csv(url)

# ===============================
# LOAD DATA
# ===============================
df = load_google_sheet()
df.columns = df.columns.str.strip()

# ===============================
# DATE TREATMENT
# ===============================
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

contratos_vencidos = df[df["Térm previsto"] < hoje]

pj = len(df[df["Tipo de contrato"] == "PJ"])
clt = len(df[df["Tipo de contrato"] == "CLT"])
estagio = len(df[df["Tipo de contrato"] == "Estágio"])

# ===============================
# UI
# ===============================
st.title("📊 People Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("👥 Headcount", headcount)
col2.metric("⏳ Contratos (30 dias)", len(contratos_30_dias))
col3.metric("⚠️ Contratos vencidos", len(contratos_vencidos))
col4.metric("📎 PJ | CLT | Estágio", f"{pj} | {clt} | {estagio}")

st.divider()
st.subheader("📋 Base de colaboradores")

st.dataframe(
    df.sort_values("Térm previsto"),
    use_container_width=True
)
