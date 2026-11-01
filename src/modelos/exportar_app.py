"""Exporta lo que necesita la app: la scorecard y las cosechas de prueba con su resultado real.

`python -m modelos.exportar_app` escribe app/datos/app.json y app/datos/prueba.bin.gz.

La app corre entera en el navegador: los créditos viajan como columnas binarias ordenadas por PD, que pesan poco y se recorren rápido.
"""

from __future__ import annotations

import gzip
import json

import numpy as np
import pandas as pd

from modelos.config import ROOT, path, settings
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


def columnas_binarias(t: pd.DataFrame, paises: list[str], ratings: list[str]) -> bytes:
    """pd, monto y tasa en float32; país, rating y evento en uint8, todo little-endian."""
    f = [t[c].to_numpy().astype("<f4").tobytes() for c in ("pd", "monto", "tasa")]
    u = [t["pais"].astype(str).map({p: i for i, p in enumerate(paises)}).to_numpy().astype("u1").tobytes(),
         t["rating"].astype(str).map({r: i for i, r in enumerate(ratings)}).to_numpy().astype("u1").tobytes(), t["malo"].to_numpy().astype("u1").tobytes()]
    return b"".join([*f, *u])


def main() -> None:
    df = cargar()
    df["particion"] = particion(df)
    m = cargar_modelos()
    pr = df[df["particion"] == "prueba"].reset_index(drop=True)
    pr["pd"] = pd_scorecard(m, pr)
    t = pr[["pais", "rating", "monto", "tasa", "malo", "pd"]].sort_values("pd", kind="stable").reset_index(drop=True)
    assert np.all(np.diff(t["pd"].to_numpy().astype("f4")) >= 0)
    paises, ratings = sorted(t["pais"].astype(str).unique()), ["AA", "A", "B", "C", "D", "E", "F", "G"]
    resumen = json.loads((path("outputs") / "corte/resumen_corte.json").read_text(encoding="utf-8"))
    cfg = settings()["corte"]
    carga = float(df.loc[df["particion"] == "entrenamiento", "carga_pct"].quantile(.999))  # arriba de esto el modelo casi no tiene datos
    destino = ROOT / "app" / "datos"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "prueba.bin.gz").write_bytes(gzip.compress(columnas_binarias(t, paises, ratings), 9, mtime=0))
    with open(destino / "app.json", "w", encoding="utf-8") as fh:
        json.dump({"n": len(t), "paises": paises, "ratings": ratings, "scorecard": scorecard_json(m), "lgd": cfg["lgd"], "lgd_baja": cfg["lgd_baja"],
                   "costo": cfg["costo_central_pp"], "corte_ks": resumen["corte_ks"], "corte_economico": resumen["corte_economico"], "carga_p999": round(carga, 1)}, fh, ensure_ascii=False, indent=1)
    print(f"app: {len(t):,} créditos")


if __name__ == "__main__":
    main()
