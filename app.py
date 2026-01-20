import streamlit as st
import pandas as pd
import bcrypt
import altair as alt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

if "investidor_selecionado" not in st.session_state:
    st.session_state.investidor_selecionado = ""

def limpar_investidor():
    st.session_state.investidor_selecionado = ""

def formatar_cpf(valor):
    v = str(valor).replace(".0", "").zfill(11)
    if len(v) != 11:
        return ""
    return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"


def formatar_cnpj(valor):
    v = str(valor).replace(".0", "").zfill(14)
    if len(v) != 14:
        return ""
    return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"

def render_table(df, *, dataframe=True, **kwargs):
    """
    Renderiza tabelas no Streamlit sem mostrar NaN / NaT / None,
    preservando os tipos originais do dataframe.
    """
    df_view = df.copy()

    # Substitui apenas para exibição
    df_view = df_view.where(pd.notna(df_view), "")

    if dataframe:
        st.dataframe(df_view, **kwargs)
    else:
        st.table(df_view)


# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------------------

st.set_page_config(
    page_title="People | V4 Company",
    layout="wide",
    page_icon="LOGO VERMELHO.png"
)

# ==============================
# LOGIN SIMPLES COM SENHA SEGURA
# ==============================

def verificar_senha(senha_digitada, senha_hash):
    return bcrypt.checkpw(
        senha_digitada.encode("utf-8"),
        senha_hash.encode("utf-8")
    )

st.title("🔐 Login")

usuario = st.text_input("Usuário")
senha = st.text_input("Senha", type="password")

users = st.secrets["users"]

if usuario not in users:
    st.error("Usuário ou senha inválidos")
    st.stop()

senha_hash = users[usuario]["password"]

if not verificar_senha(senha, senha_hash):
    st.error("Usuário ou senha inválidos")
    st.stop()

st.success(f"Bem-vindo, {users[usuario]['name']} 👋")

st.markdown("---")

        
# --------------------------------------------------
# ABAS
# --------------------------------------------------
aba_dashboard, aba_relatorios, aba_benefícios = st.tabs([
    "📊 Dashboard",
    "📄 Relatórios",
    "🎁 Benefícios"
])

# --------------------------------------------------
# ABA DASHBOARD
# --------------------------------------------------

with aba_dashboard:
    
    # --------------------------------------------------
    # ESTILO
    # --------------------------------------------------
    st.markdown("""
    <style>
    
    /* =========================
       CONSULTA INDIVIDUAL — COMPACTAÇÃO REAL
       ========================= */
    
    /* Títulos das seções */
    h5 {
        font-size: 20px !important;
        margin-top: 6px !important;
        margin-bottom: 2px !important;
    }
    
    /* Label */
    label {
        font-size: 10px !important;
        margin-bottom: 0px !important;
        color: #bdbdbd !important;
    }
    
    /* 🔥 CONTAINER DO INPUT (o retângulo) */
    div[data-testid="stTextInput"] {
        height: 30px !important;
    }
    
    /* 🔥 INPUT REAL */
    div[data-testid="stTextInput"] input {
        height: 40px !important;
        padding: 10px 10px !important;
        font-size: 12px !important;
        line-height: 0px !important; /* 👈 CENTRALIZA O TEXTO */
    }
    
    /* Remove espaço entre campos */
    div[data-testid="stTextInput"] {
        margin-bottom: 25px !important;
    }
    
    /* Remove respiro extra das colunas */
    div[data-testid="column"] {
        padding-top: 5px !important;
        padding-bottom: 0px !important;
    }
    
    /* Benefícios */
    .espaco-beneficio {
        margin-top: 15px;
        margin-bottom: 4px;
    }
    
    </style>
    """, unsafe_allow_html=True)
    
    st.cache_data.clear()
       
    # --------------------------------------------------
    # GOOGLE SHEETS
    # --------------------------------------------------
    import gspread
    from google.oauth2.service_account import Credentials
    
    @st.cache_data(ttl=600)
    def load_google_sheet():
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    
        client = gspread.authorize(creds)
    
        sheet = client.open_by_key("13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY")
        worksheet = sheet.get_worksheet(6)
    
        data = worksheet.get_all_records()
        return pd.DataFrame(data)

    
    # --------------------------------------------------
    # LOAD + ORGANIZAÇÃO
    # --------------------------------------------------
    df = load_google_sheet()
    df = df.rename(columns={"Data Início": "Início na V4"})

    df.columns = df.columns.str.strip().str.replace("\u00a0", "", regex=False)

    df.columns = df.columns.str.strip()
    df = df.sort_values(df.columns[0]).reset_index(drop=True)
    
    # 👇 AQUI É O LUGAR CERTO
    df = df.fillna("")
        
    # --------------------------------------------------
    # BACKUP RAW (ANTES DE CONVERTER)
    # --------------------------------------------------
    df["Início na V4_raw"] = df["Início na V4"]
    df["Data de nascimento_raw"] = df["Data de nascimento"]
    df["Data do contrato_raw"] = df["Data do contrato"]
    df["Térm previsto_raw"] = df["Térm previsto"]
    
    
    # --------------------------------------------------
    # CONVERSÃO CORRETA (DAYFIRST)
    # --------------------------------------------------
    
    # BACKUP TEXTO ORIGINAL
    df["Início na V4_raw"] = df["Início na V4"]
    df["Data de nascimento_raw"] = df["Data de nascimento"]
    df["Data do contrato_raw"] = df["Data do contrato"]
    df["Térm previsto_raw"] = df["Térm previsto"]
    
    # DATETIME (PARA CÁLCULOS)
    df["Início na V4_dt"] = parse_data_br(df["Início na V4_raw"])
    df["Data de nascimento_dt"] = parse_data_br(df["Data de nascimento_raw"])
    df["Data do contrato_dt"] = parse_data_br(df["Data do contrato_raw"])
    df["Térm previsto_dt"] = parse_data_br(df["Térm previsto_raw"])
    
    # TEXTO FINAL (EXIBIÇÃO)
    df["Início na V4"] = df["Início na V4_dt"].dt.strftime("%d/%m/%Y").fillna("")
    df["Data de nascimento"] = df["Data de nascimento_dt"].dt.strftime("%d/%m/%Y").fillna("")
    df["Data do contrato"] = df["Data do contrato_dt"].dt.strftime("%d/%m/%Y").fillna("")
    
    # Térm previsto: data vira data, texto continua texto
    df["Térm previsto"] = df["Térm previsto_raw"].where(
        df["Térm previsto_dt"].isna(),
        df["Térm previsto_dt"].dt.strftime("%d/%m/%Y")
    )

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------
    st.sidebar.success(f"Bem-vindo(a), {st.session_state.user_name}")
    
    if st.sidebar.button("🔄 Atualizar dados"):
        st.cache_data.clear()
        st.rerun()
    
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    # --------------------------------------------------
    # TOPO
    # --------------------------------------------------
    col_logo, col_title = st.columns([1, 6])
    
    with col_logo:
        st.image("LOGO VERMELHO.png", width=120)
        
    with col_title:
        st.markdown("<h1>Dashboard People</h1><h3 style='color:#ccc;'>V4 Company</h3>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --------------------------------------------------
    # CONSULTA INDIVIDUAL
    # --------------------------------------------------

    st.subheader("🔎 Consulta individual do investidor")
    
    df_consulta = df.fillna("")
    lista_nomes = sorted(df_consulta["Nome"].unique())
    
    c_busca, c_limpar = st.columns([5, 1])
    
    with c_busca:
        nome = st.selectbox(
            "Selecione o investidor",
            ["Selecione um investidor..."] + lista_nomes,
            key="investidor_selecionado",
            label_visibility="collapsed"
        )
    
    if nome == "Selecione um investidor...":
        nome = ""
    
    
    if nome == "Selecione um investidor...":
        nome = ""
    
    
    if nome == "Selecione um investidor...":
        nome = ""
    
    
    with c_limpar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button(
            "Limpar",
            on_click=limpar_investidor
        )
    
    
    
    if nome:
        linha = df_consulta[df_consulta["Nome"] == nome].iloc[0]
    
        col1, col2, col3 = st.columns([3, 3, 2])
    
        # -------------------------
        # COLUNA 1 — PROFISSIONAL
        # -------------------------
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
        
            tempo_casa = ""
            if linha["Início na V4"] != "":
                delta = datetime.today() - linha["Início na V4_dt"]
                anos = delta.days // 365
                meses = (delta.days % 365) // 30
                dias = (delta.days % 365) % 30
                tempo_casa = f"{anos} anos, {meses} meses e {dias} dias"
        
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
    
    
        # -------------------------
        # COLUNA 2 — ADMIN / PESSOAL
        # -------------------------
        with col2:
            st.markdown("##### 🧾 Centro de custo")
    
            # Centro de custo (código menor / descrição maior)
            codigo_cc = str(linha["Código CC"]).replace(".0", "")
    
            b1, b2 = st.columns([1, 3])
            b1.text_input("Código CC", codigo_cc, disabled=True)
            b2.text_input("Descrição CC", linha["Descrição CC"], disabled=True)
    
    
            b3, b4 = st.columns(2)
            b3.text_input("Senioridade", linha["Senioridade"], disabled=True)
            b4.text_input("Conta contábil", linha["Conta contábil"], disabled=True)
    
            st.text_input("Liderança direta", linha["Liderança direta"], disabled=True)
    
            st.markdown("##### 👤 Dados pessoais")
    
            cpf = str(linha["CPF"]).replace(".0", "")
    
            b5, b6, b7 = st.columns(3)
            cpf = formatar_cpf(linha["CPF"])
            b5.text_input("CPF", cpf, disabled=True)
            b6.text_input("Nascimento", linha["Data de nascimento"], disabled=True)
  
            idade = ""
            if linha["Data de nascimento"] != "":
                idade = int((datetime.today() - pd.to_datetime(linha["Data de nascimento"])).days / 365.25)
                idade = f"{idade} anos"
            b7.text_input("Idade", idade, disabled=True)
    
            b8, b9 = st.columns(2)
            b8.text_input("CEP", linha["CEP"], disabled=True)
            b9.text_input("Escolaridade", linha["Escolaridade"], disabled=True)
    
            st.text_input("Telefone pessoal", linha["Telefone pessoal"], disabled=True)
            st.text_input("E-mail pessoal", linha["E-mail pessoal"], disabled=True)
    
        # -------------------------
        # COLUNA 3 — FOTO / BENEFÍCIOS / LINK
        # -------------------------
        with col3:
            st.markdown("##### 🖼️ Foto")
            if linha["Foto"]:
                st.image(linha["Foto"], use_container_width=True)
            else:
                st.info("Sem foto")
    
            st.markdown("##### 🎁 Benefícios")
    
            st.text_input("Situação no plano", linha["Situação no plano"], disabled=True)
    
            carteira_med = str(linha["Carteirinha médico"]).replace(".0", "")
            carteira_odo = str(linha["Carteirinha odonto"]).replace(".0", "")
    
            st.text_input("Plano médico", linha["Operadora Médico"], disabled=True)
            st.text_input("Carteirinha médico", carteira_med, disabled=True)
    
            st.markdown('<div class="espaco-beneficio"></div>', unsafe_allow_html=True)
    
            st.text_input("Plano odonto", linha["Operadora Odonto"], disabled=True)
            st.text_input("Carteirinha odonto", carteira_odo, disabled=True)
    
    
            st.markdown("##### 🔗 Link")
            if linha["Link Drive"]: st.link_button("Abrir Drive", linha["Link Drive"])
    
    # --------------------------------------------------
    # FORMAT TABELA
    # --------------------------------------------------
    
    def limpar_numero(valor):
        if valor == "" or pd.isna(valor):
            return ""
        return str(valor).replace(".0", "").strip()
    
    
    def formatar_cpf(valor):
        v = limpar_numero(valor)
        if len(v) == 11:
            return f"{v[0:3]}.{v[3:6]}.{v[6:9]}-{v[9:11]}"
        return v
    
    
    def formatar_cnpj(valor):
        v = limpar_numero(valor)
        if len(v) == 14:
            return f"{v[0:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:14]}"
        return v
    
    
    def formatar_matricula(valor):
        v = limpar_numero(valor)
        if v.isdigit():
            return v.zfill(6)
        return v
    
    # --------------------------------------------------
    # TABELA
    # --------------------------------------------------
    st.markdown("---")
    st.markdown("### 📋 Base de investidores")
    
    busca = st.text_input(
        "Buscar na tabela",
        placeholder="🔍 Buscar na tabela...",
        label_visibility="collapsed"
    )
    
    
    df_tabela = df.copy()

    df_tabela["Data de nascimento"] = df_tabela["Data de nascimento"]
    df_tabela["Data do contrato"] = df_tabela["Data do contrato"]
    df_tabela["Início na V4"] = df_tabela["Início na V4"]

    # Datas exibidas
    df_tabela["Término do contrato"] = df_tabela["Térm previsto"]
    df_tabela["Data de início"] = df_tabela["Início na V4"]
    
    # Limpeza de campos com .0
    df_tabela["BP"] = df_tabela["BP"].apply(limpar_numero)
    df_tabela["Código CC"] = df_tabela["Código CC"].apply(limpar_numero)
    df_tabela["Carteirinha médico"] = df_tabela["Carteirinha médico"].apply(limpar_numero)
    df_tabela["Carteirinha odonto"] = df_tabela["Carteirinha odonto"].apply(limpar_numero)
    
    # Matrícula com 6 dígitos
    df_tabela["Matrícula"] = df_tabela["Matrícula"].apply(formatar_matricula)
    
    # CPF e CNPJ formatados
    df_tabela["CPF"] = df_tabela["CPF"].apply(formatar_cpf)
    df_tabela["CNPJ"] = df_tabela["CNPJ"].apply(formatar_cnpj)
    
    
    if busca:
        df_tabela = df_tabela[
            df_tabela.astype(str)
            .apply(lambda x: x.str.contains(busca, case=False).any(), axis=1)
        ]
        
    df_tabela.insert(
        df_tabela.columns.get_loc("Nome") + 1,
        "Início na V4",
        df_tabela.pop("Início na V4")
    )
    

    st.dataframe(
        df_tabela.drop(
            columns=[c for c in df_tabela.columns if c.endswith("_raw") or c.endswith("_dt")],
            errors="ignore"
        ),
        use_container_width=True,
        hide_index=True
    )

     
    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------
    st.markdown("---")
    hoje = datetime.today()
    prox_30_dias = hoje + timedelta(days=30)
    
    headcount = len(df)
    contratos_vencer = df[
        df["Térm previsto_dt"].notna() &
        (df["Térm previsto_dt"] <= prox_30_dias)
    ]
    
    contratos_vencidos = df[
        df["Térm previsto_dt"].notna() &
        (df["Térm previsto_dt"] < hoje)
    ]
    
    pj = len(df[df["Modelo de contrato"] == "PJ"])
    clt = len(df[df["Modelo de contrato"] == "CLT"])
    estagio = len(df[df["Modelo de contrato"] == "Estágio"])
    
    df_adm = df[df["Início na V4_dt"].notna()]

    media_admissoes = (
        df_adm
        .groupby(df_adm["Início na V4_dt"].dt.to_period("M"))
        .size()
        .mean()
    )
    
    # --------------------------------------------------
    # KPIs VISUAIS
    # --------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Headcount", headcount)
    c2.metric("Contratos vencendo (30 dias)", len(contratos_vencer))
    c3.metric("Contratos vencidos", len(contratos_vencidos))
    c4.metric("PJ / CLT / Estágio", f"{pj} / {clt} / {estagio}")
    c5.metric("Média admissões / mês", f"{media_admissoes:.1f}")
    
    st.markdown("---")
    
    # --------------------------------------------------
    # GRÁFICOS
    # --------------------------------------------------
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("📃 Modelo de contrato")
        contrato_df = df["Modelo de contrato"].value_counts().reset_index()
        contrato_df.columns = ["Modelo", "Quantidade"]
    
        st.altair_chart(
            alt.Chart(contrato_df)
            .mark_arc(innerRadius=60)
            .encode(
                theta="Quantidade:Q",
                color=alt.Color("Modelo:N", scale=alt.Scale(range=["#E30613", "#B0000A", "#FF4C4C"])),
                tooltip=["Modelo", "Quantidade"]
            ),
            use_container_width=True
        )
    
    with g2:
        st.subheader("📍 Local de atuação")
        local_df = df["Unidade/Atuação"].value_counts().reset_index()
        local_df.columns = ["Local", "Quantidade"]
    
        st.altair_chart(
            alt.Chart(local_df)
            .mark_bar(color="#E30613")
            .encode(
                x=alt.X("Local:N", sort="-y", axis=alt.Axis(labelAngle=-30)),
                y="Quantidade:Q",
                tooltip=["Local", "Quantidade"]
            ),
            use_container_width=True
        )
    
    # --------------------------------------------------
    # ADMISSÕES
    # --------------------------------------------------
    st.subheader("📈 Admissões por mês")
    
    adm_mes = (
        df_adm.assign(Mes=df_adm["Início na V4_dt"].dt.strftime("%b/%Y"))
        .groupby("Mes")
        .size()
        .reset_index(name="Quantidade")
    )
    
    st.altair_chart(
        alt.Chart(adm_mes)
        .mark_line(color="#E30613", point=True)
        .encode(x="Mes:N", y="Quantidade:Q", tooltip=["Mes", "Quantidade"]),
        use_container_width=True
    )
    

# --------------------------------------------------
# ABA RELATÓRIOS
# --------------------------------------------------
with aba_relatorios:

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # TOPO
    # --------------------------------------------------
    col_logo, col_title = st.columns([1, 6])

    with col_logo:
        st.image("LOGO VERMELHO.png", width=120)

    with col_title:
        st.markdown(
            "<h1>Análises & Relatórios</h1><h3 style='color:#ccc;'>V4 Company</h3>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --------------------------------------------------
    # LAYOUT PRINCIPAL — RELATÓRIOS
    # --------------------------------------------------
    col_relatorios, col_divisor, col_acoes = st.columns([7, 0.1, 3])
    
    with col_divisor:
        st.markdown(
            """
            <div style="
                height: 100%;
                border-left: 1px solid #e0e0e0;
                margin: 0 auto;
            "></div>
            """,
            unsafe_allow_html=True
        )


    # --------------------------------------------------
    # COLUNA ESQUERDA — RELATÓRIOS
    # --------------------------------------------------
    with col_relatorios:

        st.markdown("## 📊 Relatórios Principais")

        # -------------------------------
        # ANIVERSARIANTES DO MÊS
        # -------------------------------
        
        with st.expander("🎉 Aniversariantes do mês", expanded=False):
        
            meses = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
        
            mes_atual = datetime.today().month
        
            mes_selecionado = st.selectbox(
                "Mês",
                options=list(meses.keys()),
                format_func=lambda x: meses[x],
                index=mes_atual - 1
            )
        
            df_aniversario = df.copy()
        
            df_aniversario = df[
                df["Data de nascimento_dt"].dt.month == mes_selecionado
            ]

            df_check = df.copy()

            df_check["Data de nascimento_raw"] = df_check["Data de nascimento"]
            
            df_check["Data de nascimento_dt"] = pd.to_datetime(
                df_check["Data de nascimento_raw"],
                dayfirst=True,
                errors="coerce"
            )
            
            df_invalidos = df_check[df_check["Data de nascimento_dt"].isna()]


            # 🔔 LISTAR PESSOAS COM DATA INVÁLIDA
            if not df_invalidos.empty:
                col_warn, col_link = st.columns([5, 2])
            
                with col_warn:
                    st.warning(f"⚠️ {len(df_invalidos)} pessoas com data de nascimento inválida")
            
                with col_link:
                    with st.popover("👀 Ver aqui"):
                        df_invalidos_view = df_invalidos[
                            ["Nome", "Data de nascimento_raw"]
                        ].reset_index(drop=True)
            
                        st.table(df_invalidos_view)
        
            if df_aniversario.empty:
                st.info("Nenhum aniversariante neste mês 🎈")
            else:
                ano_atual = datetime.today().year
        
                df_aniversario["Nascimento"] = df_aniversario["Data de nascimento_dt"].dt.strftime("%d/%m/%Y")
        
                df_aniversario["Idade que completa"] = (
                    ano_atual - df_aniversario["Data de nascimento_dt"].dt.year
                ).astype(int).astype(str) + " anos"
        
                df_aniversario["Dia"] = df_aniversario["Data de nascimento_dt"].dt.day
        
                df_final = df_aniversario[
                    ["Nome", "E-mail corporativo", "Nascimento", "Idade que completa", "Dia"]
                ].sort_values("Dia")
        
                # 🔥 remove índice visual
                df_final = df_final.reset_index(drop=True)
                df_final.index = [""] * len(df_final)
        
                render_table(
                    df_final.drop(columns=["Dia"]),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nascimento": st.column_config.TextColumn(
                            "Nascimento",
                            width="small"
                        ),
                        "Idade que completa": st.column_config.TextColumn(
                            "Idade que completa",
                            width="small"
                        ),
                        "Nome": st.column_config.TextColumn(
                            "Nome",
                            width="large"
                        ),
                        "E-mail corporativo": st.column_config.TextColumn(
                            "E-mail corporativo",
                            width="large"
                        ),
                    }
                )


        # -------------------------------
        # VENCIMENTO / TÉRMINO PREVISTO
        # -------------------------------
        
        with st.expander("⏰ Contratos a vencer", expanded=False):
        
            col1, col2 = st.columns(2)
        
            with col1:
                data_inicio = st.date_input(
                    "Data inicial",
                    value=datetime.today().date(),
                    format="DD/MM/YYYY"
                )
            
            with col2:
                data_fim = st.date_input(
                    "Data final",
                    value=datetime.today().date() + relativedelta(months=3),
                    format="DD/MM/YYYY"
                )

        
            # 🔹 garante coluna datetime (NUNCA usar a original para .dt)
            df["Térm previsto_dt"] = pd.to_datetime(
                df["Térm previsto"],
                dayfirst=True,
                errors="coerce"
            )
        
            # 🔹 filtra período
            df_vencimento = df[
                df["Térm previsto_dt"].notna() &
                (df["Térm previsto_dt"].dt.date >= data_inicio) &
                (df["Térm previsto_dt"].dt.date <= data_fim)
            ]
        
            # 🔹 ordena ANTES de cortar colunas
            df_vencimento = df_vencimento.sort_values(
                "Térm previsto_dt",
                na_position="last"
            )
        
            if df_vencimento.empty:
                st.info("Nenhum contrato vencendo no período selecionado ⏳")
            else:
                # 🔹 formata data apenas para exibição
                df_vencimento["Térm previsto"] = (
                    df_vencimento["Térm previsto_dt"]
                    .dt.strftime("%d/%m/%Y")
                    .fillna("")
                )
        
                df_final = df_vencimento[
                    [
                        "Nome",
                        "E-mail corporativo",
                        "Térm previsto"
                    ]
                ].reset_index(drop=True)
        
                df_final.index = [""] * len(df_final)
        
                render_table(
                    df_final,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nome": st.column_config.TextColumn(
                            "Nome",
                            width="large"
                        ),
                        "E-mail corporativo": st.column_config.TextColumn(
                            "E-mail corporativo",
                            width="large"
                        ),
                        "Término previsto": st.column_config.TextColumn(
                            "Térm previsto",
                            width="small"
                        ),
                    }
                )

        # -------------------------------
        # INVESTIDORES MEI
        # -------------------------------
        with st.expander("💼 Investidores MEI", expanded=False):

            # Verifica se a coluna Modalidade PJ existe
            if "Modalidade PJ" not in df.columns:
                st.warning("Coluna 'Modalidade PJ' não encontrada no DataFrame.")
        
            else:
                # Filtra apenas MEI
                df_mei = df[
                    df["Modalidade PJ"]
                    .astype(str)
                    .str.upper()
                    .str.contains("MEI", na=False)
                ]
        
                if df_mei.empty:
                    st.info("Nenhum investidor MEI encontrado.")
        
                else:

                    # 🔔 ALERTA – TOTAL DE INVESTIDORES MEI
                    total_mei = len(df_mei)
                    
                    st.warning(
                        f"⚠️ Temos **{total_mei} investidores na modalidade MEI** que precisam regularizar a forma de contratação."
                    )

                    # 🔹 MAPEAMENTO SEGURO DE COLUNAS
                    colunas_map = {
                        "Nome": None,
                        "Email Corporativo": None,
                        "Data do contrato": None,
                        "Modalidade PJ": None,
                    }
                    
                    for col in df_mei.columns:
                        c = col.strip().lower()
                    
                        if c == "nome":
                            colunas_map["Nome"] = col
                    
                        elif "mail" in c:
                            colunas_map["Email Corporativo"] = col
                    
                        elif any(x in c for x in ["contrato", "admiss"]):
                            colunas_map["Data do contrato"] = col
                    
                        elif "modalidade" in c:
                            colunas_map["Modalidade PJ"] = col

        
                    # Remove colunas não encontradas
                    colunas_validas = {
                        k: v for k, v in colunas_map.items() if v is not None
                    }
        
                    df_mei_final = df_mei[list(colunas_validas.values())].copy()
                    df_mei_final.columns = list(colunas_validas.keys())
        
                    # Formata data do contrato
                    if "Data do contrato" in df_mei_final.columns:
                        df_mei_final["Data do contrato"] = pd.to_datetime(
                            df_mei_final["Data do contrato"],
                            errors="coerce"
                        ).dt.strftime("%d/%m/%Y")
        
                    st.dataframe(
                        df_mei_final,
                        use_container_width=True,
                        hide_index=True
                    )

    # --------------------------------------------------
    # COLUNA DIREITA — AÇÕES
    # --------------------------------------------------
    with col_acoes:

        st.markdown("## ⚙️ Ações")

        # ---------------------------------
        # BOTÃO – TÍTULO DE DOC PARA AUTOMAÇÃO
        # ---------------------------------
        
        def limpar_titulo():
            st.session_state["titulo_doc"] = ""
            st.session_state.pop("titulo_gerado", None)
        
        
        @st.dialog("📝 Gerador de título para automação")
        def modal_titulo_doc():
        
            # ---------- CAMPO TÍTULO + BOTÃO LIMPAR ----------
            col_input, col_clear = st.columns([5, 1])
        
            with col_input:
                st.text_input(
                    "Título original do arquivo",
                    placeholder="Cole aqui o título do arquivo",
                    key="titulo_doc"
                )
        
            with col_clear:
                st.markdown("<div style='height:23px'></div>", unsafe_allow_html=True)
                st.button(
                    "❌",
                    help="Limpar título",
                    on_click=limpar_titulo
                )
        
            # ---------- SELECT DE NOMES (ALFABÉTICO / EM BRANCO) ----------
            lista_nomes = sorted(df["Nome"].dropna().unique())
        
            st.selectbox(
                "Selecione o investidor",
                options=[""] + lista_nomes,
                index=0,
                key="nome_selecionado",
                placeholder="Digite ou selecione um nome"
            )

            if st.button("✅ Gerar", use_container_width=True):
                gerar = True
       
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
     
                cpf_limpo = (
                    str(dados.get("CPF", ""))
                    .replace(".", "")
                    .replace("-", "")
                    .replace("/", "")
                )
       
                email_pessoal = dados.get("E-mail pessoal", "")
       
                st.session_state["titulo_gerado"] = (
                    f"{nome_selecionado} __ "
                    f"{cpf_limpo} __ "
                    f"{email_pessoal} __ "
                    f"{titulo_doc}"
                )
        
            # ---------- TÍTULO GERADO ----------
            if "titulo_gerado" in st.session_state:
                st.markdown("#### 📄 Título gerado")
                st.code(st.session_state["titulo_gerado"])
        
        
        # ---------- BOTÃO QUE ABRE O MODAL (RESET TOTAL) ----------
        def abrir_modal_titulo():
            st.session_state["titulo_doc"] = ""
            st.session_state["nome_selecionado"] = ""
            st.session_state.pop("titulo_gerado", None)
            modal_titulo_doc()
        
        
        if st.button("📝 Título de doc para automação"):
            abrir_modal_titulo()


# --------------------------------------------------
# ABA BENEFICIOS
# --------------------------------------------------

with aba_benefícios:

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # TOPO
    # --------------------------------------------------
    col_logo, col_title = st.columns([1, 6])

    with col_logo:
        st.image("LOGO VERMELHO.png", width=120)

    with col_title:
        st.markdown(
            "<h1> Gestão de Benefícios </h1>"
            "<h3 style='color:#ccc;'>V4 Company</h3>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    from datetime import datetime, timedelta
    import altair as alt

    # --------------------------------------------------
    # LAYOUT — BENEFÍCIOS
    # --------------------------------------------------
    col_grafico, col_consulta = st.columns([4, 6])

    # ---------------------------------
    # COLUNA 1 — GRÁFICO SITUAÇÃO NO PLANO
    # ---------------------------------
    with col_grafico:

        st.markdown("<h3 style='margin-bottom:20px'>📊 Status no plano</h3>", unsafe_allow_html=True)
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    
        if "Situação no plano" in df.columns:
    
            df_plano = (
                df["Situação no plano"]
                .fillna("Não informado")
                .value_counts()
                .reset_index()
            )
    
            df_plano.columns = ["Situação", "Quantidade"]
            total = df_plano["Quantidade"].sum()
            df_plano["Percentual"] = (df_plano["Quantidade"] / total) * 100
    
            grafico_plano = (
                alt.Chart(df_plano)
                .mark_arc(innerRadius=80, outerRadius=130, stroke=None)
                .encode(
                    theta="Quantidade:Q",
                    color=alt.Color(
                        "Situação:N",
                        scale=alt.Scale(
                            range=[
                                "#2E8B57",
                                "#FFA500",
                                "#8A2BE2",
                                "#DC143C",
                                "#8B4513",
                                "#808080",
                            ]
                        ),
                        legend=alt.Legend(
                            title="Situação",
                            orient="bottom",
                            columns=2,
                            offset=20
                        )
                    ),
                    tooltip=[
                        alt.Tooltip("Situação:N", title="Situação"),
                        alt.Tooltip("Quantidade:Q", title="Qtd"),
                        alt.Tooltip("Percentual:Q", title="%", format=".1f"),
                    ],
                )
                .properties(width=320, height=380)
            )
    
            st.altair_chart(grafico_plano, use_container_width=True)
    
        else:
            st.warning("Coluna 'Situação no plano' não encontrada.")

    # ---------------------------------
    # COLUNA 2 — CONSULTA CARTEIRINHAS
    # ---------------------------------
    with col_consulta:
    
        st.markdown("### 🔎 Consulta de carteirinhas")
    
        nome_beneficio = st.selectbox(
            "Selecione o investidor",
            options=[""] + sorted(df["Nome"].dropna().unique()),
            placeholder="Digite ou selecione um nome"
        )
    
        consultar = st.button("Consultar carteirinhas", use_container_width=True)
    
        if nome_beneficio and consultar:
    
            dados = df[df["Nome"] == nome_beneficio].iloc[0]
    
            cart_med = str(dados.get("Carteirinha médico", "")).strip()
            oper_med = str(dados.get("Operadora Médico", "")).strip()
            cart_odo = str(dados.get("Carteirinha odonto", "")).strip()
            oper_odo = str(dados.get("Operadora Odonto", "")).strip()
            situacao = str(dados.get("Situação no plano", "Não informado"))
    
            # 🔴 CASO NÃO TENHA CARTEIRINHA (NÃO ATIVO)
            if not cart_med and not cart_odo:
    
                st.markdown(
                    f"""
                    <div style="
                        position: relative;
                        padding: 25px;
                        border-radius: 12px;
                        background: rgba(0,0,0,0.55);
                        backdrop-filter: blur(6px);
                        -webkit-backdrop-filter: blur(6px);
                        color: white;
                        text-align: center;
                    ">
                        <h4>⚠️ Investidor não ativo no plano</h4>
                        <p>Este investidor não possui carteirinhas ativas no momento.</p>
                        <hr style="opacity:0.2;">
                        <div style="
                            margin-top: 12px;
                            padding: 10px;
                            border-radius: 8px;
                            background-color: #8B0000;
                            color: white;
                            font-weight: bold;
                        ">
                            Situação atual no plano: {situacao}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
            # 🟢 CASO TENHA CARTEIRINHA
            else:
                st.text_input(
                    "Carteirinha médico",
                    cart_med if cart_med else "—",
                    disabled=True
                )
                st.text_input(
                    "Operadora médico",
                    oper_med if oper_med else "—",
                    disabled=True
                )
    
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    
                st.text_input(
                    "Carteirinha odonto",
                    cart_odo if cart_odo else "—",
                    disabled=True
                )
                st.text_input(
                    "Operadora odonto",
                    oper_odo if oper_odo else "—",
                    disabled=True
                )

    st.markdown("---")

    # ==============================
    # BLOCO — RELATÓRIOS & AÇÕES
    # ==============================
        
    # -------- GRID PRINCIPAL --------
    col_relatorios, col_acoes = st.columns([7, 3])
    
    # ==============================
    # COLUNA ESQUERDA — RELATÓRIOS
    # ==============================
    with col_relatorios:
        st.markdown("### 📊 Relatórios")
    
        abas = st.tabs([
            "⏰ Pendentes",
            "📂 Aguardando docs",
            "📩 Enviar para DBL",
            "🆗 Aguardando ativação"
        ])
    
        with abas[0]:
            st.markdown("#### Investidores com documentação pendente")
        
            # --- FILTRO: somente pendentes ---
            df_pendentes = df[df["Situação no plano"] == "Pendente"]
        
            # --- SELEÇÃO DAS COLUNAS ---
            tabela_docs = df_pendentes[[
                "Nome",
                "E-mail corporativo",
                "Modelo de contrato",
                "Solicitar documentação"
            ]]
        
            st.dataframe(
                tabela_docs,
                use_container_width=True,
                hide_index=True
            )

        with abas[1]:
            st.markdown("#### Aguardando envio da documentação")
        
            # --- FILTRO: somente pendentes ---
            df_pendentes = df[df["Situação no plano"] == "Aguardando docs"]
        
            # --- SELEÇÃO DAS COLUNAS ---
            tabela_docs = df_pendentes[[
                "Nome",
                "E-mail corporativo",
                "Modelo de contrato",
                "Enviar no EB"
            ]]
        
            st.dataframe(
                tabela_docs,
                use_container_width=True,
                hide_index=True
            )
            
        with abas[2]:
            st.markdown("#### Investidores para envio à DBL")
        
            # --- FILTRO: aguardando documentação ---
            df_dbl = df[df["Situação no plano"] == "Enviar à DBL"]
        
            # --- SELEÇÃO DAS COLUNAS ---
            tabela_dbl = df_dbl[[
                "Nome",
                "E-mail corporativo",
                "Modelo de contrato",
                "Enviar no EB"
            ]]
        
            st.dataframe(
                tabela_dbl,
                use_container_width=True,
                hide_index=True
            )

    
        with abas[3]:
            st.markdown("#### Investidores aguardando retorno da DBL")
        
            # --- FILTRO: aguardando DBL ---
            df_dbl_status = df[df["Situação no plano"] == "Aguardando DBL"]
        
            # --- COLUNAS EXIBIDAS ---
            tabela_dbl_status = df_dbl_status[[
                "Nome",
                "E-mail corporativo",
                "Modelo de contrato"
            ]]
        
            st.dataframe(
                tabela_dbl_status,
                use_container_width=True,
                hide_index=True
            )


    with col_acoes:
        # ==============================
        # AÇÃO — GERAR SUBFATURA
        # ==============================
        
        from docx import Document
        import re
        from datetime import datetime, date
        
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

        def formatar_cnpj(cnpj):
            # Converte para string e remove .0 se vier como float
            cnpj_str = str(cnpj).replace(".0", "")
            
            # Remove tudo que não for número
            cnpj_numeros = re.sub(r"\D", "", cnpj_str)
        
            # Garante 14 dígitos (com zeros à esquerda se necessário)
            cnpj_numeros = cnpj_numeros.zfill(14)
        
            return (
                f"{cnpj_numeros[0:2]}."
                f"{cnpj_numeros[2:5]}."
                f"{cnpj_numeros[5:8]}/"
                f"{cnpj_numeros[8:12]}-"
                f"{cnpj_numeros[12:14]}"
            )


        # -------- BOTÃO PRINCIPAL --------
        st.markdown("### ⚙️ Ações")
        
        if st.button("📄 Gerar Subfatura", use_container_width=True):
            st.session_state["abrir_subfatura"] = not st.session_state.get("abrir_subfatura", False)
        
        # -------- BLOCO SIMULANDO MODAL --------
        if st.session_state.get("abrir_subfatura", False):
        
            st.markdown("## 📄 Gerar Subfatura")
        
            nomes = sorted(df["Nome"].dropna().unique())
            nome_escolhido = st.selectbox("Selecione o investidor", nomes)
        
            data_vigencia = st.date_input(
                "Data de início da vigência",
                format="DD/MM/YYYY"
            )
        
            st.markdown("<br>", unsafe_allow_html=True)
        
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                gerar = st.button("✅ Gerar", use_container_width=True)
        
            if gerar:
        
                dados = df[df["Nome"] == nome_escolhido].iloc[0]
        
                razao_social = str(dados["Razão social"])
                cnpj = formatar_cnpj(dados["CNPJ"])
                cpf = str(dados["CPF"])
                email_pessoal = str(dados["E-mail pessoal"])
                modelo_contrato = str(dados["Modelo de contrato"])
        
                # -------- VALIDAÇÃO PJ --------
                if "PJ" not in modelo_contrato.upper():
                    st.warning(
                        f"⚠️ **{nome_escolhido}** não possui contrato PJ.\n\n"
                        f"Modelo atual: **{modelo_contrato}**"
                    )
        
                # -------- ABRE TEMPLATE --------
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
        
                nome_arquivo = (
                    f"{nome_escolhido} __ {cpf_limpo} __ {email_pessoal} __ Subfatura.docx"
                )
        
                doc.save(nome_arquivo)
        
                col_btn1, col_btn2 = st.columns(2)

                with col_btn1:
                    with open(nome_arquivo, "rb") as f:
                        st.download_button(
                            "⬇️ Download",
                            data=f,
                            file_name=nome_arquivo,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                
                with col_btn2:
                    st.link_button(
                        "🔁 Converter PDF",
                        "https://www.ilovepdf.com/pt/word_para_pdf",
                        use_container_width=True
                    )

        
                st.success("Subfatura gerada com sucesso ✅")
                
        # ==============================
        # AÇÃO — GERAR TERMO DE SUBESTIPULANTE
        # ==============================
        st.markdown("---")
        if st.button("📄 Gerar Termo de Subestipulante", use_container_width=True):
            st.session_state["abrir_termo_subestipulante"] = not st.session_state.get(
                "abrir_termo_subestipulante", False
            )
        
        if st.session_state.get("abrir_termo_subestipulante", False):

            st.markdown("## 📄 Gerar Termo de Subestipulante")
        
            nomes = sorted(df["Nome"].dropna().unique())
            nome_escolhido = st.selectbox(
                "Selecione o investidor",
                nomes,
                key="nome_termo"
            )
        
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                gerar_termo = st.button(
                    "✅ Gerar Termo",
                    use_container_width=True,
                    key="btn_gerar_termo"
                )
        
            if gerar_termo:
        
                dados = df[df["Nome"] == nome_escolhido].iloc[0]
        
                razao_social = str(dados["Razão social"])
                cnpj = formatar_cnpj(dados["CNPJ"])
                cpf = str(dados["CPF"])
                email_pessoal = str(dados["E-mail pessoal"])
        
                # -------- ABRE TEMPLATE --------
                doc = Document("Termo de integração de subestipulante.docx")
        
                hoje = date.today()
                data_assinatura = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"
        
                mapa = {
                    "{RAZAO_SOCIAL}": razao_social,
                    "{CNPJ}": cnpj,
                    "{DATA}": data_assinatura
                }
        
                # Parágrafos normais
                substituir_texto(doc.paragraphs, mapa)
                
                # Tabelas
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            substituir_texto(cell.paragraphs, mapa)
                
                # Cabeçalho
                for section in doc.sections:
                    substituir_texto(section.header.paragraphs, mapa)

        
                cpf_limpo = re.sub(r"\D", "", cpf)
        
                nome_arquivo = (
                    f"{nome_escolhido} __ {cpf_limpo} __ {email_pessoal} __ Termo Subestipulante.docx"
                )
        
                doc.save(nome_arquivo)
        
                col_btn1, col_btn2 = st.columns(2)
        
                with col_btn1:
                    with open(nome_arquivo, "rb") as f:
                        st.download_button(
                            "⬇️ Download",
                            data=f,
                            file_name=nome_arquivo,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
        
                with col_btn2:
                    st.link_button(
                        "🔁 Converter PDF",
                        "https://www.ilovepdf.com/pt/word_para_pdf",
                        use_container_width=True
                    )
        
                st.success("Termo de Subestipulante gerado com sucesso ✅")

        # ==============================
        # AÇÃO — GERAR TERMO DE NÃO ADESÃO
        # ==============================
        
        st.markdown("---")
        
        if st.button("📄 Gerar Termo de Não Adesão", use_container_width=True):
            st.session_state["abrir_termo_nao_adesao"] = not st.session_state.get(
                "abrir_termo_nao_adesao", False
            )
        
        if st.session_state.get("abrir_termo_nao_adesao", False):
        
            st.markdown("## 📄 Gerar Termo de Não Adesão")
        
            nomes = sorted(df["Nome"].dropna().unique())
            nome_escolhido = st.selectbox(
                "Selecione o investidor",
                nomes,
                key="nome_nao_adesao"
            )
        
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                gerar_nao_adesao = st.button(
                    "✅ Gerar Termo",
                    use_container_width=True,
                    key="btn_gerar_nao_adesao"
                )
        
            if gerar_nao_adesao:
        
                dados = df[df["Nome"] == nome_escolhido].iloc[0]
        
                razao_social = str(dados["Razão social"])
                cnpj = formatar_cnpj(dados["CNPJ"])
        
                hoje = date.today()
                data_assinatura = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"
        
                mapa = {
                    "{RAZAO_SOCIAL}": razao_social,
                    "{CNPJ}": cnpj,
                    "{DATA}": data_assinatura
                }

                doc = Document("Termo de não adesão - Plano de Saúde e Dental.docx")
        
                # Corpo
                substituir_texto(doc.paragraphs, mapa)
        
                # Tabelas (segurança extra)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            substituir_texto(cell.paragraphs, mapa)
        
                # Cabeçalho e rodapé
                for section in doc.sections:
                    substituir_texto(section.header.paragraphs, mapa)
                    substituir_texto(section.footer.paragraphs, mapa)
        
                nome_arquivo = f"Termo de não adesão ao plano - {nome_escolhido}.docx"
        
                doc.save(nome_arquivo)
        
                col_btn1, col_btn2 = st.columns(2)
        
                with col_btn1:
                    with open(nome_arquivo, "rb") as f:
                        st.download_button(
                            "⬇️ Download",
                            data=f,
                            file_name=nome_arquivo,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
        
                with col_btn2:
                    st.link_button(
                        "🔁 Converter PDF",
                        "https://www.ilovepdf.com/pt/word_para_pdf",
                        use_container_width=True
                    )
        
                st.success("Termo de Não Adesão gerado com sucesso ✅")
