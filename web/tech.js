/* Página 2: deep-dive tech. Usa charts.js y window.DT (data_tech.js). */
(function () {
  const D = window.DT;
  const C = { s1: "#3987e5", s2: "#d95926", s3: "#199e70", s4: "#c98500", s5: "#d55181", muted: "#52514e" };

  const years = obj => Object.keys(obj).map(Number).sort((a, b) => a - b);
  const pts = obj => years(obj).map(y => ({ x: y, y: obj[y] }));
  const movil3 = p => p.map((d, i) => {
    const w = p.slice(Math.max(0, i - 1), i + 2);
    return { x: d.x, y: +(w.reduce((a, b) => a + b.y, 0) / w.length).toFixed(2) };
  });

  const drawn = new Set(), builders = {};
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add("visible");
    e.target.querySelectorAll("[id]").forEach(n => {
      if (builders[n.id] && !drawn.has(n.id)) { drawn.add(n.id); builders[n.id](); }
    });
  }), { threshold: 0.15 });
  document.querySelectorAll(".reveal").forEach(s => io.observe(s));

  /* ---------- rankings 2009 / 2019 / 2025 ---------- */
  const SUBS = { 2009: "La era del retail", 2019: "La era del smartphone", 2025: "La era de la IA" };
  builders["rankings"] = () => {
    const box = document.getElementById("rankings");
    ["2009", "2019", "2025"].forEach(y => {
      const rows = D.top_palabras[y].slice(0, 15);
      const max = rows[0].r;
      const col = document.createElement("div");
      col.className = "rank";
      col.innerHTML = `<h3>${y}</h3><p class="sub">${SUBS[y]}</p><ol>` +
        rows.map((d, i) =>
          `<li><span class="pos">${i + 1}</span><span class="w">${d.w}` +
          (d.nueva ? ` <span class="badge">NUEVA</span>` : "") +
          `</span><span class="bar"><span style="width:${(100 * d.r / max).toFixed(0)}%${d.w === "ai" || d.w === "ia" ? ";background:var(--s2)" : ""}"></span></span>` +
          `<span class="r">${String(d.r).replace(".", ",")}</span></li>`).join("") + "</ol>";
      box.appendChild(col);
    });
  };

  /* ---------- IA vs Chile ---------- */
  builders["ch-ia"] = () => {
    const ai = pts(D.olas.ai).filter(p => p.x <= 2025);
    const cl = pts(D.olas.chile).filter(p => p.x <= 2025);
    Charts.lineChart("ch-ia", [
      { name: "“AI” o “IA”", color: C.s2, points: ai },
      { name: "“Chile”", color: C.s1, points: cl, labelDy: 14 }
    ], { yFmt: v => String(v.toFixed(1)).replace(".", ","), ymin: 0, xStep: 4 });
    document.getElementById("chips-ia").innerHTML =
      D.ia_ejemplos.slice(0, 10).map(n => `<span class="chip">${n}</span>`).join("");
  };

  /* ---------- olas sparklines ---------- */
  builders["olas"] = () => {
    const box = document.getElementById("olas");
    [["web", "la internet clásica"], ["digital", "la transformación"], ["app", "los smartphones"],
     ["cloud", "la nube"], ["smart", "los dispositivos"], ["ai", "la que está naciendo"]]
      .forEach(([w, sub]) => Charts.sparkCard(box, `“${w}”`, sub,
        pts(D.olas[w]).filter(p => p.x <= 2025), C.s1));
  };

  /* ---------- suben / bajan ---------- */
  const mkMover = (id, list, color, up) => {
    const rows = list.slice(0, 9).map(m => ({
      label: m.w, value: Math.abs(m.d), color,
      note: `${String(m.a).replace(".", ",")} → ${String(m.b).replace(".", ",")} por 1.000`
    }));
    Charts.barChart(id, rows, {
      fmt: v => (up ? "+" : "−") + String(v.toFixed(1)).replace(".", ","),
      max: Math.max(...rows.map(r => r.value)) * 1.15,
      dimName: "Palabra", valName: "Cambio por 1.000"
    });
  };
  builders["ch-suben"] = () => mkMover("ch-suben", D.suben, C.s1, true);
  builders["ch-bajan"] = () => mkMover("ch-bajan", D.bajan, C.s2, false);

  /* ---------- campos semánticos ---------- */
  builders["ch-campos"] = () => {
    const SEL = [["ia", "Inteligencia artificial", C.s2],
                 ["chile_lugar", "Lugar y Chile", C.s1],
                 ["emocion_aspiracional", "Aspiracional (power, pro, magic…)", C.s4],
                 ["servicios_negocio", "Servicios y consultoría", C.s3]];
    const series = SEL.map(([k, name, color]) => ({
      name, color, points: movil3(pts(D.campos[k]).filter(p => p.x <= 2025))
    }));
    Charts.lineChart("ch-campos", series, { yFmt: v => String(v.toFixed(1)).replace(".", ",") + "%", ymin: 0, xStep: 4, height: 340 });
  };
})();
