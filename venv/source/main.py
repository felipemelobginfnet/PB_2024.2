import pandas as pd
import streamlit as st

df = pd.read_excel("venv\data\dados_covid.xlsx")
df_populacao = pd.read_excel("venv\data\censo_2022_populacao_municipios.xlsx", dtype="str")

df_populacao["COD 6 DIGITOS"] = df_populacao["Código municipal"].apply(lambda x: x[:6])
df_doses_agrupado = df.groupby(["Município Ocorrência", "COD IBGE"]).sum().reset_index()
df_populacao["pessoas"] = df_populacao["pessoas"].astype(int)
df_populacao.rename(columns={"pessoas": "Pessoas"}, inplace=True)
df_mergiado = df_doses_agrupado.merge(df_populacao, how="inner", left_on="COD IBGE", right_on="COD 6 DIGITOS")
df_cidades_agrupadas = df_mergiado[["Município Ocorrência", "Total de Doses Aplicadas Monovalente",
                                   "UF", "Pessoas"]]
df_estados_agrupados = df_mergiado[["Total de Doses Aplicadas Monovalente",
                                   "UF", "Pessoas"]]
#df_estados_agrupados = df_estados_agrupados.drop(columns="Município Ocorrência")
df_estados_agrupados = df_estados_agrupados.groupby("UF").sum().reset_index()
df_cidades_agrupadas["Doses por Pessoa"] = round(df_cidades_agrupadas["Total de Doses Aplicadas Monovalente"]/df_cidades_agrupadas["Pessoas"], 2)
df_estados_agrupados["Doses por Pessoa"] = round(df_estados_agrupados["Total de Doses Aplicadas Monovalente"]/df_estados_agrupados["Pessoas"], 2)
df_cidades_agrupadas.sort_values(by="Total de Doses Aplicadas Monovalente", ascending=False, inplace=True)
df_estados_agrupados.sort_values(by="Total de Doses Aplicadas Monovalente", ascending=False, inplace=True)

df_cidades_agrupadas = df_cidades_agrupadas.reset_index(drop=True)
df_estados_agrupados = df_estados_agrupados.reset_index(drop=True)
df_cidades_agrupadas.rename(columns={"Total de Doses Aplicadas Monovalente": "Total de Doses Aplicadas"}, inplace=True)
df_estados_agrupados.rename(columns={"Total de Doses Aplicadas Monovalente": "Total de Doses Aplicadas"}, inplace=True)

st.header("Estatísticas Vacinação do Brasil")
st.title("Vacinação por Estado")
st.table(df_estados_agrupados)

df_cidades_agrupadas_top_10 = df_cidades_agrupadas.head(10)
st.title("Top 10 Municípios por Total de Doses Aplicadas")
st.table(df_cidades_agrupadas_top_10)

st.markdown("### Fontes:")
st.markdown("[Vacinação por município - Ministério da Saúde](https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_VACINA_C19_CNES_OCORRENCIA/SEIDIGI_DEMAS_VACINA_C19_CNES_OCORRENCIA.html)")
st.markdown("[Panorama do Censo 2022 - IBGE](https://censo2022.ibge.gov.br/panorama/mapas.html?localidade=&recorte=N6)")