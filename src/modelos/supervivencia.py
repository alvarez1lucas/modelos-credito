"""Supervivencia con riesgos competidores: cuándo llega el default y cuánto lo tapa la precancelación.

`python -m modelos.supervivencia` escribe outputs/supervivencia/.

Un modelo a 12 meses mira un solo punto. Un crédito a 60 meses puede terminar de tres formas: default, cancelación
anticipada o sigue vivo cuando se sacó la foto (censurado). El estimador de Aalen-Johansen da la incidencia acumulada
de cada causa sin descartar a los censurados, y sin tratar la precancelación como si fuera censura, que sobreestimaría
el default: quien canceló ya no puede caer.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from modelos.config import path, settings
from modelos.datos import ORDEN_RATING, cargar

CENSURADO, DEFAULT, PAGO = 0, 1, 2
HORIZONTES = [6, 12, 18, 24, 30, 36]


def duraciones(df: pd.DataFrame) -> pd.DataFrame:
    """Meses hasta el primero de: evento, pago total o foto. Un mes corresponde a 30,44 días."""
    mes = 30.4375
    out = pd.DataFrame(index=df.index)
    fin_pago = df["fecha_precancelacion"].pipe(pd.to_datetime)
    meses_pago = ((fin_pago - df["fecha"]).dt.days / mes).fillna(df["plazo"].astype(float))
    meses_evento = (df["fecha_evento"] - df["fecha"]).dt.days / mes
    out["causa"] = np.select([df["evento"], df["pagado"]], [DEFAULT, PAGO], CENSURADO)
    out["t"] = np.select([df["evento"], df["pagado"]], [meses_evento, np.minimum(meses_pago, df["antiguedad_meses"])], df["antiguedad_meses"])
    out["t"] = np.ceil(out["t"].clip(lower=1)).astype(int)
    return out


def aalen_johansen(t: np.ndarray, causa: np.ndarray, hasta: int) -> pd.DataFrame:
    """Incidencia acumulada de cada causa por mes."""
    filas, s, f1, f2 = [], 1.0, 0.0, 0.0
    for m in range(1, hasta + 1):
        en_riesgo = (t >= m).sum()
        if en_riesgo == 0:
            break
        d1 = ((t == m) & (causa == DEFAULT)).sum()
        d2 = ((t == m) & (causa == PAGO)).sum()
        f1 += s * d1 / en_riesgo
        f2 += s * d2 / en_riesgo
        s *= 1 - (d1 + d2) / en_riesgo
        filas.append({"mes": m, "default": f1, "pago": f2, "vivo": s, "en_riesgo": int(en_riesgo)})
    return pd.DataFrame(filas)


def uno_menos_km(t: np.ndarray, causa: np.ndarray, hasta: int) -> pd.DataFrame:
    """Kaplan-Meier tratando el pago como censura: el error habitual, para compararlo."""
    filas, s = [], 1.0
    for m in range(1, hasta + 1):
        en_riesgo = (t >= m).sum()
        if en_riesgo == 0:
            break
        s *= 1 - ((t == m) & (causa == DEFAULT)).sum() / en_riesgo
        filas.append({"mes": m, "default_km": 1 - s})
    return pd.DataFrame(filas)


def main() -> None:
    df = cargar()
    d = duraciones(df)
    hasta = max(HORIZONTES)
    minimo = 500
    curvas = []
    for r in ["Todos", *ORDEN_RATING]:
        g = d if r == "Todos" else d[df["rating"] == r]
        c = aalen_johansen(g["t"].to_numpy(), g["causa"].to_numpy(), hasta).assign(rating=r)
        curvas.append(c[c["en_riesgo"] >= minimo])
    curvas = pd.concat(curvas, ignore_index=True)
    km = uno_menos_km(d["t"].to_numpy(), d["causa"].to_numpy(), hasta)

    tabla = curvas[curvas["mes"].isin(HORIZONTES)].pivot(index="rating", columns="mes", values="default").reindex(["Todos", *ORDEN_RATING])
    tasa = df.groupby("rating")["tasa"].mean()
    out = path("outputs") / "supervivencia"
    out.mkdir(parents=True, exist_ok=True)
    curvas.to_csv(out / "incidencia_acumulada.csv", index=False, float_format="%.5f")
    todos = curvas[curvas["rating"] == "Todos"].merge(km, on="mes")
    todos.to_csv(out / "todos_con_km.csv", index=False, float_format="%.5f")
    (100 * tabla).to_csv(out / "default_por_rating.csv", float_format="%.2f")
    ult = todos.iloc[-1]
    with open(out / "resumen_supervivencia.json", "w", encoding="utf-8") as fh:
        json.dump({"creditos": len(d), "causas": d["causa"].value_counts().to_dict(), "ultimo_mes": int(ult["mes"]),
                   "default_ultimo_pct": 100 * float(ult["default"]), "pago_ultimo_pct": 100 * float(ult["pago"]),
                   "vivo_ultimo_pct": 100 * float(ult["vivo"]), "km_ultimo_pct": 100 * float(ult["default_km"]),
                   "default_12_pct": 100 * float(todos.loc[todos["mes"] == 12, "default"].iloc[0]),
                   "pago_12_pct": 100 * float(todos.loc[todos["mes"] == 12, "pago"].iloc[0]),
                   "tasa_por_rating": {k: round(100 * float(v), 1) for k, v in tasa.items()}}, fh, ensure_ascii=False, indent=2)
    print((100 * tabla).round(1).to_string())
    print(todos[todos["mes"].isin(HORIZONTES)].round(3).to_string())


if __name__ == "__main__":
    main()
