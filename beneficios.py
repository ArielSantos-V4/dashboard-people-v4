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
def render(df): # <-- Corrigido para receber 'df'
    
    # Proteção simples
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("Você precisa fazer login para acessar esta página.")
        st.stop()

    # NOVO CABEÇALHO (Igual ao DP)
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
    
    # ABAS
    aba_beneficios = st.tabs(["🎁 Benefícios"])
    
    with aba_beneficios[0]:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        col_grafico, col_consulta = st.columns([4, 6])

        # --- COLUNA 1: GRÁFICO ---
        with col_grafico:
            st.markdown("<h3 style='margin-bottom:20px'>📊 Status no plano</h3>", unsafe_allow_html=True)
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            
            if "Situação no plano" in df.columns:
                df_plano = df["Situação no plano"].fillna("Não informado").value_counts().reset_index()
                df_plano.columns = ["Situação", "Quantidade"]
                total = df_plano["Quantidade"].sum()
                df_plano["Percentual"] = (df_plano["Quantidade"] / total) * 100
                
                grafico_plano = alt.Chart(df_plano).mark_arc(innerRadius=80, outerRadius=130, stroke=None).encode(
                    theta="Quantidade:Q",
                    color=alt.Color("Situação:N", scale=alt.Scale(range=["#2E8B57", "#FFA500", "#8A2BE2", "#DC143C", "#8B4513", "#808080"]), legend=alt.Legend(title="Situação", orient="bottom", columns=2)),
                    tooltip=[alt.Tooltip("Situação:N"), alt.Tooltip("Quantidade:Q"), alt.Tooltip("Percentual:Q", format=".1f")]
                ).properties(width=320, height=380)
                st.altair_chart(grafico_plano, use_container_width=True)
            else:
                st.warning("Coluna 'Situação no plano' não encontrada.")

        # --- COLUNA 2: CONSULTA ---
        with col_consulta:
            st.markdown("### 🔎 Consulta de carteirinhas")
            nome_beneficio = st.selectbox("Selecione o investidor", [""] + sorted(df["Nome"].dropna().unique()), key="sel_beneficio", placeholder="Digite ou selecione um nome")
            
            if st.button("Consultar carteirinhas", use_container_width=True, key="btn_consultar_cart"):
                if nome_beneficio:
                    dados = df[df["Nome"] == nome_beneficio].iloc[0]
                    cart_med = str(dados.get("Carteirinha médico", "")).strip()
                    oper_med = str(dados.get("Operadora Médico", "")).strip()
                    cart_odo = str(dados.get("Carteirinha odonto", "")).strip()
                    oper_odo = str(dados.get("Operadora Odonto", "")).strip()
                    situacao = str(dados.get("Situação no plano", "Não informado"))

                    if not cart_med and not cart_odo:
                        st.markdown(f"""
                            <div style="padding: 25px; border-radius: 12px; background: rgba(0,0,0,0.55); color: white; text-align: center;">
                                <h4>⚠️ Investidor não ativo no plano</h4>
                                <p>Este investidor não possui carteirinhas ativas.</p>
                                <hr style="opacity:0.2;">
                                <div style="margin-top: 12px; padding: 10px; border-radius: 8px; background-color: #8B0000; color: white; font-weight: bold;">
                                    Situação atual: {situacao}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.text_input("Carteirinha médico", cart_med if cart_med else "—", disabled=True)
                        st.text_input("Operadora médico", oper_med if oper_med else "—", disabled=True)
                        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                        st.text_input("Carteirinha odonto", cart_odo if cart_odo else "—", disabled=True)
                        st.text_input("Operadora odonto", oper_odo if oper_odo else "—", disabled=True)

        st.markdown("---")

        # --- RELATÓRIOS E AÇÕES ---
        col_relatorios, col_acoes = st.columns([7, 3])
        
        with col_relatorios:
            st.markdown("### 📊 Relatórios")
            abas_rel = st.tabs(["⏰ Pendentes", "📂 Aguardando docs", "📩 Enviar para DBL", "🆗 Aguardando ativação"])
            
            with abas_rel[0]:
                st.markdown("#### Investidores com documentação pendente")
                df_pendentes = df[(df["Situação no plano"] == "Pendente") & (df["Modalidade PJ"] != "MEI")]
                st.dataframe(df_pendentes[["Nome", "E-mail corporativo", "Modelo de contrato", "Solicitar documentação"]], use_container_width=True, hide_index=True)
            
            with abas_rel[1]:
                st.markdown("#### Aguardando envio da documentação")
                df_docs = df[df["Situação no plano"] == "Aguardando docs"]
                st.dataframe(df_docs[["Nome", "E-mail corporativo", "Modelo de contrato", "Enviar no EB"]], use_container_width=True, hide_index=True)
                
            with abas_rel[2]:
                st.markdown("#### Investidores para envio à DBL")
                df_dbl = df[df["Situação no plano"] == "Enviar à DBL"]
                st.dataframe(df_dbl[["Nome", "E-mail corporativo", "Modelo de contrato", "Enviar no EB"]], use_container_width=True, hide_index=True)
                
            with abas_rel[3]:
                st.markdown("#### Investidores aguardando retorno da DBL")
                df_status = df[df["Situação no plano"] == "Aguardando DBL"]
                st.dataframe(df_status[["Nome", "E-mail corporativo", "Modelo de contrato"]], use_container_width=True, hide_index=True)

        with col_acoes:
            st.markdown("### ⚙️ Ações")
            
            if st.button("📄 Gerar Inclusão Subfatura", use_container_width=True):
                modal_inclusao_subfatura(df)
                
            if st.button("📄 Gerar Termo de Subestipulante", use_container_width=True):
                modal_subestipulante(df)
                
            if st.button("📄 Gerar Termo de Não Adesão", use_container_width=True):
                modal_nao_adesao(df)
            
            if st.button("📄 Gerar Exclusão Subfatura", use_container_width=True):
                modal_exclusao_subfatura()
