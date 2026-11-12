"""Visualización "autitos": largada → predicción del modelo → resultado real (Altair).

Vista superior de una pista oscura con un carril por posición (P1 arriba):

- izquierda: orden de largada (grilla),
- centro: los autos avanzan; la distancia horizontal de cada uno al líder pasa suavemente de la
  formación de largada (compacta, `GRID_STEP` puestos entre autos) a la que da el puntaje
  continuo del modelo (ej. 8.18 − 2.88 = 5.3 puestos detrás). El carril es la posición en ese
  momento: al pasar a otro auto se cambia de carril con una animación corta, y cada auto deja
  una estela con su recorrido,
- derecha: posición final real.

La **distancia horizontal entre autos** al llegar muestra qué tan seguro está el modelo del orden:
autos pegados = duda (se marcan con una franja), autos separados = orden claro. La interpolación la
hace Vega en el navegador a partir de un slider; los cruces (cuándo pasa cada auto) se calculan
en Python (`lane_paths`).

Uso (con las predicciones que guarda `build_app.py`, columna `score`):

    from graficos import race_cars
    table = race_cars.race_table(predicciones_de_una_temporada)
    chart = race_cars.race_cars_compare(table)        # dos pistas: modelo y ajustada
    html = race_cars.to_html(chart)                     # con botón "Correr"
"""

from __future__ import annotations

import json
from pathlib import Path
import altair as alt
import numpy as np
import pandas as pd

from graficos import colores as C

RACE_COLS = ["Year", "RoundNumber"]

# Colores aproximados de cada escudería (identidad del equipo; los compañeros comparten color,
# por eso cada auto lleva su sigla).
TEAM_COLORS = C.ESCUDERIAS
DEFAULT_COLOR = C.ESCUDERIA_DEFECTO

# Siglas oficiales que no salen de las 3 primeras letras del apellido.
DRIVER_CODES = {
    "max_verstappen": "VER", "mick_schumacher": "MSC", "de_vries": "DEV",
    "brendon_hartley": "HAR", "kevin_magnussen": "MAG",
}

# Paleta de la "pista" (tema oscuro fijo: es una escena, no un gráfico de fondo claro).
ASPHALT, LANE, INK, INK_MUTED = C.ASPHALT, C.LANE, C.INK, C.INK_MUTED
DOUBT = "#FFD54A"

# Coordenadas horizontales del gráfico (la pista va de 0 a 1; textos afuera) y siluetas en
# [-1, 1] mirando a la derecha.
X_LEFT = 0.05      # último auto de la grilla al largar
X_END = 0.76       # líder al llegar
FIELD_SPAN = 0.5   # ancho que ocupa el pelotón al llegar (del líder al más lejano)
GRID_STEP = 0.3    # separación en la formación de largada, en puestos (compacta)
LANE_CHANGE = 0.04  # duración de un cambio de carril, como fracción del avance
X_DG, X_DM, X_PCT = 1.32, 1.46, 1.60   # columnas Δ grilla, Δ modelo y mejora (borde derecho)
RACE_LAPS = 58     # vueltas supuestas por carrera (el dataset no trae el total)
CRASH_MAX = 0.9    # el choque más tardío (ej. descalificados con 0 vueltas de desventaja)
NO_CRASH = 2.0     # `crash_s` de quien no choca (fuera de 0..1)
CRASH_GRAY = "#6B6F76"
GOOD = C.MEJOR   # el modelo acierta mejor que la grilla (con ▲)
BAD = C.PEOR    # el modelo acierta peor que la grilla (con ▼)
CAR_BODY = ("M -1 -0.16 L 0.55 -0.11 L 1 -0.04 L 1 0.04 L 0.55 0.11 L -1 0.16 Z "
            "M 0.78 -0.42 L 0.94 -0.42 L 0.94 0.42 L 0.78 0.42 Z "
            "M -1 -0.36 L -0.82 -0.36 L -0.82 0.36 L -1 0.36 Z "
            "M -0.2 -0.2 L 0.2 -0.2 L 0.2 0.2 L -0.2 0.2 Z")
CAR_WHEELS = ("M -0.72 -0.42 L -0.42 -0.42 L -0.42 -0.2 L -0.72 -0.2 Z "
              "M -0.72 0.2 L -0.42 0.2 L -0.42 0.42 L -0.72 0.42 Z "
              "M 0.38 -0.38 L 0.62 -0.38 L 0.62 -0.18 L 0.38 -0.18 Z "
              "M 0.38 0.18 L 0.62 0.18 L 0.62 0.38 L 0.38 0.38 Z")


# --- Tonos de compañeros: mismo color del equipo, uno un poco más claro y otro más oscuro ---
# Se cambia solo la luminosidad en OKLab (espacio perceptual), así el tono no se corre hacia el
# de otro equipo. Cada equipo puede desplazar su par hacia arriba o abajo (`SHADE_MAX_OFFSET`)
# para alejarse de los equipos parecidos (ej. los azules de 2025).
SHADE_DELTA = 0.045       # mitad de la diferencia de luminosidad entre compañeros
SHADE_MAX_OFFSET = 0.045  # cuánto puede correrse el par de un equipo

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])


def _hex_to_oklab(hex_color: str) -> np.ndarray:
    c = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return _M2 @ np.cbrt(_M1 @ lin)


def _oklab_to_rgb(lab: np.ndarray) -> np.ndarray:
    lin = np.linalg.solve(_M1, (np.linalg.solve(_M2, lab)) ** 3)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)


def shift_lightness(hex_color: str, d_l: float) -> str:
    """Mismo tono con la luminosidad OKLab corrida `d_l` (baja el croma si no entra en sRGB)."""
    lab = _hex_to_oklab(hex_color)
    for k in np.linspace(1, 0, 41):
        rgb = _oklab_to_rgb(np.array([lab[0] + d_l, lab[1] * k, lab[2] * k]))
        if (rgb > -1e-4).all() and (rgb < 1 + 1e-4).all():
            break
    return "#" + "".join(f"{int(round(c * 255)):02X}" for c in np.clip(rgb, 0, 1))


def _color_distance(h1: str, h2: str) -> float:
    return float(100 * np.linalg.norm(_hex_to_oklab(h1) - _hex_to_oklab(h2)))


def team_palette(team_ids: list[str], delta: float = SHADE_DELTA,
                 max_offset: float = SHADE_MAX_OFFSET) -> dict[tuple[str, int], str]:
    """Colores de los dos autos de cada equipo: `(equipo, 0)` más claro, `(equipo, 1)` más oscuro.

    Elige el corrimiento de cada equipo (entre ±`max_offset`) que maximiza la distancia mínima
    entre autos de equipos distintos (búsqueda por coordenadas, determinista)."""
    teams = sorted(set(team_ids))
    offsets = np.round(np.linspace(-max_offset, max_offset, 9), 4)
    cache = {(t, o, k): shift_lightness(TEAM_COLORS.get(t, DEFAULT_COLOR), o + (delta if k == 0 else -delta))
             for t in teams for o in offsets for k in (0, 1)}

    def colors(off: dict[str, float]) -> dict[tuple[str, int], str]:
        return {(t, k): cache[(t, off[t], k)] for t in teams for k in (0, 1)}

    def worst(cols: dict[tuple[str, int], str]) -> float:
        pairs = [(a, b) for i, a in enumerate(cols) for b in list(cols)[i + 1:] if a[0] != b[0]]
        return min((_color_distance(cols[a], cols[b]) for a, b in pairs), default=np.inf)

    zero = offsets[len(offsets) // 2]
    off = {t: zero for t in teams}
    best = worst(colors(off))
    for _ in range(4):
        for t in teams:
            for o in offsets:
                trial = {**off, t: o}
                score = worst(colors(trial))
                if score > best + 1e-9:
                    best, off = score, trial
    return colors(off)


def driver_code(driver_id: str) -> str:
    """Sigla de 3 letras del piloto (ej. 'max_verstappen' -> 'VER')."""
    return DRIVER_CODES.get(driver_id, driver_id.split("_")[-1][:3].upper())


def race_table(df: pd.DataFrame, stretch: bool = False,
               race_laps: int = RACE_LAPS) -> pd.DataFrame:
    """Una fila por piloto y carrera con largada, predicción y resultado real.

    `df`: filas crudas con la predicción del modelo en `score` (posición continua dentro de la
    carrera, menor = más adelante; ver `build_app.py`).

    `behind` = distancia al líder del modelo al llegar, en puestos de puntaje (`score − mínimo`).
    Con `stretch=True` se estira a 0..N−1 en cada carrera: los modelos de regresión comprimen las
    predicciones hacia el medio (Ridge usa ~12 de 20 puestos); estirar conserva el orden y la
    separación relativa, pero ya no es comparable entre carreras.

    Columnas `*_adj` = versión **ajustada por abandonos** (usa el resultado real, solo para
    visualizar): los que no terminaron (`RACE_Finished == 0`) chocan en el avance
    `crash_s = 1 − RACE_Laps_Down / race_laps` (máx. `CRASH_MAX`), salen del orden y quedan al
    fondo (el que abandonó antes, más abajo); los que terminaron se ordenan por puntaje.
    """
    df = df.copy()
    keys = [df[c] for c in RACE_COLS]

    # 2. Todo en la misma escala 1..N por carrera (el target del modelo también es 1..N).
    races = df.groupby(RACE_COLS)
    df["grid"] = races["Q_GridPosition"].rank(method="first").astype(int)
    df["pred_pos"] = races["score"].rank(method="first").astype(int)
    df["final"] = races["RACE_Position"].rank(method="first").astype(int)

    # 3. Distancia al líder al llegar (puestos de puntaje; opcionalmente estirada a 0..N−1).
    lo = races["score"].transform("min")
    scale = 1.0
    if stretch:
        scale = races["score"].transform("size").sub(1) / (
            races["score"].transform("max") - lo).replace(0, 1)
    df["behind"] = (df["score"] - lo) * scale

    # 4. Distancia con el auto de adelante según el modelo: la "seguridad" del orden.
    df = df.sort_values(RACE_COLS + ["score"])
    keys = [df[c] for c in RACE_COLS]
    df["gap_ahead"] = df.groupby(keys)["score"].diff()

    # 5. Versión ajustada por abandonos: momento del choque y nuevo orden.
    finished = df["RACE_Finished"] if "RACE_Finished" in df else pd.Series(1, index=df.index)
    df["dnf"] = (finished == 0).astype(int)
    laps_down = df["RACE_Laps_Down"] if "RACE_Laps_Down" in df else pd.Series(
        np.nan, index=df.index)
    crash = (1 - laps_down / race_laps).clip(0, CRASH_MAX).fillna(0.5)
    df["crash_s"] = np.where(df["dnf"] == 1, crash, NO_CRASH)
    fin = df["dnf"] == 0
    # terminaron: por puntaje (o por largada, para la grilla ajustada); chocados: al fondo,
    # el último en chocar primero y empates por largada (mismo criterio que `lane_paths`)
    order_dnf = (df[~fin].sort_values(RACE_COLS + ["crash_s", "grid"],
                                      ascending=[True, True, False, True])
                 .groupby(RACE_COLS).cumcount() + 1)
    n_fin = fin.groupby(keys).transform("sum")
    df["pred_adj"] = df[fin].groupby(RACE_COLS)["score"].rank(method="first")
    df["grid_adj"] = df[fin].groupby(RACE_COLS)["grid"].rank(method="first")
    df.loc[~fin, "pred_adj"] = n_fin[~fin] + order_dnf
    df.loc[~fin, "grid_adj"] = n_fin[~fin] + order_dnf
    df[["pred_adj", "grid_adj"]] = df[["pred_adj", "grid_adj"]].astype(int)
    lo_fin = df["score"].where(fin).groupby(keys).transform("min")
    df["behind_adj"] = (df["score"] - lo_fin) * scale
    df["gap_adj"] = df[fin].groupby(RACE_COLS)["score"].diff()

    # 6. Error por carrera del modelo y de "la grilla como predicción", para comparar.
    for col, pred in [("mae_model", "pred_pos"), ("mae_grid", "grid"),
                      ("mae_adj", "pred_adj"), ("mae_grid_adj", "grid_adj")]:
        df[col] = (df[pred] - df["final"]).abs().groupby(keys).transform("mean")

    # 7. Color: paleta por temporada; en cada carrera el primer piloto del equipo (orden
    #    alfabético) va en el tono claro y el segundo en el oscuro.
    mate = df.groupby(RACE_COLS + ["TeamId"])["DriverId"].rank(method="dense").gt(1).astype(int)
    palettes = {y: team_palette(g["TeamId"].tolist()) for y, g in df.groupby("Year")}
    df["color"] = [palettes[y][(team, k)] for y, team, k in zip(df["Year"], df["TeamId"], mate)]

    status = df["RACE_Status"] if "RACE_Status" in df else pd.Series("", index=df.index)
    return pd.DataFrame({
        "race": df["Year"].astype(str) + "-" + df["RoundNumber"].astype(str).str.zfill(2),
        "race_label": df["Year"].astype(str) + " · fecha " + df["RoundNumber"].astype(str),
        "driver": df["DriverId"].map(driver_code),
        "driver_id": df["DriverId"],
        "team": df["TeamId"],
        "color": df["color"],
        "grid": df["grid"],
        "grid_official": df["Q_GridPosition"],
        "score": df["score"].round(2),
        "behind": df["behind"].round(3),
        "pred_pos": df["pred_pos"],
        "final": df["final"],
        "final_official": df["RACE_Position"],
        "status": status.fillna(""),
        "dnf": df["dnf"],
        "gap_ahead": df["gap_ahead"].round(2),
        "mae_model": df["mae_model"].round(2),
        "mae_grid": df["mae_grid"].round(2),
        "crash_s": df["crash_s"].round(3),
        "pred_adj": df["pred_adj"],
        "grid_ref": df["grid"],
        "grid_adj": df["grid_adj"],
        "behind_adj": df["behind_adj"].round(3),
        "gap_adj": df["gap_adj"].round(2),
        "mae_adj": df["mae_adj"].round(2),
        "mae_grid_adj": df["mae_grid_adj"].round(2),
    }).reset_index(drop=True)


def adjusted_view(table: pd.DataFrame) -> pd.DataFrame:
    """La tabla con las columnas ajustadas por abandonos en lugar de las originales (para usar
    `lane_paths`, `doubt_pairs` o el panel sobre la versión ajustada)."""
    return table.assign(pred_pos=table["pred_adj"], behind=table["behind_adj"],
                        grid_ref=table["grid_adj"],
                        gap_ahead=table["gap_adj"], mae_model=table["mae_adj"],
                        mae_grid=table["mae_grid_adj"])


def doubt_pairs(table: pd.DataFrame, threshold: float = 0.2,
                finishers_only: bool = False) -> pd.DataFrame:
    """Pares de autos consecutivos (según el modelo) a menos de `threshold` puestos de puntaje.

    `finishers_only=True` (versión ajustada) solo cuenta a los que terminaron. `lane_a`/`lane_b`: carriles al
    llegar (posición predicha) del de adelante y del de atrás; `behind_a`/`behind_b`: su
    distancia al líder (`behind`)."""
    if finishers_only:
        table = table[table["dnf"] == 0]
    rows = []
    for race, g in table.sort_values(["race", "score"]).groupby("race"):
        s = g.reset_index(drop=True)
        for i in range(1, len(s)):
            a, b = s.loc[i - 1], s.loc[i]
            if b["score"] - a["score"] < threshold:
                rows.append({"race": race, "lane_a": a["pred_pos"], "lane_b": b["pred_pos"],
                             "behind_a": a["behind"], "behind_b": b["behind"],
                             "pair": f"{a['driver']} – {b['driver']}",
                             "gap": round(b["score"] - a["score"], 2)})
    return pd.DataFrame(rows, columns=["race", "lane_a", "lane_b", "behind_a", "behind_b",
                                       "pair", "gap"])


def _smoothstep(x: Any) -> Any:
    """Suavizado ease in-out en [0, 1] (el mismo que usa el gráfico en el navegador)."""
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def lane_paths(table: pd.DataFrame, grid_step: float = GRID_STEP,
               change: float = LANE_CHANGE, steps: int = 2000,
               samples: int = 7, crashes: bool = False) -> pd.DataFrame:
    """Recorrido de carril de cada auto a lo largo del avance `s` (0 = largada, 1 = llegada).

    La distancia al líder de cada auto es `grid_step·(grid−1) + suave(s)·(behind − grid_step·(grid−1))`;
    el carril es el orden por esa distancia. Con `crashes=True`, desde su `crash_s` el auto sale
    del orden y va al fondo (el último en chocar primero), y los de abajo suben. Cada cambio de
    carril dura `change` (fracción del avance) con un suavizado.

    Devuelve los puntos del recorrido (`s`, `y`) con el punto anterior (`s_prev`, `y_prev`), para
    que el navegador interpole la posición en cualquier avance sin conocer los cruces.
    """
    s_grid = np.linspace(0, 1, steps + 1)
    ease = _smoothstep(s_grid)
    rows = []
    for race, g in table.sort_values(["race", "grid"]).groupby("race", sort=False):
        start = grid_step * (g["grid"].to_numpy() - 1)
        off = start[None, :] + ease[:, None] * (g["behind"].to_numpy() - start)[None, :]
        crash_s = g["crash_s"].to_numpy() if crashes else np.full(len(g), NO_CRASH)
        if crashes:
            crashed = s_grid[:, None] >= crash_s[None, :]
            off = np.where(crashed, 1e6 + (1 - crash_s)[None, :], off)
        # carril en cada instante: orden por distancia al líder (empates: orden de largada)
        order = np.argsort(off, axis=1, kind="stable")
        lanes = np.empty_like(order)
        lanes[np.arange(len(s_grid))[:, None], order] = np.arange(1, len(g) + 1)
        for k, row in enumerate(g.itertuples()):
            lane = lanes[:, k]
            idx = np.nonzero(np.diff(lane))[0]
            # cada cruce arranca medio cambio antes; se corre para terminar antes de llegar
            starts = np.clip((s_grid[idx] + s_grid[idx + 1]) / 2 - change / 2, 0, 1 - change)
            deltas = lane[idx + 1] - lane[idx]
            pts = np.unique(np.concatenate(
                [[0.0, 1.0], *[np.linspace(a, a + change, samples) for a in starts]]))
            y = lane[0] + sum(d * _smoothstep((pts - a) / change) for a, d in zip(starts, deltas))
            y = np.round(np.asarray(y, dtype=float) * np.ones_like(pts), 4)
            for i, (s, yy) in enumerate(zip(pts, y)):
                rows.append({"race": race, "driver": row.driver, "key": f"{race}|{row.driver}",
                             "s": round(float(s), 4), "y": float(yy),
                             "s_prev": round(float(pts[i - 1]), 4) if i else -1.0,
                             "y_prev": float(y[i - 1]) if i else float(yy),
                             "g": int(row.grid) - 1, "behind": row.behind, "color": row.color,
                             "crash_s": float(crash_s[k])})
    return pd.DataFrame(rows)


def _params(table: pd.DataFrame) -> tuple[Any, Any]:
    """Slider de avance (0 → 1) y selector de carrera, compartidos por todos los paneles."""
    races = table[["race", "race_label"]].drop_duplicates().sort_values("race")
    # sin control visible: lo mueve el botón «Correr» (ver `to_html`)
    avance = alt.param(name="avance", value=0.0)
    carrera = alt.param(name="carrera", value=races["race"].iloc[0], bind=alt.binding_select(
        options=races["race"].tolist(), labels=races["race_label"].tolist(), name="Carrera "))
    return avance, carrera


def _panel(t: pd.DataFrame, *, adjusted: bool, dataset: str, title: str, threshold: float,
           width: int, row_height: int, model_name: str, grid_step: float, change: float,
           max_behind: float) -> tuple[alt.LayerChart, dict[str, Any]]:
    """Un panel (pista completa) sin parámetros ni configuración. `t` trae las columnas de la
    versión a dibujar (original o `adjusted_view`). Devuelve el panel y su dataset con nombre."""
    n_max = int(t.groupby("race").size().max())
    height = row_height * n_max
    x_dom = (-0.16, 1.62)
    y_scale = alt.Scale(domain=[0.4, n_max + 0.6], reverse=True, nice=False, zero=False)
    x_scale = alt.Scale(domain=list(x_dom), nice=False, zero=False)
    no_axis = dict(axis=None)
    car_px = row_height * 1.45                               # largo del auto en píxeles
    half_car = car_px / 2 / width * (x_dom[1] - x_dom[0])    # medio auto en unidades de x
    unit = FIELD_SPAN / max_behind                           # 1 puesto en unidades de x
    lead_start = X_LEFT + (n_max - 1) * grid_step * unit     # líder al largar

    in_race = "datum.race == carrera"
    tt = "clamp(avance,0,1)"
    lead = f"({lead_start} + {tt} * {X_END - lead_start})"
    arrive = f"clamp(({tt} - 0.95) / 0.05, 0, 1)"   # solo en el último 5% del avance

    xy = dict(x=alt.X("x:Q", scale=x_scale, **no_axis), y=alt.Y("y:Q", scale=y_scale, **no_axis))
    base = alt.Chart(t[["race", "race_label", "driver", "color", "grid", "pred_pos", "final",
                        "dnf", "mae_model", "mae_grid", "grid_ref"]]).transform_filter(in_race)

    # Carriles de la pista (uno por posición).
    lanes = alt.Chart(pd.DataFrame({"y": np.arange(1, n_max + 1)})).mark_rule(
        color=LANE, strokeDash=[6, 6], strokeWidth=1).encode(
        y=alt.Y("y:Q", scale=y_scale, **no_axis))

    # Línea de largada (delante del líder) y meta a cuadros (delante del líder al llegar).
    start = alt.Chart(pd.DataFrame({"x": [lead_start + half_car * 1.4]})).mark_rule(
        color=INK, strokeWidth=2, opacity=0.6).encode(x=alt.X("x:Q", scale=x_scale, **no_axis))
    checks = pd.DataFrame([{"x": X_END + half_car + 0.085 + 0.012 * c, "y": 0.4 + 0.5 * r,
                            "black": (r + c) % 2}
                           for r in range(2 * n_max + 1) for c in range(2)])
    finish = alt.Chart(checks).mark_square(size=row_height * 4, opacity=0.85).encode(
        x=alt.X("x:Q", scale=x_scale, **no_axis), y=alt.Y("y:Q", scale=y_scale, **no_axis),
        color=alt.Color("black:N", scale=alt.Scale(domain=[0, 1], range=[INK, "#111111"]),
                        legend=None))
    x_lines = X_END + half_car + 0.115                       # después de la meta

    # Regla de distancias que acompaña al líder: una marca por puesto, número cada 5.
    ruler = alt.Chart(pd.DataFrame({"k": np.arange(0, int(np.ceil(max_behind)) + 1)})
                      ).transform_calculate(
        x=f"{lead} - datum.k * {unit}", y="0.42", y2="datum.k % 5 == 0 ? 0.62 : 0.52",
        label="datum.k % 5 == 0 ? (datum.k == 0 ? 'líder' : '−' + datum.k) : ''"
    ).transform_filter(f"datum.x >= {X_LEFT}")   # solo sobre la pista
    ruler_ticks = ruler.mark_rule(color=INK_MUTED, strokeWidth=1).encode(y2="y2:Q", **xy)
    ruler_txt = ruler.mark_text(color=INK_MUTED, fontSize=9, dy=-7).encode(text="label:N", **xy)

    # Columnas de texto: largada (izquierda) y resultado real (derecha).
    grid_txt = base.transform_calculate(x="-0.02", y="datum.grid", label=(
        "'P' + datum.grid + '  ' + datum.driver")).mark_text(
        align="right", color=INK, fontSize=12, font="monospace").encode(text="label:N", **xy)
    final_txt = base.transform_calculate(x="1.03", y="datum.final", label=(
        "'P' + datum.final + '  ' + datum.driver + (datum.dnf ? '  ✕' : '')")).mark_text(
        align="left", color=INK, fontSize=12, font="monospace").encode(text="label:N", **xy)
    final_chip = base.transform_calculate(x="1.01", y="datum.final").mark_square(
        size=60).encode(color=alt.Color("color:N", scale=None), **xy)

    # Al lado del final real (aparecen al llegar): puestos ganados (+) o perdidos (−) respecto de
    # la grilla y del modelo, y cuánto mejora (▲) o empeora (▼) el modelo a la grilla en ese
    # puesto, sobre la cantidad de puestos de la carrera: (|Δ grilla| − |Δ modelo|) / N
    # (con N = 20, acertar 1 puesto más = 5%).
    signed = ("(datum.{0} > 0 ? '+' + datum.{0} : datum.{0} < 0 ? '−' + abs(datum.{0}) : '0')")
    diffs = base.transform_joinaggregate(n="count()").transform_calculate(
        y="datum.final", dg="datum.grid_ref - datum.final", dm="datum.pred_pos - datum.final",
    ).transform_calculate(
        pct="(abs(datum.dg) - abs(datum.dm)) / datum.n",
        dg_txt=signed.format("dg"), dm_txt=signed.format("dm"), op=arrive,
    ).transform_calculate(
        pct_txt=("(datum.pct > 0 ? '▲ ' : datum.pct < 0 ? '▼ ' : '= ') + "
                 "format(abs(datum.pct), '.0%')"),
        tone="datum.pct > 0 ? 'mejor' : datum.pct < 0 ? 'peor' : 'neutro'",
    )
    fade = alt.Opacity("op:Q", scale=None)
    diff_cols = [
        diffs.transform_calculate(x=f"{X_DG}").mark_text(
            align="right", color=INK, fontSize=11, font="monospace").encode(
            text="dg_txt:N", opacity=fade, **xy),
        diffs.transform_calculate(x=f"{X_DM}").mark_text(
            align="right", color=INK, fontSize=11, font="monospace").encode(
            text="dm_txt:N", opacity=fade, **xy),
        *[diffs.transform_filter(f"datum.tone == '{name}'").transform_calculate(
            x=f"{X_PCT}").mark_text(align="right", color=color, fontSize=11,
                                     font="monospace").encode(
            text="pct_txt:N", opacity=fade, **xy)
          for name, color in [("mejor", GOOD), ("peor", BAD), ("neutro", INK_MUTED)]],
    ]

    # Recorridos: puntos ya pasados + el punto actual (interpolado entre el anterior y el
    # siguiente). x sale del avance de ese punto (quieto desde el choque); y del recorrido de
    # carril precalculado. Dataset con nombre, registrado una sola vez en el gráfico.
    # Solo se embebe (key, s, y); el punto anterior y los datos del piloto se arman acá.
    paths = lane_paths(t, grid_step, change, crashes=adjusted)
    per_car = t.assign(key=t["race"] + "|" + t["driver"], g=t["grid"] - 1,
                       crash_s=t["crash_s"] if adjusted else NO_CRASH)
    ease_s = "(datum.sx*datum.sx*(3-2*datum.sx))"
    moving = alt.Chart(alt.NamedData(name=dataset)).transform_filter(
        "indexof(datum.key, carrera + '|') == 0"
    ).transform_window(
        s_prev="lag(s)", y_prev="lag(y)", groupby=["key"], sort=[alt.SortField("s")],
    ).transform_calculate(
        s_prev="isValid(datum.s_prev) ? datum.s_prev : -1",
        y_prev="isValid(datum.y_prev) ? datum.y_prev : datum.y",
    ).transform_filter(f"datum.s_prev <= {tt}").transform_lookup(
        lookup="key", from_=alt.LookupData(per_car[["key", "driver", "g", "behind", "color",
                                                    "crash_s"]], "key",
                                           ["driver", "g", "behind", "color", "crash_s"])
    ).transform_calculate(
        head=f"datum.s > {tt} || (datum.s >= 1 && {tt} >= 1)",
        se=f"min(datum.s, {tt})",
    ).transform_calculate(
        sx="min(datum.se, datum.crash_s)",
        y=(f"datum.s > {tt} ? datum.y_prev + ({tt} - datum.s_prev) / (datum.s - datum.s_prev)"
           " * (datum.y - datum.y_prev) : datum.y"),
    ).transform_calculate(
        x=(f"({lead_start} + datum.sx * {X_END - lead_start}) - ({grid_step} * datum.g + "
           f"{ease_s} * (datum.behind - {grid_step} * datum.g)) * {unit}"),
    )
    trail = moving.mark_line(strokeWidth=2.5, opacity=0.45, interpolate="linear").encode(
        detail="driver:N", order="se:Q", color=alt.Color("color:N", scale=None), **xy)

    info = ["driver_id", "team", "grid_official", "score", "pred_pos", "final_official",
            "status", "gap_ahead"]
    lookup = t.assign(key=t["race"] + "|" + t["driver"])[["key", *info]]
    cars_data = moving.transform_filter("datum.head").transform_lookup(
        lookup="key", from_=alt.LookupData(lookup, "key", info)
    ).transform_calculate(
        crashed=f"{tt} >= datum.crash_s",
        gap_txt="isValid(datum.gap_ahead) ? format(datum.gap_ahead, '.2f') + ' puestos' : '—'",
        gap_lbl="isValid(datum.gap_ahead) ? '+' + format(datum.gap_ahead, '.2f') : ''",
        op=arrive,
    ).transform_calculate(
        fill=f"datum.crashed ? '{CRASH_GRAY}' : datum.color",
        name="datum.crashed ? datum.driver + ' ✕' : datum.driver",
    )
    tooltip = [
        alt.Tooltip("driver_id:N", title="Piloto"), alt.Tooltip("team:N", title="Escudería"),
        alt.Tooltip("grid_official:Q", title="Largada (oficial)"),
        alt.Tooltip("score:Q", title="Predicción (puntaje)", format=".2f"),
        alt.Tooltip("pred_pos:Q", title="Posición predicha" + (" (ajustada)" if adjusted else "")),
        alt.Tooltip("final_official:Q", title="Final real (oficial)"),
        alt.Tooltip("status:N", title="Estado"),
        alt.Tooltip("gap_txt:N", title="Distancia al de adelante"),
    ]
    wheels = cars_data.mark_point(shape=CAR_WHEELS, size=car_px ** 2, filled=True,
                                  fill="#0D0D0D", stroke=None, opacity=1).encode(**xy)
    cars = cars_data.mark_point(shape=CAR_BODY, size=car_px ** 2, filled=True,
                                opacity=1, stroke=ASPHALT, strokeWidth=0.6).encode(
        fill=alt.Fill("fill:N", scale=None), tooltip=tooltip, **xy)
    car_txt = cars_data.mark_text(align="left", dx=car_px / 2 + 4, color=INK, fontSize=11,
                                  fontWeight="bold").encode(text="name:N", **xy)
    # Intervalo con el de adelante, detrás de cada auto (aparece al llegar).
    gap_txt = cars_data.mark_text(align="right", dx=-car_px / 2 - 4, color=INK,
                                  fontSize=10).encode(
        text="gap_lbl:N", opacity=alt.Opacity("op:Q", scale=None), **xy)

    # Al llegar: línea punteada del carril predicho al resultado real (largo = error).
    error_line = base.transform_calculate(
        x=f"{x_lines}", y="datum.pred_pos", x2="1.0", y2="datum.final", op=arrive,
    ).mark_rule(color=INK_MUTED, strokeDash=[3, 3], strokeWidth=1).encode(
        x2="x2:Q", y2="y2:Q", opacity=alt.Opacity("op:Q", scale=None), **xy)

    # Franjas de duda: une a los autos consecutivos a menos de `threshold` puestos.
    pairs = doubt_pairs(t, threshold, finishers_only=adjusted)
    doubt = alt.Chart(pairs).transform_filter(in_race).transform_calculate(
        x=f"{X_END} - datum.behind_b * {unit} - {half_car * 1.1}",
        x2=f"{X_END} - datum.behind_a * {unit} + {half_car * 1.1}",
        y="datum.lane_a - 0.42", y2="datum.lane_b + 0.42", op=f"0.25 * {arrive}",
    ).mark_rect(fill=DOUBT, stroke=DOUBT, strokeWidth=1, cornerRadius=4).encode(
        x=alt.X("x:Q", scale=x_scale, **no_axis), x2="x2:Q",
        y=alt.Y("y:Q", scale=y_scale, **no_axis), y2="y2:Q",
        opacity=alt.Opacity("op:Q", scale=None),
        tooltip=[alt.Tooltip("pair:N", title="Orden dudoso"),
                 alt.Tooltip("gap:Q", title="Distancia (puestos)")])

    # Encabezados de columna y marcador de carrera + errores (MAE) al llegar.
    head = pd.DataFrame({"x": [-0.02, (X_LEFT + X_END) / 2, 1.03, X_DG, X_DM, X_PCT],
                         "label": ["LARGADA", f"PREDICCIÓN ({model_name})", "FINAL REAL",
                                   "Δ GRILLA", "Δ MODELO", "MEJORA"],
                         "align": ["right", "center", "left", "right", "right", "right"]})
    headers = alt.layer(*[
        alt.Chart(head.iloc[[i]]).mark_text(align=a, color=INK_MUTED, fontSize=10,
                                            fontWeight="bold", dy=-row_height * 1.0).encode(
            x=alt.X("x:Q", scale=x_scale, **no_axis), y=alt.value(0), text="label:N")
        for i, a in enumerate(head["align"])])
    mae_lbl = ("'MAE ajustado ' + format(datum.mae_model, '.2f') + '  vs  grilla ajustada '"
               if adjusted else "'MAE modelo ' + format(datum.mae_model, '.2f') + '  vs  grilla '")
    mae_lbl += (" + format(datum.mae_grid, '.2f') + '  (' + (datum.mae_model <= datum.mae_grid ? "
                "'mejora ' : 'empeora ') + format(abs(datum.mae_grid - datum.mae_model) / "
                "datum.n, '.1%') + ' de los puestos)'")
    summary = base.transform_aggregate(
        mae_model="mean(mae_model)", mae_grid="mean(mae_grid)", n="count()",
        groupby=["race_label"]
    ).transform_calculate(
        label=(f"datum.race_label + '   ·   avance ' + format({tt}, '.0%') + "
               f"(avance >= 0.999 ? '   ·   ' + {mae_lbl} : '')")
    ).mark_text(align="left", color=INK, fontSize=13, dy=-row_height * 1.8).encode(
        x=alt.value(0), y=alt.value(0), text="label:N")

    panel = alt.layer(
        lanes, start, finish, ruler_ticks, ruler_txt, doubt, error_line, trail, grid_txt,
        final_chip, final_txt, *diff_cols, wheels, cars, car_txt, gap_txt, headers, summary,
    ).properties(width=width, height=height, title=alt.Title(
        title, anchor="start", color=INK, fontSize=14, offset=row_height * 1.8))
    return panel, {dataset: paths[["key", "s", "y"]].to_dict("records")}


def _configure(chart: Any) -> Any:
    return chart.configure(
        background=ASPHALT, padding={"left": 20, "right": 20, "top": 16, "bottom": 16}
    ).configure_view(stroke=None, fill=ASPHALT).configure_text(font=C.FUENTE)


def _max_behind(table: pd.DataFrame, adjusted: bool) -> float:
    cols = ["behind", "behind_adj"] if adjusted else ["behind"]
    fin = table["dnf"] == 0 if adjusted else pd.Series(True, index=table.index)
    return max(float(table["behind"].max()), float(table.loc[fin, cols[-1]].max()), 1.0)


def race_cars_chart(table: pd.DataFrame, threshold: float = 0.2, width: int = 1000,
                    row_height: int = 30, model_name: str = "modelo",
                    grid_step: float = GRID_STEP, change: float = LANE_CHANGE,
                    adjusted: bool = False) -> alt.LayerChart:
    """Una pista con slider de avance (0 → 1) y selector de carrera.

    - Carril = posición en ese momento (quién va adelante en la pista). Al pasar a otro auto se
      cambia de carril con una animación corta (`change`, fracción del avance).
    - Distancia horizontal al líder = puestos de puntaje: arranca en la formación de largada
      (`grid_step` puestos entre autos) y se estira suavemente hasta la predicción del modelo.
      Autos pegados al llegar = el modelo duda del orden.
    - Cada auto deja una estela con su recorrido: los quiebres son los cambios de puesto.
    - `adjusted=True`: versión ajustada por abandonos (ver `race_table`).
    """
    avance, carrera = _params(table)
    t = adjusted_view(table) if adjusted else table
    panel, datasets = _panel(
        t, adjusted=adjusted, dataset="lane_paths_adj" if adjusted else "lane_paths",
        title=_TITLES[adjusted], threshold=threshold, width=width, row_height=row_height,
        model_name=model_name, grid_step=grid_step, change=change,
        max_behind=_max_behind(table, adjusted))
    chart = panel.add_params(avance, carrera).properties(datasets=datasets)
    return _configure(chart)


def race_cars_compare(table: pd.DataFrame, threshold: float = 0.2, width: int = 800,
                      row_height: int = 30, model_name: str = "modelo",
                      grid_step: float = GRID_STEP,
                      change: float = LANE_CHANGE) -> alt.HConcatChart:
    """Las dos versiones lado a lado con el mismo slider y selector: a la izquierda la
    predicción del modelo; a la derecha, ajustada por abandonos (los que no terminaron chocan en
    su vuelta de abandono, quedan grises y los de abajo suben). Misma escala en ambas."""
    avance, carrera = _params(table)
    max_behind = _max_behind(table, adjusted=True)
    common = dict(threshold=threshold, width=width, row_height=row_height,
                  model_name=model_name, grid_step=grid_step, change=change,
                  max_behind=max_behind)
    left, d1 = _panel(table, adjusted=False, dataset="lane_paths", title=_TITLES[False],
                      **common)
    right, d2 = _panel(adjusted_view(table), adjusted=True, dataset="lane_paths_adj",
                       title=_TITLES[True], **common)
    chart = alt.hconcat(left, right, spacing=60).add_params(avance, carrera).properties(
        datasets={**d1, **d2},
        title=alt.Title(
            "Largada → predicción → resultado real",
            subtitle=["Carril = posición; la estela muestra cada cambio de puesto. Distancia "
                      "horizontal al líder = puestos de puntaje del modelo. Autos pegados = duda "
                      f"del orden (franja amarilla: menos de {threshold:g} puestos).",
                      "Línea punteada = error frente al resultado real. ✕ = no terminó. "
                      "Derecha: los que no terminaron chocan en su vuelta de abandono "
                      f"(aprox., carreras de {RACE_LAPS} vueltas) y los de abajo suben."],
            anchor="start", color=INK, subtitleColor=INK_MUTED, fontSize=16, offset=16))
    return _configure(chart)


_TITLES = {False: "Predicción del modelo",
           True: "Ajustada por abandonos (usa el resultado real)"}


# Página con botón "Correr" que anima el slider (Vega-Lite no tiene reproducción automática).
_HTML = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5.30.0"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5.21.0"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6.26.0"></script>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Titillium+Web:ital,wght@0,400;0,600;0,700;1,700&display=swap" rel="stylesheet">
<style>
  html, body {{ background:{bg}; color:{ink}; font-family:{font}; margin:0;
               overflow:hidden; }}
  #controles {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px; }}
  button {{ background:{lane}; color:{ink}; border:1px solid {muted}; border-radius:4px;
           padding:6px 16px; font:600 14px {font}; cursor:pointer; letter-spacing:.04em;
           text-transform:uppercase; transition:background .15s, border-color .15s; }}
  button:hover {{ border-color:{ink}; }}
  button:focus-visible {{ outline:2px solid {ink}; outline-offset:2px; }}
  #play {{ background:{rojo}; border-color:{rojo}; color:#fff; font-style:italic;
          clip-path:polygon(8px 0, 100% 0, calc(100% - 8px) 100%, 0 100%); padding:6px 22px; }}
  #play:hover {{ filter:brightness(1.12); }}
  .vega-bindings {{ display:inline-block; margin-left:12px; }}
  .vega-bindings select {{ background:{lane}; color:{ink}; border:1px solid {muted};
                          border-radius:4px; padding:4px 6px; font:14px {font}; }}
  #marco {{ overflow:hidden; }}
  #vis {{ transform-origin:top left; }}
</style></head><body>
<div id="controles"><button id="play">Correr</button>
<button id="reset">Volver a la largada</button><span id="selector"></span></div>
<div id="marco"><div id="vis"></div></div>
<script>
const spec = {spec};
// El gráfico se achica para entrar en el ancho disponible (sin barras de desplazamiento).
function ajustar() {{
  const vis = document.getElementById("vis");
  vis.style.transform = "none";
  const escala = Math.min(1, document.body.clientWidth / vis.scrollWidth);
  vis.style.transform = "scale(" + escala + ")";
  document.getElementById("marco").style.height = (vis.scrollHeight * escala) + "px";
}}
vegaEmbed("#vis", spec, {{actions: false, bind: "#selector"}}).then(({{view}}) => {{
  ajustar();
  window.addEventListener("resize", ajustar);
  const duration = {duration_ms};
  let timer = null;
  const stop = () => {{ clearInterval(timer); timer = null; }};
  document.getElementById("play").onclick = () => {{
    stop();
    const start = Date.now();
    timer = setInterval(() => {{
      const t = Math.min(1, (Date.now() - start) / duration);
      view.signal("avance", t).runAsync();
      if (t >= 1) stop();
    }}, 30);
  }};
  document.getElementById("reset").onclick = () => {{ stop(); view.signal("avance", 0).runAsync(); }};
  view.addSignalListener("carrera", () => {{ stop(); view.signal("avance", 0).runAsync(); }});
}});
</script></body></html>
"""


def to_html(chart: alt.TopLevelMixin, duration_s: float = 6.0,
            title: str = "Autitos F1") -> str:
    """HTML autónomo con el gráfico y botones para correr la carrera y volver a la largada."""
    return _HTML.format(title=title, spec=json.dumps(chart.to_dict()), bg=ASPHALT, ink=INK,
                        lane=LANE, muted=INK_MUTED, rojo=C.F1_ROJO, font=C.FUENTE,
                        duration_ms=int(duration_s * 1000))


def save_html(chart: alt.TopLevelMixin, path: str | Path, duration_s: float = 6.0) -> Path:
    """Guarda el HTML de `to_html` y devuelve la ruta."""
    path = Path(path)
    path.write_text(to_html(chart, duration_s), encoding="utf-8")
    return path
