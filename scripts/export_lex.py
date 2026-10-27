"""
Genera web/data_lex.js (window.LEX) con todo lo que consume la historia
"Del banco a la panadería": listas por época, cintas semánticas, anillos de
alcance, concreción, partes de la oración y el explorador de palabras.

Uso: .venv/bin/python scripts/export_lex.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
WEB = ROOT / "web"

eras = json.loads((AGG / "lexico_eras.json").read_text())
sem = json.loads((AGG / "lexico_semantica.json").read_text())
conc = json.loads((AGG / "lexico_concrecion.json").read_text())
pos = json.loads((AGG / "lexico_pos.json").read_text())

tok = pd.DataFrame(eras["tokens"])
tok = tok.merge(pd.read_parquet(ROOT / "data" / "lexico_sem.parquet")[["token", "categoria", "alcance", "top_titular"]], on="token")
tok = tok.merge(pd.read_parquet(ROOT / "data" / "lexico_conc.parquet"), on="token", how="left")
tok = tok.merge(pd.read_parquet(ROOT / "data" / "lexico_pos.parquet")[["token", "pos"]], on="token", how="left")
tok["conc"] = tok["conc"].round(2)

# ---------- explorador: una fila compacta por palabra ----------
def fila(r):
    return {
        "w": r.token, "s": r.status, "a": round(r.rate_a, 2), "b": round(r.rate_b, 2),
        "c": r.categoria, "k": r.alcance, "p": r.pos if isinstance(r.pos, str) else "otro",
        "q": None if pd.isna(r.conc) else float(r.conc),
        "i": r.idioma, "y": [round(v, 1) for v in r.serie],
        "ea": list(r.ej_a)[:3], "eb": list(r.ej_b)[:3],
        "t": (r.top_titular or "")[5:40].title() if r.categoria == "corporativo" and isinstance(r.top_titular, str) else None,
    }

palabras = [fila(r) for r in tok.sort_values(["rate_b", "rate_a"], ascending=False).itertuples()]

# ---------- iconos para la narrativa: top por status ----------
def top(status, col, n=40, extra=None):
    sub = tok[tok.status == status]
    if extra is not None:
        sub = sub[extra(sub)]
    return sub.sort_values(col, ascending=False).token.head(n).tolist()

no_corp = lambda d: d.categoria != "corporativo"   # noqa: E731
iconos = {
    "salieron": top("salieron", "rate_a"),
    "salieron_sin_corp": top("salieron", "rate_a", extra=no_corp),
    "entraron": top("entraron", "rate_b"),
    "entraron_sin_corp": top("entraron", "rate_b", extra=no_corp),
    "corp_salieron": top("salieron", "rate_a", 30, extra=lambda d: d.categoria == "corporativo"),
    "corp_entraron": top("entraron", "rate_b", 20, extra=lambda d: d.categoria == "corporativo"),
}
perm = tok[tok.status == "permanecen"].copy()
perm["delta"] = perm.rate_b - perm.rate_a
perm["ratio"] = perm.rate_b / perm.rate_a
iconos["suben"] = [{"w": r.token, "a": round(r.rate_a, 2), "b": round(r.rate_b, 2)}
                   for r in perm.sort_values("delta", ascending=False).head(20).itertuples()]
iconos["bajan"] = [{"w": r.token, "a": round(r.rate_a, 2), "b": round(r.rate_b, 2)}
                   for r in perm.sort_values("delta").head(20).itertuples()]

# ---------- palabras para el campo de fondo del intro ----------
rng = np.random.default_rng(11)
def muestra(status, n):
    sub = tok[(tok.status == status) & (tok.token.str.len().between(3, 12)) & (tok.idioma != "numero")]
    sub = sub[sub.categoria != "gramatica"]
    sub = sub.sort_values("rate_a" if status == "salieron" else "rate_b", ascending=False).head(220)
    return [{"w": w, "s": status} for w in rng.choice(sub.token.tolist(), size=min(n, len(sub)), replace=False)]
fondo = muestra("permanecen", 70) + muestra("salieron", 55) + muestra("entraron", 55)
rng.shuffle(fondo)

# ---------- por categoría: palabras que entraron/salieron para los pasos ----------
cats = {}
for c in sem["categorias"]:
    sub = tok[tok.categoria == c["id"]]
    cats[c["id"]] = {
        "label": c["label"], "a": c["a"], "b": c["b"], "n_a": c["n_a"], "n_b": c["n_b"],
        "salieron": sub[sub.status == "salieron"].sort_values("rate_a", ascending=False).token.head(12).tolist(),
        "entraron": sub[sub.status == "entraron"].sort_values("rate_b", ascending=False).token.head(12).tolist(),
        "permanecen": sub[sub.status == "permanecen"].sort_values("rate_b", ascending=False).token.head(12).tolist(),
    }

# ---------- POS: palabras por tipo para el muro ----------
pos_words = {}
for p in ["adjetivo", "verbo", "adverbio"]:
    sub = tok[tok.pos == p]
    pos_words[p] = {
        "entraron": sub[sub.status == "entraron"].sort_values("rate_b", ascending=False).token.tolist(),
        "salieron": sub[sub.status == "salieron"].sort_values("rate_a", ascending=False).token.tolist(),
        "permanecen": sub[sub.status == "permanecen"].sort_values("rate_b", ascending=False).token.tolist(),
    }

out = {
    "meta": eras["meta"],
    "palabras": palabras,
    "iconos": iconos,
    "fondo": fondo,
    "categorias": sem["categorias"],
    "cats": cats,
    "alcances": sem["alcances"],
    "labels": sem["labels"],
    "scope_labels": sem["scope_labels"],
    "concrecion": {k: v for k, v in conc.items() if k != "chequeo"},
    "pos": pos,
    "pos_words": pos_words,
}
dest = WEB / "data_lex.js"
dest.write_text("window.LEX = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";", encoding="utf-8")
print(f"Listo: {dest} ({dest.stat().st_size/1e3:.0f} KB) — {len(palabras)} palabras")
print("suben:", [d['w'] for d in iconos['suben'][:12]])
print("bajan:", [d['w'] for d in iconos['bajan'][:12]])
print("salieron sin corp:", iconos["salieron_sin_corp"][:25])
print("entraron sin corp:", iconos["entraron_sin_corp"][:25])
