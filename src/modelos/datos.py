"""Datos de modelado: un crédito por fila, con lo que se sabía al otorgarlo y su resultado a 12 meses.

Sólo entran variables que no cambian después del otorgamiento: comparando dos fotos de la cartera, el rating
cambia en 0,02% de los créditos y el ingreso, la tasa, el monto y el plazo en ninguno. `nr_of_payments` cambia en
26% y queda afuera, igual que todo lo que describe el desempeño.

El evento usa la misma definición que el proyecto umbrales-credito: 90 días de atraso, default o pase a pérdida,
fechado en el inicio del atraso + 90 días. Si la foto no alcanza a mostrar 12 meses, el crédito no se usa.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from modelos.config import path, settings

NUMERICAS = ["monto", "tasa", "plazo", "ingreso", "carga_pct", "cuota"]
CATEGORICAS = ["pais"]
BENCHMARK = "rating"
ORDEN_RATING = {"AA": 1, "A": 2, "B": 3, "C": 4, "D": 5, "E": 6, "F": 7, "G": 8}


def cargar(fotos: str | None = None) -> pd.DataFrame:
    """Última foto de cada crédito, con las variables de originación y el evento."""
    cfg = settings()["datos"]
    origen = fotos or str(path("fotos") / "bondora_*.parquet").replace("\\", "/")
    dias = cfg["dias_evento"]
    df = duckdb.sql(f"""
        with fotos as (
            select * from read_parquet('{origen}', union_by_name = true)
            qualify fecha_foto = max(fecha_foto) over (partition by loan_id)
        ),
        base as (
            select *, loan_status_risk = 'Written Off' as castigado,
                   case when year(debt_occured_date_local) > 1970 then cast(debt_occured_date_local as date) end as inicio_atraso
            from fotos
            where loan_status in ('Active', 'Repaid', 'Defaulted') and loan_status_risk <> 'Cancelled'
              and not coalesce(is_early_repaid_within_14_days, false)
              and loan_issued_at >= date '{cfg['desde']}'
              and customer_risk_rating is not null and combined_income > 0 and initial_loan_duration > 0 and initial_interest_rate > 0
        ),
        eventos as (
            select *,
                (castigado or loan_status = 'Defaulted' or coalesce(is_default, false) or coalesce(days_past_due_principal, 0) >= {dias}) as evento
            from base
        )
        select
            loan_id as prestamo_id,
            cast(fecha_foto as date)                 as fecha_foto,
            cast(loan_issued_at as date)             as fecha,
            country                                  as pais,
            customer_risk_rating                     as rating,
            projected_npv_return                     as npv_bondora,
            issued_amount                            as monto,
            initial_interest_rate                    as tasa,
            initial_loan_duration                    as plazo,
            combined_income                          as ingreso,
            evento,
            case when evento then least(cast(fecha_foto as date),
                coalesce(inicio_atraso + to_days({dias}),
                         cast(fecha_foto - to_days(cast(days_past_due_principal as integer) - {dias}) as date),
                         cast(fecha_foto as date))) end as fecha_evento,
            cast(early_repaid_at as date)            as fecha_precancelacion,
            loan_status = 'Repaid' and not castigado and not evento as pagado
        from eventos
    """).df()
    return preparar(df)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Cuota, carga y ventanas de tiempo."""
    h = settings()["datos"]["horizonte_meses"]
    out = df.copy()
    out["fecha"] = pd.to_datetime(out["fecha"])
    out["fecha_foto"] = pd.to_datetime(out["fecha_foto"])
    out["fecha_evento"] = pd.to_datetime(out["fecha_evento"])
    i = out["tasa"] / 12
    out["cuota"] = out["monto"] * i / (1 - (1 + i) ** (-out["plazo"].astype(float)))
    out["carga_pct"] = 100 * out["cuota"] / out["ingreso"]
    out["antiguedad_meses"] = (out["fecha_foto"] - out["fecha"]).dt.days / 30.4375
    dias_evento = (out["fecha_evento"] - out["fecha"]).dt.days
    out["malo"] = (out["evento"] & (dias_evento <= h * 30.4375)).astype(int)
    out["maduro"] = out["antiguedad_meses"] >= h
    return out


def particion(df: pd.DataFrame) -> pd.Series:
    """Entrenamiento, validación y prueba por fecha de otorgamiento: el futuro nunca se usa para aprender."""
    cfg = settings()["datos"]
    p = pd.Series("prueba", index=df.index)
    p[df["fecha"] <= pd.Timestamp(cfg["fin_validacion"])] = "validacion"
    p[df["fecha"] <= pd.Timestamp(cfg["fin_entrenamiento"])] = "entrenamiento"
    return p.where(df["maduro"], "sin_madurar")


def matriz(df: pd.DataFrame, con_rating: bool, categorias: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Variables para los modelos de árboles, con categorías fijas para que entrenar y puntuar coincidan."""
    X = df[NUMERICAS].astype(float).copy()
    for c in CATEGORICAS:
        X[c] = pd.Categorical(df[c], categories=(categorias or {}).get(c, sorted(df[c].unique())))
    if con_rating:
        X["rating_ord"] = df[BENCHMARK].map(ORDEN_RATING).astype(float)
    return X


def log_odds(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))
