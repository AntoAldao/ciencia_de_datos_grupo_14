"""Aplicación final – F1 Grupo 14. Esqueleto inicial.

Estructura de copa de martini:
  Portada -> Tallo (Los datos, Lo que encontramos, El modelo) -> Copa (Explorá, Probá el modelo)

Correr:  streamlit run app.py
"""
import altair as alt
import pandas as pd
import streamlit as st

ARCHIVO = "data/f1_all_full_v2.parquet"

st.set_page_config(page_title="F1 – Grupo 14", layout="wide")


@st.cache_data
def cargar():
    return pd.read_parquet(ARCHIVO)


df = cargar()

# ----------------------------------------------------------------------------------------------
# PORTADA: la pregunta, la idea central en una oración, tres números.
# ----------------------------------------------------------------------------------------------
st.title("¿Se puede superar a la grilla de largada usando más datos?")
st.subheader("Más datos le ganan a la grilla, pero los abandonos esconden gran parte de esa ventaja.")
c1, c2, c3 = st.columns(3)
c1.metric("Error del modelo contra la grilla (puestos, validación 2020–2025)", "3,29 vs 3,49")
c2.metric("Filas en las que el piloto abandona (según la temporada)", "10 % a 17 %")
c3.metric("Error sin contar abandonos (modelo vs grilla)", "1,73 vs 1,96")

st.divider()

# ----------------------------------------------------------------------------------------------
# TALLO: cada sección = título que afirma + gráfico + «Cómo lo sabemos» (cerrado por defecto).
# ----------------------------------------------------------------------------------------------
st.header("1. TODO: título que afirma algo de los datos")
filas_por_anio = df.groupby("Year").size().reset_index(name="filas")
st.altair_chart(
    alt.Chart(filas_por_anio).mark_bar().encode(
        x=alt.X("Year:O", title="Temporada"),
        y=alt.Y("filas:Q", title="Filas (piloto en un GP)"),
    ),
    use_container_width=True,
)
st.write("TODO: qué mirar en el gráfico.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "- TODO: de dónde salen los datos (pipeline) y fecha\n"
        "- TODO: qué es una fila\n"
        "- TODO: filtros paso a paso, con filas en cada uno\n"
        "- TODO: columnas descartadas por fuga"
    )

st.header("2. TODO: título que afirma el hallazgo principal")
st.write("TODO: gráfico (Altair) del hallazgo del EDA.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "- TODO: hipótesis que se sostuvo, con su número\n"
        "- TODO: hipótesis que no se sostuvo, con su número\n"
        "- TODO: cómo se construyó el gráfico"
    )

st.header("3. TODO: título que afirma qué logró el modelo")
st.write("TODO: gráfico (Altair) del modelo contra la grilla y el piso.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "- TODO: métrica y por qué (MAE en puestos)\n"
        "- TODO: piso\n"
        "- TODO: validación por temporada\n"
        "- TODO: tabla de comparación con media y desvío; ajuste del elegido; resultado en test; dónde se equivoca\n"
        "- TODO: en qué se apoya"
    )

st.divider()

# ----------------------------------------------------------------------------------------------
# COPA: la maneja el usuario.
# ----------------------------------------------------------------------------------------------
tab_explora, tab_prueba = st.tabs(["Explorá", "Probá el modelo"])

with tab_explora:
    # Zoom y filtro: dos controles que cambian el gráfico.
    anios = sorted(df["Year"].unique())
    anio = st.selectbox("Temporada", ["Todas"] + [int(a) for a in anios])
    equipos = sorted(df["TeamId"].dropna().unique())
    equipo = st.selectbox("Escudería", ["Todas"] + list(equipos))

    vista = df
    if anio != "Todas":
        vista = vista[vista["Year"] == anio]
    if equipo != "Todas":
        vista = vista[vista["TeamId"] == equipo]

    # Panorama + detalle a pedido (tooltip). TODO: agregar la predicción del modelo al tooltip.
    st.altair_chart(
        alt.Chart(vista).mark_circle(opacity=0.6).encode(
            x=alt.X("Q_GridPosition:Q", title="Posición de largada"),
            y=alt.Y("RACE_Position:Q", title="Posición final"),
            tooltip=["DriverId", "TeamId", "Year", "RoundNumber", "Q_GridPosition", "RACE_Position"],
        ).interactive(),
        use_container_width=True,
    )

with tab_prueba:
    st.write("TODO: cargar las 8 columnas del modelo, avisar si el valor está fuera del rango visto, "
             "y mostrar el puntaje (0 a 1) y el puesto estimado.")
