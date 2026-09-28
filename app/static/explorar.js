/* Explorar datos (layout de Ejemplo_1). DATOS SINTETICOS. */

const E = {
  riesgos: [],
  paquetes: [],
  filtro: { buscar: '', categoria: '', estado: '', paquete: new URLSearchParams(location.search).get('paquete') || '' },
  tipoGrafico: '',
  orden: { col: 'severidad', asc: false },
  chartCat: null,
};

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
// Registro de riesgos
// ---------------------------------------------------------------------------

function renderSelects() {
  const cat = document.getElementById('f-categoria');
  cat.innerHTML = '<option value="">Todas las categorías</option>' +
    Object.entries(ui.CATEGORIA).filter(([k]) => k !== 'sin_clasificar').map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('');
  const est = document.getElementById('f-estado');
  est.innerHTML = '<option value="">Todos los estados</option>' +
    Object.entries(ui.ESTADO).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('');
}

function filtrados() {
  const f = E.filtro;
  const q = normalizar(f.buscar);
  return E.riesgos.filter((r) =>
    (!f.categoria || r.categoria === f.categoria) &&
    (!f.estado || r.estado === f.estado) &&
    (!f.paquete || r.id_paquete_trabajo === f.paquete) &&
    (!q || normalizar(`${r.id_riesgo} ${r.id_paquete_trabajo} ${nombrePaquete(r.id_paquete_trabajo)}`).includes(q)));
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
          <div><div class="t">${r.id_riesgo}</div><div class="s">${c.label}</div></div>
        </div></td>
        <td class="ink-2">${nombrePaquete(r.id_paquete_trabajo)}</td>
        <td class="ink-2">${ui.fecha(fechaDe(r))}</td>
        <td><span class="sev"><b>${r.severidad}</b><span class="pxi">${r.probabilidad}×${r.impacto}</span></span></td>
        <td><span class="status"><span class="dot ${est.lvl}"></span>${est.label}</span></td>
        <td><span class="status"><span class="dot" style="background:${r.tipo === 'oportunidad' ? 'var(--navy)' : 'var(--lvl-critico)'}"></span>${r.tipo === 'oportunidad' ? 'Oportunidad' : 'Amenaza'}</span></td>
      </tr>`;
  }).join('') || '<tr><td colspan="6" class="muted" style="padding:24px 12px">Ningún riesgo coincide con los filtros.</td></tr>';

  const partes = [`${filas.length} de ${E.riesgos.length} riesgos`];
  if (E.filtro.categoria) partes.push(ui.cat(E.filtro.categoria).label);
  document.getElementById('sub-registro').textContent = partes.join(' · ');

  const chip = document.getElementById('chip-paquete');
  chip.hidden = !E.filtro.paquete;
  if (E.filtro.paquete) chip.innerHTML = `${nombrePaquete(E.filtro.paquete)} <i data-lucide="x"></i>`;

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
document.getElementById('f-categoria').addEventListener('change', (e) => { E.filtro.categoria = e.target.value; renderTabla(); });
document.getElementById('f-estado').addEventListener('change', (e) => { E.filtro.estado = e.target.value; renderTabla(); });
document.getElementById('chip-paquete').addEventListener('click', () => { E.filtro.paquete = ''; sincronizarURL(); renderTabla(); });

document.querySelectorAll('#tabla-riesgos th.sortable').forEach((th) => th.addEventListener('click', () => {
  const col = th.dataset.col;
  E.orden = E.orden.col === col ? { col, asc: !E.orden.asc } : { col, asc: col !== 'severidad' };
  renderTabla();
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
  const [riesgosGeo, paquetesGeo, alertas] = await Promise.all([
    ui.json('/api/riesgos'), ui.json('/api/paquetes'), ui.json('/api/alertas'),
  ]);
  E.riesgos = riesgosGeo.features.map((f) => f.properties);
  E.paquetes = paquetesGeo.features.map((f) => f.properties);
  document.getElementById('fecha-corte').textContent = ui.fecha(alertas[0]?.generada_en || new Date());

  renderResumen(alertas);
  renderEstados();
  renderChartCategoria();
  renderChartSemanas();
  renderSelects();
  renderPaquetes();
  renderTabla();
  if (E.filtro.paquete) document.querySelector(`.pq-row[data-id="${E.filtro.paquete}"]`)?.scrollIntoView({ block: 'nearest' });
})();
