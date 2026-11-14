/* El modelo de la Entrega 3 calculado en el navegador, sin reentrenar.

   Hace la misma cuenta que el pipeline de sklearn, con los números que `build_app.py` guarda en
   app_data/modelo.json (ver web/modelo_json.py, que tiene la misma cuenta en numpy):

     1. Desgaste:       desgaste = (vuelta promedio − mejor vuelta) / mejor vuelta × 100
     2. Por variable:   log1p si corresponde; si falta el dato, se rellena (21 para la grilla, la
                        mediana del entrenamiento para el resto) y su indicador de faltante vale 1
     3. Interacciones:  mejor vuelta × desgaste (con los valores ya rellenados)
     4. Escala:         z = (x − media) / desvío
     5. Ridge:          puntaje = intercepto + Σ coef · z      (0 = ganador, 1 = último)

   `build_app.py` corre este archivo con node contra `modelo.predict` y corta si no coinciden. */
(function (global) {
  "use strict";

  const numero = (v) => (v === null || v === undefined || Number.isNaN(v) ? NaN : Number(v));

  /* Las variables ya transformadas de una fila (antes de escalar), por nombre.
     `fila` es un objeto {columna cruda: número | null}. */
  function transformar(modelo, fila) {
    const crudo = {};
    for (const c of modelo.entrada) crudo[c] = numero(fila[c]);
    for (const d of modelo.desgaste) {
      const mejor = crudo[d.mejor], media = crudo[d.media];
      crudo[d.nombre] = (media - mejor) / mejor * 100;
    }
    const x = {}, falta = {};
    for (const v of modelo.variables) {
      if (v.tipo === "valor") {
        let valor = crudo[v.origen];
        if (v.log1p) valor = Math.log1p(valor);
        falta[v.nombre] = Number.isNaN(valor);
        x[v.nombre] = falta[v.nombre] ? v.relleno : valor;
      } else if (v.tipo === "faltante") {
        x[v.nombre] = falta[v.origen] ? 1 : 0;
      } else {                       // producto
        x[v.nombre] = x[v.a] * x[v.b];
      }
    }
    return x;
  }

  /* Cuánto suma cada variable al puntaje: coef · (x − media) / desvío. */
  function aportes(modelo, fila) {
    const x = transformar(modelo, fila), salida = {};
    for (const v of modelo.variables) salida[v.nombre] = v.coef * ((x[v.nombre] - v.media) / v.desvio);
    return salida;
  }

  /* Puntaje de una fila: lo que devuelve `modelo.predict`. */
  function puntaje(modelo, fila) {
    const a = aportes(modelo, fila);
    let total = modelo.intercepto;
    for (const v of modelo.variables) total += a[v.nombre];
    return total;
  }

  /* Puesto de cada piloto dentro de su carrera: de menor a mayor puntaje; si dos empatan, va
     primero el que está primero en la lista (como `rank(method="first")` de pandas). */
  function puestos(puntajes) {
    return puntajes.map((p, i) => {
      let adelante = 0;
      for (let j = 0; j < puntajes.length; j++) {
        if (puntajes[j] < p || (puntajes[j] === p && j < i)) adelante++;
      }
      return adelante + 1;
    });
  }

  const ModeloF1 = { transformar, aportes, puntaje, puestos };
  if (typeof module !== "undefined" && module.exports) module.exports = ModeloF1;
  else global.ModeloF1 = ModeloF1;
})(typeof globalThis !== "undefined" ? globalThis : this);
