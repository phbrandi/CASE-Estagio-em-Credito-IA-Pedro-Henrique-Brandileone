# Monitor de Crédito — Portfólio de Acompanhamento

Pipeline automatizado que coleta notícias e comunicados públicos de 15 empresas brasileiras, classifica cada item com inteligência artificial (Claude Haiku) e gera um relatório PDF com análises de sentimento, severidade e tendências — projetado para apoiar decisões de crédito corporativo.

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

# Configure a chave de API
# Edite o arquivo .env e adicione:
# ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
```

## Como Rodar

```bash
python scripts/run.py
```

O pipeline executa automaticamente todas as etapas: coleta, deduplicação, classificação e geração do relatório.

## Outputs Gerados

| Arquivo | Descrição |
| --- | --- |
| `output/news.csv` | Tabela com todas as notícias coletadas e classificadas |
| `output/monitor.pdf` | Relatório PDF com gráficos e análise executiva |
| `output/charts/ranking_atencao.png` | Ranking de empresas por score de atenção |
| `output/charts/heatmap.png` | Heatmap de eventos negativos por empresa e mês |
| `output/charts/tendencia.png` | Evolução mensal de sentimento no portfólio |
| `output/charts/top_tags.png` | Tags temáticas mais frequentes |
| `logs/run.log` | Log detalhado da execução |

## Estrutura do news.csv

O arquivo de saída contém 12 colunas nesta ordem:

| Coluna | Descrição |
| --- | --- |
| `empresa` | Nome da empresa |
| `ticker` | Código de negociação na B3 |
| `data_publicacao` | Data/hora de publicação (ISO 8601) |
| `fonte` | Origem da notícia (Google News ou RI da empresa) |
| `tipo` | `noticia` ou `comunicado_oficial` |
| `titulo` | Título do item |
| `url` | URL original |
| `snippet_ou_trecho` | Trecho extraído do conteúdo (até 500 caracteres) |
| `sentimento` | `positivo`, `neutro` ou `negativo` |
| `tags` | Temas separados por `;` (ex: `resultado_guidance;setor_macro`) |
| `severidade` | `1` (baixo), `2` (médio) ou `3` (alto impacto) |
| `resumo_curto` | Resumo objetivo gerado pelo modelo |

### Exemplo de linha

```text
Equatorial,EQTL3,2026-03-15T14:30:00+00:00,Google News,noticia,"Equatorial Energia reporta crescimento de 18% no lucro do 4T25","https://exemplo.com/noticia","Equatorial Energia reporta lucro de R$ 1,2 bi no quarto trimestre de 2025...",positivo,resultado_guidance;setor_macro,2,"Lucro trimestral acima das estimativas com expansão regional."
```

## Empresas Monitoradas

OceanPact (OPCT3) · Brava Energia (BRAV3) · PetroRio (PRIO3) · PetroReconcavo (RECV3) · NTS (NTSB11) · Aegea (AGYS3) · Equatorial (EQTL3) · Copasa (CSMG3) · Cosan (CSAN3) · Vamos (VAMO3) · Mills (MILS3) · Armac (ARML3) · BTG (BPAC11) · Unipar (UNIP6) · Multiplan (MULT3)
