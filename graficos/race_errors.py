"""¿En qué carreras falla el modelo? MAE del modelo vs. la grilla, fecha por fecha (Altair).

Tres paneles alineados por fecha:

1. MAE de cada carrera del modelo (azul) y de la grilla usada como predicción (ámbar).
2. Diferencia `MAE grilla − MAE modelo` (▲ menta = el modelo acertó mejor; ▼ frambuesa = peor).
3. Cuántos pilotos no terminaron esa carrera (con sus siglas en el tooltip).

Una casilla cambia a la versión ajustada por abandonos (los que no terminaron van al fondo, en el
orden en que abandonaron; ver `race_cars.race_table`), para ver si el modelo pierde por los
abandonos o por otra cosa.

Uso:

    from graficos import race_cars, race_errors
    table = race_cars.race_table(predicciones_de_una_temporada)
    race_errors.errors_chart(race_errors.race_errors(table))
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from graficos import colores as C

from graficos.race_cars import ASPHALT, BAD, GOOD, INK, INK_MUTED, LANE
from graficos.season_points import SCENARIO_COLORS

MODEL_COLOR = SCENARIO_COLORS["Modelo"]
GRID_COLOR = SCENARIO_COLORS["Grilla"]
DNF_COLOR = C.ABANDONO


def race_errors(table: pd.DataFrame) -> pd.DataFrame:
    """Una fila por carrera: MAE del modelo y de la grilla (original y ajustado por abandonos),
    cantidad de pilotos y de no terminados. `table` es la salida de `race_cars.race_table`."""
    g = table.groupby(["race", "race_label"])
    out = g.agg(mae_model=("mae_model", "first"), mae_grid=("mae_grid", "first"),
                mae_adj=("mae_adj", "first"), mae_grid_adj=("mae_grid_adj", "first"),
                n=("driver", "size"), dnf=("dnf", "sum")).reset_index()
    out["dnf_drivers"] = out["race"].map(
        table[table["dnf"] == 1].sort_values("final").groupby("race")["driver"].agg(", ".join)
    ).fillna("—")
    out["round"] = out["race"].str.split("-").str[1].astype(int)
    return out.sort_values("race").reset_index(drop=True)


def errors_chart(errors: pd.DataFrame, width: int = 860,
                 model_name: str = "Ridge") -> alt.VConcatChart:
    """Paneles de MAE por carrera, diferencia y abandonos, con casilla para el ajuste."""
    ajuste = alt.param(name="ajuste", value=False,
                       bind=alt.binding_checkbox(name="Ajustar por abandonos "))
    axis = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LANE, domainColor=LANE,
                tickColor=LANE)
    n_rounds = int(errors["round"].max())
    x = alt.X("round:O", title="Fecha", axis=alt.Axis(labelAngle=0, **axis),
              scale=alt.Scale(domain=list(range(1, n_rounds + 1))))
    base = alt.Chart(errors).transform_calculate(
        m="ajuste ? datum.mae_adj : datum.mae_model",
        g="ajuste ? datum.mae_grid_adj : datum.mae_grid",
    ).transform_calculate(
        diff="datum.g - datum.m",
        tone="datum.g - datum.m > 0 ? 'mejor' : datum.g - datum.m < 0 ? 'peor' : 'igual'",
        mark="datum.g - datum.m > 0 ? '▲' : datum.g - datum.m < 0 ? '▼' : '='",
    )
    tooltip = [alt.Tooltip("race_label:N", title="Carrera"),
               alt.Tooltip("m:Q", title=f"MAE modelo ({model_name})", format=".2f"),
               alt.Tooltip("g:Q", title="MAE grilla", format=".2f"),
               alt.Tooltip("diff:Q", title="Grilla − modelo", format="+.2f"),
               alt.Tooltip("dnf:Q", title="No terminaron"),
               alt.Tooltip("dnf_drivers:N", title="Quiénes")]

    # 1. MAE por carrera: modelo y grilla unidos por una línea (pesa).
    long = base.transform_fold(["m", "g"], as_=["who", "mae"]).transform_calculate(
        who_label="datum.who == 'm' ? 'Modelo' : 'Grilla'")
    who = alt.Color("who_label:N", title=None, scale=alt.Scale(
        domain=["Modelo", "Grilla"], range=[MODEL_COLOR, GRID_COLOR]),
        legend=alt.Legend(orient="top", direction="horizontal", labelColor=INK))
    y_mae = alt.Y("mae:Q", title="MAE (puestos)", axis=alt.Axis(**axis))
    rule = base.mark_rule(color=INK_MUTED, strokeWidth=2, opacity=0.6).encode(
        x=x, y="m:Q", y2="g:Q", tooltip=tooltip)
    # grilla = anillo, modelo = punto lleno: si empatan se ven los dos
    grid_dots = long.transform_filter("datum.who == 'g'").mark_point(
        size=140, filled=False, strokeWidth=2.5, opacity=1).encode(
        x=x, y=y_mae, color=who, tooltip=tooltip)
    model_dots = long.transform_filter("datum.who == 'm'").mark_circle(
        size=55, opacity=1).encode(x=x, y=y_mae, color=who, tooltip=tooltip)
    means = long.transform_aggregate(mae="mean(mae)", groupby=["who_label"])
    mean_lines = means.mark_rule(strokeDash=[4, 4], strokeWidth=1.5).encode(
        y="mae:Q", color=who)
    # etiquetas de los promedios: el más alto un poco arriba, el otro un poco abajo
    labels = means.transform_joinaggregate(top="max(mae)").transform_calculate(
        label="'promedio ' + lower(datum.who_label) + ' ' + format(datum.mae, '.2f')")
    mean_txt = alt.layer(*[
        labels.transform_filter(cond).mark_text(align="left", dx=4, dy=dy, fontSize=10).encode(
            x=alt.value(width + 2), y="mae:Q", text="label:N", color=who)
        for cond, dy in [("datum.mae == datum.top", -7), ("datum.mae < datum.top", 8)]])
    p1 = alt.layer(rule, mean_lines, grid_dots, model_dots, mean_txt).properties(
        width=width, height=240, title=alt.Title(
            alt.ExprRef("'Error por carrera: modelo vs. grilla' + "
                        "(ajuste ? ' (ajustado por abandonos)' : '')"),
            subtitle=["MAE = cuántos puestos se equivoca en promedio con cada piloto (menos es "
                      "mejor). La grilla es usar la largada como predicción.",
                      "Modelo: punto azul; grilla: anillo ámbar (si empatan se ven los dos). "
                      "Líneas punteadas: promedio de la temporada."],
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=15))

    # 2. Diferencia: positivo = el modelo acertó mejor que la grilla.
    tone = alt.Color("tone:N", scale=alt.Scale(domain=["mejor", "peor", "igual"],
                                               range=[GOOD, BAD, INK_MUTED]), legend=None)
    bars = base.mark_bar(width=alt.RelativeBandSize(0.6), cornerRadiusEnd=3).encode(
        x=x, y=alt.Y("diff:Q", title="Grilla − modelo", axis=alt.Axis(**axis)),
        color=tone, tooltip=tooltip)
    # flecha justo afuera de la punta de la barra (arriba si es positiva, abajo si no)
    arrows = base.transform_calculate(
        ay="datum.diff + (datum.diff >= 0 ? 1 : -1) * 0.12").mark_text(fontSize=10).encode(
        x=x, y="ay:Q", text="mark:N", color=tone)
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=INK_MUTED).encode(y="y:Q")
    p2 = alt.layer(zero, bars, arrows).properties(
        width=width, height=150, title=alt.Title(
            "¿Quién acertó mejor?",
            subtitle="▲ menta: el modelo se equivocó menos que la grilla; ▼ frambuesa: más.",
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=13))

    # 3. Abandonos por carrera (otra medida: panel aparte, no segundo eje).
    p3 = alt.layer(
        base.mark_bar(width=alt.RelativeBandSize(0.6), color=DNF_COLOR,
                      cornerRadiusEnd=3).encode(
            x=x, y=alt.Y("dnf:Q", title="No terminaron", axis=alt.Axis(tickMinStep=1, **axis)),
            tooltip=tooltip),
        base.mark_text(dy=-7, fontSize=10, color=INK).encode(x=x, y="dnf:Q", text="dnf:Q"),
    ).properties(width=width, height=110, title=alt.Title(
        "Pilotos que no terminaron", color=INK, anchor="start", fontSize=13))

    return alt.vconcat(p1, p2, p3, spacing=24).add_params(ajuste).resolve_scale(
        color="independent").configure(
        background=ASPHALT, padding={"left": 20, "right": 130, "top": 16, "bottom": 16}
    ).configure_view(stroke=None, fill=ASPHALT).configure_axis(grid=True).configure_text(
        font=C.FUENTE)
