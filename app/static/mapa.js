/* Mapa simple: proyectos, riesgos y clima real (IDEAM) sobre satelite o mapa de calles, sin claves. */

const S = {
  base: 'satelite',
  activas: new Set(),    // variables de clima encendidas (cada una es una capa); al inicio, ninguna
  red: null,             // red vial unificada (INVIAS + IGAC)
  clasesOcultas: new Set(),   // estilos de via que el usuario apago
  municipios: null,      // limites municipales (DANE)
  mpiosOcultos: new Set(),   // codigos DANE de los municipios que el usuario quito
  limite: null,          // contorno de La Guajira
  rios: null,            // rios y arroyos (IGAC)
  agua: null,            // rios anchos, cienagas, lagunas y embalses (IGAC)
  ventana: 'mm_14d',     // acumulado de lluvia: mm_7d | mm_14d | mm_30d
  filtro: { categoria: '', tipo: '' },
  riesgos: [],
  paquetes: null,
  clima: null,           // estaciones (Oro)
  radiacion: null,       // puntos de radiacion media
  ahora: null,           // lecturas en vivo por estacion
  sel: null,             // { tipo, id }
  varDetalle: null,      // variable mostrada en el grafico de la tarjeta de estacion
  chart: null,
};

// ---------------------------------------------------------------------------
// Mapa y bases (ambas sin clave)
// ---------------------------------------------------------------------------

const mapa = L.map('mapa', { zoomControl: false, zoomSnap: 0.25, zoomDelta: 0.5 });
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
  calles: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }),
};
BASES.satelite.addTo(mapa);

// Orden de apilado: proyectos abajo, riesgos encima, estaciones (marcadores) arriba
mapa.createPane('proyectos').style.zIndex = 405;
mapa.createPane('mpios').style.zIndex = 400;          // rellenos casi transparentes: reciben el clic
mapa.createPane('mpiosLineas').style.zIndex = 403;    // bordes y nombres: encima de los rios, sin bloquear sus clics
mapa.getPane('mpiosLineas').style.pointerEvents = 'none';
mapa.createPane('agua').style.zIndex = 401;
mapa.createPane('rios').style.zIndex = 402;
mapa.createPane('vias').style.zIndex = 407;
mapa.createPane('paquetes').style.zIndex = 410;
mapa.createPane('riesgosPane').style.zIndex = 420;
mapa.createPane('fichasLineas').style.zIndex = 599;   // lineas y puntos de las fichas: debajo de las fichas (markerPane = 600)

const capas = {
  municipios: L.layerGroup(),
  proyectos: L.layerGroup(),
  rios: L.layerGroup(),
  vias: L.layerGroup(),
  riesgos: L.layerGroup(),
};
const gClima = {};   // una capa de Leaflet por variable de clima (se crean en renderTarjetasClima)
const limitesProyecto = L.geoJSON(null, { pane: 'proyectos', interactive: false, style: estiloProyecto });
const paquetes = L.geoJSON(null, { pane: 'paquetes', style: estiloPaquete, onEachFeature: eventosPaquete });
capas.proyectos.addLayer(limitesProyecto).addLayer(paquetes);

function estiloProyecto() {
  const claro = S.base === 'calles';
  return { color: claro ? ui.css('--ink-2') : '#ffffff', weight: 1.5, dashArray: '6 6', fill: false, opacity: claro ? 0.8 : 0.9 };
}
function estiloPaquete(f) {
  const sel = S.sel?.tipo === 'paquete' && S.sel.id === f.properties.id_paquete;
  return {
    color: S.base === 'calles' ? ui.css('--green-700') : '#ffffff', weight: sel ? 3.5 : 2,
    fillColor: ui.css('--green-500'), fillOpacity: sel ? 0.4 : 0.22,
  };
}
function eventosPaquete(f, layer) {
  layer.bindTooltip(ui.tagCorto(f.properties.nombre), { permanent: true, direction: 'center', className: 'map-tag' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('paquete', f.properties.id_paquete); });
}

// ---------------------------------------------------------------------------
// Capa de municipios (DANE): poligonos sin relleno, con el nombre escrito adentro
// ---------------------------------------------------------------------------

const municipios = L.geoJSON(null, { pane: 'mpios', style: estiloMunicipio, onEachFeature: eventosMunicipio });
const lineasMpio = L.geoJSON(null, { pane: 'mpiosLineas', interactive: false, style: estiloLineaMpio });
const contornoGuajira = L.geoJSON(null, { pane: 'mpiosLineas', interactive: false, style: estiloContorno });
const etiquetasMpio = L.layerGroup();
capas.municipios.addLayer(municipios).addLayer(lineasMpio).addLayer(contornoGuajira).addLayer(etiquetasMpio);

function estiloMunicipio(f) {
  const sat = S.base === 'satelite';
  const sel = S.sel?.tipo === 'municipio' && S.sel.id === f.properties.codigo;
  return { stroke: false, fill: true, fillColor: sat ? '#ffffff' : '#56645c', fillOpacity: sel ? 0.16 : 0.001 };   // solo recibe clics y resalta
}
function estiloLineaMpio(f) {
  const sat = S.base === 'satelite';
  const sel = S.sel?.tipo === 'municipio' && S.sel.id === f.properties.codigo;
  return { color: sat ? '#ffffff' : '#56645c', weight: sel ? 3 : 1.6, opacity: sat ? 0.85 : 0.9, dashArray: sel ? null : '7 4', fill: false };
}
function estiloContorno() {
  const sat = S.base === 'satelite';
  return { color: sat ? '#ffd400' : '#e0a100', weight: 3.5, opacity: 1, fill: false };   // amarillo: es el limite del departamento
}
function eventosMunicipio(f, layer) {
  const p = f.properties;
  layer.bindTooltip(`<b>${p.nombre}</b><br><span class="sub">${p.area_km2.toLocaleString('es-CO')} km²</span>`, { sticky: true, className: 'map-tip' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('municipio', p.codigo); });
}
function renderEtiquetasMpio() {
  etiquetasMpio.clearLayers();
  if (!S.municipios) return;
  const claro = S.base === 'calles';
  municipiosVisibles().forEach((f) => {
    const p = f.properties;
    L.marker([p.etiqueta_lat, p.etiqueta_lon], {
      interactive: false, keyboard: false, pane: 'mpiosLineas',
      icon: L.divIcon({ className: `mpio-tag${claro ? ' claro' : ''}`, iconSize: [0, 0], html: `<span>${p.nombre}</span>` }),
    }).addTo(etiquetasMpio);
  });
}

const municipiosVisibles = () => (S.municipios?.features || []).filter((f) => !S.mpiosOcultos.has(f.properties.codigo));

// Redibuja poligonos, bordes, nombres y contorno segun los municipios elegidos en la lista
function renderMunicipios() {
  const visibles = municipiosVisibles();
  const todos = visibles.length === (S.municipios?.features.length || 0);
  const col = { type: 'FeatureCollection', features: visibles };
  municipios.clearLayers();
  lineasMpio.clearLayers();
  contornoGuajira.clearLayers();
  municipios.addData(col);
  lineasMpio.addData(col);
  if (todos && S.limite) contornoGuajira.addData(S.limite);   // el contorno solo tiene sentido con todos los municipios
  renderEtiquetasMpio();
  const cuenta = document.getElementById('cuenta-mpios');
  if (cuenta) cuenta.textContent = `${visibles.length} de ${S.municipios?.features.length || 0}`;
  if (S.sel?.tipo === 'municipio' && S.mpiosOcultos.has(S.sel.id)) cerrarDetalle();
}

function renderListaMunicipios() {
  const cont = document.getElementById('lista-filas');
  const ordenados = [...S.municipios.features].sort((a, b) => a.properties.nombre.localeCompare(b.properties.nombre, 'es'));
  cont.innerHTML = ordenados.map((f) => {
    const p = f.properties;
    return `<label><input type="checkbox" data-mpio="${p.codigo}"${S.mpiosOcultos.has(p.codigo) ? '' : ' checked'}><span>${p.nombre}</span><span class="km">${Math.round(p.area_km2).toLocaleString('es-CO')} km²</span></label>`;
  }).join('');
  cont.querySelectorAll('input[data-mpio]').forEach((el) => el.addEventListener('change', () => {
    el.checked ? S.mpiosOcultos.delete(el.dataset.mpio) : S.mpiosOcultos.add(el.dataset.mpio);
    renderMunicipios();
  }));
  const marcar = (visible) => {
    S.mpiosOcultos = new Set(visible ? [] : S.municipios.features.map((f) => f.properties.codigo));
    cont.querySelectorAll('input[data-mpio]').forEach((el) => { el.checked = visible; });
    renderMunicipios();
  };
  document.getElementById('mpios-todos').addEventListener('click', () => marcar(true));
  document.getElementById('mpios-ninguno').addEventListener('click', () => marcar(false));
}

function detalleMunicipio(p) {
  const fila = (k, v) => (v == null ? '' : `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`);
  return `
    ${cabecera('map-pinned', '#eef1ee', '#44504a', p.nombre, `Municipio · código DANE ${p.codigo}`)}
    <div class="det-chips"><span class="chip ok">DANE · real</span></div>
    ${fila('Área', `${p.area_km2.toLocaleString('es-CO')} km²`)}
    ${fila('Estaciones del IDEAM', p.estaciones_catalogo != null ? `${p.estaciones_catalogo} en el catálogo · ${p.estaciones_con_datos ?? 0} con datos recientes` : null)}
    ${fila('Vías', p.km_vias != null ? `${p.km_vias.toLocaleString('es-CO')} km · ${p.km_vias_solo_tiempo_seco.toLocaleString('es-CO')} km solo en tiempo seco` : null)}
    ${fila('De ellas, red nacional', p.km_vias_nacionales != null ? `${p.km_vias_nacionales} km` : null)}
    <div class="det-foot">Límites del Marco Geoestadístico Nacional del DANE (versión 2005, base del IGAC): pueden diferir de los actuales en los bordes. Las estaciones se cuentan por su ubicación, no por el municipio que declara el catálogo.</div>`;
}

// ---------------------------------------------------------------------------
// Capa de rios y cuerpos de agua (IGAC): ~9.600 tramos, por eso se dibujan en canvas
// ---------------------------------------------------------------------------

const lienzoRios = L.canvas({ pane: 'rios', padding: 0.4, tolerance: 5 });
const lienzoAgua = L.canvas({ pane: 'agua', padding: 0.4 });
const riosNombrados = L.geoJSON(null, { pane: 'rios', renderer: lienzoRios, style: estiloRio, onEachFeature: eventosRio });
const riosSinNombre = L.geoJSON(null, { pane: 'rios', renderer: lienzoRios, style: estiloRio, interactive: false });
const cuerposAgua = L.geoJSON(null, { pane: 'agua', renderer: lienzoAgua, style: estiloAgua, onEachFeature: eventosAgua });
capas.rios.addLayer(cuerposAgua).addLayer(riosSinNombre).addLayer(riosNombrados);

const NOMBRE_TIPO = { drenaje_doble: 'Río ancho', cienaga: 'Ciénaga', laguna: 'Laguna', embalse: 'Embalse' };

function estiloRio(f) {
  const p = f.properties;
  const sat = S.base === 'satelite';
  const sel = S.sel?.tipo === 'rio' && S.sel.id === p.id_objeto;
  const inter = p.estado === 'Intermitente';
  return {
    color: sat ? '#7cc8ff' : '#2b7fd0', weight: (p.nombre ? 1.9 : 1) + (sel ? 2 : 0), opacity: p.nombre || sel ? 0.95 : 0.55,
    dashArray: inter ? '3 4' : null, lineCap: 'round',
  };
}
function estiloAgua(f) {
  const sat = S.base === 'satelite';
  const sel = S.sel?.tipo === 'agua' && S.sel.id === f.properties.id_objeto;
  return { color: sat ? '#7cc8ff' : '#2b7fd0', weight: sel ? 3 : 1.2, fillColor: '#4aa3e8', fillOpacity: sat ? 0.5 : 0.55 };
}
function eventosRio(f, layer) {
  const p = f.properties;
  layer.bindTooltip(`<b>${p.nombre}</b><br><span class="sub">${p.estado || 'Cauce'} · ${p.longitud_km} km este tramo</span>`, { sticky: true, className: 'map-tip' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('rio', p.id_objeto); });
}
function eventosAgua(f, layer) {
  const p = f.properties;
  layer.bindTooltip(`<b>${p.nombre || NOMBRE_TIPO[p.tipo]}</b><br><span class="sub">${NOMBRE_TIPO[p.tipo]} · ${p.area_km2} km²</span>`, { sticky: true, className: 'map-tip' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('agua', p.id_objeto); });
}
const restilarAgua = () => { redVial.setStyle(estiloRed); if (S.red) renderLeyendaRed(); municipios.setStyle(estiloMunicipio); lineasMpio.setStyle(estiloLineaMpio); contornoGuajira.setStyle(estiloContorno); renderEtiquetasMpio(); riosNombrados.setStyle(estiloRio); riosSinNombre.setStyle(estiloRio); cuerposAgua.setStyle(estiloAgua); };

function detalleRio(p) {
  return `
    ${cabecera('waves', '#e3f2fb', '#1f6f99', p.nombre, 'Tramo de cauce · cartografía básica 1:100.000')}
    <div class="det-chips"><span class="chip ok">IGAC · real</span><span class="chip white">${p.estado || 'Sin estado'}</span></div>
    <div class="kv"><span class="k">Longitud de este tramo</span><span class="v">${p.longitud_km} km</span></div>
    <div class="det-foot">El IGAC divide cada río en tramos; el nombre lo comparten varios. "Permanente" e "intermitente" es la clasificación del IGAC a escala 1:100.000, no una medición de caudal. Geometría simplificada a 25 m. Uso no comercial.</div>`;
}
function detalleAgua(p) {
  return `
    ${cabecera('waves', '#e3f2fb', '#1f6f99', p.nombre || NOMBRE_TIPO[p.tipo], NOMBRE_TIPO[p.tipo])}
    <div class="det-chips"><span class="chip ok">IGAC · real</span></div>
    <div class="kv"><span class="k">Área</span><span class="v">${p.area_km2} km²</span></div>
    <div class="det-foot">Cartografía básica del IGAC a escala 1:100.000: muestra el contorno, no si hay agua hoy (en La Guajira muchas lagunas y jagüeyes se secan). Uso no comercial.</div>`;
}

// ---------------------------------------------------------------------------
// Red vial unificada: la red nacional (INVIAS) y la complementaria (IGAC), sin duplicados, en una sola capa.
// Se distinguen por color: naranja grueso = nacional; rosa = complementaria, en siete clases. Canvas: ~5.300 tramos.
// ---------------------------------------------------------------------------

const NACIONAL = 'Red nacional · INVIAS';
const COMPLEMENTARIA = 'Red complementaria · IGAC';
const ESTILOS_VIA = {   // estilo -> { grupo, rotulo, sat (sobre satelite), calles, ancho, trazo }
  n1: { grupo: NACIONAL, rotulo: 'Primer orden', sat: '#ff8a1f', calles: '#c2570c', ancho: 5, trazo: null },
  n2: { grupo: NACIONAL, rotulo: 'Segundo orden', sat: '#ff8a1f', calles: '#c2570c', ancho: 3.8, trazo: null },
  n0: { grupo: NACIONAL, rotulo: 'Sin categoría en la fuente', sat: '#ff8a1f', calles: '#c2570c', ancho: 3.8, trazo: '3 6' },
  i1: { grupo: COMPLEMENTARIA, rotulo: 'Pavimentada, 2 o más carriles', sat: '#ff5ca8', calles: '#b0256a', ancho: 3, trazo: null },
  i2: { grupo: COMPLEMENTARIA, rotulo: 'Sin pavimentar, 2 o más carriles', sat: '#ff5ca8', calles: '#b0256a', ancho: 2.6, trazo: '9 5' },
  i3: { grupo: COMPLEMENTARIA, rotulo: 'Pavimentada, angosta', sat: '#ff8fc0', calles: '#c4467f', ancho: 2.2, trazo: null },
  i4: { grupo: COMPLEMENTARIA, rotulo: 'Sin pavimentar, angosta', sat: '#ff8fc0', calles: '#c4467f', ancho: 2, trazo: '7 4' },
  i5: { grupo: COMPLEMENTARIA, rotulo: 'Sin pavimentar, solo en tiempo seco', sat: '#ffb8d9', calles: '#d070a0', ancho: 1.6, trazo: '5 4' },
  i6: { grupo: COMPLEMENTARIA, rotulo: 'Trocha sin afirmar, solo en tiempo seco', sat: '#ffd6e8', calles: '#9a6a84', ancho: 1.1, trazo: '2 4' },
  i7: { grupo: COMPLEMENTARIA, rotulo: 'Camino o sendero', sat: '#ffffff', calles: '#7a7a7a', ancho: 0.9, trazo: '1 4' },
};
const lienzoVias = L.canvas({ pane: 'vias', padding: 0.4, tolerance: 5 });
const redVial = L.geoJSON(null, { pane: 'vias', renderer: lienzoVias, style: estiloRed, onEachFeature: eventosRed });
capas.vias.addLayer(redVial);

function estiloRed(f) {
  const c = ESTILOS_VIA[f.properties.estilo];
  const sat = S.base === 'satelite';
  const sel = S.sel?.tipo === 'via' && S.sel.id === f.properties.id_tramo;
  return { color: sat ? c.sat : c.calles, weight: c.ancho + (sel ? 3 : 0), opacity: sel ? 1 : 0.92, dashArray: c.trazo, lineCap: 'round', lineJoin: 'round' };
}
function eventosRed(f, layer) {
  const p = f.properties;
  const titulo = p.fuente === 'INVIAS' ? `Ruta ${p.ruta} · ${p.sector}` : (p.nombre || p.clase);
  const resto = p.fuente === 'INVIAS' ? `INVIAS · ${p.clase.replace('Red nacional, ', '')} · ${p.km} km` : `IGAC · ${p.nombre ? p.clase + ' · ' : ''}${p.accesibilidad || 'accesibilidad sin dato'} · ${p.km} km`;
  layer.bindTooltip(`<b>${titulo}</b><br><span class="sub">${resto}</span>`, { sticky: true, className: 'map-tip' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('via', p.id_tramo); });
}
function renderRedVial() {
  redVial.clearLayers();
  if (!S.red) return;
  redVial.addData({ type: 'FeatureCollection', features: S.red.features.filter((f) => !S.clasesOcultas.has(f.properties.estilo)) });
}
function renderLeyendaRed() {
  const km = {};
  S.red.features.forEach((f) => { km[f.properties.estilo] = (km[f.properties.estilo] || 0) + f.properties.km; });
  const sat = S.base === 'satelite';
  const fila = ([e, c]) => `
    <label><input type="checkbox" data-estilo="${e}"${S.clasesOcultas.has(e) ? '' : ' checked'}>
      <span class="lg-igac" style="border-top:${Math.max(c.ancho, 1.5)}px ${c.trazo ? 'dashed' : 'solid'} ${sat ? c.sat : c.calles}"></span>
      <span class="nom">${c.rotulo}</span><span class="km">${Math.round(km[e] || 0).toLocaleString('es-CO')} km</span></label>`;
  const grupo = (nombre) => {
    const filas = Object.entries(ESTILOS_VIA).filter(([, c]) => c.grupo === nombre);
    const total = filas.reduce((s, [e]) => s + (km[e] || 0), 0);
    return `<div class="leyenda-grupo"><span>${nombre}</span><span class="km">${Math.round(total).toLocaleString('es-CO')} km</span></div>${filas.map(fila).join('')}`;
  };
  document.getElementById('leyenda-vias').innerHTML = grupo(NACIONAL) + grupo(COMPLEMENTARIA);
  document.querySelectorAll('#leyenda-vias input[data-estilo]').forEach((el) => el.addEventListener('change', () => {
    el.checked ? S.clasesOcultas.delete(el.dataset.estilo) : S.clasesOcultas.add(el.dataset.estilo);
    renderRedVial();
  }));
}

function detalleRed(p) {
  const fila = (k, v) => (v ? `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>` : '');
  if (p.fuente === 'INVIAS') {
    const deIgac = (p.superficie_fuente || '').startsWith('IGAC');
    return `
      ${cabecera('route', '#fff1d6', '#b45309', p.sector || p.id_tramo, `Ruta ${p.ruta} · ${p.nombre_ruta || ''}`)}
      <div class="det-chips"><span class="chip ok">INVIAS · real</span><span class="chip white">${p.clase}</span></div>
      ${fila('Administra', p.administrador)}
      ${fila('Calzada', p.calzada)}
      ${fila('Superficie', p.superficie ? `${p.superficie}${deIgac ? ' (según el IGAC)' : ''}` : 'Sin definir en ninguna fuente')}
      ${fila('Longitud de este tramo', `${p.km} km`)}
      <div class="det-foot">Red vial nacional de INVIAS (datos.gov.co, CC BY-SA 4.0): solo troncales, transversales y accesos a capitales. La fuente deja la superficie "por definir"; se tomó de la cartografía del IGAC sobre el mismo trazado, que puede estar desactualizada. Geometría simplificada a 15 m.</div>`;
  }
  const seco = p.accesibilidad === 'Solo en tiempo seco';
  return `
    ${cabecera('route', '#ffe3f0', '#b0256a', p.nombre || p.clase, p.nombre ? p.clase : 'Red complementaria')}
    <div class="det-chips"><span class="chip ok">IGAC · real</span>${seco ? '<span class="chip warn">Solo en tiempo seco</span>' : ''}</div>
    ${fila('Superficie', p.superficie || 'Sin dato en la fuente')}
    ${fila('Ancho', p.carriles)}
    ${fila('Se transita', p.accesibilidad || 'Sin dato en la fuente')}
    ${fila('Longitud de este tramo', `${p.km} km`)}
    <div class="det-foot">Cartografía básica del IGAC a 1:100.000. "Solo en tiempo seco" quiere decir que la fuente la marca intransitable en época de lluvia; no es una medición de hoy. La clase se interpreta de los atributos del IGAC (la fuente no la explica). Geometría simplificada a 20 m. Uso no comercial.</div>`;
}

// ---------------------------------------------------------------------------
// Capa de clima (IDEAM): una variable a la vez
// ---------------------------------------------------------------------------

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

// `var`: clave en Oro. `cortes`: 4 cortes -> 5 clases de color. `oscuras`: cuantas clases llevan texto oscuro.
// Sin `rampa` (presion, nivel): un solo color, porque su valor depende de la altitud o del cauce y una escala comun engañaria.
const VISTAS = {
  lluvia: { titulo: 'Lluvia', unidad: 'mm', icono: 'cloud-rain', dec: 1, color: '#1f6fd0',
    rampa: ['#cfe8fb', '#8ec5ef', '#4a9be0', '#1f6fd0', '#12409b'], oscuras: 2 },
  temperatura: { titulo: 'Temperatura', unidad: '°C', var: 'temperatura', icono: 'thermometer', dec: 1, color: '#e2483a',
    cortes: [26, 28, 30, 32], rampa: ['#9ecae1', '#fee391', '#fdae61', '#f46d43', '#b2182b'], oscuras: 2 },
  viento: { titulo: 'Viento', unidad: 'm/s', var: 'viento_vel', dir: 'viento_dir', icono: 'wind', dec: 1, color: '#1f8a8a',
    cortes: [1.5, 3, 4.5, 6.5], rampa: ['#d7f0ec', '#93d8cd', '#48b7aa', '#1f8a8a', '#0e5560'], oscuras: 2 },
  humedad: { titulo: 'Humedad', unidad: '%', var: 'humedad', icono: 'droplets', dec: 0, color: '#2c7fb8',
    cortes: [50, 65, 75, 85], rampa: ['#f3e5c3', '#d9d7a3', '#a9d6b1', '#5fb7b0', '#2c7fb8'], oscuras: 3 },
  humedad_suelo: { titulo: 'Humedad del suelo', unidad: '%', var: 'humedad_suelo', icono: 'sprout', dec: 0, color: '#7a5c2e',
    cortes: [60, 70, 80, 90], rampa: ['#f5e6c8', '#d9bf8c', '#b58f56', '#7a5c2e', '#4a3418'], oscuras: 2 },
  presion: { titulo: 'Presión', unidad: 'hPa', var: 'presion', icono: 'gauge', dec: 0, color: '#6b7c8a', unico: '#455a64' },
  nivel: { titulo: 'Nivel del río', unidad: 'm', var: 'nivel_rio', icono: 'waves', dec: 2, color: '#1f6f99', unico: '#1f6f99' },
  radiacion: { titulo: 'Radiación', unidad: 'kWh/m²/día', icono: 'sun', dec: 1, color: '#f08c1a', fuente: 'radiacion',
    cortes: [4.8, 5.2, 5.6, 6.0], rampa: ['#fff3c4', '#fde28a', '#fbbf3d', '#f08c1a', '#b45309'], oscuras: 3 },
};
const CORTES_LLUVIA = { mm_7d: [1, 10, 30, 60], mm_14d: [2, 20, 60, 120], mm_30d: [5, 40, 100, 200] };
const cortesDe = (v) => (v === 'lluvia' ? CORTES_LLUVIA[S.ventana] : VISTAS[v].cortes);
const DIAS = { mm_7d: 7, mm_14d: 14, mm_30d: 30 };

const vistaDisponible = (v) => {
  const cfg = VISTAS[v];
  if (v === 'radiacion') return !!S.radiacion?.features?.length;
  if (v === 'lluvia') return (S.clima?.features || []).some((f) => f.properties.mm_14d != null);
  return (S.clima?.features || []).some((f) => f.properties.variables?.[cfg.var] || f.properties.ahora?.[cfg.var]);
};

// Valor mas reciente de una variable en una estacion: en vivo > ultimas horas (Oro) > ultima lectura de la ventana
function lecturaActual(p, varKey) {
  const vivo = S.ahora?.estaciones?.[p.codigo]?.[varKey];
  if (vivo) return { valor: vivo.valor, hora: vivo.hora, rumbo: vivo.rumbo, origen: 'vivo' };
  const snap = p.ahora?.[varKey];
  if (snap) return { valor: snap.valor, hora: snap.hora, rumbo: snap.rumbo, origen: 'reciente' };
  const v = p.variables?.[varKey];
  return v ? { valor: v.ultimo, hora: v.ultima_hora, rumbo: v.rumbo_ultimo, origen: 'ventana' } : null;
}

function claseDe(v, valor) {
  return cortesDe(v).filter((c) => valor >= c).length;
}
function colorDe(v, valor) {
  const cfg = VISTAS[v];
  return cfg.unico || cfg.rampa[claseDe(v, valor)];
}
function tintaDe(v, valor) {
  const cfg = VISTAS[v];
  if (cfg.unico) return '#ffffff';
  return claseDe(v, valor) < cfg.oscuras ? '#10242e' : '#ffffff';
}
const formato = (valor, dec) => (valor == null ? '-' : (dec === 0 || Math.abs(valor) >= 100 ? Math.round(valor) : Number(valor).toFixed(dec)));

function haceTexto(iso) {
  if (!iso) return '';
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 0) return 'ahora';
  if (min < 60) return `hace ${Math.max(min, 1)} min`;
  if (min < 24 * 60) return `hace ${Math.round(min / 60)} h`;
  return ui.fecha(iso);
}

function flechaViento(dirGrados) {
  // dirGrados es de donde VIENE el viento; la flecha apunta hacia donde va
  return `<svg class="flecha" viewBox="0 0 24 24" style="transform:rotate(${(dirGrados + 180) % 360}deg)"><path d="M12 3v15M6 12l6-7 6 7" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

// Puntos de una variable: [{ p, lon, lat, valor, sd, parcial, ... }]
function puntosVista(v) {
  const cfg = VISTAS[v];
  const out = [];
  if (v === 'radiacion') {
    const mes = (S.clima?.metadata?.mes_actual || new Date().getMonth() + 1) - 1;
    (S.radiacion?.features || []).forEach((f) => {
      const p = f.properties;
      const wh = p.meses?.[mes] ?? p.anual;
      if (wh == null) return;
      const [lon, lat] = f.geometry.coordinates;
      out.push({ id: `rad:${p.estacion}|${p.tipo}`, p, lon, lat, valor: wh / 1000, radiacion: true });
    });
    return out;
  }
  (S.clima?.features || []).forEach((f) => {
    const p = f.properties;
    const [lon, lat] = f.geometry.coordinates;
    if (v === 'lluvia') {
      if (p.mm_14d == null) return;
      const sd = p.dias_con_dato < 5;
      out.push({ id: p.codigo, p, lon, lat, valor: p[S.ventana], sd, parcial: !sd && p.cobertura < 0.5, cota: !sd && p.cobertura < 0.5 });
      return;
    }
    const l = lecturaActual(p, cfg.var);
    if (!l || l.valor == null) return;
    const dir = cfg.dir ? lecturaActual(p, cfg.dir) : null;
    out.push({ id: p.codigo, p, lon, lat, valor: l.valor, hora: l.hora, dir: dir?.valor, rumbo: dir?.rumbo, parcial: (p.variables?.[cfg.var]?.cobertura ?? 1) < 0.5 });
  });
  return out;
}

// dx: desplazamiento horizontal en px para que las pastillas de varias variables no se tapen
function iconoEstacion(pt, v, dx = 0) {
  const cfg = VISTAS[v];
  const sel = S.sel && (S.sel.tipo === 'estacion' || S.sel.tipo === 'radiacion') && S.sel.id === pt.id;
  const fondo = pt.sd ? '#8a928d' : colorDe(v, pt.valor);
  const tinta = pt.sd ? '#ffffff' : tintaDe(v, pt.valor);
  const texto = pt.sd ? 's/d' : `${pt.cota ? '≥' : ''}${formato(pt.valor, cfg.dec)}`;
  const flecha = pt.dir != null ? flechaViento(pt.dir) : '';
  return L.divIcon({
    className: 'est', iconSize: [0, 0],
    html: `<div class="est-pin${pt.parcial ? ' parcial' : ''}${sel ? ' sel' : ''}" style="background:${fondo};color:${tinta};margin-left:${dx}px">${flecha}${texto}</div>`,
  });
}

function tooltipEstacion(pt, v) {
  const cfg = VISTAS[v];
  const p = pt.p;
  if (pt.radiacion) return `<b>${p.estacion}</b><br><span class="sub">${p.municipio} · ${formato(pt.valor, 1)} kWh/m²/día de media en ${MESES[(S.clima?.metadata?.mes_actual || 1) - 1]}</span>`;
  if (v === 'lluvia') {
    return pt.sd
      ? `<b>${p.nombre}</b><br><span class="sub">${p.municipio} · sin datos suficientes (${p.dias_con_dato} de 30 días)</span>`
      : `<b>${p.nombre}</b><br><span class="sub">${p.municipio} · ${pt.cota ? 'al menos ' : ''}${p[S.ventana]} mm en ${DIAS[S.ventana]} días</span>`;
  }
  return `<b>${p.nombre}</b><br><span class="sub">${cfg.titulo} · ${formato(pt.valor, cfg.dec)} ${cfg.unidad}${pt.rumbo ? ` del ${pt.rumbo}` : ''} · ${haceTexto(pt.hora)}</span>`;
}

// ---------------------------------------------------------------------------
// Con una sola variable: una pastilla por estacion. Con dos o mas: una FICHA por estacion
// (tabla compacta con una celda por variable) colocada sin taparse con las demas.
// ---------------------------------------------------------------------------

const UNIDAD_CORTA = { lluvia: 'mm', temperatura: '°C', viento: 'm/s', humedad: '%', humedad_suelo: '%', presion: 'hPa', nivel: 'm', radiacion: 'kWh' };
const FICHA = { celdaW: 78, celdaH: 22, gap: 3, pad: 6, cabecera: 15, margen: 6 };
const gFichas = L.layerGroup();
const lineasFicha = L.layerGroup();
S.fichas = [];
S.modoFichas = false;

// Agrupa por estacion lo que muestra cada variable encendida (la radiacion se pega a su estacion del catalogo)
function fichasPorEstacion(encendidas) {
  const conDatos = new Set((S.clima?.features || []).map((f) => f.properties.codigo));
  const est = new Map();
  encendidas.forEach((v) => {
    puntosVista(v).forEach((pt) => {
      let clave = pt.id;
      if (pt.radiacion && pt.p.codigo && conDatos.has(pt.p.codigo)) clave = pt.p.codigo;
      let e = est.get(clave);
      if (!e) {
        e = { id: clave, lon: pt.lon, lat: pt.lat, nombre: pt.radiacion ? pt.p.estacion : pt.p.nombre, celdas: [] };
        est.set(clave, e);
      }
      if (e.celdas.some((c) => c.v === v)) return;   // dos sensores de radiacion en la misma estacion: se queda el primero
      e.celdas.push({ v, pt });
    });
  });
  return [...est.values()];
}

function celdaFicha(v, pt) {
  const cfg = VISTAS[v];
  const fondo = pt.sd ? '#8a928d' : colorDe(v, pt.valor);
  const tinta = pt.sd ? '#ffffff' : tintaDe(v, pt.valor);
  const valor = pt.sd ? 's/d' : `${pt.cota ? '≥' : ''}${formato(pt.valor, cfg.dec)}`;
  const icono = pt.dir != null ? flechaViento(pt.dir) : `<i data-lucide="${cfg.icono}"></i>`;
  const detalle = pt.sd ? 'sin datos suficientes' : `${formato(pt.valor, cfg.dec)} ${cfg.unidad}${pt.rumbo ? ` del ${pt.rumbo}` : ''}${pt.hora ? ` · ${haceTexto(pt.hora)}` : ''}`;
  return `<button class="fc-c${pt.parcial ? ' parcial' : ''}" data-v="${v}" data-rad="${pt.radiacion ? pt.id : ''}" title="${cfg.titulo}: ${detalle}" style="background:${fondo};color:${tinta}">${icono}<b>${valor}</b><span>${UNIDAD_CORTA[v]}</span></button>`;
}

function medidasFicha(n) {
  const cols = n <= 2 ? 1 : 2;
  const filas = Math.ceil(n / cols);
  const { celdaW, celdaH, gap, pad, cabecera } = FICHA;
  return { cols, w: cols * celdaW + (cols - 1) * gap + 2 * pad, h: pad + cabecera + filas * celdaH + (filas - 1) * gap + pad };
}

// Coloca cada ficha en pixeles de pantalla: prueba posiciones alrededor de su estacion, cada vez mas lejos,
// y se queda con la primera que no pisa otra ficha ni el punto de otra estacion
function colocarFichas() {
  gFichas.clearLayers();
  lineasFicha.clearLayers();
  if (!S.modoFichas) return;
  const z = mapa.getZoom();
  const pb = mapa.getPixelBounds();
  const vista = { min: pb.min.add([8, 8]), max: pb.max.subtract([8, 8]) };
  const items = S.fichas.map((e) => ({ e, p: mapa.project([e.lat, e.lon], z), ...medidasFicha(e.celdas.length) }));
  // las estaciones con mas vecinas cerca eligen primero
  items.forEach((a) => { a.vecinas = items.filter((b) => b !== a && a.p.distanceTo(b.p) < 140).length; });
  items.sort((a, b) => b.vecinas - a.vecinas);

  const dirs = [[0, -1], [1, 0], [-1, 0], [0, 1], [1, -1], [-1, -1], [1, 1], [-1, 1]];
  const ocupados = [];   // rectangulos ya usados
  const rectDe = (cx, cy, w, h, m = 0) => ({ x0: cx - w / 2 - m, y0: cy - h / 2 - m, x1: cx + w / 2 + m, y1: cy + h / 2 + m });
  const cruza = (a, b) => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
  const puntos = items.map((a) => rectDe(a.p.x, a.p.y, 14, 14));

  items.forEach((a) => {
    let mejor = null;
    for (let anillo = 0; anillo < 8 && !mejor; anillo++) {
      for (const [dx, dy] of dirs) {
        const dist = 14 + anillo * 46;
        const cx = a.p.x + dx * (a.w / 2 + dist) * (dx && dy ? 0.75 : 1);
        const cy = a.p.y + dy * (a.h / 2 + dist) * (dx && dy ? 0.75 : 1);
        const r = rectDe(cx, cy, a.w, a.h, FICHA.margen / 2);
        const dentro = r.x0 >= vista.min.x && r.x1 <= vista.max.x && r.y0 >= vista.min.y && r.y1 <= vista.max.y;
        if (!dentro) continue;
        if (ocupados.some((o) => cruza(r, o))) continue;
        if (puntos.some((q, k) => items[k] !== a && cruza(r, q))) continue;
        mejor = { cx, cy, r };
        break;
      }
    }
    if (!mejor) {   // sin hueco libre a esta escala: arriba de su estacion (acercar el mapa lo resuelve)
      const cx = a.p.x, cy = a.p.y - a.h / 2 - 14;
      mejor = { cx, cy, r: rectDe(cx, cy, a.w, a.h, FICHA.margen / 2) };
    }
    ocupados.push(mejor.r);
    a.cx = mejor.cx;
    a.cy = mejor.cy;
  });

  const claro = S.base === 'calles';
  items.forEach((a, orden) => {
    const est = L.latLng(a.e.lat, a.e.lon);
    const centro = mapa.unproject([a.cx, a.cy], z);
    L.polyline([est, centro], { pane: 'fichasLineas', interactive: false, color: claro ? '#33413a' : '#ffffff', weight: 1.5, opacity: 0.9 }).addTo(lineasFicha);
    L.circleMarker(est, { pane: 'fichasLineas', radius: 4.5, color: claro ? '#33413a' : '#ffffff', weight: 2, fillColor: '#16201b', fillOpacity: 1, interactive: false }).addTo(lineasFicha);

    const sel = S.sel && S.sel.tipo === 'estacion' && S.sel.id === a.e.id;
    const html = `<div class="ficha${sel ? ' sel' : ''}" style="width:${a.w}px;height:${a.h}px">
        <div class="fc-h">${a.e.nombre}</div>
        <div class="fc-g" style="grid-template-columns:repeat(${a.cols},1fr)">${a.e.celdas.map((c) => celdaFicha(c.v, c.pt)).join('')}</div></div>`;
    L.marker(centro, { icon: L.divIcon({ className: 'ficha-icono', iconSize: [a.w, a.h], iconAnchor: [a.w / 2, a.h / 2], html }), zIndexOffset: 1000 - orden })
      .on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        const c = e.originalEvent.target.closest('.fc-c');
        const v = c?.dataset.v;
        if (c?.dataset.rad && !S.clima.features.some((f) => f.properties.codigo === a.e.id)) seleccionar('radiacion', c.dataset.rad);
        else seleccionar('estacion', a.e.id, v);
      })
      .addTo(gFichas);
  });
  ui.icons();
}
mapa.on('zoomend resize', () => { if (S.modoFichas) colocarFichas(); });

// Redibuja las variables encendidas: pastillas (una variable) o fichas (varias)
function renderClima() {
  const disponibles = Object.keys(VISTAS).filter(vistaDisponible);
  const encendidas = disponibles.filter((v) => S.activas.has(v));
  S.modoFichas = encendidas.length >= 2;

  disponibles.forEach((v) => {
    const grupo = gClima[v];
    if (!grupo) return;
    grupo.clearLayers();
    if (!S.modoFichas && encendidas.includes(v)) {
      puntosVista(v).forEach((pt) => {
        L.marker([pt.lat, pt.lon], { icon: iconoEstacion(pt, v, 0), zIndexOffset: Math.round(pt.valor || 0) })
          .bindTooltip(tooltipEstacion(pt, v), { className: 'map-tip', direction: 'top', offset: [0, -16] })
          .on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar(pt.radiacion ? 'radiacion' : 'estacion', pt.id, v); })
          .addTo(grupo);
      });
      if (!mapa.hasLayer(grupo)) grupo.addTo(mapa);
    } else if (mapa.hasLayer(grupo)) {
      mapa.removeLayer(grupo);
    }
    const sub = document.getElementById(`sub-${v}`);
    if (sub) sub.textContent = v === 'lluvia' ? `${puntosVista(v).length} estaciones · acumulado de ${DIAS[S.ventana]} días` : `${puntosVista(v).length} estaciones`;
    renderRampa(v);
  });

  if (S.modoFichas) {
    S.fichas = fichasPorEstacion(encendidas);
    if (!mapa.hasLayer(lineasFicha)) lineasFicha.addTo(mapa);
    if (!mapa.hasLayer(gFichas)) gFichas.addTo(mapa);
    colocarFichas();
  } else {
    gFichas.clearLayers();
    lineasFicha.clearLayers();
  }
}

function renderRampa(v) {
  const cfg = VISTAS[v];
  const cont = document.getElementById(`rampa-${v}`);
  if (!cont) return;
  if (cfg.unico) {
    cont.innerHTML = `<p class="fuente">Última lectura de cada estación en ${cfg.unidad}. Sin escala de color: el valor depende ${v === 'presion' ? 'de la altitud de cada estación' : 'del cauce medido'}, y comparar colores entre estaciones engañaría.</p>`;
    return;
  }
  const c = cortesDe(v);
  const et = [`< ${c[0]}`, `${c[0]} – ${c[1]}`, `${c[1]} – ${c[2]}`, `${c[2]} – ${c[3]}`, `≥ ${c[3]}`];
  cont.innerHTML = cfg.rampa.map((col, i) => `<div class="fila"><span class="sw" style="background:${col}"></span><span>${et[i]} ${cfg.unidad}</span></div>`).join('');
}

// Una tarjeta con interruptor por cada variable disponible
function renderTarjetasClima() {
  const cont = document.getElementById('clima-capas');
  cont.innerHTML = Object.entries(VISTAS).filter(([k]) => vistaDisponible(k)).map(([k, v]) => `
    <section class="capa capa-var${S.activas.has(k) ? '' : ' off'}" id="capa-clima_${k}">
      <div class="capa-head">
        <span class="tile" style="background:${ui.alpha(v.color, 0.14)};color:${v.color}"><i data-lucide="${v.icono}"></i></span>
        <div class="grow"><div class="t">${v.titulo}</div><div class="s" id="sub-${k}">-</div></div>
        <label class="switch"><input type="checkbox" data-clima="${k}"${S.activas.has(k) ? ' checked' : ''}><span></span></label>
      </div>
      <div class="capa-body">
        ${k === 'lluvia' ? `<div class="seg full" id="f-ventana">
          <button data-v="mm_7d"${S.ventana === 'mm_7d' ? ' class="on"' : ''}>7 días</button>
          <button data-v="mm_14d"${S.ventana === 'mm_14d' ? ' class="on"' : ''}>14 días</button>
          <button data-v="mm_30d"${S.ventana === 'mm_30d' ? ' class="on"' : ''}>30 días</button>
        </div>` : ''}
        <div class="rampa" id="rampa-${k}"></div>
      </div>
    </section>`).join('');
  Object.keys(VISTAS).forEach((k) => { gClima[k] = gClima[k] || L.layerGroup(); });

  cont.querySelectorAll('input[data-clima]').forEach((el) => el.addEventListener('change', () => {
    const k = el.dataset.clima;
    el.checked ? S.activas.add(k) : S.activas.delete(k);
    document.getElementById(`capa-clima_${k}`).classList.toggle('off', !el.checked);
    renderClima();
  }));
  cont.querySelectorAll('#f-ventana button').forEach((b) => b.addEventListener('click', () => {
    cont.querySelectorAll('#f-ventana button').forEach((x) => x.classList.toggle('on', x === b));
    S.ventana = b.dataset.v;
    renderClima();
  }));
  ui.icons();
}

function renderEstadoVivo() {
  const el = document.getElementById('estado-vivo');
  const a = S.ahora;
  if (!a) { el.innerHTML = '<span class="dot" style="background:var(--muted)"></span> Consultando lecturas recientes del IDEAM...'; return; }
  if (a.origen === 'en_vivo') {
    el.innerHTML = `<span class="dot vivo"></span> En vivo · lectura más reciente ${haceTexto(a.lectura_mas_reciente)}`;
  } else if (a.origen === 'respaldo') {
    el.innerHTML = `<span class="dot" style="background:var(--lvl-alto)"></span> Sin conexión al IDEAM; se usa el último respaldo (${haceTexto(a.lectura_mas_reciente)})`;
  } else {
    el.innerHTML = '<span class="dot" style="background:var(--muted)"></span> Sin lecturas recientes; se muestran las de los últimos 30 días';
  }
}

// ---------------------------------------------------------------------------
// Capa de riesgos
// ---------------------------------------------------------------------------

function riesgosFiltrados() {
  const f = S.filtro;
  return S.riesgos.filter((r) => (!f.categoria || r.properties.categoria === f.categoria) && (!f.tipo || r.properties.tipo === f.tipo));
}

function renderRiesgos() {
  const lista = riesgosFiltrados();
  capas.riesgos.clearLayers();
  lista.forEach((r) => {
    const p = r.properties;
    const [lon, lat] = r.geometry.coordinates;
    L.circleMarker([lat, lon], {
      pane: 'riesgosPane', radius: 3.5 + Math.min(p.severidad, 25) / 6, color: '#fff', weight: 1.2,
      fillColor: p.tipo === 'oportunidad' ? '#4da3ff' : ui.css('--lvl-critico'), fillOpacity: 0.92,
    })
      .bindTooltip(`<b>${p.id_riesgo}</b> · ${ui.cat(p.categoria).label}<br><span class="sub">${ui.ESTADO[p.estado]?.label || p.estado} · severidad ${p.severidad}</span>`, { className: 'map-tip' })
      .on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('riesgo', p.id_riesgo); })
      .addTo(capas.riesgos);
  });
  document.getElementById('sub-riesgos').textContent =
    `${lista.length}${lista.length === S.riesgos.length ? '' : ` de ${S.riesgos.length}`} riesgos en el mapa`;
}

function renderFiltroCategorias() {
  const cats = [['', 'Todas'], ...Object.entries(ui.CATEGORIA).filter(([k]) => k !== 'sin_clasificar').map(([k, v]) => [k, v.corto])];
  const cont = document.getElementById('f-categoria');
  cont.innerHTML = cats.map(([v, t]) => `<button class="chip${S.filtro.categoria === v ? ' on' : ''}" data-v="${v}">${t}</button>`).join('');
  cont.querySelectorAll('.chip').forEach((b) => b.addEventListener('click', () => {
    S.filtro.categoria = b.dataset.v;
    renderFiltroCategorias();
    renderRiesgos();
  }));
}

// ---------------------------------------------------------------------------
// Detalle flotante
// ---------------------------------------------------------------------------

function seleccionar(tipo, id, variable) {
  S.sel = { tipo, id };
  if (tipo === 'estacion') {
    const p = estacion(id);
    S.varDetalle = varInicialDetalle(p, variable);
  }
  paquetes.setStyle(estiloPaquete);
  restilarAgua();
  renderClima();
  renderDetalle();
}

function cerrarDetalle() {
  S.sel = null;
  paquetes.setStyle(estiloPaquete);
  restilarAgua();
  renderClima();
  document.getElementById('detalle').hidden = true;
  if (S.chart) { S.chart.destroy(); S.chart = null; }
}

function cabecera(icono, fondo, color, titulo, sub) {
  return `
    <div class="det-head">
      <span class="tile" style="background:${fondo};color:${color}"><i data-lucide="${icono}"></i></span>
      <div class="grow"><div class="card-title">${titulo}</div><div class="card-sub">${sub}</div></div>
      <button class="icon-btn sm ghost" id="det-x" title="Cerrar"><i data-lucide="x"></i></button>
    </div>`;
}

const estacion = (codigo) => S.clima?.features.find((f) => f.properties.codigo === codigo)?.properties;

// Variables graficables de una estacion, en orden de lectura
function variablesDe(p) {
  const out = [];
  if (p.mm_14d != null) out.push('lluvia');
  ['temperatura', 'viento', 'humedad', 'humedad_suelo', 'presion', 'nivel'].forEach((v) => {
    const k = VISTAS[v].var;
    if (p.variables?.[k] || p.ahora?.[k]) out.push(v);
  });
  return out;
}
function varInicialDetalle(p, preferida) {
  const vars = variablesDe(p);
  return vars.includes(preferida) ? preferida : vars[0] || null;
}

const conSerie = (p, v) => v === 'lluvia' || !!p.variables?.[VISTAS[v]?.var];

function celdaAhora(p, v) {
  const cfg = VISTAS[v];
  const l = v === 'lluvia' ? null : lecturaActual(p, cfg.var);
  if (v === 'lluvia') {
    return `<button class="ahora-c${S.varDetalle === v ? ' on' : ''}" data-v="${v}"><span class="l">${cfg.titulo}</span><span class="v">${p.mm_14d != null ? formato(p.mm_14d, 1) : '-'}<small> mm · 14 d</small></span></button>`;
  }
  const dir = cfg.dir ? lecturaActual(p, cfg.dir) : null;
  return `<button class="ahora-c${S.varDetalle === v ? ' on' : ''}" data-v="${v}"><span class="l">${cfg.titulo}</span><span class="v">${l ? formato(l.valor, cfg.dec) : '-'}<small> ${cfg.unidad}${dir?.rumbo ? ` · ${dir.rumbo}` : ''}</small></span></button>`;
}

function contextoEstacion(p) {
  const mes = (S.clima?.metadata?.mes_actual || new Date().getMonth() + 1) - 1;
  const filas = [];
  const nl = p.normales?.precipitacion;
  if (nl && nl.meses[mes] != null && p.mm_30d != null) {
    const pct = nl.meses[mes] > 0 ? Math.round((p.mm_30d / nl.meses[mes]) * 100) : null;
    filas.push(`<div class="kv"><span class="k">Lluvia normal de ${MESES[mes]} (${nl.periodo})</span><span class="v">${nl.meses[mes]} mm${pct != null ? ` · van ${p.mm_30d} mm (${pct} %)` : ''}</span></div>`);
  }
  const nt = p.normales?.temperatura_media;
  if (nt && nt.meses[mes] != null) filas.push(`<div class="kv"><span class="k">Temperatura media normal de ${MESES[mes]}</span><span class="v">${nt.meses[mes]} °C</span></div>`);
  if (p.radiacion?.meses?.[mes] != null) filas.push(`<div class="kv"><span class="k">Radiación media de ${MESES[mes]}</span><span class="v">${(p.radiacion.meses[mes] / 1000).toFixed(1)} kWh/m²/día</span></div>`);
  if (!filas.length) return '';
  return `<div class="sec-ctx">Contexto climático</div>${filas.join('')}`;
}

function filasVariable(p, v) {
  const cfg = VISTAS[v];
  if (v === 'lluvia') {
    return `
      <div class="kv"><span class="k">Acumulado 7 / 14 / 30 días</span><span class="v">${p.mm_7d} / ${p.mm_14d} / ${p.mm_30d} mm</span></div>
      <div class="kv"><span class="k">Máximo en un día</span><span class="v">${p.max_diario_mm} mm</span></div>
      <div class="kv"><span class="k">Última lectura</span><span class="v">${ui.fecha(p.ultimo_dato + 'T12:00:00')}</span></div>
      <div class="kv"><span class="k">Cobertura de datos</span><span class="v">${Math.round(p.cobertura * 100)}% · ${p.dias_con_dato} de 30 días</span></div>`;
  }
  const s = p.variables?.[cfg.var];
  const l = lecturaActual(p, cfg.var);
  const dir = cfg.dir ? p.variables?.[cfg.dir] : null;
  if (!s) {
    return l ? `<div class="kv"><span class="k">Última lectura</span><span class="v">${formato(l.valor, cfg.dec)} ${cfg.unidad} · ${haceTexto(l.hora)}</span></div>` : '';
  }
  const filas = [
    l ? `<div class="kv"><span class="k">Última lectura</span><span class="v">${formato(l.valor, cfg.dec)} ${cfg.unidad} · ${haceTexto(l.hora)}</span></div>` : '',
    `<div class="kv"><span class="k">Promedio últimas 24 h</span><span class="v">${formato(s.prom_24h, cfg.dec)} ${cfg.unidad}</span></div>`,
    `<div class="kv"><span class="k">30 días: mín · media · máx</span><span class="v">${formato(s.min_30d, cfg.dec)} · ${formato(s.media_30d, cfg.dec)} · ${formato(s.max_30d, cfg.dec)} ${cfg.unidad}</span></div>`,
  ];
  if (dir) filas.push(`<div class="kv"><span class="k">Dirección predominante (30 d)</span><span class="v">${Math.round(dir.media_30d)}° · viento del ${dir.rumbo_ultimo || '-'} ahora</span></div>`);
  filas.push(`<div class="kv"><span class="k">Cobertura de datos</span><span class="v">${Math.round(s.cobertura * 100)}% · ${s.dias_con_dato} de 30 días</span></div>`);
  return filas.join('');
}

function detalleEstacion(p) {
  const vars = variablesDe(p);
  const cfg = VISTAS[S.varDetalle] || VISTAS.lluvia;
  return `
    ${cabecera('radio-tower', '#e3f2fb', '#1f6f99', p.nombre, `${p.municipio} · estación del IDEAM ${p.codigo}`)}
    <div class="det-chips">
      <span class="chip ok">IDEAM · real</span>
      <span class="chip white">${p.categoria}${p.tecnologia ? ' · ' + p.tecnologia : ''}</span>
      ${p.altitud != null ? `<span class="chip white">${Math.round(p.altitud)} m s. n. m.</span>` : ''}
    </div>
    <div class="ahora-grid">${vars.map((v) => celdaAhora(p, v)).join('')}</div>
    ${conSerie(p, S.varDetalle)
    ? `<div class="det-serie-t">${cfg.titulo}${S.varDetalle === 'lluvia' ? ' · lluvia diaria' : ' · últimos 30 días'}</div>
    <div class="chart-mini"><canvas id="chart-serie"></canvas></div>`
    : `<div class="det-nota">Para esta variable el IDEAM solo publica, en esta estación, las lecturas de las últimas horas; no hay serie de 30 días.</div>`}
    ${S.varDetalle ? filasVariable(p, S.varDetalle) : ''}
    ${contextoEstacion(p)}
    <div class="det-foot">Datos abiertos del IDEAM (datos.gov.co, CC BY-SA 4.0). La lluvia es la suma de las lecturas del pluviómetro, sin duplicados.
      ${p.cobertura < 0.5 && p.mm_14d != null ? '<b>Cobertura baja: el acumulado de lluvia puede estar subestimado.</b>' : ''}</div>`;
}

function detalleRadiacion(p) {
  const mes = (S.clima?.metadata?.mes_actual || 1) - 1;
  return `
    ${cabecera('sun', '#fff3c4', '#b45309', p.estacion, `${p.municipio} · estación ${p.tipo?.toLowerCase() || ''}`)}
    <div class="det-chips"><span class="chip ok">IDEAM · real</span><span class="chip white">Promedio histórico</span>${p.altitud != null ? `<span class="chip white">${p.altitud} m s. n. m.</span>` : ''}</div>
    <div class="det-num"><div class="num">${(p.meses[mes] / 1000).toFixed(1)}</div><div class="u">kWh/m²/día en ${MESES[mes]}</div></div>
    <div class="chart-mini"><canvas id="chart-serie"></canvas></div>
    <div class="kv"><span class="k">Promedio anual</span><span class="v">${(p.anual / 1000).toFixed(2)} kWh/m²/día</span></div>
    <div class="det-foot">El IDEAM publica solo el promedio mensual y anual de la radiación global (Wh/m² por día), no una serie diaria, y solo en estaciones con sensor calibrado.</div>`;
}

function detallePaquete(p) {
  const propios = S.riesgos.map((r) => r.properties).filter((r) => r.id_paquete_trabajo === p.id_paquete);
  const amenazas = propios.filter((r) => r.tipo === 'amenaza').length;
  return `
    ${cabecera('hexagon', 'var(--green-50)', 'var(--green-700)', ui.nombreCorto(p.nombre), p.id_paquete)}
    <div class="det-chips"><span class="chip warn">Sintético</span>${p.ruta_critica ? '<span class="chip">Ruta crítica</span>' : ''}</div>
    <div class="kv"><span class="k">Riesgos en el paquete</span><span class="v">${propios.length}</span></div>
    <div class="kv"><span class="k">Amenazas / oportunidades</span><span class="v">${amenazas} / ${propios.length - amenazas}</span></div>
    <div class="kv"><span class="k">Materializados</span><span class="v">${propios.filter((r) => r.estado === 'materializado').length}</span></div>
    <div class="kv"><span class="k">Próximos a materializarse</span><span class="v">${propios.filter((r) => r.estado === 'proximo_a_materializarse').length}</span></div>`;
}

function detalleRiesgo(p) {
  const c = ui.cat(p.categoria), est = ui.ESTADO[p.estado] || { label: p.estado, lvl: 'bajo' };
  return `
    ${cabecera(c.icon, c.bg, c.fg, p.id_riesgo, c.label)}
    <div class="det-chips"><span class="chip warn">Sintético</span><span class="chip white">${p.tipo === 'oportunidad' ? 'Oportunidad' : 'Amenaza'}</span></div>
    <div class="kv"><span class="k">Estado</span><span class="v"><span class="status"><span class="dot ${est.lvl}"></span>${est.label}</span></span></div>
    <div class="kv"><span class="k">Probabilidad × impacto</span><span class="v">${p.probabilidad} × ${p.impacto} = ${p.severidad}</span></div>
    <div class="kv"><span class="k">Paquete</span><span class="v">${ui.nombreCorto((S.paquetes.features.find((f) => f.properties.id_paquete === p.id_paquete_trabajo) || {}).properties?.nombre || p.id_paquete_trabajo)}</span></div>
    <div class="kv"><span class="k">Identificado</span><span class="v">${ui.fecha(String(p.fecha_identificacion).slice(0, 10) + 'T12:00:00')}</span></div>
    <div class="kv"><span class="k">Ubicación</span><span class="v">${p.geolocalizacion_inferida ? 'Aproximada (centro del paquete)' : 'Con coordenadas'}</span></div>
    <div class="det-foot">Acción de tratamiento: ${p.accion_tratamiento || '-'}</div>`;
}

function renderDetalle() {
  const el = document.getElementById('detalle');
  if (S.chart) { S.chart.destroy(); S.chart = null; }
  if (!S.sel) { el.hidden = true; return; }

  let p;
  if (S.sel.tipo === 'estacion') {
    p = estacion(S.sel.id);
    if (p) el.innerHTML = detalleEstacion(p);
  } else if (S.sel.tipo === 'radiacion') {
    p = S.radiacion.features.find((f) => `rad:${f.properties.estacion}|${f.properties.tipo}` === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleRadiacion(p);
  } else if (S.sel.tipo === 'municipio') {
    p = S.municipios.features.find((f) => f.properties.codigo === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleMunicipio(p);
  } else if (S.sel.tipo === 'rio') {
    p = S.rios.features.find((f) => f.properties.id_objeto === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleRio(p);
  } else if (S.sel.tipo === 'agua') {
    p = S.agua.features.find((f) => f.properties.id_objeto === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleAgua(p);
  } else if (S.sel.tipo === 'via') {
    p = S.red.features.find((f) => f.properties.id_tramo === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleRed(p);
  } else if (S.sel.tipo === 'paquete') {
    p = S.paquetes.features.find((f) => f.properties.id_paquete === S.sel.id)?.properties;
    if (p) el.innerHTML = detallePaquete(p);
  } else {
    p = S.riesgos.find((r) => r.properties.id_riesgo === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleRiesgo(p);
  }
  if (!p) { el.hidden = true; return; }
  el.hidden = false;
  el.scrollTop = 0;
  ui.icons();
  document.getElementById('det-x').addEventListener('click', cerrarDetalle);
  if (S.sel.tipo === 'estacion' && S.varDetalle) {
    el.querySelectorAll('.ahora-c').forEach((b) => b.addEventListener('click', () => {
      S.varDetalle = b.dataset.v;
      const y = el.scrollTop;
      renderDetalle();
      el.scrollTop = y;
    }));
    if (conSerie(p, S.varDetalle)) dibujarSerie(p, S.varDetalle);
  }
  if (S.sel.tipo === 'radiacion') dibujarRadiacion(p);
}

// ---------------------------------------------------------------------------
// Graficos
// ---------------------------------------------------------------------------

const OPC_BASE = () => ({
  maintainAspectRatio: false, animation: { duration: 250 },
  scales: {
    x: { display: false },
    y: { grid: { color: ui.css('--line') }, border: { display: false }, ticks: { maxTicksLimit: 4, color: ui.css('--muted') } },
  },
});

function dibujarSerie(p, v) {
  const cfg = VISTAS[v];
  const cnv = document.getElementById('chart-serie');
  if (!cnv) return;
  if (v === 'lluvia') {
    S.chart = new Chart(cnv, {
      type: 'bar',
      data: { labels: p.serie.map((s) => s.dia), datasets: [{ data: p.serie.map((s) => s.mm), backgroundColor: p.serie.map((s) => (s.mm == null ? 'transparent' : cfg.color)), borderRadius: 3, barPercentage: 0.9, categoryPercentage: 1 }] },
      options: { ...OPC_BASE(), scales: { ...OPC_BASE().scales, y: { ...OPC_BASE().scales.y, beginAtZero: true } },
        plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (i) => ui.fecha(i[0].label + 'T12:00:00'), label: (c) => (c.raw == null ? 'Sin dato' : `${c.raw} mm`) } } } },
    });
    return;
  }
  const s = p.variables[cfg.var].serie;
  const esDir = false;
  const datasets = [{ label: 'Media', data: s.map((d) => d.media), borderColor: cfg.color, backgroundColor: ui.alpha(cfg.color, 0.12), borderWidth: 2, pointRadius: 0, tension: 0.35, spanGaps: false, fill: false }];
  if (!esDir && s.some((d) => d.max != null)) {
    datasets.push({ label: 'Máx', data: s.map((d) => d.max), borderColor: ui.alpha(cfg.color, 0.45), borderWidth: 1, borderDash: [4, 3], pointRadius: 0, tension: 0.35 });
    datasets.push({ label: 'Mín', data: s.map((d) => d.min), borderColor: ui.alpha(cfg.color, 0.45), borderWidth: 1, borderDash: [4, 3], pointRadius: 0, tension: 0.35 });
  }
  S.chart = new Chart(cnv, {
    type: 'line', data: { labels: s.map((d) => d.dia), datasets },
    options: { ...OPC_BASE(), interaction: { intersect: false, mode: 'index' },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (i) => ui.fecha(i[0].label + 'T12:00:00'), label: (c) => `${c.dataset.label}: ${c.raw == null ? 'sin dato' : c.raw + ' ' + cfg.unidad}` } } } },
  });
}

function dibujarRadiacion(p) {
  const cnv = document.getElementById('chart-serie');
  const mes = (S.clima?.metadata?.mes_actual || 1) - 1;
  const cfg = VISTAS.radiacion;
  S.chart = new Chart(cnv, {
    type: 'bar',
    data: { labels: ['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], datasets: [{ data: p.meses.map((v) => (v == null ? null : v / 1000)), backgroundColor: p.meses.map((_, i) => (i === mes ? cfg.color : ui.alpha(cfg.color, 0.35))), borderRadius: 4 }] },
    options: { ...OPC_BASE(), scales: { x: { grid: { display: false }, border: { display: false }, ticks: { color: ui.css('--muted') } }, y: { ...OPC_BASE().scales.y, beginAtZero: false } },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { label: (c) => `${Number(c.raw).toFixed(2)} kWh/m²/día` } } } },
  });
}

// ---------------------------------------------------------------------------
// Controles
// ---------------------------------------------------------------------------

document.querySelectorAll('.map-overlay').forEach((el) => {
  L.DomEvent.disableClickPropagation(el);
  L.DomEvent.disableScrollPropagation(el);
});
mapa.on('click', () => { if (S.sel) cerrarDetalle(); });
document.getElementById('zoom-in').addEventListener('click', () => mapa.zoomIn());
document.getElementById('zoom-out').addEventListener('click', () => mapa.zoomOut());
document.getElementById('btn-centrar').addEventListener('click', encuadrar);

document.querySelectorAll('#seg-base button').forEach((b) => b.addEventListener('click', () => {
  if (S.base === b.dataset.base) return;
  mapa.removeLayer(BASES[S.base]);
  S.base = b.dataset.base;
  BASES[S.base].addTo(mapa);
  BASES[S.base].bringToBack?.();
  document.querySelectorAll('#seg-base button').forEach((x) => x.classList.toggle('on', x === b));
  limitesProyecto.setStyle(estiloProyecto);
  paquetes.setStyle(estiloPaquete);
  restilarAgua();
}));

document.querySelectorAll('.switch input[data-capa]').forEach((el) => el.addEventListener('change', () => {
  const k = el.dataset.capa;
  el.checked ? capas[k].addTo(mapa) : mapa.removeLayer(capas[k]);
  document.getElementById(`capa-${k}`).classList.toggle('off', !el.checked);
}));

document.querySelectorAll('#f-tipo button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#f-tipo button').forEach((x) => x.classList.toggle('on', x === b));
  S.filtro.tipo = b.dataset.v;
  renderRiesgos();
}));

function encuadrar() {
  const puntos = [];
  contornoGuajira.eachLayer((l) => puntos.push(l.getBounds()));
  if (!puntos.length) limitesProyecto.eachLayer((l) => puntos.push(l.getBounds()));
  if (!puntos.length) { mapa.setView([11.3, -72.5], 8); return; }
  const b = puntos.reduce((acc, x) => acc.extend(x), L.latLngBounds(puntos[0].getSouthWest(), puntos[0].getNorthEast()));
  mapa.fitBounds(b, { padding: [50, 50] });
}

// Lecturas en vivo: no bloquean el arranque y se refrescan cada 10 minutos
async function cargarAhora(forzar = false) {
  try {
    S.ahora = await ui.json(`/api/clima/ahora${forzar ? '?forzar=true' : ''}`);
  } catch (e) {
    S.ahora = { origen: 'sin_datos', estaciones: {} };
  }
  renderEstadoVivo();
  renderClima();
  if (S.sel?.tipo === 'estacion') renderDetalle();
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

(async function iniciar() {
  const [proyectos, pq, riesgos, clima, radiacion, red, rios, agua, mpios, limite] = await Promise.all([
    ui.json('/api/capas/proyectos'), ui.json('/api/paquetes'), ui.json('/api/riesgos'), ui.json('/api/clima'), ui.json('/api/clima/radiacion'),
    ui.json('/api/capas/red_vial'), ui.json('/api/capas/rios'), ui.json('/api/capas/cuerpos_agua'),
    ui.json('/api/capas/municipios'), ui.json('/api/capas/limite_departamental'),
  ]);
  S.municipios = mpios;
  S.limite = limite;
  renderMunicipios();
  if (mpios.features.length) renderListaMunicipios();
  document.getElementById('sub-municipios').textContent = mpios.features.length
    ? `${mpios.features.length} municipios · ${Math.round(mpios.metadata.km2).toLocaleString('es-CO')} km²`
    : 'Sin datos: ejecuta la ingesta de municipios (ver README)';
  document.getElementById('fuente-municipios').innerHTML = mpios.features.length
    ? `Fuente: DANE, Marco Geoestadístico Nacional (${mpios.metadata.version_geometria}), descargado el ${ui.fecha(mpios.metadata.descargado_en)}. Los límites pueden diferir de los vigentes.`
    : '';
  S.rios = rios;
  S.agua = agua;
  cuerposAgua.addData(agua);
  riosNombrados.addData({ type: 'FeatureCollection', features: rios.features.filter((f) => f.properties.nombre) });
  riosSinNombre.addData({ type: 'FeatureCollection', features: rios.features.filter((f) => !f.properties.nombre) });
  const nombrados = rios.features.filter((f) => f.properties.nombre).length;
  document.getElementById('sub-rios').textContent = rios.features.length
    ? `${rios.features.length.toLocaleString('es-CO')} tramos (${nombrados.toLocaleString('es-CO')} con nombre) · ${agua.features.length} cuerpos de agua`
    : 'Sin datos: ejecuta la ingesta de hidrografía (ver README)';
  document.getElementById('fuente-rios').innerHTML = rios.features.length
    ? `Fuente: IGAC, cartografía básica 1:100.000 (servicio del <a href="https://dhime.ideam.gov.co/server/rest/services/Cartografia_Basica/Hidrografia/MapServer" target="_blank" rel="noopener">IDEAM</a>), descargada el ${ui.fecha(rios.metadata.descargado_en)}. <b>Uso libre solo sin fines comerciales</b> (Res. 364/2012). Dibuja todo cauce cartografiado: no indica si lleva agua hoy.`
    : '';
  S.red = red;
  renderRedVial();
  if (red.features.length) renderLeyendaRed();
  const mr = red.metadata;
  document.getElementById('sub-vias').textContent = red.features.length
    ? `${red.features.length.toLocaleString('es-CO')} tramos · ${Math.round(mr.km).toLocaleString('es-CO')} km (${Math.round(mr.km_nacional)} nacionales)`
    : 'Sin datos: ejecuta la ingesta de vías (ver README)';
  document.getElementById('fuente-vias').innerHTML = red.features.length
    ? `Fuentes: <b>INVIAS</b>, <a href="https://www.datos.gov.co/d/ie7y-asdn" target="_blank" rel="noopener">Red Vial</a> (CC BY-SA 4.0) y <b>IGAC</b>, cartografía básica 1:100.000 (servicio del <a href="https://dhime.ideam.gov.co/server/rest/services/Cartografia_Basica/Vias/MapServer" target="_blank" rel="noopener">IDEAM</a>; <b>uso libre solo sin fines comerciales</b>). Lo que el IGAC repite de la red nacional se quitó: cada kilómetro cuenta una vez.`
    : '';
  S.paquetes = pq;
  S.riesgos = riesgos.features;
  S.clima = clima;
  S.radiacion = radiacion;

  limitesProyecto.addData(proyectos);
  paquetes.addData(pq);
  document.getElementById('sub-proyectos').textContent = `${proyectos.features.length} proyectos · ${pq.features.length} paquetes de trabajo`;

  const meta = clima.metadata;
  const n = clima.features.length;
  const nvars = meta ? Object.keys(meta.variables || {}).length : 0;
  document.getElementById('sub-clima').textContent = n
    ? `${n} estaciones · ${nvars} variables · datos hasta el ${ui.fecha(meta.hasta + 'T12:00:00')}`
    : 'Sin datos: ejecuta la ingesta del IDEAM (ver README)';
  document.getElementById('fuente-clima').innerHTML = n
    ? `Fuente: IDEAM, <a href="https://www.datos.gov.co/d/s54a-sgyg" target="_blank" rel="noopener">datos abiertos</a> (CC BY-SA 4.0). Serie de 30 días descargada el ${ui.fecha(meta.descargado_en)}; las lecturas recientes se consultan en vivo. Borde punteado: cobertura menor a 50 %; "s/d": sin datos suficientes.`
    : '';

  // solo arrancan encendidas las capas cuyo interruptor viene marcado en el HTML (municipios y proyectos)
  Object.entries(capas).forEach(([k, c]) => { if (document.querySelector(`input[data-capa="${k}"]`)?.checked) c.addTo(mapa); });
  renderFiltroCategorias();
  renderRiesgos();
  renderTarjetasClima();
  renderClima();
  renderEstadoVivo();
  encuadrar();
  ui.icons();

  cargarAhora();
  setInterval(() => cargarAhora(), 10 * 60 * 1000);
})();
