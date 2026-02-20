import streamlit as st
import pandas as pd
import altair as alt
import re
import unicodedata
from datetime import datetime, date
from docx import Document
import gspread
from google.oauth2.service_account import Credentials
import os

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
}

def substituir_texto(paragraphs, mapa):
    for p in paragraphs:
        for run in p.runs:
            for chave, valor in mapa.items():
                if chave in run.text:
                    run.text = run.text.replace(chave, str(valor))

def formatar_cnpj(valor):
    if pd.isna(valor) or valor == "":
        return ""
    v = str(valor).replace(".0", "").replace(".", "").replace("-", "").replace("/", "").strip()
    v = v.zfill(14)
    if len(v) == 14:
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
    return v

def normalizar_cpf(valor):
    if pd.isna(valor) or valor == "":
        return ""
    v = str(valor).replace(".0", "").replace(".", "").replace("-", "").replace("/", "").strip()
    return re.sub(r"\D", "", v).zfill(11)

def email_para_nome_arquivo(email):
    if not email:
        return ""
    return str(email).replace("@", "_").replace(".", "_").lower()

def carregar_desligados_google_sheets():
    # Tenta carregar credenciais para a planilha de desligados
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        # Ajuste se o caminho do arquivo for diferente
        creds = Credentials.from_service_account_file(
            "credenciais_google.json", 
            scopes=scopes
        )
        client = gspread.authorize(creds)
        # ID da planilha de desligados (conforme seu código original)
        spreadsheet = client.open_by_key("ID_DA_PLANILHA") 
        worksheet = spreadsheet.get_worksheet_by_id(1422602176)
        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"Erro ao carregar planilha de desligados: {e}")
        return pd.DataFrame()

# ==========================================
# MODAIS (GLOBAL)
# ==========================================

@st.dialog("📄 Gerar Inclusão Subfatura")
def modal_inclusao_subfatura(df):
    nomes = sorted(df["Nome"].dropna().unique())
    nome_escolhido = st.selectbox("Selecione o investidor", nomes, key="nome_subfatura")
    data_vigencia = st.date_input("Data de início da vigência", format="DD/MM/YYYY")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    if col2.button("✅ Gerar", use_container_width=True, key="btn_subfatura"):
        dados = df[df["Nome"] == nome_escolhido].iloc[0]
        
        razao_social = str(dados.get("Razão social", ""))
        cnpj = formatar_cnpj(dados.get("CNPJ", ""))
        cpf = normalizar_cpf(dados.get("CPF", ""))
        email_pessoal = str(dados.get("E-mail pessoal", ""))
        email_arquivo = email_para_nome_arquivo(email_pessoal)
        modelo_contrato = str(dados.get("Modelo de contrato", ""))

        if "PJ" not in modelo_contrato.upper():
            st.warning(f"⚠️ **{nome_escolhido}** não possui contrato PJ. Modelo atual: **{modelo_contrato}**")

        try:
            doc = Document("Subfatura.docx")
            vigencia_formatada = data_vigencia.strftime("%d/%m/%Y")
            hoje = date.today()
            data_assinatura = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"

            mapa = {
                "{RAZAO_SOCIAL}": razao_social,
                "{CNPJ}": cnpj,
                "{VIGENCIA}": vigencia_formatada,
                "{DATA}": data_assinatura
            }

            substituir_texto(doc.paragraphs, mapa)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        substituir_texto(cell.paragraphs, mapa)
            for section in doc.sections:
                substituir_texto(section.header.paragraphs, mapa)

            cpf_limpo = re.sub(r"\D", "", cpf)
            nome_arquivo = f"{nome_escolhido} __ {cpf_limpo} __ {email_arquivo} __ Inclusão Subfatura.docx"
            doc.save(nome_arquivo)

            with open(nome_arquivo, "rb") as f:
                st.download_button("⬇️ Download", f, file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
            st.link_button("🔁 Converter PDF", "https://www.ilovepdf.com/pt/word_para_pdf", use_container_width=True)
            st.success("Inclusão Subfatura gerada com sucesso ✅")

        except Exception as e:
            st.error(f"Erro ao gerar documento: {e}")

@st.dialog("📄 Gerar Termo de Subestipulante")
def modal_subestipulante(df):
    nomes = sorted(df["Nome"].dropna().unique())
    nome_escolhido = st.selectbox("Selecione o investidor", nomes, key="nome_termo_sub")

    col1, col2, col3 = st.columns([1, 2, 1])
    if col2.button("✅ Gerar Termo", use_container_width=True, key="btn_termo_sub"):
        dados = df[df["Nome"] == nome_escolhido].iloc[0]
        razao_social = str(dados.get("Razão social", ""))
        cnpj = formatar_cnpj(dados.get("CNPJ", ""))
        cpf = normalizar_cpf(dados.get("CPF", ""))
        email_pessoal = str(dados.get("E-mail pessoal", ""))
        email_arquivo = email_para_nome_arquivo(email_pessoal)

        try:
            doc = Document("Termo de integração de subestipulante.docx")
            hoje = date.today()
            data_assinatura = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"

            mapa = {"{RAZAO_SOCIAL}": razao_social, "{CNPJ}": cnpj, "{DATA}": data_assinatura}

            substituir_texto(doc.paragraphs, mapa)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        substituir_texto(cell.paragraphs, mapa)
            for section in doc.sections:
                substituir_texto(section.header.paragraphs, mapa)

            cpf_limpo = re.sub(r"\D", "", cpf)
            nome_arquivo = f"{nome_escolhido} __ {cpf_limpo} __ {email_arquivo} __ Termo Subestipulante.docx"
            doc.save(nome_arquivo)

            with open(nome_arquivo, "rb") as f:
                st.download_button("⬇️ Download", f, file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
            st.link_button("🔁 Converter PDF", "https://www.ilovepdf.com/pt/word_para_pdf", use_container_width=True)
            st.success("Termo de Subestipulante gerado com sucesso ✅")
        except Exception as e:
            st.error(f"Erro ao gerar documento: {e}")

@st.dialog("📄 Gerar Termo de Não Adesão")
def modal_nao_adesao(df):
    nomes = sorted(df["Nome"].dropna().unique())
    nome_escolhido = st.selectbox("Selecione o investidor", nomes, key="nome_nao_adesao")

    col1, col2, col3 = st.columns([1, 2, 1])
    if col2.button("✅ Gerar Termo", use_container_width=True, key="btn_nao_adesao"):
        dados = df[df["Nome"] == nome_escolhido].iloc[0]
        razao_social = str(dados.get("Razão social", ""))
        cnpj = formatar_cnpj(dados.get("CNPJ", ""))
        
        try:
            doc = Document("Termo de não adesão - Plano de Saúde e Dental.docx")
            hoje = date.today()
            data_assinatura = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"
            
            mapa = {"{RAZAO_SOCIAL}": razao_social, "{CNPJ}": cnpj, "{DATA}": data_assinatura}

            substituir_texto(doc.paragraphs, mapa)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        substituir_texto(cell.paragraphs, mapa)
            for section in doc.sections:
                substituir_texto(section.header.paragraphs, mapa)
                substituir_texto(section.footer.paragraphs, mapa)

            nome_arquivo = f"Termo de não adesão ao plano - {nome_escolhido}.docx"
            doc.save(nome_arquivo)

            with open(nome_arquivo, "rb") as f:
                st.download_button("⬇️ Download", f, file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
            st.link_button("🔁 Converter PDF", "https://www.ilovepdf.com/pt/word_para_pdf", use_container_width=True)
            st.success("Termo de Não Adesão gerado com sucesso ✅")
        except Exception as e:
            st.error(f"Erro ao gerar documento: {e}")

@st.dialog("📄 Gerar Exclusão Subfatura")
def modal_exclusao_subfatura():
    # Carrega planilha de desligados (função específica)
    df_desligados = carregar_desligados_google_sheets()
    
    if df_desligados.empty:
        st.warning("Não foi possível carregar a base de desligados.")
        return

    nomes = sorted(df_desligados["Nome"].dropna().unique())
    nome_escolhido = st.selectbox("Selecione o investidor", nomes, key="nome_exclusao")
    data_exclusao = st.date_input("Data de exclusão", format="DD/MM/YYYY")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    if col2.button("✅ Gerar", use_container_width=True, key="btn_exclusao"):
        dados = df_desligados[df_desligados["Nome"] == nome_escolhido].iloc[0]
        
        razao_social = str(dados.get("Razão social", ""))
        cnpj = formatar_cnpj(dados.get("CNPJ", ""))
        cpf = normalizar_cpf(dados.get("CPF", ""))
        email_pessoal = str(dados.get("E-mail pessoal", ""))
        email_arquivo = email_para_nome_arquivo(email_pessoal)
        modelo_contrato = str(dados.get("Modelo de contrato", ""))

        if "PJ" not in modelo_contrato.upper():
            st.warning(f"⚠️ **{nome_escolhido}** não possui contrato PJ. Modelo atual: **{modelo_contrato}**")

        try:
            doc = Document("Exclusao_Subfatura.docx")
            data_exclusao_formatada = data_exclusao.strftime("%d/%m/%Y")
            hoje = date.today()
            data_assinatura = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"

            mapa = {
                "{RAZAO_SOCIAL}": razao_social,
                "{CNPJ}": cnpj,
                "{DATA_EXCLUSAO}": data_exclusao_formatada,
                "{DATA}": data_assinatura
            }

            substituir_texto(doc.paragraphs, mapa)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        substituir_texto(cell.paragraphs, mapa)
            for section in doc.sections:
                substituir_texto(section.header.paragraphs, mapa)

            cpf_limpo = re.sub(r"\D", "", cpf)
            nome_arquivo = f"{nome_escolhido} __ {cpf_limpo} __ {email_arquivo} __ Exclusão Subfatura.docx"
            doc.save(nome_arquivo)

            with open(nome_arquivo, "rb") as f:
                st.download_button("⬇️ Download", f, file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
            st.link_button("🔁 Converter PDF", "https://www.ilovepdf.com/pt/word_para_pdf", use_container_width=True)
            st.success("Exclusão Subfatura gerada com sucesso ✅")
        except Exception as e:
            st.error(f"Erro ao gerar documento: {e}")

# ==========================================
# FUNÇÃO PRINCIPAL (RENDER)
# ==========================================
def render(df):
    
    # Proteção de Login
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("Você precisa fazer login para acessar esta página.")
        st.stop()

    # CABEÇALHO (PADRÃO V4)
    c_logo, c_texto = st.columns([0.5, 6]) 
    with c_logo:
        st.image("LOGO VERMELHO.png", width=100) 
    with c_texto:
        st.markdown("""
            <div style="display: flex; flex-direction: column; justify-content: center; height: 100px;">
                <h1 style="margin: 0; padding: 0; font-size: 2.2rem; line-height: 1.1;">Gestão de Benefícios</h1>
                <span style="color: grey; font-size: 1.1rem; margin-top: 2px;">V4 Company</span>
            </div>
        """, unsafe_allow_html=True)
    
    # --- AS 4 ABAS SOLICITADAS ---
    aba_dash, aba_cart, aba_anlt, aba_aco = st.tabs([
        "📊 Dashboard", 
        "💳 Carteirinhas", 
        "📈 Analytics", 
        "⚡ Ações"
    ])
    
    # ----------------------------------------------------
    # 1. ABA DASHBOARD
    # ----------------------------------------------------
    with aba_dash:
        st.markdown("<br>", unsafe_allow_html=True)
        if "Situação no plano" in df.columns:
            total_vidas = len(df[df["Situação no plano"] == "Ativo"])
            pendencias = len(df[df["Situação no plano"].isin(["Pendente", "Aguardando docs", "Enviar à DBL"])])
            em_processo = len(df[df["Situação no plano"] == "Aguardando DBL"])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Vidas Ativas", total_vidas)
            c2.metric("Pendências", pendencias, delta_color="inverse")
            c3.metric("Em ativação", em_processo)
            
            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("Situação no plano")
                df_plano = df["Situação no plano"].fillna("Não informado").value_counts().reset_index()
                df_plano.columns = ["Situação", "Quantidade"]
                grafico_pizza = alt.Chart(df_plano).mark_arc(innerRadius=80).encode(
                    theta="Quantidade:Q",
                    color=alt.Color("Situação:N", scale=alt.Scale(range=["#2E8B57", "#FFA500", "#8A2BE2", "#DC143C", "#8B4513", "#808080"])),
                    tooltip=["Situação", "Quantidade"]
                )
                st.altair_chart(grafico_pizza, use_container_width=True)

            with col_g2:
                st.subheader("Vidas por Operadora")
                df_oper = df[df["Operadora Médico"].notna() & (df["Operadora Médico"] != "")]
                df_oper_count = df_oper["Operadora Médico"].value_counts().reset_index()
                df_oper_count.columns = ["Operadora", "Quantidade"]
                grafico_barras = alt.Chart(df_oper_count).mark_bar(color="#E30613").encode(
                    x=alt.X("Operadora:N", sort="-y"), y="Quantidade:Q"
                )
                st.altair_chart(grafico_barras, use_container_width=True)

    # ----------------------------------------------------
    # 2. ABA CARTEIRINHAS
    # ----------------------------------------------------
    with aba_cart:
        st.markdown("### 🔎 Consulta Rápida")
        nome_ben = st.selectbox("Buscar investidor", [""] + sorted(df["Nome"].dropna().unique()), key="sel_ben_cart")
        
        if nome_ben:
            dados = df[df["Nome"] == nome_ben].iloc[0]
            with st.container(border=True):
                c1, c2 = st.columns(2)
                c1.markdown(f"**🏥 Saúde ({dados.get('Operadora Médico', 'N/A')})**")
                c1.code(str(dados.get("Carteirinha médico", "Não possui")).replace(".0", ""), language=None)
                c2.markdown(f"**🦷 Odonto ({dados.get('Operadora Odonto', 'N/A')})**")
                c2.code(str(dados.get("Carteirinha odonto", "Não possui")).replace(".0", ""), language=None)
        
        st.markdown("---")
        st.dataframe(df[df["Situação no plano"] == "Ativo"][["Nome", "Carteirinha médico", "Carteirinha odonto"]], use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # 3. ABA ANALYTICS (Relatórios de Auditoria)
    # ----------------------------------------------------
    with aba_anlt:
        st.markdown("### 📊 Relatórios de Acompanhamento")
        t1, t2, t3 = st.tabs(["⏰ Pendentes", "📩 Fluxo DBL", "🆗 Ativação"])
        
        with t1:
            st.dataframe(df[df["Situação no plano"] == "Pendente"][["Nome", "E-mail corporativo", "Solicitar documentação"]], use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(df[df["Situação no plano"] == "Enviar à DBL"][["Nome", "E-mail corporativo", "Enviar no EB"]], use_container_width=True, hide_index=True)
        with t3:
            st.dataframe(df[df["Situação no plano"] == "Aguardando DBL"][["Nome", "E-mail corporativo"]], use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # 4. ABA AÇÕES (Vazia/Redirecionamento)
    # ----------------------------------------------------
    with aba_aco:
        st.info("💡 As ações de geração de documentos e termos agora estão centralizadas na aba **'⚡ Ações'** do menu principal para facilitar o seu fluxo de trabalho.")
        st.markdown("---")
        st.caption("Task: Utilize o menu à esquerda para acessar a aba de Ações global.")
