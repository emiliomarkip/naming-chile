/* Orquesta la historia: intro, scrollies léxicos, charts del estudio original y explorador. */
(function () {
  const D = window.DATA, L = window.LEX, Lex = window.Lex;
  const C = { s1: "#2F6FE0", s2: "#E0862B", s3: "#2E8B5E", s4: "#B8860B", s5: "#B5467A", muted: "#C9C5AE" };
  const IDIOMA_LBL = { es: "Español", en: "Inglés", inventado: "Inventado", mixto: "Mixto", sigla: "Sigla" };
  const IDIOMA_COL = { es: C.s1, inventado: C.s2, en: C.s3, mixto: C.s4, sigla: C.s5 };
  const years = obj => Object.keys(obj).map(Number).sort((a, b) => a - b);
  const pts = obj => years(obj).map(y => ({ x: y, y: obj[y] }));
  const movil3 = p => p.map((d, i) => { const w = p.slice(Math.max(0, i - 1), i + 2); return { x: d.x, y: +(w.reduce((a, b) => a + b.y, 0) / w.length).toFixed(1) }; });
  const nf = v => v.toLocaleString("es-CL");
  const miles = v => (v >= 10000 ? Math.round(v / 1000) + " mil" : nf(v));

  /* ---------- números del meta en el texto ---------- */
  const M = L.meta;
  document.querySelectorAll("[data-n]").forEach(n => {
    const k = n.dataset.n;
    const map = { lista_a: nf(M.lista_a), lista_b: nf(M.lista_b), n_a: miles(M.n_a), n_b: miles(M.n_b),
      permanecen: nf(M.permanecen), salieron: nf(M.salieron), entraron: nf(M.entraron),
      n_puntuadas: nf(L.concrecion.n_puntuadas), n_tokens: nf(L.concrecion.n_tokens) };
    if (map[k] != null) n.textContent = map[k];
  });

  /* ---------- intro ---------- */
  const intro = document.getElementById("intro");
  Lex.wordField(intro, L.fondo);
  Lex.scrolly(intro, i => intro.classList.toggle("colored", i >= 3), { frac: 0.6 });

  /* ---------- cintas ---------- */
  const scR = document.getElementById("sc-ribbons");
  const ribbons = Lex.ribbonChart(document.getElementById("ch-ribbons"), L.categorias);
  const RIBBON_STEPS = [["corporativo"], ["alimentos", "salud", "bebidas", "animales", "hogar"], ["finanzas", "educacion", "tiempo"], ["territorio", "promesa", "naturaleza"]];
  Lex.scrolly(scR, i => ribbons.highlight(i >= 0 ? (RIBBON_STEPS[i] || null) : null));

  /* ---------- anillos ---------- */
  const scK = document.getElementById("sc-rings");
  const rings = Lex.ringsChart(document.getElementById("ch-rings"), L.alcances);
  rings.setStep(0);
  Lex.scrolly(scK, i => rings.setStep(i < 0 ? 0 : (i >= L.alcances.length ? "all" : i)));

  /* ---------- concreción ---------- */
  Lex.concDensity(document.getElementById("ch-conc-dens"), L.concrecion.densidad, L.concrecion);
  const bands = Lex.concBands(document.getElementById("ch-conc-bands"), L.concrecion.bandas);
  const BAND_STEPS = [[6, 7], [1, 2], [3, 4], null];
  Lex.scrolly(document.getElementById("sc-conc"), i => bands.highlight(i >= 0 && BAND_STEPS[i] !== undefined ? BAND_STEPS[i] : null));

  /* ---------- partes de la oración ---------- */
  const POS_LBL = { sustantivo: "Sustantivos", nombre_propio: "Nombres propios", adjetivo: "Adjetivos", verbo: "Verbos", adverbio: "Adverbios", inventado: "Inventadas", otro: "Otras" };
  Lex.waffleChart(document.getElementById("ch-waffle"), L.pos, POS_LBL);
  (function posText() {
    const w = L.pos.waffle, f = Lex.fmt1;
    const verbos = L.pos_words.verbo.entraron, salieron = L.pos_words.verbo.salieron;
    document.getElementById("pos-text").innerHTML =
      `Los <strong>nombres propios</strong> son la mayor pérdida: de ${f(w.a.nombre_propio.pct)}% a ${f(w.b.nombre_propio.pct)}% de las palabras, porque la mayoría eran marcas-casa que dejaron de repetirse. ` +
      `Los <strong>sustantivos comunes</strong> toman su lugar: de ${f(w.a.sustantivo.pct)}% a ${f(w.b.sustantivo.pct)}%. ` +
      `Los <strong>adjetivos</strong> ${w.b.adjetivo.pct - w.a.adjetivo.pct < -0.5 ? "bajan apenas" : "se mantienen"} (${f(w.a.adjetivo.pct)}% → ${f(w.b.adjetivo.pct)}%) y los <strong>verbos</strong> ${w.b.verbo.pct - w.a.verbo.pct >= 0.8 ? "suben un poco" : "se mantienen"} (${f(w.a.verbo.pct)}% → ${f(w.b.verbo.pct)}%). ` +
      `El cambio no está en cuántos verbos hay, sino en cuáles: los que salieron eran de consumo, ${Lex.marks(["enjoy", "gana", "raspe", "relax"].filter(v => salieron.includes(v)), "old")}; los ${verbos.length} que entraron son de impulso.`;
    document.getElementById("wall-verbos").innerHTML = verbos.map(v => `<span class="new">${v}</span>`).join("");
  })();

  /* ---------- charts del estudio original (se dibujan al entrar en pantalla) ---------- */
  /* dibujo perezoso robusto: en cada scroll se dibuja todo lo que ya esté cerca o por sobre
     la pantalla (un IntersectionObserver se pierde los saltos largos de scroll) */
  const builders = {}, drawn = new Set();
  let lazyTick = false;
  function lazyDraw() {
    lazyTick = false;
    const limit = innerHeight + 500;
    for (const id in builders) {
      if (drawn.has(id)) continue;
      const n = document.getElementById(id);
      if (n && n.getBoundingClientRect().top < limit) { drawn.add(id); builders[id](); }
    }
  }
  const lazyOnScroll = () => { if (!lazyTick) { lazyTick = true; requestAnimationFrame(lazyDraw); } };

  builders["ch-largo"] = () => Charts.lineChart("ch-largo", [{ name: "Caracteres", color: C.s1, points: pts(D.largo_total.chars) }], { yFmt: v => v.toFixed(1), xStep: 4 });

  builders["ch-nacionalidad"] = () => {
    const orden = ["es", "inventado", "en", "mixto", "sigla"];
    Charts.stackedChart("ch-nacionalidad", [["chilenos", "Chilenos"], ["extranjeros", "Extranjeros"]].map(([k, lbl]) => ({
      label: lbl, parts: orden.map(i => ({ name: IDIOMA_LBL[i], value: D.idioma_por_nacionalidad[k][i]["2025"], color: IDIOMA_COL[i] }))
    })));
  };

  builders["stat-cl"] = () => {
    const f = D.fracaso_nacionalidad;
    document.getElementById("stat-cl").textContent = f.chilenos.toFixed(0) + "%";
    document.getElementById("stat-ext").textContent = f.extranjeros.toFixed(0) + "%";
    Lex.pctWaffle(document.getElementById("wf-cl"), f.chilenos, "var(--old)", "Fracaso de titulares chilenos");
    Lex.pctWaffle(document.getElementById("wf-ext"), f.extranjeros, "var(--new)", "Fracaso de titulares extranjeros");
  };

  const CAT_LBL = { descriptivo: "Descriptivo (es)", ingles: "Inglés", fantasia_pura: "Fantasía pura", fantasia_comp: "Fantasía compuesta", toponimo: "Topónimo", mapuche: "Raíz mapuche", apellido: "Apellido", mixto: "Mixto", sigla: "Sigla" };
  builders["ch-tax-fracaso"] = () => {
    const rows = D.taxonomia_fracaso.filter(r => r.n > 2500).sort((a, b) => b.fracaso - a.fracaso).map(r => ({
      label: CAT_LBL[r.categoria], value: r.fracaso, color: r.categoria === "toponimo" ? C.s2 : (r.categoria.startsWith("fantasia") ? C.s1 : C.muted), note: nf(r.n) + " solicitudes"
    }));
    Charts.barChart("ch-tax-fracaso", rows, { fmt: v => v.toFixed(1).replace(".", ",") + "%", max: 44, dimName: "Origen", valName: "% fracaso" });
  };

  builders["sparks"] = () => {
    const box = document.getElementById("sparks");
    [["app", "app·", "peak pandemia"], ["eco", "eco·", "peak 2019"], ["smart", "smart·", "peak 2017–19"], ["tech", "·tech", "récord hoy"], ["pro", "·pro", "se duplicó"], ["ly", "·ly", "en alza"]]
      .forEach(([k, name, sub]) => Charts.sparkCard(box, name, sub, pts(D.afijos[k]), C.s1));
  };

  builders["ch-volumen"] = () => Charts.lineChart("ch-volumen", [{ name: "Solicitudes", color: C.s1, points: pts(D.volumen.total).filter(p => p.x <= 2025) }],
    { yFmt: v => (v / 1000).toFixed(0) + " mil", ymin: 0, xStep: 4, annotations: [{ x: 2010, label: "Start-Up Chile" }, { x: 2019, label: "estallido" }, { x: 2021, label: "boom emprendedor", dy: 14 }] });
  builders["ch-chilenos"] = () => Charts.lineChart("ch-chilenos", [{ name: "% chilenos", color: C.s2, points: pts(D.pct_chilenos).filter(p => p.x <= 2025) }],
    { yFmt: v => v.toFixed(0) + "%", ymin: 60, ymax: 90, xStep: 4, annotations: [{ x: 2020, label: "pandemia" }] });

  builders["ch-mapuche"] = () => {
    Charts.lineChart("ch-mapuche", [{ name: "Raíz mapuche", color: C.s3, points: movil3(pts(D.mapuche_anio).filter(p => p.x <= 2025)) }], { yFmt: v => v.toFixed(1).replace(".", ","), ymin: 0, xStep: 4 });
    document.getElementById("chips-mapuche").innerHTML = Lex.chips(D.taxonomia_ejemplos.mapuche, "", 8);
  };

  addEventListener("scroll", lazyOnScroll, { passive: true }); addEventListener("resize", lazyOnScroll); lazyDraw();

  /* ---------- explorador por industria ---------- */
  const selInd = document.getElementById("sel-ind"), selAnio = document.getElementById("sel-anio");
  Object.entries(D.industrias).forEach(([k, v]) => { const o = document.createElement("option"); o.value = k; o.textContent = v; selInd.appendChild(o); });
  selInd.value = "comida";
  function renderExplorer() {
    const ind = selInd.value, y = selAnio.value;
    document.getElementById("lbl-anio").textContent = y;
    const vol = (D.volumen[ind] || {})[y];
    document.getElementById("ex-vol").textContent = vol ? nf(vol) : "—";
    const tot = D.volumen.total[y];
    document.getElementById("ex-vol-note").textContent = vol ? `${(100 * vol / tot).toFixed(1)}% del total del año` : "";
    const rz = (D.rechazo_industria_anio[ind] || {})[y];
    const fr = document.getElementById("ex-fracaso"), frn = document.getElementById("ex-fracaso-note");
    if (rz && y <= 2023) { fr.textContent = rz[0].toFixed(1).replace(".", ",") + "%"; frn.textContent = `sobre ${nf(rz[1])} casos resueltos`; }
    else { fr.textContent = "—"; frn.textContent = "aún hay solicitudes en trámite"; }
    const box = document.getElementById("ex-idioma"); box.innerHTML = "";
    const det = box.parentElement.querySelector("details"); if (det) det.remove();
    const idio = D.idioma_por_industria[ind];
    if (idio && idio.es[y] != null) Charts.stackedChart("ex-idioma", [{ label: y, parts: ["es", "inventado", "en", "mixto", "sigla"].map(i => ({ name: IDIOMA_LBL[i], value: idio[i][y], color: IDIOMA_COL[i] })) }]);
    const ejs = (D.ejemplos[ind] || {})[y] || [];
    document.getElementById("ex-ejemplos").innerHTML = ejs.length ? Lex.chips(ejs) : "<span class='chip'>sin datos</span>";
  }
  selInd.addEventListener("change", renderExplorer);
  selAnio.addEventListener("input", renderExplorer);
  renderExplorer();

  /* ---------- explorador de palabras ---------- */
  const ex = Lex.explorer(L);
  document.querySelectorAll("mark.w").forEach(m => {
    m.style.cursor = "pointer"; m.title = "Ver en las listas";
    m.addEventListener("click", () => ex.search(m.textContent.trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")));
  });
})();
