"""
run.py — Orquestrador principal do pipeline de monitoramento de crédito.

Fluxo:
  1. Configura logging (arquivo + terminal)
  2. Carrega companies.csv
  3. Para cada empresa: coleta links, extrai snippets, deduplica, classifica
  4. Salva output/news.csv com 12 colunas
  5. Gera gráficos e PDF via monitor.py
"""

import csv
import logging
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

# Garante que a raiz do projeto está no path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.collector import buscar_links, deduplicar, extrair_snippet
from scripts.classifier import classify_llm

# ── Colunas de saída ──────────────────────────────────────────────────────────
COLUNAS = [
    "empresa",
    "ticker",
    "data_publicacao",
    "fonte",
    "tipo",
    "titulo",
    "url",
    "snippet_ou_trecho",
    "sentimento",
    "tags",
    "severidade",
    "resumo_curto",
]


def configurar_logging(log_path: Path) -> None:
    """Configura logging para arquivo e terminal com timestamp."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Limpar handlers anteriores (evita duplicidade ao re-executar)
    root_logger.handlers.clear()

    # Handler para arquivo
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root_logger.addHandler(fh)

    # Handler para terminal
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(fmt, datefmt))
    root_logger.addHandler(sh)


def tags_para_string(tags) -> str:
    """Converte lista de tags para string separada por ;."""
    if isinstance(tags, list):
        return ";".join(tags)
    return str(tags) if tags else "setor_macro"


def main() -> None:
    # Cria pastas necessárias
    output_dir = ROOT / "output"
    charts_dir = output_dir / "charts"
    logs_dir = ROOT / "logs"
    for d in [output_dir, charts_dir, logs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    configurar_logging(logs_dir / "run.log")
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Iniciando pipeline de monitoramento de crédito")
    logger.info("=" * 60)

    # Carrega empresas
    companies_path = ROOT / "companies.csv"
    with open(companies_path, encoding="utf-8") as f:
        empresas = [row for row in csv.DictReader(f) if row.get("empresa", "").strip()]
    total_empresas = len(empresas)
    logger.info("Carregadas %d empresas do portfólio", total_empresas)

    todos_itens = []
    total_brutos = 0
    total_deduped = 0

    for idx, empresa in enumerate(empresas, start=1):
        nome = empresa["empresa"]
        ticker = empresa["ticker"]
        prefix = f"[{idx}/{total_empresas}] {nome}"

        try:
            logger.info("%s — coletando...", prefix)
            items = buscar_links(empresa)
            n_brutos = len(items)
            total_brutos += n_brutos

            # Deduplica ANTES de extrair snippets (economiza requisições)
            items = deduplicar(items)
            n_deduped = len(items)
            total_deduped += n_deduped
            logger.info(
                "%s — %d itens coletados, %d após dedupe",
                prefix, n_brutos, n_deduped,
            )

            # Extrai snippets apenas dos itens que ainda não têm (ex: itens de RI)
            for item in items:
                if not item.get("snippet_ou_trecho"):
                    item["snippet_ou_trecho"] = extrair_snippet(item["url"])

            # Classifica cada item
            itens_empresa = []
            for i, item in enumerate(items, start=1):
                logger.info("%s — classificando item %d/%d", prefix, i, n_deduped)
                classificacao = classify_llm(item)
                item.update(classificacao)
                item["empresa"] = nome
                item["ticker"] = ticker
                item["tags"] = tags_para_string(item.get("tags"))
                itens_empresa.append(item)

            todos_itens.extend(itens_empresa)

            # Salva CSV incremental após cada empresa (evita perder progresso)
            output_csv = output_dir / "news.csv"
            df_parcial = pd.DataFrame(todos_itens)
            for col in COLUNAS:
                if col not in df_parcial.columns:
                    df_parcial[col] = ""
            df_parcial[COLUNAS].to_csv(output_csv, index=False, encoding="utf-8-sig")
            logger.info("%s — %d itens salvos no CSV parcial", prefix, len(itens_empresa))

        except Exception as exc:
            logger.error("%s — ERRO inesperado: %s. Pulando empresa.", prefix, exc)
            continue

    # CSV final
    output_csv = output_dir / "news.csv"
    if not todos_itens:
        logger.error("Nenhum item coletado. Pipeline encerrado sem output.")
        return

    df = pd.DataFrame(todos_itens)
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUNAS]
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    logger.info("CSV salvo em: %s", output_csv)

    # Resumo final
    sentimentos = Counter(df["sentimento"])
    severidades = Counter(df["severidade"])
    logger.info("=" * 60)
    logger.info("RESUMO FINAL")
    logger.info("  Empresas processadas: %d/%d", total_empresas, total_empresas)
    logger.info("  Itens brutos coletados: %d", total_brutos)
    logger.info("  Itens após dedupe: %d", total_deduped)
    logger.info("  Total no CSV: %d", len(df))
    logger.info("  Sentimentos: %s", dict(sentimentos))
    logger.info("  Severidades: %s", dict(severidades))
    logger.info("=" * 60)

    # Gera relatório (monitor.py)
    try:
        from scripts.monitor import gerar_relatorio
        logger.info("Gerando gráficos e PDF do monitor...")
        gerar_relatorio(output_csv)
        logger.info("Monitor gerado com sucesso.")
    except Exception as exc:
        logger.error("Erro ao gerar monitor: %s", exc)

    print(f"\nPipeline concluído. {len(df)} itens salvos em output/news.csv")


if __name__ == "__main__":
    main()
