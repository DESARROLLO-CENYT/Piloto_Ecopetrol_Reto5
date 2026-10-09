/* Ajustar el modelo: pesos (directos o por AHP), umbrales, reglas de escalamiento y topes del ICT, con vista previa,
   guardado versionado y vuelta a la base. */

const M = { base: null, vigente: null, edit: null, version: null, t: null, ahp: null };

const CRIT = [
  ['severidad_riesgo', 'Severidad de los riesgos', 'Matriz RAM del registro'],
  ['vulnerabilidad_territorial', 'Vulnerabilidad del territorio', 'ANT, DANE, RUNAP, vías'],
  ['exposicion_proyecto', 'Exposición del paquete', 'Ruta crítica y amenazas que lo alcanzan'],
  ['amenazas_externas', 'Amenazas externas', 'IDEAM, CHIRPS, UNGRD, MinDefensa'],
  ['convergencia', 'Convergencia de amenazas', 'Registro + territorio'],
];
const REGLAS = [
  ['ict_critico', 'ICT desde el que un paquete escala por sí solo', 'puntos'],
  ['min_amenazas_convergentes', 'Amenazas que deben converger (con ICT alto)', 'amenazas'],
  ['min_acciones_vencidas', 'Acciones de tratamiento vencidas (con ICT alto)', 'acciones'],
  ['incremento_tendencia_alerta', 'Subida del ICT que da alerta de tendencia', 'puntos'],
  ['ventana_tendencia_dias', 'Ventana de la tendencia', 'días'],
];
const COMP = {
  vulnerabilidad_territorial: [['etnico', 'Territorio étnico (ANT)'], ['pobreza', 'Pobreza (IPM, DANE)'], ['ambiental', 'Áreas protegidas (RUNAP)'], ['acceso', 'Acceso (vías en tiempo seco)']],
  amenazas_externas: [['lluvia_reciente', 'Lluvia reciente (IDEAM)'], ['anomalia_lluvia', 'Lluvia anómala (CHIRPS)'], ['emergencias', 'Emergencias (UNGRD)'], ['seguridad', 'Delitos (MinDefensa)']],
};
const TOPES = [
  ['lluvia_mm_para_saturar', 'Lluvia que cuenta como máximo', 'mm en la ventana'],
  ['emergencias_por_ano_para_saturar', 'Emergencias que cuentan como máximo', 'por año'],
  ['delitos_100k_para_saturar', 'Delitos que cuentan como máximo', 'por 100.000 hab.'],
];
const SAATY = [[9, '9'], [7, '7'], [5, '5'], [3, '3'], [1, '1 · igual'], [1 / 3, '1/3'], [1 / 5, '1/5'], [1 / 7, '1/7'], [1 / 9, '1/9']];

const clon = (x) => JSON.parse(JSON.stringify(x));
const fmt = (v, d = 0) => (v == null ? '-' : Number(v).toLocaleString('es-CO', { maximumFractionDigits: d, minimumFractionDigits: d }));
const igual = (a, b) => Math.abs(Number(a) - Number(b)) < 1e-6;
const nivelChip = (n) => `<span class="lvl ${n}">${ui.NIVEL[n]}</span>`;

function aviso(html, tipo = 'ok') {
  const a = document.getElementById('aviso');
  a.className = `aviso ${tipo}`;
  a.innerHTML = html;
  a.hidden = !html;
  ui.icons();
}

// ---------------------------------------------------------------------------
// Pesos
// ---------------------------------------------------------------------------

function renderPesos() {
  const total = CRIT.reduce((s, [k]) => s + Number(M.edit.pesos[k] || 0), 0) || 1;
  document.getElementById('pesos-directo').innerHTML = CRIT.map(([k, n, s]) => {
    const v = Number(M.edit.pesos[k] || 0) / total * 100;
    const cambio = !igual(M.edit.pesos[k], M.base.pesos[k]);
    return `<div class="peso-fila${cambio ? ' cambio' : ''}">
      <div class="n">${n}<small>${s} · base ${fmt(M.base.pesos[k] * 100)} %</small></div>
      <input type="range" class="range" min="0" max="60" step="1" value="${Math.round(v)}" data-k="${k}" style="--val:${(v / 60) * 100}">
      <div class="v">${fmt(v)}<small> %</small></div>
    </div>`;
  }).join('');
  document.querySelectorAll('#pesos-directo input').forEach((el) => el.addEventListener('input', () => {
    M.edit.pesos[el.dataset.k] = Number(el.value) / 100;
    renderPesos();
    previaLuego();
  }));
}

function renderAhp() {
  const pares = [];
  for (let i = 0; i < CRIT.length; i += 1) for (let j = i + 1; j < CRIT.length; j += 1) pares.push([i, j]);
  M.ahp ??= Object.fromEntries(pares.map(([i, j]) => [`${i}-${j}`, 1]));
  document.getElementById('ahp-pares').innerHTML = pares.map(([i, j]) => `
    <div class="ahp-par"><span>${CRIT[i][1]}</span>
      <select class="field" data-par="${i}-${j}">${SAATY.map(([v, t]) => `<option value="${v}"${igual(v, M.ahp[`${i}-${j}`]) ? ' selected' : ''}>${t}</option>`).join('')}</select>
      <span class="der">${CRIT[j][1]}</span></div>`).join('');
  document.querySelectorAll('#ahp-pares select').forEach((s) => s.addEventListener('change', () => { M.ahp[s.dataset.par] = Number(s.value); }));
}

async function calcularAhp() {
  const n = CRIT.length;
  const m = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (__, j) => (i === j ? 1 : null)));
  Object.entries(M.ahp).forEach(([par, v]) => {
    const [i, j] = par.split('-').map(Number);
    m[i][j] = v;
    m[j][i] = 1 / v;
  });
  const r = await fetch('/api/modelo/ahp', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ matriz: m }) });
  const d = await r.json();
  if (!r.ok) { document.getElementById('ahp-res').textContent = d.detail; return; }
  document.getElementById('ahp-res').innerHTML = `
    <span class="lvl-soft ${d.consistente ? 'bajo' : 'alto'}">CR ${fmt(d.razon_consistencia, 3)} · ${d.consistente ? 'consistente' : 'revisar los juicios'}</span>
    ${CRIT.map(([k, nombre]) => `<span class="chip white">${nombre.split(' ')[0]} ${fmt(d.pesos[k] * 100)} %</span>`).join(' ')}
    <button class="btn btn-primary sm" id="b-usar-ahp"><i data-lucide="check"></i> Usar estos pesos</button>`;
  ui.icons();
  document.getElementById('b-usar-ahp').addEventListener('click', () => {
    M.edit.pesos = { ...d.pesos };
    document.querySelector('#seg-pesos [data-v="directo"]').click();
    previaLuego();
  });
}

document.querySelectorAll('#seg-pesos button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-pesos button').forEach((x) => x.classList.toggle('on', x === b));
  document.getElementById('pesos-directo').hidden = b.dataset.v !== 'directo';
  document.getElementById('pesos-ahp').hidden = b.dataset.v !== 'ahp';
  if (b.dataset.v === 'directo') renderPesos(); else renderAhp();
}));
document.getElementById('b-ahp').addEventListener('click', calcularAhp);

// ---------------------------------------------------------------------------
// Umbrales, reglas y componentes (campos numericos que marcan lo que cambia frente a la base)
// ---------------------------------------------------------------------------

function campo(ruta, etiqueta, ayuda, valor, base, paso = 'any') {
  const cambio = base != null && !igual(valor, base);
  return `<label class="campo"><span>${etiqueta}${ayuda ? `<small>${ayuda}${base != null ? ` · base ${fmt(base, paso === 'any' ? 2 : 0)}` : ''}</small>` : ''}</span>
    <input class="field${cambio ? ' cambio' : ''}" type="number" step="${paso}" data-ruta="${ruta}" value="${valor ?? ''}"></label>`;
}
const leer = (obj, ruta) => ruta.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
function poner(obj, ruta, v) {
  const p = ruta.split('.');
  let o = obj;
  p.slice(0, -1).forEach((k) => { o[k] ??= {}; o = o[k]; });
  o[p[p.length - 1]] = v;
}

function renderUmbrales() {
  const u = M.edit.umbrales_criticidad;
  const tramos = [['bajo', 0, u.bajo], ['medio', u.bajo, u.medio], ['alto', u.medio, u.alto], ['critico', u.alto, 100]];
  document.getElementById('umbrales').innerHTML = `
    <div class="bloque-t">Niveles del ICT</div>
    <div class="escala-ict">${tramos.map(([n, a, b]) => `<span title="${ui.NIVEL[n]}: ${a} a ${b}" style="width:${Math.max(0, b - a)}%;background:var(--lvl-${n})"></span>`).join('')}</div>
    ${campo('umbrales_criticidad.bajo', 'Desde aquí es medio', 'ICT', u.bajo, M.base.umbrales_criticidad.bajo, 1)}
    ${campo('umbrales_criticidad.medio', 'Desde aquí es alto', 'ICT', u.medio, M.base.umbrales_criticidad.medio, 1)}
    ${campo('umbrales_criticidad.alto', 'Desde aquí es crítico', 'ICT', u.alto, M.base.umbrales_criticidad.alto, 1)}`;
  const e = M.edit.escalamiento;
  document.getElementById('reglas').innerHTML = `
    <div class="bloque-t">Reglas de escalamiento a crisis</div>
    ${REGLAS.map(([k, n, unidad]) => campo(`escalamiento.${k}`, n, unidad, e[k], M.base.escalamiento[k], 1)).join('')}
    <label class="campo sw"><span>Riesgo alto que alcanza un resguardo o un área protegida<small>regla sobre el territorio real</small></span>
      <span class="switch"><input type="checkbox" id="sw-sensible"${e.riesgo_en_area_sensible ? ' checked' : ''}><span></span></span></label>
    <p class="nota">Las reglas de la matriz RAM (VH, o H en ruta crítica) se cambian en <a href="matriz.html">Matriz RAM</a>.</p>`;
  document.getElementById('sw-sensible').addEventListener('change', (ev) => { M.edit.escalamiento.riesgo_en_area_sensible = ev.target.checked; previaLuego(); });
}

function renderComponentes() {
  const c = M.edit.criterios, b = M.base.criterios;
  const bloque = (crit, titulo) => `
    <div class="bloque-t">${titulo}</div>
    ${COMP[crit].map(([k, n]) => campo(`criterios.${crit}.componentes.${k}`, n, 'peso dentro del criterio', c[crit].componentes[k], b[crit].componentes[k])).join('')}`;
  const f = M.edit.factores_estado, fb = M.base.factores_estado;
  document.getElementById('componentes').innerHTML = `
    ${bloque('vulnerabilidad_territorial', 'Vulnerabilidad del territorio')}
    ${bloque('amenazas_externas', 'Amenazas externas')}
    ${TOPES.map(([k, n, u]) => campo(`criterios.amenazas_externas.${k}`, n, u, c.amenazas_externas[k], b.amenazas_externas[k])).join('')}
    <div class="bloque-t">Factor de severidad según el estado del riesgo</div>
    ${campo('factores_estado.latente', 'Latente', '×', f.latente, fb.latente)}
    ${campo('factores_estado.proximo_a_materializarse', 'Próximo a materializarse', '×', f.proximo_a_materializarse, fb.proximo_a_materializarse)}
    ${campo('factores_estado.materializado', 'Materializado', '×', f.materializado, fb.materializado)}`;
}

function enlazarCampos() {
  document.querySelectorAll('[data-ruta]').forEach((el) => el.addEventListener('change', () => {
    if (el.value === '') return;
    poner(M.edit, el.dataset.ruta, Number(el.value));
    el.classList.toggle('cambio', !igual(el.value, leer(M.base, el.dataset.ruta)));
    if (el.dataset.ruta.startsWith('umbrales')) { renderUmbrales(); enlazarCampos(); }
    previaLuego();
  }));
}

// ---------------------------------------------------------------------------
// Vista previa
// ---------------------------------------------------------------------------

function previaLuego() {
  clearTimeout(M.t);
  M.t = setTimeout(previa, 350);
}

async function previa() {
  try {
    const r = await fetch('/api/modelo/vista_previa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cambios: M.edit }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
    document.getElementById('sub-previa').textContent = `${d.cambian_de_nivel} paquete(s) cambian de nivel · ${d.en_escalamiento} en escalamiento · sin guardar`;
    document.querySelector('#tabla-previa tbody').innerHTML = d.paquetes.map((p) => {
      const dl = p.ict - (p.ict_actual ?? p.ict);
      const delta = Math.abs(dl) >= 0.05 ? `<span class="delta ${dl > 0 ? 'sube' : 'baja'}">${dl > 0 ? '+' : ''}${fmt(dl, 1)}</span>` : '';
      const nivel = p.nivel === p.nivel_actual ? nivelChip(p.nivel) : `${nivelChip(p.nivel_actual)}<span class="flecha">→</span>${nivelChip(p.nivel)}`;
      const esc = p.escala ? `<i data-lucide="siren" class="escala-si" title="${p.causas || ''}"></i>` : '<span class="escala-no">-</span>';
      return `<tr><td>${ui.nombreCorto(p.nombre)}</td><td><b>${fmt(p.ict, 1)}</b>${delta}</td><td>${nivel}</td><td>${esc}${p.escala !== p.escala_actual ? ' <span class="delta sube">cambia</span>' : ''}</td></tr>`;
    }).join('');
    document.getElementById('advertencias').innerHTML = (d.advertencias || []).map((a) => `<div>${a}</div>`).join('');
    ui.icons();
  } catch (e) {
    aviso(`<i data-lucide="x"></i> ${e.message}`, 'error');
  }
}

// ---------------------------------------------------------------------------
// Guardar, volver a la base e historial
// ---------------------------------------------------------------------------

function renderVersion() {
  const v = M.version || {};
  document.getElementById('chip-version').innerHTML = v.tipo === 'personalizado'
    ? `<i data-lucide="pencil"></i> Personalizado${v.editado_en ? ` · ${ui.fecha(v.editado_en)}` : ''}${v.editado_por ? ` · ${v.editado_por}` : ''}`
    : `<i data-lucide="git-branch"></i> Base de parametros.yaml · v${v.version || ''}`;
}

function renderHistorial(h) {
  const QUE = { modelo: 'Modelo ICT', ram: 'Matriz RAM', ejecucion: 'Riesgo de ejecución' };
  document.querySelector('#tabla-historial tbody').innerHTML = (h || []).map((x) => `
    <tr><td>${new Date(x.fecha).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</td>
      <td>${QUE[x.componente] || x.componente}</td><td>${x.accion}</td><td>${x.autor || '<span class="muted">-</span>'}</td><td class="wrap">${x.nota || '<span class="muted">-</span>'}</td></tr>`).join('')
    || '<tr><td colspan="5" class="muted">Aún no hay versiones guardadas: se usan los parámetros base.</td></tr>';
}

async function seguirRecalculo() {
  const t = await ui.json('/api/ram/recalcular');
  if (t.estado === 'corriendo') {
    aviso(`<i data-lucide="loader"></i> Recalculando el ICT, el escalamiento y las alertas: ${t.hechos?.length || 0} de ${t.pasos?.length || 0} pasos…`, 'info');
    setTimeout(seguirRecalculo, 1500);
    return;
  }
  if (t.estado === 'listo') aviso(`<i data-lucide="check"></i> Listo en ${t.segundos} s: el mapa, Explorar y las alertas ya usan estos parámetros.`);
  else aviso(`<i data-lucide="x"></i> El recálculo terminó con avisos en: ${(t.fallos || []).join(', ')}`, 'error');
  await cargar();
}

document.getElementById('b-guardar').addEventListener('click', async () => {
  try {
    const r = await ui.escribir('/api/modelo', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cambios: M.edit, editado_por: document.getElementById('f-autor').value, nota: document.getElementById('f-nota').value }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
    seguirRecalculo();
  } catch (e) { aviso(`<i data-lucide="x"></i> ${e.message}`, 'error'); }
});
document.getElementById('b-base').addEventListener('click', async () => {
  if (!window.confirm('¿Volver a los parámetros base de parametros.yaml? La versión personalizada queda en el historial.')) return;
  const r = await ui.escribir('/api/modelo', { method: 'DELETE' });
  const d = await r.json();
  if (r.ok) seguirRecalculo(); else aviso(`<i data-lucide="x"></i> ${d.detail || 'No se pudo volver a la base'}`, 'error');
});
document.getElementById('b-deshacer').addEventListener('click', () => {
  M.edit = clon(M.vigente);
  renderTodo();
  previa();
});

function renderTodo() {
  renderVersion();
  renderPesos();
  renderUmbrales();
  renderComponentes();
  enlazarCampos();
  ui.icons();
}

async function cargar() {
  const d = await ui.json('/api/modelo');
  M.base = d.base;
  M.vigente = d.vigente;
  M.edit = clon(d.vigente);
  M.version = d.version;
  renderTodo();
  renderHistorial(d.historial);
  previa();
}

cargar();
