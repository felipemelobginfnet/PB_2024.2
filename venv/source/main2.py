import pandas as pd
import streamlit as st
import pydeck as pdk
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import uvicorn
from transformers import pipeline
import os
import requests
import plotly.express as px
import time
from datetime import datetime, timedelta


os.environ["HUGGINGFACE_HUB_TOKEN"] = "retirada"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

modelo_perguntas = pipeline(
    "question-answering", 
    model="deepset/roberta-base-squad2",  
    tokenizer="deepset/roberta-base-squad2",  
    device=-1  
)

def coletar_dados_historicos_pe():
    """
    Coleta dados históricos dos últimos 60 dias para municípios de Pernambuco
    usando a API do Open-Meteo.
    """
    
    municipios = [
        {"nome": "Recife", "lat": -8.05428, "lon": -34.8813},
        {"nome": "Caruaru", "lat": -8.28917, "lon": -35.97361},
        {"nome": "Petrolina", "lat": -9.38722, "lon": -40.50083},
        {"nome": "Garanhuns", "lat": -8.88238, "lon": -36.49539},
        {"nome": "Serra Talhada", "lat": -7.98543, "lon": -38.28981},
        {"nome": "Salgueiro", "lat": -8.07364, "lon": -39.12462},
        {"nome": "Araripina", "lat": -7.57501, "lon": -40.49419},
        {"nome": "Goiana", "lat": -7.55890, "lon": -35.00275},
        {"nome": "Timbaúba", "lat": -7.50524, "lon": -35.31504},
        {"nome": "Palmares", "lat": -8.68423, "lon": -35.58962}
    ]
    
 
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=60)
    

    data_inicio_str = data_inicio.strftime("%Y-%m-%d")
    data_fim_str = data_fim.strftime("%Y-%m-%d")
    
    dados_historicos = []
    
    for municipio in municipios:
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={municipio['lat']}&longitude={municipio['lon']}&"
            f"start_date={data_inicio_str}&end_date={data_fim_str}&"
            f"daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
            f"precipitation_sum&timezone=America/Recife"
        )
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                dados = response.json()
                
                for i, data in enumerate(dados["daily"]["time"]):
                    dados_historicos.append({
                        "municipio": municipio["nome"],
                        "data": data,
                        "temperatura_max": dados["daily"]["temperature_2m_max"][i],
                        "temperatura_min": dados["daily"]["temperature_2m_min"][i],
                        "temperatura_media": dados["daily"]["temperature_2m_mean"][i],
                        "precipitacao": dados["daily"]["precipitation_sum"][i]
                    })
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Erro ao coletar dados de {municipio['nome']}: {str(e)}")
    
    df = pd.DataFrame(dados_historicos)
    

    df.to_csv("venv/data/HIST_CLIMA_PE_2024_Parte1.csv", sep=";", index=False)

    
    return df


def responder_pergunta(contexto, pergunta):
    if not contexto or not pergunta:
        return "Por favor, forneça um contexto e uma pergunta válidos."
    resposta = modelo_perguntas(question=pergunta, context=contexto)
    return resposta["answer"]

class EntradaTexto(BaseModel):
    texto: str

class SaidaTexto(BaseModel):
    texto_original: str
    resposta: str

app = FastAPI(title="API Clima PE", description="API para análise de dados climáticos de Pernambuco")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@st.cache_data(ttl=3600)
def carregar_dados_historicos():
    try:       
        df_2024_parte1 = pd.read_csv("venv/data/HIST_CLIMA_PE_2024_Parte1.csv", sep=";")

        return df_2024_parte1
    except FileNotFoundError:
        st.error("Arquivos de dados históricos não encontrados. Verifique se os arquivos existem no diretório 'venv/data'.")
        return pd.DataFrame()
    except ValueError as e:
        st.error(f"Erro ao carregar dados históricos: {str(e)}")
        return pd.DataFrame()

def obter_dados_climaticos(latitude, longitude):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    try:
        resposta = requests.get(url)
        if resposta.status_code == 200:
            return resposta.json()
        return None
    except:
        return None

df_estacoes = pd.DataFrame({
    "Local": ["Recife", "Olinda", "Caruaru", "Petrolina", "Garanhuns"],
    "Latitude": [-8.05428, -7.99619, -8.28917, -9.38722, -8.88238],
    "Longitude": [-34.8813, -34.85500, -35.97361, -40.50083, -36.49539],
    "Tipo": ["Estação Principal", "Estação Secundária", "Estação Principal", "Estação Principal", "Estação Secundária"]
})

def criar_card_clima(local, temperatura, vel_vento, dir_vento):
    with st.container():
        st.markdown(f"""
        <div style="
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #333;
            background-color: black;
            margin: 10px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            color: white;">
            <h3 style="margin: 0 0 10px 0; color: #00ff00;">{local}</h3>
            <p style="margin: 5px 0;">🌡️ Temperatura: {temperatura}°C</p>
            <p style="margin: 5px 0;">💨 Vel. Vento: {vel_vento} km/h</p>
            <p style="margin: 5px 0;">🧭 Dir. Vento: {dir_vento}°</p>
        </div>
        """, unsafe_allow_html=True)

def renderizar_pagina_monitoramento():
    st.title("Monitoramento Climático em Tempo Real - Pernambuco")
    
    dados_clima = []
    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]
    
    for i, (_, estacao) in enumerate(df_estacoes.iterrows()):
        clima = obter_dados_climaticos(estacao["Latitude"], estacao["Longitude"])
        if clima:
            dados_clima.append({
                "Local": estacao["Local"],
                "Temperatura": clima["current_weather"]["temperature"],
                "Velocidade do Vento": clima["current_weather"]["windspeed"],
                "Direção do Vento": clima["current_weather"]["winddirection"]
            })
            
            with columns[i]:
                criar_card_clima(
                    estacao["Local"],
                    clima["current_weather"]["temperature"],
                    clima["current_weather"]["windspeed"],
                    clima["current_weather"]["winddirection"]
                )
    
    df_clima_atual = pd.DataFrame(dados_clima)
    
    st.subheader("Dados Detalhados")
    st.dataframe(
        df_clima_atual,
        use_container_width=True,
        height=200
    )

    csv_clima = df_clima_atual.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar Dados Climáticos (CSV)",
        csv_clima,
        "dados_climaticos.csv",
        "text/csv"
    )
    
    fig_temp = px.bar(
        df_clima_atual,
        x="Local",
        y="Temperatura",
        title="Temperatura Atual por Cidade",
        labels={"Local": "Cidade", "Temperatura": "Temperatura (°C)"}
    )
    st.plotly_chart(fig_temp)

def renderizar_pagina_estatisticas():
    st.title("Estatísticas Climáticas de Pernambuco")
    
    df_historico = carregar_dados_historicos()
    
    if not df_historico.empty:
        df_historico['data'] = pd.to_datetime(df_historico['data'])
        df_historico['mes'] = df_historico['data'].dt.strftime('%Y-%m')

        municipios = df_historico['municipio'].unique()
        selecao_municipios = st.multiselect("Selecione até 3 municípios:", municipios, max_selections=3)

        if selecao_municipios:

            df_filtrado = df_historico[df_historico['municipio'].isin(selecao_municipios)]

            tipo_temperatura = st.selectbox(
                "Escolha o tipo de temperatura:",
                ["Temperatura Máxima", "Temperatura Média", "Temperatura Mínima"]
            )
            coluna_temperatura = {
                "Temperatura Máxima": "temperatura_max",
                "Temperatura Média": "temperatura_media",
                "Temperatura Mínima": "temperatura_min"
            }[tipo_temperatura]

            estatisticas_mensais = df_filtrado.groupby(['mes', 'municipio']).agg({
                coluna_temperatura: 'mean',
                'precipitacao': 'sum'
            }).reset_index()

            st.subheader(f"Variação de {tipo_temperatura} ao Longo dos Meses")
            fig_temp = px.line(
                estatisticas_mensais,
                x="mes",
                y=coluna_temperatura,
                color="municipio",
                title=f"Variação de {tipo_temperatura} ao Longo dos Meses",
                labels={"mes": "Mês", "value": f"{tipo_temperatura} (°C)", "municipio": "Município"}
            )
            st.plotly_chart(fig_temp)


            st.subheader("Precipitação Dia a Dia")
            fig_precipitacao = px.line(
                df_filtrado,
                x="data",
                y="precipitacao",
                color="municipio",
                title="Precipitação Dia a Dia",
                labels={"data": "Data", "precipitacao": "Precipitação (mm)", "municipio": "Município"}
            )
            st.plotly_chart(fig_precipitacao)


            st.subheader("Estatísticas Agregadas por Município")
            estatisticas = df_filtrado.groupby('municipio').agg({
                'temperatura_media': 'mean',
                'temperatura_max': 'max',
                'temperatura_min': 'min',
                'precipitacao': 'sum'
            }).reset_index()
            st.dataframe(estatisticas)

            st.download_button(
                "Baixar Gráfico de Variação de Temperatura (HTML)",
                fig_temp.to_html(),
                "grafico_variacao_temperatura.html",
                "text/html"
            )

        else:
            st.warning("Selecione pelo menos uma cidade para visualizar as estatísticas.")
    else:
        st.warning("Nenhum dado histórico encontrado.")


def renderizar_pagina_mapa():
    st.title("Mapa Climático de Pernambuco")
    
    municipios_pe = [
        {"nome": "Recife", "lat": -8.05428, "lon": -34.8813},
        {"nome": "Caruaru", "lat": -8.28917, "lon": -35.97361},
        {"nome": "Petrolina", "lat": -9.38722, "lon": -40.50083},
        {"nome": "Garanhuns", "lat": -8.88238, "lon": -36.49539},
        {"nome": "Serra Talhada", "lat": -7.98543, "lon": -38.28981},
        {"nome": "Salgueiro", "lat": -8.07364, "lon": -39.12462},
        {"nome": "Araripina", "lat": -7.57501, "lon": -40.49419},
        {"nome": "Goiana", "lat": -7.55890, "lon": -35.00275},
        {"nome": "Timbaúba", "lat": -7.50524, "lon": -35.31504},
        {"nome": "Palmares", "lat": -8.68423, "lon": -35.58962}
    ]
    
    df_historico = carregar_dados_historicos()
    dados_mapa = []
    
    if not df_historico.empty:
        for municipio in municipios_pe:
            clima_atual = obter_dados_climaticos(municipio["lat"], municipio["lon"])
            
            dados_municipio = df_historico[df_historico["municipio"] == municipio["nome"]]
            precipitacao_media = dados_municipio["precipitacao"].mean() if not dados_municipio.empty else 0
            
            if clima_atual:
                temp = clima_atual["current_weather"]["temperature"]
                dados_mapa.append({
                    "latitude": municipio["lat"],
                    "longitude": municipio["lon"],
                    "temperatura": temp,
                    "precipitacao": precipitacao_media,
                    "nome": municipio["nome"]
                })
        
        dados_mapa_df = pd.DataFrame(dados_mapa)
        dados_mapa_df["cor"] = dados_mapa_df["temperatura"].apply(
            lambda x: [200, 30, 0, 160] if x >= 30 else 
            ([255, 165, 0, 160] if x >= 26 else [0, 0, 255, 160])
        )

        visualizacao = pdk.ViewState(
            latitude=-8.05428, 
            longitude=-34.8813, 
            zoom=6, 
            pitch=0
        )
        
        camada = pdk.Layer(
            "ScatterplotLayer", 
            data=dados_mapa_df, 
            get_position=["longitude", "latitude"], 
            get_color="cor",
            get_radius=5,
            radius_min_pixels=5,
            radius_max_pixels=10,
            pickable=True
        )
        
        mapa = pdk.Deck(
            layers=[camada], 
            initial_view_state=visualizacao, 
            tooltip={"text": "{nome}\nTemperatura: {temperatura}°C"}
        )
        
        st.pydeck_chart(mapa)

def renderizar_pagina_arquivos():
    st.title("Gerenciamento de Arquivos Climáticos")

    st.markdown("""
    ### Formato do Arquivo CSV de Entrada
    
    | Coluna             | Tipo           | Descrição                              |
    |--------------------|----------------|----------------------------------------|
    | Município          | texto          | Nome do município                      |
    | Data               | data (YYYY-MM-DD) | Data de referência                      |
    | Temperatura Máxima | número decimal | Temperatura máxima em °C               |
    | Temperatura Mínima | número decimal | Temperatura mínima em °C               |
    | Temperatura Média  | número decimal | Temperatura média em °C                |
    | Precipitação       | número decimal | Precipitação acumulada em mm           |
    """)

    exemplo_df = pd.DataFrame({
        "municipio": ["Recife", "Olinda", "Caruaru"],
        "data": ["2024-01-01", "2024-01-01", "2024-01-01"],
        "temperatura_max": [32.5, 31.2, 30.1],
        "temperatura_min": [22.4, 21.8, 20.5],
        "temperatura_media": [27.4, 26.5, 25.3],
        "precipitacao": [120.5, 105.0, 85.3]
    })

    st.markdown("### Exemplo do formato esperado:")
    st.dataframe(exemplo_df, use_container_width=True)

    arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if arquivo:
        try:
            df_carregado = pd.read_csv(arquivo, sep=";")

            colunas_necessarias = ["municipio", "data", "temperatura_max", "temperatura_min", "temperatura_media", "precipitacao"]
            if list(df_carregado.columns) == colunas_necessarias:
                st.write("Prévia do arquivo:")
                st.dataframe(df_carregado.head(), use_container_width=True)

                if st.checkbox("Mostrar estatísticas básicas"):
                    st.write("Estatísticas descritivas:")
                    st.write(df_carregado.describe())

                df_carregado['data'] = pd.to_datetime(df_carregado['data'])

                municipios = df_carregado['municipio'].unique()
                selecao_municipios = st.multiselect("Selecione até 3 municípios:", municipios, max_selections=3)

                if selecao_municipios:
                    df_filtrado = df_carregado[df_carregado['municipio'].isin(selecao_municipios)]

                    tipo_temperatura = st.selectbox(
                        "Escolha o tipo de temperatura:",
                        ["Temperatura Máxima", "Temperatura Média", "Temperatura Mínima"]
                    )
                    coluna_temperatura = {
                        "Temperatura Máxima": "temperatura_max",
                        "Temperatura Média": "temperatura_media",
                        "Temperatura Mínima": "temperatura_min"
                    }[tipo_temperatura]

                    fig_temp = px.line(
                        df_filtrado,
                        x="data",
                        y=coluna_temperatura,
                        color="municipio",
                        title=f"Variação de {tipo_temperatura} ao Longo do Tempo",
                        labels={"data": "Data", "value": f"{tipo_temperatura} (°C)", "municipio": "Município"}
                    )
                    st.plotly_chart(fig_temp)

                    fig_precipitacao = px.line(
                        df_filtrado,
                        x="data",
                        y="precipitacao",
                        color="municipio",
                        title="Precipitação ao Longo do Tempo",
                        labels={"data": "Data", "precipitacao": "Precipitação (mm)", "municipio": "Município"}
                    )
                    st.plotly_chart(fig_precipitacao)

                    estatisticas = df_filtrado.groupby('municipio').agg({
                        'temperatura_media': 'mean',
                        'temperatura_max': 'max',
                        'temperatura_min': 'min',
                        'precipitacao': 'sum'
                    }).reset_index()
                    st.subheader("Estatísticas Agregadas por Município")
                    st.dataframe(estatisticas)

                    csv_processado = df_filtrado.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Baixar CSV Processado",
                        csv_processado,
                        "dados_processados.csv",
                        "text/csv"
                    )

                else:
                    st.warning("Selecione pelo menos um município para visualizar as estatísticas.")
            else:
                st.error(f"O arquivo não contém exatamente as colunas necessárias. As colunas esperadas são: {', '.join(colunas_necessarias)}. Por favor, verifique o formato do arquivo.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")

def renderizar_navegacao():
    st.sidebar.title("Navegação")
    return st.sidebar.radio(
        "Escolha uma página:",
        ["Monitoramento em Tempo Real", "Estatísticas Climáticas", "Mapa de Temperatura", "Gerenciamento de Arquivos", "Consulta Climática"]
    )
def preparar_contexto_clima():
    df_historico = carregar_dados_historicos()
    
    if df_historico.empty:
        return "Não há dados climáticos disponíveis no momento."
    

    contexto_clima = []    

    estatisticas_municipios = df_historico.groupby('municipio').agg({
        'temperatura': ['mean', 'max', 'min'],
        'precipitacao': ['mean', 'max', 'min']
    }).reset_index()
    
    for _, row in estatisticas_municipios.iterrows():
        municipio = row['municipio']
        temp_media = round(row[('temperatura', 'mean')], 1)
        temp_max = round(row[('temperatura', 'max')], 1)
        temp_min = round(row[('temperatura', 'min')], 1)
        prec_media = round(row[('precipitacao', 'mean')], 1)
        prec_max = round(row[('precipitacao', 'max')], 1)
        
        info_municipio = (
            f"Município de {municipio}: "
            f"Temperatura média de {temp_media}°C, "
            f"variando entre {temp_min}°C e {temp_max}°C. "
            f"Precipitação média de {prec_media}mm, "
            f"com máxima de {prec_max}mm."
        )
        contexto_clima.append(info_municipio)
    
    return "\n".join(contexto_clima)

@app.post("/resposta_clima/", response_model=SaidaTexto)
def gerar_resposta_clima(entrada: EntradaTexto):
    contexto_clima = preparar_contexto_clima()
    resposta = responder_pergunta(
        contexto=contexto_clima, 
        pergunta=entrada.texto
    )
    return SaidaTexto(texto_original=entrada.texto, resposta=resposta)

def renderizar_pagina_consulta_climatica():
    st.title("Consulta Climática")
    st.write("Faça uma pergunta sobre os dados climáticos disponíveis.")

    try:
        df_clima = pd.read_csv("venv/data/HIST_CLIMA_PE_2024_Parte1.csv", sep=";")
    except FileNotFoundError:
        st.error("Erro: Arquivo de dados climáticos não encontrado. Verifique o caminho do arquivo.")
        return
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return

    st.subheader("Dados Climáticos")
    st.dataframe(df_clima)  

    pergunta = st.text_area("Faça uma pergunta sobre o clima:")

    if st.button("Gerar Resposta"):
        if pergunta:
            with st.spinner("Processando sua pergunta..."):
                texto_contexto = "\n".join(df_clima.apply(
                    lambda x: f"Município: {x['municipio']}, Data: {x['data']}, "
                              f"Temperatura Máxima: {x['temperatura_max']}°C, "
                              f"Temperatura Mínima: {x['temperatura_min']}°C, "
                              f"Temperatura Média: {x['temperatura_media']}°C, "
                              f"Precipitação: {x['precipitacao']}mm", axis=1))

                resposta = responder_pergunta(contexto=texto_contexto, pergunta=pergunta)

                st.subheader("Resposta")
                st.success(resposta)
        else:
            st.warning("Por favor, insira uma pergunta válida.")


def renderizar_pagina_mapa():
    st.title("Mapa Climático de Pernambuco")
    
    municipios_pe = [
        {"nome": "Recife", "lat": -8.05428, "lon": -34.8813},
        {"nome": "Caruaru", "lat": -8.28917, "lon": -35.97361},
        {"nome": "Petrolina", "lat": -9.38722, "lon": -40.50083},
        {"nome": "Garanhuns", "lat": -8.88238, "lon": -36.49539},
        {"nome": "Serra Talhada", "lat": -7.98543, "lon": -38.28981},
        {"nome": "Salgueiro", "lat": -8.07364, "lon": -39.12462},
        {"nome": "Araripina", "lat": -7.57501, "lon": -40.49419},
        {"nome": "Goiana", "lat": -7.55890, "lon": -35.00275},
        {"nome": "Timbaúba", "lat": -7.50524, "lon": -35.31504},
        {"nome": "Palmares", "lat": -8.68423, "lon": -35.58962}
    ]
    
    df_historico = carregar_dados_historicos()
    dados_mapa = []
    
    if not df_historico.empty:
        for municipio in municipios_pe:
            clima_atual = obter_dados_climaticos(municipio["lat"], municipio["lon"])
            
            dados_municipio = df_historico[df_historico["municipio"] == municipio["nome"]]
            precipitacao_media = dados_municipio["precipitacao"].mean() if not dados_municipio.empty else 0
            
            if clima_atual:
                temp = clima_atual["current_weather"]["temperature"]
                dados_mapa.append({
                    "latitude": municipio["lat"],
                    "longitude": municipio["lon"],
                    "temperatura": temp,
                    "precipitacao": precipitacao_media,
                    "nome": municipio["nome"]
                })
        
        dados_mapa_df = pd.DataFrame(dados_mapa)
        dados_mapa_df["cor"] = dados_mapa_df["temperatura"].apply(
            lambda x: [200, 30, 0, 160] if x >= 30 else 
            ([255, 165, 0, 160] if x >= 26 else [0, 0, 255, 160])
        )

        aba_temp, aba_prec = st.tabs(["Temperatura", "Precipitação"])
        
        with aba_temp:
            st.subheader("Mapa de Temperaturas")
            
            visualizacao_temp = pdk.ViewState(
                latitude=-8.05428, 
                longitude=-34.8813, 
                zoom=6, 
                pitch=0
            )
            
            camada_temp = pdk.Layer(
                "ScatterplotLayer", 
                data=dados_mapa_df, 
                get_position=["longitude", "latitude"], 
                get_color="cor",
                get_radius=5,
                radius_min_pixels=5,
                radius_max_pixels=10,
                pickable=True
            )
            
            mapa_temp = pdk.Deck(
                layers=[camada_temp], 
                initial_view_state=visualizacao_temp, 
                tooltip={"text": "{nome}\nTemperatura: {temperatura}°C"}
            )
            
            st.pydeck_chart(mapa_temp)

        with aba_prec:
            st.subheader("Mapa de Precipitação Média")
            
            visualizacao_prec = pdk.ViewState(
                latitude=-8.05428, 
                longitude=-34.8813, 
                zoom=6, 
                pitch=0
            )
            
           
            dados_mapa_df["prec_normalizada"] = (dados_mapa_df["precipitacao"] - dados_mapa_df["precipitacao"].min()) / \
                (dados_mapa_df["precipitacao"].max() - dados_mapa_df["precipitacao"].min())
            
            camada_prec = pdk.Layer(
                "ScatterplotLayer", 
                data=dados_mapa_df, 
                get_position=["longitude", "latitude"], 
                get_color=["0", "prec_normalizada * 255", "prec_normalizada * 150", "180"],
                get_radius=5,
                radius_min_pixels=5,
                radius_max_pixels=10,
                pickable=True
            )
            
            mapa_prec = pdk.Deck(
                layers=[camada_prec], 
                initial_view_state=visualizacao_prec, 
                tooltip={"text": "{nome}\nPrecipitação Média: {precipitacao:.2f}mm"}
            )
            
            st.pydeck_chart(mapa_prec)



def main():
    st.set_page_config(
        page_title="Dashboard Climático - Pernambuco",
        page_icon="🌡️",
        layout="wide"
    )
    
    pagina = renderizar_navegacao()

    if pagina == "Monitoramento em Tempo Real":
        renderizar_pagina_monitoramento()
    elif pagina == "Estatísticas Climáticas":
        renderizar_pagina_estatisticas()
    elif pagina == "Mapa de Temperatura":
        renderizar_pagina_mapa()
    elif pagina == "Gerenciamento de Arquivos":
        renderizar_pagina_arquivos()
    elif pagina == "Consulta Climática":
        renderizar_pagina_consulta_climatica()    

@app.get("/clima/{latitude}/{longitude}")
async def obter_clima(latitude: float, longitude: float):
    try:
        dados = obter_dados_climaticos(latitude, longitude)
        if dados:
            return JSONResponse(content=jsonable_encoder(dados))
        raise HTTPException(status_code=404, detail="Dados climáticos não encontrados")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/perguntas/")
async def processar_pergunta(entrada: EntradaTexto):
    try:
        resposta = responder_pergunta(entrada.texto, "Qual é o clima?")
        return SaidaTexto(texto_original=entrada.texto, resposta=resposta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    main()
