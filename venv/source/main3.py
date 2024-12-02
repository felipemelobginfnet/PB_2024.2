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
import plotly.io as pio

# Configuração de variáveis de ambiente
os.environ["HUGGINGFACE_HUB_TOKEN"] = "osiudfosiduf"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Configuração do modelo de IA
modelo_perguntas = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad", device=-1)

def responder_pergunta(contexto, pergunta):
    try:
        if not contexto or not pergunta:
            return "Por favor, forneça um contexto e uma pergunta válidos."
        resposta = modelo_perguntas(question=pergunta, context=contexto)
        return resposta["answer"]
    except Exception as e:
        return f"Erro ao processar a pergunta: {str(e)}"

class EntradaTexto(BaseModel):
    texto: str

class SaidaTexto(BaseModel):
    texto_original: str
    resposta: str

app = FastAPI(title="API COVID-19", description="API para análise de dados COVID-19")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@st.cache_data(ttl=3600)
def carregar_dados_covid():
    try:
        df = pd.read_excel("venv/data/dados_covid.xlsx")
        df_populacao = pd.read_excel("venv/data/censo_2022_populacao_municipios.xlsx", dtype="str")
        return df, df_populacao
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None

@st.cache_data(ttl=3600)
def carregar_dados_2024():
    try:
        df_2024_parte1 = pd.read_csv("venv/data/HIST_PAINEL_COVIDBR_2024_Parte1_30ago2024.csv", sep=";")
        df_2024_parte2 = pd.read_csv("venv/data/HIST_PAINEL_COVIDBR_2024_Parte2_30ago2024.csv", sep=";")
        df_2024 = pd.concat([df_2024_parte1, df_2024_parte2], ignore_index=True)
        return df_2024
    except Exception as e:
        st.error(f"Erro ao carregar dados 2024: {e}")
        return None

# Carregamento de dados de vacinação
url_vacinacao = "https://minhavacina.recife.pe.gov.br/api/v1/unscheduled_vaccination_sites.json"
try:
    resposta_vacinacao = requests.get(url_vacinacao)
    if resposta_vacinacao.status_code == 200:
        dados_vacinacao = resposta_vacinacao.json()
        df_locais_vacinacao = pd.DataFrame(dados_vacinacao).drop(columns="id", axis=1)
        df_locais_vacinacao.columns = ["Local", "Público", "Bairro", "Endereço", "Horários"]
    else:
        df_locais_vacinacao = pd.DataFrame(columns=["Local", "Público", "Bairro", "Endereço", "Horários"])
except Exception as e:
    st.error(f"Erro ao carregar dados de vacinação: {e}")
    df_locais_vacinacao = pd.DataFrame(columns=["Local", "Público", "Bairro", "Endereço", "Horários"])

# Endpoints da API
@app.get("/locais_vacinacao/", response_model=dict)
def obter_locais_vacinacao():
    try:
        return JSONResponse(content=jsonable_encoder(df_locais_vacinacao.to_dict()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resposta_locais/", response_model=SaidaTexto)
def gerar_resposta_locais(entrada: EntradaTexto):
    try:
        texto_contexto = "\n".join(df_locais_vacinacao.apply(
            lambda x: f"{x['Local']} - {x['Bairro']}: {x['Endereço']} ({x['Horários']})", axis=1))
        resposta = responder_pergunta(contexto=texto_contexto, pergunta=entrada.texto)
        return SaidaTexto(texto_original=entrada.texto, resposta=resposta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def criar_nuvem_palavras(df, coluna):
    # Junta todos os termos mantendo linhas completas como termos únicos
    texto = " ".join(df[coluna].astype(str).values)
    nuvem = WordCloud(width=800, height=400, background_color="white", collocations=False).generate(texto)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(nuvem, interpolation="bilinear")
    ax.axis("off")
    return fig

def renderizar_pagina_vacinacao():
    st.title("Locais de Vacinação em Recife")
    
    # Tabela responsiva
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
    
    # Nuvem de palavras dos bairros
    st.subheader("Distribuição de Locais por Bairro")
    fig_nuvem = criar_nuvem_palavras(df_locais_vacinacao, "Bairro")
    st.pyplot(fig_nuvem)
    
    # Sistema de perguntas e respostas
    pergunta = st.text_area("Faça uma pergunta sobre os locais de vacinação:")
    if st.button("Gerar Resposta"):
        with st.spinner("Processando sua pergunta..."):
            try:
                texto_contexto = "\n".join(df_locais_vacinacao.apply(
                    lambda x: f"{x['Local']} - {x['Bairro']}: {x['Endereço']} ({x['Horários']})", axis=1))
                resposta = responder_pergunta(texto_contexto, pergunta)
                st.success(f"Resposta: {resposta}")
            except Exception as e:
                st.error(f"Erro ao gerar resposta: {e}")

def renderizar_pagina_estatisticas():
    st.title("Estatísticas de Vacinação no Brasil")
    
    try:
        df, df_populacao = carregar_dados_covid()
        if df is not None and df_populacao is not None:
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
            
            # Visualização com Plotly
            fig = px.bar(
                df_estados,
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
            #imagem_download = fig.to_image(format="png")
            #st.download_button(
             #   "Baixar Gráfico (PNG)",
              #  imagem_download,
               # "grafico_vacinacao.png"
                #"image/png"
            #)
            
            # Tabela responsiva
            if df_estados is not None and not df_estados.empty:
             st.dataframe(
             df_estados,
             use_container_width=True,
             height=400
            )
            else:
             st.warning("A tabela está vazia ou os dados não foram carregados corretamente.")

            csv_estados = df_estados.to_csv(index=False).encode("utf-8")

            st.download_button(
                "Baixar Tabela de Estatísticas (CSV)",
                csv_estados,
                "estatisticas_vacinacao.csv",
                "text/csv"
            )
            
            # Sistema de perguntas e respostas
            pergunta = st.text_area("Faça uma pergunta sobre as estatísticas:")
            if st.button("Gerar Resposta"):
                with st.spinner("Processando sua pergunta..."):
                    try:
                        texto_contexto = "\n".join(df_estados.apply(
                            lambda x: f"UF: {x['UF']}, Doses: {x['Total de Doses Aplicadas Monovalente']}, "
                                    f"Pessoas: {x['Pessoas']}, Doses por Pessoa: {x['Doses por Pessoa']}", axis=1))
                        resposta = responder_pergunta(texto_contexto, pergunta)
                        st.success(f"Resposta: {resposta}")
                    except Exception as e:
                        st.error(f"Erro ao gerar resposta: {e}")
            
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")

def renderizar_pagina_mapa():
    st.title("Mapa de Casos de COVID-19")
    
    try:
        municipios = pd.read_csv("venv/data/municipios.csv")
        df_2024 = carregar_dados_2024()
        
        if df_2024 is not None:
            municipios["codigo_ibge_6_d"] = municipios["codigo_ibge"].astype(str).str[:6].astype(int)
            df_pe = df_2024[
                (df_2024["estado"] == "PE") &
                (df_2024["semanaEpi"] != 53)
            ]
            
            df_pe = df_pe.merge(
                municipios,
                how="inner",
                left_on="codmun",
                right_on="codigo_ibge_6_d"
            )
            
            df_pe["casos_por_100k"] = df_pe["casosAcumulado"] / (df_pe["populacaoTCU2019"] / 100000)
            
            # Mapa PyDeck
            visualizacao = pdk.ViewState(latitude=-8.05428, longitude=-34.8813, zoom=5)
            camada = pdk.Layer(
                "ScatterplotLayer",
                data=df_pe[["latitude", "longitude", "casos_por_100k"]],
                get_position=["longitude", "latitude"],
                get_radius="casos_por_100k / 10",
                radius_scale=3.5,
                get_color="[200, 30, 0, 160]",
                pickable=True
            )
            
            mapa = pdk.Deck(layers=[camada], initial_view_state=visualizacao)
            st.pydeck_chart(mapa)
            
            
            mapa_html = mapa.to_html()
            
            st.download_button(
                        "Baixar Mapa",
                        mapa_html,
                        "mapa_covid.html",
                        "text/html"
                    )
            
            #imagem_mapa_download = mapa_html.to_image(format="png")
            #st.download_button(
             #   "Baixar Mapa (PNG)",
              #  imagem_mapa_download,
               # "mapa_vacinacao.png"
                #"image/png"
            #)
            
    except Exception as e:
        st.error(f"Erro ao renderizar mapa: {e}")

def renderizar_pagina_arquivos():
    st.title("Gerenciamento de Arquivos")
    
    arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if arquivo:
        try:
            df_carregado = pd.read_csv(arquivo)
            st.write("Prévia do arquivo:")
            st.dataframe(df_carregado.head(), use_container_width=True)
            
            # Opções de processamento
            if st.checkbox("Mostrar estatísticas básicas"):
                st.write("Estatísticas descritivas:")
                st.write(df_carregado.describe())
            
            # Download do arquivo processado
            csv_processado = df_carregado.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Baixar CSV Processado",
                csv_processado,
                "dados_processados.csv",
                "text/csv"
            )
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
    else:
        st.info("Aguardando upload de arquivo...")

def renderizar_navegacao():
    st.sidebar.title("Navegação")
    return st.sidebar.radio(
        "Escolha uma página:",
        ["Locais de Vacinação", "Estatísticas de Vacinação", "Mapa de Casos de COVID-19", "Gerenciamento de Arquivos"]
    )

# Renderização principal
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