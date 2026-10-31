import pytest

from modelos import sitio


@pytest.fixture(scope="module")
def d():
    return sitio.datos()


def test_num_respeta_el_idioma():
    assert sitio.num(1234.5, "es") == "1.234,5"
    assert sitio.num(1234.5, "en") == "1,234.5"


@pytest.mark.parametrize("L", ["es", "en"])
def test_pagina_y_readme_se_generan_desde_outputs(d, L):
    html = sitio.pagina(d, L)
    assert html.count('class="plotly-graph-div"') == 9
    assert "nan" not in sitio.cifras(d, L).values()
    assert "{c[" not in sitio.readme(d, L)
