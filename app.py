"""Aplicación final – F1 Grupo 14.

Estructura de copa de martini:
  Portada -> Tallo (Los datos, Lo que encontramos, El modelo) -> Copa (Explorá, Probá el modelo)

Lee lo que genera `python build_app.py` (app_data/) y el modelo de la Entrega 3 (modelos/).
Correr:  streamlit run app.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import estilo
import modelo_entrega3 as m3
from graficos import model_moves, panorama, pasos, race_cars, race_errors, season_points, tallo

APP_DATA = Path(__file__).resolve().parent / "app_data"
ANIO_TEST = 2026   # lo único que el modelo no vio al entrenar (2018-2025)
# El pipeline de la Entrega 1 vive en este mismo repositorio, en pipeline/.
PIPELINE = "https://github.com/AntoAldao/ciencia_de_datos_grupo_14/tree/main/pipeline"

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

st.set_page_config(page_title="¿La grilla lo dice todo? · F1 · Grupo 14", page_icon="🏁", layout="wide")
estilo.aplicar()


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
abandonos = tabla_nb("Peso de los abandonos")
pct_error_abandonos = float(abandonos.loc["% del error absoluto total que explican"].iloc[0]
                            .replace(",", "."))
pct_filas_abandonos = float(abandonos.loc["% de las filas"].iloc[0].replace(",", "."))

# ----------------------------------------------------------------------------------------------
# PORTADA: la pregunta, la idea central en una oración, tres números.
# ----------------------------------------------------------------------------------------------
# La página es una vuelta al circuito (estilo.py): largada, sectores 1-3, boxes y bandera a cuadros.
estilo.largada(
    "¿Se puede anticipar en qué puesto termina cada piloto de F1 con lo que se sabe antes de "
    "la carrera?",
    "El modelo ordena mejor que la grilla a los pilotos que terminan la carrera, pero los "
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

estilo.piano()

# ----------------------------------------------------------------------------------------------
# TALLO: cada sección = título que afirma + gráfico + «Cómo lo sabemos» (cerrado por defecto).
# ----------------------------------------------------------------------------------------------
# El orden de la consigna: Los datos (Entrega 1) → Lo que encontramos (Entrega 2) → El modelo
# (Entrega 3). Los abandonos no abren el relato: son el límite del modelo, al final.
n_filas, n_carreras = len(df), df["Carrera"].nunique()
pct_dnf = (df["Terminó"] == False).mean()  # noqa: E712
auc_abandonos = next(t for t in notebook if t.startswith("Anticipar abandonos")
                     ).split("AUC medio ")[1].rstrip(")")
filas_crudas = resumen["datos"]["pasos"][0]["filas"]   # «Crudo del pipeline», antes de limpiar
filas_crudas_txt = f"{filas_crudas:,}".replace(",", ".")
corte_anio, corte_fecha = resumen["datos"]["al_dia"].split(", ")   # "2026", "fecha 17"
archivo_datos = resumen["datos"]["archivo"].replace("\\", "/")     # resumen.json puede venir de Windows
hay_practica = df[tallo.FILAS_DATOS[model_moves.FP_PACE]].notna().any(axis=1)
gp_sin_practica = int((~hay_practica.groupby(df["Carrera"]).any()).sum())

# ---- Sector 1 · Los datos (Entrega 1) ------------------------------------------------------------
estilo.sector(1, "Los datos")
st.header(f"Antes de largar, la grilla está siempre; las prácticas faltan en "
          f"{gp_sin_practica} de los {n_carreras} Grandes Premios")
st.altair_chart(tallo.datos_disponibles(df), theme=None)
st.write(f"Cada fila es un piloto en un Gran Premio: {n_filas:,} filas de 2018 a 2026.".replace(",", ".")
         + " Cada casilla es el % de pilotos con ese dato en esa temporada; más lleno, más "
         "completo. Mirá las filas: la largada y la clasificación están casi siempre, el "
         "campeonato falta solo en la primera fecha (todavía no hay puntos), y las prácticas "
         f"tienen huecos en 2018-2019 y 2023-2024 ({hay_practica.mean():.0%} en total). Lo que "
         "siempre está, la grilla, va a ser lo que más pesa.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "**De dónde salen.** Del dataset que produce nuestro pipeline "
        f"de Airflow de la Entrega 1 ([carpeta pipeline]({PIPELINE})) a partir "
        "de las estadísticas estilo Ergast (resultados, clasificación y "
        "campeonato) y la telemetría de FastF1 (prácticas libres): "
        f"{filas_crudas_txt} filas, una por piloto en cada Gran Premio, "
        f"de {int(df['Year'].min())} a {int(df['Year'].max())}, con corte en la "
        f"{corte_fecha} de {corte_anio}. El respaldo es el archivo "
        f"{archivo_datos}, guardado en el repositorio; "
        "build_app.py lo lee de ahí."
    )

    st.markdown(
        "**Qué es una fila.** Un piloto en un Gran Premio. Lo que "
        "queremos predecir es su puesto final en esa carrera."
    )

    st.markdown(
        "**Qué filtramos.** Revisamos los datos paso a paso y "
        "anotamos cuántas filas quedaron después de cada uno:"
    )
    st.dataframe(tabla_nb("Limpieza aplicada"))

    st.markdown(
        "**Qué dejamos afuera.** Todo lo que se conoce recién "
        "después de la carrera (si terminó, en qué estado, cuántas "
        "vueltas perdió, las sanciones) nunca entra al modelo: si "
        "terminó o no lo usamos solo para medir. El campeonato se "
        "toma como estaba antes de cada fecha."
    )

    st.caption(
        "Columnas descartadas por fuga: RACE_Finished, RACE_Status, "
        "RACE_Laps_Down, RACE_Lapped, RACE_DNF_Type y las sanciones."
    )

    st.markdown(
        "**Cómo se arma el gráfico.** Para cada temporada contamos "
        "qué parte de los pilotos tiene cada dato. Un grupo cuenta "
        "como presente si el piloto tiene al menos uno de sus datos, "
        "por ejemplo la vuelta más rápida con alguna de las tres "
        "gomas. Los grupos y sus colores son los mismos que en "
        "«Por qué el modelo mueve a cada piloto»."
    )

    st.caption(
        f"Limitación: en {gp_sin_practica} Grandes Premios no hay "
        "ningún dato de prácticas. El modelo completa los faltantes "
        "con la mediana del entrenamiento y marca que faltaban."
    )

# ---- Sector 2 · Lo que encontramos (Entrega 2) ---------------------------------------------------
estilo.piano()
estilo.sector(2, "Lo que encontramos")
st.header("Quien larga adelante termina adelante: la grilla sola ya ordena buena parte de "
          "la carrera")
col_g, col_t = st.columns([3, 2])
with col_g:
    st.altair_chart(tallo.grilla_vs_final(df), theme=None)
top5 = df[df["Q_GridPosition"] <= 5]
with col_t:
    st.write(f"En {n_carreras} Grandes Premios de 2018 a 2026, de los que largan entre los 5 "
             f"primeros, el **{(top5['Puesto'] <= 5).mean():.0%}** termina entre los 5 primeros. "
             "Mirá la diagonal: casi todos terminan cerca de donde largaron, y los cambios "
             "grandes son la excepción. Por eso la grilla es la referencia que el modelo tiene "
             "que superar.")
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

# ---- Sector 3 · El modelo (Entrega 3) ------------------------------------------------------------
estilo.piano()
estilo.sector(3, "El modelo")
st.header(f"El modelo le gana a la grilla en los que terminan "
          f"({fmt(test['mae_modelo_sin_abandonos'])} contra "
          f"{fmt(test['mae_grilla_sin_abandonos'])} puestos), pero con los abandonos quedan casi "
          f"empatados ({fmt(test['mae_modelo'])} contra {fmt(test['mae_grilla'])})")
st.altair_chart(pasos.grafico_pasos(df, test, anio_test=ANIO_TEST), theme=None)
st.write("Recorré los pasos con los botones de arriba del gráfico. Cada barra cuenta cuántos pilotos "
         "quedaron a esa distancia de su puesto real: en el 0, la predicción acertó. El modelo le "
         "suma a la grilla la clasificación, el campeonato y las prácticas: no acierta más puestos "
         "exactos, pero tiene menos errores grandes. El gráfico arranca en el paso 3: en gris, "
         "los que no terminaron, la cola de la izquierda para los dos.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "**Qué medimos.** El error absoluto medio (MAE) indica cuántos "
        "puestos nos equivocamos en promedio, después de ordenar "
        "a los pilotos de cada carrera. Predecir quinto y terminar "
        "tercero suma dos puestos de error. Menor es mejor."
    )

    st.markdown(
        "**Las referencias.** El piso es una predicción básica que "
        "ubica a todos en la mitad de la clasificación. La referencia "
        "más exigente es la grilla: predecir el orden de llegada "
        "usando únicamente el orden de largada."
    )

    st.markdown(
        "**Cómo validamos.** Evaluamos cada temporada de 2020 a 2025 "
        "entrenando con las otras temporadas de 2018–2025, sin dividir "
        "una misma carrera entre entrenamiento y validación. "
        "Elegimos el modelo y su ajuste con esas pruebas. "
        "Luego entrenamos con 2018–2025 y evaluamos en 2026, "
        "reservado como test."
    )

    st.caption(
        "Limitación: esta validación puede entrenar con temporadas "
        "posteriores a la evaluada. El test de 2026 sí utiliza "
        "únicamente temporadas anteriores para entrenar."
    )

    st.markdown(
        "**Comparación de modelos.** La media resume el error entre "
        "temporadas y el desvío muestra cuánto varía. Elegimos el modelo "
        "lineal por su sencillez y su rendimiento competitivo."
    )
    st.dataframe(tabla_nb("Todos los modelos ajustados"))

    st.caption(f"Modelo seleccionado: {nombre_modelo}.")

    st.markdown(
        f"**Resultado en {ANIO_TEST}.** El modelo y las referencias "
        "se evalúan sobre las mismas carreras:"
    )
    st.dataframe(tabla_nb("Test 2026 ("))

    st.caption(
        "En la evaluación «sin abandonos» se seleccionan quienes "
        "terminaron y se vuelve a ordenar tanto sus predicciones "
        "como sus resultados dentro de cada carrera. No supone "
        "que sepamos de antemano quién va a terminar."
    )

    st.markdown(
        "**Dónde se equivoca.** Con todos los pilotos incluidos, "
        "tiende a ubicar algo más atrás a quienes terminan adelante "
        "y algo más adelante a quienes terminan atrás. "
        "Los abandonos se analizan en la sección siguiente."
    )

    st.markdown(
        "**En qué se apoya.** Estos pesos muestran cómo cada entrada "
        "contribuye al puntaje que usamos para ordenar a los pilotos. "
        "Un peso positivo aumenta ese puntaje y tiende a ubicarlos "
        "más atrás; uno negativo, más adelante, manteniendo "
        "las demás entradas iguales."
    )
    st.dataframe(tabla_nb("Coeficientes del modelo final"))


    st.caption(
        "Los pesos corresponden a variables transformadas y escaladas: "
        "no son puestos ganados o perdidos por cada unidad original "
        "ni demuestran una relación causal."
    )

# Segundo gráfico del sector, a la vista: los abandonos no son una rareza del test.
st.altair_chart(tallo.abandonos_por_temporada(df), theme=None)
anio_mas_abandonos = (df["Terminó"] == False).groupby(df["Year"]).mean().idxmax()  # noqa: E712
st.write(f"Los abandonos no son una rareza: pasan todas las temporadas, en promedio uno de cada "
         f"{round(1 / pct_dnf)} pilotos. "
         + (f"{ANIO_TEST}, el test, es el año con más: son el" if anio_mas_abandonos == ANIO_TEST
            else f"En el test ({ANIO_TEST}) son el")
         + f" {pct_filas_abandonos:.0f}% de los pilotos y explican "
         f"el {pct_error_abandonos:.0f}% del error, y con lo que se sabe antes de la carrera no se "
         f"pueden anticipar (AUC {auc_abandonos}; 0,5 es adivinar): esa parte del error no la baja "
         "ningún modelo con estos datos.")
with st.expander("Cómo lo sabemos"):
    st.markdown(
        "**Cuánto pesan en el error.** Separamos a quienes terminaron "
        "de quienes no terminaron y sumamos sus errores absolutos. "
        "La tabla compara cuántos registros representan y qué parte "
        "del error total concentran en el test."
    )
    st.dataframe(tabla_nb("Peso de los abandonos"))

    st.markdown(
        "**¿Podíamos anticiparlos?** Probamos un clasificador adicional "
        "con datos previos a la carrera y lo evaluamos por temporadas. "
        "Usamos el área bajo la curva ROC (AUC), que mide su capacidad "
        "para distinguir quién termina y quién no: 0,5 equivale "
        "a ordenar al azar y 1 a distinguirlos perfectamente."
    )
    st.dataframe(tabla_nb("Anticipar abandonos"))

    st.markdown(
        f"**Conclusión.** El AUC promedio fue **{auc_abandonos}**: "
        "el clasificador probado mostró poca capacidad para anticipar "
        "los abandonos. Son una limitación de nuestro enfoque."
    )

estilo.piano()
estilo.pit_lane("Tu turno: explorá las carreras y probá el modelo",
                "Hasta acá manejamos nosotros. Desde los boxes manejás vos: recorré todas las "
                "carreras, elegí una temporada y cambiale los datos a un piloto para ver dónde "
                "lo pondría el modelo.")

# ----------------------------------------------------------------------------------------------
# COPA: la maneja el usuario. De lo general a lo particular: todas las carreras → una
# temporada (carrera, campeonato, por qué mueve a cada piloto) → probá el modelo con un piloto.
# ----------------------------------------------------------------------------------------------

st.subheader("Todas las carreras", anchor="todas-las-carreras")
st.altair_chart(panorama.panorama(df, width=450), theme=None)
st.caption("Cada carrera la predice un modelo que no la vio. Elegí una temporada en el menú, "
           "arrastrá sobre la nube para quedarte con un grupo de carreras y hacé clic en la "
           "leyenda para resaltar dónde ganó cada uno.")
st.subheader("Una temporada", anchor="una-temporada")
anios = sorted(df["Year"].unique(), reverse=True)
anio = st.selectbox("Temporada", [int(a) for a in anios])
if anio < ANIO_TEST:
    st.caption(f"Cada carrera de {anio} la predice un modelo que no la vio: el mismo modelo "
               f"elegido, entrenado con las otras temporadas (la validación cruzada por "
               f"temporada del notebook).")
else:
    st.caption(f"{ANIO_TEST} es el test: lo predice el modelo final, entrenado con 2018-2025.")
tabla = tabla_temporada(df, anio)
sub_error, sub_campeonato, sub_autos, sub_porque = st.tabs(
    ["Error por carrera", "Campeonato", "Carrera por carrera", "Por qué el modelo mueve a cada piloto"])
with sub_error:
    st.altair_chart(race_errors.errors_chart(race_errors.race_errors(tabla),
                                             model_name=nombre_modelo, width=980), theme=None)
with sub_campeonato:
    st.altair_chart(season_points.points_chart(season_points.season_points(tabla),
                                               model_name=nombre_modelo, width=980), theme=None)
with sub_autos:
    # HTML propio: lleva el botón «Correr» que anima la carrera.
    st.iframe(race_cars.to_html(race_cars.race_cars_compare(
        tabla, model_name=nombre_modelo, width=1000)))
with sub_porque:
    es_anio = (df["Year"] == anio).to_numpy()
    contrib = model_moves.contributions(
        aportes[es_anio].drop(columns=["Carrera", "DriverId"]), df[es_anio])
    st.altair_chart(model_moves.moves_chart(contrib, model_name=nombre_modelo, width=800), theme=None)

# Al final, lo más chico y lo más interactivo: un piloto en una carrera, con sus datos a mano.
st.subheader("Probá el modelo", anchor="proba-el-modelo")
guardado = modelo()
rangos = resumen["modelo"]["rangos"]
habituales = resumen["modelo"].get("habituales", rangos)
medianas = resumen["modelo"].get("medianas", {})
st.write("Elegí una carrera y un piloto y cambiá lo que hizo antes de largar: el modelo le "
         "vuelve a dar un puntaje y lo ordena contra los demás de esa carrera. Los controles "
         "van del mínimo al máximo que vio el modelo al entrenar, así que no se puede cargar "
         "un valor que nunca vio; si uno queda en el 1 % más raro de cada punta, la app avisa.")
col_a, col_b = st.columns(2)
carrera = col_a.selectbox("Carrera", sorted(df["Carrera"].unique(), reverse=True))
autos = df[df["Carrera"] == carrera].reset_index(drop=True)
piloto = col_b.selectbox("Piloto", sorted(autos["DriverId"]),
                         format_func=lambda d: d.replace("_", " ").title())
i = autos.index[autos["DriverId"] == piloto][0]
clave = f"{carrera}-{piloto}"

# Lo que se puede tocar. El desgaste se carga en % (como lo calcula el modelo) y se convierte
# a la vuelta promedio en segundos, que es lo que recibe el pipeline.
CONTROLES = [
    ("Q_GridPosition", "Posición de largada", 1.0, "%.0f"),
    ("Q_Best_seconds_DBT_%", "Clasificación: % más lenta que la mejor vuelta", 0.05, "%.2f"),
    ("DriverPoints_Before_DBT_%", "Campeonato: % menos de puntos que el líder", 0.5, "%.1f"),
    ("FP_LapTime_min_SOFT_DBT_%", "Prácticas con blanda: % más lenta que la mejor", 0.05, "%.2f"),
    ("FP_LapTime_min_MED_DBT_%", "Prácticas con media: % más lenta que la mejor", 0.05, "%.2f"),
    ("FP_LapTime_min_HARD_DBT_%", "Prácticas con dura: % más lenta que la mejor", 0.05, "%.2f"),
    ("FP_Desgaste_SOFT", "Desgaste con blanda: vuelta promedio vs. mejor (%)", 0.05, "%.2f"),
    ("FP_Desgaste_MED", "Desgaste con media: vuelta promedio vs. mejor (%)", 0.05, "%.2f"),
]
entrena = df[df["conjunto"] == "entrenamiento"]
for goma in ("SOFT", "MED"):   # rangos del desgaste: los mismos criterios que las columnas
    d = entrena[f"FP_Desgaste_{goma}"]
    rangos.setdefault(f"FP_Desgaste_{goma}", [float(d.min()), float(d.max())])
    habituales.setdefault(f"FP_Desgaste_{goma}", [float(d.quantile(.01)), float(d.quantile(.99))])
    medianas.setdefault(f"FP_Desgaste_{goma}", float(d.median()))

caso = autos.copy()
valores, avisos = {}, []
for j, (col, etiqueta, paso, formato) in enumerate(CONTROLES):
    if j % 2 == 0:   # de a dos por fila, para que queden alineados
        cols = st.columns(2)
    lo, hi = rangos[col]
    h_lo, h_hi = habituales[col]
    tope = hi if col == "Q_GridPosition" else min(hi, h_hi * 3)   # las colas de 90 % no sirven en un control
    actual = autos.loc[i, col]
    with cols[j % 2]:
        sin_dato = st.checkbox(f"Sin dato: {etiqueta.split(':')[0].lower()}", value=pd.isna(actual),
                               key=f"nd-{clave}-{col}",
                               help="El modelo completa los faltantes con la mediana del "
                                    "entrenamiento y marca que faltaba.")
        if sin_dato:
            valores[col] = np.nan
            continue
        inicio = medianas.get(col, (lo + hi) / 2) if pd.isna(actual) else float(actual)
        valores[col] = st.slider(etiqueta, float(lo), float(tope), float(np.clip(inicio, lo, tope)),
                                 step=paso, format=formato, key=f"sl-{clave}-{col}")
        if pd.notna(actual) and not lo <= actual <= tope:
            avisos.append(f"**{etiqueta}**: su valor real ({actual:.2f}) está fuera de lo que "
                          "permite el control; se recortó.")
        elif not h_lo <= valores[col] <= h_hi:
            avisos.append(f"**{etiqueta}** = {valores[col]:.2f}: fuera del 98 % central de lo que "
                          f"vio el modelo ({h_lo:.2f} a {h_hi:.2f}). La predicción es menos confiable.")
if avisos:
    st.warning("\n\n".join(avisos))

for col, v in valores.items():
    if col.startswith("FP_Desgaste_"):
        goma = col.removeprefix("FP_Desgaste_")
        mejor = caso.loc[i, f"FP_LapTime_min_{goma}_ABS"]
        if pd.isna(mejor):   # sin vuelta en segundos el modelo no puede calcular el desgaste
            mejor = entrena[f"FP_LapTime_min_{goma}_ABS"].median()
            caso.loc[i, f"FP_LapTime_min_{goma}_ABS"] = mejor
        caso.loc[i, f"FP_LapTime_mean_{goma}_ABS"] = mejor * (1 + v / 100) if pd.notna(v) else np.nan
    else:
        caso.loc[i, col] = v

antes = pd.Series(m3.puntaje(guardado, autos)).rank(method="first")
despues_puntaje = pd.Series(m3.puntaje(guardado, caso))
despues = despues_puntaje.rank(method="first")
k1, k2, k3 = st.columns(3)
k1.metric("Puesto predicho con sus datos reales", int(antes[i]))
k2.metric("Puesto predicho con tus valores", int(despues[i]),
          delta=int(antes[i] - despues[i]) or None, help="positivo = el modelo lo adelanta")
k3.metric("Puntaje (0 = ganador, 1 = último)", fmt(despues_puntaje[i], 3))
st.caption(f"En la realidad terminó {int(autos.loc[i, 'Puesto'])}.º"
           + (" (no terminó la carrera)" if autos.loc[i, "Terminó"] is False
              or str(autos.loc[i, "Terminó"]) == "False" else "") + ".")

estilo.bandera(
    "Bandera a cuadros",
    f"Con lo que se sabe antes de largar, el modelo ordena a los que terminan mejor que la grilla "
    f"({fmt(test['mae_modelo_sin_abandonos'])} contra {fmt(test['mae_grilla_sin_abandonos'])} "
    f"puestos de error). Pero uno de cada {round(1 / pct_dnf)} pilotos no termina, y eso nadie lo "
    f"ve venir: con los abandonos, quedan casi empatados ({fmt(test['mae_modelo'])} contra "
    f"{fmt(test['mae_grilla'])}).",
    pie=f"Ciencia de Datos · UTN FRM · 2026 · Grupo 14 · Datos del pipeline de la Entrega 1, al "
        f"día: {resumen['datos']['al_dia']}.")
