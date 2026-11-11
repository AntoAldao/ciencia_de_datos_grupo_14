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
    season_points.points_chart(season_points.season_points(table))
"""

from __future__ import annotations

import altair as alt
import pandas as pd

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
# ajustado por abandonos. Azul y naranja: slots 1 y 2 de la paleta de referencia (dataviz).
SCENARIO_COLORS = {"Realidad": INK, "Modelo": "#3987e5", "Modelo ajustado": "#3987e5",
                   "Grilla": "#d95926", "Grilla ajustada": "#d95926"}
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


def points_chart(points: pd.DataFrame, width: int = 860, height: int = 380,
                 model_name: str = "Ridge") -> alt.VConcatChart:
    """Arriba: el campeonato de todos los pilotos en el escenario elegido (selector). Clic en un
    piloto: abajo aparecen sus cinco escenarios."""
    scenarios = list(SCENARIOS)
    year = int(points["year"].max())
    leader = (points[points["scenario"] == "Realidad"].sort_values("race")
              .groupby("driver")["cum_pts"].last().idxmax())
    escenario = alt.param(name="escenario", value="Realidad", bind=alt.binding_select(
        options=scenarios, name="Escenario (arriba) "))
    piloto = alt.selection_point(name="piloto", fields=["driver"], on="click", nearest=True,
                                 value=[{"driver": leader}], clear=False)
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

    # Arriba: todos los pilotos en el escenario elegido; el elegido resaltado.
    top_base = alt.Chart(points).transform_filter("datum.scenario == escenario")
    highlight = alt.condition(piloto, alt.value(1), alt.value(0.25))
    lines = top_base.mark_line(strokeWidth=2, interpolate="monotone").encode(
        x=x, y=y, detail="driver:N", color=alt.Color("color:N", scale=None), opacity=highlight,
        strokeWidth=alt.condition(piloto, alt.value(3.5), alt.value(1.8)))
    pts = top_base.mark_circle(size=40).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None),
        opacity=alt.condition(piloto, alt.value(0.9), alt.value(0)), tooltip=tooltip
    ).add_params(piloto)
    ends = top_base.transform_window(
        last="rank()", groupby=["driver"], sort=[alt.SortField("round", order="descending")]
    ).transform_filter("datum.last == 1").mark_text(align="left", dx=6, fontSize=10,
                                                    fontWeight="bold").encode(
        x=x, y=alt.Y("label_y_all:Q"), text="driver:N", color=alt.Color("color:N", scale=None),
        opacity=highlight)
    top = alt.layer(lines, pts, ends).properties(
        width=width, height=height, title=alt.Title(
            alt.ExprRef(f"'Campeonato {year} según: ' + escenario"),
            subtitle=["Puntos 25-18-15-12-10-8-6-4-2-1, solo carrera principal (sin sprints ni "
                      "vuelta rápida), con el orden de llegada del escenario elegido.",
                      "Clic en un piloto para ver abajo sus cinco escenarios."],
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=15))

    # Abajo: el piloto elegido en los cinco escenarios.
    color = alt.Color("scenario:N", sort=scenarios, title=None, scale=alt.Scale(
        domain=scenarios, range=[SCENARIO_COLORS[s] for s in scenarios]),
        legend=alt.Legend(orient="bottom", direction="horizontal", labelColor=INK,
                          symbolType="stroke", symbolStrokeWidth=3))
    dash = alt.StrokeDash("scenario:N", sort=scenarios, legend=None, scale=alt.Scale(
        domain=scenarios, range=[SCENARIO_DASH[s] for s in scenarios]))
    bottom_base = alt.Chart(points).transform_filter(piloto)
    s_lines = bottom_base.mark_line(strokeWidth=2.5, interpolate="monotone").encode(
        x=x, y=y, color=color, strokeDash=dash)
    s_pts = bottom_base.mark_circle(size=35).encode(x=x, y=y, color=color, tooltip=tooltip)
    s_ends = bottom_base.transform_window(
        last="rank()", groupby=["scenario"], sort=[alt.SortField("round", order="descending")]
    ).transform_filter("datum.last == 1").transform_calculate(
        label="datum.scenario + ': ' + datum.cum_pts").mark_text(
        align="left", dx=6, fontSize=11).encode(x=x, y=alt.Y("label_y_one:Q"), text="label:N",
                                                color=color)
    bottom = alt.layer(s_lines, s_pts, s_ends).properties(
        width=width, height=height, title=alt.Title(
            alt.ExprRef("'Puntos de ' + (piloto.driver ? piloto.driver[0] : '') + "
                        "' según cada escenario'"),
            subtitle=[f"Realidad (blanco), modelo {model_name} (azul) y grilla (naranja). "
                      "Punteadas: ajustadas por abandonos (los que no terminaron van al fondo, "
                      "así que no suman)."],
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=15))

    return alt.vconcat(top, bottom, spacing=40).add_params(escenario).configure(
        background=ASPHALT, padding={"left": 20, "right": 140, "top": 16, "bottom": 16}
    ).configure_view(stroke=None, fill=ASPHALT).configure_axis(grid=True).configure_text(
        font="sans-serif")
