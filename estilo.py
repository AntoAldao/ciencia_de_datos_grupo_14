"""Look and feel F1 de la app: CSS, menú lateral, encabezado, títulos de sección y pie.

Solo decoración y navegación: no cambia ningún dato ni texto del análisis. Archivos en `assets/`:
  estilo.css            el estilo de la interfaz (papel, piano, bandera a cuadros)
  logo.svg              logo de la Fórmula 1
  escuderias/<TeamId>   logos de cada equipo (ver assets/escuderias/LEEME.md)
  tires/                neumáticos: uno por sección del tallo (blando, medio, duro)
  circuit1..4.svg       trazados de circuitos, de marca de agua en los títulos

La app es una copa de martini: el tallo (secciones 1 a 3) lo guía el autor y la copa (Explorá y
Probá el modelo) la maneja el usuario. El menú lateral muestra esas dos partes.
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


def aplicar() -> None:
    """Carga el CSS de la app (estilo.css y, encima, la vuelta al circuito de vuelta.css) y el
    zócalo fijo. Llamar una vez, arriba de todo."""
    css = "".join((ASSETS / f).read_text(encoding="utf-8") for f in ("estilo.css", "vuelta.css"))
    st.html(f"<style>{css}</style>")
    zocalo()


def menu(recorrido: list[str], explorar: list[tuple[str, str, str]]) -> None:
    """Menú lateral: el objetivo, el recorrido (los tres sectores, en orden) y las partes para
    explorar por tu cuenta. Los nombres son para el usuario, no la estructura del relato."""
    pasos_tallo = "".join(
        f'<a class="f1-nav-item" href="#seccion-{i}"><img src="{_rueda(i, 64)}" alt="">'
        f'<span><small>Sector {i}</small>{html.escape(t)}</span></a>'
        for i, t in enumerate(recorrido, start=1))
    pasos_explorar = "".join(   # (texto, ancla, ícono): cada uno lleva a su propia sección
        f'<a class="f1-nav-item explorar" href="#{ancla}"><i>{icono}</i>'
        f'<span>{html.escape(t)}</span></a>' for t, ancla, icono in explorar)
    st.sidebar.html(
        f'<div class="f1-nav">'
        f'<a class="f1-nav-logo" href="#portada"><img src="{_data_uri(ASSETS / "logo.svg")}" '
        f'alt="Fórmula 1"><b>Grupo 14</b></a>'
        f'<a class="f1-nav-item portada" href="#portada"><i>🏁</i><span>El objetivo</span></a>'
        f'<div class="f1-nav-parte"><b>El recorrido</b><span>de los datos al modelo</span></div>'
        f'<div class="f1-nav-grupo">{pasos_tallo}</div>'
        f'<div class="f1-nav-parte"><b>Explorá por tu cuenta</b><span>temporadas, carreras y el modelo</span></div>'
        f'<div class="f1-nav-grupo explorar">{pasos_explorar}</div>'
        f'</div>')


def encabezado(equipos: list[str], subtitulo: str) -> None:
    """Logo F1, marca del grupo y la banda de escuderías (decorativa, no se puede tocar)."""
    items = []
    for team in equipos:
        nombre = logos.nombre(team)
        logo = logos.uri(team)
        dentro = (f'<img src="{logo}" alt="{html.escape(nombre)}">' if logo
                  else f'<span>{html.escape(nombre)}</span>')
        items.append(f'<div class="f1-escuderia" style="--equipo:{_color(team)}">{dentro}</div>')
    st.html(
        f'<div id="portada" class="f1-hero" style="--circuito:url({_circuito(4)})">'
        f'<img class="f1-hero-logo" src="{_data_uri(ASSETS / "logo.svg")}" alt="Fórmula 1">'
        f'<div class="f1-marca"><b>Grupo 14</b><span>{html.escape(subtitulo)}</span></div></div>'
        f'<div class="f1-parrilla" role="img" aria-label="Escuderías">{"".join(items)}</div>')


def _color(team: str) -> str:
    return C.ESCUDERIAS.get(team, C.ESCUDERIA_DEFECTO)


def parte(id_: str, nombre: str, bajada: str) -> None:
    """Rótulo que marca dónde empieza cada parte de la página (y ancla del menú)."""
    st.html(f'<div id="{id_}" class="f1-parte"><b>{html.escape(nombre)}</b>'
            f'<span>{html.escape(bajada)}</span></div>')


def seccion(numero: int, titulo: str) -> None:
    """Título de una sección del tallo: neumático + título + trazado de circuito de fondo."""
    st.html(
        f'<div id="seccion-{numero}" class="f1-seccion" style="--circuito:url({_circuito(numero)})">'
        f'<img class="f1-rueda" src="{_rueda(numero)}" alt="">'
        f'<h2>{html.escape(f"{numero}. {titulo}")}</h2></div>')


def pie(texto_izq: str, texto_der: str) -> None:
    st.html(f'<div class="f1-pie"><span>{html.escape(texto_izq)}</span>'
            f'<span>{html.escape(texto_der)}</span></div>')


# ------------------------------------------------------------------------------------------------
# La página como una vuelta al circuito (PR #5, «Identidad de F1 y recorrido»), en el tema claro.
# El CSS está en assets/vuelta.css. Sin logos ni marcas: solo colores, tipografía y formas.
# ------------------------------------------------------------------------------------------------

# Un circuito genérico (inventado), la misma forma que recorre el auto.
_PISTA = ("M60 200 L150 200 C190 200 200 170 230 150 L300 100 C330 80 370 90 380 120 L390 160 "
          "C395 185 370 200 345 200 L330 200 C300 200 300 235 330 245 L360 255 C380 262 375 290 350 290 "
          "L90 290 C50 290 30 260 40 230 C45 210 50 200 60 200 Z")

SECCIONES = [("largada", "Largada"), ("sector-1", "S1 · Datos"), ("sector-2", "S2 · Hallazgo"),
             ("sector-3", "S3 · Modelo"), ("boxes", "Boxes"), ("bandera", "🏁")]


def _html(codigo: str) -> None:
    st.markdown(codigo, unsafe_allow_html=True)


def zocalo() -> None:
    """El zócalo fijo abajo, como el de la transmisión: cada nombre lleva a su parte de la vuelta
    y una línea se llena a medida que se baja."""
    enlaces = "".join(f'<a href="#{ancla}" target="_self">{nombre}</a>' for ancla, nombre in SECCIONES)
    _html(f'<div class="f1-zocalo"><div class="f1-progreso"></div><div class="vuelta">VUELTA 1/1</div>'
          f'<nav>{enlaces}</nav></div>')


def largada(pregunta: str, idea: str) -> None:
    """Portada: el semáforo se enciende luz por luz, se apaga, y aparecen la pregunta y el circuito."""
    columnas = "".join('<div class="f1-columna"><div class="f1-luz"></div><div class="f1-luz roja"></div></div>'
                       for _ in range(5))
    circuito = (f'<svg class="f1-circuito" viewBox="20 70 390 240" aria-hidden="true">'
                f'<path class="f1-pista" d="{_PISTA}"/><path class="f1-trazo" d="{_PISTA}"/>'
                f'<rect x="56" y="188" width="6" height="24" fill="#FFFFFF"/>'
                f'<circle class="f1-auto" r="7" fill="{C.F1_ROJO}" stroke="#fff" stroke-width="2" opacity="0">'
                f'<set attributeName="opacity" to="1" begin="5.6s"/>'
                f'<animateMotion dur="7s" begin="5.6s" repeatCount="indefinite" path="{_PISTA}"/></circle></svg>')
    _html(f'<div id="largada" class="f1-largada">{circuito}<div class="f1-semaforo">{columnas}</div>'
          f'<div class="f1-fuera">LUCES FUERA · ARRANCA LA VUELTA</div>'
          f'<h1>{html.escape(pregunta)}</h1><p class="f1-sub">{html.escape(idea)}</p></div>')


def sector(numero: int, nombre: str) -> None:
    """Cartel de sector, con los tres minisectores encendidos hasta el actual."""
    colores = ["#FFD12E", "#3DDC84", "#B65CFF"]   # como los minisectores de la transmisión
    mini = "".join(f'<i class="{"on" if i < numero else ""}" style="--c:{c}"></i>' for i, c in enumerate(colores))
    _html(f'<div id="sector-{numero}" class="f1-sector"><span class="num">S{numero}</span>'
          f'<span class="nombre">{html.escape(nombre)}</span><span class="mini">{mini}</span></div>')


def piano() -> None:
    """Separador entre secciones: el piano rojo y blanco del borde de la pista."""
    _html('<div class="f1-kerb"></div>')


def pit_lane(titulo: str, texto: str) -> None:
    """Entrada a la copa: de acá en adelante maneja el usuario."""
    _html(f'<div id="boxes" class="f1-pit"><span class="limite">80</span><span class="cartel">PIT</span>'
          f'<span class="estado">BOXES ABIERTOS</span>'
          f'<h2>{html.escape(titulo)}</h2><p>{html.escape(texto)}</p><div class="linea"></div></div>')


def bandera(titulo: str, texto: str, pie: str = "") -> None:
    """Cierre: bandera a cuadros, la conclusión y volver a largar."""
    pie_html = f'<br><span class="pie">{html.escape(pie)}</span>' if pie else ""
    _html(f'<div id="bandera" class="f1-bandera"><div class="cuadros"></div><div class="texto">'
          f'<b>{html.escape(titulo)}</b>{html.escape(texto)}{pie_html}<br><br>'
          f'<a href="#largada" target="_self">↺ Volver a largar</a></div></div>')
