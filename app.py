import streamlit as st
from config import get_projeto_config
from utils_dados import get_all_issues 
from view_datas_sprints import sprint_tab
from view_burndown import burndown_tab
from view_visao_geral import dados_gerais
from view_todas_issues import all_issues_tab
from view_performance_time import desempenho_tab
from view_entregas_dev import entregas_tab
from view_metricas_projeto import entregas_projeto_tab
from utils_performance import cache_jira_data, measure_performance, show_performance_metrics

st.set_page_config(page_title="Métricas Jira", layout="wide", page_icon="📊")

st.sidebar.title("Painel de Controle")
projeto_selecionado = st.sidebar.selectbox("Selecione o Projeto", ["PROJETO 1", "PROJETO 2"])

jira_url, board_id, headers = get_projeto_config(projeto_selecionado)

@measure_performance
@cache_jira_data(ttl=600)
def load_all_data(_jira_url, _board_id, _headers):
    return get_all_issues(_jira_url, _board_id, _headers)

cache_key = f"jira_data_{projeto_selecionado}"

if cache_key not in st.session_state:
    with st.spinner(f"🔄 Carregando dados do {projeto_selecionado}..."):
        try:
            st.session_state[cache_key] = load_all_data(jira_url, board_id, headers)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            st.stop()

all_issues_data = st.session_state[cache_key]

pagina = st.sidebar.radio(
    "Selecione a Página:",
    options=[
        "📊 Dados Gerais",
        "📋 Datas das Sprints", 
        "📉 Burndown Atual",
        "📊 Desempenho por Sprint",
        "🚀 Desempenho por Desenvolvedor",
        "📦 Entregas do Projeto",
        "📈 Todas Issues do Projeto",
    ]
)

st.sidebar.markdown("---")
show_performance_metrics()

if st.sidebar.button("🔄 Atualizar Cache"):
    cache_key = f"jira_data_{projeto_selecionado}"
    if cache_key in st.session_state:
        del st.session_state[cache_key]
    if 'jira_cache' in st.session_state:
        st.session_state.jira_cache = {}
    st.rerun()

if pagina == "📊 Dados Gerais":
    dados_gerais(jira_url, board_id, headers, all_issues_data)

elif pagina == "📋 Datas das Sprints":
    sprint_tab(jira_url, board_id, headers)

elif pagina == "📉 Burndown Atual":
    burndown_tab(jira_url, board_id, headers)

elif pagina == "📊 Desempenho por Sprint":
    desempenho_tab(jira_url, board_id, headers)

elif pagina == "🚀 Desempenho por Desenvolvedor":
    entregas_tab(jira_url, board_id, headers, all_issues_data)

elif pagina == "📦 Entregas do Projeto":
    entregas_projeto_tab(jira_url, board_id, headers)

elif pagina == "📈 Todas Issues do Projeto":
    all_issues_tab(jira_url, board_id, headers, all_issues_data)