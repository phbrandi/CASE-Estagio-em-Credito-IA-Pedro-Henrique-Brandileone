"""
collector.py — Coleta notícias e comunicados de RI para as empresas do portfólio.

Fontes:
  1. Google News RSS
  2. Página de RI da empresa (campo ri_url do companies.csv)
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Headers realistas para evitar bloqueios
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PERIODO_DIAS = 180
TIMEOUT = 5

# Palavras-chave heurísticas para identificar comunicados de RI
KEYWORDS_RI = [
    "fato relevante",
    "comunicado",
    "release",
    "resultado",
    "press release",
    "aviso",
    "ata",
    "edital",
    "prospecto",
    "informe",
    "nota",
    "demonstração",
    "demonstracao",
    "balanço",
    "balanco",
    "relatório",
    "relatorio",
    "earnings",
    "guidance",
    "dividendo",
    "jscp",
    "proventos",
    "emissão",
    "emissao",
    "debênture",
    "debenture",
    "cri",
    "cra",
]


def _parse_date(date_str: str) -> str:
    """Tenta parsear uma string de data e retorna em formato ISO. Usa data atual como fallback."""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    formatos = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
    ]
    for fmt in formatos:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    # Fallback: data atual
    return datetime.now(timezone.utc).isoformat()


def _dentro_periodo(date_iso: str, dias: int = PERIODO_DIAS) -> bool:
    """Verifica se a data ISO está dentro do período de 'dias' dias atrás."""
    try:
        dt = datetime.fromisoformat(date_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        limite = datetime.now(timezone.utc) - timedelta(days=dias)
        return dt >= limite
    except Exception:
        # Se não conseguir parsear (ex: "desconhecida"), descarta — não inclui item sem data
        return False


def _coletar_google_news(empresa: dict) -> list[dict]:
    """Consulta o Google News RSS e retorna itens do período."""
    nome = empresa.get("empresa", "")
    ticker = empresa.get("ticker", "")
    query = f"{nome} {ticker}"
    url = (
        f"https://news.google.com/rss/search?q={requests.utils.quote(query)}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )
    items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            titulo = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            # Usa published_parsed (struct_time) quando disponível — mais confiável que a string
            published_parsed = entry.get("published_parsed")
            if published_parsed:
                import calendar
                ts = calendar.timegm(published_parsed)
                data_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            else:
                data_iso = _parse_date(entry.get("published", ""))

            if not titulo or not link or not link.startswith("http"):
                continue
            if not _dentro_periodo(data_iso):
                continue

            # O RSS já fornece um resumo — usar diretamente sem fazer GET
            summary_raw = entry.get("summary", "") or ""
            # Limpar tags HTML que o feedparser pode deixar no summary
            from bs4 import BeautifulSoup as _BS
            summary_text = _BS(summary_raw, "lxml").get_text(separator=" ", strip=True)[:500]

            items.append(
                {
                    "url": link,
                    "titulo": titulo,
                    "data_publicacao": data_iso,
                    "fonte": "Google News",
                    "tipo": "noticia",
                    "snippet_ou_trecho": summary_text,
                }
            )
        logger.info("Google News: %d itens encontrados para %s", len(items), nome)
    except Exception as exc:
        logger.warning("Erro ao consultar Google News para %s: %s", nome, exc)
    return items


def _coletar_ri(empresa: dict) -> list[dict]:
    """Raspa a página de RI buscando links de comunicados, fatos relevantes e releases."""
    nome = empresa.get("empresa", "")
    ri_url = empresa.get("ri_url", "").strip()
    if not ri_url or not ri_url.startswith("http"):
        logger.warning("URL de RI inválida para %s: '%s'", nome, ri_url)
        return []

    items = []
    try:
        resp = requests.get(ri_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            logger.warning("RI %s retornou status %d", nome, resp.status_code)
            return []
        soup = BeautifulSoup(resp.content, "lxml")

        for tag in soup.find_all("a", href=True):
            texto = tag.get_text(strip=True).lower()
            href = tag["href"].strip()

            # Filtrar links relevantes por heurística de texto ou extensão PDF
            eh_relevante = any(kw in texto for kw in KEYWORDS_RI) or href.lower().endswith(".pdf")
            if not eh_relevante:
                continue

            # Montar URL absoluta
            if href.startswith("http"):
                url_abs = href
            elif href.startswith("/"):
                parsed = urlparse(ri_url)
                url_abs = f"{parsed.scheme}://{parsed.netloc}{href}"
            else:
                url_abs = ri_url.rstrip("/") + "/" + href

            titulo = tag.get_text(strip=True) or tag.get("title", "Comunicado RI")
            if not titulo:
                continue

            # Tentar extrair data de atributos da tag ou de texto próximo (ex: <td>, <span> irmão)
            data_iso = ""
            for attr in ["data-date", "data-time", "datetime", "title"]:
                val = tag.get(attr, "")
                if val:
                    tentativa = _parse_date(val)
                    if not tentativa.startswith(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")):
                        data_iso = tentativa
                        break
            # Procura texto de data em elementos irmãos próximos
            if not data_iso:
                parent = tag.parent
                if parent:
                    import re as _re
                    texto_pai = parent.get_text(" ", strip=True)
                    # Padrões comuns: 01/04/2026, 2026-04-01, 01 abr 2026
                    m = _re.search(r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})\b', texto_pai)
                    if m:
                        data_iso = _parse_date(m.group(1))
            # Fallback: data desconhecida (não inventar datetime.now)
            if not data_iso:
                data_iso = "desconhecida"

            items.append(
                {
                    "url": url_abs,
                    "titulo": titulo,
                    "data_publicacao": data_iso,
                    "fonte": f"RI {nome}",
                    "tipo": "comunicado_oficial",
                }
            )

        logger.info("RI %s: %d itens encontrados", nome, len(items))
    except requests.exceptions.Timeout:
        logger.warning("Timeout ao acessar RI de %s (%s)", nome, ri_url)
    except Exception as exc:
        logger.warning("Erro ao raspar RI de %s: %s", nome, exc)
    return items


def buscar_links(empresa: dict) -> list[dict]:
    """
    Recebe uma linha do companies.csv como dicionário.
    Retorna lista de dicts: url, titulo, data_publicacao (ISO), fonte, tipo.
    Filtra apenas itens dos últimos 180 dias.
    """
    nome = empresa.get("empresa", "Desconhecida")
    logger.info("Coletando links para: %s", nome)

    items = []
    items.extend(_coletar_google_news(empresa))
    items.extend(_coletar_ri(empresa))

    # Filtrar itens sem URL válida ou sem título
    validos = [
        it for it in items
        if it.get("url", "").startswith("http") and it.get("titulo", "").strip()
    ]
    descartados = len(items) - len(validos)
    if descartados:
        logger.info("Descartados %d itens inválidos (sem URL ou título) para %s", descartados, nome)

    return validos


def extrair_snippet(url: str) -> str:
    """
    Faz GET na URL e extrai título + primeiro parágrafo relevante.
    Retorna string com no máximo 500 caracteres. Nunca levanta exceção.

    URLs do Google News são redirecionamentos para artigos externos com anti-scraping;
    pulamos o GET e retornamos string vazia para evitar timeouts em série.
    """
    if not url or not url.startswith("http"):
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            logger.debug("Snippet: status %d para %s", resp.status_code, url)
            return ""

        # Se o redirect ficou em domínio do Google, não há conteúdo de artigo
        final_domain = urlparse(resp.url).netloc.lower()
        if "google.com" in final_domain:
            logger.debug("Snippet: redirect ficou no Google para %s", url)
            return ""

        soup = BeautifulSoup(resp.content, "lxml")

        # Remove elementos de navegação/cabeçalho que poluem o texto
        for tag in soup.find_all(["nav", "header", "footer", "script", "style", "aside"]):
            tag.decompose()

        # Busca parágrafos reais: prioriza <p> com texto substancial (>=80 chars),
        # depois <article>, por último <div>
        paragrafo = ""
        for selector in [["p"], ["article"], ["div"]]:
            for tag in soup.find_all(selector):
                texto = tag.get_text(separator=" ", strip=True)
                if len(texto) >= 80:
                    paragrafo = texto[:400]
                    break
            if paragrafo:
                break

        return paragrafo[:500]
    except requests.exceptions.Timeout:
        logger.debug("Timeout ao extrair snippet de %s", url)
        return ""
    except Exception as exc:
        logger.debug("Erro ao extrair snippet de %s: %s", url, exc)
        return ""


async def _extrair_texto_pagina(page, url: str) -> str:
    """Navega até a URL com Playwright e extrai o texto principal do artigo."""
    try:
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")

        # Remove elementos que poluem o texto (nav, rodapé, anúncios)
        await page.evaluate("""
            () => {
                const seletores = ['nav','header','footer','script','style',
                                   'aside','[class*="ad-"]','[id*="ad-"]',
                                   '[class*="banner"]','[class*="cookie"]'];
                seletores.forEach(s => {
                    document.querySelectorAll(s).forEach(el => el.remove());
                });
            }
        """)

        # Tenta extrair <article>, depois parágrafos com >= 80 chars
        texto = await page.evaluate("""
            () => {
                const article = document.querySelector('article');
                if (article) {
                    const t = article.innerText.replace(/\\s+/g, ' ').trim();
                    if (t.length >= 80) return t;
                }
                const paras = [...document.querySelectorAll('p')]
                    .map(p => p.innerText.replace(/\\s+/g, ' ').trim())
                    .filter(t => t.length >= 80)
                    .join(' ');
                return paras;
            }
        """)
        return (texto or "")[:1500]
    except Exception as exc:
        logger.debug("Playwright: erro em %s — %s", url, exc)
        return ""


async def _extrair_snippets_async(items: list[dict], max_concurrent: int = 10) -> None:
    """Preenche snippet_ou_trecho nos itens que ainda não têm, em paralelo."""
    import asyncio
    from playwright.async_api import async_playwright

    pendentes = [it for it in items if not it.get("snippet_ou_trecho")]
    if not pendentes:
        return

    sem = asyncio.Semaphore(max_concurrent)
    total = len(pendentes)
    concluidos = 0

    async def processar(browser, item):
        nonlocal concluidos
        async with sem:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="pt-BR",
            )
            page = await context.new_page()
            try:
                item["snippet_ou_trecho"] = await _extrair_texto_pagina(page, item["url"])
            finally:
                await context.close()
                concluidos += 1
                if concluidos % 100 == 0:
                    logger.info("Playwright: %d/%d snippets extraídos", concluidos, total)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            await asyncio.gather(*[processar(browser, it) for it in pendentes])
        finally:
            await browser.close()

    preenchidos = sum(1 for it in pendentes if it.get("snippet_ou_trecho"))
    logger.info(
        "Playwright: %d/%d snippets preenchidos (%d sites bloqueados/vazios)",
        preenchidos, total, total - preenchidos,
    )


def extrair_snippets_playwright(items: list[dict]) -> None:
    """
    Preenche snippet_ou_trecho nos itens sem conteúdo usando Playwright (browser headless).
    Modifica a lista in-place. Seguro chamar mesmo se playwright não estiver instalado
    — loga aviso e retorna sem erro.
    """
    import asyncio
    import sys

    try:
        import playwright  # noqa: F401
    except ImportError:
        logger.warning(
            "playwright não instalado. Execute: pip install playwright && "
            "python -m playwright install chromium"
        )
        return

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(_extrair_snippets_async(items))


def _normalizar_url(url: str) -> str:
    """Remove parâmetros e fragmentos para normalização."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()


def deduplicar(items: list[dict]) -> list[dict]:
    """
    Remove duplicatas em duas passagens:
      1. Por hash SHA256 da URL normalizada
      2. Por similaridade de título (SequenceMatcher threshold 0.85)
    """
    # Passagem 1: dedupe por URL
    vistos_hash = set()
    sem_url_dup = []
    removidos_url = 0
    for it in items:
        h = hashlib.sha256(_normalizar_url(it["url"]).encode("utf-8")).hexdigest()
        if h in vistos_hash:
            removidos_url += 1
        else:
            vistos_hash.add(h)
            sem_url_dup.append(it)
    logger.info("Dedupe passagem 1 (URL): removidos %d itens", removidos_url)

    # Passagem 2: dedupe por título similar
    resultado = []
    removidos_titulo = 0
    for it in sem_url_dup:
        titulo_it = it["titulo"].lower().strip()
        eh_duplicado = False
        for existing in resultado:
            ratio = SequenceMatcher(None, titulo_it, existing["titulo"].lower().strip()).ratio()
            if ratio >= 0.85:
                eh_duplicado = True
                break
        if eh_duplicado:
            removidos_titulo += 1
        else:
            resultado.append(it)
    logger.info("Dedupe passagem 2 (título): removidos %d itens", removidos_titulo)

    return resultado


if __name__ == "__main__":
    import csv

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with open("companies.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        empresa = next(reader)

    print(f"Testando: {empresa['empresa']}")
    items = buscar_links(empresa)
    print(f"Links encontrados: {len(items)}")

    for item in items[:3]:
        snippet = extrair_snippet(item["url"])
        print(f"  - {item['titulo'][:60]} | snippet: {len(snippet)} chars")

    deduped = deduplicar(items)
    print(f"Após dedupe: {len(deduped)}")
