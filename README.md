# Credit risk models

[![Tests](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/tests.yml/badge.svg)](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/tests.yml) [![Monitoreo](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/monitoreo.yml/badge.svg)](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/monitoreo.yml) [![Site](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/publicar-sitio.yml/badge.svg)](https://github.com/alvarez1lucas/modelos-credito/actions/workflows/publicar-sitio.yml) ![Python 3.11](https://img.shields.io/badge/python-3.11-blue)

**[Live site](https://alvarez1lucas.github.io/modelos-credito/en/)** · **[Interactive app](https://modelos-credito.streamlit.app/)** · **[Model card](docs/ficha_modelo.md)** · [Versión en español](README_ES.md)

A risk model is judged by the decisions it improves, not by its Gini. This project trains on old vintages of a real consumer portfolio, measures on later ones, and always compares against the rating the lender already has. No Kaggle datasets.

## At a glance

| Question | Finding |
|---|---|
| Does it beat what exists? | Only by using it: LightGBM without the rating gets 0.32 against 0.36. With it, the scorecard reaches 0.42 |
| Is something complex needed? | No: scorecard 0.421 against LightGBM 0.404 on new vintages, with intervals that do not touch |
| Does the cutoff make money? | Depends on cost: from +0.00 to +3.04 €M, and 55% of the latter comes from rejecting a whole country |
| Where does it fail? | On what it never saw: Denmark is predicted at 9% with 34% actual delinquency |
| Does it still hold? | It ranks well but the level shifted: gap from 0.0 to 2.3 points with a stable Gini |
| What does a 12-month model miss? | Default goes from 7.8% at 12 months to 24.2% at 36; treating prepayment as censoring would say 35.4% |

**Stack:** Python (scikit-learn, LightGBM, SHAP, pandas, DuckDB), scorecard with WoE/IV built by hand, Aalen-Johansen for competing risks, Streamlit, pytest, GitHub Actions, GitHub Pages.

## Reproduce

Requires the Bondora snapshots from [umbrales-credito](https://github.com/alvarez1lucas/umbrales-credito).

```bash
pip install -r requirements.txt && pip install -e .
python -m modelos.entrenar && python -m modelos.corte && python -m modelos.validacion
python -m modelos.supervivencia && python -m modelos.monitoreo && python -m modelos.sitio
python -m modelos.exportar_app && streamlit run app/streamlit_app.py
pytest
```

Author: Lucas Alvarez · [GitHub](https://github.com/alvarez1lucas) · Related: [Credit thresholds](https://github.com/alvarez1lucas/umbrales-credito), [Household loan delinquency in Argentina](https://github.com/alvarez1lucas/mora_argentina)
