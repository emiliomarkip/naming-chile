"""
Categoría semántica y "alcance" de cada palabra del léxico de naming
(equivalente al USAS del artículo de The Pudding, pero para nombres de marca
en Chile).

Reglas, en orden:
  1. corporativo — el token es una marca-casa: ≥50% de sus menciones vienen de
     un mismo titular (Falabella, Entel, Soprole…). Se detecta con los datos.
  2. mapuche     — raíz mapudungun (lexicón de taxonomia.py).
  3. numero / sigla / fantasia — tokens sin significado léxico.
  4. resto (es/en/ambiguo): categoría por similitud de embeddings con listas
     semilla de 21 categorías; la categoría ganadora es la de mayor promedio de
     las 2 semillas más cercanas. Las semillas exactas se asignan directo.
     OVERRIDES corrige a mano casos frecuentes.

Alcances (anillos, de adentro hacia afuera): producto, territorio, persona,
sistema, promesa, nada.

Salidas:
  data/lexico_sem.parquet          (token, categoria, alcance, score, top_titular, conc_titular)
  data/agg/lexico_semantica.json   (cintas por categoría; anillos por alcance; palabras)

Uso: .venv/bin/python scripts/semantica.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emb_util import embed                      # noqa: E402
from lexico_eras import tokens, UMBRAL, ERA_A, ERA_B  # noqa: E402
from taxonomia import MAPUCHE, TOPONIMOS, es_palabra_comun  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "agg"
MIN_SIM = 0.42
MIN_SIM_INV = 0.52   # inventados: solo si la similitud es alta (subpalabras reconocibles)

CATS = {
    "alimentos": ("Comida y cocina", """pan panaderia pasteleria queso carne pollo pizza empanada sushi cafe cocina
        chef restaurante comida sabor dulce chocolate fruta miel huevo leche helado gourmet torta galleta
        pastel almuerzo cena desayuno receta sal pimienta aceite arroz pasta food bakery kitchen burger grill
        taco cake sweet delicious fresh snack cookie candy meat chicken cheese fruit honey bread"""),
    "bebidas": ("Bebidas, vino y bar", """vino vina cerveza pisco bar bebida jugo agua licor destileria bodega cosecha
        reserva cocteleria coctel champana sidra ron whisky wine beer brew drink juice cocktail spirits vineyard
        gin vodka tea te mate infusion refresco soda botella barril cerveceria"""),
    "moda": ("Moda, ropa y accesorios", """moda ropa vestuario zapatos calzado joyas joyeria accesorios estilo boutique
        textil lana cuero vestido camisa pantalon chaqueta cartera bolso lentes anteojos reloj fashion wear shoes
        jewelry style denim chic look outfit bag dress shirt jeans sneakers brand glam"""),
    "hogar": ("Casa, hogar y diseño", """casa hogar bano mueble muebles decoracion jardin patio ventana puerta cama
        dormitorio cortina alfombra lampara cocina home house decor garden furniture living room bath deco
        interior arquitectura arquitectos diseno design loft habitat espacio ambiente"""),
    "animales": ("Animales y mascotas", """perro gato caballo toro leon condor aguila puma lobo zorro pez ave pajaro
        abeja mariposa mascota mascotas veterinaria dog cat horse bull lion eagle wolf fox fish bird bee pet pets
        animal zoo tigre oso delfin ballena pinguino gallo vaca oveja cordero"""),
    "salud": ("Salud, cuerpo y belleza", """salud clinica medico medica dental odontologia farmacia doctor hospital
        terapia belleza piel cabello estetica cuerpo fitness gym kinesiologia psicologia nutricion health clinic
        medical pharma beauty skin hair body wellness care cuidado vital dermatologia optica laboratorio
        sonrisa dientes pelo unas masaje yoga pilates bienestar"""),
    "personas": ("Personas y familia", """familia mama papa nino nina bebe mujer hombre amigo amigos hermano hermanos
        abuela abuelo gente mujeres hombres kids baby family mom dad girl boy friend friends people senor senora
        don dona hijos tio tia primo vecino comadre compadre guagua pololo"""),
    "emocion": ("Emoción y espíritu", """amor alma vida feliz felicidad alegria sueno suenos magia pasion corazon paz
        esperanza fe divino santo santa angel espiritu karma zen love soul life happy joy dream magic passion heart
        peace hope faith divine angel spirit bless bliss buena onda sonrisa gracia bendicion milagro destino"""),
    "ocio": ("Arte, música, juego y deporte", """arte musica teatro cine danza galeria cultura festival foto fotografia
        estudio studio radio tv television canal show art music dance film gallery media sound sonido banda fiesta
        party juego juegos game games play toys juguetes entretencion entertainment deporte deportivo futbol gol
        running bike bicicleta surf ski sport sports team equipo racing moto carrera outdoor aventura adventure
        camping trekking club hobby comic anime"""),
    "territorio": ("Lugar y territorio", """lugar region ciudad pueblo valle costa norte sur austral patagonia atacama
        andes chile chileno chilena santiago nacional local pacifico cordillera isla puerto barrio calle plaza
        avenida city town village coast north south america latino latina sudamerica mundo world global
        internacional vina valparaiso concepcion temuco antofagasta rancagua talca chiloe"""),
    "naturaleza": ("Naturaleza y paisaje", """sol luna mar rio montana cerro bosque selva campo tierra agua cielo
        estrella flor arbol piedra viento fuego nieve lluvia verde natural ocean sun moon river mountain forest
        earth sky star flower tree stone wind fire green nature playa lago laguna volcan desierto jardin semilla
        raiz hoja planta roca cristal oro plata cobre arena ola"""),
    "comercio": ("Comercio, oficios e industria", """tienda bazar mercado taller almacen ferreteria libreria botilleria
        minimarket market store shop outlet mall feria distribuidora importadora comercial comercializadora fabrica
        industria industrial transporte logistica inmobiliaria propiedades constructora automotriz autos repuestos
        maquinaria maquinas herramientas suministros insumos venta ventas compra negocio local kiosco emporio
        ferreteria carniceria verduleria peluqueria barberia lavanderia funeraria"""),
    "empresa": ("Empresa, gestión y servicios", """empresa grupo servicios soluciones gestion consultores consultoria
        asesorias ingenieria sociedad corporacion holding group solutions services management consulting partners
        company corporate business negocios oficina proyectos profesional profesionales sistemas abogados legal
        contadores auditores agencia estrategia planificacion operaciones recursos humanos capital humano"""),
    "tecnologia": ("Tecnología y digital", """tecnologia digital software app apps web online net data cloud cyber
        robot inteligencia artificial ai ia smart electronica computacion tech internet virtual code bit byte pixel
        link mobile movil telecom drone automation automatica electrico electro computador celular telefono
        plataforma sistema informatica red redes conectividad conecta connect hub lab labs"""),
    "ciencia": ("Ciencia, bio y eco", """bio laboratorio ciencia quimica genetica organico eco ecologico sustentable
        sostenible ambiental reciclaje reciclado circular science organic nano biotech quimico farmaceutico
        investigacion innovacion innova ecologia planeta clima verde renovable"""),
    "finanzas": ("Dinero y finanzas", """banco financiera credito seguros inversiones capital fondo dinero pago ahorro
        tarjeta prestamo leasing factoring bank finance credit insurance invest capital fund money pay cash coin
        wallet cuenta cuotas pesos tasa bolsa trading"""),
    "educacion": ("Educación y saber", """educacion colegio escuela universidad instituto academia curso cursos
        capacitacion aprender saber conocimiento school academy learning campus college institute training libro
        lectura biblioteca editorial profesor alumno estudiante idiomas ingles jardin infantil preuniversitario"""),
    "promesa": ("Calidad y promesa", """pro premium plus max super mega ultra top best mejor calidad excelencia elite
        master primera lider one first prime gold oro platinum royal real king queen rey reina lujo luxury vip
        exclusivo total integral unico unique original nuevo new moderno modern inteligente facil easy seguro safe
        express flex perfect perfecto ideal optimo garantia confianza experto expertos pro perfecta genial"""),
    "energia": ("Energía, fuerza y velocidad", """energia poder fuerza potencia motor electrica solar luz turbo power
        energy force strong fast speed velocidad rapido jet rocket dinamica dynamic activa active motion impulso
        maximo extremo extreme boost volt watt"""),
    "gramatica": ("Palabras funcionales", """todo todos toda todas nuestro nuestra nuestros esta este ese otro otra
        mismo algo nada cada solo solamente menos muy tan aqui alla ahi donde cuando quien como porque sino
        you me we us all out up in on just only more less here there what who where which some any every
        each any never ever yes no si not with without sin con contigo conmigo tuyo mio mia tuya"""),
    "tiempo": ("Tiempo y números", """hoy manana siempre tiempo hora dia noche ano siglo era epoca ahora now today
        time hour day night year century uno dos tres cien mil one two three hundred thousand numero number
        primero segundo 24 360 365 100 2000 eterno infinito momento instante minuto"""),
}
SCOPE_OF = {
    "producto": ["alimentos", "bebidas", "moda", "hogar", "animales"],
    "territorio": ["territorio", "naturaleza", "mapuche"],
    "persona": ["personas", "salud", "emocion", "ocio"],
    "sistema": ["comercio", "empresa", "tecnologia", "ciencia", "finanzas", "educacion"],
    "promesa": ["promesa", "energia", "tiempo"],
    "corporacion": ["corporativo"],
    "nada": ["fantasia", "sigla", "gramatica"],
}
SCOPE_LBL = {"producto": "El producto", "territorio": "El territorio", "persona": "La persona",
             "sistema": "El sistema", "promesa": "La promesa", "corporacion": "La corporación",
             "nada": "Sin referente"}
CAT_LBL = {k: v[0] for k, v in CATS.items()}
CAT_LBL.update({"corporativo": "Marca corporativa", "mapuche": "Raíz mapuche",
                "fantasia": "Fantasía (inventada)", "sigla": "Siglas y códigos"})
CAT_LBL["naturaleza"] = "Naturaleza, color y paisaje"
SCOPE_LBL_OF_CAT = {c: s for s, cs in SCOPE_OF.items() for c in cs}

OVERRIDES = {
    "chile": "territorio", "spa": "salud", "centro": "comercio", "club": "ocio", "mundo": "territorio",
    "vida": "emocion", "casa": "hogar", "santa": "emocion", "san": "emocion", "red": "tecnologia",
    "cruz": "emocion", "alto": "promesa", "central": "territorio", "universidad": "educacion",
    "plaza": "comercio", "mall": "comercio", "hotel": "comercio", "cafe": "bebidas", "coffee": "bebidas",
    "dias": "tiempo", "horas": "tiempo", "trabajo": "empresa", "precio": "comercio", "puntos": "comercio",
    "zone": "territorio", "zona": "territorio", "resort": "comercio", "suites": "comercio", "cabanas": "comercio",
    "mobile": "tecnologia", "touch": "tecnologia", "cross": "ocio", "clear": "promesa", "man": "personas",
    "joven": "personas", "bello": "promesa", "guia": "educacion", "primero": "tiempo", "toda": "promesa",
    "roja": "naturaleza", "favorita": "promesa", "maxima": "promesa", "imperial": "promesa",
    "since": "tiempo", "est": "tiempo", "not": "promesa", "keep": "promesa", "flow": "energia", "glow": "energia",
    "aura": "emocion", "origen": "territorio", "tradicion": "tiempo", "experiencia": "promesa",
    "estilo": "moda", "estacion": "territorio", "taller": "comercio", "hub": "tecnologia", "gym": "salud",
    "protein": "salud", "sour": "bebidas", "acai": "alimentos", "dra": "salud", "dr": "salud",
    "catolica": "educacion", "pontificia": "educacion", "fest": "ocio", "padel": "ocio",
    "integrales": "promesa", "purificada": "ciencia", "circular": "ciencia", "comida": "alimentos",
    "juegos": "ocio", "mascotas": "animales", "pets": "animales", "pet": "animales", "dental": "salud",
    "legal": "empresa", "abogados": "empresa", "store": "comercio", "shop": "comercio", "studio": "ocio",
    "estudio": "ocio", "lab": "ciencia", "labs": "ciencia", "espacio": "hogar", "patagonia": "territorio",
    "propiedades": "comercio", "ingenieria": "empresa", "servicios": "empresa", "salud": "salud",
    "clinica": "salud", "smart": "promesa", "digital": "tecnologia", "integral": "promesa", "alma": "emocion",
    "sushi": "alimentos", "bar": "bebidas", "ai": "tecnologia", "ia": "tecnologia", "tv": "ocio",
    "hd": "tecnologia", "3d": "tecnologia", "4k": "tecnologia", "5g": "tecnologia", "go": "energia",
    "ok": "promesa", "it": "tecnologia", "pc": "tecnologia", "dj": "ocio", "fundacion": "empresa",
    "grupo": "empresa", "group": "empresa", "power": "energia", "pro": "promesa", "sur": "territorio",
    "norte": "territorio", "super": "promesa", "banco": "finanzas", "seguridad": "empresa",
    "energia": "energia", "world": "territorio", "uno": "tiempo", "instituto": "educacion",
    "hospital": "salud", "isapre": "salud", "casino": "ocio", "loteria": "ocio", "camara": "empresa",
    "paseo": "comercio", "boulevard": "comercio", "minerals": "ciencia", "bicentenario": "tiempo",
    "cristal": "naturaleza", "jumbo": "promesa", "nectar": "bebidas", "melon": "alimentos",
    "haus": "hogar", "enjoy": "emocion", "university": "educacion", "presto": "energia",
    "pulso": "salud", "resto": "alimentos", "restobar": "bebidas", "cafeteria": "bebidas", "bakery": "alimentos",
    "pasteleria": "alimentos", "panaderia": "alimentos", "funeraria": "comercio", "repuestos": "comercio",
    "odontologia": "salud", "pilates": "salud", "joyas": "moda", "accesorios": "moda", "gin": "bebidas",
    "beer": "bebidas", "conecta": "tecnologia", "connect": "tecnologia", "consultora": "empresa",
    "comercializadora": "comercio", "industriales": "comercio", "flux": "energia",
    "paris": "corporativo", "john": "personas", "marco": "personas", "manos": "personas", "gas": "energia",
    "med": "salud", "programa": "ocio", "condes": "territorio", "martin": "personas", "tomas": "personas",
    "rincon": "hogar", "vial": "comercio", "point": "territorio", "pampa": "naturaleza", "glass": "hogar",
    "pack": "comercio", "vista": "naturaleza", "serena": "territorio", "parts": "comercio", "kit": "comercio",
    "products": "comercio", "isabel": "personas", "becker": "personas", "miller": "personas",
    "torres": "personas", "lock": "tecnologia", "rent": "comercio", "live": "ocio", "aqua": "naturaleza",
    "ahumada": "territorio", "polo": "ocio", "pedro": "personas", "maipu": "territorio", "ace": "promesa",
    "oxford": "educacion", "hunter": "ocio", "milk": "alimentos", "maule": "territorio",
    "asociados": "empresa", "beneficios": "promesa", "pais": "territorio", "tec": "tecnologia",
    "old": "tiempo", "little": "promesa", "chillan": "territorio", "juan": "personas", "andino": "territorio",
    "line": "comercio", "linea": "comercio", "color": "naturaleza", "caja": "finanzas", "minera": "comercio",
    "collection": "moda", "car": "comercio", "box": "comercio", "producciones": "ocio",
    "desarrollo": "empresa", "marketing": "empresa", "punto": "comercio", "formula": "ciencia",
    "pass": "comercio", "rico": "alimentos", "way": "gramatica", "medio": "gramatica", "gps": "tecnologia",
    "stop": "gramatica", "led": "tecnologia", "menos": "gramatica", "fundo": "territorio",
    "providencia": "territorio", "mes": "tiempo", "rental": "comercio", "copec": "corporativo",
    "maria": "personas", "security": "empresa", "clean": "promesa", "control": "tecnologia",
    "click": "tecnologia", "crazy": "emocion", "beyond": "promesa", "high": "promesa",
    "superior": "promesa", "todo": "gramatica", "vive": "emocion", "todos": "gramatica",
    "andina": "territorio", "claro": "corporativo", "esta": "gramatica", "zero": "tiempo",
    "next": "tiempo", "cecinas": "alimentos", "opticas": "salud", "cosmetica": "salud",
    "automotora": "comercio", "odontologica": "salud", "parfums": "salud", "sangucheria": "alimentos",
    "avicola": "alimentos", "fogon": "alimentos", "otec": "educacion", "mantencion": "comercio",
    "integrativa": "salud", "cencosud": "corporativo", "colgate": "corporativo", "jumbo": "corporativo",
    "lider": "corporativo", "natura": "corporativo", "polar": "corporativo", "entel": "corporativo",
    "falabella": "corporativo", "ripley": "corporativo", "soprole": "corporativo", "mutual": "corporativo",
    "juegos": "ocio", "cash": "finanzas", "heroes": "emocion", "cementerio": "comercio",
    "metropolitano": "territorio", "historias": "ocio", "carpintero": "comercio", "roberto": "personas",
    "henriquez": "personas", "buin": "territorio", "trebol": "naturaleza", "promo": "comercio",
    "velvet": "moda", "holly": "naturaleza", "covadonga": "personas", "coliseo": "ocio",
    "cup": "bebidas", "tigre": "animales", "toolbox": "comercio", "blackberry": "corporativo",
    "lounge": "hogar", "garage": "comercio", "pizzeria": "alimentos", "wind": "naturaleza",
    "modular": "hogar", "sentido": "emocion", "consciente": "emocion", "neuro": "salud",
    "gluten": "alimentos", "terminal": "comercio", "india": "territorio", "iron": "naturaleza",
    "mercurio": "naturaleza", "filter": "comercio", "buses": "comercio", "airlines": "comercio",
    "flash": "tecnologia", "beta": "tecnologia", "fusion": "promesa", "fuente": "naturaleza",
    "frente": "gramatica", "basement": "hogar", "nomads": "ocio", "girls": "personas", "stars": "naturaleza",
    "abs": "salud", "outdoors": "ocio", "teens": "personas", "toys": "ocio", "cars": "comercio",
    "vintage": "tiempo", "friends": "personas", "works": "empresa", "rolls": "alimentos", "tours": "ocio",
    "drinks": "bebidas", "essentials": "promesa", "hecho": "gramatica", "especial": "promesa",
    "burning": "energia", "vamos": "gramatica", "move": "energia", "shining": "energia", "born": "tiempo",
    "feel": "emocion", "doing": "gramatica", "check": "gramatica", "like": "gramatica", "get": "gramatica",
    "hacemos": "gramatica", "estamos": "gramatica", "aqui": "gramatica", "tan": "gramatica",
    "tattoo": "moda", "together": "emocion", "pronto": "tiempo", "relax": "emocion", "tenemos": "gramatica",
    "queremos": "gramatica", "hace": "gramatica", "inside": "gramatica", "bigger": "promesa",
    "gran": "promesa", "grande": "promesa", "viva": "emocion", "via": "comercio", "hacienda": "territorio",
    "choice": "promesa", "andres": "personas", "gusto": "alimentos", "verdad": "emocion", "pura": "promesa",
    "johnson": "corporativo", "termas": "naturaleza", "hilton": "corporativo", "montt": "territorio",
    "globo": "ocio", "david": "personas", "indigo": "naturaleza", "bono": "finanzas", "octay": "territorio",
    "higgins": "personas", "rancho": "hogar", "abc": "sigla", "mistral": "personas", "antonio": "personas",
    "ticket": "ocio", "records": "ocio", "etiqueta": "comercio", "serie": "ocio", "fin": "gramatica",
    "pop": "ocio", "caren": "corporativo", "sipa": "corporativo", "pulso": "corporativo",
    "nectar": "corporativo", "haus": "corporativo", "presto": "corporativo", "cross": "ocio",
    "bien": "emocion", "bueno": "promesa", "buen": "promesa", "buena": "promesa",
    "patagonica": "territorio", "insamar": "corporativo", "indura": "corporativo",
    "cesmec": "corporativo", "cousino": "corporativo",
}


def main():
    tok = pd.read_parquet(ROOT / "data" / "lexico_tokens.parquet")
    lex = set(tok.token)

    # ---------- 1. concentración de titular por token ----------
    df = pd.read_parquet(ROOT / "data" / "features_ling.parquet",
                         columns=["brand_name", "filing_year", "applicants"])
    df = df[df.filing_year.between(*ERA_A) | df.filing_year.between(*ERA_B)]
    df["titular"] = df["applicants"].astype(str).str.split(";").str[0].str.strip().str.upper().str[:40]
    por_tok = defaultdict(Counter)
    for name, tit in zip(df["brand_name"], df["titular"]):
        for t in set(tokens(name)):
            if t in lex:
                por_tok[t][tit] += 1
    top_tit, conc_tit = {}, {}
    for t, c in por_tok.items():
        tit, n = c.most_common(1)[0]
        top_tit[t] = tit
        conc_tit[t] = n / sum(c.values())
    tok["top_titular"] = tok.token.map(top_tit)
    tok["conc_titular"] = tok.token.map(conc_tit).fillna(0).round(3)

    # ---------- 2. embeddings y similitud con semillas ----------
    seeds = {c: sorted(set(v[1].split())) for c, v in CATS.items()}
    seed_words = sorted({w for ws in seeds.values() for w in ws})
    seed_cat = defaultdict(list)
    for c, ws in seeds.items():
        for w in ws:
            seed_cat[w].append(c)
    E_seed = embed(seed_words)
    idx = {w: i for i, w in enumerate(seed_words)}
    cat_idx = {c: np.array([idx[w] for w in ws]) for c, ws in seeds.items()}

    con_sentido = tok[tok.idioma.isin(["es", "en", "ambiguo"]) | ((tok.idioma == "inventado") & (tok.token.str.len() >= 5))].token.tolist()
    E_tok = embed(con_sentido)
    S = E_tok @ E_seed.T
    best_cat, best_score = {}, {}
    for i, t in enumerate(con_sentido):
        scores = {}
        for c, ii in cat_idx.items():
            if c == "gramatica":
                continue
            s = np.sort(S[i, ii])[::-1]
            scores[c] = float(s[:2].mean())
        c = max(scores, key=scores.get)
        best_cat[t], best_score[t] = c, scores[c]

    def clasificar(row):
        t = row.token
        if t in OVERRIDES:
            return OVERRIDES[t], 1.0
        comun = es_palabra_comun(t, umbral=3.5)
        # marca-casa: un titular concentra las menciones y la palabra no es de uso común
        # (Falabella, Soprole, Entel) — o la concentración es casi total (Apple, Ferrari)
        if (row.conc_titular >= 0.5 and not comun) or row.conc_titular >= 0.8:
            return "corporativo", 1.0
        if t in seed_cat:
            return seed_cat[t][0], 1.0
        if t in TOPONIMOS:
            return "territorio", 1.0
        if t in MAPUCHE and not es_palabra_comun(t, umbral=4.3):
            return "mapuche", 1.0
        if row.idioma == "numero":
            return "tiempo", 1.0
        if row.idioma == "inventado":
            for r in MAPUCHE:
                if len(r) >= 5 and (t.startswith(r) or t.endswith(r)):
                    return "mapuche", 1.0
            if len(t) <= 3:
                return "sigla", 1.0
            c, s = best_cat.get(t), best_score.get(t, 0)
            return (c if s >= MIN_SIM_INV else "fantasia"), s
        c, s = best_cat[t], best_score[t]
        return (c if s >= MIN_SIM else "fantasia"), s

    res = tok.apply(clasificar, axis=1, result_type="expand")
    tok["categoria"], tok["score"] = res[0], res[1].round(3)
    tok["alcance"] = tok["categoria"].map(SCOPE_LBL_OF_CAT)
    assert tok["alcance"].notna().all(), tok[tok.alcance.isna()].categoria.unique()

    print("== muestra por categoría (token:score) ==")
    for c in list(CATS) + ["corporativo", "mapuche", "fantasia", "sigla"]:
        if c == "corporativo":
            continue
        sub = tok[tok.categoria == c].sort_values(["rate_a", "rate_b"], ascending=False)
        print(f"\n[{c}] n={len(sub)}  ", ", ".join(f"{t}" for t in sub.token.head(28)))
        dud = sub[sub.score < 0.5].sort_values("score").head(8)
        if len(dud):
            print("   dudosos:", ", ".join(f"{t}({s:.2f})" for t, s in zip(dud.token, dud.score)))
    inv = tok[(tok.idioma == "inventado") & (tok.score < 1)].sort_values("score", ascending=False)
    print(f"\n== inventados clasificados por similitud ({len(inv)}) ==",
          ", ".join(f"{t}→{c}({s:.2f})" for t, c, s in zip(inv.token, inv.categoria, inv.score)))
    corp = tok[tok.categoria == 'corporativo'].sort_values(["rate_a", "rate_b"], ascending=False)
    print(f"\n== corporativos ({len(corp)}) ==", ", ".join(f"{t}[{str(tit)[5:17]}]" for t, tit in zip(corp.token, corp.top_titular)))

    tok[["token", "categoria", "alcance", "score", "top_titular", "conc_titular"]].to_parquet(
        ROOT / "data" / "lexico_sem.parquet", index=False)

    # ---------- 3. agregados ----------
    lista_a = tok[tok.rate_a >= UMBRAL]
    lista_b = tok[tok.rate_b >= UMBRAL]

    def share(sub, col, key):
        tot = sub[col].sum()
        return {k: round(100 * sub[sub[key] == k][col].sum() / tot, 2) for k in sub[key].unique()}

    def share_n(sub, key):
        return {k: round(100 * (sub[key] == k).sum() / len(sub), 2) for k in sub[key].unique()}

    cintas = []
    sh_a, sh_b = share(lista_a, "rate_a", "categoria"), share(lista_b, "rate_b", "categoria")
    sn_a, sn_b = share_n(lista_a, "categoria"), share_n(lista_b, "categoria")
    for c in list(CATS) + ["corporativo", "mapuche", "fantasia", "sigla"]:
        sub = tok[tok.categoria == c].copy()
        sub["mx"] = sub[["rate_a", "rate_b"]].max(axis=1)
        sub = sub.sort_values("mx", ascending=False)
        cintas.append({
            "id": c, "label": CAT_LBL[c], "alcance": SCOPE_LBL_OF_CAT[c],
            "a": sh_a.get(c, 0.0), "b": sh_b.get(c, 0.0),
            "na": sn_a.get(c, 0.0), "nb": sn_b.get(c, 0.0),
            "n_a": int((lista_a.categoria == c).sum()), "n_b": int((lista_b.categoria == c).sum()),
            "palabras": [{"w": w, "s": s} for w, s in zip(sub.token, sub.status)],
        })
    print("\n== share de menciones por categoría: lista 2009 → 2025 ==")
    for c in sorted(cintas, key=lambda d: -d["a"]):
        print(f"{c['label']:34s} {c['a']:5.1f}% → {c['b']:5.1f}%   (palabras {c['n_a']} → {c['n_b']})")

    anillos = []
    for s, cs in SCOPE_OF.items():
        sub = tok[tok.alcance == s]
        perm = sub[sub.status == "permanecen"].sort_values("rate_b", ascending=False)
        sal = sub[sub.status == "salieron"].sort_values("rate_a", ascending=False)
        ent = sub[sub.status == "entraron"].sort_values("rate_b", ascending=False)
        anillos.append({
            "id": s, "label": SCOPE_LBL[s], "categorias": cs,
            "n_a": int((lista_a.alcance == s).sum()), "n_b": int((lista_b.alcance == s).sum()),
            "share_a": round(100 * lista_a[lista_a.alcance == s].rate_a.sum() / lista_a.rate_a.sum(), 2),
            "share_b": round(100 * lista_b[lista_b.alcance == s].rate_b.sum() / lista_b.rate_b.sum(), 2),
            "permanecen": perm.token.tolist(), "salieron": sal.token.tolist(), "entraron": ent.token.tolist(),
        })
    print("\n== alcance: palabras lista 2009 → 2025 (share menciones) ==")
    for a in anillos:
        print(f"{a['label']:14s} {a['n_a']:4d} → {a['n_b']:4d} palabras | {a['share_a']:5.1f}% → {a['share_b']:5.1f}% menciones"
              f" | salieron {len(a['salieron'])} entraron {len(a['entraron'])}")

    out = {"categorias": cintas, "alcances": anillos, "labels": CAT_LBL, "scope_labels": SCOPE_LBL,
           "min_sim": MIN_SIM}
    (AGG / "lexico_semantica.json").write_text(json.dumps(out, ensure_ascii=False))
    print("\nListo -> data/lexico_sem.parquet, data/agg/lexico_semantica.json")


if __name__ == "__main__":
    main()
