"""
Clustering semántico de las marcas de tecnología (clases de Niza 9 y 42).

1. Embeddings del nombre con paraphrase-multilingual-MiniLM-L12-v2 (fastembed,
   mismo modelo que usa el buscador Markip / colección Qdrant).
2. KMeans (k=12) sobre embeddings L2-normalizados.
3. Etiqueta de cada cluster: términos más distintivos (TF-IDF) + muestra.
4. Evolución: participación de cada cluster por año de solicitud.
5. Proyección 2D (PCA 50d -> t-SNE) de una muestra para el scatter de la web.

Salidas:
  data/tech_clusters.parquet    (application_number, cluster)
  data/agg/tech_cluster_year.json
  data/agg/tech_scatter.json    (muestra 4000 pts: x, y, cluster, nombre, año)
  data/agg/tech_cluster_info.json (tamaño, términos top, ejemplos)

Uso: .venv/bin/python scripts/cluster_tech.py
"""
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from fastembed import TextEmbedding
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
K = 12
SEED = 42

df = pd.read_parquet(ROOT / "data" / "features_ling.parquet")
tech = df[df["ind_software"]].copy()
print(f"marcas tech: {len(tech)}")

nombres = tech["brand_name"].astype(str).str.strip()
tech = tech[nombres.str.len().between(2, 60)].copy()
tech["nombre_norm"] = nombres.str.upper()

# --- embeddings (cachea en disco: tarda varios minutos la primera vez) ---
cache = ROOT / "data" / "tech_embeddings.npz"
unicos = sorted(tech["nombre_norm"].unique())
if cache.exists():
    z = np.load(cache, allow_pickle=True)
    if list(z["names"]) == unicos:
        emb = z["emb"]
    else:
        cache.unlink()
if not cache.exists():
    print(f"embeddings de {len(unicos)} nombres únicos...")
    model = TextEmbedding("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    emb = np.array(list(model.embed(unicos, batch_size=256)), dtype=np.float32)
    np.savez_compressed(cache, emb=emb, names=np.array(unicos, dtype=object))
emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
print("embeddings:", emb.shape)

# --- kmeans ---
km = KMeans(n_clusters=K, random_state=SEED, n_init=6)
labels_unicos = km.fit_predict(emb)
lbl_por_nombre = dict(zip(unicos, labels_unicos))
tech["cluster"] = tech["nombre_norm"].map(lbl_por_nombre)

# --- términos distintivos por cluster (log-odds simple sobre tokens) ---
TOK = re.compile(r"[A-ZÁÉÍÓÚÜÑ]{3,}")
tot = Counter()
por_cluster = {c: Counter() for c in range(K)}
for nom, c in zip(tech["nombre_norm"], tech["cluster"]):
    ts = set(TOK.findall(nom))
    tot.update(ts)
    por_cluster[c].update(ts)

info = {}
for c in range(K):
    n_c = int((tech["cluster"] == c).sum())
    score = {t: cnt / (tot[t] + 20) for t, cnt in por_cluster[c].items() if cnt >= 8}
    top = sorted(score, key=score.get, reverse=True)[:8]
    ejemplos = tech[tech["cluster"] == c]["brand_name"].drop_duplicates().sample(
        min(8, n_c), random_state=SEED).tolist()
    info[c] = {"n": n_c, "terminos": top, "ejemplos": ejemplos}
    print(f"\ncluster {c} (n={n_c}): {', '.join(top)}")
    print("   ej:", "; ".join(ejemplos[:5]))

# --- evolución por año ---
evo = (tech.groupby(["filing_year", "cluster"]).size()
       .unstack(fill_value=0))
evo_pct = evo.div(evo.sum(axis=1), axis=0) * 100
serie = {str(c): {int(y): round(float(evo_pct.loc[y, c]), 2) for y in evo_pct.index}
         for c in evo_pct.columns}

# --- scatter 2D (muestra) ---
rng = np.random.default_rng(SEED)
idx = rng.choice(len(unicos), size=min(4000, len(unicos)), replace=False)
sub_emb = emb[idx]
print("\nPCA + t-SNE de la muestra...")
p50 = PCA(n_components=50, random_state=SEED).fit_transform(sub_emb)
xy = TSNE(n_components=2, random_state=SEED, perplexity=40, init="pca",
          max_iter=600).fit_transform(p50)
xy = (xy - xy.min(0)) / (xy.max(0) - xy.min(0)) * 100

anio_por_nombre = tech.groupby("nombre_norm")["filing_year"].min().to_dict()
orig_por_norm = tech.drop_duplicates("nombre_norm").set_index("nombre_norm")["brand_name"].to_dict()
scatter = []
for j, i in enumerate(idx):
    nom = unicos[i]
    scatter.append({
        "x": round(float(xy[j, 0]), 1), "y": round(float(xy[j, 1]), 1),
        "c": int(labels_unicos[i]), "n": orig_por_norm.get(nom, nom),
        "a": int(anio_por_nombre.get(nom, 0)),
    })

tech[["application_number", "cluster"]].to_parquet(ROOT / "data" / "tech_clusters.parquet", index=False)
(AGG / "tech_cluster_year.json").write_text(json.dumps(serie))
(AGG / "tech_scatter.json").write_text(json.dumps(scatter, ensure_ascii=False))
(AGG / "tech_cluster_info.json").write_text(json.dumps(info, ensure_ascii=False))
print("\nListo: tech_cluster_year.json, tech_scatter.json, tech_cluster_info.json")
