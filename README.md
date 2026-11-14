# Ciencia de Datos – Grupo 14 – Fórmula 1

Proyecto integrador de Ciencia de Datos (UTN FRM, 2026). Trabajamos con datos de Fórmula 1
(2018–2026): una fila es **un piloto en un Gran Premio**.

**Aplicación publicada:** <https://antoaldao.github.io/ciencia_de_datos_grupo_14/> (GitHub Pages; ver
[Publicarla](#publicarla-en-github-pages))

## Objetivo

La **Entrega 4** es la versión final del proyecto: una aplicación web publicada en una URL que cuenta
el proyecto entero y deja usarlo. Es la misma aplicación que se muestra en la exposición final del
**25 de noviembre**.

La aplicación tiene forma de copa de martini: primero el tallo, que guía el autor, y después la copa,
que maneja el usuario. El detalle de lo que pide la consigna está en [docs/consigna.md](docs/consigna.md).

## Integrantes

- Aldao, Antonella
- Bataller, Paulina
- Berridy, Ignacio
- Gonzalez, Matías
- Manucha, Juan Pablo 
- Santibañez, Lucía
- Zalazar, Valentín

## Estructura del repositorio

```
ciencia_de_datos_grupo_14/
├── build_app.py          # Datos del pipeline -> notebook de la Entrega 3 -> app_data/ -> site/
├── site/index.html       # Generado por build_app.py: la aplicación, una sola página HTML
├── web/                  # Cómo se arma la aplicación
│   ├── pagina.py         #   arma site/index.html: los textos, las tablas y qué gráfico va dónde
│   ├── pagina.css/.js    #   estilo y comportamiento de la página
│   ├── modelo_json.py    #   exporta el modelo a JSON y verifica que dé igual que sklearn
│   ├── modelo.js         #   el modelo calculado en el navegador («Probá el modelo»)
│   └── probar_modelo.js  #   prueba de modelo.js contra sklearn (la corre build_app.py con node)
├── modelo_entrega3.py    # Clases del notebook de la Entrega 3 + cargar el modelo y predecir
├── estilo.py             # Look and feel F1: menú, encabezado con escuderías, títulos y pie (solo decoración)
├── assets/               # estilo.css, logo.svg y logos opcionales de escuderías (ver su LEEME.md)
│   └── vendor/           #   Vega, Vega-Lite y vega-embed, que van adentro de la página
├── graficos/             # Gráficos de la app (Altair)
│   ├── colores.py        #   los colores de toda la app: cada uno significa una sola cosa (aptos para daltónicos)
│   ├── pasos.py          #   Sector 3 contado en pasos (copa de martini en un gráfico, práctica 7.9)
│   └── panorama.py       #   Explorá: todas las carreras con vistas vinculadas (práctica 6.5)
├── app_data/             # Generado por build_app.py: predicciones, aportes, resumen y modelo.json
├── modelos/              # Modelo que guarda el notebook de la Entrega 3 (joblib)
├── requirements.txt      # Dependencias
├── data/                 # Datos que produce el pipeline (f1_all_full.parquet; v2 = versión anterior)
├── notebooks/            # Entrega 2 (EDA) y Entrega 3 (modelado)
├── docs/consigna.md      # Qué hay que hacer en la Entrega 4
└── CONTRIBUTING.md       # Cómo trabajar con ramas
```

El pipeline de la Entrega 1 (Airflow) vive en este mismo repositorio, en [`pipeline/`](pipeline/)
(ver su README).

## Cómo verla

La aplicación es **una sola página HTML**, `site/index.html`, sin servidor: alcanza con abrirla
en el navegador (doble clic). Vega va adentro del archivo, así que funciona sin internet (lo único
que se pide a la red es la tipografía; sin conexión usa la del sistema).

Tiene los gráficos de Altair (exportados como specs de Vega-Lite y dibujados con vega-embed), las
tablas del notebook en los «Cómo lo sabemos» y «Probá el modelo» calculado en el navegador.

## Cómo se regenera la aplicación

Hace falta Python para **generar** la página (no para verla). Desde la carpeta del repositorio,
según el sistema operativo:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python build_app.py
```

**Linux y macOS (bash/zsh):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_app.py
```

En Linux, si `python3 -m venv` falla porque falta el módulo, instalarlo primero
(en Debian/Ubuntu: `sudo apt install python3-venv`). En macOS, si no está `python3`,
instalarlo con `brew install python` o desde <https://www.python.org/downloads/>.

`build_app.py` tarda alrededor de medio minuto. No entrena nada: usa el modelo que guarda el
notebook de la Entrega 3 en `modelos/`, deja los datos en `app_data/` y genera `site/index.html`.
Después de regenerar, commitear `app_data/` y `site/` juntos: la página sale de esos datos.

Si cambian los datos del pipeline, con el entorno virtual activado:

```bash
# 1. reemplazar data/f1_all_full.parquet por la nueva salida del pipeline
python build_app.py --entrenar             # 2. ejecuta el notebook de la Entrega 3 y regenera todo
# 3. abrir site/index.html, mirar que esté bien, y commitear app_data/, modelos/ y site/
```

`build_app.py --entrenar` ejecuta el notebook **tal cual** (en una carpeta temporal, con los datos
nuevos): elige el modelo, lo entrena con 2018-2025 (semilla 14), lo mide en el test (2026) y lo
guarda. El notebook ejecutado queda en `build/Entrega_3_ejecutada.ipynb`, para comparar sus números
con los de la app. Sin `--entrenar`, usa el modelo ya guardado y solo recalcula `app_data/` y la
página.

Tres cosas que hace `build_app.py` además de predecir:

- **Predicciones fuera de muestra.** En «Explorá», cada carrera de 2018-2025 la predice un modelo
  que no la vio: una copia del modelo elegido (mismo pipeline e hiperparámetros) entrenada con las
  demás temporadas, como en la validación cruzada del notebook. 2026 lo predice el modelo final.
- **Verificación contra el notebook.** Compara el MAE del test (con y sin abandonos, modelo y
  grilla) con la tabla del notebook ejecutado y corta con un error si no coinciden. Si cambian los
  datos y no se volvió a correr el notebook, avisa.
- **Verificación del modelo en el navegador** (ver abajo).

Después de `--entrenar`, copiar `build/Entrega_3_ejecutada.ipynb` a
`notebooks/Entrega_3_Modelado_y_Validacion_F1_Grupo_14.ipynb` y commitearlo: es el notebook que
tiene que coincidir con la app.

### «Probá el modelo» sin Python

En la página no hay sklearn. `build_app.py` saca del pipeline entrenado los números que hacen falta
(qué columnas dan cada desgaste, el relleno de cada faltante, qué variables se multiplican, media
y desvío del `StandardScaler`, coeficientes e intercepto del `Ridge`) y los guarda en
`app_data/modelo.json`. `web/modelo.js` hace la misma cuenta en el navegador con esos números; no
se reentrena nada. El puesto sale de ordenar ese puntaje contra el de los demás pilotos de la
carrera.

Antes de generar la página, `build_app.py` comprueba que esa cuenta sea la del modelo:

- **numpy:** rehace la cuenta a partir del JSON y la compara con `modelo.predict` en todas las
  filas del dataset y en una copia con datos borrados al azar (lo que el usuario puede hacer con
  «Sin dato»). Si alguna difiere en más de 1e-9, **el build se corta** y no se genera la página.
- **JavaScript:** si hay `node` instalado, corre `web/modelo.js` sobre las mismas filas y compara
  puntaje y puesto con sklearn. Sin `node` avisa y sigue (la verificación con numpy corre siempre).

Si el notebook llegara a elegir un modelo que no es lineal, `build_app.py` corta con un mensaje:
la página solo sabe calcular este pipeline.

### Publicarla en GitHub Pages

La publica el workflow `.github/workflows/pages.yml`, que sube la carpeta `site/` tal como está
commiteada (no construye nada en GitHub).

1. Una sola vez, quien administra el repositorio: **Settings → Pages → Build and deployment →
   Source: «GitHub Actions»**.
2. Regenerar (`python build_app.py`), commitear `app_data/` y `site/`, y mergear a `main`.
3. El workflow corre solo con cada cambio de `site/` en `main` (o a mano: **Actions → Publicar la
   página en GitHub Pages → Run workflow**). La URL queda en el resumen de la corrida y en
   Settings → Pages.
4. Probarla desde otra computadora antes de la exposición.

## Cómo trabajar en equipo

Cada uno trabaja en su rama y se integra a `main` por pull request. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
