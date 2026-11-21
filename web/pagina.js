/* Lo que hace la página estática en el navegador (site/index.html):

     1. dibuja las specs de Vega-Lite con vega-embed (las exportó Altair en web/pagina.py);
     2. «Una temporada»: menú de temporada + pestañas, una spec por temporada y pestaña;
     3. las carreras animadas (las guiadas del Sector 3 y «Carrera por carrera»): los botones
        «Correr» y «Volver a la largada», que mueven la señal `avance` del gráfico de
        graficos/race_cars.py;
     4. «Probá el modelo»: el modelo calculado por web/modelo.js, y la carrera con los valores
        del usuario en la misma pista animada (`race_cars_sim`, con los recorridos calculados acá).

   Los datos grandes vienen dentro del HTML en gzip + base64 y se descomprimen al usarlos. */
(function () {
  "use strict";
  const CFG = JSON.parse(document.getElementById("config").textContent);
  const $ = (selector, raiz = document) => raiz.querySelector(selector);

  // ---- datos comprimidos -----------------------------------------------------------------------
  const cache = new Map();
  function datos(nombre) {
    if (!cache.has(nombre)) cache.set(nombre, (async () => {
      const b64 = document.getElementById("dato-" + nombre).textContent;
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const texto = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
      return JSON.parse(await new Response(texto).text());
    })());
    return cache.get(nombre);
  }

  // ---- gráficos --------------------------------------------------------------------------------
  async function dibujar(vista, nombre, opciones = {}) {
    try {
      // números en castellano en todos los gráficos: coma decimal y punto de miles
      const { spec, ...resto } = opciones;   // `spec`: una armada acá (sin nombre de dato)
      opciones = resto;
      return await vegaEmbed(vista, spec || await datos(nombre), {
        actions: false,
        formatLocale: { decimal: ",", thousands: ".", grouping: [3], currency: ["$", ""] },
        ...opciones,
      });
    } catch (error) {
      console.error(error);
      vista.innerHTML = '<p class="error">No se pudo dibujar este gráfico (' + nombre + "). " +
        "Probá con un navegador actualizado (Chrome, Firefox, Edge o Safari).</p>";
      return null;
    }
  }

  // ---- carreras animadas (graficos/race_cars.py) -----------------------------------------------
  // El gráfico se achica para entrar en el ancho disponible.
  function ajustarAutos(marco) {
    const vista = $(".vista", marco);
    if (!vista.scrollWidth) return;
    vista.style.transform = "none";
    const escala = Math.min(1, marco.clientWidth / vista.scrollWidth);
    vista.style.transform = "scale(" + escala + ")";
    marco.style.height = (vista.scrollHeight * escala) + "px";
  }
  window.addEventListener("resize", () => document.querySelectorAll(".grafico.autos .marco").forEach(ajustarAutos));

  // Los botones «Correr» y «Volver a la largada» de `caja` mueven la señal `avance`.
  // Devuelve la función que frena la animación.
  function animarCarrera(caja, view) {
    const DURACION = 6000;
    let cronometro = null;
    const frenar = () => { clearInterval(cronometro); cronometro = null; };
    $(".correr", caja).onclick = () => {
      frenar();
      const inicio = Date.now();
      cronometro = setInterval(() => {
        const t = Math.min(1, (Date.now() - inicio) / DURACION);
        view.signal("avance", t).runAsync();
        if (t >= 1) frenar();
      }, 30);
    };
    const largada = $(".largada", caja);   // «Probá el modelo» solo tiene «Correr animación»
    if (largada) largada.onclick = () => { frenar(); view.signal("avance", 0).runAsync(); };
    try {   // la pista de «Probá el modelo» no tiene menú de carrera
      view.addSignalListener("carrera", () => { frenar(); view.signal("avance", 0).runAsync(); });
    } catch (e) { /* sin señal `carrera` */ }
    ajustarAutos($(".marco", caja));
    return frenar;
  }

  /* Recorrido de carril de cada auto, la misma cuenta que `lane_paths` de graficos/race_cars.py
     (sin choques): la distancia al líder pasa de la formación de largada (`paso` puestos entre
     autos) a `behind`; el carril es el orden por esa distancia y cada cambio dura `cambio`.
     `autos`: [{ grid (1..N, sin empates), behind, ... }]. Devuelve las filas de `recorridos_sim`. */
  const suave = (x) => { x = Math.min(Math.max(x, 0), 1); return x * x * (3 - 2 * x); };
  function recorridos(autos, paso = 0.3, cambio = 0.04, pasos = 400, muestras = 7) {
    const orden = autos.map((_, k) => k).sort((a, b) => autos[a].grid - autos[b].grid);
    const n = orden.length, S = Array.from({ length: pasos + 1 }, (_, j) => j / pasos);
    const carril = orden.map(() => new Int16Array(pasos + 1));   // por lugar en `orden`
    const lugares = [...Array(n).keys()];
    for (let j = 0; j <= pasos; j++) {
      const e = suave(S[j]);
      const dist = orden.map((k) => {
        const inicio = paso * (autos[k].grid - 1);
        return inicio + e * (autos[k].behind - inicio);
      });
      [...lugares].sort((a, b) => dist[a] - dist[b] || a - b).forEach((q, r) => { carril[q][j] = r + 1; });
    }
    const filas = [];
    orden.forEach((k, q) => {
      const c = carril[q], a = autos[k], inicios = [], saltos = [];
      for (let j = 0; j < pasos; j++) {
        if (c[j + 1] === c[j]) continue;
        inicios.push(Math.min(Math.max((S[j] + S[j + 1]) / 2 - cambio / 2, 0), 1 - cambio));
        saltos.push(c[j + 1] - c[j]);
      }
      const puntos = new Set([0, 1]);
      for (const i of inicios) for (let m = 0; m < muestras; m++) puntos.add(i + cambio * m / (muestras - 1));
      const s = [...puntos].sort((x, y) => x - y);
      const y = s.map((v) => c[0] + inicios.reduce((t, i, u) => t + saltos[u] * suave((v - i) / cambio), 0));
      s.forEach((v, i) => filas.push({
        driver: a.driver, s: v, y: y[i], s_prev: i ? s[i - 1] : -1, y_prev: i ? y[i - 1] : y[i],
        g: a.grid - 1, behind: a.behind, color: a.color, elegido: a.elegido,
      }));
    });
    return filas;
  }

  /* Carreras guiadas del Sector 3 (scrollytelling), para pantallas de PC y notebook. Cada
     carrera es un escenario fijo que tapa la pantalla: a la izquierda el panel (título, pistas,
     «Cómo leer», el gráfico y el resumen), quieto; a la derecha, un lugar fijo
     (.guiada-notas) donde entra la tanda de notas activa, cada tarjeta a la altura de su
     recuadro en el gráfico (sin salirse del alto del gráfico). El scroll lo marcan paradas
     invisibles (.marca): la activa es la última que pasó el borde de arriba del panel. Al
     cambiar de tanda, si cambia la pista, los autos corren solos (CORRIDA ms) y después se
     prenden los recuadros (data-min..data-max); con la última tanda aparece el resumen. Al
     soltar el scroll, la página se acomoda en la parada siguiente (o la anterior), de una
     carrera a la otra sin cortes: el escenario de la segunda se monta sobre el de la primera.
     Según el ancho, se dibuja la versión completa del gráfico o la angosta (sin logos ni las
     columnas Δ y MEJORA). */
  const guiadas = [];
  const ANCHO_COMPLETO = 1250;          // px de la carrera guiada para la versión completa
  const CORRIDA = 1800;                 // ms que tardan los autos en llegar
  const MARGEN = 12;
  const sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");

  const modoGuiada = (g) => (g.clientWidth >= ANCHO_COMPLETO ? "completo" : "medio");
  const topeDe = (g) => {               // px desde arriba de la pantalla hasta el panel
    const v = parseFloat(g.style.getPropertyValue("--tope"));
    return Number.isNaN(v) ? MARGEN : v;
  };

  /* Dimensiona el gráfico según el espacio real y centra el panel: el gráfico escala para
     entrar a lo ancho (lo que deja la columna de notas) y a lo alto (la pantalla menos el
     título, «Cómo leer» y el resumen); el panel mide lo que el gráfico (o un mínimo para el
     texto) y queda arriba. Lo mismo con zoom: todo se mide en px de CSS. */
  function encajar(g) {
    const vista = $(".capa .vista", g);
    if (!vista || !vista.scrollWidth) return;
    for (const v of g.querySelectorAll(".capa .vista")) v.style.transform = "none";
    const vw = vista.scrollWidth, vh = vista.scrollHeight;
    const panel = $(".guiada-grafico", g), pasos = $(".guiada-pasos", g);
    const lienzo = $(".guiada-lienzo", g), alto = window.innerHeight;
    const gap = parseFloat(getComputedStyle(g).columnGap) || 0;
    const anchoMax = g.clientWidth - pasos.offsetWidth - gap - 2, MIN_PANEL = 560;
    // el panel usa todo el ancho disponible (así el título, «Cómo leer» y el resumen ocupan
    // pocas líneas y le dejan alto al gráfico); el gráfico escala para entrar a lo ancho y a lo
    // alto, y queda centrado en el panel
    g.style.setProperty("--panel-w", Math.max(MIN_PANEL, anchoMax) + "px");
    const fijo = panel.offsetHeight - lienzo.offsetHeight;          // título, «Cómo leer», resumen
    let s = Math.min(1.25, (anchoMax - 2) / vw, (alto - 2 * MARGEN - fijo) / vh);
    s = Math.max(s, 0.2);
    g._escala = s;
    g.style.setProperty("--lienzo-w", Math.floor(vw * s) + "px");
    g.style.setProperty("--lienzo-h", Math.floor(vh * s) + "px");
    for (const v of g.querySelectorAll(".capa .vista")) v.style.transform = "scale(" + s + ")";
    // el panel, arriba (pegado al texto que lo presenta; con pantallas altas, sobra abajo)
    g.style.setProperty("--tope", MARGEN + "px");
    // lo que sobra del escenario debajo del panel (la última carrera sube lo que sigue hasta ahí)
    g.style.setProperty("--sobra", Math.max(0, alto - MARGEN - panel.offsetHeight - 8) + "px");
    medirNotas(g);
  }
  // el lugar de las notas mide lo que el panel; --lienzo-y: dónde empieza el gráfico en él
  function medirNotas(g) {
    const panel = $(".guiada-grafico", g), lienzo = $(".guiada-lienzo", g);
    g.style.setProperty("--notas-h", panel.offsetHeight + "px");
    g.style.setProperty("--lienzo-y", lienzo.offsetTop + "px");
  }

  /* Ubica las tarjetas de una tanda a la altura de su recuadro: el número de la tarjeta queda a
     la par del recuadro; si dos se pisan, la de abajo baja; nunca quedan más arriba ni más
     abajo que el gráfico (si la última se pasa, suben las de abajo). */
  function alinearNotas(registro, grupo) {
    const g = registro.g, view = registro.views && registro.views[grupo.dataset.panel];
    const tarjetas = [...grupo.querySelectorAll(".paso-nota[data-fila]")];
    if (!view || !tarjetas.length) return;
    // la altura de cada fila la da la escala y del propio gráfico (en px del SVG, sin escalar)
    const escalaY = view.scale("y"), s = g._escala || 1;
    const origen = (view.origin && view.origin()) || view._origin || [0, 0];
    const notas = $(".guiada-notas", g), lienzo = $(".guiada-lienzo", g);
    const svg = $(".capa[data-panel='" + grupo.dataset.panel + "'] svg", g);
    if (!escalaY || !svg) return;
    const base = notas.getBoundingClientRect().top;
    const ySvg = svg.getBoundingClientRect().top - base;
    const techo = lienzo.getBoundingClientRect().top - base;
    // abajo, nunca más allá del fin del gráfico
    const piso = lienzo.getBoundingClientRect().bottom - base;
    const centro = (fila) => ySvg + (origen[1] + escalaY(fila)) * s;
    const medio = (t) => { const n = $(".num", t); return n.offsetTop + n.offsetHeight / 2; };
    const tops = tarjetas.map((t) => centro(Number(t.dataset.fila)) - medio(t));
    const GAP = 10;
    // si no entran todas en el alto del gráfico, van seguidas, sin pisarse, terminando justo
    // en el fin del gráfico (suben lo necesario, nunca bajan de él)
    const total = tarjetas.reduce((suma, t) => suma + t.offsetHeight, 0) + GAP * (tarjetas.length - 1);
    if (total > piso - techo) {
      let y = Math.max(0, piso - total);
      tarjetas.forEach((t) => { t.style.top = Math.round(y) + "px"; y += t.offsetHeight + GAP; });
      return;
    }
    let abajo = -Infinity;
    tops.forEach((y, i) => { tops[i] = Math.max(y, abajo + GAP, techo); abajo = tops[i] + tarjetas[i].offsetHeight; });
    let limite = piso;
    for (let i = tarjetas.length - 1; i >= 0; i--) {
      const h = tarjetas[i].offsetHeight;
      if (tops[i] + h > limite) tops[i] = Math.max(techo, limite - h);
      limite = tops[i] - GAP;
    }
    tarjetas.forEach((t, i) => { t.style.top = Math.round(tops[i]) + "px"; });
  }

  async function dibujarGuiada(registro) {
    const g = registro.g, modo = modoGuiada(g);
    g.classList.remove("modo-completo", "modo-medio");
    g.classList.add("modo-" + modo);
    registro.modo = modo;
    registro.views = {};
    registro.k = null;
    registro.gi = null;
    registro.corrida_de = null;
    await Promise.all([...g.querySelectorAll(".capa")].map(async (capa) => {
      const vista = $(".vista", capa);
      vista.replaceChildren();
      const r = await dibujar(vista, modo === "completo" ? capa.dataset.ancho : capa.dataset.compacto);
      if (r) registro.views[capa.dataset.panel] = r.view;
    }));
    encajar(g);
    moverGuiada(registro);
  }

  // Pone una pista en un estado; con `correr`, los autos van de la largada a la meta solos.
  function ponerPista(registro, panel, avance, pmin, pmax, correr) {
    const view = registro.views[panel];
    if (!view) return;
    cancelAnimationFrame(registro.corrida && registro.corrida[panel]);
    view.signal("paso_min", pmin).signal("paso", pmax);
    if (!correr || sinMovimiento.matches) { view.signal("avance", avance).runAsync(); return; }
    const inicio = performance.now();
    const cuadro = (ahora) => {
      const t = Math.min(1, (ahora - inicio) / CORRIDA);
      view.signal("avance", t).runAsync();
      if (t < 1) registro.corrida[panel] = requestAnimationFrame(cuadro);
    };
    registro.corrida = registro.corrida || {};
    view.signal("avance", 0).runAsync();
    registro.corrida[panel] = requestAnimationFrame(cuadro);
  }

  function moverGuiada(registro) {
    const { g, views } = registro;
    if (!views) return;
    const marcas = [...g.querySelectorAll(".marca")].filter((m) => m.offsetParent !== null);
    const linea = topeDe(g) + 40;       // un poco de margen: la parada cuenta al llegar casi al panel
    let k = -1;
    marcas.forEach((m, i) => { if (m.getBoundingClientRect().top <= linea) k = i; });
    if (k === registro.k) return;
    registro.k = k;
    const marca = marcas[k];
    const gi = marca ? Number(marca.dataset.grupo) : -1;
    const grupos = [...g.querySelectorAll(".grupo-pasos")];
    grupos.forEach((t, i) => { t.classList.toggle("activa", i === gi); t.classList.toggle("sale", i < gi); });
    // en qué parada se está: las tandas que tienen paradas a la vista
    const visibles = [...new Set(marcas.map((m) => Number(m.dataset.grupo)))];
    const parada = $(".parada", g);
    if (parada) parada.textContent = gi >= 0
      ? "Parada " + (visibles.indexOf(gi) + 1) + " de " + visibles.length + " · " + grupos[gi].dataset.nombre
      : "Bajá para empezar ↓";
    if (gi === registro.gi) return;
    const bajando = registro.gi === null || registro.gi === undefined || gi > registro.gi;
    registro.gi = gi;
    const activo = grupos[gi];
    const panel = activo ? activo.dataset.panel : "arriba";
    for (const el of g.querySelectorAll(".capa, .pista-rotulo")) el.classList.toggle("activa", el.dataset.panel === panel);
    // el resumen (debajo del gráfico) aparece con la última tanda: la de sin abandonos
    g.classList.toggle("con-resumen", !!activo && panel === "abajo");
    if (!activo) {                      // todavía antes de la primera parada: en la largada
      registro.corrida_de = null;
      ponerPista(registro, "arriba", 0, 0, 0, false);
      ponerPista(registro, "abajo", 0, 0, 0, false);
      return;
    }
    const min = Number(activo.dataset.min), max = Number(activo.dataset.max);
    const hasta = Number(activo.dataset.hasta);   // «Cómo leer»: 0, los autos en la largada
    // los autos corren al llegar bajando a una pista que todavía no corrió
    const corre = bajando && hasta > 0 && registro.corrida_de !== panel;
    if (hasta > 0) registro.corrida_de = panel;
    ponerPista(registro, panel, hasta, min, max, corre);
    // la pista que no se ve queda como corresponde: la de arriba, terminada; la de abajo, sin largar
    if (panel === "abajo") ponerPista(registro, "arriba", 1, 99, 99, false);
    else ponerPista(registro, "abajo", 0, 0, 0, false);
    alinearNotas(registro, activo);
  }

  function moverGuiadas() {
    // un escenario está «montado» cuando ya quedó fijo arriba (la segunda carrera aparece recién ahí)
    for (const r of guiadas) {
      const caja = r.g.getBoundingClientRect();
      r.g.classList.toggle("montada", caja.top <= 1);
      // terminada: el escenario dejó de estar fijo (se ve lo que sigue, pegado al panel)
      r.g.classList.toggle("terminada", caja.bottom <= window.innerHeight + 1);
    }
    guiadas.forEach(moverGuiada);
  }

  // Al soltar el scroll dentro de una carrera, se acomoda en el grupo siguiente (o anterior).
  // Mientras dura ese acomodo (`objetivo`), no se encadena otro: solo lo corta el usuario.
  // No se acomoda: con «menos movimiento» (el scroll queda como lo deja el usuario), mientras
  // se arrastra la barra de scroll, ni después de las flechas del teclado (para leer despacio).
  let ultimoY = window.scrollY, direccion = 1, espera = null, objetivo = null, vence = null;
  let arrastrando = false, conFlechas = false;
  const soltarObjetivo = () => { objetivo = null; clearTimeout(vence); };
  for (const evento of ["wheel", "touchstart", "keydown", "mousedown"]) {
    window.addEventListener(evento, soltarObjetivo, { passive: true });
  }
  window.addEventListener("mousedown", (e) => {   // la barra está fuera del ancho del documento
    if (e.clientX >= document.documentElement.clientWidth) arrastrando = true;
  });
  window.addEventListener("mouseup", () => { arrastrando = false; });
  window.addEventListener("keydown", (e) => { conFlechas = e.key === "ArrowDown" || e.key === "ArrowUp"; });
  for (const evento of ["wheel", "touchstart"]) {
    window.addEventListener(evento, () => { conFlechas = false; }, { passive: true });
  }
  function acomodar() {
    if (objetivo !== null) {            // es el scroll del propio acomodo: no se encadena
      if (Math.abs(window.scrollY - objetivo) < 6) soltarObjetivo();
      return;
    }
    if (sinMovimiento.matches || arrastrando || conFlechas) return;
    // las paradas de todas las carreras, en orden: el panel recién fijado (en la largada) y
    // cada parada invisible; la salida solo después de la última carrera
    const listas = guiadas.filter((r) => r.views), alto = window.innerHeight, y = window.scrollY;
    const paradas = [];
    listas.forEach((r, i) => {
      const caja = r.g.getBoundingClientRect(), linea = topeDe(r.g);
      paradas.push(caja.top + y);       // el escenario recién fijado (tapa toda la pantalla)
      for (const m of r.g.querySelectorAll(".marca")) {
        if (m.offsetParent !== null) paradas.push(m.getBoundingClientRect().top + y - linea);
      }
      if (i === listas.length - 1) paradas.push(caja.bottom + y - alto);
    });
    // fuera de las carreras (incluido el título y el texto de arriba) el scroll queda libre: se
    // engancha cuando la primera carrera ya está llegando arriba de la pantalla
    if (!paradas.length || y < paradas[0] - alto * 0.2 || y > paradas[paradas.length - 1] + 4) return;
    const destino = direccion > 0
      ? paradas.filter((q) => q > y + 4).sort((m, n) => m - n)[0]
      : paradas.filter((q) => q < y - 4).sort((m, n) => n - m)[0];
    // (de una parada a otra hay una pantalla y algo: más lejos, es que se salió de las carreras)
    if (destino === undefined || Math.abs(destino - y) > alto * 2.5) return;
    objetivo = Math.round(destino);
    vence = setTimeout(soltarObjetivo, 1500);      // por si el navegador no llega justo
    window.scrollTo({ top: objetivo, behavior: sinMovimiento.matches ? "auto" : "smooth" });
  }

  let pedido = false;
  window.addEventListener("scroll", () => {
    const y = window.scrollY;
    if (y !== ultimoY) direccion = y > ultimoY ? 1 : -1;
    ultimoY = y;
    clearTimeout(espera);
    espera = setTimeout(acomodar, 160);
    if (pedido) return;
    pedido = true;
    requestAnimationFrame(() => { pedido = false; moverGuiadas(); });
  }, { passive: true });
  window.addEventListener("resize", () => {
    for (const r of guiadas) {
      if (!r.views) continue;
      if (modoGuiada(r.g) !== r.modo) dibujarGuiada(r);
      else { encajar(r.g); r.k = null; moverGuiada(r); const a = $(".grupo-pasos.activa", r.g); if (a) alinearNotas(r, a); }
    }
  });
  const todasGuiadas = document.querySelectorAll(".guiada");
  if (todasGuiadas.length) todasGuiadas[todasGuiadas.length - 1].classList.add("ultima");
  for (const g of todasGuiadas) {
    const registro = { g, views: null, modo: null, k: null, gi: null, corrida: {}, corrida_de: null };
    g._registro = registro;   // para revisar desde la consola
    guiadas.push(registro);
    // al señalar una tarjeta (mouse o teclado), su recuadro en el gráfico queda solo a pleno
    const foco = (nota, n) => {
      const panel = nota.closest(".grupo-pasos").dataset.panel, view = registro.views && registro.views[panel];
      if (view) view.signal("foco", n).runAsync();
    };
    for (const nota of g.querySelectorAll(".paso-nota[data-n]")) {
      const n = Number(nota.dataset.n);
      nota.addEventListener("mouseenter", () => foco(nota, n));
      nota.addEventListener("mouseleave", () => foco(nota, 0));
      nota.addEventListener("focus", () => foco(nota, n));
      nota.addEventListener("blur", () => foco(nota, 0));
    }
    // si el panel cambia de alto (otra pista resaltada), el lugar de las notas se acomoda
    if ("ResizeObserver" in window) new ResizeObserver(() => medirNotas(g)).observe($(".guiada-grafico", g));
    const plegada = $(".como-leer.plegada", g);
    if (plegada) plegada.addEventListener("toggle", () => {
      if (!registro.views) return;
      encajar(g);
      const a = $(".grupo-pasos.activa", g);
      if (a) alinearNotas(registro, a);
    });
    if ("IntersectionObserver" in window) {
      const obs = new IntersectionObserver((es) => {
        if (es.some((e) => e.isIntersecting)) { obs.disconnect(); dibujarGuiada(registro); }
      }, { rootMargin: "800px" });
      obs.observe(g);
    } else {
      dibujarGuiada(registro);
    }
  }

  // Los fijos (tallo, pasos, panorama): se dibujan cuando están por entrar en
  // pantalla.
  const fijos = document.querySelectorAll(".grafico[data-spec]");
  const alVer = async (grafico) => {
    const resultado = await dibujar($(".vista", grafico), grafico.dataset.spec);
    if (resultado && grafico.classList.contains("autos")) animarCarrera(grafico, resultado.view);
  };
  if ("IntersectionObserver" in window) {
    const observador = new IntersectionObserver((entradas) => {
      for (const e of entradas) if (e.isIntersecting) { observador.unobserve(e.target); alVer(e.target); }
    }, { rootMargin: "600px" });
    fijos.forEach((g) => observador.observe(g));
  } else {
    fijos.forEach(alVer);
  }

  // ---- Todos los pilotos: filtros, resumen, gráfico agrupado y tabla ---------------------------
  // Una fila por piloto en cada GP (datos «pilotos», armados en web/pagina.py). Los errores van con
  // signo, como en toda la página: + = terminó más adelante de lo predicho. Con «Terminaron», los
  // puestos se reordenan entre los que terminaron (la cuenta «sin abandonos» de los títulos).
  (async function explorador() {
    const caja = $("#explorador");
    if (!caja) return;
    const D = await datos("pilotos"), C = D.columnas, N = C.a.length;
    const AZUL = "#2166AC", AMBAR = "#B8660B";
    const num = (x, d = 2) => x.toFixed(d).replace(".", ",");
    const entero = (x) => (Number.isInteger(x) ? String(x) : num(x, 1));
    const signo = (x) => (x > 0 ? "+" + entero(x) : x < 0 ? "−" + entero(-x) : "0");
    const filtro = (k) => $('[data-filtro="' + k + '"]', caja);
    const opciones = (sel, lista, todas) => {
      const previo = sel.value;
      sel.replaceChildren(new Option(todas, ""), ...lista.map(([v, t]) => new Option(t, v)));
      sel.value = lista.some(([v]) => String(v) === previo) ? previo : "";
    };
    const anios = [...new Set(C.a)].sort((x, y) => y - x);
    opciones(filtro("anio"), anios.map((a) => [a, a]), "Todas");
    opciones(filtro("piloto"), D.pilotos.map((p, i) => [i, p]), "Todos");
    opciones(filtro("equipo"), D.equipos.map((e, i) => [i, e]), "Todas");
    function opcionesGp() {   // los GP de la temporada elegida (o todos)
      const anio = filtro("anio").value, hay = new Set();
      for (let i = 0; i < N; i++) if (!anio || C.a[i] === +anio) hay.add(C.gp[i]);
      opciones(filtro("gp"), D.gps.map((g, i) => [i, g]).filter(([i]) => hay.has(i)), "Todos");
    }
    opcionesGp();

    // ---- filtrar --------------------------------------------------------------------------------
    let filas = [];   // las filas que pasan, ya con sus errores
    function filtrar() {
      const v = Object.fromEntries([...caja.querySelectorAll("[data-filtro]")].map((e) => [e.dataset.filtro, e.value]));
      const soloTerm = v.resultado === "termino";
      filas = [];
      for (let i = 0; i < N; i++) {
        if (v.anio && C.a[i] !== +v.anio) continue;
        if (v.gp && C.gp[i] !== +v.gp) continue;
        if (v.piloto && C.p[i] !== +v.piloto) continue;
        if (v.equipo && C.e[i] !== +v.equipo) continue;
        if (v.desde && C.l[i] < +v.desde) continue;
        if (v.hasta && C.l[i] > +v.hasta) continue;
        if (v.resultado === "termino" && C.ab[i]) continue;
        if (v.resultado === "abandono" && !C.ab[i]) continue;
        const [m, l, f] = soloTerm ? [C.ma[i], C.ga[i], C.fa[i]] : [C.m[i], C.lg[i], C.f[i]];
        const em = m - f, eg = l - f;   // + = terminó más adelante de lo predicho
        const quien = Math.abs(em) < Math.abs(eg) ? "modelo" : Math.abs(em) > Math.abs(eg) ? "grilla" : "igual";
        if (v.quien && quien !== v.quien) continue;
        filas.push({ i, em, eg, quien });
      }
      caja.classList.toggle("con-filtros", Object.values(v).some(Boolean));
      resumir(soloTerm); graficar();
    }

    // ---- resumen --------------------------------------------------------------------------------
    function resumir(soloTerm) {
      const n = filas.length;
      const carrerasN = new Set(filas.map((x) => C.a[x.i] * 100 + C.r[x.i])).size;
      $(".exp-cuenta", caja).textContent = n
        ? n.toLocaleString("es-AR") + (n === 1 ? " participación" : " participaciones") + " en " +
          carrerasN.toLocaleString("es-AR") + (carrerasN === 1 ? " carrera" : " carreras") +
          (soloTerm ? " · puestos reordenados entre los que terminaron" : "")
        : "Ninguna fila cumple todos los filtros.";
      if (!n) { $(".exp-resumen", caja).innerHTML = ""; return; }
      const mae = (k) => filas.reduce((s, x) => s + Math.abs(x[k]), 0) / n;
      const cuantos = (q) => filas.filter((x) => x.quien === q).length;
      const abandonos = filas.filter((x) => C.ab[x.i]).length;
      const mm = mae("em"), mg = mae("eg");
      const tarjeta = (rotulo, valor, ayuda, clase = "") =>
        '<div class="metrica ' + clase + '"><span class="rotulo">' + rotulo + '</span><span class="valor">' +
        valor + '</span><span class="ayuda">' + ayuda + "</span></div>";
      $(".exp-resumen", caja).innerHTML =
        tarjeta("Error del modelo", num(mm), "puestos por piloto, en promedio", "es-modelo") +
        tarjeta("Error de la grilla", num(mg), "si terminaran donde largaron", "es-grilla") +
        tarjeta("Quién acertó más", num(100 * cuantos("modelo") / n, 0) + " % · " + num(100 * cuantos("grilla") / n, 0) + " %",
          "filas donde se equivocó menos el modelo · la grilla (empates: " + num(100 * cuantos("igual") / n, 0) + " %)") +
        tarjeta("Abandonaron", num(100 * abandonos / n, 0) + " %", abandonos.toLocaleString("es-AR") + " de estas filas");
    }

    // ---- gráfico agrupado ------------------------------------------------------------------------
    const GRUPOS = [   // [clave, texto, valor de la fila, texto del grupo, filtro que pone el clic]
      ["anio", "Temporada", (i) => C.a[i], (g) => String(g), "anio"],
      ["gp", "Gran Premio", (i) => C.gp[i], (g) => D.gps[g], "gp"],
      ["equipo", "Escudería", (i) => C.e[i], (g) => D.equipos[g], "equipo"],
      ["piloto", "Piloto", (i) => C.p[i], (g) => D.pilotos[g], "piloto"],
      ["largada", "Largada", (i) => C.l[i], (g) => "Largó " + g + ".º", "largada"],
    ];
    let agrupar = "anio", vistaGrafico = null;
    const botones = $(".exp-agrupar", caja);
    GRUPOS.forEach(([k, t]) => {
      const b = document.createElement("button");
      Object.assign(b, { type: "button", textContent: t });
      b.dataset.grupo = k;
      b.setAttribute("aria-pressed", String(k === agrupar));
      b.addEventListener("click", () => {
        agrupar = k;
        botones.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        graficar();
      });
      botones.append(b);
    });
    const MAX_GRUPOS = 25;
    async function graficar() {
      const [, titulo, valor, texto] = GRUPOS.find((g) => g[0] === agrupar);
      const acum = new Map();
      for (const x of filas) {
        const g = valor(x.i), a = acum.get(g) || { g, n: 0, m: 0, l: 0 };
        a.n++; a.m += Math.abs(x.em); a.l += Math.abs(x.eg); acum.set(g, a);
      }
      let grupos = [...acum.values()].map((a) => ({ grupo: a.g, nombre: texto(a.g), n: a.n, modelo: a.m / a.n, grilla: a.l / a.n }));
      const natural = agrupar === "anio" || agrupar === "largada";
      // los que tienen pocas filas no dicen mucho: se muestran los que más tienen
      const recorte = grupos.length > MAX_GRUPOS;
      if (recorte) grupos = grupos.sort((x, y) => y.n - x.n).slice(0, MAX_GRUPOS);
      grupos.sort(natural ? (x, y) => x.grupo - y.grupo : (x, y) => (y.grilla - y.modelo) - (x.grilla - x.modelo));
      $(".exp-ayuda", caja).textContent = !grupos.length ? "" :
        (recorte ? "Los " + MAX_GRUPOS + " grupos con más filas. " : "") +
        (natural ? "" : "Ordenados de donde más le gana el modelo a la grilla a donde más pierde. ") +
        "Clic en un grupo para filtrar por él.";
      const vista = $(".exp-grafico .vista", caja);
      if (vistaGrafico) { vistaGrafico.finalize(); vistaGrafico = null; }
      if (!grupos.length) { vista.replaceChildren(); return; }
      const largo = grupos.map((g) => ({ ...g, quien: "Modelo", error: g.modelo }))
        .concat(grupos.map((g) => ({ ...g, quien: "Grilla", error: g.grilla })));
      const y = { field: "nombre", type: "nominal", sort: grupos.map((g) => g.nombre), title: null,
        axis: { labelFontSize: 13, labelColor: "#1F2328", labelLimit: 220, domain: false, ticks: false } };
      const tip = [{ field: "nombre", title: titulo }, { field: "n", title: "Filas" },
        { field: "modelo", title: "Error del modelo", format: ".2f" },
        { field: "grilla", title: "Error de la grilla", format: ".2f" }];
      const spec = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        width: "container", height: Math.max(80, grupos.length * 24),
        background: "transparent", config: { view: { stroke: null }, font: "Titillium Web, sans-serif",
          axis: { labelColor: "#575C63", titleColor: "#575C63", gridColor: "#DDD5C7", domainColor: "#DDD5C7" } },
        data: { values: largo },
        layer: [
          { mark: { type: "rule", color: "#575C63", strokeWidth: 2, opacity: 0.5 },
            transform: [{ filter: "datum.quien == 'Modelo'" }],
            encoding: { y, x: { field: "modelo", type: "quantitative" }, x2: { field: "grilla" }, tooltip: tip } },
          { mark: { type: "point", filled: false, size: 130, strokeWidth: 2.5, cursor: "pointer" },
            transform: [{ filter: "datum.quien == 'Grilla'" }],
            encoding: { y, x: { field: "error", type: "quantitative" }, color: { field: "quien", type: "nominal" }, tooltip: tip } },
          { mark: { type: "circle", size: 70, opacity: 1, cursor: "pointer" },
            transform: [{ filter: "datum.quien == 'Modelo'" }],
            encoding: {
              y, tooltip: tip, color: { field: "quien", type: "nominal",
                scale: { domain: ["Modelo", "Grilla"], range: [AZUL, AMBAR] },
                legend: { orient: "top", title: null, labelFontSize: 13, labelColor: "#1F2328" } },
              x: { field: "error", type: "quantitative", scale: { zero: false },
                title: "Error promedio (puestos por piloto; menos es mejor)" } } },
          { mark: { type: "text", align: "left", dx: 10, fontSize: 12, color: "#575C63" },
            transform: [{ filter: "datum.quien == 'Modelo'" }, { calculate: "max(datum.modelo, datum.grilla)", as: "fin" },
              { calculate: "datum.n + (datum.n == 1 ? ' fila' : ' filas')", as: "rot" }],
            encoding: { y, x: { field: "fin", type: "quantitative" }, text: { field: "rot" } } },
        ],
      };
      const r = await dibujar(vista, null, { spec });
      if (!r) return;
      vistaGrafico = r.view;
      r.view.addEventListener("click", (_, item) => {
        if (!item || !item.datum || item.datum.grupo === undefined) return;
        const g = item.datum.grupo, destino = GRUPOS.find((x) => x[0] === agrupar)[4];
        if (destino === "largada") { filtro("desde").value = g; filtro("hasta").value = g; }
        else { filtro(destino).value = g; if (destino === "anio") opcionesGp(); }
        filtrar();
      });
    }

    // ---- CSV (con punto y coma y coma decimal, para abrirlo en una planilla en castellano) ------
    $(".exp-csv", caja).addEventListener("click", () => {
      const cab = ["temporada", "fecha", "gran_premio", "sigla", "piloto", "escuderia", "largada",
        "prediccion_modelo", "final", "abandono", "error_modelo", "error_grilla", "clasificacion_pct", "puntos_antes"];
      const lineas = filas.map(({ i, em, eg }) => [C.a[i], C.r[i], D.gps[C.gp[i]], C.s[i], D.pilotos[C.p[i]],
        D.equipos[C.e[i]], C.l[i], C.m[i], C.f[i], C.ab[i] ? "si" : "no", entero(em), entero(eg),
        C.q[i] === null ? "" : num(C.q[i]), C.pts[i] ?? ""].join(";"));
      const url = URL.createObjectURL(new Blob(["﻿" + [cab.join(";"), ...lineas].join("\n")], { type: "text/csv" }));
      Object.assign(document.createElement("a"), { href: url, download: "f1_pilotos_filtrados.csv" }).click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

    caja.querySelectorAll("[data-filtro]").forEach((e) => e.addEventListener(e.tagName === "INPUT" ? "input" : "change", () => {
      if (e.dataset.filtro === "anio") opcionesGp();
      filtrar();
    }));
    $(".exp-limpiar", caja).addEventListener("click", () => {
      caja.querySelectorAll("[data-filtro]").forEach((e) => { e.value = ""; });
      opcionesGp(); filtrar();
    });
    filtrar();
  })();

  // ---- Una temporada: menú + pestañas ----------------------------------------------------------
  const temporada = $("#temporada");
  const pestanias = [...document.querySelectorAll(".pestanias button")];
  const dibujados = new Map();          // pestaña -> { anio, resultado de vegaEmbed }
  let frenar = () => {};                // frena la animación de «Carrera por carrera»
  const cajaAutos = $('[data-panel="autos"] .grafico.autos');

  async function mostrarPestania() {
    const activa = pestanias.find((b) => b.getAttribute("aria-selected") === "true").dataset.pestania;
    for (const panel of document.querySelectorAll(".panel")) panel.hidden = panel.dataset.panel !== activa;
    const anio = temporada.value, previo = dibujados.get(activa);
    if (previo && previo.anio === anio) { if (activa === "autos") ajustarAutos($(".marco", cajaAutos)); return; }
    if (previo && previo.resultado) previo.resultado.finalize();
    const registro = { anio, resultado: null };
    dibujados.set(activa, registro);
    const vista = $('[data-panel="' + activa + '"] .vista');
    vista.replaceChildren();
    if (activa !== "autos") { registro.resultado = await dibujar(vista, activa + "-" + anio); return; }

    frenar();
    $("#selector-autos").replaceChildren();
    const resultado = await dibujar(vista, "autos-" + anio, { bind: "#selector-autos" });
    registro.resultado = resultado;
    if (!resultado || dibujados.get("autos") !== registro) return;
    frenar = animarCarrera(cajaAutos, resultado.view);
  }

  function notaTemporada() {
    const anio = Number(temporada.value);
    $("#nota-temporada").textContent = anio < CFG.anioTest
      ? "Cada carrera de " + anio + " la predice un modelo que no la vio: el mismo modelo elegido, " +
        "entrenado con las otras temporadas (la validación cruzada por temporada del notebook)."
      : CFG.anioTest + " es el test: lo predice el modelo final, entrenado con 2018-2025.";
  }
  temporada.addEventListener("change", () => { notaTemporada(); mostrarPestania(); });
  pestanias.forEach((boton) => boton.addEventListener("click", () => {
    pestanias.forEach((b) => b.setAttribute("aria-selected", String(b === boton)));
    mostrarPestania();
  }));
  notaTemporada();
  mostrarPestania();

  // ---- Probá el modelo -------------------------------------------------------------------------
  // Se toma un piloto de una carrera, se le cambian los datos y el modelo final
  // vuelve a puntuar a todos los de esa carrera para ordenarlos.
  const esNaN = (v) => v === null || v === undefined || Number.isNaN(v);
  const coma = (x, decimales) => x.toFixed(decimales).replace(".", ",");
  const GRILLA = "Q_GridPosition";

  async function probar() {
    // la pista de la simulación: se dibuja vacía y `pintarPista` le pone los autos
    const cajaPista = $("#proba-pista");
    const dibujo = await dibujar($(".vista", cajaPista), "simulacion");
    const pista = dibujo ? dibujo.view : null;
    const frenarPista = pista ? animarCarrera(cajaPista, pista) : () => {};
    const casos = await datos("casos");
    const modelo = CFG.modelo, entrada = casos.entrada;
    const selCarrera = $("#proba-carrera"), selPiloto = $("#proba-piloto");
    const cajaControles = $("#proba-controles");
    const fila = (piloto) => Object.fromEntries(entrada.map((c, k) => [c, piloto.v[k]]));
    // el desgaste que se muestra: la misma cuenta que el paso Desgaste del modelo
    const desgaste = (f, goma) => {
      const mejor = f["FP_LapTime_min_" + goma + "_ABS"], media = f["FP_LapTime_mean_" + goma + "_ABS"];
      return esNaN(mejor) || esNaN(media) ? NaN : (media - mejor) / mejor * 100;
    };
    const valorReal = (f, col) => col.startsWith("FP_Desgaste_")
      ? desgaste(f, col.slice("FP_Desgaste_".length)) : (esNaN(f[col]) ? NaN : f[col]);
    // la largada llega hasta el último auto de la carrera (en 2026 son 22; al entrenar, 20)
    let nAutos = 20;
    const tope = (c) => c.col === GRILLA ? Math.max(c.rango[1], nAutos) : Math.min(c.rango[1], c.habitual[1] * 3);
    const recortar = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

    const carreras = Object.keys(casos.carreras).sort().reverse();
    selCarrera.replaceChildren(...carreras.map((c) => new Option(casos.carreras[c].nombre, c)));
    let estado = {};      // por control: { sinDato, valor }

    function elegirCarrera() {
      const pilotos = [...casos.carreras[selCarrera.value].pilotos].sort((a, b) => (a.id < b.id ? -1 : 1));
      selPiloto.replaceChildren(...pilotos.map((p) => new Option(p.nombre, p.id)));
      elegirPiloto();
    }

    function elegirPiloto() {         // controles en sus valores reales
      const autos = casos.carreras[selCarrera.value].pilotos;
      nAutos = autos.length;
      const real = fila(autos.find((p) => p.id === selPiloto.value));
      estado = {};
      cajaControles.replaceChildren();
      // primero lo que más mueve la predicción (largada, clasificación, campeonato); las
      // prácticas y el desgaste, en un desplegable
      const practicas = document.createElement("details");
      practicas.className = "mas-practicas";
      practicas.innerHTML = "<summary>Más datos de prácticas</summary><div class=\"controles-modelo\"></div>";
      CFG.controles.forEach((c, n) => {
        const actual = valorReal(real, c.col), lo = c.rango[0], hi = tope(c);
        const inicio = esNaN(actual) ? (esNaN(c.mediana) ? (lo + c.rango[1]) / 2 : c.mediana) : actual;
        estado[c.col] = { sinDato: esNaN(actual), valor: recortar(inicio, lo, hi) };

        const caja = document.createElement("div");
        caja.className = "control";
        caja.innerHTML =
          '<label class="casilla" title="El modelo completa los faltantes con la mediana del ' +
          'entrenamiento y marca que faltaba."><input type="checkbox"><span></span></label>' +
          '<label class="deslizador"><span><span class="etiqueta"></span><output></output></span>' +
          '<input type="range"><span class="extremos"><span></span><span></span></span></label>';
        $(".casilla span", caja).textContent = "Sin dato: " + c.etiqueta.split(":")[0].toLowerCase();
        $(".etiqueta", caja).textContent = c.etiqueta;
        const casilla = $(".casilla input", caja), barra = $('input[type="range"]', caja);
        const extremos = caja.querySelectorAll(".extremos span");
        extremos[0].textContent = coma(lo, c.decimales);
        extremos[1].textContent = coma(hi, c.decimales);
        Object.assign(barra, { min: lo, max: hi, step: c.paso, value: estado[c.col].valor });
        barra.id = "proba-control-" + n;
        casilla.checked = estado[c.col].sinDato;
        // sin dato: el control queda atenuado y deshabilitado en su lugar (nada se corre)
        const pintar = () => {
          caja.classList.toggle("sin-dato", estado[c.col].sinDato);
          barra.disabled = estado[c.col].sinDato;
          $("output", caja).textContent = estado[c.col].sinDato ? "sin dato" : coma(estado[c.col].valor, c.decimales);
        };
        casilla.addEventListener("change", () => { estado[c.col].sinDato = casilla.checked; pintar(); calcular(); });
        barra.addEventListener("input", () => { estado[c.col].valor = Number(barra.value); pintar(); calcular(); });
        pintar();
        (c.col.startsWith("FP_") ? $(".controles-modelo", practicas) : cajaControles).append(caja);
      });
      cajaControles.append(practicas);
      calcular();
    }

    function calcular() {
      const carrera = casos.carreras[selCarrera.value], autos = carrera.pilotos;
      const i = autos.findIndex((p) => p.id === selPiloto.value);
      const filas = autos.map(fila), caso = { ...filas[i] }, avisos = [];

      for (const c of CFG.controles) {
        const e = estado[c.col], actual = valorReal(filas[i], c.col);
        const valor = e.sinDato ? NaN : e.valor;
        if (!e.sinDato) {
          if (!esNaN(actual) && !(c.rango[0] <= actual && actual <= tope(c))) {
            avisos.push("<strong>" + c.etiqueta + "</strong>: su valor real (" + coma(actual, 2) +
              ") está fuera de lo que permite el control; se recortó.");
          } else if (!(c.habitual[0] <= valor && valor <= c.habitual[1])) {
            avisos.push("<strong>" + c.etiqueta + "</strong> = " + coma(valor, 2) +
              ": fuera del 98 % central de lo que vio el modelo (" + coma(c.habitual[0], 2) + " a " +
              coma(c.habitual[1], 2) + "). La predicción es menos confiable.");
          }
        }
        // El desgaste se carga en % y se convierte a la vuelta promedio en segundos, que es lo
        // que recibe el modelo.
        if (c.col.startsWith("FP_Desgaste_")) {
          const goma = c.col.slice("FP_Desgaste_".length);
          const colMejor = "FP_LapTime_min_" + goma + "_ABS";
          let mejor = caso[colMejor];
          if (esNaN(mejor)) { mejor = CFG.medianas[colMejor]; caso[colMejor] = mejor; }
          caso["FP_LapTime_mean_" + goma + "_ABS"] = esNaN(valor) ? NaN : mejor * (1 + valor / 100);
        } else {
          caso[c.col] = valor;
        }
      }

      const puntajesAntes = filas.map((f) => ModeloF1.puntaje(modelo, f));
      const antes = ModeloF1.puestos(puntajesAntes);
      const puntajes = filas.map((f, k) => ModeloF1.puntaje(modelo, k === i ? caso : f));
      const despues = ModeloF1.puestos(puntajes);
      const delta = antes[i] - despues[i];
      pintarPista(autos, filas.map((f, k) => (k === i ? caso : f)), i, puntajes, puntajesAntes, despues, antes);

      const cajaAvisos = $("#proba-avisos");
      cajaAvisos.hidden = !avisos.length;
      cajaAvisos.innerHTML = avisos.map((a) => "<p>" + a + "</p>").join("");
      const tarjeta = (rotulo, valor, ayuda) =>
        '<div class="metrica"><span class="rotulo">' + rotulo + '</span><span class="valor">' + valor +
        '</span><span class="ayuda">' + ayuda + "</span></div>";
      $("#proba-resultado").innerHTML =
        tarjeta("Puesto predicho con sus datos reales", antes[i] + ".º", "") +
        tarjeta("Puesto predicho con tus valores", despues[i] + ".º", "") +
        tarjeta("Puestos que cambió", delta
          ? '<span class="delta ' + (delta > 0 ? "sube" : "baja") + '">' + (delta > 0 ? "↑ " : "↓ ") + Math.abs(delta) + "</span>"
          : "0", delta > 0 ? "el modelo lo adelanta" : delta < 0 ? "el modelo lo atrasa" : "con tus valores queda igual");
      $("#proba-real").textContent = "En la realidad terminó " + autos[i].puesto + ".º" +
        (autos[i].termino ? "" : " (no terminó la carrera)") + ".";
      const nota = $("#proba-nota");
      nota.hidden = carrera.anio >= CFG.anioTest;
      nota.textContent = "Acá predice siempre el modelo final, entrenado con 2018-2025, que sí vio esta " +
        "carrera. En «Explorá», en cambio, las carreras de " + carrera.anio + " las predice un modelo " +
        "entrenado sin esa temporada, así que el puesto puede diferir en algunos lugares. Para un caso " +
        "sin sesgo, elegí una carrera de " + CFG.anioTest + ".";
    }

    /* La carrera con los valores del usuario en la pista: la grilla sale de la largada cargada
       (sin dato = 21, empates por orden de fila, como `race_table`) y la distancia al líder del
       puntaje en puestos (puntaje × (N − 1) + 1, como `score` en build_app.py). */
    function pintarPista(autos, filasCaso, i, puntajes, puntajesAntes, despues, antes) {
      if (!pista) return;
      const n = autos.length, enPuestos = (p) => p * (n - 1) + 1;
      const detras = (ps) => { const lo = Math.min(...ps.map(enPuestos));
        return ps.map((p) => Math.min(Math.max(enPuestos(p) - lo, 0), CFG.simMaxDetras)); };
      // El elegido larga exactamente donde dice el control (sin dato = último) y los demás
      // ocupan los otros lugares en su orden real de largada.
      const grid = new Array(n);
      const gElegido = esNaN(filasCaso[i][GRILLA]) ? n
        : Math.min(Math.max(Math.round(filasCaso[i][GRILLA]), 1), n);
      const largadaReal = (k) => (esNaN(filasCaso[k][GRILLA]) ? Infinity : filasCaso[k][GRILLA]);
      grid[i] = gElegido;
      let lugar = 1;
      autos.map((_, k) => k).filter((k) => k !== i)
        .sort((a, b) => largadaReal(a) - largadaReal(b) || a - b)
        .forEach((k) => { if (lugar === gElegido) lugar++; grid[k] = lugar++; });
      const ahora = detras(puntajes), previo = detras(puntajesAntes);
      const lista = autos.map((p, k) => ({
        driver: p.sigla, team: p.equipo, color: p.color, grid: grid[k], behind: ahora[k],
        pred_pos: despues[k], final: p.puesto, dnf: !p.termino, elegido: k === i,
        pred_antes: antes[k], behind_antes: previo[k],
      }));
      frenarPista();
      const todo = () => true;
      pista.change("autos_sim", vega.changeset().remove(todo).insert(lista))
        .change("recorridos_sim", vega.changeset().remove(todo).insert(recorridos(lista)))
        .signal("avance", 1).runAsync();
    }

    selCarrera.addEventListener("change", elegirCarrera);
    selPiloto.addEventListener("change", elegirPiloto);
    elegirCarrera();
  }
  probar().catch((error) => {
    console.error(error);
    $("#proba").innerHTML = '<p class="aviso">No se pudo cargar «Probá el modelo». Probá con un ' +
      "navegador actualizado (Chrome, Firefox, Edge o Safari).</p>";
  });

  // ---- índice lateral: marca la parte de la página que se está leyendo -------------------------
  const enlaces = [...document.querySelectorAll(".f1-nav-item")];
  const destinos = enlaces.map((a) => document.getElementById(a.getAttribute("href").slice(1)));
  function marcar() {
    let actual = 0;
    destinos.forEach((d, k) => { if (d && d.getBoundingClientRect().top < window.innerHeight * 0.35) actual = k; });
    enlaces.forEach((a, k) => a.classList.toggle("activo", k === actual));
  }
  window.addEventListener("scroll", marcar, { passive: true });
  marcar();
})();
