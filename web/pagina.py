"""Genera `site/index.html`: la aplicación como una sola página estática.

La llama `build_app.py` al final. Es la copa de martini que pide la consigna, con los gráficos de
Altair de `graficos/`, en un único archivo HTML que se abre sin servidor y sin internet:

- Los gráficos se exportan como specs de Vega-Lite (`chart.to_dict()`) y los dibuja vega-embed.
  Vega, Vega-Lite y vega-embed van adentro del archivo (`assets/vendor/`).
- Las specs y las filas de «Probá el modelo» van comprimidas (gzip + base64) y se descomprimen en
  el navegador recién cuando se usan: sin comprimir, las nueve temporadas pesan más de 20 MB.
- «Probá el modelo» se calcula en el navegador con `web/modelo.js` y los parámetros de
  `app_data/modelo.json` (ver `web/modelo_json.py`). No se reentrena nada.

Lee todo de `app_data/`. Los textos de la aplicación están acá; el menú, el encabezado, los títulos
de sección y el pie, en `estilo.py`.
"""

from __future__ import annotations

import base64
import gzip
import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import estilo
from graficos import model_moves, panorama, pasos, race_cars, race_errors, season_points, tallo

RAIZ = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent
APP_DATA = RAIZ / "app_data"
ASSETS = RAIZ / "assets"
SITIO = RAIZ / "site"
# Vega, Vega-Lite y vega-embed: las versiones que usa Altair 6.3 (altair.VEGA_VERSION, etc.), en
# ese orden de carga. Están en assets/vendor/, bajadas de https://cdn.jsdelivr.net/npm/<nombre>@<versión>.
# Si se actualiza Altair, bajar las nuevas y cambiar esta lista.
LIBRERIAS = ["vega-6.4.0.min.js", "vega-lite-6.4.1.min.js", "vega-embed-7.3.0.min.js"]
FUENTE_URL = ("https://fonts.googleapis.com/css2?family=Titillium+Web:ital,wght@0,300;0,400;0,600;"
              "0,700;0,900;1,700;1,900&display=swap")

# ---- constantes de la aplicación ----------------------------------------------------------------
ANIO_TEST = 2026
FECHA_DATOS = "11/11/2026"
PIPELINE = "https://github.com/AntoAldao/ciencia_de_datos_grupo_14/tree/main/pipeline"
CONTROLES = [   # (columna, etiqueta, paso, decimales)
    ("Q_GridPosition", "Posición de largada", 1.0, 0),
    ("Q_Best_seconds_DBT_%", "Clasificación: % más lenta que la mejor vuelta", 0.05, 2),
    ("DriverPoints_Before_DBT_%", "Campeonato: % menos de puntos que el líder", 0.5, 1),
    ("FP_LapTime_min_SOFT_DBT_%", "Prácticas con blanda: % más lenta que la mejor", 0.05, 2),
    ("FP_LapTime_min_MED_DBT_%", "Prácticas con media: % más lenta que la mejor", 0.05, 2),
    ("FP_LapTime_min_HARD_DBT_%", "Prácticas con dura: % más lenta que la mejor", 0.05, 2),
    ("FP_Desgaste_SOFT", "Desgaste con blanda: vuelta promedio vs. mejor (%)", 0.05, 2),
    ("FP_Desgaste_MED", "Desgaste con media: vuelta promedio vs. mejor (%)", 0.05, 2),
]
RECORRIDO = ["Los datos", "Lo que encontramos", "El modelo"]   # el menú lateral
EXPLORAR = [("Todas las carreras", "todas-las-carreras", "⌕"),   # (texto, ancla, ícono)
            ("Una temporada", "una-temporada", "▤"),
            ("Probá el modelo", "proba-el-modelo", "⚙")]
PESTANIAS = [("errores", "Error por carrera"), ("campeonato", "Campeonato"),
             ("autos", "Carrera por carrera"), ("porque", "Por qué el modelo mueve a cada piloto")]


def fmt(x: float, decimales: int = 2) -> str:
    return f"{x:.{decimales}f}".replace(".", ",")


# ---- HTML chico ----------------------------------------------------------------------------------
def md(texto: str) -> str:
    """Lo poco de Markdown que usan los textos: **negrita** y [enlaces](url)."""
    t = html.escape(texto, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)


def p(texto: str) -> str:
    return f"<p>{md(texto)}</p>"


def nota(texto: str) -> str:
    """Texto chico, de aclaración."""
    return f'<p class="nota">{md(texto)}</p>'


def lista(texto: str) -> str:
    items = [linea[2:] for linea in texto.split("\n") if linea.startswith("- ")]
    return "<ul>" + "".join(f"<li>{md(i)}</li>" for i in items) + "</ul>"


def tabla_html(columnas: list[str], filas: list[list[str]], indice: bool = True) -> str:
    """Una tabla del notebook. Con `indice`, la primera columna son los nombres de las filas."""
    def celda(i: int, texto: str) -> str:
        etiqueta = "th" if indice and i == 0 else "td"
        return f"<{etiqueta}>{html.escape(texto)}</{etiqueta}>"
    cabeza = "".join(f"<th>{html.escape(c)}</th>" for c in columnas)
    cuerpo = "".join("<tr>" + "".join(celda(i, x) for i, x in enumerate(f)) + "</tr>" for f in filas)
    return (f'<div class="tabla"><table><thead><tr>{cabeza}</tr></thead>'
            f"<tbody>{cuerpo}</tbody></table></div>")


def como_lo_sabemos(*bloques: str) -> str:
    return ('<details class="como"><summary>Cómo lo sabemos</summary><div>'
            + "".join(bloques) + "</div></details>")


def metrica(rotulo: str, valor: str, ayuda: str) -> str:
    return (f'<div class="metrica"><span class="rotulo">{html.escape(rotulo)}</span>'
            f'<span class="valor">{html.escape(valor)}</span>'
            f'<span class="ayuda">{html.escape(ayuda)}</span></div>')


def grafico(nombre: str) -> str:
    """Hueco donde pagina.js dibuja la spec `nombre` cuando se acerca a la pantalla."""
    return f'<div class="grafico" data-spec="{nombre}"><div class="vista"></div></div>'


def comprimido(nombre: str, dato) -> str:
    """Un dato JSON adentro de la página, en gzip + base64 (lo lee `datos()` en pagina.js)."""
    crudo = json.dumps(dato, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(gzip.compress(crudo, compresslevel=9, mtime=0)).decode("ascii")
    return f'<script type="application/gzip" id="dato-{nombre}">{b64}</script>'


def en_script(texto: str) -> str:
    """Texto que va adentro de un <script>: no puede cerrar la etiqueta."""
    return texto.replace("</script", "<\\/script").replace("<!--", "<\\!--")


# ---- la página -----------------------------------------------------------------------------------
def generar(destino: Path = SITIO) -> Path:
    """Arma `site/index.html` con lo que hay en `app_data/` y devuelve la ruta."""
    leer = lambda nombre: json.loads((APP_DATA / nombre).read_text(encoding="utf-8"))  # noqa: E731
    df = pd.read_parquet(APP_DATA / "predicciones.parquet")
    aportes = pd.read_parquet(APP_DATA / "aportes.parquet")
    resumen, notebook, modelo = leer("resumen.json"), leer("notebook.json"), leer("modelo.json")

    def tabla_nb(comienzo: str) -> tuple[list[str], list[list[str]]]:
        t = notebook[next(t for t in notebook if t.startswith(comienzo))]
        ancho = len(t["columnas"])
        return ([c or " " for c in t["columnas"]],
                [[""] * (ancho - len(f)) + f for f in t["filas"]])   # índices de dos niveles

    def tabla_tramos() -> str:
        filas, corte = [], ""
        for f in notebook[next(t for t in notebook if t.startswith("Error por tramo"))]["filas"][1:]:
            if len(f) == 5:
                corte, f = f[0], f[1:]
            filas.append([corte, *f])
        return tabla_html(["Corte", "Franja", "Pilotos", "MAE", "Sesgo"], filas, indice=False)

    def valor_nb(comienzo: str, fila: str) -> float:
        _, filas = tabla_nb(comienzo)
        return float(next(f for f in filas if f[0] == fila)[1].replace(",", "."))

    # ---- los números de los textos ------------------------------------------------------------
    test = resumen["test"]
    nombre_modelo = resumen["modelo"]["elegido"]
    pct_error_abandonos = valor_nb("Peso de los abandonos", "% del error absoluto total que explican")
    pct_filas_abandonos = valor_nb("Peso de los abandonos", "% de las filas")
    ultima = df[df["Year"] == ANIO_TEST]
    ultima = ultima[ultima["RoundNumber"] == ultima["RoundNumber"].max()]
    equipos = (ultima.groupby("TeamId")["TeamPoints_Before"].max()
               .sort_values(ascending=False).index.tolist())
    n_filas, n_carreras = len(df), df["Carrera"].nunique()
    pct_dnf = (df["Terminó"] == False).mean()  # noqa: E712
    auc_abandonos = next(t for t in notebook if t.startswith("Anticipar abandonos")
                         ).split("AUC medio ")[1].rstrip(")")
    filas_crudas_txt = f"{resumen['datos']['pasos'][0]['filas']:,}".replace(",", ".")
    corte_anio, corte_fecha = resumen["datos"]["al_dia"].split(", ")
    archivo_datos = resumen["datos"]["archivo"].replace("\\", "/")
    hay_practica = df[tallo.FILAS_DATOS[model_moves.FP_PACE]].notna().any(axis=1)
    gp_sin_practica = int((~hay_practica.groupby(df["Carrera"]).any()).sum())
    top5 = df[df["Q_GridPosition"] <= 5]
    anio_mas_abandonos = (df["Terminó"] == False).groupby(df["Year"]).mean().idxmax()  # noqa: E712
    anios = [int(a) for a in sorted(df["Year"].unique(), reverse=True)]

    # ---- gráficos de Altair, como specs de Vega-Lite ----------------------------------------------
    specs = {
        "datos": tallo.datos_disponibles(df),
        "grilla": tallo.grilla_vs_final(df),
        "pasos": pasos.grafico_pasos(df, test, anio_test=ANIO_TEST),
        "abandonos": tallo.abandonos_por_temporada(df),
        "panorama": panorama.panorama(df, width=450),
    }
    for anio in anios:
        tabla = race_cars.race_table(df[df["Year"] == anio])
        es_anio = (df["Year"] == anio).to_numpy()
        contrib = model_moves.contributions(
            aportes[es_anio].drop(columns=["Carrera", "DriverId"]), df[es_anio])
        specs[f"errores-{anio}"] = race_errors.errors_chart(
            race_errors.race_errors(tabla), model_name=nombre_modelo, width=980)
        specs[f"campeonato-{anio}"] = season_points.points_chart(
            season_points.season_points(tabla), model_name=nombre_modelo, width=980)
        specs[f"autos-{anio}"] = race_cars.race_cars_compare(
            tabla, model_name=nombre_modelo, width=1000)
        specs[f"porque-{anio}"] = model_moves.moves_chart(contrib, model_name=nombre_modelo, width=800)
    datos = {nombre: chart.to_dict() for nombre, chart in specs.items()}

    # ---- Probá el modelo: las filas de cada carrera y los límites de los controles ---------------
    entrada = modelo["entrada"]
    entrena = df[df["conjunto"] == "entrenamiento"]
    rangos = dict(resumen["modelo"]["rangos"])
    habituales = dict(resumen["modelo"].get("habituales", rangos))
    medianas = dict(resumen["modelo"].get("medianas", {}))
    for goma in ("SOFT", "MED"):   # rangos del desgaste: los mismos criterios que las columnas
        d = entrena[f"FP_Desgaste_{goma}"]
        rangos.setdefault(f"FP_Desgaste_{goma}", [float(d.min()), float(d.max())])
        habituales.setdefault(f"FP_Desgaste_{goma}", [float(d.quantile(.01)), float(d.quantile(.99))])
        medianas.setdefault(f"FP_Desgaste_{goma}", float(d.median()))
    carreras = {}
    for carrera, autos in df.groupby("Carrera", sort=False):   # en el orden del parquet
        valores = autos[entrada].to_numpy(dtype=float, na_value=np.nan)
        carreras[carrera] = {
            "anio": int(autos["Year"].iloc[0]),
            "pilotos": [{"id": piloto, "nombre": piloto.replace("_", " ").title(),
                         "puesto": int(puesto), "termino": str(termino) != "False",
                         "v": [None if np.isnan(x) else float(x) for x in fila]}
                        for piloto, puesto, termino, fila in zip(
                            autos["DriverId"], autos["Puesto"], autos["Terminó"], valores)]}
    datos["casos"] = {"entrada": entrada, "carreras": carreras}

    config = {
        "anioTest": ANIO_TEST, "anios": anios, "modelo": modelo,
        "pestanias": [clave for clave, _ in PESTANIAS],
        "controles": [{"col": col, "etiqueta": etiqueta, "paso": paso, "decimales": decimales,
                       "rango": rangos[col], "habitual": habituales[col],
                       "mediana": medianas.get(col)} for col, etiqueta, paso, decimales in CONTROLES],
        "medianas": medianas,
    }

    # ---- el cuerpo: la copa de martini, en orden ----------------------------------------------------
    cuerpo = [
        estilo.encabezado(equipos, "Ciencia de Datos · UTN FRM · 2026"),
        "<h1>¿Se puede anticipar en qué puesto termina cada piloto de F1 con lo que se sabe "
        "antes de la carrera?</h1>",
        '<p class="idea">El modelo ordena mejor que la grilla a los pilotos que terminan la carrera, '
        "pero los abandonos, que nadie anticipa, se comen esa ventaja.</p>",
        '<div class="metricas">',
        metrica("Error sin abandonos: modelo vs. grilla",
                f"{fmt(test['mae_modelo_sin_abandonos'])} vs. {fmt(test['mae_grilla_sin_abandonos'])}",
                "Puestos de error promedio por piloto, solo los que terminaron (test 2026)."),
        metrica("Error con todos los pilotos: modelo vs. grilla",
                f"{fmt(test['mae_modelo'])} vs. {fmt(test['mae_grilla'])}",
                "Con los abandonos incluidos quedan casi empatados (test 2026)."),
        metrica("Parte del error que explican los abandonos", f"{pct_error_abandonos:.0f}%",
                f"Son el {pct_filas_abandonos:.0f}% de los pilotos del test 2026."),
        "</div>",
        nota(f"Test: las {test['carreras']} carreras de {ANIO_TEST}, que el modelo no vio al "
             "entrenar. Error = cuántos puestos se equivoca en promedio con cada piloto."),
        "<hr>",
        estilo.parte("recorrido", "El recorrido", "De los datos al modelo, en tres sectores"),

        # ---- Sector 1 · Los datos ----------------------------------------------------------------
        estilo.seccion(1, f"Antes de largar, la grilla está siempre; las prácticas faltan en "
                   f"{gp_sin_practica} de los {n_carreras} Grandes Premios"),
        grafico("datos"),
        p(f"Cada fila es un piloto en un Gran Premio: {n_filas:,} filas de 2018 a 2026.".replace(",", ".")
          + " Cada casilla es el % de pilotos con ese dato en esa temporada; más lleno, más "
          "completo. Mirá las filas: la largada y la clasificación están casi siempre, el "
          "campeonato falta solo en la primera fecha (todavía no hay puntos), y las prácticas "
          f"tienen huecos en 2018-2019 y 2023-2024 ({hay_practica.mean():.0%} en total). Lo que "
          "siempre está, la grilla, va a ser lo que más pesa."),
        como_lo_sabemos(
            p("**De dónde salen.** Del dataset que produce nuestro pipeline "
              f"de Airflow de la Entrega 1 ([carpeta pipeline]({PIPELINE})) a partir "
              "de las estadísticas estilo Ergast (resultados, clasificación y "
              "campeonato) y la telemetría de FastF1 (prácticas libres): "
              f"{filas_crudas_txt} filas, una por piloto en cada Gran Premio, "
              f"de {int(df['Year'].min())} a {int(df['Year'].max())}, con corte en la "
              f"{corte_fecha} de {corte_anio} (datos del {FECHA_DATOS}). El respaldo es el archivo "
              f"{archivo_datos}, guardado en el repositorio; "
              "build_app.py lo lee de ahí."),
            p("**Qué es una fila.** Un piloto en un Gran Premio. Lo que "
              "queremos predecir es su puesto final en esa carrera."),
            p("**Qué filtramos.** Revisamos los datos paso a paso y "
              "anotamos cuántas filas quedaron después de cada uno:"),
            tabla_html(*tabla_nb("Limpieza aplicada")),
            p("**Qué dejamos afuera.** Todo lo que se conoce recién "
              "después de la carrera (si terminó, en qué estado, cuántas "
              "vueltas perdió, las sanciones) nunca entra al modelo: si "
              "terminó o no lo usamos solo para medir. El campeonato se "
              "toma como estaba antes de cada fecha."),
            nota("Columnas descartadas por fuga: RACE_Finished, RACE_Status, "
                 "RACE_Laps_Down, RACE_Lapped, RACE_DNF_Type y las sanciones."),
            p("**Cómo se arma el gráfico.** Para cada temporada contamos "
              "qué parte de los pilotos tiene cada dato. Un grupo cuenta "
              "como presente si el piloto tiene al menos uno de sus datos, "
              "por ejemplo la vuelta más rápida con alguna de las tres "
              "gomas. Los grupos y sus colores son los mismos que en "
              "«Por qué el modelo mueve a cada piloto»."),
            nota(f"Limitación: en {gp_sin_practica} Grandes Premios no hay "
                 "ningún dato de prácticas. El modelo completa los faltantes "
                 "con la mediana del entrenamiento y marca que faltaban.")),

        # ---- Sector 2 · Lo que encontramos -------------------------------------------------------
        estilo.seccion(2, "Quien larga adelante termina adelante: la grilla sola ya ordena buena parte de "
                   "la carrera"),
        '<div class="dos-columnas">', grafico("grilla"),
        p(f"En {n_carreras} Grandes Premios de 2018 a 2026, de los que largan entre los 5 "
          f"primeros, el **{(top5['Puesto'] <= 5).mean():.0%}** termina entre los 5 primeros. "
          "Mirá la diagonal: casi todos terminan cerca de donde largaron, y los cambios "
          "grandes son la excepción. Por eso la grilla es la referencia que el modelo tiene "
          "que superar."),
        "</div>",
        como_lo_sabemos(lista(
            "- **Una hipótesis que se sostuvo (H1, «la grilla manda»):** la largada y la posición "
            f"final se mueven juntas con fuerza: Spearman "
            f"**{fmt(df['Q_GridPosition'].corr(df['Puesto'], method='spearman'), 3)}** (en el EDA, "
            "0,625). Entra al modelo y es la columna que más pesa.\n"
            "- **Una que no se sostuvo (H3, «la velocidad en prácticas anticipa el resultado»):** "
            "la velocidad de la vuelta rápida se asocia con el resultado (Spearman −0,303), pero "
            "porque los autos rápidos largan adelante: descontando la grilla, la correlación parcial "
            "cae a **0,129**. Sale todo el bloque de telemetría. Tampoco se sostuvo que el desgaste "
            "de gomas predijera solo (H7: correlación −0,009).\n"
            "- **Cómo se armó el gráfico:** cada piloto-carrera se ubica por su franja de largada "
            "(fila) y de llegada (columna); cada casilla es el % de los que largaron en esa franja. "
            "Los que largan desde boxes (sin posición de grilla) cuentan en «16 o más».")),

        # ---- Sector 3 · El modelo ----------------------------------------------------------------
        estilo.seccion(3, f"El modelo le gana a la grilla en los que terminan "
                   f"({fmt(test['mae_modelo_sin_abandonos'])} contra "
                   f"{fmt(test['mae_grilla_sin_abandonos'])} puestos), pero con los abandonos quedan casi "
                   f"empatados ({fmt(test['mae_modelo'])} contra {fmt(test['mae_grilla'])})"),
        grafico("pasos"),
        p("Recorré los pasos con los botones de arriba del gráfico. Cada barra cuenta cuántos pilotos "
          "quedaron a esa distancia de su puesto real: en el 0, la predicción acertó. El modelo le "
          "suma a la grilla la clasificación, el campeonato y las prácticas: no acierta más puestos "
          "exactos, pero tiene menos errores grandes. El gráfico arranca en el paso 3: en gris, "
          "los que no terminaron, la cola de la izquierda para los dos."),
        como_lo_sabemos(
            p("**Qué medimos.** El error absoluto medio (MAE) indica cuántos "
              "puestos nos equivocamos en promedio, después de ordenar "
              "a los pilotos de cada carrera. Predecir quinto y terminar "
              "tercero suma dos puestos de error. Menor es mejor. Lo elegimos "
              "porque se lee directo en puestos, y porque no eleva al cuadrado los "
              "errores: un abandono que cae del 3.º al 20.º no tapa todo lo demás, "
              "como pasaría con el RMSE."),
            p("**Las referencias.** El piso es una predicción básica que "
              "ubica a todos en la mitad de la clasificación. La referencia "
              "más exigente es la grilla: predecir el orden de llegada "
              "usando únicamente el orden de largada."),
            p("**Cómo validamos.** Evaluamos cada temporada de 2020 a 2025 "
              "entrenando con las otras temporadas de 2018–2025, sin dividir "
              "una misma carrera entre entrenamiento y validación. "
              "Elegimos el modelo y su ajuste con esas pruebas. "
              "Luego entrenamos con 2018–2025 y evaluamos en 2026, "
              "reservado como test."),
            nota("Limitación: esta validación puede entrenar con temporadas "
                 "posteriores a la evaluada. El test de 2026 sí utiliza "
                 "únicamente temporadas anteriores para entrenar."),
            p("**Comparación de modelos.** La media resume el error entre "
              "temporadas y el desvío muestra cuánto varía. Elegimos el modelo "
              "lineal por su sencillez y su rendimiento competitivo."),
            tabla_html(*tabla_nb("Todos los modelos ajustados")),
            nota(f"Modelo seleccionado: {nombre_modelo}."),
            p("**El ajuste del elegido.** Probamos distintos valores de alpha "
              "(cuánto se achican los coeficientes) con la misma validación "
              "por temporada. Ordenados de mejor a peor:"),
            (lambda columnas, filas: tabla_html(columnas[1:], [f[1:] for f in filas], indice=False))(
                *tabla_nb("Lineal (elegido)")),
            nota(f"Nos quedamos con el primero ({resumen['modelo']['hiperparametros'].get('modelo', '')}). "
                 "La curva es casi plana: entre los mejores la diferencia está muy por "
                 "debajo del desvío entre temporadas."),
            p(f"**Resultado en {ANIO_TEST}.** El modelo y las referencias "
              "se evalúan sobre las mismas carreras:"),
            tabla_html(*tabla_nb("Test 2026 (")),
            nota("En la evaluación «sin abandonos» se seleccionan quienes "
                 "terminaron y se vuelve a ordenar tanto sus predicciones "
                 "como sus resultados dentro de cada carrera. No supone "
                 "que sepamos de antemano quién va a terminar."),
            p("**Dónde se equivoca.** Con todos los pilotos incluidos, "
              "tiende a ubicar algo más atrás a quienes terminan adelante "
              "y algo más adelante a quienes terminan atrás. "
              "Los abandonos se analizan en la sección siguiente."),
            tabla_tramos(),
            nota("Test 2026. Sesgo = puesto predicho − puesto real: positivo, lo pone "
                 "más atrás de donde terminó; negativo, más adelante. El error más "
                 "grande está en los que terminan 16.º o peor, donde caen los abandonos."),
            p("**En qué se apoya.** Estos pesos muestran cómo cada entrada "
              "contribuye al puntaje que usamos para ordenar a los pilotos. "
              "Un peso positivo aumenta ese puntaje y tiende a ubicarlos "
              "más atrás; uno negativo, más adelante, manteniendo "
              "las demás entradas iguales."),
            tabla_html(*tabla_nb("Coeficientes del modelo final")),
            nota("Los pesos corresponden a variables transformadas y escaladas: "
                 "no son puestos ganados o perdidos por cada unidad original "
                 "ni demuestran una relación causal.")),
        grafico("abandonos"),
        p(f"Los abandonos no son una rareza: pasan todas las temporadas, en promedio uno de cada "
          f"{round(1 / pct_dnf)} pilotos. "
          + (f"{ANIO_TEST}, el test, es el año con más: son el" if anio_mas_abandonos == ANIO_TEST
             else f"En el test ({ANIO_TEST}) son el")
          + f" {pct_filas_abandonos:.0f}% de los pilotos y explican "
          f"el {pct_error_abandonos:.0f}% del error, y con lo que se sabe antes de la carrera no se "
          f"pueden anticipar (AUC {auc_abandonos}; 0,5 es adivinar): esa parte del error no la baja "
          "ningún modelo con estos datos."),
        como_lo_sabemos(
            p("**Cuánto pesan en el error.** Separamos a quienes terminaron "
              "de quienes no terminaron y sumamos sus errores absolutos. "
              "La tabla compara cuántos registros representan y qué parte "
              "del error total concentran en el test."),
            tabla_html(*tabla_nb("Peso de los abandonos")),
            p("**¿Podíamos anticiparlos?** Probamos un clasificador adicional "
              "con datos previos a la carrera y lo evaluamos por temporadas. "
              "Usamos el área bajo la curva ROC (AUC), que mide su capacidad "
              "para distinguir quién termina y quién no: 0,5 equivale "
              "a ordenar al azar y 1 a distinguirlos perfectamente."),
            tabla_html(*tabla_nb("Anticipar abandonos")),
            p(f"**Conclusión.** El AUC promedio fue **{auc_abandonos}**: "
              "el clasificador probado mostró poca capacidad para anticipar "
              "los abandonos. Son una limitación de nuestro enfoque.")),
        "<hr>",

        # ---- Copa ----------------------------------------------------------------------------------
        estilo.parte("explorar", "Explorá por tu cuenta",
              "Mirá cualquier temporada y carrera, o cambiá lo que hizo un piloto antes de largar "
              "y fijate qué predice el modelo"),
        '<h3 id="todas-las-carreras">Todas las carreras</h3>',
        grafico("panorama"),
        nota("Cada carrera la predice un modelo que no la vio. Elegí una temporada en el menú, "
             "arrastrá sobre la nube para quedarte con un grupo de carreras y hacé clic en la "
             "leyenda para resaltar dónde ganó cada uno."),

        '<h3 id="una-temporada">Una temporada</h3>',
        '<label class="campo">Temporada <select id="temporada">'
        + "".join(f"<option>{a}</option>" for a in anios) + "</select></label>",
        '<p class="nota" id="nota-temporada"></p>',
        '<div class="pestanias" role="tablist">'
        + "".join(f'<button role="tab" data-pestania="{clave}" aria-selected="{str(i == 0).lower()}">'
                  f"{html.escape(titulo)}</button>" for i, (clave, titulo) in enumerate(PESTANIAS))
        + "</div>",
        '<div class="panel" data-panel="errores"><div class="grafico"><div class="vista"></div></div></div>',
        '<div class="panel" data-panel="campeonato" hidden><div class="grafico"><div class="vista"></div></div></div>',
        # «Carrera por carrera»: los botones «Correr» y «Volver a la largada» los maneja pagina.js
        '<div class="panel" data-panel="autos" hidden><div class="grafico autos">'
        '<div class="controles-autos"><button id="correr" type="button">Correr</button>'
        '<button id="largada" type="button">Volver a la largada</button>'
        '<span id="selector-autos"></span></div>'
        '<div class="marco"><div class="vista"></div></div></div></div>',
        '<div class="panel" data-panel="porque" hidden><div class="grafico"><div class="vista"></div></div></div>',

        '<h3 id="proba-el-modelo">Probá el modelo</h3>',
        p("Elegí una carrera y un piloto y cambiá lo que hizo antes de largar: el modelo le "
          "vuelve a dar un puntaje y lo ordena contra los demás de esa carrera. Los controles "
          "van del mínimo al máximo que vio el modelo al entrenar, así que no se puede cargar "
          "un valor que nunca vio; si uno queda en el 1 % más raro de cada punta, la app avisa."),
        '<div id="proba">'
        '<div class="fila-controles"><label class="campo">Carrera <select id="proba-carrera"></select></label>'
        '<label class="campo">Piloto <select id="proba-piloto"></select></label></div>'
        '<div class="fila-controles" id="proba-controles"></div>'
        '<div class="aviso" id="proba-avisos" role="status" hidden></div>'
        '<div class="metricas" id="proba-resultado" aria-live="polite"></div>'
        '<p class="nota" id="proba-real"></p><p class="nota" id="proba-nota" hidden></p></div>',

        estilo.pie("Grupo 14 · Ciencia de Datos · UTN FRM", f"Datos 2018–{ANIO_TEST}"),
    ]

    librerias = "".join(
        f"<script>{en_script((ASSETS / 'vendor' / nombre).read_text(encoding='utf-8'))}</script>\n"
        for nombre in LIBRERIAS)
    leer_web = lambda nombre: (WEB / nombre).read_text(encoding="utf-8")  # noqa: E731
    pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>F1 – Grupo 14</title>
<!-- Generado por build_app.py (web/pagina.py). No editar a mano: correr `python build_app.py`. -->
<!-- La tipografía es lo único que se pide a internet; sin conexión se usa la del sistema. -->
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FUENTE_URL}" rel="stylesheet">
<style>
{(ASSETS / "estilo.css").read_text(encoding="utf-8")}
{leer_web("pagina.css")}
</style>
</head>
<body>
<aside class="lateral">{estilo.menu(RECORRIDO, EXPLORAR)}</aside>
<main>
{chr(10).join(cuerpo)}
</main>
<script type="application/json" id="config">{en_script(json.dumps(config, ensure_ascii=False))}</script>
{chr(10).join(comprimido(nombre, dato) for nombre, dato in datos.items())}
{librerias}<script>
{en_script(leer_web("modelo.js"))}
</script>
<script>
{en_script(leer_web("pagina.js"))}
</script>
</body>
</html>
"""
    destino.mkdir(exist_ok=True)
    salida = destino / "index.html"
    salida.write_text(pagina, encoding="utf-8")
    # GitHub Pages: que no pase la carpeta por Jekyll
    (destino / ".nojekyll").write_text("", encoding="utf-8")
    return salida
