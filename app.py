"""Aplicación final – F1 Grupo 14.

Estructura de copa de martini:
  Portada -> Tallo (Los datos, Lo que encontramos, El modelo) -> Copa (Explorá, Probá el modelo)

Lee lo que genera `python build_app.py` (app_data/) y el modelo de la Entrega 3 (modelos/).
Correr:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import modelo_entrega3 as m3
from graficos import model_moves, race_cars, race_errors, season_points, tallo

APP_DATA = Path(__file__).resolve().parent / "app_data"
ANIO_TEST = 2026   # lo único que el modelo no vio al entrenar (2018-2025)
PIPELINE = "https://github.com/Gonzalez-Matias/f1-pipeline"

# Nombre legible de cada columna que recibe el modelo (Probá el modelo).
ETIQUETAS = {
    "Q_GridPosition": "Posición de largada",
    "Q_Best_seconds_DBT_%": "Mejor vuelta de clasificación (% más lenta que la mejor)",
    "DriverPoints_Before_DBT_%": "Puntos antes de la carrera (% menos que el líder)",
    "FP_LapTime_min_SOFT_DBT_%": "Prácticas: mejor vuelta con blanda (% más lenta que la mejor)",
    "FP_LapTime_min_MED_DBT_%": "Prácticas: mejor vuelta con media (% más lenta que la mejor)",
    "FP_LapTime_min_HARD_DBT_%": "Prácticas: mejor vuelta con dura (% más lenta que la mejor)",
    "FP_LapTime_min_SOFT_ABS": "Prácticas: mejor vuelta con blanda (segundos)",
    "FP_LapTime_mean_SOFT_ABS": "Prácticas: vuelta promedio con blanda (segundos)",
    "FP_LapTime_min_MED_ABS": "Prácticas: mejor vuelta con media (segundos)",
    "FP_LapTime_mean_MED_ABS": "Prácticas: vuelta promedio con media (segundos)",
}

st.set_page_config(page_title="F1 – Grupo 14", layout="wide")


@st.cache_data
def cargar():
    leer = lambda nombre: json.loads((APP_DATA / nombre).read_text(encoding="utf-8"))  # noqa: E731
    return (pd.read_parquet(APP_DATA / "predicciones.parquet"),
            pd.read_parquet(APP_DATA / "aportes.parquet"), leer("resumen.json"),
            leer("notebook.json"))


@st.cache_resource
def modelo():
    return m3.cargar()


@st.cache_data
def tabla_temporada(df, anio):
    return race_cars.race_table(df[df["Year"] == anio])


def tabla_nb(comienzo: str) -> pd.DataFrame:
    """Una tabla del notebook de la Entrega 3 ejecutado (ver build_app.py), por su título."""
    titulo = next(t for t in notebook if t.startswith(comienzo))
    t = notebook[titulo]
    ancho = len(t["columnas"])
    filas = [[""] * (ancho - len(f)) + f for f in t["filas"]]   # índices de dos niveles
    tabla = pd.DataFrame(filas, columns=[c or " " for c in t["columnas"]])
    return tabla.set_index(tabla.columns[0])


def fmt(x: float, decimales: int = 2) -> str:
    return f"{x:.{decimales}f}".replace(".", ",")


df, aportes, resumen, notebook = cargar()
test = resumen["test"]
nombre_modelo = resumen["modelo"]["elegido"]
tabla_test = tabla_temporada(df, ANIO_TEST)
abandonos = tabla_nb("Peso de los abandonos")
pct_error_abandonos = float(abandonos.loc["% del error absoluto total que explican"].iloc[0]
                            .replace(",", "."))
pct_filas_abandonos = float(abandonos.loc["% de las filas"].iloc[0].replace(",", "."))

# ----------------------------------------------------------------------------------------------
# PORTADA: la pregunta, la idea central en una oración, tres números.
# ----------------------------------------------------------------------------------------------
st.title("¿Se puede anticipar en qué puesto termina cada piloto de F1 con lo que se sabe "
         "antes de la carrera?")
st.subheader("El modelo ordena mejor que la grilla a los pilotos que terminan la carrera, pero los "
             "abandonos, que nadie anticipa, se comen esa ventaja.")
c1, c2, c3 = st.columns(3)
c1.metric("Error sin abandonos: modelo vs. grilla",
          f"{fmt(test['mae_modelo_sin_abandonos'])} vs. {fmt(test['mae_grilla_sin_abandonos'])}",
          help="Puestos de error promedio por piloto, solo los que terminaron (test 2026).")
c2.metric("Error con todos los pilotos: modelo vs. grilla",
          f"{fmt(test['mae_modelo'])} vs. {fmt(test['mae_grilla'])}",
          help="Con los abandonos incluidos quedan casi empatados (test 2026).")
c3.metric("Parte del error que explican los abandonos", f"{pct_error_abandonos:.0f}%",
          help=f"Son el {pct_filas_abandonos:.0f}% de los pilotos del test 2026.")
st.caption(f"Test: las {test['carreras']} carreras de {ANIO_TEST}, que el modelo no vio al "
           "entrenar. Error = cuántos puestos se equivoca en promedio con cada piloto.")

st.divider()

# ----------------------------------------------------------------------------------------------
# TALLO: cada sección = título que afirma + gráfico + «Cómo lo sabemos» (cerrado por defecto).
# ----------------------------------------------------------------------------------------------
n_filas, n_carreras = len(df), df["Carrera"].nunique()
pct_dnf = (df["Terminó"] == False).mean()  # noqa: E712
st.header(f"1. En {n_carreras} Grandes Premios de 2018 a 2026, uno de cada "
          f"{round(1 / pct_dnf)} pilotos no termina la carrera")
st.altair_chart(tallo.abandonos_por_temporada(df), theme=None)
st.write(f"Cada fila es un piloto en un Gran Premio: {n_filas:,} filas.".replace(",", ".")
         + f" Mirá que el {pct_dnf:.0%} de no terminados se repite todas las temporadas: es un "
         "evento frecuente, no una rareza, y el modelo no tiene forma de verlo venir.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        f"- **De dónde salen:** el pipeline de la Entrega 1 (Airflow, [{PIPELINE}]({PIPELINE})) "
        "junta clasificación, prácticas libres, campeonato y resultado de cada GP en "
        f"`{resumen['datos']['archivo']}`. Datos al día: {resumen['datos']['al_dia']}.\n"
        "- **Qué es una fila:** un piloto en un Gran Premio; el objetivo es su posición final.\n"
        "- **Qué se filtró, paso por paso** (la limpieza del notebook de la Entrega 3):")
    st.dataframe(tabla_nb("Limpieza aplicada"))
    st.markdown(
        "- **Columnas descartadas por fuga:** todo lo que se conoce después de la carrera "
        "(`RACE_Finished`, `RACE_Status`, `RACE_Laps_Down`, `RACE_Lapped`, `RACE_DNF_Type`, las "
        "sanciones) nunca entra al modelo; si terminó o no se usa solo para medir. Las columnas "
        "`_Before` se calculan con el campeonato previo a la fecha.")

st.header("2. Quien larga adelante termina adelante: la grilla sola ya ordena buena parte de "
          "la carrera")
col_g, col_t = st.columns([3, 2])
with col_g:
    st.altair_chart(tallo.grilla_vs_final(df), theme=None)
top5 = df[df["Q_GridPosition"] <= 5]
with col_t:
    st.write(f"De los que largan entre los 5 primeros, el **{(top5['Puesto'] <= 5).mean():.0%}** "
             "termina entre los 5 primeros. Mirá la diagonal: casi todos terminan cerca de "
             "donde largaron, y los cambios grandes son la excepción. Por eso la grilla es la "
             "referencia que el modelo tiene que superar.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
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
        "Los que largan desde boxes (sin posición de grilla) cuentan en «16 o más».")

st.header(f"3. El modelo le gana a la grilla en los que terminan "
          f"({fmt(test['mae_modelo_sin_abandonos'])} contra "
          f"{fmt(test['mae_grilla_sin_abandonos'])} puestos), pero con los abandonos quedan casi "
          f"empatados ({fmt(test['mae_modelo'])} contra {fmt(test['mae_grilla'])})")
st.altair_chart(race_errors.errors_chart(race_errors.race_errors(tabla_test),
                                         model_name=nombre_modelo), theme=None)
st.write("Cada punto es una carrera de 2026. Mirá el panel de abajo: las carreras con más "
         "abandonos son las de más error, para el modelo y para la grilla por igual. Con la "
         "casilla «Ajustar por abandonos» los que no terminaron pasan al fondo y el modelo gana "
         "en más carreras.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "- **Métrica: MAE en puestos**, después de ordenar a los pilotos dentro de cada GP: "
        "«en promedio, el puesto predicho está a X puestos del real». Trata igual a todos los "
        "errores y está en la misma unidad que la grilla, así que se pueden comparar.\n"
        "- **El piso:** un modelo que pone a todos en la mitad de la tabla (`DummyRegressor`). "
        "La referencia que importa es **la grilla sola**: el puesto predicho es el de largada.\n"
        "- **Cómo se validó:** validación cruzada por temporada: cada temporada de 2020 a 2025 "
        "se valida entrenando con todas las demás, así cada GP queda entero de un lado. El "
        "modelo final se entrena con 2018-2025 y se mide una sola vez en 2026.")
    st.dataframe(tabla_nb("Partición"))
    st.dataframe(tabla_nb("Piso y referencia"))
    st.markdown("**Comparación de modelos** (media y desvío de la validación cruzada; cada uno "
                "con sus mejores hiperparámetros). Ninguno le gana al lineal por más que el "
                "desvío, así que se elige el más simple:")
    st.dataframe(tabla_nb("Todos los modelos ajustados"))
    st.markdown(f"**Ajuste del elegido** ({nombre_modelo} → Ridge): la penalización `alpha`:")
    st.dataframe(tabla_nb("Lineal (elegido)"))
    st.markdown(f"**Resultado en el test ({ANIO_TEST})**, medido una sola vez:")
    st.dataframe(tabla_nb("Test 2026 ("))
    st.markdown("**Dónde se equivoca:** en los abandonos, pocas filas que explican una parte "
                "grande del error; y adelante los pone algo atrás y atrás algo adelante:")
    st.dataframe(tabla_nb("Peso de los abandonos"))
    st.dataframe(tabla_nb("Error por tramo"))
    st.markdown("Anticipar los abandonos con lo que se sabe antes de la carrera no funciona "
                "(AUC ≈ 0,57; 0,5 es adivinar):")
    st.dataframe(tabla_nb("Anticipar abandonos"))
    st.markdown("**En qué se apoya:** los coeficientes (columnas escaladas; positivo = empuja "
                "hacia atrás). Pesan la grilla, la distancia al líder y la clasificación:")
    st.dataframe(tabla_nb("Coeficientes del modelo final"))
    st.markdown("**Chequeo de fuga** en las columnas que más pesan:")
    st.dataframe(tabla_nb("Chequeo de fuga"))

st.divider()

# ----------------------------------------------------------------------------------------------
# COPA: la maneja el usuario.
# ----------------------------------------------------------------------------------------------
tab_explora, tab_prueba = st.tabs(["Explorá", "Probá el modelo"])

with tab_explora:
    anios = sorted(df["Year"].unique(), reverse=True)
    anio = st.selectbox("Temporada", [int(a) for a in anios])
    if anio < ANIO_TEST:
        st.caption(f"El modelo se entrenó con 2018-2025: en {anio} ya conocía estas carreras. "
                   f"Lo que no vio es {ANIO_TEST}.")
    tabla = tabla_temporada(df, anio)
    sub_campeonato, sub_autos, sub_porque = st.tabs(
        ["Campeonato", "Carrera por carrera", "Por qué el modelo mueve a cada piloto"])
    with sub_campeonato:
        st.altair_chart(season_points.points_chart(season_points.season_points(tabla),
                                                   model_name=nombre_modelo), theme=None)
    with sub_autos:
        # HTML propio: lleva el botón «Correr» que anima la carrera.
        st.iframe(race_cars.to_html(race_cars.race_cars_compare(
            tabla, model_name=nombre_modelo)))
    with sub_porque:
        es_anio = (df["Year"] == anio).to_numpy()
        contrib = model_moves.contributions(
            aportes[es_anio].drop(columns=["Carrera", "DriverId"]), df[es_anio])
        st.altair_chart(model_moves.moves_chart(contrib, model_name=nombre_modelo), theme=None)

with tab_prueba:
    guardado = modelo()
    rangos = resumen["modelo"]["rangos"]
    st.write("Elegí una carrera y un piloto y cambiá sus valores: el modelo lo vuelve a ordenar "
             "contra los demás de esa carrera. Los campos solo aceptan valores dentro de lo que el "
             "modelo vio al entrenar; vacío = sin dato (el modelo lo completa).")
    col_a, col_b = st.columns(2)
    carrera = col_a.selectbox("Carrera", sorted(df["Carrera"].unique(), reverse=True))
    autos = df[df["Carrera"] == carrera].reset_index(drop=True)
    piloto = col_b.selectbox("Piloto", sorted(autos["DriverId"]))
    i = autos.index[autos["DriverId"] == piloto][0]

    fuera = [c for c, (lo, hi) in rangos.items()
             if pd.notna(autos.loc[i, c]) and not lo <= autos.loc[i, c] <= hi]
    if fuera:
        st.warning("Sus datos reales tienen valores que el modelo nunca vio al entrenar ("
                   + ", ".join(ETIQUETAS.get(c, c) for c in fuera)
                   + "): en los campos se recortan al rango visto.")

    caso = autos.copy()
    cols = st.columns(2)
    for j, (col, (lo, hi)) in enumerate(rangos.items()):
        actual = autos.loc[i, col]
        caso.loc[i, col] = cols[j % 2].number_input(
            ETIQUETAS.get(col, col), min_value=lo, max_value=hi,
            value=None if pd.isna(actual) else float(min(max(actual, lo), hi)),
            key=f"{carrera}-{piloto}-{col}")

    antes = pd.Series(m3.puntaje(guardado, autos)).rank(method="first")
    despues_puntaje = pd.Series(m3.puntaje(guardado, caso))
    despues = despues_puntaje.rank(method="first")
    k1, k2, k3 = st.columns(3)
    k1.metric("Puesto predicho con sus datos reales", int(antes[i]))
    k2.metric("Puesto predicho con tus valores", int(despues[i]),
              delta=int(antes[i] - despues[i]), help="positivo = el modelo lo adelanta")
    k3.metric("Puntaje (0 = ganador, 1 = último)", fmt(despues_puntaje[i], 3))
