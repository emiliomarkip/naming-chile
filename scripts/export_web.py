"""
Genera web/data.js con todos los agregados que consume la SPA.

Uso: .venv/bin/python scripts/export_web.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
WEB.mkdir(exist_ok=True)

df = pd.read_parquet(ROOT / "data" / "features.parquet")
df = df[(df["filing_year"] >= 2009) & (df["filing_year"] <= 2026)]

AGG = ROOT / "data" / "agg"
data = {name.stem: json.loads(name.read_text()) for name in AGG.glob("*.json")}

INDUSTRIAS_ES = {
    "software": "Software y tecnología",
    "comida": "Alimentos",
    "bebidas": "Bebidas",
    "alcohol": "Vinos y licores",
    "mineria_constr": "Minería y construcción",
    "energia": "Energía y transporte",
    "moda": "Moda y vestuario",
    "farma": "Farmacéutica",
    "educacion": "Educación y cultura",
    "retail_publicidad": "Retail y publicidad",
    "finanzas": "Finanzas y seguros",
    "gastronomia_hoteles": "Gastronomía y hoteles",
}
data["industrias"] = INDUSTRIAS_ES

# --- rechazo por industria × año (solo resueltos) ---
res = df[df["outcome"].isin(["registrada", "rechazada", "abandonada"])].copy()
res["fracaso"] = res["outcome"] != "registrada"
rz = {}
for ind in INDUSTRIAS_ES:
    sub = res[res[f"ind_{ind}"]]
    g = sub.groupby("filing_year")["fracaso"].agg(["mean", "size"])
    rz[ind] = {int(y): [round(100 * r["mean"], 1), int(r["size"])]
               for y, r in g.iterrows()}
data["rechazo_industria_anio"] = rz

# --- fracaso CL vs extranjeros (resueltos <=2023) ---
r23 = res[res["filing_year"] <= 2023]
data["fracaso_nacionalidad"] = {
    "chilenos": round(100 * r23[r23["es_chileno"]]["fracaso"].mean(), 1),
    "extranjeros": round(100 * r23[~r23["es_chileno"]]["fracaso"].mean(), 1),
}

# --- ejemplos de nombres por industria × año (para el explorador) ---
ej = {}
dfs = df[df["n_chars"].between(4, 22)]
for ind in INDUSTRIAS_ES:
    sub = dfs[dfs[f"ind_{ind}"] & (dfs["outcome"] == "registrada")]
    ej[ind] = {}
    for y, g in sub.groupby("filing_year"):
        n = min(10, len(g))
        ej[ind][int(y)] = g["brand_name"].sample(n, random_state=42).tolist()
data["ejemplos"] = ej

# --- totales para el hero ---
data["meta"] = {
    "total": int(len(df)),
    "anios": [2009, 2026],
    "pct_chilenos_total": round(100 * df["es_chileno"].mean(), 1),
}

out = WEB / "data.js"
out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";",
               encoding="utf-8")
print(f"Listo: {out} ({out.stat().st_size/1e3:.0f} KB)")
