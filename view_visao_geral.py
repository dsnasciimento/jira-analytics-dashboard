import os
from dotenv import load_dotenv
import plotly.express as px
import pandas as pd
import streamlit as st
from datetime import datetime
from utils_dados import (
    get_all_issues,
    get_prioridade,
    count_bugs,
    normalizar_primeiro_nome,
    construir_mapa_dev_mais_recente,
)

load_dotenv()
excluidos = os.getenv("excluidos", "").split(",") if os.getenv("excluidos") else []

def dados_gerais(jira_url, board_id, headers, all_issues_data=None):
    st.header("📊 Relatório Geral de Atividades")

    if all_issues_data is not None:
        issues = all_issues_data
    else:
        issues = get_all_issues(jira_url, board_id, headers)

    if not issues:
        st.warning("Nenhuma atividade encontrada.")
        return

    registros = []
    for issue in issues:
        fields = issue.get("fields", {})

        prioridade = get_prioridade(issue)

        assignee_data = fields.get("assignee")
        responsavel_original = assignee_data.get("displayName") if assignee_data else "Não atribuído"

        sprint_info = fields.get("custom_fiel") or [] # Substitua "" pela chave correta para obter informações da sprint
        sprint = sprint_info[0].get("name") if sprint_info else None

        tipo_issue = fields.get("issuetype", {}).get("name", "Sem tipo definido")

        updated_raw = fields.get("updated")
        updated_dt = pd.to_datetime(updated_raw) if updated_raw else pd.NaT

        bug_count = count_bugs(fields.get("subtasks", []))

        registros.append({
            "Nome Original": responsavel_original,
            "Sprint": sprint,
            "Tipo": tipo_issue,
            "Qtd Bugs": bug_count,
            "Atualizado em": updated_dt,
        })

    df = pd.DataFrame(registros)

    if df.empty:
        st.warning("Nenhum dado processado.")
        return

    df["Dev Primeiro Nome"] = df["Nome Original"].apply(normalizar_primeiro_nome)
    mapa_dev = construir_mapa_dev_mais_recente(df, "Nome Original", "Atualizado em")
    df["Dev Responsável"] = df["Dev Primeiro Nome"].map(mapa_dev).fillna(df["Dev Primeiro Nome"])

    df["Número da Sprint"] = df["Sprint"].str.extract(r'(\d+)').astype(float)
    df = df.sort_values(by="Número da Sprint", ascending=False)

    devs = [d for d in sorted(df["Dev Responsável"].dropna().unique().tolist()) if d not in excluidos]
    devs = ["Todos"] + devs
    sprints = ["Todas"] + df["Sprint"].dropna().unique().tolist()

    dev_selecionado = st.selectbox("Filtrar por Dev", devs)
    sprint_selecionada = st.selectbox("Selecione a Sprint", sprints)

    exibir_subtasks = st.checkbox("Exibir Subtasks?", value=False)
    exibir_bugs = st.checkbox("Exibir Bugs?", value=False)

    df_filtrado = df.copy()
    if dev_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Dev Responsável"] == dev_selecionado]
    if sprint_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Sprint"] == sprint_selecionada]

    df_agrupado = df_filtrado.groupby("Tipo").size().reset_index(name="Quantidade")
    total_bugs = df_filtrado["Qtd Bugs"].sum()

    if exibir_bugs and total_bugs > 0:
        df_agrupado = pd.concat([
            df_agrupado,
            pd.DataFrame({"Tipo": ["Bug"], "Quantidade": [total_bugs]})
        ])

    ordem_tipos = ["Épico", "História", "Melhoria", "Correção", "Problema", "Tarefa", "Subtask", "Bug"]
    color_map = {
        "Épico":"purple",
        "História": "green",
        "Melhoria": "yellow",
        "Correção": "orange",
        "Problema": "red",
        "Tarefa": "blue",
        "Subtask": "gray",
        "Bug": "red"
    }

    df_agrupado["Tipo"] = pd.Categorical(df_agrupado["Tipo"], categories=ordem_tipos, ordered=True)
    df_agrupado = df_agrupado.sort_values("Tipo")

    if not exibir_subtasks:
        df_agrupado = df_agrupado[df_agrupado["Tipo"] != "Subtask"]

    st.subheader("📊 Quantidade por Tipo de Atividade")
    fig = px.bar(
        df_agrupado,
        x="Tipo",
        y="Quantidade",
        text_auto=True,
        color="Tipo",
        category_orders={"Tipo": ordem_tipos},
        color_discrete_map=color_map
    )
    fig.update_layout(xaxis_title="Tipo de Atividade", yaxis_title="Quantidade", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    total_sem_bugs = df_agrupado[df_agrupado["Tipo"] != "Bug"]["Quantidade"].sum()
    total_bugs_exibidos = df_agrupado[df_agrupado["Tipo"] == "Bug"]["Quantidade"].sum()

    st.markdown(f"**Total de Atividades:** {total_sem_bugs}")
    st.markdown(f"**Total de Bugs Encontrados:** {total_bugs_exibidos}")
