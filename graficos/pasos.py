"""Sector 3 · El modelo, contado en pasos: una copa de martini dentro de un gráfico.

Es la estructura de la sección 7.9 de la práctica de Altair: el paso es un PARÁMETRO atado a unos
botones (`binding_radio`), y cada capa declara en qué paso se ve. El gráfico no cambia: cambian los
valores que las capas leen.

    Datos:           una fila por piloto y predicción (grilla o modelo) con su error en puestos.
    Transformación:  error = puesto predicho − puesto real, redondeado y recortado a ±15; después
                     `count()` por error, predicción y estado (terminó / abandonó).
    Marca:           barras (mark_bar), agrupadas por predicción con `xOffset`; texto como capa.
    Mapeo:           error -> x (ordinal), cantidad -> y, predicción -> xOffset y color.
                     En el paso 3 el color pasa a ser "abandonó" para los que no terminaron.
    Escalas:         ejes fijos en todos los pasos (para que el gráfico no salte) y los colores de
                     graficos/colores.py: azul = modelo, naranja = grilla, gris = abandono.

Pasos:
    1 · La grilla       solo la grilla: la mayoría termina cerca de donde largó.
    2 · El modelo       aparece el modelo: un poco más concentrado en el 0.
    3 · Los abandonos   (por defecto) los que no terminaron son la cola de la izquierda.
    4 · Explorá         menú de temporada y casilla para sacar los abandonos.
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

from graficos import colores as C

TOPE = 15          # errores más grandes se acumulan en ±15
PASOS = ["1 · La grilla", "2 · El modelo", "3 · Los abandonos", "4 · Explorá"]


def _mae(err: pd.Series) -> float:
    return float(err.abs().mean())


def errores(pred: pd.DataFrame) -> pd.DataFrame:
    """Una fila por piloto y predicción, con el error en puestos (como `medir` del notebook)."""
    d = pred[["Year", "Carrera", "DriverId", "Puesto", "puesto_modelo", "Q_GridPosition",
              "Terminó"]].copy()
    car = d["Carrera"]
    real = d["Puesto"].groupby(car).rank(method="average")
    grilla = d["Q_GridPosition"].fillna(21).groupby(car).rank(method="average")
    d["termino"] = d["Terminó"].fillna(True).astype(bool)
    largo = pd.concat([
        d.assign(quien="Grilla", error=(grilla - real).to_numpy()),
        d.assign(quien="Modelo", error=(d["puesto_modelo"] - real).to_numpy()),
    ], ignore_index=True)
    largo["error_bin"] = np.clip(np.round(largo["error"]), -TOPE, TOPE).astype(int)
    largo["estado"] = np.where(largo["termino"], "Terminó", "Abandonó")
    return largo


def resumen_por_temporada(largo: pd.DataFrame) -> pd.DataFrame:
    """MAE con y sin abandonos, por temporada y predicción, para los textos del gráfico."""
    filas = []
    for anio, g in largo.groupby("Year"):
        fila = {"Year": int(anio)}
        for quien in ["Grilla", "Modelo"]:
            q = g[g["quien"] == quien]
            fila[f"mae_{quien}"] = _mae(q["error"])
            fila[f"pct_aband_{quien}"] = q.loc[~q["termino"], "error"].abs().sum() / q["error"].abs().sum()
        fila["abandonos"] = int((~g[g["quien"] == "Modelo"]["termino"]).sum())
        fila["pilotos"] = int((g["quien"] == "Modelo").sum())
        filas.append(fila)
    return pd.DataFrame(filas)


def grafico_pasos(pred: pd.DataFrame, test: dict, anio_test: int = 2026,
                  width: int = 760, height: int = 330) -> alt.LayerChart:
    """El histograma de errores contado en cuatro pasos. `test` es resumen["test"] de build_app."""
    largo = errores(pred)
    conteo = (largo.groupby(["Year", "quien", "estado", "error_bin"]).size()
              .rename("pilotos").reset_index())
    por_anio = resumen_por_temporada(largo)

    # ---- parámetros: el paso (botones) y, para el paso 4, temporada y abandonos ----------------
    paso = alt.param(name="paso", value=3, bind=alt.binding_radio(
        options=[1, 2, 3, 4], labels=PASOS, name="Paso: "))
    anios = sorted(int(a) for a in conteo["Year"].unique())
    anio = alt.param(name="anio", value=anio_test, bind=alt.binding_select(
        options=anios, name="Temporada (paso 4): "))
    sin_ab = alt.param(name="sin_ab", value=False, bind=alt.binding_checkbox(
        name="Sacar los abandonos (paso 4) "))

    # ---- escalas fijas: el gráfico no salta al cambiar de paso ---------------------------------
    # 30 % de aire arriba: ahí va el relato
    y_max = float(conteo.groupby(["Year", "quien", "error_bin"])["pilotos"].sum().max()) * 1.3
    x = alt.X("error_bin:O", title="Error de la predicción, en puestos (negativo = lo puso más adelante de lo que terminó)",
              scale=alt.Scale(domain=list(range(-TOPE, TOPE + 1))),
              axis=alt.Axis(labelAngle=0, values=list(range(-TOPE, TOPE + 1, 5)), **C.EJES))
    y = alt.Y("sum(pilotos):Q", title="Pilotos", scale=alt.Scale(domain=[0, y_max]),
              axis=alt.Axis(**C.EJES), stack="zero")
    color = alt.Color("grupo:N", title=None,
                      scale=alt.Scale(domain=["Grilla", "Modelo", "Abandonó"],
                                      range=[C.GRILLA, C.MODELO, C.ABANDONO]),
                      legend=alt.Legend(orient="top", labelColor=C.INK, symbolType="square"))

    # ---- barras: qué filas entran en cada paso y de qué color van ------------------------------
    barras = alt.Chart(conteo).transform_filter(
        # pasos 1-3: el test; paso 4: la temporada elegida
        f"(paso < 4 && datum.Year == {anio_test}) || (paso == 4 && datum.Year == anio)"
    ).transform_filter(
        "paso >= 2 || datum.quien == 'Grilla'"                      # paso 1: solo la grilla
    ).transform_filter(
        "!(paso == 4 && sin_ab && datum.estado == 'Abandonó')"     # paso 4: sin abandonos
    ).transform_calculate(
        grupo="paso >= 3 && datum.estado == 'Abandonó' ? 'Abandonó' : datum.quien",
        orden="datum.estado == 'Abandonó' ? 1 : 0",
    ).mark_bar(width=alt.RelativeBandSize(0.9), cornerRadiusEnd=1).encode(
        x=x, xOffset=alt.XOffset("quien:N", scale=alt.Scale(domain=["Grilla", "Modelo"])),
        y=y, color=color, order=alt.Order("orden:Q"),
        tooltip=[alt.Tooltip("quien:N", title="Predicción"),
                 alt.Tooltip("error_bin:O", title="Error (puestos)"),
                 alt.Tooltip("grupo:N", title="Grupo"),
                 alt.Tooltip("sum(pilotos):Q", title="Pilotos")])

    cero = alt.Chart(pd.DataFrame({"error_bin": [0]})).mark_rule(
        color=C.INK, strokeDash=[3, 3], opacity=0.6).encode(x="error_bin:O")

    # ---- el relato: un texto por paso, como capa (sección 7.5) ---------------------------------
    t = test
    f = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    pct = 1 - t["mae_modelo_sin_abandonos"] / t["mae_modelo"]
    relato = pd.DataFrame([
        {"paso": 1, "linea": 0, "texto": f"Usar la largada como predicción: erra {f(t['mae_grilla'])} puestos en promedio."},
        {"paso": 1, "linea": 1, "texto": "La mayoría termina cerca de donde largó: la grilla ya es una buena predicción."},
        {"paso": 2, "linea": 0, "texto": f"El modelo suma clasificación, campeonato y prácticas: erra {f(t['mae_modelo'])}."},
        {"paso": 2, "linea": 1, "texto": "Tiene más pilotos en el 0 que la grilla… pero el promedio casi no baja. ¿Por qué?"},
        {"paso": 3, "linea": 0, "texto": "En gris, los que no terminaron: son la cola de la izquierda, para los dos."},
        {"paso": 3, "linea": 1, "texto": f"Sin ellos, el modelo erra {f(t['mae_modelo_sin_abandonos'])} y la grilla "
                                          f"{f(t['mae_grilla_sin_abandonos'])}: los abandonos tapaban la ventaja."},
    ])
    texto = alt.Chart(relato).transform_filter("datum.paso == paso").mark_text(
        align="left", baseline="top", fontSize=14, color=C.INK
    ).transform_calculate(px="8 + datum.linea * 22").encode(
        x=alt.value(8), y=alt.Y("px:Q", scale=None), text="texto:N")

    # paso 4: el texto sale de la temporada elegida
    por_anio = por_anio.assign(
        l0=lambda d: "Temporada " + d["Year"].astype(str) + ": el modelo erra " + d["mae_Modelo"].map(f)
                     + " y la grilla " + d["mae_Grilla"].map(f) + " puestos.",
        l1=lambda d: d["abandonos"].astype(str) + " abandonos de " + d["pilotos"].astype(str)
                     + " pilotos, que explican el " + (d["pct_aband_Modelo"] * 100).round().astype(int).astype(str)
                     + " % del error del modelo.")
    texto4 = alt.Chart(por_anio.melt(id_vars="Year", value_vars=["l0", "l1"], var_name="l", value_name="texto")
                       ).transform_filter("paso == 4 && datum.Year == anio").transform_calculate(
        linea="datum.l == 'l0' ? 0 : 1").mark_text(
        align="left", baseline="top", fontSize=14, color=C.INK
    ).transform_calculate(px="8 + datum.linea * 22").encode(
        x=alt.value(8), y=alt.Y("px:Q", scale=None), text="texto:N")

    return alt.layer(barras, cero, texto, texto4).add_params(paso, anio, sin_ab).properties(width=width, height=height).configure(
        background=C.ASPHALT, padding={"left": 16, "right": 16, "top": 16, "bottom": 8}
    ).configure_view(stroke=None, fill=C.ASPHALT).configure_text(font="sans-serif")
