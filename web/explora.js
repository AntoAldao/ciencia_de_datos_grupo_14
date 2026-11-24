/* «Explorá los datos» (ver web/explora.py). Los ids de esta parte llevan el prefijo «ex-»: acá se
   escriben sin él y `$`/`$$` lo agregan. Todo lo que el usuario elige queda en el link (#v=…). */
(async function () {
  "use strict";
  const RAIZ = document.querySelector(".explora");
  if (!RAIZ) return;
  async function leer(id) {   // JSON en gzip + base64 (lo escribe `comprimido()` en web/pagina.py)
    const b64 = document.getElementById(id).textContent.trim();
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    return JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).text());
  }
  const FILAS = await leer("dato-explora");
  const CFG = JSON.parse(document.getElementById("config-explora").textContent);
  const conPrefijo = (s) => s.replace(/#(?!ex-)([A-Za-z][\w-]*)/g, "#ex-$1");
  const $ = (s) => RAIZ.querySelector(conPrefijo(s));
  const $$ = (s) => RAIZ.querySelectorAll(conPrefijo(s));
  const NUM = CFG.num, CAT = CFG.cat;
  const fmt = (v, d = 1) => (v === null || v === undefined || isNaN(v)) ? "—" : v.toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const media = (a) => a.length ? a.reduce((s, v) => s + v, 0) / a.length : NaN;
  const anios = [...new Set(FILAS.map((f) => f.anio))].sort();
  const colorEquipo = (e) => CFG.equipos[e] || "#9AA0A6";
  const BASE_CONFIG = { font: "Titillium Web, sans-serif", background: null, view: { stroke: null },
    axis: { labelFontSize: 12, titleFontSize: 13, gridColor: "#E6DED0", domainColor: "#B9AE9A" },
    legend: { labelFontSize: 12, titleFontSize: 12 } };
  const embed = (sel, spec) => vegaEmbed($(sel), { $schema: "https://vega.github.io/schema/vega-lite/v6.json", config: BASE_CONFIG, ...spec },
                                        { actions: false, renderer: "canvas" });

  // =============================== estado en la URL (para compartir) =================================
  const URLST = {
    leer() { return new URLSearchParams(location.hash.replace(/^#/, "").includes("=") ? location.hash.slice(1) : ""); },
    escribir(obj) {
      const q = new URLSearchParams();
      Object.entries(obj).forEach(([k, v]) => { if (v !== "" && v !== null && v !== undefined && v !== false) q.set(k, v === true ? "1" : v); });
      history.replaceState(null, "", "#" + q.toString());
    },
  };
  let seccionActual = "records";
  const escribirEstado = {};   // cada sección registra cómo describirse
  let arrancando = true;
  function guardar(seccion) { if (arrancando) return; seccion = seccion.replace(/^ex-/, ""); seccionActual = seccion; URLST.escribir({ v: seccion, ...(escribirEstado[seccion] ? escribirEstado[seccion]() : {}) }); }
  $("#compartir").addEventListener("click", async () => {
    guardar(seccionActual);
    try { await navigator.clipboard.writeText(location.href); } catch (e) { prompt("Copiá este link:", location.href); }
    const b = $("#compartir"); b.textContent = "¡Link copiado!"; b.classList.add("ok");
    setTimeout(() => { b.textContent = "🔗 Copiar link"; b.classList.remove("ok"); }, 1800);
  });
  // la sección visible queda marcada en el índice
  const enlaces = [...$$(".subnav a")];
  const obs = new IntersectionObserver((ents) => ents.forEach((e) => {
    if (e.isIntersecting) { enlaces.forEach((a) => a.classList.toggle("activo", a.hash === "#" + e.target.id)); seccionActual = e.target.id.replace(/^ex-/, ""); }
  }), { rootMargin: "-30% 0px -60% 0px" });
  $$("section.parte").forEach((s) => obs.observe(s));
  enlaces.forEach((a) => a.addEventListener("click", (ev) => { ev.preventDefault(); ir(a.hash.slice(1)); guardar(a.hash.slice(1)); }));
  const ir = (id) => { const el = $("#" + id.replace(/^ex-/, "")); window.scrollTo({ top: el.getBoundingClientRect().top + scrollY - $("#subnav").offsetHeight - 6, behavior: arrancando ? "instant" : "smooth" }); };

  // =============================== 1 · récords ======================================================
  let orden = CFG.records.map((_, i) => i), desde = 0;
  function mostrarRecords() {
    const lista = $("#records-lista"); lista.innerHTML = "";
    for (let k = 0; k < 3; k++) {
      const r = CFG.records[orden[(desde + k) % orden.length]];
      const div = document.createElement("div"); div.className = "record";
      div.innerHTML = `<span class="rot">${r.t}</span><span class="n">${r.n}</span><span class="x">${r.x}</span><button type="button">Ver ›</button>`;
      div.querySelector("button").addEventListener("click", () => aplicar(r.ver));
      lista.appendChild(div);
    }
  }
  $("#otro").addEventListener("click", () => { desde = (desde + 3) % orden.length; mostrarRecords(); });
  for (let i = orden.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [orden[i], orden[j]] = [orden[j], orden[i]]; }
  mostrarRecords();

  // =============================== 2 · pilotos ======================================================
  const pilotos = [...new Set(FILAS.map((f) => f.piloto))].sort();
  const sel = (id, lista, vacio) => { $(id).innerHTML = (vacio ? `<option value="">${vacio}</option>` : "") + lista.map((p) => `<option>${p}</option>`).join(""); };
  sel("#pa", pilotos); sel("#pb", pilotos, "Nadie (solo la ficha)");
  $("#pa").value = "Colapinto"; $("#pb").value = "Gasly";
  function stats(p) {
    const fs = FILAS.filter((f) => f.piloto === p), fin = fs.filter((f) => f.resultado === "Terminó");
    const equipos = [...new Set(fs.map((f) => f.equipo))];
    const mejor = fs.reduce((a, f) => (!a || f.final < a.final || (f.final === a.final && f.anio > a.anio)) ? f : a, null);
    return { fs, equipos, n: fs.length, temporadas: new Set(fs.map((f) => f.anio)).size,
      victorias: fs.filter((f) => f.final === 1).length, podios: fs.filter((f) => f.final <= 3).length,
      largada: media(fs.map((f) => f.largada).filter((v) => v !== null)), final: media(fs.map((f) => f.final)),
      ganados: media(fin.map((f) => f.ganados).filter((v) => v !== null)), abandonos: 100 * (fs.length - fin.length) / fs.length,
      mejor, ultimoEquipo: fs[fs.length - 1].equipo };
  }
  function ficha(s, nombre, rival) {
    const filas = [
      ["Carreras", s.n, rival && rival.n, null, 0], ["Temporadas", s.temporadas, rival && rival.temporadas, null, 0],
      ["Victorias", s.victorias, rival && rival.victorias, 1, 0], ["Podios", s.podios, rival && rival.podios, 1, 0],
      ["Largada promedio", s.largada, rival && rival.largada, -1, 1], ["Puesto final promedio", s.final, rival && rival.final, -1, 1],
      ["Puestos ganados por carrera", s.ganados, rival && rival.ganados, 1, 1], ["Abandonos", s.abandonos, rival && rival.abandonos, -1, 0, "%"]];
    const td = (v, r, mejor, d, u) => `<td class="${rival && mejor && ((mejor > 0 && v > r) || (mejor < 0 && v < r)) ? "gana" : ""}">${typeof v === "number" ? fmt(v, d) : v}${u || ""}</td>`;
    return `<div class="ficha" style="--c:${colorEquipo(s.ultimoEquipo)}"><div class="nombre">${nombre}</div>
      <div class="equipos">${s.equipos.join(" · ")}</div><table>${filas.map(([k, v, r, m, d, u]) => `<tr><td>${k}</td>${td(v, r, m, d, u)}</tr>`).join("")}
      <tr><td>Mejor resultado</td><td>${s.mejor.final}.º · ${s.mejor.gpl} ${s.mejor.anio}</td></tr></table></div>`;
  }
  let vistaPilotos = null;
  function dibujarPilotos() {
    const a = $("#pa").value, b = $("#pb").value;
    const sa = stats(a), sb = b && b !== a ? stats(b) : null;
    $("#fichas").innerHTML = ficha(sa, a, sb) + (sb ? ficha(sb, b, sa) : "");
    $("#fichas").style.gridTemplateColumns = sb ? "1fr 1fr" : "1fr";
    if (sb) {   // las carreras que corrieron juntos
      const porCarrera = new Map(sb.fs.map((f) => [f.car, f]));
      const juntas = sa.fs.filter((f) => porCarrera.has(f.car));
      const adelanteA = juntas.filter((f) => f.final < porCarrera.get(f.car).final).length;
      const qA = juntas.filter((f) => f.largada !== null && porCarrera.get(f.car).largada !== null && f.largada < porCarrera.get(f.car).largada).length;
      $("#cara").innerHTML = juntas.length
        ? `Corrieron juntos <b>${juntas.length}</b> carreras. <b>${a}</b> terminó adelante en <b>${adelanteA}</b> y <b>${b}</b> en <b>${juntas.length - adelanteA}</b>. En la largada: ${a} ${qA} – ${juntas.length - qA} ${b}.`
        : `${a} y ${b} nunca corrieron la misma carrera en estos datos.`;
      $("#cara").hidden = false;
    } else $("#cara").hidden = true;
    const datos = [...sa.fs, ...(sb ? sb.fs : [])];
    $("#leyenda-pilotos").innerHTML = `<span style="color:${CFG.colores.rojo}">●</span> ${a}` + (sb ? ` &nbsp; <span style="color:${CFG.colores.tinta}">●</span> ${b}` : "");
    const poner = (v) => v.data("t", datos).signal("pa", a).runAsync();
    if (vistaPilotos) poner(vistaPilotos);
    else embed("#g-pilotos", CFG.specs.pilotos).then((r) => { vistaPilotos = r.view; poner(vistaPilotos); });
    guardar("pilotos");
  }
  escribirEstado.pilotos = () => ({ a: $("#pa").value, b: $("#pb").value });
  $("#pa").addEventListener("change", dibujarPilotos); $("#pb").addEventListener("change", dibujarPilotos);

  // =============================== 3 · armá tu gráfico =================================================

  // ---- tipos de gráfico: qué pide cada uno ---------------------------------------------------------
  const ICONO = {
    dispersion: '<svg viewBox="0 0 30 22"><circle class="relleno" cx="6" cy="16" r="2.2" fill="#1F2328"/><circle class="relleno" cx="12" cy="11" r="2.2" fill="#1F2328"/><circle class="relleno" cx="18" cy="13" r="2.2" fill="#1F2328"/><circle class="relleno" cx="24" cy="5" r="2.2" fill="#1F2328"/></svg>',
    barras: '<svg viewBox="0 0 30 22"><rect class="relleno" x="4" y="3" width="20" height="4" fill="#1F2328"/><rect class="relleno" x="4" y="9" width="14" height="4" fill="#1F2328"/><rect class="relleno" x="4" y="15" width="9" height="4" fill="#1F2328"/></svg>',
    histograma: '<svg viewBox="0 0 30 22"><rect class="relleno" x="3" y="14" width="5" height="7" fill="#1F2328"/><rect class="relleno" x="9" y="6" width="5" height="15" fill="#1F2328"/><rect class="relleno" x="15" y="3" width="5" height="18" fill="#1F2328"/><rect class="relleno" x="21" y="11" width="5" height="10" fill="#1F2328"/></svg>',
    cajas: '<svg viewBox="0 0 30 22" fill="none" stroke="#1F2328" stroke-width="1.6"><rect x="4" y="7" width="8" height="9"/><line x1="8" y1="2" x2="8" y2="7"/><line x1="8" y1="16" x2="8" y2="20"/><rect x="18" y="4" width="8" height="8"/><line x1="22" y1="1" x2="22" y2="4"/><line x1="22" y1="12" x2="22" y2="18"/></svg>',
    evolucion: '<svg viewBox="0 0 30 22" fill="none" stroke="#1F2328" stroke-width="2"><polyline points="3,17 10,12 17,14 27,4"/></svg>',
    calor: '<svg viewBox="0 0 30 22"><rect class="relleno" x="3" y="2" width="7" height="6" fill="#1F2328" opacity=".9"/><rect x="11" y="2" width="7" height="6" fill="#1F2328" opacity=".35"/><rect x="11" y="9" width="7" height="6" fill="#1F2328" opacity=".8"/><rect x="19" y="9" width="7" height="6" fill="#1F2328" opacity=".3"/><rect class="relleno" x="19" y="16" width="7" height="5" fill="#1F2328"/><rect x="3" y="16" width="7" height="5" fill="#1F2328" opacity=".15"/></svg>',
  };
  const TIPOS = {
    dispersion: { nombre: "Dispersión", x: "num", y: "num", color: true, tendencia: true },
    barras:     { nombre: "Barras",     x: "cat", y: "num", medida: true, color: false },
    histograma: { nombre: "Histograma", x: "num", color: true },
    cajas:      { nombre: "Cajas",      x: "cat", y: "num" },
    evolucion:  { nombre: "Por temporada", y: "num", medida: true, color: true },
    calor:      { nombre: "Mapa de calor", x: "num", y: "num" },
  };
  const PREGUNTAS = [
    ["¿Clasificar rápido te deja adelante?", { tipo: "dispersion", x: "q_dbt", y: "final", color: "resultado", tendencia: true }],
    ["¿Dónde se larga y dónde se llega?", { tipo: "calor", x: "largada", y: "final" }],
    ["¿Qué escudería gana más puestos en carrera?", { tipo: "barras", x: "equipo", y: "ganados", medida: "mean" }],
    ["¿Desde dónde se abandona más?", { tipo: "barras", x: "zona", y: "abandono", medida: "mean" }],
    ["¿Cómo cambió cada escudería?", { tipo: "evolucion", y: "final", color: "equipo", medida: "mean" }],
    ["¿Cuánto se desgastan las gomas?", { tipo: "cajas", x: "anio", y: "desg_soft" }],
    ["¿Por qué se abandona?", { tipo: "barras", x: "tipo_ab", y: "abandono", medida: "count", f_resultado: "Abandonó" }],
  ];

  // ---- controles -----------------------------------------------------------------------------------
  const estado = { tipo: "dispersion", x: "q_dbt", y: "final", color: "resultado", medida: "mean", tendencia: false };
  const opciones = (sel, pares, vacio) => {
    sel.innerHTML = (vacio ? `<option value="">${vacio}</option>` : "") +
      pares.map(([v, t]) => `<option value="${v}">${t}</option>`).join("");
  };
  const numOpts = Object.entries(NUM).map(([k, v]) => [k, v[0]]);
  const catOpts = Object.entries(CAT);
  Object.entries(TIPOS).forEach(([k, t]) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "tipo"; b.dataset.tipo = k;
    b.innerHTML = ICONO[k] + `<span>${t.nombre}</span>`;
    b.addEventListener("click", () => { cambiarTipo(k); dibujar(); });
    $("#tipos").appendChild(b);
  });
  PREGUNTAS.forEach(([texto, conf], i) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "pregunta"; b.textContent = texto;
    b.addEventListener("click", () => {
      $$(".pregunta").forEach((x) => x.classList.remove("activa"));
      b.classList.add("activa");
      limpiarFiltros();
      cambiarTipo(conf.tipo, conf);
      if (conf.f_resultado) $("#f-resultado").value = conf.f_resultado;
      dibujar();
    });
    $("#preguntas").appendChild(b);
  });
  const aniosA = [...new Set(FILAS.map((f) => f.anio))].sort();
  opciones($("#desde"), aniosA.map((a) => [a, a])); opciones($("#hasta"), aniosA.map((a) => [a, a]));
  $("#hasta").value = aniosA[aniosA.length - 1];
  opciones($("#f-equipo"), [...new Set(FILAS.map((f) => f.equipo))].sort().map((e) => [e, e]), "Todas");
  opciones($("#f-piloto"), [...new Set(FILAS.map((f) => f.piloto))].sort().map((e) => [e, e]), "Todos");

  function cambiarTipo(tipo, conf = {}) {
    const t = TIPOS[tipo];
    estado.tipo = tipo;
    $$(".tipo").forEach((b) => b.classList.toggle("activo", b.dataset.tipo === tipo));
    // ejes según lo que pide el tipo
    const setEje = (id, clase, preferido) => {
      const sel = $("#" + id), lista = clase === "num" ? numOpts : catOpts;
      opciones(sel, lista);
      const valido = lista.some(([v]) => v === preferido);
      sel.value = valido ? preferido : (lista.some(([v]) => v === estado[id]) ? estado[id] : lista[0][0]);
      estado[id] = sel.value;
    };
    $("#c-x").hidden = !t.x; $("#c-y").hidden = !t.y;
    if (t.x) setEje("x", t.x, conf.x);
    if (t.y) setEje("y", t.y, conf.y);
    $("#c-medida").hidden = !t.medida;
    if (conf.medida) $("#medida").value = conf.medida;
    estado.medida = $("#medida").value;
    $("#c-color").hidden = !t.color;
    const colorOpts = tipo === "evolucion" ? catOpts.filter(([k]) => k !== "anio") : catOpts;
    opciones($("#color"), colorOpts, "Ninguno");
    $("#color").value = conf.color !== undefined ? conf.color : (colorOpts.some(([k]) => k === estado.color) ? estado.color : "");
    estado.color = t.color ? $("#color").value : "";
    $("#c-tendencia").hidden = !t.tendencia;
    if (conf.tendencia !== undefined) $("#tendencia").checked = conf.tendencia;
    estado.tendencia = !!t.tendencia && $("#tendencia").checked;
    $("#c-extremos").hidden = !(t.x === "num" || t.y === "num");
    $("#c-x .et").textContent = tipo === "barras" || tipo === "cajas" ? "Agrupar por" : "Eje horizontal";
    $("#c-y .et").textContent = tipo === "barras" || tipo === "evolucion" ? "Qué medir" : (tipo === "cajas" ? "Qué comparar" : "Eje vertical");
  }
  ["x", "y", "color", "medida"].forEach((id) => $("#" + id).addEventListener("change", (e) => {
    estado[id] = e.target.value; quitarPregunta(); dibujar(); }));
  $("#tendencia").addEventListener("change", (e) => { estado.tendencia = e.target.checked; dibujar(); });
  ["#extremos", "#desde", "#hasta", "#f-equipo", "#f-piloto", "#f-resultado", "#f-zona"].forEach((s) =>
    $(s).addEventListener("change", () => { quitarPregunta(); dibujar(); }));
  function quitarPregunta() { $$(".pregunta").forEach((x) => x.classList.remove("activa")); }
  function limpiarFiltros() {
    $("#desde").value = aniosA[0]; $("#hasta").value = aniosA[aniosA.length - 1];
    ["#f-equipo", "#f-piloto", "#f-resultado", "#f-zona"].forEach((s) => ($(s).value = ""));
  }
  $("#limpiar").addEventListener("click", () => { limpiarFiltros(); dibujar(); });

  // ---- filtrar -------------------------------------------------------------------------------------
  function filtradas() {
    const d = +$("#desde").value, h = +$("#hasta").value;
    const eq = $("#f-equipo").value, pi = $("#f-piloto").value, re = $("#f-resultado").value, zo = $("#f-zona").value;
    const t = TIPOS[estado.tipo];
    const usadas = [t.x === "num" && estado.x, t.y === "num" && estado.y].filter(Boolean);
    const recortar = $("#extremos").checked;
    return FILAS.filter((f) => f.anio >= Math.min(d, h) && f.anio <= Math.max(d, h)
      && (!eq || f.equipo === eq) && (!pi || f.piloto === pi) && (!re || f.resultado === re) && (!zo || f.zona === zo)
      && usadas.every((k) => f[k] !== null && (!recortar || (f[k] >= CFG.cortes[k][0] && f[k] <= CFG.cortes[k][1]))));
  }

  // ---- colores: los de la app ----------------------------------------------------------------------
  function escalaColor(campo, datos) {
    if (campo === "equipo") {
      const dom = [...new Set(datos.map((f) => f.equipo))].sort();
      return { domain: dom, range: dom.map((e) => CFG.equipos[e] || "#9AA0A6") };
    }
    if (campo === "resultado") return { domain: ["Terminó", "Abandonó"], range: [CFG.colores.tinta, CFG.colores.abandono] };
    if (campo === "anio") return { scheme: "orangered" };
    if (campo === "zona") return { domain: ["1–5", "6–10", "11–15", "16 o más"], scheme: "reds", reverse: true };
    return { scheme: "tableau10" };
  }

  // ---- armar el gráfico ----------------------------------------------------------------------------
  const etq = (k) => (NUM[k] ? NUM[k][0] : CAT[k]);
  const MEDIDA = { mean: "Promedio", median: "Mediana", count: "Cantidad" };
  const TOOL = [{ field: "piloto", title: "Piloto" }, { field: "equipo", title: "Escudería" },
                { field: "gp", title: "Gran Premio" }, { field: "anio", title: "Temporada" },
                { field: "largada", title: "Largó" }, { field: "final", title: "Terminó" },
                { field: "resultado", title: "Resultado" }];
  let vistaActual = null, filasActuales = [];

  // escala del eje de los valores: la elige el usuario
  const grupos = (k) => new Set(filasActuales.map((f) => f[k])).size || 1;
  function cuantil(v, q) { const s = v.slice().sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))]; }
  function escala(campo, datos, base) {
    const e = estado.escala;
    if (e === "cero") return { ...base, zero: true };
    if (e === "log") return { ...base, type: "symlog", zero: false };
    if (e === "centro" && campo) {
      const v = datos.map((f) => f[campo]).filter((x) => x !== null);
      const lo = cuantil(v, .05), hi = cuantil(v, .95), m = (hi - lo) * .08;
      return { ...base, domain: [lo - m, hi + m], clamp: true, nice: false, zero: false };
    }
    return base;
  }
  const zoomEn = (ejes) => ({ name: "zoom", select: { type: "interval", encodings: ejes }, bind: "scales" });
  function altoVista() {   // el gráfico ocupa lo que queda de la tarjeta, así la sección entra en una pantalla
    const v = $("#vista"), leyenda = estado.color && TIPOS[estado.tipo].color ? (estado.color === "equipo" || estado.color === "piloto" ? 100 : 44) : 0, giro = (estado.tipo === "cajas" && grupos(estado.x) > 10) || estado.tipo === "calor" ? 40 : 0;
    return Math.max(200, v.clientHeight - 48 - leyenda - giro);
  }
  let altoPrevio = 0;
  window.addEventListener("resize", () => { const h = $("#vista").clientHeight; if (Math.abs(h - altoPrevio) > 30) { altoPrevio = h; dibujar(); } });
  function spec(datos) {
    const t = TIPOS[estado.tipo], x = estado.x, y = estado.y, col = estado.color;
    const tipoCat = (k) => (k === "anio" ? "ordinal" : "nominal");
    const colorEnc = col ? { field: col, type: tipoCat(col), title: CAT[col], scale: escalaColor(col, datos),
                             legend: { orient: "top", columns: col === "equipo" || col === "piloto" ? 6 : undefined } } : undefined;
    const base = { $schema: "https://vega.github.io/schema/vega-lite/v6.json", width: "container", height: altoVista(),
                   data: { values: datos }, config: { font: "Titillium Web, sans-serif", axis: { labelFontSize: 12, titleFontSize: 13,
                   gridColor: "#E6DED0", domainColor: "#B9AE9A" }, view: { stroke: null }, background: null,
                   legend: { labelFontSize: 12, titleFontSize: 12 } } };
    const enMedida = (campo) => estado.medida === "count"
      ? { aggregate: "count", type: "quantitative", title: "Cantidad de filas" }
      : { field: campo, aggregate: estado.medida, type: "quantitative", title: `${MEDIDA[estado.medida]} de: ${etq(campo).toLowerCase()}` };

    if (estado.tipo === "dispersion") {
      const capas = [{ mark: { type: "circle", clip: true, size: 30, opacity: 0.5 },
        params: [{ name: "zoom", select: "interval", bind: "scales" }],
        encoding: { x: { field: x, type: "quantitative", title: etq(x), scale: { zero: false } },
                    y: { field: y, type: "quantitative", title: etq(y), scale: escala(y, datos, { zero: false, reverse: NUM[y][1] === "puesto" }) },
                    color: colorEnc || { value: CFG.colores.tinta },
                    tooltip: [...TOOL, { field: x, title: etq(x), format: ".2f" }, { field: y, title: etq(y), format: ".2f" }] } }];
      if (estado.tendencia) capas.push({ transform: [{ loess: y, on: x, bandwidth: 0.5 }],
        mark: { type: "line", clip: true, color: CFG.colores.rojo, strokeWidth: 3 }, encoding: { x: { field: x, type: "quantitative" }, y: { field: y, type: "quantitative" } } });
      return { ...base, layer: capas };
    }
    if (estado.tipo === "barras") {
      const muchos = new Set(datos.map((f) => f[x])).size > 25;
      const tr = muchos ? [{ joinaggregate: [{ op: "count", as: "n" }], groupby: [x] },
                           { window: [{ op: "dense_rank", as: "orden" }], sort: [{ field: "n", order: "descending" }] },
                           { filter: "datum.orden <= 25" }] : [];
      return { ...base, transform: tr,
        params: [zoomEn(["x"])], mark: { type: "bar", clip: true, color: CFG.colores.rojo, cornerRadiusEnd: 3 },
        encoding: { y: { field: x, type: tipoCat(x), title: CAT[x], sort: x === "anio" || x === "zona" ? "ascending" : "-x" },
                    x: { ...enMedida(y), scale: escala(null, datos, {}) }, tooltip: [{ field: x, title: CAT[x] }, { ...enMedida(y), format: ".2f" }, { aggregate: "count", title: "Filas" }] } };
    }
    if (estado.tipo === "histograma") {
      return { ...base, params: [zoomEn(["y"])], mark: { type: "bar", clip: true, binSpacing: 1 },
        encoding: { x: { field: x, bin: { maxbins: 30 }, title: etq(x) }, y: { aggregate: "count", title: "Cantidad de filas", scale: escala(null, datos, {}) },
                    color: colorEnc || { value: CFG.colores.rojo }, tooltip: [{ field: x, bin: true, title: etq(x) }, { aggregate: "count", title: "Filas" }] } };
    }
    if (estado.tipo === "cajas") {
      const ex = { field: x, type: tipoCat(x), title: CAT[x], sort: x === "anio" || x === "zona" ? "ascending" : { field: y, op: "median" }, axis: { labelAngle: grupos(x) <= 10 ? 0 : -35, labelLimit: 130 } };
      const ey = { field: y, type: "quantitative", title: etq(y), scale: escala(y, datos, { zero: false, reverse: NUM[y][1] === "puesto" }) };
      return { ...base, encoding: { x: ex, y: ey }, layer: [
        { mark: { type: "boxplot", clip: true, extent: 1.5, size: Math.min(70, Math.max(10, 600 / grupos(x))), color: CFG.colores.rojo, median: { color: "#fff", strokeWidth: 2 }, outliers: estado.escala === "centro" ? false : { size: 12, opacity: .35 }, rule: { color: CFG.colores.rojo } } },
        { params: [zoomEn(["y"])], mark: { type: "tick", opacity: 0 } } ] };
    }
    if (estado.tipo === "evolucion") {
      if (col === "equipo" || col === "piloto") {   // los 8 grupos con más filas, así la leyenda muestra solo esos
        const n = {}; datos.forEach((f) => (n[f[col]] = (n[f[col]] || 0) + 1));
        const top = new Set(Object.entries(n).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k]) => k));
        datos = datos.filter((f) => top.has(f[col]));
        base.data = { values: datos };
        colorEnc.scale = escalaColor(col, datos);
      }
      return { ...base, params: [zoomEn(["y"])], mark: { type: "line", clip: true, point: true, strokeWidth: 2.5 },
        encoding: { x: { field: "anio", type: "ordinal", title: "Temporada", axis: { labelAngle: 0 } },
                    y: { ...enMedida(y), scale: escala(null, datos, { zero: false, reverse: estado.medida !== "count" && NUM[y][1] === "puesto" }) },
                    color: colorEnc || { value: CFG.colores.rojo }, tooltip: [{ field: "anio", title: "Temporada" },
                    ...(col ? [{ field: col, title: CAT[col] }] : []), { ...enMedida(y), format: ".2f" }] } };
    }
    if (estado.tipo === "calor") {
      const eje = (k, titulo) => NUM[k][1] === "puesto"
        ? { field: k, type: "ordinal", title: titulo, sort: "ascending", axis: { labelAngle: 0 } }
        : { field: k, bin: { maxbins: 25 }, title: titulo };
      return { ...base, mark: "rect",
        encoding: { x: eje(x, etq(x)), y: eje(y, etq(y)),
                    color: { aggregate: "count", title: "Filas", scale: { scheme: "reds" } },
                    tooltip: [{ ...eje(x, etq(x)) }, { ...eje(y, etq(y)) }, { aggregate: "count", title: "Filas" }] } };
    }
  }

  function textos(datos) {
    const t = estado.tipo, x = estado.x, y = estado.y, col = estado.color;
    const color = col ? `, con color según ${CAT[col].toLowerCase()}` : "";
    const L = {
      dispersion: () => [`${etq(y)} según ${etq(x).toLowerCase()}`, `Cada punto es un piloto en un Gran Premio${color}. Pasá el mouse para ver quién es; arrastrá para moverte y usá la rueda para acercarte.`],
      barras: () => [estado.medida === "count" ? `Cuántas filas hay, por ${CAT[x].toLowerCase()}` : `${MEDIDA[estado.medida]} de ${etq(y).toLowerCase()}, por ${CAT[x].toLowerCase()}`, `Cada barra resume las filas de un grupo. ${new Set(datos.map((f) => f[x])).size > 25 ? "Se muestran los 25 grupos con más filas." : ""}`],
      histograma: () => [`Cómo se reparte: ${etq(x).toLowerCase()}`, `Cada barra cuenta cuántas filas caen en ese rango${color}.`],
      cajas: () => [`${etq(y)}, por ${CAT[x].toLowerCase()}`, "Cada caja va del 25 % al 75 % de las filas del grupo; la raya blanca es la mediana y las líneas, el resto sin los casos raros."],
      evolucion: () => [estado.medida === "count" ? "Cuántas filas hay, temporada por temporada" : `${MEDIDA[estado.medida]} de ${etq(y).toLowerCase()}, temporada por temporada`, `Una línea por grupo${color}${col === "equipo" || col === "piloto" ? " (los 8 con más filas; filtrá para ver otros)" : ""}.`],
      calor: () => [`${etq(x)} contra ${etq(y).toLowerCase()}`, "Cuanto más oscura la celda, más filas cayeron ahí."],
    };
    return L[t]();
  }

  async function dibujar() {
    const datos = filtradas(); marcarFiltros(); actualizarEscala(); $("#zoom-ayuda").hidden = estado.tipo === "calor";
    filasActuales = datos;
    const [titulo, lectura] = textos(datos);
    $("#titulo").textContent = titulo; $("#lectura").textContent = lectura;
    $("#cuenta").textContent = `${datos.length.toLocaleString("es-AR")} de ${FILAS.length.toLocaleString("es-AR")} filas`;
    const aviso = $("#aviso");
    aviso.hidden = datos.length > 0;
    aviso.textContent = "No quedan filas con estos filtros. Probá sacar alguno.";
    if (!datos.length) { $("#vista").innerHTML = ""; return; }
    const r = await vegaEmbed($("#vista"), spec(datos), { actions: false, renderer: "canvas" });
    vistaActual = r.view;
    if (!silencioArmar) guardar("armar");
  }

  $("#csv").addEventListener("click", () => {
    const cols = Object.keys(FILAS[0]);
    const csv = [cols.join(","), ...filasActuales.map((f) => cols.map((c) => f[c] === null ? "" : JSON.stringify(f[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = "f1_grupo14_filtrado.csv"; a.click();
  });
  $("#png").addEventListener("click", async () => {
    if (!vistaActual) return;
    const a = document.createElement("a"); a.href = await vistaActual.toImageURL("png", 2); a.download = "f1_grupo14_grafico.png"; a.click();
  });

  (function carrusel() {
    const c = $("#preguntas");
    c.addEventListener("wheel", (e) => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); c.style.scrollBehavior = "auto"; c.scrollLeft += e.deltaY; c.style.scrollBehavior = ""; } }, { passive: false });
    let x0 = 0, s0 = 0, movio = false, apretado = false;
    c.addEventListener("pointerdown", (e) => { apretado = true; movio = false; x0 = e.clientX; s0 = c.scrollLeft; });
    window.addEventListener("pointermove", (e) => { if (!apretado) return; const d = e.clientX - x0;
      if (!movio && Math.abs(d) > 5) { movio = true; c.classList.add("arrastrando"); }
      if (movio) c.scrollLeft = s0 - d; });
    window.addEventListener("pointerup", () => { apretado = false; setTimeout(() => c.classList.remove("arrastrando"), 0); });
    c.addEventListener("click", (e) => { if (movio) { e.stopPropagation(); e.preventDefault(); movio = false; } }, true);   // si arrastró, no cuenta como clic
  })();

  function marcarFiltros() {
    let n = 0;
    [["#desde", (v) => +v !== aniosA[0]], ["#hasta", (v) => +v !== aniosA[aniosA.length - 1]], ["#f-equipo", Boolean], ["#f-piloto", Boolean], ["#f-resultado", Boolean], ["#f-zona", Boolean]]
      .forEach(([s, usado]) => { const u = usado($(s).value); $(s).parentElement.classList.toggle("usado", u); if (u) n++; });
    $("#activos").textContent = n ? (n === 1 ? "1 activo" : n + " activos") : "";
  }
  estado.escala = "auto";
  function actualizarEscala() {
    const t = estado.tipo, agregado = t === "barras" || t === "evolucion" || t === "histograma";
    $("#c-escala").hidden = t === "calor";
    $("#escala").querySelector('[value="centro"]').disabled = agregado;
    if (agregado && estado.escala === "centro") { estado.escala = "auto"; $("#escala").value = "auto"; }
  }
  $("#escala").addEventListener("change", (e) => { estado.escala = e.target.value; dibujar(); });
  $$(".flecha-p").forEach((b) => b.addEventListener("click", () => {
    const c = $("#preguntas"); c.scrollBy({ left: +b.dataset.d * c.clientWidth * .8 }); }));
  let silencioArmar = false;
  const FILTROS = { desde: "#desde", hasta: "#hasta", eq: "#f-equipo", pi: "#f-piloto", re: "#f-resultado", zo: "#f-zona" };
  escribirEstado.armar = () => {
    const o = { tipo: estado.tipo, x: estado.x, y: estado.y, color: estado.color, medida: estado.medida, tendencia: estado.tendencia, esc: estado.escala === "auto" ? "" : estado.escala, todo: !$("#extremos").checked };
    Object.entries(FILTROS).forEach(([k, s]) => { const v = $(s).value; if (v && !(k === "desde" && +v === aniosA[0]) && !(k === "hasta" && +v === aniosA[aniosA.length - 1])) o[k] = v; });
    if (!TIPOS[estado.tipo].x) delete o.x; if (!TIPOS[estado.tipo].y) delete o.y;
    return o;
  };
  function armarDesde(v, silencioso) {
    silencioArmar = !!silencioso;
    quitarPregunta(); limpiarFiltros();
    const tipo = TIPOS[v.tipo] ? v.tipo : "dispersion";
    cambiarTipo(tipo, { x: v.x, y: v.y, color: v.color === undefined ? undefined : v.color, medida: v.medida, tendencia: v.tendencia === true || v.tendencia === "1" });
    estado.escala = ["centro", "cero", "log"].includes(v.esc) ? v.esc : "auto"; $("#escala").value = estado.escala;
    $("#extremos").checked = !(v.todo === true || v.todo === "1");
    Object.entries(FILTROS).forEach(([k, s]) => { if (v[k] !== undefined && [...$(s).options].some((o) => o.value === String(v[k]))) $(s).value = v[k]; });
    if (v.f_resultado) $("#f-resultado").value = v.f_resultado;
    const p = [...$$(".pregunta")].find((b) => b.textContent === v.pregunta); if (p) p.classList.add("activa");
    dibujar().then(() => { silencioArmar = false; });
  }


  // =============================== 4 · todo conectado ==================================================
  // Cada gráfico es una vista; comparten un filtro que se arma con lo que el usuario toca en cada una.
  const filtro = { anio: null, equipo: null, rango: null };
  const vistasCon = {};
  const datosCon = FILAS.filter((f) => f.largada !== null && f.largada <= 20);
  const equiposCon = [...new Set(datosCon.map((f) => f.equipo))].sort();
  const pasa = (f, salvo) => (salvo === "anio" || filtro.anio === null || f.anio === filtro.anio)
    && (salvo === "equipo" || filtro.equipo === null || f.equipo === filtro.equipo)
    && (salvo === "rango" || filtro.rango === null || (f.largada >= filtro.rango[0] && f.largada <= filtro.rango[1]));
  const anchoDe = (id, resta = 110) => Math.max(260, $(id).parentElement.clientWidth - resta);
  function mirando() {
    const n = datosCon.filter((f) => pasa(f)).length;
    const chip = (on, t) => `<span class="chip ${on ? "on" : ""}">${t}</span>`;
    $("#mirando").innerHTML = `Mirando: ${chip(filtro.anio !== null, filtro.anio !== null ? "temporada " + filtro.anio : "todas las temporadas")}
      ${chip(filtro.equipo !== null, filtro.equipo || "todas las escuderías")}
      ${chip(filtro.rango !== null, filtro.rango ? `largando del ${filtro.rango[0]}.º al ${filtro.rango[1]}.º` : "largando de cualquier puesto")}
      <span>· ${n.toLocaleString("es-AR")} resultados</span>${filtro.anio !== null || filtro.equipo || filtro.rango ? '<button type="button" id="soltar">Ver todo</button>' : ""}`;
    const b = $("#soltar"); if (b) b.addEventListener("click", () => { filtro.anio = filtro.equipo = filtro.rango = null; dibujarConectado(); });
  }
  // Los tres gráficos se crean una sola vez; al tocar algo solo se les cambian los datos y lo resaltado.
  const vCon = {};
  async function crearConectado() {
    const [ra, rb, rc] = await Promise.all([embed("#g-con-a", CFG.specs.conA), embed("#g-con-b", CFG.specs.conB), embed("#g-con-c", CFG.specs.conC)]);
    vCon.a = ra.view; vCon.b = rb.view; vCon.c = rc.view;
    vCon.a.addEventListener("click", (ev, item) => { if (item && item.datum && item.datum.anio !== undefined) { filtro.anio = filtro.anio === item.datum.anio ? null : item.datum.anio; dibujarConectado(); } });
    vCon.c.addEventListener("click", (ev, item) => { if (item && item.datum && item.datum.equipo) { filtro.equipo = filtro.equipo === item.datum.equipo ? null : item.datum.equipo; dibujarConectado(); } });
    let t; vCon.b.addSignalListener("rango", (n, v) => { clearTimeout(t); t = setTimeout(() => {
      const x = v && v.largada; const nuevo = x ? [Math.max(1, Math.ceil(x[0])), Math.min(20, Math.floor(x[1]))] : null;
      if (nuevo && nuevo[0] > nuevo[1]) return;
      if (JSON.stringify(nuevo) !== JSON.stringify(filtro.rango)) { filtro.rango = nuevo; dibujarConectado(); } }, 250); });
    dibujarConectado();
  }
  function dibujarConectado() {
    mirando();
    if (!vCon.a) return;
    if (!filtro.rango && vCon.b.signal("rango") && Object.keys(vCon.b.signal("rango")).length) {   // «Ver todo» borra también el tramo marcado
      vCon.b.signal("rango_x", []); }
    vCon.a.data("t", datosCon.filter((f) => pasa(f, "anio"))).signal("selAnio", filtro.anio === null ? -1 : filtro.anio).runAsync();
    vCon.b.data("t", datosCon.filter((f) => pasa(f, "rango"))).runAsync();
    vCon.c.data("t", datosCon.filter((f) => pasa(f, "equipo") && f.resultado === "Terminó")).signal("selEq", filtro.equipo || "").runAsync();
  }
  let anchoPrevio = window.innerWidth;
  window.addEventListener("resize", () => { if (vCon.a && Math.abs(window.innerWidth - anchoPrevio) > 40) { anchoPrevio = window.innerWidth; crearConectado(); } });

  // =============================== 5 · la carrera de las escuderías ===================================
  let vistaMov = null, timer = null, modo = "anio";
  const podiosPor = {};   // anio -> equipo -> podios
  FILAS.forEach((f) => { if (f.final <= 3) { podiosPor[f.anio] = podiosPor[f.anio] || {}; podiosPor[f.anio][f.equipo] = (podiosPor[f.anio][f.equipo] || 0) + 1; } });
  const todosEq = [...new Set(FILAS.map((f) => f.equipo))].sort();
  function tablaMov(a) {
    const t = {};
    anios.filter((x) => modo === "acum" ? x <= a : x === a).forEach((x) => Object.entries(podiosPor[x] || {}).forEach(([e, n]) => { t[e] = (t[e] || 0) + n; }));
    return Object.entries(t).map(([equipo, podios]) => ({ equipo, podios })).sort((p, q) => q.podios - p.podios).slice(0, 10);
  }
  const maxAnio = Math.max(...anios.map((x) => Math.max(0, ...Object.values(podiosPor[x] || {})))) + 2;
  const maxAcum = Math.ceil(Math.max(...tablaMovAcum().map((r) => r.podios)) / 10) * 10;
  function tablaMovAcum() { const m = modo; modo = "acum"; const r = tablaMov(anios[anios.length - 1]); modo = m; return r; }
  async function crearMovimiento() {
    const r = await embed("#g-movimiento", CFG.specs.movimiento);
    vistaMov = r.view; dibujarMovimiento();
  }
  function dibujarMovimiento() {
    const a = +$("#anio-mov").textContent, filas = tablaMov(a).map((r, i) => ({ ...r, orden: i }));
    const lider = filas[0], seg = filas[1];
    $("#lectura-mov").innerHTML = lider ? `${modo === "acum" ? `De 2018 a ${a}` : `En ${a}`}, <b>${lider.equipo}</b> subió al podio <b>${lider.podios}</b> veces` + (seg ? `; lo siguió ${seg.equipo} con ${seg.podios}.` : ".") : "";
    if (!vistaMov) return;
    vistaMov.data("t", filas).signal("tope", modo === "acum" ? maxAcum : maxAnio).runAsync();
  }
  function ponerAnio(a) { $("#anio-mov").textContent = a; $("#anio-slider").value = anios.indexOf(a); dibujarMovimiento(); }
  $("#anio-slider").max = anios.length - 1;
  $("#anio-slider").addEventListener("input", (e) => ponerAnio(anios[+e.target.value]));
  $$("#modo button").forEach((b) => b.addEventListener("click", () => {
    modo = b.dataset.m; $$("#modo button").forEach((x) => x.classList.toggle("activo", x === b)); dibujarMovimiento(); }));
  $("#play").addEventListener("click", () => {
    if (timer) { clearInterval(timer); timer = null; $("#play").textContent = "▶"; return; }
    let i = anios.indexOf(+$("#anio-mov").textContent); if (i >= anios.length - 1) { i = 0; ponerAnio(anios[0]); }
    $("#play").textContent = "❚❚";
    timer = setInterval(() => { i++; ponerAnio(anios[i]); if (i >= anios.length - 1) { clearInterval(timer); timer = null; $("#play").textContent = "▶"; } }, 1300);
  });

  // =============================== 6 · ¿quién gana? ==================================================
  const carrerasJuego = [...new Set(FILAS.filter((f) => f.largada !== null).map((f) => f.car))];
  let carreraQ = null, elegidos = [], revelado = false;
  let marcador = { yo: 0, grilla: 0, modelo: 0, n: 0 };
  try { marcador = JSON.parse(localStorage.getItem("quien-gana")) || marcador; } catch (e) { /* sin almacenamiento */ }
  const puntos = (podio, real) => podio.reduce((s, p, i) => s + (real[i] === p ? 3 : real.includes(p) ? 1 : 0), 0);
  function nuevaCarrera(car) {
    carreraQ = car || carrerasJuego[Math.floor(Math.random() * carrerasJuego.length)];
    elegidos = []; revelado = false; dibujarJuego(); guardar("quien");
  }
  escribirEstado.quien = () => ({ gp: carreraQ });
  function dibujarJuego() {
    const fs = FILAS.filter((f) => f.car === carreraQ).sort((a, b) => (a.largada ?? 99) - (b.largada ?? 99));
    $("#q-titulo").textContent = `${fs[0].gpl} ${fs[0].anio} · antes de largar`;
    $("#q-tabla").innerHTML = `<tr><th></th><th>Piloto</th><th>Largó</th><th>Clasif. (% de la pole)</th><th>Prácticas (% del mejor)</th><th>Campeonato</th></tr>` +
      fs.map((f) => { const k = elegidos.indexOf(f.piloto);
        return `<tr class="elegible ${k >= 0 ? "elegido" : ""}" data-p="${f.piloto}"><td>${k >= 0 ? `<span class="ex-marca">${k + 1}</span>` : ""}</td>
          <td><span class="eq" style="background:${colorEquipo(f.equipo)}"></span>${f.piloto}</td><td>${f.largada ?? "—"}</td>
          <td>${fmt(f.q_dbt, 2)}</td><td>${fmt(f.fp_soft, 2)}</td><td>${f.pos_camp ? f.pos_camp + ".º" : "—"}</td></tr>`; }).join("");
    $("#q-tabla").querySelectorAll("tr.elegible").forEach((tr) => tr.addEventListener("click", () => {
      if (revelado) return;
      const p = tr.dataset.p, k = elegidos.indexOf(p);
      if (k >= 0) elegidos.splice(k, 1); else if (elegidos.length < 3) elegidos.push(p);
      dibujarJuego();
    }));
    $("#revelar").disabled = elegidos.length < 3 || revelado;
    const real = [...fs].sort((a, b) => a.final - b.final).slice(0, 3).map((f) => f.piloto);
    const grilla = fs.slice(0, 3).map((f) => f.piloto);
    const modelo = [...fs].sort((a, b) => a.pm - b.pm).slice(0, 3).map((f) => f.piloto);
    const caja = (titulo, lista, pts, clase = "") => `<div class="podio ${clase}"><b>${titulo}${pts !== null ? `<span class="pts">${pts} pts</span>` : ""}</b><ol>${lista.map((p) => `<li>${p}</li>`).join("")}</ol></div>`;
    $("#podios").innerHTML = revelado
      ? caja("Lo que pasó", real, null, "real") + caja("Tu podio", elegidos, puntos(elegidos, real)) +
        caja("La grilla", grilla, puntos(grilla, real)) + caja("El modelo", modelo, puntos(modelo, real))
      : (elegidos.length ? caja("Tu podio, hasta ahora", elegidos, null) : "");
    $("#marcador").innerHTML = marcador.n
      ? `En ${marcador.n} carrera${marcador.n > 1 ? "s" : ""}: <b>vos ${marcador.yo}</b> · grilla ${marcador.grilla} · modelo ${marcador.modelo} puntos. <span class="nota">(3 por acertar el puesto, 1 por acertar que sube al podio)</span>`
      : `Elegí 3 pilotos tocando las filas: el primero que toques es tu ganador. <span class="nota">3 puntos por puesto exacto, 1 por acertar que sube al podio.</span>`;
    revelar.real = real; revelar.grilla = grilla; revelar.modelo = modelo;
  }
  function revelar() {
    revelado = true;
    marcador.n++; marcador.yo += puntos(elegidos, revelar.real); marcador.grilla += puntos(revelar.grilla, revelar.real); marcador.modelo += puntos(revelar.modelo, revelar.real);
    try { localStorage.setItem("quien-gana", JSON.stringify(marcador)); } catch (e) { /* no importa */ }
    dibujarJuego();
  }
  $("#revelar").addEventListener("click", revelar);
  $("#borrar").addEventListener("click", () => { if (!revelado) { elegidos = []; dibujarJuego(); } });
  $("#otra").addEventListener("click", () => nuevaCarrera());

  // =============================== llevar a una vista (récords y links) ===============================
  function aplicar(v) {
    if (v.v === "pilotos") { $("#pa").value = v.a; $("#pb").value = v.b || ""; dibujarPilotos(); ir("pilotos"); }
    else if (v.v === "armar") { armarDesde(v); ir("armar"); }
    else if (v.v === "quien") { nuevaCarrera(v.gp); ir("quien"); }
    else if (v.v && $("#" + v.v)) ir(v.v);
  }

  // =============================== arranque ===========================================================
  const inicial = Object.fromEntries(URLST.leer());
  dibujarPilotos(); mirando(); dibujarMovimiento();
  const perezosos = { conectado: crearConectado, movimiento: crearMovimiento };
  const obsPerezoso = new IntersectionObserver((ents) => ents.forEach((e) => {
    const id = e.target.id.replace(/^ex-/, "");
    if (e.isIntersecting && perezosos[id]) { const f = perezosos[id]; delete perezosos[id]; obsPerezoso.unobserve(e.target); f(); }
  }), { rootMargin: "400px 0px" });
  Object.keys(perezosos).forEach((id) => obsPerezoso.observe($("#" + id)));
  nuevaCarrera(inicial.v === "quien" && carrerasJuego.includes(inicial.gp) ? inicial.gp : undefined);
  armarDesde(inicial.v === "armar" ? inicial : { tipo: "dispersion", x: "q_dbt", y: "final", color: "resultado", tendencia: "1" }, inicial.v !== "armar");
  // con un link de esta parte: ir a la vista y volver a ubicarla mientras la página de arriba termina de dibujarse
  const secciones = ["records", "pilotos", "armar", "conectado", "movimiento", "quien"];
  if (inicial.v) [700, 1400, 2200, 3200, 4500, 6500].forEach((ms) => setTimeout(() => {
    const s = $("#" + (secciones.includes(inicial.v) ? inicial.v : "records"));
    const arriba = $("#subnav").offsetHeight + 6;
    if (s && Math.abs(s.getBoundingClientRect().top - arriba) > 40) window.scrollTo({ top: s.getBoundingClientRect().top + scrollY - arriba, behavior: "instant" });
  }, ms));
  if (inicial.v) setTimeout(() => { aplicar(inicial); setTimeout(() => { arrancando = false; }, 800); }, 300);
  else setTimeout(() => { arrancando = false; }, 800);
  window.addEventListener("hashchange", () => { const v = Object.fromEntries(URLST.leer()); if (v.v) aplicar(v); });
})();
