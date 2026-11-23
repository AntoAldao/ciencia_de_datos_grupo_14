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
from graficos import colores as C
from graficos import carreras, logos, model_moves, pasos, race_cars, race_errors, season_points, tallo
from web import explora

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
CARRERAS_GUIADAS = (4, 13)   # fechas del test que el Sector 3 recorre con texto (los textos las nombran)
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
# el menú lateral: versiones cortas de los títulos de cada sector («{n}»: columnas del pipeline)
RECORRIDO = ["Los datos: de {n} a 8", "La largada y los abandonos", "El modelo contra la grilla"]
EXPLORAR = [("Explorá los datos", "explora-los-datos", "✦"),   # (texto, ancla, ícono)
            ("Todos los pilotos", "todos-los-pilotos", "⌕"),
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


PILOTO_EJEMPLO = "colapinto"   # el piloto de los ejemplos de la portada


def ejemplos_portada(df: pd.DataFrame, piloto: str = PILOTO_EJEMPLO) -> dict:
    """Dos carreras del test que explican las tarjetas de la portada con un caso real.

    - «termina»: una carrera que terminó y en la que el modelo erró menos que la grilla
      (la de menor error del modelo y, entre esas, la de mayor error de la grilla).
    - «abandona»: una carrera que no terminó (la de mayor error de la grilla).
    Los errores se miden igual que en el notebook: puestos ordenados dentro de cada carrera, y la
    grilla faltante cuenta como largar último (21). Si el piloto no tiene un caso, se usa el que
    mejor lo tenga entre todos.
    """
    t = df[df["Year"] == ANIO_TEST].copy()
    car = t["Carrera"]
    real = t["Puesto"].groupby(car).rank(method="average")
    grilla = t["Q_GridPosition"].fillna(21).groupby(car).rank(method="average")
    t["error_modelo"] = (t["puesto_modelo"] - real).abs()
    t["error_grilla"] = (grilla - real).abs()
    termino = t["Terminó"] != False  # noqa: E712

    def elegir(filas: pd.DataFrame, orden: list[str], ascendente: list[bool]) -> pd.Series:
        propias = filas[filas["DriverId"] == piloto]
        return (propias if len(propias) else filas).sort_values(orden, ascending=ascendente).iloc[0]

    mejores = t[termino & (t["error_modelo"] < t["error_grilla"])]
    fila_t = elegir(mejores, ["error_modelo", "error_grilla", "RoundNumber"], [True, False, False])
    fila_a = elegir(t[~termino], ["error_grilla", "RoundNumber"], [False, False])

    def caso(f: pd.Series) -> dict:
        return {"piloto": f["DriverId"].replace("_", " ").title(), "equipo": f["TeamId"],
                "gp": carreras.nombre(int(f["Year"]), int(f["RoundNumber"])), "anio": int(f["Year"]),
                "largo": int(f["Q_GridPosition"]) if pd.notna(f["Q_GridPosition"]) else None,
                "modelo": int(round(f["puesto_modelo"])), "termino": int(f["Puesto"]),
                "autos": int(f["Autos_en_carrera"]),
                "error_modelo": int(round(f["error_modelo"])), "error_grilla": int(round(f["error_grilla"]))}

    return {"termina": caso(fila_t), "abandona": caso(fila_a)}


def tarjetas_portada(test: dict, ej: dict, pct_error: float, pct_filas: float,
                     n_abandonos: int, n_pilotos: int, mae_abandona: float, mae_termina: float) -> str:
    """Las tres tarjetas de la portada, cada una con su ejemplo. Comparten las mismas filas
    (rótulo, número, explicación, ejemplo, dibujo y leyenda), así quedan alineadas.

    En reposo, modelo y grilla usan los colores de los gráficos (graficos/colores.py); al pasar el
    mouse por una tarjeta se encienden los de la escudería del ejemplo (ver .tarjetas-portada en pagina.css).
    """
    def pos(puesto: int, autos: int) -> float:         # puesto -> % sobre la recta del 1.º al último
        return (puesto - 1) / (autos - 1) * 100

    def cabecera(c: dict) -> str:
        logo = logos.uri(c["equipo"])
        img = (f'<img src="{logo}" alt="{html.escape(logos.nombre(c["equipo"]))}">' if logo else "")
        return (f'<div class="quien">{img}{html.escape(c["piloto"])} '
                f'<span>· {html.escape(c["gp"])} {c["anio"]}</span></div>')

    def recta(puntos: list[tuple[str, int]], tramo: tuple[int, int, str], texto: str, autos: int,
              etiqueta: str) -> str:
        desde, hasta, clase = tramo
        izq, der = sorted((pos(desde, autos), pos(hasta, autos)))
        marcas = "".join(f'<div class="punto {cl}" style="left:{pos(p, autos):.1f}%"></div>'
                         for cl, p in puntos)
        return (f'<div class="pista" role="img" aria-label="{html.escape(etiqueta)}"><div class="linea"></div>'
                f'<div class="tramo {clase}" style="left:{izq:.1f}%;width:{der - izq:.1f}%"></div>{marcas}'
                f'<div class="tick" style="left:0%">1.º</div>'
                f'<div class="tick" style="left:{(izq + der) / 2:.1f}%">{html.escape(texto)}</div>'
                f'<div class="tick" style="left:100%">{autos}.º</div></div>')

    def leyenda(items: list[tuple[str, str]]) -> str:
        return ('<div class="leyenda">'
                + "".join(f'<span><i class="{cl}"></i>{html.escape(t)}</span>' for cl, t in items)
                + "</div>")

    t, a = ej["termina"], ej["abandona"]
    largo_t = t["largo"] or t["autos"]
    largo_a = a["largo"] or a["autos"]
    tarjeta1 = (
        '<div class="tarjeta"><span class="rotulo">1 · Entre los que terminan</span>'
        f'<span class="valor"><span class="m">{fmt(test["mae_modelo_sin_abandonos"])}</span> vs. '
        f'<span class="g">{fmt(test["mae_grilla_sin_abandonos"])}</span></span>'
        '<span class="ayuda">puestos de error por piloto: el <b class="m">modelo</b> erra menos que '
        'la <b class="g">grilla</b>.</span><div class="separador"></div>'
        f'<div class="caso">{cabecera(t)}Largó {largo_t}.º. El modelo dijo {t["modelo"]}.º y '
        f'<b>terminó {t["termino"]}.º</b>'
        + (": acertó justo" if t["error_modelo"] == 0 else f": le erró por {t['error_modelo']}")
        + f". La grilla le erró por {t['error_grilla']}.</div>"
        + recta([("g", largo_t), ("m", t["modelo"]), ("r", t["termino"])], (largo_t, t["termino"], "g"),
                f"error de la grilla: {t['error_grilla']}", t["autos"],
                f"Largó {largo_t}.º, el modelo dijo {t['modelo']}.º y terminó {t['termino']}.º")
        + leyenda([("g", f"Largó {largo_t}.º"), ("m", f"Modelo {t['modelo']}.º"),
                   ("r", f"Terminó {t['termino']}.º")])
        + "</div>")
    tarjeta2 = (
        '<div class="tarjeta"><span class="rotulo">2 · Contando a todos</span>'
        f'<span class="valor"><span class="m">{fmt(test["mae_modelo"])}</span> vs. '
        f'<span class="g">{fmt(test["mae_grilla"])}</span></span>'
        '<span class="ayuda">puestos de error por piloto: con los abandonos, quedan '
        '<b>casi empatados</b>.</span><div class="separador"></div>'
        f'<div class="caso">{cabecera(a)}Largó {largo_a}.º y el modelo dijo {a["modelo"]}.º… pero '
        f'<b>abandonó</b> y quedó {a["termino"]}.º. La grilla le erró por {a["error_grilla"]} y el '
        f'modelo, por {a["error_modelo"]}.</div>'
        + recta([("g", largo_a), ("m", a["modelo"]), ("a", a["termino"])],
                (min(largo_a, a["modelo"]), a["termino"], "a"),
                f"error: grilla {a['error_grilla']}, modelo {a['error_modelo']}", a["autos"],
                f"Largó {largo_a}.º, el modelo dijo {a['modelo']}.º, abandonó y quedó {a['termino']}.º")
        + leyenda([("g", f"Largó {largo_a}.º"), ("m", f"Modelo {a['modelo']}.º"),
                   ("a", f"Abandonó: {a['termino']}.º")])
        + "</div>")
    tarjeta3 = (
        '<div class="tarjeta abandonos"><span class="rotulo">3 · Por qué se empatan</span>'
        f'<span class="valor"><span class="a">{pct_error:.0f}%</span></span>'
        f'<span class="ayuda">del error lo aportan los <b>abandonos</b>, que son apenas 1 de cada '
        f'{round(100 / pct_filas)} pilotos.</span><div class="separador"></div>'
        f'<div class="caso"><div class="quien"><span class="icono">✕</span>Los {n_abandonos} abandonos '
        f'<span>· test {ANIO_TEST}</span></div>Al que abandona se le erra por '
        f'<b>{fmt(mae_abandona, 1)}</b> puestos; al que termina, por <b>{fmt(mae_termina, 1)}</b>. Y '
        'nadie puede anticipar quién abandona.</div>'
        f'<div class="barras" role="img" aria-label="Abandonos: {pct_filas:.0f}% de los pilotos y '
        f'{pct_error:.0f}% del error">'
        f'<div class="barra pilotos"><span>de los pilotos</span><div class="fondo"><div class="lleno" '
        f'style="width:{pct_filas:.0f}%"></div></div><b>{pct_filas:.0f}%</b></div>'
        f'<div class="barra error"><span>del error</span><div class="fondo"><div class="lleno" '
        f'style="width:{pct_error:.0f}%"></div></div><b>{pct_error:.0f}%</b></div></div>'
        + leyenda([("a", f"Abandonaron: {n_abandonos} de {n_pilotos} pilotos")])
        + "</div>")
    return (f'<div class="tarjetas-portada" style="--c-modelo:{C.MODELO};--c-grilla:{C.GRILLA};'
            f'--c-grilla-punto:{C.GRILLA};--c-abandono:{C.ABANDONO}">'
            f"{tarjeta1}{tarjeta2}{tarjeta3}</div>")


def metrica(rotulo: str, valor: str, ayuda: str) -> str:
    return (f'<div class="metrica"><span class="rotulo">{html.escape(rotulo)}</span>'
            f'<span class="valor">{html.escape(valor)}</span>'
            f'<span class="ayuda">{html.escape(ayuda)}</span></div>')


def grafico(nombre: str) -> str:
    """Hueco donde pagina.js dibuja la spec `nombre` cuando se acerca a la pantalla."""
    return f'<div class="grafico" data-spec="{nombre}"><div class="vista"></div></div>'


def carrera_animada(nombre: str) -> str:
    """Una carrera animada con sus botones «Correr» y «Volver a la largada» (los conecta
    pagina.js cuando la dibuja)."""
    return (f'<div class="grafico autos" data-spec="{nombre}"><div class="controles-autos">'
            '<button class="correr" type="button">Correr</button>'
            '<button class="largada" type="button">Volver a la largada</button>'
            '<span class="pista">Arriba, con todos los pilotos; abajo, sin los que abandonaron.'
            '</span></div><div class="marco"><div class="vista"></div></div></div>')


def como_leer(items: list[tuple[str, str, bool]], clase: str = "", plegado: bool = False) -> str:
    """Cómo leer el gráfico de las carreras guiadas, todo junto. `items`: (título, texto,
    solo en la versión completa del gráfico). `plegado`: en una línea que se despliega (para
    la segunda carrera, que ya se leyó la primera)."""
    lista = ("<dl>" + "".join(f'<div{" class=solo-completo" if solo else ""}><dt>{html.escape(t)}'
                              f"</dt><dd>{md(d)}</dd></div>" for t, d, solo in items) + "</dl>")
    if plegado:
        return (f'<details class="como-leer {clase} plegada"><summary>Cómo leer el gráfico'
                f"</summary>{lista}</details>")
    return f'<div class="como-leer {clase}"><h4>Cómo leer el gráfico</h4>{lista}</div>'


def carrera_guiada(ronda: int, grupos: list[tuple], resumen: str,
                   leyenda: list[tuple[str, str, bool]], descripciones: dict[str, str],
                   titulo: str, pistas: dict[str, tuple[str, str]], filas: int,
                   leyenda_plegada: bool = False, salida: str = "",
                   destino_salida: str = "", ganador: str = "", orden: str = "") -> str:
    """Una carrera guiada (scrollytelling). El escenario (un fondo fijo que tapa la pantalla
    mientras dura la carrera) lleva a la izquierda el panel: título, en qué parada se está (y un
    link para saltear), las dos pistas con sus errores (se resalta la que se ve), «Cómo leer»,
    el gráfico y, debajo, el resumen (aparece con la última tanda). A la derecha, un lugar fijo
    donde entra la tanda de notas activa, cada tarjeta a la altura de su recuadro en el gráfico.
    El scroll lo marcan paradas invisibles (.marca): al llegar a una tanda corren los autos de
    esa pista y se prenden los recuadros numerados. pagina.js lee los `data-*`, ubica las
    tarjetas y dimensiona el panel.
    `grupos`: [(pista, [(n, título, texto, fila)])], con n de arriba hacia abajo y `fila` el
    puesto donde está el recuadro. `descripciones`: por pista, el resultado en palabras para
    lectores de pantalla. `filas`: autos de la carrera. `leyenda_plegada`: «Cómo leer» en una
    línea (sin parada propia). `salida`/`destino_salida`: texto y ancla del link para saltear.
    `ganador` («grilla» o «modelo»): el color de la carrera (franja arriba del panel y etiqueta
    junto al título, los mismos colores de la grilla y el modelo en los gráficos), para que se
    note el cambio de una carrera a la otra. `orden`: «Carrera 1 de 2»."""
    nombres = {"arriba": "con todos los pilotos", "abajo": "sin los que abandonaron"}
    rotulos = "".join(
        f'<li class="pista-rotulo" data-panel="{panel}"><b>{html.escape(nombre)}</b> '
        f"<span>{html.escape(detalle)}</span></li>"
        for panel, (nombre, detalle) in pistas.items())
    capas = "".join(
        f'<div class="capa" data-panel="{panel}" data-ancho="carrera-{ronda}-{panel}" '
        f'data-compacto="carrera-{ronda}-{panel}-c" role="img" '
        f'aria-label="{html.escape(descripciones[panel])}"><div class="vista"></div></div>'
        for panel in ("arriba", "abajo"))
    # las tandas: «Cómo leer» (en notebook, si no va plegado) y una por pista
    tandas = [] if leyenda_plegada else [
        ("intro", "arriba", 0, 0, 0, "Cómo leer el gráfico", como_leer(leyenda, "suelta"))]
    for panel, notas in grupos:
        tarjetas = "".join(
            f'<article class="paso-nota" data-n="{n}" data-fila="{fila:g}" tabindex="0">'
            f'<span class="num" aria-hidden="true">{n}</span>'
            f'<div><h4><span class="solo-lectores">Nota {n}: </span>{html.escape(t)}</h4>'
            f"<p>{md(texto)}</p></div></article>" for n, t, texto, fila in notas)
        tandas.append(("", panel, 1, notas[0][0], notas[-1][0], pistas[panel][0], tarjetas))
    grupos_html = "".join(
        f'<section class="grupo-pasos {clase}" data-panel="{panel}" data-hasta="{hasta}" '
        f'data-min="{pmin}" data-max="{pmax}" data-nombre="{html.escape(nombre)}" '
        f'aria-label="{html.escape(nombre)}">{contenido}</section>'
        for clase, panel, hasta, pmin, pmax, nombre, contenido in tandas)
    marcas = "".join(f'<div class="marca {t[0]}" data-grupo="{i}"></div>' for i, t in enumerate(tandas))
    etiqueta = {"grilla": "Gana la grilla", "modelo": "Gana el modelo"}.get(ganador, "")
    return (f'<div class="guiada gana-{ganador}" id="carrera-guiada-{ronda}" data-carrera="{ronda}" '
            f'data-filas="{filas}"><div class="escenario"><div class="guiada-grafico">'
            f'<header class="guiada-cabecera"><h3 id="fecha-{ronda}">{html.escape(titulo)} '
            f'<span class="ganador">{html.escape(etiqueta)}</span></h3>'
            f'<p class="guiada-progreso"><span><span class="orden">{html.escape(orden)} · </span>'
            f'<span class="parada" aria-live="polite">Bajá para empezar ↓</span></span>'
            f'<a class="saltar" href="#{destino_salida}">{html.escape(salida)} ↓</a></p>'
            f'<ul class="pistas">{rotulos}</ul></header>'
            f'{como_leer(leyenda, "fija", plegado=leyenda_plegada)}'
            f'<div class="guiada-lienzo">{capas}</div>'
            f'<div class="guiada-resumen" aria-live="polite">{md(resumen)}</div></div></div>'
            f'<div class="guiada-pasos"><div class="guiada-notas">{grupos_html}</div>'
            f'<div class="marcas">{marcas}</div></div></div>'
            f'<span class="ancla-salida" id="despues-{ronda}"></span>')


def comprimido(nombre: str, dato) -> str:
    """Un dato JSON adentro de la página, en gzip + base64 (lo lee `datos()` en pagina.js)."""
    crudo = json.dumps(dato, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(gzip.compress(crudo, compresslevel=9, mtime=0)).decode("ascii")
    return f'<script type="application/gzip" id="dato-{nombre}">{b64}</script>'


def en_script(texto: str) -> str:
    """Texto que va adentro de un <script>: no puede cerrar la etiqueta."""
    return texto.replace("</script", "<\\/script").replace("<!--", "<\\!--")


# ---- la página -----------------------------------------------------------------------------------
def tabla_pilotos(tablas: dict[int, pd.DataFrame], df: pd.DataFrame) -> dict:
    """«Todos los pilotos»: una fila por piloto en cada GP, en columnas (así pesa menos).

    Los puestos son los de «Carrera por carrera» (`race_cars.race_table`): `l` largada, `m`
    predicción del modelo, `f` final; `ma`/`ga`, el modelo y la grilla reordenados solo entre los
    que terminaron (la cuenta «sin abandonos» de toda la página); `lg`/`ga`/`fa`, la grilla y
    el final con los que se mide (empates con el puesto promedio). Los textos repetidos (GP,
    piloto, escudería) van en listas aparte y las filas guardan su índice."""
    t = pd.concat(tablas.values(), ignore_index=True)
    t["Carrera"] = t["race"].str.replace("-", "-R")
    extra = df.set_index(["Carrera", "DriverId"])[
        ["Q_Best_seconds_DBT_%", "DriverPoints_Before", "DriverPosition_Before", "Q_GridPosition"]]
    t = t.join(extra, on=["Carrera", "driver_id"])
    t["anio"] = t["race"].str[:4].astype(int)
    t["ronda"] = t["race"].str[5:].astype(int)
    t = t.sort_values(["anio", "ronda", "final_official"]).reset_index(drop=True)
    t["gp_nombre"] = [carreras.nombre(a, r) for a, r in zip(t["anio"], t["ronda"])]
    t["piloto"] = t["driver_id"].str.replace("_", " ").str.title()
    t["escuderia"] = t["team"].map(logos.nombre)
    listas = {k: sorted(t[c].unique()) for k, c in
              [("gps", "gp_nombre"), ("pilotos", "piloto"), ("equipos", "escuderia")]}
    indice = lambda k, c: t[c].map({v: i for i, v in enumerate(listas[k])}).tolist()  # noqa: E731
    num = lambda c, d=None: [None if pd.isna(x) else (round(float(x), d) if d else int(x))  # noqa: E731
                             for x in t[c]]
    fin = t["dnf"] == 0
    # para medir, las mismas reglas que `race_cars.race_table` (y los títulos): la grilla
    # empatada con el puesto promedio y, sin abandonos, el final reordenado entre los que terminaron
    grilla = t["Q_GridPosition"].fillna(21)
    t["grid_avg"] = grilla.groupby(t["race"]).rank(method="average")
    t["grid_avg_fin"] = grilla[fin].groupby(t.loc[fin, "race"]).rank(method="average")
    t["final_fin"] = t.loc[fin, "final"].groupby(t.loc[fin, "race"]).rank(method="average")
    medio = lambda c: [None if pd.isna(x) else float(x) for x in t[c]]  # noqa: E731
    return {**listas, "columnas": {
        "a": t["anio"].tolist(), "r": t["ronda"].tolist(),
        "gp": indice("gps", "gp_nombre"), "p": indice("pilotos", "piloto"),
        "e": indice("equipos", "escuderia"), "s": t["driver"].tolist(), "c": t["color"].tolist(),
        "l": t["grid_official"].astype(int).tolist(), "m": t["pred_pos"].astype(int).tolist(),
        "f": t["final_official"].astype(int).tolist(), "ab": t["dnf"].astype(int).tolist(),
        "ma": [int(x) if ok else None for x, ok in zip(t["pred_adj"], fin)],
        "lg": medio("grid_avg"), "ga": medio("grid_avg_fin"), "fa": medio("final_fin"),
        "q": num("Q_Best_seconds_DBT_%", 2), "pts": num("DriverPoints_Before"),
        "cp": num("DriverPosition_Before"), "st": t["status"].astype(str).tolist()}}


# «Todos los pilotos»: los filtros, el resumen, el gráfico agrupado y la tabla (los llena pagina.js)
EXPLORADOR = """
<div class="explorador" id="explorador">
  <div class="exp-filtros">
    <label class="campo">Temporada <select data-filtro="anio"></select></label>
    <label class="campo">Gran Premio <select data-filtro="gp"></select></label>
    <label class="campo">Piloto <select data-filtro="piloto"></select></label>
    <label class="campo">Escudería <select data-filtro="equipo"></select></label>
    <fieldset class="campo exp-rango"><legend>Largó entre</legend>
      <input type="number" data-filtro="desde" min="1" max="26" aria-label="Largó desde el puesto">
      <span>y</span>
      <input type="number" data-filtro="hasta" min="1" max="26" aria-label="Largó hasta el puesto"></fieldset>
    <label class="campo">Resultado <select data-filtro="resultado">
      <option value="">Todos</option><option value="termino">Terminaron</option>
      <option value="abandono">Abandonaron</option></select></label>
    <label class="campo">Quién acertó mejor <select data-filtro="quien">
      <option value="">Cualquiera</option><option value="modelo">El modelo</option>
      <option value="grilla">La grilla</option><option value="igual">Empataron</option></select></label>
    <button type="button" class="exp-limpiar">Sacar los filtros</button>
  </div>
  <p class="exp-cuenta" aria-live="polite"></p>
  <div class="exp-resumen"></div>
  <div class="exp-grafico">
    <div class="exp-grafico-cabeza">
      <h4>Error promedio, agrupado por</h4>
      <div class="exp-agrupar" role="group" aria-label="Agrupar por"></div>
      <button type="button" class="exp-csv">Descargar CSV</button>
    </div>
    <p class="nota exp-ayuda">Clic en un grupo para filtrar por él.</p>
    <div class="vista"></div>
  </div>
</div>"""


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
    _, filas_peso = tabla_nb("Peso de los abandonos")
    fila_peso = lambda nombre: next(f for f in filas_peso if f[0] == nombre)  # noqa: E731
    n_abandonos_test = int(float(fila_peso("Filas")[1].replace(",", ".")))
    n_pilotos_test = test["filas"]
    mae_terminan_test = float(fila_peso("MAE de esas filas")[-1].replace(",", "."))   # «Resto de las filas»
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
    corte_anio, corte_fecha = resumen["datos"]["al_dia"].split(", ")   # «2026», «fecha 17»
    corte_gp = carreras.nombre(int(corte_anio), int(corte_fecha.split()[-1]))
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
    fechas_dup = " y ".join(f"{carreras.nombre(int(a), int(r))} de {a}"
                            for a, r in (f.split("-R") for f in fechas_dup.split(", ")))
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
    }
    tablas = {}
    for anio in anios:
        tabla = tablas[anio] = race_cars.race_table(df[df["Year"] == anio])
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
    # Sector 3: las carreras guiadas, cada una sola (sin menú) y con sus pilotos a mano (por sigla)
    guiadas = {}
    for ronda in CARRERAS_GUIADAS:
        guiadas[ronda] = tablas[ANIO_TEST][tablas[ANIO_TEST]["race"] == f"{ANIO_TEST}-{ronda:02d}"]
    g4, g13 = (guiadas[r].set_index("driver") for r in CARRERAS_GUIADAS)
    # «Probá el modelo»: la pista de la simulación (los datos los pone pagina.js)
    todas = pd.concat(tablas.values())
    sim_max_behind = float(np.ceil(todas["behind"].max()))
    specs["simulacion"] = race_cars.race_cars_sim(
        todas["team"].unique().tolist(), n_max=int(todas.groupby("race").size().max()),
        max_behind=sim_max_behind, model_name=nombre_modelo, width=1000)
    nom = lambda g, sigla: g.loc[sigla, "driver_id"].split("_")[-1].title()  # noqa: E731
    err = lambda g, sigla, col="pred_pos": int(abs(g.loc[sigla, col] - g.loc[sigla, "final"]))  # noqa: E731
    v = lambda g, sigla, col: int(g.loc[sigla, col])  # noqa: E731
    mae = lambda g, col: fmt(g[col].iloc[0])  # noqa: E731
    dnf = lambda g: g[g["dnf"] == 1].sort_values("final").index.tolist()  # noqa: E731
    nombres = lambda siglas, g: (", ".join(nom(g, x) for x in siglas[:-1])  # noqa: E731
                               + " y " + nom(g, siglas[-1]))
    # Las carreras guiadas del Sector 3 se cuentan en pasos: el gráfico queda quieto y al lado
    # pasan tarjetas; cada una mueve la carrera (`avance` de `desde` a `hasta` mientras se lee) y
    # prende su recuadro numerado en el gráfico (`paso`). Las notas son
    # (n, sigla, dónde va el recuadro, título, texto). Los números salen de los datos; qué piloto
    # se señala y por qué, de mirar cada carrera (y de los aportes de cada variable).
    notas_guiadas = {
        4: {
            "arriba": [
                (1, "LEC", "final", f"{nom(g4, 'LEC')}, al revés: lo subió y terminó {v(g4, 'LEC', 'final')}.º",
                 f"Largó {v(g4, 'LEC', 'grid')}.º y el modelo lo subió al "
                 f"{v(g4, 'LEC', 'pred_pos')}.º, sobre todo por los puntos que traía en el "
                 f"campeonato. Terminó {v(g4, 'LEC', 'final')}.º: el modelo erra por "
                 f"{err(g4, 'LEC')} y la grilla por {err(g4, 'LEC', 'grid')}."),
                (2, "NOR", "final", f"{nom(g4, 'NOR')}: el modelo lo bajó y terminó {v(g4, 'NOR', 'final')}.º",
                 f"Largó {v(g4, 'NOR', 'grid')}.º y el modelo lo bajó al "
                 f"{v(g4, 'NOR', 'pred_pos')}.º porque tenía menos puntos que los de adelante. "
                 f"Terminó {v(g4, 'NOR', 'final')}.º: el modelo erra por {err(g4, 'NOR')} y la "
                 f"grilla por {err(g4, 'NOR', 'grid')}."),
                (3, "GAS", "llegada", f"{nom(g4, 'GAS')} abandonó",
                 f"El modelo lo ponía {v(g4, 'GAS', 'pred_pos')}.º y quedó "
                 f"{v(g4, 'GAS', 'final')}.º: {err(g4, 'GAS')} puestos de error (la grilla, "
                 f"{err(g4, 'GAS', 'grid')}). Nadie podía saberlo antes de largar."),
                (4, "HAD", "final", f"{nom(g4, 'HAD')}: la grilla acierta de casualidad",
                 f"Largó último, abandonó y quedó último: error 0 para la grilla. El modelo lo "
                 f"subía al {v(g4, 'HAD', 'pred_pos')}.º y erra por {err(g4, 'HAD')}."),
            ],
            "abajo": [
                (5, dnf(g4), "grupo", "Sin los que abandonaron",
                 f"{nombres(dnf(g4), g4)} se detienen en la vuelta en que se retiraron, quedan grises al "
                 f"fondo y salen de la cuenta. Los de atrás suben un lugar por cada uno: a "
                 f"{nom(g4, 'BOR')} el modelo lo ponía {v(g4, 'BOR', 'pred_pos')}.º y ahora "
                 f"{v(g4, 'BOR', 'pred_adj')}.º. El error del modelo baja de "
                 f"{mae(g4, 'mae_model')} a {mae(g4, 'mae_adj')} y el de la grilla, de "
                 f"{mae(g4, 'mae_grid')} a {mae(g4, 'mae_grid_adj')}."),
                (6, "VER", "llegada", f"{nom(g4, 'VER')}: acá acierta el modelo",
                 f"Largó {v(g4, 'VER', 'grid')}.º, el modelo lo puso "
                 f"{v(g4, 'VER', 'pred_adj')}.º y terminó {v(g4, 'VER', 'final')}.º: erra por "
                 f"{err(g4, 'VER', 'pred_adj')}, la grilla por {err(g4, 'VER', 'grid_adj')}."),
                (7, "BOR", "final", f"{nom(g4, 'BOR')}: la remontada que nadie ve",
                 f"Largó {v(g4, 'BOR', 'grid')}.º y terminó {v(g4, 'BOR', 'final')}.º. Entre "
                 f"los que terminaron, el modelo lo ponía {v(g4, 'BOR', 'pred_adj')}.º y la "
                 f"grilla {v(g4, 'BOR', 'grid_adj')}.º: los dos erran por "
                 f"{err(g4, 'BOR', 'pred_adj')} o más."),
            ],
        },
        13: {
            "arriba": [
                (1, "ANT", ["largada", "llegada", "final"],
                 f"{nom(g13, 'ANT')} largó {v(g13, 'ANT', 'grid')}.º y ganó",
                 f"La grilla lo deja {v(g13, 'ANT', 'grid')}.º. El modelo lo sube al "
                 f"{v(g13, 'ANT', 'pred_pos')}.º: traía muchos puntos en el campeonato y su "
                 "tiempo de clasificación fue mucho mejor que su lugar de largada. No adivina que "
                 f"gana, pero erra por {err(g13, 'ANT')} y la grilla por "
                 f"{err(g13, 'ANT', 'grid')}: solo con él, el modelo saca "
                 f"{err(g13, 'ANT', 'grid') - err(g13, 'ANT')} puestos de ventaja."),
                (2, "NOR", "final", f"{nom(g13, 'NOR')}: acierto exacto",
                 f"Largó {v(g13, 'NOR', 'grid')}.º, el modelo lo puso "
                 f"{v(g13, 'NOR', 'pred_pos')}.º y terminó {v(g13, 'NOR', 'final')}.º. La "
                 f"grilla erra por {err(g13, 'NOR', 'grid')}."),
                (3, "LEC", "final", f"{nom(g13, 'LEC')} abandonó",
                 f"Los dos lo ponían {v(g13, 'LEC', 'pred_pos')}.º y quedó "
                 f"{v(g13, 'LEC', 'final')}.º: {err(g13, 'LEC')} puestos de error para cada "
                 "uno. Empatan, así que no cambia quién gana, pero sube el promedio de ambos."),
            ],
            "abajo": [
                (4, dnf(g13), "grupo", "Sin los que abandonaron",
                 f"{nombres(dnf(g13), g13)} se detienen en la vuelta en que se retiraron, quedan grises al "
                 f"fondo y salen de la cuenta. Los de atrás suben un lugar por cada uno: a "
                 f"{nom(g13, 'LAW')} el modelo lo ponía {v(g13, 'LAW', 'pred_pos')}.º y ahora "
                 f"{v(g13, 'LAW', 'pred_adj')}.º. El error del modelo baja de "
                 f"{mae(g13, 'mae_model')} a {mae(g13, 'mae_adj')} y el de la grilla, de "
                 f"{mae(g13, 'mae_grid')} a {mae(g13, 'mae_grid_adj')}."),
                (5, "GAS", "llegada", f"{nom(g13, 'GAS')} largó {v(g13, 'GAS', 'grid')}.º",
                 f"El modelo no le cree: lo baja al {v(g13, 'GAS', 'pred_adj')}.º porque tenía "
                 f"pocos puntos. Terminó {v(g13, 'GAS', 'final')}.º: el modelo erra por "
                 f"{err(g13, 'GAS', 'pred_adj')} y la grilla por {err(g13, 'GAS', 'grid_adj')}."),
                (6, "LAW", "final", f"{nom(g13, 'LAW')} largó último y terminó "
                 f"{v(g13, 'LAW', 'final')}.º",
                 f"Entre los que terminaron, el modelo lo ponía {v(g13, 'LAW', 'pred_adj')}.º "
                 f"(erra por {err(g13, 'LAW', 'pred_adj')}) y la grilla "
                 f"{v(g13, 'LAW', 'grid_adj')}.º (erra por {err(g13, 'LAW', 'grid_adj')})."),
            ],
        },
    }
    # Cómo leer el gráfico: va una sola vez, antes de la primera carrera (todo junto).
    como_se_lee = [   # (título, texto, solo en la versión completa del gráfico): cortos, entran
        # en dos líneas arriba del gráfico
        ("Largada", "El orden de salida: la predicción más simple.", False),
        ("La pista", "Cada auto llega al puesto del modelo; la estela marca cada cambio.", False),
        ("Final real", "Cómo terminó. Punteada: de la predicción al resultado. ✕ = no terminó.",
         False),
        ("Δ y Mejora", "Puestos ganados (+) o perdidos (−). ▲ el modelo erró menos que la grilla.",
         True),
    ]
    # Cada pista es un grupo de notas seguidas: al acercarse al grupo corren los autos y, al
    # llegar, ya están todas sus notas (y sus recuadros) a la vista.
    # La fila (puesto) donde está el recuadro de cada nota: ahí se ubica su tarjeta y por ahí
    # se numera (de arriba hacia abajo). Una nota con varios recuadros se ubica en el último
    # (Antonelli: su resultado).
    def fila_de(g, panel: str, sigla, donde) -> float:
        donde = donde[-1] if isinstance(donde, list) else donde
        if donde == "grupo":
            return float(g.loc[list(sigla), "final"].mean())
        col = {"final": "final", "largada": "grid",
               "llegada": "pred_pos" if panel == "arriba" else "pred_adj"}[donde]
        return float(g.loc[sigla, col])
    tablas_guiadas = {4: g4, 13: g13}
    for ronda in CARRERAS_GUIADAS:
        n = 0
        for panel in ("arriba", "abajo"):
            filas = [(fila_de(tablas_guiadas[ronda], panel, sigla, donde), k, sigla, donde, t, x)
                     for k, (_, sigla, donde, t, x) in enumerate(notas_guiadas[ronda][panel])]
            notas_guiadas[ronda][panel] = []
            for fila, _, sigla, donde, t, x in sorted(filas):
                n += 1
                notas_guiadas[ronda][panel].append((n, sigla, donde, t, x, fila))
    grupos_guiadas = {ronda: [(panel, [(n, titulo, texto, fila) for n, _, _, titulo, texto, fila
                                       in notas_guiadas[ronda][panel]])
                              for panel in ("arriba", "abajo")]
                      for ronda in CARRERAS_GUIADAS}
    def pistas_de(g) -> dict[str, tuple[str, str]]:
        """Rótulo y errores de cada pista, para la cabecera fija de la carrera guiada."""
        return {"arriba": ("Con todos los pilotos",
                           f"error medio: modelo {mae(g, 'mae_model')} · grilla {mae(g, 'mae_grid')}"),
                "abajo": (f"Sin los {int(g['dnf'].sum())} que abandonaron",
                          f"error medio: modelo {mae(g, 'mae_adj')} · grilla "
                          f"{mae(g, 'mae_grid_adj')} · ya usa el resultado, no es una predicción")}

    def descripcion_pistas(g) -> dict[str, str]:
        """El resultado de cada pista en palabras (para lectores de pantalla)."""
        nada = f"Gráfico animado de {g['race_label'].iloc[0]}: largada, predicción y resultado real. "
        return {"arriba": nada + f"Con todos los pilotos, el modelo se equivoca en promedio por "
                         f"{mae(g, 'mae_model')} puestos y la grilla por {mae(g, 'mae_grid')}. "
                         "Las notas que siguen explican qué mirar.",
                "abajo": nada + f"Sin los {int(g['dnf'].sum())} que abandonaron, el modelo se "
                         f"equivoca por {mae(g, 'mae_adj')} puestos y la grilla por "
                         f"{mae(g, 'mae_grid_adj')}. Las notas que siguen explican qué mirar."}

    for ronda in CARRERAS_GUIADAS:
        for panel in ("arriba", "abajo"):
            # una nota puede marcar varios lugares del mismo piloto (Antonelli: largada,
            # llegada y resultado)
            marcas = [{"n": n, "driver": sigla, "donde": d}
                      for n, sigla, donde, _, _, _ in notas_guiadas[ronda][panel]
                      for d in (donde if isinstance(donde, list) else [donde])]
            for compacto in (False, True):
                specs[f"carrera-{ronda}-{panel}" + ("-c" if compacto else "")] = (
                    race_cars.race_cars_guiada(
                        guiadas[ronda], abajo=panel == "abajo", marcas=marcas,
                        compacto=compacto, width=560 if compacto else 1000,
                        # filas más bajas y letras más grandes: el gráfico se ve achicado en el
                        # panel y así las filas quedan en unos 12 px o más en pantalla
                        row_height=26 if compacto else 30, letra=1.4 if compacto else 1.35,
                        model_name=nombre_modelo))
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
    # sigla, escudería y color de cada auto: los mismos que en «Carrera por carrera»
    autos_info = pd.concat(tablas.values()).assign(
        Carrera=lambda t: t["race"].str.replace("-", "-R")).set_index(["Carrera", "driver_id"])
    casos_carreras = {}
    for carrera, autos in df.groupby("Carrera", sort=False):   # en el orden del parquet
        valores = autos[entrada].to_numpy(dtype=float, na_value=np.nan)
        casos_carreras[carrera] = {
            "anio": int(autos["Year"].iloc[0]),
            "nombre": carreras.etiqueta(int(autos["Year"].iloc[0]), int(autos["RoundNumber"].iloc[0])),
            "pilotos": [{"id": piloto, "nombre": piloto.replace("_", " ").title(),
                         "puesto": int(puesto), "termino": str(termino) != "False",
                         **{k: str(autos_info.loc[(carrera, piloto), c]) for k, c in
                            [("sigla", "driver"), ("equipo", "team"), ("color", "color")]},
                         "v": [None if np.isnan(x) else float(x) for x in fila]}
                        for piloto, puesto, termino, fila in zip(
                            autos["DriverId"], autos["Puesto"], autos["Terminó"], valores)]}
    datos["casos"] = {"entrada": entrada, "carreras": casos_carreras}
    datos["pilotos"] = tabla_pilotos(tablas, df)
    # «Explorá los datos»: los datos crudos para recorrer (ver web/explora.py)
    explora_html, datos["explora"], config_explora = explora.armar(df)

    config = {
        "anioTest": ANIO_TEST, "anios": anios, "modelo": modelo,
        "pestanias": [clave for clave, _ in PESTANIAS],
        "controles": [{"col": col, "etiqueta": etiqueta, "paso": paso, "decimales": decimales,
                       "rango": rangos[col], "habitual": habituales[col],
                       "mediana": medianas.get(col)} for col, etiqueta, paso, decimales in CONTROLES],
        "medianas": medianas,
        "simMaxDetras": sim_max_behind,   # tope de la distancia al líder en la pista simulada
    }

    # ---- el cuerpo: la copa de martini, en orden ----------------------------------------------------
    cuerpo = [
        estilo.encabezado(equipos, "Ciencia de Datos · UTN FRM · 2026"),
        "<h1>¿Se puede anticipar en qué puesto termina cada piloto de F1 con lo que se sabe "
        "antes de la carrera?</h1>",
        '<p class="idea">El modelo ordena mejor que la grilla a los pilotos que terminan la carrera, '
        "pero los abandonos, que nadie anticipa, se comen esa ventaja.</p>",
        tarjetas_portada(test, ejemplos_portada(df), pct_error_abandonos, pct_filas_abandonos,
                         n_abandonos_test, n_pilotos_test,
                         valor_nb("Peso de los abandonos", "MAE de esas filas"),
                         mae_terminan_test),
        nota("Error = cuántos puestos hay entre donde lo puso la predicción y donde terminó. "
             f"Test: las {test['carreras']} carreras de {ANIO_TEST}, que el modelo no vio al entrenar."),
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
             "Resultados, clasificación y campeonato de cada Gran Premio, y cada vuelta de las "
             f"prácticas libres, de {int(df['Year'].min())} al {corte_gp} de {corte_anio}."),
            ("Los juntamos en una tabla",
             f"Una fila por piloto y carrera: {filas_crudas_txt} filas con {n_columnas} datos. Los "
             "tiempos, como distancia al mejor de esa carrera."),
            ("Revisamos las filas",
             f"Sacamos {rondas_dup} Grandes Premios con pilotos cargados dos veces. Quedan "
             f"{n_filas_txt} filas de {n_carreras} Grandes Premios."),
            ("Elegimos los datos",
             f"De los {n_columnas} quedan 8: los que se saben antes de largar y dicen algo nuevo."),
        ]),
        '<div class="dos-columnas">',
        p("**Un ejemplo: la mejor vuelta con cada goma.** Ese dato lo armamos nosotros. "
          f"{cv['piloto'].capitalize()} dio {cv['total']} vueltas en las prácticas del "
          f"{cv['gran_premio']} y solo {cv['quedan']} sirven para medir ritmo: el gráfico muestra "
          "por qué se descarta cada una. Con las que quedan guardamos, por goma, la mejor vuelta "
          f"({blandas['mejor_txt']} con blandas) y el promedio ({blandas['promedio_txt']}): la "
          f"diferencia es el desgaste ({fmt(blandas['desgaste'], 1)}\u00a0%)."),
        grafico("vueltas"),
        "</div>",
        '<div class="dos-columnas">',
        p("**Qué salió y por qué.** Cada barra gris es un grupo de datos que sacamos, con el "
          "motivo al lado. Tres reglas: **solo lo que se sabe antes de largar**; **que sirva para "
          "carreras futuras** (quién es el equipo no se sostiene: el puesto promedio de Red Bull "
          "pasa de 3,6 en 2023 a 9,1 en 2026), y **que diga algo nuevo** (la telemetría repetía "
          "lo que ya dice la grilla)."),
        grafico("columnas"),
        "</div>",
        '<div class="dos-columnas">', grafico("datos"),
        p("**Con qué trabajamos.** Cada casilla es el % de pilotos con ese dato en esa temporada. "
          "La largada y la clasificación están casi siempre; las prácticas tienen huecos "
          f"({hay_practica.mean():.0%} en total). **Ninguna fila se descarta por un faltante:** el "
          "modelo usa un valor típico y una marca de que faltaba (a la derecha). Lo que siempre "
          "está, la grilla, es lo que más pesa."),
        "</div>",
        como_lo_sabemos(
            p("**De dónde salen.** Del proceso automático de descarga que armamos en la Entrega 1 "
              f"(con Airflow; [ver el código]({PIPELINE})), a partir "
              "de las estadísticas estilo Ergast (resultados, clasificación y "
              "campeonato) y la telemetría de FastF1 (prácticas libres): "
              f"{filas_crudas_txt} filas, una por piloto en cada Gran Premio, "
              f"de {int(df['Year'].min())} a {int(df['Year'].max())}, con corte en el "
              f"{corte_gp} de {corte_anio} (datos del {FECHA_DATOS}). El respaldo es el archivo "
              f"{archivo_datos}, guardado en el repositorio; "
              "build_app.py lo lee de ahí."),
            p("**Detalles del proceso.** Arrancamos en "
              f"{int(df['Year'].min())} porque es el primer año con las vueltas de prácticas "
              "registradas (antes hay resultados pero no prácticas). De las prácticas nos quedamos "
              "con las vueltas que sirven para medir ritmo (sin boxes, banderas, vueltas anuladas "
              "ni de enfriamiento) y, por goma, con la mejor y el promedio. Los tiempos pasan a "
              "«cuánto más lento que el mejor de esa carrera», para comparar circuitos distintos. "
              f"Los pilotos cargados dos veces estaban en {fechas_dup}, sin forma de saber cuál "
              f"era la fila buena. En {gp_sin_practica} de los {n_carreras} Grandes Premios no hay "
              "ningún dato de prácticas; el valor típico de un faltante es la mediana de las "
              "temporadas con las que aprendió el modelo."),
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
          "entrenar. Leé los tres pasos en orden: la flecha marca qué mirar en cada "
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

        # ---- dos carreras del test, guiadas (la versión libre está en «Carrera por carrera») ----
        '<h3 class="subseccion" id="dos-carreras">Dos carreras, paso a paso</h3>',
        p("Para ver lo mismo en carreras concretas, elegimos dos fechas del test. El gráfico se "
          "queda quieto y **cada vez que bajás** aparece la tanda de notas siguiente: primero con "
          "todos los pilotos y después sin los que abandonaron. En cada tanda corren los autos y "
          "cada nota marca en rojo, con su número, lo que explica, a su misma altura. Si subís, "
          "vuelve atrás."),
        carrera_guiada(4, grupos_guiadas[4], ganador="grilla", orden="Carrera 1 de 2", filas=len(g4), salida="Saltar a la próxima carrera", destino_salida="carrera-guiada-13", titulo=f"{carreras.nombre(ANIO_TEST, 4)} {ANIO_TEST}", pistas=pistas_de(g4), leyenda=como_se_lee, descripciones=descripcion_pistas(g4), resumen=f"**En resumen.** Sin abandonos, la ventaja de la grilla baja de "
          f"{fmt(g4['mae_model'].iloc[0] - g4['mae_grid'].iloc[0])} a "
          f"{fmt(g4['mae_adj'].iloc[0] - g4['mae_grid_adj'].iloc[0])} puestos por piloto: casi "
          f"toda venía de los abandonos, sobre todo de {nom(g4, 'HAD')}. Lo que queda son "
          f"{nom(g4, 'LEC')} y {nom(g4, 'NOR')}: el modelo los movió por los puntos del "
          "campeonato y esta vez la carrera salió al revés."),
        carrera_guiada(13, grupos_guiadas[13], ganador="modelo", orden="Carrera 2 de 2", filas=len(g13), salida="Saltar esta carrera", destino_salida="despues-13", titulo=f"{carreras.nombre(ANIO_TEST, 13)} {ANIO_TEST}", pistas=pistas_de(g13), leyenda=como_se_lee, descripciones=descripcion_pistas(g13), resumen=f"**En resumen.** Con todos, el modelo gana por "
          f"{fmt(g13['mae_grid'].iloc[0] - g13['mae_model'].iloc[0])} puestos por piloto, y sin "
          f"abandonos por {fmt(g13['mae_grid_adj'].iloc[0] - g13['mae_adj'].iloc[0])}. "
          f"La diferencia la hacen los pilotos que largan fuera de su lugar, como "
          f"{nom(g13, 'ANT')} y {nom(g13, 'LAW')}: la grilla los deja donde largaron y el modelo, "
          "que mira más que la largada, los acerca a donde terminaron."),
        nota("¿Querés ver otra? En [Carrera por carrera](#una-temporada), más abajo, están todas "
             f"las carreras de {anios[-1]} a {anios[0]} con la misma animación."),
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
            nota("Test 2026. Sesgo = puesto predicho − puesto real, con la misma convención "
                 "que los gráficos: positivo, terminó más adelante de lo predicho (ganó "
                 "puestos); negativo, más atrás. El error más grande está en los que terminan "
                 "16.º o peor, donde caen los abandonos."),
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
        # ---- Cierre del relato: qué nos llevamos ---------------------------------------------------
        '<section class="cierre-relato" id="que-nos-llevamos"><h2>Qué nos llevamos</h2>'
        '<div class="cierre-columnas">',
        p(f"**Qué aprendimos.** Con lo que se sabe antes de largar, el modelo ordena mejor que la "
          f"grilla a los que terminan: se equivoca por {fmt(test['mae_modelo_sin_abandonos'])} "
          f"puestos y la grilla por {fmt(test['mae_grilla_sin_abandonos'])}. La largada sigue "
          "siendo lo que más pesa; el modelo suma el campeonato, la clasificación y las prácticas."),
        p(f"**Límites.** Los abandonos no se pueden anticipar con estos datos (el clasificador que "
          f"probamos tuvo un AUC de {auc_abandonos}; 0,5 es adivinar) y se comen la ventaja: con "
          f"todos los pilotos, {fmt(test['mae_modelo'])} contra {fmt(test['mae_grilla'])}. Además, "
          f"el test son {test['carreras']} carreras de {ANIO_TEST}: con más, la diferencia podría "
          "moverse."),
        p("**Qué probaríamos después.** Datos que se conocen antes de largar y no usamos, como el "
          "clima o las sanciones en la grilla, y predecir el abandono por separado para combinarlo "
          "con el orden, en lugar de tratarlo como error."),
        "</div></section>",
        "<hr>",

        # ---- Copa ----------------------------------------------------------------------------------
        estilo.parte("explorar", "Explorá por tu cuenta",
              "Recorré los datos como quieras, mirá cualquier temporada y carrera, o cambiá lo que "
              "hizo un piloto antes de largar y fijate qué predice el modelo"),
        '<h3>Explorá los datos</h3>',
        explora_html,
        '<h3 id="todos-los-pilotos">Todos los pilotos, en todas las carreras</h3>',
        p(f"Las {n_filas_txt} filas de la página: cada piloto en cada Gran Premio de 2018 a "
          f"{ANIO_TEST}, con su largada, lo que predijo el modelo y dónde terminó. Filtrá por lo "
          "que quieras; el resumen y el gráfico cuentan solo lo que queda. Cada carrera "
          "la predice un modelo que no la vio."),
        EXPLORADOR,

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
        '<div class="controles-autos"><button class="correr" type="button">Correr</button>'
        '<button class="largada" type="button">Volver a la largada</button>'
        '<span id="selector-autos"></span></div>'
        '<div class="marco"><div class="vista"></div></div></div></div>',
        '<div class="panel" data-panel="porque" hidden><div class="grafico"><div class="vista"></div></div></div>',

        '<h3 id="proba-el-modelo">Probá el modelo</h3>',
        p("Elegí una carrera y un piloto y cambiá lo que hizo antes de largar: el modelo le "
          "vuelve a dar un puntaje y lo ordena contra los demás de esa carrera. Los controles "
          "van del mínimo al máximo que vio el modelo al entrenar, así que no se puede cargar "
          "un valor que nunca vio; si uno queda en el 1 % más raro de cada punta, la app avisa."),
        # un solo panel: a la izquierda lo que se sabe antes de largar, a la derecha la carrera
        '<div id="proba" class="simulador">'
        '<div class="sim-datos">'
        '<h4 class="sim-titulo"><span>1</span> Antes de largar</h4>'
        '<div class="fila-controles"><label class="campo">Carrera <select id="proba-carrera"></select></label>'
        '<label class="campo">Piloto <select id="proba-piloto"></select></label></div>'
        '<div class="controles-modelo" id="proba-controles"></div>'
        '<div class="aviso" id="proba-avisos" role="status" hidden></div></div>'
        '<div class="sim-carrera">'
        '<h4 class="sim-titulo"><span>2</span> Lo que predice el modelo</h4>'
        '<div class="metricas" id="proba-resultado" aria-live="polite"></div>'
        '<p class="nota" id="proba-real"></p><p class="nota" id="proba-nota" hidden></p>'
        '<div class="grafico autos" id="proba-pista"><div class="controles-autos">'
        '<button class="correr" type="button">Correr animación</button>'
        '<span class="pista">En rojo, el piloto elegido; en contorno, dónde lo ponía el modelo '
        'con sus datos reales.</span></div>'
        '<div class="marco"><div class="vista"></div></div></div></div></div>',

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
{leer_web("explora.css")}
</style>
</head>
<body>
<button class="mostrar-indice" type="button" aria-controls="indice" aria-expanded="true">
  <span class="flecha" aria-hidden="true">‹</span><span class="texto">Ocultar índice</span></button>
<aside class="lateral" id="indice">{estilo.menu([t.format(n=n_columnas) for t in RECORRIDO], EXPLORAR, {3: [("Dos carreras, paso a paso", "dos-carreras"), ("Qué nos llevamos", "que-nos-llevamos")]})}</aside>
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
<script type="application/json" id="config-explora">{en_script(json.dumps(config_explora, ensure_ascii=False))}</script>
<script>
{en_script(leer_web("explora.js"))}
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
