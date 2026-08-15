"""
Agregados de la taxonomía lingüística para la web -> data/agg/*.json

Uso: .venv/bin/python scripts/analisis_taxonomia.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"

CATS = ["descriptivo", "ingles", "fantasia_pura", "fantasia_comp",
        "toponimo", "mapuche", "apellido", "mixto", "sigla"]

df = pd.read_parquet(ROOT / "data" / "features_ling.parquet")
df = df[(df["filing_year"] >= 2009) & (df["filing_year"] <= 2026)]


def share_por_anio(sub):
    t = (sub.groupby("filing_year")["categoria"].value_counts(normalize=True)
         .unstack().fillna(0).reindex(columns=CATS, fill_value=0) * 100)
    return {c: {int(y): round(float(t.loc[y, c]), 2) for y in t.index} for c in CATS}


out = {"total": share_por_anio(df), "tech": share_por_anio(df[df["ind_software"]])}
(AGG / "taxonomia_anio.json").write_text(json.dumps(out))
print("taxonomia_anio.json ok")

print("\n== share total 2009 vs 2025 ==")
for c in CATS:
    print(f"{c:15s} {out['total'][c][2009]:6.2f}% -> {out['total'][c][2025]:6.2f}%")
print("\n== share TECH 2009 vs 2025 ==")
for c in CATS:
    print(f"{c:15s} {out['tech'][c][2009]:6.2f}% -> {out['tech'][c][2025]:6.2f}%")

# fracaso por categoría (resueltos 2009-2023)
res = df[df["outcome"].isin(["registrada", "rechazada", "abandonada"])
         & (df["filing_year"] <= 2023)].copy()
res["fracaso"] = res["outcome"] != "registrada"
t = res.groupby("categoria").agg(n=("fracaso", "size"), fracaso=("fracaso", "mean"))
t["fracaso"] = (t["fracaso"] * 100).round(1)
t = t.reindex(CATS).reset_index()
(AGG / "taxonomia_fracaso.json").write_text(t.to_json(orient="records"))
print("\n== fracaso por categoría ==")
print(t.to_string(index=False))

# dónde se concentran topónimos y mapuche (por industria, todo el período)
INDS = [c[4:] for c in df.columns if c.startswith("ind_")]
conc = {}
for ind in INDS:
    sub = df[df[f"ind_{ind}"]]
    conc[ind] = {
        "toponimo": round(100 * (sub["categoria"] == "toponimo").mean(), 2),
        "mapuche": round(100 * (sub["categoria"] == "mapuche").mean(), 2),
        "apellido": round(100 * (sub["categoria"] == "apellido").mean(), 2),
        "fantasia": round(100 * sub["categoria"].isin(["fantasia_pura", "fantasia_comp"]).mean(), 2),
    }
(AGG / "taxonomia_industria.json").write_text(json.dumps(conc))
print("\n== raíces locales por industria (% del total) ==")
for ind, v in sorted(conc.items(), key=lambda kv: -kv[1]["toponimo"]):
    print(f"{ind:20s} topo {v['toponimo']:5.2f}  mapu {v['mapuche']:5.2f}  apell {v['apellido']:5.2f}  fant {v['fantasia']:5.2f}")

# ejemplos para chips (registradas, chilenas, recientes)
ej = {}
base = df[(df["outcome"] == "registrada") & df["es_chileno"] & (df["filing_year"] >= 2020)
          & df["n_chars"].between(4, 24)]
for c in ["toponimo", "mapuche", "apellido", "fantasia_pura", "fantasia_comp"]:
    sub = base[base["categoria"] == c]["brand_name"].drop_duplicates()
    ej[c] = sub.sample(min(10, len(sub)), random_state=7).tolist()
(AGG / "taxonomia_ejemplos.json").write_text(json.dumps(ej, ensure_ascii=False))
print("\nejemplos ok")

# evolución mapuche en el tiempo (por 1.000, total)
m = (df.groupby("filing_year")["categoria"].apply(lambda s: (s == "mapuche").mean() * 1000))
(AGG / "mapuche_anio.json").write_text(json.dumps({int(y): round(float(v), 2) for y, v in m.items()}))
print("mapuche_anio ok:", {int(y): round(float(v), 1) for y, v in m.items() if y in (2009, 2015, 2020, 2025)})
