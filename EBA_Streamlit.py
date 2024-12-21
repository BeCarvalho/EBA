import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da conexão com o Supabase
url: str = "https://otzttzzotxkepwqdhsnr.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enR0enpvdHhrZXB3cWRoc25yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzA1OTAzOTQsImV4cCI6MjA0NjE2NjM5NH0.tD2MZCfdUmPxoMNN9i_y3WspqYkEqFZtmYUhpODCNfU"
supabase: Client = create_client(url, key)

# Autenticação do usuário
user_id = "1ec57c7e-879a-4485-a373-6cc7fc1b6153"
user = supabase.auth.sign_in_with_password({"email": "ebenezercarvalho@gmail.com", "password": "0205"})

# Configuração do menu lateral
menu = st.sidebar.radio("Menu", options=["Inserir Dados", "Dashboard"])

if menu == "Inserir Dados":
    st.title("Análise de Esporos de Bactérias Aeróbias")

    # Formulário para inserção de dados
    with st.form("eba_form"):
        st.subheader("Inserir Novo Registro")
        ponto = st.selectbox(
            "Ponto de Coleta",
            options=["ALCAP", "NISCAP", "ALF1", "ALF2", "ALF3", "ALF4", "ALF5", "ALF6", "NISF1"]
        )
        dilui = st.number_input("Diluição", min_value=0.0, format="%.2f")
        cont = st.number_input("Contagem de colônias na placa", min_value=0, step=1)

        submitted = st.form_submit_button("Inserir Dados")

        if submitted:
            # Calcular o resultado total de colônias em 100ml
            if dilui > 0:
                result = int((100 * cont) / dilui)  # Convertendo o resultado para inteiro
            else:
                result = 0  # Evita divisão por zero caso a diluição seja zero

            # Inserir dados na tabela EBA
            data = {
                "ponto": ponto,
                "dilui": dilui,
                "cont": cont,
                "result": result,  # Inserindo o resultado como número inteiro
            }

            try:
                response = supabase.table("eba").insert(data).execute()
                if response.data:
                    st.success("Dados inseridos com sucesso!")
                else:
                    st.error("Erro ao inserir dados. Por favor, tente novamente.")
            except Exception as e:
                st.error(f"Erro ao inserir dados: {str(e)}")

    # Exibir os dados mais recentes em forma de tabela
    st.subheader("Registros Recentes")
    try:
        response = supabase.table("eba").select("*").order('created_at', desc=True).limit(5).execute()
        if response.data:
            # Converter a resposta em um formato de DataFrame (pandas) para exibir como tabela
            df = pd.DataFrame(response.data)

            # Formatando os valores numéricos para 2 casas decimais com vírgula (exceto resultado)
            df['dilui'] = df['dilui'].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notnull(x) else "")
            df['cont'] = df['cont'].apply(lambda x: f"{x}".replace('.', ',') if pd.notnull(x) else "")
            df['result'] = df['result'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "")  # Exibindo como inteiro ou vazio

            # Renomeando as colunas da tabela
            df = df[['ponto', 'dilui', 'cont', 'result']]
            df.columns = ['Ponto', 'Diluição', 'Contagem', 'Resultado']

            # Exibe a tabela formatada
            st.table(df)
        else:
            st.info("Nenhum registro encontrado.")
    except Exception as e:
        st.error(f"Erro ao buscar registros: {str(e)}")

elif menu == "Dashboard":
    st.title("Dashboard de Análise")

    # Adicionar seletor para o ponto de coleta
    ponto_selecionado = st.selectbox(
        "Selecione o ponto de coleta",
        options=["ALCAP", "NISCAP", "ALF1", "ALF2", "ALF3", "ALF4", "ALF5", "ALF6", "NISF1"]
    )

    # Filtrar os registros para o ponto selecionado
    try:
        response = supabase.table("eba").select("*").eq("ponto", ponto_selecionado).execute()
        if response.data:
            df = pd.DataFrame(response.data)

            # Garantir que as colunas numéricas estejam no tipo correto
            df['result'] = pd.to_numeric(df['result'], errors='coerce')
            df['created_at'] = pd.to_datetime(df['created_at'])

            # Ordenar por data para o gráfico
            df = df.sort_values(by='created_at')

            # Cálculo dos limites de controle
            mean_result = df['result'].mean()
            std_dev = df['result'].std()
            ucl = mean_result + 3 * std_dev  # Limite de Controle Superior
            lcl = mean_result - 3 * std_dev  # Limite de Controle Inferior

            # Criar carta de controle (gráfico de Shewhart)
            fig = go.Figure()

            # Adicionar os resultados como uma linha
            fig.add_trace(go.Scatter(x=df['created_at'], y=df['result'], mode='lines+markers', name='Resultado'))

            # Adicionar linha central (média)
            fig.add_trace(go.Scatter(x=df['created_at'], y=[mean_result] * len(df), mode='lines', name='Média', line=dict(color='blue', dash='dash')))

            # Adicionar limites de controle superior e inferior
            fig.add_trace(go.Scatter(x=df['created_at'], y=[ucl] * len(df), mode='lines', name='UCL (3σ)', line=dict(color='red', dash='dot')))
            fig.add_trace(go.Scatter(x=df['created_at'], y=[lcl] * len(df), mode='lines', name='LCL (3σ)', line=dict(color='red', dash='dot')))

            # Configuração do layout
            fig.update_layout(
                title=f'Carta de Controle de {ponto_selecionado}',
                xaxis_title='Data',
                yaxis_title='Resultado (colônias/100ml)',
                legend_title='Legenda',
                template='plotly_white'
            )

            st.plotly_chart(fig)
        else:
            st.info(f"Nenhum registro encontrado para {ponto_selecionado}.")
    except Exception as e:
        st.error(f"Erro ao buscar registros: {str(e)}")
