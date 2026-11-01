// Cálculos de la app, sin nada del navegador: Node los prueba contra la versión en Python.

export const GRILLA_CORTES = Array.from({ length: 157 }, (_, i) => (100 + 25 * i) / 10000);

export async function descomprimir(buf) {
  const b = new Uint8Array(buf);
  if (b[0] !== 0x1f || b[1] !== 0x8b) return buf; // el servidor ya lo descomprimió
  const flujo = new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Response(flujo).arrayBuffer();
}

/** Columnas en binario, ordenadas por PD: tres float32 y tres uint8, little-endian. */
export function decodificar(buf, n) {
  const d = { n };
  let i = 0;
  for (const c of ["pd", "monto", "tasa"]) {
    d[c] = new Float32Array(buf, i, n);
    i += 4 * n;
  }
  for (const c of ["pais", "rating", "malo"]) {
    d[c] = new Uint8Array(buf, i, n);
    i += n;
  }
  return d;
}

export function cuota(monto, tasa, plazo) {
  const i = tasa / 12;
  return (monto * i) / (1 - (1 + i) ** -plazo);
}

function woe(v, valor) {
  if (v.cortes === null) {
    const i = v.categorias.indexOf(String(valor));
    return i >= 0 ? v.woe[i] : 0;
  }
  const i = v.cortes.findIndex((c) => (c === null ? Infinity : c) >= valor);
  return v.woe[i < 0 ? v.woe.length - 1 : Math.min(i, v.woe.length - 1)];
}

/** Puntaje y PD de un cliente, con lo que aporta cada variable. */
export function puntuar(sc, cliente) {
  const f = sc.pdo / Math.LN2;
  let logOdds = sc.intercepto;
  let puntos = sc.base;
  const detalle = [];
  for (const v of sc.variables) {
    const w = woe(v, cliente[v.variable]);
    logOdds += v.coef * w;
    puntos += -f * v.coef * w;
    detalle.push({ variable: v.variable, puntos: -f * v.coef * w });
  }
  const calibrado = sc.calibrador.a + sc.calibrador.b * logOdds;
  return { pd: 1 / (1 + Math.exp(-calibrado)), puntos, detalle };
}

/** Agrega al cliente lo que se deriva de sus datos: la cuota y su peso sobre el ingreso. */
export function perfil(c) {
  const q = cuota(c.monto, c.tasa, c.plazo);
  return { ...c, cuota: q, carga_pct: (100 * q) / c.ingreso };
}

export const margenPp = (tasa, pd, costo, lgd) => 100 * (tasa - costo / 100 - pd * lgd);

/** Tasa más baja que aprueba al cliente. La tasa también mueve la PD y la carga: por eso se recorre en vez de despejar. */
export function tasaEquilibrio(sc, cliente, costo, lgd, desde = 0.05, hasta = 0.35) {
  for (let i = Math.round(desde * 1000); i <= Math.round(hasta * 1000); i++) {
    const tasa = i / 1000;
    if (margenPp(tasa, puntuar(sc, perfil({ ...cliente, tasa })).pd, costo, lgd) > 0) return tasa;
  }
  return null;
}

/** Resultado del primer año de cada crédito: monto × (tasa - costo) - evento × LGD × monto. */
export function resultados(d, costo, lgd) {
  const r = new Float64Array(d.n);
  const k = costo / 100;
  for (let i = 0; i < d.n; i++) r[i] = d.monto[i] * (d.tasa[i] - k) - d.malo[i] * lgd * d.monto[i];
  return r;
}

function excluidos(lista, claves) {
  const m = new Uint8Array(claves.length);
  lista.forEach((x) => {
    const i = claves.indexOf(x);
    if (i >= 0) m[i] = 1;
  });
  return m;
}

/** `regla` 'pd' aprueba hasta una PD fija; 'margen' aprueba si PD × LGD < tasa - costo. */
export function aprobar(d, esc, paises, ratings) {
  const a = new Uint8Array(d.n);
  const xp = excluidos(esc.sinPaises, paises);
  const xr = excluidos(esc.sinRatings, ratings);
  const k = esc.costo / 100;
  for (let i = 0; i < d.n; i++) {
    const base = esc.regla === "pd" ? d.pd[i] <= esc.corte : d.pd[i] * esc.lgd < d.tasa[i] - k;
    a[i] = base && !xp[d.pais[i]] && !xr[d.rating[i]] ? 1 : 0;
  }
  return a;
}

export function resumen(d, a, r) {
  let ap = 0, malosAp = 0, malos = 0, montoAp = 0, monto = 0, res = 0, cambio = 0;
  for (let i = 0; i < d.n; i++) {
    malos += d.malo[i];
    monto += d.monto[i];
    if (a[i]) {
      ap++;
      malosAp += d.malo[i];
      montoAp += d.monto[i];
      res += r[i];
    } else cambio -= r[i];
  }
  const rechazados = d.n - ap;
  const malosEvitados = malos - malosAp;
  const buenosPerdidos = rechazados - malosEvitados;
  return {
    aprobadosPct: (100 * ap) / d.n, montoPct: (100 * montoAp) / monto, moraPct: ap ? (100 * malosAp) / ap : null, moraBasePct: (100 * malos) / d.n,
    resultado: res, cambio, rechazados, malosEvitados, buenosPerdidos, buenosPorMalo: malosEvitados ? buenosPerdidos / malosEvitados : null,
  };
}

/** Resultado al subir el corte de PD, sin lo excluido. Los créditos llegan ordenados por PD. */
export function curva(d, r, esc, paises, ratings) {
  const xp = excluidos(esc.sinPaises, paises);
  const xr = excluidos(esc.sinRatings, ratings);
  const puntos = [];
  let i = 0, suma = 0, ap = 0;
  for (const corte of GRILLA_CORTES) {
    for (; i < d.n && d.pd[i] <= corte; i++) {
      if (!xp[d.pais[i]] && !xr[d.rating[i]]) {
        suma += r[i];
        ap++;
      }
    }
    puntos.push({ corte, resultado: suma, aprobadosPct: (100 * ap) / d.n });
  }
  return puntos;
}

export function mejorPunto(puntos) {
  return puntos.reduce((m, p) => (p.resultado > m.resultado ? p : m), puntos[0]);
}

export function porSegmento(d, a, r, campo, claves) {
  const f = claves.map((clave) => ({ clave, creditos: 0, ap: 0, malos: 0, cambio: 0 }));
  for (let i = 0; i < d.n; i++) {
    const s = f[d[campo][i]];
    s.creditos++;
    s.malos += d.malo[i];
    if (a[i]) s.ap++;
    else s.cambio -= r[i];
  }
  return f.map((s) => ({ clave: s.clave, creditos: s.creditos, aprobados: s.ap / s.creditos, mora: s.malos / s.creditos, cambio: s.cambio }));
}

/** Parte de la cartera con una PD menor. */
export function percentilPd(d, pd) {
  let a = 0, b = d.n;
  while (a < b) {
    const m = (a + b) >> 1;
    if (d.pd[m] < pd) a = m + 1;
    else b = m;
  }
  return a / d.n;
}

export function histogramaPd(d, tope = 0.4, tramos = 40) {
  const h = new Array(tramos).fill(0);
  for (let i = 0; i < d.n; i++) h[Math.min(Math.floor((d.pd[i] / tope) * tramos), tramos - 1)]++;
  return h;
}
