import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os.path
import pandas as pd
import logging
from gspread.exceptions import APIError, WorksheetNotFound, SpreadsheetNotFound

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)

# 1. Configuração Inicial
st.set_page_config(page_title="Sistema de Importação TJPI", page_icon="📊")
st.title("Importação de Servidores")

# 2. Autenticação
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly "]

def get_credentials():
    """Obtém ou atualiza as credenciais OAuth2."""
    creds = None
    try:
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists("client_secret.json"):
                    st.error("Arquivo client_secret.json não encontrado!")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds
    except Exception as e:
        st.error(f"Erro na autenticação: {str(e)}")
        return None

creds = get_credentials()
if not creds:
    st.stop()

try:
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"Erro na autorização do gspread: {str(e)}")
    st.stop()

# 3. Configuração da Planilha
SHEET_ID = '16hzIW5ImASPiEIwvzgoQfFo1y-b2nYrK9rDyK4qTWUQ'

# 4. Listar todas as planilhas disponíveis
def listar_todas_planilhas():
    """Lista todas as abas (worksheets) da planilha"""
    try:
        spreadsheet = gc.open_by_key(SHEET_ID)
        return [ws.title for ws in spreadsheet.worksheets()]
    except SpreadsheetNotFound:
        st.error(f"Planilha com ID {SHEET_ID} não encontrada!")
        return []
    except Exception as e:
        st.error(f"Erro ao listar planilhas: {str(e)}")
        return []

planilhas_disponiveis = listar_todas_planilhas()
if not planilhas_disponiveis:
    st.stop()

# Exibir as planilhas disponíveis
st.markdown("### 🗂️ Abas disponíveis no Google Sheets:")
for nome in planilhas_disponiveis:
    st.code(nome)

# Mostrar quais abas foram realmente encontradas no ambiente de produção
st.markdown("### 📂 Abas encontradas na planilha (exatamente como estão):")
st.write(planilhas_disponiveis)

# 5. Planilhas que queremos usar
PLANILHAS_DESEJADAS = ['SERVIDORES 2025', 'ESTAGIÁRIOS NOVOS', 'REFAZER ESOCIAL']

# Filtrar apenas as planilhas que existem (com comparação case-insensitive e sem espaço extra)
planilhas_para_carregar = []
planilhas_ignoradas = []

for sheet_name in PLANILHAS_DESEJADAS:
    found = False
    normalized = sheet_name.strip().lower()
    for ws_title in planilhas_disponiveis:
        if ws_title.strip().lower() == normalized:
            planilhas_para_carregar.append(ws_title)
            found = True
            break
    if not found:
        planilhas_ignoradas.append(sheet_name)

# Mostrar quais planilhas serão carregadas
st.markdown("### 📥 Abas selecionadas para importação:")
for nome in planilhas_para_carregar:
    st.success(f"✔️ {nome}")

# Avisar sobre planilhas desejadas que não existem
if planilhas_ignoradas:
    st.warning(f"As seguintes planilhas foram ignoradas porque não foram encontradas: {', '.join(planilhas_ignoradas)}")

if not planilhas_para_carregar:
    st.error("Nenhuma das planilhas desejadas foi encontrada!")
    st.stop()

# 6. Função para carregar dados com tratamento de erros
def carregar_planilha_segura(sheet_name):
    """Carrega uma aba com segurança, ignorando diferenças mínimas de nome"""
    try:
        logging.debug(f"Tentando carregar a planilha: {sheet_name}")
        spreadsheet = gc.open_by_key(SHEET_ID)

        # Normaliza o nome da aba desejada
        sheet_name_normalized = sheet_name.strip().lower()

        # Busca pela aba com comparação case-insensitive e sem espaços extras
        worksheet = None
        for ws in spreadsheet.worksheets():
            if ws.title.strip().lower() == sheet_name_normalized:
                worksheet = ws
                st.info(f"Aba '{sheet_name}' encontrada com título exato: '{ws.title}'")
                break

        if not worksheet:
            st.warning(f"Aba '{sheet_name}' não encontrada após revalidação.")
            return pd.DataFrame()

        data = worksheet.get_all_records()
        return pd.DataFrame(data)

    except WorksheetNotFound:
        st.warning(f"Aba '{sheet_name}' não encontrada (WorksheetNotFound).")
        return pd.DataFrame()
    except APIError as api_err:
        st.error(f"Erro de API ao carregar '{sheet_name}': {api_err.response.text}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro desconhecido ao carregar '{sheet_name}': {str(e)}")
        return pd.DataFrame()

# 7. Carregar dados
dfs = {}
for sheet_name in planilhas_para_carregar:
    with st.spinner(f"Carregando {sheet_name}..."):
        df = carregar_planilha_segura(sheet_name)
        if not df.empty:
            dfs[sheet_name] = df

if not dfs:
    st.error("Nenhuma planilha foi carregada com sucesso!")
    st.stop()

st.success("Dados carregados com sucesso!")

# 8. Função para processar dados
def processar_dados(df):
    """Filtra registros com base em colunas específicas"""
    if df.empty:
        return df

    colunas_necessarias = ['Resolvido?', 'Pendência']
    for col in colunas_necessarias:
        if col not in df.columns:
            st.warning(f"Coluna obrigatória '{col}' não encontrada na planilha!")
            return pd.DataFrame()

    try:
        return df[
            (df['Resolvido?'].isna() | (df['Resolvido?'].astype(str).str.strip() == '')) &
            (df['Pendência'].astype(str).str.strip().str.lower() == 'deferido')
        ]
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return pd.DataFrame()

# 9. Exibir resultados
st.header("Resultados")
for sheet_name, df in dfs.items():
    st.subheader(sheet_name)
    df_processado = processar_dados(df)
    if not df_processado.empty:
        st.dataframe(df_processado)
        st.write(f"Total: {len(df_processado)} registros")
    else:
        st.warning("Nenhum registro encontrado após filtragem.")

# 10. Rodapé
st.markdown("---")
st.markdown("**Desenvolvido pela STIC**")