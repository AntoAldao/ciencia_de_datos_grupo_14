"""Ejemplo de la capa bronce a la plata: las vueltas de prácticas de un piloto en un Gran Premio.

La página (Sector 1) muestra cómo sale «la mejor vuelta con cada goma», que no viene hecha: el
pipeline la calcula a partir de cada vuelta de FP1, FP2 y FP3. Este script toma las vueltas
crudas de un piloto (capa bronce del pipeline, que no se versiona por su tamaño), les aplica los
MISMOS filtros que el pipeline (`pipeline/include/f1/laps.py`) y anota por qué se descarta cada
una. Guarda el resultado en app_data/ejemplo_vueltas.json, que es lo que lee web/pagina.py.

Antes de guardar, comprueba que la mejor vuelta y el promedio por goma den exactamente lo que
tiene el dataset (data/f1_all_full.parquet) para ese piloto: si no, corta.

Se corre una sola vez, a mano (build_app.py no lo necesita):

    python web/ejemplo_vueltas.py <carpeta bronze/fastf1 del pipeline>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pipeline" / "include"))
from f1.config import FASTF1_COMPOUNDS, FASTF1_SESSIONS  # noqa: E402
from f1.laps import filter_outliers, valid_laps  # noqa: E402

ANIO, SLUG, ROUND, PILOTO = 2026, "japanese-grand-prix", 3, "LEC"
GRAN_PREMIO = "Gran Premio de Japón 2026"
SALIDA = RAIZ / "app_data" / "ejemplo_vueltas.json"
GOMAS = {"SOFT": "SOFT", "MEDIUM": "MED", "HARD": "HARD"}


def motivo(data: dict, i: int) -> str | None:
    """Por qué `valid_laps` descarta la vuelta i (mismo orden de chequeos); None si pasa."""
    def val(clave):
        v = data.get(clave, [])
        return v[i] if i < len(v) else None
    if val("compound") not in FASTF1_COMPOUNDS:
        return "Goma sin identificar"
    if val("pin") != "None" or val("pout") != "None":
        return "Entrada o salida de boxes"
    if val("status") != "1":
        return "Bandera o auto de seguridad"
    vfl = val("vfl")
    if val("iacc") is not True or vfl in ("None", None) or float(vfl) < 100 \
            or val("time") in ("None", None):
        return "Tiempo poco confiable o incompleto"
    if val("del") is True:
        return "Anulada por los comisarios"
    return None


def main(bronce: Path) -> None:
    carpeta = bronce / str(ANIO) / SLUG
    vueltas = []
    for sesion in FASTF1_SESSIONS:
        data = json.loads((carpeta / sesion / "session_laptimes.json").read_text(encoding="utf-8"))
        # las que el pipeline conserva, con su mismo código (por sesión, como en silver.py)
        quedan = {(l["driver"], l["lap"]) for l in filter_outliers(valid_laps(data))}
        validas = {(l["driver"], l["lap"]) for l in valid_laps(data)}
        for i, drv in enumerate(data["drv"]):
            if drv != PILOTO:
                continue
            vuelta = int(data["lap"][i])
            t = data["time"][i]
            m = motivo(data, i)
            if m is None and (drv, vuelta) not in quedan:
                m = "Más de 5 % más lenta que su mejor con esa goma"
            assert (m is None) == ((drv, vuelta) in quedan), (sesion, vuelta)
            assert (m is None or m.startswith("Más de")) == ((drv, vuelta) in validas), (sesion, vuelta)
            vueltas.append({"sesion": f"FP{sesion[-1]}", "vuelta": vuelta, "goma": data["compound"][i],
                            "tiempo": None if t in ("None", None) else float(t),
                            "motivo": m, "numero": data["dNum"][i]})

    # comprobación contra el dataset: mejor vuelta y promedio por goma
    d = pd.read_parquet(RAIZ / "data" / "f1_all_full.parquet")
    fila = d[(d["Year"] == ANIO) & (d["RoundNumber"] == ROUND)
             & (d["DriverNumber"].astype(str) == vueltas[0]["numero"])].iloc[0]
    for goma, k in GOMAS.items():
        t = [v["tiempo"] for v in vueltas if v["motivo"] is None and v["goma"] == goma]
        for medida, valor in [("min", min(t) if t else None), ("mean", sum(t) / len(t) if t else None)]:
            esperado = fila[f"FP_LapTime_{medida}_{k}_ABS"]
            assert (valor is None and pd.isna(esperado)) or abs(valor - esperado) < 1e-9, \
                (goma, medida, valor, esperado)

    SALIDA.write_text(json.dumps({
        "piloto": str(fila["DriverId"]), "gran_premio": GRAN_PREMIO, "anio": ANIO, "ronda": ROUND,
        "vueltas": vueltas}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)}: {len(vueltas)} vueltas de {PILOTO}, "
          f"{sum(v['motivo'] is None for v in vueltas)} quedan; coincide con el dataset.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
