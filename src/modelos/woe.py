"""Tramos con peso de la evidencia (WoE) e información (IV), la base de una scorecard tradicional.

WoE de un tramo = ln(% de buenos / % de malos): positivo si el tramo es mejor que el promedio. Los tramos se
fusionan hasta que el WoE sea monótono, porque una scorecard tiene que poder explicarse: un cliente no puede
perder puntos por ganar más sin una razón defendible. IV resume cuánto separa la variable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

EPS = 0.5  # suavizado para tramos sin buenos o sin malos


def _woe_iv(buenos: np.ndarray, malos: np.ndarray) -> tuple[np.ndarray, float]:
    db = (buenos + EPS) / (buenos.sum() + EPS * len(buenos))
    dm = (malos + EPS) / (malos.sum() + EPS * len(malos))
    w = np.log(db / dm)
    return w, float(((db - dm) * w).sum())


@dataclass
class Tramos:
    variable: str
    cortes: list[float] | None   # bordes superiores para numéricas (el último es +inf)
    categorias: list[str] | None
    woe: list[float]
    iv: float

    def transformar(self, x: pd.Series) -> np.ndarray:
        if self.cortes is not None:
            i = np.searchsorted(np.array(self.cortes), x.to_numpy(dtype=float), side="left")
            return np.array(self.woe)[np.clip(i, 0, len(self.woe) - 1)]
        mapa = dict(zip(self.categorias, self.woe))
        return x.map(mapa).fillna(0.0).to_numpy(dtype=float)  # categoría nueva: neutra

    def tabla(self) -> pd.DataFrame:
        if self.cortes is not None:
            etiquetas = [f"<= {c:,.4g}" if np.isfinite(c) else "resto" for c in self.cortes]
        else:
            etiquetas = self.categorias
        return pd.DataFrame({"variable": self.variable, "tramo": etiquetas, "woe": self.woe})


def _fusionar_monotono(buenos: list[float], malos: list[float], cortes: list[float]) -> tuple[list[float], list[float], list[float]]:
    """Fusiona tramos vecinos hasta que el WoE no cambie de sentido, respetando el sentido de la correlación global."""
    b, m, c = list(buenos), list(malos), list(cortes)
    while len(b) > 1:
        w, _ = _woe_iv(np.array(b), np.array(m))
        dif = np.diff(w)
        sentido = np.sign(w[-1] - w[0]) or 1
        malos_pares = np.where(dif * sentido < 0)[0]
        if len(malos_pares) == 0:
            break
        i = int(malos_pares[0])
        b[i] += b.pop(i + 1)
        m[i] += m.pop(i + 1)
        c.pop(i)
    return b, m, c


def ajustar_numerica(x: pd.Series, y: pd.Series, bins: int) -> Tramos:
    bordes = np.unique(np.quantile(x.to_numpy(dtype=float), np.linspace(0, 1, bins + 1)[1:-1]))
    cortes = [*bordes.tolist(), float("inf")]
    idx = np.searchsorted(np.array(cortes), x.to_numpy(dtype=float), side="left")
    malos = np.bincount(idx, weights=y.to_numpy(dtype=float), minlength=len(cortes))
    totales = np.bincount(idx, minlength=len(cortes)).astype(float)
    b, m, c = _fusionar_monotono((totales - malos).tolist(), malos.tolist(), cortes)
    w, iv = _woe_iv(np.array(b), np.array(m))
    return Tramos(x.name, c, None, w.tolist(), iv)


def ajustar_categorica(x: pd.Series, y: pd.Series) -> Tramos:
    g = pd.DataFrame({"x": x.astype(str), "y": y}).groupby("x")["y"].agg(["sum", "size"])
    w, iv = _woe_iv((g["size"] - g["sum"]).to_numpy(dtype=float), g["sum"].to_numpy(dtype=float))
    return Tramos(x.name, None, g.index.tolist(), w.tolist(), iv)


def ajustar(df: pd.DataFrame, y: pd.Series, numericas: list[str], categoricas: list[str], bins: int) -> list[Tramos]:
    return [*(ajustar_numerica(df[c], y, bins) for c in numericas), *(ajustar_categorica(df[c], y) for c in categoricas)]
