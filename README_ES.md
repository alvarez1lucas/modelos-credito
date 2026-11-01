# Modelos de crédito

[![Tests](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/tests.yml/badge.svg)](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/tests.yml) [![Monitoreo](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/monitoreo.yml/badge.svg)](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/monitoreo.yml) [![Sitio](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/publicar-sitio.yml/badge.svg)](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/publicar-sitio.yml) ![Python 3.11](https://img.shields.io/badge/python-3.11-blue)

**[Sitio](https://alvarez1lucas.github.io/modelos-credito/)** · **[App interactiva](https://alvarez1lucas.github.io/modelos-credito/app/)** · **[Ficha del modelo](docs/ficha_modelo.md)** · [English version](README.md)

Un modelo de riesgo se juzga por las decisiones que mejora, no por su Gini. Este proyecto entrena con cosechas viejas de una cartera de consumo real, mide con cosechas posteriores y compara siempre contra el rating que la empresa ya tiene. Sin datasets de Kaggle.

## En 30 segundos

| Pregunta | Hallazgo |
|---|---|
| ¿Le gana al que ya existe? | Sólo si lo usa: LightGBM sin rating da 0,32 contra 0,36. Con él, la scorecard llega a 0,42 |
| ¿Hace falta algo complejo? | No: scorecard 0,421 contra LightGBM 0,404 en cosechas nuevas, con intervalos que no se tocan |
| ¿El corte gana plata? | Depende del costo: de +0,00 a +3,04 M€, y el 55% de esto último viene de rechazar un país entero |
| ¿Dónde falla? | En lo que nunca vio: Dinamarca se predice en 9% con 34% de mora real |
| ¿Sigue valiendo? | Ordena bien, pero el nivel se corrió: brecha de 0,0 a 2,3 puntos con el Gini estable |
| ¿Qué no ve a 12 meses? | El default pasa de 7,8% a 12 meses a 24,2% a 36; tratar la cancelación como censura diría 35,4% |

**Stack:** Python (scikit-learn, LightGBM, SHAP, pandas, DuckDB), scorecard con WoE/IV escrita a mano, Aalen-Johansen para riesgos competidores, JavaScript con gráficos SVG propios, pytest, GitHub Actions, GitHub Pages.

## Reproducir

Necesita las fotos de Bondora de [umbrales-credito](https://github.com/alvarez1lucas/umbrales-credito).

```bash
pip install -r requirements.txt && pip install -e .
python -m modelos.entrenar && python -m modelos.corte && python -m modelos.validacion
python -m modelos.supervivencia && python -m modelos.monitoreo && python -m modelos.sitio
python -m modelos.exportar_app && python -m modelos.sitio && python -m http.server -d site
pytest
```

Autor: Lucas Alvarez · [GitHub](https://github.com/alvarez1lucas) · Relacionado: [Umbrales de crédito](https://github.com/alvarez1lucas/umbrales-credito), [Mora de los hogares en Argentina](https://github.com/alvarez1lucas/mora_argentina)
