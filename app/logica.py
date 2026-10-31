"""Cálculos de la app, sin Streamlit: se pueden probar por separado."""

from __future__ import annotations

import bisect
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).parent
ETIQUETAS = {"monto": ("Monto", "Amount"), "tasa": ("Tasa", "Rate"), "plazo": ("Plazo", "Term"), "ingreso": ("Ingreso", "Income"),
             "carga_pct": ("Carga de la cuota", "Payment burden"), "pais": ("País", "Country"), "rating": ("Rating", "Rating")}


def cargar_scorecard() -> dict:
    return json.loads((AQUI / "scorecard.json").read_text(encoding="utf-8"))


def cargar_prueba() -> pd.DataFrame:
    return pd.read_parquet(AQUI / "prueba.parquet")


def cuota(monto: float, tasa: float, plazo: int) -> float:
    i = tasa / 12
    return monto * i / (1 - (1 + i) ** (-plazo))


def _woe(v: dict, valor) -> float:
    if v["cortes"] is None:
        return v["woe"][v["categorias"].index(str(valor))] if str(valor) in v["categorias"] else 0.0
    bordes = [math.inf if c is None else c for c in v["cortes"]]
    return v["woe"][min(bisect.bisect_left(bordes, float(valor)), len(v["woe"]) - 1)]


def puntuar(sc: dict, cliente: dict) -> dict:
    """Puntaje y PD de un cliente, con lo que aporta cada variable."""
    f = sc["pdo"] / math.log(2)
    log_odds, puntos, detalle = sc["intercepto"], sc["base"], []
    for v in sc["variables"]:
        w = _woe(v, cliente[v["variable"]])
        log_odds += v["coef"] * w
        puntos += -f * v["coef"] * w
        detalle.append({"variable": v["variable"], "puntos": -f * v["coef"] * w})
    calibrado = sc["calibrador"]["a"] + sc["calibrador"]["b"] * log_odds
    return {"pd": 1 / (1 + math.exp(-calibrado)), "puntos": puntos, "detalle": detalle}


def resultado_credito(df: pd.DataFrame, costo_pp: float, lgd: float) -> np.ndarray:
    monto = df["monto"].to_numpy(dtype=float)
    return monto * (df["tasa"].to_numpy(dtype=float) - costo_pp / 100) - df["malo"].to_numpy() * lgd * monto


def aprobar(df: pd.DataFrame, regla: str, corte: float, costo_pp: float, lgd: float, sin_paises: list[str], sin_ratings: list[str]) -> np.ndarray:
    """`regla`: 'pd' aprueba hasta una PD fija; 'margen' aprueba si PD × LGD < tasa - costo."""
    p = df["pd"].to_numpy(dtype=float)
    base = p <= corte if regla == "pd" else p * lgd < df["tasa"].to_numpy(dtype=float) - costo_pp / 100
    return base & ~df["pais"].isin(sin_paises).to_numpy() & ~df["rating"].isin(sin_ratings).to_numpy()


def resumen(df: pd.DataFrame, aprobado: np.ndarray, r: np.ndarray) -> dict:
    malo, monto = df["malo"].to_numpy(), df["monto"].to_numpy(dtype=float)
    hay = bool(aprobado.any())
    return {"aprobados_pct": 100 * float(aprobado.mean()), "monto_pct": 100 * float(monto[aprobado].sum() / monto.sum()),
            "mora_pct": 100 * float(malo[aprobado].mean()) if hay else float("nan"), "mora_base_pct": 100 * float(malo.mean()),
            "resultado": float(r[aprobado].sum()), "cambio": float(-r[~aprobado].sum())}


def curva(df: pd.DataFrame, costo_pp: float, lgd: float) -> pd.DataFrame:
    """Resultado acumulado al subir el corte de PD. Ordena una vez: la app lo recalcula con cada movimiento."""
    orden = np.argsort(df["pd"].to_numpy(dtype=float))
    p = df["pd"].to_numpy(dtype=float)[orden]
    r = np.cumsum(resultado_credito(df, costo_pp, lgd)[orden])
    cortes = np.round(np.arange(0.01, 0.4001, 0.0025), 4)
    i = np.searchsorted(p, cortes, side="right") - 1
    valores = np.where(i >= 0, r[np.clip(i, 0, None)], 0.0)
    return pd.DataFrame({"corte": cortes, "resultado": valores})


def por_pais(df: pd.DataFrame, aprobado: np.ndarray, r: np.ndarray) -> pd.DataFrame:
    t = pd.DataFrame({"pais": df["pais"].astype(str), "a": aprobado, "malo": df["malo"].to_numpy(), "r": r})
    g = t.groupby("pais").agg(creditos=("a", "size"), aprobados=("a", "mean"), mora=("malo", "mean")).reset_index()
    cambio = t[~t["a"]].groupby("pais")["r"].sum().mul(-1)
    g["cambio"] = g["pais"].map(cambio).fillna(0.0)
    return g
