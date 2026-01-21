# 📊 JIRA Agile Metrics Dashboard

Uma aplicação interativa desenvolvida em **Python** e **Streamlit** para visualização e análise de métricas ágeis extraídas diretamente da API do JIRA. O sistema permite monitorar o progresso de múltiplos projetos, performance de desenvolvedores e saúde das sprints em tempo real.

## 🚀 Funcionalidades

* **Multiprojeto:** Suporte para alternar entre diferentes projetos (ex: PROJETO 1, PROJETO 2) através da barra lateral.
* **Gestão de Sprints:** Visualização detalhada de datas e status das sprints.
* **Burndown Chart:** Acompanhamento visual da evolução da sprint atual.
* **Análise de Performance:**
    * Métricas de entregas individuais por desenvolvedor.
    * Desempenho histórico consolidado por sprint.
    * Rastreamento de transições de status de issues (changelog).
* **Otimização de Dados:** Sistema de cache inteligente com TTL (Time To Live) para reduzir chamadas desnecessárias à API.
* **Monitoramento de Performance:** Painel na barra lateral que exibe o tempo de execução das funções de carregamento.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.x
* **Framework Web:** Streamlit
* **Integração:** JIRA REST API v3
* **Autenticação:** Basic Auth (Base64) via API Token
* **Gerenciamento de Ambiente:** Python-dotenv

## ⚙️ Configuração e Instalação

### 1. Requisitos
* Python 3.8+
* API Token do JIRA (gerado no Atlassian ID)

### 2. Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto com as seguintes chaves:

```env
# Configurações Projeto 1
email_projeto1=seu_email@empresa.com
api_token_projeto1=seu_token_aqui
url_projeto1=[https://sua-instancia.atlassian.net](https://sua-instancia.atlassian.net)
board_projeto1=ID_DO_BOARD_1

# Configurações Projeto 2
email_projeto2=seu_email@empresa.com
api_token_projeto2=seu_token_aqui
url_projeto2=[https://sua-instancia.atlassian.net](https://sua-instancia.atlassian.net)
board_projeto2=ID_DO_BOARD_2
```


### 3. Instalação
Siga os comandos abaixo no seu terminal para preparar o ambiente:

#### Clone o repositório
```
git clone https://github.com/dsnasciimento/jira-analytics-dashboard
```

#### Entre na pasta do projeto
```
cd jira-analytics-dashboard
```

####  Instale as dependências
```
pip install venv .venv
```
```
pip install requirements.txt
```
### 4. Execução
Para iniciar a aplicação, utilize o comando:

```
streamlit run app.py
```
