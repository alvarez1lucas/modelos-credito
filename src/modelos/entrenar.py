"""Entrena y compara: el rating de Bondora, una scorecard y gradient boosting, con y sin rating.

`python -m modelos.entrenar` escribe outputs/modelos/ y congela los modelos en modelos_guardados/.

La pregunta no es qué Gini da un modelo, sino si le gana al que la empresa ya tiene. Por eso el punto de
comparación es el rating de Bondora, evaluado con la misma regla: entrenar con cosechas viejas, ajustar en
validación y medir en prueba, con cosechas posteriores que nadie miró al elegir nada.
"""

from __future__ import annotations

import json

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from modelos import metricas as m
from modelos.config import path, settings
from modelos.datos import BENCHMARK, CATEGORICAS, ORDEN_RATING, cargar, log_odds, matriz, particion
from modelos.scorecard import Scorecard


def ajustar_gbm(X: pd.DataFrame, y: pd.Series, cfg: dict) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(**cfg).fit(X, y, categorical_feature=CATEGORICAS)


def mejor_gbm(Xtr: pd.DataFrame, ytr: pd.Series, Xva: pd.DataFrame, yva: pd.Series, cfg: dict) -> tuple[dict, pd.DataFrame]:
    """Búsqueda en grilla: la configuración se elige por Gini en validación, sin mirar prueba."""
    filas = []
    for extra in cfg["grilla"]:
        p = {**cfg["base"], **extra}
        g = m.gini(yva.to_numpy(), ajustar_gbm(Xtr, ytr, p).predict_proba(Xva)[:, 1])
        filas.append({**extra, "gini_validacion": g})
    t = pd.DataFrame(filas).sort_values("gini_validacion", ascending=False)
    mejor = {k: (int(v) if float(v).is_integer() else float(v)) for k, v in t.iloc[0].drop("gini_validacion").items()}
    return {**cfg["base"], **mejor}, t


def recalibrar(p_validacion: np.ndarray, y_validacion: np.ndarray) -> LogisticRegression:
    """Platt sobre log-odds en validación: corrige el nivel sin cambiar el orden."""
    return LogisticRegression(C=1e6, max_iter=1000).fit(log_odds(p_validacion).reshape(-1, 1), y_validacion)


def aplicar_calibrador(c: LogisticRegression, p: np.ndarray) -> np.ndarray:
    return c.predict_proba(log_odds(p).reshape(-1, 1))[:, 1]


def benchmark(tr: pd.DataFrame, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """PD por rating aprendida en entrenamiento, y su orden como score."""
    tasas = tr.groupby(BENCHMARK)["malo"].mean()
    p = df[BENCHMARK].map(tasas).fillna(tr["malo"].mean()).to_numpy(dtype=float)
    return p, df[BENCHMARK].map(ORDEN_RATING).fillna(9).to_numpy(dtype=float)


def evaluar(y: np.ndarray, score: np.ndarray, pd_: np.ndarray, nombre: str, conjunto: str) -> dict:
    lo, hi = m.gini_ic(y, score)
    return {"modelo": nombre, "conjunto": conjunto, "n": len(y), "malos_pct": 100 * float(np.mean(y)), "gini": m.gini(y, score),
            "gini_inf": lo, "gini_sup": hi, "ks": m.ks(y, score), "pd_media_pct": 100 * float(np.mean(pd_)),
            "error_calibracion_pp": m.error_calibracion(y, pd_)}


def main() -> None:
    cfg = settings()
    df = cargar()
    df["particion"] = particion(df)
    tr, va, pr = (df[df["particion"] == k] for k in ("entrenamiento", "validacion", "prueba"))
    out = path("outputs") / "modelos"
    out.mkdir(parents=True, exist_ok=True)
    print({k: (len(g), round(100 * g["malo"].mean(), 2)) for k, g in df.groupby("particion")})

    sc_sin = Scorecard(cfg["scorecard"]).ajustar(tr, tr["malo"], CATEGORICAS)
    sc_con = Scorecard(cfg["scorecard"]).ajustar(tr, tr["malo"], [*CATEGORICAS, BENCHMARK])
    cats = {"pais": sorted(df["pais"].unique())}
    X = lambda d, r: matriz(d, r, cats)  # noqa: E731
    par_sin, _ = mejor_gbm(X(tr, False), tr["malo"], X(va, False), va["malo"], cfg["lightgbm"])
    par_con, grilla = mejor_gbm(X(tr, True), tr["malo"], X(va, True), va["malo"], cfg["lightgbm"])
    grilla.to_csv(out / "grilla_lightgbm.csv", index=False, float_format="%.4f")
    gb_sin = ajustar_gbm(X(tr, False), tr["malo"], par_sin)
    gb_con = ajustar_gbm(X(tr, True), tr["malo"], par_con)
    sc_rp = Scorecard({**cfg["scorecard"]}).ajustar_solo(tr, tr["malo"], [BENCHMARK, "pais"])

    pred = {
        "Sólo rating y país": lambda d: sc_rp.pd(d),
        "Scorecard sin rating": lambda d: sc_sin.pd(d),
        "Scorecard con rating": lambda d: sc_con.pd(d),
        "LightGBM sin rating": lambda d: gb_sin.predict_proba(X(d, False))[:, 1],
        "LightGBM con rating": lambda d: gb_con.predict_proba(X(d, True))[:, 1],
    }
    calibradores = {k: recalibrar(f(va), va["malo"].to_numpy()) for k, f in pred.items()}
    filas = []
    conocidos = set(tr["pais"].unique())
    for nombre_c, d in (("validacion", va), ("prueba", pr), ("prueba sin paises nuevos", pr[pr["pais"].isin(conocidos)])):
        y = d["malo"].to_numpy()
        p, s = benchmark(tr, d)
        filas.append(evaluar(y, s, p, "Rating de Bondora", nombre_c))
        for k, f in pred.items():
            pc = aplicar_calibrador(calibradores[k], f(d))
            filas.append(evaluar(y, pc, pc, k, nombre_c))
    res = pd.DataFrame(filas)
    res.to_csv(out / "comparacion.csv", index=False, float_format="%.4f")
    print(res.round(3).to_string())

    pd.concat([t.tabla().assign(iv=t.iv) for t in sc_con.tramos]).to_csv(out / "woe_tramos.csv", index=False, float_format="%.4f")
    pd.Series(sc_con.informacion, name="iv").rename_axis("variable").reset_index().sort_values("iv", ascending=False).to_csv(out / "iv.csv", index=False, float_format="%.4f")
    sc_con.tabla_puntos().to_csv(out / "tabla_puntos.csv", index=False, float_format="%.1f")

    g = path("guardados")
    joblib.dump({"scorecard": sc_con, "lightgbm": gb_con, "calibrador_scorecard": calibradores["Scorecard con rating"],
                 "calibrador_lightgbm": calibradores["LightGBM con rating"], "categorias": cats,
                 "tasas_rating": tr.groupby(BENCHMARK)["malo"].mean().to_dict(), "parametros_lightgbm": par_con}, g / "modelos.joblib")
    with open(out / "particiones.json", "w", encoding="utf-8") as fh:
        json.dump({k: {"n": int(len(x)), "malos_pct": round(100 * float(x["malo"].mean()), 2),
                       "desde": str(x["fecha"].min().date()), "hasta": str(x["fecha"].max().date())}
                   for k, x in df.groupby("particion")}, fh, ensure_ascii=False, indent=2)
    print(f"entrenar: {out}")


if __name__ == "__main__":
    main()
