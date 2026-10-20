import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import io
import os

st.set_page_config(page_title="Supersonic V3", layout="wide", page_icon="🚀")

st.markdown("""
<style>
.stApp {background-color: #0d1117; color: #c9d1d9;}
h1, h2, h3 {color: #2ea043 !important;}
.stButton > button {background-color: #21262d; color: #2ea043; border: 1px solid #2ea043; width: 100%;}
div[data-testid="stMetricValue"] {color: #2ea043;}
</style>
""", unsafe_allow_html=True)

# ========== LOGIN ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Supersonic V3 - Acesso Admin")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if user == "admin" and senha == "supersonic2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
    st.stop()

# ========== BANCO ==========
def init_db():
    conn = sqlite3.connect("supersonic.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id TEXT PRIMARY KEY, nome TEXT, modelo TEXT, plano TEXT,
        email TEXT, telefone TEXT, estado TEXT, setup REAL, mensalidade REAL,
        status TEXT, data_cadastro TEXT, afiliado TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS afiliados (
        id TEXT PRIMARY KEY, nome TEXT, telefone TEXT, comissao_setup REAL,
        comissao_mensal REAL, total_indicados INTEGER, data_cadastro TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ========== TABELAS DE PREÇO ==========
ALTO_TICKET = {
    "Cooperativa Grande": {"setup": 150000.0, "mensalidade": 45000.0},
    "Clínica Médica": {"setup": 15000.0, "mensalidade": 4900.0},
    "Posto de Gasolina": {"setup": 10000.0, "mensalidade": 3999.0},
    "Associação Transporte": {"setup": 5000.0, "mensalidade": 1990.0},
    "Mercado do Bairro": {"setup": 1500.0, "mensalidade": 500.0}
}

LIGHT = {
    "Básico": {"setup": 497.0, "mensalidade": 97.0},
    "Intermediário": {"setup": 997.0, "mensalidade": 197.0},
    "Completo": {"setup": 1997.0, "mensalidade": 297.0}
}

ESTADOS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
           "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]

# ========== FUNÇÕES ==========
def add_cliente(nome, modelo, plano, email, telefone, estado, afiliado=""):
    conn = sqlite3.connect("supersonic.db")
    c = conn.cursor()
    tabela = ALTO_TICKET if modelo == "Alto Ticket" else LIGHT
    setup = tabela[plano]["setup"]
    mensalidade = tabela[plano]["mensalidade"]
    cid = str(uuid.uuid4())
    c.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (cid, nome, modelo, plano, email, telefone, estado, setup, mensalidade,
               "Ativo", datetime.now().strftime("%Y-%m-%d"), afiliado))
    conn.commit()
    conn.close()
    return cid

def listar_clientes():
    conn = sqlite3.connect("supersonic.db")
    df = pd.read_sql_query("SELECT * FROM clientes ORDER BY data_cadastro DESC", conn)
    conn.close()
    return df

def calcular_mrr():
    conn = sqlite3.connect("supersonic.db")
    c = conn.cursor()
    c.execute("SELECT SUM(mensalidade) FROM clientes WHERE status='Ativo'")
    mrr = c.fetchone()[0] or 0.0
    conn.close()
    return mrr

def add_afiliado(nome, telefone, com_setup, com_mensal):
    conn = sqlite3.connect("supersonic.db")
    c = conn.cursor()
    aid = str(uuid.uuid4())
    c.execute("INSERT INTO afiliados VALUES (?,?,?,?,?,0,?)",
              (aid, nome, telefone, com_setup, com_mensal, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return aid

def listar_afiliados():
    conn = sqlite3.connect("supersonic.db")
    df = pd.read_sql_query("SELECT * FROM afiliados", conn)
    conn.close()
    return df

# ========== INTERFACE ==========
st.title("🚀 Supersonic V3 - Painel de Controle")
st.caption("Alto Ticket + Light | Controle de Clientes, MRR e Afiliados")

menu = st.sidebar.radio("Menu", [
    "Dashboard",
    "Cadastrar Cliente",
    "Clientes",
    "Afiliados / Closers",
    "Tabela de Preços",
    "Exportar Excel"
])

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

# DASHBOARD
if menu == "Dashboard":
    st.subheader("📊 Dashboard")
    mrr = calcular_mrr()
    df = listar_clientes()
    total = len(df)
    ativos = len(df[df["status"] == "Ativo"]) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("MRR (Receita Mensal)", f"R$ {mrr:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Clientes Ativos", ativos)
    c3.metric("Total Cadastrados", total)

    if total > 0:
        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Por Modelo")
            st.bar_chart(df.groupby("modelo").size())
        with col2:
            st.subheader("Por Estado")
            st.bar_chart(df.groupby("estado").size())

# CADASTRAR CLIENTE
elif menu == "Cadastrar Cliente":
    st.subheader("➕ Cadastrar Novo Cliente")
    modelo = st.radio("Modelo", ["Alto Ticket", "Light"])
    planos = list(ALTO_TICKET.keys()) if modelo == "Alto Ticket" else list(LIGHT.keys())

    with st.form("cadastro"):
        nome = st.text_input("Nome / Razão Social")
        plano = st.selectbox("Plano", planos)
        email = st.text_input("E-mail")
        telefone = st.text_input("Telefone")
        estado = st.selectbox("Estado", ESTADOS)
        afiliado = st.text_input("Afiliado / Closer (opcional)")
        if st.form_submit_button("Cadastrar Cliente"):
            if nome:
                add_cliente(nome, modelo, plano, email, telefone, estado, afiliado)
                st.success("Cliente cadastrado com sucesso!")
            else:
                st.error("Preencha o nome")

# CLIENTES
elif menu == "Clientes":
    st.subheader("👥 Clientes Cadastrados")
    df = listar_clientes()
    if len(df) > 0:
        st.dataframe(df[["nome", "modelo", "plano", "estado", "mensalidade", "status", "data_cadastro"]], use_container_width=True)
    else:
        st.info("Nenhum cliente ainda.")

# AFILIADOS
elif menu == "Afiliados / Closers":
    st.subheader("🤝 Afiliados e Closers")
    tab1, tab2 = st.tabs(["Cadastrar", "Lista"])
    with tab1:
        with st.form("afiliado"):
            nome = st.text_input("Nome")
            telefone = st.text_input("Telefone")
            com_setup = st.number_input("% Comissão Setup", value=10.0)
            com_mensal = st.number_input("% Comissão Mensalidade", value=5.0)
            if st.form_submit_button("Cadastrar"):
                if nome:
                    add_afiliado(nome, telefone, com_setup, com_mensal)
                    st.success("Afiliado cadastrado!")
    with tab2:
        df = listar_afiliados()
        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum afiliado ainda.")

# TABELA DE PREÇOS
elif menu == "Tabela de Preços":
    st.subheader("📋 Tabela de Preços")
    st.write("### Modelo Alto Ticket")
    dados1 = [{"Plano": k, "Setup": f"R$ {v['setup']:,.2f}", "Mensalidade": f"R$ {v['mensalidade']:,.2f}"} for k, v in ALTO_TICKET.items()]
    st.table(pd.DataFrame(dados1))
    st.write("### Modelo Light")
    dados2 = [{"Plano": k, "Setup": f"R$ {v['setup']:,.2f}", "Mensalidade": f"R$ {v['mensalidade']:,.2f}"} for k, v in LIGHT.items()]
    st.table(pd.DataFrame(dados2))

# EXPORTAR
elif menu == "Exportar Excel":
    st.subheader("📥 Exportar")
    df = listar_clientes()
    if len(df) > 0:
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("Baixar Clientes em Excel", buffer.getvalue(), "clientes.xlsx")
    else:
        st.info("Nenhum dado para exportar.")

st.write("---")
st.caption("Supersonic V3 | Login: admin | Senha: supersonic2026")
