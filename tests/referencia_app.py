"""Versión en Python de los cálculos de la app: los tests la comparan con app/logica.js."""

from __future__ import annotations

import bisect
import gzip
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

DATOS = Path(__file__).resolve().parents[1] / "app" / "datos"


def cargar_meta() -> dict:
    return json.loads((DATOS / "app.json").read_text(encoding="utf-8"))


def cargar_prueba() -> pd.DataFrame:
    m = cargar_meta()
    n = m["n"]
    b = gzip.decompress((DATOS / "prueba.bin.gz").read_bytes())
    f = np.frombuffer(b, "<f4", 3 * n).reshape(3, n)
    u = np.frombuffer(b, "u1", 3 * n, 12 * n).reshape(3, n)
    return pd.DataFrame({"pd": f[0], "monto": f[1], "tasa": f[2], "pais": np.array(m["paises"])[u[0]], "rating": np.array(m["ratings"])[u[1]], "malo": u[2]})


def cuota(monto: float, tasa: float, plazo: int) -> float:
    i = tasa / 12
    return monto * i / (1 - (1 + i) ** (-plazo))


def _woe(v: dict, valor) -> float:
    if v["cortes"] is None:
        return v["woe"][v["categorias"].index(str(valor))] if str(valor) in v["categorias"] else 0.0
    bordes = [math.inf if c is None else c for c in v["cortes"]]
    return v["woe"][min(bisect.bisect_left(bordes, float(valor)), len(v["woe"]) - 1)]


def puntuar(sc: dict, cliente: dict) -> dict:
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


def aprobar(df: pd.DataFrame, e: dict) -> np.ndarray:
    p = df["pd"].to_numpy(dtype=float)
    base = p <= e["corte"] if e["regla"] == "pd" else p * e["lgd"] < df["tasa"].to_numpy(dtype=float) - e["costo"] / 100
    return base & ~df["pais"].isin(e["sinPaises"]).to_numpy() & ~df["rating"].isin(e["sinRatings"]).to_numpy()


def resumen(df: pd.DataFrame, a: np.ndarray, r: np.ndarray) -> dict:
    malo, monto = df["malo"].to_numpy(), df["monto"].to_numpy(dtype=float)
    return {"aprobadosPct": 100 * float(a.mean()), "montoPct": 100 * float(monto[a].sum() / monto.sum()), "moraPct": 100 * float(malo[a].mean()) if a.any() else None,
            "moraBasePct": 100 * float(malo.mean()), "resultado": float(r[a].sum()), "cambio": float(-r[~a].sum()), "malosEvitados": int(malo[~a].sum()),
            "buenosPerdidos": int((1 - malo[~a]).sum())}


def curva(df: pd.DataFrame, r: np.ndarray, e: dict, cortes: list[float]) -> list[float]:
    p = df["pd"].to_numpy(dtype=float)
    fuera = df["pais"].isin(e["sinPaises"]).to_numpy() | df["rating"].isin(e["sinRatings"]).to_numpy()
    return [float(r[(p <= c) & ~fuera].sum()) for c in cortes]


def por_segmento(df: pd.DataFrame, a: np.ndarray, r: np.ndarray, campo: str) -> pd.DataFrame:
    t = pd.DataFrame({"clave": df[campo].astype(str), "a": a, "malo": df["malo"].to_numpy(), "r": r})
    g = t.groupby("clave").agg(creditos=("a", "size"), aprobados=("a", "mean"), mora=("malo", "mean")).reset_index()
    g["cambio"] = g["clave"].map(t[~t["a"]].groupby("clave")["r"].sum().mul(-1)).fillna(0.0)
    return g
