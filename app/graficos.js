// Gráficos en SVG, sin librerías: la app abre rápido y los colores siguen el tema con variables de CSS.

function escalones(a, b, n = 5) {
  const crudo = (b - a) / n || 1;
  const m = 10 ** Math.floor(Math.log10(crudo));
  const r = crudo / m;
  const paso = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * m;
  const lo = Math.floor(a / paso) * paso;
  const hi = Math.ceil(b / paso) * paso;
  const marcas = [];
  for (let i = 0; i <= Math.round((hi - lo) / paso); i++) marcas.push(lo + i * paso);
  return { lo, hi, marcas, decimales: Math.max(0, -Math.floor(Math.log10(paso) + 1e-9)) };
}

/** Prepara el contenedor una sola vez: vuelve a dibujar al cambiar de ancho y deja un tooltip listo. */
function preparar(el, dibujar) {
  el.dibujar = dibujar;
  if (el.lienzo) return;
  el.lienzo = document.createElement("div");
  el.tip = document.createElement("div");
  el.tip.className = "tip";
  el.tip.hidden = true;
  el.append(el.lienzo, el.tip);
  let ancho = 0;
  new ResizeObserver(([e]) => {
    if (e.contentRect.width && e.contentRect.width !== ancho) {
      ancho = e.contentRect.width;
      el.dibujar();
    }
  }).observe(el);
}

function mostrarTip(el, x, y, valor, detalle) {
  const t = el.tip;
  t.replaceChildren();
  const b = document.createElement("b");
  b.textContent = valor;
  const s = document.createElement("span");
  s.textContent = detalle;
  t.append(b, s);
  t.hidden = false;
  const a = el.clientWidth;
  const w = t.offsetWidth;
  t.style.left = `${Math.max(0, Math.min(a - w, x + (x + w + 16 > a ? -w - 12 : 12)))}px`;
  t.style.top = `${Math.max(0, y - t.offsetHeight - 10)}px`;
}

export function curva(el, datos) {
  preparar(el, () => dibujarCurva(el));
  el.datos = datos;
  if (!el.dataset.listo) {
    el.dataset.listo = "1";
    let arrastrando = false;
    const punto = (ev) => {
      const { puntos, g } = el.datos;
      const x = ev.clientX - el.getBoundingClientRect().left;
      const corte = (x - g.l) / g.w * 0.4;
      const i = Math.max(0, Math.min(puntos.length - 1, Math.round((corte - puntos[0].corte) / 0.0025)));
      return { i, p: puntos[i] };
    };
    const hover = (ev) => {
      const { i, p } = punto(ev);
      const { g, tx, f, onCorte } = el.datos;
      const cruz = el.querySelector(".cruz");
      cruz.setAttribute("x1", g.x(p.corte));
      cruz.setAttribute("x2", g.x(p.corte));
      cruz.style.opacity = 1;
      const c = el.querySelector(".punto-cruz");
      c.setAttribute("cx", g.x(p.corte));
      c.setAttribute("cy", g.y(p.resultado / 1e6));
      c.style.opacity = 1;
      mostrarTip(el, g.x(p.corte), g.y(p.resultado / 1e6), `${f.n(p.resultado / 1e6, 2)} M€`, tx.tipCurva(f.n(100 * p.corte, 2), f.n(p.aprobadosPct, 1)));
      if (arrastrando && onCorte) onCorte(p.corte);
      return i;
    };
    const salir = () => {
      el.tip.hidden = true;
      el.querySelectorAll(".cruz,.punto-cruz").forEach((n) => (n.style.opacity = 0));
    };
    el.addEventListener("pointerdown", (ev) => {
      if (!el.datos.onCorte) return;
      arrastrando = true;
      el.setPointerCapture(ev.pointerId);
      hover(ev);
    });
    el.addEventListener("pointermove", hover);
    el.addEventListener("pointerup", (ev) => {
      arrastrando = false;
      if (ev.pointerType !== "mouse") salir();
    });
    el.addEventListener("pointercancel", () => { arrastrando = false; salir(); });
    el.addEventListener("pointerleave", () => { if (!arrastrando) salir(); });
  }
  el.dibujar();
}

function dibujarCurva(el) {
  const W = el.clientWidth;
  if (!W) return;
  const { puntos, corte, mejor, tx, f, onCorte } = el.datos;
  const H = 320, m = { l: 46, r: 14, t: 34, b: 46 };
  const w = W - m.l - m.r, h = H - m.t - m.b;
  const vals = puntos.map((p) => p.resultado / 1e6);
  const { lo, hi, marcas, decimales } = escalones(Math.min(0, ...vals), Math.max(...vals));
  const x = (c) => m.l + (c / 0.4) * w;
  const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * h;
  el.datos.g = { x, y, l: m.l, w };
  el.classList.toggle("arrastrable", !!onCorte);

  const grilla = marcas.map((v) => `<line class="${Math.abs(v) < 1e-9 ? "base" : "rejilla-l"}" x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end">${f.n(v, decimales)}</text>`).join("");
  const pasoX = W < 480 ? 10 : 5;
  const ticksX = [];
  for (let c = 0; c <= 40; c += pasoX) ticksX.push(`<text class="tick" x="${x(c / 100)}" y="${H - m.b + 18}" text-anchor="middle">${c}</text>`);
  const linea = puntos.map((p, i) => `${i ? "L" : "M"}${x(p.corte).toFixed(1)} ${y(p.resultado / 1e6).toFixed(1)}`).join("");

  let tu = "";
  if (corte !== null) {
    const v = puntos.reduce((a, p) => (Math.abs(p.corte - corte) < Math.abs(a.corte - corte) ? p : a));
    const xc = x(corte);
    const derecha = xc + 76 < W;
    tu = `<line class="marca-corte" x1="${xc}" x2="${xc}" y1="4" y2="${H - m.b}"/><circle class="punto-corte" cx="${xc}" cy="${y(v.resultado / 1e6)}" r="5"/>
      <text class="etq-corte" x="${xc + (derecha ? 6 : -6)}" y="14" text-anchor="${derecha ? "start" : "end"}">${tx.tuCorte}</text>`;
  }
  const xm = x(mejor.corte), ym = y(mejor.resultado / 1e6);
  const ancla = xm < 70 ? "start" : xm > W - 70 ? "end" : "middle";
  const max = `<circle class="punto-max" cx="${xm}" cy="${ym}" r="4"/><text class="etq-max" x="${xm}" y="${ym - 10}" text-anchor="${ancla}">${tx.maximo}: ${f.n(mejor.resultado / 1e6, 2)}</text>`;

  el.lienzo.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${tx.tituloCurva}">
    ${grilla}${ticksX.join("")}
    <text class="eje" x="${m.l + w / 2}" y="${H - 8}" text-anchor="middle">${tx.ejeCorte}</text>
    <text class="eje" transform="translate(12 ${m.t + h / 2}) rotate(-90)" text-anchor="middle">${tx.ejeResultado}</text>
    <path class="linea" d="${linea}"/>${max}${tu}
    <line class="cruz" x1="0" x2="0" y1="${m.t}" y2="${H - m.b}"/><circle class="punto-cruz" r="4"/>
  </svg>`;
}

export function aportes(el, datos) {
  preparar(el, () => dibujarAportes(el));
  el.datos = datos;
  el.dibujar();
}

function dibujarAportes(el) {
  const W = el.clientWidth;
  if (!W) return;
  const { filas, f, tx } = el.datos;
  const fila = 34, etq = W < 480 ? 104 : 136, H = filas.length * fila + 8;
  const tope = Math.max(...filas.map((r) => Math.abs(r.puntos)), 1) * 1.32;
  const ini = etq, ancho = W - etq - 6;
  const x = (v) => ini + ((v + tope) / (2 * tope)) * ancho;
  const cuerpo = filas.map((r, i) => {
    const y = 4 + i * fila, a = x(Math.min(0, r.puntos)), b = x(Math.max(0, r.puntos));
    const pos = r.puntos >= 0;
    return `<text class="etq-fila" x="0" y="${y + 21}">${r.nombre}</text>
      <rect class="${pos ? "barra-a" : "barra-b"}" x="${a}" y="${y + 8}" width="${Math.max(b - a, 1)}" height="18" rx="4"/>
      <text class="valor" x="${pos ? b + 6 : a - 6}" y="${y + 21}" text-anchor="${pos ? "start" : "end"}">${f.s(r.puntos, 1)}</text>`;
  }).join("");
  el.lienzo.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${tx.tituloAportes}">
    <line class="base" x1="${x(0)}" x2="${x(0)}" y1="0" y2="${H}"/>${cuerpo}</svg>`;
}

export function posicion(el, datos) {
  preparar(el, () => dibujarPosicion(el));
  el.datos = datos;
  if (!el.dataset.listo) {
    el.dataset.listo = "1";
    el.addEventListener("pointermove", (ev) => {
      const { hist, g, f, tx } = el.datos;
      const x = ev.clientX - el.getBoundingClientRect().left;
      const i = Math.max(0, Math.min(hist.length - 1, Math.floor((x - g.l) / g.b)));
      el.querySelectorAll(".hist").forEach((n, k) => n.classList.toggle("activa", k === i));
      mostrarTip(el, g.l + (i + 0.5) * g.b, g.y(hist[i]), f.n(hist[i], 0), tx.tipHist(f.n(i, 0), f.n(i + 1, 0), f.n(hist[i], 0)));
    });
    el.addEventListener("pointerleave", () => {
      el.tip.hidden = true;
      el.querySelectorAll(".hist.activa").forEach((n) => n.classList.remove("activa"));
    });
  }
  el.dibujar();
}

function dibujarPosicion(el) {
  const W = el.clientWidth;
  if (!W) return;
  const { hist, pd, tx } = el.datos;
  const H = 200, m = { l: 4, r: 4, t: 26, b: 42 };
  const w = W - m.l - m.r, h = H - m.t - m.b, b = w / hist.length, tope = Math.max(...hist);
  const y = (n) => m.t + (1 - n / tope) * h;
  el.datos.g = { l: m.l, b, y };
  const barras = hist.map((n, i) => `<rect class="hist" x="${m.l + i * b + 0.5}" y="${y(n)}" width="${Math.max(b - 1, 1)}" height="${Math.max(H - m.b - y(n), n ? 1 : 0)}" rx="1.5"/>`).join("");
  const ticks = [0, 10, 20, 30, 40].map((c) => `<text class="tick" x="${Math.max(m.l + 5, Math.min(W - m.r - 8, m.l + (c / 40) * w))}" y="${H - m.b + 18}" text-anchor="middle">${c}</text>`).join("");
  const xp = m.l + (Math.min(pd, 0.4) / 0.4) * w;
  const derecha = xp + 96 < W;
  el.lienzo.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${tx.tituloPosicion}">
    ${barras}<line class="base" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>${ticks}
    <text class="eje" x="${W / 2}" y="${H - 6}" text-anchor="middle">${tx.ejePd}</text>
    <line class="marca-corte" x1="${xp}" x2="${xp}" y1="${m.t - 8}" y2="${H - m.b}"/>
    <text class="etq-corte" x="${xp + (derecha ? 6 : -6)}" y="${m.t - 6}" text-anchor="${derecha ? "start" : "end"}">${tx.esteCliente}</text>
  </svg>`;
}
