import numpy as np
import pandas as pd
import pytest

from modelos.datos import CATEGORICAS
from modelos.entrenar import aplicar_calibrador, recalibrar
from modelos.scorecard import Scorecard

CFG = {"bins": 5, "iv_minimo": 0.0, "puntos_base": 600, "odds_base": 50, "pdo": 20}


@pytest.fixture
def datos():
    rng = np.random.default_rng(1)
    n = 8000
    d = pd.DataFrame({"monto": rng.uniform(100, 5000, n), "tasa": rng.uniform(.1, .3, n), "plazo": rng.integers(6, 60, n).astype(float),
                      "ingreso": rng.uniform(500, 4000, n), "carga_pct": rng.uniform(0, 30, n), "cuota": rng.uniform(10, 300, n),
                      "pais": rng.choice(["a", "b"], n)})
    y = pd.Series((rng.random(n) < .03 + .5 * (d["tasa"] - .1) + .05 * (d["pais"] == "b")).astype(int))
    return d, y


def test_puntos_suben_cuando_baja_el_riesgo(datos):
    d, y = datos
    s = Scorecard(CFG).ajustar(d, y, CATEGORICAS)
    assert np.corrcoef(s.puntos(d), s.pd(d))[0, 1] < -0.9


def test_doblar_odds_suma_pdo(datos):
    d, y = datos
    s = Scorecard(CFG).ajustar(d, y, CATEGORICAS)
    p, pts = s.pd(d), s.puntos(d)
    odds = (1 - p) / p
    pendiente = np.polyfit(np.log2(odds), pts, 1)[0]
    assert pendiente == pytest.approx(20, abs=1e-6)


def test_tabla_de_puntos_reproduce_el_puntaje(datos):
    d, y = datos
    s = Scorecard(CFG).ajustar(d, y, CATEGORICAS)
    tabla = s.tabla_puntos()
    total = np.full(len(d), s.base())
    for t, b in zip(s.tramos, s.modelo.coef_[0]):
        total += -(CFG["pdo"] / np.log(2)) * b * t.transformar(d[t.variable])
    assert total == pytest.approx(s.puntos(d))
    assert set(tabla["variable"]) == {t.variable for t in s.tramos}


def test_recalibrar_corrige_el_nivel_sin_cambiar_el_orden():
    rng = np.random.default_rng(2)
    real = rng.uniform(.02, .3, 50000)
    y = (rng.random(50000) < real).astype(int)
    sesgada = real * .5
    c = recalibrar(sesgada, y)
    p = aplicar_calibrador(c, sesgada)
    assert p.mean() == pytest.approx(y.mean(), abs=.005)
    assert (np.argsort(p) == np.argsort(sesgada)).all()
