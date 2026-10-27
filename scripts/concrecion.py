"""
Concreción de las palabras del naming: ¿los nombres se volvieron más abstractos?

Método (transferencia cross-lingüe):
  1. Normas de concreción de Brysbaert et al. (2014): 40 mil palabras en inglés
     puntuadas de 1 (abstracto) a 5 (concreto) por hablantes.
  2. Regresión ridge embedding(384d) -> puntaje, entrenada sobre ~15 mil
     palabras inglesas; validación cruzada reporta r de Pearson.
  3. Como el modelo de embeddings es multilingüe (es/en alineados), se predice
     el puntaje para las palabras del léxico de naming en español e inglés.
     Se excluyen tokens inventados, siglas y números (no tienen referente).

Salidas:
  data/lexico_conc.parquet         (token, conc)
  data/agg/lexico_concrecion.json  (densidades por lista, bandas salieron/entraron)

Uso: .venv/bin/python scripts/concrecion.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import cross_val_predict

from emb_util import embed

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
SEED = 7

# ---------- 1. normas ----------
bry = pd.read_csv(ROOT / "data" / "raw" / "brysbaert_concreteness.txt", sep="\t")
bry = bry[(bry["Bigram"] == 0) & (bry["Percent_known"] >= 0.9)]
bry = bry[bry["Word"].astype(str).str.fullmatch(r"[a-z]+").fillna(False)]
bry = bry.sample(n=min(16000, len(bry)), random_state=SEED)
print(f"normas: {len(bry)} palabras inglesas")

# ---------- 2. regresión ----------
X = embed(bry["Word"].tolist())
y = bry["Conc.M"].values
model = RidgeCV(alphas=np.logspace(-2, 2, 9))
pred = cross_val_predict(model, X, y, cv=5)
r = np.corrcoef(pred, y)[0, 1]
mae = np.abs(pred - y).mean()
print(f"validación cruzada 5-fold: r = {r:.3f}, MAE = {mae:.3f}")
model.fit(X, y)
print("alpha:", model.alpha_)

# sanity check cross-lingüe
chequeo = ["mesa", "pan", "perro", "zapato", "ladrillo", "cerveza",
           "justicia", "gestion", "calidad", "estrategia", "libertad", "siempre",
           "table", "bread", "justice", "strategy", "smart", "solutions"]
pc = model.predict(embed(chequeo))
print("chequeo:", ", ".join(f"{w}={v:.2f}" for w, v in zip(chequeo, pc)))

# ---------- 3. predicción sobre el léxico ----------
tok = pd.read_parquet(ROOT / "data" / "lexico_tokens.parquet")
sem = pd.read_parquet(ROOT / "data" / "lexico_sem.parquet")[["token", "categoria"]]
tok = tok.merge(sem, on="token", how="left")
# solo palabras con referente léxico: fuera marcas-casa (Falabella), inventadas, siglas y números
con_sentido = tok[tok["idioma"].isin(["es", "en", "ambiguo"])
                  & ~tok["categoria"].isin(["corporativo", "fantasia", "sigla"])].copy()
con_sentido["conc"] = np.clip(model.predict(embed(con_sentido["token"].tolist())), 1, 5).round(3)
con_sentido[["token", "conc"]].to_parquet(ROOT / "data" / "lexico_conc.parquet", index=False)
print(f"\npuntuadas: {len(con_sentido)} de {len(tok)} tokens "
      f"({100*len(con_sentido)/len(tok):.1f}%; el resto son marcas-casa, inventados, siglas o números)")

# ---------- 4. agregados ----------
def kde(vals, w, bw=0.18, grid=np.linspace(1, 5, 81)):
    vals, w = np.asarray(vals), np.asarray(w, dtype=float)
    w = w / w.sum()
    d = np.exp(-0.5 * ((grid[:, None] - vals[None, :]) / bw) ** 2)
    return (d * w[None, :]).sum(1) / (bw * np.sqrt(2 * np.pi))


UMBRAL = 0.15
lista_a = con_sentido[con_sentido.rate_a >= UMBRAL]
lista_b = con_sentido[con_sentido.rate_b >= UMBRAL]
grid = np.linspace(1, 5, 81)
dens = {
    "grid": [round(float(g), 2) for g in grid],
    "a": [round(float(v), 4) for v in kde(lista_a.conc, lista_a.rate_a)],
    "b": [round(float(v), 4) for v in kde(lista_b.conc, lista_b.rate_b)],
}
mean_a = float(np.average(lista_a.conc, weights=lista_a.rate_a))
mean_b = float(np.average(lista_b.conc, weights=lista_b.rate_b))
muy_conc_a = float(lista_a[lista_a.conc >= 4].rate_a.sum() / lista_a.rate_a.sum())
muy_conc_b = float(lista_b[lista_b.conc >= 4].rate_b.sum() / lista_b.rate_b.sum())
print(f"\nconcreción media (ponderada por menciones): lista 2009 {mean_a:.2f} → lista 2025 {mean_b:.2f}")
print(f"menciones muy concretas (≥4): {100*muy_conc_a:.1f}% → {100*muy_conc_b:.1f}%")

# bandas 1–5 cada 0.5 para salieron vs entraron (cuenta de palabras + top palabras)
bins = np.arange(1, 5.01, 0.5)
bandas = []
sal = con_sentido[con_sentido.status == "salieron"]
ent = con_sentido[con_sentido.status == "entraron"]
for lo, hi in zip(bins[:-1], bins[1:]):
    s = sal[(sal.conc >= lo) & (sal.conc < hi + (0.001 if hi == 5 else 0))]
    e = ent[(ent.conc >= lo) & (ent.conc < hi + (0.001 if hi == 5 else 0))]
    bandas.append({
        "lo": float(lo), "hi": float(hi),
        "pct_salieron": round(100 * len(s) / len(sal), 1),
        "pct_entraron": round(100 * len(e) / len(ent), 1),
        "salieron": s.sort_values("rate_a", ascending=False).token.tolist(),
        "entraron": e.sort_values("rate_b", ascending=False).token.tolist(),
    })
    print(f"[{lo:.1f}–{hi:.1f}] salieron {bandas[-1]['pct_salieron']:5.1f}%  entraron {bandas[-1]['pct_entraron']:5.1f}%"
          f"   | sal: {', '.join(bandas[-1]['salieron'][:6])}  | ent: {', '.join(bandas[-1]['entraron'][:6])}")

# las más concretas / abstractas de cada lista (para texto)
extremos = {
    "concretas_a": lista_a.sort_values("conc", ascending=False).head(30).token.tolist(),
    "concretas_b": lista_b.sort_values("conc", ascending=False).head(30).token.tolist(),
    "abstractas_a": lista_a.sort_values("conc").head(30).token.tolist(),
    "abstractas_b": lista_b.sort_values("conc").head(30).token.tolist(),
}
out = {"r_cv": round(float(r), 3), "mae_cv": round(float(mae), 3), "n_normas": int(len(bry)),
       "n_puntuadas": int(len(con_sentido)), "n_tokens": int(len(tok)),
       "media_a": round(mean_a, 3), "media_b": round(mean_b, 3),
       "muy_conc_a": round(100 * muy_conc_a, 1), "muy_conc_b": round(100 * muy_conc_b, 1),
       "densidad": dens, "bandas": bandas, "extremos": extremos,
       "chequeo": {w: round(float(v), 2) for w, v in zip(chequeo, pc)}}
(AGG / "lexico_concrecion.json").write_text(json.dumps(out, ensure_ascii=False))
print("\nListo -> data/lexico_conc.parquet, data/agg/lexico_concrecion.json")
