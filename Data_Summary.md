# Data Summary  
## Dados Climáticos de Pernambuco  

---

### **Fonte**  
Os dados climáticos são obtidos de várias fontes, incluindo **arquivos CSV** e **APIs de meteorologia**. As informações são utilizadas para monitoramento em tempo real das condições climáticas, bem como para análises históricas de temperatura e precipitação.  

---

## **Estrutura**  

### **1. HIST_CLIMA_PE_2024_Parte1.csv**  
Contém dados sobre o clima de Pernambuco em 2024, com as seguintes colunas:  

- **municipio:** Nome do município em Pernambuco.  
- **data:** Data do registro climático.  
- **temperatura_max:** Temperatura máxima registrada no dia.  
- **temperatura_min:** Temperatura mínima registrada no dia.  
- **temperatura_media:** Temperatura média do dia.  
- **precipitacao:** Quantidade de precipitação (chuvas) registrada no dia.  

### **2. municipios.csv**  
Contém informações sobre os municípios, incluindo:  

- **codigo_ibge:** Código do município conforme o IBGE.  
- **latitude e longitude:** Coordenadas geográficas para visualizações no mapa.  
- Informações sobre a **população** e a **densidade** de casos de precipitação e temperatura por município.  

### **3. APIs de Clima**  
As informações de clima em tempo real são obtidas por meio de uma **API externa**, que fornece dados sobre a **temperatura** e **precipitação** em diversas localizações em Pernambuco. Os dados incluem:  

- **latitude e longitude:** Coordenadas para determinar a localização no mapa.  
- **temperatura:** Temperatura atual no município.  
- **precipitacao:** Precipitação atual no município.  

---

## **Variáveis Importantes**  

### **Temperatura**  
Refere-se à temperatura **média**, **máxima** e **mínima** registrada para cada município. Esses dados são essenciais para acompanhar as variações climáticas ao longo do tempo.  

### **Precipitação**  
Quantidade de chuva registrada em milímetros (**mm**), crucial para entender a distribuição da chuva e o impacto no clima local.  

### **Latitude e Longitude**  
Coordenadas geográficas que permitem criar visualizações interativas dos dados climáticos no mapa, facilitando a **análise espacial** da temperatura e precipitação.  

### **Municipios**  
Representa a base de dados geográfica, com informações sobre a localização dos municípios, permitindo a criação de **mapas interativos** para visualização dos dados climáticos.  

---

## **Uso dos Dados**  

### **Monitoramento em Tempo Real**  
A plataforma oferece uma visão detalhada das condições climáticas atuais em Pernambuco, incluindo a **temperatura** e a **precipitação** em tempo real para vários municípios.  

### **Visualização Geográfica**  
Usando a biblioteca **pydeck**, a plataforma cria **mapas interativos** para visualizar a temperatura e a precipitação nos municípios de Pernambuco. As visualizações incluem:  

- **Mapa de Temperatura:** Exibe a distribuição de temperaturas atuais nos municípios, com a variação de cores representando diferentes faixas de temperatura.  
- **Mapa de Precipitação:** Exibe a precipitação média para os municípios, com a variação de cores representando diferentes níveis de chuva.  

### **Análise Histórica**  
A plataforma permite a **análise histórica** das condições climáticas, exibindo estatísticas como:  
- **Temperatura média**, **máxima** e **mínima**.  
- **Precipitação acumulada** por município.  

### **Gerenciamento de Arquivos**  
- Permite o **upload de arquivos CSV** com dados climáticos, para análise e processamento.  
- Os usuários podem visualizar os dados, gerar **estatísticas descritivas** e baixar arquivos processados.  

### **Consulta Climática Interativa**  
Através de uma interface de **Pergunta e Resposta (Q&A)**, os usuários podem fazer perguntas sobre o clima, como:  
- _"Qual é a temperatura média de Garanhuns?"_  
- _"Qual a precipitação acumulada de Recife?"_  
E obter respostas baseadas nos **dados históricos** e **em tempo real**.  

---

## **Aplicações e Funcionalidades**  

### **Visualização de Temperatura e Precipitação**  
A plataforma fornece **mapas interativos**, permitindo que os usuários visualizem as condições climáticas atuais de Pernambuco. Isso inclui tanto a **temperatura** quanto a **precipitação**, em uma visão espacial detalhada.  

### **Consulta de Dados Climáticos**  
A funcionalidade de **consulta** permite que os usuários obtenham respostas baseadas em dados históricos e atuais, facilitando a obtenção de informações sobre o clima de qualquer município de Pernambuco.  

### **API Climática**  
A API de clima oferece dados sobre a **temperatura** e **precipitação** de um município específico, com a possibilidade de realizar buscas por **coordenadas geográficas** (latitude e longitude).  

### **Estatísticas Climáticas**  
Através de gráficos interativos no **Streamlit**, os usuários podem visualizar as **estatísticas de temperatura e precipitação** para os municípios de Pernambuco. Isso ajuda a:  
- Identificar **tendências climáticas**.  
- Avaliar os **impactos do clima** nas diferentes regiões.  

---

## **Conclusão**  
Com esses dados, é possível realizar uma **análise detalhada do clima** de Pernambuco, ajudando na compreensão das **variações de temperatura** e **precipitação** ao longo do tempo e no espaço. A plataforma fornece **ferramentas interativas** para consultas rápidas e análises aprofundadas, facilitando a tomada de decisões informadas sobre o clima no estado.  
