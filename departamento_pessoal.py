import streamlit as st
import pandas as pd
import plotly.express as px
import bcrypt
import altair as alt
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from docx import Document
from io import BytesIO
import re
import unicodedata

# ==========================================
# GESTÃO DE ESTADO (SESSION STATE)
# ==========================================
if "investidor_selecionado" not in st.session_state:
    st.session_state.investidor_selecionado = ""

def limpar_investidor():
    st.session_state.investidor_selecionado = ""

# ==========================================
# FUNÇÕES AUXILIARES DE FORMATAÇÃO E CÁLCULO
# ==========================================
def limpar_numero(valor):
    if valor == "" or pd.isna(valor):
        return ""
    return str(valor).replace(".0", "").replace(".", "").replace("-", "").replace("/", "").strip()

def formatar_cpf(valor):
    v = limpar_numero(valor).zfill(11)
    if len(v) == 11:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    return v

def formatar_cnpj(valor):
    v = limpar_numero(valor).zfill(14)
    if len(v) == 14:
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
    return v

def formatar_matricula(valor):
    v = limpar_numero(valor)
    if v.isdigit():
        return v.zfill(6)
    return v

def parse_data_br(coluna):
    return pd.to_datetime(coluna, dayfirst=True, errors="coerce")

def calcular_tempo_casa(data_inicio):
    if pd.isna(data_inicio) or data_inicio == "":
        return ""
    
    # Garante que seja timestamp para evitar erros de tipo
    if not isinstance(data_inicio, pd.Timestamp):
        data_inicio = pd.to_datetime(data_inicio, errors='coerce')
        if pd.isna(data_inicio):
            return ""

    hoje = pd.Timestamp.today().normalize()
    diff = relativedelta(hoje, data_inicio)
    return f"{diff.years} anos, {diff.months} meses e {diff.days} dias"

def email_para_nome_arquivo(email):
    if not email:
        return ""
    email = unicodedata.normalize("NFKC", email)
    return email.strip().lower().replace(" ", "")

def normalizar_cpf(cpf):
    if not cpf:
        return ""
    cpf = re.sub(r"\D", "", str(cpf))
    return cpf.zfill(11)

def gerar_hash_senha(senha):
    return bcrypt.hashpw(
        senha.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

def render_table(df, *, dataframe=True, **kwargs):
    """Renderiza tabelas tratando NaN para exibição."""
    df_view = df.copy()
    df_view = df_view.where(pd.notna(df_view), "")
    if dataframe:
        st.dataframe(df_view, **kwargs)
    else:
        st.table(df_view)

# ==========================================
# FUNÇÕES DE DOCUMENTOS (DOCX)
# ==========================================
def gerar_docx_com_substituicoes(caminho_modelo, substituicoes):
    doc = Document(caminho_modelo)

    def substituir(paragrafo):
        for run in paragrafo.runs:
            for chave, valor in substituicoes.items():
                if chave in run.text:
                    run.text = run.text.replace(chave, valor)

    for paragrafo in doc.paragraphs:
        substituir(paragrafo)

    for tabela in doc.tables:
        for linha in tabela.rows:
            for celula in linha.cells:
                for paragrafo in celula.paragraphs:
                    substituir(paragrafo)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def substituir_runs_paragrafos(doc, mapa):
    for p in doc.paragraphs:
        for run in p.runs:
            for chave, valor in mapa.items():
                if chave in run.text:
                    run.text = run.text.replace(chave, str(valor))

def substituir_runs_tabelas(doc, mapa):
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        for chave, valor in mapa.items():
                            if chave in run.text:
                                run.text = run.text.replace(chave, str(valor))

def substituir_runs_header_footer(doc, mapa):
    for section in doc.sections:
        for p in section.header.paragraphs:
            for run in p.runs:
                for chave, valor in mapa.items():
                    if chave in run.text:
                        run.text = run.text.replace(chave, str(valor))
        for p in section.footer.paragraphs:
            for run in p.runs:
                for chave, valor in mapa.items():
                    if chave in run.text:
                        run.text = run.text.replace(chave, str(valor))

# ==========================================
# LÓGICA DE ALERTAS
# ==========================================
def gerar_alertas_investidor(linha):
    alertas = []
    hoje = pd.Timestamp.today().normalize()
    status = str(linha.get("Situação no plano", "")).strip()

    # ALERTA 1 — SOLICITAR DOCUMENTAÇÃO
    data_solicitar = pd.to_datetime(linha.get("Solicitar documentação"), errors="coerce")
    if status == "Pendente" and pd.notna(data_solicitar):
        dias = (data_solicitar - hoje).days
        if dias < 0:
            alertas.append(("error", "Plano de saúde e dental 🤕\nSolicitação de documentação em atraso. Verificar com urgência!"))
        elif dias == 0:
            alertas.append(("warning", "Plano de saúde e dental ❤️‍🩹\nHoje é a data limite para solicitar a documentação!"))
        elif dias <= 15:
            alertas.append(("info", f"Plano de saúde e dental ❤️‍🩹\nFaltam {dias} dias para solicitar a documentação ao investidor"))

    # ALERTA 2 — ENVIAR NO EB
    data_enviar_eb = pd.to_datetime(linha.get("Enviar no EB"), errors="coerce")
    if status == "Aguardando docs" and pd.notna(data_enviar_eb):
        dias = (data_enviar_eb - hoje).days
        if dias < 0:
            alertas.append(("error", "Plano de saúde e dental 🤕\nEnvio à EB em atraso. Verificar com urgência!"))
        elif dias == 0:
            alertas.append(("warning", "Plano de saúde e dental ❤️‍🩹\nHoje é a data limite para enviar à EB"))
        elif dias <= 15:
            alertas.append(("info", f"Plano de saúde e dental ❤️‍🩹\nFaltam {dias} dias para enviar à EB"))

    if status == "Aguardando DBL":
        alertas.append(("info", "Plano de saúde e dental quase prontos! 🤩 Acompanhar movimentação no portal EB"))
    
    # ALERTA — Aniversário
    nascimento = pd.to_datetime(linha.get("Data de nascimento"), errors="coerce", dayfirst=True)
    if pd.notna(nascimento):
        nascimento = pd.Timestamp(nascimento).normalize()
        if nascimento.month == hoje.month:
            if nascimento.day == hoje.day:
                alertas.append(("info", "Lembrete de Aniversário! 🎉\nHOJE é aniversário do investidor!!"))
            else:
                alertas.append(("info", "Lembrete de Aniversário! 🎉\nEste investidor faz aniversário neste mês"))

    # ALERTA 3 — Contrato
    fim_contrato = pd.to_datetime(linha.get("Térm previsto"), errors="coerce", dayfirst=True)
    if pd.notna(fim_contrato):
        fim_contrato = pd.Timestamp(fim_contrato).normalize()
        dias = (fim_contrato - hoje).days
        if dias < 0:
            alertas.append(("error", "Contrato vencido! 🚨 Verificar com urgência!"))
        elif dias <= 30:
            alertas.append(("warning", f"Alerta! ⚠️ O contrato se encerra em {dias} dia(s)."))

    # ALERTA 4 — MEI
    if linha.get("Modalidade PJ", "") == "MEI":
        alertas.append(("warning", "Atenção! Investidor ainda se encontra na modalidade MEI 😬"))

    return alertas

# ==========================================
# MODAIS (MOVIMENTO PARA ESCOPO GLOBAL)
# ==========================================

@st.dialog(" ")
def modal_consulta_investidor(df_consulta, nome):
    st.markdown('<div class="modal-investidor">', unsafe_allow_html=True)

    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]
            
    col1, col2, col3 = st.columns([3, 3, 2])
        
    # --- COLUNA 1 — PROFISSIONAL ---
    with col1:
        st.markdown("##### 📌 Dados profissionais")
        
        bp = str(linha["BP"]).replace(".0", "")
        matricula = str(linha["Matrícula"]).replace(".0", "").zfill(6)
        
        a1, a2, a3 = st.columns(3)
        a1.text_input("BP", bp, disabled=True)
        a2.text_input("Matrícula", matricula, disabled=True)
        a3.text_input("Situação", linha["Situação"], disabled=True)
    
        a4, a5, a6 = st.columns(3)
        a4.text_input("Data do contrato", linha["Data do contrato"], disabled=True)
        a5.text_input("Término previsto", linha["Térm previsto"], disabled=True)
        a6.text_input("Modelo contrato", linha["Modelo de contrato"], disabled=True)
        
        # CÁLCULO SEGURO DO TEMPO DE CASA (AGORA FUNCIONA)
        tempo_casa = calcular_tempo_casa(linha["Início na V4_dt"])
        
        a7, a8 = st.columns([1, 2])
        a7.text_input("Início na V4", linha["Início na V4"], disabled=True)
        a8.text_input("Tempo de casa", tempo_casa, disabled=True)
    
        a9, a10 = st.columns([3, 1])
        a9.text_input("Unidade / Atuação", linha["Unidade/Atuação"], disabled=True)
        a10.text_input("Modalidade PJ", linha["Modalidade PJ"], disabled=True)
        
        st.text_input("E-mail corporativo", linha["E-mail corporativo"], disabled=True)
        
        cnpj = formatar_cnpj(linha["CNPJ"])
    
        a11, a12 = st.columns(2)
        a11.text_input("CNPJ", cnpj, disabled=True)
        a12.text_input("Razão social", linha["Razão social"], disabled=True)
    
        a13, a14 = st.columns([3, 1])
        a13.text_input("Cargo", linha["Cargo"], disabled=True)
        a14.text_input("Remuneração", linha["Remuneração"], disabled=True)
        
        a15, a16 = st.columns([1, 3])
        a15.text_input("CBO", linha["CBO"], disabled=True)
        a16.text_input("Descrição CBO", linha["Descrição CBO"], disabled=True)
    
    # --- COLUNA 2 — ADMIN / PESSOAL ---
    with col2:
        st.markdown("##### 🧾 Centro de custo")
        codigo_cc = str(linha["Código CC"]).replace(".0", "")
        b1, b2 = st.columns([1, 3])
        b1.text_input("Código CC", codigo_cc, disabled=True)
        b2.text_input("Descrição CC", linha["Descrição CC"], disabled=True)

        b3, b4 = st.columns(2)
        b3.text_input("Senioridade", linha["Senioridade"], disabled=True)
        b4.text_input("Conta contábil", linha["Conta contábil"], disabled=True)
        st.text_input("Liderança direta", linha["Liderança direta"], disabled=True)

        st.markdown("##### 👤 Dados pessoais")
        cpf_val = formatar_cpf(linha["CPF"])
        b5, b6, b7 = st.columns(3)
        b5.text_input("CPF", cpf_val, disabled=True)
        b6.text_input("Nascimento", linha["Data de nascimento"], disabled=True)
        
        idade = ""
        if linha.get("Data de nascimento_dt") is not None and pd.notna(linha["Data de nascimento_dt"]):
            hoje_dt = datetime.today()
            idade = int((hoje_dt - linha["Data de nascimento_dt"]).days / 365.25)
            idade = f"{idade} anos"
        
        b7.text_input("Idade", idade, disabled=True)

        b8, b9 = st.columns(2)
        b8.text_input("CEP", linha["CEP"], disabled=True)
        b9.text_input("Escolaridade", linha["Escolaridade"], disabled=True)

        st.text_input("Telefone pessoal", linha["Telefone pessoal"], disabled=True)
        st.text_input("E-mail pessoal", linha["E-mail pessoal"], disabled=True)

    # --- COLUNA 3 — FOTO / BENEFÍCIOS / LINK ---
    with col3:
        st.markdown("##### 🖼️ Foto")
        if linha["Foto"]:
            st.markdown(f'<div style="display:flex; justify-content:center;"><img src="{linha["Foto"]}" width="160"></div>', unsafe_allow_html=True)
        else:
            st.info("Sem foto")

        st.markdown("##### 🎁 Benefícios")
        st.text_input("Situação no plano", linha["Situação no plano"], disabled=True)

        carteira_med = str(linha["Carteirinha médico"]).replace(".0", "")
        carteira_odo = str(linha["Carteirinha odonto"]).replace(".0", "")

        m1, m2 = st.columns(2)
        m1.text_input("Plano médico", linha["Operadora Médico"], disabled=True)
        m2.text_input("Carteirinha médico", carteira_med, disabled=True)

        st.markdown('<div class="espaco-beneficio"></div>', unsafe_allow_html=True)

        o1, o2 = st.columns(2)
        o1.text_input("Plano odonto", linha["Operadora Odonto"], disabled=True)
        o2.text_input("Carteirinha odonto", carteira_odo, disabled=True)

        col_link, col_alertas = st.columns([1, 3])
        
        with col_link:
            st.markdown("##### 🔗 Link")
            if linha["Link Drive"]:
                st.link_button("Drive", linha["Link Drive"])
            else:
                st.caption("Sem link de Drive")
        
        with col_alertas:
            st.markdown("##### ⚠️ Alertas")
            alertas = st.session_state.get("alertas_atuais", [])
            if alertas:
                with st.container(height=100, border=True):
                    for tipo, mensagem in alertas:
                        if tipo == "error":
                            st.error(mensagem)
                        elif tipo == "warning":
                            st.warning(mensagem)
                        else:
                            st.info(mensagem)

    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("📝 Gerador de título para automação")
def modal_titulo_doc(df):
    col_input, col_clear = st.columns([5, 1])
    with col_input:
        st.text_input("Título original do arquivo", placeholder="Cole aqui o título do arquivo", key="titulo_doc")
    with col_clear:
        st.markdown("<div style='height:23px'></div>", unsafe_allow_html=True)
        def limpar_titulo():
            st.session_state["titulo_doc"] = ""
            st.session_state.pop("titulo_gerado", None)
        st.button("❌", help="Limpar título", on_click=limpar_titulo)

    lista_nomes = sorted(df["Nome"].dropna().unique())
    st.selectbox("Selecione o investidor", options=[""] + lista_nomes, index=0, key="nome_selecionado", placeholder="Digite ou selecione um nome")

    if st.button("✅ Gerar", use_container_width=True):
        titulo_doc = st.session_state.get("titulo_doc", "")
        nome_selecionado = st.session_state.get("nome_selecionado", "")
        if not nome_selecionado or not titulo_doc:
            st.warning("Selecione um nome e informe o título do arquivo.")
            return
        
        dados_filtrados = df[df["Nome"] == nome_selecionado]
        if dados_filtrados.empty:
            st.error("Não foi possível localizar os dados dessa pessoa.")
            return
        
        dados = dados_filtrados.iloc[0]
        cpf_limpo = str(dados.get("CPF", "")).replace(".", "").replace("-", "").replace("/", "").zfill(11)
        email_pessoal = dados.get("E-mail pessoal", "")
        
        st.session_state["titulo_gerado"] = f"{nome_selecionado} __ {cpf_limpo} __ {email_pessoal} __ {titulo_doc}"

    if "titulo_gerado" in st.session_state:
        st.markdown("#### 📄 Título gerado")
        st.code(st.session_state["titulo_gerado"])

@st.dialog("📄 Demissão por comum acordo")
def modal_comum(df):
    st.markdown('<div class="modal_comum">', unsafe_allow_html=True)
    st.markdown("#### Preencha os dados abaixo")
    nome_selecionado = st.selectbox("Nome do colaborador", sorted(df["Nome"].dropna().unique()))
    data_desligamento = st.date_input("Data do desligamento", format="DD/MM/YYYY")
    
    dados_pessoa = df[df["Nome"] == nome_selecionado].iloc[0]
    cargo = dados_pessoa["Cargo"]

    if st.button("✅ Gerar doc"):
        doc = Document("Demissão por comum acordo.docx")
        mapa_substituicao = {
            "{nome_completo}": nome_selecionado,
            "{cargo}": cargo,
            "{data}": data_desligamento.strftime("%d/%m/%Y")
        }
        substituir_texto_docx(doc, mapa_substituicao) # <--- Esta função também precisa estar global
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.success("Documento gerado com sucesso ✅")
        st.download_button(label="⬇️ Baixar documento", data=buffer, file_name=f"Demissão - {nome_selecionado}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    
    if st.button("❌ Cancelar"):
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("📄 Aviso Prévio Indenizado")
def modal_aviso_previo_indenizado(df):
    st.markdown("#### Preencha os dados")
    lista_nomes = sorted(df["Nome"].dropna().unique())
    nome = st.selectbox("Nome do investidor", ["Selecione..."] + lista_nomes)
    data_desligamento = st.date_input("Data do desligamento", format="DD/MM/YYYY")
    data_homologacao = st.date_input("Data da homologação", format="DD/MM/YYYY")

    if st.button("📄 Gerar documento", use_container_width=True):
        if nome == "Selecione...":
            st.warning("Selecione o investidor.")
            return
        
        mapa = {
            "{nome_selecionado}": nome,
            "{data_desligamento}": data_desligamento.strftime("%d/%m/%Y"),
            "{data_homologacao}": data_homologacao.strftime("%d/%m/%Y"),
        }
        arquivo = gerar_docx_com_substituicoes("Aviso prévio Indenizado.docx", mapa)
        st.success("Documento gerado com sucesso!")
        st.download_button(label="⬇️ Baixar documento", data=arquivo, file_name=f"Aviso prévio Indenizado - {nome}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

@st.dialog("🚌 Atualização do Vale Transporte")
def modal_vale_transporte(df_pessoas):
    nome_sel = st.selectbox("Investidor", df_pessoas["Nome"].tolist())
    if not df_pessoas[df_pessoas["Nome"] == nome_sel].empty:
        cpf_sel = df_pessoas.loc[df_pessoas["Nome"] == nome_sel, "CPF"].values[0]
    else:
        cpf_sel = ""

    cep = st.text_input("CEP")
    endereco = st.text_input("Endereço")
    numero = st.text_input("Número")
    bairro = st.text_input("Bairro")
    cidade = st.text_input("Cidade")
    uf = st.text_input("UF")

    st.divider()
    st.subheader("Residência → Trabalho")
    qtd_res = st.selectbox("Quantidade de transportes", [1,2,3,4], key="qtd_res")
    transportes_res = []
    for i in range(qtd_res):
        c1, c2, c3, c4 = st.columns(4)
        tipo = c1.selectbox("Tipo", ["Ônibus", "Metrô", "Trem"], key=f"tipo_res_{i}")
        linha = c2.text_input("Linha", key=f"linha_res_{i}")
        valor = c3.number_input("Valor", min_value=0.0, step=0.01, key=f"valor_res_{i}")
        inte = c4.number_input("Integração", min_value=0.0, step=0.01, key=f"inte_res_{i}")
        transportes_res.append((tipo, linha, valor, inte))

    soma_linhas = len(transportes_res)
    soma_valor = sum(v for _,_,v,_ in transportes_res)
    soma_inte = sum(i for _,_,_,i in transportes_res)

    st.divider()
    st.subheader("Trabalho → Residência")
    qtd_tra = st.selectbox("Quantidade de transportes", [1,2,3,4], key="qtd_tra")
    transportes_tra = []
    for i in range(qtd_tra):
        c1, c2, c3, c4 = st.columns(4)
        tipo = c1.selectbox("Tipo", ["Ônibus", "Metrô", "Trem"], key=f"tipo_tra_{i}")
        linha = c2.text_input("Linha", key=f"linha_tra_{i}")
        valor = c3.number_input("Valor", min_value=0.0, step=0.01, key=f"valor_tra_{i}")
        inte = c4.number_input("Integração", min_value=0.0, step=0.01, key=f"inte_tra_{i}")
        transportes_tra.append((tipo, linha, valor, inte))

    soma_linhas_tra = len(transportes_tra)
    soma_valor_tra = sum(v for _,_,v,_ in transportes_tra)
    soma_inte_tra = sum(i for _,_,_,i in transportes_tra)
    soma_unit = soma_valor + soma_valor_tra
    soma_integracao = soma_inte + soma_inte_tra

    MESES_PT = {1:"janeiro",2:"fevereiro",3:"março",4:"abril",5:"maio",6:"junho",7:"julho",8:"agosto",9:"setembro",10:"outubro",11:"novembro",12:"dezembro"}
    hoje_date = date.today()
    data_extenso = f"{hoje_date.day} de {MESES_PT[hoje_date.month]} de {hoje_date.year}"

    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        gerar = st.button("📄 Gerar documento", use_container_width=True)

    if gerar:
        mapa = {
            "{nome}": nome_sel, "{cpf}": str(cpf_sel), "{cep}": cep, "{endereço}": endereco, "{número}": numero,
            "{bairro}": bairro, "{cidade}": cidade, "{uf_estado}": uf, "{soma_linhas}": str(soma_linhas),
            "{soma_valor}": f"{soma_valor:.2f}", "{soma_inte}": f"{soma_inte:.2f}", "{soma_linhas_tra}": str(soma_linhas_tra),
            "{soma_valor_tra}": f"{soma_valor_tra:.2f}", "{soma_inte_tra}": f"{soma_inte_tra:.2f}",
            "{soma_unit}": f"{soma_unit:.2f}", "{soma_integracao}": f"{soma_integracao:.2f}", "{data}": data_extenso
        }
        for i in range(1, 5):
            for sufixo in ["res", "tra"]:
                mapa.setdefault(f"{{transporte_{i}_{sufixo}}}", "")
                mapa.setdefault(f"{{linha_{i}_{sufixo}}}", "")
                mapa.setdefault(f"{{valor_{i}_{sufixo}}}", "")
                mapa.setdefault(f"{{inte_{i}_{sufixo}}}", "")

        for i, (t, l, v, it) in enumerate(transportes_res, start=1):
            mapa[f"{{transporte_{i}_res}}"] = t
            mapa[f"{{linha_{i}_res}}"] = l
            mapa[f"{{valor_{i}_res}}"] = f"{v:.2f}"
            mapa[f"{{inte_{i}_res}}"] = f"{it:.2f}"

        for i, (t, l, v, it) in enumerate(transportes_tra, start=1):
            mapa[f"{{transporte_{i}_tra}}"] = t
            mapa[f"{{linha_{i}_tra}}"] = l
            mapa[f"{{valor_{i}_tra}}"] = f"{v:.2f}"
            mapa[f"{{inte_{i}_tra}}"] = f"{it:.2f}"

        doc = Document("declaracao_vale_transporte_clt.docx")
        substituir_runs_paragrafos(doc, mapa)
        substituir_runs_tabelas(doc, mapa)
        substituir_runs_header_footer(doc, mapa)
        
        nome_arquivo = f"Declaração de Vale Transporte CLT - {nome_sel}.docx"
        doc.save(nome_arquivo)
        with open(nome_arquivo, "rb") as f:
            st.download_button("⬇️ Download do documento", f, file_name=nome_arquivo, use_container_width=True)

# ==========================================
# FUNÇÃO PRINCIPAL (RENDER)
# ==========================================
def render(df):
    
    # 🔒 Proteção da página
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("Você precisa fazer login para acessar esta página.")
        st.stop()
        
    # CABEÇALHO
    c_logo, c_texto = st.columns([0.5, 6]) 
    with c_logo:
        st.image("LOGO VERMELHO.png", width=100) 
    with c_texto:
        st.markdown("""
            <div style="display: flex; flex-direction: column; justify-content: center; height: 100px;">
                <h1 style="margin: 0; padding: 0; font-size: 2.2rem; line-height: 1.1;">Departamento Pessoal</h1>
                <span style="color: grey; font-size: 1.1rem; margin-top: 2px;">V4 Company</span>
            </div>
        """, unsafe_allow_html=True)
        
    # ABAS
    aba_dashboard, aba_relatorios = st.tabs(["📊 Dashboard", "📄 Relatórios"])
    
    # --- ABA DASHBOARD ---
    with aba_dashboard:
        # Estilos CSS
        st.markdown("""
        <style>
        div[role="dialog"]:has(.modal-investidor) { width: 95vw !important; max-width: 95vw !important; }
        div[role="dialog"]:has(.modal-investidor) > div { max-height: 90vh !important; padding-top: 0px !important;}
        div[role="dialog"]:has(.modal-investidor) > div > header { display: none !important; }
        h5 { font-size: 20px !important; margin-top: 6px !important; margin-bottom: 2px !important; }
        label { font-size: 10px !important; margin-bottom: 0px !important; color: #bdbdbd !important; }
        div[data-testid="stTextInput"] { height: 30px !important; margin-bottom: 25px !important; }
        div[data-testid="stTextInput"] input { height: 40px !important; padding: 10px 10px !important; font-size: 12px !important; line-height: 0px !important; }
        div[data-testid="column"] { padding-top: 5px !important; padding-bottom: 0px !important; }
        .espaco-beneficio { margin-top: 15px; margin-bottom: 4px; }
        </style>
        """, unsafe_allow_html=True)
        
        # PREPARAÇÃO DADOS (DATETIME)
        df["Início na V4_raw"] = df["Início na V4"]
        df["Data de nascimento_raw"] = df["Data de nascimento"]
        df["Data do contrato_raw"] = df.iloc[:, 12]
        df["Térm previsto_raw"] = df.iloc[:, 6]
        
        df["Início na V4_dt"] = parse_data_br(df["Início na V4_raw"])
        df["Data de nascimento_dt"] = parse_data_br(df["Data de nascimento_raw"])
        df["Data do contrato_dt"] = parse_data_br(df["Data do contrato_raw"])
        df["Térm previsto_dt"] = parse_data_br(df["Térm previsto_raw"])
        
        df["Início na V4"] = df["Início na V4_dt"].dt.strftime("%d/%m/%Y").fillna("")
        df["Data de nascimento"] = df["Data de nascimento_dt"].dt.strftime("%d/%m/%Y").fillna("")
        df["Data do contrato"] = df["Data do contrato_dt"].dt.strftime("%d/%m/%Y").fillna("")
        df["Térm previsto"] = df["Térm previsto_raw"].where(
            df["Térm previsto_dt"].isna(),
            df["Térm previsto_dt"].dt.strftime("%d/%m/%Y")
        )

        # SEÇÃO DE CONSULTA
        st.subheader("🔎 Consulta individual do investidor")
        df_consulta = df.fillna("")
        lista_nomes = sorted(df_consulta["Nome"].unique())
            
        with st.form("form_consulta_investidor", clear_on_submit=False):
            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                nome = st.selectbox("Selecione o investidor", ["Selecione um investidor..."] + lista_nomes, key="investidor_selecionado", label_visibility="collapsed")
            with c2:
                consultar = st.form_submit_button("🔍 Consultar")
            with c3:
                limpar = st.form_submit_button("Limpar")
            
            if consultar and st.session_state.investidor_selecionado != "Selecione um investidor...":
                linha = df_consulta[df_consulta["Nome"] == st.session_state.investidor_selecionado].iloc[0]
                st.session_state.alertas_atuais = gerar_alertas_investidor(linha)
                modal_consulta_investidor(df_consulta, st.session_state.investidor_selecionado)
                
            if limpar:
                limpar_investidor()
                st.session_state.abrir_modal_investidor = False

        # SEÇÃO DE TABELA
        st.markdown("---")
        st.markdown("### 📋 Base de investidores")
        busca = st.text_input("Buscar na tabela", placeholder="🔍 Buscar na tabela...", label_visibility="collapsed")
        
        df_tabela = df.copy()
        # Tratamento para exibição
        df_tabela["Término do contrato"] = df_tabela["Térm previsto"]
        df_tabela["Data de início"] = df_tabela["Início na V4"]
        
        for col in ["BP", "Código CC", "Carteirinha médico", "Carteirinha odonto"]:
            if col in df_tabela.columns:
                df_tabela[col] = df_tabela[col].apply(limpar_numero)
        df_tabela["Matrícula"] = df_tabela["Matrícula"].apply(formatar_matricula)
        df_tabela["CPF"] = df_tabela["CPF"].apply(formatar_cpf)
        df_tabela["CNPJ"] = df_tabela["CNPJ"].apply(formatar_cnpj)
        
        if busca:
            df_tabela = df_tabela[df_tabela.astype(str).apply(lambda x: x.str.contains(busca, case=False).any(), axis=1)]
            
        df_tabela.insert(df_tabela.columns.get_loc("Nome") + 1, "Início na V4", df_tabela.pop("Início na V4"))
        
        st.dataframe(
            df_tabela.drop(columns=[c for c in df_tabela.columns if c.endswith("_raw") or c.endswith("_dt")], errors="ignore"),
            use_container_width=True, hide_index=True
        )

        # KPIS
        st.markdown("---")
        hoje_kpi = datetime.today()
        prox_30_dias = hoje_kpi + timedelta(days=30)
        
        headcount = len(df)
        contratos_vencer = df[df["Térm previsto_dt"].notna() & (df["Térm previsto_dt"] <= prox_30_dias)]
        contratos_vencidos = df[df["Térm previsto_dt"].notna() & (df["Térm previsto_dt"] < hoje_kpi)]
        
        pj = len(df[df["Modelo de contrato"] == "PJ"])
        clt = len(df[df["Modelo de contrato"] == "CLT"])
        estagio = len(df[df["Modelo de contrato"] == "Estágio"])
        
        df_adm = df[df["Início na V4_dt"].notna()]
        media_admissoes = df_adm.groupby(df_adm["Início na V4_dt"].dt.to_period("M")).size().mean() if not df_adm.empty else 0
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Headcount", headcount)
        c2.metric("Contratos vencendo (30 dias)", len(contratos_vencer))
        c3.metric("Contratos vencidos", len(contratos_vencidos))
        c4.metric("PJ / CLT / Estágio", f"{pj} / {clt} / {estagio}")
        c5.metric("Média admissões / mês", f"{media_admissoes:.1f}")
        
        st.markdown("---")
        
        # GRÁFICOS
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📃 Modelo de contrato")
            contrato_df = df["Modelo de contrato"].value_counts().reset_index()
            contrato_df.columns = ["Modelo", "Quantidade"]
            st.altair_chart(alt.Chart(contrato_df).mark_arc(innerRadius=60).encode(
                theta="Quantidade:Q", color=alt.Color("Modelo:N", scale=alt.Scale(range=["#E30613", "#B0000A", "#FF4C4C"])),
                tooltip=["Modelo", "Quantidade"]), use_container_width=True)
                
        with g2:
            st.subheader("📍 Local de atuação")
            local_df = df["Unidade/Atuação"].value_counts().reset_index()
            local_df.columns = ["Local", "Quantidade"]
            st.altair_chart(alt.Chart(local_df).mark_bar(color="#E30613").encode(
                x=alt.X("Local:N", sort="-y", axis=alt.Axis(labelAngle=-30)), y="Quantidade:Q", tooltip=["Local", "Quantidade"]), use_container_width=True)
        
        st.subheader("📈 Admissões por mês")
        if not df_adm.empty:
            adm_mes = df_adm.assign(Mes=df_adm["Início na V4_dt"].dt.strftime("%b/%Y")).groupby("Mes").size().reset_index(name="Quantidade")
            st.altair_chart(alt.Chart(adm_mes).mark_line(color="#E30613", point=True).encode(
                x="Mes:N", y="Quantidade:Q", tooltip=["Mes", "Quantidade"]), use_container_width=True)

    # --- ABA RELATÓRIOS ---
    with aba_relatorios:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        col_relatorios, col_divisor, col_acoes = st.columns([7, 0.1, 3])
        with col_divisor:
            st.markdown("""<div style="height: 100%; border-left: 1px solid #e0e0e0; margin: 0 auto;"></div>""", unsafe_allow_html=True)
            
        with col_relatorios:
            st.markdown("## 📊 Relatórios Principais")
            
            # Aniversariantes
            with st.expander("🎉 Aniversariantes do mês", expanded=False):
                meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_atual = datetime.today().month
                mes_selecionado = st.selectbox("Mês", options=list(meses.keys()), format_func=lambda x: meses[x], index=mes_atual - 1)
                
                df_aniversario = df[df["Data de nascimento_dt"].dt.month == mes_selecionado].copy()
                if df_aniversario.empty:
                    st.info("Nenhum aniversariante neste mês 🎈")
                else:
                    ano_atual = datetime.today().year
                    df_aniversario["Nascimento"] = df_aniversario["Data de nascimento_dt"].dt.strftime("%d/%m/%Y")
                    df_aniversario["Idade que completa"] = (ano_atual - df_aniversario["Data de nascimento_dt"].dt.year).astype(int).astype(str) + " anos"
                    df_aniversario["Dia"] = df_aniversario["Data de nascimento_dt"].dt.day
                    df_final = df_aniversario[["Nome", "E-mail corporativo", "Nascimento", "Idade que completa", "Dia"]].sort_values("Dia").reset_index(drop=True)
                    render_table(df_final.drop(columns=["Dia"]), use_container_width=True, hide_index=True)

            # Contratos a vencer
            with st.expander("⏰ Contratos a vencer", expanded=False):
                c1, c2 = st.columns(2)
                d_ini = c1.date_input("Data inicial", value=datetime.today().date(), format="DD/MM/YYYY")
                d_fim = c2.date_input("Data final", value=datetime.today().date() + relativedelta(months=3), format="DD/MM/YYYY")
                
                ini_ts = pd.Timestamp(d_ini)
                fim_ts = pd.Timestamp(d_fim)
                
                df_venc = df[df["Térm previsto_dt"].notna() & (df["Térm previsto_dt"] >= ini_ts) & (df["Térm previsto_dt"] <= fim_ts)].sort_values("Térm previsto_dt")
                
                if df_venc.empty:
                    st.info("Nenhum contrato vencendo no período selecionado ⏳")
                else:
                    df_venc["Térm previsto"] = df_venc["Térm previsto_dt"].dt.strftime("%d/%m/%Y")
                    render_table(df_venc[["Nome", "E-mail corporativo", "Modelo de contrato", "Térm previsto"]], use_container_width=True, hide_index=True)

            # MEI
            with st.expander("💼 Investidores MEI", expanded=False):
                if "Modalidade PJ" in df.columns:
                    df_mei = df[df["Modalidade PJ"].astype(str).str.upper().str.contains("MEI", na=False)]
                    if df_mei.empty:
                        st.info("Nenhum investidor MEI encontrado.")
                    else:
                        st.warning(f"⚠️ Temos **{len(df_mei)} investidores MEI**.")
                        st.dataframe(df_mei[["Nome", "Modalidade PJ"]], use_container_width=True, hide_index=True)

            # Tempo de Casa
            with st.expander("⏳ Tempo de Casa", expanded=False):
                df_tempo = df.copy()
                # Tenta achar a coluna certa
                col_inicio_found = next((col for col in df_tempo.columns if "início" in col.lower() or "inicio" in col.lower()), None)
                
                if col_inicio_found:
                    df_tempo["Inicio_dt"] = pd.to_datetime(df_tempo[col_inicio_found], dayfirst=True, errors="coerce")
                    df_tempo["Tempo de casa"] = df_tempo["Inicio_dt"].apply(calcular_tempo_casa)
                    
                    min_anos = st.selectbox("Tempo mínimo de casa (anos)", [0, 1, 2, 3, 4, 5], index=0)
                    if min_anos > 0:
                        hj = pd.Timestamp.today().normalize()
                        df_tempo = df_tempo[(hj - df_tempo["Inicio_dt"]).dt.days >= min_anos * 365]
                    
                    st.dataframe(df_tempo[["Nome", col_inicio_found, "Tempo de casa"]], use_container_width=True, hide_index=True)

        with col_acoes:
            st.markdown("## ⚙️ Ações")
            
            def abrir_modal_titulo():
                st.session_state["titulo_doc"] = ""
                st.session_state["nome_selecionado"] = ""
                st.session_state.pop("titulo_gerado", None)
                modal_titulo_doc(df) # Passa df explicitamente

            if st.button("📝 Título de doc para automação", use_container_width=True):
                abrir_modal_titulo()

            if st.button("📄 Demissão por comum acordo", use_container_width=True):
                modal_comum(df)

            if st.button("📄 Aviso Prévio Indenizado", use_container_width=True):
                modal_aviso_previo_indenizado(df)

            if st.button("🚌 Atualização do Vale Transporte", use_container_width=True):
                modal_vale_transporte(df)
