/* Mapa del piloto (layout de Ejemplo_3). DATOS SINTETICOS. */

const S = {
  params: null,
  pesosOriginales: null,
  original: null,          // FeatureCollection de paquetes del ultimo corte del pipeline
  actual: null,            // original o recalculada con otros pesos
  alertasPipeline: [],
  alertas: [],
  riesgos: [],
  filtro: { categoria: '', estado: '', tipo: '' },
  sel: null,
  base: 'satelite',
  radar: null,
};

// ---------------------------------------------------------------------------
// Mapa, bases y panes
// ---------------------------------------------------------------------------

const mapa = L.map('mapa', { zoomControl: false, attributionControl: true, zoomSnap: 0.25, zoomDelta: 0.5 });
mapa.attributionControl.setPrefix(false);

const BASES = {
  satelite: L.layerGroup([
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 18, attribution: 'Imágenes &copy; Esri, Maxar, Earthstar Geographics',
    }),
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 18, opacity: 0.85,
    }),
  ]),
  claro: L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd', attribution: '&copy; OpenStreetMap &copy; CARTO',
  }),
};
BASES.satelite.addTo(mapa);

// leaflet.heat siempre usa overlayPane (z 400): contexto va debajo, zonas y riesgos encima
[['contexto', 395], ['proyectos', 405], ['zonas', 410], ['riesgosPane', 420]].forEach(([n, z]) => {
  mapa.createPane(n).style.zIndex = z;
});

const COLOR = {
  oportunidad: '#4da3ff',
  comunidad: '#8b6cff',
  area: '#9be37a',
  hidro: '#5cc8ff',
  via: '#f1f1ee',
};

const capas = {
  calor: L.layerGroup(),
  proyectos: L.geoJSON(null, { pane: 'proyectos', interactive: false, style: estiloProyecto }),
  paquetes: L.geoJSON(null, { pane: 'zonas', style: estiloPaquete, onEachFeature: eventosPaquete }),
  riesgos: L.layerGroup(),
  comunidades: L.geoJSON(null, {
    pane: 'contexto',
    pointToLayer: (f, ll) => L.circleMarker(ll, { pane: 'contexto', radius: 5, color: '#fff', weight: 2, fillColor: COLOR.comunidad, fillOpacity: 1 }),
    onEachFeature: (f, l) => l.bindTooltip(`${f.properties.nombre}<br><span style="opacity:.7">Conflictividad ${f.properties.conflictividad}</span>`, { className: 'map-tip' }),
  }),
  areas: L.geoJSON(null, {
    pane: 'contexto', style: { color: COLOR.area, weight: 1.5, dashArray: '4 4', fillColor: COLOR.area, fillOpacity: 0.16 },
    onEachFeature: (f, l) => l.bindTooltip(f.properties.nombre, { className: 'map-tip' }),
  }),
  hidro: L.geoJSON(null, { pane: 'contexto', style: { color: COLOR.hidro, weight: 2 } }),
  vias: L.geoJSON(null, { pane: 'contexto', style: { color: COLOR.via, weight: 1.5, dashArray: '2 5' } }),
};

const CAPAS_META = [
  { k: 'paquetes', label: 'Paquetes de trabajo (ICT)', sw: () => ui.css('--lvl-alto'), on: true },
  { k: 'calor', label: 'Mapa de calor', sw: () => ui.css('--lvl-critico'), on: true },
  { k: 'proyectos', label: 'Límites de proyecto', sw: () => '#ffffff', on: true },
  { k: 'riesgos', label: 'Riesgos (puntos)', sw: () => ui.css('--lvl-critico'), on: false },
  { k: 'comunidades', label: 'Comunidades', sw: () => COLOR.comunidad, on: false },
  { k: 'areas', label: 'Áreas protegidas', sw: () => COLOR.area, on: false },
  { k: 'hidro', label: 'Hidrología', sw: () => COLOR.hidro, on: false },
  { k: 'vias', label: 'Vías', sw: () => '#b9beba', on: false },
];

function estiloProyecto() {
  return S.base === 'satelite'
    ? { color: '#ffffff', weight: 1.5, dashArray: '6 6', fill: false, opacity: 0.9 }
    : { color: ui.css('--ink-2'), weight: 1.5, dashArray: '6 6', fill: false, opacity: 0.7 };
}

function estiloPaquete(f) {
  const p = f.properties;
  const sel = p.id_paquete === S.sel;
  return {
    color: '#ffffff',
    weight: sel ? 4 : 2,
    opacity: 1,
    fillColor: ui.nivelColor(p.nivel),
    fillOpacity: sel ? 0.62 : 0.4,
  };
}

function eventosPaquete(f, layer) {
  layer.bindTooltip(ui.tagCorto(f.properties.nombre), { permanent: true, direction: 'center', className: 'map-tag' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar(f.properties.id_paquete); });
  layer.on('mouseover', () => { if (f.properties.id_paquete !== S.sel) layer.setStyle({ weight: 3, fillOpacity: 0.52 }); });
  layer.on('mouseout', () => layer.setStyle(estiloPaquete(f)));
}

function capaDePaquete(id) {
  let found = null;
  capas.paquetes.eachLayer((l) => { if (l.feature.properties.id_paquete === id) found = l; });
  return found;
}

// Las etiquetas tipo tag solo se muestran con zoom suficiente para no amontonarse
mapa.on('zoomend', () => document.getElementById('map-card').classList.toggle('tags-off', mapa.getZoom() < 8.75));

// ---------------------------------------------------------------------------
// Datos y utilidades
// ---------------------------------------------------------------------------

const props = () => S.actual.features.map((f) => f.properties);
const porId = (id) => props().find((p) => p.id_paquete === id);

function alertasDesdeFeatures(fc) {
  return fc.features
    .map((f) => f.properties)
    .filter((p) => p.escalamiento)
    .map((p) => ({ id_paquete: p.id_paquete, nombre_paquete: p.nombre, ict: p.ICT, nivel: p.nivel, motivos: (p.causas_escalamiento || '').split('; ').filter(Boolean) }));
}

const GI = {
  punto_caliente_significativo: 'Punto caliente',
  punto_frio_significativo: 'Punto frío',
  sin_patron_significativo: 'Sin patrón',
};

function capitalizar(t) { return t ? t.charAt(0).toUpperCase() + t.slice(1) : t; }
function normalizar(t) { return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }

// ---------------------------------------------------------------------------
// Render: panel
// ---------------------------------------------------------------------------

function renderSliders(pesos) {
  document.getElementById('sliders').innerHTML = Object.entries(pesos).map(([k, v]) => `
    <div class="slider-row">
      <div class="top"><span>${ui.CRITERIOS[k] || k}</span><span class="val" id="val-${k}">${v.toFixed(2)}</span></div>
      <input type="range" class="range" min="0" max="1" step="0.01" value="${v}" data-k="${k}" style="--val:${v * 100}">
    </div>`).join('');
  document.querySelectorAll('#sliders .range').forEach((el) => {
    el.addEventListener('input', () => {
      el.style.setProperty('--val', el.value * 100);
      document.getElementById(`val-${el.dataset.k}`).textContent = Number(el.value).toFixed(2);
      actualizarSuma();
    });
  });
  actualizarSuma();
}

function leerPesos() {
  const pesos = {};
  document.querySelectorAll('#sliders .range').forEach((el) => { pesos[el.dataset.k] = Number(el.value); });
  return pesos;
}

function actualizarSuma() {
  const suma = Object.values(leerPesos()).reduce((a, b) => a + b, 0);
  const el = document.getElementById('suma-pesos');
  el.textContent = `Σ ${suma.toFixed(2)}`;
  el.classList.toggle('fuera', Math.abs(suma - 1) > 0.05);
  el.title = Math.abs(suma - 1) > 0.05 ? 'La suma no es 1: al recalcular los pesos se normalizan automáticamente.' : '';
}

function renderZonas() {
  const filas = [...props()].sort((a, b) => b.ICT - a.ICT);
  document.getElementById('tabla-zonas').innerHTML = filas.map((p) => {
    const t = p.tendencia_delta;
    const tend = t == null ? '<span class="muted">-</span>'
      : `<span class="${t > 0 ? 'lvl-soft critico' : t < 0 ? 'lvl-soft bajo' : 'muted'}" style="height:20px">${t > 0 ? '+' : ''}${t}</span>`;
    return `
      <tr class="clickable${p.id_paquete === S.sel ? ' sel' : ''}" data-id="${p.id_paquete}">
        <td><div class="zona-cell"><span class="lvl ${p.nivel}">${ui.NIVEL[p.nivel]}</span><span class="n">${ui.tagCorto(p.nombre)}</span></div></td>
        <td><b>${p.ICT}</b></td>
        <td>${tend}</td>
        <td class="muted">${Math.round((p.indice_confianza ?? 0) * 100)}%</td>
      </tr>`;
  }).join('');
  document.querySelectorAll('#tabla-zonas tr').forEach((tr) => tr.addEventListener('click', () => seleccionar(tr.dataset.id)));
}

function renderAlertas() {
  const alertas = S.alertas;
  document.getElementById('n-alertas').textContent = alertas.length;
  document.getElementById('n-alertas').hidden = alertas.length === 0;

  const car = document.getElementById('carrusel');
  car.innerHTML = alertas.length
    ? alertas.map((a) => `
        <button class="alert-card${a.id_paquete === S.sel ? ' on' : ''}" data-id="${a.id_paquete}">
          <div class="row"><span class="lvl ${a.nivel}">${ui.NIVEL[a.nivel]}</span><span class="num sm">${ui.num(a.ict)}</span></div>
          <div class="t">${ui.nombreCorto(a.nombre_paquete)}</div>
          <div class="s">${capitalizar(a.motivos[0] || '')}</div>
        </button>`).join('')
    : `<div class="alert-card vacio"><div class="t">Sin alertas activas</div><div class="s">Ningún paquete cumple las reglas de escalamiento con estos pesos.</div></div>`;
  car.querySelectorAll('button.alert-card').forEach((b) => b.addEventListener('click', () => seleccionar(b.dataset.id)));

  document.getElementById('lista-alertas').innerHTML = alertas.length
    ? alertas.map((a) => `
        <a class="list-item" data-id="${a.id_paquete}">
          <span class="tile" style="background:var(--lvl-${a.nivel}-bg);color:${ui.nivelColor(a.nivel)}"><i data-lucide="triangle-alert"></i></span>
          <div class="grow"><div class="t">${ui.nombreCorto(a.nombre_paquete)} · ICT ${a.ict}</div><div class="s">${a.motivos.map(capitalizar).join(' · ')}</div></div>
          <i data-lucide="arrow-up-right"></i>
        </a>`).join('')
    : '<p class="nota">Sin alertas activas.</p>';
  document.querySelectorAll('#lista-alertas .list-item').forEach((a) => a.addEventListener('click', () => seleccionar(a.dataset.id)));
  ui.icons();
}

function renderFiltros() {
  const cats = [['', 'Todas'], ...Object.entries(ui.CATEGORIA).filter(([k]) => k !== 'sin_clasificar').map(([k, v]) => [k, v.label])];
  const ests = [['', 'Todos'], ...Object.entries(ui.ESTADO).map(([k, v]) => [k, v.label])];
  const chips = (lista, campo) => lista.map(([v, t]) => `<button class="chip${S.filtro[campo] === v ? ' on' : ''}" data-v="${v}">${t}</button>`).join('');
  document.getElementById('f-categoria').innerHTML = chips(cats, 'categoria');
  document.getElementById('f-estado').innerHTML = chips(ests, 'estado');
  [['f-categoria', 'categoria'], ['f-estado', 'estado']].forEach(([id, campo]) => {
    document.querySelectorAll(`#${id} .chip`).forEach((b) => b.addEventListener('click', () => {
      S.filtro[campo] = b.dataset.v;
      renderFiltros();
      activarCapa('riesgos', true);
      renderRiesgos();
    }));
  });
}

// ---------------------------------------------------------------------------
// Render: mapa
// ---------------------------------------------------------------------------

function renderPaquetes() {
  capas.paquetes.clearLayers().addData(S.actual);
  if (S.sel) capaDePaquete(S.sel)?.bringToFront();
}

function riesgosFiltrados() {
  const f = S.filtro;
  return S.riesgos.filter((r) => {
    const p = r.properties;
    return (!f.categoria || p.categoria === f.categoria) && (!f.estado || p.estado === f.estado) && (!f.tipo || p.tipo === f.tipo);
  });
}

function renderRiesgos() {
  const lista = riesgosFiltrados();
  capas.riesgos.clearLayers();
  lista.forEach((r) => {
    const p = r.properties;
    const [lon, lat] = r.geometry.coordinates;
    L.circleMarker([lat, lon], {
      pane: 'riesgosPane', radius: 3 + Math.min(p.severidad, 25) / 6,
      color: '#fff', weight: 1.2,
      fillColor: p.tipo === 'oportunidad' ? COLOR.oportunidad : ui.css('--lvl-critico'), fillOpacity: 0.92,
    }).bindTooltip(`<b>${p.id_riesgo}</b> · ${ui.cat(p.categoria).label}<br>${ui.ESTADO[p.estado]?.label || p.estado} · severidad ${p.severidad}`, { className: 'map-tip' })
      .addTo(capas.riesgos);
  });
  document.getElementById('n-riesgos-visibles').textContent = `${lista.length} de ${S.riesgos.length} riesgos coinciden con el filtro`;
}

function activarCapa(k, on) {
  const capa = capas[k];
  if (on && !mapa.hasLayer(capa)) capa.addTo(mapa);
  if (!on && mapa.hasLayer(capa)) mapa.removeLayer(capa);
  const sw = document.querySelector(`#lista-capas input[data-k="${k}"]`);
  if (sw) sw.checked = on;
  if (k === 'riesgos') document.getElementById('toggle-riesgos').checked = on;
}

function renderListaCapas() {
  document.getElementById('lista-capas').innerHTML = CAPAS_META.map((c) => `
    <label class="row">
      <span class="sw" style="background:${c.sw()}"></span>
      <span class="grow">${c.label}</span>
      <span class="switch"><input type="checkbox" data-k="${c.k}"${mapa.hasLayer(capas[c.k]) ? ' checked' : ''}><span></span></span>
    </label>`).join('');
  document.querySelectorAll('#lista-capas input').forEach((el) => el.addEventListener('change', () => activarCapa(el.dataset.k, el.checked)));
}

// ---------------------------------------------------------------------------
// Seleccion y tarjeta de detalle (alert card de Ejemplo_3)
// ---------------------------------------------------------------------------

function seleccionar(id, { volar = true } = {}) {
  S.sel = id;
  capas.paquetes.eachLayer((l) => l.setStyle(estiloPaquete(l.feature)));
  const capa = capaDePaquete(id);
  if (capa) {
    capa.bringToFront();
    if (volar) {
      mapa.flyToBounds(capa.getBounds(), { paddingTopLeft: [40, 120], paddingBottomRight: [420, 150], maxZoom: 11, duration: 0.8 });
    }
  }
  cerrarFlotantes();
  renderZonas();
  renderAlertas();
  renderDetalle();
  document.querySelector(`#carrusel [data-id="${id}"]`)?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
}

function deseleccionar() {
  S.sel = null;
  capas.paquetes.eachLayer((l) => l.setStyle(estiloPaquete(l.feature)));
  document.getElementById('detalle').hidden = true;
  renderZonas();
  renderAlertas();
}

function renderDetalle() {
  const el = document.getElementById('detalle');
  const p = porId(S.sel);
  if (!p) { el.hidden = true; return; }

  const causas = (p.causas_escalamiento || '').split('; ').filter(Boolean);
  const t = p.tendencia_delta;
  const trend = t == null ? ''
    : t === 0 ? '<span class="trend flat">Sin cambio en 7 días</span>'
    : `<span class="trend ${t > 0 ? 'down' : ''}" title="Variación del ICT en 7 días">${t > 0 ? '+' : ''}${t} en 7 días</span>`;
  const nombreProyecto = (p.nombre.split(' - ')[1] || '').replace('Sintetico', 'Sintético');

  el.innerHTML = `
    <div class="det-head">
      <span class="tile" style="background:var(--lvl-${p.nivel}-bg);color:${ui.nivelColor(p.nivel)}"><i data-lucide="${p.escalamiento ? 'triangle-alert' : 'hexagon'}"></i></span>
      <div class="grow">
        <div class="card-title">${ui.nombreCorto(p.nombre)}</div>
        <div class="card-sub">${nombreProyecto} · ${p.id_paquete}</div>
      </div>
      <button class="icon-btn sm ghost" id="det-x" title="Cerrar"><i data-lucide="x"></i></button>
    </div>
    <div class="det-chips">
      <span class="chip white"><i data-lucide="calendar"></i> Corte ${document.getElementById('fecha-corte').textContent}</span>
      ${trend}
      ${p.ruta_critica ? '<span class="chip">Ruta crítica</span>' : ''}
    </div>
    <div class="det-gauge">
      <div class="ring" style="--p:${p.ICT};--c:${ui.nivelColor(p.nivel)}">
        <div><div class="num md">${ui.num(p.ICT)}</div><div class="muted" style="font-size:11px">ICT</div></div>
      </div>
      <div class="info">
        <span class="lvl ${p.nivel}">${ui.NIVEL[p.nivel]}</span>
        <div class="kv"><span class="k">Confianza</span><span class="v">${Math.round((p.indice_confianza ?? 0) * 100)}%</span></div>
        <div class="kv"><span class="k">Oportunidad</span><span class="v">${(p.indice_oportunidad ?? 0).toFixed(1)}</span></div>
      </div>
    </div>
    ${causas.length
      ? `<div class="issue-pill"><i data-lucide="flame"></i><span class="grow">${capitalizar(causas[0])}</span></div>
         ${causas.length > 1 ? `<ul class="causas-extra">${causas.slice(1).map((c) => `<li>${capitalizar(c)}</li>`).join('')}</ul>` : ''}`
      : '<div class="issue-pill ok"><i data-lucide="shield-check"></i><span class="grow">Sin señales de escalamiento a crisis</span></div>'}
    <div class="sec-mini">
      <span>Criterios vs. promedio del portafolio</span>
      <span class="leg-mini"><span><span class="dot" style="background:var(--green-600)"></span>Paquete</span><span><span class="dot" style="background:var(--orange)"></span>Promedio</span></span>
    </div>
    <div class="radar-wrap"><canvas id="radar"></canvas></div>
    <div class="kv"><span class="k">Getis-Ord Gi*</span><span class="v">${GI[p.clasificacion] || '-'}${p.z_score != null ? ` · z = ${p.z_score}` : ''}</span></div>
    <div class="det-foot">
      <button class="btn btn-outline sm" id="det-cerrar">Cerrar</button>
      <a class="btn btn-primary sm" href="explorar.html?paquete=${encodeURIComponent(p.id_paquete)}">Ver en datos <i data-lucide="arrow-up-right"></i></a>
    </div>`;
  el.hidden = false;
  el.scrollTop = 0;
  ui.icons();
  document.getElementById('det-x').addEventListener('click', deseleccionar);
  document.getElementById('det-cerrar').addEventListener('click', deseleccionar);
  dibujarRadar(p);
}

function dibujarRadar(p) {
  const claves = Object.keys(ui.CRITERIOS);
  const todos = props();
  const promedio = claves.map((k) => todos.reduce((s, x) => s + (x[k] ?? 0), 0) / todos.length);
  const verde = ui.css('--green-600'), naranja = ui.css('--orange');
  if (S.radar) S.radar.destroy();
  S.radar = new Chart(document.getElementById('radar'), {
    type: 'radar',
    data: {
      labels: claves.map((k) => ui.CRITERIOS[k]),
      datasets: [
        { label: 'Paquete', data: claves.map((k) => p[k] ?? 0), borderColor: verde, backgroundColor: ui.alpha(verde, 0.18), borderWidth: 2, pointRadius: 2.5, pointBackgroundColor: verde },
        { label: 'Promedio', data: promedio, borderColor: naranja, backgroundColor: ui.alpha(naranja, 0.1), borderWidth: 1.5, pointRadius: 2, pointBackgroundColor: naranja },
      ],
    },
    options: {
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { label: (c) => `${c.dataset.label}: ${Number(c.raw).toFixed(2)}` } } },
      scales: {
        r: {
          min: 0, max: 1, ticks: { display: false, stepSize: 0.25 },
          grid: { color: ui.css('--line') }, angleLines: { color: ui.css('--line') },
          pointLabels: { color: ui.css('--ink-2'), font: { size: 11, weight: '500' } },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Controles flotantes, busqueda, tabs
// ---------------------------------------------------------------------------

function cerrarFlotantes() {
  document.getElementById('pop-capas').hidden = true;
  document.getElementById('btn-capas').classList.remove('on');
  document.getElementById('resultados').hidden = true;
}

document.querySelectorAll('.map-overlay').forEach((el) => {
  L.DomEvent.disableClickPropagation(el);
  L.DomEvent.disableScrollPropagation(el);
});
mapa.on('click', () => { cerrarFlotantes(); if (S.sel) deseleccionar(); });

document.getElementById('zoom-in').addEventListener('click', () => mapa.zoomIn());
document.getElementById('zoom-out').addEventListener('click', () => mapa.zoomOut());
document.getElementById('btn-centrar').addEventListener('click', encuadrar);

document.getElementById('btn-base').addEventListener('click', (e) => {
  const btn = e.currentTarget;
  mapa.removeLayer(BASES[S.base]);
  S.base = S.base === 'satelite' ? 'claro' : 'satelite';
  BASES[S.base].addTo(mapa);
  capas.proyectos.setStyle(estiloProyecto());
  btn.innerHTML = `<i data-lucide="${S.base === 'satelite' ? 'map' : 'satellite'}"></i>`;
  btn.title = S.base === 'satelite' ? 'Cambiar a mapa claro' : 'Cambiar a satélite';
  document.getElementById('map-card').classList.toggle('base-claro', S.base === 'claro');
  ui.icons();
});

document.getElementById('btn-capas').addEventListener('click', (e) => {
  const pop = document.getElementById('pop-capas');
  const abrir = pop.hidden;
  cerrarFlotantes();
  if (abrir) {
    document.getElementById('detalle').hidden = true;
    renderListaCapas();
    pop.hidden = false;
    e.currentTarget.classList.add('on');
  } else if (S.sel) {
    renderDetalle();
  }
});

const inputBuscar = document.getElementById('buscar');
inputBuscar.addEventListener('input', () => {
  const q = normalizar(inputBuscar.value.trim());
  const cont = document.getElementById('resultados');
  if (!q) { cont.hidden = true; return; }
  const hits = props()
    .filter((p) => normalizar(`${p.nombre} ${p.id_paquete} ${ui.tagCorto(p.nombre)}`).includes(q))
    .sort((a, b) => b.ICT - a.ICT)
    .slice(0, 6);
  cont.innerHTML = hits.length
    ? hits.map((p, i) => `<button class="${i === 0 ? 'on' : ''}" data-id="${p.id_paquete}"><span class="dot ${p.nivel}"></span><span class="grow">${ui.nombreCorto(p.nombre)}</span><span class="muted">ICT ${p.ICT}</span></button>`).join('')
    : '<div class="vacio">Sin coincidencias</div>';
  cont.hidden = false;
  cont.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => { inputBuscar.value = ''; seleccionar(b.dataset.id); }));
});
inputBuscar.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.querySelector('#resultados button')?.click();
  if (e.key === 'Escape') { inputBuscar.value = ''; cerrarFlotantes(); }
});
document.getElementById('btn-focus-buscar').addEventListener('click', () => inputBuscar.focus());

document.querySelectorAll('#tabs button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#tabs button').forEach((x) => x.classList.toggle('on', x === b));
  document.querySelectorAll('.panel-body [data-panel]').forEach((s) => { s.hidden = s.dataset.panel !== b.dataset.tab; });
}));

document.querySelectorAll('#f-tipo button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#f-tipo button').forEach((x) => x.classList.toggle('on', x === b));
  S.filtro.tipo = b.dataset.v;
  activarCapa('riesgos', true);
  renderRiesgos();
}));
document.getElementById('toggle-riesgos').addEventListener('change', (e) => activarCapa('riesgos', e.target.checked));

// ---------------------------------------------------------------------------
// Recalculo de pesos
// ---------------------------------------------------------------------------

document.getElementById('btn-recalcular').addEventListener('click', async (e) => {
  const btn = e.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<i data-lucide="loader"></i> Calculando';
  ui.icons();
  try {
    const fc = await ui.json('/api/recalcular', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(leerPesos()),
    });
    // El recalculo no rehace tendencia ni Getis-Ord: se conservan los del ultimo corte
    const extra = Object.fromEntries(S.original.features.map((f) => [f.properties.id_paquete, f.properties]));
    fc.features.forEach((f) => {
      const o = extra[f.properties.id_paquete] || {};
      ['tendencia_delta', 'z_score', 'clasificacion', 'ruta_critica'].forEach((k) => { if (f.properties[k] == null) f.properties[k] = o[k]; });
    });
    S.actual = fc;
    S.alertas = alertasDesdeFeatures(fc);
    document.getElementById('nota-pesos').hidden = false;
    renderTodo();
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="refresh-cw"></i> Recalcular';
    ui.icons();
  }
});

document.getElementById('btn-reset').addEventListener('click', () => {
  renderSliders(S.pesosOriginales);
  S.actual = S.original;
  S.alertas = S.alertasPipeline;
  document.getElementById('nota-pesos').hidden = true;
  renderTodo();
});

function renderTodo() {
  renderPaquetes();
  renderZonas();
  renderAlertas();
  if (S.sel) renderDetalle();
}

function encuadrar() {
  const b = capas.proyectos.getBounds();
  if (b.isValid()) mapa.fitBounds(b, { paddingTopLeft: [24, 100], paddingBottomRight: [70, 130] });
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

(async function iniciar() {
  const [params, paquetes, grid, riesgos, alertas, com, areas, hidro, vias, proyectos] = await Promise.all([
    ui.json('/api/parametros'), ui.json('/api/paquetes'), ui.json('/api/grid'), ui.json('/api/riesgos'), ui.json('/api/alertas'),
    ui.json('/api/capas/comunidades'), ui.json('/api/capas/areas'), ui.json('/api/capas/hidro'), ui.json('/api/capas/vias'), ui.json('/api/capas/proyectos'),
  ]);

  S.params = params;
  S.pesosOriginales = params.pesos;
  S.original = paquetes;
  S.actual = paquetes;
  S.alertasPipeline = alertas;
  S.alertas = alertas;
  S.riesgos = riesgos.features;

  document.getElementById('param-version').textContent = `v${params.version.split('-')[0]}`;
  document.getElementById('fecha-corte').textContent = ui.fecha(alertas[0]?.generada_en || new Date());
  document.getElementById('panel-resumen').textContent = `La Guajira · ${proyectos.features.length} proyectos · ${paquetes.features.length} paquetes`;

  capas.comunidades.addData(com);
  capas.areas.addData(areas);
  capas.hidro.addData(hidro);
  capas.vias.addData(vias);
  capas.proyectos.addData(proyectos);

  const puntos = grid.features.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0], f.properties.intensidad]);
  capas.calor = L.heatLayer(puntos, {
    radius: 30, blur: 24, minOpacity: 0.2, max: 1,
    gradient: { 0.25: ui.css('--lime'), 0.5: ui.css('--lvl-medio'), 0.75: ui.css('--lvl-alto'), 1: ui.css('--lvl-critico') },
  });

  CAPAS_META.forEach((c) => { if (c.on) capas[c.k].addTo(mapa); });

  renderSliders(S.pesosOriginales);
  renderFiltros();
  renderRiesgos();
  renderTodo();
  encuadrar();
  ui.icons();
})();
