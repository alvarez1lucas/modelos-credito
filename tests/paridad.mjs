// Corre app/logica.js con los escenarios que llegan por stdin y escribe los resultados en JSON.
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import * as lg from "../app/logica.js";

const dir = fileURLToPath(new URL("../app/datos/", import.meta.url));
const meta = JSON.parse(readFileSync(dir + "app.json", "utf8"));
const b = gunzipSync(readFileSync(dir + "prueba.bin.gz"));
const d = lg.decodificar(b.buffer.slice(b.byteOffset, b.byteOffset + b.length), meta.n);
const { escenarios, clientes } = JSON.parse(readFileSync(0, "utf8"));

const salida = {
  cortes: lg.GRILLA_CORTES,
  escenarios: escenarios.map((e) => {
    const r = lg.resultados(d, e.costo, e.lgd);
    const a = lg.aprobar(d, e, meta.paises, meta.ratings);
    return {
      resumen: lg.resumen(d, a, r),
      curva: lg.curva(d, r, e, meta.paises, meta.ratings).map((p) => p.resultado),
      pais: lg.porSegmento(d, a, r, "pais", meta.paises),
      rating: lg.porSegmento(d, a, r, "rating", meta.ratings),
    };
  }),
  clientes: clientes.map((c) => {
    const p = lg.perfil(c);
    const pu = lg.puntuar(meta.scorecard, p);
    return { ...pu, cuota: p.cuota, percentil: lg.percentilPd(d, pu.pd), equilibrio: lg.tasaEquilibrio(meta.scorecard, c, meta.costo, meta.lgd) };
  }),
  histograma: lg.histogramaPd(d),
};
process.stdout.write(JSON.stringify(salida));
