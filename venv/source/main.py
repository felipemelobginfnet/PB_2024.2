import pandas as pd
import streamlit as st
import pydeck as pdk

# Implementando cache para carregar arquivos pesados
@st.cache_data
def carregar_dados_covid():
    df = pd.read_excel("venv\data\dados_covid.xlsx")
    df_populacao = pd.read_excel("venv\data\censo_2022_populacao_municipios.xlsx", dtype="str")
    return df, df_populacao

@st.cache_data
def carregar_dados_2024():
    df_2024 = pd.read_csv("venv\data\HIST_PAINEL_COVIDBR_2024_Parte1_30ago2024.csv", sep=";")
    df_2024 = df_2024[["regiao", "estado", "casosAcumulado", "casosNovos", "obitosAcumulado", "obitosNovos", "semanaEpi", "codmun", "populacaoTCU2019"]]
    df_2024_2 = pd.read_csv("venv\data\HIST_PAINEL_COVIDBR_2024_Parte2_30ago2024.csv", sep=";")
    df_2024_2 = df_2024_2[["regiao", "estado", "casosAcumulado", "casosNovos", "obitosAcumulado", "obitosNovos", "semanaEpi", "codmun", "populacaoTCU2019"]]
    df_2024 = pd.concat([df_2024, df_2024_2], ignore_index=True)
    return df_2024

# Carregar dados
df, df_populacao = carregar_dados_covid()
df_2024 = carregar_dados_2024()

# Aplicando manipulações nos dados
df_populacao["COD 6 DIGITOS"] = df_populacao["Código municipal"].apply(lambda x: x[:6])
df_doses_agrupado = df.groupby(["Município Ocorrência", "COD IBGE"]).sum().reset_index()
df_populacao["pessoas"] = df_populacao["pessoas"].astype(int)
df_populacao.rename(columns={"pessoas": "Pessoas"}, inplace=True)
df_mergiado = df_doses_agrupado.merge(df_populacao, how="inner", left_on="COD IBGE", right_on="COD 6 DIGITOS")
df_cidades_agrupadas = df_mergiado[["Município Ocorrência", "Total de Doses Aplicadas Monovalente",
                                   "UF", "Pessoas"]]
df_estados_agrupados = df_mergiado[["Total de Doses Aplicadas Monovalente",
                                   "UF", "Pessoas"]]
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

# Top 10 municípios por doses aplicadas
df_cidades_agrupadas_top_10 = df_cidades_agrupadas.head(10)
st.title("Top 10 Municípios por Total de Doses Aplicadas")
st.table(df_cidades_agrupadas_top_10)

# Manipulação dos dados de PE para o mapa
municipios = pd.read_csv("venv\data\municipios.csv")
municipios["codigo_ibge_6_d"] = municipios["codigo_ibge"].astype(str).apply(lambda x: x[:6]).astype(int)

df_pe = df_2024[(df_2024["estado"]=="PE") & (df_2024["semanaEpi"] != 53)]
df_pe = df_pe[["semanaEpi", "casosAcumulado", "codmun", "casosNovos", "obitosNovos", "populacaoTCU2019"]]
df_pe = df_pe.merge(municipios, how="inner", left_on="codmun", right_on="codigo_ibge_6_d")
df_pe = df_pe[["semanaEpi", "casosAcumulado", "codmun", "latitude", "longitude", "casosNovos", "obitosNovos", "populacaoTCU2019"]]
df_pe["casos_por_100k"] = df_pe["casosAcumulado"] / (df_pe["populacaoTCU2019"] / 100000)
df_pe = df_pe[df_pe["semanaEpi"]==26]

st.title("Mapa de Densidade Populacional Ajustada para Casos de COVID-19 em PE")

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

st.markdown("### Fontes:")
st.markdown("[Vacinação por município - Ministério da Saúde](https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_VACINA_C19_CNES_OCORRENCIA/SEIDIGI_DEMAS_VACINA_C19_CNES_OCORRENCIA.html)")
st.markdown("[Panorama do Censo 2022 - IBGE](https://censo2022.ibge.gov.br/panorama/mapas.html?localidade=&recorte=N6)")
