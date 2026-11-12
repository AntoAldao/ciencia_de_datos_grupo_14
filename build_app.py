"""Construye lo que muestra la aplicación a partir de los datos del pipeline y del modelo.

    python build_app.py              # usa el modelo guardado (si no está, lo entrena)
    python build_app.py --entrenar   # ejecuta el notebook de la Entrega 3 y regenera el modelo

1. Lee `data/f1_all_full.parquet` (lo que produce el pipeline) y lo limpia como la Entrega 3.
2. Con `--entrenar` (o si falta el modelo) ejecuta el notebook de la Entrega 3 **tal cual**, en
   una carpeta temporal con los archivos que espera, armados desde ese mismo parquet. El notebook
   elige el modelo, lo entrena con 2018-2025 (semilla 14), lo mide en el test (2026) y lo guarda;
   el archivo se copia a `modelos/` y el notebook ejecutado queda en `build/`.
3. Guarda en `app_data/` las predicciones, los aportes de cada variable y un resumen.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn import config_context
from sklearn.base import clone

import modelo_entrega3 as m3

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "data" / "f1_all_full.parquet"
NOTEBOOK = RAIZ / "notebooks" / "Entrega_3_Modelado_y_Validacion_F1_Grupo_14.ipynb"
EJECUTADO = RAIZ / "build" / "Entrega_3_ejecutada.ipynb"
SALIDA = RAIZ / "app_data"
CLAVE = ["Year", "RoundNumber", "DriverId"]
# Columnas que el pipeline agregó después del parquet v2 con el que se escribió el notebook.
# Tablas del notebook ejecutado que muestra la app en los «Cómo lo sabemos» (por comienzo del título).
TABLAS_NOTEBOOK = ["Limpieza aplicada", "Partición entrenamiento / validación / test",
                   "Piso y referencia", "Todos los modelos ajustados", "Lineal (elegido)",
                   "Test 2026 (", "Error por tramo", "Peso de los abandonos", "Anticipar abandonos",
                   "Coeficientes del modelo final", "Chequeo de fuga", "Resumen en números"]
COLUMNAS_NUEVAS = ["RACE_Finished", "RACE_Status", "RACE_Laps_Down", "RACE_Lapped",
                   "RACE_DNF_Type", "RACE_Penalty_Seconds", "RACE_Penalty_Positions_Lost",
                   "Q_PitLaneStart"]


def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """La limpieza de la Entrega 3 (celdas 4 y 6), con las filas que quedan en cada paso."""
    pasos = [{"paso": "Crudo del pipeline", "filas": len(df)}]
    dup = df[df.duplicated(CLAVE)][["Year", "RoundNumber"]].drop_duplicates()
    rondas = list(dup.itertuples(index=False, name=None))
    df = df[~df.set_index(["Year", "RoundNumber"]).index.isin(rondas)].reset_index(drop=True)
    pasos.append({"paso": "Sin rondas con filas duplicadas ("
                  + ", ".join(f"{a}-R{r}" for a, r in rondas) + ")", "filas": len(df)})
    pasos.append({"paso": f"Grilla en 0 pasada a faltante ({int((df['Q_GridPosition'] == 0).sum())}"
                  " filas)", "filas": len(df)})
    df["Q_GridPosition"] = df["Q_GridPosition"].replace(0, np.nan)
    df["Terminó"] = df["RACE_Finished"].astype("boolean")
    df = df.sort_values(["Year", "RoundNumber", "RACE_Position"]).reset_index(drop=True)
    df["Carrera"] = df["Year"].astype(str) + "-R" + df["RoundNumber"].astype(str).str.zfill(2)
    df["Autos_en_carrera"] = df.groupby("Carrera")["DriverId"].transform("size")
    df["Puesto"] = df.groupby("Carrera")["RACE_Position"].rank(method="first")
    df["conjunto"] = np.where(df["Year"] < 2026, "entrenamiento", "test")
    for goma in ("SOFT", "MED"):   # solo para mostrar: el modelo lo calcula adentro
        mejor, prom = df[f"FP_LapTime_min_{goma}_ABS"], df[f"FP_LapTime_mean_{goma}_ABS"]
        df[f"FP_Desgaste_{goma}"] = (prom - mejor) / mejor * 100
    return df, pasos


def ejecutar_notebook(crudo: pd.DataFrame) -> None:
    """Ejecuta el notebook de la Entrega 3 con los datos actuales y copia el modelo a modelos/."""
    import nbformat
    from nbclient import NotebookClient

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # los dos archivos que el notebook busca en su carpeta (celda 2)
        crudo.drop(columns=[c for c in COLUMNAS_NUEVAS if c in crudo]).to_parquet(
            tmp / "f1_all_full_v2.parquet")
        crudo[CLAVE + ["RACE_Finished"]].drop_duplicates(CLAVE).to_parquet(
            tmp / "f1_all_postEDA.parquet")
        nb = nbformat.read(NOTEBOOK, as_version=4)
        inicio = time.time()
        print(f"Ejecutando {NOTEBOOK.name}...", flush=True)
        NotebookClient(nb, timeout=3600, kernel_name="python3",
                       resources={"metadata": {"path": str(tmp)}}).execute()
        print(f"  listo en {time.time() - inicio:.0f} s", flush=True)
        EJECUTADO.parent.mkdir(exist_ok=True)
        nbformat.write(nb, EJECUTADO)
        m3.ARCHIVO.parent.mkdir(exist_ok=True)
        shutil.copy(tmp / "modelo_f1_grupo14.joblib", m3.ARCHIVO)


def tablas_del_notebook(ruta: Path = EJECUTADO) -> dict[str, dict]:
    """Las tablas de `TABLAS_NOTEBOOK` tal como las mostró el notebook ejecutado:
    {título: {"columnas": [...], "filas": [[...], ...]}}."""
    nb = json.loads(ruta.read_text(encoding="utf-8"))
    tablas = {}
    for celda in nb["cells"]:
        for salida in celda.get("outputs", []):
            h = "".join(salida.get("data", {}).get("text/html", ""))
            titulo = re.search(r"<caption>(.*?)</caption>", h, re.S)
            if not titulo:
                continue
            titulo = html.unescape(titulo.group(1)).strip()
            if not any(titulo.startswith(p) for p in TABLAS_NOTEBOOK):
                continue
            filas = [[html.unescape(re.sub("<.*?>", "", x)).strip()
                      for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", fila, re.S)]
                     for fila in re.findall(r"<tr>(.*?)</tr>", h, re.S)]
            # fuera la fila con el nombre del índice (solo la primera celda tiene texto)
            filas = [f for f in filas if any(f[1:])]
            tablas[titulo] = {"columnas": filas[0], "filas": filas[1:]}
    return tablas


def medir(d: pd.DataFrame) -> dict:
    """MAE del modelo, la grilla y el piso como `medir` del notebook (celda 10)."""
    car = d["Carrera"]
    real = d["Puesto"].groupby(car).rank(method="average")
    puestos = {"modelo": d["puesto_modelo"],
               "grilla": d["Q_GridPosition"].fillna(21).groupby(car).rank(method="average"),
               "piso": (d["Autos_en_carrera"] + 1) / 2}
    termino = d["Terminó"].fillna(False).astype(bool)
    res = {"carreras": int(car.nunique()), "filas": len(d)}
    for quien, p in puestos.items():
        res[f"mae_{quien}"] = float((p - real).abs().mean())
        pf = p[termino].groupby(car[termino]).rank(method="average")
        rf = real[termino].groupby(car[termino]).rank(method="average")
        res[f"mae_{quien}_sin_abandonos"] = float((pf - rf).abs().mean())
    return res


def predecir_fuera_de_muestra(guardado: dict, df: pd.DataFrame):
    """Puntaje y aportes de cada fila, predichos por un modelo que NO vio esa fila.

    - 2018-2025: validación cruzada por temporada, como en el notebook. Para cada temporada se
      entrena una copia del modelo elegido (mismo pipeline e hiperparámetros) con las demás
      temporadas de entrenamiento y se predice esa.
    - 2026 (test): el modelo final que guardó el notebook, entrenado con 2018-2025.
    Así, lo que el usuario ve en «Explorá» es lo que el modelo hubiera dicho sin conocer la carrera.
    """
    entrada = guardado["entrada"]
    puntaje = pd.Series(np.nan, index=df.index)
    partes = []
    es_test = df["conjunto"] == "test"
    puntaje[es_test] = m3.puntaje(guardado, df[es_test])
    partes.append(m3.aportes(guardado, df[es_test]))

    entrena = df[~es_test]
    objetivo = (entrena["Puesto"] - 1) / (entrena["Autos_en_carrera"] - 1)   # Puesto_01 del notebook
    for anio in sorted(entrena["Year"].unique()):
        afuera = entrena["Year"] == anio
        with config_context(transform_output="pandas"):
            modelo = clone(guardado["modelo"]).fit(entrena.loc[~afuera, entrada], objetivo[~afuera])
        pliegue = {**guardado, "modelo": modelo}
        filas = entrena.index[afuera]
        puntaje[filas] = m3.puntaje(pliegue, df.loc[filas])
        partes.append(m3.aportes(pliegue, df.loc[filas]))

    df["origen_prediccion"] = np.where(
        es_test, "modelo final (entrenado con 2018-2025)",
        "validación cruzada: modelo entrenado sin " + df["Year"].astype(str))
    aportes = None if any(p is None for p in partes) else pd.concat(partes).loc[df.index]
    return puntaje.to_numpy(), aportes


def verificar_contra_notebook(test: dict, tablas: dict) -> None:
    """Corta con error si el test de la app no coincide con el que mostró el notebook."""
    titulo = next((t for t in tablas if t.startswith("Test 2026 (")), None)
    if titulo is None:
        print("Aviso: no hay notebook ejecutado para comparar (correr con --entrenar).")
        return
    t = tablas[titulo]
    col = {c: i for i, c in enumerate(t["columnas"])}
    filas = {f[0]: f for f in t["filas"]}
    num = lambda x: float(x.replace(".", "").replace(",", "."))  # noqa: E731
    pares = [("Modelo final", "MAE (puestos)", "mae_modelo"),
             ("Modelo final", "MAE sin abandonos", "mae_modelo_sin_abandonos"),
             ("Referencia: grilla sola", "MAE (puestos)", "mae_grilla"),
             ("Referencia: grilla sola", "MAE sin abandonos", "mae_grilla_sin_abandonos")]
    for fila, columna, clave in pares:
        nb = num(next(f for n, f in filas.items() if n.startswith(fila))[col[columna]])
        assert abs(nb - test[clave]) < 0.0015, (
            f"{clave}: la app da {test[clave]:.3f} y el notebook {nb:.3f}. "
            "¿Cambiaron los datos? Correr: python build_app.py --entrenar")
    print(f"Coincide con el notebook ({titulo}).")


def construir(entrenar: bool = False) -> dict:
    crudo = pd.read_parquet(DATOS)
    df, pasos = limpiar(crudo)
    if entrenar or not m3.ARCHIVO.exists():
        ejecutar_notebook(crudo)
    guardado = m3.cargar()

    df["puntaje"], aportes = predecir_fuera_de_muestra(guardado, df)          # 0-1
    df["score"] = df["puntaje"] * (df["Autos_en_carrera"] - 1) + 1            # en puestos
    df["puesto_modelo"] = df.groupby("Carrera")["puntaje"].rank(method="average")
    entrada = [c for c in guardado["entrada"] if c != "Carrera"]
    entrena = df[df["conjunto"] == "entrenamiento"]

    SALIDA.mkdir(exist_ok=True)
    df.to_parquet(SALIDA / "predicciones.parquet", index=False)
    if aportes is not None:
        pd.concat([df[["Carrera", "DriverId"]], aportes.astype(float)], axis=1).to_parquet(
            SALIDA / "aportes.parquet", index=False)
    resumen = {
        "datos": {"archivo": str(DATOS.relative_to(RAIZ)), "pasos": pasos,
                  "al_dia": f"{int(df['Year'].max())}, fecha "
                            f"{int(df[df['Year'] == df['Year'].max()]['RoundNumber'].max())}"},
        "modelo": {"elegido": guardado.get("elegido"), "semilla": guardado.get("semilla"),
                   "hiperparametros": {k: str(v) for k, v in
                                       guardado.get("hiperparametros", {}).items()},
                   "entrada": entrada,
                   "rangos": {c: [float(entrena[c].min()), float(entrena[c].max())]
                              for c in entrada},
                   # el 98 % central de lo que vio el entrenamiento: afuera, la app avisa
                   "habituales": {c: [float(entrena[c].quantile(0.01)), float(entrena[c].quantile(0.99))]
                                  for c in entrada},
                   "medianas": {c: float(entrena[c].median()) for c in entrada}},
        "test": medir(df[df["conjunto"] == "test"]),
    }
    (SALIDA / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    if EJECUTADO.exists():
        (SALIDA / "notebook.json").write_text(
            json.dumps(tablas_del_notebook(), indent=2, ensure_ascii=False), encoding="utf-8")
    if (SALIDA / "notebook.json").exists():
        verificar_contra_notebook(resumen["test"],
                                  json.loads((SALIDA / "notebook.json").read_text(encoding="utf-8")))
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Construye app_data/ para la aplicación.")
    parser.add_argument("--entrenar", action="store_true",
                        help="ejecutar el notebook de la Entrega 3 y regenerar el modelo")
    r = construir(parser.parse_args().entrenar)
    t = r["test"]
    print(f"Modelo: {r['modelo']['elegido']} {r['modelo']['hiperparametros']}")
    print(f"Test 2026 ({t['carreras']} carreras): MAE modelo {t['mae_modelo']:.3f} · grilla "
          f"{t['mae_grilla']:.3f} · piso {t['mae_piso']:.3f} · sin abandonos "
          f"{t['mae_modelo_sin_abandonos']:.3f}")
