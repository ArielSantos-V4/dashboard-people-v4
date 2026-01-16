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
SHEET_ID = "SEU_SHEET_ID_AQUI"
GID = "2056973316"

@st.cache_data(ttl=300)
def load_google_sheet():
    try:
        url = (
            f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
            f"?format=csv&gid={GID}"
        )
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error("❌ Não foi possível carregar a planilha do Google Sheets")
        raise e


# ===============================
# LOAD DATA
# ===============================
df = load_google_sheet()

# ===============================
# TRATAMENTO DE DADOS
# ===============================
df.columns = df.columns.str.strip()

# Converter data de término
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

# Tipos de contrato
pj = len(df[df["Tipo de contrato"] == "PJ"])
clt = len(df[df["Tipo de contrato"] == "CLT"])
estagio = len(df[df["Tipo de contrato"] == "Estágio"])

# ===============================
# UI
# ===============================
st.title("📊 People Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="👥 Headcount Total",
        value=headcount
    )

with col2:
    st.metric(
        label="⏳ Contratos (próx. 30 dias)",
        value=len(contratos_30_dias)
    )

with col3:
    st.metric(
        label="⚠️ Contratos Vencidos",
        value=len(contratos_vencidos)
    )

with col4:
    st.metric(
        label="📎 PJ | CLT | Estágio",
        value=f"{pj} | {clt} | {estagio}"
    )

# ===============================
# TABELA DETALHADA
# ===============================
st.divider()
st.subheader("📋 Base completa")

st.dataframe(
    df.sort_values("Térm previsto"),
    use_container_width=True
)
