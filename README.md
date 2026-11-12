# Ciencia de Datos – Grupo 14 – Fórmula 1

Proyecto integrador de Ciencia de Datos (UTN FRM, 2026). Trabajamos con datos de Fórmula 1
(2018–2026): una fila es **un piloto en un Gran Premio**.

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
├── app.py                # La aplicación (Streamlit): lee app_data/ y el modelo
├── build_app.py          # Datos del pipeline -> notebook de la Entrega 3 -> app_data/
├── modelo_entrega3.py    # Clases del notebook de la Entrega 3 + cargar el modelo y predecir
├── graficos/             # Gráficos de la app (Altair)
├── app_data/             # Generado por build_app.py: predicciones, aportes y resumen
├── modelos/              # Modelo que guarda el notebook de la Entrega 3 (joblib)
├── requirements.txt      # Dependencias
├── data/                 # Datos que produce el pipeline (f1_all_full.parquet; v2 = versión anterior)
├── notebooks/            # Entrega 2 (EDA) y Entrega 3 (modelado)
├── docs/consigna.md      # Qué hay que hacer en la Entrega 4
└── CONTRIBUTING.md       # Cómo trabajar con ramas
```

El pipeline de la Entrega 1 (Airflow) vive en su propio repositorio:
<https://github.com/Gonzalez-Matias/f1-pipeline>.

## Cómo correrlo

Desde la carpeta del repositorio, en PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Se abre en <http://localhost:8501>.

## Cómo se regenera la aplicación

La app no entrena nada: muestra lo que deja `build_app.py` en `app_data/` y usa el modelo que
guarda el notebook de la Entrega 3 en `modelos/`. Si cambian los datos del pipeline:

```powershell
# 1. reemplazar data/f1_all_full.parquet por la nueva salida del pipeline
python build_app.py --entrenar             # 2. ejecuta el notebook de la Entrega 3 y regenera todo
streamlit run app.py                       # 3. mirar que esté bien, y commitear app_data/ y modelos/
```

`build_app.py --entrenar` ejecuta el notebook **tal cual** (en una carpeta temporal, con los datos
nuevos): elige el modelo, lo entrena con 2018-2025 (semilla 14), lo mide en el test (2026) y lo
guarda. El notebook ejecutado queda en `build/Entrega_3_ejecutada.ipynb`, para comparar sus números
con los de la app. Sin `--entrenar`, usa el modelo ya guardado y solo recalcula `app_data/`.

Dos cosas que hace `build_app.py` además de predecir:

- **Predicciones fuera de muestra.** En «Explorá», cada carrera de 2018-2025 la predice un modelo
  que no la vio: una copia del modelo elegido (mismo pipeline e hiperparámetros) entrenada con las
  demás temporadas, como en la validación cruzada del notebook. 2026 lo predice el modelo final.
- **Verificación contra el notebook.** Al final compara el MAE del test (con y sin abandonos, modelo
  y grilla) con la tabla del notebook ejecutado y corta con un error si no coinciden. Si cambian los
  datos y no se volvió a correr el notebook, avisa.

Después de `--entrenar`, copiar `build/Entrega_3_ejecutada.ipynb` a
`notebooks/Entrega_3_Modelado_y_Validacion_F1_Grupo_14.ipynb` y commitearlo: es el notebook que
tiene que coincidir con la app.

## Cómo trabajar en equipo

Cada uno trabaja en su rama y se integra a `main` por pull request. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
