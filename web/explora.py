"""«Explorá los datos»: la parte de la copa para recorrer los datos crudos (no el modelo).

Seis partes que maneja `web/explora.js`:

1. Récords y rarezas: datos llamativos calculados acá, cada uno con un link a la vista que lo muestra.
2. Pilotos, cara a cara: ficha de uno o comparación de dos.
3. Armá tu gráfico: el usuario elige tipo de gráfico, ejes, color, filtros y escala.
4. Todo conectado: tres gráficos que se filtran entre sí.
5. La carrera de las escuderías: ranking de podios que avanza temporada por temporada.
6. ¿Quién gana?: elegir el podio de una carrera real y compararlo con la grilla y con el modelo.

Los gráficos fijos (2, 4 y 5) se arman con Altair (`specs()`) sobre un dato con nombre («t»); la página
los dibuja una sola vez y después solo les cambia los datos y los parámetros, que es lo que los hace
rápidos. «Armá tu gráfico» arma su spec de Vega-Lite en el navegador, porque cambia de forma según
lo que elige el usuario. Todo lo que se elige queda en el link (`#v=armar&tipo=…`).
"""
from __future__ import annotations

import html
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd

from graficos import carreras, logos
from graficos import colores as C

WEB = Path(__file__).resolve().parent
ROJO, TINTA, BEIGE = "#E10600", "#1F2328", "#D6CCBA"

# variables que se pueden cruzar: clave -> (texto, unidad)
NUM = {
    "largada": ("Puesto de largada", "puesto"), "clasif": ("Puesto en la clasificación", "puesto"),
    "final": ("Puesto final", "puesto"), "ganados": ("Puestos ganados en carrera", "puestos"),
    "q_dbt": ("Clasificación: % más lento que la pole", "%"),
    "fp_soft": ("Prácticas con blandas: % más lento que el mejor", "%"),
    "fp_med": ("Prácticas con medias: % más lento que el mejor", "%"),
    "fp_hard": ("Prácticas con duras: % más lento que el mejor", "%"),
    "desg_soft": ("Desgaste con blandas (%)", "%"), "desg_med": ("Desgaste con medias (%)", "%"),
    "vmax": ("Velocidad máxima en prácticas (km/h)", "km/h"),
    "pts": ("Puntos antes de la carrera", "puntos"), "pos_camp": ("Puesto en el campeonato", "puesto"),
    "dist_lider": ("Distancia al líder del campeonato (%)", "%"),
    "llegada_prev": ("Carreras terminadas antes (%)", "%"),
    "abandono": ("Abandonos (%)", "%"), "vueltas_menos": ("Vueltas perdidas contra el ganador", "vueltas"),
}
CAT = {"anio": "Temporada", "equipo": "Escudería", "piloto": "Piloto", "resultado": "Resultado",
       "tipo_ab": "Cómo terminó", "zona": "Zona de largada", "gp": "Gran Premio"}
TIPOS_ABANDONO = {"desconocido": "Sin detalle", "mecanica": "Mecánica", "accidente": "Accidente",
                  "no_largo": "No largó", "otro": "Otro", "descalificacion": "Descalificado"}


# ---- datos ---------------------------------------------------------------------------------------
def tabla(p: pd.DataFrame) -> pd.DataFrame:
    """Una fila por piloto en cada GP, con nombres cortos y en castellano (`app_data/predicciones`)."""
    d = pd.DataFrame()
    d["anio"] = p.Year.astype(int)
    d["ronda"] = p.RoundNumber.astype(int)
    d["car"] = p.Carrera
    d["gp"] = [carreras.corto(a, r) for a, r in zip(d.anio, d.ronda)]
    d["gpl"] = [carreras.nombre(a, r) for a, r in zip(d.anio, d.ronda)]
    d["piloto"] = p.DriverId.str.replace("_", " ").str.title()
    d["equipo"] = p.TeamId.map(logos.nombre)
    d["largada"] = p.Q_GridPosition
    d["clasif"] = p.Q_Position
    d["final"] = p.Puesto
    d["ganados"] = p.Q_GridPosition - p.Puesto
    d["q_dbt"] = p["Q_Best_seconds_DBT_%"]
    d["fp_soft"] = p["FP_LapTime_min_SOFT_DBT_%"]
    d["fp_med"] = p["FP_LapTime_min_MED_DBT_%"]
    d["fp_hard"] = p["FP_LapTime_min_HARD_DBT_%"]
    d["desg_soft"] = p.FP_Desgaste_SOFT
    d["desg_med"] = p.FP_Desgaste_MED
    d["vmax"] = p.FP_Speed_max_ABS.replace(0, np.nan)
    d["pts"] = p.DriverPoints_Before
    d["pos_camp"] = p.DriverPosition_Before.replace(0, np.nan)
    d["dist_lider"] = p["DriverPoints_Before_DBT_%"]
    d["llegada_prev"] = p.FinishRate_Before * 100
    termino = p["Terminó"].astype(bool)
    d["abandono"] = np.where(termino, 0, 100)
    d["resultado"] = np.where(termino, "Terminó", "Abandonó")
    d["tipo_ab"] = p.RACE_DNF_Type.map(TIPOS_ABANDONO).fillna("Terminó")
    d["vueltas_menos"] = p.RACE_Laps_Down
    d["zona"] = pd.cut(p.Q_GridPosition, [0, 5, 10, 15, 30],
                       labels=["1–5", "6–10", "11–15", "16 o más"]).astype(str)
    d["pm"] = p.puesto_modelo.round().astype(int)        # dónde lo ponía el modelo (para «¿Quién gana?»)
    d["estado"] = p.RACE_Status.astype(str)
    return d


def filas_json(d: pd.DataFrame) -> list[dict]:
    """Las filas como lista de diccionarios, con None en lugar de NaN y números redondeados."""
    salida = []
    for r in d.itertuples(index=False):
        fila = {}
        for k, v in r._asdict().items():
            if isinstance(v, (float, np.floating)):
                fila[k] = None if pd.isna(v) else round(float(v), 3)
            elif isinstance(v, np.integer):
                fila[k] = int(v)
            else:
                fila[k] = v
        salida.append(fila)
    return salida


def records(d: pd.DataFrame) -> list[dict]:
    """Récords y rarezas. `ver` dice a qué vista lleva el botón «Ver» (mismo formato que el link)."""
    fin = d.resultado == "Terminó"
    limpio = d.estado.isin(["Finished", "Lapped"])       # llegó a la bandera (sin abandonos ni sanciones)
    rec = []

    def quien(f) -> str:
        return f"{f.piloto} ({f.equipo}) en el {f.gpl} {f.anio}"

    ganadores = d[d.final == 1]
    f = ganadores.loc[ganadores.largada.idxmax()]
    rec.append({"t": "La victoria desde más atrás", "n": f"{int(f.largada)}.º",
                "x": f"{quien(f)}: largó {int(f.largada)}.º y ganó.", "ver": {"v": "pilotos", "a": f.piloto}})
    f = d[fin].loc[d[fin].ganados.idxmax()]
    rec.append({"t": "La mayor remontada", "n": f"+{int(f.ganados)}",
                "x": f"{quien(f)}: largó {int(f.largada)}.º y terminó {int(f.final)}.º.",
                "ver": {"v": "armar", "tipo": "dispersion", "x": "largada", "y": "final", "color": "resultado",
                        "pi": f.piloto}})
    f = d[limpio].loc[d[limpio].ganados.idxmin()]
    rec.append({"t": "La peor caída llegando al final", "n": f"{int(f.ganados)}",
                "x": f"{quien(f)}: largó {int(f.largada)}.º y terminó {int(f.final)}.º.",
                "ver": {"v": "pilotos", "a": f.piloto}})
    ab = d.groupby(["car", "gpl", "anio"]).abandono.agg(lambda s: int((s > 0).sum())).reset_index()
    f = ab.loc[ab.abandono.idxmax()]
    rec.append({"t": "La carrera con más abandonos", "n": str(int(f.abandono)),
                "x": f"El {f.gpl} {f.anio}: {int(f.abandono)} autos no llegaron al final.",
                "ver": {"v": "armar", "tipo": "barras", "x": "tipo_ab", "y": "abandono", "medida": "count",
                        "desde": int(f.anio), "hasta": int(f.anio), "re": "Abandonó"}})
    pole = d[d.largada == 1]
    pct_pole = (pole.final == 1).mean() * 100
    rec.append({"t": "Lo que vale la pole", "n": f"{pct_pole:.0f}%",
                "x": f"El que larga primero gana el {pct_pole:.0f}% de las veces. Desde fuera del podio de "
                     f"largada sale solo el {(ganadores.largada > 3).mean() * 100:.0f}% de las victorias.",
                "ver": {"v": "armar", "tipo": "calor", "x": "largada", "y": "final"}})
    g = d[fin].groupby("piloto").agg(n=("ganados", "size"), m=("ganados", "mean"))
    g = g[g.n >= 30].sort_values("m")
    rec.append({"t": "El que más puestos gana en carrera", "n": f"+{g.m.iloc[-1]:.1f}",
                "x": f"{g.index[-1]} gana {g.m.iloc[-1]:.1f} puestos por carrera en promedio, entre los que "
                     "corrieron al menos 30.",
                "ver": {"v": "armar", "tipo": "barras", "x": "piloto", "y": "ganados", "medida": "mean",
                        "re": "Terminó"}})
    a = d.groupby("piloto").agg(n=("abandono", "size"), m=("abandono", "mean"))
    a = a[a.n >= 30].sort_values("m")
    rec.append({"t": "El que más abandona", "n": f"{a.m.iloc[-1]:.0f}%",
                "x": f"{a.index[-1]} no terminó el {a.m.iloc[-1]:.0f}% de sus {int(a.n.iloc[-1])} carreras.",
                "ver": {"v": "pilotos", "a": a.index[-1]}})
    victorias = d[d.final == 1].piloto.value_counts()
    rec.append({"t": "El que más ganó", "n": str(int(victorias.iloc[0])),
                "x": f"{victorias.index[0]} ganó {int(victorias.iloc[0])} de las {d.car.nunique()} carreras de "
                     f"{d.anio.min()} a {d.anio.max()}.",
                "ver": {"v": "pilotos", "a": victorias.index[0], "b": victorias.index[1]}})
    e = d.groupby(["equipo", "anio"]).final.mean().unstack()
    salto = e.diff(axis=1).stack().dropna()
    k = salto.abs().idxmax()
    rec.append({"t": "El cambio más brusco de una escudería", "n": f"{abs(salto[k]):.1f}",
                "x": f"{k[0]} pasó de un puesto final promedio de {e.loc[k[0], k[1] - 1]:.1f} en {k[1] - 1} "
                     f"a {e.loc[k[0], k[1]]:.1f} en {k[1]}.",
                "ver": {"v": "armar", "tipo": "evolucion", "y": "final", "color": "equipo", "medida": "mean",
                        "eq": k[0]}})
    podios = d[(d.final <= 3) & (d.largada >= 15)]
    ultimo = podios.sort_values(["anio", "ronda"]).iloc[-1]
    rec.append({"t": "Podios desde el fondo", "n": str(len(podios)),
                "x": f"Veces que alguien largó 15.º o más atrás y terminó en el podio. La última: {quien(ultimo)}.",
                "ver": {"v": "armar", "tipo": "dispersion", "x": "largada", "y": "final", "color": "zona",
                        "zo": "16 o más"}})
    return rec


# ---- gráficos fijos (Altair) ---------------------------------------------------------------------
def _sin_datos(spec: dict) -> dict:
    """Altair guarda los datos con nombre en `datasets`; la página los pone con `view.data("t", …)`."""
    spec.pop("datasets", None)
    return spec


def specs(d: pd.DataFrame, colores_equipo: dict[str, str]) -> dict[str, dict]:
    t = alt.NamedData("t")
    anios = sorted(int(a) for a in d.anio.unique())
    equipos = sorted(d.equipo.unique())
    escala_eq = alt.Scale(domain=equipos, range=[colores_equipo.get(e, "#9AA0A6") for e in equipos])

    # 2 · puesto final promedio del piloto elegido (rojo) y del rival (negro)
    pa = alt.param(name="pa", value="")
    pilotos = alt.Chart(t).mark_line(point=alt.OverlayMarkDef(size=60), strokeWidth=3).encode(
        x=alt.X("anio:O", title="Temporada", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("mean(final):Q", title="Puesto final promedio", scale=alt.Scale(reverse=True, zero=False)),
        color=alt.condition("datum.piloto === pa", alt.value(ROJO), alt.value(TINTA)),
        detail="piloto:N",
        tooltip=[alt.Tooltip("piloto:N", title="Piloto"), alt.Tooltip("anio:O", title="Temporada"),
                 alt.Tooltip("mean(final):Q", title="Puesto final promedio", format=".1f"),
                 alt.Tooltip("count():Q", title="Carreras")],
    ).add_params(pa).properties(width="container", height=260)

    # 4 · tres gráficos que se filtran entre sí (el filtro lo arma la página y les pasa los datos)
    sel_anio = alt.param(name="selAnio", value=-1)
    abandonos = alt.Chart(t).mark_bar(cornerRadiusEnd=3, cursor="pointer").encode(
        x=alt.X("anio:O", title=None, axis=alt.Axis(labelAngle=0), scale=alt.Scale(domain=anios)),
        y=alt.Y("mean(abandono):Q", title="% que abandonó"),
        color=alt.condition("selAnio === -1 || datum.anio === selAnio", alt.value(ROJO), alt.value(BEIGE)),
        tooltip=[alt.Tooltip("anio:O", title="Temporada"),
                 alt.Tooltip("mean(abandono):Q", title="% que abandonó", format=".1f"),
                 alt.Tooltip("count():Q", title="Resultados")],
    ).add_params(sel_anio).properties(width="container", height=200)

    rango = alt.selection_interval(name="rango", encodings=["x"])
    diagonal = pd.DataFrame({"a": [1, 20], "b": [1, 20]})
    largada_final = alt.layer(
        alt.Chart(t).mark_line(point=alt.OverlayMarkDef(size=45), color=TINTA, strokeWidth=2.5).encode(
            x=alt.X("largada:Q", title="Puesto de largada", scale=alt.Scale(domain=[0.5, 20.5], nice=False),
                    axis=alt.Axis(values=list(range(1, 21, 2)), format="d")),
            y=alt.Y("mean(final):Q", title="Puesto final promedio", scale=alt.Scale(domain=[20, 1])),
            tooltip=[alt.Tooltip("largada:Q", title="Largó"),
                     alt.Tooltip("mean(final):Q", title="Terminó, en promedio", format=".1f"),
                     alt.Tooltip("count():Q", title="Resultados")],
        ).add_params(rango),
        alt.Chart(diagonal).mark_line(strokeDash=[4, 4], color="#B9AE9A").encode(x="a:Q", y="b:Q"),
        alt.Chart(diagonal.tail(1).assign(t="si todos terminaran donde largaron")).mark_text(
            align="right", dx=-4, dy=-8, color="#8A7F6C", fontSize=12, fontStyle="italic",
        ).encode(x="a:Q", y="b:Q", text="t:N"),
    ).properties(width="container", height=220)

    sel_eq = alt.param(name="selEq", value="")
    remontada = alt.Chart(t).mark_bar(cornerRadiusEnd=3, cursor="pointer").encode(
        y=alt.Y("equipo:N", title=None, sort="-x"),
        x=alt.X("mean(ganados):Q", title="Puestos ganados por carrera (promedio)"),
        color=alt.Color("equipo:N", legend=None, scale=escala_eq),
        opacity=alt.condition("selEq === '' || datum.equipo === selEq", alt.value(1), alt.value(.2)),
        tooltip=[alt.Tooltip("equipo:N", title="Escudería"),
                 alt.Tooltip("mean(ganados):Q", title="Puestos ganados", format=".2f"),
                 alt.Tooltip("count():Q", title="Resultados")],
    ).add_params(sel_eq).properties(width="container", height=alt.Step(20))

    # 5 · ranking de podios; `orden` y `tope` los pone la página en cada temporada
    tope = alt.param(name="tope", value=int(d[d.final <= 3].groupby(["anio", "equipo"]).size().max()) + 2)
    base = alt.Chart(t).encode(
        y=alt.Y("equipo:N", sort=alt.EncodingSortField("orden", op="min"), title=None,
                axis=alt.Axis(labelFontSize=14, labelFontWeight=700, domain=False, ticks=False, minExtent=120)),
        x=alt.X("podios:Q", title="Podios", scale=alt.Scale(domain=[0, alt.ExprRef("tope")])),
    )
    movimiento = alt.layer(
        base.mark_bar(cornerRadiusEnd=4).encode(
            color=alt.Color("equipo:N", legend=None, scale=escala_eq),
            tooltip=[alt.Tooltip("equipo:N", title="Escudería"), alt.Tooltip("podios:Q", title="Podios")]),
        base.mark_text(align="left", dx=6, fontSize=14, fontWeight=900, fontStyle="italic", color=TINTA
                       ).encode(text="podios:Q"),
    ).add_params(tope).properties(width="container", height=alt.Step(34))

    graficos = {"pilotos": pilotos, "conA": abandonos, "conB": largada_final, "conC": remontada,
                "movimiento": movimiento}
    return {k: _sin_datos(g.configure_view(stroke=None).configure(background="transparent").to_dict())
            for k, g in graficos.items()}


# ---- lo que va en la página ----------------------------------------------------------------------
def armar(predicciones: pd.DataFrame) -> tuple[str, dict, dict]:
    """Devuelve (marcado HTML, datos que van comprimidos, configuración) de «Explorá los datos»."""
    d = tabla(predicciones)
    colores_equipo = {logos.nombre(t): c for t, c in C.ESCUDERIAS.items()}
    config = {
        "num": NUM, "cat": CAT,
        "cortes": {k: [float(d[k].quantile(.01)), float(d[k].quantile(.99))] for k in NUM},
        "records": records(d), "equipos": colores_equipo, "specs": specs(d, colores_equipo),
        "colores": {"modelo": C.MODELO, "grilla": C.GRILLA, "abandono": C.ABANDONO, "tinta": TINTA, "rojo": ROJO},
    }
    n = f"{len(d):,}".replace(",", ".")
    marcado = (WEB / "explora.html").read_text(encoding="utf-8").replace(
        "{n_filas}", html.escape(n)).replace("{desde}", str(d.anio.min())).replace("{hasta}", str(d.anio.max()))
    return f'<div class="explora" id="explora-los-datos">{marcado}</div>', filas_json(d), config
