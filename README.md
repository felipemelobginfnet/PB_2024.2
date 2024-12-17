# Análise de Dados Climáticos em Pernambuco

## Descrição  
Este projeto consiste em uma aplicação interativa que analisa dados climáticos históricos e em tempo real de municípios de Pernambuco. A aplicação utiliza **FastAPI** para APIs e **Streamlit** como interface do usuário, oferecendo visualizações gráficas, mapas interativos e consultas personalizadas.

---

## Tecnologias Utilizadas  
- **Python**  
- **FastAPI**  
- **Streamlit**  
- **Pandas**  
- **Plotly**  
- **Pydeck**  
- **Uvicorn**

---

## Estrutura do Projeto  
- **`app.py`**: Código principal que integra a API com rotas e a aplicação Streamlit.  
- **`venv/`**: Ambiente virtual contendo as dependências do projeto.  
- **`data/`**: Diretório contendo arquivos de dados climáticos históricos.  
- **`main.py`**: Ponto de entrada para executar a aplicação.

---

## Instalação e Execução  

1. **Clone este repositório e navegue até a pasta do projeto:**  


# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # macOS / Linux
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar API FastAPI
uvicorn app:app --reload

# Em outra aba do terminal, execute a interface Streamlit
streamlit run main.py

# Acesse os serviços:
# API FastAPI: http://127.0.0.1:8000
# Aplicação Streamlit: http://localhost:8501

# Formato do Arquivo CSV Esperado
# Coluna           Tipo            Descrição
# municipio        texto           Nome do município
# data             data (YYYY-MM-DD) Data de referência
# temperatura_max  número decimal  Temperatura máxima em °C
# temperatura_min  número decimal  Temperatura mínima em °C
# temperatura_media número decimal Temperatura média em °C
# precipitacao     número decimal  Precipitação acumulada em mm

# Funcionalidades:
# - Gerenciamento de Arquivos Climáticos:
#     - Upload de arquivos CSV no formato específico.
#     - Visualização de estatísticas básicas e dados carregados.
#     - Gráficos de temperatura e precipitação por município.
#     - Download do arquivo processado.
# - Mapa Climático Interativo:
#     - Visualização de temperaturas e precipitação média em municípios de Pernambuco.
#     - Uso de Pydeck para criar mapas dinâmicos.
# - Consulta Climática:
#     - Faça perguntas sobre dados climáticos disponíveis, utilizando um modelo de linguagem para processar o contexto e gerar respostas.
# - Monitoramento em Tempo Real:
#     - Exibição dos dados climáticos atuais em municípios selecionados.

# Uso da Aplicação:
# - Gerencie seus dados climáticos: Carregue arquivos CSV e visualize gráficos e estatísticas.
# - Analise mapas interativos: Explore visualmente os dados de temperatura e precipitação em Pernambuco.
# - Faça perguntas climáticas: Utilize a interface de consulta para gerar respostas personalizadas.
# - Monitore em tempo real: Acompanhe as informações climáticas atuais de diferentes municípios.
