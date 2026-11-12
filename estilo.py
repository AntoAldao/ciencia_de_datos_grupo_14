"""Look and feel F1 de la app: CSS, encabezado, títulos de sección y pie.

Solo decoración: no cambia ningún dato ni texto del análisis. Los archivos están en `assets/`:
  estilo.css            el estilo de la interfaz (piano, bandera a cuadros, tablero de tiempos)
  logo.svg              logo de la Fórmula 1
  escuderias/<TeamId>   logos de cada equipo (ver assets/escuderias/LEEME.md)
  tires/                neumáticos: uno por sección del tallo (blanda, media, dura)
  circuit1..4.svg       trazados de circuitos, de marca de agua en los títulos
"""
from __future__ import annotations

import base64
import html
import io
from functools import lru_cache
from pathlib import Path

import streamlit as st
from PIL import Image

from graficos import colores as C

ASSETS = Path(__file__).resolve().parent / "assets"
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}

# Nombre de cada escudería (texto alternativo del logo, o el nombre si no hay logo).
NOMBRES = {
    "mclaren": "McLaren", "ferrari": "Ferrari", "mercedes": "Mercedes", "red_bull": "Red Bull",
    "williams": "Williams", "aston_martin": "Aston Martin", "alpine": "Alpine", "haas": "Haas",
    "rb": "Racing Bulls", "alphatauri": "AlphaTauri", "toro_rosso": "Toro Rosso",
    "sauber": "Sauber", "alfa": "Alfa Romeo", "audi": "Audi", "cadillac": "Cadillac",
    "renault": "Renault", "force_india": "Force India", "racing_point": "Racing Point",
}
# Logos que se muestran con sus colores; el resto va en blanco (son oscuros sobre fondo oscuro).
LOGO_EN_COLOR = {"ferrari"}

# Neumático y circuito de cada sección del tallo (como los compuestos de una carrera).
RUEDAS = {1: "soft", 2: "medium", 3: "hard"}
CIRCUITOS = {1: "circuit1", 2: "circuit2", 3: "circuit3"}


@lru_cache(maxsize=None)
def _data_uri(ruta: Path, alto: int = 0) -> str:
    """Imagen como data URI. Las de mapa de bits se achican a `alto` px (los originales son
    enormes) y se pasan a WebP para que la página no pese de más."""
    if ruta.suffix == ".svg" or not alto:
        datos, mime = ruta.read_bytes(), _MIME[ruta.suffix]
    else:
        img = Image.open(ruta).convert("RGBA")
        img.thumbnail((alto, alto))
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=90)
        datos, mime = buf.getvalue(), "image/webp"
    return f"data:{mime};base64,{base64.b64encode(datos).decode()}"


@lru_cache(maxsize=None)
def _circuito(nombre: str) -> str:
    """Trazado de circuito en tinta clara (los SVG vienen en negro)."""
    svg = (ASSETS / f"{nombre}.svg").read_text(encoding="utf-8")
    svg = svg.replace('fill="#000000"', f'fill="{C.INK}"')
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"


def _rueda(compuesto: str) -> Path:
    return next(p for ext in (".webp", ".png") if (p := ASSETS / "tires" / f"{compuesto}{ext}").exists())


def _logo_escuderia(team: str) -> Path | None:
    return next((p for ext in _MIME if (p := ASSETS / "escuderias" / f"{team}{ext}").exists()), None)


def aplicar() -> None:
    """Carga el CSS de la app."""
    st.html(f"<style>{(ASSETS / 'estilo.css').read_text(encoding='utf-8')}</style>")


def encabezado(equipos: list[str], subtitulo: str) -> None:
    """Logo F1, marca del grupo y la banda de escuderías (decorativa, no se puede tocar)."""
    items = []
    for team in equipos:
        nombre = NOMBRES.get(team, team.replace("_", " ").title())
        color = C.ESCUDERIAS.get(team, C.ESCUDERIA_DEFECTO)
        logo = _logo_escuderia(team)
        clase = "f1-logo color" if team in LOGO_EN_COLOR else "f1-logo"
        dentro = (f'<img class="{clase}" src="{_data_uri(logo)}" alt="{html.escape(nombre)}">'
                  if logo else f'<span>{html.escape(nombre)}</span>')
        items.append(f'<div class="f1-escuderia" style="--equipo:{color}">{dentro}</div>')
    st.html(
        f'<div class="f1-hero" style="--circuito:url({_circuito("circuit4")})">'
        f'<img class="f1-hero-logo" src="{_data_uri(ASSETS / "logo.svg")}" alt="Fórmula 1">'
        f'<div class="f1-marca"><b>Grupo 14</b><span>{html.escape(subtitulo)}</span></div></div>'
        f'<div class="f1-parrilla" role="img" aria-label="Escuderías">{"".join(items)}</div>')


def seccion(numero: int, titulo: str) -> None:
    """Título de una sección del tallo: neumático + título + trazado de circuito de fondo."""
    rueda = _data_uri(_rueda(RUEDAS.get(numero, "hard")), alto=160)
    circuito = _circuito(CIRCUITOS.get(numero, "circuit4"))
    st.html(
        f'<div class="f1-seccion" style="--circuito:url({circuito})">'
        f'<img class="f1-rueda" src="{rueda}" alt="">'
        f'<h2>{html.escape(f"{numero}. {titulo}")}</h2></div>')


def pie(texto_izq: str, texto_der: str) -> None:
    st.html(f'<div class="f1-pie"><span>{html.escape(texto_izq)}</span>'
            f'<span>{html.escape(texto_der)}</span></div>')
