# CLAUDE.md — Monitor de Crédito: Portfólio de Acompanhamento

## Objetivo do Projeto

Pipeline automatizado de monitoramento de crédito para 15 empresas brasileiras. O sistema coleta notícias e comunicados públicos de RI a partir do Google News RSS e das páginas de Relações com Investidores de cada empresa, classifica cada item com Claude Haiku (sentimento, severidade, tags temáticas) e gera um dashboard HTML interativo autocontido — pronto para uso por um gestor de crédito.

## Estrutura de Pastas

```
/
├── .env                        # Variáveis de ambiente (ANTHROPIC_API_KEY)
├── .gitignore
├── README.md                   # Documentação para usuário final
├── CLAUDE.md                   # Este arquivo — contexto técnico do projeto
├── dashboard.txt               # Guia descritivo do dashboard (abas e gráficos)
├── documentacao_pipeline.txt   # Documentação técnica do pipeline para entrega
├── companies.csv               # Cadastro das 15 empresas (empresa, ticker, setor, segmento, ri_url)
├── requirements.txt            # Dependências Python
├── /scripts
│   ├── run.py                  # Orquestrador principal — ponto de entrada do pipeline
│   ├── collector.py            # Coleta via Google News RSS + raspagem de RI + Playwright
│   ├── classifier.py           # Classificação via API Anthropic (Claude Haiku)
│   ├── fetch_stocks.py         # Coleta de preços históricos via yfinance (B3)
│   └── generate_dashboard.py   # Gera output/dashboard.html (HTML autocontido)
├── /output
│   ├── news.csv                # Notícias coletadas e classificadas (12 colunas)
│   ├── stock_data.csv          # Preços históricos das ações (6 meses, B3)
│   └── dashboard.html          # Dashboard interativo — output principal
└── /logs
    └── run.log                 # Log detalhado de cada execução
```

## Como Rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Instalar browser headless (necessário para Playwright — apenas na primeira vez)
python -m playwright install chromium

# 3. Configurar a chave de API no .env
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. Executar o pipeline completo
python scripts/run.py
```

O pipeline gera automaticamente `output/news.csv`, `output/stock_data.csv` e `output/dashboard.html`.

Para regenerar apenas o dashboard (sem re-coletar dados):

```bash
python scripts/generate_dashboard.py
```

Para atualizar apenas os dados de preço:

```bash
python scripts/fetch_stocks.py
```

## Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Chave de API da Anthropic para chamadas ao Claude Haiku | Sim |

## Decisões Técnicas

- **Fontes abertas apenas**: Google News RSS (sem autenticação) + páginas de RI públicas. Nenhuma fonte com paywall.
- **Modelo de classificação**: `claude-haiku-4-5-20251001` — modelo leve e econômico, adequado para classificação em escala.
- **Extração de snippets com Playwright**: browser Chromium headless executa o JavaScript dos redirects do Google News e extrai até 1.500 chars do texto real do artigo. Roda com 10 abas em paralelo via `asyncio`.
- **Deduplicação em 2 passagens**: primeiro por hash SHA256 da URL normalizada, depois por similaridade de título via `difflib.SequenceMatcher` (threshold 0.85).
- **Período de coleta**: 180 dias retroativos à data de execução; itens com data anterior a 01/10/2025 são descartados.
- **Dados de preço**: `yfinance` com sufixo `.SA` para tickers da B3. NTS (debenture) e Aegea (ticker indisponível no Yahoo Finance) não retornam dados — tratados com warning.
- **Dashboard**: HTML único autocontido (~1.1 MB) com dados embutidos como JSON. Toda lógica de filtragem, cálculo e renderização de gráficos é feita em JavaScript no browser via Chart.js. Funciona offline (exceto Chart.js via CDN).
- **Tratamento de erros**: toda exceção de rede e de API é capturada com try/except — o pipeline nunca interrompe por falha em uma única empresa ou item.
- **Rate limiting**: sleep de 0.5s entre chamadas à API para respeitar os limites da Anthropic.
- **Encoding**: CSVs de saída em UTF-8 com BOM (`utf-8-sig`) para abrir corretamente no Excel.
- **Logging**: dois handlers simultâneos — arquivo `logs/run.log` e terminal — com timestamp em cada linha.

## Scripts Independentes

Cada script pode ser executado de forma independente sem rodar o pipeline completo:

| Script | Comando | O que faz |
| --- | --- | --- |
| `run.py` | `python scripts/run.py` | Pipeline completo (coleta + classifica + preços + dashboard) |
| `fetch_stocks.py` | `python scripts/fetch_stocks.py` | Atualiza apenas stock_data.csv |
| `generate_dashboard.py` | `python scripts/generate_dashboard.py` | Regenera o dashboard a partir dos CSVs existentes |

## Estrutura do news.csv (12 colunas)

| Coluna | Descrição |
| --- | --- |
| `empresa` | Nome da empresa |
| `ticker` | Código B3 (sem .SA) |
| `data_publicacao` | ISO 8601 UTC |
| `fonte` | Google News ou RI {empresa} |
| `tipo` | `noticia` ou `comunicado_oficial` |
| `titulo` | Título do item |
| `url` | URL original |
| `snippet_ou_trecho` | Texto extraído pelo Playwright (até 1.500 chars) |
| `sentimento` | `positivo`, `neutro` ou `negativo` |
| `tags` | Temas separados por `;` |
| `severidade` | `1` (baixo), `2` (médio), `3` (alto) |
| `resumo_curto` | 1-2 frases com dados concretos geradas pelo Claude |

## Estrutura do stock_data.csv (8 colunas)

`empresa, ticker, date, open, high, low, close, volume`
