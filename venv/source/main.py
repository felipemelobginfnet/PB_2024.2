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

class TextoEntrada(BaseModel):
    texto: str

class TextoSaida(BaseModel):
    texto_original: str
    analise: str
    probabilidade: float

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

modelo_sentimento = pipeline(
    "sentiment-analysis",
    model="pierreguillou/bert-base-cased-sentiment-br",
    framework="pt" 
)

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

df, df_populacao = carregar_dados_covid()
df_2024 = carregar_dados_2024()

@app.get("/dados/", response_model=dict)
def ler_dados():
    return JSONResponse(content=jsonable_encoder(df.to_dict()))

@app.post("/envio/", response_model=dict)
def enviar_dados(item: dict):
    return {"status": "Dados recebidos com sucesso", "dados": item}

@app.post("/processar_texto/", response_model=TextoSaida)
def processar_texto(entrada: TextoEntrada):
    try:
        resultado = modelo_sentimento(entrada.texto)[0]
        return {
            "texto_original": entrada.texto,
            "analise": resultado["label"],
            "probabilidade": round(resultado["score"], 6)
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao processar o texto")

def render_pagina_1():
    st.title("Estatísticas Vacinação do Brasil")
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
    st.title("Informativos de Vacinação para Sua Segurança")
    st.subheader("Mapa de Densidade Populacional Ajustada para Casos de COVID-19 em PE")
    municipios = pd.read_csv("venv/data/municipios.csv")
    municipios["codigo_ibge_6_d"] = municipios["codigo_ibge"].astype(str).apply(lambda x: x[:6]).astype(int)
    df_pe = df_2024[(df_2024["estado"]=="PE") & (df_2024["semanaEpi"] != 53)]
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
    st.download_button(
        label="Baixar dados de vacinação",
        data=df.to_csv(index=False),
        file_name="dados_vacinacao.csv",
        mime="text/csv"
    )

pagina_selecionada = "Mapa"

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Estatísticas"):
        pagina_selecionada = "Estatísticas"
with col2:
    if st.button("Mapa"):
        pagina_selecionada = "Mapa"
with col3:
    if st.button("Upload e Download"):
        pagina_selecionada = "Upload e Download"

if pagina_selecionada == "Estatísticas":
    render_pagina_1()
elif pagina_selecionada == "Mapa":
    render_pagina_2()
elif pagina_selecionada == "Upload e Download":
    render_pagina_3()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
