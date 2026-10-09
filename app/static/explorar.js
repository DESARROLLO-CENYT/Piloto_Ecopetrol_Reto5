/* Explorar datos (layout de Ejemplo_1). DATOS SINTETICOS. */

const E = {
  riesgos: [],
  paquetes: [],
  filtro: { buscar: '', categoria: '', estado: '', accion: '', ia: false, paquete: new URLSearchParams(location.search).get('paquete') || '', ram: null },
  tipoGrafico: '',
  orden: { col: 'puntaje_ram', asc: false },
  chartCat: null,
  ram: null,             // configuracion de la matriz RAM (parametros.yaml)
  etapaRam: 'residual',  // residual (con controles) | inherente (sin controles)
};

// Escalas de consecuencia del instructivo ECP-DRI-I-007 (para los encabezados de la matriz)
const CONSECUENCIA_RAM = {
  5: 'Personas: una o más fatalidades · Económica: más de USD 10 M · Ambiental: contaminación irreparable · Clientes: veto como proveedor · Imagen: internacional',
  4: 'Personas: incapacidad permanente · Económica: USD 1 M a 10 M · Ambiental: contaminación mayor · Clientes: pérdida de mercado · Imagen: nacional',
  3: 'Personas: incapacidad temporal (> 1 día) · Económica: USD 100 mil a 1 M · Ambiental: contaminación localizada · Clientes: pérdida de clientes · Imagen: regional',
  2: 'Personas: lesión menor sin incapacidad · Económica: USD 10 mil a 100 mil · Ambiental: efecto menor · Clientes: quejas o reclamos · Imagen: local',
  1: 'Personas: primeros auxilios · Económica: menos de USD 10 mil · Ambiental: efecto leve · Clientes: incumplir especificaciones · Imagen: interna',
  0: 'Ninguna consecuencia',
};
const ORDEN_RAM = ['VH', 'H', 'M', 'L', 'N'];

const DIA = 24 * 3600 * 1000;
const fechaDe = (r) => new Date(String(r.fecha_identificacion).slice(0, 10) + 'T00:00:00');
const normalizar = (t) => (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const nombrePaquete = (id) => ui.tagCorto(E.paquetes.find((p) => p.id_paquete === id)?.nombre || id);

// ---------------------------------------------------------------------------
// Tarjetas de resumen
// ---------------------------------------------------------------------------

function renderResumen(alertas) {
  const icts = E.paquetes.map((p) => p.ICT);
  document.getElementById('ict-prom').innerHTML = `${ui.num(icts.reduce((a, b) => a + b, 0) / icts.length)}<span class="unit" style="font-size:var(--fs-18)"> / 100</span>`;
  document.getElementById('ict-paquetes').textContent = `${E.paquetes.length} paquetes de trabajo`;
  const esc = E.paquetes.filter((p) => p.escalamiento).length;
  document.getElementById('ict-escalamiento').textContent = `${esc} en escalamiento · ${alertas.length} alertas`;

  const hoy = new Date();
  const ult7 = E.riesgos.filter((r) => hoy - fechaDe(r) <= 7 * DIA).length;
  const prev7 = E.riesgos.filter((r) => hoy - fechaDe(r) > 7 * DIA && hoy - fechaDe(r) <= 14 * DIA).length;
  document.getElementById('n-riesgos').textContent = E.riesgos.length;
  document.getElementById('trend-riesgos').textContent = `+${ult7} esta semana`;
  document.getElementById('n-amenazas').textContent = E.riesgos.filter((r) => r.tipo === 'amenaza').length;
  document.getElementById('n-oport').textContent = E.riesgos.filter((r) => r.tipo === 'oportunidad').length;

  document.getElementById('n-semana').textContent = ult7;
  const delta = ult7 - prev7;
  const tr = document.getElementById('trend-semana');
  tr.textContent = `${delta >= 0 ? '+' : ''}${delta} vs. semana previa`;
  tr.className = `trend ${delta > 0 ? 'down' : delta < 0 ? '' : 'flat'}`;
}

function renderEstados() {
  const total = E.riesgos.length;
  document.getElementById('estados').innerHTML = Object.entries(ui.ESTADO).map(([k, v]) => {
    const n = E.riesgos.filter((r) => r.estado === k).length;
    const pct = total ? (n / total) * 100 : 0;
    return `
      <div class="estado-row">
        <div class="top"><span class="status"><span class="dot ${v.lvl}"></span>${v.label}</span><span><b>${n}</b><span class="pct">${pct.toFixed(0)}%</span></span></div>
        <div class="meter"><span style="width:${pct}%;background:var(--lvl-${v.lvl})"></span></div>
      </div>`;
  }).join('');
}

// ---------------------------------------------------------------------------
// Graficos
// ---------------------------------------------------------------------------

function opcionesBarras() {
  return {
    maintainAspectRatio: false,
    layout: { padding: { top: 30 } },
    onHover: (e, els) => { e.native.target.style.cursor = els.length ? 'pointer' : 'default'; },
    onClick: (e, els) => {
      if (!els.length) return;
      const clave = E.chartCat.$claves[els[0].index];
      E.filtro.categoria = E.filtro.categoria === clave ? '' : clave;
      document.getElementById('f-categoria').value = E.filtro.categoria;
      renderMatrizRam();
      renderTabla();
    },
    plugins: { legend: { display: false }, tooltip: ui.tooltip() },
    scales: {
      x: { grid: { display: false }, border: { display: false }, ticks: { color: ui.css('--muted') } },
      y: {
        beginAtZero: true, grid: { color: ui.css('--line') }, border: { display: false, dash: [4, 4] },
        ticks: { color: ui.css('--muted'), maxTicksLimit: 5, precision: 0 },
      },
    },
  };
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
    labels: claves.map((k) => ui.cat(k).corto),
    datasets: [{
      data: valores, backgroundColor: valores.map((v) => (v === max ? top : base)),
      borderRadius: 999, borderSkipped: false, barPercentage: 0.78, categoryPercentage: 0.9,
    }],
  };
  if (E.chartCat) {
    E.chartCat.data = data;
    E.chartCat.$claves = claves;
    E.chartCat.update();
    return;
  }
  E.chartCat = new Chart(canvas, { type: 'bar', data, options: opcionesBarras(), plugins: [ui.bubblePlugin] });
  E.chartCat.$claves = claves;
}

function renderChartSemanas() {
  const semanas = 20;
  const fin = new Date();
  const conteo = new Array(semanas).fill(0);
  E.riesgos.forEach((r) => {
    const idx = semanas - 1 - Math.floor((fin - fechaDe(r)) / (7 * DIA));
    if (idx >= 0 && idx < semanas) conteo[idx] += 1;
  });
  const labels = conteo.map((_, i) => new Date(fin - (semanas - 1 - i) * 7 * DIA).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }));
  const canvas = document.getElementById('chart-semanas');
  const ctx = canvas.getContext('2d');
  const verde = ui.css('--green-600');
  const g = ctx.createLinearGradient(0, 0, 0, canvas.parentElement.clientHeight || 150);
  g.addColorStop(0, ui.alpha(verde, 0.3));
  g.addColorStop(1, ui.alpha(verde, 0));
  new Chart(canvas, {
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

// ---------------------------------------------------------------------------
// Matriz RAM: amenazas abiertas (latentes o proximas a materializarse) en cada celda
// ---------------------------------------------------------------------------

function amenazasParaMatriz() {
  const f = E.filtro;
  return E.riesgos.filter((r) => r.tipo === 'amenaza' && r.estado !== 'materializado'
    && (!f.categoria || r.categoria === f.categoria) && (!f.paquete || r.id_paquete_trabajo === f.paquete));
}

function renderMatrizRam() {
  if (!E.ram) return;
  const etapa = E.etapaRam;
  const lista = amenazasParaMatriz();
  const cuenta = {};
  lista.forEach((r) => { const c = r[`ram_${etapa}`]; if (c) cuenta[c] = (cuenta[c] || 0) + 1; });
  const letras = ['A', 'B', 'C', 'D', 'E'];
  const sel = E.filtro.ram;
  const cab = letras.map((l) => `<th title="${l}: ${E.ram.probabilidades[l]}">${l}<small>${E.ram.probabilidades[l].replace('Sucede varias veces al año', 'Varias veces al año').replace('No ha ocurrido', 'Nunca')}</small></th>`).join('');  const textoCons = (c) => (E.ram.consecuencias
    ? Object.entries(E.ram.consecuencias).map(([d, t]) => `${ui.DIM_RAM[d]}: ${t[c]}`).join(' · ') : CONSECUENCIA_RAM[c]);
  const filas = [5, 4, 3, 2, 1, 0].map((c) => `<tr><th title="${textoCons(c)}">${c}</th>${letras.map((l, i) => {
    const nivel = E.ram.matriz[c][i];
    const codigo = `${c}${l}`;
    const n = cuenta[codigo] || 0;
    const r = ui.RAM[nivel];
    const esSel = sel && sel.codigo === codigo && sel.etapa === etapa;
    return `<td class="${n ? '' : 'vacia'}${esSel ? ' sel' : ''}" data-codigo="${codigo}" style="background:${r.bg};color:${r.fg}" title="${codigo} · ${r.nombre}: ${n} amenaza${n === 1 ? '' : 's'}"><span class="niv">${nivel}</span><span class="n">${n}</span></td>`;
  }).join('')}</tr>`).join('');
  document.getElementById('ram-matriz').innerHTML = `<thead><tr><th class="ram-eje" title="Consecuencia (filas) × probabilidad (columnas)">C \\ P</th>${cab}</tr></thead><tbody>${filas}</tbody>`;

  const porNivel = {};
  lista.forEach((r) => { const n = r[`nivel_${etapa}`]; if (n) porNivel[n] = (porNivel[n] || 0) + 1; });
  document.getElementById('ram-niveles').innerHTML = ORDEN_RAM.map((n) => {
    const cfg = E.ram.niveles[n];
    const esSel = sel && sel.nivel === n && sel.etapa === etapa;
    return `<button class="ram-nivel${esSel ? ' sel' : ''}" data-nivel="${n}" style="background:${esSel ? 'var(--surface-muted)' : 'transparent'};cursor:pointer;text-align:left">
      ${ui.ramChip(n)}<span class="t">${ui.RAM[n].nombre}</span><span class="n">${porNivel[n] || 0}</span>
      <span class="d">${cfg.decision}. Aprueba: ${cfg.aprueba.replace(/\.$/, '')}.</span></button>`;
  }).join('');

  const ambito = E.filtro.paquete ? nombrePaquete(E.filtro.paquete) : 'todo el portafolio';
  document.getElementById('sub-ram').textContent = `${lista.length} amenazas abiertas de ${ambito} · ${etapa === 'residual' ? 'con los controles actuales' : 'sin controles'} · clic en una celda o un nivel para filtrar el registro`;
  const v = E.ram.version || {};
  document.getElementById('ram-fuente').innerHTML = (v.tipo === 'personalizada'
    ? `<b>Matriz personalizada</b> (editada el ${ui.fecha(v.editado_en)}${v.editado_por ? ` por ${v.editado_por}` : ''}${v.nota ? `: ${v.nota}` : ''}), basada en ${E.ram.fuente}.`
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
  return f.codigo ? r[`ram_${f.etapa}`] === f.codigo && r.tipo === 'amenaza' && r.estado !== 'materializado'
    : r[`nivel_${f.etapa}`] === f.nivel && r.tipo === 'amenaza' && r.estado !== 'materializado';
};

// ---------------------------------------------------------------------------
// Registro de riesgos
// ---------------------------------------------------------------------------

function renderSelects() {
  const cat = document.getElementById('f-categoria');
  cat.innerHTML = '<option value="">Todas las categorías</option>' +
    Object.entries(ui.CATEGORIA).filter(([k]) => k !== 'sin_clasificar').map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('');
  const est = document.getElementById('f-estado');
  est.innerHTML = '<option value="">Todos los estados</option>' +
    Object.entries(ui.ESTADO).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('');
  const acc = document.getElementById('f-accion');
  acc.innerHTML = '<option value="">Todas las acciones</option>' +
    Object.entries(ACCION).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('');
}

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

function filtrados() {
  const f = E.filtro;
  const q = normalizar(f.buscar);
  return E.riesgos.filter((r) =>
    (!f.categoria || r.categoria === f.categoria) &&
    (!f.estado || r.estado === f.estado) && (!f.accion || estadoAccion(r) === f.accion) &&
    (!f.paquete || r.id_paquete_trabajo === f.paquete) && pasaRam(r) && (!f.ia || tocaIa(r)) &&
    (!q || normalizar(`${r.id_riesgo} ${r.id_paquete_trabajo} ${nombrePaquete(r.id_paquete_trabajo)} ${r.descripcion || ''} ${r.causa || ''} ${r.accion_tratamiento || ''}`).includes(q)));
}

// La IA del registro (plata.sinteticos) asigno la categoria o pide revisar la categoria o la ubicacion
const tocaIa = (r) => r.categoria_origen === 'ia' || r.categoria_origen === 'pendiente' || r.revisar_categoria || r.revisar_ubicacion;
function marcaIa(r) {
  const notas = [];
  if (r.categoria_origen === 'ia') notas.push(`Categoría asignada por la IA (confianza ${Math.round((r.confianza_ia || 0) * 100)} %${r.palabras_ia ? `; por: ${r.palabras_ia}` : ''})`);
  if (r.categoria_origen === 'pendiente') notas.push('Sin categoría: la IA no alcanzó la confianza mínima');
  if (r.revisar_categoria) notas.push(`El texto sugiere ${ui.cat(r.categoria_ia).label.toLowerCase()} (${Math.round((r.confianza_ia || 0) * 100)} %), no ${ui.cat(r.categoria).label.toLowerCase()}`);
  if (r.revisar_ubicacion) notas.push(`Menciona ${r.municipio_mencionado}, lejos de su paquete`);
  if (!notas.length) return '';
  const revisar = r.revisar_categoria || r.revisar_ubicacion || r.categoria_origen === 'pendiente';
  return `<span class="ia-marca${revisar ? ' revisar' : ''}" title="${notas.join(' · ')}"><i data-lucide="sparkles"></i>${revisar ? 'revisar' : 'IA'}</span>`;
}

function celdaAccion(r) {
  if (!r.accion_tratamiento) return '<span class="muted">Sin acción registrada</span>';
  const a = ACCION[estadoAccion(r)];
  const fecha = r.fecha_ejecucion_accion ? ui.fecha(String(r.fecha_ejecucion_accion).slice(0, 10) + 'T12:00:00') : 'sin fecha';
  return `<div class="acc-t" title="${r.accion_tratamiento.replace(/"/g, '&quot;')}">${r.accion_tratamiento}</div>
    <div class="acc-s"><span class="dot ${a.lvl}"></span>${fecha} · ${a.corto}</div>`;
}

function renderTabla() {
  const { col, asc } = E.orden;
  const filas = filtrados().sort((a, b) => {
    const av = a[col], bv = b[col];
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv));
    return asc ? cmp : -cmp;
  });

  document.querySelector('#tabla-riesgos tbody').innerHTML = filas.map((r) => {
    const c = ui.cat(r.categoria);
    const est = ui.ESTADO[r.estado] || { label: r.estado, lvl: 'bajo' };
    return `
      <tr>
        <td><div class="cell-main">
          <span class="tile" style="background:${c.bg};color:${c.fg}"><i data-lucide="${c.icon}"></i></span>
          <div><div class="t">${r.id_riesgo}</div><div class="s">${c.label} ${marcaIa(r)}</div></div>
        </div></td>
        <td class="ink-2">${nombrePaquete(r.id_paquete_trabajo)}</td>
        <td class="ink-2">${ui.fecha(fechaDe(r))}</td>
        <td><span class="sev" title="${r.tipo === 'oportunidad' ? 'Oportunidad: el nivel indica el beneficio potencial' : `Sin controles ${r.ram_inherente || '-'} (${r.nivel_inherente || '-'}); controles: ${r.controles || '-'}`}">${ui.ramChip(r.nivel_residual)}<b>${r.ram_residual || '-'}</b><span class="pxi">${ui.DIM_RAM[r.dimension_dominante] || ''}${r.ram_inherente && r.ram_inherente !== r.ram_residual ? ` · antes ${r.ram_inherente}` : ''}</span></span></td>
        <td><span class="status"><span class="dot ${est.lvl}"></span>${est.label}</span></td>
        <td class="accion">${celdaAccion(r)}</td>
        <td><span class="status"><span class="dot" style="background:${r.tipo === 'oportunidad' ? 'var(--navy)' : 'var(--lvl-critico)'}"></span>${r.tipo === 'oportunidad' ? 'Oportunidad' : 'Amenaza'}</span></td>
      </tr>`;
  }).join('') || '<tr><td colspan="7" class="muted" style="padding:24px 12px">Ningún riesgo coincide con los filtros.</td></tr>';

  document.getElementById('n-ia').textContent = E.riesgos.filter(tocaIa).length;
  document.getElementById('f-ia').classList.toggle('on', E.filtro.ia);
  const partes = [`${filas.length} de ${E.riesgos.length} riesgos`];
  if (E.filtro.categoria) partes.push(ui.cat(E.filtro.categoria).label);
  const vencidas = filas.filter((r) => estadoAccion(r) === 'vencida').length;
  if (vencidas) partes.push(`${vencidas} con la acción vencida`);
  document.getElementById('sub-registro').textContent = partes.join(' · ');

  const chip = document.getElementById('chip-paquete');
  chip.hidden = !E.filtro.paquete;
  if (E.filtro.paquete) chip.innerHTML = `${nombrePaquete(E.filtro.paquete)} <i data-lucide="x"></i>`;
  const chipRam = document.getElementById('chip-ram');
  const fr = E.filtro.ram;
  chipRam.hidden = !fr;
  if (fr) chipRam.innerHTML = `RAM ${fr.etapa} ${fr.codigo || ui.RAM[fr.nivel].nombre.toLowerCase()} <i data-lucide="x"></i>`;

  document.querySelectorAll('#tabla-riesgos th').forEach((th) => {
    const activo = th.dataset.col === col;
    th.classList.toggle('sorted', activo);
    th.textContent = th.textContent.replace(/ [↑↓]$/, '') + (activo ? (asc ? ' ↑' : ' ↓') : '');
  });
  document.querySelectorAll('.pq-row').forEach((b) => b.classList.toggle('sel', b.dataset.id === E.filtro.paquete));
  ui.icons();
}

function renderPaquetes() {
  const filas = [...E.paquetes].sort((a, b) => b.ICT - a.ICT);
  document.getElementById('lista-paquetes').innerHTML = filas.map((p) => {
    const t = p.tendencia_delta;
    const tend = t == null || t === 0 ? 'sin cambio' : `${t > 0 ? '+' : ''}${t} en 7 días`;
    return `
      <button class="pq-row" data-id="${p.id_paquete}">
        <span class="lvl ${p.nivel}">${ui.NIVEL[p.nivel]}</span>
        <div class="grow">
          <div class="t">${ui.nombreCorto(p.nombre)}</div>
          <div class="s">${p.escalamiento ? '<span class="alerta">En escalamiento</span> · ' : ''}Tendencia ${tend}</div>
        </div>
        <div class="num sm">${ui.num(p.ICT)}</div>
      </button>`;
  }).join('');
  document.querySelectorAll('.pq-row').forEach((b) => b.addEventListener('click', () => {
    E.filtro.paquete = E.filtro.paquete === b.dataset.id ? '' : b.dataset.id;
    sincronizarURL();
    renderMatrizRam();
    renderTabla();
  }));
}

function sincronizarURL() {
  const url = new URL(location.href);
  if (E.filtro.paquete) url.searchParams.set('paquete', E.filtro.paquete); else url.searchParams.delete('paquete');
  history.replaceState(null, '', url);
}

// ---------------------------------------------------------------------------
// Eventos
// ---------------------------------------------------------------------------

document.getElementById('f-buscar').addEventListener('input', (e) => { E.filtro.buscar = e.target.value; renderTabla(); });
document.getElementById('f-categoria').addEventListener('change', (e) => { E.filtro.categoria = e.target.value; renderMatrizRam(); renderTabla(); });
document.getElementById('f-estado').addEventListener('change', (e) => { E.filtro.estado = e.target.value; renderTabla(); });
document.getElementById('f-accion').addEventListener('change', (e) => { E.filtro.accion = e.target.value; renderTabla(); });
document.getElementById('f-ia').addEventListener('click', () => { E.filtro.ia = !E.filtro.ia; renderTabla(); });
document.getElementById('chip-paquete').addEventListener('click', () => { E.filtro.paquete = ''; sincronizarURL(); renderMatrizRam(); renderTabla(); });

document.querySelectorAll('#tabla-riesgos th.sortable').forEach((th) => th.addEventListener('click', () => {
  const col = th.dataset.col;
  E.orden = E.orden.col === col ? { col, asc: !E.orden.asc } : { col, asc: col !== 'puntaje_ram' };
  renderTabla();
}));
document.getElementById('chip-ram').addEventListener('click', () => { E.filtro.ram = null; renderMatrizRam(); renderTabla(); });
document.querySelectorAll('#seg-ram button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-ram button').forEach((x) => x.classList.toggle('on', x === b));
  E.etapaRam = b.dataset.v;
  renderMatrizRam();
}));

document.querySelectorAll('#seg-tipo button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-tipo button').forEach((x) => x.classList.toggle('on', x === b));
  E.tipoGrafico = b.dataset.v;
  renderChartCategoria();
}));

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

(async function iniciar() {
  const [riesgosGeo, paquetesGeo, alertas, params] = await Promise.all([
    ui.json('/api/riesgos'), ui.json('/api/paquetes'), ui.json('/api/alertas'), ui.json('/api/parametros'),
  ]);
  E.ram = params.ram || null;
  E.riesgos = riesgosGeo.features.map((f) => f.properties);
  E.paquetes = paquetesGeo.features.map((f) => f.properties);
  document.getElementById('fecha-corte').textContent = ui.fecha(alertas[0]?.generada_en || new Date());

  renderResumen(alertas);
  renderEstados();
  renderChartCategoria();
  renderChartSemanas();
  renderSelects();
  renderPaquetes();
  renderMatrizRam();
  renderTabla();
  if (E.filtro.paquete) document.querySelector(`.pq-row[data-id="${E.filtro.paquete}"]`)?.scrollIntoView({ block: 'nearest' });
})();
