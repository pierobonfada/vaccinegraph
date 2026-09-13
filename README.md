# VaccineGraph

Ferramenta CLI avançada e modular em Python para download, processamento, cache e visualização gráfica dos microdados abertos do SI-PNI (Sistema de Informação do Programa Nacional de Imunizações - DATASUS).

## Funcionalidades
- **100% focado no SIPNIBD moderno (2023+)**: Analisa e cruza dados absolutos das campanhas e rotinas mais recentes.
- **Cache Inteligente Parquet**: Faz o download e conversão de arquivos de gigabytes e retém a análise em memória otimizada.
- **Filtros Modulares**: Gere recortes temporais (`--start-year`), geográficos (`--state`, `--city`), e imunobiológicos (`--search`).
- **Diversidade Gráfica**: Visualize barras agregadas (`doses`, `people`), evolução temporal combinada (`timeline`), e panorama absoluto anual (`total_yearly`).

## Instalação
O projeto requer Python 3 e as bibliotecas listadas (Pandas, Matplotlib, PyArrow).

## Uso Básico
\`\`\`bash
./vacinas_cli.py --chart doses --start-year 2023 --end-year 2024 --state RS --search Pentavalente Influenza -o grafico_rs.png
\`\`\`
