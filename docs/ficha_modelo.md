# Ficha del modelo

Documento de validación del modelo elegido. Las cifras son las de la foto del 22-oct-2026 y están en `outputs/`.

## Qué es

- **Modelo:** scorecard tradicional, con regresión logística sobre WoE y recalibración de nivel en validación.
- **Objetivo:** probabilidad de llegar a 90 días de atraso, default o pérdida dentro de los 12 meses del otorgamiento.
- **Uso:** ejercicio de portfolio. No es un modelo en producción ni está aprobado para decidir sobre personas.
- **Población:** créditos de consumo de Bondora otorgados desde oct-23, en Finlandia, Estonia, Países Bajos y Letonia.
- **Fuera de alcance:** países sin historia en entrenamiento (hoy, Dinamarca) y solicitantes rechazados.

## Datos

| Conjunto | Otorgados | Créditos | Mora a 12 meses | Uso |
|---|---|---:|---:|---|
| Entrenamiento | oct-23 a sep-24 | 121.623 | 8,0% | Tramos, coeficientes y árboles |
| Validación | oct-24 a dic-24 | 41.119 | 7,0% | Hiperparámetros, recalibración y cortes |
| Prueba | ene-25 a oct-25 | 137.835 | 7,9% | Sólo medición |

**Fuga de información.** Comparando dos fotos, el rating cambia en 0,02% de los créditos, y el ingreso, la tasa, el monto y el plazo en ninguno.
`nr_of_payments` cambia en 26% y queda afuera. Tampoco se usa ninguna variable de desempeño.

## Variables

Rating (IV 0,30), país (0,07), ingreso (0,07), plazo (0,06), tasa (0,06), carga de la cuota (0,04), monto (0,03) y cuota (0,01). Los tramos se
fusionan hasta que el WoE sea monótono, para que cada punto se pueda explicar. Tabla completa en `outputs/modelos/tabla_puntos.csv`.

## Desempeño en prueba

| Modelo | Gini | IC 95% | KS |
|---|---:|---:|---:|
| Rating de Bondora | 0,363 | 0,354-0,373 | 0,27 |
| Sólo rating y país | 0,386 | 0,378-0,396 | 0,29 |
| Scorecard sin rating | 0,293 | 0,282-0,305 | 0,23 |
| LightGBM sin rating | 0,322 | 0,312-0,334 | 0,24 |
| LightGBM con rating | 0,404 | 0,397-0,413 | 0,29 |
| **Scorecard con rating** | **0,421** | **0,413-0,430** | **0,31** |

LightGBM tuvo búsqueda en grilla por Gini en validación. En validación ambos empataron en 0,413, así que la scorecard se eligió por simpleza y explicación;
la prueba lo confirmó. Sin Dinamarca, la diferencia se mantiene: 0,415 contra 0,402.

## Debilidades conocidas

- **Calibración en baja:** predice 6,2% y la mora real de 2025T4 es 8,5%. La brecha crece desde 2024T4.
- **Dinamarca:** predice 9% contra 34% real. No tiene créditos en entrenamiento.
- **Letonia:** predice 20% contra 26%, con muestra chica en entrenamiento.
- **Sesgo de selección:** se entrena sólo con aprobados por Bondora.
- **Ventana corta:** cuatro trimestres de entrenamiento, uno de validación y una sola prueba. No cubre un ciclo.
- **Dependencia del rating:** la mayor parte de la señal es del rating de Bondora, una caja negra cuyo método puede cambiar.

## Corte

Con costo supuesto de 10 puntos y LGD de 69%, en prueba:

| Regla | Créditos que quedan | Cambio en resultado (M€) | IC 95% |
|---|---:|---:|---:|
| Sin ratings E a G | 92,6% | +0,50 | +0,43 a +0,57 |
| Corte por KS (PD ≤ 7,6%) | 68,2% | +0,34 | +0,03 a +0,65 |
| Corte económico (PD ≤ 20%) | 98,0% | +0,03 | -0,01 a +0,08 |
| Margen esperado por crédito | 75,0% | +3,04 | +2,82 a +3,29 |

En prueba, el mejor corte por PD habría sido 12,75% (+0,71 M€), cerca del equilibrio teórico de 11%. No se puede saber de antemano: el corte económico de validación dio 20%, porque un solo trimestre es inestable.

La regla por margen no debe leerse como +3,04 M€ de mérito del modelo: el 55% viene de rechazar todo Países Bajos, cuya tasa iguala al costo supuesto,
y con costo de 5 puntos la mejora es +0,14 M€. **Conclusión:** comparar riesgo contra tasa es la lógica correcta, pero su valor depende del costo real por país, que no es público.

## Monitoreo

El modelo queda congelado en `modelos_guardados/`. El workflow mensual lo evalúa con cada foto nueva, sin reentrenar:

| Señal | Vigilar | Actuar | Hoy |
|---|---:|---:|---|
| Caída de Gini | 0,03 | 0,05 | OK |
| Brecha de calibración, última cosecha (pp) | 1,0 | 2,0 | Actuar (2,3) |
| Peor brecha por país (pp) | 3,0 | 5,0 | Actuar (23,3, Dinamarca) |
| PSI de créditos nuevos | 0,10 | 0,25 | OK (0,07) |
| Países fuera de dominio | - | alguno | Actuar (Dinamarca) |

**Acción recomendada:** recalibrar el nivel, excluir Dinamarca del alcance hasta tener historia propia y reentrenar cuando madure 2025T4. El PSI de la tasa con tramos fijos
de 2,5 puntos es 0,79, por cambios reales de precios. Con tramos por cuantiles daba 3,57, inflado por los valores de lista.

## Supervivencia

Incidencia acumulada a 36 meses por Aalen-Johansen, sobre 480.392 créditos: 24,2% de default, 48,0% de cancelación y 27,9% vivos. Tratar la cancelación como
censura daría 35,4%. El default a 36 meses es unas tres veces el de 12 meses (7,8%), así que la PD a 12 meses no sirve como pérdida de vida completa.

## Limitaciones

- La mora a 12 meses se conoce un año después: el monitoreo de calibración siempre llega tarde.
- La recalibración con el trimestre anterior que muestra `outputs/monitoreo/` prueba que el error es de nivel y no de orden; no es un pronóstico, porque ese dato todavía no se tiene al puntuar.
- El costo de 10 puntos es un supuesto y es igual para todos los países. La LGD de 69% viene de cosechas viejas; encadenando el recupero reciente da ~50%.
- El resultado económico mira el primer año y usa el monto como exposición.
- No se evaluó impacto por grupos demográficos: Bondora no publica esos datos.
