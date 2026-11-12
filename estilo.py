"""Look and feel F1 de la app: CSS, encabezado, franja de escuderías y pie.

Solo decoración: no cambia ningún dato ni texto del análisis. Los archivos están en `assets/`:
  estilo.css            el estilo de la interfaz (rojo F1, piano, bandera a cuadros)
  logo.svg              la marca del grupo
  escuderias/<TeamId>   logos opcionales de cada equipo (ver assets/escuderias/LEEME.md)
"""
from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from graficos import colores as C

ASSETS = Path(__file__).resolve().parent / "assets"
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}

# Nombre corto de cada escudería (para la franja, si no hay logo).
NOMBRES = {
    "mclaren": "McLaren", "ferrari": "Ferrari", "mercedes": "Mercedes", "red_bull": "Red Bull",
    "williams": "Williams", "aston_martin": "Aston Martin", "alpine": "Alpine", "haas": "Haas",
    "rb": "Racing Bulls", "alphatauri": "AlphaTauri", "toro_rosso": "Toro Rosso",
    "sauber": "Sauber", "alfa": "Alfa Romeo", "audi": "Audi", "cadillac": "Cadillac",
    "renault": "Renault", "force_india": "Force India", "racing_point": "Racing Point",
}


def _data_uri(ruta: Path) -> str:
    return f"data:{_MIME[ruta.suffix]};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


def _logo_escuderia(team: str) -> Path | None:
    return next((p for ext in _MIME if (p := ASSETS / "escuderias" / f"{team}{ext}").exists()), None)


def aplicar() -> None:
    """Carga el CSS de la app."""
    st.html(f"<style>{(ASSETS / 'estilo.css').read_text(encoding='utf-8')}</style>")


def encabezado(equipos: list[str], subtitulo: str) -> None:
    """Marca del grupo y franja con el color (o logo) de cada escudería, en el orden dado."""
    chips = []
    for team in equipos:
        nombre = NOMBRES.get(team, team.replace("_", " ").title())
        color = C.ESCUDERIAS.get(team, C.ESCUDERIA_DEFECTO)
        logo = _logo_escuderia(team)
        dentro = (f'<img src="{_data_uri(logo)}" alt="{html.escape(nombre)}">' if logo
                  else html.escape(nombre))
        chips.append(f'<div class="f1-escuderia" style="--equipo:{color}" '
                     f'title="{html.escape(nombre)}">{dentro}</div>')
    st.html(
        f'<div class="f1-hero"><img src="{_data_uri(ASSETS / "logo.svg")}" alt="">'
        f'<div class="f1-marca"><b>Fórmula 1 · Grupo 14</b>'
        f'<span>{html.escape(subtitulo)}</span></div></div>'
        f'<div class="f1-parrilla" aria-hidden="true">{"".join(chips)}</div>')


def pie(texto_izq: str, texto_der: str) -> None:
    st.html(f'<div class="f1-pie"><span>{html.escape(texto_izq)}</span>'
            f'<span>{html.escape(texto_der)}</span></div>')
