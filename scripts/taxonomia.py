"""
Taxonomía lingüística fina de nombres de marca sobre data/features.parquet.

Categorías (en orden de prioridad):
  toponimo      — lugar chileno o geografía reconocible (gazetteer)
  mapuche       — raíz mapudungun en el nombre
  apellido      — apellido frecuente en Chile
  descriptivo   — palabras comunes del español
  ingles        — palabras del inglés
  mixto         — mezcla es/en
  sigla         — siglas / iniciales
  fantasia_comp — inventado con morfemas reconocibles (agro-, -tec, -sol…)
  fantasia_pura — inventado sin morfemas reconocibles

Salida: data/features_ling.parquet (features + columna `categoria`)
Uso: .venv/bin/python scripts/taxonomia.py
"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=None)
def es_palabra_comun(tok, umbral=3.5):
    """El token es una palabra corriente del español o inglés (no distintiva)."""
    return zipf_frequency(tok, "es") >= umbral or zipf_frequency(tok, "en") >= umbral


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ---------- gazetteer: lugares de Chile + geografía famosa ----------
TOPONIMOS = """
chile atacama patagonia andes antartica pacifico aconcagua altiplano araucania
arica iquique antofagasta calama copiapo vallenar serena coquimbo ovalle illapel
valparaiso quillota quilpue villa-alemana casablanca san-antonio rancagua rengo
machali curico talca linares cauquenes chillan concepcion talcahuano coronel
lota arauco temuco villarrica pucon valdivia osorno puerto-montt puerto-varas
castro ancud quellon coyhaique aysen punta-arenas porvenir natales santiago
providencia las-condes vitacura nunoa maipu la-florida puente-alto colina lampa
melipilla talagante buin paine pirque batuco chicureo huechuraba renca quilicura
recoleta independencia macul penalolen la-reina lo-barnechea pudahuel cerrillos
maule biobio nuble los-lagos los-rios magallanes tarapaca elqui limari choapa
huasco tamarugal chacabuco cordillera cachapoal colchagua curepto itata
maipo casablanca leyda cachagua zapallar papudo pichilemu matanzas maitencillo
tongoy guanaqueros bahia-inglesa juan-fernandez rapa-nui pascua chiloe
llanquihue rupanco ranco calafquen panguipulli riñihue puyehue todos-los-santos
osorno calbuco frutillar llaima lonquimay tolhuaca antuco chillan copahue
villarrica osorno tronador fitz-roy torres-del-paine paine cuernos
licanray lican-ray niebla corral mehuin queule toltén tolten imperial carahue
lautaro victoria angol renaico mulchen nacimiento cabrero yumbel tome penco
lirquen dichato cobquecura quirihue coelemu bulnes quillon yungay pemuco
parral retiro longavi colbun panimavida rari vichuquen llico iloca duao
constitucion chanco pelluhue curanipe navidad litueche marchigue peralillo
lolol pumanque paredones bucalemu tunca coya sewell machali coya
farellones portillo valle-nevado la-parva el-colorado lonquen pomaire
isla-negra algarrobo el-quisco el-tabo cartagena rocas-de-santo-domingo
mostazal graneros codegua olivar requinoa quinta-de-tilcoco pichidegua
peumo las-cabras san-vicente pichilemu tanume
elqui vicuna paihuano pisco-elqui monte-grande andacollo rio-hurtado
combarbala punitaqui canela los-vilos pichidangui quilimari caiman
mejillones tocopilla maria-elena quillagua san-pedro-de-atacama toconao
socaire peine ollague chuquicamata sierra-gorda baquedano taltal
paposo chanaral diego-de-almagro el-salvador caldera tierra-amarilla
freirina alto-del-carmen huayco
putre camarones camina colchane huara pozo-almonte pica matilla
mamiña la-tirana victoria puchuncavi quintero ventanas concon renaca
horcon quinteros limache olmue villa-alemana penablanca
america brasil argentina peru bolivia mexico madrid barcelona paris london
londres roma milan berlin tokio kioto nueva-york california texas miami
amazonas sahara everest alaska siberia bali hawai caribe mediterraneo
"""
TOPONIMOS = {t.replace("-", " ") for t in TOPONIMOS.split() if len(t) >= 4}

# ---------- raíces mapudungun ----------
MAPUCHE = """
mapu ruka ruca che antu kalfu calfu curi kuri quilla küla lemu rayen
raihuen lafquen lafken pewen pehuen peuma pichi huala wala ñuke lican likan
newen nehuen quime kume trafkin trawun kimun wenu huenu wekun leufu relmu
ayun ayin amuy kutral quitral pillan wanglen huanglen aliwen alihuen rehue
regue machi lonko toki weichafe kona pichintun futa fucha huentru wentru
lamngen peñi wenüy kelluwun mingako mingaco llellipun ngillatun
antü kürüf kurruf meli epu kiñe kine regle aylla mari pataka warangka
kawell cahuel trewa luan pudu nahuel manque manke ñamku namku traru
diuca loyca lloyca chucao hued hued pitio queltehue treile chincol zorzal
tue tui llampudken pilmaiquen pinda quintu quintral copihue chilco maqui
boldo peumo quillay litre canelo foye arrayan luma tepa ulmo tineo
notro ciruelillo chilca romerillo nalca pangue coleu coligue quila
""".split()
MAPUCHE = {m for m in MAPUCHE if len(m) >= 4}
# raíces que solo cuentan como palabra exacta (prefijos de familias españolas)
EXACT_ONLY = {"maqui", "quila", "peumo", "boldo", "luma"}

# ---------- apellidos frecuentes en Chile ----------
APELLIDOS = """
gonzalez munoz rojas diaz perez soto contreras silva martinez sepulveda
morales rodriguez lopez fuentes hernandez torres araya flores espinoza
valenzuela castillo tapia reyes gutierrez castro pizarro alvarez vasquez
sanchez fernandez ramirez carrasco gomez cortes herrera nunez jara vergara
rivera figueroa riquelme garcia miranda bravo vera molina vega sandoval
zuniga orellana campos olivares alarcon ortiz garrido salazar gallardo
ruiz aguilera guzman saavedra henriquez navarro parra bustos pena
salinas cardenas leiva palma becerra acuna aravena valdes toro sanhueza
carvajal donoso escobar cifuentes lagos maldonado farias arriagada
medina yanez navarrete jimenez moreno mella barrera aguirre venegas
poblete villarroel cornejo veliz galvez ahumada paredes ramos romero
inostroza pincheira jorquera villalobos quezada bustamante caceces
caceres canales godoy uribe ponce astudillo cuevas monsalve avila
suarez rubio bahamondes montecinos larrain errazuriz undurraga concha
edwards montt balmaceda alessandri frei aylwin lagos bachelet pinera
subercaseaux irarrazaval echenique cousino ossandon prieto matte
angelini luksic paulmann solari ibanez yarur said sarquis calderon
del-rio de-la-fuente san-martin santa-maria santa-cruz von-appen
""".split()
APELLIDOS = {a.replace("-", " ") for a in APELLIDOS if len(a) >= 4}

# ---------- morfemas para fantasía compuesta ----------
MORFEMAS = """
agro alim aqua audio auto bio celu ciber cyber deco dent digi eco edu electro
ener farm ferro fito flex foto gastro geo grafic helio hidro hydro immo inmo
indu info inter kine lab laser log ludo maq maqui max mec med mega metal
micro mini moto multi nano naut neo nutri optic orto pan pesc petro pharma
plast poli prot psico quim rehab robo salud sano seg serv sismo sol solar
sonido super tec tech tele term termo trans tur vet vial vida vino vita
zoo dermo cardio uro gine neuro trauma kines fono radio tv web net soft
data digital smart clean green fast easy pro plus star gold king queen
mundo casa tierra sur norte austral pacifico global total full top mi tu
don dona san santa villa hogar campo mar rio monte cerro isla luna
""".split()
MORFEMAS = {m for m in MORFEMAS if len(m) >= 3}

TOKEN_RE = re.compile(r"[a-zñ]+")


def contiene(nombre_norm, lexicon):
    """True si algún término del lexicon aparece como palabra completa."""
    toks = set(TOKEN_RE.findall(nombre_norm))
    if toks & lexicon:
        return True
    # entradas multi-palabra ("san pedro", "torres del paine")
    return any(" " in t and t in nombre_norm for t in lexicon)


def raiz_mapuche(nombre_norm):
    """Token exacto mapudungun, o raíz al inicio/fin de un token inventado.
    Un token que además es palabra común del español/inglés (máquina, mariana,
    kinect…) no cuenta — la coincidencia de raíz es casual."""
    for t in TOKEN_RE.findall(nombre_norm):
        if t in MAPUCHE and not es_palabra_comun(t, umbral=4.3):
            return True
        if es_palabra_comun(t):
            continue
        for r in MAPUCHE:
            if r in EXACT_ONLY:
                continue
            if len(r) >= 5 and (t.startswith(r) or t.endswith(r)):
                return True
            if len(r) == 4 and (t.startswith(r) or t.endswith(r)) and len(t) <= len(r) + 2:
                return True
    return False


def tiene_apellido(nombre_norm):
    """Apellido frecuente como token, descartando los que son palabra común
    (reyes, canales, campos…) para no marcar frases descriptivas."""
    for t in TOKEN_RE.findall(nombre_norm):
        if t in APELLIDOS and not es_palabra_comun(t, umbral=4.0):
            return True
    return any(" " in a and a in nombre_norm for a in APELLIDOS)


def clasificar(row):
    idioma = row["idioma"]
    nombre = norm(row["brand_name"])
    if idioma == "sigla":
        return "sigla"
    if contiene(nombre, TOPONIMOS):
        return "toponimo"
    if raiz_mapuche(nombre):
        return "mapuche"
    if tiene_apellido(nombre):
        return "apellido"
    if idioma == "es":
        return "descriptivo"
    if idioma == "en":
        return "ingles"
    if idioma == "mixto":
        return "mixto"
    # inventado: ¿compuesta o pura?
    toks = TOKEN_RE.findall(nombre)
    if any(m in t for t in toks for m in MORFEMAS
           if len(t) >= len(m) + 2 and (t.startswith(m) or t.endswith(m))):
        return "fantasia_comp"
    return "fantasia_pura"


def main():
    df = pd.read_parquet(ROOT / "data" / "features.parquet")
    print(f"{len(df)} marcas; clasificando...")
    df["categoria"] = df.apply(clasificar, axis=1)
    out = ROOT / "data" / "features_ling.parquet"
    df.to_parquet(out, index=False)
    print(f"Listo -> {out}\n")
    print(df["categoria"].value_counts().to_string())
    print("\n-- solo tecnología (9/42) --")
    print(df[df["ind_software"]]["categoria"].value_counts().to_string())
    for cat in ["toponimo", "mapuche", "apellido", "fantasia_comp", "fantasia_pura"]:
        print(f"\n== muestra {cat} ==")
        print(df[df.categoria == cat]["brand_name"].sample(8, random_state=5).to_string(index=False))


if __name__ == "__main__":
    main()
