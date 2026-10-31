"""Simulador de corte y puntaje de un cliente, con la scorecard del proyecto y resultados reales.

Local: `streamlit run app/streamlit_app.py`.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import logica as lg

AZUL, NARANJA, NEUTRO = "#2a78d6", "#eb6834", "#898781"
PAIS = {"es": {"Finland": "Finlandia", "Estonia": "Estonia", "Netherlands": "Países Bajos", "Latvia": "Letonia", "Denmark": "Dinamarca"},
        "en": {"Finland": "Finland", "Estonia": "Estonia", "Netherlands": "Netherlands", "Latvia": "Latvia", "Denmark": "Denmark"}}
RATINGS = ["AA", "A", "B", "C", "D", "E", "F", "G"]
SITIO = "https://alvarez1lucas.github.io/modelos-credito/"
REPO = "https://github.com/alvarez1lucas/modelos-credito"

st.set_page_config(page_title="Simulador de crédito", layout="wide")


@st.cache_data
def datos():
    return lg.cargar_prueba(), lg.cargar_scorecard()


def num(x: float, L: str, d: int = 1) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".") if L == "es" else s


def signo(x: float, L: str, d: int = 2) -> str:
    return ("+" if x >= 0 else "") + num(x, L, d)


def estilo(fig: go.Figure, L: str, y: str, x: str, alto: int = 340) -> go.Figure:
    fig.update_layout(height=alto, margin=dict(l=56, r=16, t=16, b=48), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      separators=",." if L == "es" else ".,", hovermode="x unified")
    fig.update_xaxes(title=x, showgrid=False)
    fig.update_yaxes(title=y, gridcolor="rgba(137,135,129,.25)", zeroline=False)
    return fig


df, sc = datos()
L = "es" if st.sidebar.radio("Idioma / Language", ["Español", "English"], label_visibility="collapsed") == "Español" else "en"
tx = lambda es, en: es if L == "es" else en  # noqa: E731
nombre_pais = lambda p: PAIS[L].get(p, p)  # noqa: E731

st.title(tx("Simulador de crédito", "Credit simulator"))
st.caption(tx("Mové el corte y mirá qué pasa con los créditos reales de 2025, o puntuá un cliente con la scorecard. Ejercicio de portfolio: no es una herramienta para decidir sobre personas.",
              "Move the cutoff and see what happens to real 2025 loans, or score a customer with the scorecard. Portfolio exercise: not a tool for deciding about real people."))
corte_tab, cliente_tab, nota_tab = st.tabs([tx("Simulador de corte", "Cutoff simulator"), tx("Puntaje de un cliente", "Customer score"), tx("Cómo leerlo", "How to read this")])

with corte_tab:
    izq, der = st.columns([1, 2.4], gap="large")
    with izq:
        regla = st.radio(tx("Regla", "Rule"), ["pd", "margen"], format_func=lambda r: {"pd": tx("PD máxima fija", "Fixed maximum PD"), "margen": tx("Margen por crédito", "Margin per loan")}[r],
                         help=tx("PD fija: aprueba hasta un riesgo. Margen: aprueba si PD × LGD es menor que tasa menos costo.", "Fixed PD: approves up to a risk level. Margin: approves if PD × LGD is below rate minus cost."))
        corte = st.slider(tx("Corte de PD (%)", "PD cutoff (%)"), 1.0, 40.0, 20.0, 0.25, disabled=regla == "margen") / 100
        costo = st.slider(tx("Costo de fondeo y operación (puntos)", "Funding and operating cost (points)"), 0.0, 20.0, float(sc["costo"]), 0.5,
                          help=tx("Supuesto: no sale de los datos.", "Assumption: it does not come from the data."))
        lgd = st.slider(tx("LGD (%)", "LGD (%)"), 30, 90, int(100 * sc["lgd"]), 1, help=tx("Madura: 69%. Con el recupero reciente: ~50%.", "Mature: 69%. With recent recoveries: ~50%.")) / 100
        sin_paises = st.multiselect(tx("Excluir países", "Exclude countries"), sorted(df["pais"].astype(str).unique()), format_func=nombre_pais)
        sin_ratings = st.multiselect(tx("Excluir ratings", "Exclude ratings"), RATINGS)

    r = lg.resultado_credito(df, costo, lgd)
    ap = lg.aprobar(df, regla, corte, costo, lgd, sin_paises, sin_ratings)
    res = lg.resumen(df, ap, r)

    with der:
        a, b, c, d = st.columns(4)
        a.metric(tx("Aprobados", "Approved"), f"{num(res['aprobados_pct'], L)}%", help=tx(f"{num(res['monto_pct'], L)}% del monto", f"{num(res['monto_pct'], L)}% of the amount"))
        b.metric(tx("Mora a 12 meses", "12-month delinq."), "-" if res["mora_pct"] != res["mora_pct"] else f"{num(res['mora_pct'], L)}%",
                 help=tx(f"Sin regla: {num(res['mora_base_pct'], L)}%", f"No rule: {num(res['mora_base_pct'], L)}%"))
        c.metric(tx("Resultado (M€)", "Result (€M)"), num(res["resultado"] / 1e6, L, 2), help=tx("Primer año, con los supuestos elegidos", "First year, with the chosen assumptions"))
        d.metric(tx("Cambio (M€)", "Change (€M)"), signo(res["cambio"] / 1e6, L), help=tx("Contra aprobar todo", "Against approving everything"))

        p = lg.por_pais(df, ap, r)
        ceros = p[(p["aprobados"] == 0) & ~p["pais"].isin(sin_paises)]["pais"].tolist()
        if ceros and regla == "margen":
            st.warning(tx(f"Con este costo se rechaza todo {', '.join(map(nombre_pais, ceros))}: esa mejora viene del supuesto, no del modelo. Probá bajar el costo.",
                          f"With this cost all of {', '.join(map(nombre_pais, ceros))} is rejected: that gain comes from the assumption, not the model. Try a lower cost."))
        if "Denmark" not in sin_paises:
            st.info(tx("Dinamarca no estaba en el entrenamiento: el modelo predice ~9% y la mora real es ~34%. Probá excluirla.",
                       "Denmark was not in the training data: the model predicts ~9% and actual delinquency is ~34%. Try excluding it."))

        cu = lg.curva(df, costo, lgd)
        fig = go.Figure(go.Scatter(x=100 * cu["corte"], y=cu["resultado"] / 1e6, mode="lines", line=dict(color=AZUL, width=2), hovertemplate="%{y:.2f} M€<extra></extra>"))
        if regla == "pd":
            fig.add_vline(x=100 * corte, line=dict(color=NARANJA, width=2), annotation_text=tx("Tu corte", "Your cutoff"), annotation_font=dict(color=NARANJA))
        estilo(fig, L, tx("Resultado (M€)", "Result (€M)"), tx("Corte: PD máxima aprobada (%)", "Cutoff: highest PD approved (%)"))
        st.plotly_chart(fig, width="stretch")

        tabla = pd.DataFrame({tx("País", "Country"): p["pais"].map(nombre_pais), tx("Créditos", "Loans"): [num(v, L, 0) for v in p["creditos"]],
                              tx("Aprobados", "Approved"): [f"{num(100 * v, L)}%" for v in p["aprobados"]],
                              tx("Mora sin regla", "Delinquency, no rule"): [f"{num(100 * v, L)}%" for v in p["mora"]],
                              tx("Cambio (M€)", "Change (€M)"): [signo(v / 1e6, L) for v in p["cambio"]]})
        st.dataframe(tabla, hide_index=True, width="stretch")

with cliente_tab:
    izq, der = st.columns([1, 2], gap="large")
    with izq:
        paises = [*sc["paises_entrenamiento"], "Denmark"]
        paises = [p for p in paises if p != "Spain"]
        pais = st.selectbox(tx("País", "Country"), paises, format_func=nombre_pais)
        rating = st.selectbox("Rating", RATINGS, index=3)
        monto = st.number_input(tx("Monto (€)", "Amount (€)"), 100, 15000, 2000, 100)
        tasa = st.slider(tx("Tasa anual (%)", "Annual rate (%)"), 5.0, 35.0, 18.0, 0.5) / 100
        plazo = st.select_slider(tx("Plazo (meses)", "Term (months)"), [6, 12, 18, 24, 36, 48, 60, 72, 84, 120], value=60)
        ingreso = st.number_input(tx("Ingreso mensual (€)", "Monthly income (€)"), 300, 15000, 2300, 100)

    q = lg.cuota(monto, tasa, plazo)
    carga = 100 * q / ingreso
    pu = lg.puntuar(sc, {"monto": monto, "tasa": tasa, "plazo": plazo, "ingreso": ingreso, "carga_pct": carga, "pais": pais, "rating": rating})
    costo_c, lgd_c = sc["costo"] / 100, sc["lgd"]
    margen = 100 * (tasa - costo_c - pu["pd"] * lgd_c)
    with der:
        a, b, c = st.columns(3)
        a.metric(tx("Puntaje", "Score"), num(pu["puntos"], L, 0))
        b.metric(tx("PD a 12 meses", "12-month PD"), f"{num(100 * pu['pd'], L)}%")
        c.metric(tx("Margen esperado", "Expected margin"), f"{signo(margen, L, 1)} pp", help=tx(f"Costo {sc['costo']} pp, LGD {num(100 * lgd_c, L, 0)}%", f"Cost {sc['costo']} pp, LGD {num(100 * lgd_c, L, 0)}%"))
        if margen >= 0:
            st.success(tx("Con estos supuestos, la regla por margen lo aprueba.", "With these assumptions, the margin rule approves it."))
        else:
            st.error(tx("Con estos supuestos, la regla por margen lo rechaza.", "With these assumptions, the margin rule rejects it."))
        if pais not in sc["paises_entrenamiento"]:
            st.warning(tx("País fuera de dominio: el modelo nunca lo vio y lo trata como neutro. Este puntaje no es confiable.",
                          "Out-of-domain country: the model never saw it and treats it as neutral. This score is not reliable."))
        d = sorted(pu["detalle"], key=lambda f: f["puntos"])
        ind = 0 if L == "es" else 1
        fig = go.Figure(go.Bar(y=[lg.ETIQUETAS[f["variable"]][ind] for f in d], x=[f["puntos"] for f in d], orientation="h",
                               marker=dict(color=[AZUL if f["puntos"] >= 0 else NARANJA for f in d], cornerradius=4), hovertemplate="%{x:+.1f}<extra></extra>"))
        estilo(fig, L, "", tx("Puntos que suma o resta cada variable", "Points each variable adds or subtracts"), alto=320)
        fig.update_layout(hovermode="closest", margin=dict(l=8))
        fig.update_xaxes(showgrid=True, gridcolor="rgba(137,135,129,.25)", zeroline=True, zerolinecolor=NEUTRO)
        fig.update_yaxes(automargin=True, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        st.caption(tx(f"Puntos de base: {num(sc['base'], L, 0)}. Cuota: {num(q, L, 0)} €, {num(carga, L)}% del ingreso. Cada {sc['pdo']} puntos se duplican las odds.",
                      f"Base points: {num(sc['base'], L, 0)}. Payment: €{num(q, L, 0)}, {num(carga, L)}% of income. Every {sc['pdo']} points the odds double."))

with nota_tab:
    if L == "es":
        st.markdown(f"""
**Qué mirar.** Con costo de 5 puntos, la regla por margen casi no cambia nada. Con 10 rechaza todo Países Bajos, y parece una gran mejora. El resultado depende del supuesto: esa es la lección.

**Datos.** {num(len(df), L, 0)} créditos de consumo de Bondora otorgados en 2025, que el modelo no vio al entrenar, con su resultado real a 12 meses.

**Resultado.** Monto × (tasa - costo) - evento × LGD × monto. Mira el primer año, antes de impuestos, y usa el monto como exposición.

**Límites.** A los rechazados por Bondora no se los observa: sólo se puede evaluar endurecer. La PD está calibrada con datos de 2024 y subestima la mora de 2025.

[Sitio del proyecto]({SITIO}) · [Código]({REPO}) · [Ficha del modelo]({REPO}/blob/main/docs/ficha_modelo.md)
""")
    else:
        st.markdown(f"""
**What to look at.** With a cost of 5 points, the margin rule barely changes anything. With 10 it rejects all of the Netherlands and looks like a big gain. The result depends on the assumption: that is the lesson.

**Data.** {num(len(df), L, 0)} Bondora consumer loans granted in 2025, which the model did not see in training, with their real 12-month outcome.

**Result.** Amount × (rate - cost) - event × LGD × amount. It covers the first year, before taxes, and uses the amount as exposure.

**Limits.** Applicants rejected by Bondora are not observed: only tightening can be evaluated. PD is calibrated on 2024 data and underestimates 2025 delinquency.

[Project site]({SITIO}en/) · [Code]({REPO}) · [Model card]({REPO}/blob/main/docs/ficha_modelo.md)
""")
