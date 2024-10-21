# Data Summary

## Dados COVID-19
- **Fonte**: Dados coletados de arquivos Excel e CSV.
- **Estrutura**:
  - `dados_covid.xlsx`: Contém informações sobre casos e vacinação por município.
  - `censo_2022_populacao_municipios.xlsx`: Informações populacionais por município.
  - `HIST_PAINEL_COVIDBR_2024_Parte1_30ago2024.csv` e `HIST_PAINEL_COVIDBR_2024_Parte2_30ago2024.csv`: Dados sobre COVID-19 em 2024, contendo colunas como `codmun`, `estado`, `casosAcumulado`, entre outras.
  - `municipios.csv`: Informações sobre municípios, incluindo `codigo_ibge` e dados de latitude e longitude.

## Variáveis Importantes
- **Total de Doses Aplicadas Monovalente**: Total de vacinas aplicadas.
- **Pessoas**: População total por município.
- **casos_por_100k**: Casos de COVID-19 ajustados por 100 mil habitantes.

## Uso dos Dados
- A API fornece acesso a dados de vacinação e permite o envio de novos dados.
- As páginas do Streamlit exibem estatísticas de vacinação e mapas de densidade populacional.
