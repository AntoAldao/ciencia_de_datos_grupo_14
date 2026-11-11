"""Gráficos de la app (Altair) y paleta común.

La paleta vale para TODA la aplicación: un color significa siempre lo mismo.
  ROJO     -> lo que entra al modelo (rojo Ferrari / F1)
  AMARILLO -> el objetivo: la posición final (bandera amarilla)
  GRIS     -> lo que se descarta (asfalto)
"""
import altair as alt
import pandas as pd

# --- Paleta --------------------------------------------------------------------------------
ROJO = "#E10600"
AMARILLO = "#FFD400"
GRIS = "#7A7A85"
FONDO = "#15151E"       # carbono, el fondo de las pantallas de la F1
TEXTO = "#F2F2F5"
LLANTA = "#D9D9DE"

# --- Qué pasó con cada una de las 59 columnas (tabla de la Sección 7 del EDA) ---------------
GRUPOS_COLUMNAS = {
    "Entran al modelo": [
        "Q_GridPosition", "Q_Best_seconds_DBT_%", "DriverPoints_Before_DBT_%",
        "FP_LapTime_min_SOFT_DBT_%", "FP_LapTime_min_MED_DBT_%", "FP_LapTime_min_HARD_DBT_%",
    ],
    "Objetivo": ["RACE_Position"],
    "Telemetría": [
        "FP_Throttle_fastlap_ABS", "FP_Speed_fastlap_ABS", "FP_Speed_max_ABS", "FP_RPM_fastlap_ABS",
        "FP_Brake_fastlap_ABS", "FP_Throttle_fastlap_DBT_%", "FP_Speed_fastlap_DBT_%",
        "FP_Speed_max_DBT_%", "FP_RPM_fastlap_DBT_%", "FP_Brake_fastlap_DBT_%",
        "FP_Throttle_mean_MED_ABS", "FP_Speed_mean_MED_ABS", "FP_RPM_mean_MED_ABS",
        "FP_Brake_mean_MED_ABS", "FP_Throttle_mean_MED_DBT_%", "FP_Speed_mean_MED_DBT_%",
        "FP_RPM_mean_MED_DBT_%", "FP_Brake_mean_MED_DBT_%",
    ],
    "Tiempos en segundos (versión absoluta)": [
        "Q1_seconds_ABS", "Q2_seconds_ABS", "Q3_seconds_ABS", "Q_Best_seconds_ABS",
        "FP_LapTime_min_SOFT_ABS", "FP_LapTime_mean_SOFT_ABS", "FP_LapTime_min_MED_ABS",
        "FP_LapTime_mean_MED_ABS", "FP_LapTime_min_HARD_ABS", "FP_LapTime_mean_HARD_ABS",
    ],
    "Repiten a otra columna": [
        "Q_Position", "Q1_seconds_DBT_%", "Q2_seconds_DBT_%", "Q3_seconds_DBT_%",
        "DriverPosition_Before", "DriverPoints_Before", "DriverPoints_Rate_Before",
        "TeamPosition_Before", "TeamPoints_Before",
    ],
    "Contexto de la fecha": [
        "Year", "RoundNumber", "Races_Before", "FinishRate_Before", "Avg_Position_Gain_Before",
    ],
    "Casi sin datos (lluvia e intermedios)": [
        "FP_LapTime_min_INTER_ABS", "FP_LapTime_min_INTER_DBT_%",
        "FP_LapTime_min_WET_ABS", "FP_LapTime_min_WET_DBT_%",
    ],
    "Vueltas promedio": [
        "FP_LapTime_mean_SOFT_DBT_%", "FP_LapTime_mean_MED_DBT_%", "FP_LapTime_mean_HARD_DBT_%",
    ],
    "Identificadores": ["DriverId", "TeamId", "DriverNumber"],
}


def destino(grupo):
    if grupo == "Entran al modelo":
        return "Entra al modelo"
    if grupo == "Objetivo":
        return "Objetivo"
    return "Se descarta"


def tabla_columnas(columnas):
    """Una fila por grupo, con cuántas columnas tiene y cuáles. Falla si falta alguna columna."""
    asignadas = {c for cols in GRUPOS_COLUMNAS.values() for c in cols}
    sin_grupo = set(columnas) - asignadas
    if sin_grupo:
        raise ValueError(f"Columnas sin clasificar: {sorted(sin_grupo)}")
    filas = []
    for grupo, cols in GRUPOS_COLUMNAS.items():
        presentes = [c for c in cols if c in set(columnas)]
        filas.append({"motivo": grupo, "n": len(presentes), "destino": destino(grupo),
                      "columnas": ", ".join(presentes)})
    return pd.DataFrame(filas)


def grafico_columnas(columnas):
    """Las 59 columnas, agrupadas por lo que pasó con ellas. Cada barra termina en un neumático."""
    datos = tabla_columnas(columnas)
    orden = datos.sort_values("n", ascending=False)["motivo"].tolist()
    tope = int(datos["n"].max()) + 3

    base = alt.Chart(datos).encode(
        y=alt.Y("motivo:N", sort=orden, title=None, axis=alt.Axis(labelLimit=320, labelFontSize=13)),
        x=alt.X("n:Q", title="Cantidad de columnas", scale=alt.Scale(domain=[0, tope])),
    )
    color = alt.Color(
        "destino:N", title=None,
        scale=alt.Scale(domain=["Entra al modelo", "Objetivo", "Se descarta"],
                        range=[ROJO, AMARILLO, GRIS]),
        legend=alt.Legend(orient="bottom"),
    )

    pista = base.mark_bar(height=6, opacity=0.9).encode(color=color.legend(None))
    neumatico = base.mark_circle(size=1500, opacity=1, stroke=FONDO, strokeWidth=6).encode(
        color=color,
        tooltip=[alt.Tooltip("motivo:N", title="Motivo"), alt.Tooltip("n:Q", title="Columnas"),
                 alt.Tooltip("columnas:N", title="Cuáles")],
    )
    llanta = base.mark_circle(size=260, color=LLANTA, opacity=1)
    cifra = base.mark_text(align="left", dx=26, fontSize=15, fontWeight="bold", color=TEXTO).encode(text="n:Q")

    return (
        alt.layer(pista, neumatico, llanta, cifra)
        .properties(height=380, background=FONDO, padding={"left": 10, "right": 20, "top": 10, "bottom": 10})
        .configure_axis(labelColor=TEXTO, titleColor=TEXTO, gridColor="#2A2A36", domainColor="#2A2A36",
                        tickColor="#2A2A36")
        .configure_legend(labelColor=TEXTO, labelFontSize=13, symbolType="circle", symbolSize=200)
        .configure_view(stroke=None)
    )
