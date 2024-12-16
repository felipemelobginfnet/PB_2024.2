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
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np

os.environ["HUGGINGFACE_HUB_TOKEN"] = "retirada"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

modelo_perguntas = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad", device=-1)

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
def carregar_dados_clima():
    try:
        df = pd.read_excel("data/dados_clima.xlsx")
        df_municipios = pd.read_excel("data/municipios_pe.xlsx", dtype="str")
        return df, df_municipios
    except FileNotFoundError:
        st.error("Arquivos de dados climáticos não encontrados. Verifique se os arquivos existem no diretório 'data'.")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def carregar_dados_historicos():
    try:
        caminho_base = os.path.join(os.getcwd(), 'venv', 'data')
        caminho_parte1 = os.path.join(caminho_base, 'HIST_CLIMA_PE_2024_Parte1.csv')
        caminho_parte2 = os.path.join(caminho_base, 'HIST_CLIMA_PE_2024_Parte2.csv')
        
        df_2024_parte1 = pd.read_csv("venv/data/HIST_CLIMA_PE_2024_Parte1.csv", sep=";")
        df_2024_parte2 = pd.read_csv("venv/data/HIST_CLIMA_PE_2024_Parte2.csv", sep=";")
        df_2024 = pd.concat([df_2024_parte1, df_2024_parte2], ignore_index=True)
        return df_2024
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
    
    df, df_municipios = carregar_dados_clima()
    
    if not df.empty:
        fig = px.line(
            df,
            x="Mês",
            y=["Temperatura Média", "Temperatura Máxima", "Temperatura Mínima"],
            title="Variação de Temperatura ao Longo do Ano"
        )
        st.plotly_chart(fig)

        st.download_button(
            "Baixar Gráfico (HTML)",
            fig.to_html(),
            "grafico_temperatura.html",
            "text/html"
        )

        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )

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
    
    | Coluna | Tipo | Descrição |
    |--------|------|-----------|
    | Município | texto | Nome do município |
    | Código | número inteiro | Código do município |
    | Temperatura | número decimal | Temperatura em °C |
    | Precipitação | número decimal | Precipitação em mm |
    """)
    
    exemplo_df = pd.DataFrame({
        "Município": ["Recife", "Olinda", "Caruaru"],
        "Código": [261160, 261110, 260410],
        "Temperatura": [28.5, 28.2, 25.8],
        "Precipitação": [150.2, 142.8, 55.4]
    })
    
    st.markdown("### Exemplo do formato esperado:")
    st.dataframe(exemplo_df, use_container_width=True)
    
    arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if arquivo:
        try:
            df_carregado = pd.read_csv(arquivo)
            if all(coluna in df_carregado.columns for coluna in ["Município", "Código", "Temperatura", "Precipitação"]):
                st.write("Prévia do arquivo:")
                st.dataframe(df_carregado.head(), use_container_width=True)
                
                if st.checkbox("Mostrar estatísticas básicas"):
                    st.write("Estatísticas descritivas:")
                    st.write(df_carregado.describe())
                
                csv_processado = df_carregado.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Baixar CSV Processado",
                    csv_processado,
                    "dados_processados.csv",
                    "text/csv"
                )
            else:
                st.error("O arquivo não contém todas as colunas necessárias. Por favor, verifique o formato do arquivo.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")

def renderizar_navegacao():
    st.sidebar.title("Navegação")
    return st.sidebar.radio(
        "Escolha uma página:",
        ["Monitoramento em Tempo Real", "Estatísticas Climáticas", "Mapa de Temperatura", "Gerenciamento de Arquivos"]
    )

def preparar_contexto_clima():
    df_historico = carregar_dados_historicos()
    
    if df_historico.empty:
        return "Não há dados climáticos disponíveis no momento."
    
    # Prepare um contexto textual detalhado sobre clima
    contexto_clima = []
    
    # Agrupe por município e calcule estatísticas
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

# Na função renderizar_pagina_mapa(), reintegre a parte de precipitação
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
            
            # Normalize precipitation for color scaling
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

# No renderizar_navegacao(), adicione um novo campo no sidebar
def renderizar_navegacao():
    st.sidebar.title("Navegação")
    sidebar_clima = st.sidebar.radio(
        "Escolha uma página:",
        ["Monitoramento em Tempo Real", "Estatísticas Climáticas", "Mapa de Temperatura", "Gerenciamento de Arquivos", "Consulta Climática"]
    )
    
    if sidebar_clima == "Consulta Climática":
        st.sidebar.header("Faça uma pergunta sobre o clima")
        pergunta_clima = st.sidebar.text_input("Pergunta sobre clima:")
        if st.sidebar.button("Enviar Pergunta"):
            if pergunta_clima:
                resposta = gerar_resposta_clima(EntradaTexto(texto=pergunta_clima))
                st.sidebar.write(resposta.resposta)
    
    return sidebar_clima

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