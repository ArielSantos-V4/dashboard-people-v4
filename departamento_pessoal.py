import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from docx import Document
from io import BytesIO
import re
import unicodedata

# ==========================================
# CONFIGURAÇÕES E CORES
# ==========================================
CORES_V4 = ["#E30613", "#8B0000", "#FF4C4C", "#404040", "#D3D3D3"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ==========================================
# FUNÇÕES AUXILIARES GERAIS
# ==========================================
def limpar_numero(valor):
    if valor == "" or pd.isna(valor): return ""
    return str(valor).replace(".0", "").replace(".", "").replace("-", "").replace("/", "").strip()

def formatar_cpf(valor):
    v = limpar_numero(valor).zfill(11)
    return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}" if len(v) == 11 else v

def formatar_cnpj(valor):
    v = limpar_numero(valor).zfill(14)
    return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}" if len(v) == 14 else v

def parse_data_br(coluna):
    return pd.to_datetime(coluna, dayfirst=True, errors="coerce")

def calcular_tempo_casa(data_inicio):
    if pd.isna(data_inicio) or data_inicio == "": return ""
    hoje = pd.Timestamp.today().normalize()
    diff = relativedelta(hoje, data_inicio)
    return f"{diff.years} anos, {diff.months} meses e {diff.days} dias"

def calcular_idade(dt_nasc):
    if pd.isna(dt_nasc) or dt_nasc == "": return ""
    try:
        hoje = pd.Timestamp.today()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{idade} anos"
    except: return ""

def substituir_texto_docx(doc, mapa):
    def replace_runs(paragraph):
        for run in paragraph.runs:
            for k, v in mapa.items():
                if k in run.text: run.text = run.text.replace(k, str(v))
    for p in doc.paragraphs: replace_runs(p)
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs: replace_runs(p)

def gerar_docx_com_substituicoes(caminho, mapa):
    doc = Document(caminho)
    substituir_texto_docx(doc, mapa)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def validar_clt(row):
    modelo = str(row.get("Modelo de contrato", "")).upper()
    nao_clt = ["PJ", "PRESTADOR", "ESTÁGIO", "ESTAGIÁRIO", "BOLSISTA"]
    for termo in nao_clt:
        if termo in modelo: return False, modelo
    return True, "CLT"

# ==========================================
# LÓGICA DE ALERTAS
# ==========================================
def gerar_alertas_investidor(linha):
    alertas = []
    hoje = pd.Timestamp.today().normalize()
    status = str(linha.get("Situação no plano", "")).strip()
    nascimento = pd.to_datetime(linha.get("Data de nascimento_dt"), errors="coerce")
    if pd.notna(nascimento) and nascimento.month == hoje.month:
        alertas.append(("success", f"Aniversariante do mês (Dia {nascimento.day}) 🎉"))
    if str(linha.get("Modalidade PJ", "")).strip().upper() == "MEI":
        alertas.append(("warning", "Investidor MEI ⚠️"))
    return alertas

# ==========================================
# MODAIS DE AÇÃO
# ==========================================

@st.dialog("📥 Exportar Relatório Master", width="large")
def modal_exportar_excel(df_master):
    st.markdown("Selecione as colunas que deseja incluir no arquivo Excel.")
    colunas_escolhidas = st.multiselect("Colunas:", options=sorted(df_master.columns.tolist()), default=["Nome", "Cargo", "Área"])
    if colunas_escolhidas:
        output = BytesIO()
        df_master[colunas_escolhidas].to_excel(output, index=False)
        st.download_button("📗 Baixar Excel", output.getvalue(), "Relatorio_Master.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)

@st.dialog("📝 Título Doc Automação")
def modal_titulo_doc(df):
    nome = st.selectbox("Investidor", [""] + sorted(df["Nome"].unique()))
    if not nome: 
        st.markdown('<div style="padding:10px;border-radius:5px;border:1px solid #dcdfe6;background-color:#f8f9fa;color:#606266;">🔍 Selecione um investidor.</div>', unsafe_allow_html=True)
        return
    titulo = st.text_input("Nome do Documento")
    if st.button("Gerar", type="primary"):
        row = df[df["Nome"]==nome].iloc[0]
        st.code(f"{nome} __ {row.get('CPF','')} __ {titulo}")

@st.dialog("📄 Demissão Comum Acordo")
def modal_comum(df):
    nome = st.selectbox("Colaborador", [""] + sorted(df["Nome"].unique()))
    if not nome: return
    data = st.date_input("Data", format="DD/MM/YYYY")
    dados = df[df["Nome"]==nome].iloc[0]
    eh_clt, tipo = validar_clt(dados)
    if not eh_clt:
        st.warning(f"Vínculo: {tipo}")
        if not st.checkbox("Gerar mesmo assim"): return
    mapa = {"{nome_completo}": nome, "{cargo}": dados.get("Cargo",""), "{data}": data.strftime("%d/%m/%Y")}
    try:
        arquivo = gerar_docx_com_substituicoes("Demissão por comum acordo.docx", mapa)
        st.download_button("📄 Baixar DOC", arquivo, f"Demissão - {nome}.docx", type="primary", use_container_width=True)
        st.link_button("🔃 Converter em PDF", "https://www.ilovepdf.com/pt/word_para_pdf", use_container_width=True)
    except: st.error("Modelo não encontrado.")

@st.dialog("📄 Aviso Prévio Indenizado")
def modal_aviso_previo_indenizado(df):
    nome = st.selectbox("Investidor", [""] + sorted(df["Nome"].unique()))
    if not nome: return
    d1 = st.date_input("Desligamento", format="DD/MM/YYYY")
    d2 = st.date_input("Homologação", format="DD/MM/YYYY")
    dados = df[df["Nome"]==nome].iloc[0]
    mapa = {"{nome_selecionado}": nome, "{data_desligamento}": d1.strftime("%d/%m/%Y"), "{data_homologacao}": d2.strftime("%d/%m/%Y")}
    try:
        arquivo = gerar_docx_com_substituicoes("Aviso prévio Indenizado.docx", mapa)
        st.download_button("📄 Baixar DOC", arquivo, f"Aviso - {nome}.docx", type="primary", use_container_width=True)
        st.link_button("🔃 Converter em PDF", "https://www.ilovepdf.com/pt/word_para_pdf", use_container_width=True)
    except: st.error("Modelo não encontrado.")

@st.dialog("🚌 Atualização do Vale Transporte")
def modal_vale_transporte(df_pessoas):
    nome_sel = st.selectbox("Investidor", [""] + sorted(df_pessoas["Nome"].unique()))
    if not nome_sel: return
    res = df_pessoas[df_pessoas["Nome"] == nome_sel].iloc[0]
    opcao = st.radio("Opção:", ["Adesão ao VT", "Não adesão ao VT"], horizontal=True)
    
    c1, c2 = st.columns([3, 1])
    cidade = c1.text_input("Cidade")
    uf = c2.text_input("UF")
    
    # Cálculos simplificados para o mapa
    s_val, s_int, s_val_t, s_int_t = 0.0, 0.0, 0.0, 0.0
    if opcao == "Adesão ao VT":
        st.info("Preencha os transportes no documento após baixar.") # Simplificado para evitar erro de loop
    
    mapa = {"{nome}": nome_sel, "{cidade}": cidade, "{uf_estado}": uf, "{soma_valor}": "0.00", "{soma_inte}": "0.00", "{soma_unit}": "0.00", "{soma_integracao}": "0.00"}
    modelo = "declaracao_vale_transporte_clt.docx" if opcao == "Adesão ao VT" else "declaracao_nao_vale_transporte_clt.docx"
    try:
        arquivo = gerar_docx_com_substituicoes(modelo, mapa)
        st.download_button(f"📄 Baixar {opcao}", arquivo, f"VT_{nome_sel}.docx", type="primary", use_container_width=True)
    except: st.error("Modelo não encontrado.")

@st.dialog(" ", width="large")
def modal_consulta_investidor(df_consulta, nome, tipo_base="ativo"):
    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]
    st.markdown(f"## {nome}")
    st.write(f"Cargo: {linha.get('Cargo','')}")
    st.write(f"Área: {linha.get('Área','')}")

# ==========================================
# RENDER PRINCIPAL
# ==========================================
def render(df_ativos, df_desligados):
    if not st.session_state.authenticated:
        st.warning("Faça login.")
        st.stop()

    # --- PREPARAÇÃO ---
    def preparar(df_raw):
        df = df_raw.copy()
        cols = ["Início na V4", "Data de nascimento", "Data do contrato", "Térm previsto", "Data de rescisão"]
        for c in cols:
            if c in df.columns:
                df[f"{c}_dt"] = parse_data_br(df[c])
                df[c] = df[f"{c}_dt"].dt.strftime("%d/%m/%Y").fillna("")
        return df

    df_ativos_proc = preparar(df_ativos)
    df_desligados_proc = preparar(df_desligados)

    # --- TABS PRINCIPAIS ---
    aba_dash, aba_roll, aba_analyt, aba_acoes = st.tabs(["📊 Dashboard", "👥 Rolling", "📈 Analytics", "⚡ Ações"])

    with aba_dash:
        st.write("Conteúdo do Dashboard")

    with aba_roll:
        modo = st.radio("Base:", ["Ativos", "Desligados"], horizontal=True)
        df_rol = df_ativos_proc if modo == "Ativos" else df_desligados_proc
        sel = st.selectbox("Consultar:", [""] + list(df_rol["Nome"].unique()))
        if st.button("Ver Detalhes") and sel:
            modal_consulta_investidor(df_rol, sel)

    with aba_analyt:
        m, d, e, f = st.tabs(["📋 Master", "👥 Demográfico", "📊 Estatístico", "💰 Financeiro"])
        with m:
            status = st.multiselect("Status:", ["Ativos", "Desligados"], default=["Ativos"])
            bases = []
            if "Ativos" in status: bases.append(df_ativos_proc)
            if "Desligados" in status: bases.append(df_desligados_proc)
            if bases:
                df_m = pd.concat(bases, ignore_index=True)
                cols = ["Nome", "E-mail corporativo", "BP", "Modelo de contrato", "Cargo", "Remuneração", "Senioridade", "Área", "CPF"]
                st.dataframe(df_m[[c for c in cols if c in df_m.columns]], hide_index=True)
                if st.button("📥 Gerar Relatório Customizado", type="primary"):
                    modal_exportar_excel(df_m)
        with d:
            st.write("Relatórios de Aniversário e Tempo de Casa aqui.")
        with e:
            st.write("Vencimento de Contratos e MEI aqui.")
        with f:
            st.info("⚙️ Configurações futuras.")

    with aba_acoes:
        st.markdown("### ⚡ Central de Ações")
        c1, c2 = st.columns(2)
        if c1.button("📝 Título Doc", use_container_width=True, type="primary"): modal_titulo_doc(df_ativos_proc)
        if c1.button("📄 Demissão Comum", use_container_width=True, type="primary"): modal_comum(df_ativos_proc)
        if c2.button("📄 Aviso Prévio", use_container_width=True, type="primary"): modal_aviso_previo_indenizado(df_ativos_proc)
        if c2.button("🚌 Vale Transporte", use_container_width=True, type="primary"): modal_vale_transporte(df_ativos_proc)
