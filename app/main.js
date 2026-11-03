import * as lg from "./logica.js";
import * as gr from "./graficos.js";
import { PAISES, T } from "./textos.js";

const $ = (id) => document.getElementById(id);
const PLAZOS = [6, 12, 18, 24, 36, 48, 60, 72, 84, 120];
const ICONO = {
  aviso: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2 1 18h18L10 2Zm0 6v5m0 2.2v.3"/></svg>',
  nota: '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8"/><path d="M10 9v5m0-8v.3"/></svg>',
  ok: '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8"/><path d="m6.5 10.5 2.4 2.4 4.6-5.2"/></svg>',
  no: '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8"/><path d="m7 7 6 6m0-6-6 6"/></svg>',
};

const e = {
  L: idiomaInicial(), tab: "corte", segmento: "pais",
  esc: { regla: "pd", corte: 0.2, costo: 10, lgd: 0.69, sinPaises: [], sinRatings: [] },
  cli: { pais: "Finland", rating: "C", monto: 2000, ingreso: 2300, tasa: 0.18, plazo: 60 },
};
let d, meta, sc, presets = [], filasPresets = [], hist;
const memo = { r: { clave: null }, curva: { clave: null } };

const tx = () => T[e.L];
const pais = (p) => PAISES[e.L][p] ?? p;

function idiomaInicial() {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "es" || q === "en") return q;
  return "en"; // inglés por defecto; ?lang=es o el botón ES pasan a español
}

const formatos = new Map();
function n(x, dec = 1) {
  const k = `${e.L}${dec}`;
  if (!formatos.has(k)) formatos.set(k, new Intl.NumberFormat(tx().locale, { minimumFractionDigits: dec, maximumFractionDigits: dec }));
  const v = Math.round(x * 10 ** dec) / 10 ** dec;
  return formatos.get(k).format(v === 0 ? 0 : v);
}
const s = (x, dec = 1) => (Math.round(x * 10 ** dec) / 10 ** dec >= 0 ? "+" : "") + n(x, dec);
const f = { n, s };

function costoTxt(c) {
  return n(c, Number.isInteger(c) ? 0 : 1);
}

// ---------------------------------------------------------------- textos

function aplicarTextos() {
  const t = tx();
  document.documentElement.lang = e.L;
  document.title = t.titulo;
  document.querySelectorAll("[data-t]").forEach((x) => (x.textContent = t[x.dataset.t]));
  document.querySelectorAll("[data-t-aria]").forEach((x) => x.setAttribute("aria-label", t[x.dataset.tAria]));
  $("enlace-sitio").href = t.sitio;
  $("es").setAttribute("aria-pressed", e.L === "es");
  $("en").setAttribute("aria-pressed", e.L === "en");
  const links = t.enlaces.map(([a, u]) => `<a href="${u}">${a}</a>`).join(" · ");
  $("pie").innerHTML = `${t.pie} ${links}`;
  if (!meta) return;
  $("bajada-corte").textContent = t.bajadaCorte(n(meta.n, 0));
  $("metodo").innerHTML = t.secciones_metodo(n(meta.n, 0)).map(([a, b]) => `<article class="tarjeta"><h2>${a}</h2><p>${b}</p></article>`).join("");
  armarSelectores();
}

function armarSelectores() {
  const c = $("c-pais");
  const paises = [...meta.scorecard.paises_entrenamiento.filter((p) => meta.paises.includes(p)), "Denmark"];
  c.innerHTML = paises.sort((a, b) => pais(a).localeCompare(pais(b))).map((p) => `<option value="${p}">${pais(p)}</option>`).join("");
  c.value = e.cli.pais;
  $("c-rating").innerHTML = meta.ratings.map((r) => `<option>${r}</option>`).join("");
  $("c-rating").value = e.cli.rating;
}

// ---------------------------------------------------------------- simulador

function resultadosActuales() {
  const clave = `${e.esc.costo}|${e.esc.lgd}`;
  if (memo.r.clave !== clave) Object.assign(memo.r, { clave, v: lg.resultados(d, e.esc.costo, e.esc.lgd) });
  return memo.r.v;
}

function curvaActual(r) {
  const clave = `${e.esc.costo}|${e.esc.lgd}|${e.esc.sinPaises}|${e.esc.sinRatings}`;
  if (memo.curva.clave !== clave) Object.assign(memo.curva, { clave, v: lg.curva(d, r, e.esc, meta.paises, meta.ratings) });
  return memo.curva.v;
}

const mismos = (a, b) => [...a].sort().join() === [...b].sort().join();

function presetActivo() {
  return presets.find((p) => {
    const x = p.esc;
    return x.regla === e.esc.regla && x.costo === e.esc.costo && x.lgd === e.esc.lgd && (x.regla === "margen" || x.corte === e.esc.corte) &&
      mismos(x.sinPaises, e.esc.sinPaises) && mismos(x.sinRatings, e.esc.sinRatings);
  });
}

function armarPresets() {
  const b = { regla: "pd", corte: 0.4, costo: meta.costo, lgd: meta.lgd, sinPaises: [], sinRatings: [] };
  presets = [
    { id: "aprobar", esc: b },
    { id: "eg", esc: { ...b, sinRatings: ["E", "F", "G"] } },
    { id: "ks", esc: { ...b, corte: meta.corte_ks } },
    { id: "eco", esc: { ...b, corte: meta.corte_economico } },
    { id: "m10", esc: { ...b, regla: "margen" } },
    { id: "m5", esc: { ...b, regla: "margen", costo: 5 } },
  ];
  filasPresets = presets.map((p) => ({ id: p.id, costo: p.esc.costo, ...lg.resumen(d, lg.aprobar(d, p.esc, meta.paises, meta.ratings), lg.resultados(d, p.esc.costo, p.esc.lgd)) }));
}

const aplicarPreset = (p) => {
  e.esc = { ...p.esc, sinPaises: [...p.esc.sinPaises], sinRatings: [...p.esc.sinRatings] };
  pintar();
};

function kpi(titulo, valor, nota) {
  return `<div class="kpi"><div class="kpi-etq">${titulo}</div><div class="kpi-valor">${valor}</div><div class="kpi-nota">${nota}</div></div>`;
}

function aviso(tipo, texto) {
  const t = tx();
  return `<div class="aviso ${tipo === "aviso" ? "medio" : "suave"}">${ICONO[tipo]}<p><strong>${tipo === "aviso" ? t.aviso : t.nota}.</strong> ${texto}</p></div>`;
}

function barraSegmentada(id, valor) {
  $(id).querySelectorAll("button").forEach((b) => {
    const on = b.dataset.v === valor;
    b.setAttribute("aria-checked", on);
    b.tabIndex = on ? 0 : -1;
  });
}

function pintarDeslizador(id, salida, texto) {
  const x = $(id);
  x.style.setProperty("--p", `${(100 * (x.value - x.min)) / (x.max - x.min)}%`);
  $(salida).textContent = texto;
}

function pintarControles() {
  const t = tx(), c = e.esc, activo = presetActivo();
  barraSegmentada("regla", c.regla);
  barraSegmentada("segmento", e.segmento);
  $("ayuda-regla").textContent = c.regla === "pd" ? t.ayudaPd : t.ayudaMargen;
  $("corte").value = 100 * c.corte;
  $("corte").disabled = c.regla === "margen";
  $("grupo-corte").classList.toggle("apagado", c.regla === "margen");
  $("costo").value = c.costo;
  $("lgd").value = 100 * c.lgd;
  pintarDeslizador("corte", "v-corte", c.regla === "pd" ? `${n(100 * c.corte, 2)}%` : t.noAplica);
  pintarDeslizador("costo", "v-costo", `${n(c.costo, 1)} pp`);
  pintarDeslizador("lgd", "v-lgd", `${n(100 * c.lgd, 0)}%`);
  $("atajos").innerHTML = presets.map((p) => `<button class="chip" data-id="${p.id}" aria-pressed="${p === activo}">${t.presets[p.id]}</button>`).join("");
  $("f-paises").innerHTML = meta.paises.map((p) => `<button class="chip filtro" data-v="${p}" aria-pressed="${!c.sinPaises.includes(p)}">${pais(p)}</button>`).join("");
  $("f-ratings").innerHTML = meta.ratings.map((r) => `<button class="chip filtro" data-v="${r}" aria-pressed="${!c.sinRatings.includes(r)}">${r}</button>`).join("");
}

function tablaSegmentos(a, r) {
  const t = tx(), porPais = e.segmento === "pais";
  let f = lg.porSegmento(d, a, r, e.segmento, porPais ? meta.paises : meta.ratings);
  if (porPais) f = f.sort((x, y) => y.creditos - x.creditos);
  $("tabla-seg").innerHTML = `<table><thead><tr><th>${porPais ? t.cSegPais : t.cSegRating}</th><th class="der opcional">${t.cCreditos}</th><th>${t.cAprobados}</th><th class="der">${t.cMora}</th><th class="der">${t.cCambio}</th></tr></thead><tbody>` +
    f.map((x) => `<tr><td>${porPais ? pais(x.clave) : x.clave}</td><td class="der opcional">${n(x.creditos, 0)}</td>
      <td><div class="celda-barra"><span class="pista"><span style="width:${100 * x.aprobados}%"></span></span><span>${n(100 * x.aprobados, 0)}%</span></div></td>
      <td class="der">${n(100 * x.mora, 1)}%</td><td class="der">${s(x.cambio / 1e6, 2)}</td></tr>`).join("") + "</tbody></table>";
}

function tablaReglas(res) {
  const t = tx(), activo = presetActivo();
  const fila = (id, nombre, x, costo, on) => `<tr class="${on ? "activa" : ""}"><td><button class="enlace" ${id ? `data-id="${id}"` : "disabled"} ${on ? 'aria-current="true"' : ""}>${nombre}</button></td>
    <td class="der opcional">${costoTxt(costo)}</td><td class="der">${n(x.aprobadosPct, 1)}%</td><td class="der">${x.moraPct === null ? "-" : `${n(x.moraPct, 1)}%`}</td><td class="der">${s(x.cambio / 1e6, 2)}</td></tr>`;
  const propio = activo ? "" : fila(null, t.presets.propio, res, e.esc.costo, true);
  $("tabla-reglas").innerHTML = `<table><thead><tr><th>${t.cRegla}</th><th class="der opcional">${t.cCosto}</th><th class="der">${t.cAprobados}</th><th class="der">${t.cMoraRegla}</th><th class="der">${t.cCambio}</th></tr></thead><tbody>${propio}` +
    filasPresets.map((x) => fila(x.id, t.presets[x.id], x, x.costo, activo?.id === x.id)).join("") + "</tbody></table>";
}

function pintarSimulador() {
  const t = tx(), c = e.esc;
  pintarControles();
  const r = resultadosActuales();
  const a = lg.aprobar(d, c, meta.paises, meta.ratings);
  const res = lg.resumen(d, a, r);
  $("titular").textContent = t.titular(res, f);
  $("kpis").innerHTML = kpi(t.kAprobados, `${n(res.aprobadosPct, 1)}%`, t.nMonto(n(res.montoPct, 1))) +
    kpi(t.kMora, res.moraPct === null ? "-" : `${n(res.moraPct, 1)}%`, t.nMoraBase(n(res.moraBasePct, 1))) +
    kpi(t.kResultado, n(res.resultado / 1e6, 2), t.nResultado) + kpi(t.kCambio, s(res.cambio / 1e6, 2), t.nCambio);

  const avisos = [];
  const seg = lg.porSegmento(d, a, r, "pais", meta.paises);
  const ceros = seg.filter((x) => x.aprobados === 0 && !c.sinPaises.includes(x.clave)).map((x) => pais(x.clave));
  if (c.regla === "margen" && ceros.length) avisos.push(aviso("aviso", t.avisoPais(ceros.join(", "), costoTxt(c.costo))));
  if (!c.sinPaises.includes("Denmark")) avisos.push(aviso("nota", t.avisoDk));
  $("avisos").innerHTML = avisos.join("");

  const puntos = curvaActual(r), mejor = lg.mejorPunto(puntos);
  $("sub-curva").textContent = c.regla === "pd" ? t.subCurvaPd : t.subCurvaMargen;
  $("nota-curva").textContent = t.notaCurva(n(100 * mejor.corte, 1));
  gr.curva($("g-curva"), { puntos, mejor, tx: t, f, corte: c.regla === "pd" ? c.corte : null, onCorte: c.regla === "pd" ? moverCorte : null });
  tablaSegmentos(a, r);
  tablaReglas(res);
  $("pegado").innerHTML = `<div><span>${t.kAprobados}</span><b>${n(res.aprobadosPct, 1)}%</b></div><div><span>${t.kMora}</span><b>${res.moraPct === null ? "-" : `${n(res.moraPct, 1)}%`}</b></div><div><span>${t.kCambio}</span><b>${s(res.cambio / 1e6, 2)}</b></div>`;
}

function moverCorte(c) {
  if (c === e.esc.corte) return;
  e.esc.corte = c;
  pedirPintar();
}

// ---------------------------------------------------------------- cliente

function pintarCliente() {
  const t = tx(), c = e.cli, { costo, lgd } = e.esc;
  $("c-pais").value = c.pais;
  $("c-rating").value = c.rating;
  if (document.activeElement !== $("c-monto")) $("c-monto").value = c.monto;
  if (document.activeElement !== $("c-ingreso")) $("c-ingreso").value = c.ingreso;
  $("c-tasa").value = 100 * c.tasa;
  $("c-plazo").value = PLAZOS.indexOf(c.plazo);
  pintarDeslizador("c-tasa", "v-tasa", `${n(100 * c.tasa, 1)}%`);
  pintarDeslizador("c-plazo", "v-plazo", `${c.plazo} ${t.meses}`);

  const p = lg.perfil(c), pu = lg.puntuar(sc, p), margen = lg.margenPp(c.tasa, pu.pd, costo, lgd);
  const eq = lg.tasaEquilibrio(sc, c, costo, lgd), aprobado = margen > 0;
  const k = `${n(100 * lgd, 0)}`;
  $("veredicto").innerHTML = `<div class="veredicto ${aprobado ? "bien" : "mal"}">${ICONO[aprobado ? "ok" : "no"]}<div><strong>${aprobado ? t.aprobada : t.rechazada}</strong><span>${t.supuestos(costoTxt(costo), k)}</span></div></div>`;
  const fuera = [];
  if (!sc.paises_entrenamiento.includes(c.pais)) fuera.push(aviso("aviso", t.avisoDominio));
  if (p.carga_pct > meta.carga_p999) fuera.push(aviso("aviso", t.avisoCarga(n(p.carga_pct, 0), n(meta.carga_p999, 0))));
  $("avisos-cliente").innerHTML = fuera.join("");
  $("kpis-cliente").innerHTML = kpi(t.kPuntaje, n(pu.puntos, 0), t.nPuntaje(n(sc.base, 0), sc.pdo)) + kpi(t.kPd, `${n(100 * pu.pd, 1)}%`, t.nPd) +
    kpi(t.kMargen, `${s(margen, 1)} pp`, t.nMargen) + kpi(t.kEquilibrio, eq === null ? t.nada : `${n(100 * eq, 1)}%`, eq === null ? t.sinEquilibrio : t.nEquilibrio);

  const filas = pu.detalle.map((x) => ({ nombre: t.variables[x.variable], puntos: x.puntos })).sort((a, b) => b.puntos - a.puntos);
  const restan = filas.filter((x) => x.puntos < -0.05).slice(-2).reverse().map((x) => `${x.nombre} (${s(x.puntos, 0)})`).join(e.L === "es" ? " y " : " and ");
  $("sub-aportes").textContent = t.subAportes(n(p.cuota, 0), n(p.carga_pct, 1), restan);
  gr.aportes($("g-aportes"), { filas, f, tx: t });
  $("sub-posicion").textContent = t.subPosicion(n(100 * lg.percentilPd(d, pu.pd), 0));
  gr.posicion($("g-posicion"), { hist, pd: pu.pd, f, tx: t });
}

// ---------------------------------------------------------------- pintado y eventos

let pendiente = false;
function pedirPintar() {
  if (pendiente) return;
  pendiente = true;
  requestAnimationFrame(() => {
    pendiente = false;
    pintar();
  });
}

function pintar() {
  if (!d) return;
  if (e.tab === "corte") pintarSimulador();
  if (e.tab === "cliente") pintarCliente();
}

function irA(tab, foco = false) {
  e.tab = tab;
  for (const x of ["corte", "cliente", "metodo"]) {
    const on = x === tab;
    $(`panel-${x}`).hidden = !on;
    $(`tab-${x}`).setAttribute("aria-selected", on);
    $(`tab-${x}`).tabIndex = on ? 0 : -1;
  }
  document.body.classList.toggle("con-pegado", tab === "corte");
  if (foco) $(`tab-${tab}`).focus();
  pintar();
  window.scrollTo({ top: 0 });
}

function alternar(lista, v) {
  const i = lista.indexOf(v);
  if (i >= 0) lista.splice(i, 1);
  else lista.push(v);
}

function enlaceEscenario() {
  const c = e.esc, q = new URLSearchParams({ r: c.regla, c: c.corte, k: c.costo, l: c.lgd });
  if (c.sinPaises.length) q.set("xp", c.sinPaises.join());
  if (c.sinRatings.length) q.set("xr", c.sinRatings.join());
  return `${location.origin}${location.pathname}?lang=${e.L}#${q}`;
}

function leerEscenario() {
  const q = new URLSearchParams(location.hash.slice(1));
  const num = (k, a, b) => {
    const v = Number(q.get(k));
    return q.has(k) && Number.isFinite(v) ? Math.min(b, Math.max(a, v)) : null;
  };
  const lista = (k, validos) => (q.get(k) ?? "").split(",").filter((x) => validos.includes(x));
  if (!q.has("r")) return false;
  e.esc = { regla: q.get("r") === "margen" ? "margen" : "pd", corte: num("c", 0.01, 0.4) ?? 0.2, costo: num("k", 0, 20) ?? meta.costo, lgd: num("l", 0.3, 0.9) ?? meta.lgd,
            sinPaises: lista("xp", meta.paises), sinRatings: lista("xr", meta.ratings) };
  return true;
}

let brindisId;
function brindis(texto) {
  const b = $("brindis");
  b.textContent = texto;
  b.classList.add("visible");
  clearTimeout(brindisId);
  brindisId = setTimeout(() => b.classList.remove("visible"), 2200);
}

function eventos() {
  ["corte", "cliente", "metodo"].forEach((x) => $(`tab-${x}`).addEventListener("click", () => irA(x)));
  document.querySelector(".pestanas").addEventListener("keydown", (ev) => {
    const orden = ["corte", "cliente", "metodo"], i = orden.indexOf(e.tab);
    if (ev.key === "ArrowRight") irA(orden[(i + 1) % 3], true);
    if (ev.key === "ArrowLeft") irA(orden[(i + 2) % 3], true);
  });
  for (const id of ["es", "en"]) {
    $(id).addEventListener("click", () => {
      e.L = id;
      history.replaceState(null, "", `?lang=${id}${location.hash}`);
      aplicarTextos();
      pintar();
    });
  }
  $("tema").addEventListener("click", () => {
    const raiz = document.documentElement;
    const oscuro = raiz.dataset.theme ? raiz.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    raiz.dataset.theme = oscuro ? "light" : "dark";
    try { localStorage.setItem("tema", raiz.dataset.theme); } catch { /* sin almacenamiento el tema dura lo que la visita */ }
  });
  const segmentado = (id, fn) => {
    const g = $(id);
    g.addEventListener("click", (ev) => { const b = ev.target.closest("button"); if (b) fn(b.dataset.v); });
    g.addEventListener("keydown", (ev) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(ev.key)) return;
      ev.preventDefault();
      const bs = [...g.querySelectorAll("button")], otro = bs.find((b) => b.getAttribute("aria-checked") !== "true");
      fn(otro.dataset.v);
      otro.focus();
    });
  };
  segmentado("regla", (v) => { e.esc.regla = v; pintar(); });
  segmentado("segmento", (v) => { e.segmento = v; pintar(); });
  $("corte").addEventListener("input", (ev) => { e.esc.corte = Number(ev.target.value) / 100; pedirPintar(); });
  $("costo").addEventListener("input", (ev) => { e.esc.costo = Number(ev.target.value); pedirPintar(); });
  $("lgd").addEventListener("input", (ev) => { e.esc.lgd = Math.round(Number(ev.target.value)) / 100; pedirPintar(); });
  const conPreset = (cont) => cont.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-id]");
    if (b) aplicarPreset(presets.find((p) => p.id === b.dataset.id));
  });
  conPreset($("atajos"));
  conPreset($("tabla-reglas"));
  $("f-paises").addEventListener("click", (ev) => { const b = ev.target.closest("[data-v]"); if (b) { alternar(e.esc.sinPaises, b.dataset.v); pintar(); } });
  $("f-ratings").addEventListener("click", (ev) => { const b = ev.target.closest("[data-v]"); if (b) { alternar(e.esc.sinRatings, b.dataset.v); pintar(); } });
  $("reiniciar").addEventListener("click", () => aplicarPreset(presets.find((p) => p.id === "ks")));
  $("compartir").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(enlaceEscenario());
      brindis(tx().copiado);
    } catch {
      brindis(tx().sinCopiar);
    }
  });
  $("c-pais").addEventListener("change", (ev) => { e.cli.pais = ev.target.value; pintar(); });
  $("c-rating").addEventListener("change", (ev) => { e.cli.rating = ev.target.value; pintar(); });
  for (const [id, k] of [["c-monto", "monto"], ["c-ingreso", "ingreso"]]) {
    const x = $(id);
    x.addEventListener("input", () => {
      const v = Number(x.value);
      if (x.value !== "" && v >= Number(x.min) && v <= Number(x.max)) { e.cli[k] = v; pedirPintar(); }
    });
    x.addEventListener("blur", () => { x.value = e.cli[k]; });
  }
  $("c-tasa").addEventListener("input", (ev) => { e.cli.tasa = Number(ev.target.value) / 100; pedirPintar(); });
  $("c-plazo").addEventListener("input", (ev) => { e.cli.plazo = PLAZOS[Number(ev.target.value)]; pedirPintar(); });
}

async function iniciar() {
  aplicarTextos();
  irA("corte");
  eventos();
  if (typeof DecompressionStream === "undefined") throw new Error(tx().errorNavegador);
  const [rm, rb] = await Promise.all([fetch("datos/app.json"), fetch("datos/prueba.bin.gz")]);
  if (!rm.ok || !rb.ok) throw new Error(tx().errorDatos);
  const [m, buf] = await Promise.all([rm.json(), rb.arrayBuffer()]);
  meta = m;
  sc = meta.scorecard;
  d = lg.decodificar(await lg.descomprimir(buf), meta.n);
  hist = lg.histogramaPd(d);
  armarPresets();
  e.esc = { ...presets.find((p) => p.id === "ks").esc };
  leerEscenario();
  aplicarTextos();
  pintar();
  document.body.classList.add("listo");
}

iniciar().catch((err) => {
  console.error(err);
  const x = $("error");
  x.textContent = err.message && Object.values(tx()).includes(err.message) ? err.message : tx().errorDatos;
  x.hidden = false;
});
