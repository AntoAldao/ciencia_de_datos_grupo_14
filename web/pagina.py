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


def proceso(pasos: list[tuple[str, str]]) -> str:
    """Pasos numerados, uno al lado del otro (título y una explicación corta cada uno)."""
    return ('<ol class="proceso">' + "".join(
        f"<li><b>{md(t)}</b><span>{md(d)}</span></li>" for t, d in pasos) + "</ol>")


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
    ejemplo_vueltas = leer("ejemplo_vueltas.json")   # lo genera web/ejemplo_vueltas.py (una vez, a mano)

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
    n_filas_txt = f"{len(df):,}".replace(",", ".")
    filas_crudas_txt = f"{resumen['datos']['pasos'][0]['filas']:,}".replace(",", ".")
    corte_anio, corte_fecha = resumen["datos"]["al_dia"].split(", ")
    archivo_datos = resumen["datos"]["archivo"].replace("\\", "/")
    hay_practica = df[tallo.FILAS_DATOS[model_moves.FP_PACE]].notna().any(axis=1)
    gp_sin_practica = int((~hay_practica.groupby(df["Carrera"]).any()).sum())
    top5 = df[df["Q_GridPosition"] <= 5]
    anio_mas_abandonos = (df["Terminó"] == False).groupby(df["Year"]).mean().idxmax()  # noqa: E712
    anios = [int(a) for a in sorted(df["Year"].unique(), reverse=True)]
    n_columnas = len(tallo.columnas_del_pipeline())   # las que arma el pipeline
    pasos_datos = resumen["datos"]["pasos"]
    fechas_dup = pasos_datos[1]["paso"].split("(")[1].rstrip(")")   # «2023-R11, 2025-R16»
    rondas_dup = len(fechas_dup.split(", "))
    fechas_dup = " y ".join(f"{a}, fecha {r}" for a, r in (f.split("-R") for f in fechas_dup.split(", ")))
    cv = tallo.cifras_vueltas(ejemplo_vueltas)   # el ejemplo de vueltas de prácticas (Sector 1)
    mot = lambda m: cv["motivos"].get(m, 0)  # noqa: E731
    blandas = cv["por_goma"]["SOFT"] | {"mejor_txt": tallo._reloj(cv["por_goma"]["SOFT"]["mejor"]),
                                        "promedio_txt": tallo._reloj(cv["por_goma"]["SOFT"]["promedio"])}
    cg = tallo.cifras_grilla(df)                 # los números del texto del Sector 2
    pct = lambda x: f"{x:.0%}".replace("%", "\u00a0%")  # noqa: E731
    sq, sq_t = cg["se_queda"], cg["se_queda_terminaron"]
    n_term_txt = f"{cg['n_terminaron']:,}".replace(",", ".")
    n_ab_txt = f"{cg['n_todos'] - cg['n_terminaron']:,}".replace(",", ".")
    cp = pasos.cifras(df, anio_test=ANIO_TEST)   # los números de los textos del Sector 3
    pct_ab_filas = cp["abandonos"] / cp["pilotos"]

    # ---- gráficos de Altair, como specs de Vega-Lite ----------------------------------------------
    specs = {
        "vueltas": tallo.vueltas_ejemplo(ejemplo_vueltas),
        "columnas": tallo.seleccion_columnas(df),
        "datos": tallo.datos_disponibles(df),
        "grilla": tallo.grilla_vs_final(df),
        "grilla-sin": tallo.grilla_vs_final_sin_abandonos(df),
        **{f"paso-{i}": g for i, g in enumerate(pasos.graficos_pasos(df, test, anio_test=ANIO_TEST), 1)},
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
        estilo.seccion(1, f"De {n_columnas} datos por piloto y carrera nos quedamos con 8: los que "
                          "se saben antes de largar y dicen algo nuevo"),
        p("Antes de predecir hay que saber con qué se cuenta. Cada fila de nuestros datos es **un "
          "piloto en un Gran Premio**, y lo que queremos predecir es en qué puesto termina. Para "
          "llegar a esas filas hicimos cuatro pasos:"),
        proceso([
            ("Bajamos los datos",
             "De dos fuentes públicas: una con los resultados, la clasificación y el campeonato de "
             "cada Gran Premio, y otra con cada vuelta de las prácticas libres (tiempo, goma, si "
             "entró a boxes, si hubo bandera). Los guardamos tal como vienen. Arrancamos en "
             f"{int(df['Year'].min())} porque es el primer año con las vueltas de prácticas "
             "registradas: antes hay resultados pero no prácticas, y las filas no serían "
             f"comparables. Llegamos hasta la {corte_fecha} de {corte_anio}."),
            ("Los juntamos en una tabla",
             "Para cada Gran Premio nos quedamos con las vueltas de prácticas que sirven para medir "
             "ritmo y guardamos, para cada goma, la mejor y el promedio (abajo, un ejemplo). Lo "
             "unimos con resultados, clasificación y campeonato, y pasamos cada tiempo a «cuánto más "
             "lento que el mejor de esa carrera», para comparar circuitos distintos. Al final junta "
             f"todas las carreras: {filas_crudas_txt} filas, una por piloto y carrera, con "
             f"{n_columnas} datos cada una."),
            ("Revisamos las filas",
             f"En {rondas_dup} fechas ({fechas_dup}) había pilotos cargados dos veces, sin forma "
             "de saber cuál era la fila buena: las sacamos enteras. Quedan "
             f"{n_filas_txt} filas de {n_carreras} Grandes Premios."),
            ("Elegimos los datos",
             f"De los {n_columnas} quedan 8: los que se saben antes de largar, sirven para "
             "carreras futuras y dicen algo que otro dato no dice. En el gráfico de abajo, qué "
             "salió y por qué."),
        ]),
        '<div class="dos-columnas">',
        p("**Un ejemplo: cómo sale la mejor vuelta con cada goma.** Ese dato no viene hecho: lo "
          "armamos nosotros con cada vuelta de las prácticas. Así fue con "
          f"{cv['piloto'].capitalize()} en el {cv['gran_premio']}: dio {cv['total']} vueltas en "
          f"FP1, FP2 y FP3, y solo {cv['quedan']} sirven para medir ritmo. Primero salen las "
          f"entradas y salidas de boxes ({mot('Entrada o salida de boxes')}), las que tienen un "
          f"tiempo poco confiable o incompleto ({mot('Tiempo poco confiable o incompleto')}), las "
          f"anuladas por los comisarios ({mot('Anulada por los comisarios')}) y las que tuvieron "
          f"bandera o auto de seguridad ({mot('Bandera o auto de seguridad')}). Después, en cada "
          "sesión y con cada goma, las que son más de 5 % más lentas que su mejor vuelta "
          f"({mot('Más de 5 % más lenta que su mejor con esa goma')}): por ejemplo, vueltas de "
          "enfriamiento o con tráfico. Con las que quedan se guardan dos datos por goma: la mejor "
          f"vuelta (con blandas, {blandas['mejor_txt']}) y el promedio ({blandas['promedio_txt']}). "
          "Cuánto más lento es el promedio que la mejor es el desgaste de esa goma "
          f"({fmt(blandas['desgaste'], 1)}\u00a0% con blandas), uno de los dos datos que calcula el modelo."),
        grafico("vueltas"),
        "</div>",
        '<div class="dos-columnas">',
        p("**Qué salió y por qué.** Leé el gráfico de arriba hacia abajo: cada barra gris es un "
          "grupo de datos que sacamos, con el motivo al lado. Detrás hay tres reglas. **Solo vale "
          "lo que se sabe antes de largar:** usar si terminó o si lo sancionaron sería hacer "
          "trampa. **Tiene que servir para carreras futuras:** quién es el piloto o el equipo "
          "funciona en estos años pero no se sostiene (en el EDA, el puesto promedio de Red Bull "
          "pasa de 3,6 en 2023 a 9,1 en 2026). **Tiene que decir algo nuevo:** la "
          "telemetría parecía útil, pero lo que mostraba es que los autos rápidos largan "
          "adelante, y eso ya lo dice la grilla. Los dos datos calculados los arma el modelo con "
          "las vueltas de las prácticas: cuánto se gastan las gomas."),
        grafico("columnas"),
        "</div>",
        '<div class="dos-columnas">', grafico("datos"),
        p("**Con qué trabajamos.** De esos 8 datos, no todos están siempre. En el gráfico, cada "
          "casilla es el % de pilotos con ese dato en esa temporada: más lleno, más completo. La "
          "largada y la clasificación están casi siempre, el campeonato falta solo en la primera "
          "fecha (todavía no hay puntos), y las prácticas tienen huecos en 2018-2019 y 2023-2024 "
          f"({hay_practica.mean():.0%} en total; en {gp_sin_practica} de los {n_carreras} Grandes "
          "Premios no hay ningún dato de prácticas). **Ninguna fila se descarta por un faltante:** "
          "a la derecha de cada dato está qué hace el modelo cuando falta. El «valor típico» es el "
          "del medio (la mediana) de las temporadas con las que aprendió, y la marca le avisa al "
          "modelo que ese valor fue completado, así no lo confunde con uno real. Lo que siempre "
          "está, la grilla, va a ser lo que más pesa."),
        "</div>",
        como_lo_sabemos(
            p("**De dónde salen.** Del proceso automático de descarga que armamos en la Entrega 1 "
              f"(con Airflow; [ver el código]({PIPELINE})), a partir "
              "de las estadísticas estilo Ergast (resultados, clasificación y "
              "campeonato) y la telemetría de FastF1 (prácticas libres): "
              f"{filas_crudas_txt} filas, una por piloto en cada Gran Premio, "
              f"de {int(df['Year'].min())} a {int(df['Year'].max())}, con corte en la "
              f"{corte_fecha} de {corte_anio} (datos del {FECHA_DATOS}). El respaldo es el archivo "
              f"{archivo_datos}, guardado en el repositorio; "
              "build_app.py lo lee de ahí."),
            p("**Qué filtramos.** Revisamos los datos paso a paso y "
              "anotamos cuántas filas quedaron después de cada uno:"),
            tabla_html(*tabla_nb("Limpieza aplicada")),
            p("**Qué columnas salieron.** Cada motivo sale del EDA (Entrega 2): lo que se conoce "
              "después de la carrera (fuga), los identificadores (su fuerza cambia con la era), "
              "la regla ABS contra DBT (gana la distancia al mejor en las nueve métricas), H3 (la "
              "telemetría: descontada la grilla, la correlación parcial cae a 0,129), H4 (el "
              "contexto de la fecha, todo en rojo), la redundancia (Q_Position contra la grilla, "
              "0,961) y la falta de datos. El campeonato se toma como estaba antes de cada fecha, "
              "y si terminó o no se usa solo para medir."),
            tabla_html(["Motivo", "Cuántas", "Columnas"],
                       [[nombre, str(len(cols)), ", ".join(cols)] for nombre, _, cols in tallo.DESCARTES]
                       + [["Quedan", str(len(tallo.QUEDAN)), ", ".join(tallo.QUEDAN)],
                          ["Calculadas por el modelo", str(len(tallo.CALCULADAS)),
                           ", ".join(tallo.CALCULADAS) + " (con FP_LapTime_min/mean_SOFT/MED_ABS)"]]),
            p("**Cómo se arman los gráficos.** El de columnas cuenta cuántas quedan después de cada "
              "motivo, en el orden en que se leen. El de temporadas cuenta, para cada una, qué "
              "parte de los pilotos tiene cada dato. Un grupo cuenta como presente si el piloto "
              "tiene al menos uno de sus datos, por ejemplo la vuelta más rápida con alguna de las "
              "tres gomas. Los grupos y sus colores son los mismos que en «Por qué el modelo "
              "mueve a cada piloto»."),
            nota(f"Limitación: en {gp_sin_practica} Grandes Premios no hay "
                 "ningún dato de prácticas. El modelo completa los faltantes "
                 "con la mediana del entrenamiento y marca que faltaban.")),

        # ---- Sector 2 · Lo que encontramos -------------------------------------------------------
        estilo.seccion(2, "Quien larga adelante termina adelante, y lo que más desordena la carrera "
                   "son los abandonos"),
        '<div class="dos-columnas">',
        p("**Cómo se lee.** Cada fila es una franja de largada y cada columna, una franja de "
          "llegada. Cada casilla dice qué parte de los que largaron en esa fila terminó en esa "
          f"columna, así que cada fila suma 100 %. Son los {n_carreras} Grandes Premios de 2018 a "
          f"{ANIO_TEST}. Si la grilla acertara siempre, todo estaría en la diagonal: cuanto más "
          "oscura la diagonal, mejor predice la grilla. Los dos mapas tienen las mismas franjas y "
          "los mismos colores: el primero cuenta a todos los pilotos, y el segundo, solo a los "
          "que terminaron la carrera. Las notas de cada gráfico marcan qué mirar."),
        grafico("grilla"),
        "</div>",
        '<div class="dos-columnas">', grafico("grilla-sin"),
        p(f"**Sin los que abandonaron.** Es el mismo cruce, contando solo a los {n_term_txt} pilotos "
          f"que terminaron la carrera (salen {n_ab_txt} abandonos). La diagonal se oscurece: de los "
          f"que largan entre los 5 primeros, el {pct(sq_t['1–5'])} termina ahí (con todos, "
          f"{pct(sq['1–5'])}), y en el medio sube a {pct(sq_t['6–10'])} y {pct(sq_t['11–15'])} "
          f"(con todos, {pct(sq['6–10'])} y {pct(sq['11–15'])}). Buena parte de lo que «mezclaba» la "
          "carrera eran abandonos: el que abandona queda entre los últimos, largue donde largue. "
          f"La única casilla de la diagonal que baja es la de atrás ({pct(sq_t['16 o más'])}, con "
          f"todos {pct(sq['16 o más'])}): esos últimos puestos eran de los que abandonaron, y sin "
          "ellos los que largan atrás terminan un poco más adelante. Es lo mismo que se ve en el "
          "Sector 3: sin abandonos, tanto la grilla como el modelo aciertan más."),
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
            "Los que largan desde boxes (sin posición de grilla) cuentan en «16 o más». El mapa "
            "«Sin los que abandonaron» hace la misma cuenta solo con los que terminaron la carrera (columna "
            "«Terminó», que no entra al modelo: se usa solo para medir)."),
            p("**Dónde gana el modelo, por franja de largada.** Error medio en puestos de cada "
              f"predicción, en las temporadas 2018 a {ANIO_TEST}: cada una la predice un modelo que "
              f"no la vio (2018 a {ANIO_TEST - 1}, con la validación por temporada; {ANIO_TEST}, "
              "con el modelo final). Incluye a los que abandonaron."),
            tabla_html(["Largó", "Pilotos-carrera", "Grilla", "Modelo"],
                       [[f, f"{cg['n_por_franja'][f]:,}".replace(",", "."),
                         fmt(cg['error'][f]['Grilla']), fmt(cg['error'][f]['Modelo'])]
                        for f in ["1–5", "6–10", "11–15", "16 o más"]])),

        '<div class="dos-columnas">', grafico("abandonos"),
        p(f"**Los abandonos pasan siempre.** No son una rareza: hay en todas las temporadas, en "
          f"promedio uno de cada {round(1 / pct_dnf)} pilotos, y "
          + (f"{ANIO_TEST}, el año del test, es el que más tiene. "
             if anio_mas_abandonos == ANIO_TEST else
             f"el año con más es {anio_mas_abandonos}. ")
          + "Y no se pueden anticipar con lo que se sabe antes de la carrera: probamos predecir "
          f"quién abandona y el resultado fue casi como adivinar (AUC {auc_abandonos}; 0,5 es "
          "adivinar y 1, acertar siempre). Por eso, de acá en adelante medimos dos veces: con "
          "todos los pilotos y sin los que abandonaron."),
        "</div>",
        como_lo_sabemos(
            p("**¿Podíamos anticiparlos?** Probamos un clasificador adicional "
              "con datos previos a la carrera y lo evaluamos por temporadas. "
              "Usamos el área bajo la curva ROC (AUC), que mide su capacidad "
              "para distinguir quién termina y quién no: 0,5 equivale "
              "a ordenar al azar y 1 a distinguirlos perfectamente."),
            tabla_html(*tabla_nb("Anticipar abandonos")),
            p(f"**Conclusión.** El AUC promedio fue **{auc_abandonos}**: "
              "el clasificador probado mostró poca capacidad para anticipar "
              "los abandonos. Son una limitación de nuestro enfoque.")),

        # ---- Sector 3 · El modelo ----------------------------------------------------------------
        estilo.seccion(3, f"El modelo le gana a la grilla en los que terminan la carrera "
                   f"({fmt(test['mae_modelo_sin_abandonos'])} contra "
                   f"{fmt(test['mae_grilla_sin_abandonos'])} puestos), pero con los abandonos quedan casi "
                   f"empatados ({fmt(test['mae_modelo'])} contra {fmt(test['mae_grilla'])})"),
        p(f"Son las {test['carreras']} carreras del test ({ANIO_TEST}), que el modelo no vio al "
          "entrenar. Leé los tres pasos de izquierda a derecha: la flecha marca qué mirar en cada "
          "gráfico, y debajo está la explicación."),
        '<div class="pasos-fila">',
        '<div class="paso">', grafico("paso-1"),
        p("**Cómo se lee.** Cada barra cuenta cuántos pilotos terminaron a esa distancia del puesto "
          "que se les predijo. En el 0, la predicción acertó. A la izquierda están los que "
          "terminaron más atrás de lo predicho, y a la derecha, los que terminaron más adelante. "
          "La grilla es la vara que el modelo tiene que superar: es lo que diría cualquiera que "
          "mira la clasificación del sábado. Y es difícil de superar, porque en la Fórmula 1 el "
          "que larga adelante suele terminar adelante."),
        "</div>",
        '<div class="paso">', grafico("paso-2"),
        p("**Qué agrega el modelo.** Además de la posición de largada, mira los puntos del "
          "campeonato y el ritmo en las prácticas. Con eso puede mover a un piloto lejos de donde "
          "largó, y por eso en las zonas sombreadas las barras azules quedan más bajas que las "
          f"ámbar: erra por {cp['grande']} puestos o más con {cp['grandes']['Modelo']} pilotos, y "
          f"la grilla con {cp['grandes']['Grilla']}. A cambio, acierta el puesto exacto menos "
          f"veces ({cp['exactos']['Modelo']} contra {cp['exactos']['Grilla']}): la grilla le "
          "pega justo a los que no se mueven de su lugar."),
        "</div>",
        '<div class="paso">', grafico("paso-3"),
        p(f"**Por qué el promedio casi no baja.** En el test abandonaron {cp['abandonos']} de los "
          f"{cp['pilotos']} pilotos ({fmt(pct_ab_filas * 100, 0)} %). Ninguna de las dos "
          "predicciones sabe quién va a abandonar: los ubican según cómo venían, y al abandonar "
          "quedan últimos. Con ellos, el modelo se equivoca por "
          f"{fmt(cp['mae_modelo_por_estado']['Abandonó'], 1)} puestos en promedio; con los demás, "
          f"por {fmt(cp['mae_modelo_por_estado']['Terminó'], 1)}. Son "
          f"{fmt(pct_ab_filas * 100, 0)} % de los pilotos, pero explican el "
          f"{fmt(cp['pct_error_abandonos']['Modelo'] * 100, 0)} % del error del modelo (y el "
          f"{fmt(cp['pct_error_abandonos']['Grilla'] * 100, 0)} % del de la grilla). Como los dos "
          "fallan casi igual con ellos, ese error tapa la mejora del paso 2."),
        "</div>",
        "</div>",
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
              "El error más grande lo ponen los abandonos (abajo)."),
            tabla_tramos(),
            nota("Test 2026. Sesgo = puesto predicho − puesto real: positivo, lo pone "
                 "más atrás de donde terminó; negativo, más adelante. El error más "
                 "grande está en los que terminan 16.º o peor, donde caen los abandonos."),
            p("**Cuánto pesan los abandonos en el error.** Separamos a quienes terminaron "
              "de quienes no terminaron y sumamos sus errores absolutos. "
              "La tabla compara cuántos registros representan y qué parte "
              "del error total concentran en el test."),
            tabla_html(*tabla_nb("Peso de los abandonos")),
            p("**En qué se apoya.** Estos pesos muestran cómo cada entrada "
              "contribuye al puntaje que usamos para ordenar a los pilotos. "
              "Un peso positivo aumenta ese puntaje y tiende a ubicarlos "
              "más atrás; uno negativo, más adelante, manteniendo "
              "las demás entradas iguales."),
            tabla_html(*tabla_nb("Coeficientes del modelo final")),
            nota("Los pesos corresponden a variables transformadas y escaladas: "
                 "no son puestos ganados o perdidos por cada unidad original "
                 "ni demuestran una relación causal.")),
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
        '<div class="fila-temporada"><label class="campo">Temporada <select id="temporada">'
        + "".join(f"<option>{a}</option>" for a in anios) + "</select></label>"
        '<p class="nota" id="nota-temporada"></p></div>',
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
        '<div class="fila-controles controles-modelo" id="proba-controles"></div>'
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
