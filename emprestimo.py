import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Carregar a configuração de autenticação de um arquivo YAML
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
    config["preauthorized"],
)

# Tela de login
name, authentication_status, username = authenticator.login(
    key="Login", location="main"
)

if authentication_status is True:
    # Função para conectar ao banco de dados
    def conectar_banco():
        conn = sqlite3.connect("emprestimo.db")
        return conn

    # Função para criar as tabelas no banco de dados
    def criar_tabelas():
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pagamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                valor REAL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                valor_emprestimo REAL,
                taxa_juros REAL,
                quantidade_meses INTEGER
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_configuracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_modificacao TEXT,
                valor_emprestimo REAL,
                taxa_juros REAL,
                quantidade_meses INTEGER
            )
        """
        )
        conn.commit()
        conn.close()

    # Função para inserir configuração no banco de dados
    def inserir_configuracao(valor_emprestimo, taxa_juros, quantidade_meses):
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO configuracoes (valor_emprestimo, taxa_juros, quantidade_meses) VALUES (?, ?, ?)",
            (valor_emprestimo, taxa_juros, quantidade_meses),
        )
        conn.commit()
        conn.close()

    # Função para obter a configuração atual
    def obter_configuracao():
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM configuracoes ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row

    # Função para editar configuração
    def editar_configuracao(
        id, valor_emprestimo, taxa_juros, quantidade_meses
    ):
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE configuracoes SET valor_emprestimo = ?, taxa_juros = ?, quantidade_meses = ? WHERE id = ?",
            (valor_emprestimo, taxa_juros, quantidade_meses, id),
        )
        conn.commit()
        conn.close()

    # Função para inserir pagamento no banco de dados
    def inserir_pagamento(data, valor):
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pagamentos (data, valor) VALUES (?, ?)", (data, valor)
        )
        conn.commit()
        conn.close()

    # Função para obter todos os pagamentos
    def obter_pagamentos():
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pagamentos")
        rows = cursor.fetchall()
        conn.close()
        return rows

    # Função para editar pagamento
    def editar_pagamento(id, data, valor):
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pagamentos SET data = ?, valor = ? WHERE id = ?",
            (data, valor, id),
        )
        conn.commit()
        conn.close()

    # Função para excluir pagamento
    def excluir_pagamento(id):
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pagamentos WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    # Criar as tabelas no banco de dados
    criar_tabelas()

    # Função para calcular o saldo devedor e valor pago
    def calcular_emprestimo(valor, taxa, meses):
        taxa_mensal = taxa / 100  # Taxa de 2% ao mês
        parcela = (
            valor
            * (taxa_mensal * (1 + taxa_mensal) ** meses)
            / ((1 + taxa_mensal) ** meses - 1)
        )
        saldo_devedor = valor
        total_juros = 0
        for _ in range(meses):
            juros = saldo_devedor * taxa_mensal
            amortizacao = parcela - juros
            saldo_devedor -= amortizacao
            total_juros += juros
        valor_final = valor + total_juros
        return parcela, valor_final

    # Função para formatar valores
    def formatar_valores(valor):
        return (
            f"{valor:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # Função para calcular saldo devedor e valor pago
    def atualizar_valores(
        df_pagamentos, valor_emprestimo, taxa_juros, quantidade_meses
    ):
        valor_pago = df_pagamentos["Valor"].sum()
        parcela, valor_final = calcular_emprestimo(
            valor_emprestimo, taxa_juros, quantidade_meses
        )
        saldo_restante = valor_final - valor_pago
        return valor_pago, saldo_restante, parcela

    # Título do App
    st.markdown(
        "<h1 style='text-align: center;'>Gerenciador de Empréstimos</h1>",
        unsafe_allow_html=True,
    )

    # Obter a configuração atual do banco de dados
    configuracao = obter_configuracao()

    if configuracao:
        configuracao_id, valor_emprestimo, taxa_juros, quantidade_meses = (
            configuracao
        )
    else:
        valor_emprestimo = st.number_input(
            "Valor do Empréstimo", min_value=0.0, value=10000.0, step=100.0
        )
        taxa_juros = st.number_input(
            "Taxa de Juros Anual (%)", min_value=0.0, value=5.0, step=0.1
        )
        quantidade_meses = st.number_input(
            "Quantidade de Meses", min_value=1, value=12, step=1
        )
        if st.button("Salvar Configuração"):
            inserir_configuracao(
                valor_emprestimo, taxa_juros, quantidade_meses
            )
            st.experimental_rerun()

    if configuracao:
        st.subheader("Configuração Atual")
        st.write(
            f"Valor do Empréstimo: R$ {formatar_valores(valor_emprestimo)}"
        )
        st.write(f"Taxa de Juros Anual: {taxa_juros}%")
        st.write(f"Quantidade de Meses: {quantidade_meses}")

        if st.button("Editar Configuração"):
            st.session_state.show_config_modal = True

    # Sidebar para registrar pagamentos
    st.sidebar.header("Registrar Pagamento")

    # Input de data e valor do pagamento
    data_pagamento = st.sidebar.text_input(
        "Data do Pagamento (dd/mm/yyyy)", datetime.now().strftime("%d/%m/%Y")
    )
    valor_pagamento = st.sidebar.number_input(
        "Valor do Pagamento", min_value=0.0, step=100.0
    )

    # Botão para adicionar novo pagamento
    if st.sidebar.button("Adicionar Pagamento"):
        try:
            data_pagamento_dt = datetime.strptime(data_pagamento, "%d/%m/%Y")
            data_pagamento_str = data_pagamento_dt.strftime("%Y-%m-%d")
            inserir_pagamento(data_pagamento_str, valor_pagamento)
            st.success("Pagamento adicionado com sucesso!")
        except ValueError:
            st.error("Por favor, insira uma data válida no formato dd/mm/yyyy")
        except Exception as e:
            st.error(f"Erro ao adicionar pagamento: {e}")

    # Obter pagamentos do banco de dados
    pagamentos = obter_pagamentos()
    pagamentos_df = pd.DataFrame(pagamentos, columns=["ID", "Data", "Valor"])
    pagamentos_df["Data"] = pd.to_datetime(pagamentos_df["Data"])

    # Atualizar valores pagos e saldo devedor
    valor_pago, saldo_restante, valor_parcela = atualizar_valores(
        pagamentos_df, valor_emprestimo, taxa_juros, quantidade_meses
    )

    # Exibir valores pagos, saldo devedor, quantidade de meses e taxa de juros em cards no topo da tela
    st.markdown(
        "<h3 style='text-align: center;'>Situação Atual</h3>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Valor Pago", value=f"R$ {formatar_valores(valor_pago)}"
        )

    with col2:
        st.metric(
            label="Saldo Devedor",
            value=f"R$ {formatar_valores(saldo_restante)}",
        )

    with col3:
        st.metric(
            label="Valor da Parcela",
            value=f"R$ {formatar_valores(valor_parcela)}",
        )

    # Exibir a tabela de pagamentos
    st.markdown(
        "<h3 style='text-align: center;'>Histórico de Pagamentos</h3>",
        unsafe_allow_html=True,
    )

    for i, row in pagamentos_df.iterrows():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            st.write(row["Data"].strftime("%d/%m/%Y"))
        with col2:
            st.write(f"R$ {formatar_valores(row['Valor'])}")
        with col3:
            if st.button("Editar", key=f"edit_{row['ID']}"):
                st.session_state.edit_index = row["ID"]
                st.session_state.show_modal = True
        with col4:
            if st.button("Excluir", key=f"delete_{row['ID']}"):
                excluir_pagamento(row["ID"])
                st.experimental_rerun()

    # Modal para editar o pagamento
    if "show_modal" in st.session_state and st.session_state.show_modal:
        with st.form(key="edit_form"):
            st.write("Editar Pagamento")
            edit_row = pagamentos_df[
                pagamentos_df["ID"] == st.session_state.edit_index
            ]
            new_data = st.text_input(
                "Nova Data",
                edit_row["Data"].dt.strftime("%d/%m/%Y").values[0],
            )
            new_valor = st.number_input(
                "Novo Valor",
                value=edit_row["Valor"].values[0],
                min_value=0.0,
                step=100.0,
            )
            save_button = st.form_submit_button("Salvar")

            if save_button:
                try:
                    new_data_dt = datetime.strptime(new_data, "%d/%m/%Y")
                    new_data_str = new_data_dt.strftime("%Y-%m-%d")
                    editar_pagamento(
                        st.session_state.edit_index, new_data_str, new_valor
                    )
                    st.session_state.show_modal = False
                    st.experimental_rerun()
                except ValueError:
                    st.error(
                        "Por favor, insira uma data válida no formato dd/mm/yyyy"
                    )
                except Exception as e:
                    st.error(f"Erro ao editar pagamento: {e}")

    # Modal para editar a configuração
    if (
        "show_config_modal" in st.session_state
        and st.session_state.show_config_modal
    ):
        with st.form(key="edit_config_form"):
            st.write("Editar Configuração")
            new_valor_emprestimo = st.number_input(
                "Novo Valor do Empréstimo",
                min_value=0.0,
                value=valor_emprestimo,
                step=100.0,
            )
            new_taxa_juros = st.number_input(
                "Nova Taxa de Juros Anual (%)",
                min_value=0.0,
                value=taxa_juros,
                step=0.1,
            )
            new_quantidade_meses = st.number_input(
                "Nova Quantidade de Meses",
                min_value=1,
                value=quantidade_meses,
                step=1,
            )
            save_config_button = st.form_submit_button("Salvar")

            if save_config_button:
                try:
                    editar_configuracao(
                        configuracao_id,
                        new_valor_emprestimo,
                        new_taxa_juros,
                        new_quantidade_meses,
                    )
                    st.session_state.show_config_modal = False
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erro ao editar configuração: {e}")

    authenticator.logout(key="Logout", location="sidebar")

elif authentication_status is False:
    st.error("Usuário ou senha incorretos")

elif authentication_status is None:
    st.warning("Por favor, insira seu nome de usuário e senha")
