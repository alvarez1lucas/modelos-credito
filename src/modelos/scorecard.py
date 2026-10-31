"""Scorecard tradicional: regresión logística sobre WoE, expresada en puntos.

Es el formato que usan bancos y financieras: cada tramo de cada variable suma o resta puntos, y cualquier
decisión se puede explicar sumando una tabla. Con `pdo` puntos se duplican las odds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from modelos import woe
from modelos.datos import NUMERICAS, log_odds


class Scorecard:
    """Regresión logística sobre WoE, expresada en puntos."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tramos: list[woe.Tramos] = []
        self.modelo: LogisticRegression | None = None

    def ajustar(self, df: pd.DataFrame, y: pd.Series, variables_cat: list[str]) -> "Scorecard":
        todos = woe.ajustar(df, y, NUMERICAS, variables_cat, self.cfg["bins"])
        self.informacion = {t.variable: t.iv for t in todos}
        self.tramos = [t for t in todos if t.iv >= self.cfg["iv_minimo"]]
        self.modelo = LogisticRegression(C=1e6, max_iter=2000).fit(self._x(df), y)
        return self

    def ajustar_solo(self, df: pd.DataFrame, y: pd.Series, categoricas: list[str]) -> "Scorecard":
        """Scorecard sólo con variables categóricas: la línea de base más simple."""
        self.tramos = [woe.ajustar_categorica(df[c], y) for c in categoricas]
        self.modelo = LogisticRegression(C=1e6, max_iter=2000).fit(self._x(df), y)
        return self

    def _x(self, df: pd.DataFrame) -> np.ndarray:
        return np.column_stack([t.transformar(df[t.variable]) for t in self.tramos])

    def pd(self, df: pd.DataFrame) -> np.ndarray:
        return self.modelo.predict_proba(self._x(df))[:, 1]

    def puntos(self, df: pd.DataFrame) -> np.ndarray:
        f = self.cfg["pdo"] / np.log(2)
        o = self.cfg["puntos_base"] - f * np.log(self.cfg["odds_base"])
        return o - f * log_odds(self.pd(df))

    def base(self) -> float:
        """Puntos de partida, antes de sumar los de cada variable."""
        f = self.cfg["pdo"] / np.log(2)
        return float(self.cfg["puntos_base"] - f * np.log(self.cfg["odds_base"]) - f * self.modelo.intercept_[0])

    def tabla_puntos(self) -> pd.DataFrame:
        """Puntos que suma o resta cada tramo. Base + suma de los tramos = puntaje del cliente."""
        f = self.cfg["pdo"] / np.log(2)
        filas = []
        for t, b in zip(self.tramos, self.modelo.coef_[0]):
            d = t.tabla()
            d["puntos"] = -f * b * d["woe"]
            filas.append(d)
        return pd.concat(filas, ignore_index=True)
