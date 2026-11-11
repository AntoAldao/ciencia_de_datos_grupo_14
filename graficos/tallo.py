"""Gráficos del tallo que no vienen de los otros módulos: Los datos y Lo que encontramos.

Mismo estilo que el resto de la app (fondo oscuro) y mismos colores con el mismo significado:
gris = no terminó (como en `race_errors`), naranja = la grilla (como en `season_points`).
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from graficos.race_cars import ASPHALT, INK, INK_MUTED, LANE
from graficos.race_errors import DNF_COLOR

GRID_ORANGE = "#d95926"
FRANJAS = [(1, 5, "1–5"), (6, 10, "6–10"), (11, 15, "11–15"), (16, 99, "16 o más")]
AXIS = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LANE, domainColor=LANE,
            tickColor=LANE)


def _estilo(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    return chart.configure(background=ASPHALT, padding=16).configure_view(
        stroke=None, fill=ASPHALT).configure_text(font="sans-serif")


def _franja(puesto: pd.Series) -> pd.Series:
    etiqueta = pd.Series("16 o más", index=puesto.index)
    for lo, hi, nombre in FRANJAS:
        etiqueta[(puesto >= lo) & (puesto <= hi)] = nombre
    return etiqueta


def abandonos_por_temporada(df: pd.DataFrame, width: int = 760) -> alt.TopLevelMixin:
    """% de pilotos que no terminó la carrera, por temporada (barras), con el promedio."""
    t = df.groupby("Year").agg(filas=("DriverId", "size"),
                               no_terminaron=("Terminó", lambda s: int((s == False).sum())),  # noqa: E712
                               carreras=("Carrera", "nunique")).reset_index()
    t["pct"] = t["no_terminaron"] / t["filas"]
    promedio = t["no_terminaron"].sum() / t["filas"].sum()
    tooltip = [alt.Tooltip("Year:O", title="Temporada"), alt.Tooltip("carreras:Q", title="Carreras"),
               alt.Tooltip("filas:Q", title="Pilotos-carrera"),
               alt.Tooltip("no_terminaron:Q", title="No terminaron"),
               alt.Tooltip("pct:Q", title="% que no terminó", format=".1%")]
    base = alt.Chart(t).encode(x=alt.X("Year:O", title="Temporada",
                                       axis=alt.Axis(labelAngle=0, **AXIS)))
    barras = base.mark_bar(color=DNF_COLOR, cornerRadiusEnd=3, width=alt.RelativeBandSize(0.6)
                           ).encode(y=alt.Y("pct:Q", title="% de pilotos que no terminó",
                                            axis=alt.Axis(format="%", **AXIS)), tooltip=tooltip)
    etiquetas = base.mark_text(dy=-7, color=INK, fontSize=11).encode(
        y="pct:Q", text=alt.Text("pct:Q", format=".0%"))
    linea = alt.Chart(pd.DataFrame({"y": [promedio]})).mark_rule(
        color=INK_MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    texto = alt.Chart(pd.DataFrame({"y": [promedio], "t": [f"promedio {promedio:.0%}"]})).mark_text(
        align="left", dx=4, dy=-6, color=INK_MUTED, fontSize=11).encode(
        y="y:Q", x=alt.value(0), text="t:N")
    return _estilo(alt.layer(barras, etiquetas, linea, texto).properties(width=width, height=260))


def grilla_vs_final(df: pd.DataFrame, width: int = 520) -> alt.TopLevelMixin:
    """De los que largan en cada franja de la grilla, en qué franja terminan (% por fila)."""
    d = pd.DataFrame({"largada": _franja(df["Q_GridPosition"].fillna(99)),
                      "final": _franja(df["Puesto"])})
    t = d.value_counts().rename("n").reset_index()
    t["pct"] = t["n"] / t.groupby("largada")["n"].transform("sum")
    orden = [f[2] for f in FRANJAS]
    tooltip = [alt.Tooltip("largada:N", title="Largó"), alt.Tooltip("final:N", title="Terminó"),
               alt.Tooltip("n:Q", title="Pilotos-carrera"),
               alt.Tooltip("pct:Q", title="% de los que largaron ahí", format=".0%")]
    base = alt.Chart(t).encode(
        y=alt.Y("largada:N", sort=orden, title="Largó en el puesto", axis=alt.Axis(**AXIS)),
        x=alt.X("final:N", sort=orden, title="Terminó en el puesto",
                axis=alt.Axis(labelAngle=0, orient="top", **AXIS)))
    celdas = base.mark_rect(stroke=ASPHALT, strokeWidth=2).encode(
        color=alt.Color("pct:Q", scale=alt.Scale(range=["#3a2d27", GRID_ORANGE], domain=[0, 0.8]),
                        legend=None), tooltip=tooltip)
    texto = base.mark_text(fontSize=14, color=INK).encode(text=alt.Text("pct:Q", format=".0%"))
    return _estilo(alt.layer(celdas, texto).properties(width=width, height=width * 0.75))
