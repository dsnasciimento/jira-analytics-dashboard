import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import altair as alt
from utils_dados import calcular_dias_uteis, convert_time_to_hours

def burndown_tab(jira_url, board_id, headers):
    st.header("📉 Burndown da Sprint Atual")

    sprint_url = f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint"
    response = requests.get(sprint_url, headers=headers)
    if response.status_code != 200:
        st.error(f"Erro ao buscar sprints: {response.status_code}")
        return

    sprints = response.json()["values"]
    sprint = next((s for s in sprints if s["state"] == "active" and "Sprint" in s["name"]), None)
    if not sprint:
        st.warning("Nenhuma sprint ativa com nome encontrada.")
        return

    sprint_id = sprint['id']
    sprint_name = sprint['name']
    sprint_start = datetime.fromisoformat(sprint["startDate"].replace("Z", "+00:00"))
    sprint_end = datetime.fromisoformat(sprint["endDate"].replace("Z", "+00:00"))

    dias_uteis_count, dias_uteis_lista, feriados_lista = calcular_dias_uteis(sprint_start, sprint_end)
    HORAS_POR_DIA = 8
    horas_disponiveis = dias_uteis_count * HORAS_POR_DIA

    issues_url = f"{jira_url}/rest/api/3/search/jql"
    jql = f"sprint = {sprint_id} ORDER BY created DESC"
    fields = "*all,-comment"

    params = {
        "jql": jql,
        "fields": fields,
        "maxResults": 100,
        "validateQuery": "warn"
    }

    issues_resp = requests.get(issues_url, headers=headers, params=params)
    if issues_resp.status_code != 200:
        st.error(f"Erro ao buscar issues: {issues_resp.status_code}")
        st.error(f"Detalhes: {issues_resp.text}")
        return

    issues = issues_resp.json().get("issues", [])
    issues_extras = [i for i in issues if 'extra' in i['fields'].get('summary', '').lower()]

    total_estimate = 0
    completed_estimate = 0
    total_days = (sprint_end - sprint_start).days + 1
    dates = [sprint_start + timedelta(days=i) for i in range(total_days)]
    daily_reduction = defaultdict(float)
    rolled_over_work = []
    rolled_over = 0
    remaining_work = []

    for issue in issues:
        summary = issue['fields'].get('summary', '').lower()
        if 'extra' in summary:
            continue

        estimate = convert_time_to_hours(issue['fields']['timetracking'].get('originalEstimate', '0h'))
        status = issue['fields']['status']['name'].upper()
        category = issue['fields']['status']['statusCategory']['name']
        updated = datetime.fromisoformat(issue['fields']['updated'].replace("Z", "+00:00"))

        total_estimate += estimate

        if status in ["DONE", "APROVADO", "CONCLUIDO", "FINALIZADO"] or category == "Done":
            completed_estimate += estimate

        for date in dates:
            if date.date() >= updated.date():
                if status in ["DONE", "APROVADO", "CONCLUIDO", "FINALIZADO"] or category == "Done":
                    daily_reduction[date] += estimate
                else:
                    daily_reduction[date] += 0

    for date in dates:
        remaining = total_estimate - daily_reduction.get(date, 0) - rolled_over
        rolled_over_work.append(rolled_over)
        if remaining < 0:
            rolled_over += abs(remaining)
            remaining = 0
        remaining_work.append(remaining)

    n = len(dates)
    ideal = [total_estimate * (1 - i / (n - 1)) for i in range(n)] if n > 1 else [total_estimate]

    df_burndown = pd.DataFrame({
        "Data": dates,
        "Ideal": ideal,
        "Restante": remaining_work,
    })

    df_burndown["Data"] = df_burndown["Data"].dt.date

    horas_restantes = round(total_estimate - completed_estimate, 2)

    st.markdown(f"""
    **{sprint_name}**    
    **Período:** {sprint_start.strftime('%d/%m/%Y')} até {sprint_end.strftime('%d/%m/%Y')}  
    **Total de Atividades:** {len(issues) - len(issues_extras)}  
    **Total de Extras:** {len(issues_extras)}

    **Horas Estimadas:** {total_estimate:.1f}h  
    **Horas Concluídas:** {completed_estimate:.1f}h  
    **Horas de trabalho restantes:** {horas_restantes:.1f}h
    """)

    df_burndown_reset = df_burndown.copy()

    hoje = datetime.now().date()

    chart = alt.Chart(df_burndown_reset).transform_fold(
        ["Ideal", "Restante"],
        as_=["Métrica", "Valor"]
    ).mark_line().encode(
        x=alt.X("Data:T", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("Valor:Q"),
        color=alt.Color(
            "Métrica:N",
            scale=alt.Scale(
                domain=["Ideal", "Restante"],
                range=["gray", "red"]
            ),
            legend=alt.Legend(title="Métrica")
        ),
        tooltip=["Data:T", "Métrica:N", "Valor:Q"]
    )


    linha_hoje = alt.Chart(pd.DataFrame({"Data": [hoje]})).mark_rule(
        color="gray",
        strokeDash=[5, 5]
    ).encode(
        x="Data:T"
    )

    chart = chart.properties(width="container", height=400).interactive()
    linha_hoje = linha_hoje.properties(width="container", height=400)

    st.altair_chart(chart + linha_hoje, use_container_width=True)

