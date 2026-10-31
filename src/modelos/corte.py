"""El punto de corte es otro umbral: se elige por resultado económico, no por una métrica estadística.

`python -m modelos.corte` escribe outputs/corte/.

Todas las reglas se fijan en validación y se miden en prueba. Se comparan:
- aprobar todo lo que se aprobó (punto de partida: la cartera ya pasó por la política de Bondora);
- el corte estadístico habitual, que maximiza KS y no sabe nada de plata;
- el corte económico, la PD única que maximiza el resultado en validación;
- la regla por margen esperado, crédito por crédito: aprobar si PD × LGD < tasa - costo;
- la regla simple de sacar ratings E a G, como comparación contra lo que ya se puede hacer sin modelo.

Los créditos rechazados por Bondora no se observan: sólo se puede evaluar endurecer.
El costo y la LGD son supuestos, por eso se muestra la sensibilidad.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from modelos.config import path, settings
from modelos.datos import cargar, particion
from modelos.puntaje import cargar_modelos, pd_scorecard


def resultado_credito(df: pd.DataFrame, costo_pp: float, lgd: float) -> np.ndarray:
    """Resultado del primer año: monto × (tasa - costo) - evento × LGD × monto."""
    monto = df["monto"].to_numpy()
    return monto * (df["tasa"].to_numpy() - costo_pp / 100) - df["malo"].to_numpy() * lgd * monto


def grilla_cortes() -> np.ndarray:
    return np.round(np.arange(0.01, 0.6001, 0.0025), 4)


def curva(df: pd.DataFrame, p: np.ndarray, costo_pp: float, lgd: float) -> pd.DataFrame:
    r = resultado_credito(df, costo_pp, lgd)
    malo, monto = df["malo"].to_numpy(), df["monto"].to_numpy()
    filas = []
    for c in grilla_cortes():
        a = p <= c
        filas.append({"corte_pd": c, "aprobados_pct": 100 * a.mean(), "mora_pct": 100 * malo[a].mean() if a.any() else np.nan,
                      "resultado": r[a].sum(), "resultado_pct_monto": 100 * r[a].sum() / monto[a].sum() if a.any() else np.nan})
    return pd.DataFrame(filas)


def corte_ks(y: np.ndarray, p: np.ndarray) -> float:
    """Corte que maximiza la separación entre malos y buenos."""
    orden = np.argsort(p)
    ys, ps = y[orden], p[orden]
    d = np.cumsum(ys) / ys.sum() - np.cumsum(1 - ys) / (1 - ys).sum()
    return float(ps[int(np.argmax(np.abs(d)))])


def corte_economico(df: pd.DataFrame, p: np.ndarray, costo_pp: float, lgd: float) -> float:
    c = curva(df, p, costo_pp, lgd)
    return float(c.loc[c["resultado"].idxmax(), "corte_pd"])


def reglas(df: pd.DataFrame, p: np.ndarray, ks: float, eco: float, costo_pp: float, lgd: float) -> dict[str, np.ndarray]:
    return {"Aprobar todo": np.ones(len(df), bool), "Sin ratings E a G": ~df["rating"].isin(["E", "F", "G"]).to_numpy(),
            "Corte por KS": p <= ks, "Corte económico": p <= eco,
            "Margen esperado por crédito": p * lgd < df["tasa"].to_numpy() - costo_pp / 100}


def evaluar(df: pd.DataFrame, aprobado: np.ndarray, r: np.ndarray, n_boot: int = 500, seed: int = 7) -> dict:
    """Métricas de una regla y el intervalo de lo que cambia contra aprobar todo."""
    rng = np.random.default_rng(seed)
    malo, monto = df["malo"].to_numpy(), df["monto"].to_numpy()
    fuera = r[~aprobado]
    ic = (0.0, 0.0)
    if len(fuera):
        i = rng.integers(0, len(fuera), (n_boot, len(fuera)))
        ic = tuple(np.percentile(-fuera[i].sum(axis=1), [2.5, 97.5]))
    return {"aprobados_pct": 100 * aprobado.mean(), "monto_pct": 100 * monto[aprobado].sum() / monto.sum(), "mora_pct": 100 * malo[aprobado].mean(),
            "resultado": float(r[aprobado].sum()), "cambio": float(-fuera.sum()), "cambio_inf": float(ic[0]), "cambio_sup": float(ic[1]),
            "resultado_pct_monto": 100 * r[aprobado].sum() / monto[aprobado].sum()}


def main() -> None:
    cfg = settings()["corte"]
    df = cargar()
    df["particion"] = particion(df)
    m = cargar_modelos()
    va = df[df["particion"] == "validacion"].reset_index(drop=True)
    pr = df[df["particion"] == "prueba"].reset_index(drop=True)
    pva, ppr = pd_scorecard(m, va), pd_scorecard(m, pr)
    costo, lgd = cfg["costo_central_pp"], cfg["lgd"]

    ks = corte_ks(va["malo"].to_numpy(), pva)
    eco = corte_economico(va, pva, costo, lgd)
    r = resultado_credito(pr, costo, lgd)
    tabla = pd.DataFrame([{"regla": k, **evaluar(pr, a, r)} for k, a in reglas(pr, ppr, ks, eco, costo, lgd).items()])

    sens = []
    for c in cfg["costos_pp"]:
        for lg in (cfg["lgd"], cfg["lgd_baja"]):
            e = corte_economico(va, pva, c, lg)
            rr = resultado_credito(pr, c, lg)
            sens.append({"costo_pp": c, "lgd": lg, "corte_economico": e, **evaluar(pr, ppr <= e, rr, n_boot=100)})
    sens = pd.DataFrame(sens)

    # La regla por margen depende del costo: se muestra cuánto gana, y cuánto viene de rechazar un país entero
    margen = []
    for c in cfg["costos_pp"]:
        rr = resultado_credito(pr, c, lgd)
        a = ppr * lgd < pr["tasa"].to_numpy() - c / 100
        g = pd.DataFrame({"pais": pr["pais"], "a": a, "r": rr})
        for pais, x in [("Total", g), *g.groupby("pais")]:
            margen.append({"costo_pp": c, "pais": pais, "aprobados_pct": 100 * x["a"].mean(), "cambio": float(-x.loc[~x["a"], "r"].sum())})
    margen = pd.DataFrame(margen)

    aprobado = ppr <= eco
    por_pais = pr.assign(aprobado=aprobado, r=r).groupby("pais").agg(creditos=("malo", "size"), mora_pct=("malo", lambda s: 100 * s.mean()),
                                                                     aprobados_pct=("aprobado", lambda s: 100 * s.mean()), resultado=("r", "sum")).reset_index()
    por_rating = pr.assign(aprobado=aprobado).groupby("rating").agg(creditos=("malo", "size"), aprobados_pct=("aprobado", lambda s: 100 * s.mean())).reset_index()

    out = path("outputs") / "corte"
    out.mkdir(parents=True, exist_ok=True)
    curva(pr, ppr, costo, lgd).to_csv(out / "curva_prueba.csv", index=False, float_format="%.4f")
    curva(va, pva, costo, lgd).to_csv(out / "curva_validacion.csv", index=False, float_format="%.4f")
    tabla.to_csv(out / "reglas_prueba.csv", index=False, float_format="%.4f")
    sens.to_csv(out / "sensibilidad.csv", index=False, float_format="%.4f")
    margen.to_csv(out / "margen_por_costo.csv", index=False, float_format="%.4f")
    por_pais.to_csv(out / "por_pais.csv", index=False, float_format="%.4f")
    por_rating.to_csv(out / "por_rating.csv", index=False, float_format="%.4f")
    with open(out / "resumen_corte.json", "w", encoding="utf-8") as fh:
        json.dump({"corte_ks": ks, "corte_economico": eco, "costo_pp": costo, "lgd": lgd,
                   "equilibrio_teorico_pd": float((pr["tasa"].mean() - costo / 100) / lgd),
                   "monto_prueba": float(pr["monto"].sum()), "creditos_prueba": len(pr)}, fh, ensure_ascii=False, indent=2)
    print(tabla.round(3).to_string())
    print({"ks": ks, "eco": eco})


if __name__ == "__main__":
    main()
