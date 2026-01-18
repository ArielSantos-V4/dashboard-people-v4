import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

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
# --------------------------------------------------
# LOGIN
# --------------------------------------------------
def check_password(username, password):
    users = st.secrets["users"]
    if username not in users:
        return False, None
    return password == users[username]["password"], users[username]["name"]
    
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    
if not st.session_state.authenticated:
    st.title("🔐 Login — Dashboard People V4")
    
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        valid, name = check_password(username, password)
        if valid:
            st.session_state.authenticated = True
            st.session_state.user_name = name
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    
    st.stop()
        
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
    
    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------
    def check_password(username, password):
        users = st.secrets["users"]
        if username not in users:
            return False, None
        return password == users[username]["password"], users[username]["name"]
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 Login — Dashboard People V4")
    
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
    
        if st.button("Entrar"):
            valid, name = check_password(username, password)
            if valid:
                st.session_state.authenticated = True
                st.session_state.user_name = name
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
    
        st.stop()
    
    # --------------------------------------------------
    # GOOGLE SHEETS
    # --------------------------------------------------
    @st.cache_data(ttl=600)
    def load_google_sheet():
        sheet_id = "13EPwhiXgh8BkbhyrEy2aCy3cv1O8npxJ_hA-HmLZ-pY"
        gid = 2056973316
    
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?gid={gid}&tqx=out:csv"
        return pd.read_csv(url)
    
    
    def parse_data_br(coluna):
        return pd.to_datetime(
            coluna.astype(str).str.strip().replace("", pd.NA),
            dayfirst=True,
            errors="coerce"
        )
    
    # --------------------------------------------------
    # LOAD + ORGANIZAÇÃO
    # --------------------------------------------------
    df = load_google_sheet()
    df = df.rename(columns={"Data Início": "Início na V4"})

    df.columns = df.columns.str.strip()
    df = df.sort_values("Nome").reset_index(drop=True)
    
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
    col_relatorios, col_divisor, col_acoes = st.columns([8, 0.1, 2])
    
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
        # VENCIMENTO DE CONTRATOS
        # -------------------------------
        
        with st.expander("⏳ Vencimento de contratos", expanded=False):
        
            # -------------------------------
            # FILTRO DE PERÍODO
            # -------------------------------
            col_d1, col_d2 = st.columns(2)
        
            hoje = datetime.today().date()
        
            with col_d1:
                data_inicio = st.date_input(
                    "De:",
                    value=hoje,
                    format="DD/MM/YYYY"
                )
        
            with col_d2:
                data_fim = st.date_input(
                    "Até:",
                    value=hoje + timedelta(days=30),
                    format="DD/MM/YYYY"
                )
        
            # -------------------------------
            # BASE
            # -------------------------------
            df_vencimento = df.copy()
        
            # -------------------------------
            # LIMPEZA FORTE DA DATA
            # -------------------------------
            df_vencimento["Térm previsto_raw"] = df_vencimento["Térm previsto"]
        
            df_vencimento["Térm previsto"] = (
                df_vencimento["Térm previsto"]
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .replace("Indeterminado", pd.NA)
            )
        
            df_vencimento = df[
                df["Térm previsto"].notna() &
                (df["Térm previsto_dt"].dt.date >= data_inicio) &
                (df["Térm previsto_dt"].dt.date <= data_fim)
            ]
        
            # -------------------------------
            # DATAS INVÁLIDAS (PADRÃO IGUAL)
            # -------------------------------
            df_invalidos = df_vencimento[
                df_vencimento["Térm previsto"].isna() &
                df_vencimento["Térm previsto_raw"].notna() &
                (df_vencimento["Térm previsto_raw"] != "Indeterminado")
            ][["Nome", "Térm previsto_raw"]]
        
            if not df_invalidos.empty:
                col_warn, col_link = st.columns([5, 2])
        
                with col_warn:
                    st.warning(
                        f"⚠️ {len(df_invalidos)} pessoas com data de término inválida"
                    )
        
                with col_link:
                    with st.popover("👀 Ver aqui"):
                        df_invalidos_view = (
                            df_invalidos
                            .rename(columns={"Térm previsto_raw": "Data informada"})
                            .reset_index(drop=True)
                        )
        
                        st.table(df_invalidos_view)
        
            # -------------------------------
            # FILTRO POR PERÍODO
            # -------------------------------
            df_vencimento = df_vencimento[
                df_vencimento["Térm previsto"].notna() &
                (df["Térm previsto_dt"].dt.date >= data_inicio) &
                (df["Térm previsto_dt"].dt.date <= data_fim)
            ]
        
            if df_vencimento.empty:
                st.info("Nenhum contrato vencendo no período selecionado")
            else:
                df_vencimento["Término previsto_dt"] = (
                    df_vencimento["Térm previsto_dt"]
                    .dt.strftime("%d/%m/%Y")
                )
        
                df_final = df_vencimento[
                    [
                        "Nome",
                        "E-mail corporativo",
                        "Término previsto",
                        "Modelo de contrato",
                        "Modalidade PJ"
                    ]
                ].sort_values("Término previsto")
        
                df_final = df_final.reset_index(drop=True)
                df_final.index = [""] * len(df_final)
        
                render_table(
                    df_final,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Término previsto": st.column_config.TextColumn(
                            "Término previsto",
                            width="small"
                        ),
                        "Modelo de contrato": st.column_config.TextColumn(
                            "Modelo de contrato",
                            width="small"
                        ),
                        "Modalidade PJ": st.column_config.TextColumn(
                            "Modalidade PJ",
                            width="medium"
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
        
            # ---------- BOTÃO CENTRALIZADO ----------
            col_esq, col_centro, col_dir = st.columns([1, 2, 1])
        
            with col_centro:
                if st.button("✅ Gerar título", use_container_width=True):
        
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
    st.info("Área reservada para atualizações futuras.")
