import streamlit as st
import pandas as pd
import plotly.express as px
from utils_dados import (
    get_all_issues,
    count_bugs,
    normalizar_primeiro_nome,
    construir_mapa_dev_mais_recente,
)

def entregas_tab(jira_url, board_id, headers, all_issues_data=None):
    st.header("🚀 Análise de Entregas por Desenvolvedor")

    try:
        if all_issues_data is not None:
            issues = all_issues_data
        else:
            issues = get_all_issues(jira_url, board_id, headers)
    except Exception as e:
        st.error(f"Erro ao buscar issues: {e}")
        return

    if not issues:
        st.warning("Nenhuma issue encontrada.")
        return

    dados_entregas = processar_dados_entregas(issues)

    if dados_entregas.empty:
        st.warning("Nenhuma issue entregue encontrada.")
        return

    st.subheader("🔧 Filtros")
    with st.container():
        col1, col2, col3 = st.columns(3)

        with col1:
            sprints_disponiveis = sorted(dados_entregas['Sprint'].dropna().unique())
            sprint_selecionada = st.selectbox(
                "Sprint",
                options=["Todas"] + sprints_disponiveis,
                index=0
            )

        with col2:
            devs_disponiveis = sorted(dados_entregas['Desenvolvedor'].unique())
            devs_selecionados = st.multiselect(
                "Desenvolvedores",
                options=devs_disponiveis,
                default=devs_disponiveis
            )

        with col3:
            tipos_disponiveis = sorted(dados_entregas['Tipo'].unique())
            tipos_selecionados = st.multiselect(
                "Tipos de Issue",
                options=tipos_disponiveis,
                default=tipos_disponiveis
            )

    dados_filtrados = dados_entregas.copy()
    dados_filtrados = dados_filtrados[
        (dados_filtrados['Desenvolvedor'].isin(devs_selecionados)) &
        (dados_filtrados['Tipo'].isin(tipos_selecionados))
    ]
    if sprint_selecionada != "Todas":
        dados_filtrados = dados_filtrados[dados_filtrados['Sprint'] == sprint_selecionada]

    if dados_filtrados.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados.")
        return

    st.subheader("📊 Métricas Gerais")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_entregas = len(dados_filtrados)
        st.metric("Total de Entregas", total_entregas)

    with col2:
        devs_ativos = dados_filtrados['Desenvolvedor'].nunique()
        st.metric("Desenvolvedor(es) Ativo(s) no Filtro", devs_ativos)

    with col3:
        media_entregas_dev = total_entregas / devs_ativos if devs_ativos > 0 else 0
        st.metric("Média de Entregas por Desenvolvedor", int(media_entregas_dev))

    with col4:
        dias = (dados_filtrados['Data Entrega'].max() - dados_filtrados['Data Entrega'].min()).days + 1
        entregas_dia = total_entregas / dias if dias > 0 else 0
        st.metric("Entrega(s) por Dia", int(entregas_dia))

    with col5:
        total_bugs = dados_filtrados['Qtd Bugs'].sum()
        st.metric("Total de Bugs durante Desenvolvimento", total_bugs)

    st.subheader("👨‍💻 Total de Entregas por Desenvolvedor")
    fig_entregas_dev = criar_grafico_entregas_por_dev(dados_filtrados)
    st.plotly_chart(fig_entregas_dev, width="stretch", theme="streamlit")

    if total_bugs > 0:
        st.subheader("Índice de Retrabalho (Bugs) por Desenvolvedor")
        fig_bugs_dev = criar_grafico_bugs_por_dev(dados_filtrados)
        if fig_bugs_dev:
            st.plotly_chart(fig_bugs_dev, width="stretch", theme="streamlit")
        else:
            st.info("Nenhum bug associado aos desenvolvedores filtrados.")
    else:
        st.info("🎉 Nenhum bug identificado nas entregas filtradas!")

    st.subheader("📈 Entregas por Tipo de Issue")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "User Stories",
        "Melhorias",
        "Tasks",
        "Problemas",
        "Correção"
    ])

    with tab1:
        mostrar_grafico_tipo(dados_filtrados, "História", "User Stories")
    with tab2:
        mostrar_grafico_tipo(dados_filtrados, "Melhoria", "Melhorias")
    with tab3:
        mostrar_grafico_tipo(dados_filtrados, "Tarefa", "Tasks")
    with tab4:
        mostrar_grafico_tipo(dados_filtrados, "Problema", "Problemas")
    with tab5:
        mostrar_grafico_tipo(dados_filtrados, "Correção", "Correções")

    st.subheader("📅 Evolução Temporal das Entregas")
    fig_evolucao = criar_grafico_evolucao_temporal(dados_filtrados)
    st.plotly_chart(fig_evolucao, use_container_width=True)
    
    st.subheader("📋 Detalhamento das Entregas")
    col1, _ = st.columns(2)
    with col1:
        ordenacao = st.selectbox(
            "Ordenar por",
            options=[
                'Data Entrega (Mais Recente)',
                'Data Entrega (Mais Antiga)',
                'Desenvolvedor',
                'Tipo',
                'Qtd Bugs'
            ]
        )

    if ordenacao == 'Data Entrega (Mais Recente)':
        dados_ordenados = dados_filtrados.sort_values('Data Entrega', ascending=False)
    elif ordenacao == 'Data Entrega (Mais Antiga)':
        dados_ordenados = dados_filtrados.sort_values('Data Entrega', ascending=True)
    elif ordenacao == 'Desenvolvedor':
        dados_ordenados = dados_filtrados.sort_values('Desenvolvedor')
    elif ordenacao == 'Qtd Bugs':
        dados_ordenados = dados_filtrados.sort_values('Qtd Bugs', ascending=False)
    else:
        dados_ordenados = dados_filtrados.sort_values('Tipo')

    st.dataframe(dados_ordenados, use_container_width=True, height=400)

def processar_dados_entregas(issues):
    dados = []

    for issue in issues:
        fields = issue.get('fields', {})

        status = (fields.get('status') or {}).get('name', '').lower()
        status_category = (fields.get('status') or {}).get('statusCategory', {}).get('name', '').lower()

        is_entregue = (
            'done' in status_category or
            'concluído' in status or
            'fechado' in status or
            'aprovado' in status or
            'resolvido' in status
        )

        if is_entregue:
            resolution_date = fields.get('resolutiondate')
            if resolution_date:
                data_entrega = pd.to_datetime(resolution_date).tz_convert(None)
            else:
                data_entrega = pd.to_datetime(fields.get('updated')).tz_convert(None) if fields.get('updated') else pd.NaT

            assignee = fields.get('assignee', {})
            dev_original = assignee.get('displayName', 'Não atribuído') if assignee else 'Não atribuído'

            issue_type = fields.get('issuetype', {}).get('name', 'Desconhecido')

            subtasks = fields.get('subtasks', [])
            qtd_bugs = count_bugs(subtasks)

            sprint_field = fields.get('customfield_10020')
            sprints = []
            if isinstance(sprint_field, list):
                sprints = [s.get('name', 'Não atribuído') for s in sprint_field if isinstance(s, dict)]
            elif isinstance(sprint_field, dict):
                sprints = [sprint_field.get('name', 'Não atribuído')]
            if not sprints:
                sprints = ['Não atribuído']

            for sprint in sprints:
                dados.append({
                    'Chave': issue.get('key'),
                    'Resumo': fields.get('summary', ''),
                    'Tipo': issue_type,
                    'Desenvolvedor': dev_original,
                    'Sprint': sprint,
                    'Status': fields.get('status', {}).get('name', ''),
                    'Data Entrega': data_entrega,
                    'Data Criação': pd.to_datetime(fields.get('created')).tz_convert(None) if fields.get('created') else pd.NaT,
                    'Tempo Total de Resolução (dias)': (
                        (data_entrega - pd.to_datetime(fields.get('created')).tz_convert(None)).days
                        if fields.get('created') and pd.notna(data_entrega)
                        else None
                    ),
                    'Qtd Bugs': qtd_bugs
                })

    df = pd.DataFrame(dados)

    if df.empty:
        return df

    df["Primeiro nome"] = df["Desenvolvedor"].apply(normalizar_primeiro_nome)
    mapa_dev = construir_mapa_dev_mais_recente(df, "Desenvolvedor", "Data Entrega")
    df["Desenvolvedor"] = df["Primeiro nome"].map(mapa_dev).fillna(df["Primeiro nome"])

    return df


def criar_grafico_entregas_por_dev(dados):
    entregas_por_dev = dados.groupby('Desenvolvedor').size().sort_values(ascending=False)
    
    fig = px.bar(
        x=entregas_por_dev.index,
        y=entregas_por_dev.values,
        title="Produtividade: Volume Total de Entregas<br><sup>Itens concluídos (Done) por responsável</sup>",
        labels={'x': 'Desenvolvedor', 'y': 'Número de Entregas'}
    )
    fig.update_layout(xaxis_tickangle=-45, showlegend=False, height=400)
    return fig


def criar_grafico_bugs_por_dev(dados):
    bugs_por_dev = dados.groupby('Desenvolvedor')['Qtd Bugs'].sum().sort_values(ascending=False)
    bugs_por_dev = bugs_por_dev[bugs_por_dev > 0]

    if bugs_por_dev.empty:
        return None

    fig = px.bar(
        x=bugs_por_dev.index,
        y=bugs_por_dev.values,
        title="Qualidade: Bugs de Retorno (Pós-Entrega)<br><sup>Defeitos identificados em Homologação/QA vinculados à entrega</sup>",
        labels={'x': 'Desenvolvedor', 'y': 'Quantidade de Bugs'},
        color=bugs_por_dev.values,
        text=bugs_por_dev.values,
        color_continuous_scale='Reds'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        coloraxis_showscale=False, 
        height=400,
        yaxis_title="Quantidade de Bugs",
        xaxis_title="Desenvolvedor"
    )
    return fig


def criar_grafico_por_tipo(dados, titulo):
    entregas_por_dev = dados.groupby('Desenvolvedor').size().sort_values(ascending=False)
    
    fig = px.bar(
        x=entregas_por_dev.index,
        y=entregas_por_dev.values,
        title=f"Classificação: Entregas de '{titulo}'<br><sup>Distribuição de responsabilidade por tipo</sup>",
        labels={'x': 'Desenvolvedor', 'y': f'Número de {titulo}'},
        color=entregas_por_dev.values,
        color_continuous_scale='blues',
        text=entregas_por_dev.values
    )
    fig.update_layout(xaxis_tickangle=-45, showlegend=False, height=300, coloraxis_showscale=False)
    return fig


def mostrar_grafico_tipo(dados, tipo, titulo):
    dados_tipo = dados[dados['Tipo'] == tipo]
    if not dados_tipo.empty:
        fig = criar_grafico_por_tipo(dados_tipo, titulo)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"Total {titulo}", len(dados_tipo))
        with col2:
            st.metric(f"Total de Desenvolvedor(es) em atuação com {titulo}", dados_tipo['Desenvolvedor'].nunique())
    else:
        st.info(f"Nenhuma {titulo} entregue.")


def criar_grafico_evolucao_temporal(dados):
    evolucao = dados.groupby('Data Entrega').size().reset_index()
    evolucao.columns = ['Data', 'Entregas']
    evolucao = evolucao.sort_values('Data')

    fig = px.line(
        evolucao,
        x='Data',
        y='Entregas',
        title='Cadência: Linha do Tempo de Entregas<br><sup>Frequência diária de conclusões (Throughput)</sup>',
        markers=True
    )
    fig.update_layout(xaxis_title='Data', yaxis_title='Número de Entregas', height=400)
    return fig