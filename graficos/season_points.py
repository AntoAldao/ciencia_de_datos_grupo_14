"""Campeonato acumulado según la grilla, el modelo y la realidad (Altair, gráfico de líneas).

Para cada carrera se reparten puntos (25-18-15-12-10-8-6-4-2-1, solo carrera principal: el
dataset no trae sprints ni vuelta rápida) con cinco órdenes de llegada distintos:

- **Realidad**: posición final real.
- **Modelo** / **Modelo ajustado**: orden predicho; el ajustado manda al fondo a los que no
  terminaron (en el orden en que abandonaron), como en `race_cars`.
- **Grilla** / **Grilla ajustada**: el orden de largada como predicción, con el mismo ajuste.

Todas las posiciones son 1..N dentro de la carrera (igual que el target del modelo).

Uso:

    from graficos import race_cars, season_points
    table = race_cars.race_table(predicciones_de_una_temporada)
    points = season_points.season_points(table)
    season_points.season_chart(points)           # todos los pilotos
    season_points.driver_chart(points, "ANT")    # un piloto en los cinco escenarios
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from graficos import colores as C

from graficos.race_cars import ASPHALT, INK, INK_MUTED, LANE

POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]

# Escenario -> columna de posición en `race_cars.race_table`.
SCENARIOS = {
    "Realidad": "final",
    "Modelo": "pred_pos",
    "Modelo ajustado": "pred_adj",
    "Grilla": "grid",
    "Grilla ajustada": "grid_adj",
}
# El color dice de dónde sale el orden (realidad / modelo / grilla) y el punteado, que está
# ajustado por abandonos. Azul y ámbar: slots 1 y 2 de la paleta de referencia (dataviz).
SCENARIO_COLORS = {"Realidad": C.REAL, "Modelo": C.MODELO, "Modelo ajustado": C.MODELO,
                   "Grilla": C.GRILLA, "Grilla ajustada": C.GRILLA}
# Selecciones del gráfico de la temporada que eligen piloto con un clic (para `on_select`).
CLICK_PARAMS = ["clic_linea", "clic_nombre"]

# Qué significa cada escenario, en palabras (las fichas de la app).
SCENARIO_DESC = {
    "Realidad": "Cómo terminaron de verdad las carreras",
    "Modelo": "Llegan en el orden que predijo el modelo",
    "Modelo ajustado": "Lo que predijo el modelo, pero los que abandonaron van al fondo y no "
                       "suman: así el modelo no pierde por un abandono que no podía prever",
    "Grilla": "Llegan en el mismo orden en que largaron",
    "Grilla ajustada": "El orden de largada, pero los que abandonaron van al fondo y no suman",
}
SCENARIO_DASH = {"Realidad": [1, 0], "Modelo": [1, 0], "Modelo ajustado": [6, 4],
                 "Grilla": [1, 0], "Grilla ajustada": [6, 4]}


def points_for(position: pd.Series) -> pd.Series:
    """Puntos de carrera por posición (1..10 suman; el resto, 0)."""
    return position.map(lambda p: POINTS[int(p) - 1] if 1 <= p <= len(POINTS) else 0)


def _spread(values: pd.Series, min_gap: float, floor: float = 0.0) -> pd.Series:
    """Alturas de etiqueta separadas al menos `min_gap`, lo más cerca posible de su valor y sin
    bajar de `floor`: primero cada una baja lo justo para no pisar a la de arriba; después,
    desde abajo, las que quedaron bajo el piso suben."""
    order = values.sort_values(ascending=False)
    ys = []
    for v in order:
        ys.append(v if not ys else min(v, ys[-1] - min_gap))
    for i in range(len(ys) - 1, -1, -1):
        low = floor if i == len(ys) - 1 else ys[i + 1] + min_gap
        ys[i] = max(ys[i], low)
    return pd.Series(ys, index=order.index).reindex(values.index)


def season_points(table: pd.DataFrame) -> pd.DataFrame:
    """Una fila por piloto, carrera y escenario con la posición, los puntos de esa carrera y el
    acumulado del campeonato. `table` es la salida de `race_cars.race_table`."""
    base = table.assign(round=table["race"].str.split("-").str[1].astype(int),
                        year=table["race"].str.split("-").str[0].astype(int))
    # color y equipo del piloto: los de su última carrera (hay pilotos que cambian de equipo)
    last = base.sort_values("race").groupby("driver").tail(1).set_index("driver")
    frames = []
    for name, col in SCENARIOS.items():
        f = base[["race", "race_label", "year", "round", "driver", "driver_id", col]].rename(
            columns={col: "pos"})
        f["scenario"] = name
        f["pts"] = points_for(f["pos"])
        frames.append(f)
    out = pd.concat(frames, ignore_index=True).sort_values(["scenario", "driver", "race"])
    out["cum_pts"] = out.groupby(["scenario", "year", "driver"])["pts"].cumsum()
    out["color"] = out["driver"].map(last["color"])
    out["team"] = out["driver"].map(last["team"])

    # Alturas de las etiquetas del final de cada línea, sin que se pisen: entre pilotos de un
    # mismo escenario (gráfico de arriba) y entre escenarios de un mismo piloto (abajo).
    out = out.reset_index(drop=True)
    end = out.sort_values("race").groupby(["scenario", "driver"]).tail(1)
    out["label_y_all"] = end["cum_pts"]  # quien no corrió la última fecha: en su última carrera
    at_end = end[end["round"] == out["round"].max()]
    out.loc[at_end.index, "label_y_all"] = pd.concat([
        _spread(g["cum_pts"], 0.028 * max(out["cum_pts"].max(), 1))
        for _, g in at_end.groupby("scenario")])
    out["label_y_one"] = pd.concat([
        _spread(g["cum_pts"], 0.05 * max(g["cum_pts"].max(), 1))
        for _, g in end.groupby("driver")])
    return out


def standings(points: pd.DataFrame) -> pd.DataFrame:
    """Tabla final del campeonato en cada escenario: una fila por escenario y piloto con sus
    puntos al terminar la temporada y el puesto (`rank`, 1 = campeón; empates, por orden)."""
    end = points.sort_values("race").groupby(["scenario", "driver"]).tail(1)
    end = end[["scenario", "driver", "driver_id", "team", "color", "cum_pts"]].sort_values(
        ["scenario", "cum_pts", "driver"], ascending=[True, False, True])
    end["rank"] = end.groupby("scenario").cumcount() + 1
    return end.reset_index(drop=True)


def _axes(points: pd.DataFrame) -> tuple[alt.X, alt.Y, list[alt.Tooltip]]:
    axis = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LANE, domainColor=LANE,
                tickColor=LANE)
    x = alt.X("round:Q", title="Fecha", scale=alt.Scale(domain=[1, int(points["round"].max())],
                                                       nice=False),
              axis=alt.Axis(tickMinStep=1, format="d", **axis))
    y = alt.Y("cum_pts:Q", title="Puntos acumulados", axis=alt.Axis(**axis))
    tooltip = [alt.Tooltip("driver_id:N", title="Piloto"), alt.Tooltip("team:N", title="Equipo"),
               alt.Tooltip("scenario:N", title="Escenario"),
               alt.Tooltip("race_label:N", title="Carrera"),
               alt.Tooltip("pos:Q", title="Posición"), alt.Tooltip("pts:Q", title="Puntos"),
               alt.Tooltip("cum_pts:Q", title="Acumulado")]
    return x, y, tooltip


def _configure(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    return chart.configure(
        background=ASPHALT, padding={"left": 20, "right": 140, "top": 16, "bottom": 16}
    ).configure_view(stroke=None, fill=ASPHALT).configure_axis(grid=True).configure_text(
        font=C.FUENTE)


def season_chart(points: pd.DataFrame, width: int = 860, height: int = 380,
                 driver: str | None = None) -> alt.LayerChart:
    """El campeonato de todos los pilotos en el escenario elegido (selector del gráfico). La
    línea de `driver` (el piloto elegido en la app) va resaltada, y también la que tenga el
    mouse encima."""
    year = int(points["year"].max())
    x, y, tooltip = _axes(points)
    escenario = alt.param(name="escenario", value="Realidad", bind=alt.binding_select(
        options=list(SCENARIOS), name="Escenario "))
    # Clic en una línea (el punto más cercano) o en el nombre del final: la app lee estas dos
    # selecciones (`CLICK_PARAMS`) y elige a ese piloto.
    clic_linea = alt.selection_point(name="clic_linea", fields=["driver"], on="click",
                                     nearest=True)
    clic_nombre = alt.selection_point(name="clic_nombre", fields=["driver"], on="click")
    hover = alt.selection_point(name="hover", fields=["driver"], on="pointerover",
                                nearest=True, clear="pointerout")
    base = alt.Chart(points).transform_filter("datum.scenario == escenario")
    elegido = f"datum.driver == {driver!r}" if driver else "false"
    # Resaltado: el piloto elegido siempre; el del mouse, mientras esté encima.
    on = alt.when(hover, empty=False).then(alt.value(1))
    highlight = on.when(elegido).then(alt.value(1)).otherwise(
        alt.value(0.25 if driver else 0.6))
    color = alt.Color("color:N", scale=None)
    lines = base.mark_line(interpolate="monotone", cursor="pointer").encode(
        x=x, y=y, detail="driver:N", color=color, opacity=highlight,
        strokeWidth=alt.when(hover, empty=False).then(alt.value(3.5)).when(elegido).then(
            alt.value(4)).otherwise(alt.value(1.8)))
    pts = base.mark_circle(size=40).encode(
        x=x, y=y, color=color, tooltip=tooltip,
        opacity=alt.when(hover, empty=False).then(alt.value(0.9)).when(elegido).then(
            alt.value(0.9)).otherwise(alt.value(0))).add_params(hover, clic_linea)
    ends = base.transform_window(
        last="rank()", groupby=["driver"], sort=[alt.SortField("round", order="descending")]
    ).transform_filter("datum.last == 1").mark_text(align="left", dx=6, fontSize=12,
                                                    fontWeight="bold", cursor="pointer").encode(
        x=x, y=alt.Y("label_y_all:Q"), text="driver:N", color=color, opacity=highlight).add_params(clic_nombre)
    chart = alt.layer(lines, pts, ends).add_params(escenario).properties(
        width=width, height=height, title=alt.Title(
            alt.ExprRef(f"'Campeonato {year} de todos los pilotos según: ' + escenario"),
            subtitle=["Puntos 25-18-15-12-10-8-6-4-2-1, solo carrera principal (sin sprints ni "
                      "vuelta rápida), con el orden de llegada del escenario elegido.",
                      "Resaltado: el piloto elegido. Hacé clic en una línea o en un nombre "
                      "para elegir a otro (o usá el selector de más abajo)."],
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=17))
    return _configure(chart)


def driver_chart(points: pd.DataFrame, driver: str, width: int = 860, height: int = 380,
                 model_name: str = "Ridge") -> alt.LayerChart:
    """Un piloto (código, p. ej. "ANT") en los cinco escenarios."""
    scenarios = list(SCENARIOS)
    x, y, tooltip = _axes(points)
    color = alt.Color("scenario:N", sort=scenarios, title=None, scale=alt.Scale(
        domain=scenarios, range=[SCENARIO_COLORS[s] for s in scenarios]),
        legend=alt.Legend(orient="bottom", direction="horizontal", labelColor=INK,
                          symbolType="stroke", symbolStrokeWidth=3))
    dash = alt.StrokeDash("scenario:N", sort=scenarios, legend=None, scale=alt.Scale(
        domain=scenarios, range=[SCENARIO_DASH[s] for s in scenarios]))
    one = points[points["driver"] == driver]
    base = alt.Chart(one)
    lines = base.mark_line(strokeWidth=2.5, interpolate="monotone").encode(
        x=x, y=y, color=color, strokeDash=dash)
    pts = base.mark_circle(size=35).encode(x=x, y=y, color=color, tooltip=tooltip)
    ends = base.transform_window(
        last="rank()", groupby=["scenario"], sort=[alt.SortField("round", order="descending")]
    ).transform_filter("datum.last == 1").transform_calculate(
        label="datum.scenario + ': ' + datum.cum_pts").mark_text(
        align="left", dx=6, fontSize=13).encode(x=x, y=alt.Y("label_y_one:Q"), text="label:N",
                                                color=color)
    chart = alt.layer(lines, pts, ends).properties(
        width=width, height=height, title=alt.Title(
            f"Puntos de {driver} según cada escenario",
            subtitle=[f"Realidad (negro), modelo {model_name} (azul) y grilla (ámbar). "
                      "Punteadas: ajustadas por abandonos (los que no terminaron van al fondo, "
                      "así que no suman)."],
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=17))
    return _configure(chart)
