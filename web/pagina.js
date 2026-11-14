/* Lo que hace la página estática en el navegador (site/index.html):

     1. dibuja las specs de Vega-Lite con vega-embed (las exportó Altair en web/pagina.py);
     2. «Una temporada»: menú de temporada + pestañas, una spec por temporada y pestaña;
     3. «Carrera por carrera»: los botones «Correr» y «Volver a la largada», que mueven la señal
        `avance` del gráfico de graficos/race_cars.py;
     4. «Probá el modelo»: el modelo calculado por web/modelo.js.

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
      return await vegaEmbed(vista, await datos(nombre), { actions: false, ...opciones });
    } catch (error) {
      console.error(error);
      vista.innerHTML = '<p class="error">No se pudo dibujar este gráfico (' + nombre + "). " +
        "Probá con un navegador actualizado (Chrome, Firefox, Edge o Safari).</p>";
      return null;
    }
  }

  // Los del tallo y el panorama: se dibujan cuando están por entrar en pantalla.
  const fijos = document.querySelectorAll(".grafico[data-spec]");
  const alVer = (grafico) => dibujar($(".vista", grafico), grafico.dataset.spec);
  if ("IntersectionObserver" in window) {
    const observador = new IntersectionObserver((entradas) => {
      for (const e of entradas) if (e.isIntersecting) { observador.unobserve(e.target); alVer(e.target); }
    }, { rootMargin: "600px" });
    fijos.forEach((g) => observador.observe(g));
  } else {
    fijos.forEach(alVer);
  }

  // ---- Una temporada: menú + pestañas ----------------------------------------------------------
  const temporada = $("#temporada");
  const pestanias = [...document.querySelectorAll(".pestanias button")];
  const dibujados = new Map();          // pestaña -> { anio, resultado de vegaEmbed }
  let cronometro = null;                // animación de «Carrera por carrera»
  const frenar = () => { clearInterval(cronometro); cronometro = null; };

  function ajustarAutos() {             // el gráfico se achica para entrar en el ancho disponible
    const marco = $('[data-panel="autos"] .marco'), vista = $(".vista", marco);
    if (!vista.scrollWidth) return;
    vista.style.transform = "none";
    const escala = Math.min(1, marco.clientWidth / vista.scrollWidth);
    vista.style.transform = "scale(" + escala + ")";
    marco.style.height = (vista.scrollHeight * escala) + "px";
  }
  window.addEventListener("resize", ajustarAutos);

  async function mostrarPestania() {
    const activa = pestanias.find((b) => b.getAttribute("aria-selected") === "true").dataset.pestania;
    for (const panel of document.querySelectorAll(".panel")) panel.hidden = panel.dataset.panel !== activa;
    const anio = temporada.value, previo = dibujados.get(activa);
    if (previo && previo.anio === anio) { if (activa === "autos") ajustarAutos(); return; }
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
    const view = resultado.view, DURACION = 6000;
    ajustarAutos();
    $("#correr").onclick = () => {
      frenar();
      const inicio = Date.now();
      cronometro = setInterval(() => {
        const t = Math.min(1, (Date.now() - inicio) / DURACION);
        view.signal("avance", t).runAsync();
        if (t >= 1) frenar();
      }, 30);
    };
    $("#largada").onclick = () => { frenar(); view.signal("avance", 0).runAsync(); };
    view.addSignalListener("carrera", () => { frenar(); view.signal("avance", 0).runAsync(); });
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
    const tope = (c) => c.col === GRILLA ? c.rango[1] : Math.min(c.rango[1], c.habitual[1] * 3);
    const recortar = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

    const carreras = Object.keys(casos.carreras).sort().reverse();
    selCarrera.replaceChildren(...carreras.map((c) => new Option(c, c)));
    let estado = {};      // por control: { sinDato, valor }

    function elegirCarrera() {
      const pilotos = [...casos.carreras[selCarrera.value].pilotos].sort((a, b) => (a.id < b.id ? -1 : 1));
      selPiloto.replaceChildren(...pilotos.map((p) => new Option(p.nombre, p.id)));
      elegirPiloto();
    }

    function elegirPiloto() {         // controles en sus valores reales
      const autos = casos.carreras[selCarrera.value].pilotos;
      const real = fila(autos.find((p) => p.id === selPiloto.value));
      estado = {};
      cajaControles.replaceChildren();
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
        extremos[0].textContent = lo.toFixed(c.decimales);
        extremos[1].textContent = hi.toFixed(c.decimales);
        Object.assign(barra, { min: lo, max: hi, step: c.paso, value: estado[c.col].valor });
        barra.id = "proba-control-" + n;
        casilla.checked = estado[c.col].sinDato;
        const pintar = () => {
          $(".deslizador", caja).hidden = estado[c.col].sinDato;
          $("output", caja).textContent = estado[c.col].valor.toFixed(c.decimales);
        };
        casilla.addEventListener("change", () => { estado[c.col].sinDato = casilla.checked; pintar(); calcular(); });
        barra.addEventListener("input", () => { estado[c.col].valor = Number(barra.value); pintar(); calcular(); });
        pintar();
        cajaControles.append(caja);
      });
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
            avisos.push("<strong>" + c.etiqueta + "</strong>: su valor real (" + actual.toFixed(2) +
              ") está fuera de lo que permite el control; se recortó.");
          } else if (!(c.habitual[0] <= valor && valor <= c.habitual[1])) {
            avisos.push("<strong>" + c.etiqueta + "</strong> = " + valor.toFixed(2) +
              ": fuera del 98 % central de lo que vio el modelo (" + c.habitual[0].toFixed(2) + " a " +
              c.habitual[1].toFixed(2) + "). La predicción es menos confiable.");
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

      const antes = ModeloF1.puestos(filas.map((f) => ModeloF1.puntaje(modelo, f)));
      const puntajes = filas.map((f, k) => ModeloF1.puntaje(modelo, k === i ? caso : f));
      const despues = ModeloF1.puestos(puntajes);
      const delta = antes[i] - despues[i];

      const cajaAvisos = $("#proba-avisos");
      cajaAvisos.hidden = !avisos.length;
      cajaAvisos.innerHTML = avisos.map((a) => "<p>" + a + "</p>").join("");
      const tarjeta = (rotulo, valor, ayuda) =>
        '<div class="metrica"><span class="rotulo">' + rotulo + '</span><span class="valor">' + valor +
        '</span><span class="ayuda">' + ayuda + "</span></div>";
      $("#proba-resultado").innerHTML =
        tarjeta("Puesto predicho con sus datos reales", antes[i], "") +
        tarjeta("Puesto predicho con tus valores", despues[i] + (delta
          ? '<span class="delta ' + (delta > 0 ? "sube" : "baja") + '">' + (delta > 0 ? "↑ " : "↓ ") + delta + "</span>"
          : ""), "positivo = el modelo lo adelanta") +
        tarjeta("Puntaje (0 = ganador, 1 = último)", coma(puntajes[i], 3), "");
      $("#proba-real").textContent = "En la realidad terminó " + autos[i].puesto + ".º" +
        (autos[i].termino ? "" : " (no terminó la carrera)") + ".";
      const nota = $("#proba-nota");
      nota.hidden = carrera.anio >= CFG.anioTest;
      nota.textContent = "Acá predice siempre el modelo final, entrenado con 2018-2025, que sí vio esta " +
        "carrera. En «Explorá», en cambio, las carreras de " + carrera.anio + " las predice un modelo " +
        "entrenado sin esa temporada, así que el puesto puede diferir en algunos lugares. Para un caso " +
        "sin sesgo, elegí una carrera de " + CFG.anioTest + ".";
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
