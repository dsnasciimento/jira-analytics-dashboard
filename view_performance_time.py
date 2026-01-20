import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils_dados import (
    get_all_issues_with_transitions,
    normalizar_primeiro_nome,
    construir_mapa_dev_mais_recente,
)

@st.cache_data
def carregar_dados(jira_url, board_id, headers):
    return get_all_issues_with_transitions(jira_url, board_id, headers, filtro_nome="Sprint")

def desempenho_tab(jira_url, board_id, headers):
    st.header("📊 Desempenho por Sprint")

    df_all = carregar_dados(jira_url, board_id, headers)
    if df_all.empty:
        st.warning("Nenhum dado encontrado.")
        return

    if "Dev Nome Original" in df_all.columns and "Data Atualização" in df_all.columns:
        df_all["Dev Primeiro Nome"] = df_all["Dev Nome Original"].apply(normalizar_primeiro_nome)
        mapa_dev = construir_mapa_dev_mais_recente(df_all, "Dev Nome Original", "Data Atualização")
        df_all["Dev Responsável"] = df_all["Dev Primeiro Nome"].map(mapa_dev).fillna(df_all["Dev Primeiro Nome"])
    else:
        if "Dev Nome Original" in df_all.columns:
            df_all["Dev Responsável"] = df_all["Dev Nome Original"]
        else:
            st.error("Coluna 'Dev Nome Original' não encontrada nos dados.")
            return

    sprints_unicos = sorted(
        df_all["Sprint"].astype(str).unique(),
        key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in str(x)) else 0,
        reverse=True
    )
    
    if not sprints_unicos:
        st.warning("Nenhuma sprint encontrada.")
        return

    sprint_sel = st.selectbox("Selecione a Sprint", sprints_unicos)

    df_sprint = df_all[df_all["Sprint"] == sprint_sel].copy()

    devs_unicos = sorted(df_sprint["Dev Responsável"].astype(str).unique())
    devs_sel = st.multiselect("Filtrar por Desenvolvedor", devs_unicos, default=devs_unicos)
    df_sprint = df_sprint[df_sprint["Dev Responsável"].isin(devs_sel)]

    if df_sprint.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    col_dev_efetivo = "EM DESENVOLVIMENTO"
    if col_dev_efetivo not in df_sprint.columns:
        df_sprint[col_dev_efetivo] = 0.0

    df_dev = df_sprint.groupby("Dev Responsável").agg({
        "Estimativa em Horas": "sum",
        "Tempo Registrado (Worklog em Horas)": "sum",
        col_dev_efetivo: "sum",
        "Issue Key": "count"
    }).reset_index()

    df_dev.rename(columns={
        "Tempo Registrado (Worklog em Horas)": "Tempo Registrado",
        col_dev_efetivo: "Desenvolvimento Efetivo",
        "Issue Key": "Qtd Issues"
    }, inplace=True)

    df_dev["Acurácia (%)"] = (
        df_dev["Tempo Registrado"] /
        df_dev["Estimativa em Horas"].replace(0, 1)
    ) * 100
    
    df_dev["Tempo Médio por Issue"] = (
        df_dev["Tempo Registrado"] /
        df_dev["Qtd Issues"].replace(0, 1)
    )

    df_dev_display = df_dev.copy()
    cols_to_format = [
        "Estimativa em Horas",
        "Tempo Registrado",
        "Desenvolvimento Efetivo",
        "Acurácia (%)",
        "Tempo Médio por Issue"
    ]
    for col in cols_to_format:
        if col in df_dev_display.columns:
            df_dev_display[col] = df_dev_display[col].map(lambda x: f"{x:.1f}")

    st.subheader("📋 Resumo por Desenvolvedor")
    st.dataframe(df_dev_display, use_container_width=True)

    st.subheader("⏱ Horas Estimadas, Registradas e Desenvolvimento Efetivo")

    horas_long = df_dev.melt(
        id_vars=["Dev Responsável"],
        value_vars=[
            "Estimativa em Horas",
            "Tempo Registrado",
            "Desenvolvimento Efetivo"
        ],
        var_name="Tipo de Hora",
        value_name="Horas"
    )

    cores = {
        "Estimativa em Horas": "#1f77b4", 
        "Tempo Registrado": "#ff8e03", 
        "Desenvolvimento Efetivo": "#d62728"    
    }

    ordem_horas = ["Estimativa em Horas", "Tempo Registrado", "Desenvolvimento Efetivo"]

    chart_lado_a_lado = alt.Chart(horas_long).mark_bar().encode(
        x=alt.X(
            'Dev Responsável:N',
            title="Desenvolvedor",
            axis=alt.Axis(labelAngle=-45)
        ),
        y=alt.Y('Horas:Q', title="Horas"),
        color=alt.Color(
            'Tipo de Hora:N',
            scale=alt.Scale(domain=ordem_horas, range=[cores[h] for h in ordem_horas]),
            legend=alt.Legend(title="Métrica", orient="bottom")
        ),
        xOffset=alt.XOffset('Tipo de Hora:N', scale=alt.Scale(domain=ordem_horas)),
        tooltip=['Dev Responsável', 'Tipo de Hora', 'Horas']
    ).properties(width=600, height=400)

    st.altair_chart(chart_lado_a_lado, use_container_width=True)

    st.subheader("Tempo Médio por Issue (h)")
    
    chart_tempo_medio = alt.Chart(df_dev).mark_bar().encode(
        x=alt.X(
            'Dev Responsável:N', 
            title="Desenvolvedor", 
            axis=alt.Axis(labelAngle=-45)
        ),
        y=alt.Y('Tempo Médio por Issue:Q', title="Horas Médias"),
        tooltip=['Dev Responsável', alt.Tooltip('Tempo Médio por Issue', format='.1f')],
        color=alt.value("blue")
    ).properties(height=400)

    st.altair_chart(chart_tempo_medio, use_container_width=True)
