import numpy as np
import pandas as pd
import pytest

from modelos import corte, supervivencia as s


@pytest.fixture
def cartera():
    return pd.DataFrame({"monto": [100.0, 100.0, 100.0, 100.0], "tasa": [0.2, 0.2, 0.2, 0.2], "malo": [0, 0, 0, 1], "rating": ["A", "B", "E", "G"]})


def test_resultado_credito(cartera):
    r = corte.resultado_credito(cartera, 10, 0.5)
    assert r.tolist() == pytest.approx([10, 10, 10, -40])


def test_corte_economico_excluye_lo_que_pierde(cartera):
    p = np.array([0.02, 0.03, 0.04, 0.5])
    e = corte.corte_economico(cartera, p, 10, 0.5)
    assert 0.04 <= e < 0.5


def test_corte_ks_separa_buenos_y_malos():
    y = np.array([0, 0, 0, 1, 1])
    assert corte.corte_ks(y, np.array([.1, .2, .3, .7, .8])) == pytest.approx(.3)


def test_margen_esperado_compara_con_la_tasa(cartera):
    p = np.array([0.1, 0.1, 0.3, 0.1])
    a = corte.reglas(cartera, p, .5, .5, 10, 0.5)["Margen esperado por crédito"]
    assert a.tolist() == [True, True, False, True]


def test_evaluar_mide_el_cambio_de_sacar_lo_malo(cartera):
    r = corte.resultado_credito(cartera, 10, 0.5)
    e = corte.evaluar(cartera, np.array([True, True, True, False]), r, n_boot=20)
    assert e["cambio"] == pytest.approx(40) and e["aprobados_pct"] == 75 and e["mora_pct"] == 0


def test_aalen_johansen_sin_censura_suma_uno():
    t = np.array([1, 1, 2, 2, 3])
    c = np.array([1, 2, 1, 2, 1])
    r = s.aalen_johansen(t, c, 3)
    fin = r.iloc[-1]
    assert fin["default"] == pytest.approx(.6) and fin["pago"] == pytest.approx(.4) and fin["vivo"] == pytest.approx(0)


def test_censura_reparte_el_riesgo_hacia_adelante():
    r = s.aalen_johansen(np.array([1, 2, 2, 2]), np.array([0, 1, 0, 0]), 2)
    assert r.iloc[-1]["default"] == pytest.approx(1 / 3)


def test_tratar_el_pago_como_censura_sobreestima_el_default():
    rng = np.random.default_rng(1)
    t = rng.integers(1, 20, 5000)
    c = rng.choice([1, 2], 5000, p=[.3, .7])
    aj = s.aalen_johansen(t, c, 19).iloc[-1]["default"]
    km = s.uno_menos_km(t, c, 19).iloc[-1]["default_km"]
    assert km > aj + .1


def test_duraciones_asigna_causas():
    df = pd.DataFrame({"fecha": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]), "fecha_evento": pd.to_datetime(["2024-07-01", None, None]),
                       "fecha_precancelacion": [None, pd.Timestamp("2024-04-01"), None], "evento": [True, False, False], "pagado": [False, True, False],
                       "plazo": [36, 36, 36], "antiguedad_meses": [20.0, 20.0, 20.0]})
    d = s.duraciones(df)
    assert d["causa"].tolist() == [s.DEFAULT, s.PAGO, s.CENSURADO]
    assert d["t"].tolist() == [6, 3, 20]
