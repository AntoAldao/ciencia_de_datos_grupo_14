"""¿Por qué el modelo mueve a cada piloto respecto de su largada? (Altair)

Descompone la predicción de un modelo lineal (Ridge) en aportes por grupo de variables:

    puntaje_i = b + Σ_j coef_j · z_ij           (z = variables ya imputadas y escaladas)

La largada es la línea base. Cada lugar de grilla vale `k = coef_largada / σ_largada` puntos de
puntaje, así que el puntaje se puede escribir como

    puntaje_i = cte + k · (largada_i + Σ_grupos aporte_ig)

con `aporte_ig = −Σ_{j∈g} coef_j · (z_ij − z̄_j) / k` (centrado en la carrera, signo cambiado
para que positivo = lo adelanta). Es decir: cada grupo **corre al piloto tantos lugares de
grilla** (incluidos sus indicadores de faltante), y el orden de `largada − Σ aportes` es
exactamente el orden que predice el modelo.

Uso (con los aportes y las predicciones que guarda `build_app.py`):

    from graficos import model_moves
    contrib = model_moves.contributions(aportes, filas)
    model_moves.moves_chart(contrib)
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

from graficos import colores as C

from graficos.race_cars import ASPHALT, INK, INK_MUTED, LANE, RACE_COLS, driver_code

# Grupos de variables, en el orden de la paleta (cada variable se lleva su indicador de faltante).
# La largada no es un grupo: es la línea base.
GRID = "Q_GridPosition"
CHAMP = "Puntos en el campeonato (vs. el líder)"
QUALY = "Ritmo en qualy (vs. el más rápido)"
FP_PACE = "Prácticas: vuelta más rápida"
FP_WEAR = "Prácticas: desgaste de gomas"
FINISH = "Carreras terminadas antes"
GROUPS = {
    CHAMP: ["DriverPoints_Before_DBT_%"],
    QUALY: ["Q_Best_seconds_DBT_%"],
    FP_PACE: ["FP_LapTime_min_SOFT_DBT_%", "FP_LapTime_min_MED_DBT_%", "FP_LapTime_min_HARD_DBT_%"],
    FP_WEAR: ["FP_Desgaste_SOFT", "FP_Desgaste_MED"],
    FINISH: ["FinishRate_Before"],
}
# Qué mide cada grupo (glosario del gráfico).
GROUP_HELP = {
    CHAMP: "puntos que tiene el piloto antes de esta carrera, en % menos que el líder del "
           "campeonato (0% = es el líder; 100% = todavía sin puntos)",
    QUALY: "su mejor vuelta de clasificación, en % más lenta que la mejor de la carrera",
    FP_PACE: "su vuelta más rápida en prácticas libres con cada goma, en % más lenta que la mejor",
    FP_WEAR: "en prácticas, cuánto más lenta es su vuelta promedio que su mejor vuelta, en % "
             "(cuánto se gastan las gomas)",
    FINISH: "% de sus carreras anteriores que terminó",
}
# Paleta categórica de referencia (skill dataviz, pasos para fondo oscuro), en su orden fijo y
# validada sobre ASPHALT (pasa todas las pruebas con estos 5; el 6.º, verde, queda bajo 3:1).
# no usa el azul ni el naranja: esos son el modelo y la grilla en toda la app
GROUP_COLORS = C.GRUPOS
OTHER = "Otras"


def _group_of(name: str) -> str:
    if " × " in name:   # término cruzado mejor vuelta × desgaste: modifica el peso del desgaste
        return FP_WEAR
    base = name.removeprefix("missingindicator_")
    return next((g for g, cols in GROUPS.items() if base in cols), OTHER)


def _pct(v: float, digits: int = 1) -> str:
    return f"{v:.{digits}f}%".replace(".", ",")


def _value_text(row: pd.Series) -> dict[str, str]:
    """El valor real del piloto en cada grupo, en palabras (para el tooltip)."""
    pts, q, fin = (row.get("DriverPoints_Before_DBT_%"), row.get("Q_Best_seconds_DBT_%"),
                   row.get("FinishRate_Before"))
    compounds = {"blanda": "SOFT", "media": "MED", "dura": "HARD"}
    laps = [f"{name} +{_pct(row[f'FP_LapTime_min_{c}_DBT_%'])}" for name, c in compounds.items()
            if pd.notna(row.get(f"FP_LapTime_min_{c}_DBT_%"))]
    wear = [f"{name} {_pct(row[f'FP_Desgaste_{c}'])}" for name, c in compounds.items()
            if pd.notna(row.get(f"FP_Desgaste_{c}"))]
    return {
        CHAMP: ("1.ª fecha del año: todavía no hay puntos" if pd.isna(pts) else
                "es el líder del campeonato" if pts == 0 else
                "todavía no sumó puntos" if pts >= 100 else
                f"tiene un {_pct(pts, 0)} menos de puntos que el líder"),
        QUALY: ("sin tiempo de clasificación" if pd.isna(q) else
                "hizo el mejor tiempo de clasificación" if q == 0 else
                f"{_pct(q, 2)} más lento que el mejor en clasificación"),
        FP_PACE: ("sin datos de prácticas" if not laps else
                  "vs. la mejor vuelta con esa goma: " + ", ".join(laps)),
        FP_WEAR: ("sin datos de prácticas" if not wear else
                  "vuelta promedio vs. su mejor vuelta: " + ", ".join(wear)),
        FINISH: ("sin carreras anteriores" if pd.isna(fin) else
                 f"terminó el {fin * 100:.0f}% de sus carreras anteriores"),
    }


def contributions(aportes: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """Cuántos lugares de grilla corre cada grupo de variables a cada piloto (+ = lo adelanta,
    − = lo atrasa) respecto de su largada. Una fila por piloto, carrera y grupo.

    `aportes`: coeficiente × variable transformada de un modelo lineal, una columna por variable
    (ver `build_app.py`); `rows`: las filas crudas correspondientes (mismo índice), con `score`."""
    # 1. Valor de un lugar de grilla en puntaje: pendiente del aporte de la largada (los faltantes
    #    de largada el modelo los completa con 21).
    grid_raw = rows[GRID].fillna(21).astype(float)
    k = np.polyfit(grid_raw, aportes[GRID], 1)[0]
    if k <= 0:
        raise ValueError("el modelo no ordena por largada (coeficiente ≤ 0): no hay línea base")

    # 2. Aporte de cada grupo (sin la largada), centrado en la carrera, en lugares de grilla.
    races = [rows[c] for c in RACE_COLS]
    others = aportes.columns[aportes.columns != GRID]
    terms = aportes[others] - aportes[others].groupby(races).transform("mean")
    gains = -terms.T.groupby(others.map(_group_of)).sum().T / k
    grid = rows.groupby(RACE_COLS)[GRID].rank(method="first")

    # 3. Datos del piloto para etiquetas y tooltip.
    pred = rows.groupby(RACE_COLS)["score"].rank(method="first").astype(int)
    final = rows.groupby(RACE_COLS)["RACE_Position"].rank(method="first").astype(int)
    info = pd.DataFrame({
        "race": rows["Year"].astype(str) + "-" + rows["RoundNumber"].astype(str).str.zfill(2),
        "race_label": rows["Year"].astype(str) + " · fecha " + rows["RoundNumber"].astype(str),
        "driver": rows["DriverId"].map(driver_code),
        "driver_id": rows["DriverId"],
        "grid": grid.astype(int),
        "pred_pos": pred,
        "final": final,
        "dnf": (rows.get("RACE_Finished", pd.Series(1, index=rows.index)) == 0).astype(int),
        "total": gains.sum(axis=1).round(2),
    })
    long = gains.round(3).rename_axis(columns="group").stack().rename("gain").reset_index(
        level="group")
    out = info.join(long)
    values = {i: _value_text(r) for i, r in rows.iterrows()}
    out["value_txt"] = [values[i].get(g, "") for i, g in zip(out.index, out["group"])]

    order = {g: i for i, g in enumerate([*GROUPS, OTHER])}
    out["group_order"] = out["group"].map(order)
    return out.reset_index(drop=True)


def moves_chart(contrib: pd.DataFrame, width: int = 620, row_height: int = 24,
                model_name: str = "Ridge") -> alt.VConcatChart:
    """Arriba: cuánto mueve cada grupo en promedio (todas las carreras). Abajo: para la carrera
    elegida, barras divergentes por piloto (derecha = el modelo lo adelanta respecto de su
    largada) con el total marcado. Selector de carrera y casilla para ocultar abandonos."""
    groups = [g for g in [*GROUPS, OTHER] if g in set(contrib["group"])]
    # sin leyenda: el glosario muestra cada color con su nombre y qué mide
    color = alt.Color("group:N", scale=alt.Scale(domain=groups, range=GROUP_COLORS[:len(groups)]),
                      sort=groups, legend=None)
    races = contrib[["race", "race_label"]].drop_duplicates().sort_values("race")
    carrera = alt.param(name="carrera", value=races["race"].iloc[0], bind=alt.binding_select(
        options=races["race"].tolist(), labels=races["race_label"].tolist(), name="Carrera "))
    abandonos = alt.param(name="abandonos", value=True,
                          bind=alt.binding_checkbox(name="Mostrar los que no terminaron "))
    axis = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LANE, domainColor=LANE,
                tickColor=LANE)

    # Arriba: importancia media (|aporte| promedio por piloto) en todas las carreras.
    summary_bars = alt.Chart(contrib).transform_calculate(
        abs_gain="abs(datum.gain)").transform_aggregate(
        mean_abs="mean(abs_gain)", groupby=["group", "group_order"]
    ).transform_calculate(label="format(datum.mean_abs, '.2f')").encode(
        y=alt.Y("group:N", sort=groups, title=None,
                axis=alt.Axis(labelLimit=220, grid=False, **axis)),
        x=alt.X("mean_abs:Q", title="lugares de grilla (promedio)", axis=alt.Axis(**axis)),
        tooltip=[alt.Tooltip("group:N", title="Grupo"),
                 alt.Tooltip("mean_abs:Q", title="Lugares de grilla promedio", format=".2f")],
    )
    top = alt.layer(
        summary_bars.mark_bar(cornerRadiusEnd=4, height=14).encode(color=color),
        summary_bars.mark_text(align="left", dx=4, color=INK, fontSize=11).encode(text="label:N"),
    ).properties(width=width, height=22 * len(groups), title=alt.Title(
        "Qué mueve al modelo en promedio",
        subtitle="lugares de grilla que cada grupo corre a un piloto (hacia adelante o atrás), "
                 "promedio de todos los pilotos de todas las carreras",
        color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=14))

    # Glosario: qué mide cada grupo (nombre y una línea de explicación).
    gloss = pd.DataFrame({"group": groups, "i": range(len(groups)),
                          "help": [GROUP_HELP.get(g, "") for g in groups]})
    g_base = alt.Chart(gloss).encode(y=alt.Y("i:O", axis=None))
    glossary = alt.layer(
        g_base.mark_square(size=90).encode(x=alt.value(6), color=color),
        g_base.mark_text(align="left", dx=18, dy=-7, color=INK, fontSize=12,
                         fontWeight="bold").encode(x=alt.value(0), text="group:N"),
        g_base.mark_text(align="left", dx=18, dy=8, color=INK_MUTED, fontSize=11).encode(
            x=alt.value(0), text="help:N"),
    ).properties(width=width + 200, height=36 * len(groups), title=alt.Title(
        "Qué mide cada grupo", color=INK, anchor="start", fontSize=14))

    # Abajo: la carrera elegida, un renglón por piloto ordenado por largada.
    help_df = pd.DataFrame({"group": list(GROUP_HELP), "help": list(GROUP_HELP.values())})
    race = alt.Chart(contrib).transform_filter("datum.race == carrera").transform_filter(
        "abandonos || datum.dnf == 0"
    ).transform_lookup(
        lookup="group", from_=alt.LookupData(help_df, "group", ["help"])
    ).transform_calculate(
        row="'P' + datum.grid + '  ' + datum.driver + (datum.dnf ? ' ✕' : '')",
        move=("'P' + datum.grid + ' → P' + datum.pred_pos + '  (real P' + datum.final + ')'"),
        gain_txt=("(datum.gain >= 0 ? '+' : '−') + format(abs(datum.gain), '.2f') + "
                  "(datum.gain >= 0 ? ' (lo adelanta)' : ' (lo atrasa)')"),
        total_txt="(datum.total >= 0 ? '+' : '−') + format(abs(datum.total), '.2f')",
    )
    n_rows = int(contrib.groupby("race")["driver"].nunique().max())
    y = alt.Y("row:N", sort=alt.EncodingSortField("grid", op="min", order="ascending"), title=None,
              axis=alt.Axis(labelFont="monospace", labelFontSize=11, labelColor=INK, ticks=False,
                            domain=False, labelPadding=8, grid=False))
    tooltip = [alt.Tooltip("driver_id:N", title="Piloto"), alt.Tooltip("group:N", title="Grupo"),
               alt.Tooltip("value_txt:N", title="Su valor"),
               alt.Tooltip("help:N", title="Qué mide"),
               alt.Tooltip("gain_txt:N", title="Aporte (lugares de grilla)"),
               alt.Tooltip("total_txt:N", title="Total"), alt.Tooltip("move:N", title="Posición")]
    bars = race.mark_bar(height=row_height * 0.62, stroke=ASPHALT, strokeWidth=1).encode(
        y=y, x=alt.X("gain:Q", stack="zero",
                     title="← lo atrasa  ·  lugares de grilla  ·  lo adelanta →",
                     axis=alt.Axis(**axis)),
        color=color, order=alt.Order("group_order:Q"), opacity=alt.condition(
            "datum.dnf == 1", alt.value(0.45), alt.value(1)),
        tooltip=tooltip)
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK_MUTED, strokeWidth=1).encode(
        x="x:Q")
    totals = race.transform_filter(f"datum.group == '{groups[0]}'")
    total_mark = totals.mark_tick(color=INK, thickness=2, size=row_height * 0.8).encode(
        y=y, x="total:Q", tooltip=[alt.Tooltip("driver_id:N", title="Piloto"),
                                   alt.Tooltip("total_txt:N", title="Total (lugares de grilla)"),
                                   alt.Tooltip("move:N", title="Posición")])
    move_txt = totals.mark_text(align="left", color=INK_MUTED, fontSize=11,
                                font="monospace").encode(
        y=y, x=alt.value(width + 8), text="move:N")
    bottom = alt.layer(zero, bars, total_mark, move_txt).properties(
        width=width, height=row_height * n_rows,
        title=alt.Title(
            f"Por qué el modelo ({model_name}) mueve a cada piloto",
            subtitle=["La largada es la base: cada barra es cuántos lugares de grilla corre "
                      "al piloto ese grupo (derecha = lo adelanta). Raya blanca: total.",
                      "Ordenar por largada − total da la predicción del modelo (a la derecha: "
                      "largada → predicción, y el resultado real). ✕ = no terminó.",
                      "Pasá el mouse por una barra para ver el valor del piloto (ej. cuántos "
                      "puntos tiene menos que el líder)."],
            color=INK, subtitleColor=INK_MUTED, anchor="start", fontSize=14))

    chart = alt.vconcat(top, glossary, bottom, spacing=30).add_params(carrera, abandonos).configure(
        background=ASPHALT, padding={"left": 20, "right": 220, "top": 16, "bottom": 16}
    ).configure_view(stroke=None, fill=ASPHALT).configure_axis(grid=True).configure_text(
        font="sans-serif").configure_legend(labelColor=INK)
    return chart
