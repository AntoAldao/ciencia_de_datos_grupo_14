"""El modelo de la Entrega 3: sus clases, cargarlo y predecir.

El notebook de la Entrega 3 guarda el pipeline con joblib (Sección 10) y `build_app.py` lo deja en
`modelos/modelo_f1_grupo14.joblib`. Como las clases se definieron en el notebook, joblib las busca
en `__main__`: `cargar()` las pone ahí antes de leer el archivo.

El código es una copia **textual** de las celdas del notebook
`notebooks/Entrega_3_Modelado_y_Validacion_F1_Grupo_14.ipynb` (celdas 16 y 30, con sus constantes
de la celda 8). Si el notebook cambia esas clases, hay que copiarlas de nuevo acá.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn import config_context
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin, clone

SEMILLA = 14
ABS_DESGASTE = [f"FP_LapTime_{m}_{c}_ABS" for c in ["SOFT", "MED"] for m in ["min", "mean"]]


# ---- celda 16 ----------------------------------------------------------------------------------
class Desgaste(BaseEstimator, TransformerMixin):
    # Calcula FP_Desgaste_SOFT y FP_Desgaste_MED con las vueltas en segundos y descarta esas columnas.
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        for c in ["SOFT", "MED"]:
            mejor, media = X[f"FP_LapTime_min_{c}_ABS"], X[f"FP_LapTime_mean_{c}_ABS"]
            X[f"FP_Desgaste_{c}"] = (media - mejor) / mejor * 100
        return X.drop(columns=ABS_DESGASTE)


class PesarDistanciaLider(BaseEstimator, TransformerMixin):
    # Multiplica la distancia al líder por (ronda - 1) / 20. Probado en la Sección 6; apagado por defecto.
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        if "DriverPoints_Before_DBT_%" in X.columns and "Carrera" in X.columns:
            rondas = X["Carrera"].str.extract(r"-R(\d+)")[0].astype(float)
            X["DriverPoints_Before_DBT_%"] = X["DriverPoints_Before_DBT_%"] * (rondas - 1).clip(lower=0) / 20.0
        return X


class Interacciones(BaseEstimator, TransformerMixin):
    # Agrega mejor vuelta × desgaste para SOFT y MED, si las dos columnas están.
    PARES = [("FP_LapTime_min_SOFT_DBT_%", "FP_Desgaste_SOFT"),
             ("FP_LapTime_min_MED_DBT_%", "FP_Desgaste_MED")]

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        for a, b in self.PARES:
            if a in X.columns and b in X.columns:
                X[f"{a} × {b}"] = X[a] * X[b]
        return X


class ReglaGrilla(BaseEstimator, RegressorMixin):
    # Referencia sin aprendizaje: el puntaje es la posición de largada.
    def fit(self, X, y=None):
        self.ajustado_ = True
        return self

    def predict(self, X):
        return np.asarray(X, dtype=float)[:, 0] / 21


# ---- celda 30 ----------------------------------------------------------------------------------
class PorZonaDeGrilla(BaseEstimator, RegressorMixin):
    # Un modelo por zona de grilla; la predicción promedia las zonas que contienen al piloto.
    def __init__(self, modelo=None, ventanas=((1, 8), (5, 14), (11, 22))):
        self.modelo = modelo
        self.ventanas = ventanas

    def _grilla(self, X):
        return X["Q_GridPosition"].fillna(21).to_numpy()

    def fit(self, X, y):
        g, y = self._grilla(X), np.asarray(y)
        self.modelos_ = []
        for lo, hi in self.ventanas:
            m = (g >= lo) & (g <= hi)
            self.modelos_.append(clone(self.modelo).fit(X[m], y[m]))
        return self

    def predict(self, X):
        g = self._grilla(X)
        suma, cuenta = np.zeros(len(X)), np.zeros(len(X))
        for (lo, hi), mod in zip(self.ventanas, self.modelos_):
            m = (g >= lo) & (g <= hi)
            if m.any():
                suma[m] += mod.predict(X[m])
                cuenta[m] += 1
        return suma / np.maximum(cuenta, 1)


class RankingPorCarrera(BaseEstimator, RegressorMixin):
    # LambdaMART agrupado por carrera. Devuelve un puntaje donde menor = mejor, como el resto.
    def __init__(self, preprocesador=None, n_estimators=300, learning_rate=0.05, num_leaves=15,
                 min_child_samples=30, random_state=SEMILLA):
        self.preprocesador = preprocesador
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.random_state = random_state

    def fit(self, X, y):
        from lightgbm import LGBMRanker

        self.prep_ = clone(self.preprocesador).fit(X, y)
        Xt = np.asarray(self.prep_.transform(X), dtype=float)
        carrera = X["Carrera"].to_numpy()
        inicios = np.flatnonzero(np.r_[True, carrera[1:] != carrera[:-1]])
        grupos = np.diff(np.r_[inicios, len(carrera)])
        relevancia = np.rint((1 - np.asarray(y)) * 20).astype(int)
        self.ranker_ = LGBMRanker(objective="lambdarank", n_estimators=self.n_estimators,
                                  learning_rate=self.learning_rate, num_leaves=self.num_leaves,
                                  min_child_samples=self.min_child_samples,
                                  label_gain=list(range(31)), random_state=self.random_state, verbose=-1)
        self.ranker_.fit(Xt, relevancia, group=grupos)
        return self

    def predict(self, X):
        return -self.ranker_.predict(np.asarray(self.prep_.transform(X), dtype=float))


CLASES = [Desgaste, PesarDistanciaLider, Interacciones, ReglaGrilla, PorZonaDeGrilla,
          RankingPorCarrera]


ARCHIVO = Path(__file__).resolve().parent / "modelos" / "modelo_f1_grupo14.joblib"


def cargar(archivo: str | Path = ARCHIVO) -> dict:
    """Lo que guardó el notebook: {"modelo": pipeline, "entrada": columnas, "elegido", ...}."""
    import joblib

    principal = sys.modules["__main__"]
    for clase in CLASES:   # donde las buscó joblib al guardar desde el notebook
        setattr(principal, clase.__name__, clase)
    return joblib.load(archivo)


# Las clases del notebook necesitan DataFrames entre pasos (como `set_config` en el notebook). La
# configuración de sklearn es por hilo y Streamlit cambia de hilo: se fija en cada llamada.
def puntaje(guardado: dict, df: pd.DataFrame) -> np.ndarray:
    """Puntaje 0-1 por fila (0 = ganador, 1 = último): lo que predice el modelo."""
    with config_context(transform_output="pandas"):
        return np.asarray(guardado["modelo"].predict(df[guardado["entrada"]]), dtype=float)


def aportes(guardado: dict, df: pd.DataFrame) -> pd.DataFrame | None:
    """Coeficiente × variable transformada (con el intercepto suman el puntaje). None si el
    modelo no es lineal."""
    pipe = guardado["modelo"]
    final = pipe.steps[-1][1]
    if not hasattr(final, "coef_"):
        return None
    with config_context(transform_output="pandas"):
        Z = pipe[:-1].transform(df[guardado["entrada"]])
    return Z * np.ravel(final.coef_)
