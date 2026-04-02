# CLAUDE.md — Monitor de Crédito: Portfólio de Acompanhamento

## Objetivo do Projeto

Pipeline automatizado de monitoramento de crédito para 15 empresas brasileiras. O sistema coleta notícias e comunicados públicos de RI a partir do Google News RSS e das páginas de Relações com Investidores de cada empresa, classifica cada item com Claude Haiku (sentimento, severidade, tags temáticas) e gera um CSV estruturado mais um PDF de monitoramento com gráficos analíticos — pronto para uso por um gestor de crédito.

## Estrutura de Pastas

```
/
├── .env                      # Variáveis de ambiente (ANTHROPIC_API_KEY)
├── .gitignore
├── README.md                 # Documentação para usuário final
├── CLAUDE.md                 # Este arquivo — contexto técnico do projeto
├── companies.csv             # Cadastro das 15 empresas (empresa, ticker, setor, segmento, ri_url)
├── requirements.txt          # Dependências Python
├── /scripts
│   ├── run.py                # Orquestrador principal — ponto de entrada do pipeline
│   ├── collector.py          # Coleta de links via Google News RSS + raspagem de RI
│   ├── classifier.py         # Classificação de itens via API Anthropic (Claude Haiku)
│   └── monitor.py            # Geração de gráficos PNG e PDF de monitoramento
├── /output
│   ├── news.csv              # Output principal: itens coletados e classificados
│   ├── monitor.pdf           # Relatório PDF para o gestor
│   └── /charts               # Gráficos PNG gerados pelo monitor.py
└── /logs
    └── run.log               # Log detalhado de cada execução
```

## Como Rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar a chave de API no .env
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 3. Executar o pipeline completo
python scripts/run.py
```

O pipeline gera automaticamente `output/news.csv`, os gráficos em `output/charts/` e o relatório `output/monitor.pdf`.

## Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
|---|---|---|
| `ANTHROPIC_API_KEY` | Chave de API da Anthropic para chamadas ao Claude Haiku | Sim |

## Decisões Técnicas

- **Fontes abertas apenas**: Google News RSS (sem autenticação) + páginas de RI públicas. Nenhuma fonte com paywall.
- **Modelo de classificação**: `claude-haiku-4-5-20251001` — modelo leve e econômico, adequado para classificação em escala.
- **Deduplicação em 2 passagens**: primeiro por hash SHA256 da URL normalizada, depois por similaridade de título via `difflib.SequenceMatcher` (threshold 0.85).
- **Período de coleta**: 180 dias retroativos à data de execução.
- **Tratamento de erros**: toda exceção de rede e de API é capturada com try/except — o pipeline nunca interrompe por falha em uma única empresa ou item.
- **Rate limiting**: sleep de 0.5s entre chamadas à API para respeitar os limites da Anthropic.
- **Encoding**: CSV de saída em UTF-8 com BOM (`utf-8-sig`) para abrir corretamente no Excel.
- **Backend matplotlib**: `Agg` (sem GUI) para compatibilidade com ambientes Windows sem display.
- **Logging**: dois handlers simultâneos — arquivo `logs/run.log` e terminal — com timestamp em cada linha.
