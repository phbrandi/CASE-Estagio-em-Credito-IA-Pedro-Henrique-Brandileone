"""
classifier.py — Classifica itens de notícias usando a API Anthropic (Claude Haiku).

Retorna campos: sentimento, tags, severidade, resumo_curto.
"""

import json
import logging
import re
import time

import anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Tags válidas
TAGS_VALIDAS = {
    "liquidez_refinanciamento",
    "resultado_guidance",
    "governanca",
    "legal_regulatorio",
    "operacional_incidente",
    "m&a_estrategia",
    "setor_macro",
    "esg_reputacional",
}

SENTIMENTOS_VALIDOS = {"positivo", "neutro", "negativo"}
SEVERIDADES_VALIDAS = {1, 2, 3}

DEFAULTS = {
    "sentimento": "neutro",
    "tags": ["setor_macro"],
    "severidade": 1,
    "resumo_curto": "Classificação indisponível",
}

PROMPT_TEMPLATE = """Você é um analista de crédito sênior. Classifique a notícia abaixo SOMENTE com base no texto fornecido. NÃO infira nada além do que está explícito.

Título: {titulo}
Trecho: {trecho}

Retorne APENAS um JSON válido com exatamente este schema (sem texto adicional, sem markdown, sem backticks):
{{
  "sentimento": "positivo|neutro|negativo",
  "tags": ["tag1", "tag2"],
  "severidade": 1,
  "resumo_curto": "1-2 linhas objetivas sobre o evento"
}}

Regras:
- sentimento: escolha exatamente um entre positivo, neutro ou negativo
- tags: lista com 1 ou mais dos valores: liquidez_refinanciamento, resultado_guidance, governanca, legal_regulatorio, operacional_incidente, m&a_estrategia, setor_macro, esg_reputacional
- severidade: 1 (baixo impacto/ruído), 2 (relevante, merece atenção), 3 (potencialmente material)
- resumo_curto: string objetiva de 1-2 linhas

Retorne SOMENTE o JSON, sem nenhum texto antes ou depois."""


def _limpar_json(texto: str) -> str:
    """Remove markdown backticks e texto extra antes/depois do JSON."""
    # Remover blocos de código markdown
    texto = re.sub(r"```(?:json)?", "", texto).strip()
    # Encontrar o primeiro { e o último }
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio != -1 and fim != -1:
        return texto[inicio : fim + 1]
    return texto


def _validar(resultado: dict) -> bool:
    """Valida se o resultado tem todos os campos corretos."""
    if resultado.get("sentimento") not in SENTIMENTOS_VALIDOS:
        return False
    tags = resultado.get("tags")
    if not isinstance(tags, list) or not tags:
        return False
    if not all(t in TAGS_VALIDAS for t in tags):
        return False
    if resultado.get("severidade") not in SEVERIDADES_VALIDAS:
        return False
    if not isinstance(resultado.get("resumo_curto"), str) or not resultado["resumo_curto"].strip():
        return False
    return True


def _chamar_api(client: anthropic.Anthropic, titulo: str, trecho: str) -> dict | None:
    """Chama a API e retorna o dict classificado ou None em caso de falha."""
    prompt = PROMPT_TEMPLATE.format(
        titulo=titulo[:300],
        trecho=trecho[:500] if trecho else "(sem trecho disponível)",
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = msg.content[0].text.strip()
        json_limpo = _limpar_json(texto)
        resultado = json.loads(json_limpo)
        return resultado
    except json.JSONDecodeError as exc:
        logger.warning("Erro ao parsear JSON da API: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Erro na chamada à API Anthropic: %s", exc)
        return None


def classify_llm(item: dict) -> dict:
    """
    Classifica um item usando Claude Haiku.
    Recebe dict com campos 'titulo' e 'snippet_ou_trecho'.
    Retorna dict com sentimento, tags, severidade, resumo_curto.
    """
    titulo = item.get("titulo", "")
    trecho = item.get("snippet_ou_trecho", "")

    client = anthropic.Anthropic()  # Lê ANTHROPIC_API_KEY do ambiente

    # Tentativa 1
    resultado = _chamar_api(client, titulo, trecho)
    if resultado and _validar(resultado):
        time.sleep(0.5)
        return resultado

    logger.warning("Primeira tentativa inválida para '%s'. Fazendo retry...", titulo[:60])

    # Retry único
    time.sleep(1.0)
    resultado = _chamar_api(client, titulo, trecho)
    if resultado and _validar(resultado):
        time.sleep(0.5)
        return resultado

    logger.error("Falha na classificação de '%s'. Usando defaults.", titulo[:60])
    time.sleep(0.5)
    return dict(DEFAULTS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    item = {
        "titulo": "Petrobras anuncia novo plano de investimentos de R$ 100 bilhões",
        "snippet_ou_trecho": (
            "A Petrobras divulgou nesta segunda-feira seu novo plano estratégico "
            "2025-2029 com investimentos de R$ 100 bilhões focados em exploração do pré-sal."
        ),
    }
    result = classify_llm(item)
    print(result)
