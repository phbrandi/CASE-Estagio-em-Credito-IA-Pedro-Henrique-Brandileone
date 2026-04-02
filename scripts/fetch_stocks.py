"""
fetch_stocks.py — Coleta dados históricos de preço dos últimos 6 meses
para as 15 empresas do portfólio e salva em output/stock_data.csv.
"""

import csv
import logging
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

# Garante que a raiz do projeto está no path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Colunas de saída na ordem exata exigida
COLUNAS = ["empresa", "ticker", "date", "open", "high", "low", "close", "volume"]


def fetch_company(empresa: str, ticker: str, idx: int, total: int) -> pd.DataFrame | None:
    """Busca os últimos 6 meses de dados de preço para uma empresa."""
    ticker_sa = f"{ticker}.SA"
    logger.info("[%d/%d] Buscando %s (%s)...", idx, total, empresa, ticker_sa)

    try:
        df = yf.download(
            ticker_sa,
            period="6mo",
            auto_adjust=True,
            progress=False,
        )

        if df is None or df.empty:
            logger.warning("[%d/%d] %s — FALHA: nenhum dado retornado para %s", idx, total, empresa, ticker_sa)
            return None

        # Achatar MultiIndex de colunas se existir (yfinance 0.2+ pode retornar)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Renomear colunas para minúsculo
        df.columns = [c.lower() for c in df.columns]

        # Manter apenas as colunas que nos interessam
        colunas_disponiveis = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[colunas_disponiveis].copy()

        # Converter índice de data para coluna string YYYY-MM-DD
        df = df.reset_index()
        df.rename(columns={"index": "date", "Date": "date"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # Arredondar preços e converter volume para inteiro
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = df[col].round(2)
        if "volume" in df.columns:
            df["volume"] = df["volume"].fillna(0).astype(int)

        # Adicionar identificação da empresa
        df.insert(0, "empresa", empresa)
        df.insert(1, "ticker", ticker)

        data_inicio = df["date"].min()
        data_fim = df["date"].max()
        logger.info(
            "[%d/%d] %s — %d dias de dados coletados (de %s até %s)",
            idx, total, empresa, len(df), data_inicio, data_fim,
        )
        return df

    except Exception as exc:
        logger.warning("[%d/%d] %s — FALHA: %s", idx, total, empresa, exc)
        return None


def main() -> None:
    companies_path = ROOT / "companies.csv"
    output_path = ROOT / "output" / "stock_data.csv"

    # Carrega empresas do CSV
    with open(companies_path, encoding="utf-8") as f:
        empresas = [row for row in csv.DictReader(f) if row.get("empresa", "").strip()]

    total = len(empresas)
    logger.info("Iniciando coleta de dados históricos para %d empresas", total)

    frames = []
    falhas = []

    for idx, row in enumerate(empresas, start=1):
        nome = row["empresa"].strip()
        ticker = row["ticker"].strip()
        df = fetch_company(nome, ticker, idx, total)
        if df is not None:
            frames.append(df)
        else:
            falhas.append(nome)

    if not frames:
        logger.error("Nenhum dado coletado. Encerrando sem gerar CSV.")
        return

    # Consolidar e garantir ordem de colunas
    resultado = pd.concat(frames, ignore_index=True)
    for col in COLUNAS:
        if col not in resultado.columns:
            resultado[col] = ""
    resultado = resultado[COLUNAS]

    resultado.to_csv(output_path, index=False, encoding="utf-8-sig")

    # Resumo final
    com_dados = total - len(falhas)
    periodo_medio = resultado.groupby("empresa")["date"].count().mean()
    print()
    print("=" * 55)
    print("RESUMO FINAL — COLETA DE DADOS HISTÓRICOS")
    print("=" * 55)
    print(f"  Total de empresas com dados coletados : {com_dados}/{total}")
    print(f"  Total de linhas no CSV                : {len(resultado)}")
    print(f"  Período médio de dados                : {periodo_medio:.0f} dias")
    if falhas:
        print(f"  Empresas que falharam                 : {', '.join(falhas)}")
    print(f"  CSV salvo em                          : {output_path}")
    print("=" * 55)


if __name__ == "__main__":
    main()
