"""
Parte de la oración (POS) de cada palabra del léxico de naming.

Un token suelto se etiqueta mal; en cambio, dentro del nombre completo
("Panadería San José") spaCy tiene contexto. Por eso se procesan todos los
nombres de las dos épocas y cada token recibe el POS mayoritario entre sus
apariciones. Nombres en español -> es_core_news_sm; en inglés o mixtos ->
también en_core_web_sm; el voto que cuenta es el del modelo del idioma del token.

Salidas:
  data/lexico_pos.parquet        (token, pos, votos)
  data/agg/lexico_pos.json       (waffle: palabras por POS × lista × status)

Uso: .venv/bin/python scripts/pos.py
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import spacy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taxonomia import es_palabra_comun, TOPONIMOS, APELLIDOS  # noqa: E402
from wordfreq import top_n_list  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
UMBRAL = 0.15
POS_OK = {"NOUN": "sustantivo", "PROPN": "nombre_propio", "ADJ": "adjetivo",
          "VERB": "verbo", "ADV": "adverbio", "NUM": "numero"}


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


tok = pd.read_parquet(ROOT / "data" / "lexico_tokens.parquet")
lex = set(tok.token)
sem = pd.read_parquet(ROOT / "data" / "lexico_sem.parquet")[["token", "categoria"]]
categoria = dict(zip(sem.token, sem.categoria))

# INAPI escribe casi todo en MAYÚSCULAS SIN TILDES; restauramos tildes con el
# diccionario de frecuencias (pasteleria -> pastelería) para que spaCy reconozca la palabra
ACENTO = {}
for w in top_n_list("es", 300000):
    k = norm(w)
    if k != w and k not in ACENTO:
        ACENTO[k] = w
WORD_RE = re.compile(r"[a-záéíóúüñ]+", re.I)


def con_tildes(nombre):
    return WORD_RE.sub(lambda m: ACENTO.get(m.group(0), m.group(0)), str(nombre).lower())
idioma = dict(zip(tok.token, tok.idioma))

df = pd.read_parquet(ROOT / "data" / "features_ling.parquet",
                     columns=["brand_name", "filing_year", "idioma"])
df = df[df.filing_year.between(2009, 2011) | df.filing_year.between(2023, 2025)]
nombres = df.drop_duplicates("brand_name")
print(f"{len(nombres)} nombres únicos")

votos = defaultdict(Counter)   # token -> Counter(pos)


def procesar(nlp, textos, lang):
    for doc in nlp.pipe(textos, batch_size=512):
        for t in doc:
            k = norm(t.text)
            if k in lex and t.pos_ in POS_OK:
                il = idioma[k]
                # el modelo español vota por tokens es/ambiguo/inventado; el inglés por en/ambiguo
                if (lang == "es" and il != "en") or (lang == "en" and il in ("en", "ambiguo")):
                    votos[k][t.pos_] += 1


try:
    es = spacy.load("es_core_news_md", disable=["parser", "ner", "lemmatizer"])
except OSError:
    es = spacy.load("es_core_news_sm", disable=["parser", "ner", "lemmatizer"])
print("español…")
procesar(es, [con_tildes(n) for n in nombres["brand_name"]], "es")
en = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])
mix = nombres[nombres["idioma"].isin(["en", "mixto"])]
print(f"inglés… ({len(mix)} nombres)")
procesar(en, mix["brand_name"].astype(str).str.lower().tolist(), "en")

# correcciones manuales de palabras frecuentes que spaCy etiqueta mal en nombres
OVERRIDE = {
    "pro": "ADJ", "max": "ADJ", "plus": "ADJ", "super": "ADJ", "mega": "ADJ", "ultra": "ADJ",
    "smart": "ADJ", "premium": "ADJ", "top": "ADJ", "best": "ADJ", "eco": "ADJ", "bio": "ADJ",
    "express": "ADJ", "global": "ADJ", "digital": "ADJ", "natural": "ADJ", "integral": "ADJ",
    "fresh": "ADJ", "easy": "ADJ", "fast": "ADJ", "mas": "ADV", "siempre": "ADV", "hoy": "ADV",
    "aqui": "ADV", "ya": "ADV", "solo": "ADV", "ahora": "ADV", "now": "ADV", "just": "ADV",
    "only": "ADV", "online": "ADV", "live": "ADV", "go": "VERB", "ser": "VERB",
    "ingenieria": "NOUN", "gestion": "NOUN", "consulting": "NOUN", "studio": "NOUN",
    "solutions": "NOUN", "group": "NOUN", "lab": "NOUN", "labs": "NOUN", "shop": "NOUN",
    "store": "NOUN", "market": "NOUN", "food": "NOUN", "foods": "NOUN", "chile": "PROPN",
    "santiago": "PROPN", "patagonia": "PROPN", "atacama": "PROPN", "andes": "PROPN",
    "ai": "NOUN", "ia": "NOUN", "tv": "NOUN", "app": "NOUN", "spa": "NOUN",
    "dra": "NOUN", "dr": "NOUN", "mente": "NOUN", "camino": "NOUN", "impacto": "NOUN", "podcast": "NOUN",
    "favorita": "ADJ", "isapre": "NOUN", "paseo": "NOUN", "trabajo": "NOUN", "precio": "NOUN",
    "turbo": "ADJ", "tomas": "PROPN", "marco": "PROPN", "cine": "NOUN", "catolica": "PROPN",
    "est": "NOUN", "fest": "NOUN", "comida": "NOUN", "historia": "NOUN", "canal": "NOUN",
    "learning": "NOUN", "primera": "ADJ", "tattoo": "NOUN", "holly": "PROPN", "doble": "ADJ",
    "boulevard": "NOUN", "cross": "NOUN", "man": "NOUN", "zone": "NOUN", "puntos": "NOUN",
    "horas": "NOUN", "dias": "NOUN", "toda": "ADJ", "mobile": "ADJ", "touch": "NOUN",
    "camara": "NOUN", "resort": "NOUN", "minerals": "NOUN", "hospital": "NOUN", "enjoy": "VERB",
    "conecta": "VERB", "connect": "VERB", "circular": "ADJ", "glow": "VERB", "keep": "VERB",
    "pay": "VERB", "dale": "VERB", "vamos": "VERB", "burning": "VERB", "hace": "VERB",
    "consultora": "NOUN", "pontificia": "ADJ", "nativo": "ADJ", "sustentable": "ADJ",
    "consciente": "ADJ", "integrales": "ADJ", "industriales": "ADJ", "purificada": "ADJ",
    "sour": "ADJ", "safe": "ADJ", "joven": "ADJ", "roja": "ADJ", "maxima": "ADJ", "bello": "ADJ",
    "clear": "ADJ", "daily": "ADJ", "multi": "ADJ", "marina": "ADJ", "grand": "ADJ", "locos": "ADJ",
    "bicentenario": "NOUN", "melon": "NOUN", "loteria": "NOUN", "ahumada": "PROPN",
    "joyas": "NOUN", "pets": "NOUN", "protein": "NOUN", "repuestos": "NOUN", "estilo": "NOUN",
    "accesorios": "NOUN", "pilates": "NOUN", "padel": "NOUN", "aura": "NOUN", "tradicion": "NOUN",
    "since": "ADV", "aqui": "ADV", "together": "ADV", "well": "ADV", "pronto": "ADV",
    "viaje": "NOUN", "refugio": "NOUN", "hecho": "ADJ", "mate": "NOUN", "colo": "PROPN", "encanto": "NOUN",
    "alcance": "NOUN", "cumbia": "NOUN", "corte": "NOUN", "aseo": "NOUN", "amigo": "NOUN", "modular": "ADJ",
    "cambio": "NOUN", "fibra": "NOUN", "progreso": "NOUN", "sello": "NOUN", "gluten": "NOUN", "acero": "NOUN",
    "era": "NOUN", "berry": "NOUN", "bear": "NOUN", "cave": "NOUN", "hit": "NOUN", "focus": "NOUN",
    "works": "NOUN", "mejora": "NOUN", "compra": "NOUN", "born": "ADJ", "wipes": "NOUN", "smile": "VERB",
    "boost": "VERB", "emprende": "VERB", "crea": "VERB", "impulsa": "VERB", "ilumina": "VERB",
    "inspira": "VERB", "explora": "VERB", "invierte": "VERB", "ama": "VERB", "hablemos": "VERB",
    "empanadas": "NOUN", "lacteos": "NOUN", "papas": "NOUN", "dulces": "NOUN", "promo": "NOUN",
    "naranja": "NOUN", "imperio": "NOUN", "historias": "NOUN", "asesoria": "NOUN", "human": "ADJ",
    "precio": "NOUN", "turismo": "NOUN", "estampa": "NOUN", "reino": "NOUN", "gana": "VERB", "ver": "VERB",
    "raspe": "VERB", "relax": "VERB", "tenemos": "VERB", "queremos": "VERB",
    "santander": "PROPN", "zurich": "PROPN", "paul": "PROPN", "miller": "PROPN", "cobre": "NOUN",
    "suiza": "PROPN", "tomate": "NOUN", "negocio": "NOUN", "bono": "NOUN", "hola": "ADV", "mago": "NOUN",
    "leasing": "NOUN", "met": "PROPN", "vendome": "PROPN", "choco": "NOUN", "primer": "ADJ",
    "protege": "VERB", "lee": "VERB", "mueve": "VERB", "saber": "VERB", "conviene": "VERB",
    "piensa": "VERB", "actuar": "VERB", "mira": "VERB", "prevenir": "VERB", "pague": "VERB",
}


NOMBRES_PILA = set("""maria jose juan pedro pablo carlos andres diego sofia martin tomas marco antonio francisco
javier daniel david rodrigo cristian camila valentina isidora emilia josefa lucia fernando covadonga ana
luis jorge manuel miguel alejandro sebastian nicolas matias felipe ignacio vicente benjamin gabriel
paula carolina francisca catalina constanza antonia magdalena trinidad rosa carmen teresa elena laura
clara julia paz esperanza victoria gloria mercedes pilar monica patricia claudia veronica daniela""".split())
SUFIJOS_NOUN = ("oria", "orias", "ias", "eria", "cion", "sion", "dad", "tad", "ismo", "miento", "anza", "encia", "ancia",
                "logia", "teca", "ista", "ismo", "aje", "tura", "dora", "dores", "tores", "ciones",
                "erias", "dades", "mientos", "ings", "ness", "ment", "ships", "tion", "sion")
SUFIJOS_ADV = ("mente",)


def por_sufijo(t):
    if t.endswith(SUFIJOS_ADV) and len(t) > 7:
        return "adverbio"
    if t.endswith(SUFIJOS_NOUN) and len(t) > 5:
        return "sustantivo"
    return None


def pos_final(t):
    if t in OVERRIDE:
        return POS_OK[OVERRIDE[t]]
    if categoria.get(t) != "corporativo" and por_sufijo(t):
        return por_sufijo(t)
    if idioma[t] == "numero":
        return "numero"
    # marcas-casa, topónimos y apellidos son nombres propios por definición
    if categoria.get(t) == "corporativo" or t in TOPONIMOS or t in APELLIDOS or t in NOMBRES_PILA:
        return "nombre_propio"
    if idioma[t] == "inventado":
        return "inventado"
    if t in votos and votos[t]:
        v = votos[t].copy()
        # un nombre propio que además es palabra común (plaza, sol) cuenta como esa palabra
        if es_palabra_comun(t, umbral=3.5) and "PROPN" in v:
            v.pop("PROPN")
        # sustantivos deverbales (viaje, cambio, sello): el verbo solo gana con margen claro
        if v.get("VERB", 0) and v.get("VERB", 0) < 1.6 * v.get("NOUN", 0):
            v.pop("VERB")
        if v:
            p, n = v.most_common(1)[0]
            return POS_OK[p]
    return "otro"


tok["pos"] = tok["token"].map(pos_final)
tok["votos"] = tok["token"].map(lambda t: sum(votos[t].values()) if t in votos else 0)
# nombre propio sin ser lugar/apellido suele ser marca: los agrupamos con sustantivos
# para el waffle, pero conservamos la etiqueta fina.
print("\n== POS × status (palabras) ==")
print(pd.crosstab(tok["pos"], tok["status"]).to_string())
for p in ["sustantivo", "adjetivo", "verbo", "adverbio", "nombre_propio"]:
    sub = tok[tok.pos == p]
    print(f"\n{p}: salieron -> {', '.join(sub[sub.status=='salieron'].sort_values('rate_a', ascending=False).token.head(14))}")
    print(f"{p}: entraron -> {', '.join(sub[sub.status=='entraron'].sort_values('rate_b', ascending=False).token.head(14))}")

tok[["token", "pos", "votos"]].to_parquet(ROOT / "data" / "lexico_pos.parquet", index=False)

# ---------- waffle: cada cuadrado es una palabra ----------
ORDEN = ["sustantivo", "nombre_propio", "adjetivo", "verbo", "adverbio", "inventado", "otro"]
tok["pos_w"] = tok["pos"].where(tok["pos"].isin(ORDEN), "otro")
waffle = {}
for lista, col, otros in [("a", "rate_a", "salieron"), ("b", "rate_b", "entraron")]:
    sub = tok[tok[col] >= UMBRAL]
    waffle[lista] = {}
    for p in ORDEN:
        s = sub[sub.pos_w == p].sort_values(col, ascending=False)
        waffle[lista][p] = {
            "n": int(len(s)), "pct": round(100 * len(s) / len(sub), 1),
            "palabras": [{"w": w, "s": st} for w, st in zip(s.token, s.status)],
        }
print("\n== share de palabras por POS ==")
for p in ORDEN:
    print(f"{p:14s} lista 2009 {waffle['a'][p]['pct']:5.1f}%  lista 2025 {waffle['b'][p]['pct']:5.1f}%")

# share ponderado por menciones (más fiel al uso)
pond = {}
for lista, col in [("a", "rate_a"), ("b", "rate_b")]:
    sub = tok[tok[col] >= UMBRAL]
    tot = sub[col].sum()
    pond[lista] = {p: round(100 * sub[sub.pos_w == p][col].sum() / tot, 1) for p in ORDEN}
print("\n== share de menciones por POS ==")
for p in ORDEN:
    print(f"{p:14s} lista 2009 {pond['a'][p]:5.1f}%  lista 2025 {pond['b'][p]:5.1f}%")

(AGG / "lexico_pos.json").write_text(json.dumps({"orden": ORDEN, "waffle": waffle, "menciones": pond},
                                                ensure_ascii=False))
print("\nListo -> data/lexico_pos.parquet, data/agg/lexico_pos.json")
