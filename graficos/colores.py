"""Los colores de toda la aplicación, en un solo lugar.

Cada color significa una sola cosa en todos los gráficos (lo pide la consigna):

- MODELO (azul) y GRILLA (ámbar): las dos predicciones que se comparan siempre.
- REAL (tinta, casi negro): lo que pasó en la carrera.
- ABANDONO (gris): los que no terminaron.
- MEJOR / PEOR: el modelo acertó mejor / peor que la grilla (siempre con ▲ / ▼).
- Los grupos de variables del modelo usan otra paleta, que NO repite el azul ni el ámbar.
- Las escuderías, sus colores de identidad (esos NO se tocan: el color es la marca).

Apta para daltónicos: todo lo que significa algo se eligió para que se distinga también con
protanopía, deuteranopía y tritanopía (simulación de Machado et al., 2009, distancia en OKLab).
Por eso nada se apoya en el par rojo/verde: azul contra ámbar, y MEJOR / PEOR se separan por
luminosidad (verde claro contra vino oscuro) además de por el tono y el símbolo.
Validada sobre el fondo claro tipo papel (FONDO): el texto principal tiene contraste 13:1.

Los rojos de la "identidad F1" (F1_ROJO, bordes de pista) son solo decoración de la interfaz:
nunca codifican un dato.

Los módulos de `graficos/` importan de acá: si un color cambia, cambia en toda la app.
"""

# Fondo y tinta (tema claro tipo papel: ni blanco ni gris, no cansa la vista)
FONDO = "#F4EFE6"       # papel: fondo de la app y de los gráficos
PANEL = "#FBF8F2"       # tarjetas y paneles, apenas más claros que el papel
LINEA = "#DDD5C7"       # grillas y bordes
INK = "#1F2328"         # texto principal (casi negro)
INK_MUTED = "#575C63"   # texto secundario

# Lo que se compara
MODELO = "#2166AC"      # azul
GRILLA = "#B8660B"      # ámbar oscuro: se separa del azul con cualquier tipo de daltonismo
REAL = INK
ABANDONO = "#8A8F98"
PISO = "#5F6368"
MEJOR = "#52B788"       # el modelo acierta mejor que la grilla (con ▲): verde claro
MEJOR_TEXTO = "#2F855A" # el mismo verde, más oscuro, para texto chico
PEOR = "#6A1B4D"        # el modelo acierta peor que la grilla (con ▼): vino, mucho más oscuro

# Grupos de variables del modelo (verde azulado, arena, rosa, índigo, vino y gris para «Otras»):
# ninguno es azul ni ámbar y se distinguen con daltonismo.
GRUPOS = ["#469990", "#B8A44A", "#E377C2", "#332288", "#882255", "#8A8F98"]

# Identidad F1 de la interfaz (solo decoración, nunca un dato)
F1_ROJO = "#E10600"
CARBONO = "#15151E"     # negro de los neumáticos y la bandera a cuadros
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

# Nombre de cada escudería para mostrar
NOMBRES_ESCUDERIAS = {
    "mclaren": "McLaren", "ferrari": "Ferrari", "mercedes": "Mercedes", "red_bull": "Red Bull",
    "williams": "Williams", "aston_martin": "Aston Martin", "alpine": "Alpine", "haas": "Haas",
    "rb": "Racing Bulls", "alphatauri": "AlphaTauri", "toro_rosso": "Toro Rosso",
    "sauber": "Sauber", "alfa": "Alfa Romeo", "audi": "Audi", "cadillac": "Cadillac",
    "renault": "Renault", "force_india": "Force India", "racing_point": "Racing Point",
}

# Ejes con la misma tinta en todos los gráficos
EJES = dict(labelColor=INK_MUTED, titleColor=INK_MUTED, gridColor=LINEA, domainColor=LINEA, tickColor=LINEA)
