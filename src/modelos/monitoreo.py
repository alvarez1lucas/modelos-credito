"""Monitoreo del modelo congelado: cada cosecha que madura se compara contra lo que predijo.

`python -m modelos.monitoreo` escribe outputs/monitoreo/ y agrega una fila al historial por cada foto.

El modelo no se reentrena acá. Se vigila lo que un Gini global no muestra:
- discriminación y calibración por trimestre de originación;
- cambio de población contra entrenamiento (PSI);
- segmentos fuera de dominio: países que el modelo nunca vio;
- calibración por país, porque un promedio global esconde segmentos muy mal predichos.
Cada señal da un grado (ok, vigilar, actuar) según los umbrales de config/settings.yaml.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from modelos import metricas as m
from modelos.config import path, settings
from modelos.datos import cargar, log_odds, particion
from modelos.puntaje import cargar_modelos, pd_scorecard

GRADOS = ["ok", "vigilar", "actuar"]


def grado(valor: float, vigilar: float, actuar: float) -> str:
    return "actuar" if valor >= actuar else "vigilar" if valor >= vigilar else "ok"


def peor(grados: list[str]) -> str:
    return max(grados, key=GRADOS.index)


def corrimiento(p_prev: np.ndarray, y_prev: np.ndarray) -> float:
    """Ajuste en log-odds que iguala la PD media de una cosecha con lo que después se observó en ella."""
    objetivo = float(np.mean(y_prev))
    lo, hi = -5.0, 5.0
    base = log_odds(p_prev)
    for _ in range(60):
        medio = (lo + hi) / 2
        if (1 / (1 + np.exp(-(base + medio)))).mean() < objetivo:
            lo = medio
        else:
            hi = medio
    return (lo + hi) / 2


def serie_trimestral(df: pd.DataFrame, p: np.ndarray, referencia: np.ndarray) -> pd.DataFrame:
    """Métricas por cosecha, con la brecha que quedaría recalibrando con el trimestre maduro anterior."""
    d = df.assign(p=p, trimestre=df["fecha"].dt.to_period("Q").astype(str))
    filas, anterior = [], None
    for t, g in d.groupby("trimestre"):
        y, q = g["malo"].to_numpy(), g["p"].to_numpy()
        recal = None
        if anterior is not None:
            d0 = corrimiento(*anterior)
            recal = 100 * float((1 / (1 + np.exp(-(log_odds(q) + d0)))).mean())
        filas.append({"trimestre": t, "n": len(g), "gini": m.gini(y, q), "pd_media_pct": 100 * q.mean(), "observado_pct": 100 * y.mean(),
                      "brecha_pp": 100 * (y.mean() - q.mean()), "brecha_recalibrada_pp": None if recal is None else 100 * y.mean() - recal,
                      "psi_puntaje": m.psi(referencia, q)})
        anterior = (q, y)
    return pd.DataFrame(filas)


def fuera_de_dominio(df: pd.DataFrame, paises_entrenamiento: set[str]) -> list[str]:
    return sorted(set(df["pais"].unique()) - paises_entrenamiento)


def main() -> None:
    cfg = settings()["monitoreo"]
    df = cargar()
    df["particion"] = particion(df)
    mo = cargar_modelos()
    tr = df[df["particion"] == "entrenamiento"]
    paises = set(tr["pais"].unique())
    p_ref = pd_scorecard(mo, tr)
    fuera_tr = df[(df["particion"].isin(["validacion", "prueba"]))].reset_index(drop=True)
    p = pd_scorecard(mo, fuera_tr)
    serie = serie_trimestral(fuera_tr, p, p_ref)
    ult = serie.iloc[-1]

    d = fuera_tr.assign(p=p)
    reciente = d[d["fecha"].dt.to_period("Q").astype(str).isin(serie["trimestre"].tail(2))]
    pais = reciente.groupby("pais").agg(n=("malo", "size"), pd_media_pct=("p", lambda s: 100 * s.mean()), observado_pct=("malo", lambda s: 100 * s.mean())).reset_index()
    pais["brecha_pp"] = pais["observado_pct"] - pais["pd_media_pct"]
    pais["fuera_de_dominio"] = ~pais["pais"].isin(paises)

    # sin madurar: la población ya se ve aunque el resultado todavía no
    nuevos = df[df["particion"] == "sin_madurar"]
    psi_nuevos = m.psi(p_ref, pd_scorecard(mo, nuevos))
    gini_base = float(serie.iloc[0]["gini"])
    senales = {
        "discriminacion": {"valor": gini_base - float(ult["gini"]), "grado": grado(gini_base - float(ult["gini"]), cfg["caida_gini"]["vigilar"], cfg["caida_gini"]["actuar"])},
        "calibracion": {"valor": abs(float(ult["brecha_pp"])), "grado": grado(abs(float(ult["brecha_pp"])), cfg["brecha_pp"]["vigilar"], cfg["brecha_pp"]["actuar"])},
        "calibracion_por_pais": {"valor": float(pais["brecha_pp"].abs().max()), "pais": pais.loc[pais["brecha_pp"].abs().idxmax(), "pais"],
                                 "grado": grado(float(pais["brecha_pp"].abs().max()), cfg["brecha_pais_pp"]["vigilar"], cfg["brecha_pais_pp"]["actuar"])},
        "poblacion": {"valor": psi_nuevos, "grado": grado(psi_nuevos, cfg["psi"]["vigilar"], cfg["psi"]["actuar"])},
    }
    externos = fuera_de_dominio(df[df["particion"] != "entrenamiento"], paises)
    senales["fuera_de_dominio"] = {"valor": externos, "grado": "actuar" if externos else "ok"}
    global_ = peor([s["grado"] for s in senales.values()])

    out = path("outputs") / "monitoreo"
    out.mkdir(parents=True, exist_ok=True)
    serie.to_csv(out / "serie_trimestral.csv", index=False, float_format="%.4f")
    pais.to_csv(out / "brecha_por_pais.csv", index=False, float_format="%.4f")
    fecha = str(df["fecha_foto"].max().date())
    with open(out / "alertas.json", "w", encoding="utf-8") as fh:
        json.dump({"fecha_foto": fecha, "ultimo_trimestre": ult["trimestre"], "grado": global_, "senales": senales}, fh, ensure_ascii=False, indent=2)
    h = out / "historial.csv"
    fila = pd.DataFrame([{"fecha_foto": fecha, "ultimo_trimestre": ult["trimestre"], "gini": ult["gini"], "pd_media_pct": ult["pd_media_pct"],
                          "observado_pct": ult["observado_pct"], "brecha_pp": ult["brecha_pp"], "psi_nuevos": psi_nuevos, "grado": global_}])
    hist = pd.concat([pd.read_csv(h), fila], ignore_index=True) if h.exists() else fila
    hist.drop_duplicates("fecha_foto", keep="last").to_csv(h, index=False, float_format="%.4f")
    print(serie.round(3).to_string()); print(pais.round(2).to_string()); print(global_, json.dumps(senales, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
