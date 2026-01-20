import streamlit as st
import pandas as pd
import plotly.express as px
import io
import pytz
import re
import requests
from datetime import datetime
from utils_dados import calcular_dias_uteis
from service_jira import get_sprints

def sprint_tab(jira_url, board_id, headers):
    st.title("📋 Análise de Datas das Sprints")

    try:
        sprints_data = get_sprints_data(jira_url, board_id, headers)
    except Exception as e:
        st.error(str(e))
        return

    if sprints_data.empty:
        st.warning("Nenhuma sprint encontrada.")
        return

    opcoes_sprints = ["Todas"] + sprints_data["Nome da Sprint"].dropna().unique().tolist()
    sprint_selecionada = st.selectbox("Selecione a Sprint", opcoes_sprints)

    df_filtrado = sprints_data.copy()
    if sprint_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Nome da Sprint"] == sprint_selecionada]

    st.subheader("📋 Dados das Sprints")
    st.dataframe(df_filtrado.drop(columns=["Número da Sprint"]), use_container_width=True)

    st.subheader("📊 Gráfico de Dias por Sprint")
    df_grafico = df_filtrado[["Nome da Sprint", "Dias de Atraso", "Dias Úteis Totais", "Dias Totais"]].copy()
    df_grafico = df_grafico.melt(id_vars="Nome da Sprint", var_name="Métrica", value_name="Dias").dropna()
    df_grafico["Dias"] = pd.to_numeric(df_grafico["Dias"], errors="coerce")

    fig = px.bar(
        df_grafico,
        x="Nome da Sprint",
        y="Dias",
        color="Métrica",
        barmode="group",
        text_auto=True,
        title="Comparativo de Dias por Sprint"
    )
    fig.update_layout(
        xaxis_title="Sprint",
        yaxis_title="Dias",
        legend_title="Legenda",
        xaxis=dict(categoryorder="array", categoryarray=df_filtrado["Nome da Sprint"].tolist())
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Totais Agregados de Dias (Todas as Sprints)")

    totais = {
        "Dias de Atraso": sprints_data["Dias de Atraso"].sum(skipna=True),
        "Dias Úteis Totais": sprints_data["Dias Úteis Totais"].sum(skipna=True),
        "Dias Totais": sprints_data["Dias Totais"].sum(skipna=True)
    }

    df_totais = pd.DataFrame(list(totais.items()), columns=["Métrica", "Total de Dias"])

    fig_totais = px.bar(
        df_totais,
        x="Métrica",
        y="Total de Dias",
        text_auto=True,
        title="Soma Total de Dias por Tipo",
        color="Métrica",
    )
    fig_totais.update_layout(
        xaxis_title="",
        yaxis_title="Total de Dias",
        showlegend=False
    )

    st.plotly_chart(fig_totais, use_container_width=True)

    timezone_brazil = pytz.timezone('America/Sao_Paulo')
    now_brazil = datetime.now(timezone_brazil)
    file_name = f"Sprints_{now_brazil.strftime('%d_%m_%y')}.xlsx"
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sprints_data.drop(columns=["Número da Sprint"]).to_excel(writer, index=False, sheet_name="Dados Sprints")
    output.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@st.cache_data
def get_sprints_data(jira_url, board_id, headers):
    try:
        sprints = get_sprints(jira_url, board_id, headers)
    except Exception as e:
        raise Exception(f"Erro ao buscar sprints: {str(e)}")

    sprints_data = []

    for sprint in sprints:
        if "Sprint" not in sprint["name"]:
            continue
        try:
            inicio = datetime.strptime(sprint.get("startDate", ""), "%Y-%m-%dT%H:%M:%S.%fZ") if sprint.get("startDate") else None
            fim = datetime.strptime(sprint.get("endDate", ""), "%Y-%m-%dT%H:%M:%S.%fZ") if sprint.get("endDate") else None
            fechamento = datetime.strptime(sprint.get("completeDate", ""), "%Y-%m-%dT%H:%M:%S.%fZ") if sprint.get("completeDate") else None

            dias_totais = (fim - inicio).days + 1 if inicio and fim else None
            dias_uteis_count, _, _ = calcular_dias_uteis(sprint.get("startDate"), sprint.get("completeDate")) if inicio and fim else (None, [], [])
            dias_uteis = dias_uteis_count if dias_uteis_count is not None else None
            dias_atraso = (fechamento - fim).days if fechamento and fim and fechamento > fim else 0

            status = "Fechada" if sprint["state"] == "closed" else "Ativa" if sprint["state"] == "active" else "Planejada"

            sprints_data.append({
                "ID": sprint["id"],
                "Nome da Sprint": sprint["name"],
                "Status": status,
                "Data de Início": inicio.strftime("%d/%m/%Y") if inicio else None,
                "Previsão de Conclusão": fim.strftime("%d/%m/%Y") if fim else None,
                "Data de Fechamento": fechamento.strftime("%d/%m/%Y") if fechamento else None,
                "Dias de Atraso": dias_atraso if sprint["state"] == "closed" else None,
                "Dias Úteis Totais": dias_uteis_count,
                "Dias Totais": dias_totais if sprint["state"] in ["closed", "active"] else None
            })
        except Exception as e:
            st.warning(f"Erro ao processar sprint {sprint['name']}: {e}")

    df = pd.DataFrame(sprints_data)
    if not df.empty:
        df["Número da Sprint"] = df["Nome da Sprint"].str.extract(r'(\d+)').astype(float)
        df = df.sort_values(by="Número da Sprint", ascending=False)

        def extrair_valor_simples(v):
            if isinstance(v, (list, tuple)) and len(v) == 1:
                return v[0]
            elif isinstance(v, (list, tuple)):
                return None
            return v

        for col in ["Dias de Atraso", "Dias Úteis Totais", "Dias Totais"]:
            df[col] = df[col].apply(extrair_valor_simples)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df if not df.empty else pd.DataFrame()