"""
Léxico esencial del naming chileno en dos épocas — la "lista 2009" y la
"lista 2025" (inspirado en la comparación GSL 1953 vs NGSL 2023).

Época A = solicitudes 2009–2011; Época B = 2023–2025.
Para cada época, el léxico esencial son los tokens que aparecen en al menos
UMBRAL marcas por cada 1.000 solicitudes de la época. Cada token queda como
  permanecen  — está en ambas listas
  salieron    — solo en la lista 2009
  entraron    — solo en la lista 2025

Salidas:
  data/lexico_tokens.parquet          (tabla token × métricas, para scripts siguientes)
  data/agg/lexico_eras.json           (resumen + tokens con series anuales y ejemplos)

Uso: .venv/bin/python scripts/lexico_eras.py
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
AGG.mkdir(parents=True, exist_ok=True)

ERA_A = (2009, 2011)
ERA_B = (2023, 2025)
UMBRAL = 0.15          # marcas por 1.000 solicitudes de la época (≈20 marcas)
ANIOS = list(range(2009, 2026))

TOK = re.compile(r"[a-z0-9ñ]+")
# palabras funcionales + sufijos societarios + tokens web: no son vocabulario de naming
STOP = set("""
de la del el los las en tu tus para con por al lo que es y e a o u un una unos unas
mi mis su sus se le les nos ni si sin sobre entre hacia desde hasta como mas
the of and for in on to by at your my a an is it as or from with its this that
spa ltda limitada sa sac eirl inc llc corp co ltd sociedad empresa empresas cia
com www http https cl net org
""".split())
# tokens de 2 letras que sí son vocabulario (siglas con significado propio)
DOS_LETRAS_OK = {"ai", "ia", "tv", "3d", "hd", "4k", "5g", "ok", "go", "it", "pc", "rx", "dj", "ia"}


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokens(nombre):
    out = []
    for t in TOK.findall(norm(nombre)):
        if t in STOP:
            continue
        if len(t) < 2 or (len(t) == 2 and t not in DOS_LETRAS_OK and not t.isdigit()):
            continue
        out.append(t)
    return out


_cache = {}


def idioma_token(t):
    """es / en / ambiguo / inventado / numero (misma regla que features.py)."""
    if t in _cache:
        return _cache[t]
    if t.isdigit():
        r = "numero"
    else:
        es, en = zipf_frequency(t, "es"), zipf_frequency(t, "en")
        if es < 2.0 and en < 2.0:
            r = "inventado"
        elif es >= en + 0.5:
            r = "es"
        elif en >= es + 0.5:
            r = "en"
        else:
            r = "ambiguo"
    _cache[t] = r
    return r


def main():
    df = pd.read_parquet(ROOT / "data" / "features_ling.parquet",
                         columns=["brand_name", "filing_year", "outcome", "es_chileno",
                                  "n_chars", "categoria", "ind_software"])
    df = df[df["filing_year"].between(ANIOS[0], ANIOS[-1])].copy()
    df["toks"] = df["brand_name"].map(lambda s: sorted(set(tokens(s))))
    print(f"{len(df)} marcas 2009–2025")

    n_anio = df.groupby("filing_year").size().to_dict()
    freq_anio = {y: Counter() for y in ANIOS}
    for y, g in df.groupby("filing_year"):
        c = freq_anio[int(y)]
        for ts in g["toks"]:
            c.update(ts)

    def rate_span(t, span):
        ys = range(span[0], span[1] + 1)
        num = sum(freq_anio[y].get(t, 0) for y in ys)
        den = sum(n_anio[y] for y in ys)
        return 1000 * num / den

    nA = sum(n_anio[y] for y in range(ERA_A[0], ERA_A[1] + 1))
    nB = sum(n_anio[y] for y in range(ERA_B[0], ERA_B[1] + 1))
    univ = set()
    for y in list(range(ERA_A[0], ERA_A[1] + 1)) + list(range(ERA_B[0], ERA_B[1] + 1)):
        univ |= set(freq_anio[y])

    rows = []
    for t in univ:
        ra, rb = rate_span(t, ERA_A), rate_span(t, ERA_B)
        inA, inB = ra >= UMBRAL, rb >= UMBRAL
        if not (inA or inB):
            continue
        status = "permanecen" if (inA and inB) else ("salieron" if inA else "entraron")
        rows.append({"token": t, "rate_a": round(ra, 3), "rate_b": round(rb, 3),
                     "status": status, "idioma": idioma_token(t),
                     "serie": [round(1000 * freq_anio[y].get(t, 0) / n_anio[y], 2) for y in ANIOS]})
    tok = pd.DataFrame(rows).sort_values(["status", "rate_a", "rate_b"], ascending=[True, False, False])
    print("\n== tamaño de las listas ==")
    lista_a = tok[tok.rate_a >= UMBRAL]
    lista_b = tok[tok.rate_b >= UMBRAL]
    print(f"lista 2009 (2009–11): {len(lista_a)} palabras | lista 2025 (2023–25): {len(lista_b)} palabras")
    print(tok["status"].value_counts().to_string())
    print("\nidioma × status:")
    print(pd.crosstab(tok["idioma"], tok["status"]).to_string())

    # cobertura: % de marcas de la época con ≥1 palabra de su lista
    setA, setB = set(lista_a.token), set(lista_b.token)
    A = df[df.filing_year.between(*ERA_A)]
    B = df[df.filing_year.between(*ERA_B)]
    covA = A["toks"].map(lambda ts: bool(set(ts) & setA)).mean()
    covB = B["toks"].map(lambda ts: bool(set(ts) & setB)).mean()
    sinA = A["toks"].map(len).eq(0).mean()
    sinB = B["toks"].map(len).eq(0).mean()
    print(f"\ncobertura lista 2009 sobre marcas 2009–11: {100*covA:.1f}%  (sin tokens útiles: {100*sinA:.1f}%)")
    print(f"cobertura lista 2025 sobre marcas 2023–25: {100*covB:.1f}%  (sin tokens útiles: {100*sinB:.1f}%)")

    # ejemplos de marcas por token (registradas, cortas), por época
    ej = defaultdict(lambda: {"a": [], "b": []})
    for era, sub in [("a", A), ("b", B)]:
        sub = sub[(sub["outcome"] == "registrada") & sub["n_chars"].between(4, 26)]
        sub = sub.sample(frac=1, random_state=3)
        for name, ts in zip(sub["brand_name"], sub["toks"]):
            for t in ts:
                lst = ej[t][era]
                if len(lst) < 3 and name not in lst:
                    lst.append(name)
    tok["ej_a"] = tok["token"].map(lambda t: ej[t]["a"])
    tok["ej_b"] = tok["token"].map(lambda t: ej[t]["b"])

    # movers dentro de las que permanecen
    perm = tok[tok.status == "permanecen"].copy()
    perm["delta"] = perm.rate_b - perm.rate_a
    print("\n== permanecen pero suben más (por 1.000) ==")
    print(perm.sort_values("delta", ascending=False).head(25)[["token", "rate_a", "rate_b"]].to_string(index=False))
    print("\n== permanecen pero bajan más ==")
    print(perm.sort_values("delta").head(25)[["token", "rate_a", "rate_b"]].to_string(index=False))
    print("\n== salieron (top por rate 2009) ==")
    print(", ".join(tok[tok.status == "salieron"].sort_values("rate_a", ascending=False).head(60).token))
    print("\n== entraron (top por rate 2025) ==")
    print(", ".join(tok[tok.status == "entraron"].sort_values("rate_b", ascending=False).head(60).token))

    tok.to_parquet(ROOT / "data" / "lexico_tokens.parquet", index=False)
    out = {
        "meta": {"era_a": list(ERA_A), "era_b": list(ERA_B), "umbral": UMBRAL,
                 "n_a": int(nA), "n_b": int(nB),
                 "lista_a": int(len(lista_a)), "lista_b": int(len(lista_b)),
                 "permanecen": int((tok.status == "permanecen").sum()),
                 "salieron": int((tok.status == "salieron").sum()),
                 "entraron": int((tok.status == "entraron").sum()),
                 "cobertura_a": round(100 * covA, 1), "cobertura_b": round(100 * covB, 1),
                 "anios": ANIOS},
        "tokens": tok.to_dict(orient="records"),
    }
    (AGG / "lexico_eras.json").write_text(json.dumps(out, ensure_ascii=False))
    print(f"\nListo -> data/lexico_tokens.parquet, data/agg/lexico_eras.json ({len(tok)} tokens)")


if __name__ == "__main__":
    main()
