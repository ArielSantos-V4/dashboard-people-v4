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
# MODAL DE CONSULTA (HÍBRIDO - LARGO)
# ==========================================
@st.dialog(" ", width="large")
def modal_consulta_investidor(df_consulta, nome, tipo_base="ativo"):
    st.markdown('<div class="modal-investidor">', unsafe_allow_html=True)
    
    linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]
            
    col1, col2, col3 = st.columns([3, 3, 2])
        
    # --- COLUNA 1 ---
    with col1:
        st.markdown("##### 📌 Profissional")
        col_a, col_b = st.columns(2)
        col_a.text_input("BP", str(linha.get("BP", "")).replace(".0", ""), disabled=True)
        col_b.text_input("Matrícula", str(linha.get("Matrícula", "")).replace(".0", "").zfill(6), disabled=True)
        
        c1, c2 = st.columns(2)
        c1.text_input("Data Contrato", linha.get("Data do contrato", ""), disabled=True)
        c2.text_input("Modelo", linha.get("Modelo de contrato", ""), disabled=True)
        
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

    # --- COLUNA 2 ---
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

    # --- COLUNA 3 ---
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
        # ADICIONADO key= PARA CORRIGIR ERRO DE DUPLICIDADE
        h1.text_input("Operadora", linha.get("Operadora Médico", ""), disabled=True, label_visibility="collapsed", key="op_medico")
        h2.text_input("Cart.", str(linha.get("Carteirinha médico", "")).replace(".0",""), disabled=True, label_visibility="collapsed", key="cart_medico")

        st.markdown("**Odonto**")
        i1, i2 = st.columns(2)
        # ADICIONADO key= PARA CORRIGIR ERRO DE DUPLICIDADE
        i1.text_input("Operadora", linha.get("Operadora Odonto", ""), disabled=True, label_visibility="collapsed", key="op_odonto")
        i2.text_input("Cart.", str(linha.get("Carteirinha odonto", "")).replace(".0",""), disabled=True, label_visibility="collapsed", key="cart_odonto")
        
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
# MODAIS DE AÇÃO
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
    nome = st.selectbox("Investidor", sorted(df["Nome"].unique()))
    data = st.date_input("Data Desligamento")
    if st.button("Gerar DOC"):
        st.success("Simulação: Documento gerado!") 

@st.dialog("📄 Aviso Prévio Indenizado")
def modal_aviso_previo_indenizado(df):
    nome = st.selectbox("Investidor", sorted(df["Nome"].unique()))
    data_des = st.date_input("Data Desligamento")
    data_hom = st.date_input("Data Homologação")
    if st.button("Gerar DOC"):
        st.success("Simulação: Documento gerado!")

@st.dialog("🚌 Vale Transporte")
def modal_vale_transporte(df):
    nome = st.selectbox("Investidor", sorted(df["Nome"].unique()))
    st.info("Preencha os dados de transporte (Ônibus/Metrô)...")
    if st.button("Gerar Declaração"):
        st.success("Simulação: Declaração gerada!")


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
    # ABA ROLLING
    # ----------------------------------------------------
    with aba_rolling:
        # Texto Explicativo (NOVO)
        st.markdown("""
            <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
                <span style="color: #404040; font-size: 14px;">
                    Utilize esta área para <b>consultas individuais detalhadas</b> ou para visualizar a <b>tabela completa</b> de todos os investidores, incluindo ativos e desligados.
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        tab_ativos, tab_desligados = st.tabs(["🟢 Base Ativa", "🔴 Base Desligados"])
        
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

        # ATIVOS
        with tab_ativos:
            st.markdown("<br>", unsafe_allow_html=True)
            c_sel, c_btn = st.columns([3, 1])
            sel_ativo = c_sel.selectbox("Consultar Investidor Ativo", [""] + sorted(df_ativos_proc["Nome"].unique()), key="sel_rol_ativo")
            if c_btn.button("🔍 Ver Detalhes", key="btn_rol_ativo") and sel_ativo:
                modal_consulta_investidor(df_ativos_proc, sel_ativo, "ativo")
            
            st.markdown("---")
            st.markdown("### 📋 Base de investidores (Ativos)")
            busca_a = st.text_input("Filtrar tabela ativa", placeholder="Digite para buscar...", key="busca_a")
            df_view_a = df_ativos_proc.copy()
            if busca_a:
                df_view_a = df_view_a[df_view_a.astype(str).apply(lambda x: x.str.contains(busca_a, case=False).any(), axis=1)]
            
            st.dataframe(df_view_a, use_container_width=True, hide_index=True, column_config=get_column_config(df_view_a.columns))

        # DESLIGADOS
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
            
            st.dataframe(df_view_d, use_container_width=True, hide_index=True, column_config=get_column_config(df_view_d.columns))

    # ----------------------------------------------------
    # ABA ANALYTICS (RESTAURADO)
    # ----------------------------------------------------
    with aba_analytics:
        # Texto Explicativo (NOVO)
        st.markdown("""
            <div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid #E30613; border-radius: 4px; margin-bottom: 20px;">
                <span style="color: #404040; font-size: 14px;">
                    Consulte <b>relatórios operacionais</b> (Aniversariantes, Vencimentos, MEI) e utilize a Central de Ações para <b>gerar documentos</b> automaticamente.
                </span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        col_relatorios, col_divisor, col_acoes = st.columns([7, 0.1, 3])
        with col_divisor:
            st.markdown("""<div style="height: 100%; border-left: 1px solid #e0e0e0; margin: 0 auto;"></div>""", unsafe_allow_html=True)
            
        with col_relatorios:
            st.markdown("## 📊 Relatórios Principais")
            
            # 1. Aniversariantes
            with st.expander("🎉 Aniversariantes do mês", expanded=False):
                meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_atual = datetime.today().month
                mes_selecionado = st.selectbox("Mês", options=list(meses.keys()), format_func=lambda x: meses[x], index=mes_atual - 1)
                
                df_aniversario = df_ativos_proc[df_ativos_proc["Data de nascimento_dt"].dt.month == mes_selecionado].copy()
                if df_aniversario.empty:
                    st.info("Nenhum aniversariante neste mês 🎈")
                else:
                    df_aniversario["Dia"] = df_aniversario["Data de nascimento_dt"].dt.day
                    df_final = df_aniversario[["Dia", "Nome", "Área", "E-mail corporativo"]].sort_values("Dia").reset_index(drop=True)
                    st.dataframe(df_final, use_container_width=True, hide_index=True)

            # 2. Contratos a vencer
            with st.expander("⏰ Contratos a vencer", expanded=False):
                c1, c2 = st.columns(2)
                d_ini = c1.date_input("Data inicial", value=datetime.today().date(), format="DD/MM/YYYY")
                d_fim = c2.date_input("Data final", value=datetime.today().date() + relativedelta(months=3), format="DD/MM/YYYY")
                
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
                    st.dataframe(df_venc[["Nome", "Térm previsto", "Modelo de contrato", "Liderança direta"]], use_container_width=True, hide_index=True)

            # 3. MEI
            with st.expander("💼 Investidores MEI", expanded=False):
                if "Modalidade PJ" in df_ativos_proc.columns:
                    df_mei = df_ativos_proc[df_ativos_proc["Modalidade PJ"].astype(str).str.upper().str.contains("MEI", na=False)]
                    if df_mei.empty:
                        st.info("Nenhum investidor MEI encontrado.")
                    else:
                        st.warning(f"⚠️ Temos **{len(df_mei)} investidores MEI**.")
                        st.dataframe(df_mei[["Nome", "Modalidade PJ", "Início na V4"]], use_container_width=True, hide_index=True)

            # 4. Tempo de Casa
            with st.expander("⏳ Tempo de Casa", expanded=False):
                if "Início na V4_dt" in df_ativos_proc.columns:
                    min_anos = st.selectbox("Tempo mínimo de casa (anos)", [1, 2, 3, 4, 5, 10], index=0)
                    hj = pd.Timestamp.today().normalize()
                    
                    df_tempo = df_ativos_proc[df_ativos_proc["Início na V4_dt"].notna()].copy()
                    df_tempo["Anos"] = (hj - df_tempo["Início na V4_dt"]).dt.days / 365.25
                    
                    df_filtrado = df_tempo[df_tempo["Anos"] >= min_anos].sort_values("Anos", ascending=False)
                    
                    if df_filtrado.empty:
                        st.info(f"Ninguém com mais de {min_anos} anos de casa ainda.")
                    else:
                        df_filtrado["Tempo"] = df_filtrado["Início na V4_dt"].apply(calcular_tempo_casa)
                        st.dataframe(df_filtrado[["Nome", "Início na V4", "Tempo"]], use_container_width=True, hide_index=True)

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
