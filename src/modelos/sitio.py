"""Sitio bilingüe en HTML estático, generado desde outputs/, y READMEs.

`python -m modelos.sitio` escribe site/index.html, site/en/index.html, README.md y README_ES.md.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from modelos.config import ROOT, path, settings

OUT = path("outputs")
PLOTLY_JS = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"
PLOTLY_ES = "https://cdn.jsdelivr.net/npm/plotly.js@2.35.2/dist/plotly-locale-es.js"
SERIES = {"s1": ("#2a78d6", "#3987e5"), "s2": ("#eb6834", "#d95926"), "s3": ("#1baf7a", "#199e70")}
TINTA = {"claro": {"texto": "#0b0b0b", "secundario": "#52514e", "grilla": "#e1e0d9", "eje": "#c3c2b7"},
         "oscuro": {"texto": "#f0efec", "secundario": "#c3c2b7", "grilla": "#2c2c2a", "eje": "#383835"}}
NEUTRO = "#898781"
DEC = {"es": (",", "."), "en": (".", ",")}
PAIS = {"es": {"Denmark": "Dinamarca", "Latvia": "Letonia", "Netherlands": "Países Bajos", "Finland": "Finlandia", "Estonia": "Estonia"},
        "en": {"Denmark": "Denmark", "Latvia": "Latvia", "Netherlands": "Netherlands", "Finland": "Finland", "Estonia": "Estonia"}}
REGLA_EN = {"Aprobar todo": "Approve everything", "Sin ratings E a G": "No ratings E to G", "Corte por KS": "KS cutoff",
            "Corte económico": "Economic cutoff", "Margen esperado por crédito": "Expected margin per loan"}
MODELO_EN = {"Rating de Bondora": "Bondora's rating", "Sólo rating y país": "Rating and country only", "Scorecard sin rating": "Scorecard, no rating",
             "Scorecard con rating": "Scorecard with rating", "LightGBM sin rating": "LightGBM, no rating", "LightGBM con rating": "LightGBM with rating"}
GRADO = {"es": {"ok": "OK", "vigilar": "Vigilar", "actuar": "Actuar"}, "en": {"ok": "OK", "vigilar": "Watch", "actuar": "Act"}}


def num(x: float, L: str, d: int = 1) -> str:
    s = f"{x:,.{d}f}"
    if L == "es":
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def signo(x: float, L: str, d: int = 1) -> str:
    return ("+" if x >= 0 else "") + num(x, L, d)


def _tx(L: str, es: str, en: str) -> str:
    return es if L == "es" else en


def datos() -> dict:
    def j(r):
        with open(OUT / r, encoding="utf-8") as fh:
            return json.load(fh)
    return {
        "comp": pd.read_csv(OUT / "modelos/comparacion.csv"), "iv": pd.read_csv(OUT / "modelos/iv.csv"), "puntos": pd.read_csv(OUT / "modelos/tabla_puntos.csv"),
        "part": j("modelos/particiones.json"), "reglas": pd.read_csv(OUT / "corte/reglas_prueba.csv"), "curva": pd.read_csv(OUT / "corte/curva_prueba.csv"),
        "margen": pd.read_csv(OUT / "corte/margen_por_costo.csv"), "corte": j("corte/resumen_corte.json"), "psi": pd.read_csv(OUT / "validacion/psi.csv"),
        "tri": pd.read_csv(OUT / "validacion/por_trimestre.csv"), "cal": pd.read_csv(OUT / "validacion/calibracion_prueba.csv"),
        "cal_pais": pd.read_csv(OUT / "validacion/calibracion_pais.csv"), "shap": pd.read_csv(OUT / "validacion/shap_lightgbm.csv"),
        "inc": pd.read_csv(OUT / "supervivencia/incidencia_acumulada.csv"), "km": pd.read_csv(OUT / "supervivencia/todos_con_km.csv"),
        "sup": j("supervivencia/resumen_supervivencia.json"), "serie": pd.read_csv(OUT / "monitoreo/serie_trimestral.csv"), "alertas": j("monitoreo/alertas.json"),
        "pais_m": pd.read_csv(OUT / "monitoreo/brecha_por_pais.csv"),
    }


def cifras(d: dict, L: str) -> dict:
    pp = lambda x, k=1: num(x, L, k)  # noqa: E731
    c = d["comp"]
    pr = c[c["conjunto"] == "prueba"].set_index("modelo")
    psn = c[c["conjunto"] == "prueba sin paises nuevos"].set_index("modelo")
    va = c[c["conjunto"] == "validacion"].set_index("modelo")
    r = d["reglas"].set_index("regla")
    mg = d["margen"].set_index(["costo_pp", "pais"])
    cp = d["cal_pais"].set_index("pais")
    s = d["serie"]
    sup = d["sup"]
    tri = d["tri"].set_index(["modelo", "trimestre"])["gini"]
    psi = d["psi"].set_index("variable")["psi"]
    cambio = lambda k: signo(r.loc[k, "cambio"] / 1e6, L, 2)  # noqa: E731
    pais_b = d["alertas"]["senales"]["calibracion_por_pais"]
    return {
        "g_ra": pp(pr.loc["Rating de Bondora", "gini"], 2), "g_sc": pp(pr.loc["Scorecard con rating", "gini"], 2), "g_gb": pp(pr.loc["LightGBM con rating", "gini"], 2),
        "g_sc_i": pp(pr.loc["Scorecard con rating", "gini_inf"], 3), "g_sc_s": pp(pr.loc["Scorecard con rating", "gini_sup"], 3),
        "g_gb_i": pp(pr.loc["LightGBM con rating", "gini_inf"], 3), "g_gb_s": pp(pr.loc["LightGBM con rating", "gini_sup"], 3),
        "g_sc3": pp(pr.loc["Scorecard con rating", "gini"], 3), "g_gb3": pp(pr.loc["LightGBM con rating", "gini"], 3),
        "g_sin_sc": pp(pr.loc["Scorecard sin rating", "gini"], 2), "g_sin_gb": pp(pr.loc["LightGBM sin rating", "gini"], 2), "g_rp": pp(pr.loc["Sólo rating y país", "gini"], 2),
        "g_sc_sd": pp(psn.loc["Scorecard con rating", "gini"], 3), "g_gb_sd": pp(psn.loc["LightGBM con rating", "gini"], 3),
        "g_va": pp(va.loc["Scorecard con rating", "gini"], 3), "g_va_gb": pp(va.loc["LightGBM con rating", "gini"], 3),
        "n_tr": pp(d["part"]["entrenamiento"]["n"], 0), "n_va": pp(d["part"]["validacion"]["n"], 0), "n_pr": pp(d["part"]["prueba"]["n"], 0),
        "n_tot": pp(sup["creditos"], 0), "malos": pp(d["part"]["prueba"]["malos_pct"]),
        "c_opt": pp(100 * d["curva"].loc[d["curva"]["resultado"].idxmax(), "corte_pd"], 0),
        "r_opt": signo((d["curva"]["resultado"].max() - r.loc["Aprobar todo", "resultado"]) / 1e6, L, 2),
        "c_ks": pp(100 * d["corte"]["corte_ks"]), "c_eco": pp(100 * d["corte"]["corte_economico"], 0), "eq": pp(100 * d["corte"]["equilibrio_teorico_pd"], 0),
        "costo": str(d["corte"]["costo_pp"]), "lgd": pp(100 * d["corte"]["lgd"], 0),
        "ks_ap": pp(r.loc["Corte por KS", "aprobados_pct"], 0), "ks_c": cambio("Corte por KS"), "ks_i": signo(r.loc["Corte por KS", "cambio_inf"] / 1e6, L, 2), "ks_s": signo(r.loc["Corte por KS", "cambio_sup"] / 1e6, L, 2),
        "eco_ap": pp(r.loc["Corte económico", "aprobados_pct"], 0), "eco_c": cambio("Corte económico"), "eg_ap": pp(r.loc["Sin ratings E a G", "aprobados_pct"], 0), "eg_c": cambio("Sin ratings E a G"),
        "mg_c": cambio("Margen esperado por crédito"), "mg_ap": pp(r.loc["Margen esperado por crédito", "aprobados_pct"], 0),
        "mg_nl": signo(mg.loc[(10, "Netherlands"), "cambio"] / 1e6, L, 2), "mg_nl_pct": pp(100 * mg.loc[(10, "Netherlands"), "cambio"] / mg.loc[(10, "Total"), "cambio"], 0),
        "mg_5": signo(mg.loc[(5, "Total"), "cambio"] / 1e6, L, 2), "mg_0": signo(mg.loc[(0, "Total"), "cambio"] / 1e6, L, 2), "mg_15": signo(mg.loc[(15, "Total"), "cambio"] / 1e6, L, 1),
        "dk_p": pp(cp.loc["Denmark", "pd_media_pct"], 0), "dk_o": pp(cp.loc["Denmark", "observado_pct"], 0), "dk_n": pp(cp.loc["Denmark", "n"], 0),
        "lv_p": pp(cp.loc["Latvia", "pd_media_pct"], 0), "lv_o": pp(cp.loc["Latvia", "observado_pct"], 0),
        "br_ini": pp(s["brecha_pp"].iloc[0]), "br_fin": pp(s["brecha_pp"].iloc[-1]), "t_ini": s["trimestre"].iloc[0], "t_fin": s["trimestre"].iloc[-1],
        "g_gb_max": pp(tri["LightGBM"].max(), 2), "g_gb_fin": pp(tri["LightGBM"].iloc[-1], 2), "g_sc_fin": pp(tri["Scorecard"].iloc[-1], 2),
        "pd_fin": pp(s["pd_media_pct"].iloc[-1]), "ob_fin": pp(s["observado_pct"].iloc[-1]),
        "psi_t": pp(psi["tasa"], 2), "psi_p": pp(psi["puntaje del modelo"], 2), "psi_i": pp(psi["ingreso"], 3),
        "d12": pp(sup["default_12_pct"]), "d36": pp(sup["default_ultimo_pct"]), "km36": pp(sup["km_ultimo_pct"]), "p36": pp(sup["pago_ultimo_pct"], 0), "v36": pp(sup["vivo_ultimo_pct"], 0),
        "p12": pp(sup["pago_12_pct"], 0), "mult": pp(sup["default_ultimo_pct"] / sup["default_12_pct"], 0),
        "grado": GRADO[L][d["alertas"]["grado"]], "pais_b": PAIS[L].get(pais_b["pais"], pais_b["pais"]), "pais_v": pp(pais_b["valor"], 0),
        "umbrales": "https://alvarez1lucas.github.io/umbrales-credito/" + ("" if L == "es" else "en/"),
    }


# --------------------------------------------------------------------------- gráficos

def _layout(fig: go.Figure, L: str, y: str, alto: int = 330, x: str = "") -> go.Figure:
    t = TINTA["claro"]
    fig.update_layout(height=alto, margin=dict(l=56, r=16, t=16, b=64), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13, color=t["texto"]), hovermode="x unified",
                      legend=dict(orientation="h", y=-0.24, x=0, font=dict(color=t["secundario"])), separators="".join(DEC[L]), bargap=0.35)
    fig.update_xaxes(showgrid=False, linecolor=t["eje"], tickcolor=t["eje"], tickfont=dict(color=t["secundario"]), title=dict(text=x, font=dict(color=t["secundario"], size=12)))
    fig.update_yaxes(gridcolor=t["grilla"], zeroline=False, linecolor=t["eje"], tickfont=dict(color=t["secundario"]), title=dict(text=y, font=dict(color=t["secundario"], size=12)))
    return fig


def _linea(x, y, nombre: str, rol: str, fmt: str = ".1f", **kw) -> go.Scatter:
    kw.setdefault("mode", "lines+markers")
    return go.Scatter(x=x, y=y, name=nombre, line=dict(color=SERIES[rol][0], width=2), marker=dict(color=SERIES[rol][0], size=7), meta={"rol": rol}, hovertemplate=f"%{{y:{fmt}}}", **kw)


def _barra(x, y, nombre: str, rol: str, fmt: str = ".1f", **kw) -> go.Bar:
    return go.Bar(x=x, y=y, name=nombre, marker=dict(color=SERIES[rol][0], cornerradius=4), meta={"rol": rol}, hovertemplate=f"%{{y:{fmt}}}", **kw)


def fig_gini(d: dict, L: str) -> go.Figure:
    c = d["comp"][d["comp"]["conjunto"] == "prueba"].sort_values("gini")
    n = [k if L == "es" else MODELO_EN[k] for k in c["modelo"]]
    fig = go.Figure(go.Bar(y=n, x=c["gini"], orientation="h", marker=dict(color=SERIES["s1"][0], cornerradius=4), meta={"rol": "s1"},
                           error_x=dict(type="data", symmetric=False, array=c["gini_sup"] - c["gini"], arrayminus=c["gini"] - c["gini_inf"], color=NEUTRO, thickness=1.5, width=4),
                           hovertemplate="%{x:.3f}<extra></extra>"))
    _layout(fig, L, "", alto=310, x=_tx(L, "Gini en cosechas de prueba", "Gini on test vintages"))
    fig.update_layout(hovermode="closest", margin=dict(l=8, b=56), showlegend=False)
    fig.update_xaxes(showgrid=True, gridcolor=TINTA["claro"]["grilla"], range=[0, 0.5])
    fig.update_yaxes(automargin=True, gridcolor="rgba(0,0,0,0)")
    return fig


def fig_gini_tiempo(d: dict, L: str) -> go.Figure:
    t = d["tri"]
    fig = go.Figure([_linea(g["trimestre"], g["gini"], m, r, ".3f") for m, r in (("Scorecard", "s1"), ("LightGBM", "s2")) for g in [t[t["modelo"] == m]]])
    return _layout(fig, L, "Gini", alto=300)


def fig_curva(d: dict, L: str) -> go.Figure:
    c = d["curva"]
    c = c[c["corte_pd"] <= 0.35]
    fig = go.Figure([_linea(100 * c["corte_pd"], c["resultado"] / 1e6, _tx(L, "Resultado", "Result"), "s1", ".2f", mode="lines")])
    ks, eco = 100 * d["corte"]["corte_ks"], 100 * d["corte"]["corte_economico"]
    fig.add_vline(x=ks, line=dict(color=NEUTRO, width=1, dash="dot"), annotation_text=_tx(L, "Corte por KS", "KS cutoff"), annotation_position="top right", annotation_font=dict(color=NEUTRO, size=12))
    fig.add_vline(x=eco, line=dict(color=NEUTRO, width=1, dash="dot"), annotation_text=_tx(L, "Corte económico", "Economic cutoff"), annotation_position="bottom right", annotation_font=dict(color=NEUTRO, size=12))
    fig.update_layout(showlegend=False)
    return _layout(fig, L, _tx(L, "Resultado del primer año (M€)", "First-year result (€M)"), alto=310, x=_tx(L, "Corte: PD máxima aprobada (%)", "Cutoff: highest PD approved (%)"))


def fig_margen(d: dict, L: str) -> go.Figure:
    m = d["margen"]
    t = m[m["pais"] == "Total"].sort_values("costo_pp")
    nl = m[m["pais"] == "Netherlands"].set_index("costo_pp").reindex(t["costo_pp"])["cambio"].clip(lower=0).to_numpy()
    x = [f"{int(c)} pp" for c in t["costo_pp"]]
    fig = go.Figure([_barra(x, nl / 1e6, _tx(L, "Por rechazar Países Bajos", "From rejecting the Netherlands"), "s2", ".2f"),
                     _barra(x, (t["cambio"].to_numpy() - nl) / 1e6, _tx(L, "Resto", "Rest"), "s1", ".2f")])
    fig.update_layout(barmode="stack")
    return _layout(fig, L, _tx(L, "Mejora del resultado (M€)", "Improvement in result (€M)"), alto=310, x=_tx(L, "Costo supuesto de fondeo y operación", "Assumed funding and operating cost"))


def fig_pais(d: dict, L: str) -> go.Figure:
    c = d["cal_pais"].sort_values("observado_pct", ascending=False)
    x = [PAIS[L][p] for p in c["pais"]]
    fig = go.Figure([_barra(x, c["pd_media_pct"], _tx(L, "Predicho", "Predicted"), "s1"), _barra(x, c["observado_pct"], _tx(L, "Observado", "Observed"), "s2")])
    fig.update_layout(barmode="group", bargroupgap=0.08)
    return _layout(fig, L, _tx(L, "Mora 90+ a 12 meses (%)", "90+ delinquency at 12 months (%)"), alto=310)


def fig_brecha(d: dict, L: str) -> go.Figure:
    s = d["serie"]
    fig = go.Figure([_linea(s["trimestre"], s["pd_media_pct"], _tx(L, "Predicho", "Predicted"), "s1"), _linea(s["trimestre"], s["observado_pct"], _tx(L, "Observado", "Observed"), "s2")])
    _layout(fig, L, _tx(L, "Mora 90+ a 12 meses (%)", "90+ delinquency at 12 months (%)"), alto=300, x=_tx(L, "Trimestre de originación", "Origination quarter"))
    fig.update_yaxes(rangemode="tozero")
    return fig


def fig_calibracion(d: dict, L: str) -> go.Figure:
    c = d["cal"]
    fig = go.Figure([_linea(c["decil"], 100 * c["pd_media"], _tx(L, "Predicho", "Predicted"), "s1"), _linea(c["decil"], 100 * c["observado"], _tx(L, "Observado", "Observed"), "s2")])
    return _layout(fig, L, _tx(L, "Mora 90+ a 12 meses (%)", "90+ delinquency at 12 months (%)"), alto=300, x=_tx(L, "Decil de riesgo (10 = más riesgoso)", "Risk decile (10 = riskiest)"))


def fig_incidencia(d: dict, L: str) -> go.Figure:
    i = d["inc"]
    fig = go.Figure()
    for r, rol in (("AA", "s3"), ("C", "s1"), ("G", "s2")):
        g = i[i["rating"] == r]
        fig.add_trace(_linea(g["mes"], 100 * g["default"], f"Rating {r}", rol, mode="lines"))
    return _layout(fig, L, _tx(L, "Default acumulado (%)", "Cumulative default (%)"), alto=300, x=_tx(L, "Meses desde el otorgamiento", "Months since origination"))


def fig_km(d: dict, L: str) -> go.Figure:
    k = d["km"]
    fig = go.Figure([_linea(k["mes"], 100 * k["default_km"], _tx(L, "Tratando la cancelación como censura", "Treating prepayment as censoring"), "s2", mode="lines"),
                     _linea(k["mes"], 100 * k["default"], _tx(L, "Riesgos competidores", "Competing risks"), "s1", mode="lines"),
                     _linea(k["mes"], 100 * k["pago"], _tx(L, "Cancelados", "Prepaid"), "s3", mode="lines")])
    return _layout(fig, L, _tx(L, "Incidencia acumulada (%)", "Cumulative incidence (%)"), alto=320, x=_tx(L, "Meses desde el otorgamiento", "Months since origination"))


def _div(fig: go.Figure, id_: str, L: str) -> str:
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=id_, config={"displayModeBar": False, "responsive": True, "locale": L})


def _tile(v: str, e: str, n: str = "") -> str:
    x = f'<div class="tile-nota">{n}</div>' if n else ""
    return f'<div class="tile"><div class="tile-valor">{v}</div><div class="tile-etq">{e}</div>{x}</div>'


def _tabla(h: list[str], f: list[list[str]]) -> str:
    th = "".join(f"<th>{x}</th>" for x in h)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in f)
    return f'<div class="tabla"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def tabla_reglas(d: dict, L: str) -> str:
    pp = lambda x, k=1: num(x, L, k)  # noqa: E731
    filas = [[f.regla if L == "es" else REGLA_EN[f.regla], f"{pp(f.aprobados_pct)}%", f"{pp(f.mora_pct)}%",
              "-" if f.regla == "Aprobar todo" else signo(f.cambio / 1e6, L, 2),
              "-" if f.regla == "Aprobar todo" else f"{signo(f.cambio_inf / 1e6, L, 2)} / {signo(f.cambio_sup / 1e6, L, 2)}"] for f in d["reglas"].itertuples()]
    return _tabla([_tx(L, "Regla", "Rule"), _tx(L, "Créditos que quedan", "Loans kept"), _tx(L, "Mora a 12 meses", "12-month delinquency"), _tx(L, "Cambio (M€)", "Change (€M)"), "IC 95%" if L == "es" else "95% CI"], filas)


def tabla_senales(d: dict, L: str) -> str:
    pp = lambda x, k=2: num(x, L, k)  # noqa: E731
    s = d["alertas"]["senales"]
    filas = [
        [_tx(L, "Discriminación", "Discrimination"), _tx(L, "Caída de Gini contra el primer trimestre", "Gini drop from the first quarter"), pp(max(s["discriminacion"]["valor"], 0)), GRADO[L][s["discriminacion"]["grado"]]],
        [_tx(L, "Calibración", "Calibration"), _tx(L, "Observado menos predicho, última cosecha (pp)", "Observed minus predicted, latest vintage (pp)"), pp(s["calibracion"]["valor"], 1), GRADO[L][s["calibracion"]["grado"]]],
        [_tx(L, "Calibración por país", "Calibration by country"), _tx(L, f"Peor brecha reciente: {PAIS[L].get(s['calibracion_por_pais']['pais'])} (pp)", f"Worst recent gap: {PAIS[L].get(s['calibracion_por_pais']['pais'])} (pp)"), pp(s["calibracion_por_pais"]["valor"], 1), GRADO[L][s["calibracion_por_pais"]["grado"]]],
        [_tx(L, "Población", "Population"), _tx(L, "PSI de créditos nuevos contra entrenamiento", "PSI of new loans vs training"), pp(s["poblacion"]["valor"]), GRADO[L][s["poblacion"]["grado"]]],
        [_tx(L, "Fuera de dominio", "Out of domain"), _tx(L, "Países que el modelo nunca vio", "Countries the model never saw"), ", ".join(PAIS[L].get(p, p) for p in s["fuera_de_dominio"]["valor"]) or "-", GRADO[L][s["fuera_de_dominio"]["grado"]]],
    ]
    return _tabla([_tx(L, "Señal", "Signal"), _tx(L, "Qué mide", "What it measures"), _tx(L, "Valor", "Value"), _tx(L, "Grado", "Grade")], filas)


def contenido(d: dict, L: str) -> tuple[str, str, str]:
    c = cifras(d, L)
    if L == "es":
        hero = "".join([
            _tile(f"{c['g_ra']} → {c['g_sc']}", "Gini: del rating de la empresa a la scorecard", "Cosechas que el modelo nunca vio"),
            _tile(f"{c['g_sc']} vs {c['g_gb']}", "La scorecard le gana a LightGBM", "Con búsqueda de hiperparámetros"),
            _tile(f"{c['dk_p']}% vs {c['dk_o']}%", "Predicho y real en un país nuevo", "Ningún Gini global lo avisa"),
            _tile(f"{c['d12']}% → {c['d36']}%", "Default a 12 y a 36 meses", "Un modelo a 12 meses ve un tercio"),
        ])
        sint = f"""<section class="sintesis"><h2>En síntesis</h2>
<p>Un modelo de riesgo no se juzga por su Gini, sino por las decisiones que mejora. Acá se entrena con cosechas viejas y se mide con cosechas posteriores, siempre contra el rating que la empresa ya tiene.</p>
<ol>
<li><strong>¿Le gana al que ya existe?</strong> Sólo si lo usa. Sin el rating, ningún modelo lo alcanza ({c['g_sin_gb']} contra {c['g_ra']}). Con él, la scorecard llega a {c['g_sc']}.</li>
<li><strong>¿Hace falta algo complejo?</strong> No. La scorecard ({c['g_sc']}) supera a LightGBM ({c['g_gb']}) en cosechas nuevas, y se explica sumando una tabla.</li>
<li><strong>¿El corte gana plata?</strong> Depende del costo. La mejora de la regla por margen va de {c['mg_0']} a {c['mg_c']} M€ según el costo supuesto, y el {c['mg_nl_pct']}% de esta última viene de rechazar un país entero.</li>
<li><strong>¿Dónde falla?</strong> En lo que nunca vio. En Dinamarca, un mercado nuevo, predice {c['dk_p']}% y la mora real es {c['dk_o']}%.</li>
<li><strong>¿Sigue valiendo?</strong> Ordena bien, pero el nivel se corrió: la brecha pasó de {c['br_ini']} a {c['br_fin']} puntos con el Gini estable. El monitoreo marca <em>{c['grado'].lower()}</em>.</li>
</ol></section>"""
        sec = f"""
<section><h2>1. ¿Le gana al que ya existe?</h2>
<p>Bondora asigna un rating propio a cada crédito. Ese es el modelo a vencer. Se usan {c['n_tot']} créditos desde oct-23, cuando el rating cubre toda la cartera: {c['n_tr']} para entrenar, {c['n_va']} para ajustar y {c['n_pr']} de 2025 como prueba, que no se tocan para elegir nada.</p>
{_div(fig_gini(d, L), 'g-gini', L)}
<p>Sin el rating, los modelos quedan por debajo: {c['g_sin_sc']} y {c['g_sin_gb']} contra {c['g_ra']}. <strong>Lo primero que aporta valor es combinar:</strong> rating y país solos ya dan {c['g_rp']}, y agregar plazo, ingreso y carga lleva la scorecard a {c['g_sc']}.</p>
<p>La scorecard ({c['g_sc_i']}-{c['g_sc_s']}) le gana a LightGBM ({c['g_gb_i']}-{c['g_gb_s']}), con intervalos que no se tocan. En validación empataron ({c['g_va']} y {c['g_va_gb']}), así que no se eligió mirando la prueba, y el resultado se sostiene sin los países nuevos ({c['g_sc_sd']} contra {c['g_gb_sd']}). El motivo se ve en el tiempo: LightGBM llega a {c['g_gb_max']} en las cosechas con las que se entrenó y baja a {c['g_gb_fin']} en las nuevas, un sobreajuste que la scorecard no tiene. <strong>El Gini en entrenamiento no dice nada.</strong></p>
{_div(fig_gini_tiempo(d, L), 'g-tiempo', L)}
</section>

<section><h2>2. ¿El corte gana plata?</h2>
<p>Un buen ranking no decide nada hasta que se elige un corte, y ese corte es otro umbral. Todas las reglas se fijaron en validación y se midieron en prueba, con un costo supuesto de {c['costo']} puntos y una LGD de {c['lgd']}%. El corte estadístico (KS) aprueba hasta {c['c_ks']}% de PD y saca al {num(100 - float(d['reglas'].set_index('regla').loc['Corte por KS', 'aprobados_pct']), L, 0)}% de los créditos. El corte económico queda en {c['c_eco']}%: casi no toca la cartera, porque Bondora ya hizo el filtro.</p>
{_div(fig_curva(d, L), 'g-curva', L)}
<p>En prueba, el mejor corte habría sido cerca de {c['c_opt']}% ({c['r_opt']} M€), muy cerca del equilibrio teórico de {c['eq']}% entre tasa, costo y LGD. Elegirlo mirando la prueba sería hacer trampa: lo que se puede saber de antemano es el {c['c_eco']}% que dio validación. <strong>Un corte económico estimado con un solo trimestre es inestable</strong>, y conviene partir del equilibrio teórico.</p>
{tabla_reglas(d, L)}
<p>El corte por KS mejora {c['ks_c']} M€ con un intervalo muy ancho ({c['ks_i']} a {c['ks_s']}) y a costa de un tercio del volumen. La regla simple de sacar E a G logra {c['eg_c']} M€ sin modelo. La PD sola no alcanza: <strong>el corte útil compara el riesgo de cada crédito con su propia tasa</strong>, y esa regla da {c['mg_c']} M€.</p>
<p>Pero hay que desarmar ese número. El {c['mg_nl_pct']}% viene de rechazar todos los créditos de Países Bajos, donde la tasa (~10%) iguala al costo supuesto: es el supuesto, no el modelo. Con 5 puntos de costo, la mejora cae a {c['mg_5']} M€. <strong>Antes de presentar una mejora hay que saber de dónde sale.</strong></p>
{_div(fig_margen(d, L), 'g-margen', L)}
</section>

<section><h2>3. ¿Dónde falla?</h2>
<p>Un buen promedio esconde segmentos mal predichos. Dinamarca entró en 2025: tiene {c['dk_n']} créditos en prueba y ninguno en entrenamiento. El modelo la trata como neutra y predice {c['dk_p']}%, con mora real de {c['dk_o']}%. Letonia, con pocos datos, predice {c['lv_p']}% contra {c['lv_o']}%.</p>
{_div(fig_pais(d, L), 'g-pais', L)}
<p><strong>Un modelo sólo vale dentro de la población que conoce.</strong> Un mercado nuevo no se puntúa con el modelo viejo: se limita con cupos hasta tener datos propios.</p>
</section>

<section><h2>4. ¿Sigue valiendo?</h2>
<p>El modelo sigue ordenando bien, pero el nivel se corrió: para {c['t_fin']} predice {c['pd_fin']}% y la mora real es {c['ob_fin']}%. Discriminación y calibración son cosas distintas, y mirar sólo el Gini no lo habría mostrado. Las decisiones de corte y de previsiones dependen del nivel.</p>
{_div(fig_brecha(d, L), 'g-brecha', L)}
<p>La población también cambió: el PSI del puntaje contra entrenamiento es {c['psi_p']}, y el de la tasa {c['psi_t']}, por cambios reales de precios. El ingreso casi no se movió ({c['psi_i']}).</p>
{_div(fig_calibracion(d, L), 'g-calibracion', L)}
<p>El modelo está congelado. Un workflow lo evalúa con cada foto nueva de la cartera, sin reentrenar, y gradúa cada señal:</p>
{tabla_senales(d, L)}
<p class="nota">La mora a 12 meses se conoce un año después, así que el monitoreo siempre llega con retraso. La calibración de las cosechas recientes todavía no se puede medir: por eso también se vigila la población.</p>
</section>

<section><h2>5. ¿Qué no ve un modelo a 12 meses?</h2>
<p>Estos créditos duran hasta 7 años. A 12 meses el default es {c['d12']}%; a 36, {c['d36']}%. El modelo a 12 meses ve un tercio de la historia.</p>
{_div(fig_incidencia(d, L), 'g-incidencia', L)}
<p>La cancelación anticipada también importa: a 36 meses canceló el {c['p36']}% y queda vivo el {c['v36']}%. Quien canceló ya no puede caer, y por eso tratarla como censura, el error habitual, infla el default a {c['km36']}%. Se usa el estimador de riesgos competidores (Aalen-Johansen). Además, la cancelación se lleva los intereses de los mejores clientes: es otro costo que un modelo de PD no ve.</p>
{_div(fig_km(d, L), 'g-km', L)}
</section>

<section><h2>Cómo sigue</h2>
<p>El proyecto <a href="{c['umbrales']}">Umbrales de crédito</a> muestra cómo evaluar cualquier umbral de la política; acá el umbral es el corte de un modelo. Ficha completa del modelo y método: <a href="{settings()['sitio']['repo_url']}/blob/main/docs/ficha_modelo.md">ficha del modelo</a>.</p>
</section>"""
        tit = "Lo que estos datos no permiten afirmar"
        lim = ["A los rechazados por Bondora no se los observa: sólo se evalúa endurecer, y el modelo se entrena sobre aprobados.",
               f"El costo de {c['costo']} puntos es un supuesto, igual para todos los países. La LGD viene de cosechas viejas.",
               "El resultado económico mira sólo el primer año y usa el monto como exposición.",
               "Hay una sola ventana de prueba, de 2025. No alcanza para hablar de un ciclo completo.",
               "La recalibración con el trimestre anterior muestra que el error es de nivel, no es un pronóstico: ese resultado se conoce un año después."]
    else:
        hero = "".join([
            _tile(f"{c['g_ra']} → {c['g_sc']}", "Gini: from the lender's rating to the scorecard", "Vintages the model never saw"),
            _tile(f"{c['g_sc']} vs {c['g_gb']}", "The scorecard beats LightGBM", "With a hyperparameter search"),
            _tile(f"{c['dk_p']}% vs {c['dk_o']}%", "Predicted and actual in a new country", "No global Gini warns about it"),
            _tile(f"{c['d12']}% → {c['d36']}%", "Default at 12 and 36 months", "A 12-month model sees a third"),
        ])
        sint = f"""<section class="sintesis"><h2>In short</h2>
<p>A risk model is not judged by its Gini but by the decisions it improves. Here it is trained on old vintages and measured on later ones, always against the rating the lender already has.</p>
<ol>
<li><strong>Does it beat what exists?</strong> Only by using it. Without the rating no model reaches it ({c['g_sin_gb']} against {c['g_ra']}). With it, the scorecard gets to {c['g_sc']}.</li>
<li><strong>Is something complex needed?</strong> No. The scorecard ({c['g_sc']}) beats LightGBM ({c['g_gb']}) on new vintages, and it can be explained by adding up a table.</li>
<li><strong>Does the cutoff make money?</strong> It depends on cost. The margin rule's gain goes from {c['mg_0']} to {c['mg_c']} €M with the assumed cost, and {c['mg_nl_pct']}% of the latter comes from rejecting a whole country.</li>
<li><strong>Where does it fail?</strong> On what it never saw. In Denmark, a new market, it predicts {c['dk_p']}% and actual delinquency is {c['dk_o']}%.</li>
<li><strong>Does it still hold?</strong> It ranks well, but the level shifted: the gap went from {c['br_ini']} to {c['br_fin']} points with a stable Gini. Monitoring reads <em>{c['grado'].lower()}</em>.</li>
</ol></section>"""
        sec = f"""
<section><h2>1. Does it beat what exists?</h2>
<p>Bondora assigns its own rating to each loan. That is the model to beat. The data are {c['n_tot']} loans since Oct-23, when the rating covers the whole portfolio: {c['n_tr']} for training, {c['n_va']} for tuning and {c['n_pr']} from 2025 as a test set that is not touched to choose anything.</p>
{_div(fig_gini(d, L), 'g-gini', L)}
<p>Without the rating, models fall short: {c['g_sin_sc']} and {c['g_sin_gb']} against {c['g_ra']}. <strong>The first thing that adds value is combining:</strong> rating and country alone give {c['g_rp']}, and adding term, income and payment burden takes the scorecard to {c['g_sc']}.</p>
<p>The scorecard ({c['g_sc_i']}-{c['g_sc_s']}) beats LightGBM ({c['g_gb_i']}-{c['g_gb_s']}), with intervals that do not touch. They tied in validation ({c['g_va']} and {c['g_va_gb']}), so it was not chosen by looking at the test set, and the result holds without new countries ({c['g_sc_sd']} against {c['g_gb_sd']}). The reason shows over time: LightGBM reaches {c['g_gb_max']} on the vintages it was trained on and falls to {c['g_gb_fin']} on new ones, an overfit the scorecard does not have. <strong>Training Gini says nothing.</strong></p>
{_div(fig_gini_tiempo(d, L), 'g-tiempo', L)}
</section>

<section><h2>2. Does the cutoff make money?</h2>
<p>A good ranking decides nothing until a cutoff is chosen, and that cutoff is one more threshold. All rules were set on validation and measured on test, with an assumed cost of {c['costo']} points and an LGD of {c['lgd']}%. The statistical cutoff (KS) approves up to {c['c_ks']}% PD and removes {num(100 - float(d['reglas'].set_index('regla').loc['Corte por KS', 'aprobados_pct']), L, 0)}% of loans. The economic cutoff sits at {c['c_eco']}%: it barely touches the portfolio, because Bondora already filtered it.</p>
{_div(fig_curva(d, L), 'g-curva', L)}
<p>On test, the best cutoff would have been near {c['c_opt']}% ({c['r_opt']} €M), very close to the theoretical break-even of {c['eq']}% between rate, cost and LGD. Picking it by looking at the test set would be cheating: what could be known in advance is the {c['c_eco']}% from validation. <strong>An economic cutoff estimated on a single quarter is unstable</strong>, and it is better to start from the theoretical break-even.</p>
{tabla_reglas(d, L)}
<p>The KS cutoff improves by {c['ks_c']} €M with a very wide interval ({c['ks_i']} to {c['ks_s']}) at the cost of a third of volume. The simple rule of removing E to G gets {c['eg_c']} €M with no model. PD alone is not enough: <strong>the useful cutoff compares each loan's risk with its own rate</strong>, and that rule gives {c['mg_c']} €M.</p>
<p>But that number has to be taken apart. {c['mg_nl_pct']}% comes from rejecting every loan in the Netherlands, where the rate (~10%) equals the assumed cost: that is the assumption, not the model. With a cost of 5 points the gain falls to {c['mg_5']} €M. <strong>Before presenting a gain you have to know where it comes from.</strong></p>
{_div(fig_margen(d, L), 'g-margen', L)}
</section>

<section><h2>3. Where does it fail?</h2>
<p>A good average hides badly predicted segments. Denmark entered in 2025: it has {c['dk_n']} loans in test and none in training. The model treats it as neutral and predicts {c['dk_p']}%, with actual delinquency of {c['dk_o']}%. Latvia, with little data, gets {c['lv_p']}% against {c['lv_o']}%.</p>
{_div(fig_pais(d, L), 'g-pais', L)}
<p><strong>A model is only worth something within the population it knows.</strong> A new market is not scored with the old model: it is limited with caps until it has its own data.</p>
</section>

<section><h2>4. Does it still hold?</h2>
<p>The model still ranks well, but the level shifted: for {c['t_fin']} it predicts {c['pd_fin']}% and actual delinquency is {c['ob_fin']}%. Discrimination and calibration are different things, and the Gini alone would not have shown this. Cutoff and provisioning decisions depend on the level.</p>
{_div(fig_brecha(d, L), 'g-brecha', L)}
<p>The population changed too: the score's PSI against training is {c['psi_p']}, and the rate's {c['psi_t']}, from real pricing changes. Income barely moved ({c['psi_i']}).</p>
{_div(fig_calibracion(d, L), 'g-calibracion', L)}
<p>The model is frozen. A workflow evaluates it with each new portfolio snapshot, without retraining, and grades each signal:</p>
{tabla_senales(d, L)}
<p class="nota">12-month delinquency is only known a year later, so monitoring always lags. Calibration of recent vintages cannot be measured yet: that is why the population is watched too.</p>
</section>

<section><h2>5. What does a 12-month model not see?</h2>
<p>These loans last up to 7 years. At 12 months default is {c['d12']}%; at 36, {c['d36']}%. The 12-month model sees a third of the story.</p>
{_div(fig_incidencia(d, L), 'g-incidencia', L)}
<p>Prepayment matters too: by month 36, {c['p36']}% had prepaid and {c['v36']}% are still alive. A loan that prepaid can no longer default, so treating it as censoring, the usual mistake, inflates default to {c['km36']}%. The competing-risks estimator (Aalen-Johansen) is used instead. Prepayment also takes away the interest from the best customers: one more cost a PD model does not see.</p>
{_div(fig_km(d, L), 'g-km', L)}
</section>

<section><h2>What comes next</h2>
<p>The <a href="{c['umbrales']}">Credit thresholds</a> project shows how to evaluate any policy threshold; here the threshold is a model's cutoff. Full model documentation: <a href="{settings()['sitio']['repo_url']}/blob/main/docs/ficha_modelo.md">model card</a>.</p>
</section>"""
        tit = "What these data cannot tell us"
        lim = ["Applicants rejected by Bondora are not observed: only tightening can be evaluated, and the model is trained on approved loans.",
               f"The {c['costo']}-point cost is an assumption, the same for every country. LGD comes from old vintages.",
               "The economic result covers only the first year and uses the amount as exposure.",
               "There is a single test window, from 2025. It is not enough to speak of a full cycle.",
               "Recalibrating with the previous quarter shows the error is one of level, and is not a forecast: that outcome is only known a year later."]
    fin = f"<section><h2>{tit}</h2><ul>{''.join(f'<li>{x}</li>' for x in lim)}</ul></section>"
    return hero, sint, sec + fin


CSS = """
:root{color-scheme:light;--bg:#f9f9f7;--surface:#fcfcfb;--text:#0b0b0b;--text2:#52514e;--muted:#898781;--line:#e1e0d9;--accent:#2a78d6;--lado1:rgba(42,120,214,.075);--lado2:rgba(235,104,52,.055)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--accent:#3987e5;--lado1:rgba(57,135,229,.10);--lado2:rgba(217,89,38,.07)}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--accent:#3987e5;--lado1:rgba(57,135,229,.10);--lado2:rgba(217,89,38,.07)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}
@media screen and (min-width:1000px){body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
background:radial-gradient(50% 85% at 0% 25%,var(--lado1),transparent 72%),radial-gradient(50% 85% at 100% 75%,var(--lado2),transparent 72%)}}
header{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
h1{font-size:2rem;line-height:1.2;margin:8px 0}
h2{font-size:1.35rem;margin:48px 0 8px}
.sub{color:var(--text2);max-width:720px;margin:0 0 24px}
a{color:var(--accent)}
.idioma{font-size:.9rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px}
.tile-valor{font-size:1.7rem;font-weight:600;line-height:1.1}
.tile-etq{color:var(--text2);font-size:.92rem;margin-top:6px}
.tile-nota{color:var(--muted);font-size:.82rem;margin-top:6px}
section .js-plotly-plot,section .plotly-graph-div{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:12px 0}
.tabla{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--text2);font-weight:600}
.nota{color:var(--text2);font-size:.9rem}
.sintesis{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:4px 20px 8px;margin-top:28px}
.sintesis h2{margin:16px 0 4px}
.sintesis ol{padding-left:20px;margin:8px 0}
.sintesis li{margin:10px 0}
footer{color:var(--muted);font-size:.85rem;margin-top:48px;border-top:1px solid var(--line);padding-top:16px}
"""

JS_TEMA = """
const SERIES=%s, TINTA=%s;
function aplicarTema(){
  const t=document.documentElement.dataset.theme, osc=t?t==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
  const k=osc?1:0, ink=TINTA[osc?'oscuro':'claro'];
  document.querySelectorAll('.js-plotly-plot').forEach(g=>{
    const idx=[],colores=[];
    g.data.forEach((tr,i)=>{const r=tr.meta&&tr.meta.rol;if(r){idx.push(i);colores.push(SERIES[r][k])}});
    if(idx.length)Plotly.restyle(g,{'line.color':colores,'marker.color':colores},idx);
    Plotly.relayout(g,{'font.color':ink.texto,'legend.font.color':ink.secundario,
      'xaxis.tickfont.color':ink.secundario,'yaxis.tickfont.color':ink.secundario,
      'yaxis.title.font.color':ink.secundario,'xaxis.title.font.color':ink.secundario,
      'yaxis.gridcolor':ink.grilla,'xaxis.linecolor':ink.eje,'yaxis.linecolor':ink.eje});
  });
}
window.addEventListener('load',aplicarTema);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',aplicarTema);
"""


def pagina(d: dict, L: str) -> str:
    hero, sint, sec = contenido(d, L)
    repo = settings()["sitio"]["repo_url"]
    es = L == "es"
    titulo = "Modelos de crédito" if es else "Credit risk models"
    sub = ("Si un modelo le gana al rating que la empresa ya tiene, qué corte conviene, dónde falla y cuándo deja de valer, con datos reales de una cartera de consumo."
           if es else "Whether a model beats the rating the lender already has, which cutoff pays off, where it fails and when it stops holding, with real data from a consumer portfolio.")
    otro = ("English", "en/") if es else ("Español", "../")
    pie = (f"Datos: dos fotos de la cartera de Bondora. Foto más reciente: {d['alertas']['fecha_foto']}. Código y método: <a href=\"{repo}\">{repo}</a>."
           if es else f"Data: two snapshots of Bondora's portfolio. Latest snapshot: {d['alertas']['fecha_foto']}. Code and methods: <a href=\"{repo}\">{repo}</a>.")
    js = JS_TEMA % (json.dumps({k: list(v) for k, v in SERIES.items()}), json.dumps(TINTA))
    return f"""<!doctype html>
<html lang="{L}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{sub}">
<style>{CSS}</style>
<script src="{PLOTLY_JS}"></script>
{f'<script src="{PLOTLY_ES}"></script>' if es else ""}
</head>
<body>
<main>
<header><h1>{titulo}</h1><a class="idioma" href="{otro[1]}">{otro[0]}</a></header>
<p class="sub">{sub}</p>
<div class="tiles">{hero}</div>
{sint}
{sec}
<footer>{pie}</footer>
</main>
<script>{js}</script>
</body>
</html>
"""


def readme(d: dict, L: str) -> str:
    c = cifras(d, L)
    cfg = settings()["sitio"]
    url, repo = cfg["url"], cfg["repo_url"]
    wf = f"{repo}/actions/workflows"
    badges = (f"[![Tests]({wf}/tests.yml/badge.svg)]({wf}/tests.yml) [![Monitoreo]({wf}/monitoreo.yml/badge.svg)]({wf}/monitoreo.yml) "
              f"[![{'Site' if L == 'en' else 'Sitio'}]({wf}/publicar-sitio.yml/badge.svg)]({wf}/publicar-sitio.yml) ![Python 3.11](https://img.shields.io/badge/python-3.11-blue)")
    if L == "en":
        return f"""# Credit risk models

{badges}

**[Live site]({url}en/)** · **[Model card](docs/ficha_modelo.md)** · [Versión en español](README_ES.md)

A risk model is judged by the decisions it improves, not by its Gini. This project trains on old vintages of a real consumer portfolio, measures on later ones, and always compares against the rating the lender already has. No Kaggle datasets.

## At a glance

| Question | Finding |
|---|---|
| Does it beat what exists? | Only by using it: LightGBM without the rating gets {c['g_sin_gb']} against {c['g_ra']}. With it, the scorecard reaches {c['g_sc']} |
| Is something complex needed? | No: scorecard {c['g_sc3']} against LightGBM {c['g_gb3']} on new vintages, with intervals that do not touch |
| Does the cutoff make money? | Depends on cost: from {c['mg_0']} to {c['mg_c']} €M, and {c['mg_nl_pct']}% of the latter comes from rejecting a whole country |
| Where does it fail? | On what it never saw: Denmark is predicted at {c['dk_p']}% with {c['dk_o']}% actual delinquency |
| Does it still hold? | It ranks well but the level shifted: gap from {c['br_ini']} to {c['br_fin']} points with a stable Gini |
| What does a 12-month model miss? | Default goes from {c['d12']}% at 12 months to {c['d36']}% at 36; treating prepayment as censoring would say {c['km36']}% |

**Stack:** Python (scikit-learn, LightGBM, SHAP, pandas, DuckDB), scorecard with WoE/IV built by hand, Aalen-Johansen for competing risks, pytest, GitHub Actions, GitHub Pages.

## Reproduce

Requires the Bondora snapshots from [umbrales-credito](https://github.com/alvarez1lucas/umbrales-credito).

```bash
pip install -r requirements.txt && pip install -e .
python -m modelos.entrenar && python -m modelos.corte && python -m modelos.validacion
python -m modelos.supervivencia && python -m modelos.monitoreo && python -m modelos.sitio
pytest
```

Author: Lucas Alvarez · [GitHub](https://github.com/alvarez1lucas) · Related: [Credit thresholds](https://github.com/alvarez1lucas/umbrales-credito), [Household loan delinquency in Argentina](https://github.com/alvarez1lucas/mora_argentina)
"""
    return f"""# Modelos de crédito

{badges}

**[Sitio]({url})** · **[Ficha del modelo](docs/ficha_modelo.md)** · [English version](README.md)

Un modelo de riesgo se juzga por las decisiones que mejora, no por su Gini. Este proyecto entrena con cosechas viejas de una cartera de consumo real, mide con cosechas posteriores y compara siempre contra el rating que la empresa ya tiene. Sin datasets de Kaggle.

## En 30 segundos

| Pregunta | Hallazgo |
|---|---|
| ¿Le gana al que ya existe? | Sólo si lo usa: LightGBM sin rating da {c['g_sin_gb']} contra {c['g_ra']}. Con él, la scorecard llega a {c['g_sc']} |
| ¿Hace falta algo complejo? | No: scorecard {c['g_sc3']} contra LightGBM {c['g_gb3']} en cosechas nuevas, con intervalos que no se tocan |
| ¿El corte gana plata? | Depende del costo: de {c['mg_0']} a {c['mg_c']} M€, y el {c['mg_nl_pct']}% de esto último viene de rechazar un país entero |
| ¿Dónde falla? | En lo que nunca vio: Dinamarca se predice en {c['dk_p']}% con {c['dk_o']}% de mora real |
| ¿Sigue valiendo? | Ordena bien, pero el nivel se corrió: brecha de {c['br_ini']} a {c['br_fin']} puntos con el Gini estable |
| ¿Qué no ve a 12 meses? | El default pasa de {c['d12']}% a 12 meses a {c['d36']}% a 36; tratar la cancelación como censura diría {c['km36']}% |

**Stack:** Python (scikit-learn, LightGBM, SHAP, pandas, DuckDB), scorecard con WoE/IV escrita a mano, Aalen-Johansen para riesgos competidores, pytest, GitHub Actions, GitHub Pages.

## Reproducir

Necesita las fotos de Bondora de [umbrales-credito](https://github.com/alvarez1lucas/umbrales-credito).

```bash
pip install -r requirements.txt && pip install -e .
python -m modelos.entrenar && python -m modelos.corte && python -m modelos.validacion
python -m modelos.supervivencia && python -m modelos.monitoreo && python -m modelos.sitio
pytest
```

Autor: Lucas Alvarez · [GitHub](https://github.com/alvarez1lucas) · Relacionado: [Umbrales de crédito](https://github.com/alvarez1lucas/umbrales-credito), [Mora de los hogares en Argentina](https://github.com/alvarez1lucas/mora_argentina)
"""


def main() -> None:
    d = datos()
    destino = ROOT / settings()["sitio"]["destino"]
    for L, rel in (("es", "index.html"), ("en", "en/index.html")):
        f = destino / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(pagina(d, L), encoding="utf-8")
    (ROOT / "README.md").write_text(readme(d, "en"), encoding="utf-8")
    (ROOT / "README_ES.md").write_text(readme(d, "es"), encoding="utf-8")
    print(f"sitio: {destino}, README.md, README_ES.md")


if __name__ == "__main__":
    main()
