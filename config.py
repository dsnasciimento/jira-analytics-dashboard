import os
import base64
from dotenv import load_dotenv

load_dotenv()

def get_env_int(var_name, default=0):
    value = os.getenv(var_name)
    if value and value.isdigit():
        return int(value)
    return default

PROJETOS = {
    "PROJETO 1": {
        "email": os.getenv("email_projeto1"),
        "api_token": os.getenv("api_token_projeto1"),
        "url": os.getenv("url_projeto1"),
        "board_id": get_env_int("board_projeto1"),
    },
    "PROJETO 2": {
        "email": os.getenv("email_projeto2"),
        "api_token": os.getenv("api_token_projeto2"),
        "url": os.getenv("url_projeto2"),
        "board_id": get_env_int("board_projeto2"),
    }
}

def get_projeto_config(nome_projeto):
    config = PROJETOS.get(nome_projeto)
    if not config:
        raise ValueError("Projeto inválido ou não configurado.")
    
    if not config['email'] or not config['api_token']:
        raise ValueError(f"Credenciais (email ou token) não encontradas para {nome_projeto} no arquivo .env")

    auth_string = f"{config['email']}:{config['api_token']}"
    auth_value = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_value}",
        "Content-Type": "application/json"
    }
    
    return config['url'], config['board_id'], headers