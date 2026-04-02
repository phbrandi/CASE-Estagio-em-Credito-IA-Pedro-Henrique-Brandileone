"""
Repopula a coluna snippet_ou_trecho no news.csv existente,
sem reclassificar. Usa threads para acelerar os GETs.
"""
import sys
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '.')
from scripts.collector import extrair_snippet

CSV_PATH = "output/news.csv"
MAX_WORKERS = 20  # requisições paralelas

df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

# Re-busca para TODOS os itens do Google News (RSS summary é só o título repetido)
# e também os demais que estão vazios
mask_refetch = (df["fonte"] == "Google News") | df["snippet_ou_trecho"].isna() | (df["snippet_ou_trecho"].fillna("") == "")
indices_vazios = df[mask_refetch].index.tolist()
print(f"Itens para re-buscar snippet: {len(indices_vazios)} / {len(df)}")

if not indices_vazios:
    print("Nada a fazer.")
    sys.exit(0)

# Busca em paralelo
resultados = {}

def fetch(idx):
    url = df.at[idx, "url"]
    return idx, extrair_snippet(url)

print(f"Buscando snippets com {MAX_WORKERS} threads em paralelo...")
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(fetch, idx): idx for idx in indices_vazios}
    done = 0
    for future in as_completed(futures):
        idx, snippet = future.result()
        resultados[idx] = snippet
        done += 1
        if done % 100 == 0:
            print(f"  {done}/{len(indices_vazios)} concluídos...")

# Aplica resultados
preenchidos = 0
for idx, snippet in resultados.items():
    if snippet:
        df.at[idx, "snippet_ou_trecho"] = snippet
        preenchidos += 1

print(f"\nSnippets preenchidos: {preenchidos}")
ainda_vazios = df["snippet_ou_trecho"].isna().sum() + (df["snippet_ou_trecho"].fillna("") == "").sum()
print(f"Ainda vazios (sites bloqueados/paywall): {ainda_vazios}")

df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
print(f"CSV salvo em {CSV_PATH}")
