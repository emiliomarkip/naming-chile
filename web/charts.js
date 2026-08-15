/* Mini librería de charts SVG — línea, barras, stacked, sparkline.
   Tokens de color en CSS vars; tooltip compartido; tabla accesible opcional. */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const tooltip = () => document.getElementById("tooltip");

  function el(tag, attrs, children) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
    (children || []).forEach(c => n.appendChild(c));
    return n;
  }
  function txt(tag, attrs, s) { const n = el(tag, attrs); n.textContent = s; return n; }

  function showTip(evt, html) {
    const t = tooltip();
    t.innerHTML = html;
    t.style.opacity = 1;
    const pad = 14, w = t.offsetWidth, h = t.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY - h - pad;
    if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
    if (y < 8) y = evt.clientY + pad;
    t.style.left = x + "px"; t.style.top = y + "px";
  }
  function hideTip() { tooltip().style.opacity = 0; }

  function niceTicks(min, max, n) {
    const span = max - min || 1, step0 = span / n,
      mag = Math.pow(10, Math.floor(Math.log10(step0))),
      step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => span / s <= n) || mag * 10,
      lo = Math.floor(min / step) * step, out = [];
    for (let v = lo; v <= max + 1e-9; v += step) if (v >= min - 1e-9) out.push(+v.toFixed(6));
    return out;
  }
  const fmt = v => v.toLocaleString("es-CL");

  function tableView(container, headers, rows) {
    const d = document.createElement("details");
    d.className = "tabla";
    d.innerHTML = "<summary>Ver datos en tabla</summary>";
    const t = document.createElement("table");
    t.innerHTML = "<thead><tr>" + headers.map(h => `<th scope="col">${h}</th>`).join("") + "</tr></thead>" +
      "<tbody>" + rows.map(r => "<tr>" + r.map(c => `<td>${c}</td>`).join("") + "</tr>").join("") + "</tbody>";
    d.appendChild(t);
    container.appendChild(d);
  }

  /* ---- line chart: series = [{name,color,points:[{x,y}]}] ---- */
  function lineChart(id, series, opts) {
    opts = opts || {};
    const box = document.getElementById(id);
    const W = Math.min(box.clientWidth || 780, 780), H = opts.height || 300;
    const M = { t: 16, r: opts.rightPad || 70, b: 30, l: 40 };
    const xs = series.flatMap(s => s.points.map(p => p.x));
    const ys = series.flatMap(s => s.points.map(p => p.y));
    const xmin = Math.min(...xs), xmax = Math.max(...xs);
    let ymin = opts.ymin != null ? opts.ymin : Math.min(...ys), ymax = opts.ymax != null ? opts.ymax : Math.max(...ys);
    const yr = ymax - ymin; if (opts.ymin == null) ymin -= yr * .08; if (opts.ymax == null) ymax += yr * .08;
    const X = x => M.l + (x - xmin) / (xmax - xmin) * (W - M.l - M.r);
    const Y = y => H - M.b - (y - ymin) / (ymax - ymin) * (H - M.t - M.b);
    const svg = el("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, role: "img" });

    niceTicks(ymin, ymax, 4).forEach(v => {
      svg.appendChild(el("line", { x1: M.l, x2: W - M.r, y1: Y(v), y2: Y(v), class: "gridline" }));
      svg.appendChild(txt("text", { x: M.l - 8, y: Y(v) + 4, "text-anchor": "end", class: "tick" }, opts.yFmt ? opts.yFmt(v) : fmt(v)));
    });
    const step = opts.xStep || 4;
    const xticks = xs.filter((v, i, a) => a.indexOf(v) === i)
      .filter(v => v % step === 1 || v === xmin || v === xmax)
      .filter((v, i, a) => v !== xmax || xmax - a[i - 1] >= 2 || a.length === 1);
    xticks.forEach(v => svg.appendChild(txt("text", { x: X(v), y: H - 8, "text-anchor": "middle", class: "tick" }, v)));
    svg.appendChild(el("line", { x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: "axisline" }));

    (opts.annotations || []).forEach(a => {
      svg.appendChild(el("line", { x1: X(a.x), x2: X(a.x), y1: M.t, y2: H - M.b, stroke: "var(--axis)", "stroke-width": 1 }));
      svg.appendChild(txt("text", { x: X(a.x) + 5, y: M.t + 10 + (a.dy || 0), class: "hito" }, a.label));
    });

    series.forEach(s => {
      const d = s.points.map((p, i) => (i ? "L" : "M") + X(p.x) + " " + Y(p.y)).join(" ");
      const path = el("path", { d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round" });
      svg.appendChild(path);
      requestAnimationFrame(() => {
        const len = path.getTotalLength();
        path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
        path.getBoundingClientRect();
        path.style.transition = "stroke-dashoffset 1.4s ease";
        path.style.strokeDashoffset = 0;
        setTimeout(() => { path.style.strokeDasharray = "none"; }, 1600);
      });
      const last = s.points[s.points.length - 1];
      svg.appendChild(el("circle", { cx: X(last.x), cy: Y(last.y), r: 4.5, fill: s.color, stroke: "var(--surface)", "stroke-width": 2 }));
      svg.appendChild(txt("text", { x: X(last.x) + 8, y: Y(last.y) + 4 + (s.labelDy || 0), class: "dlabel" },
        opts.yFmt ? opts.yFmt(last.y) : last.y));
    });

    /* hover: crosshair por x más cercano */
    const hover = el("rect", { x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: "transparent" });
    const cross = el("line", { y1: M.t, y2: H - M.b, stroke: "var(--muted)", "stroke-width": 1, opacity: 0 });
    svg.appendChild(cross); svg.appendChild(hover);
    const allX = [...new Set(xs)].sort((a, b) => a - b);
    hover.addEventListener("mousemove", e => {
      const r = svg.getBoundingClientRect(), sx = W / r.width;
      const mx = (e.clientX - r.left) * sx;
      const xv = allX.reduce((a, b) => Math.abs(X(b) - mx) < Math.abs(X(a) - mx) ? b : a);
      cross.setAttribute("x1", X(xv)); cross.setAttribute("x2", X(xv)); cross.setAttribute("opacity", .5);
      const lines = series.map(s => {
        const p = s.points.find(p => p.x === xv);
        return p ? `<span class="sw" style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${s.color};margin-right:4px"></span>${s.name}: <b>${opts.yFmt ? opts.yFmt(p.y) : fmt(p.y)}</b>` : null;
      }).filter(Boolean).join("<br>");
      showTip(e, `<b>${xv}</b><br>${lines}`);
    });
    hover.addEventListener("mouseleave", () => { cross.setAttribute("opacity", 0); hideTip(); });

    box.appendChild(svg);
    if (series.length > 1) {
      const lg = document.createElement("div"); lg.className = "legend";
      lg.innerHTML = series.map(s => `<span><span class="sw" style="background:${s.color}"></span>${s.name}</span>`).join("");
      box.appendChild(lg);
    }
    tableView(box.parentElement, ["Año", ...series.map(s => s.name)],
      allX.map(x => [x, ...series.map(s => { const p = s.points.find(p => p.x === x); return p ? (opts.yFmt ? opts.yFmt(p.y) : p.y) : "—"; })]));
  }

  /* ---- barras horizontales: items=[{label,value,color,note}] ---- */
  function barChart(id, items, opts) {
    opts = opts || {};
    const box = document.getElementById(id);
    const W = Math.min(box.clientWidth || 780, 780), rowH = 44, H = items.length * rowH + 26;
    const M = { l: 132, r: 70 };
    const vmax = opts.max || Math.max(...items.map(i => i.value)) * 1.12;
    const svg = el("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, role: "img" });
    items.forEach((it, i) => {
      const y = i * rowH + 10, bw = (it.value / vmax) * (W - M.l - M.r), bh = 20;
      svg.appendChild(txt("text", { x: M.l - 10, y: y + bh / 2 + 4, "text-anchor": "end", class: "tick", style: "font-size:12px;fill:var(--ink-2)" }, it.label));
      const bar = el("rect", { x: M.l, y, width: 0, height: bh, rx: 4, fill: it.color });
      bar.style.transition = "width 1s cubic-bezier(.2,.7,.3,1) " + (i * .08) + "s";
      svg.appendChild(bar);
      requestAnimationFrame(() => setTimeout(() => bar.setAttribute("width", Math.max(bw, 2)), 100));
      svg.appendChild(txt("text", { x: M.l + bw + 8, y: y + bh / 2 + 4, class: "dlabel" }, (opts.fmt || fmt)(it.value)));
      const hit = el("rect", { x: 0, y: y - 4, width: W, height: bh + 8, fill: "transparent" });
      hit.addEventListener("mousemove", e => showTip(e, `<b>${it.label}</b><br>${(opts.fmt || fmt)(it.value)}${it.note ? "<br><span style='color:var(--muted)'>" + it.note + "</span>" : ""}`));
      hit.addEventListener("mouseleave", hideTip);
      svg.appendChild(hit);
    });
    svg.appendChild(el("line", { x1: M.l, x2: M.l, y1: 4, y2: H - 10, class: "axisline" }));
    box.appendChild(svg);
    tableView(box.parentElement, [opts.dimName || "Categoría", opts.valName || "Valor"],
      items.map(it => [it.label, (opts.fmt || fmt)(it.value)]));
  }

  /* ---- 100% stacked horizontal: rows=[{label,parts:[{name,value,color}]}] ---- */
  function stackedChart(id, rows, opts) {
    opts = opts || {};
    const box = document.getElementById(id);
    const W = Math.min(box.clientWidth || 780, 780), rowH = 64, H = rows.length * rowH + 6;
    const M = { l: 110, r: 16 };
    const svg = el("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, role: "img" });
    rows.forEach((row, ri) => {
      const y = ri * rowH + 14, bh = 24, total = row.parts.reduce((a, p) => a + p.value, 0);
      svg.appendChild(txt("text", { x: M.l - 10, y: y + bh / 2 + 4, "text-anchor": "end", class: "tick", style: "font-size:12px;fill:var(--ink-2)" }, row.label));
      let x = M.l;
      row.parts.forEach(p => {
        const w = p.value / total * (W - M.l - M.r);
        const seg = el("rect", { x: x + 1, y, width: Math.max(w - 2, 0), height: bh, rx: 3, fill: p.color });
        seg.addEventListener("mousemove", e => showTip(e, `<b>${p.name}</b> — ${row.label}<br><b>${p.value.toFixed(1)}%</b>`));
        seg.addEventListener("mouseleave", hideTip);
        svg.appendChild(seg);
        if (w > 52) svg.appendChild(txt("text", {
          x: x + w / 2, y: y + bh / 2 + 4, "text-anchor": "middle",
          style: "font-size:11px;font-weight:600;fill:#fff"
        }, Math.round(p.value) + "%"));
        x += w;
      });
    });
    box.appendChild(svg);
    const lg = document.createElement("div"); lg.className = "legend";
    lg.innerHTML = rows[0].parts.map(p => `<span><span class="sw" style="background:${p.color}"></span>${p.name}</span>`).join("");
    box.appendChild(lg);
    tableView(box.parentElement, ["", ...rows[0].parts.map(p => p.name)],
      rows.map(r => [r.label, ...r.parts.map(p => p.value.toFixed(1) + "%")]));
  }

  /* ---- sparkline card ---- */
  function sparkCard(container, name, sub, points, color) {
    const card = document.createElement("div");
    card.className = "card"; card.style.marginTop = 0; card.style.padding = "1rem 1.2rem";
    card.innerHTML = `<p class="chart-title" style="margin-bottom:0">${name}</p><p class="chart-sub" style="margin-bottom:.5rem">${sub}</p>`;
    const W = 200, H = 56;
    const xs = points.map(p => p.x), ys = points.map(p => p.y);
    const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = 0, ymax = Math.max(...ys) * 1.1;
    const X = x => 4 + (x - xmin) / (xmax - xmin) * (W - 30);
    const Y = y => H - 8 - (y - ymin) / (ymax - ymin) * (H - 14);
    const svg = el("svg", { width: "100%", viewBox: `0 0 ${W} ${H}` });
    const peak = points.reduce((a, b) => b.y > a.y ? b : a);
    svg.appendChild(el("path", { d: points.map((p, i) => (i ? "L" : "M") + X(p.x) + " " + Y(p.y)).join(" "), fill: "none", stroke: color, "stroke-width": 2, "stroke-linecap": "round" }));
    svg.appendChild(el("circle", { cx: X(peak.x), cy: Y(peak.y), r: 3.5, fill: color, stroke: "var(--surface)", "stroke-width": 2 }));
    svg.appendChild(txt("text", { x: Math.min(X(peak.x) + 5, W - 42), y: Math.max(Y(peak.y) - 5, 10), class: "hito", style: "fill:var(--ink-2);font-weight:600" }, peak.x));
    const hover = el("rect", { x: 0, y: 0, width: W, height: H, fill: "transparent" });
    hover.addEventListener("mousemove", e => {
      const r = svg.getBoundingClientRect(), mx = (e.clientX - r.left) * (W / r.width);
      const p = points.reduce((a, b) => Math.abs(X(b.x) - mx) < Math.abs(X(a.x) - mx) ? b : a);
      showTip(e, `<b>${p.x}</b><br>${p.y.toFixed(1)} por 1.000 marcas`);
    });
    hover.addEventListener("mouseleave", hideTip);
    svg.appendChild(hover);
    card.appendChild(svg);
    container.appendChild(card);
  }

  /* ---- scatter semántico en canvas: points=[{x,y,c,n,a}] 0-100 ---- */
  function scatterChart(id, points, opts) {
    opts = opts || {};
    const box = document.getElementById(id);
    const W = Math.min(box.clientWidth || 780, 780), H = opts.height || 520;
    const cv = document.createElement("canvas");
    const dpr = Math.min(devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr;
    cv.style.width = "100%"; cv.style.maxWidth = W + "px"; cv.style.borderRadius = "12px";
    box.appendChild(cv);
    const ctx = cv.getContext("2d");
    ctx.scale(dpr, dpr);
    const pad = 14;
    const px = p => pad + p.x / 100 * (W - 2 * pad);
    const py = p => pad + p.y / 100 * (H - 2 * pad);
    const colorOf = opts.colorOf || (() => "#3987e5");

    let yearMax = opts.yearInit || 2026, highlight = null;
    function draw() {
      ctx.clearRect(0, 0, W, H);
      for (const p of points) {
        const activo = p.a <= yearMax;
        ctx.globalAlpha = activo ? 0.75 : 0.08;
        ctx.fillStyle = colorOf(p);
        ctx.beginPath();
        ctx.arc(px(p), py(p), activo ? 2.4 : 1.6, 0, 6.284);
        ctx.fill();
      }
      if (highlight) {
        const p = highlight;
        ctx.globalAlpha = 1;
        ctx.lineWidth = 2; ctx.strokeStyle = "#fff";
        ctx.beginPath(); ctx.arc(px(p), py(p), 5, 0, 6.284); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    draw();

    cv.addEventListener("mousemove", e => {
      const r = cv.getBoundingClientRect();
      const mx = (e.clientX - r.left) * (W / r.width), my = (e.clientY - r.top) * (H / r.height);
      let best = null, bd = 144;
      for (const p of points) {
        if (p.a > yearMax) continue;
        const d = (px(p) - mx) ** 2 + (py(p) - my) ** 2;
        if (d < bd) { bd = d; best = p; }
      }
      if (best !== highlight) { highlight = best; draw(); }
      if (best) showTip(e, `<b>${best.n}</b><br>${best.a}${opts.labelOf ? " · " + opts.labelOf(best) : ""}`);
      else hideTip();
    });
    cv.addEventListener("mouseleave", () => { highlight = null; hideTip(); draw(); });

    return { setYear(y) { yearMax = y; highlight = null; draw(); } };
  }

  window.Charts = { lineChart, barChart, stackedChart, sparkCard, tableView, scatterChart };
})();
