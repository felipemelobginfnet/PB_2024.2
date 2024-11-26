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
from io import BytesIO
import os

# Configuração do token da Hugging Face
os.environ["HUGGINGFACE_HUB_TOKEN"] = "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"

# Modelos para FastAPI
class TextoEntrada(BaseModel):
    texto: str

class TextoSaida(BaseModel):
    texto_original: str
    resposta: str

# Inicialização da API
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Pipeline de análise de LLMs
modelo_generativo = pipeline("text-generation", model="pierreguillou/gpt2-small-portuguese", device=-1)
modelo_sumarizacao = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)

# Cache de dados
@st.cache_data
def carregar_dados_covid():
    df = pd.read_excel("venv/data/dados_covid.xlsx")
    df_populacao = pd.read_excel("venv/data/censo_2022_populacao_municipios.xlsx", dtype="str")
    return df, df_populacao

@st.cache_data
def carregar_dados_2024():
    df_2024 = pd.read_csv("venv/data/HIST_PAINEL_COVIDBR_2024_Parte1_30ago2024.csv", sep=";")
    df_2024_2 = pd.read_csv("venv/data/HIST_PAINEL_COVIDBR_2024_Parte2_30ago2024.csv", sep=";")
    df_2024 = pd.concat([df_2024, df_2024_2], ignore_index=True)
    return df_2024

# Carregamento inicial de dados
df, df_populacao = carregar_dados_covid()
df_2024 = carregar_dados_2024()

# Rotas da API
@app.get("/dados/", response_model=dict)
def ler_dados():
    return JSONResponse(content=jsonable_encoder(df.to_dict()))

@app.post("/gerar_resposta/", response_model=TextoSaida)
def gerar_resposta(entrada: TextoEntrada):
    try:
        resultado = modelo_generativo(
            entrada.texto,
            max_length=100,
            num_return_sequences=1,
            do_sample=True,
            top_k=50,
            top_p=0.95
        )[0]
        return {
            "texto_original": entrada.texto,
            "resposta": resultado["generated_text"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta: {str(e)}")

@app.post("/sumarizar/", response_model=TextoSaida)
def sumarizar_texto(entrada: TextoEntrada):
    try:
        resultado = modelo_sumarizacao(entrada.texto, max_length=50, min_length=25, do_sample=False)[0]
        return {
            "texto_original": entrada.texto,
            "resposta": resultado["summary_text"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sumarizar texto: {str(e)}")

# Funções de renderização do Streamlit
def render_pagina_1():
    st.title("Estatísticas de Vacinação no Brasil")
    df_populacao["COD 6 DIGITOS"] = df_populacao["Código municipal"].apply(lambda x: x[:6])
    df_doses_agrupado = df.groupby(["Município Ocorrência", "COD IBGE"]).sum().reset_index()
    df_populacao["pessoas"] = df_populacao["pessoas"].astype(int)
    df_populacao.rename(columns={"pessoas": "Pessoas"}, inplace=True)
    df_mergiado = df_doses_agrupado.merge(df_populacao, how="inner", left_on="COD IBGE", right_on="COD 6 DIGITOS")
    df_estados_agrupados = df_mergiado[["Total de Doses Aplicadas Monovalente", "UF", "Pessoas"]]
    df_estados_agrupados = df_estados_agrupados.groupby("UF").sum().reset_index()
    df_estados_agrupados["Doses por Pessoa"] = round(df_estados_agrupados["Total de Doses Aplicadas Monovalente"]/df_estados_agrupados["Pessoas"], 2)
    st.table(df_estados_agrupados)

def render_pagina_2():
    st.title("Mapa de Casos de COVID-19")
    municipios = pd.read_csv("venv/data/municipios.csv")
    municipios["codigo_ibge_6_d"] = municipios["codigo_ibge"].astype(str).apply(lambda x: x[:6]).astype(int)
    df_pe = df_2024[(df_2024["estado"] == "PE") & (df_2024["semanaEpi"] != 53)]
    df_pe = df_pe.merge(municipios, how="inner", left_on="codmun", right_on="codigo_ibge_6_d")
    df_pe["casos_por_100k"] = df_pe["casosAcumulado"] / (df_pe["populacaoTCU2019"] / 100000)
    view_state = pdk.ViewState(latitude=-8.05428, longitude=-34.8813, zoom=5)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_pe[["latitude", "longitude", "casos_por_100k"]],
        get_position=["longitude", "latitude"],
        get_radius="casos_por_100k / 10",
        radius_scale=3.5,
        get_color="[200, 30, 0, 160]",
        pickable=True
    )
    r = pdk.Deck(layers=[layer], initial_view_state=view_state)
    st.pydeck_chart(r)

def render_pagina_3():
    st.title("Upload e Download de Arquivos")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if uploaded_file:
        df_uploaded = pd.read_csv(uploaded_file)
        st.write("Arquivo carregado com sucesso!")
        st.write(df_uploaded)
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label="Baixar dados de vacinação",
        data=buffer,
        file_name="dados_vacinacao.csv",
        mime="text/csv"
    )

def render_pagina_4():
    st.title("Memória Conversacional e Sumarização")
    input_text = st.text_area("Digite seu texto:")
    if st.button("Gerar Resposta"):
        try:
            resultado = modelo_generativo(input_text, max_length=100, num_return_sequences=1, do_sample=True, top_k=50, top_p=0.95)[0]
            st.write("Resposta Gerada:", resultado["generated_text"])
        except Exception as e:
            st.error(f"Erro: {e}")

    if st.button("Sumarizar Texto"):
        try:
            resultado = modelo_sumarizacao(input_text, max_length=50, min_length=25, do_sample=False)[0]
            st.write("Texto Sumarizado:", resultado["summary_text"])
        except Exception as e:
            st.error(f"Erro: {e}")

# Navegação entre páginas
pagina_selecionada = st.sidebar.radio("Navegação", ["Estatísticas", "Mapa", "Upload e Download", "IA (Memória e Sumarização)"])

if pagina_selecionada == "Estatísticas":
    render_pagina_1()
elif pagina_selecionada == "Mapa":
    render_pagina_2()
elif pagina_selecionada == "Upload e Download":
    render_pagina_3()
elif pagina_selecionada == "IA (Memória e Sumarização)":
    render_pagina_4()

# Inicialização da API
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
