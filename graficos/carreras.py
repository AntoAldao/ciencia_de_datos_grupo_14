"""El nombre de cada carrera (el lugar) en lugar de su número de fecha.

El dataset identifica cada carrera por año y fecha (`Year`, `RoundNumber`). El nombre sale del
calendario de la misma API que usa el pipeline (Jolpica, estilo Ergast), guardado en
`data/calendario.csv`. Para volver a bajarlo (por ejemplo, al sumar carreras nuevas):

    python -m graficos.carreras

Uso:

    from graficos import carreras
    carreras.nombre(2026, 3)     # 'GP de Japón'
    carreras.corto(2026, 3)      # 'Japón'
    carreras.etiqueta(2026, 3)   # '2026 · GP de Japón'
"""

from __future__ import annotations

import csv
import json
import urllib.request
from functools import lru_cache
from pathlib import Path

CALENDARIO = Path(__file__).resolve().parent.parent / "data" / "calendario.csv"
API = "https://api.jolpi.ca/ergast/f1/{anio}.json?limit=100"

# raceName de la API -> (nombre en castellano, nombre corto para ejes)
NOMBRES = {
    "70th Anniversary Grand Prix": ("GP del 70.º Aniversario", "70.º Aniv."),
    "Abu Dhabi Grand Prix": ("GP de Abu Dabi", "Abu Dabi"),
    "Australian Grand Prix": ("GP de Australia", "Australia"),
    "Austrian Grand Prix": ("GP de Austria", "Austria"),
    "Azerbaijan Grand Prix": ("GP de Azerbaiyán", "Azerbaiyán"),
    "Bahrain Grand Prix": ("GP de Baréin", "Baréin"),
    "Bahrain Grand Prix in Malaysia": ("GP de Baréin en Malasia", "Malasia"),
    "Barcelona Grand Prix": ("GP de Barcelona", "Barcelona"),
    "Belgian Grand Prix": ("GP de Bélgica", "Bélgica"),
    "Brazilian Grand Prix": ("GP de Brasil", "Brasil"),
    "British Grand Prix": ("GP de Gran Bretaña", "Gran Bretaña"),
    "Canadian Grand Prix": ("GP de Canadá", "Canadá"),
    "Chinese Grand Prix": ("GP de China", "China"),
    "Dutch Grand Prix": ("GP de los Países Bajos", "Países Bajos"),
    "Eifel Grand Prix": ("GP de Eifel", "Eifel"),
    "Emilia Romagna Grand Prix": ("GP de Emilia-Romaña", "Emilia-Romaña"),
    "French Grand Prix": ("GP de Francia", "Francia"),
    "German Grand Prix": ("GP de Alemania", "Alemania"),
    "Hungarian Grand Prix": ("GP de Hungría", "Hungría"),
    "Italian Grand Prix": ("GP de Italia", "Italia"),
    "Japanese Grand Prix": ("GP de Japón", "Japón"),
    "Las Vegas Grand Prix": ("GP de Las Vegas", "Las Vegas"),
    "Mexican Grand Prix": ("GP de México", "México"),
    "Mexico City Grand Prix": ("GP de la Ciudad de México", "México"),
    "Miami Grand Prix": ("GP de Miami", "Miami"),
    "Monaco Grand Prix": ("GP de Mónaco", "Mónaco"),
    "Portuguese Grand Prix": ("GP de Portugal", "Portugal"),
    "Qatar Grand Prix": ("GP de Catar", "Catar"),
    "Russian Grand Prix": ("GP de Rusia", "Rusia"),
    "Sakhir Grand Prix": ("GP de Sakhir", "Sakhir"),
    "Saudi Arabian Grand Prix": ("GP de Arabia Saudita", "Arabia Saudita"),
    "Singapore Grand Prix": ("GP de Singapur", "Singapur"),
    "Spanish Grand Prix": ("GP de España", "España"),
    "Styrian Grand Prix": ("GP de Estiria", "Estiria"),
    "São Paulo Grand Prix": ("GP de São Paulo", "São Paulo"),
    "Turkish Grand Prix": ("GP de Turquía", "Turquía"),
    "Tuscan Grand Prix": ("GP de la Toscana", "Toscana"),
    "United States Grand Prix": ("GP de Estados Unidos", "EE. UU."),
}


@lru_cache(maxsize=1)
def _calendario() -> dict[tuple[int, int], str]:
    with open(CALENDARIO, encoding="utf-8") as f:
        return {(int(r["Year"]), int(r["RoundNumber"])): r["raceName"] for r in csv.DictReader(f)}


def _nombres(anio: int, ronda: int) -> tuple[str, str]:
    crudo = _calendario().get((int(anio), int(ronda)))
    if crudo is None:   # carrera que no está en el calendario guardado: queda la fecha
        return f"Fecha {ronda}", f"F{ronda}"
    lugar = crudo.removesuffix(" Grand Prix")
    return NOMBRES.get(crudo, (f"GP de {lugar}", lugar))


def nombre(anio: int, ronda: int) -> str:
    """'GP de Japón'."""
    return _nombres(anio, ronda)[0]


def corto(anio: int, ronda: int) -> str:
    """'Japón': para los ejes, donde no entra el nombre completo."""
    return _nombres(anio, ronda)[1]


def etiqueta(anio: int, ronda: int) -> str:
    """'2026 · GP de Japón': para menús y tooltips, donde se mezclan temporadas."""
    return f"{anio} · {nombre(anio, ronda)}"


def eje(anio: int, rondas) -> str:
    """Expresión de Vega para `labelExpr` de un eje por fecha: muestra el nombre corto del lugar
    (la fecha sigue siendo el valor del eje, así el orden y los huecos no cambian)."""
    pares = ", ".join(f"'{int(r)}': {json.dumps(corto(anio, r), ensure_ascii=False)}"
                      for r in rondas)
    return f"({{{pares}}})[datum.value] || datum.label"


def descargar(anios: range = range(2018, 2027)) -> None:
    """Vuelve a bajar el calendario de la API y lo guarda en `data/calendario.csv`."""
    filas = []
    for anio in anios:
        pedido = urllib.request.Request(API.format(anio=anio), headers={"User-Agent": "f1-calendario"})
        with urllib.request.urlopen(pedido, timeout=30) as r:
            for c in json.load(r)["MRData"]["RaceTable"]["Races"]:
                lugar = c["Circuit"]["Location"]
                filas.append([anio, int(c["round"]), c["raceName"], lugar["locality"], lugar["country"]])
    with open(CALENDARIO, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Year", "RoundNumber", "raceName", "locality", "country"])
        w.writerows(filas)
    _calendario.cache_clear()


if __name__ == "__main__":
    descargar()
    print(f"Calendario guardado en {CALENDARIO}")
