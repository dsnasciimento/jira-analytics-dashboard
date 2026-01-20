import requests
from datetime import datetime

def get_sprints(jira_url, board_id, headers):
    url = f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("values", [])
    else:
        raise Exception(f"Erro ao buscar sprints: {response.status_code} - {response.text}")

def get_active_sprint(jira_url, board_id, headers):
    sprints = get_sprints(jira_url, board_id, headers)
    for sprint in sprints:
        if sprint["state"] == "active" and "Sprint" in sprint["name"]:
            return {
                "id": sprint["id"],
                "name": sprint["name"],
                "start": datetime.fromisoformat(sprint["startDate"].replace("Z", "+00:00")),
                "end": datetime.fromisoformat(sprint["endDate"].replace("Z", "+00:00"))
            }
    return None

def get_issues_from_sprint(jira_url, sprint_id, headers):
    url = f"{jira_url}/rest/api/3/search/jql"

    jql_query = f"sprint = {sprint_id} ORDER BY created DESC"
    
    fields = "*all,-comment" #Passar os campos necessário

    params = {
        "jql": jql_query,
        "fields": fields,
        "maxResults": 100, #Máximo por requisição
        "validateQuery": "warn"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("issues", [])

def get_all_sprints(jira_url, board_id, headers, filtro_nome=None):
    response = requests.get(f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint", headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erro ao buscar sprints: {response.status_code}")
    sprints = response.json().get("values", [])
    if filtro_nome:
        sprints = [s for s in sprints if filtro_nome.lower() in s["name"].lower()]
    return sprints

def get_status_transitions(jira_url, issue_key, headers):
    url = f"{jira_url}/rest/api/3/issue/{issue_key}?expand=changelog"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    issue = response.json()
    transitions = []
    for history in issue.get("changelog", {}).get("histories", []):
        for item in history.get("items", []):
            if item.get("field") == "status":
                change_date = datetime.strptime(history["created"], "%Y-%m-%dT%H:%M:%S.%f%z")
                transitions.append((item.get("fromString"), item.get("toString"), change_date))
    transitions.sort(key=lambda x: x[2])
    return transitions