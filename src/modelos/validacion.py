"""Validación del modelo: calibración, estabilidad en el tiempo y explicación.

`python -m modelos.validacion` escribe outputs/validacion/.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import shap

from modelos import metricas as m
from modelos.config import path
from modelos.datos import CATEGORICAS, NUMERICAS, cargar, matriz, particion
from modelos.puntaje import cargar_modelos, pd_lightgbm, pd_scorecard


def por_trimestre(df: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    d = df.assign(p=p, trimestre=df["fecha"].dt.to_period("Q").astype(str))
    filas = []
    for t, g in d.groupby("trimestre"):
        filas.append({"trimestre": t, "n": len(g), "gini": m.gini(g["malo"], g["p"]), "pd_media_pct": 100 * g["p"].mean(), "observado_pct": 100 * g["malo"].mean()})
    return pd.DataFrame(filas)


def estabilidad(base: pd.DataFrame, actual: pd.DataFrame, pb: np.ndarray, pa: np.ndarray) -> pd.DataFrame:
    filas = [{"variable": c, "psi": m.psi(base[c].to_numpy(dtype=float), actual[c].to_numpy(dtype=float))} for c in NUMERICAS if c != "tasa"]
    filas.append({"variable": "tasa", "psi": m.psi_categorica(m.tramo_tasa(base["tasa"]), m.tramo_tasa(actual["tasa"]))})
    filas += [{"variable": c, "psi": m.psi_categorica(base[c], actual[c])} for c in [*CATEGORICAS, "rating"]]
    filas.append({"variable": "puntaje del modelo", "psi": m.psi(pb, pa)})
    return pd.DataFrame(filas).sort_values("psi", ascending=False)


def main() -> None:
    df = cargar()
    df["particion"] = particion(df)
    mo = cargar_modelos()
    madurar = df[df["particion"] != "sin_madurar"].reset_index(drop=True)
    tr = madurar[madurar["particion"] == "entrenamiento"]
    pr = madurar[madurar["particion"] == "prueba"]
    p_sc = pd_scorecard(mo, madurar)
    p_gb = pd_lightgbm(mo, madurar)
    i_tr, i_pr = tr.index.to_numpy(), pr.index.to_numpy()

    tri = pd.concat([por_trimestre(madurar, p_sc).assign(modelo="Scorecard"), por_trimestre(madurar, p_gb).assign(modelo="LightGBM")], ignore_index=True)
    est = estabilidad(tr, pr, p_sc[i_tr], p_sc[i_pr])
    cal = m.calibracion(pr["malo"].to_numpy(), p_sc[i_pr])

    muestra = pr.sample(20000, random_state=7)
    X = matriz(muestra, True, mo["categorias"])
    valores = shap.TreeExplainer(mo["lightgbm"]).shap_values(X)
    valores = valores[1] if isinstance(valores, list) else valores
    imp = pd.DataFrame({"variable": X.columns, "shap_medio": np.abs(valores).mean(axis=0)}).sort_values("shap_medio", ascending=False)

    pr_i = pr.assign(p=p_sc[i_pr])
    por_rating = pr_i.groupby("rating").agg(n=("malo", "size"), pd_media_pct=("p", lambda s: 100 * s.mean()), observado_pct=("malo", lambda s: 100 * s.mean())).reset_index()
    por_pais = pr_i.groupby("pais").agg(n=("malo", "size"), pd_media_pct=("p", lambda s: 100 * s.mean()), observado_pct=("malo", lambda s: 100 * s.mean())).reset_index()
    por_pais["n_entrenamiento"] = por_pais["pais"].map(tr["pais"].value_counts()).fillna(0).astype(int)

    out = path("outputs") / "validacion"
    out.mkdir(parents=True, exist_ok=True)
    tri.to_csv(out / "por_trimestre.csv", index=False, float_format="%.4f")
    est.to_csv(out / "psi.csv", index=False, float_format="%.4f")
    cal.to_csv(out / "calibracion_prueba.csv", index=False, float_format="%.4f")
    imp.to_csv(out / "shap_lightgbm.csv", index=False, float_format="%.4f")
    por_rating.to_csv(out / "calibracion_rating.csv", index=False, float_format="%.4f")
    por_pais.to_csv(out / "calibracion_pais.csv", index=False, float_format="%.4f")
    print(tri.round(3).to_string()); print(est.round(3).to_string()); print(cal.round(3).to_string()); print(imp.round(3).to_string())
    print(por_rating.round(2).to_string()); print(por_pais.round(2).to_string())


if __name__ == "__main__":
    main()
