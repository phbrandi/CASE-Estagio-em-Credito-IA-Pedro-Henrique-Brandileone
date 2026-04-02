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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Cores por setor
SECTOR_COLORS = {
    "Óleo & Gás": "#F59E0B",
    "Infraestrutura": "#3B82F6",
    "Serviços Industriais": "#8B5CF6",
    "Financeiro/Outros": "#10B981",
}

# Empresa → setor
COMPANY_SECTORS = {
    "OceanPact": "Óleo & Gás",
    "Brava Energia": "Óleo & Gás",
    "PetroRio": "Óleo & Gás",
    "PetroReconcavo": "Óleo & Gás",
    "NTS": "Óleo & Gás",
    "Aegea": "Infraestrutura",
    "Equatorial": "Infraestrutura",
    "Copasa": "Infraestrutura",
    "Cosan": "Infraestrutura",
    "Vamos": "Serviços Industriais",
    "Mills": "Serviços Industriais",
    "Armac": "Serviços Industriais",
    "BTG": "Financeiro/Outros",
    "Unipar": "Financeiro/Outros",
    "Multiplan": "Financeiro/Outros",
}


def main() -> None:
    # Lê os três CSVs
    df_comp = pd.read_csv(ROOT / "companies.csv", encoding="utf-8")
    df_news = pd.read_csv(ROOT / "output" / "news.csv", encoding="utf-8-sig")
    df_stocks = pd.read_csv(ROOT / "output" / "stock_data.csv", encoding="utf-8-sig")

    # Processa notícias
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
            "empresa": str(row["empresa"]),
            "ticker": str(row["ticker"]),
            "data": str(row["date_iso"]),
            "fonte": str(row["fonte"]),
            "tipo": str(row["tipo"]),
            "titulo": str(row["titulo"]),
            "url": str(row["url"]),
            "snippet": str(row.get("snippet_ou_trecho", ""))[:500],
            "sentimento": str(row["sentimento"]),
            "tags": tags,
            "severidade": int(row["severidade"]),
            "resumo": str(row.get("resumo_curto", ""))[:300],
            "setor": str(row["setor"]),
        })

    # Processa ações — normaliza para base 100 por empresa
    df_stocks["_dt"] = pd.to_datetime(df_stocks["date"])
    stocks_list = []
    for empresa, grp in df_stocks.groupby("empresa"):
        grp = grp.sort_values("_dt").copy()
        fc = grp["close"].iloc[0]
        grp["close_norm"] = (grp["close"] / fc * 100).round(2) if fc and fc > 0 else 100.0
        sector = COMPANY_SECTORS.get(str(empresa), "Financeiro/Outros")
        for _, row in grp.iterrows():
            stocks_list.append({
                "empresa": str(empresa),
                "ticker": str(row["ticker"]),
                "date": str(row["_dt"].strftime("%Y-%m-%d")),
                "close": round(float(row["close"]), 2),
                "close_norm": round(float(row["close_norm"]), 2),
                "setor": sector,
            })

    companies_list = df_comp.fillna("").to_dict(orient="records")

    # Serializa como JSON (ensure_ascii=False preserva acentos)
    json_news = json.dumps(news_list, ensure_ascii=False)
    json_stocks = json.dumps(stocks_list, ensure_ascii=False)
    json_companies = json.dumps(companies_list, ensure_ascii=False)
    json_sector_colors = json.dumps(SECTOR_COLORS, ensure_ascii=False)
    json_company_sectors = json.dumps(COMPANY_SECTORS, ensure_ascii=False)

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    valid_dt = df_news["_dt"].dropna()
    date_min = valid_dt.min().strftime("%d/%m/%Y") if not valid_dt.empty else ""
    date_max = valid_dt.max().strftime("%d/%m/%Y") if not valid_dt.empty else ""

    # Substitui placeholders no template HTML
    html = get_html_template()
    html = html.replace("INJECT_DATA_NEWS", json_news)
    html = html.replace("INJECT_DATA_STOCKS", json_stocks)
    html = html.replace("INJECT_DATA_COMPANIES", json_companies)
    html = html.replace("INJECT_SECTOR_COLORS", json_sector_colors)
    html = html.replace("INJECT_COMPANY_SECTORS", json_company_sectors)
    html = html.replace("INJECT_GENERATED_AT", generated_at)
    html = html.replace("INJECT_DATE_MIN", date_min)
    html = html.replace("INJECT_DATE_MAX", date_max)

    out = ROOT / "output" / "dashboard.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = out.stat().st_size / 1024
    logger.info("Dashboard gerado: output/dashboard.html (%.0f KB)", size_kb)
    print(f"Dashboard gerado: output/dashboard.html ({size_kb:.0f} KB)")


def get_html_template() -> str:
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitor de Crédito — Portfólio</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0A0E1A;color:#F9FAFB;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px}
.hdr{background:#0D1117;border-bottom:1px solid #1F2937;padding:13px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.hdr h1{font-size:17px;font-weight:700;color:#F9FAFB}
.hdr p{font-size:11px;color:#6B7280;margin-top:2px}
.hdr-r{text-align:right;font-size:12px;color:#6B7280;line-height:1.7}
.tabs{display:flex;background:#0D1117;border-bottom:1px solid #1F2937;padding:0 24px;position:sticky;top:55px;z-index:99}
.tab-btn{padding:10px 18px;cursor:pointer;color:#6B7280;border:none;border-bottom:2px solid transparent;background:none;font-size:13px;transition:all .15s}
.tab-btn:hover{color:#F9FAFB}
.tab-btn.active{color:#F9FAFB;border-bottom-color:#3B82F6;background:#111827}
.tc{display:none;padding:20px 24px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.card{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px}
.st{font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:11px}
.scroll340{max-height:340px;overflow-y:auto;padding-right:4px}
.ni{padding:9px 0;border-bottom:1px solid #1F2937}
.ni:last-child{border-bottom:none}
.ni-h{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px}
.ni-d{color:#6B7280;font-size:11px;margin-left:auto;white-space:nowrap}
.ni-t a{color:#F9FAFB;text-decoration:none;font-size:13px;line-height:1.4}
.ni-t a:hover{color:#3B82F6}
.ni-s{color:#6B7280;font-size:11px;margin-top:3px;line-height:1.4}
.badge{padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;white-space:nowrap}
.ac{background:#1A0A0A;border-left:3px solid #7F1D1D;padding:10px 12px;border-radius:0 4px 4px 0;margin-bottom:8px}
.ml{font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
.mv{font-size:28px;font-weight:800;line-height:1}
.ms{font-size:11px;color:#6B7280;margin-top:5px}
.md{font-size:11px;margin-top:3px}
.bt{flex:1;height:18px;background:#1F2937;border-radius:3px;overflow:hidden;display:flex}
.bs{height:100%}
.dtbl{width:100%;border-collapse:collapse}
.dtbl th{background:#0A0E1A;color:#6B7280;font-size:10px;text-transform:uppercase;padding:9px 12px;text-align:left;border-bottom:1px solid #1F2937;white-space:nowrap}
.dtbl td{padding:8px 12px;border-bottom:1px solid #1F2937;vertical-align:middle}
.dtbl tr:nth-child(even) td{background:#0F1623}
.dtbl tr:hover td{background:#1A2332}
.hm-tbl{width:100%;border-collapse:collapse}
.hm-tbl th{background:#0A0E1A;color:#9CA3AF;font-size:10px;text-transform:uppercase;padding:7px 10px;text-align:center;border:1px solid #0A0E1A}
.hm-tbl th:first-child{text-align:left;min-width:130px}
.hm-tbl td{padding:7px 10px;text-align:center;border:1px solid #0A0E1A;font-size:12px;min-width:68px;cursor:default;transition:opacity .1s}
.hm-tbl td:first-child{text-align:left;font-weight:600;padding-left:4px}
.cw{position:relative;height:300px}
.cwt{position:relative;height:360px}
.tg{display:flex;gap:4px;margin-bottom:10px}
.tgb{background:#1F2937;color:#6B7280;border:1px solid #374151;padding:5px 14px;border-radius:4px;cursor:pointer;font-size:12px}
.tgb.active{background:#3B82F6;color:#fff;border-color:#3B82F6}
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
.nt tr:nth-child(odd) td{background:#111827}
.nt tr:nth-child(even) td{background:#0F1623}
.nt tr:hover td{background:#1A2332}
.nt td a{color:#F9FAFB;text-decoration:none}
.nt td a:hover{color:#3B82F6}
.pill{display:inline-block;background:#1F2937;border:1px solid #374151;color:#6B7280;font-size:10px;padding:1px 5px;border-radius:3px;margin:1px;white-space:nowrap}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:#0A0E1A}
::-webkit-scrollbar-thumb{background:#374151;border-radius:3px}
</style>
</head>
<body>

<div class="hdr">
  <div>
    <h1>Monitor de Crédito</h1>
    <p>Portfólio de Acompanhamento — 15 empresas</p>
  </div>
  <div class="hdr-r">
    <div>Gerado em INJECT_GENERATED_AT</div>
    <div>Período: INJECT_DATE_MIN &rarr; INJECT_DATE_MAX</div>
  </div>
</div>

<nav class="tabs">
  <button class="tab-btn" onclick="showTab(1)">Visão Geral</button>
  <button class="tab-btn" onclick="showTab(2)">Análise Histórica</button>
  <button class="tab-btn" onclick="showTab(3)">Explorador de Notícias</button>
</nav>

<!-- ── Tab 1 ── -->
<div id="tab1" class="tc">
  <div class="g2">
    <div class="card">
      <div class="st">Últimas notícias</div>
      <div class="scroll340" id="latest-news"></div>
    </div>
    <div class="card">
      <div class="st">Alertas críticos — Severidade 3</div>
      <div class="scroll340" id="critical-alerts"></div>
    </div>
  </div>

  <div class="g4">
    <div class="card" id="m6"></div>
    <div class="card" id="m3"></div>
    <div class="card" id="m1"></div>
    <div class="card" id="m7"></div>
  </div>

  <div class="card" style="margin-bottom:16px">
    <div class="st">Eventos por setor</div>
    <table class="dtbl">
      <thead><tr><th>Setor</th><th>Total eventos</th><th>% Negativo</th><th>Alertas sev.3</th><th>Tendência (30d vs 30d ant.)</th></tr></thead>
      <tbody id="sector-tbody"></tbody>
    </table>
  </div>

  <div class="g2">
    <div class="card">
      <div class="st">Score de atenção por empresa</div>
      <div id="attn-rank"></div>
    </div>
    <div class="card">
      <div class="st">Temas em destaque</div>
      <div id="theme-rank"></div>
    </div>
  </div>
</div>

<!-- ── Tab 2 ── -->
<div id="tab2" class="tc">
  <div class="card" style="margin-bottom:16px">
    <div class="st">Heatmap — eventos negativos por empresa e mês</div>
    <div style="overflow-x:auto" id="heatmap"></div>
  </div>
  <div class="g2" style="margin-bottom:16px">
    <div class="card"><div class="cw"><canvas id="cs"></canvas></div></div>
    <div class="card"><div class="cwt"><canvas id="ct"></canvas></div></div>
  </div>
  <div class="card">
    <div class="st">Desempenho relativo das ações (base 100) com alertas sev.3</div>
    <div class="tg">
      <button id="btn-top5" class="tgb active" onclick="renderStocks(false)">Top 5 empresas</button>
      <button id="btn-all" class="tgb" onclick="renderStocks(true)">Todas as empresas (13)</button>
    </div>
    <div class="cwt"><canvas id="ck"></canvas></div>
    <div style="color:#6B7280;font-size:11px;margin-top:8px">* NTS: debênture de infraestrutura — sem cotação em bolsa. Aegea: ticker indisponível no Yahoo Finance.</div>
  </div>
</div>

<!-- ── Tab 3 ── -->
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
      <option value="">Sentimento</option>
      <option value="positivo">Positivo</option>
      <option value="neutro">Neutro</option>
      <option value="negativo">Negativo</option>
    </select>
    <select id="fsv" class="fs" onchange="f3.severidade=this.value;applyF()">
      <option value="">Severidade</option>
      <option value="1">1 — Baixo</option>
      <option value="2">2 — Médio</option>
      <option value="3">3 — Alto</option>
    </select>
    <select id="ftm" class="fs" onchange="f3.tema=this.value;applyF()"><option value="">Tema</option></select>
    <button class="breset" onclick="resetF()">Limpar filtros</button>
  </div>
  <div class="nc" id="nctr">Carregando...</div>
  <div class="card" style="padding:0;overflow:hidden">
    <div class="ntw">
      <table class="nt">
        <thead><tr>
          <th>Data</th><th>Empresa</th><th>Sev</th><th>Sent</th>
          <th style="min-width:220px">Título</th><th style="min-width:170px">Temas</th>
          <th style="min-width:210px">Resumo</th>
        </tr></thead>
        <tbody id="ntb"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const DATA_NEWS     = INJECT_DATA_NEWS;
const DATA_STOCKS   = INJECT_DATA_STOCKS;
const DATA_COMPANIES= INJECT_DATA_COMPANIES;
const SECTOR_COLORS = INJECT_SECTOR_COLORS;
const COMPANY_SECTORS = INJECT_COMPANY_SECTORS;

Chart.defaults.color       = '#9CA3AF';
Chart.defaults.borderColor = '#1F2937';

// ── Helpers ──────────────────────────────────────────────────
function sc(emp){ return SECTOR_COLORS[COMPANY_SECTORS[emp]] || '#9CA3AF'; }

function fd(iso){
  if(!iso||iso.length<10) return '';
  const p=iso.substring(0,10).split('-');
  return p[2]+'/'+p[1]+'/'+p[0];
}

function sa(s){
  if(s==='positivo') return '<span style="color:#34D399;font-weight:bold">&#9650;</span>';
  if(s==='negativo') return '<span style="color:#EF4444;font-weight:bold">&#9660;</span>';
  return '<span style="color:#6B7280;font-weight:bold">&#8212;</span>';
}

function sb(v){
  const m={1:['#064E3B','#34D399','SEV 1'],2:['#78350F','#FCD34D','SEV 2'],3:['#7F1D1D','#FCA5A5','SEV 3']};
  const [bg,cl,lb]=m[v]||m[1];
  return '<span class="badge" style="background:'+bg+';color:'+cl+'">'+lb+'</span>';
}

function cs2(emp){
  return '<span style="color:'+sc(emp)+';font-weight:600">'+eh(emp)+'</span>';
}

function np(arr){
  if(!arr.length) return 0;
  return arr.filter(n=>n.sentimento==='negativo').length/arr.length*100;
}

function pc(p){ return p<25?'#34D399':p<40?'#FCD34D':'#EF4444'; }

function score(emp){
  const it=DATA_NEWS.filter(n=>n.empresa===emp);
  return it.filter(n=>n.sentimento==='negativo').length*2+it.filter(n=>n.severidade===3).length*3;
}

function months6(){
  const r=[]; const now=new Date();
  for(let i=5;i>=0;i--){
    const d=new Date(now.getFullYear(),now.getMonth()-i,1);
    const key=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');
    const raw=d.toLocaleDateString('pt-BR',{month:'short'}).replace('.','');
    r.push({key,lbl:raw.charAt(0).toUpperCase()+raw.slice(1)});
  }
  return r;
}

function byDays(d){ const c=new Date(Date.now()-d*864e5); return DATA_NEWS.filter(n=>n.data&&new Date(n.data)>=c); }

function eh(s){
  if(!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Tab management ───────────────────────────────────────────
const CH={};
let t1=false,t2=false,t3=false;

function showTab(n){
  document.querySelectorAll('.tc').forEach(t=>t.style.display='none');
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab'+n).style.display='block';
  document.querySelectorAll('.tab-btn')[n-1].classList.add('active');
  if(n===1&&!t1){initT1();t1=true;}
  if(n===2&&!t2){initT2();t2=true;}
  if(n===3&&!t3){initT3();t3=true;}
}

// ── Tab 1 ────────────────────────────────────────────────────
function initT1(){
  renderNews();renderAlerts();renderCards();renderSectors();renderAttn();renderThemes();
}

function renderNews(){
  const items=DATA_NEWS.filter(n=>n.data).sort((a,b)=>new Date(b.data)-new Date(a.data)).slice(0,10);
  document.getElementById('latest-news').innerHTML=items.map(n=>`
    <div class="ni">
      <div class="ni-h">${sa(n.sentimento)} ${sb(n.severidade)} ${cs2(n.empresa)} <span class="ni-d">${fd(n.data)}</span></div>
      <div class="ni-t"><a href="${eh(n.url)}" target="_blank" rel="noopener">${eh(n.titulo)}</a></div>
      ${n.resumo?'<div class="ni-s">'+eh(n.resumo.substring(0,160))+'</div>':''}
    </div>`).join('');
}

function renderAlerts(){
  const al=DATA_NEWS.filter(n=>n.severidade===3).sort((a,b)=>new Date(b.data)-new Date(a.data));
  const el=document.getElementById('critical-alerts');
  if(!al.length){el.innerHTML='<div style="color:#6B7280;padding:12px;font-size:13px">Nenhum alerta crítico no período</div>';return;}
  el.innerHTML=al.map(n=>`
    <div class="ac">
      <div class="ni-h">${sa(n.sentimento)} ${cs2(n.empresa)} <span class="ni-d">${fd(n.data)}</span></div>
      <div class="ni-t"><a href="${eh(n.url)}" target="_blank" rel="noopener">${eh(n.titulo)}</a></div>
      ${n.resumo?'<div class="ni-s" style="color:#9CA3AF">'+eh(n.resumo.substring(0,160))+'</div>':''}
    </div>`).join('');
}

function renderCards(){
  const wins=[
    {id:'m6',lbl:'Últimos 6 meses',d:180},{id:'m3',lbl:'Últimos 3 meses',d:90},
    {id:'m1',lbl:'Último mês',d:30},{id:'m7',lbl:'Últimos 7 dias',d:7}
  ];
  wins.forEach(w=>{
    const now=Date.now();
    const cur=byDays(w.d);
    const prv=DATA_NEWS.filter(n=>{
      if(!n.data)return false; const t=new Date(n.data).getTime();
      return t>=now-w.d*2*864e5&&t<now-w.d*864e5;
    });
    const cp=np(cur),pp=np(prv),delta=cp-pp;
    const cl=pc(cp),dc=delta>0?'#EF4444':delta<0?'#34D399':'#6B7280';
    const dt=Math.abs(delta)<0.1?'sem variação':(delta>0?'+':'')+delta.toFixed(1)+'pp vs período ant.';
    document.getElementById(w.id).innerHTML=
      '<div class="ml">'+w.lbl+'</div>'+
      '<div class="mv" style="color:'+cl+'">'+cp.toFixed(1)+'%</div>'+
      '<div class="ms">'+cur.length+' eventos</div>'+
      '<div class="md" style="color:'+dc+'">'+dt+'</div>';
  });
}

function renderSectors(){
  const secs=['Óleo & Gás','Infraestrutura','Serviços Industriais','Financeiro/Outros'];
  const now=Date.now();
  const rows=secs.map(sec=>{
    const it=DATA_NEWS.filter(n=>COMPANY_SECTORS[n.empresa]===sec);
    const tot=it.length,pct=np(it),s3=it.filter(n=>n.severidade===3).length;
    const cm=it.filter(n=>n.data&&new Date(n.data).getTime()>=now-30*864e5);
    const pm=it.filter(n=>{if(!n.data)return false;const t=new Date(n.data).getTime();return t>=now-60*864e5&&t<now-30*864e5;});
    const d=np(cm)-np(pm);
    const tr=Math.abs(d)<0.1?'<span style="color:#6B7280">—</span>':
      d<0?'<span style="color:#34D399">&#9660; '+Math.abs(d).toFixed(1)+'pp</span>':
          '<span style="color:#EF4444">&#9650; '+d.toFixed(1)+'pp</span>';
    const c=SECTOR_COLORS[sec]||'#9CA3AF',p=pc(pct);
    return '<tr><td style="color:'+c+';font-weight:600">'+eh(sec)+'</td><td>'+tot+'</td><td style="color:'+p+'">'+pct.toFixed(1)+'%</td><td>'+s3+'</td><td>'+tr+'</td></tr>';
  });
  const tp=np(DATA_NEWS),ts3=DATA_NEWS.filter(n=>n.severidade===3).length;
  document.getElementById('sector-tbody').innerHTML=rows.join('')+
    '<tr style="border-top:2px solid #374151"><td style="font-weight:700">Total</td><td style="font-weight:700">'+DATA_NEWS.length+'</td><td style="font-weight:700;color:'+pc(tp)+'">'+tp.toFixed(1)+'%</td><td style="font-weight:700">'+ts3+'</td><td></td></tr>';
}

function renderAttn(){
  const emps=[...new Set(DATA_NEWS.map(n=>n.empresa))];
  const scored=emps.map(emp=>{
    const it=DATA_NEWS.filter(n=>n.empresa===emp);
    const pos=it.filter(n=>n.sentimento==='positivo').length;
    const neu=it.filter(n=>n.sentimento==='neutro').length;
    const neg=it.filter(n=>n.sentimento==='negativo').length;
    const s3=it.filter(n=>n.severidade===3).length;
    return {emp,pos,neu,neg,sc2:neg*2+s3*3,tot:it.length||1};
  }).sort((a,b)=>b.sc2-a.sc2);
  document.getElementById('attn-rank').innerHTML=scored.map(x=>{
    const c=sc(x.emp);
    const pw=(x.pos/x.tot*100).toFixed(1),nw=(x.neu/x.tot*100).toFixed(1),ngw=(x.neg/x.tot*100).toFixed(1);
    return '<div style="margin-bottom:9px">'+
      '<div style="display:flex;justify-content:space-between;margin-bottom:2px">'+
      '<span style="color:'+c+';font-weight:600;font-size:12px">'+eh(x.emp)+'</span>'+
      '<span style="color:#6B7280;font-size:11px">Score '+x.sc2+'&nbsp;('+x.tot+' eventos)</span></div>'+
      '<div class="bt">'+
      '<div class="bs" style="width:'+pw+'%;background:#34D399"></div>'+
      '<div class="bs" style="width:'+nw+'%;background:#374151"></div>'+
      '<div class="bs" style="width:'+ngw+'%;background:#EF4444"></div>'+
      '</div></div>';
  }).join('');
}

function renderThemes(){
  const tc={};
  DATA_NEWS.forEach(n=>(n.tags||[]).forEach(tag=>{
    if(!tag)return;
    if(!tc[tag])tc[tag]={tot:0,neg:0};
    tc[tag].tot++;
    if(n.sentimento==='negativo')tc[tag].neg++;
  }));
  const sorted=Object.entries(tc).sort((a,b)=>b[1].tot-a[1].tot);
  const mx=sorted[0]?.[1].tot||1;
  document.getElementById('theme-rank').innerHTML=sorted.map(([tag,{tot,neg}])=>{
    const p=neg/tot*100,bc=p>50?'#EF4444':p>25?'#F59E0B':'#3B82F6';
    const w=(tot/mx*100).toFixed(1);
    return '<div style="margin-bottom:9px">'+
      '<div style="display:flex;justify-content:space-between;margin-bottom:2px">'+
      '<span style="color:#9CA3AF;font-size:12px">'+tag.replace(/_/g,' ')+'</span>'+
      '<span style="color:#6B7280;font-size:11px">'+tot+'&nbsp;&nbsp;'+p.toFixed(0)+'% neg</span></div>'+
      '<div class="bt" style="height:13px"><div class="bs" style="width:'+w+'%;background:'+bc+'"></div></div></div>';
  }).join('');
}

// ── Tab 2 ────────────────────────────────────────────────────
function initT2(){
  renderHeatmap();
  setTimeout(()=>{renderSentChart();renderThemeChart();renderStocks(false);},80);
}

function renderHeatmap(){
  const ms=months6();
  const emps=Object.keys(COMPANY_SECTORS);
  let h='<table class="hm-tbl"><thead><tr><th>Empresa</th>';
  ms.forEach(m=>h+='<th>'+m.lbl+'</th>');
  h+='</tr></thead><tbody>';
  emps.forEach(emp=>{
    const c=sc(emp),its=DATA_NEWS.filter(n=>n.empresa===emp);
    h+='<tr><td style="color:'+c+'">'+eh(emp)+'</td>';
    ms.forEach(m=>{
      const neg=its.filter(n=>n.data&&n.data.startsWith(m.key)&&n.sentimento==='negativo');
      const s3=its.filter(n=>n.data&&n.data.startsWith(m.key)&&n.severidade===3);
      const cnt=neg.length;
      const bg=cnt===0?'#111827':cnt<=2?'#1F2937':cnt<=5?'#7F1D1D':cnt<=9?'#991B1B':'#EF4444';
      const tc2=cnt===0?'#374151':'#F9FAFB';
      h+='<td style="background:'+bg+';color:'+tc2+'" title="'+eh(emp)+' &mdash; '+m.lbl+': '+cnt+' neg, '+s3.length+' sev.3">'+(cnt>0?cnt:'')+'</td>';
    });
    h+='</tr>';
  });
  h+='</tbody></table>';
  document.getElementById('heatmap').innerHTML=h;
}

function renderSentChart(){
  const ctx=document.getElementById('cs'); if(!ctx)return;
  if(CH.s)CH.s.destroy();
  const ms=months6();
  const pos=ms.map(m=>DATA_NEWS.filter(n=>n.data&&n.data.startsWith(m.key)&&n.sentimento==='positivo').length);
  const neu=ms.map(m=>DATA_NEWS.filter(n=>n.data&&n.data.startsWith(m.key)&&n.sentimento==='neutro').length);
  const neg=ms.map(m=>DATA_NEWS.filter(n=>n.data&&n.data.startsWith(m.key)&&n.sentimento==='negativo').length);
  CH.s=new Chart(ctx,{
    type:'line',
    data:{labels:ms.map(m=>m.lbl),datasets:[
      {label:'Positivo',data:pos,borderColor:'#34D399',tension:.3,pointRadius:4,fill:false},
      {label:'Neutro',data:neu,borderColor:'#6B7280',tension:.3,pointRadius:4,fill:false},
      {label:'Negativo',data:neg,borderColor:'#EF4444',tension:.3,pointRadius:4,fill:false}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{
        title:{display:true,text:'Evolução do sentimento — portfólio completo',color:'#9CA3AF',font:{size:12}},
        legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:10}}
      },
      scales:{
        x:{ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'}},
        y:{ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'},beginAtZero:true}
      }
    }
  });
}

function renderThemeChart(){
  const ctx=document.getElementById('ct'); if(!ctx)return;
  if(CH.t)CH.t.destroy();
  const td={};
  DATA_NEWS.forEach(n=>(n.tags||[]).forEach(tag=>{
    if(!tag)return;
    if(!td[tag])td[tag]={p:0,n:0,ng:0};
    if(n.sentimento==='positivo')td[tag].p++;
    else if(n.sentimento==='neutro')td[tag].n++;
    else if(n.sentimento==='negativo')td[tag].ng++;
  }));
  const sorted=Object.entries(td).sort((a,b)=>(b[1].p+b[1].n+b[1].ng)-(a[1].p+a[1].n+a[1].ng));
  CH.t=new Chart(ctx,{
    type:'bar',
    data:{labels:sorted.map(([t])=>t.replace(/_/g,' ')),datasets:[
      {label:'Positivo',data:sorted.map(([,v])=>v.p),backgroundColor:'#34D399'},
      {label:'Neutro',data:sorted.map(([,v])=>v.n),backgroundColor:'#374151'},
      {label:'Negativo',data:sorted.map(([,v])=>v.ng),backgroundColor:'#EF4444'}
    ]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{
        title:{display:true,text:'Distribuição de temas por sentimento',color:'#9CA3AF',font:{size:12}},
        legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:10}}
      },
      scales:{
        x:{stacked:true,ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'}},
        y:{stacked:true,ticks:{color:'#9CA3AF',font:{size:11}},grid:{color:'#1F2937'}}
      }
    }
  });
}

function renderStocks(all){
  document.getElementById('btn-top5').classList.toggle('active',!all);
  document.getElementById('btn-all').classList.toggle('active',all);
  const ctx=document.getElementById('ck'); if(!ctx)return;
  if(CH.k)CH.k.destroy();
  const se=[...new Set(DATA_STOCKS.map(s=>s.empresa))];
  const emps=all?se:[...se].map(e=>({e,sc3:score(e)})).sort((a,b)=>b.sc3-a.sc3).slice(0,5).map(x=>x.e);
  const allDates=[...new Set(DATA_STOCKS.map(s=>s.date))].sort();
  const sev3={};
  DATA_NEWS.filter(n=>n.severidade===3&&n.sentimento==='negativo'&&n.data).forEach(n=>{
    const d=n.data.substring(0,10);
    if(!sev3[n.empresa])sev3[n.empresa]=new Set();
    sev3[n.empresa].add(d);
  });
  const ds=[];
  emps.forEach(emp=>{
    const c=sc(emp),sm={};
    DATA_STOCKS.filter(s=>s.empresa===emp).forEach(s=>sm[s.date]=s.close_norm);
    ds.push({label:emp,data:allDates.map(d=>sm[d]!==undefined?sm[d]:null),
      borderColor:c,borderWidth:1.5,pointRadius:0,pointHoverRadius:4,spanGaps:false,tension:.1});
    const s3=sev3[emp];
    if(s3&&s3.size){
      const pts=allDates.map(d=>s3.has(d)&&sm[d]!==undefined?sm[d]:null);
      if(pts.some(v=>v!==null))
        ds.push({label:'* '+emp,data:pts,type:'scatter',borderColor:'#EF4444',
          backgroundColor:'#EF4444',pointRadius:5,showLine:false});
    }
  });
  const dlbl=allDates.map(d=>{const p=d.split('-');return p[2]+'/'+p[1];});
  CH.k=new Chart(ctx,{
    type:'line',
    data:{labels:dlbl,datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{position:'bottom',labels:{color:'#9CA3AF',boxWidth:12,padding:8,
          filter:item=>!item.text.startsWith('*')}},
        tooltip:{callbacks:{label:c2=>{if(c2.raw===null)return null;return c2.dataset.label+': '+c2.raw.toFixed(1);}}}
      },
      scales:{
        x:{ticks:{color:'#9CA3AF',maxTicksLimit:12,maxRotation:45,font:{size:10}},grid:{color:'#1F2937'}},
        y:{ticks:{color:'#9CA3AF'},grid:{color:'#1F2937'},
          title:{display:true,text:'Base 100',color:'#6B7280',font:{size:11}}}
      }
    }
  });
}

// ── Tab 3 ────────────────────────────────────────────────────
const TAGS=['liquidez_refinanciamento','resultado_guidance','governanca','legal_regulatorio',
            'operacional_incidente','m&a_estrategia','setor_macro','esg_reputacional'];
let f3={empresa:'',setor:'',sentimento:'',severidade:'',tema:''};

function initT3(){
  populateT3();
  applyF();
}

function populateT3(){
  const emps=[...new Set(DATA_NEWS.map(n=>n.empresa))].sort();
  const se=document.getElementById('fe');
  se.innerHTML='<option value="">Empresa</option>'+emps.map(e=>'<option value="'+eh(e)+'">'+eh(e)+'</option>').join('');
  const st=document.getElementById('ftm');
  if(st.options.length<=1)
    st.innerHTML='<option value="">Tema</option>'+TAGS.map(t=>'<option value="'+t+'">'+t.replace(/_/g,' ')+'</option>').join('');
}

function handleSec(val){
  f3.setor=val; f3.empresa='';
  const emps=val?[...new Set(DATA_NEWS.filter(n=>COMPANY_SECTORS[n.empresa]===val).map(n=>n.empresa))].sort()
               :[...new Set(DATA_NEWS.map(n=>n.empresa))].sort();
  document.getElementById('fe').innerHTML='<option value="">Empresa</option>'+
    emps.map(e=>'<option value="'+eh(e)+'">'+eh(e)+'</option>').join('');
  applyF();
}

function handleEmp(val){
  f3.empresa=val;
  if(val){const s=COMPANY_SECTORS[val]||'';f3.setor=s;document.getElementById('fse').value=s;}
  applyF();
}

function applyF(){
  let r=DATA_NEWS;
  if(f3.empresa) r=r.filter(n=>n.empresa===f3.empresa);
  if(f3.setor)   r=r.filter(n=>COMPANY_SECTORS[n.empresa]===f3.setor);
  if(f3.sentimento) r=r.filter(n=>n.sentimento===f3.sentimento);
  if(f3.severidade) r=r.filter(n=>n.severidade===parseInt(f3.severidade));
  if(f3.tema) r=r.filter(n=>(n.tags||[]).includes(f3.tema));
  renderTable(r);
  document.getElementById('nctr').textContent='Exibindo '+r.length+' de '+DATA_NEWS.length+' notícias';
}

function resetF(){
  f3={empresa:'',setor:'',sentimento:'',severidade:'',tema:''};
  ['fe','fse','fst','fsv','ftm'].forEach(id=>document.getElementById(id).value='');
  populateT3(); applyF();
}

function renderTable(items){
  const sorted=[...items].sort((a,b)=>new Date(b.data)-new Date(a.data));
  document.getElementById('ntb').innerHTML=sorted.map(n=>{
    const tags=(n.tags||[]).filter(Boolean).map(t=>'<span class="pill">'+t.replace(/_/g,' ')+'</span>').join('');
    const tit=n.titulo.length>90?n.titulo.substring(0,90)+'…':n.titulo;
    const res=n.resumo.length>120?n.resumo.substring(0,120)+'…':n.resumo;
    return '<tr>'+
      '<td style="color:#6B7280;white-space:nowrap">'+fd(n.data)+'</td>'+
      '<td>'+cs2(n.empresa)+'</td>'+
      '<td>'+sb(n.severidade)+'</td>'+
      '<td>'+sa(n.sentimento)+'</td>'+
      '<td style="max-width:280px"><a href="'+eh(n.url)+'" target="_blank" rel="noopener">'+eh(tit)+'</a></td>'+
      '<td>'+tags+'</td>'+
      '<td style="color:#6B7280;font-size:12px;max-width:240px">'+eh(res)+'</td>'+
      '</tr>';
  }).join('');
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>showTab(1));
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
