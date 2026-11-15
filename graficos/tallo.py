"""Gráficos del tallo que no vienen de los otros módulos: Los datos y Lo que encontramos.

`vueltas_ejemplo`: cómo sale la mejor vuelta con cada goma, con las vueltas de prácticas de un piloto (Los datos).
`seleccion_columnas`: de los datos que arma el pipeline a los 8 del modelo, y por qué sale cada
    grupo (Los datos).
`datos_disponibles`: qué se sabe de cada piloto antes de largar (Los datos).
`grilla_vs_final` y `grilla_vs_final_sin_abandonos`: la grilla manda (Lo que encontramos), con
    todos los pilotos y solo con los que terminaron, con sus notas adentro;
    `cifras_grilla`, los números de esas notas y de la tabla de «Cómo lo sabemos».
`abandonos_por_temporada`: cuántos no terminan (en «Cómo lo sabemos» del modelo).

Mismo estilo que el resto de la app (fondo oscuro) y mismos colores con el mismo significado:
gris = no terminó (como en `race_errors`), ámbar = la grilla (como en `season_points`).
"""

from __future__ import annotations

import json

import altair as alt
import pandas as pd

from graficos import colores as C

from graficos import model_moves as mm
from graficos.race_cars import ASPHALT, INK, INK_MUTED, LANE
from graficos.race_errors import DNF_COLOR

GRID_ORANGE = C.GRILLA
FRANJAS = [(1, 5, "1–5"), (6, 10, "6–10"), (11, 15, "11–15"), (16, 99, "16 o más")]
AXIS = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LANE, domainColor=LANE,
            tickColor=LANE)


def _estilo(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    return chart.configure(background=ASPHALT, padding=16).configure_view(
        stroke=None, fill=ASPHALT).configure_text(font=C.FUENTE)


def _franja(puesto: pd.Series) -> pd.Series:
    etiqueta = pd.Series("16 o más", index=puesto.index)
    for lo, hi, nombre in FRANJAS:
        etiqueta[(puesto >= lo) & (puesto <= hi)] = nombre
    return etiqueta


# Qué se sabe antes de largar: la largada y los grupos de variables del modelo, con los mismos
# nombres y colores que «Por qué el modelo mueve a cada piloto» (model_moves) y la grilla en ámbar.
FILAS_DATOS = {"Largada (grilla)": [mm.GRID],
               **{g: cols for g, cols in mm.GROUPS.items() if g != mm.FINISH}}


def disponibilidad(df: pd.DataFrame) -> pd.DataFrame:
    """% de pilotos-carrera con dato en cada grupo (al menos una de sus columnas), por temporada."""
    filas = []
    for fila, cols in FILAS_DATOS.items():
        hay = df[cols].notna().any(axis=1)
        t = hay.groupby(df["Year"]).agg(["mean", "sum", "size"]).reset_index()
        filas.append(t.rename(columns={"mean": "pct", "sum": "con_dato", "size": "filas"})
                     .assign(fila=fila))
    return pd.concat(filas, ignore_index=True)


# Qué hace el modelo cuando falta cada dato (app_data/modelo.json: «relleno» y las columnas
# «missingindicator_»). Ninguna fila se descarta por un faltante.
QUE_SE_HACE = {
    "Largada (grilla)": "Si falta (largó desde boxes), se lo\npone 21.º: detrás de toda la grilla.",
    mm.CHAMP: "Falta en la 1.ª fecha (nadie tiene\npuntos): valor típico + marca de\nque faltaba.",
    mm.QUALY: "Si no marcó tiempo: valor típico\n+ marca de que faltaba.",
    mm.FP_PACE: "Si no giró con esa goma: valor típico\n+ marca de que faltaba (no usarla\ntambién dice algo).",
    mm.FP_WEAR: "Igual que la vuelta más rápida:\nvalor típico + marca de que faltaba.",
}


def datos_disponibles(df: pd.DataFrame, width: int = 400) -> alt.TopLevelMixin:
    """Qué se sabe de cada piloto antes de largar: % con dato por grupo y temporada, y qué hace
    el modelo cuando falta.

    Datos: una fila por grupo y temporada (`disponibilidad`). Marca: rectángulo + texto.
    Mapeo: temporada -> x, grupo -> y, % con dato -> opacidad (más lleno = más completo) y texto.
    Un solo color para todas las filas, así se comparan entre sí. Escala de opacidad de 50% a
    100%: debajo de la mitad no hay ningún grupo, y así se ven los huecos. A la derecha de cada
    fila, qué se hace con los faltantes (`QUE_SE_HACE`)."""
    t = disponibilidad(df)
    orden = list(FILAS_DATOS)
    faltan = [f for f in orden if f not in QUE_SE_HACE]
    assert not faltan, f"falta decir qué se hace con los faltantes de: {faltan}"
    tooltip = [alt.Tooltip("fila:N", title="Dato"), alt.Tooltip("Year:O", title="Temporada"),
               alt.Tooltip("pct:Q", title="% con dato", format=".0%"),
               alt.Tooltip("con_dato:Q", title="Pilotos-carrera con dato"),
               alt.Tooltip("filas:Q", title="Pilotos-carrera")]
    y = alt.Y("fila:N", sort=orden, title=None, axis=alt.Axis(labelLimit=320, labelFontSize=13, **AXIS))
    base = alt.Chart(t).encode(
        x=alt.X("Year:O", title=None, axis=alt.Axis(labelAngle=0, orient="top", **AXIS)), y=y)
    celdas = base.mark_rect(stroke=ASPHALT, strokeWidth=3, cornerRadius=3, color=C.MODELO).encode(
        opacity=alt.Opacity("pct:Q", scale=alt.Scale(domain=[0.5, 1], range=[0.06, 0.55]),
                            legend=None),
        tooltip=tooltip)
    texto = base.mark_text(fontSize=13, color=INK).encode(
        text=alt.Text("pct:Q", format=".0%"), tooltip=tooltip)
    notas = alt.Chart(pd.DataFrame({"fila": orden, "t": [QUE_SE_HACE[f] for f in orden]})).mark_text(
        align="left", baseline="middle", lineBreak="\n", fontSize=13, lineHeight=16, color=INK
    ).encode(y=y, x=alt.value(width + 18), text="t:N")
    encabezado = alt.Chart(pd.DataFrame({"t": ["Si falta, qué hace el modelo"]})).mark_text(
        align="left", baseline="bottom", fontSize=13, fontWeight=700, color=INK
    ).encode(x=alt.value(width + 18), y=alt.value(-8), text="t:N")
    return _estilo(alt.layer(celdas, texto, notas, encabezado).properties(
        width=width, height=60 * len(orden),
        title=alt.Title("Qué datos faltan y qué hacemos con los faltantes", anchor="start", fontSize=19,
                        color=INK, offset=14,
                        subtitle="% de pilotos con cada dato, por temporada. Más lleno, más completo.",
                        subtitleColor=INK_MUTED, subtitleFontSize=14))).configure_title(font=C.FUENTE)


# ---- De las vueltas sueltas a la tabla: la mejor vuelta con cada goma (Los datos) ---------------------
GOMAS = [("SOFT", "Blandas", "#DA291C"), ("MEDIUM", "Medias", "#F2C300"), ("HARD", "Duras", "#F4F4F4")]
MOTIVOS = ["Entrada o salida de boxes", "Bandera o auto de seguridad",
           "Tiempo poco confiable o incompleto", "Anulada por los comisarios", "Goma sin identificar",
           "Más de 5 % más lenta que su mejor con esa goma"]


MOTIVOS_CORTOS = {"Tiempo poco confiable o incompleto": "Tiempo poco confiable",
                  "Más de 5 % más lenta que su mejor con esa goma": "Más de 5 % más lenta que su mejor"}


def _reloj(seg: float, decimales: int = 3) -> str:
    """90.229 -> «1:30,229» (como se leen los tiempos de vuelta)."""
    m, s_ = divmod(seg, 60)
    return f"{int(m)}:{s_:0{3 + decimales}.{decimales}f}".replace(".", ",")


def cifras_vueltas(ej: dict) -> dict:
    """Los números del texto del ejemplo: cuántas vueltas, por qué salen y qué queda por goma."""
    v = pd.DataFrame(ej["vueltas"])
    quedan = v[v["motivo"].isna()]
    por_goma = {}
    for goma, nombre, _ in GOMAS:
        t = quedan.loc[quedan["goma"] == goma, "tiempo"]
        if len(t):
            por_goma[goma] = {"nombre": nombre, "n": len(t), "mejor": float(t.min()),
                              "promedio": float(t.mean()),
                              "desgaste": float((t.mean() - t.min()) / t.min() * 100)}
    return {"total": len(v), "quedan": len(quedan),
            "motivos": v["motivo"].value_counts().to_dict(), "por_goma": por_goma,
            "piloto": ej["piloto"], "gran_premio": ej["gran_premio"]}


def vueltas_ejemplo(ej: dict, width: int = 360) -> alt.TopLevelMixin:
    """Todas las vueltas de prácticas de un piloto en un GP: cuáles descarta el pipeline y por qué,
    y con cuáles calcula la mejor vuelta y el promedio de cada goma.

    Datos: app_data/ejemplo_vueltas.json (web/ejemplo_vueltas.py, con los filtros del pipeline).
    Marca: un punto por vuelta. Mapeo: tiempo -> x (las muy lentas se apilan en el borde
    derecho, con un triángulo), motivo o goma -> y, goma -> color (gris = descartada).
    A la derecha, la mejor vuelta y el promedio de cada goma: los dos datos que pasan a la tabla."""
    c = cifras_vueltas(ej)
    v = pd.DataFrame(ej["vueltas"]).dropna(subset=["tiempo"]).reset_index(drop=True)
    nombres = {g: n for g, n, _ in GOMAS}
    v["fila"] = v["motivo"].where(v["motivo"].notna(), v["goma"].map(nombres))
    mejor = min(x["mejor"] for x in c["por_goma"].values())
    tope = mejor * 1.11
    v["x"] = v["tiempo"].clip(upper=tope)
    v["recortada"] = v["tiempo"] > tope
    v["tiempo_txt"] = v["tiempo"].map(_reloj)
    v["estado"] = v["motivo"].fillna("Queda")
    v["es_mejor"] = False
    for goma, x in c["por_goma"].items():
        v.loc[(v["motivo"].isna()) & (v["goma"] == goma) & (v["tiempo"] == x["mejor"]), "es_mejor"] = True

    conteo = c["motivos"]
    filas = [m for m in MOTIVOS if conteo.get(m)] + [n for g, n, _ in GOMAS if g in c["por_goma"]]
    etiqueta = {m: f"{MOTIVOS_CORTOS.get(m, m)} ({conteo[m]})" for m in MOTIVOS if conteo.get(m)}
    etiqueta.update({x["nombre"]: f"{x['nombre']} ({x['n']})" for x in c["por_goma"].values()})
    # cada fila es un número (0 arriba); dentro de la fila los puntos se corren un poco para no taparse
    n_fila = {f: k for k, f in enumerate(filas)}
    v["yy"] = v["fila"].map(n_fila) + (v.groupby("fila").cumcount() % 5 - 2) * 0.09
    expr = " : ".join(f"datum.value == {k} ? {json_str(etiqueta[f])}" for f, k in n_fila.items()) + " : ''"
    escala_y = alt.Scale(domain=[-0.6, len(filas) - 0.4], reverse=True, nice=False, zero=False)
    y = alt.Y("yy:Q", title=None, scale=escala_y,
              axis=alt.Axis(values=list(range(len(filas))), labelExpr=expr, labelLimit=260,
                            labelFontSize=13, domain=False, ticks=False, grid=False, labelColor=INK))
    x = alt.X("x:Q", title="Tiempo de la vuelta", scale=alt.Scale(domain=[mejor * 0.995, tope], nice=False),
              axis=alt.Axis(labelExpr="floor(datum.value / 60) + ':' + (datum.value % 60 < 10 ? '0' : '') "
                                      "+ format(datum.value % 60, '.0f')", **AXIS))
    color = alt.Color("goma:N", legend=None, scale=alt.Scale(
        domain=[g for g, _, _ in GOMAS], range=[col for _, _, col in GOMAS]))
    tooltip = [alt.Tooltip("sesion:N", title="Sesión"), alt.Tooltip("vuelta:Q", title="Vuelta"),
               alt.Tooltip("goma:N", title="Goma"), alt.Tooltip("tiempo_txt:N", title="Tiempo"),
               alt.Tooltip("estado:N", title="¿Queda?")]
    base = alt.Chart(v).encode(x=x, y=y, tooltip=tooltip)
    descartadas = base.transform_filter("datum.motivo != null").mark_point(
        size=55, filled=False, strokeWidth=1.3, color=C.ABANDONO).encode(
        shape=alt.condition("datum.recortada", alt.value("triangle-right"), alt.value("circle")))
    quedan = base.transform_filter("datum.motivo == null").mark_point(
        size=70, filled=True, opacity=1, stroke=INK, strokeWidth=0.8).encode(color=color)
    anillo = base.transform_filter("datum.es_mejor").mark_point(
        size=330, filled=False, strokeWidth=2.2, color=INK)

    # a la derecha de cada goma: la mejor vuelta y el promedio (los dos datos que quedan)
    txt = pd.DataFrame([{"yy": n_fila[x["nombre"]],
                         "t": f"mejor {_reloj(x['mejor'])} · promedio {_reloj(x['promedio'])}"}
                        for x in c["por_goma"].values()])
    lado = alt.Chart(txt).mark_text(align="left", baseline="middle", fontSize=14, fontWeight=600,
                                    color=INK).encode(y=y, x=alt.value(width + 14), text="t:N")
    # línea punteada entre lo que se descarta y lo que queda
    corte = alt.Chart(pd.DataFrame({"yy": [len(filas) - len(c["por_goma"]) - 0.5]})).mark_rule(
        color=INK, strokeDash=[4, 3], opacity=0.5).encode(y=y, x=alt.value(-240), x2=alt.value(width + 280))
    grafico = alt.layer(descartadas, quedan, anillo, lado, corte).properties(
        width=width, height=40 * len(filas),
        title=alt.Title(f"Cómo sale la mejor vuelta con cada goma: {c['piloto'].capitalize()} en el "
                        f"{c['gran_premio']}", anchor="start", fontSize=19, color=INK, offset=14,
                        subtitle=[f"Cada punto es una de sus {c['total']} vueltas en las tres prácticas "
                                  "(las que no tienen tiempo no se dibujan; las muy lentas, con un "
                                  "triángulo en el borde derecho).", "En gris, las que se descartan y por qué; en color, las que "
                                  "quedan. El anillo marca la mejor con cada goma."],
                        subtitleColor=INK_MUTED, subtitleFontSize=14, subtitlePadding=6))
    return _estilo(grafico).configure_title(font=C.FUENTE)


def json_str(x: str) -> str:
    return json.dumps(x, ensure_ascii=False)


# ---- De 67 datos a 8: qué columnas descartamos y por qué (Los datos) ------------------------------
# Cada columna que arma el pipeline cae en una sola fila: o se descarta por un motivo, o queda.
# Los motivos salen del EDA (Entrega 2): fuga, identificadores (cambian con la era), ABS vs DBT,
# H3 (telemetría), H4 (contexto), redundancia, vueltas promedio y falta de datos.
_ABS_TIEMPOS = ["Q1_seconds_ABS", "Q2_seconds_ABS", "Q3_seconds_ABS", "Q_Best_seconds_ABS",
                *[f"FP_LapTime_{m}_{g}_ABS" for m in ["min", "mean"] for g in ["SOFT", "MED", "HARD"]]]
_TELEMETRIA = [f"FP_{c}_{v}" for c in ["Throttle_fastlap", "Speed_fastlap", "Speed_max", "RPM_fastlap",
                                       "Brake_fastlap", "Throttle_mean_MED", "Speed_mean_MED",
                                       "RPM_mean_MED", "Brake_mean_MED"] for v in ["ABS", "DBT_%"]]
DESCARTES = [   # (qué es, por qué sale, columnas)
    ("El puesto final", "es la respuesta: lo que queremos predecir", ["RACE_Position"]),
    ("Lo que pasa en la carrera", "si terminó, abandonos, vueltas perdidas, sanciones: no se sabe antes",
     ["RACE_Finished", "RACE_Status", "RACE_Laps_Down", "RACE_Lapped", "RACE_DNF_Type",
      "RACE_Penalty_Seconds", "RACE_Penalty_Positions_Lost"]),
    ("Quién es", "piloto, dorsal y equipo: la fuerza de cada uno cambia de un año a otro",
     ["DriverId", "DriverNumber", "TeamId"]),
    ("Tiempos en segundos", "dependen del largo del circuito: usamos el % más lento que el mejor",
     _ABS_TIEMPOS),
    ("Telemetría de prácticas", "acelerador, velocidad, motor, freno: descontada la grilla, no agrega",
     _TELEMETRIA),
    ("Contexto de la fecha", "año, fecha, carreras corridas: casi no se relaciona con el resultado",
     ["Year", "RoundNumber", "Races_Before", "FinishRate_Before", "Avg_Position_Gain_Before"]),
    ("Repiten a otro dato", "tandas de la qualy, puntos del equipo, largar desde boxes",
     ["Q_Position", "Q1_seconds_DBT_%", "Q2_seconds_DBT_%", "Q3_seconds_DBT_%",
      "DriverPosition_Before", "DriverPoints_Before", "DriverPoints_Rate_Before",
      "TeamPosition_Before", "TeamPoints_Before", "Q_PitLaneStart"]),
    ("Vueltas promedio de prácticas", "dicen menos que la mejor vuelta",
     [f"FP_LapTime_mean_{g}_DBT_%" for g in ["SOFT", "MED", "HARD"]]),
    ("Prácticas con lluvia", "gomas intermedias y de lluvia: faltan en 9 de cada 10 filas",
     ["FP_LapTime_min_INTER_ABS", "FP_LapTime_min_INTER_DBT_%", "FP_LapTime_min_WET_ABS",
      "FP_LapTime_min_WET_DBT_%"]),
]
QUEDAN = ["Q_GridPosition", "Q_Best_seconds_DBT_%", "DriverPoints_Before_DBT_%",
          "FP_LapTime_min_SOFT_DBT_%", "FP_LapTime_min_MED_DBT_%", "FP_LapTime_min_HARD_DBT_%"]
CALCULADAS = ["FP_Desgaste_SOFT", "FP_Desgaste_MED"]   # las calcula el modelo con las vueltas en segundos


def columnas_del_pipeline() -> list[str]:
    """Todas las columnas que arma el pipeline, cada una una sola vez (descartadas + las que quedan)."""
    todas = [c for _, _, cols in DESCARTES for c in cols] + QUEDAN
    assert len(todas) == len(set(todas)), "una columna está en dos motivos"
    return todas


def seleccion_columnas(df: pd.DataFrame, width: int = 300) -> alt.TopLevelMixin:
    """Cascada de columnas: de las que arma el pipeline a las que usa el modelo.

    Datos: una fila por paso (el total, cada motivo de descarte, las que quedan y las
    calculadas). Marca: barra horizontal de `desde` a `hasta` (cuántas columnas quedan antes y
    después de cada paso) y, a la derecha, el texto con el motivo. Mapeo: paso -> y (en orden de
    lectura), columnas -> x. Color: gris = sale, azul (el del modelo en toda la app) = entra."""
    todas = columnas_del_pipeline()
    faltan = [c for c in todas if c not in df.columns]
    assert not faltan, f"columnas que ya no están en los datos: {faltan}"
    total = len(todas)

    filas, quedan = [], total
    filas.append({"paso": "total", "desde": 0, "hasta": total, "tipo": "total",
                  "titulo": f"{total} datos por piloto y carrera",
                  "detalle": "los que juntamos: resultados, qualy, campeonato y prácticas"})
    for nombre, porque, cols in DESCARTES:
        filas.append({"paso": nombre, "desde": quedan - len(cols), "hasta": quedan, "tipo": "sale",
                      "titulo": f"−{len(cols)}  {nombre}", "detalle": porque})
        quedan -= len(cols)
    assert quedan == len(QUEDAN)
    filas.append({"paso": "quedan", "desde": 0, "hasta": quedan, "tipo": "entra",
                  "titulo": f"Quedan {quedan}",
                  "detalle": "grilla, mejor vuelta de qualy, puntos vs. el líder, mejor vuelta por goma"})
    filas.append({"paso": "calculadas", "desde": quedan, "hasta": quedan + len(CALCULADAS),
                  "tipo": "calculada", "titulo": f"+{len(CALCULADAS)}  calculadas: {quedan + len(CALCULADAS)} en el modelo",
                  "detalle": "desgaste de gomas blandas y medias (vuelta promedio vs. la mejor)"})
    t = pd.DataFrame(filas)
    orden = t["paso"].tolist()
    alto_fila = 44
    y = alt.Y("paso:N", sort=orden, axis=None, scale=alt.Scale(paddingInner=0.3))
    x = alt.X("desde:Q", title=None, scale=alt.Scale(domain=[0, total]), axis=None)
    tipos = ["total", "sale", "entra", "calculada"]
    barras = alt.Chart(t).mark_bar(cornerRadius=2).encode(
        y=y, x=x, x2="hasta:Q",
        color=alt.Color("tipo:N", legend=None, scale=alt.Scale(
            domain=tipos, range=[INK_MUTED, C.ABANDONO, C.MODELO, C.MODELO])),
        opacity=alt.Opacity("tipo:N", legend=None, scale=alt.Scale(domain=tipos, range=[0.55, 0.45, 1, 0.5])),
        tooltip=[alt.Tooltip("titulo:N", title="Paso"), alt.Tooltip("detalle:N", title="Por qué")])
    # el texto, a la derecha de todas las barras: título arriba y motivo abajo, en la misma fila
    texto = alt.Chart(t).encode(y=y, x=alt.value(width + 16))
    titulo = texto.mark_text(align="left", baseline="bottom", dy=1, fontSize=15, fontWeight=700,
                             color=INK).encode(text="titulo:N")
    detalle = texto.mark_text(align="left", baseline="top", dy=3, fontSize=14,
                              color=INK_MUTED).encode(text="detalle:N")
    # línea que separa los descartes de lo que queda
    corte = alt.Chart(pd.DataFrame({"paso": ["quedan"]})).mark_rule(
        color=INK, strokeDash=[4, 3], opacity=0.5).encode(
        y=alt.Y("paso:N", sort=orden, axis=None, bandPosition=0, scale=alt.Scale(paddingInner=0.3)),
        yOffset=alt.value(-8), x=alt.value(0), x2=alt.value(width + 560))
    return _estilo(alt.layer(barras, titulo, detalle, corte).properties(
        width=width, height=alto_fila * len(orden),
        title=alt.Title(f"De {total} datos a los {quedan + len(CALCULADAS)} del modelo", anchor="start",
                        fontSize=19, color=INK, offset=14))).configure_title(font=C.FUENTE)


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
    etiquetas = base.mark_text(dy=-7, color=INK, fontSize=13).encode(
        y="pct:Q", text=alt.Text("pct:Q", format=".0%"))
    linea = alt.Chart(pd.DataFrame({"y": [promedio]})).mark_rule(
        color=INK_MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    texto = alt.Chart(pd.DataFrame({"y": [promedio], "t": [f"promedio {promedio:.0%}"]})).mark_text(
        align="left", dx=4, dy=-6, color=INK_MUTED, fontSize=13).encode(
        y="y:Q", x=alt.value(0), text="t:N")
    return _estilo(alt.layer(barras, etiquetas, linea, texto).properties(width=width, height=260))


LINEA_PX = 19      # alto de una línea de las notas del gráfico, en píxeles


def _nota(texto: str, x: float, y: float, **estilo) -> alt.Chart:
    """Texto en píxeles del gráfico (no en datos): `y` es el borde de arriba de la primera línea."""
    return alt.Chart(pd.DataFrame({"t": [texto]})).mark_text(
        align="left", baseline="top", lineBreak="\n", fontSize=15, lineHeight=LINEA_PX, color=INK,
        **estilo).encode(x=alt.value(x), y=alt.value(y), text="t:N")


def _trazo(x: float, x2: float, y: float, y2: float, ancho: float = 1.8) -> alt.Chart:
    return alt.Chart(pd.DataFrame({"a": [0]})).mark_rule(color=INK, strokeWidth=ancho).encode(
        x=alt.value(x), x2=alt.value(x2), y=alt.value(y), y2=alt.value(y2))


def _punta(x: float, y: float, forma: str) -> alt.Chart:
    return alt.Chart(pd.DataFrame({"a": [0]})).mark_point(
        shape=forma, size=90, filled=True, opacity=1, color=INK).encode(x=alt.value(x), y=alt.value(y))


def _cruce(df: pd.DataFrame) -> pd.DataFrame:
    """Cuántos de los que largan en cada franja terminan en cada franja, y qué % de su fila son."""
    d = pd.DataFrame({"largada": _franja(df["Q_GridPosition"].fillna(99)),
                      "final": _franja(df["Puesto"])})
    t = d.value_counts().rename("n").reset_index()
    t["pct"] = t["n"] / t.groupby("largada")["n"].transform("sum")
    return t


def _mapa(t: pd.DataFrame, width: int, con_antes: bool = False) -> tuple[alt.Chart, list[alt.Chart]]:
    """El mapa de calor (casillas, % y recuadros), igual en los dos gráficos: mismas franjas y
    misma escala de color, así se comparan. Con `con_antes`, la diagonal muestra abajo, entre
    paréntesis, el % con todos los pilotos (columna `antes`)."""
    orden = [f[2] for f in FRANJAS]
    tooltip = [alt.Tooltip("largada:N", title="Largó"), alt.Tooltip("final:N", title="Terminó"),
               alt.Tooltip("n:Q", title="Pilotos-carrera"),
               alt.Tooltip("pct:Q", title="% de los que largaron ahí", format=".0%")]
    base = alt.Chart(t).encode(
        y=alt.Y("largada:N", sort=orden, title="Largó en el puesto", axis=alt.Axis(**AXIS)),
        x=alt.X("final:N", sort=orden, title="Terminó en el puesto",
                axis=alt.Axis(labelAngle=0, orient="bottom", **AXIS)))
    celdas = base.mark_rect(stroke=ASPHALT, strokeWidth=2).encode(
        color=alt.Color("pct:Q", scale=alt.Scale(range=["#FBF3E6", GRID_ORANGE], domain=[0, 0.8]),
                        legend=None), tooltip=tooltip)
    blanco = alt.condition("datum.pct > 0.45", alt.value("#FFFFFF"), alt.value(INK))
    capas = [celdas]
    if con_antes:
        diagonal = "datum.largada == datum.final"
        capas += [base.transform_filter(f"!({diagonal})").mark_text(fontSize=17).encode(
                      text=alt.Text("pct:Q", format=".0%"), color=blanco),
                  base.transform_filter(diagonal).mark_text(fontSize=17, dy=-8).encode(
                      text=alt.Text("pct:Q", format=".0%"), color=blanco),
                  base.transform_filter(diagonal).transform_calculate(
                      antes_txt="'(' + format(datum.antes, '.0%') + ')'").mark_text(
                      fontSize=13, dy=12).encode(text="antes_txt:N", color=blanco)]
    else:
        capas.append(base.mark_text(fontSize=17).encode(text=alt.Text("pct:Q", format=".0%"), color=blanco))

    # Qué mirar: el recuadro lleno es donde la grilla casi no falla (largan y terminan entre los
    # 5 primeros); los punteados, la diagonal del medio, donde la carrera mezcla más.
    def marco(celdas_: list[str], **trazo) -> alt.Chart:
        return base.transform_filter(
            alt.FieldOneOfPredicate(field="largada", oneOf=celdas_)
        ).transform_filter("datum.largada == datum.final").mark_rect(
            fill=None, stroke=INK, **trazo)
    capas += [marco(["1–5"], strokeWidth=4), marco(["6–10", "11–15"], strokeWidth=2.5, strokeDash=[6, 4])]
    return base, capas


def _flecha_arriba(texto: str, width: int) -> list[alt.Chart]:
    """Nota arriba del mapa con una flecha que baja al recuadro de los 5 primeros."""
    lineas = texto.count("\n") + 1
    celda_x = width / 4
    y_texto = -(lineas * LINEA_PX + 34)
    return [_nota(texto, 0, y_texto, fontWeight=600),
            _trazo(celda_x / 2, celda_x / 2, y_texto + lineas * LINEA_PX + 4, -12),
            _punta(celda_x / 2, -7, "triangle-down")]


def _llave(width: int, alto: float, fila_desde: int, fila_hasta: int,
           bloques: list[tuple[str, int] | None]) -> list[alt.Chart]:
    """Llave a la derecha del mapa que abarca las filas [fila_desde, fila_hasta) (0 = la de arriba)
    y, al lado, el texto: bloques (texto, peso de la letra); None deja un renglón de aire."""
    celda_y = alto / 4
    x0, y0, y1 = width + 14, fila_desde * celda_y + 6, fila_hasta * celda_y - 6
    lineas = sum(1 if b is None else b[0].count("\n") + 1 for b in bloques)
    y = (y0 + y1) / 2 - lineas * LINEA_PX / 2
    capas = [_trazo(x0, x0, y0, y1), _trazo(x0 - 7, x0, y0, y0), _trazo(x0 - 7, x0, y1, y1)]
    for b in bloques:
        if b is None:
            y += LINEA_PX
            continue
        capas.append(_nota(b[0], x0 + 18, y, fontWeight=b[1]))
        y += (b[0].count("\n") + 1) * LINEA_PX
    return capas


def _titulo(titulo: str, subtitulo: str) -> alt.Title:
    return alt.Title(titulo, subtitle=subtitulo, anchor="start", fontSize=19, color=INK, offset=16,
                     subtitleColor=INK_MUTED, subtitleFontSize=14, subtitlePadding=4)


def grilla_vs_final(df: pd.DataFrame, width: int = 400) -> alt.TopLevelMixin:
    """De los que largan en cada franja de la grilla, en qué franja terminan (% por fila), con
    todos los pilotos.

    Las notas van adentro del gráfico y señalan de qué parte hablan: una flecha al recuadro de
    los 5 primeros (arriba) y una llave a las filas del 6.º para atrás (a la derecha)."""
    _, capas = _mapa(_cruce(df), width)
    c = cifras_grilla(df)
    pct = lambda x: f"{x:.0%}".replace("%", " %")  # noqa: E731
    f = lambda x: f"{x:.2f}".replace(".", ",")  # noqa: E731
    e = c["error"]
    alto = width * 0.75

    arriba = (f"Adelante, la grilla casi no falla: de los que\nlargan 1.º a 5.º, el "
              f"{pct(c['se_queda']['1–5'])} termina entre los 5\nprimeros. El que larga primero "
              f"gana el {pct(c['gana_pole'])}\nde las carreras.")

    # A la derecha: llave que abarca las filas del 6.º para atrás
    notas_derecha = _llave(width, alto, 1, 4, [   # renglones cortos: tiene que entrar en 1366 px
        ("Del 6.º para atrás, la carrera mezcla:", 700),
        (f"en la diagonal punteada, solo el {pct(c['se_queda']['6–10'])}\ny el "
         f"{pct(c['se_queda']['11–15'])} terminan en la franja en la\nque largaron; el resto se "
         "reparte\npara los dos lados.", 400),
        None,
        ("Ahí está el margen para mejorar\nla grilla, y ahí el modelo le gana:", 700),
        (f"con los que largan 11.º a 15.º erra\n{f(e['11–15']['Modelo'])} puestos y la grilla "
         f"{f(e['11–15']['Grilla'])}. Con los\n5 primeros quedan parejos "
         f"({f(e['1–5']['Modelo'])}\ncontra {f(e['1–5']['Grilla'])}).", 400),
    ])

    n_txt = f"{c['n_todos']:,}".replace(",", ".")
    grafico = alt.layer(*capas, *_flecha_arriba(arriba, width), *notas_derecha).properties(
        width=width, height=alto, title=_titulo("Todos los pilotos", f"{n_txt} pilotos-carrera"))
    return _estilo(grafico).configure_title(font=C.FUENTE)


def grilla_vs_final_sin_abandonos(df: pd.DataFrame, width: int = 400) -> alt.TopLevelMixin:
    """El mismo cruce contando solo a los que terminaron la carrera. En la diagonal, entre
    paréntesis, el % con todos los pilotos, para comparar sin ir y volver."""
    termino = df["Terminó"].fillna(True).astype(bool)
    t = _cruce(df[termino])
    todos = _cruce(df).set_index(["largada", "final"])["pct"]
    t["antes"] = [todos.get((a, b), 0.0) for a, b in zip(t["largada"], t["final"])]
    _, capas = _mapa(t, width, con_antes=True)
    c = cifras_grilla(df)
    pct = lambda x: f"{x:.0%}".replace("%", " %")  # noqa: E731
    q = c["se_queda_terminaron"]
    arriba = (f"Sin abandonos, adelante sube: de los que\nlargan 1.º a 5.º, el {pct(q['1–5'])} termina "
              "entre los 5\nprimeros. Entre paréntesis, el mismo % con\ntodos los pilotos (el otro mapa).")
    alto = width * 0.75
    notas_derecha = [
        *_llave(width, alto, 1, 3, [
            ("En el medio, también se oscurece:", 700),
            (f"{pct(q['6–10'])} y {pct(q['11–15'])} terminan en la franja en la\nque largaron (con "
             f"todos, {pct(c['se_queda']['6–10'])} y {pct(c['se_queda']['11–15'])}).\nMucho de lo que "
             "«mezclaba» la\ncarrera eran abandonos.", 400)]),
        *_llave(width, alto, 3, 4, [
            ("Atrás es al revés:", 700),
            (f"baja de {pct(c['se_queda']['16 o más'])} a {pct(q['16 o más'])}: los últimos\npuestos "
             "eran de los que abandonaron.", 400)]),
    ]
    n_txt = f"{c['n_terminaron']:,}".replace(",", ".")
    ab_txt = f"{c['n_todos'] - c['n_terminaron']:,}".replace(",", ".")
    grafico = alt.layer(*capas, *_flecha_arriba(arriba, width), *notas_derecha).properties(
        width=width, height=alto,
        title=_titulo("Sin los que abandonaron", f"{n_txt} que terminaron (salen {ab_txt} abandonos)"))
    return _estilo(grafico).configure_title(font=C.FUENTE)


def cifras_grilla(df: pd.DataFrame) -> dict:
    """Los números del texto de «Lo que encontramos», de las mismas filas que el gráfico."""
    from graficos import pasos   # errores por piloto (grilla y modelo), como en el Sector 3

    largada = _franja(df["Q_GridPosition"].fillna(99))
    final = _franja(df["Puesto"])
    termino = df["Terminó"].fillna(True).astype(bool)
    se_queda = {f: float((final[largada == f] == f).mean()) for _, _, f in FRANJAS}
    se_queda_terminaron = {f: float((final[(largada == f) & termino] == f).mean()) for _, _, f in FRANJAS}
    top5_termina = float((final[(largada == "1–5") & termino] == "1–5").mean())
    pole = df["Q_GridPosition"] == 1
    gana_pole = float((df.loc[pole, "Puesto"] == 1).mean())

    largo = pasos.errores(df)
    largo["franja"] = _franja(largo["Q_GridPosition"].fillna(99)).to_numpy()
    mae = largo.assign(ae=largo["error"].abs()).groupby(["franja", "quien"])["ae"].mean()
    error = {f: {q: float(mae[(f, q)]) for q in ["Grilla", "Modelo"]} for _, _, f in FRANJAS}
    return {"se_queda": se_queda, "top5_termina": top5_termina, "gana_pole": gana_pole,
            "se_queda_terminaron": se_queda_terminaron, "n_todos": len(df),
            "n_terminaron": int(termino.sum()),
            "carreras": int(df["Carrera"].nunique()), "ultimo_anio": int(df["Year"].max()),
            "error": error, "n_por_franja": largada.value_counts().to_dict()}
