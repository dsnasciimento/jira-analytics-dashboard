import base64
import holidays
import requests
from datetime import datetime, timedelta
from dateutil.parser import parse
import pandas as pd
import time
import functools
from streamlit import cache_data
import unicodedata


@functools.lru_cache(maxsize=128)
@cache_data(ttl=300) 
def get_all_issues_cached(_jira_url, _board_id, _headers):
    return get_all_issues(_jira_url, _board_id, _headers)

def get_issues_batch(jira_url, issue_keys, headers):
    jql = f'key in ({",".join(issue_keys)})'
    params = {
        "jql": jql,
        "maxResults": len(issue_keys),
        "fields": "*all,-comment",
        "expand": "changelog"
    }
    response = requests.get(
        f"{jira_url}/rest/api/3/search/jql",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    return response.json().get("issues", [])

def autenticar(email, token):
    return base64.b64encode(f"{email}:{token}".encode()).decode()

def get_all_issues(jira_url, board_id, headers):
    delay_per_request = 0.12

    board_url = f"{jira_url}/rest/agile/1.0/board/{board_id}"
    board_resp = requests.get(board_url, headers=headers)
    board_resp.raise_for_status()
    board_data = board_resp.json()

    project_id = board_data.get("location", {}).get("projectId")
    if not project_id:
        raise Exception("Não foi possível identificar o projeto pelo board_id")

    search_url = f"{jira_url}/rest/api/3/search/jql"

    jql = f'project = "{project_id}" ORDER BY created DESC'

    fields = "*all,-comment"

    params = {
        "jql": jql,
        "maxResults": 100,
        "fields": fields,
        "validateQuery": "warn"
    }

    all_issues = []
    next_page_token = None

    while True:
        if next_page_token:
            params["nextPageToken"] = next_page_token
        else:
            params.pop("nextPageToken", None)

        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        issues = data.get("issues", [])
        all_issues.extend(issues)

        if data.get("isLast", True):
            break

        next_page_token = data.get("nextPageToken")
        time.sleep(delay_per_request)

    return all_issues

def get_prioridade(issue):
    priority_translation = {
        "Highest": "Muito Alta",
        "High": "Alta",
        "Medium": "Média",
        "Low": "Baixa",
        "Lowest": "Muito Baixa"
    }

    if 'priority' in issue['fields'] and issue['fields']['priority']:
        prioridade_en = issue['fields']['priority']['name']
        return priority_translation.get(prioridade_en, prioridade_en)

    return "Prioridade não definida"

def get_color_issue(issue):
    color_map = {
        "História": "green",
        "Melhoria": "yellow",
        "Tarefa": "blue",
        "Problema": "red",
        "Correção": "orange"
    }
    tipo = issue.get("fields", {}).get("issuetype", {}).get("name", "")
    return color_map.get(tipo, "gray")

def get_epic_color(issue):
    color_map = {
        'dark_gray': '#243859',
        'dark_yellow': '#FA9920',
        'yellow': '#FAC304',
        'dark_blue': '#2A53CC',
        'dark_teal': '#2AA3BF',
        'green': '#58D8A4',
        'purple': '#8677D9',
        'dark_purple': '#5244AA',
        'orange': "#8F8F8F",
        'blue': '#3884FF',
        'teal': "#34C7E6",
        'gray': '#6B778C',
        'dark_green': '#128759',
        'dark_orange': '#DD350D'
    }
    epic_color = issue.get("fields", {}).get("", "") # Substitua "" pelo campo correto do Jira que contém a cor do épico
    if epic_color in color_map:
        return color_map[epic_color]

def calcular_dias_uteis(inicio, fim):
    if not inicio or not fim:
        return None, [], []

    inicio_date = pd.to_datetime(inicio).date()
    fim_date = pd.to_datetime(fim).date()
    feriados = holidays.Brazil(state='SP') # Adicione o estado se necessário
    dias_uteis = [
        dia for dia in pd.date_range(inicio_date, fim_date)
        if dia.weekday() < 5 and dia.date() not in feriados
    ]
    feriados_periodo = [f for f in feriados if inicio_date <= f <= fim_date]
    return len(dias_uteis), dias_uteis, feriados_periodo

def convert_time_to_hours(time_str):
    if not time_str:
        return 0
    weeks, days, hours, minutes = 0, 0, 0, 0
    parts = time_str.split()
    for part in parts:
        if "w" in part:
            weeks = int(part.replace("w", "")) * 40
        elif "d" in part:
            days = int(part.replace("d", "")) * 8
        elif "h" in part:
            hours = int(part.replace("h", ""))
        elif "m" in part:
            minutes = int(part.replace("m", "")) / 60
    return round(weeks + days + hours + minutes, 2)

def calculate_working_hours(start, end, horas_por_dia=7):
    if not start or not end:
        return 0
    dias_uteis = pd.date_range(start.date(), end.date(), freq='B')
    total_horas = len(dias_uteis) * horas_por_dia
    return round(total_horas, 2)

def count_bugs(subtasks):
    return sum(
        1 for sub in subtasks
        if any(
            b in (sub.get('fields', {}).get('summary', '') or '').lower()
            for b in ['bug', 'defeito', 'comportamento']
        )
    )

def get_all_issues_with_transitions(jira_url, board_id, headers, filtro_nome="Sprint"):
    sprint_url = f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint"
    endpoint = f"{jira_url}/rest/api/3/search/jql"

    response = requests.get(sprint_url, headers=headers)
    response.raise_for_status()
    sprints = response.json()["values"]
    target_sprints = [s for s in sprints if filtro_nome.lower() in s["name"].lower()]

    sprint_dataframes = []
    for sprint in target_sprints:
        sprint_id = sprint["id"]
        sprint_name = sprint["name"]

        jql = f'sprint = {sprint_id} ORDER BY created DESC'
        fields = "*all,-comment"

        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": 100,
            "validateQuery": "warn",
            "expand": "changelog"
        }

        response = requests.get(endpoint, params=params, headers=headers)
        if response.status_code != 200:
            continue

        issues = response.json().get("issues", [])
        data = []

        for issue in issues:
            key = issue['key']
            fields_issue = issue['fields']
            assignee_field = fields_issue.get('assignee')
            dev_nome_original = assignee_field['displayName'] if assignee_field else "Não atribuído"

            created_raw = fields_issue.get("created")
            created_dt = parse(created_raw) if created_raw else None

            updated_raw = fields_issue.get("updated")
            updated_dt = parse(updated_raw) if updated_raw else None

            resolution_raw = fields_issue.get("resolutiondate")
            resolution_dt = parse(resolution_raw) if resolution_raw else None

            sprints_field = fields_issue.get('sprints', [])
            sprint_name_issue = sprints_field[0].get('name') if sprints_field and len(sprints_field) > 0 else "-"

            estimate = convert_time_to_hours(fields_issue.get('timetracking', {}).get('originalEstimate'))
            spent = convert_time_to_hours(fields_issue.get('timetracking', {}).get('timeSpent'))

            epic = fields_issue.get('parent', {}).get('fields', {}).get('summary', '-') if 'parent' in fields_issue else "-"
            status_atual = fields_issue.get('status', {}).get('name', '-')

            status_times = {}
            url = f"{jira_url}/rest/api/3/issue/{key}?expand=changelog"
            res_status = requests.get(url, headers=headers)
            if res_status.status_code == 200:
                transitions = []
                for history in res_status.json().get("changelog", {}).get("histories", []):
                    for item in history.get("items", []):
                        if item.get("field") == "status":
                            from_status = item.get("fromString", "N/A")
                            to_status = item.get("toString", "N/A")
                            change_date = datetime.strptime(history["created"], "%Y-%m-%dT%H:%M:%S.%f%z")
                            transitions.append((from_status, to_status, change_date))
                transitions.sort(key=lambda x: x[2])

                if transitions:
                    first_status = transitions[0][0]
                    first_date = transitions[0][2]
                    created_date = parse(fields_issue.get("created"))
                    if created_date < first_date:
                        status_times[first_status] = calculate_working_hours(created_date, first_date)

                    prev_status, prev_date = first_status, first_date
                    for from_status, to_status, change_date in transitions:
                        if prev_status and prev_date:
                            hours = calculate_working_hours(prev_date, change_date)
                            status_times[prev_status] = status_times.get(prev_status, 0) + hours
                        prev_status = to_status
                        prev_date = change_date

                    if prev_status and prev_date:
                        hours = calculate_working_hours(prev_date, datetime.now(prev_date.tzinfo))
                        status_times[prev_status] = status_times.get(prev_status, 0) + hours

            bug_count = count_bugs(fields_issue.get('subtasks', []))

            row = {
                "Sprint": sprint_name,
                "Issue Key": key,
                "Épico": epic,
                "Tipo da Issue": fields_issue['issuetype']['name'],
                "Status Atual": status_atual,
                "Prioridade": fields_issue.get('priority', {}).get('name', 'Prioridade não definida'),
                "Título": fields_issue.get('summary', '-'),
                "Nome Original": dev_nome_original,
                "Data Atualização": updated_dt,
                "Data Criação": created_dt,
                "Data Entrega": resolution_dt,
                "Estimativa em Horas": estimate,
                "Tempo Registrado(h))": spent,
                "Quantidade de Bugs": bug_count
            }
            row.update(status_times)
            data.append(row)

        if data:
            sprint_dataframes.append(pd.DataFrame(data))

    if not sprint_dataframes:
        return pd.DataFrame()

    df = pd.concat(sprint_dataframes, ignore_index=True)
    return df

def remover_acentos(texto: str) -> str:
    if not texto:
        return texto
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

def normalizar_primeiro_nome(nome: str) -> str:
    if not nome or nome == "Não atribuído":
        return "Não atribuído"
    
    partes = str(nome).strip().split()
    primeiro = partes[0]

    primeiro_sem_acento = remover_acentos(primeiro).capitalize()

    return primeiro_sem_acento

def extrair_nome_sobrenome(nome: str) -> str:
    if not nome or nome == "Não atribuído":
        return "Não atribuído"
    partes = str(nome).strip().split()
    if len(partes) >= 2:
        return f"{partes[0]} {partes[1]}"
    return partes[0]

def construir_mapa_dev_mais_recente(df: pd.DataFrame, col_nome_original: str, col_data: str):
    if df.empty or col_nome_original not in df.columns or col_data not in df.columns:
        return {}

    tmp = df[[col_nome_original, col_data]].dropna(subset=[col_nome_original, col_data]).copy()
    if tmp.empty:
        return {}

    tmp["PrimeiroNome"] = tmp[col_nome_original].apply(normalizar_primeiro_nome)

    tmp = tmp.sort_values(col_data)

    mapping = {}
    for primeiro_nome, grupo in tmp.groupby("PrimeiroNome"):
        nome_completo = grupo.iloc[-1][col_nome_original]
        mapping[primeiro_nome] = extrair_nome_sobrenome(nome_completo)

    return mapping
