import streamlit as st
import pandas as pd
import plotly.express as px
from utils_dados import (
    get_all_issues_with_transitions,
    normalizar_primeiro_nome,
    construir_mapa_dev_mais_recente,
)

@st.cache_data(ttl=900)
def carregar_entregas(jira_url, board_id, headers):
    df = get_all_issues_with_transitions(jira_url, board_id, headers)
    return df if not df.empty else pd.DataFrame()

def entregas_projeto_tab(jira_url, board_id, headers):

    st.title("📦 Entregas do Projeto")

    df = carregar_entregas(jira_url, board_id, headers)
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    if "Dev Nome Original" in df.columns and "Data Atualização" in df.columns:
        df["Dev Primeiro Nome"] = df["Dev Nome Original"].apply(normalizar_primeiro_nome)
        mapa_dev = construir_mapa_dev_mais_recente(df, "Dev Nome Original", "Data Atualização")
        df["Dev Responsável"] = df["Dev Primeiro Nome"].map(mapa_dev).fillna(df["Dev Primeiro Nome"])

    df["Data Criação"] = pd.to_datetime(df["Data Criação"], errors="coerce")
    df["Data Atualização"] = pd.to_datetime(df["Data Atualização"], errors="coerce")
    df["Data Entrega"] = pd.to_datetime(df["Data Entrega"], errors="coerce")

    df = df.dropna(subset=["Data Criação", "Data Entrega"])

    df["Entrega Dia"] = df["Data Entrega"].dt.date
    df["Mês"] = df["Data Entrega"].dt.to_period("M").dt.to_timestamp()

    throughput_mes = df.groupby("Mês").size()

    df["Sprint_Num"] = df["Sprint"].astype(str).str.extract(r"(\d+)").astype(float)
    df_sprints_validas = df[df["Sprint"].str.contains("Sprint", case=False, na=False)]
    df_sprints_finalizadas = df["Status"].str.lower().isin(["done", "concluído", "concluido"])

    throughput_sprint = (
        df_sprints_validas
        .groupby("Sprint_Num")
        .size()
        .sort_index()
    )

    col_status = [c for c in df.columns if c.upper() == "EM DESENVOLVIMENTO"]
    if col_status:
        df["Cycle Time (h)"] = df[col_status[0]]
        df["Cycle Time (dias)"] = df["Cycle Time (h)"] / 7
    else:
        df["Cycle Time (dias)"] = (df["Data Entrega"] - df["Data Criação"]).dt.days

    df["Lead Time (dias)"] = (df["Data Entrega"] - df["Data Criação"]).dt.days

    st.subheader("📅 Throughput Mensal")
    fig_mes = px.line(
        throughput_mes,
        title="Throughput Mensal",
        markers=True
    )
    st.plotly_chart(fig_mes, use_container_width=True)

    
    df_through = (
        df_sprints_validas
        .groupby(["Sprint_Num", "Sprint"])
        .size()
        .reset_index(name="Entregas")
        .sort_values("Sprint_Num")
    )

    st.subheader("📦 Throughput por Sprint (somente sprints finalizadas)")

    fig_sprint = px.bar(
        df_sprints_finalizadas,
        x="Sprint",
        y="Entregas",
        text="Entregas",
        title="Throughput",
        labels={"Sprint": "Sprint", "Entregas": "Total de Entregas"}
    )

    fig_sprint.update_traces(textposition="outside")
    fig_sprint.update_layout(xaxis_title="Sprint", yaxis_title="Total de Entregas")

    st.plotly_chart(fig_sprint, use_container_width=True)

    st.plotly_chart(fig_sprint, use_container_width=True)

    st.header("📊 Médias do Projeto")

    media_geral = len(df) / ((df["Data Entrega"].max() - df["Data Entrega"].min()).days + 1)
    media_tipo = df.groupby("Tipo da Issue").size().sort_values(ascending=False)

    st.metric("📌 Média Geral de Entregas por Dia", f"{media_geral:.2f}")

    st.subheader("📌 Média de Entregas por Tipo de Issue")
    st.bar_chart(media_tipo)
    st.header("⏱ Lead Time")

    fig_lead = px.histogram(
        df,
        x="Lead Time (dias)",
        nbins=20,
        title="Distribuição do Lead Time"
    )
    st.plotly_chart(fig_lead, use_container_width=True)

    df_scatter_lead = df.copy()
    df_scatter_lead["Data_str"] = df_scatter_lead["Data Entrega"].dt.strftime("%Y-%m-%d")

    fig_lead_scatter = px.scatter(
        df_scatter_lead,
        x="Data_str",
        y="Lead Time (dias)",
        color="Dev Responsável",
        title="Lead Time por Entrega"
    )
    st.plotly_chart(fig_lead_scatter, use_container_width=True)

    
    st.header("🔄 Cycle Time")

    fig_cycle = px.histogram(
        df,
        x="Cycle Time (dias)",
        nbins=20,
        title="Distribuição do Cycle Time"
    )
    st.plotly_chart(fig_cycle, use_container_width=True)

    df_scatter_cycle = df.copy()
    df_scatter_cycle["Data_str"] = df_scatter_cycle["Data Entrega"].dt.strftime("%Y-%m-%d")

    fig_cycle_scatter = px.scatter(
        df_scatter_cycle,
        x="Data_str",
        y="Cycle Time (dias)",
        color="Dev Responsável",
        title="Cycle Time por Entrega"
    )
    st.plotly_chart(fig_cycle_scatter, use_container_width=True)

    
    st.header("📊 CFD - Cumulative Flow Diagram")

    cols_status = [
        c for c in df.columns
        if c not in [
            "Sprint", "Issue Key", "Título", "Dev Responsável",
            "Estimativa em Horas", "Tempo Registrado",
            "Tipo da Issue", "Prioridade", "Épico",
            "Qtd Bugs", "Data Entrega",
            "Data Criação", "Data Atualização"
        ]
    ]

    if cols_status:
        df_cfd = df[["Data Atualização"] + cols_status].copy()
        df_cfd["Dia"] = df_cfd["Data Atualização"].dt.date
        dados_cfd = df_cfd.groupby("Dia")[cols_status].sum()

        fig_cfd = px.area(
            dados_cfd,
            title="CFD - Fluxo Acumulado"
        )
        st.plotly_chart(fig_cfd, use_container_width=True)
    else:
        st.info("Não há dados suficientes para o CFD.")

    
    st.header("🌡 Heatmap de Throughput por Dia da Semana")

    df["Dia Semana"] = df["Data Entrega"].dt.day_name()
    heatmap = df.groupby(["Dia Semana", "Sprint"]).size().reset_index(name="Entregas")

    fig_heatmap = px.density_heatmap(
        heatmap,
        x="Sprint",
        y="Dia Semana",
        z="Entregas",
        color_continuous_scale="Blues",
        title="Heatmap de Entregas"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.header("📋 Tabela Final de Entregas")

    st.dataframe(
        df[
            [
                "Issue Key", "Título", "Tipo da Issue", "Sprint",
                "Dev Responsável", "Data Criação",
                "Data Entrega", "Lead Time (dias)", "Cycle Time (dias)",
                "Qtd Bugs"
            ]
        ].sort_values("Data Entrega", ascending=False),
        use_container_width=True,
        height=450
    )
