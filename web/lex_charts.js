/* ===========================================================
   Gráficos de la historia léxica — SVG vanilla, sin dependencias.
   scrolly · wordField · ribbonChart · ringsChart · concDensity ·
   concBands · waffleChart · pctWaffle · explorer · marquee
   =========================================================== */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, children) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
    (children || []).forEach(c => n.appendChild(c));
    return n;
  };
  const txt = (tag, attrs, s) => { const n = el(tag, attrs); n.textContent = s; return n; };
  const html = (tag, cls, inner) => { const n = document.createElement(tag); if (cls) n.className = cls; if (inner != null) n.innerHTML = inner; return n; };
  const fmtPct = v => String(v.toFixed(1)).replace(".", ",") + "%";
  const fmt1 = v => String(v.toFixed(1)).replace(".", ",");
  const fmt2 = v => String(v.toFixed(2)).replace(".", ",");
  const STATUS_CLS = { permanecen: "both", salieron: "old", entraron: "new" };
  const STATUS_LBL = { permanecen: "permanece", salieron: "salió", entraron: "entró" };
  const COL = { old: "var(--old)", new: "var(--new)", both: "var(--both)", oldhl: "var(--old-hl)", newhl: "var(--new-hl)", bothhl: "var(--both-hl)" };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const up = w => w.toUpperCase();

  /* ---------- tooltip compartido ---------- */
  const tip = () => document.getElementById("tooltip");
  function showTip(evt, content) {
    const t = tip(); if (!t) return;
    t.innerHTML = content; t.style.opacity = 1;
    const pad = 14, w = t.offsetWidth, h = t.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY - h - pad;
    if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
    if (y < 8) y = evt.clientY + pad;
    t.style.left = x + "px"; t.style.top = y + "px";
  }
  const hideTip = () => { const t = tip(); if (t) t.style.opacity = 0; };

  /* ---------- marquee: textos que se desplazan a lo largo de su path ---------- */
  const marquees = [];
  let marqueeRunning = false;
  function addMarquee(node, span, speed, attr) {
    /* node: <textPath> (attr startOffset) o <text> (attr x); span: largo de un ciclo */
    const m = { node, span, speed: speed || 14, attr: attr || "startOffset", base: 0, visible: true, offset: Math.random() * span };
    marquees.push(m);
    if (!marqueeRunning && !reduced) { marqueeRunning = true; requestAnimationFrame(tick); }
    return m;
  }
  let lastT = 0;
  function tick(t) {
    const dt = Math.min((t - lastT) / 1000, 0.1); lastT = t;
    for (const m of marquees) {
      if (!m.visible || !m.span) continue;
      m.offset = (m.offset + m.speed * dt) % m.span;
      m.node.setAttribute(m.attr, m.base - m.offset);
    }
    requestAnimationFrame(tick);
  }
  function watchVisible(svg, ms) {
    new IntersectionObserver(es => ms.forEach(m => m.visible = es[0].isIntersecting), { threshold: 0 }).observe(svg);
  }
  /* repite las palabras para cubrir el largo del path y mide el ciclo */
  function fillText(tp, words, minLen) {
    let s = words.join(",  ");
    const one = s + ",  ";
    tp.textContent = one;
    let len = 0;
    try { len = tp.getComputedTextLength(); } catch (e) { len = one.length * 8; }
    if (!len) len = one.length * 8;
    let reps = Math.max(2, Math.ceil(minLen / len) + 1);
    tp.textContent = one.repeat(reps);
    return len;
  }

  /* ---------- scrollytelling ---------- */
  function scrolly(container, onStep, opts) {
    opts = opts || {};
    const steps = [...container.querySelectorAll(".step")];
    const targets = steps.map(s => s.querySelector(opts.target || ".step-card, .copy") || s);
    const frac = opts.frac || 0.78;            // el paso se activa cuando su tarjeta sube por sobre esta fracción de la pantalla
    let active = -2, ticking = false;
    function update() {
      ticking = false;
      const vh = innerHeight, line = vh * frac;
      let i = -1;
      targets.forEach((t, j) => { const r = t.getBoundingClientRect(); if (r.top < line && r.bottom > 0 - vh) i = j; });
      // si todo el bloque ya quedó arriba, mantenemos el último paso
      const last = targets[targets.length - 1].getBoundingClientRect();
      if (last.bottom < 0) i = targets.length - 1;
      if (i !== active) { active = i; steps.forEach((s, j) => s.classList.toggle("is-active", j === i)); onStep(i); }
    }
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("resize", onScroll);
    update();
    return { steps, update };
  }

  /* ---------- intro: campo de palabras ---------- */
  function wordField(container, words) {
    const field = container.querySelector(".field");
    const rng = mulberry(5);
    const spans = words.map(d => {
      const s = document.createElement("span");
      s.textContent = up(d.w); s.className = STATUS_CLS[d.s];
      s.style.left = (2 + rng() * 92) + "%";
      s.style.top = (3 + rng() * 92) + "%";
      s.style.transform = `rotate(${(rng() - .5) * 6}deg)`;
      field.appendChild(s); return s;
    });
    const n = spans.length;
    for (let i = 0; i < n * .5; i++) spans[Math.floor(rng() * n)].classList.add("on");
    if (!reduced) setInterval(() => {
      for (let k = 0; k < 4; k++) spans[Math.floor(Math.random() * n)].classList.toggle("on");
    }, 420);
  }
  function mulberry(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  /* ---------- cintas por categoría (1 banda = 1 categoría) ---------- */
  function ribbonChart(container, cats, opts) {
    opts = opts || {};
    cats = cats.filter(c => c.a > 0 || c.b > 0);
    const W = 880, LBL = 196, CAP = 46, X0 = LBL + 4, X1 = W - 70, H = opts.height || 760;
    const TOP = 30, BOT = 8, GAP = 6;
    const avail = H - TOP - BOT - GAP * (cats.length - 1);
    const k = avail / 100;                                     // px por punto porcentual
    const hOf = v => Math.max(v * k, 2.2);
    const left = [...cats].sort((p, q) => q.a - p.a), right = [...cats].sort((p, q) => q.b - p.b);
    const yA = {}, yB = {};
    let y = TOP; left.forEach(c => { yA[c.id] = y; y += hOf(c.a) + GAP; });
    y = TOP; right.forEach(c => { yB[c.id] = y; y += hOf(c.b) + GAP; });
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Cintas por categoría semántica, lista 2009 vs lista 2025" });
    const defs = el("defs"); svg.appendChild(defs);
    svg.appendChild(txt("text", { x: X0, y: 14, class: "lbl-mono" }, "Lista 2009"));
    svg.appendChild(txt("text", { x: X1 + CAP, y: 14, class: "lbl-mono", "text-anchor": "end" }, "Lista 2025"));
    const groups = {}, ms = [];
    cats.forEach((c, i) => {
      const ratio = c.a > 0 ? c.b / c.a : 9;
      const dir = ratio >= 1.18 ? "new" : (ratio <= 0.84 ? "old" : "both");
      const fill = dir === "new" ? COL.newhl : (dir === "old" ? COL.oldhl : COL.both);
      const ya0 = yA[c.id], ya1 = ya0 + hOf(c.a), yb0 = yB[c.id], yb1 = yb0 + hOf(c.b);
      const xa = X0 + CAP, xb = X1, mid = (xa + xb) / 2;
      const d = `M${xa},${ya0} C${mid},${ya0} ${mid},${yb0} ${xb},${yb0} L${xb},${yb1} C${mid},${yb1} ${mid},${ya1} ${xa},${ya1} Z`;
      const g = el("g", { class: "ribbon", "data-id": c.id });
      const clip = el("clipPath", { id: `rb-clip-${c.id}` }, [el("path", { d })]);
      defs.appendChild(clip);
      // caps (extremos rectos con el %)
      g.appendChild(el("rect", { x: X0, y: ya0, width: CAP, height: ya1 - ya0, fill, opacity: .55 }));
      g.appendChild(el("rect", { x: X1, y: yb0, width: CAP, height: yb1 - yb0, fill, opacity: .55 }));
      g.appendChild(el("path", { d, fill }));
      // texto: palabras de la categoría recorriendo la cinta
      const hmin = Math.min(ya1 - ya0, yb1 - yb0);
      const fs = Math.max(10, Math.min(24, hmin * .66));
      if (hmin >= 10 && c.palabras.length) {
        const cy0 = (ya0 + ya1) / 2, cy1 = (yb0 + yb1) / 2;
        const pd = `M${X0 - 40},${cy0} L${xa},${cy0} C${mid},${cy0} ${mid},${cy1} ${xb},${cy1} L${X1 + CAP + 40},${cy1}`;
        const pid = `rb-path-${c.id}`;
        defs.appendChild(el("path", { id: pid, d: pd }));
        const t = el("text", { class: "words", "font-size": fs, dy: fs * .35, "clip-path": `url(#rb-clip-${c.id})` });
        const tp = el("textPath", { href: `#${pid}`, startOffset: 0 });
        t.appendChild(tp); g.appendChild(t);
        const words = c.palabras.slice(0, 160).map(p => up(p.w));
        requestAnimationFrame(() => {
          const span = fillText(tp, words, 1000);
          ms.push(addMarquee(tp, span, 12 + (i % 3) * 3));
        });
      } else {
        const cy0 = (ya0 + ya1) / 2, cy1 = (yb0 + yb1) / 2;
        g.appendChild(el("path", { d: `M${xa},${cy0} C${mid},${cy0} ${mid},${cy1} ${xb},${cy1}`, fill: "none", stroke: "var(--ink-2)", "stroke-width": .8, "stroke-dasharray": "3 3", opacity: .6 }));
      }
      // etiquetas
      const lbl = txt("text", { x: LBL - 8, y: (ya0 + ya1) / 2 + 4, class: "lbl-mono", "text-anchor": "end", "font-size": c.a >= 2 ? 11 : 10 }, c.label);
      g.appendChild(lbl);
      if (ya1 - ya0 >= 12) g.appendChild(txt("text", { x: X0 + CAP / 2, y: (ya0 + ya1) / 2 + 4, class: "dlabel", "text-anchor": "middle", "font-size": 10.5 }, fmtPct(c.a)));
      if (yb1 - yb0 >= 12) g.appendChild(txt("text", { x: X1 + CAP / 2, y: (yb0 + yb1) / 2 + 4, class: "dlabel", "text-anchor": "middle", "font-size": 10.5 }, fmtPct(c.b)));
      const hit = el("path", { d, fill: "transparent" });
      hit.addEventListener("mousemove", e => showTip(e, `<b>${c.label}</b><br>Lista 2009: <b>${fmtPct(c.a)}</b> · Lista 2025: <b>${fmtPct(c.b)}</b><br><span style="opacity:.75">${c.n_a} → ${c.n_b} palabras</span>`));
      hit.addEventListener("mouseleave", hideTip);
      g.appendChild(hit);
      svg.appendChild(g); groups[c.id] = g;
    });
    container.appendChild(svg);
    watchVisible(svg, ms);
    return {
      highlight(ids) {
        const set = ids ? new Set(ids) : null;
        Object.entries(groups).forEach(([id, g]) => g.classList.toggle("dim", !!set && !set.has(id)));
      }
    };
  }

  /* ---------- anillos concéntricos por alcance ---------- */
  function ringsChart(container, anillos, opts) {
    opts = opts || {};
    const W = 720, cx = W / 2, cy = W / 2, R0 = 54, BAND = 22, GAP = 15, STEP = BAND + GAP;
    const svg = el("svg", { viewBox: `0 0 ${W} ${W}`, role: "img", "aria-label": "Anillos: palabras por alcance, lista 2009 a la izquierda y lista 2025 a la derecha" });
    const defs = el("defs"); svg.appendChild(defs);
    svg.appendChild(el("line", { x1: cx, x2: cx, y1: 14, y2: W - 14, stroke: "var(--axis)", "stroke-dasharray": "3 4" }));
    svg.appendChild(txt("text", { x: 6, y: cy + 4, class: "lbl-mono" }, "Lista 2009"));
    svg.appendChild(txt("text", { x: W - 6, y: cy + 4, class: "lbl-mono", "text-anchor": "end" }, "Lista 2025"));
    const P = (r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
    const arc = (r, a0, a1) => { const [x0, y0] = P(r, a0), [x1, y1] = P(r, a1); return `M${x0},${y0} A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1},${y1}`; };
    const sector = (r0, r1, a0, a1) => {
      const [ax, ay] = P(r1, a0), [bx, by] = P(r1, a1), [cx1, cy1] = P(r0, a1), [dx, dy] = P(r0, a0);
      const lg = a1 - a0 > Math.PI ? 1 : 0;
      return `M${ax},${ay} A${r1},${r1} 0 ${lg} 1 ${bx},${by} L${cx1},${cy1} A${r0},${r0} 0 ${lg} 0 ${dx},${dy} Z`;
    };
    const rings = [], ms = [];
    const center = txt("text", { x: cx, y: cy + 4, class: "lbl-mono", "text-anchor": "middle", "font-size": 12 }, "");
    anillos.forEach((a, i) => {
      const rc = R0 + i * STEP + BAND / 2, r0 = rc - BAND / 2, r1 = rc + BAND / 2;
      const g = el("g", { class: "ring hidden", "data-id": a.id });
      const nP = a.permanecen.length, nS = a.salieron.length, nE = a.entraron.length;
      const segs = [
        // izquierda: de abajo (π/2) hacia arriba (3π/2), pasando por la izquierda (π): permanecen y luego salieron
        { st: "permanecen", words: a.permanecen, a0: Math.PI / 2, a1: Math.PI / 2 + Math.PI * nP / (nP + nS), fill: COL.both, cls: "both", pre: "" },
        { st: "salieron", words: a.salieron, a0: Math.PI / 2 + Math.PI * nP / (nP + nS), a1: 3 * Math.PI / 2, fill: COL.old, cls: "old", pre: "− " },
        // derecha: de arriba (3π/2) hacia abajo (5π/2): entraron y luego permanecen
        { st: "entraron", words: a.entraron, a0: 3 * Math.PI / 2, a1: 3 * Math.PI / 2 + Math.PI * nE / (nP + nE), fill: COL.new, cls: "new", pre: "+ " },
        { st: "permanecen", words: a.permanecen, a0: 3 * Math.PI / 2 + Math.PI * nE / (nP + nE), a1: 5 * Math.PI / 2, fill: COL.both, cls: "both", pre: "" },
      ];
      segs.forEach((s, j) => {
        if (s.a1 - s.a0 < 0.002) return;
        const id = `ring-${i}-${j}`;
        const sec = sector(r0, r1, s.a0, s.a1);
        defs.appendChild(el("clipPath", { id: `${id}-clip` }, [el("path", { d: sec })]));
        g.appendChild(el("path", { d: sec, fill: s.fill, opacity: s.st === "permanecen" ? .9 : 1 }));
        const pid = `${id}-path`;
        // el path de texto se extiende un poco más allá del sector (el clip recorta)
        defs.appendChild(el("path", { id: pid, d: arc(rc, s.a0 - .6, s.a1 + .6) }));
        const t = el("text", { class: `words ${s.cls}`, "font-size": 12.5, dy: 4.4, "clip-path": `url(#${id}-clip)` });
        const tp = el("textPath", { href: `#${pid}`, startOffset: 0 });
        t.appendChild(tp); g.appendChild(t);
        const words = s.words.slice(0, 220).map(w => s.pre + up(w));
        if (words.length) requestAnimationFrame(() => {
          const span = fillText(tp, words, rc * (s.a1 - s.a0 + 1.2) + 50);
          const m = addMarquee(tp, span, 9 + (i % 2) * 3);
          m.base = rc * .6; ms.push(m);
        });
        const hit = el("path", { d: sec, fill: "transparent" });
        hit.addEventListener("mousemove", e => showTip(e, `<b>${a.label}</b> · ${s.st === "permanecen" ? "permanecen" : s.st}<br><b>${s.words.length}</b> palabras${s.st === "permanecen" ? " en ambas listas" : (s.st === "salieron" ? " solo en la lista 2009" : " solo en la lista 2025")}<br><span style="opacity:.75">${s.words.slice(0, 8).join(", ")}…</span>`));
        hit.addEventListener("mouseleave", hideTip);
        g.appendChild(hit);
      });
      // etiqueta del anillo: curva en la parte superior, en el espacio entre anillos
      if (i > 0) {
        const lr = r1 + 9, lid = `ring-lbl-${i}`;
        defs.appendChild(el("path", { id: lid, d: arc(lr, -Math.PI / 2 - .9, -Math.PI / 2 + .9) }));
        const lt = el("text", { class: "lbl-mono ring-lbl", "font-size": 10.5 });
        const ltp = el("textPath", { href: `#${lid}`, startOffset: "50%", "text-anchor": "middle" });
        ltp.textContent = up(a.label); lt.appendChild(ltp); g.appendChild(lt);
      }
      svg.appendChild(g); rings.push(g);
    });
    svg.appendChild(center);
    center.textContent = up(anillos[0].label);
    container.appendChild(svg);
    watchVisible(svg, ms);
    return {
      /* step: índice del anillo activo; "all" muestra todos sin atenuar */
      setStep(step) {
        rings.forEach((g, i) => {
          const visible = step === "all" || i <= step;
          g.classList.toggle("hidden", !visible);
          g.classList.toggle("dim", step !== "all" && visible && i !== step);
        });
        center.textContent = up(anillos[0].label);
      }
    };
  }

  /* ---------- concreción: densidad ---------- */
  function concDensity(container, dens, meta) {
    const W = 760, H = 300, M = { t: 34, r: 110, b: 44, l: 34 };
    const xs = dens.grid, ya = dens.a, yb = dens.b;
    const ymax = Math.max(...ya, ...yb) * 1.08;
    const X = v => M.l + (v - 1) / 4 * (W - M.l - M.r);
    const Y = v => H - M.b - v / ymax * (H - M.t - M.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Distribución de concreción de las dos listas" });
    // zona muy concreta
    svg.appendChild(el("rect", { x: X(4), y: M.t, width: X(5) - X(4), height: H - M.t - M.b, fill: "var(--bg-2)" }));
    [1, 2, 3, 4, 5].forEach(v => {
      svg.appendChild(el("line", { x1: X(v), x2: X(v), y1: M.t, y2: H - M.b, class: "gridline" }));
      svg.appendChild(txt("text", { x: X(v), y: H - M.b + 16, class: "tick", "text-anchor": "middle" }, v));
    });
    svg.appendChild(txt("text", { x: X(1), y: H - 6, class: "lbl-mono", "font-size": 10 }, "abstracto"));
    svg.appendChild(txt("text", { x: X(5), y: H - 6, class: "lbl-mono", "text-anchor": "end", "font-size": 10 }, "concreto"));
    svg.appendChild(txt("text", { x: M.l, y: M.t - 14, class: "lbl-mono", "font-size": 10 }, "↑ más palabras"));
    const path = (ys, color, dash) => el("path", { d: xs.map((x, i) => (i ? "L" : "M") + X(x) + "," + Y(ys[i])).join(" "), fill: "none", stroke: color, "stroke-width": 2.2, "stroke-dasharray": dash || "none", "stroke-linejoin": "round" });
    svg.appendChild(path(ya, "var(--old)", "6 4"));
    svg.appendChild(path(yb, "var(--new)"));
    const last = xs.length - 1;
    svg.appendChild(txt("text", { x: X(5) + 8, y: Y(ya[last]) + 4, class: "lbl-mono", style: "fill:var(--old-ink)" }, "Lista 2009"));
    svg.appendChild(txt("text", { x: X(5) + 8, y: Y(yb[last]) + 4 + (Math.abs(Y(yb[last]) - Y(ya[last])) < 14 ? 14 : 0), class: "lbl-mono", style: "fill:var(--new-ink)" }, "Lista 2025"));
    svg.appendChild(txt("text", { x: X(4.5), y: M.t + 2, class: "hito", "text-anchor": "middle" }, `muy concretas: ${fmt1(meta.muy_conc_a)}% → ${fmt1(meta.muy_conc_b)}%`));
    // hover
    const hover = el("rect", { x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: "transparent" });
    hover.addEventListener("mousemove", e => {
      const r = svg.getBoundingClientRect(); const mx = (e.clientX - r.left) * (W / r.width);
      const v = 1 + (mx - M.l) / (W - M.l - M.r) * 4; const i = Math.round((v - 1) / 4 * last);
      if (i < 0 || i > last) return;
      showTip(e, `concreción <b>${fmt2(xs[i])}</b><br>Lista 2009: ${fmt2(ya[i])} · Lista 2025: ${fmt2(yb[i])}`);
    });
    hover.addEventListener("mouseleave", hideTip);
    svg.appendChild(hover);
    container.appendChild(svg);
  }

  /* ---------- concreción: bandas divergentes con palabras ---------- */
  function concBands(container, bandas) {
    const W = 980, ROW = 50, TOP = 86, H = TOP + bandas.length * ROW + 40, cx = W / 2, half = W / 2 - 40;
    const vmax = Math.max(...bandas.flatMap(b => [b.pct_salieron, b.pct_entraron]), 10);
    const scale = half / Math.ceil(vmax / 10) / 10;                 // px por punto %
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Palabras que salieron y entraron según su concreción" });
    const defs = el("defs"); svg.appendChild(defs);
    svg.appendChild(txt("text", { x: cx - 16, y: 24, class: "lbl-mono", "text-anchor": "end" }, "← Palabras que salieron de la lista 2009"));
    svg.appendChild(txt("text", { x: cx + 16, y: 24, class: "lbl-mono" }, "Palabras que entraron a la lista 2025 →"));
    svg.appendChild(el("line", { x1: 30, x2: W - 30, y1: 40, y2: 40, class: "gridline", "stroke-dasharray": "2 3" }));
    for (let v = 0; v <= Math.ceil(vmax / 10) * 10; v += 10) {
      [-1, 1].forEach(s => svg.appendChild(txt("text", { x: cx + s * (v * scale + (v ? 0 : 12 * s)), y: 56, class: "tick", "text-anchor": "middle" }, v + "%")));
    }
    svg.appendChild(txt("text", { x: cx, y: TOP - 12, class: "lbl-mono", "text-anchor": "middle", "font-size": 10 }, "abstracto"));
    svg.appendChild(txt("text", { x: cx, y: H - 10, class: "lbl-mono", "text-anchor": "middle", "font-size": 10 }, "concreto"));
    const rows = [], ms = [];
    bandas.forEach((b, i) => {
      const y = TOP + i * ROW, bh = ROW - 12;
      const g = el("g", { class: "ribbon", "data-i": i });
      svg.appendChild(el("line", { x1: cx, x2: cx, y1: y - 6, y2: y + ROW - 6, class: "gridline", "stroke-dasharray": "2 3" }));
      svg.appendChild(txt("text", { x: cx, y: y - 2, class: "tick", "text-anchor": "middle", "font-size": 10 }, b.lo));
      const wl = b.pct_salieron * scale, wr = b.pct_entraron * scale;
      [["l", wl, b.salieron, COL.oldhl, "old"], ["r", wr, b.entraron, COL.newhl, "new"]].forEach(([side, w, words, fill, cls]) => {
        if (w <= 0) return;
        const x = side === "l" ? cx - 4 - w : cx + 4;
        const id = `cb-${i}-${side}`;
        defs.appendChild(el("clipPath", { id }, [el("rect", { x, y, width: w, height: bh })]));
        g.appendChild(el("rect", { x, y, width: w, height: bh, fill }));
        if (words.length && w > 20) {
          const t = el("text", { class: `words ${cls}`, "font-size": Math.min(20, bh * .62), y: y + bh / 2 + 6, "clip-path": `url(#${id})` });
          t.setAttribute("x", side === "l" ? cx - 10 : cx + 10);
          if (side === "l") t.setAttribute("text-anchor", "end");
          t.textContent = words.map(up).join(",  ") + ",  ";
          g.appendChild(t);
          requestAnimationFrame(() => {
            let len = 0; try { len = t.getComputedTextLength(); } catch (e) { len = 0; }
            if (len > w) {
              const one = t.textContent; t.textContent = one.repeat(3);
              const m = addMarquee(t, len, 11, "x");
              m.base = side === "l" ? cx - 10 + len : cx + 10;
              if (side === "l") { m.speed = -11; m.offset = 0; }
              ms.push(m);
            }
          });
        }
        const lbl = txt("text", { x: side === "l" ? x - 6 : x + w + 6, y: y + bh / 2 + 4, class: "dlabel", "text-anchor": side === "l" ? "end" : "start", "font-size": 10.5 }, fmtPct(side === "l" ? b.pct_salieron : b.pct_entraron));
        lbl.classList.add("pct"); g.appendChild(lbl);
        const hit = el("rect", { x, y, width: w, height: bh, fill: "transparent" });
        hit.addEventListener("mousemove", e => showTip(e, `<b>concreción ${b.lo}–${b.hi}</b><br>${side === "l" ? fmtPct(b.pct_salieron) + " de las palabras que salieron" : fmtPct(b.pct_entraron) + " de las palabras que entraron"}<br><span style="opacity:.75">${words.slice(0, 10).join(", ")}${words.length > 10 ? "…" : ""}</span>`));
        hit.addEventListener("mouseleave", hideTip);
        g.appendChild(hit);
      });
      svg.appendChild(g); rows.push(g);
    });
    container.appendChild(svg);
    watchVisible(svg, ms);
    return {
      highlight(idx) {
        const set = idx ? new Set(idx) : null;
        rows.forEach((g, i) => g.classList.toggle("dim", !!set && !set.has(i)));
      }
    };
  }

  /* ---------- waffle: cada cuadrado es una palabra, por parte de la oración ---------- */
  function waffleChart(container, pos, labels) {
    const ORDEN = pos.orden.filter(p => (pos.waffle.a[p].n + pos.waffle.b[p].n) > 0);
    const CELL = 7, GAPC = 1.6, STEPC = CELL + GAPC, COLGAP = 22, LEFT = 96;
    const colsOf = n => Math.max(4, Math.min(24, Math.round(Math.sqrt(n) / 1.45)));
    const widths = ORDEN.map(p => colsOf(Math.max(pos.waffle.a[p].n, pos.waffle.b[p].n)) * STEPC);
    const W = LEFT + widths.reduce((a, b) => a + b, 0) + COLGAP * (ORDEN.length - 1) + 20;
    const rowsA = Math.max(...ORDEN.map((p, i) => Math.ceil(pos.waffle.a[p].n / (widths[i] / STEPC))));
    const rowsB = Math.max(...ORDEN.map((p, i) => Math.ceil(pos.waffle.b[p].n / (widths[i] / STEPC))));
    const BASE = 24 + rowsA * STEPC, TOPB = BASE + 46, H = TOPB + rowsB * STEPC + 20;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Waffle: palabras por parte de la oración en cada lista" });
    svg.appendChild(txt("text", { x: LEFT - 10, y: BASE - 2, class: "lbl-mono", "text-anchor": "end", "font-size": 12 }, "Lista 2009"));
    svg.appendChild(txt("text", { x: LEFT - 10, y: TOPB + 10, class: "lbl-mono", "text-anchor": "end", "font-size": 12 }, "Lista 2025"));
    const fillOf = { permanecen: COL.both, salieron: COL.old, entraron: COL.new };
    let x0 = LEFT;
    ORDEN.forEach((p, i) => {
      const cols = widths[i] / STEPC;
      const put = (lista, words, baseY, dirUp) => {
        // orden: primero las que cambian (salieron/entraron) junto al eje, luego las que permanecen
        const ordered = [...words.filter(w => w.s !== "permanecen"), ...words.filter(w => w.s === "permanecen")];
        ordered.forEach((w, j) => {
          const c = j % cols, r = Math.floor(j / cols);
          const x = x0 + c * STEPC, y = dirUp ? baseY - (r + 1) * STEPC + GAPC : baseY + r * STEPC;
          const rect = el("rect", { x, y, width: CELL, height: CELL, fill: fillOf[w.s], rx: .8 });
          rect.addEventListener("mousemove", e => showTip(e, `<b>${up(w.w)}</b><br>${labels[p]} · ${STATUS_LBL[w.s]}`));
          rect.addEventListener("mouseleave", hideTip);
          svg.appendChild(rect);
        });
      };
      put("a", pos.waffle.a[p].palabras, BASE, true);
      put("b", pos.waffle.b[p].palabras, TOPB, false);
      svg.appendChild(txt("text", { x: x0 + widths[i] / 2, y: BASE + 16, class: "lbl-mono", "text-anchor": "middle", "font-size": 10.5 }, labels[p]));
      svg.appendChild(txt("text", { x: x0 + widths[i] / 2, y: BASE + 30, class: "tick", "text-anchor": "middle", "font-size": 10 }, `${fmt1(pos.waffle.a[p].pct)}% → ${fmt1(pos.waffle.b[p].pct)}%`));
      x0 += widths[i] + COLGAP;
    });
    container.appendChild(svg);
  }

  /* ---------- waffle de porcentaje (100 cuadrados) ---------- */
  function pctWaffle(container, pct, color, label) {
    const N = 10, CELL = 14, GAP = 3, S = N * (CELL + GAP);
    const svg = el("svg", { viewBox: `0 0 ${S} ${S}`, role: "img", "aria-label": label, style: "max-width:190px" });
    const k = Math.round(pct);
    for (let i = 0; i < 100; i++) {
      const r = Math.floor(i / N), c = i % N;
      svg.appendChild(el("rect", { x: c * (CELL + GAP), y: (N - 1 - r) * (CELL + GAP), width: CELL, height: CELL, rx: 2, fill: i < k ? color : "var(--both-hl)" }));
    }
    container.appendChild(svg);
  }

  /* ---------- sparkline mínima ---------- */
  function spark(serie, w, h, color) {
    const max = Math.max(...serie, .01);
    const X = i => 1 + i / (serie.length - 1) * (w - 2), Y = v => h - 1 - v / max * (h - 2);
    const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, style: "display:inline-block;vertical-align:middle" });
    svg.appendChild(el("path", { d: serie.map((v, i) => (i ? "L" : "M") + X(i) + "," + Y(v)).join(" "), fill: "none", stroke: color, "stroke-width": 1.4 }));
    return svg;
  }

  /* ---------- explorador de palabras (panel lateral) ---------- */
  function explorer(LEX) {
    const rail = html("button", "explorer-rail", "Listas de palabras");
    rail.setAttribute("aria-label", "Abrir listas de palabras");
    const panel = html("aside", "explorer");
    panel.innerHTML = `
      <header>
        <button class="close" aria-label="Cerrar">×</button>
        <h4>Las listas de palabras</h4>
        <div class="tabs"></div>
        <input type="search" placeholder="Busca una palabra…" aria-label="Buscar palabra">
        <p class="count"></p>
      </header>
      <div class="list"></div>`;
    document.body.appendChild(rail); document.body.appendChild(panel);
    const TABS = [["todas", "Todas"], ["a", "Lista 2009"], ["b", "Lista 2025"], ["salieron", "Salieron"], ["entraron", "Entraron"], ["permanecen", "Permanecen"]];
    const tabs = panel.querySelector(".tabs"), list = panel.querySelector(".list"), q = panel.querySelector("input"), count = panel.querySelector(".count");
    let tab = "todas", limit = 250;
    TABS.forEach(([k, l]) => { const b = html("button", k === tab ? "on" : "", l); b.dataset.k = k; b.onclick = () => { tab = k; limit = 250; tabs.querySelectorAll("button").forEach(x => x.classList.toggle("on", x.dataset.k === k)); render(); }; tabs.appendChild(b); });
    const open = () => { panel.classList.add("open"); render(); setTimeout(() => q.focus(), 350); };
    const close = () => panel.classList.remove("open");
    rail.onclick = open; panel.querySelector(".close").onclick = close;
    document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
    q.addEventListener("input", () => { limit = 250; render(); });
    const umbral = LEX.meta.umbral;
    const SCOPE = LEX.scope_labels, CAT = LEX.labels;
    const POS = { sustantivo: "sustantivo", nombre_propio: "nombre propio", adjetivo: "adjetivo", verbo: "verbo", adverbio: "adverbio", inventado: "inventada", numero: "número", otro: "otro" };
    function render() {
      const needle = q.value.trim().toLowerCase();
      let rows = LEX.palabras.filter(p => {
        if (tab === "a") return p.a >= umbral;
        if (tab === "b") return p.b >= umbral;
        if (tab === "salieron" || tab === "entraron" || tab === "permanecen") return p.s === tab;
        return true;
      });
      if (needle) rows = rows.filter(p => p.w.includes(needle) || (p.ea.concat(p.eb)).some(e => e.toLowerCase().includes(needle)));
      if (tab === "a" || tab === "salieron") rows = [...rows].sort((x, y) => y.a - x.a);
      count.textContent = `${rows.length.toLocaleString("es-CL")} palabras · menciones por 1.000 marcas, 2009–11 → 2023–25`;
      list.innerHTML = "";
      rows.slice(0, limit).forEach(p => {
        const row = html("div", "row");
        row.innerHTML = `<span class="w"><i class="${STATUS_CLS[p.s]}"></i>${p.w}</span><span class="meta"><b>${fmt1(p.a)}</b> → <b>${fmt1(p.b)}</b></span>`;
        row.appendChild(spark(p.y, 64, 18, p.s === "salieron" ? "var(--old)" : (p.s === "entraron" ? "var(--new)" : "var(--both-ink)")));
        row.onclick = () => {
          const next = row.nextElementSibling;
          if (next && next.classList.contains("detail")) { next.remove(); return; }
          const d = html("div", "detail");
          d.innerHTML = `<div class="ex"><b>Qué es</b>${CAT[p.c] || p.c} · ${SCOPE[p.k] || p.k} · ${POS[p.p] || p.p}${p.q != null ? ` · concreción ${fmt2(p.q)}` : ""}</div>` +
            (p.t ? `<div class="ex"><b>Titular</b>${p.t}</div>` : "") +
            (p.ea.length ? `<div class="ex"><b>2009–11</b>${p.ea.join(" · ")}</div>` : "") +
            (p.eb.length ? `<div class="ex"><b>2023–25</b>${p.eb.join(" · ")}</div>` : "");
          row.after(d);
        };
        list.appendChild(row);
      });
      if (rows.length > limit) {
        const more = html("button", "btn", `Ver ${Math.min(250, rows.length - limit)} más`);
        more.style.margin = "1rem"; more.onclick = () => { limit += 250; render(); };
        list.appendChild(more);
      }
    }
    return { open, close, search(w) { q.value = w; tab = "todas"; open(); } };
  }

  /* ---------- helpers para texto: chips y marks ---------- */
  const chips = (words, cls, n) => words.slice(0, n || words.length).map(w => `<span class="chip ${cls || ""}">${w}</span>`).join("");
  const marks = (words, cls) => words.map((w, i) => `<mark class="${cls} w">${w}</mark>${i < words.length - 1 ? ", " : ""}`).join("");

  window.Lex = { scrolly, wordField, ribbonChart, ringsChart, concDensity, concBands, waffleChart, pctWaffle, spark, explorer, chips, marks, showTip, hideTip, fmtPct, fmt1 };
})();
