"""Los colores de toda la aplicación, en un solo lugar.

Cada color significa una sola cosa en todos los gráficos (lo pide la consigna):

- MODELO (azul) y GRILLA (ámbar): las dos predicciones que se comparan siempre.
- REAL (blanco): lo que pasó en la carrera.
- ABANDONO (gris): los que no terminaron.
- MEJOR / PEOR: el modelo acertó mejor / peor que la grilla (siempre con ▲ / ▼).
- Los grupos de variables del modelo usan otra paleta, que NO repite el azul ni el ámbar.
- Las escuderías, sus colores de identidad (esos NO se tocan: el color es la marca).

Apta para daltónicos: todo lo que significa algo se eligió para que se distinga también con
protanopía, deuteranopía y tritanopía (simulación de Machado et al., 2009, distancia en OKLab).
Por eso nada se apoya en el par rojo/verde: azul contra ámbar, y MEJOR / PEOR se separan por
luminosidad (claro contra oscuro) además de por el tono y el símbolo.

Los rojos de la "identidad F1" (F1_ROJO, bordes de pista) son solo decoración de la interfaz:
nunca codifican un dato.

Los módulos de `graficos/` importan de acá: si un color cambia, cambia en toda la app.
"""

# Fondo y tinta (tema oscuro fijo)
ASPHALT = "#26282C"     # fondo
LANE = "#3A3D43"        # grillas y bordes
INK = "#E8EAED"         # texto principal
INK_MUTED = "#9AA0A6"   # texto secundario

# Lo que se compara
MODELO = "#3B8FE5"      # azul
GRILLA = "#E69F00"      # ámbar (Okabe-Ito): se separa del azul con cualquier tipo de daltonismo
REAL = INK
ABANDONO = "#8A8F98"
PISO = "#5F6368"
MEJOR = "#9EEBCF"       # el modelo acierta mejor que la grilla (con ▲): menta claro
PEOR = "#D94A7E"        # el modelo acierta peor que la grilla (con ▼): frambuesa, más oscuro

# Grupos de variables del modelo (verde azulado, amarillo, rosa claro, ocre, lavanda y un gris
# oscuro para «Otras»): ninguno es azul ni ámbar y se distinguen con daltonismo.
GRUPOS = ["#2E9C86", "#F0E442", "#F5B8D2", "#A8782E", "#9C8BE0", "#6B6F76"]

# Identidad F1 de la interfaz (solo decoración, nunca un dato)
F1_ROJO = "#E10600"
CARBONO = "#15151E"     # paneles oscuros tipo fibra de carbono
FUENTE = "Titillium Web, sans-serif"

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
