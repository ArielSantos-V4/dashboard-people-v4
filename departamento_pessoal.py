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
# Vermelho V4, Vermelho Escuro, Vermelho Claro, Cinza Escuro, Cinza Claro
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

# ==========================================
# LÓGICA DE ALERTAS (ATIVOS)
# ==========================================
def gerar_alertas_investidor(linha):
    alertas = []
    hoje = pd.Timestamp.today().normalize()
    status = str(linha.get("Situação no plano", "")).strip()

    # Docs Plano
    data_solicitar = pd.to_datetime(linha.get("Solicitar documentação"), errors="coerce")
    if status == "Pendente" and pd.notna(data_solicitar):
        dias = (data_solicitar - hoje).days
        if dias < 0: alertas.append(("error", "Docs Plano: Atrasado!"))
        elif dias <= 15: alertas.append(("info", f"Docs Plano: Faltam {dias} dias"))

    # Envio EB
    data_enviar_eb = pd.to_datetime(linha.get("Enviar no EB"), errors="coerce")
    if status == "Aguardando docs" and pd.notna(data_enviar_eb):
        dias = (data_enviar_eb - hoje).days
        if dias < 0: alertas.append(("error", "Envio EB: Atrasado!"))
        elif dias <= 15: alertas.append(("info", f"Envio EB: Faltam {dias} dias"))

    # Aniversário
    nascimento = pd.to_datetime(linha.get("Data de nascimento"), errors="coerce", dayfirst=True)
    if pd.notna(nascimento):
        nascimento = pd.Timestamp(nascimento).normalize()
        if nascimento.month == hoje.month:
            if nascimento.day == hoje.day:
                alertas.append(("success", "Feliz Aniversário! Hoje! 🎂"))
            else:
                alertas.append(("info", f"Aniversariante do mês (Dia {nascimento.day}) 🎉"))

    # Contrato
    fim_contrato = pd.to_datetime(linha.get("Térm previsto"), errors="coerce", dayfirst=True)
    if pd.notna(fim_contrato):
        fim_contrato = pd.Timestamp(fim_contrato).normalize()
        dias = (fim_contrato - hoje).days
        if dias < 0: alertas.append(("error", "Contrato Vencido! 🚨"))
        elif dias <= 30: alertas.append(("warning", f"Contrato vence em {dias} dias"))

    if linha.get("Modalidade PJ", "") == "MEI":
        alertas.append(("warning", "Investidor MEI ⚠️"))

    return alertas

# ==========================================
# MODAL DE CONSULTA (HÍBRIDO)
# ==========================================
@st.dialog(" ")
def modal_consulta_investidor(df_consulta, nome, tipo_base="ativo"):
    st.markdown('<div class="modal-investidor">', unsafe_allow_html=True)
    
    # Filtra e pega a primeira linha
    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]
            
    col1, col2, col3 = st.columns([3, 3, 2])
        
    # --- COLUNA 1: DADOS CONTRATUAIS ---
    with col1:
        st.markdown("##### 📌 Profissional")
        
        col_a, col_b = st.columns(2)
        col_a.text_input("BP", str(linha.get("BP", "")).replace(".0", ""), disabled=True)
        col_b.text_input("Matrícula", str(linha.get("Matrícula", "")).replace(".0", "").zfill(6), disabled=True)
        
        c1, c2 = st.columns(2)
        c1.text_input("Data Contrato", linha.get("Data do contrato", ""), disabled=True)
        c2.text_input("Modelo", linha.get("Modelo de contrato", ""), disabled=True)
        
        # Diferenciação para Desligados
        if tipo_base == "desligado":
            st.markdown("🔴 **Desligamento**")
            d1, d2 = st.columns(2)
            d1.text_input("Data Rescisão", linha.get("Data de rescisão", ""), disabled=True)
            d2.text_input("Valor Distrato", linha.get("Valor distrato", ""), disabled=True)
            st.text_input("Término Previsto (Orig)", linha.get("Térm previsto", ""), disabled=True)
        else:
            st.text_input("Término Previsto", linha.get("Térm previsto", ""), disabled=True)
        
        tempo = calcular_tempo_casa(linha.get("Início na V4_dt"))
        st.text_input("Início na V4", linha.get("Início na V4", ""), disabled=True)
        if tipo_base == "ativo":
            st.caption(f"Tempo de casa: {tempo}")

        st.text_input("E-mail Corp", linha.get("E-mail corporativo", ""), disabled=True)
        
        e1, e2 = st.columns(2)
        e1.text_input("CNPJ", formatar_cnpj(linha.get("CNPJ")), disabled=True)
        e2.text_input("Razão Social", linha.get("Razão social", ""), disabled=True)
        
        st.text_input("Cargo", linha.get("Cargo", ""), disabled=True)

    # --- COLUNA 2: PESSOAL / ADMIN ---
    with col2:
        st.markdown("##### 👤 Pessoal / Admin")
        
        cc_code = str(linha.get("Código CC", "")).replace(".0", "")
        f1, f2 = st.columns([1, 2])
        f1.text_input("Cód CC", cc_code, disabled=True)
        f2.text_input("Centro de Custo", linha.get("Descrição CC", ""), disabled=True)
        
        st.text_input("Liderança", linha.get("Liderança direta", ""), disabled=True)
        st.text_input("Conta Contábil", linha.get("Conta contábil", ""), disabled=True)

        g1, g2 = st.columns(2)
        g1.text_input("CPF", formatar_cpf(linha.get("CPF")), disabled=True)
        g2.text_input("Nascimento", linha.get("Data de nascimento", ""), disabled=True)
        
        st.text_input("E-mail Pessoal", linha.get("E-mail pessoal", ""), disabled=True)
        st.text_input("Telefone", linha.get("Telefone pessoal", ""), disabled=True)
        
        if linha.get("Link Drive Docs"):
            st.link_button("📂 Abrir Drive Docs", linha["Link Drive Docs"], use_container_width=True)

    # --- COLUNA 3: FOTO / BENEFÍCIOS ---
    with col3:
        st.markdown("##### 🖼️ Foto")
        foto = linha.get("Foto", "")
        if foto and str(foto).startswith("http"):
            st.markdown(f'<div style="display:flex; justify-content:center; margin-bottom:20px"><img src="{foto}" width="150" style="border-radius:10px"></div>', unsafe_allow_html=True)
        else:
            st.info("Sem foto disponível")

        st.markdown("##### 🎁 Benefícios")
        st.text_input("Status Plano", linha.get("Situação no plano", ""), disabled=True)
        
        st.markdown("**Saúde**")
        h1, h2 = st.columns(2)
        h1.text_input("Operadora", linha.get("Operadora Médico", ""), disabled=True, label_visibility="collapsed")
        h2.text_input("Cart.", str(linha.get("Carteirinha médico", "")).replace(".0",""), disabled=True, label_visibility="collapsed")

        st.markdown("**Odonto**")
        i1, i2 = st.columns(2)
        i1.text_input("Operadora", linha.get("Operadora Odonto", ""), disabled=True, label_visibility="collapsed")
        i2.text_input("Cart.", str(linha.get("Carteirinha odonto", "")).replace(".0",""), disabled=True, label_visibility="collapsed")
        
        # Alertas só aparecem para ativos
        if tipo_base == "ativo":
            st.markdown("---")
            st.markdown("##### ⚠️ Alertas")
            alertas = gerar_alertas_investidor(linha)
            if alertas:
                with st.container(height=120, border=True):
                    for tipo, msg in alertas:
                        if tipo == "error": st.error(msg, icon="🚨")
                        elif tipo == "warning": st.warning(msg, icon="⚠️")
                        elif tipo == "success": st.success(msg, icon="🎉")
                        else: st.info(msg, icon="ℹ️")

    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# MODAIS DE AÇÃO (MANTIDOS)
# ==========================================
@st.dialog("📝 Título Doc Automação")
def modal_titulo_doc(df):
    st.info("Gera o nome do arquivo padronizado para salvar no Drive.")
    nome = st.selectbox("Investidor", sorted(df["Nome"].unique()))
    titulo = st.text_input("Nome do Documento (ex: Contrato PJ)")
    if st.button("Gerar Código"):
        if nome and titulo:
            row = df[df["Nome"]==nome].iloc[0]
            cpf = re.sub(r"\D", "", str(row.get("CPF",""))).zfill(11)
            email = str(row.get("E-mail pessoal","")).lower()
            st.code(f"{nome} __ {cpf} __ {email} __ {titulo}")

@st.dialog("📄 Demissão Comum Acordo")
def modal_comum(df):
    nome = st.selectbox("Colaborador", sorted(df["Nome"].unique()))
    data = st.date_input("Data Desligamento")
    if st.button("Gerar DOC"):
        st.success("Simulação: Documento gerado!") 

@st.dialog("📄 Aviso Prévio Indenizado")
def modal_aviso_previo_indenizado(df):
    nome = st.selectbox("Colaborador", sorted(df["Nome"].unique()))
    data_des = st.date_input("Data Desligamento")
    data_hom = st.date_input("Data Homologação")
    if st.button("Gerar DOC"):
        st.success("Simulação: Documento gerado!")

@st.dialog("🚌 Vale Transporte")
def modal_vale_transporte(df):
    nome = st.selectbox("Colaborador", sorted(df["Nome"].unique()))
    st.info("Preencha os dados de transporte (Ônibus/Metrô)...")
    if st.button("Gerar Declaração"):
        st.success("Simulação: Declaração gerada!")


# ==========================================
# RENDER PRINCIPAL
# ==========================================
def render(df_ativos, df_desligados):
    
    # 🔒 Segurança
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("Faça login na tela inicial.")
        st.stop()
        
    # CABEÇALHO
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
                # Atualiza a string para visualização bonita (DD/MM/YYYY)
                df[col] = df[f"{col}_dt"].dt.strftime("%d/%m/%Y").fillna("")
        return df

    df_ativos_proc = preparar_dataframe(df_ativos)
    df_desligados_proc = preparar_dataframe(df_desligados)

    # ----------------------------------------------------
    # ABA DASHBOARD
    # ----------------------------------------------------
    with aba_dashboard:
        # Usa apenas ATIVOS para os KPIs
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        col_k1.metric("Headcount Ativo", len(df_ativos_proc))
        
        # Contratos vencendo em 30 dias
        hoje = pd.Timestamp.today().normalize()
        venc_prox = df_ativos_proc[
            (df_ativos_proc["Térm previsto_dt"].notna()) & 
            (df_ativos_proc["Térm previsto_dt"] > hoje) &
            (df_ativos_proc["Térm previsto_dt"] <= hoje + timedelta(days=30))
        ]
        col_k2.metric("Contratos Vencendo (30d)", len(venc_prox), help="Contratos que vencem nos próximos 30 dias")
        
        # Média de idade
        if "Data de nascimento_dt" in df_ativos_proc.columns:
            idades = (hoje - df_ativos_proc["Data de nascimento_dt"]).dt.days / 365.25
            media_idade = idades.mean()
            col_k3.metric("Média de Idade", f"{media_idade:.1f} anos")
        
        # Total Desligados (Histórico)
        col_k4.metric("Total Desligados", len(df_desligados_proc))
        
        st.markdown("---")
        
        # Gráficos (COM CORES V4)
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📍 Por Unidade / Atuação")
            if "Unidade/Atuação" in df_ativos_proc.columns:
                df_uni = df_ativos_proc["Unidade/Atuação"].value_counts().reset_index()
                df_uni.columns = ["Unidade", "Qtd"]
                # COR ALTERADA AQUI:
                chart_uni = alt.Chart(df_uni).mark_bar(color="#E30613").encode(
                    x=alt.X("Unidade", sort="-y"), y="Qtd", tooltip=["Unidade", "Qtd"]
                )
                st.altair_chart(chart_uni, use_container_width=True)
                
        with g2:
            st.subheader("📃 Modelo de Contrato")
            if "Modelo de contrato" in df_ativos_proc.columns:
                df_mod = df_ativos_proc["Modelo de contrato"].value_counts().reset_index()
                df_mod.columns = ["Modelo", "Qtd"]
                # CORES ALTERADAS AQUI (RANGE V4):
                chart_mod = alt.Chart(df_mod).mark_arc(innerRadius=60).encode(
                    theta="Qtd", 
                    color=alt.Color("Modelo", scale=alt.Scale(range=CORES_V4)), 
                    tooltip=["Modelo", "Qtd"]
                )
                st.altair_chart(chart_mod, use_container_width=True)

    # ----------------------------------------------------
    # ABA ROLLING (TABELAS COMPLETAS COM COLUNAS OCULTAS)
    # ----------------------------------------------------
    with aba_rolling:
        tab_ativos, tab_desligados = st.tabs(["🟢 Base Ativa", "🔴 Base Desligados"])
        
        # Função para configurar as colunas ocultas
        def get_column_config(df_cols):
            config = {}
            # Lista de colunas para ocultar (mas deixar disponível)
            cols_to_hide = [
                "Foto", "Solicitar documentação", "Enviar no EB", "Situação no plano", 
                "Carteirinha médico", "Operadora Médico", "Carteirinha odonto", 
                "Operadora Odonto", "Link Drive Docs", "FotoView", 
                "Início na V4_dt", "Data de nascimento_dt", "Data do contrato_dt", 
                "Térm previsto_dt", "Data de rescisão_dt"
            ]
            for col in df_cols:
                if col in cols_to_hide:
                    config[col] = st.column_config.TextColumn(hidden=True)
            return config

        # --- ATIVOS ---
        with tab_ativos:
            st.markdown("<br>", unsafe_allow_html=True)
            c_sel, c_btn = st.columns([3, 1])
            sel_ativo = c_sel.selectbox("Consultar Investidor Ativo", [""] + sorted(df_ativos_proc["Nome"].unique()), key="sel_rol_ativo")
            if c_btn.button("🔍 Ver Detalhes", key="btn_rol_ativo") and sel_ativo:
                modal_consulta_investidor(df_ativos_proc, sel_ativo, "ativo")
            
            st.markdown("---")
            st.markdown("### 📋 Base de investidores (Ativos)")
            
            # Filtro
            busca_a = st.text_input("Filtrar tabela ativa", placeholder="Digite para buscar...", key="busca_a")
            df_view_a = df_ativos_proc.copy()
            if busca_a:
                df_view_a = df_view_a[df_view_a.astype(str).apply(lambda x: x.str.contains(busca_a, case=False).any(), axis=1)]
            
            # EXIBIR TODAS AS COLUNAS (com configuração de ocultar)
            st.dataframe(
                df_view_a, 
                use_container_width=True, 
                hide_index=True,
                column_config=get_column_config(df_view_a.columns)
            )

        # --- DESLIGADOS ---
        with tab_desligados:
            st.markdown("<br>", unsafe_allow_html=True)
            c_sel_d, c_btn_d = st.columns([3, 1])
            sel_deslig = c_sel_d.selectbox("Consultar Investidor Desligado", [""] + sorted(df_desligados_proc["Nome"].unique()), key="sel_rol_deslig")
            if c_btn_d.button("🔍 Ver Detalhes", key="btn_rol_deslig") and sel_deslig:
                modal_consulta_investidor(df_desligados_proc, sel_deslig, "desligado")
            
            st.markdown("---")
            st.markdown("### 📋 Base de investidores (Desligados)")
            
            busca_d = st.text_input("Filtrar tabela desligados", placeholder="Digite para buscar...", key="busca_d")
            df_view_d = df_desligados_proc.copy()
            if busca_d:
                df_view_d = df_view_d[df_view_d.astype(str).apply(lambda x: x.str.contains(busca_d, case=False).any(), axis=1)]
            
            # EXIBIR TODAS AS COLUNAS (com configuração de ocultar)
            st.dataframe(
                df_view_d, 
                use_container_width=True, 
                hide_index=True,
                column_config=get_column_config(df_view_d.columns)
            )

    # ----------------------------------------------------
    # ABA ANALYTICS / AÇÕES (Mantido)
    # ----------------------------------------------------
    with aba_analytics:
        st.markdown("<br>", unsafe_allow_html=True)
        col_rel, _, col_act = st.columns([2, 0.1, 1])
        
        with col_rel:
            st.subheader("📊 Relatórios Rápidos")
            with st.expander("🎉 Aniversariantes do Mês"):
                mes_atual = datetime.now().month
                anis = df_ativos_proc[df_ativos_proc["Data de nascimento_dt"].dt.month == mes_atual].copy()
                if not anis.empty:
                    anis["Dia"] = anis["Data de nascimento_dt"].dt.day
                    st.dataframe(anis[["Dia", "Nome", "Área"]].sort_values("Dia"), hide_index=True)
                else:
                    st.info("Ninguém faz aniversário este mês.")

        with col_act:
            st.subheader("⚙️ Ações (Docs)")
            if st.button("📝 Título Doc Padrão", use_container_width=True):
                modal_titulo_doc(df_ativos_proc)
            if st.button("📄 Demissão Comum Acordo", use_container_width=True):
                modal_comum(df_ativos_proc)
            if st.button("📄 Aviso Prévio Indenizado", use_container_width=True):
                modal_aviso_previo_indenizado(df_ativos_proc)
            if st.button("🚌 Vale Transporte", use_container_width=True):
                modal_vale_transporte(df_ativos_proc)
