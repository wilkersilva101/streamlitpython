import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os.path
import pandas as pd
import plotly.express as px
import logging

# Configurações da página
st.set_page_config(page_title="Lista de Servidores para Importação para o sistema pessoas TJPI", page_icon="📊")

# Título da aplicação
st.title("Servidores para Importação TJPI")

# Escopos necessários para acessar o Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Função para autenticar e obter credenciais
def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

# Autenticação
creds = get_credentials()
gc = gspread.authorize(creds)

# Função para carregar dados da planilha
def carregar_dados(sheet_name):
    worksheet = gc.open_by_key('16hzIW5ImASPiEIwvzgoQfFo1y-b2nYrK9rDyK4qTWUQ').worksheet(sheet_name)
    return pd.DataFrame(worksheet.get_all_records())

# Estilos CSS para o progresso circular
st.markdown("""
    <style>
        .circle-wrap {
            margin: 50px auto;
            width: 150px;
            height: 150px;
            background: #f7f7f7;
            border-radius: 50%;
            position: relative;
        }

        .circle-wrap .circle .mask,
        .circle-wrap .circle .fill {
            width: 150px;
            height: 150px;
            position: absolute;
            border-radius: 50%;
        }

        .circle-wrap .circle .mask {
            clip: rect(0px, 150px, 150px, 75px);
        }

        .circle-wrap .circle .fill {
            clip: rect(0px, 75px, 150px, 0px);
            background-color: #3498db;
        }

        .circle-wrap .circle .mask.full,
        .circle-wrap .circle .fill.fix {
            clip: rect(auto, auto, auto, auto);
        }

        .circle-wrap .inside-circle {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: #fff;
            line-height: 120px;
            text-align: center;
            margin-top: 15px;
            margin-left: 15px;
            position: absolute;
            z-index: 100;
            font-weight: 700;
            font-size: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Exibe o círculo de progresso e a porcentagem
progress_text = st.empty()
progress_text.markdown(
    '<div class="circle-wrap"><div class="circle"><div class="mask full"><div class="fill"></div></div><div class="mask half"><div class="fill"></div><div class="fill fix"></div></div></div><div class="inside-circle">0%</div></div>',
    unsafe_allow_html=True)

# Simula o carregamento dos dados com progresso circular
sheets = ['SERVIDORES', 'ESTAGIÁRIOS', 'ESTAGIÁRIOS NOVOS']
dfs = {}

for i, sheet_name in enumerate(sheets):
    dfs[sheet_name] = carregar_dados(sheet_name)

    # Atualiza a porcentagem de progresso e o CSS dinamicamente
    percent_complete = int(((i + 1) / len(sheets)) * 100)

    if percent_complete == 100:
        progress_text.markdown(f"""
        <style>
            .circle .mask.full .fill,
            .circle .mask.half .fill {{
                background-color: white;
            }}
            .inside-circle {{
                content: '100%';
            }}
        </style>
        <div class="circle-wrap">
            <div class="circle">
                <div class="mask full">
                    <div class="fill"></div>
                </div>
                <div class="mask half">
                    <div class="fill"></div>
                    <div class="fill fix"></div>
                </div>
            </div>
            <div class="inside-circle">{percent_complete}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        progress_text.markdown(f"""
        <style>
            .circle .mask.full .fill {{
                transform: rotate({(percent_complete / 100) * 180}deg);
            }}
            .circle .mask.half .fill {{
                transform: rotate({(percent_complete / 100) * 360}deg);
            }}
            .inside-circle {{
                content: '{percent_complete}%';
            }}
        </style>
        <div class="circle-wrap">
            <div class="circle">
                <div class="mask full">
                    <div class="fill"></div>
                </div>
                <div class="mask half">
                    <div class="fill"></div>
                    <div class="fill fix"></div>
                </div>
            </div>
            <div class="inside-circle">{percent_complete}%</div>
        </div>
        """, unsafe_allow_html=True)

# Remove a animação após o carregamento e exibe a mensagem de sucesso no centro da tela
st.markdown('<style>.loading-text {text-align: center;}</style>', unsafe_allow_html=True)
st.markdown('<div class="loading-text">Dados carregados com sucesso!</div>', unsafe_allow_html=True)

# Função para filtrar registros
def filtrar_registros(df):
    return df[
        ((df['Resolvido?'].isnull()) | (df['Resolvido?'] == '') | (df['Resolvido?'] == ' ')) &
        (df['Pendência'].str.lower() == 'deferido')
        ]

# Aplicar filtros
df_servidores_vazio = filtrar_registros(dfs['SERVIDORES'])
df_estagiarios_novos_vazio = filtrar_registros(dfs['ESTAGIÁRIOS NOVOS'])
df_estagiarios_vazio = filtrar_registros(dfs['ESTAGIÁRIOS'])

# Filtrar registros onde 'Pendência' é diferente de 'DEFERIDO' ou 'deferido' e 'Resolvido?' é diferente de 'sim'
df_servidores_vazio_diferente = dfs['SERVIDORES'][
    (~dfs['SERVIDORES']['Pendência'].str.lower().isin(['deferido'])) &
    (~dfs['SERVIDORES']['Resolvido?'].str.lower().isin(['sim']))
    ]

# Estilos CSS
st.markdown("""
<style>
    .header {
        padding: 20px;
        background-color: #f8f9fa;
        border-bottom: 1px solid #e9ecef;
        text-align: center;
    }
    .footer {
        padding: 10px;
        background-color: #f8f9fa;
        border-top: 1px solid #e9ecef;
        text-align: center;
        margin-top: 20px;
    }
    .dataframe {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Função para exibir DataFrame com total de registros
def exibir_dataframe_com_total(df, titulo):
    st.markdown(f'<div class="header">{titulo}</div>', unsafe_allow_html=True)
    st.dataframe(df)
    st.write(f"Total de registros: {len(df)}")

# Exibir os DataFrames filtrados com total de registros
exibir_dataframe_com_total(df_servidores_vazio, "SERVIDORES")
exibir_dataframe_com_total(df_estagiarios_novos_vazio, "ESTAGIÁRIOS NOVOS")
exibir_dataframe_com_total(df_estagiarios_vazio, "ESTAGIÁRIOS")
exibir_dataframe_com_total(df_servidores_vazio_diferente, "Servidores com Pendências")

# Contagem de importações e gráfico
st.markdown("<h2 style='text-align: center;'>Importações</h2>", unsafe_allow_html=True)

# Função para filtrar registros com "Resolvido?" igual a "sim"
def filtrar_registros_resolvidos(df):
    return df[df['Resolvido?'].str.lower() == 'sim']

# Aplicar filtro para registros resolvidos
df_servidores_resolvidos = filtrar_registros_resolvidos(dfs['SERVIDORES'])
df_estagiarios_novos_resolvidos = filtrar_registros_resolvidos(dfs['ESTAGIÁRIOS NOVOS'])
df_estagiarios_resolvidos = filtrar_registros_resolvidos(dfs['ESTAGIÁRIOS'])

# Dados para o gráfico
importacoes_resolvidas = {
    "SERVIDORES": len(df_servidores_resolvidos),
    "ESTAGIÁRIOS NOVOS": len(df_estagiarios_novos_resolvidos),
    "ESTAGIÁRIOS": len(df_estagiarios_resolvidos),
    "Servidores com Pendências": len(df_servidores_vazio_diferente)
}

# Criar DataFrame para o gráfico
df_importacoes_resolvidas = pd.DataFrame(list(importacoes_resolvidas.items()), columns=["Categoria", "Quantidade"])

# Definir cores para cada categoria
cores = {
    "SERVIDORES": "blue",
    "ESTAGIÁRIOS NOVOS": "green",
    "ESTAGIÁRIOS": "orange",
    "Servidores com Pendências": "red"
}

# Gráfico de barras
fig = px.bar(df_importacoes_resolvidas, x="Categoria", y="Quantidade", text="Quantidade",
             title="Importações por Categoria", color="Categoria", color_discrete_map=cores)
fig.update_traces(texttemplate='%{text}', textposition='outside')
st.plotly_chart(fig)

# Rodapé
st.markdown('<div class="footer">Desenvolvido pela Secretaria de Tecnologia da Informação e Comunicação - STIC</div>',
            unsafe_allow_html=True)

# Configuração do logging
logging.basicConfig(level=logging.INFO)