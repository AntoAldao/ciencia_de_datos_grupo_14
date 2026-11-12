"""Logos de las escuderías para los gráficos (Altair `mark_image`) y la interfaz.

Lee `assets/escuderias/<TeamId>.svg` (o .png / .webp) y lo devuelve como data URI, así el
gráfico no depende de archivos servidos aparte. Si un equipo no tiene logo, devuelve None y el
gráfico muestra solo el nombre.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import pandas as pd

from graficos import colores as C

CARPETA = Path(__file__).resolve().parent.parent / "assets" / "escuderias"
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}


@lru_cache(maxsize=None)
def uri(team: str) -> str | None:
    ruta = next((p for ext in _MIME if (p := CARPETA / f"{team}{ext}").exists()), None)
    if ruta is None:
        return None
    return f"data:{_MIME[ruta.suffix]};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


def nombre(team: str) -> str:
    return C.NOMBRES_ESCUDERIAS.get(team, team.replace("_", " ").title())


def tabla(teams) -> pd.DataFrame:
    """Una fila por escudería: TeamId, nombre para mostrar y logo (data URI o vacío)."""
    teams = sorted(set(teams))
    return pd.DataFrame({"team": teams, "Escudería": [nombre(t) for t in teams],
                         "logo": [uri(t) or "" for t in teams]})
