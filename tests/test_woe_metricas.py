import numpy as np
import pandas as pd
import pytest

from modelos import metricas as m
from modelos import woe


def test_woe_positivo_en_el_tramo_bueno():
    x = pd.Series(np.r_[np.repeat(1.0, 500), np.repeat(2.0, 500)], name="v")
    y = pd.Series(np.r_[np.zeros(450), np.ones(50), np.zeros(350), np.ones(150)].astype(int))
    t = woe.ajustar_numerica(x, y, bins=2)
    assert t.woe[0] > 0 > t.woe[-1]
    assert t.iv > 0.02


def test_tramos_quedan_monotonos():
    rng = np.random.default_rng(1)
    x = pd.Series(rng.uniform(0, 1, 20000), name="v")
    y = pd.Series((rng.random(20000) < 0.05 + 0.2 * x + 0.03 * np.sin(30 * x)).astype(int))
    w = np.array(woe.ajustar_numerica(x, y, bins=20).woe)
    d = np.diff(w)
    assert (d <= 0).all() or (d >= 0).all()


def test_transformar_categoria_nueva_es_neutra():
    t = woe.Tramos("pais", None, ["a", "b"], [0.5, -0.5], 0.1)
    assert t.transformar(pd.Series(["a", "z"])).tolist() == [0.5, 0.0]


def test_transformar_numerica_usa_el_tramo_correcto():
    t = woe.Tramos("v", [1.0, float("inf")], None, [0.3, -0.3], 0.1)
    assert t.transformar(pd.Series([0.5, 1.0, 9.0])).tolist() == [0.3, 0.3, -0.3]


def test_gini_y_ks_extremos():
    y = np.array([0, 0, 1, 1])
    assert m.gini(y, np.array([1, 2, 3, 4])) == pytest.approx(1)
    assert m.gini(y, np.array([4, 3, 2, 1])) == pytest.approx(-1)
    assert m.ks(y, np.array([1, 2, 3, 4])) == pytest.approx(1)


def test_psi_cero_si_no_cambia_y_alto_si_cambia():
    rng = np.random.default_rng(2)
    a = rng.normal(size=20000)
    assert m.psi(a, a) == pytest.approx(0)
    assert m.psi(a, a + 1) > 0.25


def test_calibracion_perfecta():
    rng = np.random.default_rng(3)
    p = rng.uniform(0.01, 0.4, 200000)
    y = (rng.random(200000) < p).astype(int)
    assert m.error_calibracion(y, p) < 0.5


def test_psi_categorica():
    a = pd.Series(["x"] * 50 + ["y"] * 50)
    assert m.psi_categorica(a, a) == pytest.approx(0)
    assert m.psi_categorica(a, pd.Series(["x"] * 90 + ["y"] * 10)) > 0.25
