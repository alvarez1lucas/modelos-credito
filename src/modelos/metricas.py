"""Métricas de validación: discriminación, calibración y estabilidad."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def gini(y: np.ndarray, score: np.ndarray) -> float:
    """Gini = 2 × AUC - 1. `score` más alto = más riesgo."""
    return float(2 * roc_auc_score(y, score) - 1)


def ks(y: np.ndarray, score: np.ndarray) -> float:
    """Máxima distancia entre las distribuciones acumuladas de malos y buenos."""
    y = np.asarray(y)
    orden = np.argsort(score)
    y = y[orden]
    malos = np.cumsum(y) / y.sum()
    buenos = np.cumsum(1 - y) / (1 - y).sum()
    return float(np.abs(malos - buenos).max())


def gini_ic(y: np.ndarray, score: np.ndarray, n: int = 200, seed: int = 7) -> tuple[float, float]:
    """Intervalo de 95% por bootstrap."""
    rng = np.random.default_rng(seed)
    y, score = np.asarray(y), np.asarray(score)
    valores = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].sum() > 0:
            valores.append(gini(y[i], score[i]))
    return float(np.percentile(valores, 2.5)), float(np.percentile(valores, 97.5))


def calibracion(y: np.ndarray, pd_: np.ndarray, grupos: int = 10) -> pd.DataFrame:
    """PD predicha contra tasa observada por decil de riesgo."""
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(pd_)})
    d["decil"] = pd.qcut(d["p"].rank(method="first"), grupos, labels=False) + 1
    return d.groupby("decil").agg(n=("y", "size"), pd_media=("p", "mean"), observado=("y", "mean")).reset_index()


def error_calibracion(y: np.ndarray, pd_: np.ndarray, grupos: int = 10) -> float:
    """Error absoluto medio ponderado entre predicho y observado por decil, en puntos."""
    c = calibracion(y, pd_, grupos)
    return float(100 * (np.abs(c["pd_media"] - c["observado"]) * c["n"]).sum() / c["n"].sum())


def psi(base: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Índice de estabilidad poblacional. Regla práctica: < 0,10 estable; 0,10-0,25 vigilar; > 0,25 cambio fuerte."""
    bordes = np.unique(np.quantile(base, np.linspace(0, 1, bins + 1)))
    bordes[0], bordes[-1] = -np.inf, np.inf
    a = np.histogram(base, bordes)[0] / len(base)
    b = np.histogram(actual, bordes)[0] / len(actual)
    a, b = np.clip(a, 1e-4, None), np.clip(b, 1e-4, None)
    return float(((b - a) * np.log(b / a)).sum())


def tramo_tasa(tasa: pd.Series, ancho: float = 0.025) -> pd.Series:
    """Tramos fijos para la tasa. Las tasas se agrupan en pocos valores de lista, y con tramos por cuantiles
    un cambio mínimo (de 18,05% a 18,77%) cruza un borde artificialmente angosto e infla el PSI."""
    return (tasa / ancho).round().astype(int)


def psi_categorica(base: pd.Series, actual: pd.Series) -> float:
    a = base.value_counts(normalize=True)
    b = actual.value_counts(normalize=True)
    i = a.index.union(b.index)
    a, b = a.reindex(i, fill_value=0).clip(lower=1e-4), b.reindex(i, fill_value=0).clip(lower=1e-4)
    return float(((b - a) * np.log(b / a)).sum())
