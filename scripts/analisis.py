"""
Agregaciones para la narrativa: idioma, largo, afijos, nacionalidad y
tasa de rechazo por año × industria. Imprime reporte y deja JSONs en data/agg/.

Uso: .venv/bin/python scripts/analisis.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
AGG.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(ROOT / "data" / "features.parquet")
df = df[(df["filing_year"] >= 2009) & (df["filing_year"] <= 2026)]

INDUSTRIAS = [c[4:] for c in df.columns if c.startswith("ind_")]
AFIJOS = [c[3:] for c in df.columns if c.startswith("af_")]
IDIOMAS = ["es", "en", "inventado", "mixto", "sigla"]


def guardar(nombre, obj):
    (AGG / f"{nombre}.json").write_text(json.dumps(obj, ensure_ascii=False))
    print(f"  -> data/agg/{nombre}.json")


def pct(x, n=1):
    return round(100 * x, n)


# ---------- 1. idioma por año (total y por industria) ----------
print("\n===== 1. IDIOMA POR AÑO (total) =====")
tab = (df.groupby("filing_year")["idioma"].value_counts(normalize=True)
         .unstack().fillna(0)[IDIOMAS])
print((tab * 100).round(1).to_string())

serie = {i: {int(y): pct(tab.loc[y, i]) for y in tab.index} for i in IDIOMAS}
guardar("idioma_total", serie)

idioma_ind = {}
for ind in INDUSTRIAS:
    sub = df[df[f"ind_{ind}"]]
    t = (sub.groupby("filing_year")["idioma"].value_counts(normalize=True)
           .unstack().fillna(0).reindex(columns=IDIOMAS, fill_value=0))
    idioma_ind[ind] = {i: {int(y): pct(t.loc[y, i]) for y in t.index} for i in IDIOMAS}
guardar("idioma_por_industria", idioma_ind)

print("\n--- inglés + inventado por industria, 2009 vs 2025 ---")
for ind in INDUSTRIAS:
    d = idioma_ind[ind]
    v09 = d["en"].get(2009, 0) + d["inventado"].get(2009, 0)
    v25 = d["en"].get(2025, 0) + d["inventado"].get(2025, 0)
    print(f"{ind:20s} {v09:5.1f}% -> {v25:5.1f}%")

# ---------- 2. largo por año ----------
print("\n===== 2. LARGO DEL NOMBRE =====")
largo = df.groupby("filing_year").agg(chars=("n_chars", "mean"),
                                      words=("n_words", "mean")).round(2)
print(largo.to_string())
guardar("largo_total", {
    "chars": {int(y): round(v, 2) for y, v in largo["chars"].items()},
    "words": {int(y): round(v, 2) for y, v in largo["words"].items()},
})

largo_ind = {}
for ind in INDUSTRIAS:
    sub = df[df[f"ind_{ind}"]]
    g = sub.groupby("filing_year").agg(chars=("n_chars", "mean"),
                                       words=("n_words", "mean"))
    largo_ind[ind] = {
        "chars": {int(y): round(v, 2) for y, v in g["chars"].items()},
        "words": {int(y): round(v, 2) for y, v in g["words"].items()},
    }
guardar("largo_por_industria", largo_ind)

# ---------- 3. afijos por año ----------
print("\n===== 3. AFIJOS DE MODA (por 1.000 marcas) =====")
af = df.groupby("filing_year")[[f"af_{a}" for a in AFIJOS]].mean() * 1000
af.columns = AFIJOS
print(af.round(1).to_string())
guardar("afijos", {a: {int(y): round(v, 2) for y, v in af[a].items()} for a in AFIJOS})

# ---------- 4. chilenos vs extranjeros ----------
print("\n===== 4. CHILENOS VS EXTRANJEROS =====")
mix = df.groupby("filing_year")["es_chileno"].mean()
print("% solicitudes de chilenos por año:")
print((mix * 100).round(1).to_string())
guardar("pct_chilenos", {int(y): pct(v) for y, v in mix.items()})

nac_idioma = {}
for quien, mask in [("chilenos", df["es_chileno"]), ("extranjeros", ~df["es_chileno"])]:
    t = (df[mask].groupby("filing_year")["idioma"].value_counts(normalize=True)
           .unstack().fillna(0).reindex(columns=IDIOMAS, fill_value=0))
    nac_idioma[quien] = {i: {int(y): pct(t.loc[y, i]) for y in t.index} for i in IDIOMAS}
guardar("idioma_por_nacionalidad", nac_idioma)
print("\nidioma chilenos 2025:",
      {i: nac_idioma["chilenos"][i].get(2025) for i in IDIOMAS})
print("idioma extranjeros 2025:",
      {i: nac_idioma["extranjeros"][i].get(2025) for i in IDIOMAS})

# ---------- 5. tasa de rechazo (solo casos resueltos, 2009-2023) ----------
print("\n===== 5. TASA DE RECHAZO POR ESTILO (resueltos 2009-2023) =====")
res = df[(df["outcome"].isin(["registrada", "rechazada", "abandonada"]))
         & (df["filing_year"] <= 2023)].copy()
res["fracaso"] = res["outcome"] != "registrada"

print("\npor idioma (% denegada, % no registrada):")
t = res.groupby("idioma").agg(n=("fracaso", "size"),
                              denegada=("outcome", lambda s: (s == "rechazada").mean()),
                              fracaso=("fracaso", "mean"))
t[["denegada", "fracaso"]] = (t[["denegada", "fracaso"]] * 100).round(1)
print(t.to_string())
guardar("rechazo_por_idioma", t.reset_index().to_dict(orient="records"))

print("\npor nº de palabras:")
res["palabras"] = res["n_words"].clip(upper=6)
t = res.groupby("palabras").agg(n=("fracaso", "size"), fracaso=("fracaso", "mean"))
t["fracaso"] = (t["fracaso"] * 100).round(1)
print(t.to_string())
guardar("rechazo_por_palabras", t.reset_index().to_dict(orient="records"))

print("\nchilenos vs extranjeros:")
t = res.groupby("es_chileno").agg(n=("fracaso", "size"),
                                  denegada=("outcome", lambda s: (s == "rechazada").mean()),
                                  fracaso=("fracaso", "mean"))
t[["denegada", "fracaso"]] = (t[["denegada", "fracaso"]] * 100).round(1)
print(t.to_string())

print("\npor industria:")
rows = []
for ind in INDUSTRIAS:
    sub = res[res[f"ind_{ind}"]]
    rows.append({"industria": ind, "n": len(sub),
                 "fracaso": pct(sub["fracaso"].mean())})
t = pd.DataFrame(rows).sort_values("fracaso", ascending=False)
print(t.to_string(index=False))
guardar("rechazo_por_industria", t.to_dict(orient="records"))

# ---------- 6. volumen por industria × año ----------
vol = {ind: {int(y): int(v) for y, v in
             df[df[f"ind_{ind}"]].groupby("filing_year").size().items()}
       for ind in INDUSTRIAS}
vol["total"] = {int(y): int(v) for y, v in df.groupby("filing_year").size().items()}
guardar("volumen", vol)

print("\nListo.")
