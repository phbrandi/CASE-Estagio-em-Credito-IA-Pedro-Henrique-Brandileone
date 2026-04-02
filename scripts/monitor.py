"""
monitor.py — Gera gráficos PNG e PDF de monitoramento de crédito.

Entrada: output/news.csv
Saída:
  - output/charts/ranking_atencao.png
  - output/charts/heatmap.png
  - output/charts/tendencia.png
  - output/charts/top_tags.png
  - output/monitor.pdf
"""

import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Backend sem GUI para Windows
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)


# ── Paletas de cores ──────────────────────────────────────────────────────────
COR_POSITIVO = "#2ecc71"
COR_NEUTRO = "#95a5a6"
COR_NEGATIVO = "#e74c3c"


def _carregar_dados(csv_path: Path) -> pd.DataFrame:
    """Carrega o news.csv e prepara colunas derivadas."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # Normaliza tags (string → lista)
    df["tags_lista"] = df["tags"].fillna("setor_macro").apply(
        lambda x: [t.strip() for t in str(x).split(";") if t.strip()]
    )

    # Normaliza data
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce", utc=True)
    df["mes"] = df["data_publicacao"].dt.to_period("M")

    # Garante severidade numérica
    df["severidade"] = pd.to_numeric(df["severidade"], errors="coerce").fillna(1).astype(int)

    return df


def _score_atencao(grupo: pd.DataFrame) -> float:
    """Calcula score de atenção: negativas*2 + sev3*3."""
    neg = (grupo["sentimento"] == "negativo").sum()
    sev3 = (grupo["severidade"] == 3).sum()
    return neg * 2 + sev3 * 3


def gerar_ranking_atencao(df: pd.DataFrame, output_path: Path) -> None:
    """Barras horizontais com score de atenção por empresa."""
    scores = df.groupby("empresa").apply(_score_atencao).sort_values()
    empresas = scores.index.tolist()
    valores = scores.values.tolist()

    fig, ax = plt.subplots(figsize=(10, 6))

    # Gradiente verde → vermelho
    max_val = max(valores) if max(valores) > 0 else 1
    cmap = plt.cm.RdYlGn_r
    bar_colors = [cmap(v / max_val) for v in valores]

    bars = ax.barh(empresas, valores, color=bar_colors, edgecolor="white", linewidth=0.5)

    # Anotações
    for bar, val in zip(bars, valores):
        ax.text(
            bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
            str(int(val)), va="center", ha="left", fontsize=9, color="#333333"
        )

    ax.set_xlabel("Score de Atenção", fontsize=11)
    ax.set_title("Ranking de Atenção por Empresa", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, max_val * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico salvo: %s", output_path)


def gerar_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """Heatmap empresa x mês com contagem de eventos negativos/críticos."""
    df_filtrado = df[
        (df["sentimento"] == "negativo") | (df["severidade"] >= 3)
    ].copy()

    # Últimos 6 meses
    ultimo_mes = df["mes"].max()
    meses = pd.period_range(end=ultimo_mes, periods=6, freq="M")

    pivot_data = {}
    for mes in meses:
        sub = df_filtrado[df_filtrado["mes"] == mes]
        pivot_data[str(mes)] = sub.groupby("empresa").size()

    pivot = pd.DataFrame(pivot_data, index=df["empresa"].unique()).fillna(0).astype(int)
    # Garante ordem dos meses
    cols_existentes = [str(m) for m in meses if str(m) in pivot.columns]
    pivot = pivot[cols_existentes]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        pivot, annot=True, fmt="d", cmap="YlOrRd",
        linewidths=0.5, linecolor="#dddddd",
        ax=ax, cbar_kws={"label": "Eventos negativos/críticos"}
    )
    ax.set_title("Eventos Negativos ou Críticos por Empresa e Mês", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Mês", fontsize=10)
    ax.set_ylabel("Empresa", fontsize=10)
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico salvo: %s", output_path)


def gerar_tendencia(df: pd.DataFrame, output_path: Path) -> None:
    """Linha do tempo: contagem mensal de itens por sentimento."""
    mensal = df.groupby(["mes", "sentimento"]).size().unstack(fill_value=0)

    # Garante as três colunas
    for sent in ["positivo", "neutro", "negativo"]:
        if sent not in mensal.columns:
            mensal[sent] = 0

    meses_str = [str(m) for m in mensal.index]
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(meses_str, mensal["positivo"], color=COR_POSITIVO, marker="o",
            linewidth=2, markersize=5, label="Positivo")
    ax.plot(meses_str, mensal["neutro"], color=COR_NEUTRO, marker="s",
            linewidth=2, markersize=5, label="Neutro")
    ax.plot(meses_str, mensal["negativo"], color=COR_NEGATIVO, marker="^",
            linewidth=2, markersize=5, label="Negativo")

    ax.set_title("Tendência Mensal por Sentimento (Portfólio)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Mês", fontsize=10)
    ax.set_ylabel("Quantidade de Notícias", fontsize=10)
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico salvo: %s", output_path)


def gerar_top_tags(df: pd.DataFrame, output_path: Path) -> None:
    """Barras verticais com as tags mais frequentes no portfólio."""
    contador = Counter()
    for lista in df["tags_lista"]:
        contador.update(lista)

    if not contador:
        logger.warning("Nenhuma tag encontrada para gráfico top_tags")
        return

    tags_ord = sorted(contador.items(), key=lambda x: x[1], reverse=True)
    tags_nomes = [t[0] for t in tags_ord]
    tags_vals = [t[1] for t in tags_ord]

    fig, ax = plt.subplots(figsize=(10, 5))
    bar_colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(tags_nomes)))[::-1]
    ax.bar(tags_nomes, tags_vals, color=bar_colors, edgecolor="white")
    ax.set_title("Tags Mais Frequentes no Portfólio", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Tag", fontsize=10)
    ax.set_ylabel("Ocorrências", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    for i, v in enumerate(tags_vals):
        ax.text(i, v + 0.3, str(v), ha="center", va="bottom", fontsize=8, color="#333333")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico salvo: %s", output_path)


def _gerar_resumo_executivo(df: pd.DataFrame) -> str:
    """Gera texto de resumo executivo programaticamente."""
    # Top 3 empresas por score de atenção
    scores = df.groupby("empresa").apply(_score_atencao).sort_values(ascending=False)
    top3 = scores.head(3)

    # Tags mais frequentes
    contador = Counter()
    for lista in df["tags_lista"]:
        contador.update(lista)
    top_tags = [t[0] for t in sorted(contador.items(), key=lambda x: x[1], reverse=True)[:3]]

    # Contagem de sentimentos
    sent_counts = df["sentimento"].value_counts()
    total = len(df)
    pct_neg = int(sent_counts.get("negativo", 0) / total * 100) if total else 0

    linhas = []
    linhas.append(
        f"O monitoramento abrangeu {total} notícias e comunicados de {df['empresa'].nunique()} "
        f"empresas do portfólio. "
    )
    if len(top3) >= 1:
        linhas.append(
            f"As empresas que demandam maior atenção são: "
            + ", ".join([f"{emp} (score {int(sc)})" for emp, sc in top3.items()])
            + ". "
        )
    linhas.append(
        f"{pct_neg}% das notícias apresentaram sentimento negativo. "
    )
    if top_tags:
        linhas.append(
            f"Os principais temas identificados foram: {', '.join(top_tags)}."
        )
    return " ".join(linhas)


def gerar_pdf(df: pd.DataFrame, charts_dir: Path, output_path: Path) -> None:
    """Gera o PDF com 3 páginas: resumo, gráficos de ranking/heatmap, tendência/tags/tabela."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "Titulo", parent=styles["Title"],
        fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a2a4a"),
    )
    subtitulo_style = ParagraphStyle(
        "Subtitulo", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#555555"), spaceAfter=16,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=16, spaceAfter=12,
    )
    secao_style = ParagraphStyle(
        "Secao", parent=styles["Heading2"],
        fontSize=13, textColor=colors.HexColor("#1a2a4a"), spaceBefore=14, spaceAfter=6,
    )
    tabela_header_style = ParagraphStyle(
        "TabelaHeader", parent=styles["Normal"],
        fontSize=8, textColor=colors.white, fontName="Helvetica-Bold",
    )
    tabela_cell_style = ParagraphStyle(
        "TabelaCell", parent=styles["Normal"],
        fontSize=7, leading=10,
    )

    story = []
    largura_img = 16 * cm

    data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # ── Página 1: Capa + Resumo Executivo ─────────────────────────────────────
    story.append(Paragraph("Monitor de Crédito", titulo_style))
    story.append(Paragraph("Portfólio de Acompanhamento", titulo_style))
    story.append(Paragraph(f"Gerado em: {data_geracao}", subtitulo_style))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Resumo Executivo", secao_style))
    resumo = _gerar_resumo_executivo(df)
    story.append(Paragraph(resumo, body_style))

    # Tabela de métricas sumárias
    sent_counts = df["sentimento"].value_counts()
    sev_counts = df["severidade"].value_counts().sort_index()
    metricas = [
        ["Métrica", "Valor"],
        ["Total de notícias", str(len(df))],
        ["Empresas monitoradas", str(df["empresa"].nunique())],
        ["Notícias positivas", str(sent_counts.get("positivo", 0))],
        ["Notícias neutras", str(sent_counts.get("neutro", 0))],
        ["Notícias negativas", str(sent_counts.get("negativo", 0))],
        ["Severidade 1 (baixo)", str(sev_counts.get(1, 0))],
        ["Severidade 2 (médio)", str(sev_counts.get(2, 0))],
        ["Severidade 3 (alto)", str(sev_counts.get(3, 0))],
    ]
    t_metricas = Table(metricas, colWidths=[9 * cm, 4 * cm])
    t_metricas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2a4a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f5f5"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_metricas)

    # ── Página 2: Ranking + Heatmap ───────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Ranking de Atenção e Heatmap Temporal", secao_style))

    for nome_img in ["ranking_atencao.png", "heatmap.png"]:
        img_path = charts_dir / nome_img
        if img_path.exists():
            story.append(Image(str(img_path), width=largura_img, height=9 * cm))
            story.append(Spacer(1, 0.4 * cm))

    # ── Página 3: Tendência + Top Tags + Tabela top 10 ───────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Tendência Temporal e Principais Temas", secao_style))

    for nome_img in ["tendencia.png", "top_tags.png"]:
        img_path = charts_dir / nome_img
        if img_path.exists():
            story.append(Image(str(img_path), width=largura_img, height=7.5 * cm))
            story.append(Spacer(1, 0.3 * cm))

    # Tabela: top 10 notícias de maior severidade
    story.append(Paragraph("Top Notícias por Severidade", secao_style))
    df_sev3 = df[df["severidade"] == 3].sort_values("data_publicacao", ascending=False).head(10)
    if df_sev3.empty:
        df_sev3 = df.sort_values("severidade", ascending=False).head(10)

    tabela_dados = [[
        Paragraph("Empresa", tabela_header_style),
        Paragraph("Data", tabela_header_style),
        Paragraph("Título", tabela_header_style),
        Paragraph("URL", tabela_header_style),
    ]]
    for _, row in df_sev3.iterrows():
        data_str = ""
        if pd.notna(row.get("data_publicacao")):
            try:
                data_str = pd.to_datetime(row["data_publicacao"]).strftime("%d/%m/%Y")
            except Exception:
                data_str = str(row.get("data_publicacao", ""))[:10]
        url_curta = str(row.get("url", ""))[:60] + "..."
        tabela_dados.append([
            Paragraph(str(row.get("empresa", ""))[:20], tabela_cell_style),
            Paragraph(data_str, tabela_cell_style),
            Paragraph(str(row.get("titulo", ""))[:80], tabela_cell_style),
            Paragraph(url_curta, tabela_cell_style),
        ])

    col_widths = [3.5 * cm, 2.2 * cm, 6.5 * cm, 4.5 * cm]
    t_top = Table(tabela_dados, colWidths=col_widths, repeatRows=1)
    t_top.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2a4a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_top)

    doc.build(story)
    logger.info("PDF gerado: %s", output_path)


def gerar_relatorio(csv_path: Path | str | None = None) -> None:
    """Função principal — carrega dados, gera gráficos e PDF."""
    if csv_path is None:
        csv_path = ROOT / "output" / "news.csv"
    csv_path = Path(csv_path)

    if not csv_path.exists():
        logger.error("Arquivo não encontrado: %s", csv_path)
        return

    charts_dir = ROOT / "output" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Carregando dados de: %s", csv_path)
    df = _carregar_dados(csv_path)
    logger.info("Total de registros: %d", len(df))

    # Gera os 4 gráficos
    gerar_ranking_atencao(df, charts_dir / "ranking_atencao.png")
    gerar_heatmap(df, charts_dir / "heatmap.png")
    gerar_tendencia(df, charts_dir / "tendencia.png")
    gerar_top_tags(df, charts_dir / "top_tags.png")

    # Gera o PDF
    pdf_path = ROOT / "output" / "monitor.pdf"
    gerar_pdf(df, charts_dir, pdf_path)

    logger.info("Relatório completo gerado com sucesso.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Aceita caminho opcional como argumento
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    gerar_relatorio(csv_path)
    print("Monitor gerado com sucesso. Verifique output/monitor.pdf e output/charts/")
