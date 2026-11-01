// Todos los textos de la app, en los dos idiomas.

const SITIO = "https://alvarez1lucas.github.io/modelos-credito/";
const REPO = "https://github.com/alvarez1lucas/modelos-credito";
const FICHA = `${REPO}/blob/main/docs/ficha_modelo.md`;

export const T = {
  es: {
    locale: "es-AR", titulo: "Simulador de crédito", saltar: "Saltar al contenido", marca: "Simulador de crédito", secciones: "Secciones", cambiarTema: "Cambiar entre tema claro y oscuro",
    tabCorte: "Simulador", tabCliente: "Un cliente", tabMetodo: "Cómo leerlo",
    tituloCorte: "¿Qué pasa si cambiás el corte?",
    bajadaCorte: (n) => `Probá una regla sobre ${n} créditos reales otorgados en 2025, que el modelo no vio al entrenar. Ejercicio de portfolio: no sirve para decidir sobre personas.`,
    atajos: "Empezá por una regla", regla: "Regla", reglaPd: "PD máxima", reglaMargen: "Margen",
    ayudaPd: "Aprueba hasta un nivel de riesgo, igual para todos.", ayudaMargen: "Aprueba si PD × LGD es menor que tasa menos costo: cada crédito se compara con su propia tasa.",
    corte: "Corte de PD", noAplica: "No aplica", costo: "Costo de fondeo y operación", lgd: "LGD",
    ayudaCosto: "Supuesto: no sale de los datos.", ayudaLgd: "Madura: 69%. Con el recupero reciente: ~50%.",
    paises: "Países", ratings: "Ratings", ayudaFiltros: "Tocá uno para excluirlo.", compartir: "Copiar enlace", reiniciar: "Reiniciar", copiado: "Enlace copiado", sinCopiar: "No se pudo copiar el enlace",
    presets: { aprobar: "Aprobar todo", eg: "Sacar E a G", ks: "Corte por KS", eco: "Corte económico", m10: "Margen, costo 10", m5: "Margen, costo 5", propio: "Tu escenario" },
    titular: (s, f) => {
      if (s.rechazados === 0) return "Esta regla no rechaza ningún crédito: es lo mismo que aprobar todo.";
      if (s.moraPct === null) return "Esta regla rechaza todos los créditos.";
      const mora = s.moraPct <= s.moraBasePct ? "baja" : "sube";
      const res = s.cambio >= 0 ? "sube" : "baja";
      const costo = s.buenosPorMalo === null ? "" : ` Por cada crédito malo que evita, rechaza ${f.n(s.buenosPorMalo, 1)} buenos.`;
      return `Aprueba el ${f.n(s.aprobadosPct, 1)}% de los créditos. La mora ${mora} de ${f.n(s.moraBasePct, 1)}% a ${f.n(s.moraPct, 1)}% y el resultado ${res} ${f.n(Math.abs(s.cambio) / 1e6, 2)} M€.${costo}`;
    },
    kAprobados: "Aprobados", kMora: "Mora a 12 meses", kResultado: "Resultado", kCambio: "Cambio",
    nMonto: (x) => `${x}% del monto`, nMoraBase: (x) => `Sin regla: ${x}%`, nResultado: "Primer año, en M€", nCambio: "M€, contra aprobar todo",
    aviso: "Atención", nota: "Nota",
    avisoPais: (l, c) => `Con un costo de ${c} puntos se rechaza todo ${l}. Esa mejora viene del supuesto, no del modelo: probá bajar el costo.`,
    avisoDk: "Dinamarca no estaba en el entrenamiento: el modelo predice ~9% y la mora real es ~34%. Probá excluirla.",
    tituloCurva: "Resultado según el corte", subCurvaPd: "Arrastrá sobre el gráfico para mover el corte.", subCurvaMargen: "La regla por margen no usa un corte único: la curva muestra la alternativa con PD fija.",
    ejeCorte: "Corte: PD máxima aprobada (%)", ejeResultado: "Resultado (M€)", tuCorte: "Tu corte", maximo: "Máximo",
    tipCurva: (c, a) => `Corte ${c}% · aprueba ${a}%`,
    notaCurva: (c) => `El máximo está cerca de ${c}%, pero sólo se conoce después: elegirlo mirando estos créditos sería hacer trampa.`,
    tituloSegmento: "Dónde pega la regla", subSegmento: "Qué parte de cada grupo aprueba y cuánto cambia el resultado.", porPais: "País", porRating: "Rating",
    cSegPais: "País", cSegRating: "Rating", cCreditos: "Créditos", cAprobados: "Aprobados", cMora: "Mora sin regla", cCambio: "Cambio (M€)", cRegla: "Regla", cCosto: "Costo", cMoraRegla: "Mora",
    tituloReglas: "Comparar reglas", subReglas: "Tocá una fila para aplicarla. El cambio se mide contra aprobar todo, con el costo de cada fila.",
    tituloCliente: "Puntuá un cliente", bajadaCliente: "La scorecard suma puntos por variable: se puede explicar cada decisión. Los datos no salen de tu navegador.",
    pais: "País", monto: "Monto (€)", ingreso: "Ingreso mensual (€)", tasa: "Tasa anual", plazo: "Plazo", meses: "meses",
    aprobada: "Aprobado por la regla de margen", rechazada: "Rechazado por la regla de margen",
    supuestos: (c, l) => `Con costo de ${c} puntos y LGD de ${l}%, los del simulador.`,
    kPuntaje: "Puntaje", kPd: "PD a 12 meses", kMargen: "Margen esperado", kEquilibrio: "Tasa de equilibrio",
    nPuntaje: (b, p) => `Base ${b}. Cada ${p} puntos se duplican las odds`, nPd: "Calibrada con datos de 2024", nMargen: "Tasa - costo - PD × LGD", nEquilibrio: "La más baja que aprueba", sinEquilibrio: "Ninguna hasta 35%", nada: "-",
    avisoDominio: "País fuera de dominio: el modelo nunca lo vio y lo trata como neutro. Este puntaje no es confiable.",
    avisoCarga: (c, x) => `La cuota es el ${c}% del ingreso, y el 99,9% de los créditos del entrenamiento quedó debajo de ${x}%. El modelo casi no vio casos así: este puntaje no es confiable.`,
    tituloAportes: "Qué suma y qué resta", subAportes: (q, c, l) => `Cuota de ${q} €, ${c}% del ingreso.${l ? ` Lo que más resta: ${l}.` : ""}`,
    variables: { monto: "Monto", tasa: "Tasa", plazo: "Plazo", ingreso: "Ingreso", carga_pct: "Carga de la cuota", pais: "País", rating: "Rating" },
    tituloPosicion: "Dónde queda en la cartera", subPosicion: (p) => `Más riesgoso que el ${p}% de los créditos de 2025.`, ejePd: "PD a 12 meses (%)", esteCliente: "Este cliente", tipHist: (a, b, n) => `${n} créditos con PD de ${a}% a ${b}%`,
    tituloMetodo: "Cómo leerlo", bajadaMetodo: "Lo que hay detrás de los números y hasta dónde se puede confiar en ellos.",
    secciones_metodo: (n) => [
      ["Qué mirar", "Probá la regla de margen con costo 10 y después con 5. Con 10 rechaza todo Países Bajos y parece una gran mejora; con 5 casi no cambia nada. El resultado depende del supuesto: esa es la lección."],
      ["Datos", `${n} créditos de consumo de Bondora otorgados en 2025, con su resultado real a 12 meses. El modelo no los vio al entrenar.`],
      ["Resultado", "Monto × (tasa - costo) - evento × LGD × monto. Mira el primer año, antes de impuestos, y usa el monto como exposición."],
      ["Límites", "A los rechazados por Bondora no se los observa: sólo se puede evaluar endurecer. La PD está calibrada con datos de 2024 y subestima la mora de 2025."],
      ["Scorecard", "Cada variable se agrupa en tramos con WoE y entra en una regresión logística. La tabla de puntos usa base 600 con odds de 50 y duplica las odds cada 20 puntos. La tasa de equilibrio se busca probando tasas, porque la tasa también mueve la PD."],
      ["Cómo funciona", "Sin servidor: los créditos llegan comprimidos y cada número se calcula en tu navegador. Los tests comparan estos cálculos con la versión en Python y con los resultados del proyecto."],
    ],
    enlaces: [["Sitio del proyecto", SITIO], ["Código", REPO], ["Ficha del modelo", FICHA]], pie: "Datos: Bondora. Ejercicio de portfolio de Lucas Alvarez.", sitio: "../",
    errorDatos: "No se pudieron cargar los datos. Recargá la página.", errorNavegador: "Este navegador es muy antiguo para esta app. Probá con una versión actual.",
  },
  en: {
    locale: "en-US", titulo: "Credit simulator", saltar: "Skip to content", marca: "Credit simulator", secciones: "Sections", cambiarTema: "Switch between light and dark theme",
    tabCorte: "Simulator", tabCliente: "One customer", tabMetodo: "How to read this",
    tituloCorte: "What happens if you change the cutoff?",
    bajadaCorte: (n) => `Try a rule on ${n} real loans granted in 2025, which the model did not see in training. Portfolio exercise: not for deciding about real people.`,
    atajos: "Start from a rule", regla: "Rule", reglaPd: "Maximum PD", reglaMargen: "Margin",
    ayudaPd: "Approves up to a risk level, the same for everyone.", ayudaMargen: "Approves if PD × LGD is below rate minus cost: each loan is compared with its own rate.",
    corte: "PD cutoff", noAplica: "Not used", costo: "Funding and operating cost", lgd: "LGD",
    ayudaCosto: "Assumption: it does not come from the data.", ayudaLgd: "Mature: 69%. With recent recoveries: ~50%.",
    paises: "Countries", ratings: "Ratings", ayudaFiltros: "Tap one to exclude it.", compartir: "Copy link", reiniciar: "Reset", copiado: "Link copied", sinCopiar: "Could not copy the link",
    presets: { aprobar: "Approve all", eg: "Remove E to G", ks: "KS cutoff", eco: "Economic cutoff", m10: "Margin, cost 10", m5: "Margin, cost 5", propio: "Your scenario" },
    titular: (s, f) => {
      if (s.rechazados === 0) return "This rule rejects no loans: it is the same as approving everything.";
      if (s.moraPct === null) return "This rule rejects every loan.";
      const mora = s.moraPct <= s.moraBasePct ? "falls" : "rises";
      const res = s.cambio >= 0 ? "rises" : "falls";
      const costo = s.buenosPorMalo === null ? "" : ` For each bad loan it avoids, it rejects ${f.n(s.buenosPorMalo, 1)} good ones.`;
      return `It approves ${f.n(s.aprobadosPct, 1)}% of loans. Delinquency ${mora} from ${f.n(s.moraBasePct, 1)}% to ${f.n(s.moraPct, 1)}% and the result ${res} by €${f.n(Math.abs(s.cambio) / 1e6, 2)}M.${costo}`;
    },
    kAprobados: "Approved", kMora: "12-month delinquency", kResultado: "Result", kCambio: "Change",
    nMonto: (x) => `${x}% of the amount`, nMoraBase: (x) => `No rule: ${x}%`, nResultado: "First year, in €M", nCambio: "€M, vs approving all",
    aviso: "Warning", nota: "Note",
    avisoPais: (l, c) => `With a cost of ${c} points all of ${l} is rejected. That gain comes from the assumption, not the model: try a lower cost.`,
    avisoDk: "Denmark was not in the training data: the model predicts ~9% and actual delinquency is ~34%. Try excluding it.",
    tituloCurva: "Result by cutoff", subCurvaPd: "Drag across the chart to move the cutoff.", subCurvaMargen: "The margin rule has no single cutoff: the curve shows the fixed-PD alternative.",
    ejeCorte: "Cutoff: highest PD approved (%)", ejeResultado: "Result (€M)", tuCorte: "Your cutoff", maximo: "Peak",
    tipCurva: (c, a) => `Cutoff ${c}% · approves ${a}%`,
    notaCurva: (c) => `The peak is near ${c}%, but it is only known afterwards: choosing it by looking at these loans would be cheating.`,
    tituloSegmento: "Where the rule bites", subSegmento: "How much of each group is approved and how the result changes.", porPais: "Country", porRating: "Rating",
    cSegPais: "Country", cSegRating: "Rating", cCreditos: "Loans", cAprobados: "Approved", cMora: "Delinq., no rule", cCambio: "Change (€M)", cRegla: "Rule", cCosto: "Cost", cMoraRegla: "Delinq.",
    tituloReglas: "Compare rules", subReglas: "Tap a row to apply it. Change is measured against approving all, with each row's cost.",
    tituloCliente: "Score a customer", bajadaCliente: "The scorecard adds points by variable, so every decision can be explained. Your inputs never leave the browser.",
    pais: "Country", monto: "Amount (€)", ingreso: "Monthly income (€)", tasa: "Annual rate", plazo: "Term", meses: "months",
    aprobada: "Approved by the margin rule", rechazada: "Rejected by the margin rule",
    supuestos: (c, l) => `With a cost of ${c} points and an LGD of ${l}%, as set in the simulator.`,
    kPuntaje: "Score", kPd: "12-month PD", kMargen: "Expected margin", kEquilibrio: "Break-even rate",
    nPuntaje: (b, p) => `Base ${b}. Odds double every ${p} points`, nPd: "Calibrated on 2024 data", nMargen: "Rate - cost - PD × LGD", nEquilibrio: "Lowest that is approved", sinEquilibrio: "None up to 35%", nada: "-",
    avisoDominio: "Out-of-domain country: the model never saw it and treats it as neutral. This score is not reliable.",
    avisoCarga: (c, x) => `The payment is ${c}% of income, and 99.9% of training loans stayed below ${x}%. The model barely saw cases like this: this score is not reliable.`,
    tituloAportes: "What adds and what subtracts", subAportes: (q, c, l) => `Payment of €${q}, ${c}% of income.${l ? ` Largest deductions: ${l}.` : ""}`,
    variables: { monto: "Amount", tasa: "Rate", plazo: "Term", ingreso: "Income", carga_pct: "Payment burden", pais: "Country", rating: "Rating" },
    tituloPosicion: "Where it sits in the portfolio", subPosicion: (p) => `Riskier than ${p}% of 2025 loans.`, ejePd: "12-month PD (%)", esteCliente: "This customer", tipHist: (a, b, n) => `${n} loans with PD from ${a}% to ${b}%`,
    tituloMetodo: "How to read this", bajadaMetodo: "What is behind the numbers and how far they can be trusted.",
    secciones_metodo: (n) => [
      ["What to look at", "Try the margin rule with a cost of 10 and then 5. With 10 it rejects all of the Netherlands and looks like a big gain; with 5 it barely changes anything. The result depends on the assumption: that is the lesson."],
      ["Data", `${n} Bondora consumer loans granted in 2025, with their real 12-month outcome. The model did not see them in training.`],
      ["Result", "Amount × (rate - cost) - event × LGD × amount. It covers the first year, before taxes, and uses the amount as exposure."],
      ["Limits", "Applicants rejected by Bondora are not observed: only tightening can be evaluated. PD is calibrated on 2024 data and underestimates 2025 delinquency."],
      ["Scorecard", "Each variable is binned with WoE and enters a logistic regression. The points table uses base 600 at odds of 50 and doubles the odds every 20 points. The break-even rate is found by trying rates, because the rate also moves PD."],
      ["How it works", "No server: the loans arrive compressed and every number is computed in your browser. Tests compare these calculations with the Python version and the project's results."],
    ],
    enlaces: [["Project site", `${SITIO}en/`], ["Code", REPO], ["Model card", FICHA]], pie: "Data: Bondora. Portfolio exercise by Lucas Alvarez.", sitio: "../en/",
    errorDatos: "The data could not be loaded. Reload the page.", errorNavegador: "This browser is too old for this app. Try a current version.",
  },
};

export const PAISES = {
  es: { Finland: "Finlandia", Estonia: "Estonia", Netherlands: "Países Bajos", Latvia: "Letonia", Denmark: "Dinamarca" },
  en: { Finland: "Finland", Estonia: "Estonia", Netherlands: "Netherlands", Latvia: "Latvia", Denmark: "Denmark" },
};
