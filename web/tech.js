/* Página 2: deep-dive tech. Usa charts.js, window.DT (data_tech.js) y window.DATA (mapa semántico). */
(function () {
  const D = window.DT, DD = window.DATA;
  const C = { s1: "#2F6FE0", s2: "#E0862B", s3: "#2E8B5E", s4: "#B8860B", s5: "#B5467A", muted: "#C9C5AE" };
  const years = obj => Object.keys(obj).map(Number).sort((a, b) => a - b);
  const pts = obj => years(obj).map(y => ({ x: y, y: obj[y] }));
  const movil3 = p => p.map((d, i) => { const w = p.slice(Math.max(0, i - 1), i + 2); return { x: d.x, y: +(w.reduce((a, b) => a + b.y, 0) / w.length).toFixed(2) }; });
  const f1 = v => String(v.toFixed(1)).replace(".", ",");

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

  const SUBS = { 2009: "La era del retail", 2019: "La era del smartphone", 2025: "La era de la IA" };
  builders["rankings"] = () => {
    const box = document.getElementById("rankings");
    ["2009", "2019", "2025"].forEach(y => {
      const rows = D.top_palabras[y].slice(0, 15), max = rows[0].r;
      const col = document.createElement("div"); col.className = "rank";
      col.innerHTML = `<h3>${y}</h3><p class="sub">${SUBS[y]}</p><ol>` + rows.map((d, i) =>
        `<li><span class="pos">${i + 1}</span><span class="w">${d.w}${d.nueva ? `<span class="badge">NUEVA</span>` : ""}</span>` +
        `<span class="bar"><span class="${d.w === "ai" || d.w === "ia" ? "hot" : ""}" style="width:${(100 * d.r / max).toFixed(0)}%"></span></span>` +
        `<span class="r">${String(d.r).replace(".", ",")}</span></li>`).join("") + "</ol>";
      box.appendChild(col);
    });
  };

  builders["ch-ia"] = () => {
    Charts.lineChart("ch-ia", [
      { name: "“AI” o “IA”", color: C.s2, points: pts(D.olas.ai).filter(p => p.x <= 2025) },
      { name: "“Chile”", color: C.s1, points: pts(D.olas.chile).filter(p => p.x <= 2025), labelDy: 14 }
    ], { yFmt: v => f1(v), ymin: 0, xStep: 4 });
    document.getElementById("chips-ia").innerHTML = D.ia_ejemplos.slice(0, 10).map(n => `<span class="chip">${n}</span>`).join("");
  };

  builders["olas"] = () => {
    const box = document.getElementById("olas");
    [["web", "la internet clásica"], ["digital", "la transformación"], ["app", "los smartphones"], ["cloud", "la nube"], ["smart", "los dispositivos"], ["ai", "la que está naciendo"]]
      .forEach(([w, sub]) => Charts.sparkCard(box, `“${w}”`, sub, pts(D.olas[w]).filter(p => p.x <= 2025), C.s1));
  };

  const mkMover = (id, list, color, up) => {
    const rows = list.slice(0, 9).map(m => ({ label: m.w, value: Math.abs(m.d), color, note: `${f1(m.a)} → ${f1(m.b)} por 1.000` }));
    Charts.barChart(id, rows, { fmt: v => (up ? "+" : "−") + f1(v), max: Math.max(...rows.map(r => r.value)) * 1.15, dimName: "Palabra", valName: "Cambio por 1.000" });
  };
  builders["ch-suben"] = () => mkMover("ch-suben", D.suben, C.s1, true);
  builders["ch-bajan"] = () => mkMover("ch-bajan", D.bajan, C.s2, false);

  builders["ch-campos"] = () => {
    const SEL = [["ia", "Inteligencia artificial", C.s2], ["chile_lugar", "Lugar y Chile", C.s1], ["emocion_aspiracional", "Aspiracional (power, pro, magic…)", C.s4], ["servicios_negocio", "Servicios y consultoría", C.s3]];
    Charts.lineChart("ch-campos", SEL.map(([k, name, color]) => ({ name, color, points: movil3(pts(D.campos[k]).filter(p => p.x <= 2025)) })),
      { yFmt: v => f1(v) + "%", ymin: 0, xStep: 4, height: 340 });
  };

  /* ---------- mapa semántico (antes en la página 1) ---------- */
  const CAT_LBL = { descriptivo: "Descriptivo (es)", ingles: "Inglés", fantasia_pura: "Fantasía pura" };
  builders["ch-tech-estilos"] = () => {
    const t = DD.taxonomia_anio.tech;
    Charts.lineChart("ch-tech-estilos", [["fantasia_pura", C.s1], ["descriptivo", C.s2], ["ingles", C.s3]].map(([k, col]) => ({ name: CAT_LBL[k], color: col, points: movil3(pts(t[k])) })),
      { yFmt: v => v.toFixed(0) + "%", ymin: 10, ymax: 45, xStep: 4 });
  };
  const CLUSTER_COLORS = [C.s1, C.s2, C.s3, C.s4, C.s5, "#5E8C31", "#7C6BD1", "#C9553D"];
  const CLUSTER_NOMBRES = { 0: "Luz, visión y óptica", 1: "Marca corta abstracta", 2: "Tech explícito (app, digital)", 3: "Fantasía pura", 4: "Juego, música y emoción", 5: "Chile explícito", 6: "Negocios y consultoría", 7: "Frases en español", 8: "Fantasía evocadora", 9: "Bio, salud y laboratorio", 10: "Energía y potencia", 11: "Data y siglas técnicas" };
  const CLUSTER_EVO = [["5", C.s2], ["7", C.s4], ["8", C.s1], ["10", C.s3]];
  builders["ch-scatter"] = () => {
    if (!DD.tech_scatter) return;
    const info = DD.tech_cluster_info;
    const top = Object.entries(info).sort((a, b) => b[1].n - a[1].n).slice(0, 8).map(([k]) => +k);
    const colorMap = {}, lblMap = {};
    top.forEach((c, i) => colorMap[c] = CLUSTER_COLORS[i]);
    Object.entries(info).forEach(([k, v]) => lblMap[k] = CLUSTER_NOMBRES[k] || v.terminos.slice(0, 3).join(" · "));
    const chart = Charts.scatterChart("ch-scatter", DD.tech_scatter, { colorOf: p => colorMap[p.c] || "#C9C5AE", labelOf: p => lblMap[p.c] || "", yearInit: 2026 });
    document.getElementById("lg-scatter").innerHTML = top.map(c => `<span><span class="sw" style="background:${colorMap[c]}"></span>${lblMap[c]}</span>`).join("") + `<span><span class="sw" style="background:#C9C5AE"></span>otros territorios</span>`;
    const sl = document.getElementById("sl-scatter");
    sl.addEventListener("input", () => { document.getElementById("lbl-scatter").textContent = "hasta " + sl.value; chart.setYear(+sl.value); });
  };
  builders["ch-clusters-evo"] = () => {
    if (!DD.tech_cluster_year) return;
    const series = CLUSTER_EVO.map(([c, col]) => {
      const raw = movil3(pts(DD.tech_cluster_year[c]).filter(p => p.x <= 2025));
      const base = (raw[0].y + raw[1].y + raw[2].y) / 3;
      return { name: CLUSTER_NOMBRES[c], color: col, points: raw.map(p => ({ x: p.x, y: +(100 * p.y / base).toFixed(1) })) };
    });
    Charts.lineChart("ch-clusters-evo", series, { yFmt: v => v.toFixed(0), xStep: 4, height: 340 });
  };

  addEventListener("scroll", lazyOnScroll, { passive: true }); addEventListener("resize", lazyOnScroll); lazyDraw();
})();
