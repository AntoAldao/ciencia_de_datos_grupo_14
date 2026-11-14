"""El modelo de la Entrega 3 como una lista de números, para calcularlo en el navegador.

La página estática (`site/index.html`) no tiene Python: «Probá el modelo» hace la cuenta en
JavaScript (`web/modelo.js`). Para eso `parametros()` saca del pipeline entrenado todo lo que la
cuenta necesita y lo deja como un dict que se guarda en `app_data/modelo.json`:

    Desgaste        -> qué dos columnas en segundos dan cada desgaste
    ColumnTransformer -> por variable: de qué columna sale, si lleva log1p y con qué se rellena
                       un faltante; y los indicadores de faltante
    Interacciones   -> qué dos variables se multiplican
    StandardScaler  -> media y desvío de cada variable
    Ridge           -> coeficiente de cada variable e intercepto

    puntaje = intercepto + Σ coef_j · (x_j − media_j) / desvío_j

No se reentrena nada. `verificar()` rehace la cuenta en numpy **a partir de ese dict** y la
compara con `modelo.predict` fila por fila: si no dan lo mismo, el build se corta. Y
`verificar_js()` corre la versión JavaScript con node sobre las mismas filas.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

import modelo_entrega3 as m3

TOLERANCIA = 1e-9
PRUEBA_JS = Path(__file__).resolve().parent / "probar_modelo.js"


class ModeloNoExportable(ValueError):
    """El pipeline guardado no tiene la forma que la página sabe calcular."""


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ModeloNoExportable(
            f"No se puede llevar el modelo al navegador: {mensaje}. La página estática solo sabe "
            "calcular Desgaste → ColumnTransformer → Interacciones → StandardScaler → Ridge. "
            "Si el notebook eligió otro modelo, hay que extender web/modelo_json.py y "
            "web/modelo.js.")


def _columnas_transformadas(ct: ColumnTransformer) -> list[dict]:
    """Una entrada por columna que sale del ColumnTransformer, en su orden."""
    salida = []
    for nombre, transformador, columnas in ct.transformers_:
        if isinstance(transformador, str):
            _exigir(transformador == "drop", f"el bloque «{nombre}» pasa columnas sin transformar")
            continue
        pasos = ([p for _, p in transformador.steps] if isinstance(transformador, Pipeline)
                 else [transformador])
        log1p = False
        if isinstance(pasos[0], FunctionTransformer):
            _exigir(pasos[0].func is np.log1p, f"el bloque «{nombre}» usa una función que no es log1p")
            log1p, pasos = True, pasos[1:]
        _exigir(len(pasos) == 1 and isinstance(pasos[0], SimpleImputer),
                f"el bloque «{nombre}» no termina en un SimpleImputer")
        imputador = pasos[0]
        for columna, relleno in zip(columnas, imputador.statistics_):
            salida.append({"nombre": columna, "tipo": "valor", "origen": columna, "log1p": log1p,
                           "relleno": float(relleno)})
        if imputador.indicator_ is not None:   # solo las columnas con faltantes al entrenar
            for i in imputador.indicator_.features_:
                salida.append({"nombre": f"missingindicator_{columnas[i]}", "tipo": "faltante",
                               "origen": columnas[i]})
    nombres = [v["nombre"] for v in salida]
    _exigir(nombres == list(ct.get_feature_names_out()),
            "las columnas del ColumnTransformer no salen en el orden esperado")
    return salida


def parametros(guardado: dict) -> dict:
    """Todo lo que hace falta para calcular el puntaje sin sklearn (ver el docstring del módulo)."""
    pipe = guardado["modelo"]
    _exigir(isinstance(pipe, Pipeline), "lo guardado no es un Pipeline")
    pasos = [p for _, p in pipe.steps]
    formas = [m3.Desgaste, ColumnTransformer, m3.Interacciones, StandardScaler, Ridge]
    _exigir(len(pasos) == len(formas) and all(type(p).__name__ == f.__name__
                                              for p, f in zip(pasos, formas)),
            "los pasos son " + " → ".join(type(p).__name__ for p in pasos))
    _, columnas, interacciones, escala, ridge = pasos

    variables = _columnas_transformadas(columnas)
    nombres = {v["nombre"] for v in variables}
    for a, b in interacciones.PARES:   # como Interacciones.transform: solo si están las dos
        if a in nombres and b in nombres:
            variables.append({"nombre": f"{a} × {b}", "tipo": "producto", "a": a, "b": b})
    _exigir([v["nombre"] for v in variables] == list(escala.feature_names_in_),
            "las variables que llegan al StandardScaler no son las esperadas")
    _exigir(escala.with_mean and escala.with_std, "el StandardScaler no centra o no escala")
    coeficientes = np.ravel(ridge.coef_)
    _exigir(len(coeficientes) == len(variables), "hay distinta cantidad de coeficientes que de variables")
    for v, media, desvio, coef in zip(variables, escala.mean_, escala.scale_, coeficientes):
        v.update(media=float(media), desvio=float(desvio), coef=float(coef))

    return {
        "elegido": guardado.get("elegido"),
        "semilla": guardado.get("semilla"),
        "hiperparametros": {k: str(v) for k, v in guardado.get("hiperparametros", {}).items()},
        # columnas crudas que recibe el modelo («Carrera» viaja en el pipeline pero se descarta)
        "entrada": [c for c in guardado["entrada"] if c != "Carrera"],
        # paso Desgaste: desgaste = (vuelta promedio − mejor vuelta) / mejor vuelta × 100
        "desgaste": [{"nombre": f"FP_Desgaste_{c}", "mejor": f"FP_LapTime_min_{c}_ABS",
                      "media": f"FP_LapTime_mean_{c}_ABS"} for c in ("SOFT", "MED")],
        "variables": variables,
        "intercepto": float(ridge.intercept_),
    }


def predecir(params: dict, df: pd.DataFrame) -> np.ndarray:
    """La misma cuenta que `modelo.predict`, en numpy y usando solo `params` (lo que se guarda en
    el JSON). Es la versión de referencia de `web/modelo.js`: las dos hacen los mismos pasos en
    el mismo orden."""
    crudo = {c: df[c].to_numpy(dtype=float, na_value=np.nan) for c in params["entrada"]}
    for d in params["desgaste"]:
        mejor, media = crudo[d["mejor"]], crudo[d["media"]]
        crudo[d["nombre"]] = (media - mejor) / mejor * 100
    x, falta = {}, {}
    for v in params["variables"]:
        if v["tipo"] == "valor":
            valor = crudo[v["origen"]]
            if v["log1p"]:
                valor = np.log1p(valor)
            falta[v["nombre"]] = np.isnan(valor)
            x[v["nombre"]] = np.where(falta[v["nombre"]], v["relleno"], valor)
        elif v["tipo"] == "faltante":
            x[v["nombre"]] = falta[v["origen"]].astype(float)
        else:   # producto
            x[v["nombre"]] = x[v["a"]] * x[v["b"]]
    puntaje = np.full(len(df), params["intercepto"])
    for v in params["variables"]:
        puntaje = puntaje + v["coef"] * ((x[v["nombre"]] - v["media"]) / v["desvio"])
    return puntaje


def casos_de_prueba(params: dict, df: pd.DataFrame, semilla: int = 14) -> pd.DataFrame:
    """Las filas con las que se verifica: todas las del dataset y, además, una copia de cada una
    con datos borrados al azar. En «Probá el modelo» el usuario puede marcar «Sin dato» en
    cualquier control, incluso en combinaciones que el dataset no trae (p. ej. sin grilla)."""
    entrada = params["entrada"]
    base = df[entrada + ["Carrera"]].reset_index(drop=True)
    base[entrada] = base[entrada].astype(float)
    con_huecos = base.copy()
    borrar = np.random.default_rng(semilla).random((len(base), len(entrada))) < 0.3
    con_huecos[entrada] = con_huecos[entrada].mask(borrar)
    return pd.concat([base, con_huecos], ignore_index=True)


def filas_json(df: pd.DataFrame, columnas: list[str]) -> list[dict]:
    """Filas como las lee el navegador: cada número con todos sus decimales (`DataFrame.to_json`
    los redondea a 10) y los faltantes como null."""
    valores = df[columnas].to_numpy(dtype=float, na_value=np.nan)
    return [{c: (None if np.isnan(v) else float(v)) for c, v in zip(columnas, fila)}
            for fila in valores]


def verificar(params: dict, guardado: dict, df: pd.DataFrame) -> dict:
    """Corta con error si la cuenta hecha desde `params` no da lo mismo que `modelo.predict`.

    Usa `params` después de pasarlo por JSON, que es lo que va a leer el navegador."""
    params = json.loads(json.dumps(params))
    casos = casos_de_prueba(params, df)
    esperado = m3.puntaje(guardado, casos)
    diferencia = float(np.max(np.abs(predecir(params, casos) - esperado)))
    if not diferencia <= TOLERANCIA:
        raise AssertionError(
            f"El modelo exportado a JSON no coincide con modelo.predict: diferencia máxima "
            f"{diferencia:.3g} (tolerancia {TOLERANCIA:g}) en {len(casos)} filas. No se genera la página.")
    return {"filas": len(casos), "filas_del_dataset": len(df), "diferencia_maxima": diferencia,
            "tolerancia": TOLERANCIA}


def verificar_js(params: dict, guardado: dict, df: pd.DataFrame) -> dict | None:
    """Corre `web/modelo.js` con node sobre las mismas filas y lo compara con `modelo.predict`
    (puntaje y puesto dentro de cada carrera). Devuelve None si no hay node instalado."""
    node = shutil.which("node")
    if node is None:
        return None
    casos = casos_de_prueba(params, df)
    esperado = m3.puntaje(guardado, casos)
    # puesto dentro de la carrera, como «Probá el modelo»: rank(method="first")
    grupo = casos["Carrera"] + np.where(casos.index < len(df), "", " (con huecos)")
    puesto = pd.Series(esperado).groupby(grupo).rank(method="first").astype(int)
    datos = {"modelo": params, "tolerancia": TOLERANCIA,
             "filas": filas_json(casos, params["entrada"]),
             "grupo": grupo.tolist(), "puntaje": esperado.tolist(), "puesto": puesto.tolist()}
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "casos.json"
        archivo.write_text(json.dumps(datos), encoding="utf-8")
        corrida = subprocess.run([node, str(PRUEBA_JS), str(archivo)], capture_output=True,
                                 text=True)
    if corrida.returncode != 0:
        raise AssertionError("web/modelo.js no coincide con modelo.predict:\n"
                             + corrida.stdout + corrida.stderr)
    return json.loads(corrida.stdout)
