"""Sector 3 · El modelo, contado en tres pasos: tres gráficos fijos, uno por fila, en zigzag.

Cada paso es su propio gráfico, con un título que dice qué mirar y una flecha que apunta
exactamente ahí. El lector no tiene que descubrir ningún botón: lee de arriba abajo. La
explicación larga de cada paso va al lado de su gráfico (web/pagina.py, con los números de `cifras`).

    Datos:           una fila por piloto y predicción (grilla o modelo) con su error en puestos.
    Transformación:  error = puesto predicho − puesto real, redondeado y recortado a ±15; después
                     cantidad de pilotos por error, predicción y estado (terminó / abandonó).
    Marca:           barras (mark_bar), agrupadas por predicción con `xOffset`; la flecha es una
                     regla con un triángulo en la punta, y el texto, una capa más.
    Mapeo:           error -> x (ordinal), cantidad -> y, predicción -> xOffset y color.
                     En el paso 3 el color pasa a ser "abandonó" para los que no terminaron.
    Escalas:         los tres pasos comparten los ejes (se comparan de un vistazo) y los colores
                     de graficos/colores.py: azul = modelo, ámbar = grilla, gris = abandono.

Pasos:
    1 · La grilla       solo la grilla: la mayoría termina cerca de donde largó.
    2 · El modelo       aparece el modelo: menos errores grandes, aunque no más aciertos exactos.
    3 · Los abandonos   los que no terminaron son la cola de la izquierda.
"""

from __future__ import annotations

import textwrap

import altair as alt
import numpy as np
import pandas as pd

from graficos import colores as C

TOPE = 15          # errores más grandes se acumulan en ±15
GRANDE = 8         # «error grande» en el relato del paso 2: 8 puestos o más


def _mae(err: pd.Series) -> float:
    return float(err.abs().mean())


def errores(pred: pd.DataFrame) -> pd.DataFrame:
    """Una fila por piloto y predicción, con el error en puestos (como `medir` del notebook)."""
    d = pred[["Year", "Carrera", "DriverId", "Puesto", "puesto_modelo", "Q_GridPosition",
              "Terminó"]].copy()
    car = d["Carrera"]
    real = d["Puesto"].groupby(car).rank(method="average")
    grilla = d["Q_GridPosition"].fillna(21).groupby(car).rank(method="average")
    d["termino"] = d["Terminó"].fillna(True).astype(bool)
    largo = pd.concat([
        d.assign(quien="Grilla", error=(grilla - real).to_numpy()),
        d.assign(quien="Modelo", error=(d["puesto_modelo"] - real).to_numpy()),
    ], ignore_index=True)
    largo["error_bin"] = np.clip(np.round(largo["error"]), -TOPE, TOPE).astype(int)
    largo["estado"] = np.where(largo["termino"], "Terminó", "Abandonó")
    return largo


def resumen_por_temporada(largo: pd.DataFrame) -> pd.DataFrame:
    """MAE con y sin abandonos, por temporada y predicción, para los textos del gráfico."""
    filas = []
    for anio, g in largo.groupby("Year"):
        fila = {"Year": int(anio)}
        for quien in ["Grilla", "Modelo"]:
            q = g[g["quien"] == quien]
            fila[f"mae_{quien}"] = _mae(q["error"])
            fila[f"pct_aband_{quien}"] = q.loc[~q["termino"], "error"].abs().sum() / q["error"].abs().sum()
        fila["abandonos"] = int((~g[g["quien"] == "Modelo"]["termino"]).sum())
        fila["pilotos"] = int((g["quien"] == "Modelo").sum())
        filas.append(fila)
    return pd.DataFrame(filas)


# ---- piezas comunes ----------------------------------------------------------------------------
def _conteo(largo: pd.DataFrame) -> pd.DataFrame:
    return (largo.groupby(["Year", "quien", "estado", "error_bin"]).size()
            .rename("pilotos").reset_index())


def _eje_x() -> alt.X:
    # la misma convención en toda la página: + / derecha = más adelante (ganó puestos)
    return alt.X("error_bin:O", title="← terminó más atrás  ·  puestos de error  ·  terminó más adelante →",
                 scale=alt.Scale(domain=list(range(-TOPE, TOPE + 1))),
                 axis=alt.Axis(labelAngle=0, values=list(range(-TOPE, TOPE + 1, 5)), labelFontSize=13,
                               titleFontSize=13, titlePadding=10, ticks=False, **C.EJES))


def _eje_y(campo: str, y_max: float, apilar: bool = False) -> alt.Y:
    return alt.Y(campo, title="Pilotos", scale=alt.Scale(domain=[0, y_max]),
                 axis=alt.Axis(labelFontSize=13, titleFontSize=13, tickCount=5, domain=False, ticks=False,
                               **C.EJES),
                 stack="zero" if apilar else None)


def _color(grupos: list[str]) -> alt.Color:
    rango = {"Grilla": C.GRILLA, "Modelo": C.MODELO, "Abandonó": C.ABANDONO}
    return alt.Color("grupo:N", title=None, scale=alt.Scale(domain=grupos, range=[rango[g] for g in grupos]),
                     legend=alt.Legend(orient="top", direction="horizontal", labelColor=C.INK, symbolType="square",
                                       symbolSize=180, labelFontSize=14, columnPadding=18, offset=14))


def _barras(datos: pd.DataFrame, quienes: list[str], grupos: list[str], y_max: float) -> alt.Chart:
    return alt.Chart(datos).mark_bar(width=alt.RelativeBandSize(0.86), cornerRadiusEnd=2).encode(
        x=_eje_x(), xOffset=alt.XOffset("quien:N", scale=alt.Scale(domain=quienes)),
        y=_eje_y("sum(pilotos):Q", y_max, apilar=True), color=_color(grupos), order=alt.Order("orden:Q"),
        tooltip=[alt.Tooltip("quien:N", title="Predicción"),
                 alt.Tooltip("error_bin:O", title="Error (puestos)"),
                 alt.Tooltip("grupo:N", title="Grupo"),
                 alt.Tooltip("sum(pilotos):Q", title="Pilotos")])


def _cero(y_max: float, hasta: float = 0.7) -> alt.Chart:
    """Línea punteada en el 0 (acierto exacto). Llega a `hasta` del alto: arriba van los textos."""
    d = pd.DataFrame({"error_bin": [0], "y": [0.0], "y2": [y_max * hasta], "texto": ["acierto"]})
    regla = alt.Chart(d).mark_rule(color=C.INK, strokeDash=[3, 3], opacity=0.6).encode(
        x=_eje_x(), y=_eje_y("y:Q", y_max), y2="y2:Q")
    rotulo = alt.Chart(d).mark_text(baseline="bottom", dy=-4, fontSize=12, color=C.INK_MUTED,
                                    fontStyle="italic").encode(x=_eje_x(), y=_eje_y("y2:Q", y_max),
                                                               text="texto:N")
    return alt.layer(regla, rotulo)


def _zona(tramos: list[tuple[int, int]], y_max: float) -> alt.Chart:
    """Franja sombreada detrás de las barras: la parte del gráfico de la que habla el texto.
    Un rectángulo por tramo (de la columna `error_bin` a la `fin`, ambas incluidas), sin cortes."""
    d = pd.DataFrame([{"error_bin": a, "fin": b, "y": 0.0, "alto": y_max} for a, b in tramos])
    x = _eje_x()           # el mismo eje que las barras, así no se dibuja otro encima
    x.bandPosition = 0
    return alt.Chart(d).mark_rect(color=C.INK, opacity=0.06, cornerRadius=4).encode(
        x=x,
        x2=alt.X2("fin:O", bandPosition=1), y=_eje_y("y:Q", y_max), y2="alto:Q")


LINEA_PX = 20      # alto de una línea del texto de las flechas, en píxeles


def _flecha(bin_: int, punta: float, arriba: float, texto: str, y_max: float, height: int,
            align: str = "center", dx: int = 0) -> alt.LayerChart:
    """Texto con su borde de arriba en `arriba` (en pilotos) y, debajo, una flecha vertical que
    baja hasta `punta` sobre la columna `bin_`. Con align «left» o «right» el texto arranca o
    termina en esa columna (corrido `dx` píxeles), así la flecha queda debajo de su comienzo."""
    por_px = y_max / height
    lineas = texto.count("\n") + 1
    base = arriba - (lineas * LINEA_PX + 6) * por_px     # debajo de la última línea
    hueco = 7 * por_px                                    # aire entre la punta y la barra
    d = pd.DataFrame({"error_bin": [bin_], "base": [base], "punta": [punta + hueco + 5 * por_px],
                      "tri": [punta + hueco], "arriba": [arriba], "texto": [texto]})
    base_chart = alt.Chart(d)
    linea = base_chart.mark_rule(color=C.INK, strokeWidth=1.6).encode(
        x=_eje_x(), y=_eje_y("base:Q", y_max), y2="punta:Q")
    triangulo = base_chart.mark_point(shape="triangle-down", size=110, filled=True, opacity=1,
                                      color=C.INK).encode(x=_eje_x(), y=_eje_y("tri:Q", y_max))
    rotulo = base_chart.mark_text(
        align=align, baseline="top", dx=dx, lineBreak="\n", fontSize=15, lineHeight=LINEA_PX,
        fontWeight=600, color=C.INK).encode(x=_eje_x(), y=_eje_y("arriba:Q", y_max), text="texto:N")
    return alt.layer(linea, triangulo, rotulo)


def _letras(width: int) -> int:
    """Letras por línea del subtítulo (15 px, ~6,8 px por letra) para que ocupe el ancho del
    gráfico más el eje de la izquierda (~55 px)."""
    return int((width + 55) / 6.8)


def _cerrar(grafico: alt.LayerChart, titulo: str, subtitulo: list[str], width: int, height: int):
    return grafico.properties(
        width=width, height=height,
        title=alt.Title(titulo, subtitle=subtitulo, anchor="start", fontSize=22, fontWeight=700,
                        color=C.INK, subtitleColor=C.INK_MUTED, subtitleFontSize=15,
                        subtitleLineHeight=21, subtitlePadding=8, offset=6),
    ).configure(
        background=C.FONDO, padding={"left": 8, "right": 20, "top": 8, "bottom": 8}
    ).configure_view(stroke=None, fill=C.FONDO).configure_text(font=C.FUENTE).configure_title(font=C.FUENTE)


# ---- los números de los textos ------------------------------------------------------------------
def _cifras(del_test: pd.DataFrame) -> dict:
    # Salen de las mismas filas que dibujan las barras (todos los pilotos del test): si cambian
    # los datos, el texto no puede decir lo contrario del gráfico.
    err = {q: del_test.loc[del_test["quien"] == q, "error"].abs() for q in ["Grilla", "Modelo"]}
    fila = resumen_por_temporada(del_test).iloc[0]
    return {
        "exactos": {q: int((e.round() == 0).sum()) for q, e in err.items()},
        "grandes": {q: int((e >= GRANDE).sum()) for q, e in err.items()},
        "cerca": float((err["Grilla"] <= 2).mean()),
        "abandonos": int(fila["abandonos"]), "pilotos": int(fila["pilotos"]),
        "pct_error_abandonos": {q: float(fila[f"pct_aband_{q}"]) for q in ["Grilla", "Modelo"]},
        # error medio del modelo con los que abandonaron y con los que terminaron (sin reordenar)
        "mae_modelo_por_estado": {e: _mae(g["error"]) for e, g in
                                  del_test[del_test["quien"] == "Modelo"].groupby("estado")},
    }


def cifras(pred: pd.DataFrame, anio_test: int = 2026) -> dict:
    """Los números que citan los textos de los pasos (los del gráfico y los de debajo)."""
    largo = errores(pred)
    return _cifras(largo[largo["Year"] == anio_test]) | {"grande": GRANDE}


# ---- los tres pasos ----------------------------------------------------------------------------
def graficos_pasos(pred: pd.DataFrame, test: dict, anio_test: int = 2026,
                   width: int = 640, height: int = 320) -> list[alt.LayerChart]:
    """Los pasos 1, 2 y 3, cada uno su gráfico. `test` es resumen["test"] de build_app."""
    largo = errores(pred)
    del_test = largo[largo["Year"] == anio_test]
    conteo = _conteo(del_test)
    alto_col = conteo.groupby(["quien", "error_bin"])["pilotos"].sum()   # alto de cada barra
    y_max = float(alto_col.max()) * 1.6        # arriba queda lugar para el texto y la flecha
    f = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    t = test

    c = _cifras(del_test)
    exactos, grandes, cerca = c["exactos"], c["grandes"], c["cerca"]
    mas_menos = lambda a, b: "más" if a > b else "menos" if a < b else "los mismos"  # noqa: E731
    exactos_txt, grandes_txt = (mas_menos(exactos["Modelo"], exactos["Grilla"]),
                                mas_menos(grandes["Modelo"], grandes["Grilla"]))
    nexo = "pero" if (exactos_txt == "más") != (grandes_txt == "menos") else "y"
    pct = lambda x: f"{x:.0%}".replace("%", " %")  # noqa: E731

    def alto(quien: str, b: int) -> float:
        return float(alto_col.get((quien, b), 0))

    # ---- 1 · La grilla: la montaña alrededor del 0 ----
    d1 = conteo[conteo["quien"] == "Grilla"].assign(grupo="Grilla", orden=0)
    pico = int(alto_col.loc["Grilla"].idxmax())
    paso1 = alt.layer(
        _zona([(-2, 2)], y_max), _barras(d1, ["Grilla"], ["Grilla"], y_max), _cero(y_max),
        _flecha(pico, alto("Grilla", pico), y_max * 0.97,
                f"El {pct(cerca)} termina a 2 puestos\no menos de donde largó", y_max, height))
    sub1 = (f"Predecir que cada uno termina donde largó erra {f(t['mae_grilla'])} puestos en "
            "promedio. La mayoría queda cerca del 0: ya es una buena predicción.")

    # ---- 2 · El modelo: menos errores grandes ----
    d2 = conteo.assign(grupo=conteo["quien"], orden=0)
    # la flecha va a la columna de errores grandes (a la derecha) donde más se nota la diferencia
    derecha = range(GRANDE, TOPE + 1)
    blanco = max(derecha, key=lambda b: (alto("Grilla", b) - alto("Modelo", b), -b))
    zona2 = [(-TOPE, -GRANDE), (GRANDE, TOPE)]
    paso2 = alt.layer(
        _zona(zona2, y_max), _barras(d2, ["Grilla", "Modelo"], ["Grilla", "Modelo"], y_max), _cero(y_max),
        _flecha(blanco, max(alto("Grilla", blanco), alto("Modelo", blanco)), y_max * 0.97,
                f"Errores de {GRANDE} puestos o más\n(sombreado): modelo {grandes['Modelo']}, "
                f"grilla {grandes['Grilla']}", y_max, height, align="right", dx=8))
    sub2 = (f"Suma clasificación, campeonato y prácticas: erra {f(t['mae_modelo'])}; la grilla, "
            f"{f(t['mae_grilla'])}. Acierta {exactos_txt} exactos ({exactos['Modelo']} contra "
            f"{exactos['Grilla']}), {nexo} se equivoca por mucho {grandes_txt}. Aun así, el promedio "
            "casi no baja. ¿Por qué? →")

    # ---- 3 · Los abandonos: la cola de la izquierda ----
    d3 = conteo.assign(grupo=np.where(conteo["estado"] == "Abandonó", "Abandonó", conteo["quien"]),
                       orden=np.where(conteo["estado"] == "Abandonó", 1, 0))
    cola = -TOPE
    paso3 = alt.layer(
        _barras(d3, ["Grilla", "Modelo"], ["Grilla", "Modelo", "Abandonó"], y_max), _cero(y_max),
        _flecha(cola, max(alto("Grilla", cola), alto("Modelo", cola)), y_max * 0.97,
                "Los que no terminaron:\nlos ponían adelante\ny quedaron atrás",
                y_max, height, align="left", dx=4))
    sub3 = ("En gris, los que no terminaron la carrera: son la cola de la izquierda, para los dos. "
            f"Sin ellos, el modelo erra {f(t['mae_modelo_sin_abandonos'])} y la grilla "
            f"{f(t['mae_grilla_sin_abandonos'])}: los abandonos tapaban la ventaja.")

    # Vega no corta el subtítulo solo: se corta acá al ancho de la tarjeta, y los tres quedan con
    # la misma cantidad de líneas para que los gráficos arranquen a la misma altura.
    cortados = [textwrap.wrap(sub, width=_letras(width)) for sub in (sub1, sub2, sub3)]
    n = max(len(c) for c in cortados)
    return [_cerrar(paso, titulo, c + [" "] * (n - len(c)), width, height)
            for paso, titulo, c in zip([paso1, paso2, paso3],
                                       ["1 · La grilla", "2 · El modelo", "3 · Los abandonos"], cortados)]
