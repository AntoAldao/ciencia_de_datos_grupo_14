"""Look and feel F1 de la página: menú lateral, encabezado, títulos de sección y pie, como HTML.

Solo decoración y navegación: no cambia ningún dato ni texto del análisis. Lo usa `web/pagina.py`
para armar `site/index.html`. Archivos en `assets/`:
  estilo.css            el estilo de la interfaz (papel, piano, bandera a cuadros)
  logo.svg              logo de la Fórmula 1
  escuderias/<TeamId>   logos de cada equipo (ver assets/escuderias/LEEME.md)
  tires/                neumáticos: uno por sección del tallo (blando, medio, duro)
  circuit1..4.svg       trazados de circuitos, de marca de agua en los títulos

La página es una copa de martini: el tallo (secciones 1 a 3) lo guía el autor y la copa (Explorá y
Probá el modelo) la maneja el usuario. El menú lateral muestra esas dos partes.
"""
from __future__ import annotations

import base64
import html
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image

from graficos import colores as C
from graficos import logos

ASSETS = Path(__file__).resolve().parent / "assets"
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}

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


def _rueda(numero: int, alto: int = 160) -> str:
    compuesto = RUEDAS.get(numero, "hard")
    ruta = next(p for ext in (".webp", ".png") if (p := ASSETS / "tires" / f"{compuesto}{ext}").exists())
    return _data_uri(ruta, alto)


def _circuito(numero: int) -> str:
    return _data_uri(ASSETS / f"{CIRCUITOS.get(numero, 'circuit4')}.svg")


def _color(team: str) -> str:
    return C.ESCUDERIAS.get(team, C.ESCUDERIA_DEFECTO)


def menu(recorrido: list[str], explorar: list[tuple[str, str, str]],
         subpartes: dict[int, list[tuple[str, str]]] | None = None) -> str:
    """Menú lateral: la pregunta, el recorrido (los tres sectores, en orden, con el número de
    su título; `subpartes`: entradas debajo de un sector, (texto, ancla)) y las partes para
    explorar por tu cuenta. Cada rótulo es una versión corta del título al que lleva."""
    subpartes = subpartes or {}
    pasos_tallo = "".join(
        f'<a class="f1-nav-item" href="#seccion-{i}"><img src="{_rueda(i, 64)}" alt="">'
        f'<span><small>Sector {i}</small>{html.escape(t)}</span></a>'
        + "".join(f'<a class="f1-nav-item sub" href="#{ancla}"><span>{html.escape(texto)}</span></a>'
                  for texto, ancla in subpartes.get(i, []))
        for i, t in enumerate(recorrido, start=1))
    pasos_explorar = "".join(   # (texto, ancla, ícono): cada uno lleva a su propia sección
        f'<a class="f1-nav-item explorar" href="#{ancla}"><i>{icono}</i>'
        f'<span>{html.escape(t)}</span></a>' for t, ancla, icono in explorar)
    return (
        f'<nav class="f1-nav" aria-label="Índice">'
        f'<a class="f1-nav-logo" href="#portada"><img src="{_data_uri(ASSETS / "logo.svg")}" '
        f'alt="Fórmula 1"><b>Grupo 14</b></a>'
        f'<a class="f1-nav-item portada" href="#portada"><i>🏁</i><span>La pregunta</span></a>'
        f'<div class="f1-nav-parte"><b>El recorrido</b><span>de los datos al modelo</span></div>'
        f'<div class="f1-nav-grupo">{pasos_tallo}</div>'
        f'<div class="f1-nav-parte"><b>Explorá por tu cuenta</b><span>temporadas, carreras y el modelo</span></div>'
        f'<div class="f1-nav-grupo explorar">{pasos_explorar}</div>'
        f'</nav>')


def encabezado(equipos: list[str], subtitulo: str) -> str:
    """Logo F1, marca del grupo y la banda de escuderías (decorativa, no se puede tocar)."""
    items = []
    for team in equipos:
        nombre = logos.nombre(team)
        logo = logos.uri(team)
        dentro = (f'<img src="{logo}" alt="{html.escape(nombre)}">' if logo
                  else f'<span>{html.escape(nombre)}</span>')
        items.append(f'<div class="f1-escuderia" style="--equipo:{_color(team)}">{dentro}</div>')
    return (
        f'<div id="portada" class="f1-hero" style="--circuito:url({_circuito(4)})">'
        f'<img class="f1-hero-logo" src="{_data_uri(ASSETS / "logo.svg")}" alt="Fórmula 1">'
        f'<div class="f1-marca"><b>Grupo 14</b><span>{html.escape(subtitulo)}</span></div></div>'
        f'<div class="f1-parrilla" role="img" aria-label="Escuderías">{"".join(items)}</div>')


def parte(id_: str, nombre: str, bajada: str) -> str:
    """Rótulo que marca dónde empieza cada parte de la página (y ancla del menú)."""
    return (f'<div id="{id_}" class="f1-parte"><b>{html.escape(nombre)}</b>'
            f'<span>{html.escape(bajada)}</span></div>')


def seccion(numero: int, titulo: str) -> str:
    """Título de una sección del tallo: neumático + título + trazado de circuito de fondo."""
    return (
        f'<div id="seccion-{numero}" class="f1-seccion" style="--circuito:url({_circuito(numero)})">'
        f'<img class="f1-rueda" src="{_rueda(numero)}" alt="">'
        f'<h2>{html.escape(f"{numero}. {titulo}")}</h2></div>')


def pie(texto_izq: str, texto_der: str) -> str:
    return (f'<div class="f1-pie"><span>{html.escape(texto_izq)}</span>'
            f'<span>{html.escape(texto_der)}</span></div>')
