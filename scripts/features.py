"""
Calcula features lingüísticas por marca sobre data/marcas.parquet
y guarda data/features.parquet.

Features: largo, nº palabras, idioma (es/en/inventado/mixto/sigla),
afijos de moda, nacionalidad del titular, outcome del trámite.

Uso: .venv/bin/python scripts/features.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_parquet(ROOT / "data" / "marcas.parquet")

# --- universo: marcas con elemento verbal ---
df = df[df["sign_type"].isin(["Denominativa", "Mixta"])].copy()
df = df[df["brand_name"].notna() & (df["brand_name"].str.strip() != "")]

TOKEN_RE = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


_cache = {}


def clasificar_token(tok: str) -> str:
    """es / en / inventado / ambiguo para un token."""
    tok = tok.lower()
    if tok in _cache:
        return _cache[tok]
    es = zipf_frequency(tok, "es")
    en = zipf_frequency(tok, "en")
    base = sin_tildes(tok)
    if base != tok:
        es = max(es, zipf_frequency(base, "es"))
    if es < 2.0 and en < 2.0:
        r = "inventado"
    elif es >= en + 0.5:
        r = "es"
    elif en >= es + 0.5:
        r = "en"
    else:
        r = "ambiguo"
    _cache[tok] = r
    return r


def clasificar_nombre(nombre: str) -> str:
    """Clasifica el nombre completo por mayoría de tokens."""
    tokens = [t for t in TOKEN_RE.findall(nombre) if len(t) >= 3]
    if not tokens:
        return "sigla"  # solo siglas/números/símbolos
    votos = [clasificar_token(t) for t in tokens]
    n = len(votos)
    es = votos.count("es")
    en = votos.count("en")
    inv = votos.count("inventado")
    if inv / n > 0.5:
        return "inventado"
    if es > 0 and en > 0:
        return "mixto"
    if es >= en and es >= inv:
        return "es"
    if en > 0:
        return "en"
    return "inventado"


AFIJOS = {
    "tech": re.compile(r"\b\w*te[c]?h\b|\btec\b|\w{3,}tec\b", re.I),
    "max": re.compile(r"\bmax\b|\w{3,}max\b", re.I),
    "pro": re.compile(r"\bpro\b|\w{4,}pro\b", re.I),
    "chile": re.compile(r"chile", re.I),
    "mart": re.compile(r"\w{2,}mart\b", re.I),
    "eco": re.compile(r"\beco\w{2,}|\beco\b", re.I),
    "i_prefijo": re.compile(r"\bi[A-Z]\w+"),
    "app": re.compile(r"\bapp\b|\bapp\w{2,}|\w{3,}app\b", re.I),
    "punto_cl": re.compile(r"\.cl\b", re.I),
    "go": re.compile(r"\bgo\w{3,}", re.I),
    "smart": re.compile(r"\bsmart\w*", re.I),
    "ly": re.compile(r"\w{3,}ly\b", re.I),
}

INDUSTRIAS = {
    "software": {9, 42},
    "comida": {29, 30},
    "bebidas": {32},
    "alcohol": {33},
    "mineria_constr": {6, 37, 40},
    "energia": {4, 39},
    "moda": {25},
    "farma": {5},
    "educacion": {41},
    "retail_publicidad": {35},
    "finanzas": {36},
    "gastronomia_hoteles": {43},
}

nombres = df["brand_name"].astype(str)

df["n_chars"] = nombres.str.len()
df["n_words"] = nombres.apply(lambda s: len(s.split()))
print("clasificando idioma (cachea tokens)...")
df["idioma"] = nombres.apply(clasificar_nombre)

for afijo, rx in AFIJOS.items():
    df[f"af_{afijo}"] = nombres.str.contains(rx)

df["es_chileno"] = df["applicant_country"] == "CL"


# Verificado contra registration_number: Caducado = registro que no se renovó
# (100% tiene nº de registro); Vencida = solicitud que expiró sin registrarse (0%).
OUTCOME_MAP = {
    "Registrada": "registrada",
    "Caducado": "registrada",
    "Denegada": "rechazada",
    "Abandonada": "abandonada",
    "Desistida": "abandonada",
    "Vencida": "abandonada",
    "En Trámite": "en_tramite",
}


def outcome(s):
    if pd.isna(s):
        return "otro"
    return OUTCOME_MAP.get(str(s).strip(), "otro")


df["outcome"] = df["status"].apply(outcome)

fy = pd.to_datetime(df["filing_date"], errors="coerce").dt.year
df["filing_year"] = fy.fillna(df["year"]).astype(int)

for ind, cls in INDUSTRIAS.items():
    df[f"ind_{ind}"] = df["niza_classes"].apply(
        lambda l: bool(cls & set(l)) if l is not None and len(l) else False)

out = ROOT / "data" / "features.parquet"
df.to_parquet(out, index=False)
print(f"Listo: {len(df)} filas -> {out}")
print("\nidioma:")
print(df["idioma"].value_counts().to_string())
print("\noutcome:")
print(df["outcome"].value_counts().to_string())
