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
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

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

app = FastAPI(title="API COVID-19", description="API para análise de dados COVID-19")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@st.cache_data(ttl=3600)
def carregar_dados_covid():
    df = pd.read_excel("venv/data/dados_covid.xlsx")
    df_populacao = pd.read_excel("venv/data/censo_2022_populacao_municipios.xlsx", dtype="str")
    return df, df_populacao

@st.cache_data(ttl=3600)
def carregar_dados_2024():
    df_2024_parte1 = pd.read_csv("venv/data/HIST_PAINEL_COVIDBR_2024_Parte1_30ago2024.csv", sep=";",
                                 usecols=["estado", "codmun", "semanaEpi", "populacaoTCU2019", "casosAcumulado"])
    df_2024_parte2 = pd.read_csv("venv/data/HIST_PAINEL_COVIDBR_2024_Parte2_30ago2024.csv", sep=";",
                                 usecols=["estado", "codmun", "semanaEpi", "populacaoTCU2019", "casosAcumulado"])
    df_2024 = pd.concat([df_2024_parte1, df_2024_parte2], ignore_index=True)
    return df_2024

url_vacinacao = "https://minhavacina.recife.pe.gov.br/api/v1/unscheduled_vaccination_sites.json"
try:
    resposta_vacinacao = requests.get(url_vacinacao)
    if resposta_vacinacao.status_code == 200:
        dados_vacinacao = resposta_vacinacao.json()
        df_locais_vacinacao = pd.DataFrame(dados_vacinacao).drop(columns="id", axis=1)
        df_locais_vacinacao.columns = ["Local", "Público", "Bairro", "Endereço", "Horários"]
    else:
        df_locais_vacinacao = pd.DataFrame(columns=["Local", "Público", "Bairro", "Endereço", "Horários"])
except:
    df_locais_vacinacao = pd.DataFrame(columns=["Local", "Público", "Bairro", "Endereço", "Horários"])

@app.get("/locais_vacinacao/", response_model=dict)
def obter_locais_vacinacao():
    return JSONResponse(content=jsonable_encoder(df_locais_vacinacao.to_dict()))

@app.post("/resposta_locais/", response_model=SaidaTexto)
def gerar_resposta_locais(entrada: EntradaTexto):
    texto_contexto = "\n".join(df_locais_vacinacao.apply(
        lambda x: f"{x['Local']} - {x['Bairro']}: {x['Endereço']} ({x['Horários']})", axis=1))
    resposta = responder_pergunta(contexto=texto_contexto, pergunta=entrada.texto)
    return SaidaTexto(texto_original=entrada.texto, resposta=resposta)

def renderizar_pagina_vacinacao():
    st.title("Locais de Vacinação em Recife")
    
    st.dataframe(
        df_locais_vacinacao,
        use_container_width=True,
        height=400
    )

    csv_locais = df_locais_vacinacao.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar Locais de Vacinção (CSV)",
        csv_locais,
        "locais_vacinacao.csv",
        "text/csv"
    )
    
    contagem_bairros = df_locais_vacinacao["Bairro"].value_counts()
    fig_hist = px.bar(
        x=contagem_bairros.index,
        y=contagem_bairros.values,
        title="Quantidade de Locais por Bairro",
        labels={"x": "Bairro", "y": "Quantidade de Locais"}
    )
    fig_hist.update_layout(showlegend=False)
    st.plotly_chart(fig_hist)
    
    pergunta = st.text_area("Faça uma pergunta sobre os locais de vacinação:")
    if st.button("Gerar Resposta"):
        with st.spinner("Processando sua pergunta..."):
            texto_contexto = "\n".join(df_locais_vacinacao.apply(
                lambda x: f"{x['Local']} - {x['Bairro']}: {x['Endereço']} ({x['Horários']})", axis=1))
            resposta = responder_pergunta(texto_contexto, pergunta)
            st.success(f"Resposta: {resposta}")

def renderizar_pagina_estatisticas():
    st.title("Estatísticas de Vacinação no Brasil")
    
    df, df_populacao = carregar_dados_covid()
    df_populacao["codigo_6_digitos"] = df_populacao["Código municipal"].astype(str).str[:6]
    df_doses = df.groupby(["Município Ocorrência", "COD IBGE"]).sum().reset_index()
    
    df_populacao["pessoas"] = pd.to_numeric(df_populacao["pessoas"], errors="coerce")
    df_populacao.rename(columns={"pessoas": "Pessoas"}, inplace=True)
    
    df_combinado = df_doses.merge(
        df_populacao,
        how="inner",
        left_on="COD IBGE",
        right_on="codigo_6_digitos"
    )
    
    df_estados = df_combinado.groupby("UF").agg({
        "Total de Doses Aplicadas Monovalente": "sum",
        "Pessoas": "sum"
    }).reset_index()
    
    df_estados["Doses por Pessoa"] = round(
        df_estados["Total de Doses Aplicadas Monovalente"] / df_estados["Pessoas"],
        2
    )
    
    df_estados_sorted = df_estados.sort_values("Doses por Pessoa", ascending=False)
    
    fig = px.bar(
        df_estados_sorted,
        x="UF",
        y="Doses por Pessoa",
        title="Doses de Vacina por Pessoa por Estado"
    )
    st.plotly_chart(fig)

    st.download_button(
        "Baixar Gráfico (HTML)",
        fig.to_html(),
        "grafico_vacinacao.html",
        "text/html"
    )

    st.dataframe(
        df_estados_sorted,
        use_container_width=True,
        height=400
    )

    csv_estados = df_estados_sorted.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar Tabela de Estatísticas (CSV)",
        csv_estados,
        "estatisticas_vacinacao.csv",
        "text/csv"
    )
    
    pergunta = st.text_area("Faça uma pergunta sobre as estatísticas:")
    if st.button("Gerar Resposta"):
        with st.spinner("Processando sua pergunta..."):
            texto_contexto = "\n".join(df_estados_sorted.apply(
                lambda x: f"UF: {x['UF']}, Doses: {x['Total de Doses Aplicadas Monovalente']}, "
                        f"Pessoas: {x['Pessoas']}, Doses por Pessoa: {x['Doses por Pessoa']}", axis=1))
            resposta = responder_pergunta(texto_contexto, pergunta)
            st.success(f"Resposta: {resposta}")

def renderizar_pagina_mapa():
    st.title("Mapa de Casos de COVID-19")
    
    municipios_df = pd.read_csv("venv/data/municipios.csv")
    dados_2024_df = carregar_dados_2024()
    
    municipios_df["codigo_ibge_6_d"] = municipios_df["codigo_ibge"].astype(str).str[:6].astype(int)
    dados_pe_df = dados_2024_df[(dados_2024_df["semanaEpi"] != 53) & (dados_2024_df["estado"] == "PE")]
    
    dados_pe_df = dados_pe_df.merge(
        municipios_df,
        how="inner",
        left_on="codmun",
        right_on="codigo_ibge_6_d"
    )
    
    dados_pe_df["casos_por_100k"] = round(dados_pe_df["casosAcumulado"] / (dados_pe_df["populacaoTCU2019"] / 100000), 1)
    dados_pe_df["casos_normalizados"] = 5 + (70 * (dados_pe_df["casos_por_100k"] - dados_pe_df["casos_por_100k"].min()) / 
                                            (dados_pe_df["casos_por_100k"].max() - dados_pe_df["casos_por_100k"].min()))
    
    dados_mapa_df = dados_pe_df[["latitude", "longitude", "casos_normalizados", "casos_por_100k"]].copy()
    dados_mapa_df = dados_mapa_df.dropna()
    
    visualizacao = pdk.ViewState(
        latitude=-8.05428,
        longitude=-34.8813,
        zoom=5,
        pitch=0
    )
    
    camada = pdk.Layer(
        "ScatterplotLayer",
        data=dados_mapa_df,
        get_position=["longitude", "latitude"],
        get_radius=["casos_normalizados"],
        radius_scale=100,
        radius_min_pixels=5,
        radius_max_pixels=75,
        get_color=[200, 30, 0, 160],
        pickable=True
    )
    
    mapa = pdk.Deck(
        layers=[camada],
        initial_view_state=visualizacao,
        tooltip={"text": "Casos por 100k habitantes: {casos_por_100k}"}
    )
    
    st.pydeck_chart(mapa)
    
    mapa.to_html("mapa_covid.html")
    with open("mapa_covid.html", "rb") as arquivo:
        st.download_button(
            label="Baixar Mapa",
            data=arquivo,
            file_name="mapa_covid.html",
            mime="text/html"
        )

def renderizar_pagina_arquivos():
    st.title("Gerenciamento de Arquivos")
    
    st.markdown("""
    ### Formato do Arquivo CSV de Entrada
    
    | Coluna | Tipo | Descrição |
    |--------|------|-----------|
    | Município Ocorrência | texto | Nome do município |
    | COD IBGE | número inteiro | Código IBGE do município (6 dígitos) |
    | Total de Doses Aplicadas Monovalente | número inteiro | Total de doses aplicadas |
    """)
    
    exemplo_df = pd.DataFrame({
        'Município Ocorrência': ['Recife', 'Olinda', 'Jaboatão dos Guararapes'],
        'COD IBGE': [261160, 261110, 260720],
        'Total de Doses Aplicadas Monovalente': [1500000, 800000, 950000]
    })
    
    st.markdown("### Exemplo do formato esperado:")
    st.dataframe(exemplo_df, use_container_width=True)
    
    arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if arquivo:
        try:
            df_carregado = pd.read_csv(arquivo)
            colunas_necessarias = ['Município Ocorrência', 'COD IBGE', 'Total de Doses Aplicadas Monovalente']
            if all(coluna in df_carregado.columns for coluna in colunas_necessarias):
                try:
                    df_carregado['COD IBGE'] = df_carregado['COD IBGE'].astype(int)
                    df_carregado['Total de Doses Aplicadas Monovalente'] = df_carregado['Total de Doses Aplicadas Monovalente'].astype(int)
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
                except ValueError:
                    st.error("Erro nos tipos de dados. Verifique se os campos numéricos contêm apenas números.")
            else:
                st.error("O arquivo não contém todas as colunas necessárias. Por favor, verifique o formato do arquivo.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
    else:
        st.info("Aguardando upload de arquivo...")

def renderizar_navegacao():
    st.sidebar.title("Navegação")
    return st.sidebar.radio(
        "Escolha uma página:",
        ["Locais de Vacinação", "Estatísticas de Vacinação", "Mapa de Casos de COVID-19", "Gerenciamento de Arquivos"]
    )

pagina = renderizar_navegacao()

if pagina == "Locais de Vacinação":
    renderizar_pagina_vacinacao()
elif pagina == "Estatísticas de Vacinação":
    renderizar_pagina_estatisticas()
elif pagina == "Mapa de Casos de COVID-19":
    renderizar_pagina_mapa()
elif pagina == "Gerenciamento de Arquivos":
    renderizar_pagina_arquivos()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)