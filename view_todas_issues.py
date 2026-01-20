import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
from utils_dados import (
    get_all_issues,
    normalizar_primeiro_nome,
    construir_mapa_dev_mais_recente,
)

def all_issues_tab(jira_url, board_id, headers, all_issues_data=None):
    st.title("📋 Todas as Issues do Projeto")

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

    issues_data = []
    for issue in issues:
        fields = issue.get("fields", {})

        sprint_field = fields.get("") # Substitua "" pelo nome correto do campo de sprint
        sprint_name = "Não atribuído"

        if isinstance(sprint_field, list) and len(sprint_field) > 0:
            sprint_name = sprint_field[0].get("name", "Não atribuído")
        elif isinstance(sprint_field, dict):
            sprint_name = sprint_field.get("name", "Não atribuído")

        assignee = (fields.get("assignee") or {}).get("displayName", "Não atribuído")

        issues_data.append({
            # Dados básicos
        })

    df = pd.DataFrame(issues_data)
    
    df["Criado em"] = pd.to_datetime(df["Criado em"], errors="coerce")
    df["Atualizado em"] = pd.to_datetime(df["Atualizado em"], errors="coerce")

    df["Primeiro Nome Resp"] = df["Responsável Original"].apply(normalizar_primeiro_nome)
    mapa_dev = construir_mapa_dev_mais_recente(df, "Responsável Original", "Atualizado em")
    df["Responsável"] = df["Primeiro Nome Resp"].map(mapa_dev).fillna(df["Primeiro Nome Resp"])

    df_display = df.copy()
    for col in ["Criado em", "Atualizado em"]:
        df_display[col] = df_display[col].dt.strftime("%d/%m/%Y %H:%M")

    st.subheader("📋 Lista de Issues (Tratadas)")
    st.dataframe(df_display[[
        # Colunas a serem exibidas
    ]], use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Issues", len(df))
    with col2:
        st.metric("Tipos Únicos", df["Tipo"].nunique())
    with col3:
        st.metric("Status Únicos", df["Status"].nunique())

    st.subheader("🔍 Filtros")
    col1, col2 = st.columns(2)

    with col1:
        tipos_filtro = st.multiselect(
            "Filtrar por Tipo",
            options=sorted(df["Tipo"].dropna().unique()),
            default=sorted(df["Tipo"].dropna().unique())
        )

    with col2:
        status_filtro = st.multiselect(
            "Filtrar por Status",
            options=sorted(df["Status"].dropna().unique()),
            default=sorted(df["Status"].dropna().unique())
        )

    df_filtrado = df[
        (df["Tipo"].isin(tipos_filtro)) &
        (df["Status"].isin(status_filtro))
    ]

    st.metric("Issues Filtradas", len(df_filtrado))

    try:
        df2 = pd.json_normalize(issues)
        with st.expander("📊 Dados Brutos da API"):
            st.dataframe(df2, use_container_width=True)
    except Exception as e:
        st.warning(f"Não foi possível exibir dados brutos: {e}")

    timezone_brazil = pytz.timezone('America/Sao_Paulo')
    now_brazil = datetime.now(timezone_brazil)
    file_name = f"Issues_{now_brazil.strftime('%d_%m_%y')}.xlsx"

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_display.to_excel(writer, index=False, sheet_name="Issues")
    output.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )