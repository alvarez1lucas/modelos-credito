"""Carga de los modelos congelados y puntuación: lo comparten el corte, la validación y el monitoreo."""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from modelos.config import path
from modelos.datos import matriz
from modelos.entrenar import aplicar_calibrador


def cargar_modelos() -> dict:
    return joblib.load(path("guardados") / "modelos.joblib")


def pd_scorecard(m: dict, df: pd.DataFrame) -> np.ndarray:
    return aplicar_calibrador(m["calibrador_scorecard"], m["scorecard"].pd(df))


def pd_lightgbm(m: dict, df: pd.DataFrame) -> np.ndarray:
    p = m["lightgbm"].predict_proba(matriz(df, True, m["categorias"]))[:, 1]
    return aplicar_calibrador(m["calibrador_lightgbm"], p)
