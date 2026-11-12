"""Los colores de toda la aplicación, en un solo lugar.

Cada color significa una sola cosa en todos los gráficos (lo pide la consigna):

- MODELO (azul) y GRILLA (naranja): las dos predicciones que se comparan siempre.
- REAL (blanco): lo que pasó en la carrera.
- ABANDONO (gris): los que no terminaron.
- MEJOR / PEOR: el modelo acertó mejor / peor que la grilla.
- Los grupos de variables del modelo usan otra paleta, que NO repite el azul ni el naranja.
- Las escuderías, sus colores de identidad.

Los módulos de `graficos/` importan de acá: si un color cambia, cambia en toda la app.
"""

# Fondo y tinta (tema oscuro fijo)
ASPHALT = "#26282C"     # fondo
LANE = "#3A3D43"        # grillas y bordes
INK = "#E8EAED"         # texto principal
INK_MUTED = "#9AA0A6"   # texto secundario

# Lo que se compara
MODELO = "#3987e5"
GRILLA = "#d95926"
REAL = INK
ABANDONO = "#8A8F98"
PISO = "#5F6368"
MEJOR = "#4CC38A"       # el modelo acierta mejor que la grilla (con ▲)
PEOR = "#F2685B"        # el modelo acierta peor que la grilla (con ▼)

# Grupos de variables del modelo (verde, ámbar, rosa, violeta, gris): ninguno es azul ni naranja.
GRUPOS = ["#199e70", "#c98500", "#d55181", "#9b7bd6", "#7f8c8d", "#5ab4ac"]

# Escuderías (colores de identidad aproximados; los compañeros de equipo comparten color).
ESCUDERIAS = {
    "mclaren": "#FF8000", "ferrari": "#E8002D", "mercedes": "#27F4D2",
    "red_bull": "#3671C6", "williams": "#64C4FF", "aston_martin": "#229971",
    "alpine": "#0093CC", "haas": "#B6BABD", "rb": "#6692FF", "alphatauri": "#5E8FAA",
    "toro_rosso": "#469BFF", "sauber": "#52E252", "alfa": "#C92D4B", "audi": "#F50537",
    "cadillac": "#D4AF37", "renault": "#FFF500", "force_india": "#F596C8",
    "racing_point": "#F596C8",
}
ESCUDERIA_DEFECTO = "#9AA0A6"

# Ejes con la misma tinta en todos los gráficos
EJES = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LANE, domainColor=LANE, tickColor=LANE)
