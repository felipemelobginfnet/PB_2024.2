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

os.environ["HUGGINGFACE_HUB_TOKEN"] = "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"
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

modelo_qa = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad", device=-1)

def responder_pergunta(contexto, pergunta):
    try:
        resposta = modelo_qa(question=pergunta, context=contexto)
        return resposta['answer']
    except Exception as e:
        return str(e)

class TextoEntrada(BaseModel):
    texto: str

class TextoSaida(BaseModel):
    texto_original: str
    resposta: str

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

try:
    df, df_populacao = carregar_dados_covid()
    df_2024 = carregar_dados_2024()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")

url_locais_vacinacao = "https://minhavacina.recife.pe.gov.br/api/v1/unscheduled_vaccination_sites.json"
response_locais_vacinacao = requests.get(url_locais_vacinacao)
if response_locais_vacinacao.status_code == 200:
    dados_locais = response_locais_vacinacao.json()
    df_locais_vacinacao = pd.DataFrame(dados_locais).drop(columns="id", axis=1)
    df_locais_vacinacao.columns = ["Local", "Público", "Bairro", "Endereço", "Horários"]
else:
    df_locais_vacinacao = pd.DataFrame(columns=["Local", "Público", "Bairro", "Endereço", "Horários"])

@app.get("/dados_locais_vacinacao/", response_model=dict)
def obter_dados_locais():
    return JSONResponse(content=jsonable_encoder(df_locais_vacinacao.to_dict()))

@app.post("/gerar_resposta_locais/", response_model=TextoSaida)
def gerar_resposta_locais(entrada: TextoEntrada):
    try:
        texto_contexto = "\n".join(df_locais_vacinacao.apply(lambda x: f"{x['Local']} - {x['Bairro']}: {x['Endereço']} ({x['Horários']})", axis=1))
        resposta = responder_pergunta(contexto=texto_contexto, pergunta=entrada.texto)
        return {
            "texto_original": entrada.texto,
            "resposta": resposta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta: {str(e)}")

@app.post("/gerar_respostas_uf/", response_model=TextoSaida)
def gerar_resposta_uf(entrada: TextoEntrada):
    try:
        texto_contexto = "\n".join(df_estados_agrupados.apply(lambda x: f"UF: {x['UF']}\nTotal de Doses Aplicadas Monovalente: {x['Total de Doses Aplicadas Monovalente']}\nPessoas: {x['Pessoas']}\nDoses por Pessoa: {x['Doses por Pessoa']}\n", axis=1))
        resposta = responder_pergunta(contexto=texto_contexto, pergunta=entrada.texto)
        return {
            "texto_original": entrada.texto,
            "resposta": resposta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta: {str(e)}")        

def render_pagina_locais_vacinacao():
    st.title("Locais de Vacinação em Recife")
    st.dataframe(df_locais_vacinacao.style.set_properties(**{'text-align': 'left'}))
    input_text = st.text_area("Pergunte sobre os locais de vacinação:")
    if st.button("Gerar Resposta"):
        try:
            texto_contexto = "\n".join(df_locais_vacinacao.apply(lambda x: f"{x['Local']} - {x['Bairro']}: {x['Endereço']} ({x['Horários']})", axis=1))
            resposta = responder_pergunta(contexto=texto_contexto, pergunta=input_text)
            st.write("Resposta Gerada:", resposta)
        except Exception as e:
            st.error(f"Erro: {e}")

def render_pagina_1():
    st.title("Estatísticas de Vacinação no Brasil")
    df_populacao["COD 6 DIGITOS"] = df_populacao["Código municipal"].apply(lambda x: x[:6])
    df_doses_agrupado = df.groupby(["Município Ocorrência", "COD IBGE"]).sum().reset_index()
    df_populacao["pessoas"] = df_populacao["pessoas"].astype(int)
    df_populacao.rename(columns={"pessoas": "Pessoas"}, inplace=True)
    df_mergiado = df_doses_agrupado.merge(df_populacao, how="inner", left_on="COD IBGE", right_on="COD 6 DIGITOS")
    df_estados_agrupados = df_mergiado[["Total de Doses Aplicadas Monovalente", "UF", "Pessoas"]]
    df_estados_agrupados = df_estados_agrupados.groupby("UF").sum().reset_index()
    df_estados_agrupados["Doses por Pessoa"] = round(df_estados_agrupados["Total de Doses Aplicadas Monovalente"] / df_estados_agrupados["Pessoas"], 2)
    st.table(df_estados_agrupados)

    input_text = st.text_area("Pergunte sobre as estatísticas de vacinação:")
    if st.button("Gerar Resposta"):
        try:
            texto_contexto = "\n".join(df_estados_agrupados.apply(lambda x: f"UF: {x['UF']}\nTotal de Doses Aplicadas Monovalente: {x['Total de Doses Aplicadas Monovalente']}\nPessoas: {x['Pessoas']}\nDoses por Pessoa: {x['Doses por Pessoa']}\n", axis=1))
            resposta = responder_pergunta(contexto=texto_contexto, pergunta=input_text)
            st.write("Resposta Gerada:", resposta)
        except Exception as e:
            st.error(f"Erro: {e}")

    uploaded_file = st.file_uploader("Carregue um arquivo CSV para adicionar dados", type="csv")
    if uploaded_file:
        try:
            df_carregado = pd.read_csv(uploaded_file)
            df_estados_agrupados = pd.concat([df_estados_agrupados, df_carregado], ignore_index=True)
            df_estados_agrupados = df_estados_agrupados.groupby("UF").sum().reset_index()
            df_estados_agrupados["Doses por Pessoa"] = round(df_estados_agrupados["Total de Doses Aplicadas Monovalente"] / df_estados_agrupados["Pessoas"], 2)
            st.table(df_estados_agrupados)
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")

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

    if st.button("Baixar Mapa como Imagem"):
        r.to_html("mapa_covid.html")
        with open("mapa_covid.html", "rb") as f:
            st.download_button(
                label="Baixar Mapa",
                data=f,
                file_name="mapa_covid.html",
                mime="text/html"
            )

def render_pagina_3():
    st.title("Upload e Download de Arquivos")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if uploaded_file:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            st.write("Visualização do arquivo carregado:")
            st.dataframe(df_uploaded)
            csv_data = df_uploaded.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar CSV Modificado",
                data=csv_data,
                file_name="arquivo_modificado.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
    else:
        st.info("Por favor, carregue um arquivo CSV para continuar.")

def render_navegacao():
    st.sidebar.title("Navegação")
    pagina = st.sidebar.radio(
        "Escolha uma página:",
        options=["Locais de Vacinação", "Estatísticas de Vacinação", "Mapa de Casos de COVID-19", "Upload e Download de Arquivos"]
    )
    return pagina

pagina = render_navegacao()

if pagina == "Locais de Vacinação":
    render_pagina_locais_vacinacao()
elif pagina == "Estatísticas de Vacinação":
    render_pagina_1()
elif pagina == "Mapa de Casos de COVID-19":
    render_pagina_2()
elif pagina == "Upload e Download de Arquivos":
    render_pagina_3()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
