# Monitor de Crédito — Portfólio de Acompanhamento

Pipeline automatizado que coleta notícias e comunicados públicos de 15 empresas brasileiras, classifica cada item com inteligência artificial (Claude Haiku) e gera um dashboard HTML interativo com análise de sentimento, severidade, tendências e projeção de preço — projetado para apoiar decisões de crédito corporativo.

## Pré-requisitos

- Python 3.12+
- Chave de API da Anthropic (obtenha em [console.anthropic.com](https://console.anthropic.com))

## Instalação

```bash
# Clone o repositório
git clone https://github.com/phbrandi/CASE-Estagio-em-Credito-IA-Pedro-Henrique-Brandileone.git
cd CASE-Estagio-em-Credito-IA-Pedro-Henrique-Brandileone

# Instale as dependências
pip install -r requirements.txt

# Instale o browser headless (apenas na primeira vez)
python -m playwright install chromium

# Configure a chave de API — crie o arquivo .env com:
# ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
```

## Como Rodar

```bash
python scripts/run.py
```

O pipeline executa todas as etapas automaticamente: coleta, extração de conteúdo, deduplicação, classificação, preços históricos e geração do dashboard.

### Executar etapas individualmente

```bash
# Apenas atualizar os dados de preço das ações
python scripts/fetch_stocks.py

# Apenas regenerar o dashboard (sem re-coletar notícias)
python scripts/generate_dashboard.py
```

## Outputs Gerados

| Arquivo | Descrição |
| --- | --- |
| `output/news.csv` | Tabela com todas as notícias coletadas e classificadas (12 colunas) |
| `output/stock_data.csv` | Preços históricos de 6 meses das ações na B3 (8 colunas) |
| `output/dashboard.html` | Dashboard interativo — abra no navegador |
| `logs/run.log` | Log detalhado da execução |

## Dashboard

O arquivo `output/dashboard.html` é autocontido (~1.1 MB) e funciona diretamente no navegador sem servidor. Possui três abas:

- **Visão Geral** — últimas notícias, alertas críticos (sev.3), distribuição de sentimento por período, ranking de atenção por empresa e análise temática
- **Análise Histórica** — heatmap de eventos negativos, preço das ações sobrepostos com marcadores de eventos clicáveis, correlação sentimento vs. retorno semanal e projeção para a próxima semana
- **Explorador de Notícias** — tabela completa com filtros em tempo real por empresa, setor, sentimento, severidade e tema

Todos os pontos dos gráficos são clicáveis e abrem as notícias correspondentes.

## Estrutura do news.csv

| Coluna | Descrição |
| --- | --- |
| `empresa` | Nome da empresa |
| `ticker` | Código de negociação na B3 |
| `data_publicacao` | Data/hora de publicação (ISO 8601 UTC) |
| `fonte` | Origem da notícia (Google News ou RI da empresa) |
| `tipo` | `noticia` ou `comunicado_oficial` |
| `titulo` | Título do item |
| `url` | URL original |
| `snippet_ou_trecho` | Texto extraído do artigo via Playwright (até 1.500 caracteres) |
| `sentimento` | `positivo`, `neutro` ou `negativo` |
| `tags` | Temas separados por `;` |
| `severidade` | `1` (baixo), `2` (médio) ou `3` (alto impacto) |
| `resumo_curto` | Resumo objetivo com dados concretos gerado pelo modelo |

## Empresas Monitoradas

OceanPact (OPCT3) · Brava Energia (BRAV3) · PetroRio (PRIO3) · PetroReconcavo (RECV3) · NTS (NTSB11) · Aegea (AGYS3) · Equatorial (EQTL3) · Copasa (CSMG3) · Cosan (CSAN3) · Vamos (VAMO3) · Mills (MILS3) · Armac (ARML3) · BTG (BPAC11) · Unipar (UNIP6) · Multiplan (MULT3)

> NTS e Aegea não possuem cotação disponível no Yahoo Finance e ficam sem dados de preço no dashboard.
