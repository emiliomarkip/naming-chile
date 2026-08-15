/* Orquesta: hero 3D, reveals, charts y explorador. */
(function () {
  const D = window.DATA;
  const C = { s1: "#3987e5", s2: "#d95926", s3: "#199e70", s4: "#c98500", s5: "#d55181", muted: "#52514e" };
  const IDIOMA_LBL = { es: "Español", en: "Inglés", inventado: "Inventado", mixto: "Mixto", sigla: "Sigla" };
  const IDIOMA_COL = { es: C.s1, inventado: C.s2, en: C.s3, mixto: C.s4, sigla: C.s5 };

  const years = obj => Object.keys(obj).map(Number).sort((a, b) => a - b);
  const pts = obj => years(obj).map(y => ({ x: y, y: obj[y] }));
  function movil3(p) {
    return p.map((d, i) => {
      const w = p.slice(Math.max(0, i - 1), i + 2);
      return { x: d.x, y: +(w.reduce((a, b) => a + b.y, 0) / w.length).toFixed(1) };
    });
  }

  /* ---------- reveals (charts se dibujan al entrar en pantalla) ---------- */
  const drawn = new Set();
  const builders = {};
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add("visible");
    e.target.querySelectorAll("[id]").forEach(n => {
      if (builders[n.id] && !drawn.has(n.id)) { drawn.add(n.id); builders[n.id](); }
    });
  }), { threshold: 0.18 });
  document.querySelectorAll(".reveal").forEach(s => io.observe(s));

  /* ---------- 1. largo ---------- */
  builders["ch-largo"] = () => Charts.lineChart("ch-largo", [
    { name: "Caracteres", color: C.s1, points: pts(D.largo_total.chars) }
  ], { yFmt: v => v.toFixed(1), xStep: 4 });

  /* ---------- 2. idioma por industria ---------- */
  builders["ch-idioma-ind"] = () => {
    const inds = [["software", C.s1], ["moda", C.s2], ["alcohol", C.s3], ["gastronomia_hoteles", C.s4]];
    const series = inds.map(([k, col], i) => {
      const en = D.idioma_por_industria[k].en, inv = D.idioma_por_industria[k].inventado;
      const p = years(en).map(y => ({ x: y, y: +(en[y] + inv[y]).toFixed(1) }));
      return { name: D.industrias[k], color: col, points: movil3(p), labelDy: [0, 0, 14, 0][i] };
    });
    Charts.lineChart("ch-idioma-ind", series, { yFmt: v => v.toFixed(0) + "%", ymin: 30, ymax: 80, xStep: 4 });
  };

  /* ---------- 3. idioma por nacionalidad (2025) ---------- */
  builders["ch-nacionalidad"] = () => {
    const orden = ["es", "inventado", "en", "mixto", "sigla"];
    const rows = [["chilenos", "Chilenos"], ["extranjeros", "Extranjeros"]].map(([k, lbl]) => ({
      label: lbl,
      parts: orden.map(i => ({ name: IDIOMA_LBL[i], value: D.idioma_por_nacionalidad[k][i]["2025"], color: IDIOMA_COL[i] }))
    }));
    Charts.stackedChart("ch-nacionalidad", rows);
  };

  /* ---------- 4. fracaso stats ---------- */
  builders["stat-cl"] = () => {
    const f = D.fracaso_nacionalidad;
    document.getElementById("stat-cl").textContent = f.chilenos.toFixed(1).replace(".", ",") + "%";
    document.getElementById("stat-ext").textContent = f.extranjeros.toFixed(1).replace(".", ",") + "%";
    setTimeout(() => {
      document.getElementById("meter-cl").style.width = f.chilenos + "%";
      document.getElementById("meter-ext").style.width = f.extranjeros + "%";
    }, 250);
  };

  /* ---------- 5. fracaso por idioma ---------- */
  builders["ch-idioma-fracaso"] = () => {
    const rows = D.rechazo_por_idioma
      .filter(r => r.idioma !== "sigla")
      .sort((a, b) => b.fracaso - a.fracaso)
      .map(r => ({
        label: IDIOMA_LBL[r.idioma], value: r.fracaso,
        color: r.idioma === "inventado" ? C.s1 : C.muted,
        note: r.n.toLocaleString("es-CL") + " solicitudes"
      }));
    Charts.barChart("ch-idioma-fracaso", rows, { fmt: v => v.toFixed(1).replace(".", ",") + "%", max: 40, dimName: "Estilo", valName: "% fracaso" });
    const chips = (D.ejemplos.software[2024] || []).slice(0, 4)
      .concat((D.ejemplos.comida[2024] || []).slice(0, 3), (D.ejemplos.bebidas[2024] || []).slice(0, 3));
    document.getElementById("chips-inventados").innerHTML =
      chips.map(n => `<span class="chip">${n}</span>`).join("");
  };

  /* ---------- 6. sparklines de afijos ---------- */
  builders["sparks"] = () => {
    const box = document.getElementById("sparks");
    [["app", "app·", "peak pandemia"], ["eco", "eco·", "peak 2019"], ["smart", "smart·", "peak 2017–19"],
     ["tech", "·tech", "récord hoy"], ["pro", "·pro", "se duplicó"], ["ly", "·ly", "en alza"]]
      .forEach(([k, name, sub]) => Charts.sparkCard(box, name, sub, pts(D.afijos[k]), C.s1));
  };

  /* ---------- 7. volumen + % chilenos ---------- */
  builders["ch-volumen"] = () => Charts.lineChart("ch-volumen", [
    { name: "Solicitudes", color: C.s1, points: pts(D.volumen.total).filter(p => p.x <= 2025) }
  ], {
    yFmt: v => (v / 1000).toFixed(0) + " mil", ymin: 0, xStep: 4,
    annotations: [
      { x: 2010, label: "Start-Up Chile" },
      { x: 2019, label: "estallido", dy: 0 },
      { x: 2021, label: "boom emprendedor", dy: 14 }
    ]
  });
  builders["ch-chilenos"] = () => Charts.lineChart("ch-chilenos", [
    { name: "% chilenos", color: C.s2, points: pts(D.pct_chilenos).filter(p => p.x <= 2025) }
  ], {
    yFmt: v => v.toFixed(0) + "%", ymin: 60, ymax: 90, xStep: 4,
    annotations: [{ x: 2020, label: "pandemia" }]
  });

  /* ---------- explorador ---------- */
  const selInd = document.getElementById("sel-ind");
  const selAnio = document.getElementById("sel-anio");
  Object.entries(D.industrias).forEach(([k, v]) => {
    const o = document.createElement("option"); o.value = k; o.textContent = v; selInd.appendChild(o);
  });
  selInd.value = "software";

  function renderExplorer() {
    const ind = selInd.value, y = selAnio.value;
    document.getElementById("lbl-anio").textContent = y;
    const vol = (D.volumen[ind] || {})[y];
    document.getElementById("ex-vol").textContent = vol ? vol.toLocaleString("es-CL") : "—";
    const tot = D.volumen.total[y];
    document.getElementById("ex-vol-note").textContent = vol ? `${(100 * vol / tot).toFixed(1)}% del total del año` : "";
    const rz = (D.rechazo_industria_anio[ind] || {})[y];
    const fr = document.getElementById("ex-fracaso"), frn = document.getElementById("ex-fracaso-note");
    if (rz && y <= 2023) { fr.textContent = rz[0].toFixed(1).replace(".", ",") + "%"; frn.textContent = `sobre ${rz[1].toLocaleString("es-CL")} casos resueltos`; }
    else { fr.textContent = "—"; frn.textContent = "aún hay solicitudes en trámite"; }
    const box = document.getElementById("ex-idioma"); box.innerHTML = "";
    const det = box.parentElement.querySelector("details"); if (det) det.remove();
    const idio = D.idioma_por_industria[ind];
    if (idio && idio.es[y] != null) {
      Charts.stackedChart("ex-idioma", [{
        label: y, parts: ["es", "inventado", "en", "mixto", "sigla"].map(i =>
          ({ name: IDIOMA_LBL[i], value: idio[i][y], color: IDIOMA_COL[i] }))
      }]);
    }
    const ejs = (D.ejemplos[ind] || {})[y] || [];
    document.getElementById("ex-ejemplos").innerHTML =
      ejs.length ? ejs.map(n => `<span class="chip">${n}</span>`).join("") : "<span class='chip'>sin datos</span>";
  }
  selInd.addEventListener("change", renderExplorer);
  selAnio.addEventListener("input", renderExplorer);
  renderExplorer();

  /* ---------- hero Three.js: nube de nombres ---------- */
  const script = document.createElement("script");
  script.src = "https://unpkg.com/three@0.160.0/build/three.min.js";
  script.onload = initHero;
  document.head.appendChild(script);

  function makeSprite(name) {
    const cv = document.createElement("canvas");
    const ctx = cv.getContext("2d");
    const fs = 42;
    ctx.font = `600 ${fs}px system-ui, sans-serif`;
    cv.width = Math.ceil(ctx.measureText(name).width) + 20; cv.height = fs + 18;
    const c2 = cv.getContext("2d");
    c2.font = `600 ${fs}px system-ui, sans-serif`;
    c2.fillStyle = "#ffffff"; c2.textBaseline = "middle";
    c2.fillText(name, 10, cv.height / 2);
    const tx = new THREE.CanvasTexture(cv);
    tx.minFilter = THREE.LinearFilter;
    const m = new THREE.SpriteMaterial({ map: tx, transparent: true, opacity: 0.16, depthWrite: false });
    const s = new THREE.Sprite(m);
    const k = 0.006;
    s.scale.set(cv.width * k, cv.height * k, 1);
    return s;
  }

  function initHero() {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const box = document.getElementById("hero3d");
    const W = box.clientWidth, H = box.clientHeight;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
    renderer.setSize(W, H);
    box.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0d0d0d, 6, 16);
    const cam = new THREE.PerspectiveCamera(60, W / H, 0.1, 40);
    cam.position.z = 8;
    const names = (window.NOMBRES_HERO || []).slice(0, 170);
    const sprites = names.map(n => {
      const s = makeSprite(n);
      s.position.set((Math.random() - .5) * 18, (Math.random() - .5) * 10, (Math.random() - .5) * 14);
      s.userData.v = 0.0018 + Math.random() * 0.0035;
      scene.add(s); return s;
    });
    let mx = 0, my = 0;
    addEventListener("pointermove", e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; }, { passive: true });
    let running = true;
    new IntersectionObserver(es => running = es[0].isIntersecting).observe(box);
    (function loop() {
      requestAnimationFrame(loop);
      if (!running) return;
      sprites.forEach(s => {
        s.position.z += s.userData.v;
        if (s.position.z > 9) s.position.z = -10;
      });
      cam.position.x += (mx * 1.4 - cam.position.x) * .04;
      cam.position.y += (-my * 1 - cam.position.y) * .04;
      cam.lookAt(0, 0, 0);
      renderer.render(scene, cam);
    })();
    addEventListener("resize", () => {
      const w = box.clientWidth, h = box.clientHeight;
      cam.aspect = w / h; cam.updateProjectionMatrix(); renderer.setSize(w, h);
    });
  }
})();
