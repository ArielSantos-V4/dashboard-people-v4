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
# PALETA DE CORES V4
# ==========================================
CORES_V4 = ["#E30613", "#8B0000", "#FF4C4C", "#404040", "#D3D3D3"]

# ==========================================
# GESTÃO DE ESTADO
# ==========================================
if "investidor_selecionado" not in st.session_state:
    st.session_state.investidor_selecionado = ""

# ==========================================
# FUNÇÕES AUXILIARES
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

def formatar_matricula(valor):
    v = limpar_numero(valor)
    return v.zfill(6) if v.isdigit() else v

def parse_data_br(coluna):
    return pd.to_datetime(coluna, dayfirst=True, errors="coerce")

def calcular_tempo_casa(data_inicio):
    if pd.isna(data_inicio) or data_inicio == "": return ""
    if not isinstance(data_inicio, pd.Timestamp):
        data_inicio = pd.to_datetime(data_inicio, errors='coerce')
        if pd.isna(data_inicio): return ""
    hoje = pd.Timestamp.today().normalize()
    diff = relativedelta(hoje, data_inicio)
    return f"{diff.years} anos, {diff.months} meses e {diff.days} dias"

def email_para_nome_arquivo(email):
    if not email: return ""
    return unicodedata.normalize("NFKC", email).strip().lower().replace(" ", "")

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
    for s in doc.sections:
        for p in s.header.paragraphs: replace_runs(p)
        for p in s.footer.paragraphs: replace_runs(p)

def gerar_docx_com_substituicoes(caminho, mapa):
    doc = Document(caminho)
    substituir_texto_docx(doc, mapa)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def calcular_idade(dt_nasc):
    if pd.isna(dt_nasc) or dt_nasc == "": return ""
    try:
        # Se for string, tenta converter, se já for timestamp, usa direto
        if not isinstance(dt_nasc, pd.Timestamp):
            dt_nasc = pd.to_datetime(dt_nasc, dayfirst=True, errors='coerce')
        
        if pd.isna(dt_nasc): return ""
        
        hoje = pd.Timestamp.today()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{idade} anos"
    except:
        return ""
        
# ==========================================
# LÓGICA DE ALERTAS (ATIVOS)
# ==========================================
def gerar_alertas_investidor(linha):
    alertas = []
    hoje = pd.Timestamp.today().normalize()
    status = str(linha.get("Situação no plano", "")).strip()

    # --- AJUSTE AQUI OS DIAS DE AVISO ---
    DIAS_AVISO_PREVIO = 15  # Voltei para 15 dias conforme seu fluxo original
    
    # 1. Docs Plano (CORREÇÃO: dayfirst=True)
    data_solicitar = pd.to_datetime(linha.get("Solicitar documentação"), dayfirst=True, errors="coerce")
    if status == "Pendente" and pd.notna(data_solicitar):
        data_solicitar = data_solicitar.normalize() # Remove horas para comparar apenas datas
        dias = (data_solicitar - hoje).days
        
        if dias < 0: 
            alertas.append(("error", "Docs Plano: Atrasado!"))
        elif dias <= DIAS_AVISO_PREVIO: 
            alertas.append(("info", f"Docs Plano: Faltam {dias} dias"))

    # 2. Envio EB (CORREÇÃO: dayfirst=True)
    data_enviar_eb = pd.to_datetime(linha.get("Enviar no EB"), dayfirst=True, errors="coerce")
    if status == "Aguardando docs" and pd.notna(data_enviar_eb):
        data_enviar_eb = data_enviar_eb.normalize()
        dias = (data_enviar_eb - hoje).days
        
        if dias < 0: 
            alertas.append(("error", "Envio EB: Atrasado!"))
        elif dias <= DIAS_AVISO_PREVIO: 
            alertas.append(("info", f"Envio EB: Faltam {dias} dias"))

    # 3. Aniversário (CORREÇÃO: dayfirst=True)
    nascimento = pd.to_datetime(linha.get("Data de nascimento"), dayfirst=True, errors="coerce")
    if pd.notna(nascimento):
        nascimento = nascimento.normalize()
        if nascimento.month == hoje.month:
            if nascimento.day == hoje.day:
                alertas.append(("success", "Feliz Aniversário! Hoje! 🎂"))
            else:
                alertas.append(("info", f"Aniversariante do mês (Dia {nascimento.day}) 🎉"))

    # 4. Contrato (CORREÇÃO: dayfirst=True)
    fim_contrato = pd.to_datetime(linha.get("Térm previsto"), dayfirst=True, errors="coerce")
    if pd.notna(fim_contrato):
        fim_contrato = fim_contrato.normalize()
        dias = (fim_contrato - hoje).days
        
        if dias < 0: 
            alertas.append(("error", "Contrato Vencido! 🚨"))
        elif dias <= 30: 
            alertas.append(("warning", f"Contrato vence em {dias} dias"))

    if str(linha.get("Modalidade PJ", "")).strip().upper() == "MEI":
        alertas.append(("warning", "Investidor MEI ⚠️"))

    return alertas

# ==========================================
# FUNÇÕES AUXILIARES DE AÇÃO
# ==========================================
def validar_clt(row):
    """Verifica se o investidor é CLT ou PJ/Estágio"""
    modelo = str(row.get("Modelo de contrato", "")).upper()
    # Lista de termos que indicam NÃO ser CLT
    nao_clt = ["PJ", "PRESTADOR", "ESTÁGIO", "ESTAGIÁRIO", "BOLSISTA"]
    
    eh_clt = True
    tipo_encontrado = "CLT"
    
    for termo in nao_clt:
        if termo in modelo:
            eh_clt = False
            tipo_encontrado = modelo
            break
            
    return eh_clt, tipo_encontrado

# ==========================================
# MODAIS DE AÇÃO (DEFINIÇÕES GLOBAIS)
# ==========================================

@st.dialog("📝 Título Doc Automação")
def modal_titulo_doc(df):
    st.markdown("""
        <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
            <span style="color: #404040; font-size: 14px;">
                Gera o nome do arquivo padronizado para salvar no Drive/B4.
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    nome = st.selectbox("Investidor", sorted(df["Nome"].unique()))
    titulo = st.text_input("Nome do Documento (ex: Contrato PJ)")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Centralizando botão
    c1, c2, c3 = st.columns([1, 2, 1])
    if c2.button("Gerar Título", use_container_width=True):
        if nome and titulo:
            row = df[df["Nome"]==nome].iloc[0]
            cpf = str(row.get("CPF","")).replace(".", "").replace("-", "").zfill(11)
            email = str(row.get("E-mail pessoal","")).lower()
            st.code(f"{nome} __ {cpf} __ {email} __ {titulo}")
        else:
            st.warning("Preencha todos os campos.")

@st.dialog("📄 Demissão Comum Acordo")
def modal_comum(df):
    st.markdown("""
        <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
            <span style="color: #404040; font-size: 14px;">
                Gera a minuta de acordo para formalização do desligamento consensual.
            </span>
        </div>
    """, unsafe_allow_html=True)

    nome_selecionado = st.selectbox("Nome do colaborador", sorted(df["Nome"].dropna().unique()), key="sel_comum")
    data_desligamento = st.date_input("Data do desligamento", format="DD/MM/YYYY", key="dt_comum")
    
    # 1. VALIDAÇÃO VÍNCULO
    dados_pessoa = df[df["Nome"] == nome_selecionado].iloc[0]
    eh_clt, tipo_contrato = validar_clt(dados_pessoa)
    
    liberar_geracao = False
    
    if eh_clt:
        liberar_geracao = True
    else:
        st.markdown(f"""
            <div style="padding: 10px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 4px; margin-bottom: 10px;">
                ⚠️ <b>Atenção:</b> O vínculo cadastrado é <b>{tipo_contrato}</b>. Este documento é padrão CLT.
            </div>
        """, unsafe_allow_html=True)
        if st.checkbox("Estou ciente e desejo gerar mesmo assim", key="chk_comum"):
            liberar_geracao = True

    # 2. GERAÇÃO
    if liberar_geracao:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        
        mapa = {
            "{nome_completo}": nome_selecionado,
            "{cargo}": dados_pessoa.get("Cargo", ""),
            "{data}": data_desligamento.strftime("%d/%m/%Y")
        }

        try:
            # Tenta gerar o arquivo em memória para download imediato
            arquivo_pronto = gerar_docx_com_substituicoes("Demissão por comum acordo.docx", mapa)
            
            c2.download_button(
                label="📄 Gerar e Baixar DOC",
                data=arquivo_pronto,
                file_name=f"Demissão - {nome_selecionado}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary"
            )
        except Exception as e:
            c2.error("Modelo .docx não encontrado")
            # st.caption(f"Detalhe do erro: {e}") # Descomente para debug

@st.dialog("📄 Aviso Prévio Indenizado")
def modal_aviso_previo_indenizado(df):
    st.markdown("""
        <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
            <span style="color: #404040; font-size: 14px;">
                Emite o comunicado de dispensa com aviso prévio indenizado.
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    nome = st.selectbox("Nome do investidor", ["Selecione..."] + sorted(df["Nome"].dropna().unique()), key="sel_aviso")
    
    c_dat1, c_dat2 = st.columns(2)
    data_des = c_dat1.date_input("Data desligamento", format="DD/MM/YYYY", key="dt_des_aviso")
    data_hom = c_dat2.date_input("Data homologação", format="DD/MM/YYYY", key="dt_hom_aviso")
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])

    if nome != "Selecione...":
        # 1. VALIDAÇÃO VÍNCULO
        dados_pessoa = df[df["Nome"] == nome].iloc[0]
        eh_clt, tipo_contrato = validar_clt(dados_pessoa)
        
        liberar_geracao = False
        
        if eh_clt:
            liberar_geracao = True
        else:
            st.markdown(f"""
                <div style="padding: 10px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 4px; margin-bottom: 10px;">
                    ⚠️ <b>Atenção:</b> Investidor cadastrado como <b>{tipo_contrato}</b>. Aviso Prévio é típico de CLT.
                </div>
            """, unsafe_allow_html=True)
            if st.checkbox("Confirmar geração mesmo assim", key="chk_aviso"):
                liberar_geracao = True
        
        # 2. GERAÇÃO
        if liberar_geracao:
            mapa = {
                "{nome_selecionado}": nome,
                "{data_desligamento}": data_des.strftime("%d/%m/%Y"),
                "{data_homologacao}": data_hom.strftime("%d/%m/%Y"),
            }
            
            try:
                arquivo_pronto = gerar_docx_com_substituicoes("Aviso prévio Indenizado.docx", mapa)
                
                c2.download_button(
                    label="📄 Gerar e Baixar DOC",
                    data=arquivo_pronto,
                    file_name=f"Aviso Prévio - {nome}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                c2.error("Modelo .docx não encontrado")

@st.dialog("🚌 Atualização do Vale Transporte")
def modal_vale_transporte(df_pessoas):
    st.markdown("""
        <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
            <span style="color: #404040; font-size: 14px;">
                Gera a declaração de opção/desistência de Vale Transporte (CLT).
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    nome_sel = st.selectbox("Investidor", sorted(df_pessoas["Nome"].dropna().unique()), key="sel_vt")
    
    # Validações e Busca de Dados
    cpf_sel = ""
    eh_clt = True
    tipo_contrato = "CLT"

    if nome_sel:
        res = df_pessoas[df_pessoas["Nome"] == nome_sel]
        if not res.empty: 
            row = res.iloc[0]
            cpf_sel = str(row.get("CPF", ""))
            eh_clt, tipo_contrato = validar_clt(row)

    c_end1, c_end2 = st.columns([1, 3])
    cep = c_end1.text_input("CEP")
    endereco = c_end2.text_input("Endereço")
    
    c_end3, c_end4, c_end5 = st.columns([1, 2, 2])
    numero = c_end3.text_input("Número")
    bairro = c_end4.text_input("Bairro")
    cidade = c_end5.text_input("Cidade")
    uf = st.text_input("UF")

    st.divider()
    
    # --- ÁREA DE VALIDAÇÃO ---
    liberar_geracao = False
    if eh_clt:
        liberar_geracao = True
    else:
        st.markdown(f"""
            <div style="padding: 10px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 4px; margin-bottom: 10px;">
                ⚠️ <b>Atenção:</b> Investidor <b>{tipo_contrato}</b> não tem direito legal a Vale Transporte (CLT).
            </div>
        """, unsafe_allow_html=True)
        if st.checkbox("Forçar geração do documento", key="chk_vt"):
            liberar_geracao = True

    # --- INPUTS E GERAÇÃO (SÓ APARECE SE LIBERADO) ---
    if liberar_geracao:
        # =====================
        # IDA
        # =====================
        st.subheader("Residência → Trabalho")
        qtd_res = st.selectbox("Quantidade de transportes (Ida)", [1,2,3,4], key="qtd_res")
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

        # =====================
        # VOLTA
        # =====================
        st.divider()
        st.subheader("Trabalho → Residência")
        qtd_tra = st.selectbox("Quantidade de transportes (Volta)", [1,2,3,4], key="qtd_tra")
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
        
        # TOTAIS
        soma_unit = soma_valor + soma_valor_tra
        soma_integracao = soma_inte + soma_inte_tra

        # DATA
        MESES_PT = {1:"janeiro",2:"fevereiro",3:"março",4:"abril",5:"maio",6:"junho",7:"julho",8:"agosto",9:"setembro",10:"outubro",11:"novembro",12:"dezembro"}
        hoje = datetime.today()
        data_extenso = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"
        
        st.divider()
        c1, c2, c3 = st.columns([1, 2, 1])

        mapa = {
            "{nome}": nome_sel, "{cpf}": cpf_sel, "{cep}": cep, "{endereço}": endereco,
            "{número}": numero, "{bairro}": bairro, "{cidade}": cidade, "{uf_estado}": uf,
            "{soma_linhas}": str(soma_linhas), "{soma_valor}": f"{soma_valor:.2f}", "{soma_inte}": f"{soma_inte:.2f}",
            "{soma_linhas_tra}": str(soma_linhas_tra), "{soma_valor_tra}": f"{soma_valor_tra:.2f}", "{soma_inte_tra}": f"{soma_inte_tra:.2f}",
            "{soma_unit}": f"{soma_unit:.2f}", "{soma_integracao}": f"{soma_integracao:.2f}",
            "{data}": data_extenso,
        }

        # 🔹 GARANTE CAMPOS EM BRANCO
        for i in range(1, 5):
            for sufixo in ["res", "tra"]:
                mapa[f"{{transporte_{i}_{sufixo}}}"] = ""
                mapa[f"{{linha_{i}_{sufixo}}}"] = ""
                mapa[f"{{valor_{i}_{sufixo}}}"] = ""
                mapa[f"{{inte_{i}_{sufixo}}}"] = ""

        # 🔹 PREENCHE IDA E VOLTA
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

        try:
            arquivo_pronto = gerar_docx_com_substituicoes("declaracao_vale_transporte_clt.docx", mapa)
            
            c2.download_button(
                label="📄 Gerar e Baixar Declaração",
                data=arquivo_pronto,
                file_name=f"VT - {nome_sel}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary"
            )
        except Exception as e:
            c2.error("Modelo .docx não encontrado")
            
# ==========================================
# MODAL DE CONSULTA (HÍBRIDO - REFORMULADO V3)
# ==========================================
@st.dialog(" ", width="large")
def modal_consulta_investidor(df_consulta, nome, tipo_base="ativo"):
    # --- CSS INJETADO ---
    st.markdown("""
        <style>
        .stTextInput input[disabled] {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
            font-weight: 500 !important;
            opacity: 1 !important;
        }
        .stElementContainer {
            margin-bottom: -15px;
        }
        h2 {
            padding-top: 0rem !important;
            padding-bottom: 0.5rem !important;
        }
        h5 {
            font-size: 16px !important;
            margin-bottom: 5px !important;
            color: #E30613 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Função auxiliar
    def safe_val(val):
        if pd.isna(val) or str(val).lower() in ['nan', 'nat', 'none', '']:
            return ""
        return str(val)

    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]

    # --- CABEÇALHO PERSONALIZADO ---
    if tipo_base == "desligado":
        dt_rescisao = safe_val(linha.get("Data de rescisão", ""))
        # HTML para alinhar Nome à esquerda e Status à direita na mesma linha
        st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <h2 style="margin: 0;">{nome}</h2>
                <span style="color: #E30613; font-weight: bold; font-size: 16px;">
                    Desligado em {dt_rescisao}
                </span>
            </div>
            <hr style="margin-top: 0px; margin-bottom: 20px; border-top: 1px solid #ff4b4b;">
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"## {nome}")
        st.markdown("---")
            
    # Layout de 3 Colunas
    col1, col2, col3 = st.columns([1.3, 1.3, 0.8])
        
    # ==========================================
    # COLUNA 1: PROFISSIONAL
    # ==========================================
    with col1:
        st.markdown("##### 👔 Profissional")
        st.markdown("<br>", unsafe_allow_html=True)

        # Linha 1: BP | Matrícula | Data Contrato
        c1_1, c1_2, c1_3 = st.columns(3)
        c1_1.text_input("BP", safe_val(str(linha.get("BP", "")).replace(".0", "")), disabled=True)
        c1_2.text_input("Matrícula", safe_val(str(linha.get("Matrícula", "")).replace(".0", "").zfill(6)), disabled=True)
        c1_3.text_input("Data Contrato", safe_val(linha.get("Data do contrato")), disabled=True)

        # Linha 2: Modelo | Modalidade | Término
        c2_1, c2_2, c2_3 = st.columns(3)
        c2_1.text_input("Modelo", safe_val(linha.get("Modelo de contrato")), disabled=True)
        c2_2.text_input("Modalidade PJ", safe_val(linha.get("Modalidade PJ")), disabled=True)
        
        lbl_term = "Data Rescisão" if tipo_base == "desligado" else "Término Prev."
        val_term = linha.get("Data de rescisão") if tipo_base == "desligado" else linha.get("Térm previsto")
        c2_3.text_input(lbl_term, safe_val(val_term), disabled=True)

        # Linha 3: Unidade (Pequeno) | Email (Grande) -> Proporção 1:2
        c3_1, c3_2 = st.columns([1, 2])
        c3_1.text_input("Unidade", safe_val(linha.get("Unidade/Atuação")), disabled=True)
        c3_2.text_input("E-mail Corporativo", safe_val(linha.get("E-mail corporativo")), disabled=True)

        # Linha 4: Início (Pequeno) | Tempo (Grande) -> Proporção 1:2
        c4_1, c4_2 = st.columns([1, 2])
        tempo = calcular_tempo_casa(linha.get("Início na V4_dt"))
        c4_1.text_input("Início na V4", safe_val(linha.get("Início na V4")), disabled=True)
        c4_2.text_input("Tempo de Casa", safe_val(tempo), disabled=True)

        # Linha 5: CNPJ | Razão
        c5_1, c5_2 = st.columns([1, 1.5])
        c5_1.text_input("CNPJ", formatar_cnpj(safe_val(linha.get("CNPJ"))), disabled=True)
        c5_2.text_input("Razão Social", safe_val(linha.get("Razão social")), disabled=True)

        # Linha 6: Cargo (Grande) | Remuneração (Pequeno - tam BP) -> Proporção 2:1
        c6_1, c6_2 = st.columns([2, 1])
        c6_1.text_input("Cargo", safe_val(linha.get("Cargo")), disabled=True)
        c6_2.text_input("Remuneração", safe_val(linha.get("Remuneração")), disabled=True)

        # Linha 7: CBO
        c7_1, c7_2 = st.columns([1, 2])
        c7_1.text_input("CBO", safe_val(str(linha.get("CBO", "")).replace(".0","")), disabled=True)
        c7_2.text_input("Descrição CBO", safe_val(linha.get("Descrição CBO")), disabled=True)

        # Link Drive (Movido para cá)
        st.markdown("<br>", unsafe_allow_html=True)
        if linha.get("Link Drive Docs"):
            st.link_button("📂 Abrir documentação do investidor", linha["Link Drive Docs"], use_container_width=True)
        else:
            st.button("📂 Sem documentação", disabled=True, use_container_width=True)

    # ==========================================
    # COLUNA 2: CENTRO DE CUSTO & PESSOAL
    # ==========================================
    with col2:
        st.markdown("##### 🏢 Centro de Custo")
        st.markdown("<br>", unsafe_allow_html=True)

        d1_1, d1_2 = st.columns([1, 2.5])
        d1_1.text_input("Cód. CC", safe_val(str(linha.get("Código CC", "")).replace(".0", "")), disabled=True)
        d1_2.text_input("Descrição CC", safe_val(linha.get("Descrição CC")), disabled=True)
        
        d2_1, d2_2, d2_3 = st.columns([1, 1, 1])
        d2_1.text_input("ID Vaga", safe_val(str(linha.get("ID Vaga", "")).replace(".0","")), disabled=True)
        d2_2.text_input("Conta Contábil", safe_val(str(linha.get("Conta contábil", "")).replace(".0","")), disabled=True)
        d2_3.text_input("Área", safe_val(linha.get("Área")), disabled=True)

        d3_1, d3_2 = st.columns([1, 2]) 
        d3_1.text_input("Senioridade", safe_val(linha.get("Senioridade")), disabled=True)
        d3_2.text_input("Liderança Direta", safe_val(linha.get("Liderança direta")), disabled=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        st.markdown("##### 👤 Dados Pessoais")
        st.markdown("<br>", unsafe_allow_html=True)

        e1_1, e1_2, e1_3 = st.columns([1.2, 1, 0.8])
        e1_1.text_input("CPF", formatar_cpf(safe_val(linha.get("CPF"))), disabled=True)
        e1_2.text_input("Nascimento", safe_val(linha.get("Data de nascimento")), disabled=True)
        idade_str = calcular_idade(linha.get("Data de nascimento_dt"))
        e1_3.text_input("Idade", safe_val(idade_str), disabled=True)

        e2_1, e2_2 = st.columns([1, 2])
        e2_1.text_input("CEP", safe_val(str(linha.get("CEP", "")).replace(".0","")), disabled=True)
        e2_2.text_input("Escolaridade", safe_val(linha.get("Escolaridade")), disabled=True)

        # Email Pessoal (Grande) | Telefone (Pequeno - tam Área) -> Proporção 2:1
        e3_1, e3_2 = st.columns([2, 1])
        e3_1.text_input("E-mail Pessoal", safe_val(linha.get("E-mail pessoal")), disabled=True)
        e3_2.text_input("Telefone", safe_val(linha.get("Telefone pessoal")), disabled=True)

    # ==========================================
    # COLUNA 3: FOTO, BENEFÍCIOS & ALERTAS
    # ==========================================
    with col3:
        # Foto (Sem título, apenas a imagem)
        foto = linha.get("Foto", "")
        if foto and str(foto).startswith("http"):
            st.markdown(f'<div style="display:flex; justify-content:center; margin-bottom:20px; margin-top: 25px;"><img src="{foto}" width="120" style="border-radius:8px; box-shadow: 0px 2px 5px rgba(0,0,0,0.1);"></div>', unsafe_allow_html=True)
        else:
            st.markdown("<br><br>", unsafe_allow_html=True) # Espaço vazio para alinhar se não tiver foto
            st.info("Sem foto")

        st.divider()
        st.markdown("##### 🎁 Benefícios")
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.text_input("Situação Plano", safe_val(linha.get("Situação no plano")), disabled=True)
        
        st.markdown("**Saúde**")
        f1_1, f1_2 = st.columns(2)
        f1_1.text_input("Op. Méd", safe_val(linha.get("Operadora Médico")), disabled=True, label_visibility="collapsed", key="k_op_m")
        f1_2.text_input("Cart. Méd", safe_val(str(linha.get("Carteirinha médico", "")).replace(".0","")), disabled=True, label_visibility="collapsed", key="k_crt_m")

        st.markdown("**Dental**")
        f2_1, f2_2 = st.columns(2)
        f2_1.text_input("Op. Dent", safe_val(linha.get("Operadora Odonto")), disabled=True, label_visibility="collapsed", key="k_op_d")
        f2_2.text_input("Cart. Dent", safe_val(str(linha.get("Carteirinha odonto", "")).replace(".0","")), disabled=True, label_visibility="collapsed", key="k_crt_d")
        
        if tipo_base == "ativo":
            st.divider()
            st.markdown("##### ⚠️ Alertas")
            alertas = gerar_alertas_investidor(linha)
            if alertas:
                # Altura fixa com rolagem automática se passar do tamanho
                with st.container(height=80, border=True):
                    for tipo, msg in alertas:
                        if tipo == "error": st.error(msg, icon="🚨")
                        elif tipo == "warning": st.warning(msg, icon="⚠️")
                        elif tipo == "success": st.success(msg, icon="🎉")
                        else: st.info(msg, icon="ℹ️")
                                        
# ==========================================
# RENDER PRINCIPAL
# ==========================================
def render(df_ativos, df_desligados):
    
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("Faça login na tela inicial.")
        st.stop()
        
    c_logo, c_texto = st.columns([0.5, 6]) 
    with c_logo: st.image("LOGO VERMELHO.png", width=100) 
    with c_texto:
        st.markdown("""
            <div style="display: flex; flex-direction: column; justify-content: center; height: 100px;">
                <h1 style="margin: 0; padding: 0; font-size: 2.2rem; line-height: 1.1;">Departamento Pessoal</h1>
                <span style="color: grey; font-size: 1.1rem; margin-top: 2px;">Gestão de Talentos</span>
            </div>
        """, unsafe_allow_html=True)
        
    aba_dashboard, aba_rolling, aba_analytics = st.tabs(["📊 Dashboard", "👥 Rolling", "📈 Analytics"])
    
    # --- PREPARAÇÃO DE DATAS ---
    def preparar_dataframe(df_raw):
        df = df_raw.copy()
        cols_data = ["Início na V4", "Data de nascimento", "Data do contrato", "Térm previsto", "Data de rescisão"]
        for col in cols_data:
            if col in df.columns:
                df[f"{col}_dt"] = parse_data_br(df[col])
                df[col] = df[f"{col}_dt"].dt.strftime("%d/%m/%Y").fillna("")
        return df

    df_ativos_proc = preparar_dataframe(df_ativos)
    df_desligados_proc = preparar_dataframe(df_desligados)

    # ----------------------------------------------------
    # ABA DASHBOARD (COM FILTROS DINÂMICOS)
    # ----------------------------------------------------
    with aba_dashboard:
        # --- SEÇÃO DE FILTROS ---
        st.markdown("""
            <div style="background-color: #f9f9f9; padding: 10px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 10px;">
                <span style="color: #404040; font-size: 14px;">
                    Acompanhe abaixo os principais indicadores (KPIs) e gráficos demográficos referentes exclusivamente à <b>base de investidores</b>.
                </span>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 Filtros Dinâmicos", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            
            # Opções de Filtro (Ordenadas e Únicas)
            opts_unidade = sorted(list(df_ativos_proc["Unidade/Atuação"].dropna().unique()))
            opts_area = sorted(list(df_ativos_proc["Área"].dropna().unique())) if "Área" in df_ativos_proc.columns else []
            opts_lider = sorted(list(df_ativos_proc["Liderança direta"].dropna().unique())) if "Liderança direta" in df_ativos_proc.columns else []

            sel_unidade = col_f1.multiselect("Filtrar por Unidade", opts_unidade)
            sel_area = col_f2.multiselect("Filtrar por Área", opts_area)
            sel_lider = col_f3.multiselect("Filtrar por Liderança", opts_lider)

        # --- APLICAÇÃO DOS FILTROS ---
        # Cria cópias para não alterar os dados originais das outras abas
        df_dash_ativos = df_ativos_proc.copy()
        df_dash_deslig = df_desligados_proc.copy()

        # Filtro Unidade
        if sel_unidade:
            df_dash_ativos = df_dash_ativos[df_dash_ativos["Unidade/Atuação"].isin(sel_unidade)]
            if "Unidade/Atuação" in df_dash_deslig.columns:
                df_dash_deslig = df_dash_deslig[df_dash_deslig["Unidade/Atuação"].isin(sel_unidade)]

        # Filtro Área
        if sel_area and "Área" in df_dash_ativos.columns:
            df_dash_ativos = df_dash_ativos[df_dash_ativos["Área"].isin(sel_area)]
            if "Área" in df_dash_deslig.columns:
                df_dash_deslig = df_dash_deslig[df_dash_deslig["Área"].isin(sel_area)]

        # Filtro Liderança
        if sel_lider and "Liderança direta" in df_dash_ativos.columns:
            df_dash_ativos = df_dash_ativos[df_dash_ativos["Liderança direta"].isin(sel_lider)]
            # Nota: Desligados podem não ter líder preenchido ou o líder mudou, mas aplicamos se existir
            if "Liderança direta" in df_dash_deslig.columns:
                df_dash_deslig = df_dash_deslig[df_dash_deslig["Liderança direta"].isin(sel_lider)]

        # --- LINHA 1: KPIs (Baseados nos dados FILTRADOS) ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
        
        col_k1.metric("Headcount (Filtro)", len(df_dash_ativos))
        
        # KPI: Admissões no Ano
        ano_atual = datetime.now().year
        if "Início na V4_dt" in df_dash_ativos.columns:
            df_adm_kpi = df_dash_ativos[df_dash_ativos["Início na V4_dt"].notna()]
            qtd_ano = len(df_adm_kpi[df_adm_kpi["Início na V4_dt"].dt.year == ano_atual])
            col_k2.metric(f"Entradas {ano_atual}", qtd_ano)
        else:
            col_k2.metric(f"Entradas {ano_atual}", 0)
        
        # KPI: Tempo Médio
        if "Início na V4_dt" in df_dash_ativos.columns:
            hj = pd.Timestamp.today().normalize()
            datas_inicio = df_dash_ativos[df_dash_ativos["Início na V4_dt"].notna()]["Início na V4_dt"]
            if not datas_inicio.empty:
                anos_medios = (hj - datas_inicio).dt.days.mean() / 365.25
                col_k3.metric("Tempo Médio (Anos)", f"{anos_medios:.1f}")
            else:
                col_k3.metric("Tempo Médio", "-")
        
        # KPI: Idade Média
        if "Data de nascimento_dt" in df_dash_ativos.columns:
            df_nasc = df_dash_ativos[df_dash_ativos["Data de nascimento_dt"].notna()]
            if not df_nasc.empty:
                media_idade = ((pd.Timestamp.today() - df_nasc["Data de nascimento_dt"]).dt.days / 365.25).mean()
                col_k4.metric("Idade Média", f"{media_idade:.1f}")
            else:
                col_k4.metric("Idade Média", "-")
        
        col_k5.metric("Desligados (Filtro)", len(df_dash_deslig))
        
        st.markdown("---")
        
        # --- LINHA 2: GRÁFICOS (UNIDADE E SENIORIDADE) ---
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📍 Por Unidade / Atuação")
            if "Unidade/Atuação" in df_dash_ativos.columns and not df_dash_ativos.empty:
                df_uni = df_dash_ativos["Unidade/Atuação"].fillna("Não Inf.").value_counts().reset_index()
                df_uni.columns = ["Unidade", "Qtd"]
                chart_uni = alt.Chart(df_uni).mark_bar(color="#E30613").encode(
                    x=alt.X("Unidade", sort="-y"), y="Qtd", tooltip=["Unidade", "Qtd"]
                )
                st.altair_chart(chart_uni, use_container_width=True)
            else:
                st.info("Sem dados para exibir com os filtros atuais.")
                
        with g2:
            st.subheader("🏆 Por Senioridade")
            if "Senioridade" in df_dash_ativos.columns and not df_dash_ativos.empty:
                df_sen = df_dash_ativos["Senioridade"].fillna("Não Informado").replace("", "Não Informado").value_counts().reset_index()
                df_sen.columns = ["Senioridade", "Qtd"]
                chart_sen = alt.Chart(df_sen).mark_bar(color="#404040").encode(
                    x=alt.X("Qtd", title="Qtd"), y=alt.Y("Senioridade", sort="-x"), tooltip=["Senioridade", "Qtd"]
                )
                st.altair_chart(chart_sen, use_container_width=True)
            else:
                st.info("Sem dados para exibir com os filtros atuais.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- LINHA 3: EVOLUÇÃO E LIDERANÇA ---
        g3, g4 = st.columns(2)
        
        with g3:
            st.subheader("📈 Evolução de Admissões")
            col_data = "Início na V4_dt"
            # Junta ativos e desligados (já filtrados) para o gráfico
            if col_data in df_dash_ativos.columns:
                series_ativos = df_dash_ativos[col_data]
                if col_data in df_dash_deslig.columns:
                    series_total = pd.concat([series_ativos, df_dash_deslig[col_data]])
                else:
                    series_total = series_ativos
                
                df_evo = pd.DataFrame({"Data": series_total}).dropna()
                
                if not df_evo.empty:
                    df_evo["Ano"] = df_evo["Data"].dt.year
                    df_evo_count = df_evo["Ano"].value_counts().reset_index()
                    df_evo_count.columns = ["Ano", "Investidores"]
                    chart_evo = alt.Chart(df_evo_count).mark_line(point=True, color="#000000").encode(
                        x=alt.X("Ano:O"), y="Investidores", tooltip=["Ano", "Investidores"]
                    )
                    st.altair_chart(chart_evo, use_container_width=True)
                else:
                    st.info("Sem dados históricos para os filtros selecionados.")

        with g4:
            st.subheader("👥 Span of Control (Top 10)")
            if "Liderança direta" in df_dash_ativos.columns and not df_dash_ativos.empty:
                df_lider = df_dash_ativos["Liderança direta"].replace("", pd.NA).dropna().value_counts().head(10).reset_index()
                df_lider.columns = ["Líder", "Liderados"]
                if not df_lider.empty:
                    chart_lider = alt.Chart(df_lider).mark_bar(color="#8B0000").encode(
                        x=alt.X("Liderados", title="Qtd"), y=alt.Y("Líder", sort="-x"), tooltip=["Líder", "Liderados"]
                    )
                    st.altair_chart(chart_lider, use_container_width=True)
                else:
                    st.info("Sem dados de liderança.")
            else:
                st.info("Sem dados para exibir.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- LINHA 4: ÁREA E MODELO ---
        g5, g6 = st.columns(2)

        with g5:
            st.subheader("🏢 Distribuição por Área")
            if "Área" in df_dash_ativos.columns and not df_dash_ativos.empty:
                df_area = df_dash_ativos["Área"].fillna("Não Inf.").value_counts().reset_index()
                df_area.columns = ["Área", "Qtd"]
                chart_area = alt.Chart(df_area).mark_bar(color="#E30613").encode(
                    x=alt.X("Qtd"), y=alt.Y("Área", sort="-x"), tooltip=["Área", "Qtd"]
                )
                st.altair_chart(chart_area, use_container_width=True)

        with g6:
            st.subheader("📃 Modelo de Contrato")
            if "Modelo de contrato" in df_dash_ativos.columns and not df_dash_ativos.empty:
                df_mod = df_dash_ativos["Modelo de contrato"].fillna("Outros").value_counts().reset_index()
                df_mod.columns = ["Modelo", "Qtd"]
                chart_mod = alt.Chart(df_mod).mark_arc(innerRadius=60).encode(
                    theta="Qtd", 
                    color=alt.Color("Modelo", scale=alt.Scale(range=CORES_V4)), 
                    tooltip=["Modelo", "Qtd"]
                )
                st.altair_chart(chart_mod, use_container_width=True)
                
    # ----------------------------------------------------
    # ABA ROLLING (TÍTULOS PADRONIZADOS)
    # ----------------------------------------------------
    with aba_rolling:
        # Texto Explicativo
        st.markdown("""
            <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
                <span style="color: #404040; font-size: 14px;">
                    Utilize os controles abaixo para alternar entre a base de <b>Ativos</b> e <b>Desligados</b>.
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        # --- SELETOR DE VISUALIZAÇÃO ---
        modo_visualizacao = st.radio(
            "Selecione a base:",
            ["Investidores Ativos", "Investidores Desligados"], 
            horizontal=True,
            label_visibility="collapsed" 
        )
        
        st.markdown("---")

        # Configuração de colunas para esconder
        def get_column_config(df_cols):
            config = {}
            cols_to_hide = [
                "Foto", "Nome completo com acentos", "Solicitar documentação", "Enviar no EB", "Situação no plano", 
                "Carteirinha médico", "Operadora Médico", "Carteirinha odonto", 
                "Operadora Odonto", "Link Drive Docs", "FotoView", 
                "Início na V4_dt", "Data de nascimento_dt", "Data do contrato_dt", 
                "Térm previsto_dt", "Data de rescisão_dt"
            ]
            for col in df_cols:
                if col in cols_to_hide:
                    config[col] = None
            return config

        # --- LÓGICA DINÂMICA ---
        if modo_visualizacao == "Investidores Ativos":
            df_atual = df_ativos_proc
            tipo_base = "ativo"
            key_suffix = "_ativo"
            cor_titulo = "green"
        else:
            df_atual = df_desligados_proc
            tipo_base = "desligado"
            key_suffix = "_deslig"
            cor_titulo = "red"

        # Pega a última palavra (Ativos/Desligados) para usar no título
        texto_base = modo_visualizacao.split(' ')[-1]

        # --- TÍTULO DA CONSULTA (PADRONIZADO) ---
        st.markdown(f"### 🔍 Consultar Investidor :{cor_titulo}[{texto_base}]")

        # --- ÁREA DE SELEÇÃO ---
        c_sel, c_btn = st.columns([3, 1])
        
        with c_sel:
            # Selectbox sem rótulo visível (o título H3 acima faz esse papel)
            sel_investidor = st.selectbox(
                "label_oculto", 
                [""] + sorted(df_atual["Nome"].unique()), 
                key=f"sel_rol{key_suffix}",
                label_visibility="collapsed"
            )
        
        with c_btn:
            # Como tiramos o label do selectbox, o botão alinha naturalmente sem espaçador extra
            if st.button("🔍 Ver Detalhes", key=f"btn_rol{key_suffix}") and sel_investidor:
                modal_consulta_investidor(df_atual, sel_investidor, tipo_base)
        
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("---")
        
        # --- TÍTULO DA TABELA (PADRONIZADO) ---
        st.markdown(f"### 📋 Base Completa :{cor_titulo}[{texto_base}]")
        
        busca = st.text_input(f"Filtrar tabela", placeholder="Digite nome, cargo ou área...", key=f"busca{key_suffix}")
        
        df_view = df_atual.copy()
        if busca:
            df_view = df_view[df_view.astype(str).apply(lambda x: x.str.contains(busca, case=False).any(), axis=1)]
        
        st.dataframe(df_view, use_container_width=True, hide_index=True, column_config=get_column_config(df_view.columns))
        
    # ----------------------------------------------------
    # ABA ANALYTICS (AJUSTADO E REFINADO)
    # ----------------------------------------------------
    with aba_analytics:
        # Texto Explicativo
        st.markdown("""
            <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
                <span style="color: #404040; font-size: 14px;">
                    Consulte <b>relatórios operacionais</b> detalhados e utilize a Central de Ações para <b>gerar documentos</b> automaticamente.
                </span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        col_relatorios, col_divisor, col_acoes = st.columns([7, 0.1, 3])
        with col_divisor:
            st.markdown("""<div style="height: 100%; border-left: 1px solid #e0e0e0; margin: 0 auto;"></div>""", unsafe_allow_html=True)
            
        with col_relatorios:
            st.markdown("## 📊 Relatórios Principais")
            
            # ==========================================
            # 1. ANIVERSARIANTES DO MÊS
            # ==========================================
            with st.expander("🎉 Aniversariantes do mês", expanded=False):
                meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_atual = datetime.today().month
                mes_selecionado = st.selectbox("Mês", options=list(meses.keys()), format_func=lambda x: meses[x], index=mes_atual - 1)
                
                if "Data de nascimento_dt" in df_ativos_proc.columns:
                    df_aniversario = df_ativos_proc[df_ativos_proc["Data de nascimento_dt"].dt.month == mes_selecionado].copy()
                    
                    if df_aniversario.empty:
                        st.info("Nenhum aniversariante neste mês 🎈")
                    else:
                        # Ordena pelo dia
                        df_aniversario["Dia_Sort"] = df_aniversario["Data de nascimento_dt"].dt.day
                        df_aniversario = df_aniversario.sort_values("Dia_Sort")
                        
                        # Calcula a idade que a pessoa faz NESTE ano
                        ano_atual = datetime.today().year
                        df_aniversario["Idade"] = (ano_atual - df_aniversario["Data de nascimento_dt"].dt.year).astype(str) + " anos"
                        
                        # Colunas solicitadas: Nome, Email, Área, Data Nascimento, Idade
                        cols_niver = ["Nome", "E-mail corporativo", "Área", "Data de nascimento", "Idade"]
                        cols_final = [c for c in cols_niver if c in df_aniversario.columns]
                        
                        st.dataframe(df_aniversario[cols_final], use_container_width=True, hide_index=True)
                else:
                    st.warning("Coluna de Data de Nascimento não encontrada.")

            # ==========================================
            # 2. CONTRATOS A VENCER
            # ==========================================
            with st.expander("⏰ Contratos a vencer", expanded=False):
                c1, c2 = st.columns(2)
                d_ini = c1.date_input("Data inicial", value=datetime.today().date(), format="DD/MM/YYYY")
                d_fim = c2.date_input("Data final", value=datetime.today().date() + relativedelta(months=3), format="DD/MM/YYYY")
                
                if "Térm previsto_dt" in df_ativos_proc.columns:
                    ini_ts = pd.Timestamp(d_ini)
                    fim_ts = pd.Timestamp(d_fim)
                    
                    df_venc = df_ativos_proc[
                        (df_ativos_proc["Térm previsto_dt"].notna()) & 
                        (df_ativos_proc["Térm previsto_dt"] >= ini_ts) & 
                        (df_ativos_proc["Térm previsto_dt"] <= fim_ts)
                    ].sort_values("Térm previsto_dt")
                    
                    if df_venc.empty:
                        st.info("Nenhum contrato vencendo no período selecionado ⏳")
                    else:
                        # Colunas solicitadas: Nome, Cargo, Modelo, Término, Email, Liderança
                        cols_venc = ["Nome", "Cargo", "Modelo de contrato", "Térm previsto", "E-mail corporativo", "Liderança direta"]
                        cols_final = [c for c in cols_venc if c in df_venc.columns]
                        st.dataframe(df_venc[cols_final], use_container_width=True, hide_index=True)
                else:
                    st.warning("Coluna de Término Previsto não encontrada.")

            # ==========================================
            # 3. INVESTIDORES MEI
            # ==========================================
            with st.expander("💼 Investidores MEI", expanded=False):
                if "Modalidade PJ" in df_ativos_proc.columns:
                    df_mei = df_ativos_proc[df_ativos_proc["Modalidade PJ"].astype(str).str.upper().str.contains("MEI", na=False)]
                    if df_mei.empty:
                        st.info("Nenhum investidor MEI encontrado.")
                    else:
                        st.warning(f"⚠️ Temos **{len(df_mei)} investidores MEI**.")
                        # Colunas solicitadas: Nome, Email, Cargo, Modalidade
                        cols_mei = ["Nome", "E-mail corporativo", "Cargo", "Modalidade PJ"]
                        cols_final = [c for c in cols_mei if c in df_mei.columns]
                        st.dataframe(df_mei[cols_final], use_container_width=True, hide_index=True)
                else:
                    st.warning("Coluna Modalidade PJ não encontrada.")

            # ==========================================
            # 4. TEMPO DE CASA (CÁLCULO EXATO DE CALENDÁRIO)
            # ==========================================
            with st.expander("⏳ Tempo de Casa", expanded=False):
                if "Início na V4_dt" in df_ativos_proc.columns:
                    st.markdown("**Configurações do Relatório:**")
                    
                    c_ano, c_mes, c_ref = st.columns([1, 1, 1.5])
                    min_anos = c_ano.number_input("Mín. Anos", min_value=0, value=1, step=1)
                    min_meses = c_mes.number_input("Mín. Meses", min_value=0, max_value=11, value=0, step=1)
                    
                    # Data de Referência formatada BR
                    data_ref_input = c_ref.date_input("Data de Referência", value=datetime.today(), format="DD/MM/YYYY")
                    data_ref = pd.Timestamp(data_ref_input).normalize()
                    
                    # --- LÓGICA CORRIGIDA (DATA DE CORTE) ---
                    # Em vez de contar dias, calculamos a data limite exata no passado.
                    # Quem entrou DEPOIS dessa data, não entra no filtro.
                    data_limite = data_ref - relativedelta(years=min_anos, months=min_meses)
                    
                    # Pega apenas quem tem data de início preenchida
                    df_tempo = df_ativos_proc[df_ativos_proc["Início na V4_dt"].notna()].copy()
                    
                    # Filtra quem entrou ANTES ou NO DIA da data limite
                    df_filtrado = df_tempo[
                        (df_tempo["Início na V4_dt"] <= data_limite)
                    ].copy()
                    
                    # Ordena pelos mais antigos
                    df_filtrado = df_filtrado.sort_values("Início na V4_dt", ascending=True)
                    
                    if df_filtrado.empty:
                        st.info(f"Ninguém com mais de {min_anos} anos e {min_meses} meses completos até {data_ref.strftime('%d/%m/%Y')}.")
                    else:
                        # Função para texto dinâmico
                        def texto_tempo_dinamico(inicio):
                            if pd.isna(inicio) or inicio > data_ref: return "-"
                            d = relativedelta(data_ref, inicio)
                            return f"{d.years} anos, {d.months} meses e {d.days} dias"

                        df_filtrado["Tempo de Casa"] = df_filtrado["Início na V4_dt"].apply(texto_tempo_dinamico)
                        
                        cols_tempo = ["Nome", "Remuneração", "Início na V4", "Tempo de Casa"]
                        cols_final = [c for c in cols_tempo if c in df_filtrado.columns]
                        
                        st.markdown(f"Em **{data_ref.strftime('%d/%m/%Y')}**, temos **{len(df_filtrado)} investidores** com esse tempo mínimo:")
                        st.dataframe(df_filtrado[cols_final], use_container_width=True, hide_index=True)
                else:
                    st.warning("Coluna Início na V4 não encontrada.")

        with col_acoes:
            st.markdown("## ⚙️ Ações")
            if st.button("📝 Título de doc para automação", use_container_width=True):
                modal_titulo_doc(df_ativos_proc)

            if st.button("📄 Demissão por comum acordo", use_container_width=True):
                modal_comum(df_ativos_proc)

            if st.button("📄 Aviso Prévio Indenizado", use_container_width=True):
                modal_aviso_previo_indenizado(df_ativos_proc)

            if st.button("🚌 Atualização do Vale Transporte", use_container_width=True):
                modal_vale_transporte(df_ativos_proc)
