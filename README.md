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
- Gonzales, Matías
- Manucha, Juan Pablo
- Zalazar, Valentin

## Estructura del repositorio

```
ciencia_de_datos_grupo_14/
├── app.py                # La aplicación (Streamlit, esqueleto inicial)
├── requirements.txt      # Dependencias
├── data/                 # Dataset que produce el pipeline
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

## Cómo trabajar en equipo

Cada uno trabaja en su rama y se integra a `main` por pull request. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
