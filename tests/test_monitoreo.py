import numpy as np
import pandas as pd
import pytest

from modelos import metricas as m
from modelos import monitoreo as mo


def test_grado_por_umbrales():
    assert mo.grado(.05, .1, .25) == "ok"
    assert mo.grado(.1, .1, .25) == "vigilar"
    assert mo.grado(.3, .1, .25) == "actuar"


def test_peor_grado():
    assert mo.peor(["ok", "vigilar"]) == "vigilar"
    assert mo.peor(["vigilar", "actuar", "ok"]) == "actuar"


def test_corrimiento_iguala_la_media():
    rng = np.random.default_rng(1)
    p = rng.uniform(.02, .2, 20000)
    y = (rng.random(20000) < p * 1.4).astype(float)
    d = mo.corrimiento(p, y)
    lo = np.log(p / (1 - p)) + d
    assert (1 / (1 + np.exp(-lo))).mean() == pytest.approx(y.mean(), abs=1e-4)


def test_serie_recalibrada_achica_una_brecha_persistente():
    rng = np.random.default_rng(2)
    n = 40000
    q = rng.uniform(.02, .2, n)
    y = (rng.random(n) < q * 1.4).astype(int)
    df = pd.DataFrame({"fecha": pd.to_datetime(np.where(np.arange(n) % 2, "2025-01-15", "2025-04-15")), "malo": y})
    s = mo.serie_trimestral(df, q, q)
    assert pd.isna(s.loc[0, "brecha_recalibrada_pp"])
    assert abs(s.loc[1, "brecha_recalibrada_pp"]) < abs(s.loc[1, "brecha_pp"]) / 3


def test_fuera_de_dominio_detecta_pais_nuevo():
    df = pd.DataFrame({"pais": ["Finland", "Denmark", "Denmark"]})
    assert mo.fuera_de_dominio(df, {"Finland"}) == ["Denmark"]


def test_psi_tasa_ignora_movimientos_chicos_entre_valores_de_lista():
    a = pd.Series([.18] * 500 + [.24] * 500)
    b = pd.Series([.181] * 500 + [.241] * 500)
    assert m.psi_categorica(m.tramo_tasa(a), m.tramo_tasa(b)) == pytest.approx(0)
