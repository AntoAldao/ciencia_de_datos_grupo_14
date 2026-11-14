/* Prueba de web/modelo.js contra sklearn. La corre build_app.py (web/modelo_json.py):

       node web/probar_modelo.js casos.json

   casos.json trae el modelo exportado, filas de entrada y, para cada una, el puntaje de
   `modelo.predict` y su puesto dentro de la carrera. Imprime un resumen en JSON y termina con
   error si alguna fila difiere más que la tolerancia o si cambia algún puesto. */
"use strict";
const fs = require("fs");
const ModeloF1 = require("./modelo.js");

const { modelo, filas, grupo, puntaje, puesto, tolerancia } = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

const calculado = filas.map((f) => ModeloF1.puntaje(modelo, f));
let maxima = 0, peor = -1;
calculado.forEach((p, i) => {
  const d = Math.abs(p - puntaje[i]);
  if (!(d <= maxima)) { maxima = d; peor = i; }     // un NaN también queda como la peor
});

// puestos dentro de cada carrera, en el orden en que vienen las filas
const porGrupo = new Map();
grupo.forEach((g, i) => { if (!porGrupo.has(g)) porGrupo.set(g, []); porGrupo.get(g).push(i); });
let puestosDistintos = 0;
for (const indices of porGrupo.values()) {
  const orden = ModeloF1.puestos(indices.map((i) => calculado[i]));
  indices.forEach((i, k) => { if (orden[k] !== puesto[i]) puestosDistintos++; });
}

const resultado = {
  node: process.version,
  filas: filas.length,
  carreras: porGrupo.size,
  diferencia_maxima: maxima,
  tolerancia,
  puestos_distintos: puestosDistintos,
  ejemplo: peor >= 0 ? { fila: peor, js: calculado[peor], sklearn: puntaje[peor] } : null,
};
console.log(JSON.stringify(resultado));
process.exit(maxima <= tolerancia && puestosDistintos === 0 ? 0 : 1);
