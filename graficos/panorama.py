"""Explorá · panorama: todas las carreras, con vistas vinculadas (sección 6.5 de la práctica).

Arriba a la izquierda, un punto por Gran Premio: cuánto erró la grilla (x) contra cuánto erró el
modelo (y). Debajo de la diagonal, el modelo acertó mejor. Arrastrando sobre la nube se marca un
rectángulo (un *brush*): las barras de la derecha y el ranking de abajo pasan a contar solo las
carreras que quedaron adentro.

    Datos:           una fila por piloto en un GP, con el error de la grilla y del modelo y, unido, el
                     error medio de su carrera (para poder filtrar por el brush en los tres paneles).
    Transformación:  agregaciones dentro del gráfico: mean() por carrera, por escudería y por
                     predicción (`transform_aggregate`, `transform_fold`).
    Marcas:          círculos (carreras), barras (escuderías) y barras (temporadas).
    Parámetros:      `brush` (selection_interval) filtra los otros paneles; `temporada` (menú)
                     filtra los tres; `quien_gano` (clic en la leyenda) resalta.
    Escalas:         los colores de graficos/colores.py; los ejes de error arrancan en 0 (barras).
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from graficos import colores as C


def tabla(pred: pd.DataFrame) -> pd.DataFrame:
    """Una fila por piloto en un GP, con sus errores y los de su carrera."""
    d = pred[["Year", "RoundNumber", "Carrera", "DriverId", "TeamId", "Puesto", "puesto_modelo",
              "Q_GridPosition", "Terminó"]].copy()
    car = d["Carrera"]
    real = d["Puesto"].groupby(car).rank(method="average")
    grilla = d["Q_GridPosition"].fillna(21).groupby(car).rank(method="average")
    d["err_modelo"] = (d["puesto_modelo"] - real).abs()
    d["err_grilla"] = (grilla - real).abs()
    d["abandono"] = (d["Terminó"] == False).astype(int)  # noqa: E712
    gp = d.groupby("Carrera").agg(gp_modelo=("err_modelo", "mean"), gp_grilla=("err_grilla", "mean"),
                                  gp_abandonos=("abandono", "sum"))
    gp["gp_quien"] = (gp["gp_modelo"] < gp["gp_grilla"]).map({True: "Mejor el modelo", False: "Mejor la grilla"})
    d = d.join(gp, on="Carrera")
    d["Escudería"] = d["TeamId"].str.replace("_", " ").str.title()
    d["Ganador"] = d.groupby("Carrera")["DriverId"].transform(
        lambda s: s.loc[d.loc[s.index, "Puesto"].idxmin()]).str.replace("_", " ").str.title()
    return d[["Year", "RoundNumber", "Carrera", "Escudería", "Ganador", "err_modelo", "err_grilla",
              "abandono", "gp_modelo", "gp_grilla", "gp_abandonos", "gp_quien"]]


def panorama(pred: pd.DataFrame, width: int = 430) -> alt.VConcatChart:
    d = tabla(pred)
    anios = sorted(int(a) for a in d["Year"].unique())

    temporada = alt.param(name="temporada", value="Todas", bind=alt.binding_select(
        options=["Todas"] + anios, name="Temporada "))
    brush = alt.selection_interval(name="brush", encodings=["x", "y"])
    quien = alt.selection_point(name="quien_gano", fields=["gp_quien"], bind="legend")
    por_temporada = "temporada == 'Todas' || datum.Year == temporada"
    eje = dict(**C.EJES)
    lim = float(max(d["gp_modelo"].max(), d["gp_grilla"].max())) + 0.3
    escala = alt.Scale(domain=[0, lim], nice=False)
    color_quien = alt.Color("gp_quien:N", title=None, scale=alt.Scale(
        domain=["Mejor el modelo", "Mejor la grilla"], range=[C.MODELO, C.GRILLA]),
        legend=alt.Legend(orient="top", labelColor=C.INK, title="Clic para resaltar",
                          titleColor=C.INK_MUTED, titleFontWeight="normal"))

    # 1 · panorama: un punto por carrera (se agrega desde las filas de pilotos)
    base = alt.Chart(d).transform_filter(por_temporada)
    carreras = base.transform_aggregate(
        gp_modelo="mean(gp_modelo)", gp_grilla="mean(gp_grilla)", gp_abandonos="mean(gp_abandonos)",
        groupby=["Carrera", "Year", "gp_quien", "Ganador"]
    ).mark_circle(size=70, stroke=C.ASPHALT, strokeWidth=0.8).encode(
        x=alt.X("gp_grilla:Q", title="Error de la grilla en el GP (puestos)", scale=escala, axis=alt.Axis(**eje)),
        y=alt.Y("gp_modelo:Q", title="Error del modelo en el GP (puestos)", scale=escala, axis=alt.Axis(**eje)),
        color=alt.condition(brush, color_quien, alt.value(C.LANE)),
        opacity=alt.condition(quien, alt.value(0.9), alt.value(0.12)),
        tooltip=[alt.Tooltip("Carrera:N"), alt.Tooltip("Ganador:N"),
                 alt.Tooltip("gp_grilla:Q", title="Error grilla", format=".2f"),
                 alt.Tooltip("gp_modelo:Q", title="Error modelo", format=".2f"),
                 alt.Tooltip("gp_abandonos:Q", title="Abandonos", format=".0f")],
    ).add_params(brush, quien)
    diagonal = alt.Chart(pd.DataFrame({"a": [0, lim]})).mark_line(
        color=C.INK_MUTED, strokeDash=[5, 5]).encode(x="a:Q", y="a:Q")
    rotulo = alt.Chart(pd.DataFrame({"x": [lim * 0.97], "y": [lim * 0.06], "t": ["debajo: mejor el modelo"]})
                       ).mark_text(align="right", color=C.INK_MUTED, fontSize=11).encode(
        x="x:Q", y="y:Q", text="t:N")
    nube = (diagonal + carreras + rotulo).properties(
        width=width, height=width, title=alt.Title("Cada punto es un Gran Premio",
                                                   subtitle="Arrastrá para elegir carreras; doble clic para soltar.",
                                                   color=C.INK, subtitleColor=C.INK_MUTED, anchor="start"))

    # 2 · error medio por escudería, en las carreras elegidas
    filtrado = base.transform_filter(brush)
    equipos = filtrado.transform_fold(
        ["err_grilla", "err_modelo"], as_=["serie", "error"]
    ).transform_calculate(
        Predicción="datum.serie == 'err_modelo' ? 'Modelo' : 'Grilla'"
    ).mark_bar(height={"band": 0.8}).encode(
        y=alt.Y("Escudería:N", sort=alt.EncodingSortField("error", op="mean", order="descending"),
                title=None, axis=alt.Axis(labelColor=C.INK, **{k: v for k, v in eje.items() if k != "labelColor"})),
        yOffset=alt.YOffset("Predicción:N", sort=["Grilla", "Modelo"]),
        x=alt.X("mean(error):Q", title="Error medio por piloto (puestos)", axis=alt.Axis(**eje)),
        color=alt.Color("Predicción:N", scale=alt.Scale(domain=["Grilla", "Modelo"], range=[C.GRILLA, C.MODELO]),
                        legend=alt.Legend(orient="top", title=None, labelColor=C.INK)),
        tooltip=["Escudería:N", "Predicción:N", alt.Tooltip("mean(error):Q", title="Error medio", format=".2f"),
                 alt.Tooltip("count():Q", title="Pilotos-carrera")],
    ).properties(width=width - 60, height=width, title=alt.Title(
        "¿A qué escuderías lee mejor?", subtitle="Solo las carreras elegidas a la izquierda.",
        color=C.INK, subtitleColor=C.INK_MUTED, anchor="start"))

    # 3 · resumen de lo elegido: carreras, error medio de cada uno y abandonos
    resumen = filtrado.transform_aggregate(
        modelo="mean(err_modelo)", grilla="mean(err_grilla)", abandonos="sum(abandono)",
        pilotos="count()", carreras="distinct(Carrera)"
    ).transform_calculate(
        texto="datum.carreras + ' carreras elegidas · error del modelo ' + replace(format(datum.modelo, '.2f'), '.', ',')"
              " + ' · de la grilla ' + replace(format(datum.grilla, '.2f'), '.', ',') + ' · ' + datum.abandonos"
              " + ' abandonos de ' + datum.pilotos + ' pilotos'"
    ).mark_text(align="left", fontSize=14, color=C.INK).encode(x=alt.value(0), y=alt.value(10), text="texto:N"
    ).properties(width=2 * width, height=20)

    return alt.vconcat(alt.hconcat(nube, equipos, spacing=50).resolve_scale(color="independent"), resumen, spacing=18).add_params(
        temporada).configure(background=C.ASPHALT, padding=16).configure_view(
        stroke=None, fill=C.ASPHALT).configure_text(font="sans-serif").configure_title(fontSize=15)
