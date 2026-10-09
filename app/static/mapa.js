/* Mapa simple: proyectos, riesgos y clima real (IDEAM) sobre satelite o mapa de calles, sin claves. */

const S = {
  base: 'satelite',
  activas: new Set(),    // variables de clima encendidas (cada una es una capa); al inicio, ninguna
  red: null,             // red vial unificada (INVIAS + IGAC)
  clasesOcultas: new Set(),   // estilos de via que el usuario apago
  cobertura: null,       // areas de las estaciones (cercana / radio) por variable
  coberturaPaq: null,    // que estacion representa a cada paquete
  cobVar: 'lluvia',
  tiempo: { modo: 'diario', iDia: null, iMes: null, jugando: null },   // controlador de tiempo
  chirps: null,          // lluvia mensual CHIRPS por municipio
  chirpsModo: 'mm',      // mm del mes | anomalia frente a la normal
  cobModo: 'cercana',
  social: null,          // indicadores por municipio: censo 2018, agua, territorio, delitos por mes, emergencias
  socialInd: 'ipm',      // indicador que pinta la capa social
  resguardos: null,      // resguardos indigenas (ANT)
  areasRunap: null,      // areas protegidas (RUNAP)
  contexto: null,        // contexto real de cada paquete
  chart2: null,          // segundo grafico de la ficha (delitos por mes)
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
  colorPaquete: 'ict',   // color de los paquetes: ict | ejecucion | ninguno
  ejec: null,            // riesgo de ejecucion por paquete (IRE), se pide al elegir ese color
  calor: null,           // superficie de calor (grilla) de amenazas y oportunidades
  calorModo: 'ict',      // ict (criticidad por celda) | amenazas | oportunidades
  crisis: null,          // puntos donde un riesgo puede escalar a crisis
  zonas: null,           // zonas de intervencion prioritaria
  alertas: [],           // alertas tempranas (Oro)
  alertasEstado: null,   // tarea diaria: novedades del corte, proxima ejecucion y canales de aviso
  umbrales: { bajo: 25, medio: 50, alto: 75 },
  paramsIct: null,       // parametros del modelo (criterios, grilla, kde)
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
mapa.createPane('chirps').style.zIndex = 398;         // lluvia CHIRPS por municipio: relleno de fondo
mapa.getPane('chirps').style.pointerEvents = 'none';
mapa.createPane('social').style.zIndex = 397;         // indicadores sociales por municipio: relleno de fondo
mapa.getPane('social').style.pointerEvents = 'none';
mapa.createPane('territorios').style.zIndex = 404;    // resguardos y areas protegidas: encima de los limites, reciben clic
mapa.createPane('cobertura').style.zIndex = 399;      // debajo de los limites municipales: es un relleno de fondo
mapa.getPane('cobertura').style.pointerEvents = 'none';
mapa.createPane('agua').style.zIndex = 401;
mapa.createPane('rios').style.zIndex = 402;
mapa.createPane('vias').style.zIndex = 407;
mapa.createPane('paquetes').style.zIndex = 410;
mapa.createPane('riesgosPane').style.zIndex = 420;
mapa.createPane('fichasLineas').style.zIndex = 599;   // lineas y puntos de las fichas: debajo de las fichas (markerPane = 600)
mapa.createPane('calor').style.zIndex = 406;          // superficie de calor: encima de los territorios, debajo de los paquetes
mapa.getPane('calor').style.pointerEvents = 'none';
mapa.createPane('zonas').style.zIndex = 408;          // zonas de intervencion: contorno, sin bloquear clics
mapa.getPane('zonas').style.pointerEvents = 'none';
mapa.createPane('crisisPane').style.zIndex = 590;     // puntos de crisis: encima de los riesgos, debajo de las fichas

const capas = {
  social: L.layerGroup(),
  resguardos: L.layerGroup(),
  areas: L.layerGroup(),
  chirps: L.layerGroup(),
  cobertura: L.layerGroup(),
  municipios: L.layerGroup(),
  proyectos: L.layerGroup(),
  rios: L.layerGroup(),
  vias: L.layerGroup(),
  riesgos: L.layerGroup(),
  crisis: L.layerGroup(),
  calor: L.layerGroup(),
};
const gClima = {};   // una capa de Leaflet por variable de clima (se crean en renderTarjetasClima)
const limitesProyecto = L.geoJSON(null, { pane: 'proyectos', interactive: false, style: estiloProyecto });
const paquetes = L.geoJSON(null, { pane: 'paquetes', style: estiloPaquete, onEachFeature: eventosPaquete });
capas.proyectos.addLayer(limitesProyecto).addLayer(paquetes);

function estiloProyecto() {
  const claro = S.base === 'calles';
  return { color: claro ? ui.css('--ink-2') : '#ffffff', weight: 1.5, dashArray: '6 6', fill: false, opacity: claro ? 0.8 : 0.9 };
}
const nivelIre = (v) => (v >= 75 ? 'critico' : v >= 50 ? 'alto' : v >= 25 ? 'medio' : 'bajo');
// Nivel con el que se pinta un paquete: el de su ICT, el de su riesgo de ejecucion (IRE) o ninguno
function nivelPaquete(p) {
  if (S.colorPaquete === 'ict') return p.nivel || null;
  if (S.colorPaquete === 'ejecucion') { const e = S.ejec?.[p.id_paquete]; return e ? nivelIre(e.ire) : null; }
  return null;
}
function valorPaquete(p) {
  if (S.colorPaquete === 'ict') return p.ICT;
  if (S.colorPaquete === 'ejecucion') return S.ejec?.[p.id_paquete]?.ire;
  return null;
}
function estiloPaquete(f) {
  const sel = S.sel?.tipo === 'paquete' && S.sel.id === f.properties.id_paquete;
  const nivel = nivelPaquete(f.properties);
  const claro = S.base === 'calles';
  if (!nivel) {
    return { color: claro ? ui.css('--green-700') : '#ffffff', weight: sel ? 3.5 : 2, fillColor: ui.css('--green-500'), fillOpacity: sel ? 0.4 : 0.22 };
  }
  const c = ui.css(`--lvl-${nivel}`);
  return { color: claro ? c : '#ffffff', weight: sel ? 3.5 : 1.8, fillColor: c, fillOpacity: sel ? 0.85 : 0.62 };
}
function tagPaquete(p) {
  const v = valorPaquete(p);
  return v == null ? ui.tagCorto(p.nombre) : `${ui.tagCorto(p.nombre)} · <b>${Math.round(v)}</b>`;
}
function eventosPaquete(f, layer) {
  layer.bindTooltip(tagPaquete(f.properties), { permanent: true, direction: 'center', className: 'map-tag tag-paquete' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('paquete', f.properties.id_paquete); });
}
// De lejos, una etiqueta por proyecto (con su peor paquete); de cerca, una por paquete
function tagProyecto(f) {
  const propios = (S.paquetes?.features || []).map((x) => x.properties).filter((x) => x.id_proyecto === f.properties.id_proyecto);
  const vals = propios.map(valorPaquete).filter((v) => v != null);
  const nombre = `Proyecto ${Number(String(f.properties.id_proyecto).split('-')[1])}`;
  if (!vals.length) return nombre;
  return `${nombre} · ${S.colorPaquete === 'ict' ? 'ICT' : 'IRE'} máx. <b>${Math.round(Math.max(...vals))}</b>`;
}
function etiquetarProyectos() {
  limitesProyecto.eachLayer((l) => {
    if (l.getTooltip()) l.setTooltipContent(tagProyecto(l.feature));
    else l.bindTooltip(tagProyecto(l.feature), { permanent: true, direction: 'center', className: 'map-tag tag-proyecto' });
  });
  paquetes.eachLayer((l) => l.setTooltipContent(tagPaquete(l.feature.properties)));
}
function etiquetasPorZoom() {
  document.getElementById('mapa').classList.toggle('tags-cerca', mapa.getZoom() >= 10.5);
}
mapa.on('zoomend', etiquetasPorZoom);

function renderLeyendaPaquetes() {
  const el = document.getElementById('leyenda-paquetes');
  const nota = document.getElementById('nota-paquetes');
  document.querySelectorAll('#f-color-paquete button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.colorPaquete));
  if (S.colorPaquete === 'ninguno') {
    el.innerHTML = '<div class="leyenda-fila"><span class="lg-circ"></span> Paquete de trabajo</div>';
    nota.textContent = '';
    return;
  }
  const u = S.colorPaquete === 'ict' ? S.umbrales : { bajo: 25, medio: 50, alto: 75 };
  const tramos = [['bajo', 0, u.bajo], ['medio', u.bajo, u.medio], ['alto', u.medio, u.alto], ['critico', u.alto, 100]];
  el.innerHTML = tramos.map(([n, a, b]) => `<span class="lvl-ley"><span class="sw" style="background:var(--lvl-${n})"></span>${ui.NIVEL[n]}<small>${a}-${b}</small></span>`).join('');
  nota.innerHTML = S.colorPaquete === 'ict'
    ? 'ICT de 0 a 100: severidad de los riesgos (RAM), exposición del paquete, vulnerabilidad y amenazas del territorio real, y convergencia. Clic en un paquete para ver por qué.'
    : 'IRE de 0 a 100: probabilidad de que el atraso del paquete pase su holgura más la tolerancia (Monte Carlo sobre la RAM y el territorio). Detalle en <a href="ejecucion.html">Riesgo de ejecución</a>.';
}

async function cambiarColorPaquete(modo) {
  if (modo === 'ejecucion' && !S.ejec) {
    try {
      const d = await ui.json('/api/ejecucion');
      S.ejec = d.disponible ? Object.fromEntries(d.paquetes.map((x) => [x.id_paquete, x])) : {};
    } catch (e) { S.ejec = {}; }
  }
  S.colorPaquete = modo;
  paquetes.setStyle(estiloPaquete);
  etiquetarProyectos();
  renderLeyendaPaquetes();
  if (S.sel?.tipo === 'paquete') renderDetalle();
}
document.querySelectorAll('#f-color-paquete button').forEach((b) => b.addEventListener('click', () => cambiarColorPaquete(b.dataset.v)));

// ---------------------------------------------------------------------------
// Mapa de calor: densidad (kernel) de las amenazas o de las oportunidades, y puntos calientes (Gi*)
// ---------------------------------------------------------------------------

const CALOR = {
  amenazas: { campo: 'intensidad', rampa: ['#fee8c8', '#fdbb84', '#fc8d59', '#e34a33', '#b30000'] },
  oportunidades: { campo: 'intensidad_oportunidades', rampa: ['#e0f3db', '#a8ddb5', '#7bccc4', '#43a2ca', '#0868ac'] },
};
const CORTES_CALOR = [0.05, 0.15, 0.3, 0.5, 0.75];
const ETIQUETAS_CALOR = ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta'];

function renderCalor() {
  capas.calor.clearLayers();
  if (!S.calor?.features?.length) {
    document.getElementById('sub-calor').textContent = 'Sin datos: corre el pipeline (ver README)';
    return;
  }
  const h = (S.paramsIct?.grid?.resolucion_grados || 0.02) / 2;
  let n = 0;
  if (S.calorModo === 'ict') {
    const opac = { bajo: 0.22, medio: 0.34, alto: 0.5, critico: 0.62 };
    S.calor.features.forEach((f) => {
      const nivel = f.properties.nivel;
      if (!nivel) return;
      const [lon, lat] = f.geometry.coordinates;
      L.rectangle([[lat - h, lon - h], [lat + h, lon + h]], {
        pane: 'calor', interactive: false, stroke: false, fillColor: ui.css(`--lvl-${nivel}`), fillOpacity: opac[nivel] || 0.3,
      }).addTo(capas.calor);
      n += 1;
    });
    document.querySelectorAll('#f-calor button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.calorModo));
    const u = S.umbrales;
    document.getElementById('rampa-calor').innerHTML = [['bajo', `menos de ${u.bajo}`], ['medio', `${u.bajo} a ${u.medio}`], ['alto', `${u.medio} a ${u.alto}`], ['critico', `${u.alto} o más`]]
      .map(([k, txt]) => `<div class="fila"><span class="sw" style="background:var(--lvl-${k})"></span><span>${ui.NIVEL[k]} · ICT ${txt}</span></div>`).join('');
    const max = Math.max(...S.calor.features.map((f) => f.properties.ict || 0));
    document.getElementById('sub-calor').textContent = `${n} celdas de ~2 km · ICT máximo ${Math.round(max)}`;
    document.getElementById('nota-calor').textContent = 'El ICT calculado en cada celda alrededor de los proyectos con los mismos criterios y pesos: las amenazas del registro que la alcanzan y el territorio real de la celda (resguardos, pobreza, áreas protegidas, vías, lluvia, emergencias, delitos). En una celda no hay ruta crítica: esa parte es del paquete.';
    return;
  }
  const cfg = CALOR[S.calorModo];
  S.calor.features.forEach((f) => {
    const v = f.properties[cfg.campo];
    if (!(v >= CORTES_CALOR[0])) return;
    const k = CORTES_CALOR.filter((c) => v >= c).length - 1;
    const [lon, lat] = f.geometry.coordinates;
    const caliente = S.calorModo === 'amenazas' && f.properties.punto_caliente;
    L.rectangle([[lat - h, lon - h], [lat + h, lon + h]], {
      pane: 'calor', interactive: false, stroke: caliente, color: '#ffffff', weight: 1.4, dashArray: '3 3', opacity: 0.95,
      fillColor: cfg.rampa[k], fillOpacity: 0.24 + 0.08 * k,
    }).addTo(capas.calor);
    n += 1;
  });
  const calientes = S.calor.features.filter((f) => f.properties.punto_caliente).length;
  document.querySelectorAll('#f-calor button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.calorModo));
  document.getElementById('rampa-calor').innerHTML = cfg.rampa.map((col, i) => `<div class="fila"><span class="sw" style="background:${col}"></span><span>Densidad ${ETIQUETAS_CALOR[i].toLowerCase()}</span></div>`).join('')
    + (S.calorModo === 'amenazas' ? '<div class="fila"><span class="sw lg-caliente"></span><span>Punto caliente significativo (Gi*, 95 %)</span></div>' : '');
  document.getElementById('sub-calor').textContent = `${n} celdas de ~2 km · ${calientes} puntos calientes`;
  document.getElementById('nota-calor').textContent = S.calorModo === 'amenazas'
    ? `Densidad (kernel gaussiano, banda de ${((S.paramsIct?.kde?.bandwidth_m || 4000) / 1000).toLocaleString('es-CO')} km) de las amenazas del registro, ponderada por su nivel RAM y su estado. Los puntos calientes son conglomerados que el estadístico Getis-Ord Gi* distingue del azar.`
    : 'Densidad de las oportunidades abiertas del registro, ponderada por el nivel RAM de su beneficio. Se muestra aparte: no se resta de las amenazas.';
}
document.querySelectorAll('#f-calor button').forEach((b) => b.addEventListener('click', () => { S.calorModo = b.dataset.v; renderCalor(); }));

// ---------------------------------------------------------------------------
// Escalamiento a crisis: puntos donde un riesgo puede escalar y zonas de intervencion prioritaria
// ---------------------------------------------------------------------------

const zonasCapa = L.geoJSON(null, {
  pane: 'zonas', interactive: false,
  style: (f) => {
    const c = ui.css(f.properties.prioridad === 'critica' ? '--lvl-critico' : '--lvl-alto');
    return { color: c, weight: 2, dashArray: '7 5', opacity: 0.95, fillColor: c, fillOpacity: 0.07 };
  },
});
const puntosCrisis = L.layerGroup();
capas.crisis.addLayer(zonasCapa).addLayer(puntosCrisis);
const PRIORIDAD = { critica: 'crítica', alta: 'alta', media: 'media' };

function renderCrisis() {
  zonasCapa.clearLayers();
  puntosCrisis.clearLayers();
  if (!S.crisis?.features?.length) {
    document.getElementById('sub-crisis').textContent = S.crisis ? 'Ningún paquete en escalamiento hoy' : 'Sin datos: corre el pipeline (ver README)';
    return;
  }
  if (S.zonas?.features?.length) zonasCapa.addData(S.zonas);
  S.crisis.features.forEach((f) => {
    const p = f.properties;
    const [lon, lat] = f.geometry.coordinates;
    const icono = L.divIcon({ className: 'pc-wrap', html: `<span class="pc ${p.prioridad}${p.tipo === 'paquete' ? ' paquete' : ''}"></span>`, iconSize: [18, 18], iconAnchor: [9, 9] });
    const titulo = p.tipo === 'riesgo' ? `${p.id_riesgo} · RAM ${p.ram}` : ui.nombreCorto(p.nombre_paquete);
    L.marker([lat, lon], { icon: icono, pane: 'crisisPane', keyboard: false, riseOnHover: true })
      .bindTooltip(`<b>${titulo}</b> · prioridad ${PRIORIDAD[p.prioridad]}<br><span class="sub">${String(p.causas).split('; ')[0]}</span>`, { className: 'map-tip', direction: 'top', offset: [0, -8] })
      .on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('crisis', p.id_punto); })
      .addTo(puntosCrisis);
  });
  const nPaq = new Set(S.crisis.features.map((f) => f.properties.id_paquete)).size;
  const criticos = S.crisis.features.filter((f) => f.properties.prioridad === 'critica').length;
  document.getElementById('sub-crisis').textContent = `${S.crisis.features.length} puntos (${criticos} críticos) en ${nPaq} paquetes · ${S.zonas?.features?.length || 0} zonas de intervención`;
  document.getElementById('nota-crisis').textContent = 'Reglas de parametros.yaml: ICT crítico; riesgo RAM muy alto (VH), o alto (H) en ruta crítica; riesgo alto cuya área de influencia alcanza un resguardo o un área protegida (reales); convergencia de amenazas o acciones vencidas con ICT alto. La zona es el área de influencia de cada punto.';
}

function renderBotonAlertas() {
  const b = document.getElementById('n-alertas');
  b.hidden = !S.alertas.length;
  b.textContent = S.alertas.length;
  b.classList.toggle('critica', S.alertas.some((a) => a.prioridad === 'critica'));
}

function irAPaquete(id) {
  let capa = null;
  paquetes.eachLayer((l) => { if (l.feature.properties.id_paquete === id) capa = l; });
  if (capa) mapa.flyToBounds(capa.getBounds(), { maxZoom: 12.5, padding: [80, 80], duration: 0.8 });
  seleccionar('paquete', id);
}

// ---------------------------------------------------------------------------
// Cobertura de estaciones: cada estacion extendida a un area (mas cercana o radio de influencia), pintada con el valor
// de la variable. Sirve para ver el clima sobre un territorio y no solo en un punto.
// ---------------------------------------------------------------------------

const coberturaAreas = L.geoJSON(null, { pane: 'cobertura', interactive: false, style: estiloCobertura });
const coberturaPuntos = L.layerGroup();
capas.cobertura.addLayer(coberturaAreas).addLayer(coberturaPuntos);

// Valor de la variable en una estacion, con la misma regla que las pastillas (lluvia: acumulado de la ventana elegida)
function valorEstacion(codigo, v) {
  const p = estacion(codigo);
  if (!p) return null;
  if (v === 'lluvia') return fechaDia() ? lluviaHasta(p, fechaDia(), DIAS[S.ventana]).mm : p[S.ventana];
  return lecturaActual(p, VISTAS[v].var)?.valor ?? null;
}

function estiloCobertura(f) {
  const v = S.cobVar;
  const valor = valorEstacion(f.properties.codigo, v);
  const radio = f.properties.modo === 'radio';
  return {
    fillColor: valor == null ? '#8a928d' : colorDe(v, valor), fillOpacity: radio ? 0.38 : 0.5,
    color: '#ffffff', weight: radio ? 1.4 : 1, opacity: 0.85, dashArray: radio ? '5 4' : null,
  };
}

function variablesConCobertura() {
  const vs = new Set((S.cobertura?.features || []).map((f) => f.properties.variable));
  return Object.keys(VISTAS).filter((k) => vs.has(k));
}

function renderCobertura() {
  coberturaAreas.clearLayers();
  coberturaPuntos.clearLayers();
  if (!S.cobertura) return;
  const feats = S.cobertura.features.filter((f) => f.properties.variable === S.cobVar && f.properties.modo === S.cobModo);
  coberturaAreas.addData({ type: 'FeatureCollection', features: feats });
  // la estacion de cada area, para saber de donde sale el color
  feats.forEach((f) => {
    const e = estacion(f.properties.codigo);
    if (!e) return;
    const est = S.clima.features.find((x) => x.properties.codigo === f.properties.codigo);
    L.circleMarker([est.geometry.coordinates[1], est.geometry.coordinates[0]], {
      pane: 'cobertura', interactive: false, radius: 3.5, color: '#ffffff', weight: 1.5, fillColor: '#16201b', fillOpacity: 1,
    }).addTo(coberturaPuntos);
  });
  const cfg = VISTAS[S.cobVar];
  const meta = S.cobertura.metadata;
  const r = meta.radios_km[S.cobVar];
  const hay = feats.length;
  document.getElementById('sub-cobertura').textContent = `${cfg.titulo} · ${hay ? `${meta.estaciones_por_variable[S.cobVar]} estaciones` : 'sin estaciones'}`;
  document.getElementById('rampa-cob').innerHTML = htmlRampa(S.cobVar);
  document.getElementById('nota-cob').innerHTML = S.cobModo === 'cercana'
    ? `Cada punto del departamento se pinta con el valor de su estación más cercana (${cfg.titulo.toLowerCase()}). <b>No dice qué tan bueno es el dato lejos de la estación:</b> mira el radio de influencia para eso.${hay ? '' : ' Esta variable tiene una sola estación: no hay reparto que hacer.'}`
    : `Círculo de <b>${r} km</b> alrededor de cada estación. Es un <b>supuesto de trabajo</b> (regla práctica, no una cifra oficial del IDEAM); se ajusta en <span class="mono">parametros.yaml</span>. Lo que queda fuera de los círculos no tiene cobertura.`;
}

function htmlRampa(v) {
  const cfg = VISTAS[v];
  if (cfg.unico) return `<p class="fuente">Sin escala de color: el valor de ${cfg.titulo.toLowerCase()} depende ${v === 'presion' ? 'de la altitud' : 'del cauce'}. Se pinta de un solo color.</p>`;
  const c = cortesDe(v);
  const et = [`< ${c[0]}`, `${c[0]} – ${c[1]}`, `${c[1]} – ${c[2]}`, `${c[2]} – ${c[3]}`, `≥ ${c[3]}`];
  return cfg.rampa.map((col, i) => `<div class="fila"><span class="sw" style="background:${col}"></span><span>${et[i]} ${cfg.unidad}</span></div>`).join('');
}

function renderControlesCobertura() {
  const vars = variablesConCobertura();
  if (!vars.includes(S.cobVar)) S.cobVar = vars[0] || 'lluvia';
  const cont = document.getElementById('f-cob-var');
  cont.innerHTML = vars.map((k) => `<button class="chip${S.cobVar === k ? ' on' : ''}" data-v="${k}"><i data-lucide="${VISTAS[k].icono}"></i>${VISTAS[k].titulo}</button>`).join('');
  cont.querySelectorAll('.chip').forEach((b) => b.addEventListener('click', () => {
    S.cobVar = b.dataset.v;
    renderControlesCobertura();
    renderCobertura();
  }));
  ui.icons();
}

document.querySelectorAll('#f-cob-modo button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#f-cob-modo button').forEach((x) => x.classList.toggle('on', x === b));
  S.cobModo = b.dataset.v;
  renderCobertura();
}));

// Clima que representa a un paquete: la estacion mas cercana por variable, a cuantos km y si queda cubierto
const ESTADO_COB = { cubierto: ['ok', 'Cubierto'], parcial: ['warn', 'Parcial'], sin_cobertura: ['white', 'Sin cobertura'] };
function climaDelPaquete(idPaquete) {
  const filas = S.coberturaPaq?.paquetes?.[idPaquete];
  if (!filas?.length) return '';
  const orden = Object.keys(VISTAS);
  const html = [...filas].sort((a, b) => orden.indexOf(a.variable) - orden.indexOf(b.variable)).map((f) => {
    const cfg = VISTAS[f.variable];
    const [clase, rotulo] = ESTADO_COB[f.estado];
    const valor = valorEstacion(f.codigo, f.variable);
    return `<div class="fila">
      <span class="t">${cfg.titulo} · ${valor == null ? '-' : `${formato(valor, cfg.dec)} ${cfg.unidad}`}</span><span class="chip ${clase}">${rotulo}</span>
      <span class="s">${f.estacion} · a ${f.distancia_km} km (radio ${f.radio_km} km)</span></div>`;
  }).join('');
  return `<div class="sec-ctx">Clima que representa a este paquete</div><div class="clima-paq">${html}</div>
    <div class="det-foot">Estación más cercana por variable, medida desde el centro del paquete. "Cubierto": dentro del radio de influencia; "parcial": hasta el doble; "sin cobertura": más lejos. Los radios son supuestos de trabajo.</div>`;
}

// ---------------------------------------------------------------------------
// Lluvia CHIRPS por municipio: cada municipio pintado con la lluvia del mes elegido (o su anomalia frente a la normal)
// ---------------------------------------------------------------------------

const RAMPA_CHIRPS = {
  mm: { cortes: [10, 50, 100, 200], rampa: ['#eef6fd', '#a9d3f3', '#5aa7e6', '#1f6fd0', '#12409b'], unidad: 'mm', oscuras: 2 },
  anomalia: { cortes: [-60, -20, 20, 60], rampa: ['#a6611a', '#dfc27d', '#f2f2f2', '#80cdc1', '#018571'], unidad: '%', oscuras: 4 },
};
const chirpsCapa = L.geoJSON(null, { pane: 'chirps', interactive: false, style: estiloChirps });
capas.chirps.addLayer(chirpsCapa);

// Indice del mes a mostrar; si el mes elegido aun no esta publicado (CHIRPS sale ~3 semanas despues), el ultimo publicado
function indiceMesChirps() {
  const meses = mesesChirps();
  const i = meses.indexOf(mesReferencia());
  return { i: i >= 0 ? i : meses.length - 1, exacto: i >= 0 };
}
function valorChirps(codigo) {
  const z = S.chirps?.municipios?.[codigo];
  if (!z) return null;
  const { i } = indiceMesChirps();
  return S.chirpsModo === 'mm' ? z.mm[i] : z.anomalia_pct[i];
}
function estiloChirps(f) {
  const v = valorChirps(f.properties.codigo);
  const r = RAMPA_CHIRPS[S.chirpsModo];
  const k = v == null ? -1 : r.cortes.filter((c) => v >= c).length;
  return { fillColor: v == null ? '#8a928d' : r.rampa[k], fillOpacity: 0.66, color: '#ffffff', weight: 0.8, opacity: 0.6 };
}
function renderChirps() {
  chirpsCapa.clearLayers();
  if (!S.chirps || !S.municipios) return;
  chirpsCapa.addData({ type: 'FeatureCollection', features: municipiosVisibles() });
  const r = RAMPA_CHIRPS[S.chirpsModo];
  const c = r.cortes;
  const et = S.chirpsModo === 'mm'
    ? [`< ${c[0]} mm`, `${c[0]} – ${c[1]} mm`, `${c[1]} – ${c[2]} mm`, `${c[2]} – ${c[3]} mm`, `≥ ${c[3]} mm`]
    : ['Mucho más seco (< −60 %)', 'Más seco (−60 a −20 %)', 'Normal (±20 %)', 'Más lluvioso (+20 a +60 %)', 'Mucho más lluvioso (> +60 %)'];
  document.getElementById('rampa-chirps').innerHTML = r.rampa.map((col, i) => `<div class="fila"><span class="sw" style="background:${col}"></span><span>${et[i]}</span></div>`).join('');
  const { i, exacto } = indiceMesChirps();
  const m = S.chirps.metadata;
  const dep = S.chirps.departamento;
  document.getElementById('sub-chirps').textContent = `${etiquetaMes(mesesChirps()[i])}${exacto ? '' : ' (último publicado)'} · La Guajira ${dep?.mm[i] != null ? formato(dep.mm[i], 0) + ' mm' : '-'}`;
  document.getElementById('nota-chirps').innerHTML = `${S.chirpsModo === 'mm' ? 'Lluvia del mes' : `Cuánto se apartó el mes de su <b>normal ${m.normal}</b> (el promedio de ese mes en esos 30 años)`}, promedio de las celdas de ~5 km que cubren cada municipio. `
    + `Fuente: <a href="https://doi.org/10.15780/G2JQ0P" target="_blank" rel="noopener">CHIRPS v3</a> (Climate Hazards Center, UCSB; satélite + estaciones), CC BY 4.0. `
    + `${m.desde.slice(0, 4)}–${m.hasta.slice(0, 4)}; cada mes se publica unas 3 semanas después de terminar${exacto ? '' : '. <b>El mes elegido aún no está publicado</b>: se muestra el último'}.`;
}
document.querySelectorAll('#f-chirps-modo button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#f-chirps-modo button').forEach((x) => x.classList.toggle('on', x === b));
  S.chirpsModo = b.dataset.v;
  renderChirps();
}));
// al encender la capa, el tiempo pasa a meses (es la escala de CHIRPS)
document.querySelector('input[data-capa="chirps"]').addEventListener('change', (e) => {
  if (e.target.checked && S.tiempo.modo !== 'mensual') cambiarModoTiempo('mensual');
});

function lluviaDelMunicipio(codigo) {
  const z = S.chirps?.municipios?.[codigo];
  if (!z) return '';
  const { i } = indiceMesChirps();
  const mes = mesesChirps()[i];
  const normal = z.normal[Number(mes.slice(5, 7)) - 1];
  const a = z.anomalia_pct[i];
  return `<div class="sec-ctx">Lluvia por satélite (CHIRPS)</div>
    <div class="kv"><span class="k">${etiquetaMes(mes)}</span><span class="v">${formato(z.mm[i], 1)} mm${a != null ? ` · ${a > 0 ? '+' : ''}${a} % frente a lo normal (${formato(normal, 0)} mm)` : ''}</span></div>
    <div class="kv"><span class="k">Lluvia normal en un año (${S.chirps.metadata.normal})</span><span class="v">${z.normal_anual != null ? z.normal_anual.toLocaleString('es-CO') + ' mm' : '-'}</span></div>
    <div class="det-serie-t">Lluvia de cada mes · la línea es lo normal de ese mes</div>
    <div class="chart-mini"><canvas id="chart-serie"></canvas></div>`;
}

function dibujarChirps(codigo) {
  const z = S.chirps.municipios[codigo];
  const meses = mesesChirps();
  const { i: sel } = indiceMesChirps();
  const normal = meses.map((m) => z.normal[Number(m.slice(5, 7)) - 1]);
  S.chart = new Chart(document.getElementById('chart-serie'), {
    data: {
      labels: meses,
      datasets: [
        { type: 'bar', label: 'Lluvia', data: z.mm, backgroundColor: meses.map((_, k) => (k === sel ? '#12409b' : 'rgba(31,111,208,.45)')), barPercentage: 1, categoryPercentage: 1 },
        { type: 'line', label: 'Normal', data: normal, borderColor: '#a6611a', borderWidth: 1.2, pointRadius: 0, tension: 0.3 },
      ],
    },
    options: { ...OPC_BASE(), scales: { ...OPC_BASE().scales, y: { ...OPC_BASE().scales.y, beginAtZero: true } },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (it) => etiquetaMes(it[0].label), label: (c) => `${c.dataset.label}: ${formato(c.raw, 1)} mm` } } },
      onClick: (_, els) => { if (els.length) { S.tiempo.modo = 'mensual'; S.tiempo.iMes = mesesTiempo().indexOf(meses[els[0].index]); alCambiarTiempo(); } } },
  });
}

// ---------------------------------------------------------------------------
// Indicadores sociales por municipio (censo 2018, agua, territorio, delitos, emergencias): un relleno por municipio
// ---------------------------------------------------------------------------

const RAMPAS_SOCIAL = {
  naranja: ['#fef3e2', '#fdd49e', '#fc8d59', '#d7301f', '#7f0000'],
  morado: ['#f5f0ff', '#d9c8fb', '#a78bfa', '#7c3aed', '#4c1d95'],
  verde: ['#f0fbf3', '#c3ebcf', '#74c98e', '#2e9a55', '#14532d'],
};
const RAMPA_DE = { pct_indigena: 'morado', pct_resguardo: 'morado', pct_area_protegida: 'verde' };
const socialCapa = L.geoJSON(null, { pane: 'social', interactive: false, style: estiloSocial });
capas.social.addLayer(socialCapa);

const indicadorSocial = () => S.social?.indicadores.find((i) => i.id === S.socialInd) || S.social?.indicadores[0];
const zonaSocial = (codigo) => (codigo === '44' ? S.social?.departamento : S.social?.municipios?.[codigo]);
const mesesSocial = () => S.social?.metadata?.meses || [];
// Meses del controlador de tiempo: los de CHIRPS y los de los delitos
const mesesTiempo = () => [...new Set([...mesesChirps(), ...mesesSocial()])].sort();

// Mes de los delitos a mostrar: el elegido o, si aun no esta publicado, el ultimo
function indiceMesSocial() {
  const meses = mesesSocial();
  const ref = mesReferencia();
  const i = meses.indexOf(ref);
  if (i >= 0) return { i, exacto: true };
  return { i: ref && ref < meses[0] ? 0 : meses.length - 1, exacto: false };
}
// Victimas de un delito en los 12 meses que terminan en el mes elegido, por 100.000 habitantes (censo 2018)
function tasa12m(z, delito) {
  const serie = z?.seguridad?.serie?.[delito];
  const pob = z?.censo?.poblacion_2018;
  if (!serie || !pob) return null;
  const { i } = indiceMesSocial();
  const n = serie.slice(Math.max(0, i - 11), i + 1).reduce((a, b) => a + b, 0);
  return { n, tasa: (n / pob) * 1e5 };
}
function valorSocial(codigo, ind = indicadorSocial()) {
  const z = zonaSocial(codigo);
  if (!z || !ind) return null;
  if (ind.valor.startsWith('tasa:')) return tasa12m(z, ind.valor.slice(5))?.tasa ?? null;
  return ind.valor.split('.').reduce((o, k) => (o == null ? null : o[k]), z) ?? null;
}
const sufijoSocial = (ind) => (ind.unidad.startsWith('%') ? ' %' : '');
function textoSocial(v, ind) {
  if (v == null) return 'sin dato';
  return `${formato(v, ind.unidad.startsWith('%') || ind.valor.startsWith('tasa:') ? 1 : 0)}${sufijoSocial(ind)}`;
}
function estiloSocial(f) {
  const ind = indicadorSocial();
  const v = valorSocial(f.properties.codigo, ind);
  const rampa = RAMPAS_SOCIAL[RAMPA_DE[ind?.id] || 'naranja'];
  const k = v == null ? -1 : ind.cortes.filter((c) => v >= c).length;
  return { fillColor: v == null ? '#8a928d' : rampa[k], fillOpacity: 0.68, color: '#ffffff', weight: 0.8, opacity: 0.6 };
}

function renderOpcionesSocial() {
  const sel = document.getElementById('f-social');
  const grupos = {};
  S.social.indicadores.forEach((i) => { (grupos[i.grupo] ||= []).push(i); });
  sel.innerHTML = Object.entries(grupos).map(([g, inds]) => `<optgroup label="${g}">${inds.map((i) => `<option value="${i.id}"${i.id === S.socialInd ? ' selected' : ''}>${i.nombre}</option>`).join('')}</optgroup>`).join('');
  sel.addEventListener('change', () => {
    S.socialInd = sel.value;
    if (indicadorSocial().temporal && S.tiempo.modo !== 'mensual') cambiarModoTiempo('mensual');
    else renderSocial();
  });
}

function renderSocial() {
  socialCapa.clearLayers();
  if (!S.social || !S.municipios) return;
  socialCapa.addData({ type: 'FeatureCollection', features: municipiosVisibles() });
  const ind = indicadorSocial();
  const c = ind.cortes, u = sufijoSocial(ind);
  const et = [`< ${c[0]}${u}`, `${c[0]} – ${c[1]}${u}`, `${c[1]} – ${c[2]}${u}`, `${c[2]} – ${c[3]}${u}`, `≥ ${c[3]}${u}`];
  const rampa = RAMPAS_SOCIAL[RAMPA_DE[ind.id] || 'naranja'];
  document.getElementById('rampa-social').innerHTML = rampa.map((col, i) => `<div class="fila"><span class="sw" style="background:${col}"></span><span>${et[i]}</span></div>`).join('')
    + '<div class="fila"><span class="sw" style="background:#8a928d"></span><span>Sin dato</span></div>';
  let cuando = ind.fuente;
  if (ind.temporal) {
    const { i, exacto } = indiceMesSocial();
    cuando = `12 meses hasta ${etiquetaMes(mesesSocial()[i])}${exacto ? '' : ' (último publicado)'}`;
  }
  document.getElementById('sub-social').textContent = `${ind.nombre} · ${cuando} · La Guajira ${textoSocial(valorSocial('44', ind), ind)}`;
  const m = S.social.metadata;
  document.getElementById('nota-social').innerHTML = `<b>${ind.nombre}</b> (${ind.unidad}). ${ind.descripcion} Fuente: ${ind.fuente}.`
    + (ind.temporal ? ` Cambia con el controlador de tiempo (escala Meses). ${m.poblacion_base}` : '')
    + ` Haz clic en un municipio para ver todos sus indicadores.`;
}

// Fichas: indicadores del municipio
function socialDelMunicipio(codigo) {
  const z = zonaSocial(codigo);
  if (!z) return '';
  const kv = (k, v) => (v == null ? '' : `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`);
  const pct = (v) => (v == null ? null : `${formato(v, 1)} %`);
  const c = z.censo || {};
  const partes = [];
  if (z.censo) {
    const comp = [['Vivienda inadecuada', c.nbi_vivienda], ['Servicios inadecuados', c.nbi_servicios], ['Hacinamiento crítico', c.nbi_hacinamiento],
      ['Inasistencia escolar', c.nbi_inasistencia], ['Dependencia económica', c.nbi_dependencia]].filter(([, v]) => v != null);
    partes.push(`<div class="sec-ctx">Población y pobreza · censo 2018 (DANE)${z.pdet ? ' <span class="chip white">PDET</span>' : ''}</div>
      ${kv('Población 2018', c.poblacion_2018 != null ? `${Math.round(c.poblacion_2018).toLocaleString('es-CO')} hab. · ${formato(c.pct_rural_disperso, 0)} % rural disperso` : null)}
      ${kv('Indígena · afro', c.pct_indigena != null ? `${formato(c.pct_indigena, 1)} % · ${formato(c.pct_afro, 1)} %` : null)}
      ${kv('Pobreza multidimensional (IPM)', pct(c.ipm))}
      ${kv('Necesidades básicas insatisfechas', c.nbi != null ? `${formato(c.nbi, 1)} % · miseria ${formato(c.miseria, 1)} %` : null)}
      ${kv('Hogares sin acueducto', pct(c.hogares_sin_acueducto))}
      ${kv('Déficit habitacional', pct(c.deficit_habitacional))}
      ${comp.length ? `<div class="det-serie-t">Componentes de las NBI (% de personas)</div><div class="barras-h">${comp.map(([l, v]) => `<div class="b"><span class="l">${l}</span><span class="n">${formato(v, 1)}</span><span class="track"><span style="width:${Math.min(100, v)}%"></span></span></div>`).join('')}</div>` : ''}
      ${z.pdet ? kv('PDET', z.subregion_pdet || 'Sí') : ''}`);
  }
  const t = z.territorio;
  if (t) {
    partes.push(`<div class="sec-ctx">Territorio étnico y protegido</div>
      ${kv('En resguardos indígenas', t.resguardo_km2 != null ? `${formato(t.pct_resguardo, 1)} % · ${t.resguardos_n} resguardo${t.resguardos_n === 1 ? '' : 's'}` : null)}
      ${t.pueblos?.length ? kv('Pueblos', t.pueblos.join(', ')) : ''}
      ${kv('En áreas protegidas', t.area_protegida_km2 != null ? `${formato(t.pct_area_protegida, 1)} % · ${t.area_protegidas_n} área${t.area_protegidas_n === 1 ? '' : 's'}` : null)}`);
  }
  if (z.irca?.ultimo) {
    const u = z.irca.ultimo;
    partes.push(kv(`Calidad del agua (IRCA ${u.anio}, INS)`, `${formato(u.valor, 1)} · ${u.nivel}`));
  }
  if (z.seguridad) {
    const r = z.seguridad.resumen;
    const D = S.social.metadata.delitos;
    const { i } = indiceMesSocial();
    const hasta = etiquetaMes(mesesSocial()[i]);
    const h = tasa12m(z, 'homicidio'), ex = tasa12m(z, 'extorsion');
    const otros = Object.keys(D).filter((d) => !['homicidio', 'extorsion'].includes(d) && r[d]?.total_desde_2003 > 0)
      .sort((a, b) => r[b].total_desde_2003 - r[a].total_desde_2003);
    partes.push(`<div class="sec-ctx">Seguridad · Ministerio de Defensa</div>
      ${kv(`Homicidios, 12 meses hasta ${hasta}`, h ? `${h.n} · ${formato(h.tasa, 1)} por 100.000 hab.` : null)}
      ${kv(`Extorsión, 12 meses hasta ${hasta}`, ex ? `${ex.n} · ${formato(ex.tasa, 1)} por 100.000 hab.` : null)}
      <div class="det-serie-t">Homicidios (barras) y extorsión (línea) por mes</div>
      <div class="chart-mini"><canvas id="chart-seg"></canvas></div>
      ${otros.length ? `<div class="det-serie-t">Otros delitos · últimos 12 meses publicados / desde 2003</div>
      <div class="eventos">${otros.map((d) => `<div class="e"><span>${D[d]}</span><small>${r[d].ultimos_12m} / ${r[d].total_desde_2003}</small></div>`).join('')}</div>` : ''}`);
  }
  const em = z.emergencias;
  if (em) {
    const max = Math.max(...Object.values(em.por_tipo));
    partes.push(`<div class="sec-ctx">Emergencias atendidas · UNGRD</div>
      ${kv('Emergencias', `${em.total} (${Object.keys(em.por_anio).join(', ')})`)}
      ${kv('Personas afectadas · fallecidos', `${em.personas.toLocaleString('es-CO')} · ${em.fallecidos}`)}
      <div class="barras-h">${Object.entries(em.por_tipo).map(([tp, n]) => `<div class="b"><span class="l">${tp}</span><span class="n">${n}</span><span class="track"><span style="width:${(n / max) * 100}%;background:#c2410c"></span></span></div>`).join('')}</div>
      <div class="det-serie-t">Últimas emergencias</div>
      <div class="eventos">${em.ultimas.slice(0, 5).map((e) => `<div class="e"><span>${e.evento}</span><small>${ui.fecha(e.fecha + 'T12:00:00')}${e.personas ? ` · ${e.personas.toLocaleString('es-CO')} pers.` : ''}</small></div>`).join('')}</div>`);
  }
  return partes.join('');
}

function dibujarSeguridad(codigo) {
  const z = zonaSocial(codigo);
  const cnv = document.getElementById('chart-seg');
  if (!cnv || !z?.seguridad) return;
  const meses = mesesSocial();
  const { i: sel } = indiceMesSocial();
  S.chart2 = new Chart(cnv, {
    data: {
      labels: meses,
      datasets: [
        { type: 'bar', label: 'Homicidios', data: z.seguridad.serie.homicidio, backgroundColor: meses.map((_, k) => (k === sel ? '#7f0000' : 'rgba(215,48,31,.5)')), barPercentage: 1, categoryPercentage: 1 },
        { type: 'line', label: 'Extorsión', data: z.seguridad.serie.extorsion, borderColor: '#4c1d95', borderWidth: 1.2, pointRadius: 0, tension: 0.3 },
      ],
    },
    options: { ...OPC_BASE(), scales: { ...OPC_BASE().scales, y: { ...OPC_BASE().scales.y, beginAtZero: true } },
      plugins: { legend: { display: false }, tooltip: { ...ui.tooltip(), callbacks: { title: (it) => etiquetaMes(it[0].label), label: (c) => `${c.dataset.label}: ${c.raw}` } } },
      onClick: (_, els) => { if (els.length) { S.tiempo.modo = 'mensual'; S.tiempo.iMes = mesesTiempo().indexOf(meses[els[0].index]); alCambiarTiempo(); } } },
  });
}

// Ficha del paquete: el entorno real (municipio, resguardos, areas protegidas, delitos, emergencias)
function contextoDelPaquete(id) {
  const c = S.contexto?.paquetes?.[id];
  if (!c) return '';
  const kv = (k, v) => (v == null ? '' : `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`);
  const cerca = (pct, nombre, extra, dist) => (nombre == null ? null
    : pct > 0 ? `${formato(pct, 0)} % del paquete en ${nombre}${extra ? ` (${extra})` : ''}` : `${nombre}${extra ? ` (${extra})` : ''} a ${formato(dist, 1)} km`);
  return `<div class="sec-ctx">Contexto real del territorio</div>
    ${kv('Municipio', c.municipio ? `${c.municipio}${c.pdet ? ' · PDET' : ''}` : null)}
    ${kv('Pobreza (IPM) · NBI', c.ipm != null ? `${formato(c.ipm, 1)} % · ${formato(c.nbi, 1)} %` : null)}
    ${kv('Población indígena del municipio', c.pct_indigena != null ? `${formato(c.pct_indigena, 1)} %` : null)}
    ${kv('Resguardo indígena', cerca(c.pct_en_resguardo, c.resguardo_cercano, c.resguardo_pueblo, c.distancia_resguardo_km))}
    ${kv('Área protegida', cerca(c.pct_en_area_protegida, c.area_protegida_cercano, null, c.distancia_area_protegida_km))}
    ${kv('Homicidios en el municipio (12 meses)', c.homicidio_12m_municipio != null ? `${c.homicidio_12m_municipio} · ${formato(c.tasa_homicidio_12m, 1)} por 100.000` : null)}
    ${kv('Extorsión en el municipio (12 meses)', c.extorsion_12m_municipio != null ? `${c.extorsion_12m_municipio} · ${formato(c.tasa_extorsion_12m, 1)} por 100.000` : null)}
    ${kv('Emergencias en el municipio', c.emergencias_municipio != null ? `${c.emergencias_municipio}${c.emergencias_tipo_principal ? ` · sobre todo ${c.emergencias_tipo_principal.toLowerCase()}` : ''}` : null)}
    ${kv(`Calidad del agua (IRCA ${c.irca_anio ?? ''})`, c.irca_ultimo != null ? formato(c.irca_ultimo, 1) : null)}
    <div class="det-foot">El paquete es sintético; su entorno es real (DANE censo 2018, ANT, RUNAP, Ministerio de Defensa, UNGRD, INS). Tener un resguardo cerca indica dónde aplica la consulta previa, no una amenaza. Este contexto entra al ICT en la vulnerabilidad y en las amenazas externas.</div>`;
}

// ---------------------------------------------------------------------------
// Resguardos indigenas (ANT) y areas protegidas (RUNAP)
// ---------------------------------------------------------------------------

const ESTILO_AP = { nacional: ['#15803d', 'rgba(22,163,74,.28)'], regional: ['#0f766e', 'rgba(45,212,191,.22)'], privada: ['#65a30d', 'rgba(190,242,100,.3)'] };
const resguardosCapa = L.geoJSON(null, { pane: 'territorios', style: estiloResguardo, onEachFeature: eventosResguardo });
const areasCapa = L.geoJSON(null, { pane: 'territorios', style: estiloArea, onEachFeature: eventosArea });
capas.resguardos.addLayer(resguardosCapa);
capas.areas.addLayer(areasCapa);

function estiloResguardo(f) {
  const sel = S.sel?.tipo === 'resguardo' && S.sel.id === f.properties.id_resguardo;
  return { color: '#7c3aed', weight: sel ? 3 : 1.8, dashArray: sel ? null : '6 4', fillColor: '#a78bfa', fillOpacity: sel ? 0.4 : 0.2 };
}
function estiloArea(f) {
  const sel = S.sel?.tipo === 'area' && S.sel.id === f.properties.id_area;
  const [borde, relleno] = ESTILO_AP[f.properties.ambito] || ESTILO_AP.nacional;
  return { color: borde, weight: sel ? 3 : 1.6, fillColor: relleno, fillOpacity: sel ? 0.6 : 1 };
}
function eventosResguardo(f, layer) {
  const p = f.properties;
  layer.bindTooltip(`<b>${p.nombre}</b><br><span class="sub">${p.pueblo || 'Pueblo sin dato'} · ${km2(p.area_km2)} km²${p.poblacion_2020 ? ` · ${Math.round(p.poblacion_2020).toLocaleString('es-CO')} hab. (2020)` : ''}</span>`, { sticky: true, className: 'map-tip' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('resguardo', p.id_resguardo); });
}
function eventosArea(f, layer) {
  const p = f.properties;
  layer.bindTooltip(`<b>${p.nombre}</b><br><span class="sub">${p.categoria}</span>`, { sticky: true, className: 'map-tip' });
  layer.on('click', (e) => { L.DomEvent.stopPropagation(e); seleccionar('area', p.id_area); });
}
const km2 = (v) => (v == null ? '-' : v < 10 ? Number(v).toFixed(2) : Math.round(v).toLocaleString('es-CO'));
const nombreMpio = (cod) => S.municipios?.features.find((f) => f.properties.codigo === cod)?.properties.nombre || cod;

function detalleResguardo(p) {
  const kv = (k, v) => (v == null ? '' : `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`);
  return `
    ${cabecera('tent', '#f1e9fe', '#6d28d9', p.nombre, `Resguardo indígena${p.codigo_resguardo ? ` · código ${p.codigo_resguardo}` : ''}`)}
    <div class="det-chips"><span class="chip ok">ANT · real</span>${p.pueblo ? `<span class="chip white">Pueblo ${p.pueblo}</span>` : ''}</div>
    ${kv('Área en La Guajira', `${km2(p.area_km2)} km²`)}
    ${kv('Población (proyección 2020)', p.poblacion_2020 ? `${Math.round(p.poblacion_2020).toLocaleString('es-CO')} hab. en La Guajira` : 'sin dato del Ministerio del Interior')}
    ${kv('Municipios', p.municipios ? p.municipios.split(',').map(nombreMpio).join(', ') : null)}
    ${kv('Último acto administrativo', p.ultimo_acto)}
    <div class="det-foot">Polígono de la Agencia Nacional de Tierras, recortado a La Guajira. Un proyecto que pueda afectar directamente a la comunidad requiere consulta previa (Convenio 169 de la OIT); la Dirección de la Autoridad Nacional de Consulta Previa del Ministerio del Interior determina si procede. También hay comunidades fuera de resguardos.</div>`;
}
function detalleArea(p) {
  const kv = (k, v) => (v == null ? '' : `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`);
  const AMB = { nacional: 'Nacional', regional: 'Regional', privada: 'Privada (sociedad civil)' };
  return `
    ${cabecera('trees', '#e3f5e9', '#15803d', p.nombre, p.categoria)}
    <div class="det-chips"><span class="chip ok">RUNAP · real</span><span class="chip white">${AMB[p.ambito] || p.ambito}</span></div>
    ${kv('Administra', p.organizacion)}
    ${kv('Área total', `${km2(p.area_km2)} km²`)}
    ${kv('En tierra de La Guajira', `${km2(p.area_en_guajira_km2)} km²`)}
    ${kv('Inscrita en el RUNAP', p.inscrita)}
    <div class="det-foot">Registro Único Nacional de Áreas Protegidas (Parques Nacionales Naturales de Colombia). Las actividades permitidas dependen de la categoría y del plan de manejo de cada área.</div>`;
}

// ---------------------------------------------------------------------------
// Barra de tiempo
// ---------------------------------------------------------------------------

function cambiarModoTiempo(modo) {
  pararTiempo();
  S.tiempo.modo = modo;
  const socialMensual = mapa.hasLayer(capas.social) && indicadorSocial()?.temporal;
  if (modo === 'mensual' && !mapa.hasLayer(capas.chirps) && !socialMensual) {   // sin capa mensual encendida, se enciende CHIRPS
    const sw = document.querySelector('input[data-capa="chirps"]');
    if (sw && !sw.checked) { sw.checked = true; sw.dispatchEvent(new Event('change', { bubbles: true })); }
  }
  alCambiarTiempo();
}

function renderBarraTiempo() {
  const slider = document.getElementById('t-slider');
  document.querySelectorAll('#t-modo button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.tiempo.modo));
  let etiqueta, desde, hasta, nota;
  if (S.tiempo.modo === 'diario') {
    const dias = diasIdeam();
    if (S.tiempo.iDia == null || S.tiempo.iDia > dias.length - 1) S.tiempo.iDia = dias.length - 1;
    slider.max = dias.length - 1;
    slider.value = S.tiempo.iDia;
    const d = dias[S.tiempo.iDia];
    etiqueta = d === 'ahora' ? 'Ahora · en vivo' : ui.fecha(`${d}T12:00:00`);
    desde = dias.length > 1 ? ui.fecha(`${dias[0]}T12:00:00`) : '';
    hasta = 'ahora';
    nota = 'Estaciones del IDEAM, un valor por día';
  } else {
    const meses = mesesTiempo();
    if (!meses.length) { S.tiempo.modo = 'diario'; return renderBarraTiempo(); }
    if (S.tiempo.iMes == null || S.tiempo.iMes > meses.length - 1) S.tiempo.iMes = meses.length - 1;
    slider.max = meses.length - 1;
    slider.value = S.tiempo.iMes;
    etiqueta = etiquetaMes(meses[S.tiempo.iMes]);
    desde = meses[0].slice(0, 4);
    hasta = meses[meses.length - 1].slice(0, 4);
    nota = 'Lluvia CHIRPS y delitos por municipio · las estaciones muestran su dato actual';
  }
  document.getElementById('t-fecha').textContent = etiqueta;
  document.getElementById('t-desde').textContent = desde;
  document.getElementById('t-hasta').textContent = hasta;
  document.getElementById('t-nota').textContent = nota;
  document.querySelector('#t-modo [data-v="mensual"]').disabled = !mesesTiempo().length;
}

// Todo lo que depende de la fecha se vuelve a dibujar; la ficha abierta conserva su scroll
function alCambiarTiempo() {
  renderBarraTiempo();
  renderClima();
  renderCobertura();
  renderChirps();
  renderSocial();
  if (S.sel && ['estacion', 'paquete', 'municipio', 'radiacion'].includes(S.sel.tipo)) {
    const el = document.getElementById('detalle');
    const y = el.scrollTop;
    renderDetalle();
    el.scrollTop = y;
  }
}

function pararTiempo() {
  if (!S.tiempo.jugando) return;
  clearInterval(S.tiempo.jugando);
  S.tiempo.jugando = null;
  document.getElementById('t-play').innerHTML = '<i data-lucide="play"></i>';
  ui.icons();
}
function reproducirTiempo() {
  if (S.tiempo.jugando) { pararTiempo(); return; }
  const clave = S.tiempo.modo === 'diario' ? 'iDia' : 'iMes';
  const max = Number(document.getElementById('t-slider').max);
  if (S.tiempo[clave] >= max) S.tiempo[clave] = 0;           // si estaba al final, empieza de nuevo
  document.getElementById('t-play').innerHTML = '<i data-lucide="pause"></i>';
  ui.icons();
  S.tiempo.jugando = setInterval(() => {
    if (S.tiempo[clave] >= max) { pararTiempo(); return; }
    S.tiempo[clave] += 1;
    alCambiarTiempo();
  }, S.tiempo.modo === 'diario' ? 700 : 450);
}

document.getElementById('t-slider').addEventListener('input', (e) => {
  pararTiempo();
  S.tiempo[S.tiempo.modo === 'diario' ? 'iDia' : 'iMes'] = Number(e.target.value);
  alCambiarTiempo();
});
document.querySelectorAll('#t-modo button').forEach((b) => b.addEventListener('click', () => cambiarModoTiempo(b.dataset.v)));
document.getElementById('t-play').addEventListener('click', reproducirTiempo);
L.DomEvent.disableClickPropagation(document.getElementById('barra-tiempo'));
L.DomEvent.disableScrollPropagation(document.getElementById('barra-tiempo'));

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
  layer.bindTooltip(() => {
    let extra = '';
    if (S.chirps && mapa.hasLayer(capas.chirps)) {
      const z = S.chirps.municipios[p.codigo];
      const { i } = indiceMesChirps();
      if (z && z.mm[i] != null) extra = `<br><span class="sub">Lluvia ${etiquetaMes(mesesChirps()[i])}: ${formato(z.mm[i], 1)} mm${z.anomalia_pct[i] != null ? ` (${z.anomalia_pct[i] > 0 ? '+' : ''}${z.anomalia_pct[i]} % frente a lo normal)` : ''}</span>`;
    }
    if (S.social && mapa.hasLayer(capas.social)) {
      const ind = indicadorSocial();
      extra += `<br><span class="sub">${ind.nombre}: ${textoSocial(valorSocial(p.codigo, ind), ind)}${ind.temporal ? ' por 100.000 hab.' : ''}</span>`;
    }
    return `<b>${p.nombre}</b><br><span class="sub">${p.area_km2.toLocaleString('es-CO')} km²</span>${extra}`;
  }, { sticky: true, className: 'map-tip' });
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
    ${socialDelMunicipio(p.codigo)}
    ${lluviaDelMunicipio(p.codigo)}
    <div class="det-foot">Límites del Marco Geoestadístico Nacional del DANE (${S.municipios?.metadata?.version_geometria || 'MGN'}). Las estaciones se cuentan por su ubicación, no por el municipio que declara el catálogo. Las tasas por 100.000 habitantes usan la población del censo 2018.</div>`;
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

// ---------------------------------------------------------------------------
// Controlador de tiempo. Dos escalas:
//   dias    los ultimos 30 dias de las estaciones del IDEAM (un valor por dia) y, al final, "ahora" (en vivo)
//   meses   la lluvia CHIRPS por municipio de los ultimos anos (un valor por mes)
// ---------------------------------------------------------------------------

const RUMBOS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO'];
const rumboDe = (g) => (g == null ? undefined : RUMBOS[Math.round(((g % 360) + 360) % 360 / 22.5) % 16]);
const hoyISO = () => new Date().toISOString().slice(0, 10);
const etiquetaMes = (m) => (m ? `${MESES[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}` : '-');

function diasIdeam() {
  const m = S.clima?.metadata;
  if (!m?.desde) return ['ahora'];
  const out = [];
  const d = new Date(`${m.desde}T12:00:00`), fin = new Date(`${m.hasta}T12:00:00`);
  while (d <= fin) { out.push(d.toISOString().slice(0, 10)); d.setDate(d.getDate() + 1); }
  out.push('ahora');
  return out;
}
const mesesChirps = () => S.chirps?.metadata?.meses || [];

// Dia elegido (AAAA-MM-DD) o null si se ve "ahora" (o si la escala es mensual: las estaciones muestran su dato actual)
function fechaDia() {
  if (S.tiempo.modo !== 'diario') return null;
  const dias = diasIdeam();
  const d = dias[Math.min(S.tiempo.iDia ?? dias.length - 1, dias.length - 1)];
  return d && d !== 'ahora' ? d : null;
}
// Mes de referencia (AAAA-MM): el elegido en la escala mensual, o el del dia elegido
function mesReferencia() {
  if (S.tiempo.modo === 'mensual') return mesesTiempo()[S.tiempo.iMes ?? mesesTiempo().length - 1] || null;
  return (fechaDia() || hoyISO()).slice(0, 7);
}
const mesIndice = () => Number((mesReferencia() || hoyISO()).slice(5, 7)) - 1;

// Lluvia acumulada en la ventana de n dias que termina en `dia`, con la serie diaria de la estacion
function lluviaHasta(p, dia, n) {
  const fin = new Date(`${dia}T12:00:00`), ini = new Date(fin);
  ini.setDate(ini.getDate() - (n - 1));
  let mm = 0, con = 0, enSerie = 0;
  (p.serie || []).forEach((s) => {
    const d = new Date(`${s.dia}T12:00:00`);
    if (d < ini || d > fin) return;
    enSerie += 1;
    if (s.mm != null) { mm += s.mm; con += 1; }
  });
  return { mm: Math.round(mm * 10) / 10, con, completo: enSerie === n && con === n };
}

// Valor de una variable en una estacion: el del dia elegido, o el mas reciente (en vivo > ultimas horas > ventana)
function lecturaActual(p, varKey) {
  const dia = fechaDia();
  if (dia) {
    const s = p.variables?.[varKey]?.serie?.find((x) => x.dia === dia);
    return s && s.media != null ? { valor: s.media, hora: `${dia}T12:00:00`, rumbo: varKey === 'viento_dir' ? rumboDe(s.media) : undefined, origen: 'dia' } : null;
  }
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
    const mes = mesIndice();
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
      const dia = fechaDia();
      if (dia) {
        const l = lluviaHasta(p, dia, DIAS[S.ventana]);
        const sinDato = l.con === 0;
        out.push({ id: p.codigo, p, lon, lat, valor: l.mm, sd: sinDato, parcial: !sinDato && !l.completo, cota: !sinDato && !l.completo, hasta: dia });
        return;
      }
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
  if (pt.radiacion) return `<b>${p.estacion}</b><br><span class="sub">${p.municipio} · ${formato(pt.valor, 1)} kWh/m²/día de media en ${MESES[mesIndice()]}</span>`;
  if (v === 'lluvia') {
    return pt.sd
      ? `<b>${p.nombre}</b><br><span class="sub">${p.municipio} · sin datos suficientes (${p.dias_con_dato} de 30 días)</span>`
      : `<b>${p.nombre}</b><br><span class="sub">${p.municipio} · ${pt.cota ? 'al menos ' : ''}${formato(pt.valor, 1)} mm en ${DIAS[S.ventana]} días${pt.hasta ? ` hasta el ${ui.fecha(pt.hasta + 'T12:00:00')}` : ''}</span>`;
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
    renderCobertura();
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
      pane: 'riesgosPane', radius: 3.5 + (p.puntaje_ram || 1) * 1.1, color: '#fff', weight: 1.2,
      fillColor: p.tipo === 'oportunidad' ? '#4da3ff' : (ui.RAM[p.nivel_residual]?.bg || ui.css('--lvl-critico')), fillOpacity: 0.95,
    })
      .bindTooltip(`<b>${p.id_riesgo}</b> · ${ui.cat(p.categoria).label}<br><span class="sub">${ui.ESTADO[p.estado]?.label || p.estado} · RAM ${p.ram_residual || '-'} (${ui.RAM[p.nivel_residual]?.nombre || 'sin calificar'})</span>`, { className: 'map-tip' })
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
  resguardosCapa.setStyle(estiloResguardo);
  areasCapa.setStyle(estiloArea);
  restilarAgua();
  renderClima();
  renderDetalle();
}

function cerrarDetalle() {
  S.sel = null;
  paquetes.setStyle(estiloPaquete);
  resguardosCapa.setStyle(estiloResguardo);
  areasCapa.setStyle(estiloArea);
  restilarAgua();
  renderClima();
  document.getElementById('detalle').hidden = true;
  if (S.chart) { S.chart.destroy(); S.chart = null; }
  if (S.chart2) { S.chart2.destroy(); S.chart2 = null; }
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
  const mes = mesIndice();
  return `
    ${cabecera('sun', '#fff3c4', '#b45309', p.estacion, `${p.municipio} · estación ${p.tipo?.toLowerCase() || ''}`)}
    <div class="det-chips"><span class="chip ok">IDEAM · real</span><span class="chip white">Promedio histórico</span>${p.altitud != null ? `<span class="chip white">${p.altitud} m s. n. m.</span>` : ''}</div>
    <div class="det-num"><div class="num">${(p.meses[mes] / 1000).toFixed(1)}</div><div class="u">kWh/m²/día en ${MESES[mes]}</div></div>
    <div class="chart-mini"><canvas id="chart-serie"></canvas></div>
    <div class="kv"><span class="k">Promedio anual</span><span class="v">${(p.anual / 1000).toFixed(2)} kWh/m²/día</span></div>
    <div class="det-foot">El IDEAM publica solo el promedio mensual y anual de la radiación global (Wh/m² por día), no una serie diaria, y solo en estaciones con sensor calibrado.</div>`;
}

// Criterios del ICT: nombre, color en la barra apilada y como se lee cada componente con su valor real
const CRIT_ICT = [
  ['severidad_riesgo', 'Severidad de los riesgos', '--green-800'],
  ['vulnerabilidad_territorial', 'Vulnerabilidad del territorio', '--green-600'],
  ['exposicion_proyecto', 'Exposición del paquete', '--green-500'],
  ['amenazas_externas', 'Amenazas externas', '--green-300'],
  ['convergencia', 'Convergencia de amenazas', '--lime'],
];
function componentesIct(p) {
  const cfg = S.paramsIct?.criterios?.amenazas_externas || {};
  const pct = (v) => `${formato(v * 100, 0)} %`;
  const resg = p.distancia_resguardo_km == null ? null
    : p.fraccion_resguardo > 0 ? `${pct(p.fraccion_resguardo)} del paquete dentro de un resguardo`
      : p.distancia_resguardo_km === 0 ? 'Colinda con un resguardo' : `Resguardo más cercano a ${formato(p.distancia_resguardo_km, 1)} km`;
  const area = p.distancia_area_protegida_km == null ? null
    : p.fraccion_area_protegida > 0 ? `${pct(p.fraccion_area_protegida)} dentro de un área protegida`
      : `Área protegida más cercana a ${formato(p.distancia_area_protegida_km, 1)} km`;
  const lluvia = p.lluvia_mm != null
    ? `${formato(p.lluvia_mm, 1)} mm en ${cfg.ventana_dias || 14} días · ${p.lluvia_estacion} a ${formato(p.lluvia_distancia_km, 1)} km`
    : `Sin dato al día: ninguna estación del IDEAM a menos de ${cfg.distancia_maxima_estacion_km || 20} km tiene ${cfg.dias_minimos_con_dato || 10} de los últimos ${cfg.ventana_dias || 14} días`;
  return [
    ['Vulnerabilidad', [
      ['Territorio étnico (ANT)', p.vul_etnico, resg],
      ['Pobreza (DANE)', p.vul_pobreza, p.ipm != null ? `IPM ${formato(p.ipm, 1)} % (censo 2018)` : null],
      ['Áreas protegidas (RUNAP)', p.vul_ambiental, area],
      ['Acceso (INVIAS + IGAC)', p.vul_acceso, p.vias_tiempo_seco != null ? `${pct(p.vias_tiempo_seco)} de los km cercanos solo en tiempo seco` : null],
    ]],
    ['Amenazas externas', [
      ['Lluvia reciente (IDEAM)', p.ext_lluvia_reciente, lluvia],
      ['Lluvia fuera de lo normal (CHIRPS)', p.ext_anomalia_lluvia, p.anomalia_lluvia != null ? `${formato(p.anomalia_lluvia * 100, 0)} % de desviación en los últimos meses` : null],
      ['Emergencias (UNGRD)', p.ext_emergencias, p.emergencias_por_ano != null ? `${formato(p.emergencias_por_ano, 1)} al año en ${p.municipio}` : null],
      ['Delitos contra proyectos (MinDefensa)', p.ext_seguridad, p.delitos_100k != null ? `${formato(p.delitos_100k, 1)} por 100.000 hab. en 12 meses` : null],
    ]],
  ];
}
function ictDelPaquete(p) {
  if (p.ICT == null) return '';
  const d = p.tendencia_delta;
  const tend = d == null ? '' : d > 0 ? `<span class="t-sube">+${formato(d, 1)}</span>` : d < 0 ? `<span class="t-baja">${formato(d, 1)}</span>` : '<span>sin cambio</span>';
  const barra = CRIT_ICT.map(([k, n, c]) => `<span title="${n}: ${formato(p[`${k}_contrib`], 1)} puntos" style="width:${p[`${k}_contrib`] || 0}%;background:var(${c})"></span>`).join('');
  const filas = CRIT_ICT.map(([k, n, c]) => `
    <div class="crit-fila"><span class="sw" style="background:var(${c})"></span><span class="n">${n}</span>
      <span class="meter"><span style="width:${(p[k] || 0) * 100}%"></span></span><b>${formato(p[`${k}_contrib`], 1)}</b></div>`).join('');
  const comps = componentesIct(p).map(([titulo, lista]) => `
    <div class="comp-t">${titulo}</div>
    ${lista.map(([n, v, txt]) => `<div class="comp${v == null ? ' sin' : ''}"><span class="n">${n}</span><span class="meter"><span style="width:${(v || 0) * 100}%"></span></span><b>${v == null ? 's/d' : formato(v, 2)}</b><span class="txt">${txt || 'sin dato'}</span></div>`).join('')}`).join('');
  const causas = p.escalamiento ? String(p.causas_escalamiento).split('; ') : [];
  return `
    <div class="ict-cab">
      <div class="num lg">${formato(p.ICT, 0)}</div>
      <div class="ict-meta">
        <div><span class="lvl ${p.nivel}">${ui.NIVEL[p.nivel]}</span> <span class="sub">ICT de 0 a 100</span></div>
        <div class="sub">7 días: ${tend} · confianza ${formato((p.indice_confianza || 0) * 100, 0)} %${p.en_punto_caliente ? ' · en un punto caliente' : ''}</div>
      </div>
    </div>
    <div class="ict-barra">${barra}</div>
    <div class="crit-filas">${filas}</div>
    ${causas.length ? `<div class="escala-box"><div class="t"><i data-lucide="siren"></i> Puede escalar a crisis${p.puntos_crisis ? ` · ${p.puntos_crisis === 1 ? '1 punto' : `${p.puntos_crisis} puntos`} en el mapa` : ''}</div><ul>${causas.map((c) => `<li>${c}</li>`).join('')}</ul></div>` : ''}
    <details class="ict-comp"><summary>Qué hay detrás: el territorio real del paquete</summary>${comps}
      <div class="det-foot">Cada componente vale de 0 a 1 con un tope fijo (parametros.yaml). Un componente sin dato no se imputa: no cuenta y baja la confianza.</div>
    </details>
    <div class="kv"><span class="k">Índice de oportunidad</span><span class="v">${formato(p.indice_oportunidad, 0)} de 100 (riesgos positivos abiertos)</span></div>`;
}

function detallePaquete(p) {
  const propios = S.riesgos.map((r) => r.properties).filter((r) => r.id_paquete_trabajo === p.id_paquete);
  const amenazas = propios.filter((r) => r.tipo === 'amenaza').length;
  return `
    ${cabecera('hexagon', 'var(--green-50)', 'var(--green-700)', ui.nombreCorto(p.nombre), `${p.id_paquete}${p.municipio ? ` · ${p.municipio}` : ''}`)}
    <div class="det-chips"><span class="chip warn">Registro sintético</span><span class="chip ok">Territorio real</span>${p.ruta_critica ? '<span class="chip">Ruta crítica</span>' : ''}</div>
    ${ictDelPaquete(p)}
    <div class="sec-ctx">Registro de riesgos</div>
    <div class="kv"><span class="k">Riesgos en el paquete</span><span class="v">${propios.length}</span></div>
    <div class="kv"><span class="k">Amenazas / oportunidades</span><span class="v">${amenazas} / ${propios.length - amenazas}</span></div>
    <div class="kv"><span class="k">Materializados</span><span class="v">${propios.filter((r) => r.estado === 'materializado').length}</span></div>
    <div class="kv"><span class="k">Próximos a materializarse</span><span class="v">${propios.filter((r) => r.estado === 'proximo_a_materializarse').length}</span></div>
    ${ramDelPaquete(p, propios)}
    ${climaDelPaquete(p.id_paquete)}
    ${contextoDelPaquete(p.id_paquete)}`;
}

// Ficha del paquete: perfil RAM de sus amenazas abiertas y lo que sugiere el territorio real
function ramDelPaquete(p, propios) {
  const abiertas = propios.filter((r) => r.tipo === 'amenaza' && r.estado !== 'materializado' && r.nivel_residual);
  const orden = ['VH', 'H', 'M', 'L', 'N'];
  const n = Object.fromEntries(orden.map((k) => [k, abiertas.filter((r) => r.nivel_residual === k).length]));
  const peor = orden.find((k) => n[k]);
  const cfg = peor && S.ram?.niveles?.[peor];
  const c = S.contexto?.paquetes?.[p.id_paquete] || {};
  const sug = [
    c.ram_prob_seguridad && `seguridad física: probabilidad ${c.ram_prob_seguridad} (${PROB_RAM[c.ram_prob_seguridad]?.toLowerCase()}, por delitos en ${c.municipio})`,
    c.ram_prob_desastres && `riesgos climáticos: probabilidad ${c.ram_prob_desastres} (emergencias de la UNGRD en el municipio)`,
    c.ram_cons_imagen ? `social: consecuencia en Imagen de al menos ${c.ram_cons_imagen} (${c.distancia_resguardo_km === 0 ? 'dentro de un resguardo' : 'resguardo o PDET cerca'})` : null,
    c.ram_cons_ambiental ? `ambiental: consecuencia de al menos ${c.ram_cons_ambiental} (${c.distancia_area_protegida_km === 0 ? 'dentro de un área protegida' : `área protegida a ${formato(c.distancia_area_protegida_km, 1)} km`})` : null,
  ].filter(Boolean);
  return `<div class="sec-ctx">Matriz RAM · amenazas abiertas (con controles)</div>
    <div class="ram-fila">${orden.map((k) => `<span class="ram-cuenta">${ui.ramChip(k)}<b>${n[k]}</b></span>`).join('')}</div>
    ${cfg ? `<div class="kv"><span class="k">Peor nivel: ${ui.RAM[peor].nombre}</span><span class="v">${cfg.decision}. Aprueba: ${cfg.aprueba}</span></div>` : ''}
    ${sug.length ? `<div class="det-serie-t">Lo que sugiere el territorio real para calificar</div><ul class="ram-sug">${sug.map((s) => `<li>${s}</li>`).join('')}</ul>` : ''}
    ${c.ram_por_revisar ? `<div class="kv"><span class="k">Amenazas calificadas por debajo de esa evidencia</span><span class="v">${c.ram_por_revisar}: ${String(c.ram_por_revisar_ids).split(',').join(', ')}</span></div>` : ''}`;
}

// Calificacion RAM de un riesgo: nivel residual (con controles), el inherente y las cinco dimensiones
const PROB_RAM = { A: 'No ha ocurrido en la industria', B: 'Ha ocurrido en la industria', C: 'Ha ocurrido en la empresa', D: 'Varias veces al año en la empresa', E: 'Varias veces al año en la unidad' };
const COL_DIM = { PE: 'cons_personas', EC: 'cons_economica', MA: 'cons_ambiental', CL: 'cons_clientes', IM: 'cons_imagen' };
function ramDelRiesgo(p) {
  if (!p.nivel_residual) return '<div class="kv"><span class="k">Matriz RAM</span><span class="v">sin calificar</span></div>';
  const op = p.tipo === 'oportunidad';
  const dims = Object.entries(COL_DIM).map(([d, col]) => `<span class="ram-dim${d === p.dimension_dominante ? ' manda' : ''}" title="${ui.DIM_RAM[d]}">${d} ${p[col] ?? '-'}</span>`).join('');
  return `
    <div class="kv"><span class="k">Matriz RAM ${op ? '(beneficio)' : 'residual'}</span><span class="v">${ui.ramChip(p.nivel_residual)} ${p.ram_residual} · ${ui.RAM[p.nivel_residual].nombre}</span></div>
    ${p.ram_inherente !== p.ram_residual ? `<div class="kv"><span class="k">Sin controles (inherente)</span><span class="v">${ui.ramChip(p.nivel_inherente)} ${p.ram_inherente}</span></div>` : ''}
    <div class="kv"><span class="k">Probabilidad</span><span class="v">${p.probabilidad_residual} · ${PROB_RAM[p.probabilidad_residual] || ''}</span></div>
    <div class="kv"><span class="k">Consecuencia por dimensión</span><span class="v ram-dims">${dims}</span></div>
    ${!op && p.controles ? `<div class="kv"><span class="k">Controles</span><span class="v">${p.controles}</span></div>` : ''}`;
}

// Lo que hizo la IA con el texto de este riesgo
function iaDelRiesgo(p) {
  const pct = Math.round((p.confianza_ia || 0) * 100);
  const filas = [];
  if (p.categoria_origen === 'ia') filas.push(`Llegó sin categoría; la IA lo clasificó como <b>${ui.cat(p.categoria).label.toLowerCase()}</b> (confianza ${pct} %${p.palabras_ia ? `, por: ${p.palabras_ia}` : ''}).`);
  if (p.categoria_origen === 'pendiente') filas.push('Llegó sin categoría y la IA no alcanzó la confianza mínima: queda pendiente.');
  if (p.revisar_categoria) filas.push(`Registrado como ${ui.cat(p.categoria).label.toLowerCase()}, pero el texto sugiere <b>${ui.cat(p.categoria_ia).label.toLowerCase()}</b> (${pct} %): revisar.`);
  if (p.revisar_ubicacion) filas.push(`Menciona <b>${p.municipio_mencionado}</b>, a más de 15 km de su paquete: revisar la ubicación.`);
  if (!filas.length) return '';
  return `<div class="ia-box"><div class="t"><i data-lucide="sparkles"></i> IA sobre el texto del registro</div>${filas.map((f) => `<div>${f}</div>`).join('')}</div>`;
}

function detalleRiesgo(p) {
  const c = ui.cat(p.categoria), est = ui.ESTADO[p.estado] || { label: p.estado, lvl: 'bajo' };
  return `
    ${cabecera(c.icon, c.bg, c.fg, p.id_riesgo, c.label)}
    <div class="det-chips"><span class="chip warn">Sintético</span><span class="chip white">${p.tipo === 'oportunidad' ? 'Oportunidad' : 'Amenaza'}</span></div>
    <div class="kv"><span class="k">Estado</span><span class="v"><span class="status"><span class="dot ${est.lvl}"></span>${est.label}</span></span></div>
    ${p.punto_crisis ? `<div class="escala-box"><div class="t"><i data-lucide="siren"></i> Punto donde puede escalar a crisis</div><ul>${String(p.causa_crisis).split('; ').map((c) => `<li>${c}</li>`).join('')}</ul></div>` : ''}
    ${p.descripcion ? `<div class="det-desc">${p.descripcion}${p.causa && p.causa !== 'sin_causa_registrada' ? `<span class="sub"> · Causa: ${p.causa}</span>` : ''}</div>` : ''}
    ${iaDelRiesgo(p)}
    ${ramDelRiesgo(p)}
    <div class="kv"><span class="k">Paquete</span><span class="v">${ui.nombreCorto((S.paquetes.features.find((f) => f.properties.id_paquete === p.id_paquete_trabajo) || {}).properties?.nombre || p.id_paquete_trabajo)}</span></div>
    <div class="kv"><span class="k">Identificado</span><span class="v">${ui.fecha(String(p.fecha_identificacion).slice(0, 10) + 'T12:00:00')}</span></div>
    <div class="kv"><span class="k">Ubicación</span><span class="v">${p.geolocalizacion_inferida ? 'Aproximada (centro del paquete)' : 'Con coordenadas'}</span></div>
    <div class="det-foot">Acción de tratamiento: ${p.accion_tratamiento || '-'}</div>`;
}

// Punto donde un riesgo puede escalar a crisis
function detalleCrisis(p) {
  const kv = (k, v) => (v == null || v === '' ? '' : `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`);
  const titulo = p.tipo === 'riesgo' ? `${p.id_riesgo} puede escalar a crisis` : `${ui.nombreCorto(p.nombre_paquete)} puede escalar a crisis`;
  const c = p.categoria ? ui.cat(p.categoria) : null;
  return `
    ${cabecera('siren', 'var(--lvl-critico-bg)', 'var(--lvl-critico)', titulo, `${ui.nombreCorto(p.nombre_paquete)} · prioridad ${PRIORIDAD[p.prioridad]}`)}
    <div class="det-chips"><span class="lvl-soft ${p.prioridad === 'critica' ? 'critico' : 'alto'}">Prioridad ${PRIORIDAD[p.prioridad]}</span>${p.nivel_ram ? `<span class="chip white">${ui.ramChip(p.nivel_ram)} RAM ${p.ram || ui.RAM[p.nivel_ram].nombre}</span>` : ''}${c ? `<span class="chip white">${c.label}</span>` : ''}</div>
    <div class="escala-box"><div class="t"><i data-lucide="siren"></i> Por qué</div><ul>${String(p.causas).split('; ').map((x) => `<li>${x}</li>`).join('')}</ul></div>
    ${kv('Qué exige la RAM', p.decision)}
    ${kv('Decide', p.aprueba)}
    ${kv('Acción de tratamiento', p.accion_tratamiento ? `${p.accion_tratamiento}${p.fecha_accion ? ` · ${ui.fecha(p.fecha_accion + 'T12:00:00')}` : ''}${p.accion_vencida ? ' · <b class="vencida">vencida</b>' : ''}` : null)}
    ${kv('Zona de intervención', `círculo de ${formato(p.radio_m / 1000, 1)} km alrededor (radio de influencia${c ? ` de un riesgo ${c.corto.toLowerCase()}` : ''})`)}
    <div class="det-acciones">
      <button class="btn btn-outline sm" data-ir-paquete="${p.id_paquete}"><i data-lucide="hexagon"></i> Ver el paquete</button>
      ${p.id_riesgo ? `<button class="btn btn-outline sm" data-ir-riesgo="${p.id_riesgo}"><i data-lucide="triangle-alert"></i> Ver el riesgo</button>` : ''}
    </div>
    <div class="det-foot">Regla de escalamiento configurable en parametros.yaml. El riesgo es del registro sintético; los resguardos y las áreas protegidas que alcanza son reales (ANT, RUNAP).</div>`;
}

// Alertas tempranas: una por paquete en escalamiento o con el ICT al alza
function detalleAlertas() {
  const a = S.alertas;
  const fecha = a[0]?.generada_en ? ui.fecha(a[0].generada_en) : '';
  const nivelSoft = { critica: 'critico', alta: 'alto', media: 'medio' };
  const nov = S.alertasEstado?.novedades;
  const marca = (id) => (nov?.nuevas?.includes(id) ? '<span class="ai-marca nueva">nueva</span>' : nov?.suben?.includes(id) ? '<span class="ai-marca sube">sube</span>' : '');
  return `
    ${cabecera('bell', 'var(--lvl-critico-bg)', 'var(--lvl-critico)', 'Alertas tempranas', a.length ? `${a.length} activas${fecha ? ` · calculadas el ${fecha}` : ''}` : 'Sin alertas activas')}
    ${estadoAlertas()}
    ${a.map((x) => `
      <div class="alerta-item">
        <div class="ai-head"><span class="lvl-soft ${nivelSoft[x.prioridad]}">${PRIORIDAD[x.prioridad]}</span><b>${ui.nombreCorto(x.nombre_paquete)}</b>${marca(x.id_paquete)}<span class="ai-ict">ICT ${formato(x.ict, 0)}</span></div>
        <div class="ai-sub">${x.municipio || ''}${x.puntos_crisis ? ` · ${x.puntos_crisis === 1 ? '1 punto' : `${x.puntos_crisis} puntos`} de crisis` : ''}</div>
        <ul class="ai-causas">${x.causas.map((c) => `<li>${c.texto}</li>`).join('')}</ul>
        ${x.acciones?.length ? `<div class="ai-acc"><b>Qué hacer</b><ul>${x.acciones.map((c) => `<li>${c}</li>`).join('')}</ul></div>` : ''}
        <button class="btn btn-outline sm" data-ir-paquete="${x.id_paquete}"><i data-lucide="map-pin"></i> Ver en el mapa</button>
      </div>`).join('')}
    <div class="det-foot">Cada corte cruza el registro con el territorio real (la lluvia del IDEAM se descarga cada día); las reglas y los umbrales están en parametros.yaml.</div>`;
}

const fechaHora = (iso) => (iso ? new Date(iso).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-');

// Estado de la tarea diaria: novedades del ultimo corte, cuando corre y por donde avisa
function estadoAlertas() {
  const e = S.alertasEstado;
  if (!e) return '';
  const nov = e.novedades, prog = e.programada || {}, ult = e.ultima;
  const canal = (k, nombre) => {
    const c = e.canales?.[k];
    if (!c?.activo) return `<span class="canal off">${nombre}: apagado</span>`;
    return c.configurado ? `<span class="canal ok">${nombre}: activo</span>` : `<span class="canal warn">${nombre}: sin configurar</span>`;
  };
  return `
    <div class="alertas-estado">
      ${nov ? `<div><b>Corte del ${ui.fecha(nov.fecha + 'T12:00:00')}</b> · ${nov.comparado_con ? `frente al ${ui.fecha(nov.comparado_con + 'T12:00:00')}` : 'primer corte'}: ${nov.nuevas.length} nuevas, ${nov.suben.length} suben, ${nov.resueltas.length} resueltas</div>` : ''}
      <div>${prog.activa ? `Se actualizan solas cada día a las ${prog.hora} · próxima: ${fechaHora(prog.proxima)}` : 'Actualización automática apagada'}${ult ? ` · última: ${fechaHora(ult.fin)} (${ult.origen})` : ''}</div>
      <div class="canales"><span class="canal ok">Boletín: activo</span>${canal('teams', 'Teams')}${canal('correo', 'Correo')}</div>
      <div class="det-acciones">
        <button class="btn btn-primary sm" id="al-actualizar"><i data-lucide="refresh-cw"></i> Actualizar ahora</button>
        <a class="btn btn-outline sm" href="/api/alertas/boletin" target="_blank" rel="noopener"><i data-lucide="file-text"></i> Boletín del día</a>
      </div>
      <div class="al-progreso" id="al-progreso" hidden></div>
    </div>`;
}

async function abrirAlertas() {
  seleccionar('alertas', null);
  try { S.alertasEstado = await ui.json('/api/alertas/estado'); } catch (e) { S.alertasEstado = null; }
  if (S.sel?.tipo === 'alertas') renderDetalle();
}

// Recarga lo que produce el modelo (paquetes, calor, crisis, alertas, registro) despues de un recalculo
async function recargarModelo() {
  const [pq, calor, crisis, zonas, alertas, riesgos] = await Promise.all([
    ui.json('/api/paquetes'), ui.json('/api/capas/grid_calor'), ui.json('/api/capas/puntos_crisis'),
    ui.json('/api/capas/zonas_intervencion'), ui.json('/api/alertas'), ui.json('/api/riesgos'),
  ]);
  S.paquetes = pq;
  paquetes.clearLayers();
  paquetes.addData(pq);
  S.calor = calor;
  S.crisis = crisis;
  S.zonas = zonas;
  S.alertas = Array.isArray(alertas) ? alertas : [];
  S.riesgos = riesgos.features;
  etiquetarProyectos();
  renderCalor();
  renderCrisis();
  renderRiesgos();
  renderBotonAlertas();
  const nEsc = pq.features.filter((f) => f.properties.escalamiento).length;
  const nProy = new Set(pq.features.map((f) => f.properties.id_proyecto)).size;
  document.getElementById('sub-proyectos').textContent = `${nProy} proyectos · ${pq.features.length} paquetes · ${nEsc} en escalamiento`;
}

async function actualizarAlertas() {
  const prog = document.getElementById('al-progreso');
  const btn = document.getElementById('al-actualizar');
  const mostrar = (txt) => { if (prog) { prog.hidden = false; prog.innerHTML = txt; } };
  btn.disabled = true;
  try {
    const r = await ui.escribir('/api/alertas/actualizar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ descargas: true }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `Error ${r.status}`);
    for (;;) {
      const t = await ui.json('/api/ram/recalcular');
      if (t.estado !== 'corriendo') {
        await recargarModelo();
        await abrirAlertas();
        const env = (t.resultado?.envios || []).filter((x) => x.canal !== 'archivo').map((x) => `${x.canal}: ${x.estado.replace('_', ' ')}`).join(' · ');
        mostrar(t.estado === 'listo' ? `Listo en ${t.segundos} s.${env ? ` ${env}.` : ''}` : `Terminó con avisos en: ${(t.fallos || []).join(', ')}`);
        return;
      }
      const actual = t.pasos?.[t.hechos?.length || 0];
      mostrar(`<span class="dot vivo"></span> Actualizando: ${t.hechos?.length || 0} de ${t.pasos?.length || 0} pasos${actual ? ` · ${actual}` : ''}… (la descarga del IDEAM tarda unos minutos)`);
      await new Promise((ok) => setTimeout(ok, 2000));
    }
  } catch (e) {
    mostrar(`No se pudo actualizar: ${e.message}`);
    btn.disabled = false;
  }
}

function renderDetalle() {
  const el = document.getElementById('detalle');
  if (S.chart) { S.chart.destroy(); S.chart = null; }
  if (S.chart2) { S.chart2.destroy(); S.chart2 = null; }
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
  } else if (S.sel.tipo === 'resguardo') {
    p = S.resguardos?.features.find((f) => f.properties.id_resguardo === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleResguardo(p);
  } else if (S.sel.tipo === 'area') {
    p = S.areasRunap?.features.find((f) => f.properties.id_area === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleArea(p);
  } else if (S.sel.tipo === 'crisis') {
    p = S.crisis?.features.find((f) => f.properties.id_punto === S.sel.id)?.properties;
    if (p) el.innerHTML = detalleCrisis(p);
  } else if (S.sel.tipo === 'alertas') {
    p = { alertas: S.alertas };
    el.innerHTML = detalleAlertas();
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
  el.querySelectorAll('[data-ir-paquete]').forEach((b) => b.addEventListener('click', () => irAPaquete(b.dataset.irPaquete)));
  el.querySelectorAll('[data-ir-riesgo]').forEach((b) => b.addEventListener('click', () => seleccionar('riesgo', b.dataset.irRiesgo)));
  el.querySelector('#al-actualizar')?.addEventListener('click', actualizarAlertas);
  if (S.sel.tipo === 'municipio' && S.chirps?.municipios?.[p.codigo]) dibujarChirps(p.codigo);
  if (S.sel.tipo === 'municipio') dibujarSeguridad(p.codigo);
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
  const mes = mesIndice();
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
document.getElementById('btn-alertas').addEventListener('click', () => {
  if (S.sel?.tipo === 'alertas') cerrarDetalle();
  else abrirAlertas();
});

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


// Rios y vias pesan unos 7 MB: se descargan la primera vez que se enciende su capa
const cargando = {};
async function cargarRios() {
  if (S.rios || cargando.rios) return;
  cargando.rios = true;
  document.getElementById('sub-rios').textContent = 'Cargando…';
  const [rios, agua] = await Promise.all([ui.json('/api/capas/rios'), ui.json('/api/capas/cuerpos_agua')]);
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
  restilarAgua();
}
async function cargarVias() {
  if (S.red || cargando.vias) return;
  cargando.vias = true;
  document.getElementById('sub-vias').textContent = 'Cargando…';
  const red = await ui.json('/api/capas/red_vial');
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
}

document.querySelectorAll('.switch input[data-capa]').forEach((el) => el.addEventListener('change', () => {
  const k = el.dataset.capa;
  if (el.checked && k === 'rios') cargarRios();
  if (el.checked && k === 'vias') cargarVias();
  el.checked ? capas[k].addTo(mapa) : mapa.removeLayer(capas[k]);
  document.getElementById(`capa-${k}`).classList.toggle('off', !el.checked);
}));

// Grupo de clima: un boton despliega o recoge todas sus variables. Recogido, dice cuales siguen encendidas en el mapa.
function resumenClimaEncendido() {
  const el = document.getElementById('clima-encendidas');
  const plegado = document.getElementById('grupo-clima').classList.contains('plegado');
  const nombres = [...document.querySelectorAll('#clima-cuerpo .switch input:checked')]
    .map((i) => i.closest('.capa')?.querySelector('.t')?.firstChild?.textContent.trim()).filter(Boolean);
  el.hidden = !plegado || !nombres.length;
  el.textContent = `En el mapa: ${nombres.join(', ')}`;
}
function plegarClima(plegar) {
  const grupo = document.getElementById('grupo-clima');
  const btn = document.getElementById('clima-plegar');
  grupo.classList.toggle('plegado', plegar);
  btn.setAttribute('aria-expanded', String(!plegar));
  btn.title = plegar ? 'Desplegar las variables del clima' : 'Recoger las variables del clima';
  resumenClimaEncendido();
}
document.querySelector('#grupo-clima > .capa-head').addEventListener('click', () => {
  plegarClima(!document.getElementById('grupo-clima').classList.contains('plegado'));
});
document.getElementById('clima-cuerpo').addEventListener('change', resumenClimaEncendido);   // el grupo arranca recogido (ver mapa.html)

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
  renderCobertura();
  if (S.sel?.tipo === 'estacion' || S.sel?.tipo === 'paquete') renderDetalle();
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

(async function iniciar() {
  const [proyectos, pq, riesgos, clima, radiacion, mpios, limite, cobertura, coberturaPaq, chirps, social, resguardos, areasAp, contexto, parametros] = await Promise.all([
    ui.json('/api/capas/proyectos'), ui.json('/api/paquetes'), ui.json('/api/riesgos'), ui.json('/api/clima'), ui.json('/api/clima/radiacion'),
    ui.json('/api/capas/municipios'), ui.json('/api/capas/limite_departamental'),
    ui.json('/api/capas/cobertura_estaciones'), ui.json('/api/capas/cobertura_paquetes'), ui.json('/api/capas/lluvia_chirps'),
    ui.json('/api/capas/indicadores_municipio'), ui.json('/api/capas/resguardos'), ui.json('/api/capas/areas_protegidas_runap'),
    ui.json('/api/capas/contexto_paquetes'), ui.json('/api/parametros'),
  ]);
  const [calor, crisis, zonas, alertas] = await Promise.all([
    ui.json('/api/capas/grid_calor'), ui.json('/api/capas/puntos_crisis'), ui.json('/api/capas/zonas_intervencion'), ui.json('/api/alertas'),
  ]);
  S.calor = calor;
  S.crisis = crisis;
  S.zonas = zonas;
  S.alertas = Array.isArray(alertas) ? alertas : [];
  S.paramsIct = parametros;
  if (parametros?.umbrales_criticidad) S.umbrales = parametros.umbrales_criticidad;
  S.ram = parametros?.ram || null;
  S.chirps = chirps?.municipios ? chirps : null;
  S.social = social?.municipios ? social : null;
  S.resguardos = resguardos.features?.length ? resguardos : null;
  S.areasRunap = areasAp.features?.length ? areasAp : null;
  S.contexto = contexto?.paquetes && Object.keys(contexto.paquetes).length ? contexto : null;
  if (S.resguardos) {
    resguardosCapa.addData(resguardos);
    const pob = resguardos.features.reduce((a, f) => a + (f.properties.poblacion_2020 || 0), 0);
    document.getElementById('sub-resguardos').textContent = `${resguardos.features.length} resguardos · ${Math.round(resguardos.metadata.km2).toLocaleString('es-CO')} km² · ${Math.round(pob).toLocaleString('es-CO')} hab. (2020)`;
    document.getElementById('fuente-resguardos').innerHTML = `Fuente: Agencia Nacional de Tierras, resguardos formalizados (polígonos, recortados a La Guajira); población: Ministerio del Interior, proyección 2020. Descargado el ${ui.fecha(resguardos.metadata.descargado_en)}. Una comunidad indígena también puede estar fuera de un resguardo.`;
  } else document.getElementById('sub-resguardos').textContent = 'Sin datos: corre el pipeline (ver README)';
  if (S.areasRunap) {
    areasCapa.addData(areasAp);
    document.getElementById('sub-areas').textContent = `${areasAp.features.length} áreas · ${Math.round(areasAp.metadata.km2_en_guajira).toLocaleString('es-CO')} km² en tierra de La Guajira`;
    document.getElementById('fuente-areas').innerHTML = `Fuente: <a href="https://runap.parquesnacionales.gov.co" target="_blank" rel="noopener">RUNAP</a>, Parques Nacionales Naturales de Colombia, descargado el ${ui.fecha(areasAp.metadata.descargado_en)}. Las áreas marinas costeras se muestran completas.`;
  } else document.getElementById('sub-areas').textContent = 'Sin datos: corre el pipeline (ver README)';
  if (S.social) renderOpcionesSocial();
  else document.getElementById('sub-social').textContent = 'Sin datos: corre el pipeline (ver README)';
  document.querySelector('input[data-capa="social"]').addEventListener('change', (e) => {
    if (e.target.checked && indicadorSocial()?.temporal && S.tiempo.modo !== 'mensual') cambiarModoTiempo('mensual');
  });
  S.cobertura = cobertura.features?.length ? cobertura : null;
  S.coberturaPaq = coberturaPaq.paquetes ? coberturaPaq : null;
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
  document.getElementById('sub-rios').textContent = 'Se carga al encenderla (unos 4 MB)';
  document.getElementById('sub-vias').textContent = 'Se carga al encenderla (unos 3 MB)';
  S.paquetes = pq;
  S.riesgos = riesgos.features;
  S.clima = clima;
  S.radiacion = radiacion;

  limitesProyecto.addData(proyectos);
  paquetes.addData(pq);
  etiquetarProyectos();
  renderLeyendaPaquetes();
  const nEsc = pq.features.filter((f) => f.properties.escalamiento).length;
  document.getElementById('sub-proyectos').textContent = `${proyectos.features.length} proyectos · ${pq.features.length} paquetes · ${nEsc} en escalamiento`;

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
  renderCalor();
  renderCrisis();
  renderBotonAlertas();
  renderTarjetasClima();
  renderClima();
  renderControlesCobertura();
  renderCobertura();
  renderChirps();
  renderSocial();
  renderBarraTiempo();
  if (!S.chirps) document.getElementById('sub-chirps').textContent = 'Sin datos: corre el pipeline (ver README)';
  if (!S.cobertura) document.getElementById('sub-cobertura').textContent = 'Sin datos: corre el pipeline (ver README)';
  renderEstadoVivo();
  encuadrar();
  etiquetasPorZoom();
  ui.icons();

  cargarAhora();
  setInterval(() => cargarAhora(), 10 * 60 * 1000);
})();
