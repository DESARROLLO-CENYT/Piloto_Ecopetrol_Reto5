/* Explorar datos en tres subpaginas: Resumen (cuantos hay y donde), Proyectos y actividades (avance y cronograma) y
   Riesgos (matriz RAM, registro y ficha de cada riesgo). DATOS SINTETICOS. */

const E = {
  vista: null,
  riesgos: [],
  paquetes: [],          // paquetes con su ICT (Oro) y su cronograma (oro.cronograma)
  proyectos: [],         // cronograma de cada proyecto
  actividades: [],
  corte: null,
  ram: null,             // configuracion de la matriz RAM (parametros.yaml)
  charts: {},
  resumenListo: false,
  // Resumen
  tipoGrafico: '',
  cruce: 'categoria',
  vistaTipos: 'estado',   // estado | riesgos
  // Proyectos y actividades
  proySel: null,
  abiertos: new Set(),   // paquetes desplegados en el cronograma
  act: { buscar: '', paquete: '', tipo: '', estado: '' },
  ordenAct: { col: 'orden', asc: true },
  // Riesgos
  filtro: null,
  orden: { col: 'puntaje_ram', asc: false },
  etapaRam: 'residual',  // residual (con controles) | inherente (sin controles)
  lista: [],             // ids del registro tal como se ve (para moverse en la ficha)
  ficha: null,
};

const FILTRO_VACIO = { buscar: '', proyecto: '', paquete: '', actividad: '', municipio: '', categoria: '', tipo: '', estado: '', accion: '', ia: false, ram: null };
E.filtro = { ...FILTRO_VACIO };

// Escalas de consecuencia del instructivo ECP-DRI-I-007 (si parametros.yaml no trae las suyas)
const CONSECUENCIA_RAM = {
  5: 'Personas: una o más fatalidades · Económica: más de USD 10 M · Ambiental: contaminación irreparable · Clientes: veto como proveedor · Imagen: internacional',
  4: 'Personas: incapacidad permanente · Económica: USD 1 M a 10 M · Ambiental: contaminación mayor · Clientes: pérdida de mercado · Imagen: nacional',
  3: 'Personas: incapacidad temporal (> 1 día) · Económica: USD 100 mil a 1 M · Ambiental: contaminación localizada · Clientes: pérdida de clientes · Imagen: regional',
  2: 'Personas: lesión menor sin incapacidad · Económica: USD 10 mil a 100 mil · Ambiental: efecto menor · Clientes: quejas o reclamos · Imagen: local',
  1: 'Personas: primeros auxilios · Económica: menos de USD 10 mil · Ambiental: efecto leve · Clientes: incumplir especificaciones · Imagen: interna',
  0: 'Ninguna consecuencia',
};
const ORDEN_RAM = ['VH', 'H', 'M', 'L', 'N'];
const ORIGEN_ACT = {
  registro: 'Código que trae el registro',
  nombre: 'Nombre escrito en el registro (se reconoció)',
  inferida: 'El registro no la traía: se infirió por el momento del riesgo y su texto',
  corregida: '<span class="lvl-soft medio">revisar</span> El registro traía una de otro paquete o que no cuadra con el estado del riesgo; se infirió otra',
};
// cuanto falta (o hace cuanto vencio) la accion de un riesgo abierto
function plazoAccion(r) {
  if (r.estado === 'materializado' || !r.fecha_ejecucion_accion) return '';
  const d = Math.round((dia(r.fecha_ejecucion_accion) - dia(E.corte)) / DIA);
  return d < 0 ? ` <span class="muted">· venció hace ${fmt(-d)} días</span>` : ` <span class="muted">· faltan ${fmt(d)} días</span>`;
}

// meses durante los que un riesgo abierto puede pegarle a su actividad (lo mismo que usa el modelo de ejecucion)
const exposicionMeses = (a) => (a.estado === 'completada' ? 0
  : Math.max(0, (dia(a.fecha_fin_proyectada) - Math.max(dia(E.corte), dia(a.fecha_inicio_proyectada))) / DIA) / 30.44);
const CONS = [['PE', 'cons_personas'], ['EC', 'cons_economica'], ['MA', 'cons_ambiental'], ['CL', 'cons_clientes'], ['IM', 'cons_imagen']];
const ESTADO_ACT = {
  completada: { label: 'Completada', lvl: 'bajo', icon: 'circle-check' },
  en_curso: { label: 'En curso', lvl: 'medio', icon: 'circle-play' },
  por_iniciar: { label: 'Por iniciar', lvl: '', icon: 'circle-dashed' },
};

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

const DIA = 24 * 3600 * 1000;
const fmt = (v, d = 0) => (v == null || Number.isNaN(Number(v)) ? '-' : Number(v).toLocaleString('es-CO', { maximumFractionDigits: d, minimumFractionDigits: d }));
const pct = (v, d = 0) => (v == null ? '-' : `${fmt(v * 100, d)} %`);
const dia = (s) => (s ? new Date(`${String(s).slice(0, 10)}T12:00:00`) : null);
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];
const fMes = (s) => { if (!s) return '-'; const d = dia(s); return `${d.getDate()} ${MES[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`; };
const fCorta = (s) => (s ? dia(s).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }) : '-');
const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const normalizar = (t) => (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const fechaDe = (r) => new Date(String(r.fecha_identificacion).slice(0, 10) + 'T00:00:00');
const abierta = (r) => r.tipo === 'amenaza' && r.estado !== 'materializado';
const altaRam = (r) => r.nivel_residual === 'H' || r.nivel_residual === 'VH';
const paq = (id) => E.paquetes.find((p) => p.id_paquete === id);
const proy = (id) => E.proyectos.find((p) => p.id_proyecto === id);
const nombreProy = (id) => proy(id)?.nombre || id;
const nombrePaquete = (id) => ui.tagCorto(paq(id)?.nombre || id);
const numPaquete = (id) => `Paquete ${Number(String(id).split('PT')[1])}`;
const actDe = (id) => E.actIdx[id];
const disciplinaDe = (r) => actDe(r.id_actividad)?.disciplina;
const contar = (lista, clave) => lista.reduce((m, x) => { const k = typeof clave === 'function' ? clave(x) : x[clave]; m[k] = (m[k] || 0) + 1; return m; }, {});
const delta = (d) => (d > 0 ? `<span class="atr">+${fmt(d)} d</span>` : '<span class="a-tiempo">a tiempo</span>');

// Acciones de tratamiento: vencida si su fecha ya paso y el riesgo sigue abierto; por vencer, en los proximos 30 dias.
// Aqui cuentan amenazas y oportunidades; para escalar un paquete por acciones vencidas, oro.ict cuenta solo amenazas.
const ACCION = {
  vencida: { label: 'Vencidas', corto: 'vencida', lvl: 'critico' },
  por_vencer: { label: 'Por vencer (30 días)', corto: 'por vencer', lvl: 'alto' },
  programada: { label: 'Programadas', corto: 'programada', lvl: 'bajo' },
  materializado: { label: 'Riesgo ya materializado', corto: 'materializado', lvl: '' },
  sin_accion: { label: 'Sin acción o sin fecha', corto: 'sin fecha', lvl: '' },
};
function estadoAccion(r) {
  if (!r.accion_tratamiento || !r.fecha_ejecucion_accion) return 'sin_accion';
  if (r.estado === 'materializado') return 'materializado';
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  const fecha = new Date(String(r.fecha_ejecucion_accion).slice(0, 10) + 'T00:00:00');
  if (fecha < hoy) return 'vencida';
  return fecha - hoy <= 30 * DIA ? 'por_vencer' : 'programada';
}

// Tipos de actividad en el orden en que suelen ejecutarse (posicion media dentro de su paquete)
function tiposActividad() {
  const n = contar(E.actividades, 'id_paquete');
  const pos = {};
  E.actividades.forEach((a) => { (pos[a.disciplina] = pos[a.disciplina] || []).push(a.orden / n[a.id_paquete]); });
  return Object.entries(pos).map(([k, v]) => [k, v.reduce((s, x) => s + x, 0) / v.length]).sort((a, b) => a[1] - b[1]).map(([k]) => k);
}
const nombreTipo = (disciplina) => E.actividades.find((a) => a.disciplina === disciplina)?.nombre || disciplina;

// ---------------------------------------------------------------------------
// Navegacion entre subpaginas (#resumen, #proyectos, #riesgos)
// ---------------------------------------------------------------------------

const VISTAS = {
  resumen: { txt: 'Cuántos proyectos, actividades y riesgos hay, dónde están y cómo se cruzan', pintar: () => pintarResumen() },
  proyectos: { txt: 'Avance de cada proyecto, su cronograma y las actividades que faltan', pintar: () => pintarProyectos() },
  riesgos: { txt: 'Cada riesgo con sus características: clic en una fila para ver su ficha', pintar: () => pintarRiesgos() },
};

function mostrar(destino, { historial = true } = {}) {
  let [vista, arg] = String(destino || '').split('/');
  if (!VISTAS[vista]) vista = 'resumen';
  if (vista === 'proyectos' && arg && proy(arg) && arg !== E.proySel) { E.proySel = arg; E.abiertos = new Set(); }
  E.vista = vista;
  document.querySelectorAll('.vista').forEach((v) => { v.hidden = v.id !== `v-${vista}`; });
  document.querySelectorAll('#subnav button').forEach((b) => b.classList.toggle('on', b.dataset.vista === vista));
  document.getElementById('subnav-txt').textContent = VISTAS[vista].txt;
  if (vista !== 'riesgos') cerrarFicha();
  VISTAS[vista].pintar();
  if (vista === 'riesgos' && arg && E.riesgos.some((r) => r.id_riesgo === arg)) abrirFicha(arg, { historial: false });
  const hash = `#${vista}${vista === 'riesgos' && E.ficha ? `/${E.ficha}` : ''}`;
  if (historial && location.hash !== hash) history.pushState(null, '', `${location.pathname}${hash}`);
  ui.icons();
}

// Llevar al usuario a otra subpagina con un filtro ya puesto (clic en un municipio, una celda, un paquete...)
function irA(vista, opciones = {}) {
  cerrarFicha();
  if (vista === 'riesgos') {
    E.filtro = { ...FILTRO_VACIO, ...opciones };
  } else if (vista === 'proyectos') {
    if (opciones.proyecto) E.proySel = opciones.proyecto;
    E.act = { buscar: '', paquete: opciones.paquete || '', tipo: '', estado: '' };
    if (opciones.paquete) E.abiertos.add(opciones.paquete);
  }
  mostrar(vista);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('#subnav button').forEach((b) => b.addEventListener('click', () => mostrar(b.dataset.vista)));
window.addEventListener('popstate', () => mostrar(location.hash.slice(1), { historial: false }));

// ===========================================================================
// 1. RESUMEN
// ===========================================================================

function pintarResumen() {
  if (E.resumenListo) return;     // los datos no cambian mientras la pagina esta abierta
  E.resumenListo = true;
  renderKpis();
  renderMunicipios();
  renderTipos();
  renderCruce();
  renderEstados();
  renderChartSemanas();
  renderChartCategoria();
}

function kpi(icon, titulo, valor, sub, ir, filtro = {}) {
  return `<section class="card kpi-card${ir ? ' clic' : ''}"${ir ? ` data-ir="${ir}" data-f='${JSON.stringify(filtro)}'` : ''}>
    <div class="kpi-top"><span class="tile"><i data-lucide="${icon}"></i></span><span class="l">${titulo}</span>${ir ? '<i data-lucide="arrow-up-right" class="ir"></i>' : ''}</div>
    <div class="num lg">${valor}</div><div class="s">${sub}</div></section>`;
}

function renderKpis() {
  const est = contar(E.actividades, 'estado');
  const munPaq = new Set(E.paquetes.map((p) => p.municipio).filter(Boolean));
  const munRie = new Set(E.riesgos.map((r) => r.municipio).filter(Boolean));
  const pres = E.proyectos.reduce((s, p) => s + p.presupuesto_usd, 0);
  const avance = E.proyectos.reduce((s, p) => s + p.avance * p.presupuesto_usd, 0) / (pres || 1);
  const plan = E.proyectos.reduce((s, p) => s + p.avance_plan * p.presupuesto_usd, 0) / (pres || 1);
  const ab = E.riesgos.filter(abierta);
  const vencidas = E.riesgos.filter((r) => estadoAccion(r) === 'vencida').length;
  const tipos = new Set(E.actividades.map((a) => a.disciplina)).size;
  document.getElementById('kpis').innerHTML = [
    kpi('briefcase', 'Proyectos', fmt(E.proyectos.length), `${E.paquetes.length} paquetes de trabajo`, 'proyectos'),
    kpi('list-checks', 'Actividades', fmt(E.actividades.length), `${tipos} tipos · ${est.completada || 0} completadas · ${est.en_curso || 0} en curso · ${est.por_iniciar || 0} por iniciar`, 'proyectos'),
    kpi('gauge', 'Avance del portafolio', `${ui.num(avance * 100)}<span class="unit"> %</span>`, `planeado a hoy ${pct(plan, 1)} · ponderado por presupuesto (USD ${fmt(pres / 1e6)} M)`, 'proyectos'),
    kpi('map-pin', 'Municipios', fmt(munPaq.size), `con paquetes · ${munRie.size} con riesgos ubicados`),
    kpi('file-text', 'Riesgos', fmt(E.riesgos.length), `${E.riesgos.filter((r) => r.tipo === 'amenaza').length} amenazas · ${E.riesgos.filter((r) => r.tipo === 'oportunidad').length} oportunidades`, 'riesgos'),
    kpi('shield-alert', 'Amenazas abiertas', fmt(ab.length), `${ab.filter(altaRam).length} con RAM alta o muy alta · ${vencidas} acciones vencidas`, 'riesgos', { tipo: 'amenaza', estado: 'abierto' }),
  ].join('');
  document.querySelectorAll('#kpis [data-ir]').forEach((c) => c.addEventListener('click', () => irA(c.dataset.ir, JSON.parse(c.dataset.f))));
}

function renderMunicipios() {
  const nombres = new Set([...E.paquetes.map((p) => p.municipio), ...E.riesgos.map((r) => r.municipio)].filter(Boolean));
  const filas = [...nombres].map((m) => {
    const paqs = E.paquetes.filter((p) => p.municipio === m);
    const ids = new Set(paqs.map((p) => p.id_paquete));
    const rs = E.riesgos.filter((r) => r.municipio === m);
    const ab = rs.filter(abierta);
    return {
      m, proyectos: new Set(paqs.map((p) => p.id_proyecto)).size, paquetes: paqs.length,
      actividades: E.actividades.filter((a) => ids.has(a.id_paquete)).length,
      riesgos: rs.length, abiertas: ab.length, altas: ab.filter(altaRam).length,
    };
  }).sort((a, b) => b.riesgos - a.riesgos || b.paquetes - a.paquetes);
  const max = Math.max(1, ...filas.map((f) => f.riesgos));
  const sinMun = E.riesgos.filter((r) => !r.municipio).length;
  const cero = (v) => (v ? fmt(v) : '<span class="muted">0</span>');
  document.querySelector('#tabla-municipios tbody').innerHTML = filas.map((f) => `
    <tr class="clickable" data-m="${esc(f.m)}">
      <td><span class="mun"><span class="dot" style="background:var(--green-600)"></span>${esc(f.m)}</span></td>
      <td>${cero(f.proyectos)}</td><td>${cero(f.paquetes)}</td><td>${cero(f.actividades)}</td>
      <td><div class="barra-n"><b>${fmt(f.riesgos)}</b><span class="meter"><span style="width:${(f.riesgos / max) * 100}%"></span></span></div></td>
      <td>${cero(f.abiertas)}</td><td>${f.altas ? `<span class="lvl-soft alto">${f.altas}</span>` : '<span class="muted">0</span>'}</td>
    </tr>`).join('') + `
    <tr class="total"><td>Total</td><td>${fmt(E.proyectos.length)}</td><td>${fmt(E.paquetes.length)}</td><td>${fmt(E.actividades.length)}</td>
      <td><b>${fmt(E.riesgos.length)}</b></td><td>${fmt(E.riesgos.filter(abierta).length)}</td><td>${fmt(E.riesgos.filter((r) => abierta(r) && altaRam(r)).length)}</td></tr>`;
  document.getElementById('sub-municipios').textContent = `${filas.length} municipios de La Guajira${sinMun ? ` · ${sinMun} riesgos sin municipio` : ''} · un proyecto puede abarcar varios`;
  document.querySelectorAll('#tabla-municipios tr[data-m]').forEach((tr) => tr.addEventListener('click', () => irA('riesgos', { municipio: tr.dataset.m })));
}

function seriesTipos(tipos) {
  if (E.vistaTipos === 'riesgos') {     // amenazas abiertas que pegan en cada tipo de actividad, por nivel RAM residual
    const ab = E.riesgos.filter(abierta);
    const top = tipos.map((t) => [t, ab.filter((r) => disciplinaDe(r) === t).length]).sort((a, b) => b[1] - a[1])[0];
    return {
      sub: `${ab.length} amenazas abiertas según la actividad a la que pegan${top ? ` · ${pct(top[1] / (ab.length || 1))} en ${top[0].toLowerCase()}` : ''}`,
      series: ORDEN_RAM.map((n) => ({ label: `RAM ${ui.RAM[n].nombre.toLowerCase()}`, color: ui.RAM[n].bg, data: tipos.map((t) => ab.filter((r) => disciplinaDe(r) === t && r.nivel_residual === n).length) })),
    };
  }
  const comp = E.actividades.filter((a) => a.estado === 'completada').length;
  return {
    sub: `${E.actividades.length} actividades en ${tipos.length} tipos · ${pct(comp / (E.actividades.length || 1))} completadas`,
    series: [['completada', ui.css('--green-600')], ['en_curso', ui.css('--green-300')], ['por_iniciar', '#dfe3e0']].map(([e, c]) => ({
      label: ESTADO_ACT[e].label, color: c, data: tipos.map((t) => E.actividades.filter((a) => a.disciplina === t && a.estado === e).length) })),
  };
}

function renderTipos() {
  const tipos = tiposActividad();
  const { sub, series } = seriesTipos(tipos);
  document.getElementById('ley-tipos').innerHTML = series.map((s) => `<span><i class="sw" style="background:${s.color}"></i>${s.label}</span>`).join('');
  document.getElementById('sub-tipos').textContent = sub;
  E.charts.tipos?.destroy();
  E.charts.tipos = new Chart(document.getElementById('chart-tipos'), {
    type: 'bar',
    data: {
      labels: tipos,
      datasets: series.map((s) => ({ label: s.label, data: s.data, backgroundColor: s.color, borderRadius: 6, borderSkipped: false, barPercentage: 0.72, categoryPercentage: 0.9 })),
    },
    options: {
      indexAxis: 'y', maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { ...ui.tooltip(), displayColors: true, callbacks: { title: (i) => `${i[0].label}: ${nombreTipo(i[0].label)}`, label: (c) => ` ${c.dataset.label}: ${c.raw}` } },
      },
      scales: {
        x: { stacked: true, grid: { color: ui.css('--line') }, border: { display: false }, ticks: { precision: 0, color: ui.css('--muted') } },
        y: { stacked: true, grid: { display: false }, border: { display: false }, ticks: { color: ui.css('--ink-2') } },
      },
    },
  });
}

document.querySelectorAll('#seg-tipos button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-tipos button').forEach((x) => x.classList.toggle('on', x === b));
  E.vistaTipos = b.dataset.v;
  renderTipos();
}));

// Cruce proyecto/paquete x categoria, nivel RAM, estado o tipo de actividad: que riesgos tiene cada uno
function columnasCruce() {
  if (E.cruce === 'actividad') {
    return { cols: tiposActividad().map((t) => ({ k: t, h: t, t: nombreTipo(t) })), de: (r) => disciplinaDe(r), base: () => true,
      nota: 'Todos los riesgos del registro según el tipo de actividad a la que pegan.' };
  }
  if (E.cruce === 'nivel') {
    return { cols: ORDEN_RAM.map((n) => ({ k: n, h: ui.ramChip(n), t: ui.RAM[n].nombre })), de: (r) => r.nivel_residual, base: (r) => abierta(r),
      nota: 'Nivel RAM residual (con controles) de las amenazas abiertas: latentes o próximas a materializarse.' };
  }
  if (E.cruce === 'estado') {
    return { cols: Object.entries(ui.ESTADO).map(([k, v]) => ({ k, h: v.label, t: v.label })), de: (r) => r.estado, base: () => true,
      nota: 'Todos los riesgos del registro (amenazas y oportunidades) según su ciclo de materialización.' };
  }
  const presentes = Object.keys(ui.CATEGORIA).filter((k) => E.riesgos.some((r) => r.categoria === k));
  return { cols: presentes.map((k) => ({ k, h: ui.cat(k).corto, t: ui.cat(k).label })), de: (r) => r.categoria, base: () => true,
    nota: 'Todos los riesgos del registro (amenazas y oportunidades) por categoría.' };
}

function renderCruce() {
  const { cols, de, base, nota } = columnasCruce();
  const lista = E.riesgos.filter(base);
  const fila = (rs) => cols.map((c) => rs.filter((r) => de(r) === c.k).length);
  const grupos = E.proyectos.map((p) => ({
    p, rs: lista.filter((r) => r.id_proyecto === p.id_proyecto),
    paqs: E.paquetes.filter((q) => q.id_proyecto === p.id_proyecto).sort((a, b) => a.id_paquete.localeCompare(b.id_paquete))
      .map((q) => ({ q, rs: lista.filter((r) => r.id_paquete_trabajo === q.id_paquete) })),
  }));
  const maxPaq = Math.max(1, ...grupos.flatMap((g) => g.paqs.flatMap((x) => fila(x.rs))));
  const maxProy = Math.max(1, ...grupos.flatMap((g) => fila(g.rs)));
  const celda = (n, max, attrs) => {
    const a = n ? 0.1 + 0.8 * (n / max) : 0;
    return `<td class="c${n ? '' : ' cero'}"${attrs} style="background:${n ? ui.alpha(ui.css('--green-700'), a) : 'transparent'};color:${a > 0.5 ? '#fff' : 'inherit'}">${n || '·'}</td>`;
  };
  const filaHtml = (clase, etiqueta, sub, rs, max, filtro) => `<tr class="${clase}">
      <th><div class="t">${etiqueta}</div><div class="s">${sub}</div></th>
      ${fila(rs).map((n, i) => celda(n, max, ` data-f='${JSON.stringify({ ...filtro, col: cols[i].k })}' title="${esc(cols[i].t)}: ${n}"`)).join('')}
      <td class="tot" data-f='${JSON.stringify(filtro)}'>${rs.length}</td></tr>`;
  const cuerpo = grupos.map((g) => filaHtml('proy', g.p.nombre, `${g.paqs.length} paquetes`, g.rs, maxProy, { proyecto: g.p.id_proyecto })
    + g.paqs.map((x) => filaHtml('paq', numPaquete(x.q.id_paquete), `${esc(x.q.municipio || '')}${x.q.ruta_critica ? ' · ruta crítica' : ''}`, x.rs, maxPaq,
      { proyecto: g.p.id_proyecto, paquete: x.q.id_paquete })).join('')).join('');
  const totales = fila(lista);
  document.getElementById('tabla-cruce').innerHTML = `
    <thead><tr><th></th>${cols.map((c) => `<th title="${esc(c.t)}">${c.h}</th>`).join('')}<th>Total</th></tr></thead>
    <tbody>${cuerpo}</tbody>
    <tfoot><tr><th>Total</th>${totales.map((n) => `<td>${n}</td>`).join('')}<td>${lista.length}</td></tr></tfoot>`;
  document.getElementById('nota-cruce').textContent = `${nota} El color compara paquetes con paquetes y proyectos con proyectos.`;
  document.querySelectorAll('#tabla-cruce [data-f]').forEach((td) => td.addEventListener('click', () => {
    const f = JSON.parse(td.dataset.f);
    const o = { proyecto: f.proyecto, paquete: f.paquete || '' };
    if (f.col != null) {
      if (E.cruce === 'categoria') o.categoria = f.col;
      if (E.cruce === 'estado') o.estado = f.col;
      if (E.cruce === 'actividad') o.actividad = `t:${f.col}`;
      if (E.cruce === 'nivel') o.ram = { nivel: f.col, etapa: 'residual' };
    } else if (E.cruce === 'nivel') { o.tipo = 'amenaza'; o.estado = 'abierto'; }
    irA('riesgos', o);
  }));
}

document.querySelectorAll('#seg-cruce button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-cruce button').forEach((x) => x.classList.toggle('on', x === b));
  E.cruce = b.dataset.v;
  renderCruce();
  ui.icons();
}));

function renderEstados() {
  const total = E.riesgos.length;
  document.getElementById('estados').innerHTML = Object.entries(ui.ESTADO).map(([k, v]) => {
    const n = E.riesgos.filter((r) => r.estado === k).length;
    const p = total ? (n / total) * 100 : 0;
    return `
      <button class="estado-row" data-e="${k}">
        <div class="top"><span class="status"><span class="dot ${v.lvl}"></span>${v.label}</span><span><b>${n}</b><span class="pct">${p.toFixed(0)}%</span></span></div>
        <div class="meter"><span style="width:${p}%;background:var(--lvl-${v.lvl})"></span></div>
      </button>`;
  }).join('');
  document.querySelectorAll('#estados [data-e]').forEach((b) => b.addEventListener('click', () => irA('riesgos', { estado: b.dataset.e })));
}

function renderChartSemanas() {
  const semanas = 20;
  const fin = new Date();
  const conteo = new Array(semanas).fill(0);
  E.riesgos.forEach((r) => {
    const idx = semanas - 1 - Math.floor((fin - fechaDe(r)) / (7 * DIA));
    if (idx >= 0 && idx < semanas) conteo[idx] += 1;
  });
  const ult7 = E.riesgos.filter((r) => fin - fechaDe(r) <= 7 * DIA).length;
  const prev7 = E.riesgos.filter((r) => fin - fechaDe(r) > 7 * DIA && fin - fechaDe(r) <= 14 * DIA).length;
  document.getElementById('n-semana').textContent = ult7;
  const d = ult7 - prev7;
  const tr = document.getElementById('trend-semana');
  tr.textContent = `${d >= 0 ? '+' : ''}${d} vs. semana previa`;
  tr.className = `trend ${d > 0 ? 'down' : d < 0 ? '' : 'flat'}`;

  const labels = conteo.map((_, i) => new Date(fin - (semanas - 1 - i) * 7 * DIA).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }));
  const canvas = document.getElementById('chart-semanas');
  const ctx = canvas.getContext('2d');
  const verde = ui.css('--green-600');
  const g = ctx.createLinearGradient(0, 0, 0, canvas.parentElement.clientHeight || 150);
  g.addColorStop(0, ui.alpha(verde, 0.3));
  g.addColorStop(1, ui.alpha(verde, 0));
  E.charts.semanas?.destroy();
  E.charts.semanas = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets: [{ data: conteo, borderColor: verde, borderWidth: 2, fill: true, backgroundColor: g, tension: 0.4, pointRadius: 0, pointHoverRadius: 4 }] },
    options: {
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (i) => `Semana del ${i[0].label}`, label: (c) => `${c.raw} riesgos` } } },
      scales: { x: { display: false }, y: { display: false, beginAtZero: true } },
    },
  });
}

function renderChartCategoria() {
  const lista = E.tipoGrafico ? E.riesgos.filter((r) => r.tipo === E.tipoGrafico) : E.riesgos;
  const claves = Object.keys(ui.CATEGORIA).filter((k) => k !== 'sin_clasificar' || lista.some((r) => r.categoria === k));
  const valores = claves.map((k) => lista.filter((r) => r.categoria === k).length);
  const max = Math.max(...valores);
  const canvas = document.getElementById('chart-categoria');
  const ctx = canvas.getContext('2d');
  const base = ui.hatch(ctx, ui.css('--green-200'), ui.css('--green-300'));
  const top = ui.hatch(ctx, ui.css('--green-700'), ui.css('--green-800'));
  const data = {
    labels: claves.map((k) => ui.cat(k).label),
    datasets: [{ data: valores, backgroundColor: valores.map((v) => (v === max ? top : base)), borderRadius: 999, borderSkipped: false, barPercentage: 0.6, categoryPercentage: 0.9, maxBarThickness: 64 }],
  };
  if (E.charts.cat) {
    E.charts.cat.data = data;
    E.charts.cat.$claves = claves;
    E.charts.cat.update();
    return;
  }
  E.charts.cat = new Chart(canvas, {
    type: 'bar', data, plugins: [ui.bubblePlugin],
    options: {
      maintainAspectRatio: false,
      layout: { padding: { top: 30 } },
      onHover: (e, els) => { e.native.target.style.cursor = els.length ? 'pointer' : 'default'; },
      onClick: (e, els) => {
        if (!els.length) return;
        irA('riesgos', { categoria: E.charts.cat.$claves[els[0].index], tipo: E.tipoGrafico });
      },
      plugins: { legend: { display: false }, tooltip: ui.tooltip() },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: ui.css('--muted') } },
        y: { beginAtZero: true, grid: { color: ui.css('--line') }, border: { display: false, dash: [4, 4] }, ticks: { color: ui.css('--muted'), maxTicksLimit: 5, precision: 0 } },
      },
    },
  });
  E.charts.cat.$claves = claves;
}

document.querySelectorAll('#seg-tipo button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-tipo button').forEach((x) => x.classList.toggle('on', x === b));
  E.tipoGrafico = b.dataset.v;
  renderChartCategoria();
}));

// ===========================================================================
// 2. PROYECTOS Y ACTIVIDADES
// ===========================================================================

function pintarProyectos() {
  if (!E.proyectos.length) {
    document.getElementById('proy-cards').innerHTML = '<section class="card span-12 muted">Aún no hay cronograma: corre el pipeline (paso oro.cronograma).</section>';
    return;
  }
  if (!E.proySel || !proy(E.proySel)) E.proySel = E.proyectos[0].id_proyecto;
  const p = proy(E.proySel);
  if (!E.abiertos.size && p.paquete_que_define_el_fin) E.abiertos.add(p.paquete_que_define_el_fin);
  renderProyCards();
  renderGantt();
  renderSelectsAct();
  renderActividades();
  renderListaPaquetes();
  renderAvanceTipos();
  ui.icons();
}

function renderProyCards() {
  document.getElementById('proy-cards').innerHTML = E.proyectos.map((p) => {
    const muns = [...new Set(E.paquetes.filter((q) => q.id_proyecto === p.id_proyecto).map((q) => q.municipio).filter(Boolean))];
    const ab = E.riesgos.filter((r) => r.id_proyecto === p.id_proyecto && abierta(r));
    const atraso = p.atraso_proyectado_dias;
    const estado = atraso > 30 ? ['alto', `${fmt(atraso)} días tarde`] : atraso > 0 ? ['medio', `${fmt(atraso)} días tarde`] : ['bajo', 'a tiempo'];
    return `<section class="card span-4 proy-card${p.id_proyecto === E.proySel ? ' sel' : ''}" data-id="${p.id_proyecto}">
      <div class="card-head">
        <div class="card-icon"><i data-lucide="briefcase"></i></div>
        <div class="grow"><div class="card-title">${esc(p.nombre)}</div><div class="card-sub">${esc(muns.join(', '))}</div></div>
        <span class="lvl-soft ${estado[0]}">${estado[1]}</span>
      </div>
      <div class="fila">
        <div class="ring" style="--p:${p.avance * 100};--size:96px"><div><div class="num md">${fmt(p.avance * 100, 1)}<span class="unit" style="font-size:var(--fs-13)"> %</span></div><div class="lbl">avance</div></div></div>
        <div class="kpis">
          <div class="kpi"><div class="l">Planeado a hoy</div><div class="v">${fmt(p.avance_plan * 100, 1)} <small>%</small></div></div>
          <div class="kpi"><div class="l">Cumplimiento</div><div class="v">${fmt(p.indice_cumplimiento, 2)}</div></div>
          <div class="kpi"><div class="l">Fin planeado</div><div class="v sm">${fCorta(p.fecha_fin_plan)}</div></div>
          <div class="kpi"><div class="l">Fin proyectado</div><div class="v sm">${fCorta(p.fecha_fin_proyectada)}</div></div>
        </div>
      </div>
      <div class="av-doble" title="Real ${pct(p.avance, 1)} · planeado ${pct(p.avance_plan, 1)}"><span class="plan" style="width:${p.avance_plan * 100}%"></span><span class="real" style="width:${p.avance * 100}%"></span></div>
      <div class="pie">${p.n_paquetes} paquetes · ${p.n_actividades} actividades (${p.n_completadas} completadas) · ${ab.length} amenazas abiertas${ab.filter(altaRam).length ? `, ${ab.filter(altaRam).length} ${ab.filter(altaRam).length === 1 ? 'alta' : 'altas'}` : ''}</div>
    </section>`;
  }).join('');
  document.querySelectorAll('.proy-card').forEach((c) => c.addEventListener('click', () => {
    if (E.proySel === c.dataset.id) return;
    E.proySel = c.dataset.id;
    E.abiertos = new Set([proy(E.proySel).paquete_que_define_el_fin].filter(Boolean));
    E.act = { buscar: '', paquete: '', tipo: '', estado: '' };
    pintarProyectos();
  }));
}

// --- Cronograma (diagrama de Gantt en HTML) ------------------------------------------------------------------------

function escalaTiempo(filas) {
  const fechas = filas.flatMap((f) => [f.fecha_inicio_plan, f.fecha_fin_plan, f.fecha_inicio_proyectada, f.fecha_fin_proyectada]).filter(Boolean).map((s) => dia(s).getTime());
  const t0 = Math.min(...fechas), t1 = Math.max(...fechas);
  const margen = (t1 - t0) * 0.02;
  return { t0: t0 - margen, t1: t1 + margen * 3 };
}

function marcasMes(t0, t1) {
  const meses = (t1 - t0) / (30.44 * DIA);
  const paso = meses > 30 ? 3 : meses > 15 ? 2 : 1;
  const d = new Date(t0); d.setDate(1); d.setHours(12); d.setMonth(d.getMonth() + 1);
  const out = [];
  while (d.getTime() < t1) {
    if (d.getMonth() % paso === 0) out.push(new Date(d));
    d.setMonth(d.getMonth() + 1);
  }
  return out;
}

function barras(f, x) {
  const ip = x(f.fecha_inicio_plan), fp = x(f.fecha_fin_plan), iq = x(f.fecha_inicio_proyectada), fq = x(f.fecha_fin_proyectada);
  const atr = (dia(f.fecha_fin_proyectada) - dia(f.fecha_fin_plan)) / DIA;
  return `<span class="b-plan" style="left:${ip}%;width:${Math.max(0.3, fp - ip)}%"></span>
    <span class="b-proy" style="left:${iq}%;width:${Math.max(0.3, fq - iq)}%"><span class="b-hecho" style="width:${(f.avance || 0) * 100}%"></span></span>
    ${atr > 0 ? `<span class="b-atraso" style="left:${fp}%;width:${fq - fp}%"></span><span class="b-lbl" style="left:${fq}%">+${fmt(atr)} d</span>` : ''}`;
}

function renderGantt() {
  const p = proy(E.proySel);
  const paqs = E.paquetes.filter((q) => q.id_proyecto === p.id_proyecto && q.fecha_inicio_plan).sort((a, b) => dia(a.fecha_inicio_plan) - dia(b.fecha_inicio_plan));
  const acts = E.actividades.filter((a) => a.id_proyecto === p.id_proyecto);
  const { t0, t1 } = escalaTiempo([p, ...acts]);
  const x = (s) => ((dia(s).getTime() - t0) / (t1 - t0)) * 100;
  const marcas = marcasMes(t0, t1);
  const corte = x(E.corte);
  document.getElementById('gantt-titulo').textContent = `Cronograma de ${p.nombre} · ${fCorta(p.fecha_inicio_plan)} a ${fCorta(p.fecha_fin_proyectada)}`;
  const etiqMes = (d) => d.toLocaleDateString('es-CO', { month: 'short', ...(d.getMonth() < 3 ? { year: '2-digit' } : {}) });
  const tituloFila = (f) => `Planeado ${fCorta(f.fecha_inicio_plan)} → ${fCorta(f.fecha_fin_plan)} · proyectado ${fCorta(f.fecha_inicio_proyectada)} → ${fCorta(f.fecha_fin_proyectada)} · avance ${pct(f.avance, 1)}`;
  const filas = [`<div class="g-row proy" title="${tituloFila(p)}"><div class="g-lab"><div><b>${esc(p.nombre)}</b><span>${pct(p.avance, 1)} · plan ${pct(p.avance_plan, 1)}</span></div></div><div class="g-track">${barras(p, x)}</div></div>`];
  paqs.forEach((q) => {
    const abierto = E.abiertos.has(q.id_paquete);
    const suyas = acts.filter((a) => a.id_paquete === q.id_paquete).sort((a, b) => a.orden - b.orden);
    filas.push(`<div class="g-row paq${abierto ? ' open' : ''}${q.atraso_sobre_holgura_dias > 0 ? ' tarde' : ''}" data-id="${q.id_paquete}" title="${tituloFila(q)} · holgura ${fmt(q.holgura_dias)} d">
      <div class="g-lab"><i data-lucide="chevron-right" class="caret"></i><div><b>${numPaquete(q.id_paquete)}</b><span>${pct(q.avance, 1)} · ${suyas.length} act.${q.ruta_critica ? ' · ruta crítica' : ` · holgura ${fmt(q.holgura_dias)} d`}</span></div></div>
      <div class="g-track">${barras(q, x)}</div></div>`);
    if (abierto) {
      suyas.forEach((a) => filas.push(`<div class="g-row act ${a.estado}" title="${esc(a.nombre)} · ${tituloFila(a)}">
        <div class="g-lab"><span class="dot ${ESTADO_ACT[a.estado]?.lvl || ''}"></span><div><b>${esc(a.nombre)}</b><span>${pct(a.peso_en_paquete)} del paquete · ${pct(a.avance)}${a.amenazas_abiertas ? ` · <em class="${a.amenazas_altas ? 'alta' : ''}">${a.amenazas_abiertas} amenaza${a.amenazas_abiertas === 1 ? '' : 's'}</em>` : ''}</span></div></div>
        <div class="g-track">${barras(a, x)}</div></div>`));
    }
  });
  document.getElementById('gantt').innerHTML = `
    <div class="g-row g-escala"><div class="g-lab"></div><div class="g-track">${marcas.map((d) => `<span class="g-mes" style="left:${x(d.toISOString())}%">${etiqMes(d)}</span>`).join('')}</div></div>
    <div class="g-cuerpo">
      ${marcas.map((d) => `<span class="g-linea" style="--x:${x(d.toISOString()) / 100}"></span>`).join('')}
      <span class="g-hoy" style="--x:${corte / 100}" title="Fecha de corte: ${fCorta(E.corte)}"><span>hoy</span></span>
      ${filas.join('')}
    </div>`;
  document.querySelectorAll('#gantt .g-row.paq').forEach((r) => r.addEventListener('click', () => {
    const id = r.dataset.id;
    if (E.abiertos.has(id)) E.abiertos.delete(id); else E.abiertos.add(id);
    renderGantt();
    ui.icons();
  }));
}

// --- Actividades ---------------------------------------------------------------------------------------------------

function renderSelectsAct() {
  const paqs = E.paquetes.filter((q) => q.id_proyecto === E.proySel).sort((a, b) => a.id_paquete.localeCompare(b.id_paquete));
  const opt = (v, t, sel) => `<option value="${esc(v)}"${v === sel ? ' selected' : ''}>${esc(t)}</option>`;
  document.getElementById('a-paquete').innerHTML = opt('', 'Todos los paquetes', E.act.paquete) + paqs.map((q) => opt(q.id_paquete, ui.nombreCorto(q.nombre), E.act.paquete)).join('');
  document.getElementById('a-tipo').innerHTML = opt('', 'Todos los tipos', E.act.tipo) + tiposActividad().map((t) => opt(t, nombreTipo(t), E.act.tipo)).join('');
  document.getElementById('a-estado').innerHTML = opt('', 'Todos los estados', E.act.estado) + Object.entries(ESTADO_ACT).map(([k, v]) => opt(k, v.label, E.act.estado)).join('');
  document.getElementById('a-buscar').value = E.act.buscar;
}

function actividadesFiltradas() {
  const f = E.act;
  const q = normalizar(f.buscar);
  return E.actividades.filter((a) => a.id_proyecto === E.proySel && (!f.paquete || a.id_paquete === f.paquete) && (!f.tipo || a.disciplina === f.tipo)
    && (!f.estado || a.estado === f.estado) && (!q || normalizar(`${a.nombre} ${a.disciplina} ${a.id_actividad}`).includes(q)));
}

function renderActividades() {
  const { col, asc } = E.ordenAct;
  const filas = actividadesFiltradas().sort((a, b) => {
    if (col === 'orden') return (a.id_paquete.localeCompare(b.id_paquete) || a.orden - b.orden) * (asc ? 1 : -1);
    const av = a[col], bv = b[col];
    const cmp = typeof av === 'number' ? av - bv : String(av ?? '').localeCompare(String(bv ?? ''));
    return asc ? cmp : -cmp;
  });
  const todas = E.actividades.filter((a) => a.id_proyecto === E.proySel);
  const pend = filas.filter((a) => a.estado !== 'completada');
  const puntos = pend.reduce((s, a) => s + (a.aporte_total_pp - a.aporte_avance_pp), 0);
  document.getElementById('sub-actividades').textContent = `${filas.length} de ${todas.length} actividades · ${pend.length} por ejecutar · faltan ${fmt(puntos, 1)} puntos de avance del proyecto`;
  document.querySelector('#tabla-actividades tbody').innerHTML = filas.map((a) => {
    const e = ESTADO_ACT[a.estado] || { label: a.estado, lvl: '', icon: 'circle' };
    const atr = a.atraso_proyectado_dias;
    return `<tr class="${a.estado}">
      <td><div class="cell-main"><span class="tile act-${a.estado}"><i data-lucide="${e.icon}"></i></span>
        <div><div class="t">${esc(a.nombre)}</div><div class="s" title="${fmt(a.aporte_total_pp, 1)} puntos de avance del proyecto">${numPaquete(a.id_paquete)} · ${a.orden}.ª · pesa ${pct(a.peso_en_paquete)}</div></div></div></td>
      <td><div class="av-cel"><span class="meter"><span style="width:${a.avance * 100}%"></span></span><b>${pct(a.avance)}</b></div><div class="s"><span class="status"><span class="dot ${e.lvl}"></span>${e.label}</span> · aporta ${fmt(a.aporte_avance_pp, 1)} pts</div></td>
      <td>${a.amenazas_abiertas ? `<button class="link" data-act="${a.id_actividad}" title="Ver sus amenazas abiertas">${a.amenazas_abiertas} abierta${a.amenazas_abiertas === 1 ? '' : 's'}</button>${a.amenazas_altas ? ` <span class="lvl-soft alto">${a.amenazas_altas} alta${a.amenazas_altas === 1 ? '' : 's'}</span>` : ''}` : '<span class="muted">sin abiertas</span>'}
        <div class="s">${a.riesgos_materializados ? `${a.riesgos_materializados} materializado${a.riesgos_materializados === 1 ? '' : 's'}` : '&nbsp;'}</div></td>
      <td class="ink-2" title="Planeado del ${fCorta(a.fecha_inicio_plan)} al ${fCorta(a.fecha_fin_plan)}">${fMes(a.fecha_inicio_plan)} → ${fMes(a.fecha_fin_plan)}
        <div class="s">${a.estado === 'completada' ? 'terminó' : 'termina'} ${fMes(a.fecha_fin_real || a.fecha_fin_proyectada)} · ${delta(atr)}</div></td>
    </tr>`;
  }).join('') || '<tr><td colspan="4" class="muted" style="padding:24px 12px">Ninguna actividad coincide con los filtros.</td></tr>';
  document.querySelectorAll('#tabla-actividades th').forEach((th) => {
    const activo = th.dataset.col === col;
    th.classList.toggle('sorted', activo);
    th.textContent = th.textContent.replace(/ [↑↓]$/, '') + (activo ? (asc ? ' ↑' : ' ↓') : '');
  });
  document.querySelectorAll('.pq-item').forEach((b) => b.classList.toggle('sel', b.dataset.id === E.act.paquete));
  document.querySelectorAll('#tabla-actividades [data-act]').forEach((b) => b.addEventListener('click', () => {
    const a = actDe(b.dataset.act);
    irA('riesgos', { proyecto: a.id_proyecto, paquete: a.id_paquete, actividad: `a:${a.id_actividad}`, tipo: 'amenaza', estado: 'abierto' });
  }));
  ui.icons();
}

function renderListaPaquetes() {
  const paqs = E.paquetes.filter((q) => q.id_proyecto === E.proySel).sort((a, b) => a.id_paquete.localeCompare(b.id_paquete));
  document.getElementById('lista-paquetes').innerHTML = paqs.map((q) => {
    const ab = E.riesgos.filter((r) => r.id_paquete_trabajo === q.id_paquete && abierta(r));
    return `<div class="pq-item${q.id_paquete === E.act.paquete ? ' sel' : ''}" data-id="${q.id_paquete}">
      <div class="top">
        <div class="grow"><div class="t">${numPaquete(q.id_paquete)}${q.ruta_critica ? ' <span class="chip outline mini">ruta crítica</span>' : ''}</div>
          <div class="s">${esc(q.municipio || '')} · pesa ${pct(q.peso_en_proyecto)} del proyecto</div></div>
        <span class="lvl ${q.nivel}" title="Índice de criticidad territorial">ICT ${fmt(q.ICT)}</span>
      </div>
      <div class="av-doble" title="Real ${pct(q.avance, 1)} · planeado ${pct(q.avance_plan, 1)}"><span class="plan" style="width:${q.avance_plan * 100}%"></span><span class="real" style="width:${q.avance * 100}%"></span></div>
      <div class="bot"><span>${pct(q.avance, 1)} · fin ${fCorta(q.fecha_fin_proyectada)} ${delta(q.atraso_proyectado_dias)}</span>
        <button class="link" data-riesgos="${q.id_paquete}" title="Ver los riesgos de este paquete">${ab.length} amenazas abiertas <i data-lucide="arrow-up-right"></i></button></div>
    </div>`;
  }).join('');
  document.querySelectorAll('.pq-item').forEach((el) => el.addEventListener('click', (ev) => {
    if (ev.target.closest('[data-riesgos]')) return;
    const id = el.dataset.id;
    E.act.paquete = E.act.paquete === id ? '' : id;
    if (E.act.paquete) E.abiertos.add(id);
    document.getElementById('a-paquete').value = E.act.paquete;
    renderGantt();
    renderActividades();
  }));
  document.querySelectorAll('[data-riesgos]').forEach((b) => b.addEventListener('click', () => {
    const q = paq(b.dataset.riesgos);
    irA('riesgos', { proyecto: q.id_proyecto, paquete: q.id_paquete, tipo: 'amenaza', estado: 'abierto' });
  }));
}

function renderAvanceTipos() {
  const acts = E.actividades.filter((a) => a.id_proyecto === E.proySel);
  document.getElementById('avance-tipos').innerHTML = tiposActividad().map((t) => {
    const suyas = acts.filter((a) => a.disciplina === t);
    if (!suyas.length) return '';
    const peso = suyas.reduce((s, a) => s + a.peso_en_proyecto, 0);
    const av = suyas.reduce((s, a) => s + a.peso_en_proyecto * a.avance, 0) / (peso || 1);
    return `<div class="tipo-row" title="${esc(nombreTipo(t))}">
      <div class="top"><span>${esc(t)}</span><span><b>${pct(av)}</b><span class="pct">${pct(peso)} del proyecto</span></span></div>
      <div class="meter"><span style="width:${av * 100}%"></span></div></div>`;
  }).join('');
}

document.getElementById('a-buscar').addEventListener('input', (e) => { E.act.buscar = e.target.value; renderActividades(); });
document.getElementById('a-paquete').addEventListener('change', (e) => {
  E.act.paquete = e.target.value;
  if (E.act.paquete) { E.abiertos.add(E.act.paquete); renderGantt(); }
  renderActividades();
});
document.getElementById('a-tipo').addEventListener('change', (e) => { E.act.tipo = e.target.value; renderActividades(); });
document.getElementById('a-estado').addEventListener('change', (e) => { E.act.estado = e.target.value; renderActividades(); });
document.querySelectorAll('#tabla-actividades th.sortable').forEach((th) => th.addEventListener('click', () => {
  const col = th.dataset.col;
  E.ordenAct = E.ordenAct.col === col ? { col, asc: !E.ordenAct.asc } : { col, asc: true };
  renderActividades();
}));

// ===========================================================================
// 3. RIESGOS
// ===========================================================================

function pintarRiesgos() {
  renderSelects();
  renderMatrizRam();
  renderTabla();
}

// --- Matriz RAM: amenazas abiertas (latentes o proximas a materializarse) en cada celda ----------------------------

function amenazasParaMatriz() {
  const f = E.filtro;
  return E.riesgos.filter((r) => abierta(r) && (!f.categoria || r.categoria === f.categoria) && (!f.proyecto || r.id_proyecto === f.proyecto)
    && (!f.paquete || r.id_paquete_trabajo === f.paquete) && (!f.municipio || r.municipio === f.municipio));
}

function renderMatrizRam() {
  if (!E.ram) return;
  const etapa = E.etapaRam;
  const lista = amenazasParaMatriz();
  const cuenta = contar(lista.filter((r) => r[`ram_${etapa}`]), `ram_${etapa}`);
  const letras = ['A', 'B', 'C', 'D', 'E'];
  const sel = E.filtro.ram;
  const cab = letras.map((l) => `<th title="${l}: ${E.ram.probabilidades[l]}">${l}<small>${E.ram.probabilidades[l].replace('Sucede varias veces al año', 'Varias veces al año').replace('No ha ocurrido', 'Nunca')}</small></th>`).join('');
  const textoCons = (c) => (E.ram.consecuencias ? Object.entries(E.ram.consecuencias).map(([d, t]) => `${ui.DIM_RAM[d]}: ${t[c]}`).join(' · ') : CONSECUENCIA_RAM[c]);
  const filas = [5, 4, 3, 2, 1, 0].map((c) => `<tr><th title="${textoCons(c)}">${c}</th>${letras.map((l, i) => {
    const nivel = E.ram.matriz[c][i];
    const codigo = `${c}${l}`;
    const n = cuenta[codigo] || 0;
    const r = ui.RAM[nivel];
    const esSel = sel && sel.codigo === codigo && sel.etapa === etapa;
    return `<td class="${n ? '' : 'vacia'}${esSel ? ' sel' : ''}" data-codigo="${codigo}" style="background:${r.bg};color:${r.fg}" title="${codigo} · ${r.nombre}: ${n} amenaza${n === 1 ? '' : 's'}"><span class="niv">${nivel}</span><span class="n">${n}</span></td>`;
  }).join('')}</tr>`).join('');
  document.getElementById('ram-matriz').innerHTML = `<thead><tr><th class="ram-eje" title="Consecuencia (filas) × probabilidad (columnas)">C \\ P</th>${cab}</tr></thead><tbody>${filas}</tbody>`;

  const porNivel = contar(lista.filter((r) => r[`nivel_${etapa}`]), `nivel_${etapa}`);
  document.getElementById('ram-niveles').innerHTML = ORDEN_RAM.map((n) => {
    const cfg = E.ram.niveles[n];
    const esSel = sel && sel.nivel === n && sel.etapa === etapa;
    return `<button class="ram-nivel${esSel ? ' sel' : ''}" data-nivel="${n}">
      ${ui.ramChip(n)}<span class="t">${ui.RAM[n].nombre}</span><span class="n">${porNivel[n] || 0}</span>
      <span class="d">${cfg.decision}. Aprueba: ${cfg.aprueba.replace(/\.$/, '')}.</span></button>`;
  }).join('');

  const f = E.filtro;
  const ambito = f.paquete ? nombrePaquete(f.paquete) : f.proyecto ? nombreProy(f.proyecto) : f.municipio || 'todo el portafolio';
  document.getElementById('sub-ram').textContent = `${lista.length} amenazas abiertas de ${ambito} · ${etapa === 'residual' ? 'con los controles actuales' : 'sin controles'} · clic en una celda o un nivel para filtrar el registro`;
  const v = E.ram.version || {};
  document.getElementById('ram-fuente').innerHTML = (v.tipo === 'personalizada'
    ? `<b>Matriz personalizada</b> (editada el ${ui.fecha(v.editado_en)}${v.editado_por ? ` por ${esc(v.editado_por)}` : ''}${v.nota ? `: ${esc(v.nota)}` : ''}), basada en ${E.ram.fuente}.`
    : `Escalas y matriz: ${E.ram.fuente}.`) + ' Manda la peor de las cinco dimensiones. <a href="matriz.html">Ajustar la matriz</a>. Datos sintéticos.';

  document.querySelectorAll('#ram-matriz td').forEach((td) => td.addEventListener('click', () => {
    const codigo = td.dataset.codigo;
    E.filtro.ram = sel && sel.codigo === codigo && sel.etapa === etapa ? null : { codigo, etapa };
    renderMatrizRam();
    renderTabla();
  }));
  document.querySelectorAll('.ram-nivel').forEach((b) => b.addEventListener('click', () => {
    const nivel = b.dataset.nivel;
    E.filtro.ram = sel && sel.nivel === nivel && sel.etapa === etapa ? null : { nivel, etapa };
    renderMatrizRam();
    renderTabla();
  }));
  ui.icons();
}

const pasaRam = (r) => {
  const f = E.filtro.ram;
  if (!f) return true;
  return abierta(r) && (f.codigo ? r[`ram_${f.etapa}`] === f.codigo : r[`nivel_${f.etapa}`] === f.nivel);
};

// --- Registro ------------------------------------------------------------------------------------------------------

function renderSelects() {
  const f = E.filtro;
  const opt = (v, t, sel) => `<option value="${esc(v)}"${v === sel ? ' selected' : ''}>${esc(t)}</option>`;
  const set = (id, vacio, pares, valor) => { document.getElementById(id).innerHTML = opt('', vacio, valor) + pares.map(([v, t]) => opt(v, t, valor)).join(''); };
  set('f-proyecto', 'Todos los proyectos', E.proyectos.map((p) => [p.id_proyecto, p.nombre]), f.proyecto);
  const paqs = E.paquetes.filter((q) => !f.proyecto || q.id_proyecto === f.proyecto).sort((a, b) => a.id_paquete.localeCompare(b.id_paquete));
  set('f-paquete', 'Todos los paquetes', paqs.map((q) => [q.id_paquete, ui.nombreCorto(q.nombre)]), f.paquete);
  const muns = [...new Set(E.riesgos.map((r) => r.municipio).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
  set('f-municipio', 'Todos los municipios', muns.map((m) => [m, m]), f.municipio);
  set('f-categoria', 'Todas las categorías', Object.entries(ui.CATEGORIA).filter(([k]) => k !== 'sin_clasificar').map(([k, v]) => [k, v.label]), f.categoria);
  set('f-tipo', 'Amenazas y oportunidades', [['amenaza', 'Amenazas'], ['oportunidad', 'Oportunidades']], f.tipo);
  set('f-estado', 'Todos los estados', [['abierto', 'Abiertos (latentes o próximos)'], ...Object.entries(ui.ESTADO).map(([k, v]) => [k, v.label])], f.estado);
  set('f-accion', 'Todas las acciones', Object.entries(ACCION).map(([k, v]) => [k, v.label]), f.accion);
  const tiposOpt = tiposActividad().map((t) => opt(`t:${t}`, t, f.actividad)).join('');
  const dePaquete = f.paquete ? E.actividades.filter((a) => a.id_paquete === f.paquete).sort((a, b) => a.orden - b.orden) : [];
  document.getElementById('f-actividad').innerHTML = opt('', 'Todas las actividades', f.actividad)
    + `<optgroup label="Tipo de actividad">${tiposOpt}</optgroup>`
    + (dePaquete.length ? `<optgroup label="Actividades del paquete">${dePaquete.map((a) => opt(`a:${a.id_actividad}`, `${a.orden}. ${a.nombre}`, f.actividad)).join('')}</optgroup>` : '');
  document.getElementById('f-buscar').value = f.buscar;
}

function filtrados() {
  const f = E.filtro;
  const q = normalizar(f.buscar);
  return E.riesgos.filter((r) =>
    (!f.proyecto || r.id_proyecto === f.proyecto) && (!f.paquete || r.id_paquete_trabajo === f.paquete) && (!f.municipio || r.municipio === f.municipio)
    && (!f.actividad || (f.actividad.startsWith('a:') ? r.id_actividad === f.actividad.slice(2) : disciplinaDe(r) === f.actividad.slice(2)))
    && (!f.categoria || r.categoria === f.categoria) && (!f.tipo || r.tipo === f.tipo)
    && (!f.estado || (f.estado === 'abierto' ? r.estado !== 'materializado' : r.estado === f.estado)) && (!f.accion || estadoAccion(r) === f.accion) && pasaRam(r) && (!f.ia || tocaIa(r))
    && (!q || normalizar(`${r.id_riesgo} ${r.id_paquete_trabajo} ${nombrePaquete(r.id_paquete_trabajo)} ${r.municipio || ''} ${r.actividad || ''} ${r.descripcion || ''} ${r.causa || ''} ${r.accion_tratamiento || ''}`).includes(q)));
}

// La IA del registro (plata.sinteticos) asigno la categoria o pide revisar la categoria o la ubicacion
const tocaIa = (r) => r.categoria_origen === 'ia' || r.categoria_origen === 'pendiente' || r.revisar_categoria || r.revisar_ubicacion;
function notasIa(r) {
  const notas = [];
  if (r.categoria_origen === 'ia') notas.push(`Categoría asignada por la IA (confianza ${Math.round((r.confianza_ia || 0) * 100)} %${r.palabras_ia ? `; por: ${r.palabras_ia}` : ''})`);
  if (r.categoria_origen === 'pendiente') notas.push('Sin categoría: la IA no alcanzó la confianza mínima');
  if (r.revisar_categoria) notas.push(`El texto sugiere ${ui.cat(r.categoria_ia).label.toLowerCase()} (${Math.round((r.confianza_ia || 0) * 100)} %), no ${ui.cat(r.categoria).label.toLowerCase()}`);
  if (r.revisar_ubicacion) notas.push(`Menciona ${r.municipio_mencionado}, lejos de su paquete`);
  return notas;
}
function marcaIa(r) {
  const notas = notasIa(r);
  if (!notas.length) return '';
  const revisar = r.revisar_categoria || r.revisar_ubicacion || r.categoria_origen === 'pendiente';
  return `<span class="ia-marca${revisar ? ' revisar' : ''}" title="${esc(notas.join(' · '))}"><i data-lucide="sparkles"></i>${revisar ? 'revisar' : 'IA'}</span>`;
}

function celdaAccion(r) {
  if (!r.accion_tratamiento) return '<span class="muted">Sin acción registrada</span>';
  const a = ACCION[estadoAccion(r)];
  const fecha = r.fecha_ejecucion_accion ? fCorta(r.fecha_ejecucion_accion) : 'sin fecha';
  return `<div class="acc-t">${esc(r.accion_tratamiento)}</div><div class="acc-s"><span class="dot ${a.lvl}"></span>${fecha} · ${a.corto}</div>`;
}

function renderTabla() {
  const { col, asc } = E.orden;
  const filas = filtrados().sort((a, b) => {
    const av = a[col], bv = b[col];
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv), 'es');
    return asc ? cmp : -cmp;
  });
  E.lista = filas.map((r) => r.id_riesgo);

  document.querySelector('#tabla-riesgos tbody').innerHTML = filas.map((r) => {
    const c = ui.cat(r.categoria);
    const est = ui.ESTADO[r.estado] || { label: r.estado, lvl: 'bajo' };
    return `
      <tr class="clickable${E.ficha === r.id_riesgo ? ' sel' : ''}" data-id="${r.id_riesgo}">
        <td><div class="cell-main">
          <span class="tile" style="background:${c.bg};color:${c.fg}"><i data-lucide="${c.icon}"></i></span>
          <div><div class="t">${r.id_riesgo}</div><div class="s"><span class="dot" style="background:${r.tipo === 'oportunidad' ? 'var(--navy)' : 'var(--lvl-critico)'}"></span> ${c.corto} · ${r.tipo} ${marcaIa(r)}</div></div>
        </div></td>
        <td class="desc"><div>${esc(r.descripcion)}</div></td>
        <td class="ink-2" title="${esc(r.actividad || '')}">${nombrePaquete(r.id_paquete_trabajo)}<div class="s">${esc(disciplinaDe(r) || '-')}${r.revisar_actividad ? ' <span class="ia-marca revisar">revisar</span>' : ''} · ${esc(r.municipio || '-')}</div></td>
        <td class="ink-2" title="Identificado el ${ui.fecha(fechaDe(r))}${r.revisar_fechas ? ` · Revisar: ${esc(r.problema_fechas)}` : ''}">${fMes(r.fecha_identificacion)}${r.revisar_fechas ? '<div><span class="ia-marca revisar">revisar</span></div>' : ''}</td>
        <td><span class="sev" title="${r.tipo === 'oportunidad' ? 'Oportunidad: el nivel indica el beneficio potencial' : `Sin controles ${r.ram_inherente || '-'} (${r.nivel_inherente || '-'})`}">${ui.ramChip(r.nivel_residual)}<b>${r.ram_residual || '-'}</b><span class="pxi">${ui.DIM_RAM[r.dimension_dominante] || ''}${r.ram_inherente && r.ram_inherente !== r.ram_residual ? ` · antes ${r.ram_inherente}` : ''}</span></span></td>
        <td><span class="status"><span class="dot ${est.lvl}"></span>${est.label}</span></td>
        <td class="accion">${celdaAccion(r)}</td>
      </tr>`;
  }).join('') || '<tr><td colspan="7" class="muted" style="padding:24px 12px">Ningún riesgo coincide con los filtros.</td></tr>';

  document.getElementById('n-ia').textContent = E.riesgos.filter(tocaIa).length;
  document.getElementById('f-ia').classList.toggle('on', E.filtro.ia);
  const f = E.filtro;
  const partes = [`${filas.length} de ${E.riesgos.length} riesgos`];
  if (f.proyecto && !f.paquete) partes.push(nombreProy(f.proyecto));
  if (f.paquete) partes.push(nombrePaquete(f.paquete));
  if (f.actividad) partes.push(f.actividad.startsWith('a:') ? actDe(f.actividad.slice(2))?.nombre : `actividades de ${f.actividad.slice(2).toLowerCase()}`);
  if (f.municipio) partes.push(f.municipio);
  if (f.categoria) partes.push(ui.cat(f.categoria).label);
  const vencidas = filas.filter((r) => estadoAccion(r) === 'vencida').length;
  if (vencidas) partes.push(`${vencidas} con la acción vencida`);
  partes.push('clic en una fila para ver la ficha');
  document.getElementById('sub-registro').textContent = partes.join(' · ');
  const hayFiltro = JSON.stringify({ ...f, buscar: f.buscar.trim() }) !== JSON.stringify(FILTRO_VACIO);
  document.getElementById('f-limpiar').hidden = !hayFiltro;

  const chipRam = document.getElementById('chip-ram');
  chipRam.hidden = !f.ram;
  if (f.ram) chipRam.innerHTML = `RAM ${f.ram.etapa} ${f.ram.codigo || ui.RAM[f.ram.nivel].nombre.toLowerCase()} <i data-lucide="x"></i>`;

  document.querySelectorAll('#tabla-riesgos th').forEach((th) => {
    const activo = th.dataset.col === col;
    th.classList.toggle('sorted', activo);
    th.textContent = th.textContent.replace(/ [↑↓]$/, '') + (activo ? (asc ? ' ↑' : ' ↓') : '');
  });
  document.querySelectorAll('#tabla-riesgos tbody tr[data-id]').forEach((tr) => tr.addEventListener('click', () => abrirFicha(tr.dataset.id)));
  ui.icons();
}

const alCambiar = (clave, matriz = true) => (e) => {
  E.filtro[clave] = e.target.value;
  if (clave === 'proyecto') E.filtro.paquete = '';
  if (clave === 'paquete' && e.target.value) E.filtro.proyecto = paq(e.target.value).id_proyecto;
  if ((clave === 'proyecto' || clave === 'paquete') && E.filtro.actividad.startsWith('a:')) E.filtro.actividad = '';
  if (clave === 'actividad' && e.target.value.startsWith('a:')) {
    const a = actDe(e.target.value.slice(2));
    Object.assign(E.filtro, { proyecto: a.id_proyecto, paquete: a.id_paquete });
  }
  if (['proyecto', 'paquete', 'actividad'].includes(clave)) renderSelects();
  if (matriz) renderMatrizRam();
  renderTabla();
};
document.getElementById('f-buscar').addEventListener('input', (e) => { E.filtro.buscar = e.target.value; renderTabla(); });
document.getElementById('f-proyecto').addEventListener('change', alCambiar('proyecto'));
document.getElementById('f-paquete').addEventListener('change', alCambiar('paquete'));
document.getElementById('f-municipio').addEventListener('change', alCambiar('municipio'));
document.getElementById('f-actividad').addEventListener('change', alCambiar('actividad'));
document.getElementById('f-categoria').addEventListener('change', alCambiar('categoria'));
document.getElementById('f-tipo').addEventListener('change', alCambiar('tipo', false));
document.getElementById('f-estado').addEventListener('change', alCambiar('estado', false));
document.getElementById('f-accion').addEventListener('change', alCambiar('accion', false));
document.getElementById('f-ia').addEventListener('click', () => { E.filtro.ia = !E.filtro.ia; renderTabla(); });
document.getElementById('chip-ram').addEventListener('click', () => { E.filtro.ram = null; renderMatrizRam(); renderTabla(); });
document.getElementById('f-limpiar').addEventListener('click', () => { E.filtro = { ...FILTRO_VACIO }; pintarRiesgos(); });
document.querySelectorAll('#tabla-riesgos th.sortable').forEach((th) => th.addEventListener('click', () => {
  const col = th.dataset.col;
  E.orden = E.orden.col === col ? { col, asc: !E.orden.asc } : { col, asc: col !== 'puntaje_ram' };
  renderTabla();
}));
document.querySelectorAll('#seg-ram button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-ram button').forEach((x) => x.classList.toggle('on', x === b));
  E.etapaRam = b.dataset.v;
  renderMatrizRam();
}));

// --- Ficha de un riesgo --------------------------------------------------------------------------------------------

function kv(etiqueta, valor) {
  return valor == null || valor === '' ? '' : `<div class="k">${etiqueta}</div><div class="v">${valor}</div>`;
}

function htmlFicha(r) {
  const c = ui.cat(r.categoria);
  const est = ui.ESTADO[r.estado] || { label: r.estado, lvl: '' };
  const q = paq(r.id_paquete_trabajo);
  const opor = r.tipo === 'oportunidad';
  const consecuencias = CONS.map(([d, campo]) => {
    const v = r[campo] == null ? null : Math.round(Number(r[campo]));
    const manda = r.dimension_dominante === d;
    const texto = E.ram?.consecuencias?.[d]?.[v] ?? '';
    return `<div class="cons${manda ? ' manda' : ''}" title="${esc(texto)}">
      <span class="d">${ui.DIM_RAM[d]}${manda ? ' <em>manda</em>' : ''}</span>
      <span class="pasos">${[1, 2, 3, 4, 5].map((i) => `<i class="${v != null && i <= v ? 'on' : ''}"></i>`).join('')}</span>
      <b>${v ?? '-'}</b><span class="tx">${esc(texto)}</span></div>`;
  }).join('');
  const prob = (l) => (l ? `<b>${l}</b> · ${esc(E.ram?.probabilidades?.[l] || '')}` : '-');
  const nivelCfg = E.ram?.niveles?.[r.nivel_residual];
  const acc = ACCION[estadoAccion(r)];
  const ia = notasIa(r);
  const resg = r.alcanza_resguardo, area = r.alcanza_area_protegida;
  const act = actDe(r.id_actividad);
  return `
    <div class="f-top">
      <span class="tile lg" style="background:${c.bg};color:${c.fg}"><i data-lucide="${c.icon}"></i></span>
      <div class="grow"><div class="f-id">${r.id_riesgo}<span class="muted"> · ${esc(r.id_evento_riesgo || '')}</span></div>
        <div class="f-cat">${c.label} · <span class="status"><span class="dot" style="background:${opor ? 'var(--navy)' : 'var(--lvl-critico)'}"></span>${opor ? 'Oportunidad' : 'Amenaza'}</span></div></div>
    </div>
    <h2 class="f-desc">${esc(r.descripcion)}</h2>
    <div class="chips">
      <span class="chip white"><span class="dot ${est.lvl}"></span>${est.label}</span>
      ${r.punto_crisis ? '<span class="chip warn"><i data-lucide="siren"></i>Punto de crisis</span>' : ''}
      ${resg ? '<span class="chip white"><i data-lucide="users"></i>Alcanza un resguardo</span>' : ''}
      ${area ? '<span class="chip white"><i data-lucide="trees"></i>Alcanza un área protegida</span>' : ''}
      ${ia.length ? marcaIa(r) : ''}
    </div>

    <div class="f-sec"><i data-lucide="search"></i>Causa</div>
    <p class="f-txt">${esc(r.causa) || '<span class="muted">Sin causa registrada</span>'}</p>

    <div class="f-sec"><i data-lucide="grid-3x3"></i>Calificación RAM${opor ? ' <span class="muted">(beneficio potencial)</span>' : ''}</div>
    <div class="f-ram">
      <div class="f-ram-c"><span class="l">Inherente · sin controles</span><span class="sev">${ui.ramChip(r.nivel_inherente)}<b>${r.ram_inherente || '-'}</b></span><span class="s">${r.nivel_inherente ? ui.RAM[r.nivel_inherente].nombre : ''}</span></div>
      <i data-lucide="arrow-right" class="flecha"></i>
      <div class="f-ram-c"><span class="l">Residual · con controles</span><span class="sev">${ui.ramChip(r.nivel_residual)}<b>${r.ram_residual || '-'}</b></span><span class="s">${r.nivel_residual ? ui.RAM[r.nivel_residual].nombre : ''}</span></div>
    </div>
    <div class="f-sub">Consecuencia por dimensión (0 a 5)</div>
    <div class="conss">${consecuencias}</div>
    <div class="fkv">
      ${kv('Probabilidad inherente', prob(r.probabilidad))}
      ${kv('Probabilidad residual', prob(r.probabilidad_residual))}
      ${kv('Controles', esc(r.controles) || '<span class="muted">Sin controles registrados</span>')}
      ${!opor && nivelCfg ? kv('Qué exige', `${esc(nivelCfg.decision)}. <span class="muted">Aprueba: ${esc(nivelCfg.aprueba.replace(/\.$/, ''))}.</span>`) : ''}
    </div>

    <div class="f-sec"><i data-lucide="clipboard-check"></i>Tratamiento</div>
    <div class="fkv">
      ${kv('Acción', esc(r.accion_tratamiento) || '<span class="muted">Sin acción registrada</span>')}
      ${r.accion_tratamiento ? kv('Fecha', `${fCorta(r.fecha_ejecucion_accion)} · <span class="status"><span class="dot ${acc.lvl}"></span>${acc.corto}</span>${plazoAccion(r)}`) : ''}
      ${kv('Identificado', fCorta(r.fecha_identificacion))}
      ${r.fecha_materializacion ? kv('Materializado', `${fCorta(r.fecha_materializacion)} <span class="muted">· ${fmt((dia(r.fecha_materializacion) - dia(r.fecha_identificacion)) / DIA)} días después de identificarse</span>`) : ''}
      ${r.revisar_fechas ? kv('Revisar', `<span class="lvl-soft medio">fechas</span> ${esc(r.problema_fechas)}`) : ''}
    </div>

    <div class="f-sec"><i data-lucide="map-pin"></i>Dónde</div>
    <div class="fkv">
      ${kv('Proyecto', esc(nombreProy(r.id_proyecto)))}
      ${kv('Paquete', `<button class="link" id="ficha-paquete">${q ? ui.nombreCorto(q.nombre) : esc(r.id_paquete_trabajo)} <i data-lucide="arrow-up-right"></i></button>`)}
      ${kv('Municipio', `${esc(r.municipio || '-')} <span class="muted">(por sus coordenadas)</span>`)}
      ${r.municipio_mencionado ? kv('El texto menciona', `${esc(r.municipio_mencionado)}${r.revisar_ubicacion ? ' <span class="lvl-soft medio">lejos del paquete</span>' : ''}`) : ''}
      ${kv('Coordenadas', `${fmt(r.lat, 4)}, ${fmt(r.lon, 4)}${r.geolocalizacion_inferida ? ' <span class="muted">· inferidas: centro del paquete</span>' : ''}`)}
      ${resg ? kv('Resguardo', esc(resg)) : ''}
      ${area ? kv('Área protegida', esc(area)) : ''}
      ${r.punto_crisis ? kv('Por qué es crisis', esc(r.causa_crisis)) : ''}
    </div>

    ${act ? `<div class="f-sec"><i data-lucide="list-checks"></i>Actividad afectada</div>
    <div class="fkv">
      ${kv('Actividad', `<button class="link" id="ficha-actividad">${act.orden}. ${esc(act.nombre)} <i data-lucide="arrow-up-right"></i></button>`)}
      ${kv('Cómo va', `<span class="status"><span class="dot ${ESTADO_ACT[act.estado]?.lvl || ''}"></span>${ESTADO_ACT[act.estado]?.label || act.estado}</span> · ${pct(act.avance)} · pesa ${pct(act.peso_en_paquete)} del paquete`)}
      ${kv('Ventana', `${fCorta(act.fecha_inicio_proyectada)} → ${fCorta(act.fecha_fin_proyectada)} ${delta(act.atraso_proyectado_dias)}`)}
      ${kv(r.estado === 'materializado' ? 'Cuándo' : 'Exposición', r.estado === 'materializado'
    ? `Se materializó el ${fCorta(r.fecha_materializacion)}, durante esta actividad`
    : `Puede pegar durante ${fmt(exposicionMeses(act), 1)} meses: lo que le falta a la actividad. Es el horizonte que usa el modelo de riesgo de ejecución.`)}
      ${kv('De dónde sale', `${ORIGEN_ACT[r.actividad_origen] || '-'}${r.actividad_registrada && r.actividad_origen !== 'registro' ? ` <span class="muted">· el registro decía «${esc(String(r.actividad_registrada).trim())}»</span>` : ''}`)}
      ${kv('Otras amenazas en ella', `${fmt(act.amenazas_abiertas)} abiertas${act.amenazas_altas ? ` · ${act.amenazas_altas} de RAM alta o muy alta` : ''}`)}
    </div>` : ''}

    ${q ? `<div class="f-sec"><i data-lucide="hexagon"></i>Su paquete hoy</div>
    <div class="fkv">
      ${kv('Criticidad (ICT)', `<span class="lvl ${q.nivel}">${fmt(q.ICT)} · ${ui.NIVEL[q.nivel]}</span>${q.escalamiento ? ' <span class="lvl-soft critico">en escalamiento</span>' : ''}`)}
      ${q.avance != null ? kv('Avance', `${pct(q.avance, 1)} <span class="muted">(planeado ${pct(q.avance_plan, 1)})</span>`) : ''}
      ${q.fecha_fin_proyectada ? kv('Fin proyectado', `${fCorta(q.fecha_fin_proyectada)} ${delta(q.atraso_proyectado_dias)}`) : ''}
      ${kv('Amenazas abiertas', fmt(E.riesgos.filter((x) => x.id_paquete_trabajo === q.id_paquete && abierta(x)).length))}
    </div>` : ''}

    <div class="f-sec"><i data-lucide="sparkles"></i>IA sobre el texto</div>
    <div class="fkv">
      ${kv('Categoría registrada', r.categoria_registrada ? ui.cat(r.categoria_registrada).label : '<span class="muted">vacía o ilegible</span>')}
      ${kv('La IA sugiere', r.categoria_ia ? `${ui.cat(r.categoria_ia).label} <span class="muted">(${Math.round((r.confianza_ia || 0) * 100)} % de confianza)</span>` : '-')}
      ${r.palabras_ia ? kv('Por estas palabras', esc(r.palabras_ia)) : ''}
      ${kv('Categoría final', `${c.label} <span class="muted">(${{ registro: 'la del registro', ia: 'asignada por la IA', pendiente: 'pendiente de revisar' }[r.categoria_origen] || r.categoria_origen})</span>`)}
      ${ia.length ? kv('Revisar', esc(ia.join(' · '))) : ''}
    </div>

    <div class="f-sec"><i data-lucide="file-spreadsheet"></i>Origen</div>
    <div class="fkv">${kv('Archivo', `<span class="mono">${esc(r.fuente)}</span>`)}${kv('Evento', esc(r.id_evento_riesgo))}</div>
    <p class="f-pie">Registro sintético: no es información de Ecopetrol ni de ninguna comunidad.</p>`;
}

function abrirFicha(id, { historial = true } = {}) {
  const r = E.riesgos.find((x) => x.id_riesgo === id);
  if (!r) return;
  E.ficha = id;
  if (historial) history.replaceState(null, '', `${location.pathname}#riesgos/${id}`);
  document.getElementById('ficha-cuerpo').innerHTML = htmlFicha(r);
  document.getElementById('ficha-cuerpo').scrollTop = 0;
  const i = E.lista.indexOf(id);
  document.getElementById('ficha-pos').textContent = i >= 0 ? `${i + 1} de ${E.lista.length}` : '';
  document.getElementById('ficha-prev').disabled = i <= 0;
  document.getElementById('ficha-next').disabled = i < 0 || i >= E.lista.length - 1;
  document.getElementById('ficha').hidden = false;
  document.getElementById('velo').hidden = false;
  document.querySelectorAll('#tabla-riesgos tbody tr').forEach((tr) => tr.classList.toggle('sel', tr.dataset.id === id));
  document.querySelector(`#tabla-riesgos tr[data-id="${id}"]`)?.scrollIntoView({ block: 'nearest' });
  document.getElementById('ficha-paquete')?.addEventListener('click', () => irA('proyectos', { proyecto: r.id_proyecto, paquete: r.id_paquete_trabajo }));
  document.getElementById('ficha-actividad')?.addEventListener('click', () => irA('proyectos', { proyecto: r.id_proyecto, paquete: r.id_paquete_trabajo }));
  ui.icons();
}

function cerrarFicha() {
  if (E.ficha && location.hash.startsWith('#riesgos/')) history.replaceState(null, '', `${location.pathname}#riesgos`);
  E.ficha = null;
  document.getElementById('ficha').hidden = true;
  document.getElementById('velo').hidden = true;
  document.querySelectorAll('#tabla-riesgos tbody tr.sel').forEach((tr) => tr.classList.remove('sel'));
}

function moverFicha(paso) {
  const i = E.lista.indexOf(E.ficha);
  const j = i + paso;
  if (i >= 0 && j >= 0 && j < E.lista.length) abrirFicha(E.lista[j]);
}

document.getElementById('ficha-cerrar').addEventListener('click', cerrarFicha);
document.getElementById('velo').addEventListener('click', cerrarFicha);
document.getElementById('ficha-prev').addEventListener('click', () => moverFicha(-1));
document.getElementById('ficha-next').addEventListener('click', () => moverFicha(1));
document.addEventListener('keydown', (e) => {
  if (!E.ficha || ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
  if (e.key === 'Escape') cerrarFicha();
  if (e.key === 'ArrowDown') { e.preventDefault(); moverFicha(1); }
  if (e.key === 'ArrowUp') { e.preventDefault(); moverFicha(-1); }
});

// ===========================================================================
// Arranque
// ===========================================================================

(async function iniciar() {
  const [riesgosGeo, paquetesGeo, alertas, params, cron] = await Promise.all([
    ui.json('/api/riesgos'), ui.json('/api/paquetes'), ui.json('/api/alertas'), ui.json('/api/parametros'),
    ui.json('/api/cronograma').catch(() => ({ disponible: false })),
  ]);
  E.ram = params.ram || null;
  E.riesgos = riesgosGeo.features.map((f) => f.properties);
  const cronPaq = Object.fromEntries((cron.disponible ? cron.paquetes : []).map((p) => [p.id_paquete, p]));
  E.paquetes = paquetesGeo.features.map((f) => ({ ...(cronPaq[f.properties.id_paquete] || {}), ...f.properties }));
  E.proyectos = cron.disponible ? [...cron.proyectos].sort((a, b) => a.id_proyecto.localeCompare(b.id_proyecto)) : [];
  E.actividades = cron.disponible ? cron.actividades : [];
  E.actIdx = Object.fromEntries(E.actividades.map((a) => [a.id_actividad, a]));
  E.corte = cron.fecha_corte || new Date().toISOString().slice(0, 10);
  document.getElementById('fecha-corte').textContent = ui.fecha(alertas[0]?.generada_en || new Date());

  // enlaces viejos: explorar.html?paquete=PRY-01-PT02 abre el registro de ese paquete
  const deUrl = new URLSearchParams(location.search).get('paquete');
  if (deUrl && paq(deUrl)) {
    E.filtro = { ...FILTRO_VACIO, proyecto: paq(deUrl).id_proyecto, paquete: deUrl };
    history.replaceState(null, '', `${location.pathname}#riesgos`);
  }
  mostrar(location.hash.slice(1) || 'resumen', { historial: false });
})();
