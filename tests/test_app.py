import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import logica as lg  # noqa: E402

from modelos import corte  # noqa: E402
from modelos.puntaje import cargar_modelos, pd_scorecard  # noqa: E402


@pytest.fixture(scope="module")
def sc():
    return lg.cargar_scorecard()


def _df(**kw):
    base = {"pais": ["Finland", "Estonia"], "rating": ["A", "C"], "ingreso": [2000.0, 2500.0], "monto": [1000.0, 3000.0], "tasa": [0.18, 0.22],
            "plazo": [36.0, 60.0], "cuota": [36.15, 82.8], "carga_pct": [1.8, 3.3], "npv_bondora": [0.1, 0.1]}
    return pd.DataFrame({**base, **kw})


def test_puntaje_json_coincide_con_el_modelo_guardado(sc):
    m = cargar_modelos()
    d = _df()
    p = pd_scorecard(m, d)
    pts = m["scorecard"].puntos(d)
    for i, f in d.iterrows():
        r = lg.puntuar(sc, f.to_dict())
        assert r["pd"] == pytest.approx(p[i], rel=1e-9)
        assert r["puntos"] == pytest.approx(pts[i], rel=1e-9)


def test_detalle_suma_el_puntaje(sc):
    r = lg.puntuar(sc, _df().iloc[0].to_dict())
    assert sc["base"] + sum(x["puntos"] for x in r["detalle"]) == pytest.approx(r["puntos"])


def test_pais_nuevo_es_neutro(sc):
    a = lg.puntuar(sc, _df(pais=["Denmark", "Denmark"]).iloc[0].to_dict())
    v = next(x for x in a["detalle"] if x["variable"] == "pais")
    assert v["puntos"] == 0


def test_cuota_francesa():
    assert lg.cuota(1000, 0.12, 12) == pytest.approx(88.85, abs=0.01)


@pytest.fixture
def cartera():
    return pd.DataFrame({"pais": ["a", "a", "b", "b"], "rating": ["A", "G", "A", "G"], "monto": [100.0] * 4, "tasa": [.2, .2, .2, .1], "malo": [0, 1, 0, 0], "pd": [.05, .5, .1, .1]})


def test_resultado_igual_al_del_proyecto(cartera):
    assert lg.resultado_credito(cartera, 10, .5).tolist() == corte.resultado_credito(cartera, 10, .5).tolist()


def test_regla_margen_compara_con_la_tasa(cartera):
    assert lg.aprobar(cartera, "margen", 0, 10, .5, [], []).tolist() == [True, False, True, False]


def test_exclusiones(cartera):
    assert lg.aprobar(cartera, "pd", 1, 10, .5, ["b"], ["G"]).tolist() == [True, False, False, False]


def test_curva_coincide_con_aplicar_el_corte(cartera):
    df = pd.DataFrame({"pais": "a", "rating": "A", "monto": 100.0, "tasa": .2, "malo": [0, 1, 0, 1, 0], "pd": [.02, .05, .1, .2, .3]})
    r = lg.resultado_credito(df, 10, .5)
    c = lg.curva(df, 10, .5).set_index("corte")["resultado"]
    for k in (.05, .1, .2):
        assert c[k] == pytest.approx(r[df["pd"].to_numpy() <= k].sum())


def test_prueba_exportada_reproduce_el_proyecto():
    df = lg.cargar_prueba()
    r = lg.resultado_credito(df, 10, .69)
    assert 100 * df["malo"].mean() == pytest.approx(7.883, abs=.01)
    assert r.sum() / 1e6 == pytest.approx(2.163, abs=.01)


def test_app_arranca_y_responde():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"), default_timeout=60).run()
    assert not at.exception
    assert len(at.metric) == 7
    regla = next(r for r in at.radio if "Margen por crédito" in r.options)
    regla.set_value("Margen por crédito").run()
    assert not at.exception
    assert any("Netherlands" in w.value or "Países Bajos" in w.value for w in at.warning)
    next(r for r in at.radio if "English" in r.options).set_value("English").run()
    assert not at.exception
