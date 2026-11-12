# Logos de las escuderías (opcional)

La banda de escuderías del encabezado de la app muestra, para cada equipo, su color de identidad
y su nombre. Si en esta carpeta hay un archivo con el `TeamId` del equipo, muestra el logo en vez
del nombre:

```
assets/escuderias/<TeamId>.svg   (o .png / .webp)
```

Los `TeamId` son los del dataset: `mclaren`, `ferrari`, `mercedes`, `red_bull`, `williams`,
`aston_martin`, `alpine`, `haas`, `rb`, `audi`, `cadillac` (y los de temporadas anteriores:
`alphatauri`, `toro_rosso`, `sauber`, `alfa`, `renault`, `force_india`, `racing_point`).

Los logos se muestran en blanco (el fondo es oscuro), salvo los de `LOGO_EN_COLOR` en `estilo.py`.

Los logos son marcas registradas de cada equipo: usarlos solo en el contexto académico del
proyecto y revisar la licencia de donde se descarguen.
