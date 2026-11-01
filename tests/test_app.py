import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import referencia_app as ref  # noqa: E402

from modelos import corte  # noqa: E402
from modelos.config import path  # noqa: E402
from modelos.puntaje import cargar_modelos, pd_scorecard  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BASE = {"regla": "pd", "corte": 0.2, "costo": 10, "lgd": 0.69, "sinPaises": [], "sinRatings": []}
ESCENARIOS = [BASE, {**BASE, "corte": 0.4}, {**BASE, "corte": 0.0761, "lgd": 0.5}, {**BASE, "regla": "margen"}, {**BASE, "regla": "margen", "costo": 5},
              {**BASE, "corte": 0.4, "sinRatings": ["E", "F", "G"]}, {**BASE, "corte": 0.12, "costo": 0, "sinPaises": ["Denmark", "Latvia"]},
              {**BASE, "regla": "margen", "costo": 20, "lgd": 0.9, "sinPaises": ["Finland"], "sinRatings": ["AA"]}, {**BASE, "corte": 0.001}]
CLIENTES = [{"monto": 2000, "tasa": 0.18, "plazo": 60, "ingreso": 2300, "pais": "Finland", "rating": "C"},
            {"monto": 518, "tasa": 0.1154, "plazo": 24, "ingreso": 1316.5325, "pais": "Estonia", "rating": "AA"},
            {"monto": 15000, "tasa": 0.35, "plazo": 120, "ingreso": 300, "pais": "Latvia", "rating": "G"},
            {"monto": 3000, "tasa": 0.22, "plazo": 48, "ingreso": 1800, "pais": "Denmark", "rating": "E"},
            {"monto": 100, "tasa": 0.05, "plazo": 6, "ingreso": 15000, "pais": "Netherlands", "rating": "A"}]


def _perfil(c):
    q = ref.cuota(c["monto"], c["tasa"], c["plazo"])
    return {**c, "carga_pct": 100 * q / c["ingreso"]}


@pytest.fixture(scope="module")
def js():
    if shutil.which("node") is None:
        if os.environ.get("CI"):
            pytest.fail("Falta Node en CI")
        pytest.skip("Node no está instalado")
    p = subprocess.run(["node", str(RAIZ / "tests" / "paridad.mjs")], input=json.dumps({"escenarios": ESCENARIOS, "clientes": CLIENTES}), capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(p.stdout)


@pytest.fixture(scope="module")
def df():
    return ref.cargar_prueba()


@pytest.fixture(scope="module")
def meta():
    return ref.cargar_meta()


def test_datos_exportados_reproducen_el_proyecto(df):
    assert len(df) == 137835
    assert df["pd"].is_monotonic_increasing
    assert 100 * df["malo"].mean() == pytest.approx(7.883, abs=.01)
    assert ref.resultado_credito(df, 10, .69).sum() / 1e6 == pytest.approx(2.163, abs=.01)


def test_ninguna_pd_supera_el_tope_del_control(df):
    assert df["pd"].max() < 0.4


def test_tope_de_carga_viene_del_entrenamiento(meta):
    assert 20 < meta["carga_p999"] < 40


def test_scorecard_exportada_coincide_con_el_modelo_guardado(meta):
    m = cargar_modelos()
    c = [_perfil(x) for x in CLIENTES]
    t = pd.DataFrame(c).assign(cuota=lambda d: d["carga_pct"] * d["ingreso"] / 100, npv_bondora=0.1)
    p = pd_scorecard(m, t)
    pts = m["scorecard"].puntos(t)
    for i, x in enumerate(c):
        r = ref.puntuar(meta["scorecard"], x)
        assert r["pd"] == pytest.approx(p[i], rel=1e-9)
        assert r["puntos"] == pytest.approx(pts[i], rel=1e-9)


def test_resultado_de_la_referencia_igual_al_del_proyecto():
    t = pd.DataFrame({"monto": [100.0, 200.0], "tasa": [.2, .1], "malo": [0, 1]})
    assert ref.resultado_credito(t, 10, .5).tolist() == corte.resultado_credito(t, 10, .5).tolist()


@pytest.mark.parametrize("i", range(len(ESCENARIOS)))
def test_escenario_igual_en_javascript_y_en_python(js, df, i):
    e, s = ESCENARIOS[i], js["escenarios"][i]
    r = ref.resultado_credito(df, e["costo"], e["lgd"])
    a = ref.aprobar(df, e)
    for k, v in ref.resumen(df, a, r).items():
        assert s["resumen"][k] == (None if v is None else pytest.approx(v, rel=1e-9, abs=1e-6)), k
    assert s["curva"] == pytest.approx(ref.curva(df, r, e, js["cortes"]), rel=1e-9, abs=1e-6)
    for campo in ("pais", "rating"):
        p = ref.por_segmento(df, a, r, campo).set_index("clave")
        for f in s[campo]:
            for k in ("creditos", "aprobados", "mora", "cambio"):
                assert f[k] == pytest.approx(p.loc[f["clave"], k], rel=1e-9, abs=1e-6), (campo, f["clave"], k)


@pytest.mark.parametrize("i", range(len(CLIENTES)))
def test_cliente_igual_en_javascript_y_en_python(js, df, meta, i):
    sc, c, s = meta["scorecard"], _perfil(CLIENTES[i]), js["clientes"][i]
    r = ref.puntuar(sc, c)
    assert s["pd"] == pytest.approx(r["pd"], rel=1e-12)
    assert s["puntos"] == pytest.approx(r["puntos"], rel=1e-12)
    assert [x["puntos"] for x in s["detalle"]] == pytest.approx([x["puntos"] for x in r["detalle"]], rel=1e-12, abs=1e-12)
    assert sc["base"] + sum(x["puntos"] for x in s["detalle"]) == pytest.approx(s["puntos"])
    assert s["percentil"] == pytest.approx((df["pd"].to_numpy() < float(pd.Series([r["pd"]]).astype("float32").iloc[0])).mean(), abs=1e-3)


def test_tasa_de_equilibrio_es_la_primera_que_aprueba(js, meta):
    sc, costo, lgd = meta["scorecard"], meta["costo"], meta["lgd"]
    aprueba = lambda c, t: t - costo / 100 - ref.puntuar(sc, _perfil({**c, "tasa": t}))["pd"] * lgd > 0  # noqa: E731
    for c, s in zip(CLIENTES, js["clientes"]):
        t = s["equilibrio"]
        if t is None:
            assert not any(aprueba(c, i / 1000) for i in range(50, 351))
        else:
            assert aprueba(c, t) and not any(aprueba(c, i / 1000) for i in range(50, round(t * 1000)))


def test_pais_nuevo_es_neutro(meta):
    sc = meta["scorecard"]
    d = ref.puntuar(sc, _perfil({**CLIENTES[0], "pais": "Denmark"}))["detalle"]
    assert next(x for x in d if x["variable"] == "pais")["puntos"] == 0


def test_histograma_cubre_toda_la_cartera(js, df):
    assert sum(js["histograma"]) == len(df)


def test_reglas_de_la_app_reproducen_las_del_proyecto(df, meta):
    t = pd.read_csv(path("outputs") / "corte/reglas_prueba.csv").set_index("regla")
    r = ref.resultado_credito(df, meta["costo"], meta["lgd"])
    casos = {"Aprobar todo": {**BASE, "corte": .4}, "Sin ratings E a G": {**BASE, "corte": .4, "sinRatings": ["E", "F", "G"]}, "Corte por KS": {**BASE, "corte": meta["corte_ks"]},
             "Corte económico": {**BASE, "corte": meta["corte_economico"]}, "Margen esperado por crédito": {**BASE, "regla": "margen"}}
    for regla, e in casos.items():
        s = ref.resumen(df, ref.aprobar(df, e), r)
        assert s["aprobadosPct"] == pytest.approx(t.loc[regla, "aprobados_pct"], abs=.01), regla
        assert s["cambio"] / 1e6 == pytest.approx(t.loc[regla, "cambio"] / 1e6, abs=.005), regla
