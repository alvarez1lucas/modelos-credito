"""Exporta lo que necesita la app: la scorecard en JSON y las cosechas de prueba con su resultado real.

`python -m modelos.exportar_app` escribe app/scorecard.json y app/prueba.parquet.

La app no carga el pickle ni instala LightGBM: con los tramos y los coeficientes alcanza, y arranca rápido.
"""

from __future__ import annotations

import json

import pandas as pd

from modelos.config import ROOT, settings
from modelos.datos import cargar, particion
from modelos.puntaje import cargar_modelos, pd_scorecard


def scorecard_json(m: dict) -> dict:
    s = m["scorecard"]
    variables = []
    for t, b in zip(s.tramos, s.modelo.coef_[0]):
        variables.append({"variable": t.variable, "coef": float(b), "woe": t.woe,
                          "cortes": None if t.cortes is None else [None if c == float("inf") else c for c in t.cortes],
                          "categorias": t.categorias})
    return {"variables": variables, "intercepto": float(s.modelo.intercept_[0]), "base": s.base(), "pdo": s.cfg["pdo"],
            "calibrador": {"a": float(m["calibrador_scorecard"].intercept_[0]), "b": float(m["calibrador_scorecard"].coef_[0][0])},
            "paises_entrenamiento": sorted(c for c in next(v for v in s.tramos if v.variable == "pais").categorias)}


def main() -> None:
    df = cargar()
    df["particion"] = particion(df)
    m = cargar_modelos()
    pr = df[df["particion"] == "prueba"].reset_index(drop=True)
    pr["pd"] = pd_scorecard(m, pr)
    t = pr[["pais", "rating", "monto", "tasa", "malo", "pd"]].astype({"pais": "category", "rating": "category", "monto": "float32", "tasa": "float32",
                                                                     "pd": "float32", "malo": "int8"})
    app = ROOT / "app"
    t.to_parquet(app / "prueba.parquet", index=False, compression="zstd")
    with open(app / "scorecard.json", "w", encoding="utf-8") as fh:
        json.dump({**scorecard_json(m), "lgd": settings()["corte"]["lgd"], "costo": settings()["corte"]["costo_central_pp"]}, fh, ensure_ascii=False, indent=1)
    print(f"app: {len(t):,} créditos")


if __name__ == "__main__":
    main()
