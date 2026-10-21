/* Riesgo de ejecucion: resultados del modelo (oro.ejecucion), escenarios en vivo y supuestos editables. */

const X = {
  d: null,            // GET /api/ejecucion
  c: null,            // GET /api/cronograma
  paqCron: null,      // paquete cuyas actividades se muestran
  proy: null,         // proyecto seleccionado
  paq: null,          // paquete seleccionado (o null: todo el proyecto)
  sup: null,          // supuestos en edicion
  esc: { factor: { clima: 1, seguridad_fisica: 1, social_comunidad: 1, ambiental: 1, contractual: 1 }, sinControles: false },
  sim: null,          // resultado del escenario
  charts: {},
  t: null,
};

const LETRAS = ['A', 'B', 'C', 'D', 'E'];
const DIMS = ['PE', 'EC', 'MA', 'CL', 'IM'];
const CATS = ['seguridad_fisica', 'climatico', 'social_comunidad', 'logistico_acceso', 'ambiental', 'contractual'];
const COVS = {
  tasa_delitos_rel: ['Delitos contra proyectos', (c) => `${fmt(c.tasa_delitos_100k, 1)} por 100.000 hab.`],
  emergencias_rel: ['Emergencias UNGRD', (c) => `${fmt(c.emergencias_por_ano, 1)} al año`],
  anomalia_lluvia: ['Lluvia fuera de lo normal', (c) => `${fmt(c.anomalia_lluvia_pct, 0)} % de desviación (CHIRPS)`],
  en_resguardo: ['Dentro de resguardo', (c) => `${fmt(c.pct_en_resguardo, 0)} % del paquete`],
  ipm_rel: ['Pobreza multidimensional', (c) => `IPM ${fmt(c.ipm, 1)} %`],
  pdet: ['Municipio PDET', (c) => (c.pdet ? 'sí' : 'no')],
  vias_tiempo_seco: ['Vías solo en tiempo seco', (c) => `${fmt(c.vias_tiempo_seco_pct, 0)} % de los km cercanos`],
};
const clon = (x) => JSON.parse(JSON.stringify(x));
const fmt = (v, d = 0) => (v == null || Number.isNaN(Number(v)) ? '-' : Number(v).toLocaleString('es-CO', { maximumFractionDigits: d, minimumFractionDigits: d }));
const usd = (v) => (v == null ? '-' : v >= 1e6 ? `USD ${fmt(v / 1e6, 1)} M` : `USD ${fmt(v / 1e3, 0)} mil`);
const nivelIre = (v) => (v >= 75 ? 'critico' : v >= 50 ? 'alto' : v >= 25 ? 'medio' : 'bajo');
const nombreProy = (id) => `Proyecto ${Number(String(id).split('-')[1])}`;
const catCorto = (c) => ui.cat(c).corto;

// multiplicador territorial de una categoria para un paquete (misma formula que modelo/ejecucion.py)
function multiplicador(cat, p, cfg) {
  const betas = (cfg.covariables || {})[cat] || {};
  const s = Object.entries(betas).reduce((a, [k, b]) => a + b * (Number(p[`z_${k}`]) || 0), 0);
  const m = Number(cfg.multiplicador_max || 3);
  return Math.min(m, Math.max(1 / m, Math.exp(Number(cfg.gamma ?? 0.5) * s)));
}

// ---------------------------------------------------------------------------
// Proyectos
// ---------------------------------------------------------------------------

function renderProyectos() {
  const cont = document.getElementById('proyectos');
  const tol = X.d.resumen.metadata.tolerancia_proyecto;
  cont.innerHTML = X.d.proyectos.map((p) => {
    const lv = nivelIre(p.ire);
    return `<section class="card span-4 proy${p.id_proyecto === X.proy ? ' sel' : ''}" data-id="${p.id_proyecto}">
      <div class="card-head">
        <div class="card-icon"><i data-lucide="briefcase"></i></div>
        <div class="grow"><div class="card-title">${nombreProy(p.id_proyecto)}</div>
          <div class="card-sub">${X.d.paquetes.filter((q) => q.id_proyecto === p.id_proyecto).length} paquetes · tolerancia ${tol} días</div></div>
        <span class="lvl ${lv}">${ui.NIVEL[lv]}</span>
      </div>
      <div class="fila">
        <div class="ring" style="--p:${p.ire};--c:var(--lvl-${lv});--size:92px"><div><div class="num md">${fmt(p.ire, 0)}</div><div class="lbl">IRE</div></div></div>
        <div class="kpis">
          <div class="kpi"><div class="l">Atraso esperado</div><div class="v">${fmt(p.atraso_media, 0)} <small>días</small></div></div>
          <div class="kpi"><div class="l">Atraso P90</div><div class="v">${fmt(p.atraso_p90, 0)} <small>días</small></div></div>
          <div class="kpi"><div class="l">Sobrecosto P90</div><div class="v">${usd(p.costo_p90).replace('USD ', '')} <small>USD</small></div></div>
          <div class="kpi"><div class="l">Sin atraso</div><div class="v">${fmt(p.prob_sin_atraso * 100, 0)} <small>%</small></div></div>
        </div>
      </div>
      <div class="hist"><canvas id="h-${p.id_proyecto}"></canvas></div>
      <div class="pie">Probabilidad de cada atraso (días) en ${fmt(X.d.resumen.metadata.simulaciones)} escenarios · naranja: pasa la tolerancia</div>
    </section>`;
  }).join('');
  X.d.proyectos.forEach((p) => histogramaMini(p.id_proyecto, tol));
  cont.querySelectorAll('.proy').forEach((c) => c.addEventListener('click', () => { X.proy = c.dataset.id; X.paq = null; renderTodo(); }));
}

function histogramaMini(id, tol) {
  const h = X.d.resumen.histogramas[id].atraso;
  const centros = h.bordes.slice(0, -1).map((b, i) => (b + h.bordes[i + 1]) / 2);
  X.charts[id]?.destroy();
  X.charts[id] = new Chart(document.getElementById(`h-${id}`), {
    type: 'bar',
    data: { labels: centros.map((c) => fmt(c, 0)), datasets: [{ data: h.frecuencia.map((f) => f * 100), backgroundColor: centros.map((c) => (c > tol ? ui.css('--lvl-alto') : ui.css('--green-300'))), borderRadius: 3, barPercentage: 1, categoryPercentage: 0.92 }] },
    options: { maintainAspectRatio: false, animation: false, plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (i) => `~${i[0].label} días`, label: (c) => `${fmt(c.raw, 1)} % de los escenarios` } } },
      scales: { x: { display: false }, y: { display: false, beginAtZero: true } } },
  });
}

// ---------------------------------------------------------------------------
// Paquetes y detalle
// ---------------------------------------------------------------------------

function renderPaquetes() {
  const filas = X.d.paquetes.filter((p) => p.id_proyecto === X.proy).sort((a, b) => b.ire - a.ire || b.atraso_media - a.atraso_media);
  const max = Math.max(1, ...filas.map((p) => p.atraso_media));
  document.getElementById('sub-paquetes').textContent = `${nombreProy(X.proy)} · clic en un paquete para ver por qué · IRE = probabilidad de pasar la holgura + ${X.d.resumen.metadata.tolerancia_paquete} días`;
  document.querySelector('#tabla-paquetes tbody').innerHTML = filas.map((p) => {
    const lv = nivelIre(p.ire);
    const fut = Math.max(0, p.atraso_media - p.atraso_consumido);
    return `<tr data-id="${p.id_paquete}" class="${p.id_paquete === X.paq ? 'sel' : ''}">
      <td><div class="cell-main"><span class="tile" style="background:var(--green-50);color:var(--green-700)"><i data-lucide="hexagon"></i></span>
        <div><div class="t">${ui.nombreCorto(p.nombre)}</div><div class="s">${p.municipio || ''}${p.ruta_critica ? ' · ruta crítica' : ''}</div></div></div></td>
      <td class="ink-2">${fmt(p.meses_restantes, 1)} meses</td>
      <td class="ink-2">${fmt(p.holgura_dias, 0)} d</td>
      <td class="atr"><b>${fmt(p.atraso_media, 0)}</b> d <span class="sub">· P90 ${fmt(p.atraso_p90, 0)}</span>
        <div class="barra-atr" title="Gris: ya consumido (${fmt(p.atraso_consumido, 0)} d) · naranja: por venir (${fmt(fut, 0)} d)"><span class="c" style="width:${(p.atraso_consumido / max) * 100}%"></span><span class="f" style="width:${(fut / max) * 100}%"></span></div></td>
      <td class="ink-2">${usd(p.costo_p90)}</td>
      <td><span class="lvl ${lv}">${fmt(p.ire, 0)}</span></td>
      <td><span class="ink-2">${p.riesgo_principal || '-'}</span> <span class="sub">${p.categoria_principal ? catCorto(p.categoria_principal) : ''}</span></td>
    </tr>`;
  }).join('');
  document.querySelectorAll('#tabla-paquetes tbody tr').forEach((tr) => tr.addEventListener('click', () => {
    X.paq = X.paq === tr.dataset.id ? null : tr.dataset.id;
    renderPaquetes();
    renderDetalle();
  }));
  ui.icons();
}

function filaRiesgo(r, maxAporte) {
  return `<div class="det-riesgo">
    <span class="t">${ui.ramChip(r.nivel_residual)} ${r.id_riesgo} <span class="sub">${catCorto(r.categoria)}</span></span>
    <b>${fmt(r.atraso_esperado, 1)} d</b>
    <span class="s">${r.actividad ? `Pega en ${r.actividad} · ` : ''}RAM ${r.ram_residual} · ${fmt(r.probabilidad * 100, r.probabilidad < 0.01 ? 2 : 0)} % de ocurrir en ${fmt(r.horizonte_anios * 12, r.horizonte_anios * 12 < 3 ? 1 : 0)} meses · ${fmt(r.dias_por_evento, 0)} días por evento${r.multiplicador_territorial !== 1 ? ` · territorio ×${fmt(r.multiplicador_territorial, 2)}` : ''}</span>
    <div class="meter"><span style="width:${(r.atraso_esperado / maxAporte) * 100}%"></span></div>
  </div>`;
}

function renderDetalle() {
  const cfg = X.d.supuestos;
  const cuerpo = document.getElementById('det-cuerpo');
  if (X.paq) {
    const p = X.d.paquetes.find((q) => q.id_paquete === X.paq);
    const rs = X.d.riesgos.filter((r) => r.id_paquete === X.paq && r.lambda > 0).sort((a, b) => b.atraso_esperado - a.atraso_esperado);
    const mat = X.d.riesgos.filter((r) => r.id_paquete === X.paq && r.consumido_dias > 0);
    document.getElementById('det-titulo').textContent = ui.nombreCorto(p.nombre);
    document.getElementById('det-sub').textContent = `${p.municipio} · ${fmt(p.amenazas_abiertas)} amenazas abiertas · IRE ${fmt(p.ire, 0)}`;
    const terr = CATS.map((c) => [c, multiplicador(c, p, cfg)]).filter(([, m]) => Math.abs(m - 1) > 0.02);
    const covs = Object.entries(COVS).filter(([k]) => Math.abs(Number(p[`z_${k}`]) || 0) > 0.01);
    const max = Math.max(1e-9, ...rs.map((r) => r.atraso_esperado));
    cuerpo.innerHTML = `
      <div class="sec">El territorio multiplica la frecuencia</div>
      <div class="terr">${terr.length ? terr.map(([c, m]) => `<div class="x ${m > 1 ? 'sube' : 'baja'}"><span>${ui.cat(c).label}</span><b>×${fmt(m, 2)}</b></div>`).join('') : '<div class="x"><span>En el promedio de La Guajira</span><b>×1</b></div>'}</div>
      <div class="terr">${covs.map(([k, [n, f]]) => `<div class="x"><span class="sub">${n}</span><span class="sub">${f(p)}</span></div>`).join('')}</div>
      <div class="sec">Los riesgos que más atraso aportan</div>
      ${rs.slice(0, 6).map((r) => filaRiesgo(r, max)).join('') || '<div class="sub">Sin amenazas abiertas</div>'}
      ${mat.length ? `<div class="sec">Ya consumido</div><div class="sub">${mat.length} amenaza(s) materializada(s): ${fmt(p.atraso_consumido, 0)} días y ${usd(p.costo_consumido)} (${fmt((cfg.fraccion_consumida_materializado ?? 0.35) * 100, 0)} % de su consecuencia potencial).</div>` : ''}
      ${p.atraso_evitado_por_controles > 0.05 ? `<div class="ahorro">Los controles registrados evitan unos <b>${fmt(p.atraso_evitado_por_controles, 1)} días</b> de atraso esperado en este paquete.</div>` : ''}`;
  } else {
    const rs = X.d.riesgos.filter((r) => r.id_proyecto === X.proy && r.lambda > 0).sort((a, b) => b.atraso_esperado - a.atraso_esperado);
    const max = Math.max(1e-9, ...rs.map((r) => r.atraso_esperado));
    const evitado = X.d.paquetes.filter((p) => p.id_proyecto === X.proy).reduce((a, p) => a + (p.atraso_evitado_por_controles || 0), 0);
    document.getElementById('det-titulo').textContent = `Por qué: ${nombreProy(X.proy)}`;
    document.getElementById('det-sub').textContent = 'Los riesgos que más atraso esperado aportan';
    cuerpo.innerHTML = `${rs.slice(0, 7).map((r) => filaRiesgo(r, max)).join('') || '<div class="sub">Sin amenazas abiertas</div>'}
      ${evitado > 0.05 ? `<div class="ahorro">Los controles registrados evitan unos <b>${fmt(evitado, 0)} días</b> de atraso esperado en el proyecto.</div>` : ''}`;
  }
  ui.icons();
}

// ---------------------------------------------------------------------------
// Cronograma: avance y fechas por paquete y por actividad
// ---------------------------------------------------------------------------

const fechaCorta = (s) => (s ? new Date(`${String(s).slice(0, 10)}T12:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }) : '-');
const pct = (v, d = 0) => (v == null ? '-' : `${fmt(v * 100, d)} %`);
const ESTADO_ACT = { completada: ['Completada', 'bajo'], en_curso: ['En curso', 'medio'], por_iniciar: ['Por iniciar', ''] };

function barraAvance(real, plan) {
  return `<div class="av" title="Real ${pct(real, 1)} · planeado ${pct(plan, 1)}"><span class="plan" style="width:${(plan || 0) * 100}%"></span><span class="real" style="width:${(real || 0) * 100}%"></span></div>`;
}

function renderCronograma() {
  const c = X.c;
  const card = document.getElementById('cronograma');
  if (!c || !c.disponible) { card.hidden = true; return; }
  card.hidden = false;
  const pr = c.proyectos.find((p) => p.id_proyecto === X.proy);
  const paqs = c.paquetes.filter((p) => p.id_proyecto === X.proy).sort((a, b) => b.atraso_sobre_holgura_dias - a.atraso_sobre_holgura_dias || b.atraso_proyectado_dias - a.atraso_proyectado_dias);
  document.getElementById('sub-cron').textContent = `${nombreProy(X.proy)} · a ${fechaCorta(c.fecha_corte)} · cada actividad pesa en su paquete y cada paquete en el proyecto según su presupuesto`;
  const defineFin = c.paquetes.find((p) => p.id_paquete === pr.paquete_que_define_el_fin);
  const atr = pr.atraso_proyectado_dias;
  document.getElementById('cron-proy').innerHTML = `<div class="cron-kpis">
    <div class="kpi"><div class="l">Avance del proyecto</div><div class="v">${fmt(pr.avance * 100, 1)} <small>% · planeado ${fmt(pr.avance_plan * 100, 1)} %</small></div>${barraAvance(pr.avance, pr.avance_plan)}</div>
    <div class="kpi"><div class="l">Índice de cumplimiento</div><div class="v">${fmt(pr.indice_cumplimiento, 2)} <small>${pr.indice_cumplimiento >= 1 ? 'al día' : 'avance real / planeado'}</small></div></div>
    <div class="kpi"><div class="l">Inicio → fin planeado</div><div class="v sm">${fechaCorta(pr.fecha_inicio_plan)} → ${fechaCorta(pr.fecha_fin_plan)}</div></div>
    <div class="kpi"><div class="l">Fin proyectado</div><div class="v sm">${fechaCorta(pr.fecha_fin_proyectada)} <span class="delta ${atr > 0 ? 'sube' : 'baja'}">${atr > 0 ? '+' : ''}${fmt(atr, 0)} d</span></div>
      <div class="sub">Lo define ${defineFin ? ui.nombreCorto(defineFin.nombre) : '-'}</div></div>
    <div class="kpi"><div class="l">Actividades</div><div class="v">${fmt(pr.n_completadas)} <small>de ${fmt(pr.n_actividades)} completadas · ${fmt(pr.meses_restantes, 1)} meses por ejecutar</small></div></div>
  </div>`;
  if (!X.paqCron || !paqs.some((p) => p.id_paquete === X.paqCron)) X.paqCron = (paqs.find((p) => p.id_paquete === X.paq) || paqs[0])?.id_paquete;
  document.querySelector('#tabla-cron tbody').innerHTML = paqs.map((p) => {
    const sobre = p.atraso_sobre_holgura_dias;
    return `<tr data-id="${p.id_paquete}" class="${p.id_paquete === X.paqCron ? 'sel' : ''}">
      <td><div class="cell-main"><span class="tile" style="background:var(--green-50);color:var(--green-700)"><i data-lucide="hexagon"></i></span>
        <div><div class="t">${ui.nombreCorto(p.nombre)}</div><div class="s">${p.ruta_critica ? 'ruta crítica · ' : ''}pesa ${pct(p.peso_en_proyecto)} del proyecto</div></div></div></td>
      <td><b>${pct(p.avance, 1)}</b>${barraAvance(p.avance, p.avance_plan)}</td>
      <td class="ink-2">${pct(p.avance_plan, 1)}</td>
      <td class="ink-2">${fechaCorta(p.fecha_fin_plan)}</td>
      <td class="ink-2">${fechaCorta(p.fecha_fin_proyectada)}</td>
      <td>${p.atraso_proyectado_dias <= 0 ? '<span class="status">a tiempo</span>' : `<b>+${fmt(p.atraso_proyectado_dias, 0)} d</b> <span class="sub">de ${fmt(p.holgura_dias, 0)} d de holgura</span>${sobre > 0 ? ` <span class="lvl alto">${fmt(sobre, 0)} d de más</span>` : ''}`}</td>
    </tr>`;
  }).join('');
  document.querySelectorAll('#tabla-cron tbody tr').forEach((tr) => tr.addEventListener('click', () => { X.paqCron = tr.dataset.id; renderCronograma(); }));
  renderActividades();
  ui.icons();
}

function renderActividades() {
  const c = X.c;
  const p = c.paquetes.find((q) => q.id_paquete === X.paqCron);
  if (!p) { document.getElementById('cron-act').innerHTML = ''; return; }
  const acts = c.actividades.filter((a) => a.id_paquete === p.id_paquete).sort((a, b) => a.orden - b.orden);
  document.getElementById('cron-act').innerHTML = `<div class="sec">Actividades de ${ui.nombreCorto(p.nombre)}</div>
    <div class="sub">${p.actividad_en_curso ? `En curso: ${p.actividad_en_curso}` : 'Ninguna en curso'}${p.siguiente_actividad ? ` · sigue: ${p.siguiente_actividad}` : ''}</div>
    <ol class="acts">${acts.map((a) => {
      const [txt, lv] = ESTADO_ACT[a.estado] || [a.estado, ''];
      return `<li class="${a.estado}">
        <div class="top"><span class="n">${a.nombre}</span><span class="lvl-soft ${lv}">${txt}</span></div>
        <div class="s">pesa ${pct(a.peso_en_paquete)} del paquete · aporta ${fmt(a.aporte_avance_pp, 1)} de ${fmt(a.aporte_total_pp, 1)} puntos al proyecto</div>
        <div class="av"><span class="real" style="width:${a.avance * 100}%"></span></div>
        <div class="s">Plan ${fechaCorta(a.fecha_inicio_plan)} → ${fechaCorta(a.fecha_fin_plan)} · ${a.estado === 'completada' ? 'terminó' : 'termina'} ${fechaCorta(a.fecha_fin_proyectada)}${a.atraso_proyectado_dias > 0 && a.estado !== 'completada' ? ` <b class="atr-a">(+${fmt(a.atraso_proyectado_dias, 0)} d)</b>` : ''}</div>
      </li>`;
    }).join('')}</ol>`;
}

// ---------------------------------------------------------------------------
// Escenarios
// ---------------------------------------------------------------------------

const CTRL_ESC = [
  ['clima', 'Clima y acceso', 'Frecuencia de riesgos climáticos y logísticos (p. ej. una temporada de lluvias fuerte)'],
  ['seguridad_fisica', 'Seguridad física', 'Frecuencia de extorsión, terrorismo, voladuras...'],
  ['social_comunidad', 'Social y comunidades', 'Bloqueos, paros, consulta previa'],
  ['ambiental', 'Ambiental', 'Incidentes y exigencias ambientales'],
  ['contractual', 'Contractual', 'Incumplimientos de contratistas y proveedores'],
];

function renderControlesEsc() {
  const tol = X.sup.tolerancia_dias_proyecto;
  document.getElementById('esc-ctrls').innerHTML = CTRL_ESC.map(([k, n, s]) => {
    const v = X.esc.factor[k];
    return `<div class="esc-c"><div class="top"><span>${n}</span><b>×${fmt(v, 1)}</b></div>
      <input type="range" class="range" min="0" max="3" step="0.1" value="${v}" data-k="${k}" style="--val:${(v / 3) * 100}">
      <div class="s">${s}</div></div>`;
  }).join('') + `
    <div class="esc-c"><div class="top"><span>Tolerancia de atraso del proyecto</span><b>${tol} días</b></div>
      <input type="range" class="range" min="0" max="120" step="5" value="${tol}" id="esc-tol" style="--val:${(tol / 120) * 100}">
      <div class="s">El IRE del proyecto es la probabilidad de pasarla</div></div>
    <label class="esc-sw"><span class="switch"><input type="checkbox" id="esc-ctrl"${X.esc.sinControles ? ' checked' : ''}><span></span></span> Sin los controles registrados (probabilidad inherente)</label>`;
  document.querySelectorAll('#esc-ctrls input[data-k]').forEach((el) => el.addEventListener('input', () => {
    X.esc.factor[el.dataset.k] = Number(el.value);
    el.style.setProperty('--val', (el.value / 3) * 100);
    el.closest('.esc-c').querySelector('b').textContent = `×${fmt(el.value, 1)}`;
    simularLuego();
  }));
  document.getElementById('esc-tol').addEventListener('input', (e) => {
    X.sup.tolerancia_dias_proyecto = Number(e.target.value);
    e.target.style.setProperty('--val', (e.target.value / 120) * 100);
    e.target.closest('.esc-c').querySelector('b').textContent = `${e.target.value} días`;
    simularLuego();
  });
  document.getElementById('esc-ctrl').addEventListener('change', (e) => { X.esc.sinControles = e.target.checked; simularLuego(); });
}

function cuerpoSimulacion() {
  const f = X.esc.factor;
  return {
    supuestos: X.sup,
    escenario: {
      factor: { climatico: f.clima, logistico_acceso: f.clima, seguridad_fisica: f.seguridad_fisica, social_comunidad: f.social_comunidad, ambiental: f.ambiental, contractual: f.contractual },
      controles: X.esc.sinControles ? 'inherente' : 'residual',
    },
  };
}

function simularLuego() {
  clearTimeout(X.t);
  X.t = setTimeout(simular, 300);
}

async function simular() {
  try {
    const r = await fetch('/api/ejecucion/simular', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpoSimulacion()) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
    X.sim = d;
    renderResultadoEsc();
    document.getElementById('advertencias').innerHTML = (d.advertencias || []).map((a) => `<div>${a}</div>`).join('');
  } catch (e) { aviso(`<i data-lucide="x"></i> ${e.message}`, 'error'); }
}

function delta(a, b, dec = 0, invertido = false) {
  const dlt = b - a;
  if (Math.abs(dlt) < 10 ** -dec / 2) return '';
  const peor = invertido ? dlt < 0 : dlt > 0;
  return `<span class="delta ${peor ? 'sube' : 'baja'}">${dlt > 0 ? '+' : ''}${fmt(dlt, dec)}</span>`;
}

function renderResultadoEsc() {
  if (!X.sim) return;
  const base = Object.fromEntries(X.d.proyectos.map((p) => [p.id_proyecto, p]));
  const filas = X.sim.proyectos.map((p) => {
    const b = base[p.id_proyecto] || p;
    return `<tr><td><b>${nombreProy(p.id_proyecto)}</b></td>
      <td><span class="lvl ${nivelIre(p.ire)}">${fmt(p.ire, 0)}</span>${delta(b.ire, p.ire)}</td>
      <td>${fmt(p.atraso_media, 0)} d${delta(b.atraso_media, p.atraso_media)}</td>
      <td>${fmt(p.atraso_p90, 0)} d${delta(b.atraso_p90, p.atraso_p90)}</td>
      <td>${usd(p.costo_p90)}${delta(b.costo_p90 / 1e6, p.costo_p90 / 1e6, 1)}</td></tr>`;
  }).join('');
  const port = X.sim.portafolio, pb = X.d.resumen.portafolio;
  document.getElementById('esc-res').innerHTML = `
    <table><thead><tr><th></th><th>IRE</th><th>Atraso esperado</th><th>Atraso P90</th><th>Sobrecosto P90</th></tr></thead>
    <tbody>${filas}<tr><td><b>Portafolio</b></td><td></td><td>${fmt(port.atraso_media, 0)} d${delta(pb.atraso_media, port.atraso_media)}</td>
      <td>${fmt(port.atraso_p90, 0)} d${delta(pb.atraso_p90, port.atraso_p90)}</td><td>${usd(port.costo_p90)}${delta(pb.costo_p90 / 1e6, port.costo_p90 / 1e6, 1)}</td></tr></tbody></table>
    <div class="esc-hist"><canvas id="h-esc"></canvas></div>
    <div class="nota">${nombreProy(X.proy)}: probabilidad de cada atraso, actual (gris) contra el escenario (naranja). Los cambios en rojo empeoran; en verde mejoran.</div>`;
  const serie = (h) => h.bordes.slice(0, -1).map((b, i) => ({ x: (b + h.bordes[i + 1]) / 2, y: h.frecuencia[i] * 100 }));
  X.charts.esc?.destroy();
  X.charts.esc = new Chart(document.getElementById('h-esc'), {
    type: 'line',
    data: { datasets: [
      { label: 'Actual', data: serie(X.d.resumen.histogramas[X.proy].atraso), borderColor: ui.css('--ink-2'), backgroundColor: ui.alpha(ui.css('--ink-2'), 0.08), fill: true, tension: 0.35, pointRadius: 0, borderWidth: 1.5 },
      { label: 'Escenario', data: serie(X.sim.histogramas[X.proy].atraso), borderColor: ui.css('--lvl-alto'), backgroundColor: ui.alpha(ui.css('--lvl-alto'), 0.12), fill: true, tension: 0.35, pointRadius: 0, borderWidth: 2 },
    ] },
    options: { maintainAspectRatio: false, animation: false, interaction: { intersect: false, mode: 'nearest', axis: 'x' },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (i) => `~${fmt(i[0].parsed.x, 0)} días`, label: (c) => `${c.dataset.label}: ${fmt(c.parsed.y, 1)} %` } } },
      scales: { x: { type: 'linear', title: { display: true, text: 'días de atraso del proyecto', color: ui.css('--muted') }, grid: { display: false }, ticks: { color: ui.css('--muted') } },
        y: { beginAtZero: true, grid: { color: ui.css('--line') }, ticks: { color: ui.css('--muted'), callback: (v) => `${v} %` } } } },
  });
}

document.getElementById('b-reset-esc').addEventListener('click', () => {
  X.esc = { factor: { clima: 1, seguridad_fisica: 1, social_comunidad: 1, ambiental: 1, contractual: 1 }, sinControles: false };
  X.sup.tolerancia_dias_proyecto = X.d.supuestos.tolerancia_dias_proyecto;
  renderControlesEsc();
  simular();
});

// ---------------------------------------------------------------------------
// Formula y supuestos
// ---------------------------------------------------------------------------

function renderFormula() {
  const pasos = [
    ['Frecuencia de cada amenaza', 'λ = λ₀(letra RAM con controles) · e^(γ·Σ βₖ·zₖ) · factor de estado', 'La letra de la RAM se traduce a eventos por año en un paquete; el territorio real (z = 0 en el promedio de La Guajira) la sube o la baja, entre ×1/3 y ×3.'],
    ['Probabilidad en lo que falta', 'P = 1 − e^(−λ·T)', 'T: los años que le faltan al paquete según su cronograma (sintético).'],
    ['Días y costo por evento', 'días ~ Triangular(½D, D, 2D);  D = máx por dimensión\ncosto = LogUniforme(banda USD) + costo diario de parada · días', 'Manda la peor dimensión, como en la RAM. Las bandas en USD son las del instructivo.'],
    ['Escenarios y dependencia', 'N ~ Poisson(λ·T·W)', `W es un choque común (media 1) que comparten los riesgos climáticos de un municipio y los sociales de un proyecto: hay años en que todo falla junto. ${fmt(X.d.resumen.metadata.simulaciones)} escenarios.`],
    ['Paquete y proyecto', 'D_paquete = Σ días + atraso ya consumido\nD_proyecto = Σ máx(0, D_paquete − holgura)', 'Los paquetes de ruta crítica no tienen holgura: todo su atraso pasa al proyecto.'],
    ['Resultados', 'IRE = 100 · P(D > holgura + tolerancia)', 'Además: atraso esperado, P50 y P90 de atraso y sobrecosto, aporte de cada riesgo y días que evitan los controles.'],
  ];
  document.getElementById('formula').innerHTML = pasos.map(([t, f, s], i) => `<div class="paso-f"><span class="n">${i + 1}</span><span class="t">${t}</span><code>${f}</code>${s}</div>`).join('');
}

function campo(ruta, valor, base, paso = 'any') {
  const cambio = base != null && Number(valor) !== Number(base);
  return `<input class="field${cambio ? ' cambio' : ''}" type="number" step="${paso}" data-ruta="${ruta}" value="${valor ?? ''}" title="${base != null ? `Base: ${base}` : ''}">`;
}

function renderSupuestos() {
  const s = X.sup, b = X.d.supuestos_base;
  const covCols = Object.keys(COVS);
  document.getElementById('sup').innerHTML = `
    <div class="sup-b"><div class="t">1. Frecuencia por letra RAM (eventos por año en un paquete)</div>
      <div class="s">Las letras hablan del historial de la industria, la empresa o la unidad; aquí se reparten entre los paquetes comparables (E ≈ varias veces al año entre ~6 paquetes de una unidad).</div>
      <table><tr>${LETRAS.map((l) => `<th>${l}</th>`).join('')}</tr><tr>${LETRAS.map((l) => `<td>${campo(`lambda_por_letra.${l}`, s.lambda_por_letra[l], b.lambda_por_letra[l])}</td>`).join('')}</tr></table></div>
    <div class="sup-b"><div class="t">2. Peso del territorio</div>
      <div class="s">γ reparte el peso entre la letra del evaluador y el territorio (0 = solo la letra). El multiplicador queda entre 1/m y m.</div>
      <div class="sup-fila"><span>γ (peso del territorio)</span>${campo('gamma', s.gamma, b.gamma)}</div>
      <div class="sup-fila"><span>m (multiplicador máximo)</span>${campo('multiplicador_max', s.multiplicador_max, b.multiplicador_max)}</div>
      <div class="sup-fila"><span>Factor si está próximo a materializarse</span>${campo('factor_estado.proximo_a_materializarse', s.factor_estado.proximo_a_materializarse, b.factor_estado.proximo_a_materializarse)}</div>
      <div class="sup-fila"><span>Fracción consumida de lo ya materializado</span>${campo('fraccion_consumida_materializado', s.fraccion_consumida_materializado, b.fraccion_consumida_materializado)}</div></div>
    <div class="sup-b" style="grid-column:1/-1"><div class="t">3. Qué variable del territorio pesa en cada tipo de riesgo (β)</div>
      <div class="s">Vacío = no influye. z vale 0 en el promedio de La Guajira; un β de 0,6 con z = 1 multiplica la frecuencia por e^(γ·0,6).</div>
      <table><tr><th></th>${covCols.map((k) => `<th>${COVS[k][0]}</th>`).join('')}</tr>
      ${CATS.map((c) => `<tr><th>${ui.cat(c).label}</th>${covCols.map((k) => `<td>${campo(`covariables.${c}.${k}`, (s.covariables[c] || {})[k], (b.covariables[c] || {})[k] ?? '')}</td>`).join('')}</tr>`).join('')}</table></div>
    <div class="sup-b"><div class="t">4. Días de atraso por evento según la consecuencia RAM</div>
      <div class="s">Valor más probable (el evento dura entre la mitad y el doble). Manda la peor dimensión.</div>
      <table><tr><th></th>${[1, 2, 3, 4, 5].map((n) => `<th>${n}</th>`).join('')}</tr>
      ${DIMS.map((d) => `<tr><th>${ui.DIM_RAM[d]}</th>${[1, 2, 3, 4, 5].map((n) => `<td>${campo(`dias_por_consecuencia.${d}.${n}`, s.dias_por_consecuencia[d][n], b.dias_por_consecuencia[d][n])}</td>`).join('')}</tr>`).join('')}</table></div>
    <div class="sup-b"><div class="t">5. Dependencia, tolerancias y simulación</div>
      <div class="s">σ del choque común: 0 = riesgos independientes; más alto = más años en que todo falla junto (P90 más alto).</div>
      <div class="sup-fila"><span>σ clima (por municipio)</span>${campo('choques.clima', s.choques.clima, b.choques.clima)}</div>
      <div class="sup-fila"><span>σ social (por proyecto)</span>${campo('choques.social', s.choques.social, b.choques.social)}</div>
      <div class="sup-fila"><span>Tolerancia de atraso del paquete (días)</span>${campo('tolerancia_dias_paquete', s.tolerancia_dias_paquete, b.tolerancia_dias_paquete)}</div>
      <div class="sup-fila"><span>Tolerancia de atraso del proyecto (días)</span>${campo('tolerancia_dias_proyecto', s.tolerancia_dias_proyecto, b.tolerancia_dias_proyecto)}</div>
      <div class="sup-fila"><span>Solapamiento de atrasos en un paquete (1 = en fila, 0 = a la vez)</span>${campo('solapamiento', s.solapamiento, b.solapamiento)}</div>
      <div class="sup-fila"><span>Escenarios simulados</span>${campo('simulaciones', s.simulaciones, b.simulaciones, 1000)}</div></div>`;
  document.querySelectorAll('#sup [data-ruta]').forEach((el) => el.addEventListener('input', () => {
    const partes = el.dataset.ruta.split('.');
    let o = X.sup;
    partes.slice(0, -1).forEach((k) => { o[k] ??= {}; o = o[k]; });
    const ult = partes[partes.length - 1];
    if (el.value === '') delete o[ult]; else o[ult] = Number(el.value);
    el.classList.toggle('cambio', el.title.startsWith('Base') && Number(el.value) !== Number(el.title.replace('Base: ', '')));
  }));
}

// solo lo editable, en el formato de la API (dias como listas de 6)
function supuestosParaApi() {
  const s = clon(X.sup);
  s.dias_por_consecuencia = Object.fromEntries(DIMS.map((d) => [d, [0, 1, 2, 3, 4, 5].map((n) => Number(s.dias_por_consecuencia[d][n] ?? 0))]));
  s.covariables = Object.fromEntries(CATS.map((c) => [c, Object.fromEntries(Object.entries(s.covariables[c] || {}).filter(([, v]) => v !== '' && v != null && !Number.isNaN(Number(v))))]));
  ['version', 'semilla', 'horizonte_meses_por_defecto', 'meses_anomalia_lluvia', 'costo_directo_usd'].forEach((k) => delete s[k]);
  return s;
}

function aviso(texto, tipo = 'ok') {
  const a = document.getElementById('aviso');
  a.className = `aviso ${tipo}`;
  a.innerHTML = texto;
  a.hidden = !texto;
  ui.icons();
}

async function seguirRecalculo() {
  const est = await ui.json('/api/ram/recalcular');
  if (est.estado === 'corriendo') {
    aviso('<i data-lucide="loader"></i> Recalculando el modelo de riesgo de ejecución con los supuestos nuevos…', 'info');
    setTimeout(seguirRecalculo, 1200);
    return;
  }
  if (est.estado === 'listo') {
    aviso(`<i data-lucide="check"></i> Listo en ${est.segundos} s: los resultados ya usan estos supuestos.`);
    await cargar();
  } else aviso(`<i data-lucide="x"></i> El recálculo falló en: ${(est.fallos || []).join(', ')}`, 'error');
}

document.getElementById('b-probar').addEventListener('click', () => {
  document.getElementById('escenarios').scrollIntoView({ behavior: 'smooth' });
  X.sup = { ...X.sup, ...supuestosParaApi() };
  simular();
});
document.getElementById('b-guardar').addEventListener('click', async () => {
  try {
    const r = await ui.escribir('/api/ejecucion/supuestos', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ supuestos: supuestosParaApi(), editado_por: document.getElementById('f-autor').value, nota: document.getElementById('f-nota').value }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
    seguirRecalculo();
  } catch (e) { aviso(`<i data-lucide="x"></i> ${e.message}`, 'error'); }
});
document.getElementById('b-base').addEventListener('click', async () => {
  if (!window.confirm('¿Volver a los supuestos base de parametros.yaml? Se borran los supuestos guardados.')) return;
  const r = await ui.escribir('/api/ejecucion/supuestos', { method: 'DELETE' });
  if (r.ok) seguirRecalculo(); else aviso('<i data-lucide="x"></i> No se pudo volver a los supuestos base', 'error');
});

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

function renderTodo() {
  renderProyectos();
  renderPaquetes();
  renderDetalle();
  renderCronograma();
  renderResultadoEsc();
  ui.icons();
}

async function cargar() {
  X.d = await ui.json('/api/ejecucion');
  X.c = await ui.json('/api/cronograma').catch(() => null);
  if (!X.d.disponible) {
    aviso('<i data-lucide="info"></i> Aún no hay resultados: corre el pipeline (paso oro.ejecucion).', 'info');
    return;
  }
  X.proy = X.proy || [...X.d.proyectos].sort((a, b) => b.ire - a.ire || b.atraso_media - a.atraso_media)[0].id_proyecto;
  X.sup = clon(X.d.supuestos);
  const v = X.d.supuestos.version || {};
  document.getElementById('chip-supuestos').innerHTML = X.d.personalizados
    ? `<i data-lucide="pencil"></i> Supuestos personalizados · ${v.editado_en ? ui.fecha(v.editado_en) : ''}${v.editado_por ? ` · ${v.editado_por}` : ''}`
    : '<i data-lucide="sliders-horizontal"></i> Supuestos base (parametros.yaml)';
  renderFormula();
  renderSupuestos();
  renderControlesEsc();
  renderTodo();
  simular();
}

cargar();
