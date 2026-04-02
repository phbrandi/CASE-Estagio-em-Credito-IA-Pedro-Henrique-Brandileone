"""
generate_dashboard.py — Gera dashboard HTML interativo de monitoramento de crédito.
Lê companies.csv, output/news.csv e output/stock_data.csv.
Gera output/dashboard.html autocontido com tema escuro, 3 abas e Chart.js.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

SECTOR_COLORS = {
    "Óleo & Gás": "#F59E0B",
    "Infraestrutura": "#3B82F6",
    "Serviços Industriais": "#8B5CF6",
    "Financeiro/Outros": "#10B981",
}

COMPANY_SECTORS = {
    "OceanPact": "Óleo & Gás", "Brava Energia": "Óleo & Gás",
    "PetroRio": "Óleo & Gás", "PetroReconcavo": "Óleo & Gás", "NTS": "Óleo & Gás",
    "Aegea": "Infraestrutura", "Equatorial": "Infraestrutura",
    "Copasa": "Infraestrutura", "Cosan": "Infraestrutura",
    "Vamos": "Serviços Industriais", "Mills": "Serviços Industriais", "Armac": "Serviços Industriais",
    "BTG": "Financeiro/Outros", "Unipar": "Financeiro/Outros", "Multiplan": "Financeiro/Outros",
}

# Cor individual por empresa — usada nas linhas do Gráfico A para diferenciar dentro do setor.
# Cores intencionalmente misturadas entre setores para máximo contraste visual.
COMPANY_COLORS = {
    # Óleo & Gás: âmbar, vermelho, azul, esmeralda, laranja — famílias distintas
    "OceanPact":      "#F59E0B",  # âmbar
    "Brava Energia":  "#EF4444",  # vermelho
    "PetroRio":       "#3B82F6",  # azul
    "PetroReconcavo": "#10B981",  # esmeralda
    "NTS":            "#F97316",  # laranja
    # Infraestrutura: violeta, ciano, rosa-quente, lima — famílias distintas
    "Aegea":          "#8B5CF6",  # violeta
    "Equatorial":     "#06B6D4",  # ciano
    "Copasa":         "#EC4899",  # rosa-quente
    "Cosan":          "#84CC16",  # lima
    # Serviços Industriais: rosa-vivo, teal, roxo
    "Vamos":          "#F43F5E",  # rosa-vivo
    "Mills":          "#14B8A6",  # teal
    "Armac":          "#A855F7",  # roxo
    # Financeiro/Outros: amarelo, verde-menta, azul-céu
    "BTG":            "#FBBF24",  # amarelo
    "Unipar":         "#34D399",  # verde-menta
    "Multiplan":      "#38BDF8",  # azul-céu
}


def main() -> None:
    df_comp   = pd.read_csv(ROOT / "companies.csv", encoding="utf-8")
    df_news   = pd.read_csv(ROOT / "output" / "news.csv", encoding="utf-8-sig")
    df_stocks = pd.read_csv(ROOT / "output" / "stock_data.csv", encoding="utf-8-sig")

    df_news["_dt"] = pd.to_datetime(df_news["data_publicacao"], errors="coerce", utc=True)
    df_news["date_iso"] = df_news["_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").fillna("")
    df_news["severidade"] = pd.to_numeric(df_news["severidade"], errors="coerce").fillna(1).astype(int)
    df_news["setor"] = df_news["empresa"].map(COMPANY_SECTORS).fillna("Financeiro/Outros")
    df_news = df_news.fillna("")

    news_list = []
    for _, row in df_news.iterrows():
        tags_raw = str(row.get("tags", ""))
        tags = [t.strip() for t in tags_raw.split(";") if t.strip()]
        news_list.append({
            "empresa": str(row["empresa"]), "ticker": str(row["ticker"]),
            "data": str(row["date_iso"]), "fonte": str(row["fonte"]),
            "tipo": str(row["tipo"]), "titulo": str(row["titulo"]),
            "url": str(row["url"]), "snippet": str(row.get("snippet_ou_trecho", ""))[:500],
            "sentimento": str(row["sentimento"]), "tags": tags,
            "severidade": int(row["severidade"]), "resumo": str(row.get("resumo_curto", ""))[:300],
            "setor": str(row["setor"]),
        })

    df_stocks["_dt"] = pd.to_datetime(df_stocks["date"])
    stocks_list = []
    for empresa, grp in df_stocks.groupby("empresa"):
        grp = grp.sort_values("_dt").copy()
        fc = grp["close"].iloc[0]
        grp["close_norm"] = (grp["close"] / fc * 100).round(2) if fc and fc > 0 else 100.0
        sector = COMPANY_SECTORS.get(str(empresa), "Financeiro/Outros")
        for _, row in grp.iterrows():
            stocks_list.append({
                "empresa": str(empresa), "ticker": str(row["ticker"]),
                "date": str(row["_dt"].strftime("%Y-%m-%d")),
                "close": round(float(row["close"]), 2),
                "close_norm": round(float(row["close_norm"]), 2),
                "setor": sector,
            })

    companies_list = df_comp.fillna("").to_dict(orient="records")

    json_news            = json.dumps(news_list,       ensure_ascii=False)
    json_stocks          = json.dumps(stocks_list,     ensure_ascii=False)
    json_companies       = json.dumps(companies_list,  ensure_ascii=False)
    json_sector_colors   = json.dumps(SECTOR_COLORS,   ensure_ascii=False)
    json_company_sectors = json.dumps(COMPANY_SECTORS, ensure_ascii=False)
    json_company_colors  = json.dumps(COMPANY_COLORS,  ensure_ascii=False)

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    valid_dt = df_news["_dt"].dropna()
    date_min = valid_dt.min().strftime("%d/%m/%Y") if not valid_dt.empty else ""
    date_max = valid_dt.max().strftime("%d/%m/%Y") if not valid_dt.empty else ""

    html = get_html_template()
    html = html.replace("INJECT_DATA_NEWS",       json_news)
    html = html.replace("INJECT_DATA_STOCKS",     json_stocks)
    html = html.replace("INJECT_DATA_COMPANIES",  json_companies)
    html = html.replace("INJECT_SECTOR_COLORS",   json_sector_colors)
    html = html.replace("INJECT_COMPANY_SECTORS", json_company_sectors)
    html = html.replace("INJECT_COMPANY_COLORS",  json_company_colors)
    html = html.replace("INJECT_GENERATED_AT",    generated_at)
    html = html.replace("INJECT_DATE_MIN",        date_min)
    html = html.replace("INJECT_DATE_MAX",        date_max)

    out = ROOT / "output" / "dashboard.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = out.stat().st_size / 1024
    logger.info("Dashboard gerado: output/dashboard.html (%.0f KB)", size_kb)
    print(f"Dashboard gerado: output/dashboard.html ({size_kb:.0f} KB)")


def get_html_template() -> str:
    return r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Monitor de Crédito — Portfólio</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0A0E1A;color:#F9FAFB;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px}
.hdr{background:#0D1117;border-bottom:1px solid #1F2937;padding:13px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.hdr h1{font-size:17px;font-weight:700}.hdr p{font-size:11px;color:#6B7280;margin-top:2px}
.hdr-r{text-align:right;font-size:12px;color:#6B7280;line-height:1.7}
.tabs{display:flex;background:#0D1117;border-bottom:1px solid #1F2937;padding:0 24px;position:sticky;top:55px;z-index:99}
.tab-btn{padding:10px 18px;cursor:pointer;color:#6B7280;border:none;border-bottom:2px solid transparent;background:none;font-size:13px;transition:all .15s}
.tab-btn:hover{color:#F9FAFB}.tab-btn.active{color:#F9FAFB;border-bottom-color:#3B82F6;background:#111827}
.tc{display:none;padding:20px 24px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;align-items:start}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.card{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px}
.st{font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:11px}
.scroll340{max-height:340px;overflow-y:auto;padding-right:4px}
.ni{padding:9px 0;border-bottom:1px solid #1F2937}.ni:last-child{border-bottom:none}
.ni-h{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px}
.ni-d{color:#6B7280;font-size:11px;margin-left:auto;white-space:nowrap}
.ni-t a{color:#F9FAFB;text-decoration:none;font-size:13px;line-height:1.4}.ni-t a:hover{color:#3B82F6}
.ni-s{color:#6B7280;font-size:11px;margin-top:3px;line-height:1.4}
.badge{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;white-space:nowrap}
.ac{background:#1A0A0A;border-left:3px solid #7F1D1D;padding:10px 12px;border-radius:0 4px 4px 0;margin-bottom:8px}
.bt{flex:1;height:18px;background:#1F2937;border-radius:3px;overflow:hidden;display:flex}.bs{height:100%}
.dtbl{width:100%;border-collapse:collapse}
.dtbl th{background:#0A0E1A;color:#6B7280;font-size:10px;text-transform:uppercase;padding:9px 12px;text-align:left;border-bottom:1px solid #1F2937;white-space:nowrap}
.dtbl td{padding:8px 12px;border-bottom:1px solid #1F2937;vertical-align:middle}
.dtbl tr:nth-child(even) td{background:#0F1623}.dtbl tr:hover td{background:#1A2332}
.hm-tbl{width:100%;border-collapse:collapse}
.hm-tbl th{background:#0A0E1A;color:#9CA3AF;font-size:10px;text-transform:uppercase;padding:7px 10px;text-align:center;border:1px solid #0A0E1A}
.hm-tbl th:first-child{text-align:left;min-width:130px}
.hm-tbl td{padding:7px 10px;text-align:center;border:1px solid #0A0E1A;font-size:12px;min-width:68px}
.hm-tbl td:first-child{text-align:left;font-weight:600;padding-left:4px}
.cw{position:relative;height:300px}.cwt{position:relative;height:370px}.cwl{position:relative;height:440px}
.cleg{display:flex;gap:12px;font-size:11px;color:#9CA3AF;flex-wrap:wrap;margin-bottom:8px}
.cleg-i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}
.cleg-c{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:middle}
/* Tab 2 selector */
.t2-sel{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:14px 16px;margin-bottom:16px}
.t2-row1{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.t2-row2{display:flex;gap:6px;flex-wrap:wrap;padding-top:10px;border-top:1px solid #1F2937;margin-top:10px}
.selb{padding:6px 13px;border-radius:4px;cursor:pointer;font-size:12px;border:1px solid #374151;background:#1F2937;color:#9CA3AF;transition:all .15s;white-space:nowrap}
.selb:hover{background:#374151;color:#F9FAFB}
.t2-div{width:1px;height:20px;background:#374151;margin:0 4px}
.t2-badge{margin-top:10px;font-size:13px;padding-top:8px;border-top:1px solid #1F2937}
/* Explorer */
.fb{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:13px;background:#111827;border:1px solid #1F2937;border-radius:8px;margin-bottom:13px}
.fs{background:#1F2937;color:#F9FAFB;border:1px solid #374151;padding:7px 10px;border-radius:4px;font-size:13px;min-width:145px}
.fs:focus{outline:1px solid #3B82F6}
.breset{background:#374151;color:#9CA3AF;border:none;padding:7px 14px;border-radius:4px;cursor:pointer;font-size:13px}
.breset:hover{background:#4B5563;color:#F9FAFB}
.nc{color:#9CA3AF;font-size:13px;margin-bottom:10px}
.ntw{overflow-y:auto;max-height:580px}
.nt{width:100%;border-collapse:collapse}
.nt th{background:#0A0E1A;color:#6B7280;font-size:10px;text-transform:uppercase;padding:9px 10px;text-align:left;border-bottom:1px solid #1F2937;position:sticky;top:0;z-index:10;white-space:nowrap}
.nt td{padding:7px 10px;border-bottom:1px solid #1F2937;vertical-align:top;font-size:13px}
.nt tr:nth-child(odd) td{background:#111827}.nt tr:nth-child(even) td{background:#0F1623}
.nt tr:hover td{background:#1A2332}
.nt td a{color:#F9FAFB;text-decoration:none}.nt td a:hover{color:#3B82F6}
.pill{display:inline-block;background:#1F2937;border:1px solid #374151;color:#6B7280;font-size:10px;padding:1px 5px;border-radius:3px;margin:1px;white-space:nowrap}
/* Modal */
.modal{display:none;position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.78);align-items:center;justify-content:center}
.mbox{background:#111827;border:1px solid #374151;border-radius:10px;width:92%;max-width:720px;max-height:82vh;display:flex;flex-direction:column}
.mhdr{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #1F2937;flex-shrink:0}
.mbody{overflow-y:auto;padding:0 18px 18px;flex:1}
.mcls{background:none;border:none;color:#9CA3AF;cursor:pointer;font-size:24px;line-height:1;padding:0}.mcls:hover{color:#F9FAFB}
::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-track{background:#0A0E1A}::-webkit-scrollbar-thumb{background:#374151;border-radius:3px}
</style>
</head>
<body>

<!-- Modal -->
<div id="modal" class="modal" onclick="if(event.target===this)hideModal()">
  <div class="mbox">
    <div class="mhdr"><span id="modal-title" style="font-weight:700;font-size:14px;color:#F9FAFB"></span><button class="mcls" onclick="hideModal()">&times;</button></div>
    <div id="modal-body" class="mbody"></div>
  </div>
</div>

<div class="hdr">
  <div><h1>Monitor de Crédito</h1><p>Portfólio de Acompanhamento — 15 empresas</p></div>
  <div class="hdr-r"><div>Gerado em INJECT_GENERATED_AT</div><div>Período: INJECT_DATE_MIN &rarr; INJECT_DATE_MAX</div></div>
</div>
<nav class="tabs">
  <button class="tab-btn" onclick="showTab(1)">Visão Geral</button>
  <button class="tab-btn" onclick="showTab(2)">Análise Histórica</button>
  <button class="tab-btn" onclick="showTab(3)">Explorador de Notícias</button>
</nav>

<!-- ══ Tab 1 ══════════════════════════════════════════════════ -->
<div id="tab1" class="tc">
  <div class="g2">
    <div class="card"><div class="st">Últimas notícias</div><div class="scroll340" id="latest-news"></div></div>
    <div class="card"><div class="st">Alertas críticos — Severidade 3</div><div class="scroll340" id="critical-alerts"></div></div>
  </div>

  <div class="g4">
    <div class="card" id="m6"></div>
    <div class="card" id="m3"></div>
    <div class="card" id="m1"></div>
    <div class="card" id="m7"></div>
  </div>

  <div class="card" style="margin-bottom:16px">
    <div class="st">Eventos por setor</div>
    <table class="dtbl"><thead><tr><th>Setor</th><th>Total</th><th>% Negativo</th><th>Alertas sev.3</th><th>Tendência (30d vs 30d ant.)</th></tr></thead>
    <tbody id="sector-tbody"></tbody></table>
  </div>

  <!-- Rankings + tema dist na mesma linha -->
  <div class="g2">
    <!-- Esquerda: score de atenção -->
    <div class="card">
      <div class="st">Score de atenção por empresa</div>
      <div class="cleg">
        <span><span class="cleg-i" style="background:#34D399"></span>Positivos</span>
        <span><span class="cleg-i" style="background:#374151"></span>Neutros</span>
        <span><span class="cleg-i" style="background:#EF4444"></span>Negativos</span>
        <span style="color:#4B5563;font-size:10px">Score = neg×2 + sev.3×3</span>
      </div>
      <div id="attn-rank"></div>
    </div>
    <!-- Direita: temas em destaque + distribuição empilhada -->
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="card" style="flex:0 0 auto">
        <div class="st">Temas em destaque</div>
        <div id="theme-rank"></div>
        <div class="cleg" style="margin-top:10px;padding-top:8px;border-top:1px solid #1F2937">
          <span><span class="cleg-i" style="background:#3B82F6"></span>&lt;25% negativos</span>
          <span><span class="cleg-i" style="background:#F59E0B"></span>25–50% negativos</span>
          <span><span class="cleg-i" style="background:#EF4444"></span>&gt;50% negativos</span>
        </div>
      </div>
      <div class="card" style="flex:1">
        <div class="st">Distribuição de temas por sentimento</div>
        <div class="cleg">
          <span><span class="cleg-i" style="background:#34D399"></span>Positivo</span>
          <span><span class="cleg-i" style="background:#374151"></span>Neutro</span>
          <span><span class="cleg-i" style="background:#EF4444"></span>Negativo</span>
        </div>
        <div style="position:relative;height:260px"><canvas id="ct1"></canvas></div>
      </div>
    </div>
  </div>
</div>

<!-- ══ Tab 2 ══════════════════════════════════════════════════ -->
<div id="tab2" class="tc">
  <!-- Seletor por botões -->
  <div class="t2-sel">
    <div class="t2-row1" id="t2-row1"></div>
    <div class="t2-row2" id="t2-row2"></div>
    <div class="t2-badge" id="t2-badge"></div>
  </div>

  <div class="card" style="margin-bottom:16px">
    <div class="st">Heatmap — eventos negativos por empresa e mês</div>
    <div class="cleg">
      <span><span class="cleg-i" style="background:#111827;border:1px solid #374151"></span>0 eventos</span>
      <span><span class="cleg-i" style="background:#1F2937"></span>1–2</span>
      <span><span class="cleg-i" style="background:#7F1D1D"></span>3–5</span>
      <span><span class="cleg-i" style="background:#991B1B"></span>6–9</span>
      <span><span class="cleg-i" style="background:#EF4444"></span>10+</span>
    </div>
    <div style="overflow-x:auto" id="heatmap"></div>
  </div>

  <!-- Gráfico A: preço + eventos clicáveis -->
  <div class="card" style="margin-bottom:16px">
    <div class="st">Preço base 100 + eventos — clique nos marcadores para ver as notícias</div>
    <div class="cleg">
      <span><span class="cleg-c" style="background:#34D399"></span>Evento positivo</span>
      <span><span class="cleg-c" style="background:#EF4444"></span>Evento negativo</span>
      <span><span class="cleg-c" style="background:#6B7280"></span>Evento neutro</span>
      <span><span class="cleg-c" style="background:#F59E0B"></span>Alerta sev.3</span>
      <span style="color:#4B5563;font-size:10px;font-style:italic">Linhas coloridas por empresa — fundo verde/vermelho = sentimento 7 dias (ao filtrar empresa ou setor)</span>
    </div>
    <div class="cwl"><canvas id="ca"></canvas></div>
    <div style="color:#4B5563;font-size:11px;margin-top:6px">* NTS: debênture sem cotação. Aegea: ticker indisponível no Yahoo Finance.</div>
  </div>

  <!-- Gráficos B e C lado a lado -->
  <div class="g2">
    <div class="card">
      <div class="st">Sentimento semanal vs Retorno semanal</div>
      <div class="cleg">
        <span><span class="cleg-c" style="background:#34D399"></span>Semana positiva (score &gt;0.15)</span>
        <span><span class="cleg-c" style="background:#EF4444"></span>Semana negativa</span>
        <span><span class="cleg-c" style="background:#F59E0B"></span>Com sev.3</span>
        <span><span class="cleg-c" style="background:#6B7280"></span>Neutra</span>
        <span style="color:#4B5563;font-size:10px;font-style:italic">Clique para ver notícias da semana</span>
      </div>
      <div class="cw"><canvas id="cb"></canvas></div>
    </div>
    <div class="card">
      <div class="st">Projeção de preço — sentimento atual + correlação histórica</div>
      <div class="cleg">
        <span><span class="cleg-i" style="background:#9CA3AF"></span>Histórico (base 100)</span>
        <span><span class="cleg-c" style="background:#F9FAFB;border:2px solid #9CA3AF"></span>Projeção próxima semana (ponto + banda ±1σ)</span>
        <span style="color:#4B5563;font-size:10px;font-style:italic">Linhas pontilhadas = bandas de confiança ±1σ. Apenas indicativo.</span>
      </div>
      <div id="cc-nodata" style="display:none;color:#6B7280;padding:40px;text-align:center;font-size:13px">Selecione uma empresa ou setor para ver a projeção</div>
      <div id="cc-wrap" class="cw"><canvas id="cc"></canvas></div>
    </div>
  </div>
</div>

<!-- ══ Tab 3 ══════════════════════════════════════════════════ -->
<div id="tab3" class="tc">
  <div class="fb">
    <select id="fe" class="fs" onchange="handleEmp(this.value)"><option value="">Empresa</option></select>
    <select id="fse" class="fs" onchange="handleSec(this.value)">
      <option value="">Setor</option>
      <option value="Óleo &amp; Gás">Óleo &amp; Gás</option>
      <option value="Infraestrutura">Infraestrutura</option>
      <option value="Serviços Industriais">Serviços Industriais</option>
      <option value="Financeiro/Outros">Financeiro/Outros</option>
    </select>
    <select id="fst" class="fs" onchange="f3.sentimento=this.value;applyF()">
      <option value="">Sentimento</option><option value="positivo">Positivo</option>
      <option value="neutro">Neutro</option><option value="negativo">Negativo</option>
    </select>
    <select id="fsv" class="fs" onchange="f3.severidade=this.value;applyF()">
      <option value="">Severidade</option><option value="1">1 — Baixo</option>
      <option value="2">2 — Médio</option><option value="3">3 — Alto</option>
    </select>
    <select id="ftm" class="fs" onchange="f3.tema=this.value;applyF()"><option value="">Tema</option></select>
    <button class="breset" onclick="resetF()">Limpar filtros</button>
  </div>
  <div class="nc" id="nctr">Carregando...</div>
  <div class="card" style="padding:0;overflow:hidden">
    <div class="ntw">
      <table class="nt">
        <thead><tr><th>Data</th><th>Empresa</th><th>Sev</th><th>Sent</th>
        <th style="min-width:220px">Título</th><th style="min-width:170px">Temas</th>
        <th style="min-width:210px">Resumo</th></tr></thead>
        <tbody id="ntb"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const DATA_NEWS      = INJECT_DATA_NEWS;
const DATA_STOCKS    = INJECT_DATA_STOCKS;
const DATA_COMPANIES = INJECT_DATA_COMPANIES;
const SECTOR_COLORS  = INJECT_SECTOR_COLORS;
const COMPANY_SECTORS= INJECT_COMPANY_SECTORS;
const COMPANY_COLORS = INJECT_COMPANY_COLORS;

Chart.defaults.color       = '#9CA3AF';
Chart.defaults.borderColor = '#1F2937';

// ── Plugins globais ────────────────────────────────────────────
// Plugin: fundo por sentimento (janela 7 dias)
Chart.register({
  id:'sentBg',
  beforeDraw(chart){
    const segs=chart.options.plugins?.sentBg?.segments;
    if(!segs||!segs.length)return;
    const{ctx,chartArea,scales}=chart;
    if(!scales.x||!chartArea)return;
    segs.forEach(s=>{
      const x1=Math.max(chartArea.left, scales.x.getPixelForValue(s.x1));
      const x2=Math.min(chartArea.right,scales.x.getPixelForValue(s.x2));
      if(x2<=x1)return;
      ctx.save();ctx.fillStyle=s.color;
      ctx.fillRect(x1,chartArea.top,x2-x1,chartArea.bottom-chartArea.top);
      ctx.restore();
    });
  }
});
// Plugin: linha vertical "Hoje"
Chart.register({
  id:'todayLine',
  afterDraw(chart){
    const idx=chart.options.plugins?.todayLine?.idx;
    if(idx==null)return;
    const{ctx,chartArea,scales}=chart;
    if(!scales.x||!chartArea)return;
    const x=scales.x.getPixelForValue(idx);
    ctx.save();
    ctx.strokeStyle='#6B7280';ctx.lineWidth=1.5;ctx.setLineDash([5,5]);
    ctx.beginPath();ctx.moveTo(x,chartArea.top);ctx.lineTo(x,chartArea.bottom);ctx.stroke();
    ctx.setLineDash([]);ctx.fillStyle='#9CA3AF';ctx.font='10px sans-serif';ctx.textAlign='left';
    ctx.fillText('Hoje',x+4,chartArea.top+13);
    ctx.restore();
  }
});

// ── Helpers ────────────────────────────────────────────────────
function sc(emp){ return SECTOR_COLORS[COMPANY_SECTORS[emp]]||'#9CA3AF'; }
function cc(emp){ return COMPANY_COLORS[emp]||sc(emp); }
function fd(iso){ if(!iso||iso.length<10)return ''; const p=iso.substring(0,10).split('-'); return p[2]+'/'+p[1]+'/'+p[0]; }
function sa(s){
  if(s==='positivo')return '<span style="color:#34D399;font-weight:bold">&#9650;</span>';
  if(s==='negativo')return '<span style="color:#EF4444;font-weight:bold">&#9660;</span>';
  return '<span style="color:#6B7280;font-weight:bold">&#8212;</span>';
}
function sb(v){
  const m={1:['#064E3B','#34D399','SEV 1'],2:['#78350F','#FCD34D','SEV 2'],3:['#7F1D1D','#FCA5A5','SEV 3']};
  const[bg,cl,lb]=m[v]||m[1];
  return '<span class="badge" style="background:'+bg+';color:'+cl+'">'+lb+'</span>';
}
function cs2(emp){ return '<span style="color:'+sc(emp)+';font-weight:600">'+eh(emp)+'</span>'; }
function eh(s){ if(s==null)return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function byDays(d,src){ const c=new Date(Date.now()-d*864e5); return (src||DATA_NEWS).filter(n=>n.data&&new Date(n.data)>=c); }
function score(emp,src){ const it=(src||DATA_NEWS).filter(n=>n.empresa===emp); return it.filter(n=>n.sentimento==='negativo').length*2+it.filter(n=>n.severidade===3).length*3; }
function months6(){ const r=[],now=new Date(); for(let i=5;i>=0;i--){ const d=new Date(now.getFullYear(),now.getMonth()-i,1); const key=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0'); const raw=d.toLocaleDateString('pt-BR',{month:'short'}).replace('.',''); r.push({key,lbl:raw.charAt(0).toUpperCase()+raw.slice(1)}); } return r; }
function getWeekKey(ds){ const d=new Date(ds+'T12:00:00Z'),day=d.getUTCDay()||7; d.setUTCDate(d.getUTCDate()+4-day); const jan1=new Date(Date.UTC(d.getUTCFullYear(),0,1)); return d.getUTCFullYear()+'-W'+String(Math.ceil(((d-jan1)/86400000+1)/7)).padStart(2,'0'); }

// ── Modal ──────────────────────────────────────────────────────
function showModal(items,title){
  document.getElementById('modal-title').textContent=title||'';
  document.getElementById('modal-body').innerHTML=(items||[]).map(n=>`
    <div style="border-bottom:1px solid #1F2937;padding:12px 0">
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:5px">
        ${sa(n.sentimento)} ${sb(n.severidade)} ${cs2(n.empresa)}<span style="color:#6B7280;font-size:11px;margin-left:auto">${fd(n.data)}</span>
      </div>
      <div style="margin-bottom:5px"><a href="${eh(n.url)}" target="_blank" rel="noopener" style="color:#F9FAFB;text-decoration:none;font-size:13px">${eh(n.titulo)}</a></div>
      ${n.resumo?'<div style="color:#9CA3AF;font-size:12px;line-height:1.5">'+eh(n.resumo)+'</div>':''}
      ${(n.tags||[]).filter(Boolean).length?'<div style="margin-top:5px">'+n.tags.filter(Boolean).map(t=>'<span class="pill">'+t.replace(/_/g,' ')+'</span>').join('')+'</div>':''}
    </div>`).join('');
  document.getElementById('modal').style.display='flex';
}
function hideModal(){ document.getElementById('modal').style.display='none'; }

// ── Tabs ───────────────────────────────────────────────────────
const CH={};const TI=[false,false,false];
function showTab(n){
  document.querySelectorAll('.tc').forEach(t=>t.style.display='none');
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab'+n).style.display='block';
  document.querySelectorAll('.tab-btn')[n-1].classList.add('active');
  if(n===1&&!TI[0]){initT1();TI[0]=true;}
  if(n===2&&!TI[1]){initT2();TI[1]=true;}
  if(n===3&&!TI[2]){initT3();TI[2]=true;}
}

// ══ Tab 1 ══════════════════════════════════════════════════════
function initT1(){ renderNews();renderAlerts();renderCards();renderSectors();renderAttn();renderThemes();setTimeout(()=>renderThemeDist(),80); }

function renderNews(){
  const items=DATA_NEWS.filter(n=>n.data).sort((a,b)=>new Date(b.data)-new Date(a.data)).slice(0,10);
  document.getElementById('latest-news').innerHTML=items.map(n=>`
    <div class="ni">
      <div class="ni-h">${sa(n.sentimento)} ${sb(n.severidade)} ${cs2(n.empresa)}<span class="ni-d">${fd(n.data)}</span></div>
      <div class="ni-t"><a href="${eh(n.url)}" target="_blank" rel="noopener">${eh(n.titulo)}</a></div>
      ${n.resumo?'<div class="ni-s">'+eh(n.resumo.substring(0,160))+'</div>':''}
    </div>`).join('');
}

function renderAlerts(){
  const al=DATA_NEWS.filter(n=>n.severidade===3).sort((a,b)=>new Date(b.data)-new Date(a.data));
  const el=document.getElementById('critical-alerts');
  if(!al.length){el.innerHTML='<div style="color:#6B7280;padding:12px;font-size:13px">Nenhum alerta crítico no período</div>';return;}
  el.innerHTML=al.map(n=>`<div class="ac"><div class="ni-h">${sa(n.sentimento)} ${cs2(n.empresa)}<span class="ni-d">${fd(n.data)}</span></div><div class="ni-t"><a href="${eh(n.url)}" target="_blank" rel="noopener">${eh(n.titulo)}</a></div>${n.resumo?'<div class="ni-s" style="color:#9CA3AF">'+eh(n.resumo.substring(0,160))+'</div>':''}</div>`).join('');
}

function renderCards(){
  const wins=[{id:'m6',lbl:'Últimos 6 meses',d:180},{id:'m3',lbl:'Últimos 3 meses',d:90},{id:'m1',lbl:'Último mês',d:30},{id:'m7',lbl:'Últimos 7 dias',d:7}];
  wins.forEach(w=>{
    const now=Date.now(),cur=byDays(w.d),prv=DATA_NEWS.filter(n=>{if(!n.data)return false;const t=new Date(n.data).getTime();return t>=now-w.d*2*864e5&&t<now-w.d*864e5;});
    const tot=cur.length,pos=cur.filter(n=>n.sentimento==='positivo').length,neu=cur.filter(n=>n.sentimento==='neutro').length,neg=cur.filter(n=>n.sentimento==='negativo').length;
    const pPos=tot?(pos/tot*100).toFixed(0):0,pNeu=tot?(neu/tot*100).toFixed(0):0,pNeg=tot?(neg/tot*100).toFixed(0):0;
    const prevNeg=prv.length?(prv.filter(n=>n.sentimento==='negativo').length/prv.length*100):parseFloat(pNeg);
    const delta=parseFloat(pNeg)-prevNeg;
    const dc=delta>1?'#EF4444':delta<-1?'#34D399':'#6B7280';
    const ds=Math.abs(delta)<0.5?'Estável vs período anterior':(delta>0?'▲ +':'▼ ')+Math.abs(delta).toFixed(1)+'pp de negativos';
    document.getElementById(w.id).innerHTML=
      '<div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.05em;font-weight:700;margin-bottom:6px">'+w.lbl+'</div>'+
      '<div style="font-size:11px;color:#6B7280;margin-bottom:8px">'+tot+' eventos no período</div>'+
      '<div style="height:10px;border-radius:5px;overflow:hidden;display:flex;gap:1px;margin-bottom:7px">'+
      '<div style="flex:'+pPos+';background:#34D399;min-width:'+(pPos>0?3:0)+'px"></div>'+
      '<div style="flex:'+pNeu+';background:#374151;min-width:'+(pNeu>0?3:0)+'px"></div>'+
      '<div style="flex:'+pNeg+';background:#EF4444;min-width:'+(pNeg>0?3:0)+'px"></div></div>'+
      '<div style="display:flex;justify-content:space-between;font-size:13px;font-weight:700">'+
      '<span style="color:#34D399">▲ '+pPos+'%</span><span style="color:#6B7280">— '+pNeu+'%</span><span style="color:#EF4444">▼ '+pNeg+'%</span></div>'+
      '<div style="display:flex;justify-content:space-between;font-size:10px;color:#4B5563;margin-top:2px"><span>positivo</span><span>neutro</span><span>negativo</span></div>'+
      '<div style="color:'+dc+';margin-top:8px;font-size:11px">'+ds+'</div>';
  });
}

function renderSectors(){
  const secs=['Óleo & Gás','Infraestrutura','Serviços Industriais','Financeiro/Outros'];
  const now=Date.now();
  const rows=secs.map(sec=>{
    const it=DATA_NEWS.filter(n=>COMPANY_SECTORS[n.empresa]===sec);
    const tot=it.length,pct=tot?it.filter(n=>n.sentimento==='negativo').length/tot*100:0,s3=it.filter(n=>n.severidade===3).length;
    const cm=it.filter(n=>n.data&&new Date(n.data).getTime()>=now-30*864e5);
    const pm=it.filter(n=>{if(!n.data)return false;const t=new Date(n.data).getTime();return t>=now-60*864e5&&t<now-30*864e5;});
    const pm2=cm.length?cm.filter(n=>n.sentimento==='negativo').length/cm.length*100:0;
    const pp2=pm.length?pm.filter(n=>n.sentimento==='negativo').length/pm.length*100:pm2;
    const d=pm2-pp2;
    const tr=Math.abs(d)<0.5?'<span style="color:#6B7280">—</span>':d<0?'<span style="color:#34D399">&#9660; '+Math.abs(d).toFixed(1)+'pp</span>':'<span style="color:#EF4444">&#9650; '+d.toFixed(1)+'pp</span>';
    const cc=SECTOR_COLORS[sec]||'#9CA3AF',cp=pct<25?'#34D399':pct<40?'#FCD34D':'#EF4444';
    return '<tr><td style="color:'+cc+';font-weight:600">'+eh(sec)+'</td><td>'+tot+'</td><td style="color:'+cp+'">'+pct.toFixed(1)+'%</td><td>'+s3+'</td><td>'+tr+'</td></tr>';
  });
  const tp=DATA_NEWS.length?DATA_NEWS.filter(n=>n.sentimento==='negativo').length/DATA_NEWS.length*100:0;
  const ts3=DATA_NEWS.filter(n=>n.severidade===3).length,tpc=tp<25?'#34D399':tp<40?'#FCD34D':'#EF4444';
  document.getElementById('sector-tbody').innerHTML=rows.join('')+'<tr style="border-top:2px solid #374151"><td style="font-weight:700">Total</td><td style="font-weight:700">'+DATA_NEWS.length+'</td><td style="font-weight:700;color:'+tpc+'">'+tp.toFixed(1)+'%</td><td style="font-weight:700">'+ts3+'</td><td></td></tr>';
}

function renderAttn(){
  const emps=[...new Set(DATA_NEWS.map(n=>n.empresa))];
  const scored=emps.map(emp=>{
    const it=DATA_NEWS.filter(n=>n.empresa===emp);
    const pos=it.filter(n=>n.sentimento==='positivo').length,neu=it.filter(n=>n.sentimento==='neutro').length,neg=it.filter(n=>n.sentimento==='negativo').length,s3=it.filter(n=>n.severidade===3).length;
    return{emp,pos,neu,neg,sc2:neg*2+s3*3,tot:it.length||1};
  }).sort((a,b)=>b.sc2-a.sc2);
  document.getElementById('attn-rank').innerHTML=scored.map(x=>{
    const c=sc(x.emp),pw=(x.pos/x.tot*100).toFixed(1),nw=(x.neu/x.tot*100).toFixed(1),ngw=(x.neg/x.tot*100).toFixed(1);
    return '<div style="margin-bottom:9px"><div style="display:flex;justify-content:space-between;margin-bottom:3px"><span style="color:'+c+';font-weight:600;font-size:12px">'+eh(x.emp)+'</span><span style="color:#6B7280;font-size:11px">Score '+x.sc2+' ('+x.tot+' ev.)</span></div><div class="bt"><div class="bs" style="width:'+pw+'%;background:#34D399"></div><div class="bs" style="width:'+nw+'%;background:#374151"></div><div class="bs" style="width:'+ngw+'%;background:#EF4444"></div></div></div>';
  }).join('');
}

function renderThemes(){
  const tc={};
  DATA_NEWS.forEach(n=>(n.tags||[]).forEach(tag=>{if(!tag)return;if(!tc[tag])tc[tag]={tot:0,neg:0};tc[tag].tot++;if(n.sentimento==='negativo')tc[tag].neg++;}));
  const sorted=Object.entries(tc).sort((a,b)=>b[1].tot-a[1].tot);
  const mx=sorted[0]?.[1].tot||1;
  document.getElementById('theme-rank').innerHTML=sorted.map(([tag,{tot,neg}])=>{
    const p=neg/tot*100,bc=p>50?'#EF4444':p>25?'#F59E0B':'#3B82F6';
    return '<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;margin-bottom:3px"><span style="color:#D1D5DB;font-size:12px">'+tag.replace(/_/g,' ')+'</span><span style="color:#6B7280;font-size:11px">'+tot+'&nbsp;'+p.toFixed(0)+'% neg</span></div><div class="bt" style="height:12px"><div class="bs" style="width:'+(tot/mx*100).toFixed(1)+'%;background:'+bc+'"></div></div></div>';
  }).join('');
}

function renderThemeDist(){
  const ctx=document.getElementById('ct1');if(!ctx)return;if(CH.t1)CH.t1.destroy();
  const td={};DATA_NEWS.forEach(n=>(n.tags||[]).forEach(tag=>{if(!tag)return;if(!td[tag])td[tag]={p:0,n:0,ng:0};if(n.sentimento==='positivo')td[tag].p++;else if(n.sentimento==='neutro')td[tag].n++;else td[tag].ng++;}));
  const sorted=Object.entries(td).sort((a,b)=>(b[1].p+b[1].n+b[1].ng)-(a[1].p+a[1].n+a[1].ng));
  CH.t1=new Chart(ctx,{type:'bar',
    data:{labels:sorted.map(([t])=>t.replace(/_/g,' ')),datasets:[
      {label:'Positivo',data:sorted.map(([,v])=>v.p),backgroundColor:'#34D399'},
      {label:'Neutro',  data:sorted.map(([,v])=>v.n),backgroundColor:'#374151'},
      {label:'Negativo',data:sorted.map(([,v])=>v.ng),backgroundColor:'#EF4444'}
    ]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:8,font:{size:10}}}},
      scales:{x:{stacked:true,ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'}},y:{stacked:true,ticks:{color:'#9CA3AF',font:{size:10}},grid:{color:'#1F2937'}}}
    }
  });
}

// ══ Tab 2 ══════════════════════════════════════════════════════
const T2={empresa:'',setor:''};

function initT2(){
  // Linha 1: Todas + setores
  const secs=['Óleo & Gás','Infraestrutura','Serviços Industriais','Financeiro/Outros'];
  let r1='<button class="selb" id="btn-all" onclick="T2sel(\'all\')">Todas as empresas</button><div class="t2-div"></div>';
  r1+=secs.map(s=>`<button class="selb" data-sec="${s.replace(/&/g,'&amp;')}" onclick="T2sel('sec','${s.replace(/'/g,"\\'")}')" style="border-color:${SECTOR_COLORS[s]}40;color:${SECTOR_COLORS[s]}">${s.replace(/&/g,'&amp;')}</button>`).join('');
  document.getElementById('t2-row1').innerHTML=r1;
  // Linha 2: empresas agrupadas por setor
  let r2='';
  secs.forEach((s,si)=>{
    const emps=Object.keys(COMPANY_SECTORS).filter(e=>COMPANY_SECTORS[e]===s);
    r2+=emps.map(e=>`<button class="selb" data-emp="${e.replace(/'/g,"\\'")}" onclick="T2sel('emp','${e.replace(/'/g,"\\'")}')" style="border-color:${SECTOR_COLORS[s]}50;color:${SECTOR_COLORS[s]}">${e}</button>`).join('');
    if(si<secs.length-1) r2+='<span style="color:#374151;padding:0 4px;align-self:center">|</span>';
  });
  document.getElementById('t2-row2').innerHTML=r2;
  T2sel('all');
}

function T2sel(type,val){
  T2.empresa='';T2.setor='';
  if(type==='sec')T2.setor=val;
  if(type==='emp')T2.empresa=val;
  // Atualizar estado visual dos botões
  document.querySelectorAll('#t2-row1 .selb,#t2-row2 .selb').forEach(b=>{
    b.style.fontWeight='';b.style.background='#1F2937';
    const sec=b.dataset.sec,emp=b.dataset.emp,isAll=b.id==='btn-all';
    let active=false;
    if(type==='all'&&isAll)active=true;
    if(type==='sec'&&sec===val)active=true;
    if(type==='emp'&&emp===val)active=true;
    if(type==='sec'&&emp&&COMPANY_SECTORS[emp]===val)active=true; // highlight companies in selected sector
    if(active){
      const c=type==='all'?'#F9FAFB':type==='sec'?SECTOR_COLORS[val]:sc(val);
      b.style.background=c+'22';b.style.borderColor=c;b.style.color=c;b.style.fontWeight='700';
    }
  });
  applyT2();
}

function getT2Data(){
  let news=DATA_NEWS,stocks=DATA_STOCKS;
  if(T2.empresa){news=news.filter(n=>n.empresa===T2.empresa);stocks=stocks.filter(s=>s.empresa===T2.empresa);}
  else if(T2.setor){news=news.filter(n=>COMPANY_SECTORS[n.empresa]===T2.setor);stocks=stocks.filter(s=>COMPANY_SECTORS[s.empresa]===T2.setor);}
  return{news,stocks};
}

function applyT2(){
  const{news,stocks}=getT2Data();
  updateT2Bg(news);updateT2Badge(news);
  renderHeatmap(news);
  ['a','b','c'].forEach(k=>{if(CH[k]){CH[k].destroy();CH[k]=null;}});
  const useBg=!!(T2.empresa||T2.setor);
  setTimeout(()=>{renderPriceEvents(news,stocks,useBg);renderSentReturn(news,stocks);renderForecast(news,stocks);},60);
}

function updateT2Bg(news){
  const tot=news.length||1,pos=news.filter(n=>n.sentimento==='positivo').length,neg=news.filter(n=>n.sentimento==='negativo').length;
  const s=(pos-neg)/tot;
  const tab=document.getElementById('tab2');
  tab.style.background=s>0.15?'linear-gradient(180deg,#041a0c 0%,#0A0E1A 50%)':s<-0.15?'linear-gradient(180deg,#1a0404 0%,#0A0E1A 50%)':'';
}

function updateT2Badge(news){
  const tot=news.length,pos=news.filter(n=>n.sentimento==='positivo').length,neg=news.filter(n=>n.sentimento==='negativo').length,neu=news.filter(n=>n.sentimento==='neutro').length;
  const s=tot?(pos-neg)/tot:0;
  const label=T2.empresa||T2.setor||'Portfólio completo';
  const icon=s>0.1?'▲':s<-0.1?'▼':'—',color=s>0.1?'#34D399':s<-0.1?'#EF4444':'#6B7280';
  const pP=tot?(pos/tot*100).toFixed(0):0,pN=tot?(neu/tot*100).toFixed(0):0,pNg=tot?(neg/tot*100).toFixed(0):0;
  document.getElementById('t2-badge').innerHTML='<span style="color:'+color+';font-weight:700">'+icon+' '+eh(label)+'</span> <span style="color:#4B5563;font-size:12px">'+tot+' eventos — <span style="color:#34D399">'+pP+'% pos</span> / <span style="color:#6B7280">'+pN+'% neu</span> / <span style="color:#EF4444">'+pNg+'% neg</span></span>';
}

function renderHeatmap(news){
  const ms=months6();
  const emps=T2.empresa?[T2.empresa]:T2.setor?Object.keys(COMPANY_SECTORS).filter(e=>COMPANY_SECTORS[e]===T2.setor):Object.keys(COMPANY_SECTORS);
  let h='<table class="hm-tbl"><thead><tr><th>Empresa</th>';
  ms.forEach(m=>h+='<th>'+m.lbl+'</th>');h+='</tr></thead><tbody>';
  emps.forEach(emp=>{
    const c=sc(emp),its=news.filter(n=>n.empresa===emp);
    h+='<tr><td style="color:'+c+'">'+eh(emp)+'</td>';
    ms.forEach(m=>{
      const neg=its.filter(n=>n.data&&n.data.startsWith(m.key)&&n.sentimento==='negativo');
      const s3=its.filter(n=>n.data&&n.data.startsWith(m.key)&&n.severidade===3);
      const cnt=neg.length,bg=cnt===0?'#111827':cnt<=2?'#1F2937':cnt<=5?'#7F1D1D':cnt<=9?'#991B1B':'#EF4444',tc2=cnt===0?'#374151':'#F9FAFB';
      h+='<td style="background:'+bg+';color:'+tc2+'" title="'+eh(emp)+' — '+m.lbl+': '+cnt+' neg, '+s3.length+' sev.3">'+(cnt>0?cnt:'')+'</td>';
    });h+='</tr>';
  });h+='</tbody></table>';
  document.getElementById('heatmap').innerHTML=h;
}

// Computa segmentos de fundo por sentimento (janela 7 dias)
function buildSentBgSegs(news,allDates){
  const sm={positivo:1,neutro:0,negativo:-1};
  const half=3.5*86400000;
  const segs=[];let prevCat=null,segStart=0;
  allDates.forEach((date,i)=>{
    const t=new Date(date+'T12:00:00Z').getTime();
    const wn=news.filter(n=>{if(!n.data||n.data.length<10)return false;return Math.abs(new Date(n.data.substring(0,10)+'T12:00:00Z').getTime()-t)<=half;});
    const sc2=wn.length?wn.reduce((s,n)=>s+(sm[n.sentimento]||0),0)/wn.length:0;
    const cat=sc2>0.12?'pos':sc2<-0.12?'neg':'neu';
    if(cat!==prevCat){if(prevCat!==null)segs.push({x1:segStart-0.5,x2:i-0.5,cat:prevCat});prevCat=cat;segStart=i;}
    if(i===allDates.length-1)segs.push({x1:segStart-0.5,x2:i+0.5,cat:prevCat});
  });
  return segs.map(s=>({...s,color:s.cat==='pos'?'rgba(52,211,153,0.22)':s.cat==='neg'?'rgba(239,68,68,0.26)':'transparent'})).filter(s=>s.color!=='transparent');
}

// Gráfico A: preço + marcadores de eventos clicáveis
function renderPriceEvents(news,stocks,useBg){
  const ctx=document.getElementById('ca');if(!ctx||!stocks.length)return;
  const allDates=[...new Set(stocks.map(s=>s.date))].sort();
  const dateIdx=Object.fromEntries(allDates.map((d,i)=>[d,i]));
  const visibleEmps=new Set(stocks.map(s=>s.empresa));
  const companies=[...visibleEmps];
  const priceMap={};
  companies.forEach(emp=>{
    const rows=stocks.filter(s=>s.empresa===emp).sort((a,b)=>a.date.localeCompare(b.date));
    const base=rows[0]?.close||1;priceMap[emp]={};
    rows.forEach(r=>priceMap[emp][r.date]=parseFloat((r.close/base*100).toFixed(2)));
  });
  const datasets=[];
  companies.forEach(emp=>{
    datasets.push({type:'line',label:emp,data:allDates.map((_,i)=>({x:i,y:priceMap[emp][allDates[i]]!==undefined?priceMap[emp][allDates[i]]:null})),borderColor:cc(emp),borderWidth:companies.length===1?2:1.5,pointRadius:0,spanGaps:false,tension:0.1,order:3});
  });
  // Eventos: apenas de empresas visíveis no gráfico
  const evtMap={};
  news.filter(n=>n.data&&n.data.length>=10&&visibleEmps.has(n.empresa)).forEach(n=>{
    const d=n.data.substring(0,10);
    if(dateIdx[d]===undefined||!priceMap[n.empresa]||priceMap[n.empresa][d]===undefined)return;
    const k=n.empresa+'|'+d;if(!evtMap[k])evtMap[k]={empresa:n.empresa,date:d,news:[]};
    evtMap[k].news.push(n);
  });
  const evPos=[],evNeg=[],evNeu=[],evSev3=[];
  Object.values(evtMap).forEach(ev=>{
    const idx=dateIdx[ev.date],y=priceMap[ev.empresa][ev.date];
    const pt={x:idx,y,_news:ev.news,_empresa:ev.empresa,_date:ev.date};
    const hasSev3=ev.news.some(n=>n.severidade===3);
    const ms=ev.news.some(n=>n.sentimento==='negativo')?'negativo':ev.news.some(n=>n.sentimento==='positivo')?'positivo':'neutro';
    if(hasSev3)evSev3.push(pt);else if(ms==='positivo')evPos.push(pt);else if(ms==='negativo')evNeg.push(pt);else evNeu.push(pt);
  });
  if(evPos.length)  datasets.push({type:'scatter',label:'Positivo', data:evPos, backgroundColor:'#34D399',pointRadius:5,pointHoverRadius:7,order:1});
  if(evNeg.length)  datasets.push({type:'scatter',label:'Negativo', data:evNeg, backgroundColor:'#EF4444',pointRadius:5,pointHoverRadius:7,order:1});
  if(evNeu.length)  datasets.push({type:'scatter',label:'Neutro',   data:evNeu, backgroundColor:'#6B7280',pointRadius:4,pointHoverRadius:6,order:2});
  if(evSev3.length) datasets.push({type:'scatter',label:'Sev.3',   data:evSev3,backgroundColor:'#F59E0B',pointRadius:9,pointHoverRadius:12,order:0});
  const dlbl=allDates.map(d=>{const p=d.split('-');return p[2]+'/'+p[1];});
  const bgSegs=useBg?buildSentBgSegs(news,allDates):[];
  CH.a=new Chart(ctx,{type:'scatter',data:{labels:dlbl,datasets},
    options:{responsive:true,maintainAspectRatio:false,
      onClick:(e,els)=>{if(!els.length)return;const pt=CH.a.data.datasets[els[0].datasetIndex].data[els[0].index];if(pt&&pt._news)showModal(pt._news,eh(pt._empresa)+' — '+fd(pt._date));},
      plugins:{
        sentBg:{segments:bgSegs},
        legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:8}},
        tooltip:{callbacks:{label:c2=>{const pt=c2.raw;if(pt&&pt._news)return eh(pt._empresa)+' '+fd(pt._date)+': '+pt._news.length+' evento(s) — clique';return (c2.dataset.label||'')+': '+(c2.raw&&c2.raw.y!=null?c2.raw.y.toFixed(1):'');}}}
      },
      scales:{
        x:{type:'linear',min:0,max:allDates.length-1,ticks:{color:'#9CA3AF',maxTicksLimit:12,callback:v=>{const i=Math.round(v);return dlbl[i]||'';}},grid:{color:'#1F2937'}},
        y:{ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'},title:{display:true,text:'Base 100 (1º dia)',color:'#6B7280',font:{size:11}}}
      }
    }
  });
}

// Gráfico B: sentimento semanal vs retorno semanal
function renderSentReturn(news,stocks){
  const ctx=document.getElementById('cb');if(!ctx||!stocks.length||!news.length)return;
  const weekNews={};
  news.filter(n=>n.data&&n.data.length>=10).forEach(n=>{const wk=getWeekKey(n.data.substring(0,10));if(!weekNews[wk])weekNews[wk]=[];weekNews[wk].push(n);});
  const companies=[...new Set(stocks.map(s=>s.empresa))];
  const priceByComp={};
  companies.forEach(emp=>{
    const rows=stocks.filter(s=>s.empresa===emp).sort((a,b)=>a.date.localeCompare(b.date));
    const base=rows[0]?.close||1;priceByComp[emp]={};
    rows.forEach(r=>priceByComp[emp][r.date]=r.close/base*100);
  });
  const allDates=[...new Set(stocks.map(s=>s.date))].sort();
  const weekDates={};allDates.forEach(d=>{const wk=getWeekKey(d);if(!weekDates[wk])weekDates[wk]=[];weekDates[wk].push(d);});
  const points=[];
  Object.keys(weekNews).sort().forEach(wk=>{
    const wN=weekNews[wk],wD=weekDates[wk];if(!wD||wD.length<2)return;
    const sentMap={positivo:1,neutro:0,negativo:-1};
    const sentScore=wN.reduce((s,n)=>s+(sentMap[n.sentimento]||0),0)/wN.length;
    const returns=[];
    companies.forEach(emp=>{
      const m=priceByComp[emp],ds=wD.filter(d=>m&&m[d]!=null).sort();
      if(ds.length<2)return;
      returns.push((m[ds[ds.length-1]]-m[ds[0]])/m[ds[0]]*100);
    });
    if(!returns.length)return;
    const avgRet=returns.reduce((a,b)=>a+b,0)/returns.length;
    points.push({x:parseFloat(sentScore.toFixed(3)),y:parseFloat(avgRet.toFixed(3)),_news:wN,_week:wk});
  });
  if(!points.length)return;
  const N=points.length,sx=points.reduce((a,p)=>a+p.x,0)/N,sy=points.reduce((a,p)=>a+p.y,0)/N;
  const sxy=points.reduce((a,p)=>a+(p.x-sx)*(p.y-sy),0),sxx=points.reduce((a,p)=>a+(p.x-sx)**2,0);
  const slope=sxx?sxy/sxx:0,intercept=sy-slope*sx;
  const ssTot=points.reduce((a,p)=>a+(p.y-sy)**2,0),ssRes=points.reduce((a,p)=>{const yH=slope*p.x+intercept;return a+(p.y-yH)**2;},0);
  const r2=ssTot>0?Math.max(0,1-ssRes/ssTot):0;
  const xMin=Math.min(...points.map(p=>p.x)),xMax=Math.max(...points.map(p=>p.x));
  const ptColors=points.map(p=>p._news.some(n=>n.severidade===3)?'#F59E0B':p.x>0.15?'#34D399':p.x<-0.15?'#EF4444':'#6B7280');
  CH.b=new Chart(ctx,{type:'scatter',
    data:{datasets:[
      {label:'Semana',data:points,backgroundColor:ptColors,pointRadius:6,pointHoverRadius:9},
      {label:'Tendência (R²='+r2.toFixed(2)+')',data:[{x:xMin,y:slope*xMin+intercept},{x:xMax,y:slope*xMax+intercept}],type:'line',borderColor:'#3B82F6',borderWidth:2,borderDash:[5,5],pointRadius:0,fill:false}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      onClick:(e,els)=>{if(!els.length)return;const pt=CH.b.data.datasets[els[0].datasetIndex].data[els[0].index];if(pt&&pt._news)showModal(pt._news,'Semana '+pt._week+' — '+pt._news.length+' eventos');},
      plugins:{legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:8}},tooltip:{callbacks:{label:c2=>{const pt=c2.raw;if(!pt||!pt._news)return c2.dataset.label;return 'Sem. '+pt._week+' | Sent: '+pt.x.toFixed(2)+' | Ret: '+pt.y.toFixed(2)+'% | '+pt._news.length+' ev.';}}}} ,
      scales:{
        x:{title:{display:true,text:'Score de sentimento (−1 negativo → +1 positivo)',color:'#6B7280',font:{size:10}},ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'}},
        y:{title:{display:true,text:'Retorno semanal médio (%)',color:'#6B7280',font:{size:10}},ticks:{color:'#9CA3AF',callback:v=>v.toFixed(1)+'%'},grid:{color:'#1F2937'}}
      }
    }
  });
}

// Gráfico C: Projeção de preço baseada em sentimento + correlação histórica
function renderForecast(news,stocks){
  const ctx=document.getElementById('cc');if(!ctx)return;
  const nodata=document.getElementById('cc-nodata'),wrap=document.getElementById('cc-wrap');
  const companies=[...new Set(stocks.map(s=>s.empresa))];
  if(!companies.length){nodata.style.display='block';wrap.style.display='none';return;}
  const filtered=T2.empresa||T2.setor;
  const shown=filtered?companies:companies.map(e=>({e,sc3:score(e,news)})).sort((a,b)=>b.sc3-a.sc3).slice(0,5).map(x=>x.e);
  nodata.style.display='none';wrap.style.display='block';

  const allHistDates=[...new Set(stocks.map(s=>s.date))].sort();
  const today=allHistDates[allHistDates.length-1];
  const lastWeekDate=allHistDates[Math.max(0,allHistDates.length-6)]; // ~5 pregoes atras
  const nextWeekDate=(()=>{const d=new Date(today+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+7);return d.toISOString().substring(0,10);})();
  const todayLabel=(()=>{const p=today.split('-');return p[2]+'/'+p[1];})();
  const lastWeekLabel=(()=>{const p=lastWeekDate.split('-');return p[2]+'/'+p[1];})();
  const nextWeekLabel=(()=>{const p=nextWeekDate.split('-');return p[2]+'/'+p[1];})();
  // Eixo X: 3 posicoes fixas — 0=sem.passada, 1=hoje, 2=+1sem
  const xLabels=[lastWeekLabel+' (sem. passada)',todayLabel+' (hoje)',nextWeekLabel+' (+1 semana)'];

  const sentMapV={positivo:1,neutro:0,negativo:-1};
  const datasets=[];
  const subtitles=[];

  shown.forEach(emp=>{
    const empStocks=stocks.filter(s=>s.empresa===emp).sort((a,b)=>a.date.localeCompare(b.date));
    if(empStocks.length<5)return;
    // Calcular regressao com TODO o historico
    const allSD=[...new Set(empStocks.map(s=>s.date))].sort();
    const priceByDate={};empStocks.forEach(s=>priceByDate[s.date]=s.close);
    const weekDatesL={};allSD.forEach(d=>{const wk=getWeekKey(d);if(!weekDatesL[wk])weekDatesL[wk]=[];weekDatesL[wk].push(d);});
    const empNews=news.filter(n=>n.empresa===emp);
    const weekNewsL={};empNews.filter(n=>n.data&&n.data.length>=10).forEach(n=>{const wk=getWeekKey(n.data.substring(0,10));if(!weekNewsL[wk])weekNewsL[wk]=[];weekNewsL[wk].push(n);});
    const weeks=Object.keys(weekDatesL).sort();
    const regData=[];
    for(let i=0;i<weeks.length-1;i++){
      const wk=weeks[i],nwk=weeks[i+1];
      const wN=weekNewsL[wk]||[];
      const sentScore=wN.length?wN.reduce((s,n)=>s+(sentMapV[n.sentimento]||0),0)/wN.length:0;
      const wDs=weekDatesL[wk],nDs=weekDatesL[nwk];
      const sp=wDs[0]&&priceByDate[wDs[0]],ep=nDs&&nDs[nDs.length-1]&&priceByDate[nDs[nDs.length-1]];
      if(!sp||!ep)continue;
      regData.push({sentScore,ret:(ep-sp)/sp*100});
    }
    if(regData.length<4)return;
    const N=regData.length,mx=regData.reduce((a,d)=>a+d.sentScore,0)/N,my=regData.reduce((a,d)=>a+d.ret,0)/N;
    const sxy=regData.reduce((a,d)=>a+(d.sentScore-mx)*(d.ret-my),0),sxx=regData.reduce((a,d)=>a+(d.sentScore-mx)**2,0);
    const beta=sxx>0?sxy/sxx:0,alpha=my-beta*mx;
    const residuals=regData.map(d=>d.ret-(alpha+beta*d.sentScore));
    const rStd=Math.sqrt(residuals.reduce((a,r)=>a+r*r,0)/Math.max(residuals.length-1,1));
    const ssTot=regData.reduce((a,d)=>a+(d.ret-my)**2,0),ssRes=regData.reduce((a,d)=>{const yH=alpha+beta*d.sentScore;return a+(d.ret-yH)**2;},0);
    const r2=ssTot>0?Math.max(0,1-ssRes/ssTot):0;
    // Sentimento atual (ultimas 2 semanas)
    const last14Date=new Date(new Date(today+'T12:00:00Z').getTime()-14*86400000).toISOString().substring(0,10);
    const recentN=empNews.filter(n=>n.data&&n.data.substring(0,10)>=last14Date);
    const curSent=recentN.length?recentN.reduce((s,n)=>s+(sentMapV[n.sentimento]||0),0)/recentN.length:0;
    const expWeekRetPct=(alpha+beta*curSent); // em %
    // Precos reais para normalizar base 100 na semana passada
    const pLastWeek=priceByDate[lastWeekDate]||empStocks[Math.max(0,empStocks.length-6)].close;
    const pToday=priceByDate[today]||empStocks[empStocks.length-1].close;
    if(!pLastWeek||!pLastWeek)return;
    const yLastWeek=100;
    const yToday=parseFloat((pToday/pLastWeek*100).toFixed(2));
    const yForecast=parseFloat((yToday*(1+expWeekRetPct/100)).toFixed(2));
    const bandPct=rStd/100;
    const yUpper=parseFloat((yForecast*(1+bandPct)).toFixed(2));
    const yLower=parseFloat((yForecast*(1-bandPct)).toFixed(2));
    const empColor=sc(emp);
    // Linha semana passada → hoje (solida)
    datasets.push({type:'line',label:emp,
      data:[{x:0,y:yLastWeek},{x:1,y:yToday}],
      borderColor:empColor,borderWidth:2.5,pointRadius:5,pointHoverRadius:7,
      spanGaps:false,tension:0,order:2});
    // Linha hoje → projecao (tracejada)
    datasets.push({type:'line',label:'',
      data:[{x:1,y:yToday},{x:2,y:yForecast}],
      borderColor:empColor+'BB',borderWidth:2,borderDash:[6,4],pointRadius:0,
      spanGaps:false,tension:0,order:2});
    // Ponto de projecao (grande, borda branca)
    const projLabel=emp+': '+(expWeekRetPct>=0?'+':'')+expWeekRetPct.toFixed(1)+'% (R2='+r2.toFixed(2)+')';
    datasets.push({type:'scatter',label:projLabel,
      data:[{x:2,y:yForecast}],
      backgroundColor:empColor,borderColor:'#F9FAFB',borderWidth:2,
      pointRadius:11,pointHoverRadius:14,order:0,
      _proj:{upper:yUpper,lower:yLower,ret:expWeekRetPct,r2,curSent,emp,yToday}});
    // Barra de erro vertical +-1sigma
    datasets.push({type:'line',label:'',
      data:[{x:2,y:yUpper},{x:2,y:yLower}],
      borderColor:empColor+'AA',borderWidth:4,pointRadius:5,pointStyle:'line',
      spanGaps:false,tension:0,order:1});
    const sentIcon=curSent>0.1?'pos':curSent<-0.1?'neg':'neu';
    subtitles.push(emp+': sent. '+sentIcon+' ('+curSent.toFixed(2)+') -> '+(expWeekRetPct>=0?'+':'')+expWeekRetPct.toFixed(1)+'% +-'+rStd.toFixed(1)+'% 1-sigma | R2='+r2.toFixed(2));
  });

  if(!datasets.length){nodata.style.display='block';wrap.style.display='none';return;}
  CH.c=new Chart(ctx,{type:'scatter',
    data:{datasets},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{
        legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:6,font:{size:10},filter:item=>item.text!==''}},
        tooltip:{callbacks:{label:c2=>{
          const v=c2.raw,ds=c2.dataset;
          if(!v||v.y==null)return null;
          if(ds._proj){const p=ds._proj;return [ds.label,'  Hoje: '+p.yToday.toFixed(1),'  Projecao: '+v.y.toFixed(1),'  Superior (+1sigma): '+p.upper.toFixed(1),'  Inferior (-1sigma): '+p.lower.toFixed(1),'  R2 historico: '+p.r2.toFixed(2)];}
          return (ds.label?ds.label+': ':'')+v.y.toFixed(1);
        }}}
      },
      scales:{
        x:{type:'linear',min:-0.3,max:2.3,
          ticks:{color:'#9CA3AF',stepSize:1,callback:v=>{const i=Math.round(v);return xLabels[i]||'';}},
          grid:{color:'#1F2937'}},
        y:{ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'},
          title:{display:true,text:'Preco relativo (base 100 = semana passada)',color:'#6B7280',font:{size:10}}}
      }
    }
  });
  // Linha vertical "hoje"
  const chartInst=CH.c;
  const origDraw=chartInst.draw.bind(chartInst);
  chartInst.draw=function(){
    origDraw();
    const sc2=chartInst.scales.x,ca=chartInst.chartArea;
    if(!sc2||!ca)return;
    const xPx=sc2.getPixelForValue(1);
    const ct2=chartInst.ctx;
    ct2.save();ct2.strokeStyle='#4B5563';ct2.lineWidth=1;ct2.setLineDash([4,4]);
    ct2.beginPath();ct2.moveTo(xPx,ca.top);ct2.lineTo(xPx,ca.bottom);ct2.stroke();
    ct2.setLineDash([]);ct2.fillStyle='#6B7280';ct2.font='10px sans-serif';ct2.textAlign='left';
    ct2.fillText('Hoje',xPx+4,ca.top+13);ct2.restore();
  };
  // Painel de subtitulos
  let sub=ctx.parentElement.nextElementSibling;
  if(!sub||!sub.classList.contains('proj-sub')){sub=document.createElement('div');sub.className='proj-sub';ctx.parentElement.after(sub);}
  sub.innerHTML='<div style="font-size:10px;color:#6B7280;margin-top:8px;line-height:1.8;padding:8px 0;border-top:1px solid #1F2937">'+
    subtitles.map(s=>'<div>'+s+'</div>').join('')+
    '<div style="color:#374151;margin-top:4px;font-style:italic">Projecao indicativa baseada na correlacao historica sentimento/retorno. Nao constitui recomendacao de investimento.</div></div>';
}

// ══ Tab 3 ══════════════════════════════════════════════════════
const TAGS=['liquidez_refinanciamento','resultado_guidance','governanca','legal_regulatorio','operacional_incidente','m&a_estrategia','setor_macro','esg_reputacional'];
let f3={empresa:'',setor:'',sentimento:'',severidade:'',tema:''};
function initT3(){populateT3();applyF();}
function populateT3(){
  const emps=[...new Set(DATA_NEWS.map(n=>n.empresa))].sort();
  document.getElementById('fe').innerHTML='<option value="">Empresa</option>'+emps.map(e=>'<option value="'+eh(e)+'">'+eh(e)+'</option>').join('');
  const st=document.getElementById('ftm');
  if(st.options.length<=1)st.innerHTML='<option value="">Tema</option>'+TAGS.map(t=>'<option value="'+t+'">'+t.replace(/_/g,' ')+'</option>').join('');
}
function handleSec(val){f3.setor=val;f3.empresa='';const emps=val?[...new Set(DATA_NEWS.filter(n=>COMPANY_SECTORS[n.empresa]===val).map(n=>n.empresa))].sort():[...new Set(DATA_NEWS.map(n=>n.empresa))].sort();document.getElementById('fe').innerHTML='<option value="">Empresa</option>'+emps.map(e=>'<option value="'+eh(e)+'">'+eh(e)+'</option>').join('');applyF();}
function handleEmp(val){f3.empresa=val;if(val){const s=COMPANY_SECTORS[val]||'';f3.setor=s;document.getElementById('fse').value=s;}applyF();}
function applyF(){
  let r=DATA_NEWS;
  if(f3.empresa)r=r.filter(n=>n.empresa===f3.empresa);
  if(f3.setor)r=r.filter(n=>COMPANY_SECTORS[n.empresa]===f3.setor);
  if(f3.sentimento)r=r.filter(n=>n.sentimento===f3.sentimento);
  if(f3.severidade)r=r.filter(n=>n.severidade===parseInt(f3.severidade));
  if(f3.tema)r=r.filter(n=>(n.tags||[]).includes(f3.tema));
  renderTable(r);document.getElementById('nctr').textContent='Exibindo '+r.length+' de '+DATA_NEWS.length+' notícias';
}
function resetF(){f3={empresa:'',setor:'',sentimento:'',severidade:'',tema:''};['fe','fse','fst','fsv','ftm'].forEach(id=>document.getElementById(id).value='');populateT3();applyF();}
function renderTable(items){
  const sorted=[...items].sort((a,b)=>new Date(b.data)-new Date(a.data));
  document.getElementById('ntb').innerHTML=sorted.map(n=>{
    const tags=(n.tags||[]).filter(Boolean).map(t=>'<span class="pill">'+t.replace(/_/g,' ')+'</span>').join('');
    const tit=n.titulo.length>90?n.titulo.substring(0,90)+'…':n.titulo;
    const res=n.resumo.length>120?n.resumo.substring(0,120)+'…':n.resumo;
    return '<tr><td style="color:#6B7280;white-space:nowrap">'+fd(n.data)+'</td><td>'+cs2(n.empresa)+'</td><td>'+sb(n.severidade)+'</td><td>'+sa(n.sentimento)+'</td><td style="max-width:280px"><a href="'+eh(n.url)+'" target="_blank" rel="noopener">'+eh(tit)+'</a></td><td>'+tags+'</td><td style="color:#6B7280;font-size:12px;max-width:240px">'+eh(res)+'</td></tr>';
  }).join('');
}

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>showTab(1));
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
