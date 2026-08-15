"""
Deep-dive léxico de marcas tecnológicas (clases de Niza 9 y 42).

Genera data/agg/tech_deepdive.json con:
  top_palabras: top 22 tokens por 1.000 marcas en 2009 / 2019 / 2025 (con flag "nueva")
  movers: palabras que más subieron/bajaron (2009-11 vs 2023-25, por 1.000)
  olas: series anuales por 1.000 de las palabras-ola (web, digital, app, cloud, data, ai…)
  campos: series anuales de campos semánticos (% de marcas que tocan cada campo)
  morfo: series de morfología (largo, % 1 palabra, % con dígito, % .cl)
  ia_ejemplos: marcas recientes con ai/ia en el nombre

Uso: .venv/bin/python scripts/deepdive_tech.py
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"

df = pd.read_parquet(ROOT / "data" / "features_ling.parquet")
tech = df[df["ind_software"] & df["filing_year"].between(2009, 2026)].copy()
print(f"marcas tech: {len(tech)}")


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


TOKEN_RE = re.compile(r"[a-z0-9ñ]+")
STOP = set("""
de la el los las del y en por para con su sus un una al lo se tu tus mi mas
the of and for in on to by at your my a an is it as or
spa ltda limitada sa sac eirl inc llc corp co ltd sociedad empresa empresas
com www http https
""".split())

tech["toks"] = tech["brand_name"].map(lambda s: [t for t in TOKEN_RE.findall(norm(s))
                                                 if len(t) >= 2 and t not in STOP])

# ---------- frecuencia por año (presencia por marca, por 1.000) ----------
anios = sorted(tech["filing_year"].unique())
n_por_anio = tech.groupby("filing_year").size().to_dict()
freq = {}  # {year: Counter}
for y, g in tech.groupby("filing_year"):
    c = Counter()
    for toks in g["toks"]:
        c.update(set(toks))
    freq[int(y)] = c


def rate(tok, y):
    return 1000 * freq[y].get(tok, 0) / n_por_anio[y]


def rate_span(tok, ys):
    num = sum(freq[y].get(tok, 0) for y in ys)
    den = sum(n_por_anio[y] for y in ys)
    return 1000 * num / den


# ---------- top palabras 2009 / 2019 / 2025 ----------
ERAS = [2009, 2019, 2025]
top_palabras = {}
top09 = {t for t, _ in freq[2009].most_common(60)}
for y in ERAS:
    top = freq[y].most_common(22)
    top_palabras[y] = [{"w": t, "r": round(1000 * n / n_por_anio[y], 1),
                        "nueva": (y != 2009 and t not in top09)}
                       for t, n in top]
    print(f"\n== top {y} ==")
    print(", ".join(f"{d['w']}({d['r']})" + ("*" if d["nueva"] else "") for d in top_palabras[y]))

# ---------- movers 2009-11 vs 2023-25 ----------
A, B = [2009, 2010, 2011], [2023, 2024, 2025]
univ = {t for y in A + B for t, n in freq[y].items()}
movers = []
for t in univ:
    ra, rb = rate_span(t, A), rate_span(t, B)
    tot = sum(freq[y].get(t, 0) for y in A + B)
    if tot < 60:
        continue
    movers.append({"w": t, "a": round(ra, 1), "b": round(rb, 1), "d": round(rb - ra, 1)})
movers.sort(key=lambda m: m["d"])
bajan = movers[:12]
suben = sorted(movers, key=lambda m: -m["d"])[:12]
print("\n== suben ==")
print(", ".join(f"{m['w']} {m['a']}→{m['b']}" for m in suben))
print("== bajan ==")
print(", ".join(f"{m['w']} {m['a']}→{m['b']}" for m in bajan))

# ---------- olas tecnológicas ----------
OLAS = ["web", "digital", "app", "cloud", "data", "ai", "smart", "net", "soft", "tec", "chile"]
olas = {w: {int(y): round(rate(w, y), 1) for y in anios} for w in OLAS}
# ai incluye token "ia" (español)
olas["ai"] = {int(y): round(rate("ai", y) + rate("ia", y), 1) for y in anios}

# ---------- campos semánticos ----------
CAMPOS = {
    "datos_digital": "data datos digital software cloud nube cyber ciber code codigo dev bit byte pixel online virtual net web informatica computacion sistemas plataforma".split(),
    "ia": "ai ia bot gpt neural cognitive inteligencia artificial".split(),
    "servicios_negocio": "consultores consultoria asesorias servicios gestion soluciones solutions services group business negocios ingenieria engineering".split(),
    "seguridad": "seguridad security secure guard alarma vigilancia protect proteccion safe".split(),
    "salud_bio": "salud health medic medical bio lab clinic doctor pharma dental".split(),
    "educacion": "educa academia escuela school learning aprende cursos capacitacion instituto universidad college".split(),
    "chile_lugar": "chile chileno santiago andes patagonia atacama austral sur norte".split(),
    "emocion_aspiracional": "love vida life happy feliz magic magia dream sueno smart genius pro max plus ultra super mega top star gold king power".split(),
}
campos = {}
for campo, kws in CAMPOS.items():
    kws = set(kws)
    serie = {}
    for y, g in tech.groupby("filing_year"):
        hit = g["toks"].map(lambda ts: bool(set(ts) & kws)).mean()
        serie[int(y)] = round(100 * hit, 2)
    campos[campo] = serie
    print(f"campo {campo}: 2009 {serie[2009]}% -> 2025 {serie[2025]}%")

# ---------- morfología ----------
morfo = {}
g = tech.groupby("filing_year")
morfo["chars"] = {int(y): round(v, 2) for y, v in g["n_chars"].mean().items()}
morfo["una_palabra"] = {int(y): round(100 * v, 1) for y, v in
                        g["n_words"].apply(lambda s: (s == 1).mean()).items()}
morfo["con_digito"] = {int(y): round(100 * v, 1) for y, v in
                       g["brand_name"].apply(lambda s: s.str.contains(r"\d", regex=True).mean()).items()}
morfo["punto_cl"] = {int(y): round(1000 * v, 1) for y, v in
                     g["brand_name"].apply(lambda s: s.str.contains(r"\.cl\b", case=False, regex=True).mean()).items()}

# ---------- ejemplos IA ----------
ia_mask = tech["toks"].map(lambda ts: "ai" in ts or "ia" in ts) & (tech["filing_year"] >= 2023)
ia_ej = tech[ia_mask & tech["n_chars"].between(3, 24)]["brand_name"].drop_duplicates()
ia_ejemplos = ia_ej.sample(min(14, len(ia_ej)), random_state=11).tolist()
print("\nIA ejemplos:", ia_ejemplos[:8])
print("IA por año:", {y: olas['ai'][y] for y in [2019, 2021, 2023, 2024, 2025, 2026]})

out = {"top_palabras": {str(k): v for k, v in top_palabras.items()},
       "suben": suben, "bajan": bajan, "olas": olas, "campos": campos,
       "morfo": morfo, "ia_ejemplos": ia_ejemplos,
       "n_por_anio": {int(y): int(n) for y, n in n_por_anio.items()}}
(AGG / "tech_deepdive.json").write_text(json.dumps(out, ensure_ascii=False))
print("\nListo -> data/agg/tech_deepdive.json")
