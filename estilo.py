"""La identidad de Fórmula 1 de la app: la página es una vuelta al circuito.

Nada de esto toca los datos ni los gráficos: es HTML y CSS que Streamlit inserta alrededor.

    Vuelta de formación   portada: semáforo de largada (5 luces que se encienden y se apagan) y un
                          circuito que se dibuja con un auto dando vueltas.
    Sectores 1, 2 y 3     el tallo: cada sección arranca con su cartel de sector, como en la
                          transmisión, y se separa de la siguiente con un piano (kerb) rojo y blanco.
    Pit lane / boxes      la copa: el usuario toma el control.
    Bandera a cuadros     el cierre.

El recorrido:
- Una barra fija abajo, como el zócalo de la transmisión, marca en qué parte de la vuelta estás y
  se llena a medida que bajás (animación ligada al scroll, CSS `scroll-timeline`).
- Cada bloque entra deslizándose cuando aparece en pantalla (`animation-timeline: view()`).
Las dos animaciones usan CSS moderno: en navegadores que no lo soportan, la página se ve igual pero
quieta. Y si el sistema pide menos movimiento (`prefers-reduced-motion`), no se anima nada.

No usa logos ni marcas de la F1 ni de los equipos: solo colores, tipografía y formas genéricas.
"""

from __future__ import annotations

import streamlit as st

ROJO = "#E10600"
FONDO = "#15151E"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&display=swap');

/* ---------- base ---------- */
.stApp {{ background: {FONDO}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
h1, h2, h3, .f1-titulo, [data-testid="stMetricValue"] {{
    font-family: 'Titillium Web', 'Segoe UI', sans-serif !important;
}}
h1 {{ font-weight: 900 !important; letter-spacing: -0.01em; }}
h2 {{ font-weight: 700 !important; }}
[data-testid="stMainBlockContainer"] {{ padding-bottom: 6rem; }}

/* la página es el circuito: la línea de largada a la izquierda */
[data-testid="stMain"] {{ scroll-timeline: --vuelta y; scroll-behavior: smooth; }}

/* ---------- números como la torre de tiempos ---------- */
[data-testid="stMetric"] {{
    background: linear-gradient(90deg, #1F1F2B 0%, #1A1A24 100%);
    border-left: 5px solid {ROJO}; border-radius: 4px; padding: 14px 18px;
}}
[data-testid="stMetricValue"] {{ font-weight: 900; font-variant-numeric: tabular-nums; }}
[data-testid="stMetricLabel"] p {{ text-transform: uppercase; letter-spacing: .06em; font-size: .78rem !important; color: #B8B8C4; }}

/* ---------- desplegables «Cómo lo sabemos»: como la telemetría del box ---------- */
[data-testid="stExpander"] details {{ border: 1px solid #2E2E3A; border-left: 3px solid #6A6A78; background: #18181F; }}
[data-testid="stExpander"] summary p {{ font-family: 'Titillium Web', sans-serif; font-weight: 700; letter-spacing: .04em; }}

/* ---------- pestañas: como selector de cámara ---------- */
button[data-baseweb="tab"] p {{ font-family: 'Titillium Web', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }}

/* ---------- semáforo de largada ---------- */
.f1-largada {{ position: relative; padding: 28px 0 8px; }}
.f1-semaforo {{ display: flex; gap: 14px; margin: 0 0 22px; }}
.f1-columna {{ background: #0B0B0F; border-radius: 10px; padding: 8px 7px; display: flex; flex-direction: column; gap: 7px;
               box-shadow: inset 0 0 0 2px #26262F; }}
.f1-luz {{ width: 30px; height: 30px; border-radius: 50%; background: #2A0303; }}
.f1-luz.roja {{ animation: f1-prender 4.2s forwards; }}
.f1-columna:nth-child(1) .roja {{ animation-delay: .3s; }}
.f1-columna:nth-child(2) .roja {{ animation-delay: .9s; }}
.f1-columna:nth-child(3) .roja {{ animation-delay: 1.5s; }}
.f1-columna:nth-child(4) .roja {{ animation-delay: 2.1s; }}
.f1-columna:nth-child(5) .roja {{ animation-delay: 2.7s; }}
@keyframes f1-prender {{
    0% {{ background: #2A0303; box-shadow: none; }}
    3%, 92% {{ background: {ROJO}; box-shadow: 0 0 18px 4px rgba(225,6,0,.75); }}
    100% {{ background: #2A0303; box-shadow: none; }}
}}
.f1-fuera {{ font-family: 'Titillium Web', sans-serif; font-weight: 900; letter-spacing: .3em; color: {ROJO};
             font-size: .85rem; opacity: 0; animation: f1-aparecer .5s 4.4s forwards; }}
.f1-largada h1, .f1-largada .f1-sub, .f1-largada .f1-circuito {{ opacity: 0; animation: f1-subir .9s forwards; }}
.f1-largada h1 {{ animation-delay: 4.5s; font-size: 3.1rem; line-height: 1.05; max-width: 22ch; margin: 6px 0 14px; }}
.f1-largada .f1-sub {{ animation-delay: 4.9s; font-size: 1.25rem; color: #C8C8D0; max-width: 62ch; }}
.f1-largada .f1-circuito {{ animation-delay: 4.2s; position: absolute; right: 0; top: 10px; width: 38%; max-width: 460px; }}
@keyframes f1-aparecer {{ to {{ opacity: 1; }} }}
@keyframes f1-subir {{ from {{ opacity: 0; transform: translateY(18px); }} to {{ opacity: 1; transform: none; }} }}

/* el circuito se dibuja y un auto da vueltas */
.f1-pista {{ fill: none; stroke: #3A3A48; stroke-width: 16; stroke-linecap: round; stroke-linejoin: round; }}
.f1-trazo {{ fill: none; stroke: {ROJO}; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round;
             stroke-dasharray: 1400; stroke-dashoffset: 1400; animation: f1-dibujar 2.6s 4.4s ease-out forwards; }}
@keyframes f1-dibujar {{ to {{ stroke-dashoffset: 0; }} }}

/* ---------- cartel de sector ---------- */
.f1-sector {{ display: flex; align-items: stretch; gap: 0; margin: 10px 0 4px; font-family: 'Titillium Web', sans-serif; }}
.f1-sector .num {{ background: {ROJO}; color: white; font-weight: 900; padding: 4px 14px; font-size: 1.05rem;
                   clip-path: polygon(0 0, 100% 0, 88% 100%, 0 100%); padding-right: 22px; }}
.f1-sector .nombre {{ background: #22222D; color: #F0F0F0; font-weight: 700; padding: 4px 16px; letter-spacing: .12em;
                      text-transform: uppercase; font-size: .95rem; }}
.f1-sector .mini {{ display: flex; gap: 3px; align-items: center; padding-left: 10px; }}
.f1-sector .mini i {{ display: block; width: 22px; height: 6px; border-radius: 2px; background: #3A3A48; }}
.f1-sector .mini i.on {{ background: var(--c); }}

/* ---------- piano (kerb) entre secciones ---------- */
.f1-kerb {{ height: 12px; margin: 44px 0 30px; border-radius: 2px;
            background: repeating-linear-gradient(90deg, {ROJO} 0 34px, #F4F4F4 34px 68px);
            transform: skewX(-25deg); opacity: .9; }}

/* ---------- pit lane ---------- */
.f1-pit {{ margin: 10px 0 18px; padding: 22px 26px; border-radius: 6px; position: relative; overflow: hidden;
           background: repeating-linear-gradient(-45deg, #1C1C24 0 18px, #20202A 18px 36px); border: 1px solid #2E2E3A; }}
.f1-pit .linea {{ position: absolute; left: 0; right: 0; bottom: 12px; height: 4px;
                  background: repeating-linear-gradient(90deg, #F4F4F4 0 26px, transparent 26px 46px); opacity: .7; }}
.f1-pit .cartel {{ display: inline-block; background: #F4F4F4; color: #111; font-family: 'Titillium Web', sans-serif;
                   font-weight: 900; padding: 2px 12px; letter-spacing: .2em; border-radius: 3px; margin-right: 12px; }}
.f1-pit .limite {{ display: inline-flex; width: 46px; height: 46px; border-radius: 50%; border: 5px solid {ROJO};
                   background: #F4F4F4; color: #111; font-weight: 900; align-items: center; justify-content: center;
                   font-family: 'Titillium Web', sans-serif; float: right; }}
.f1-pit h2 {{ margin: 10px 0 4px !important; }}
.f1-pit p {{ color: #C8C8D0; margin: 0 0 14px; max-width: 70ch; }}

/* ---------- bandera a cuadros ---------- */
.f1-bandera {{ margin: 40px 0 10px; border-radius: 8px; overflow: hidden; position: relative; }}
.f1-bandera .cuadros {{ height: 70px; background: conic-gradient(#F4F4F4 25%, #111 0 50%, #F4F4F4 0 75%, #111 0) 0 0 / 35px 35px;
                        animation: f1-flamear 2.5s ease-in-out infinite alternate; transform-origin: left center; }}
@keyframes f1-flamear {{ from {{ transform: skewY(0deg); }} to {{ transform: skewY(-1.5deg); }} }}
.f1-bandera .texto {{ background: #1C1C24; padding: 22px 26px; }}
.f1-bandera .texto b {{ font-family: 'Titillium Web', sans-serif; font-size: 1.5rem; font-weight: 900; display: block; margin-bottom: 6px; }}
.f1-bandera a {{ color: {ROJO}; font-weight: 700; text-decoration: none; }}

/* ---------- zócalo fijo: la vuelta ---------- */
.f1-zocalo {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 999990; height: 42px; display: flex;
              align-items: center; gap: 0; background: rgba(12,12,16,.94); border-top: 2px solid {ROJO};
              font-family: 'Titillium Web', sans-serif; backdrop-filter: blur(6px); }}
.f1-zocalo .vuelta {{ background: {ROJO}; color: #fff; font-weight: 900; height: 100%; display: flex; align-items: center;
                      padding: 0 16px; letter-spacing: .12em; font-size: .85rem; }}
.f1-zocalo nav {{ display: flex; flex: 1; height: 100%; }}
.f1-zocalo nav a {{ flex: 1; display: flex; align-items: center; justify-content: center; color: #C8C8D0; text-decoration: none;
                    font-weight: 700; font-size: .8rem; letter-spacing: .1em; text-transform: uppercase; border-left: 1px solid #26262F; }}
.f1-zocalo nav a:hover {{ color: #fff; background: #1F1F2B; }}
.f1-progreso {{ position: absolute; left: 0; top: -2px; height: 2px; width: 100%; background: #F4F4F4;
                transform-origin: left; transform: scaleX(0); }}

@supports (animation-timeline: scroll()) {{
  @media (prefers-reduced-motion: no-preference) {{
    .f1-progreso {{ animation: f1-llenar linear both; animation-timeline: --vuelta; }}
    @keyframes f1-llenar {{ to {{ transform: scaleX(1); }} }}
    /* cada bloque entra a pista cuando aparece en pantalla */
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:not(:has(.f1-zocalo, .f1-largada, style)),
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > [data-testid="stExpander"] {{
        animation: f1-entrar linear both; animation-timeline: view(); animation-range: entry 0% entry 40%;
    }}
    @keyframes f1-entrar {{ from {{ opacity: 0; transform: translateX(-40px); }} to {{ opacity: 1; transform: none; }} }}
    .f1-kerb {{ animation: f1-kerb linear both; animation-timeline: view(); animation-range: entry 0% cover 40%; }}
    @keyframes f1-kerb {{ from {{ clip-path: inset(0 100% 0 0); }} to {{ clip-path: inset(0 0 0 0); }} }}
  }}
}}
/* Con "reducir movimiento" (en Windows: Efectos de animación apagados) se saca lo que se MUEVE,
   pero el semáforo se enciende igual: es un cambio de color, no un movimiento. */
@media (prefers-reduced-motion: reduce) {{
  .f1-largada h1, .f1-largada .f1-sub, .f1-largada .f1-circuito {{ animation-name: f1-aparecer !important; }}
  .f1-trazo {{ animation: none !important; stroke-dashoffset: 0 !important; }}
  .f1-bandera .cuadros {{ animation: none !important; }}
}}
@media (max-width: 900px) {{ .f1-largada .f1-circuito {{ display: none; }} .f1-largada h1 {{ font-size: 2.2rem; }} }}
</style>
"""

# Un circuito genérico (inventado), la misma forma que recorre el auto.
_PISTA = ("M60 200 L150 200 C190 200 200 170 230 150 L300 100 C330 80 370 90 380 120 L390 160 "
          "C395 185 370 200 345 200 L330 200 C300 200 300 235 330 245 L360 255 C380 262 375 290 350 290 "
          "L90 290 C50 290 30 260 40 230 C45 210 50 200 60 200 Z")

SECCIONES = [("largada", "Largada"), ("sector-1", "S1 · Datos"), ("sector-2", "S2 · Hallazgo"),
             ("sector-3", "S3 · Modelo"), ("boxes", "Boxes"), ("bandera", "🏁")]


def _html(codigo: str) -> None:
    st.markdown(codigo, unsafe_allow_html=True)


def aplicar() -> None:
    """El CSS de toda la app y el zócalo fijo de la vuelta. Llamar una vez, arriba de todo."""
    _html(CSS)
    enlaces = "".join(f'<a href="#{ancla}" target="_self">{nombre}</a>' for ancla, nombre in SECCIONES)
    _html(f'<div class="f1-zocalo"><div class="f1-progreso"></div><div class="vuelta">VUELTA 1/1</div>'
          f'<nav>{enlaces}</nav></div>')


def largada(pregunta: str, idea: str) -> None:
    """Portada: el semáforo se enciende luz por luz, se apaga, y aparecen la pregunta y el circuito."""
    columnas = "".join('<div class="f1-columna"><div class="f1-luz"></div><div class="f1-luz roja"></div></div>'
                       for _ in range(5))
    circuito = (f'<svg class="f1-circuito" viewBox="20 70 390 240" aria-hidden="true">'
                f'<path class="f1-pista" d="{_PISTA}"/><path class="f1-trazo" d="{_PISTA}"/>'
                f'<rect x="56" y="188" width="6" height="24" fill="#F4F4F4"/>'
                f'<circle class="f1-auto" r="7" fill="{ROJO}" stroke="#fff" stroke-width="2" opacity="0">'
                f'<set attributeName="opacity" to="1" begin="5.6s"/>'
                f'<animateMotion dur="7s" begin="5.6s" repeatCount="indefinite" path="{_PISTA}"/></circle></svg>')
    _html(f'<div id="largada" class="f1-largada">{circuito}<div class="f1-semaforo">{columnas}</div>'
          f'<div class="f1-fuera">LUCES FUERA · ARRANCA LA VUELTA</div>'
          f'<h1>{pregunta}</h1><p class="f1-sub">{idea}</p></div>')


def sector(numero: int, nombre: str) -> None:
    """Cartel de sector, con los tres minisectores encendidos hasta el actual."""
    colores = ["#FFD12E", "#3DDC84", "#B65CFF"]   # como los minisectores de la transmisión
    mini = "".join(f'<i class="{"on" if i < numero else ""}" style="--c:{c}"></i>' for i, c in enumerate(colores))
    _html(f'<div id="sector-{numero}" class="f1-sector"><span class="num">S{numero}</span>'
          f'<span class="nombre">{nombre}</span><span class="mini">{mini}</span></div>')


def piano() -> None:
    """Separador entre secciones: el piano rojo y blanco del borde de la pista."""
    _html('<div class="f1-kerb"></div>')


def pit_lane(titulo: str, texto: str) -> None:
    """Entrada a la copa: de acá en adelante maneja el usuario."""
    _html(f'<div id="boxes" class="f1-pit"><span class="limite">80</span><span class="cartel">PIT</span>'
          f'<span style="color:#B8B8C4;letter-spacing:.12em;font-weight:700;font-size:.85rem">BOXES ABIERTOS</span>'
          f'<h2>{titulo}</h2><p>{texto}</p><div class="linea"></div></div>')


def bandera(titulo: str, texto: str) -> None:
    """Cierre: bandera a cuadros, la conclusión y volver a largar."""
    _html(f'<div id="bandera" class="f1-bandera"><div class="cuadros"></div><div class="texto">'
          f'<b>{titulo}</b>{texto}<br><br><a href="#largada" target="_self">↺ Volver a largar</a></div></div>')
