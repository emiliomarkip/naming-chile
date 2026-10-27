"""Embeddings de palabras con caché en disco (data/emb_cache.npz).

Modelo: paraphrase-multilingual-MiniLM-L12-v2 (fastembed), el mismo que usa
el buscador de Markip. Alinea español e inglés en el mismo espacio, lo que
permite usar normas en inglés (concreción) sobre palabras en español.
"""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "emb_cache.npz"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_cache = None


def _load_cache():
    global _cache
    if _cache is None:
        _cache = {}
        if CACHE.exists():
            z = np.load(CACHE, allow_pickle=True)
            _cache = dict(zip(z["keys"].tolist(), z["emb"]))
    return _cache


def embed(words):
    """Devuelve matriz (n, 384) L2-normalizada para la lista de strings."""
    global _model
    cache = _load_cache()
    faltan = sorted({w for w in words if w not in cache})
    if faltan:
        if _model is None:
            from fastembed import TextEmbedding
            _model = TextEmbedding(MODEL)
        print(f"  embeddings: {len(faltan)} palabras nuevas…")
        vecs = np.array(list(_model.embed(faltan, batch_size=256)), dtype=np.float32)
        for w, v in zip(faltan, vecs):
            cache[w] = v
        keys = list(cache.keys())
        np.savez_compressed(CACHE, keys=np.array(keys, dtype=object),
                            emb=np.stack([cache[k] for k in keys]))
    m = np.stack([cache[w] for w in words]).astype(np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)
