/* Flujo de la aplicacion: de la fuente al tablero.
   Lo que cambia con cada corrida (pasos, dependencias, fechas, licencias, auditoria, pruebas, versiones) viene de
   /api/flujo, /api/parametros y /api/alertas/estado; aqui solo vive el texto que explica cada pieza. */
(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fechaHora = (iso) => (iso ? new Date(iso).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-');
  const S = { pasos: [], por: {}, hijos: {}, sel: null, versiones: {} };

  // ---- Nombres legibles de cada fuente del pipeline -------------------------------------------------------------
  const FUENTE = {
    sinteticos: ['Registro de riesgos', 'file-spreadsheet'],
    ideam: ['Clima IDEAM', 'cloud-rain'],
    chirps: ['Lluvia CHIRPS', 'satellite'],
    municipios: ['Municipios DANE', 'map'],
    social: ['Censo, agua y PDET', 'users'],
    resguardos: ['Resguardos ANT', 'tent'],
    runap: ['Áreas protegidas', 'trees'],
    seguridad: ['Delitos MinDefensa', 'shield-alert'],
    emergencias: ['Emergencias UNGRD', 'siren'],
    invias: ['Vías INVIAS', 'route'],
    vias_igac: ['Vías IGAC', 'signpost'],
    red_vial: ['Red vial unificada', 'git-merge'],
    hidrografia: ['Ríos IGAC', 'waves'],
    ict: ['ICT, crisis y alertas', 'radar'],
    validacion: ['Validación del modelo', 'scale'],
    contexto: ['Contexto territorial', 'map-pinned'],
    cronograma: ['Cronograma y avance', 'calendar-range'],
    ejecucion: ['Riesgo de ejecución', 'timer'],
    cobertura: ['Cobertura de estaciones', 'circle-dot'],
    indicadores: ['Indicadores municipales', 'chart-column'],
    territorios: ['Capas de territorio', 'layers'],
    gis: ['GeoPackage y GeoJSON', 'package'],
    alertas: ['Boletín diario', 'bell-ring'],
  };
  const nombre = (p) => (FUENTE[p.fuente] || [p.fuente])[0];
  const icono = (p) => (FUENTE[p.fuente] || [, 'circle'])[1];
  const ORDEN = ['sinteticos', 'ict', 'validacion', 'contexto', 'cronograma', 'ejecucion', 'alertas', 'ideam', 'cobertura', 'chirps',
    'municipios', 'social', 'indicadores', 'resguardos', 'runap', 'territorios', 'seguridad', 'emergencias', 'invias',
    'vias_igac', 'red_vial', 'hidrografia', 'gis'];
  const CAPAS = [['bronce', 'Bronce', 'Extracción'], ['plata', 'Plata', 'Limpieza'], ['oro', 'Oro', 'Modelos'], ['consumo', 'Consumo', 'Salidas']];

  // ---- Seis etapas del recorrido ---------------------------------------------------------------------------------
  const ETAPAS = [
    {
      tono: 'origen', icon: 'satellite-dish', nombre: 'Fuentes', titulo: 'Origen de los datos',
      cifra: () => '12 <small>entidades + registro</small>',
      hace: [
        'Registro de riesgos en Excel con texto libre, proyectos, paquetes y actividades con fechas y avance (sintéticos, sucios a propósito)',
        'Territorio real: clima, lluvia satelital, censo, resguardos, áreas protegidas, vías, ríos, delitos y emergencias',
        'Datos abiertos oficiales, sin claves ni registro',
      ],
      con: ['API Socrata · datos.gov.co', 'ArcGIS REST', 'GeoTIFF COG', 'Excel / CSV'],
      sale: ['.xlsx', '.csv', '.geojson', '.tif'],
      prod: 'Las mismas fuentes, más el registro real, la Geodatabase y las capas ArcGIS de Ecopetrol',
    },
    {
      tono: 'bronce', icon: 'download', nombre: 'Bronce', titulo: 'Extracción',
      cifra: (c) => `${c?.bronce ?? '–'} <small>pasos</small>`,
      hace: [
        'Descarga con reintentos, paginación y tiempos de espera (cliente HTTP propio)',
        'Recorta a la caja de La Guajira con margen',
        'Guarda tal como llega, sin transformar: el origen siempre se puede reconstruir',
        'Deja un <span class="mono">*_meta.json</span> con fuente, licencia, servicio y fecha',
      ],
      con: ['Python 3.12', 'urllib', 'rasterio', 'openpyxl'],
      sale: ['data/bronze', '*_meta.json'],
      prod: 'Azure Data Factory programa la ingesta hacia Azure Data Lake Storage Gen2',
    },
    {
      tono: 'plata', icon: 'eraser', nombre: 'Plata', titulo: 'Limpieza y conformación',
      cifra: (c) => `${c?.plata ?? '–'} <small>pasos</small>`,
      hace: [
        'Quita duplicados, nulos e imposibles; unifica unidades, fechas y códigos DANE',
        'Coordenadas en EPSG:4326; distancias y áreas en EPSG:3116 (metros); geometrías reparadas y recortadas',
        'IA sobre el texto del registro y calificación con la matriz RAM de Ecopetrol',
        'Reporte de calidad y proveniencia por fuente',
      ],
      con: ['pandas', 'GeoPandas', 'Shapely', 'pyproj', 'NumPy'],
      sale: ['Parquet', 'GeoJSON', 'reporte_calidad_*.csv', 'proveniencia_*.json'],
      prod: 'Azure Databricks con tablas Delta en la capa Plata',
    },
    {
      tono: 'oro', icon: 'sigma', nombre: 'Oro', titulo: 'Modelos y productos',
      cifra: (c) => `${c?.oro ?? '–'} <small>pasos</small>`,
      hace: [
        'Índice de Criticidad Territorial por paquete y por celda de 2 km',
        'Escalamiento a crisis, puntos de crisis y zonas de intervención',
        'Mapa de calor: densidad kernel y puntos calientes Getis-Ord Gi*',
        'Avance y fechas proyectadas de cada proyecto desde sus actividades',
        'Alertas, riesgo de ejecución (Monte Carlo) y validación',
      ],
      con: ['NumPy', 'SciPy', 'GeoPandas'],
      sale: ['paquetes_ict', 'grid_calor', 'puntos_crisis', 'alertas.json', 'cronograma_*', 'ejecucion_*'],
      prod: 'Azure Databricks con Apache Sedona para los cruces espaciales distribuidos',
    },
    {
      tono: 'servicio', icon: 'server', nombre: 'Servicio', titulo: 'API y tareas programadas',
      cifra: () => 'REST <small>API</small>',
      hace: [
        'Sirve la capa Oro como API REST para el tablero y otras herramientas',
        'Recalcula el ICT en memoria al ajustar parámetros, con vista previa antes de guardar',
        'Tarea diaria a las 06:00 y lectura del IDEAM en vivo',
        'Edición protegida con clave; parámetros versionados',
      ],
      con: ['FastAPI', 'uvicorn', 'Starlette', 'PyYAML'],
      sale: ['/api/paquetes', '/api/alertas', '/api/capas/{capa}', '/api/flujo'],
      prod: 'Red privada sin exposición directa; publicación por Azure Front Door + WAF',
    },
    {
      tono: 'consumo', icon: 'layout-dashboard', nombre: 'Consumo', titulo: 'Tablero y salidas',
      cifra: () => '8 <small>vistas</small>',
      hace: [
        'Tablero web para gerentes, líderes de proyecto y equipos técnicos',
        'GeoPackage y GeoJSON, listos para ArcGIS o QGIS',
        'Boletín diario en HTML y Markdown',
        'Avisos por Microsoft Teams o correo',
      ],
      con: ['Leaflet 1.9.4', 'Chart.js 4.4.4', 'Lucide', 'HTML/CSS/JS'],
      sale: ['mapa.html', 'exports/*.gpkg', 'boletin_*.html'],
      prod: 'ArcGIS Enterprise o Power BI si Ecopetrol los licencia; Teams y correo corporativos',
    },
  ];

  function pintarRecorrido(capas) {
    $('#riel').innerHTML = ETAPAS.map((e, i) => `
      <button class="riel-nodo ${e.tono}" data-i="${i}" title="${esc(e.titulo)}">
        <span class="riel-ic"><i data-lucide="${e.icon}"></i></span>
        <span class="riel-t">${e.nombre}</span>
      </button>`).join('<span class="riel-flecha" aria-hidden="true"><i data-lucide="arrow-right"></i></span>');
    $('#etapas').innerHTML = ETAPAS.map((e, i) => `
      <article class="etapa ${e.tono}" id="etapa-${i}">
        <div class="et-top">
          <span class="et-num">${i + 1}</span>
          <span class="et-ic"><i data-lucide="${e.icon}"></i></span>
          <div class="grow"><div class="et-capa">${e.nombre}</div><h3>${e.titulo}</h3></div>
          <div class="et-cifra num">${e.cifra(capas)}</div>
        </div>
        <ul>${e.hace.map((h) => `<li>${h}</li>`).join('')}</ul>
        <div class="et-bloque"><span class="et-k">Con</span><div class="chips">${e.con.map((t) => `<span class="chip white">${esc(t)}</span>`).join('')}</div></div>
        <div class="et-bloque"><span class="et-k">Entrega</span><div class="chips">${e.sale.map((t) => `<span class="chip mono-chip">${esc(t)}</span>`).join('')}</div></div>
        <div class="et-prod"><i data-lucide="cloud"></i><span><b>En producción:</b> ${esc(e.prod)}</span></div>
      </article>`).join('');
    document.querySelectorAll('.riel-nodo').forEach((b) => b.addEventListener('click', () => {
      const el = $(`#etapa-${b.dataset.i}`);
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.remove('destello'); void el.offsetWidth; el.classList.add('destello');
    }));
  }

  // ---- Grafo del pipeline ----------------------------------------------------------------------------------------
  function prepararGrafo(pasos) {
    S.pasos = pasos;
    S.por = Object.fromEntries(pasos.map((p) => [p.id, p]));
    S.hijos = Object.fromEntries(pasos.map((p) => [p.id, []]));
    pasos.forEach((p) => p.depende_de.forEach((d) => S.hijos[d] && S.hijos[d].push(p.id)));
  }

  const cerrar = (id, vecinos) => {
    const vistos = new Set();
    const pila = [...vecinos(id)];
    while (pila.length) { const x = pila.pop(); if (!vistos.has(x)) { vistos.add(x); pila.push(...vecinos(x)); } }
    return vistos;
  };
  const ancestros = (id) => cerrar(id, (x) => S.por[x]?.depende_de || []);
  const descendientes = (id) => cerrar(id, (x) => S.hijos[x] || []);

  function pintarGrafo() {
    const pos = (p) => { const i = ORDEN.indexOf(p.fuente); return i < 0 ? 99 : i; };
    $('#dag-cols').innerHTML = CAPAS.map(([capa, medal, rol]) => {
      const lista = S.pasos.filter((p) => p.capa === capa).sort((a, b) => pos(a) - pos(b));
      return `<div class="dag-col">
        <div class="dag-col-h"><span class="medal ${capa === 'consumo' ? 'consumo' : capa}">${medal}</span><span class="muted">${rol} · ${lista.length}</span></div>
        ${lista.map((p) => `
          <button class="nodo" data-id="${p.id}" title="${esc(p.descripcion)}">
            <span class="tile n-ic"><i data-lucide="${icono(p)}"></i></span>
            <span class="n-tx"><span class="n-t">${esc(nombre(p))}</span><span class="n-id mono">${p.id}</span></span>
            ${p.requiere_red ? '<span class="ld red" title="Descarga de internet"></span>' : ''}
            ${p.obligatorio ? '<span class="ld obl" title="Obligatorio: si falla, el pipeline se detiene"></span>' : ''}
          </button>`).join('')}
      </div>`;
    }).join('');
    document.querySelectorAll('.nodo').forEach((n) => n.addEventListener('click', () => seleccionar(n.dataset.id)));
  }

  function dibujarAristas() {
    const svg = $('#dag-svg');
    const dag = $('#dag');
    if (window.matchMedia('(max-width: 760px)').matches) { svg.innerHTML = ''; return; }
    const caja = dag.getBoundingClientRect();
    svg.setAttribute('viewBox', `0 0 ${caja.width} ${caja.height}`);
    svg.setAttribute('width', caja.width);
    svg.setAttribute('height', caja.height);
    const col = Object.fromEntries(CAPAS.map(([c], i) => [c, i]));
    const caminos = [];
    S.pasos.forEach((p) => p.depende_de.forEach((d) => {
      const a = dag.querySelector(`.nodo[data-id="${d}"]`)?.getBoundingClientRect();
      const b = dag.querySelector(`.nodo[data-id="${p.id}"]`)?.getBoundingClientRect();
      if (!a || !b) return;
      const y1 = a.top + a.height / 2 - caja.top, y2 = b.top + b.height / 2 - caja.top;
      let dpath;
      if (col[S.por[d].capa] < col[p.capa]) {
        const x1 = a.right - caja.left, x2 = b.left - caja.left, dx = (x2 - x1) / 2;
        dpath = `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
      } else {
        // dependencia dentro de la misma capa (p. ej. municipios -> vias_igac): arco por la izquierda
        const x1 = a.left - caja.left, x2 = b.left - caja.left, off = 16 + Math.min(30, Math.abs(y2 - y1) / 10);
        dpath = `M${x1},${y1} C${x1 - off},${y1} ${x2 - off},${y2} ${x2},${y2}`;
      }
      caminos.push(`<path class="arista" data-a="${d}" data-b="${p.id}" d="${dpath}"/>`);
    }));
    svg.innerHTML = caminos.join('');
    marcarSeleccion();
  }

  function marcarSeleccion() {
    const id = S.sel;
    if (!id) return;
    const arriba = ancestros(id), abajo = descendientes(id);
    document.querySelectorAll('.nodo').forEach((n) => {
      const x = n.dataset.id;
      n.classList.toggle('sel', x === id);
      n.classList.toggle('arriba', arriba.has(x));
      n.classList.toggle('abajo', abajo.has(x));
      n.classList.toggle('tenue', x !== id && !arriba.has(x) && !abajo.has(x));
    });
    const linaArriba = new Set([...arriba, id]), linaAbajo = new Set([...abajo, id]);
    document.querySelectorAll('.arista').forEach((e) => {
      const { a, b } = e.dataset;
      const up = linaArriba.has(a) && linaArriba.has(b);
      const down = linaAbajo.has(a) && linaAbajo.has(b);
      e.classList.toggle('on-arriba', up);
      e.classList.toggle('on-abajo', down && !up);
      e.classList.toggle('tenue', !up && !down);
    });
  }

  function seleccionar(id) {
    if (!S.por[id]) return;
    S.sel = id;
    marcarSeleccion();
    const p = S.por[id];
    const arriba = ancestros(id), abajo = descendientes(id);
    const fuentesArriba = [...arriba].filter((x) => S.por[x].capa === 'bronce').length + (p.capa === 'bronce' ? 1 : 0);
    const enlace = (x) => `<button class="chip white enlace" data-id="${x}"><i data-lucide="${icono(S.por[x])}"></i>${esc(nombre(S.por[x]))}</button>`;
    $('#dag-detalle').innerHTML = `
      <div class="dd-top">
        <span class="medal ${p.capa === 'consumo' ? 'consumo' : p.capa}">${CAPAS.find(([c]) => c === p.capa)[1]}</span>
        ${p.requiere_red ? '<span class="chip"><i data-lucide="globe"></i>Descarga de internet</span>' : '<span class="chip"><i data-lucide="hard-drive"></i>Local</span>'}
        ${p.obligatorio ? '<span class="chip warn"><i data-lucide="lock"></i>Obligatorio</span>' : ''}
      </div>
      <h3>${esc(nombre(p))}</h3>
      <div class="mono muted dd-id">${p.id}</div>
      <p class="dd-desc">${esc(p.descripcion)}</p>
      <div class="kv"><span class="k">Última salida</span><span class="v">${fechaHora(p.actualizado)}</span></div>
      <div class="kv"><span class="k">Archivos que escribe</span><span class="v">${p.archivos} · ${ui.num(p.megabytes, 1)} MB</span></div>
      <div class="kv"><span class="k">Cómo correrlo solo</span><span class="v mono">${p.comando}</span></div>
      <div class="kv"><span class="k">Linaje</span><span class="v">${fuentesArriba} fuente${fuentesArriba === 1 ? '' : 's'} · alimenta ${abajo.size} paso${abajo.size === 1 ? '' : 's'}</span></div>
      <div class="dd-sub"><span class="ld-arriba"></span>Lee de</div>
      <div class="chips">${p.depende_de.length ? p.depende_de.map(enlace).join('') : '<span class="muted dd-vacio">Nada del pipeline: es el origen</span>'}</div>
      <div class="dd-sub"><span class="ld-abajo"></span>Entrega a</div>
      <div class="chips">${(S.hijos[id] || []).length ? S.hijos[id].map(enlace).join('') : '<span class="muted dd-vacio">Nadie: es una salida final</span>'}</div>
      <div class="dd-sub">Artefactos que escribe</div>
      <div class="chips">${p.escribe.map((a) => `<span class="chip mono-chip">${esc(a)}</span>`).join('')}</div>`;
    $('#dag-detalle').querySelectorAll('.enlace').forEach((b) => b.addEventListener('click', () => seleccionar(b.dataset.id)));
    ui.icons();
  }

  // ---- Fuentes ---------------------------------------------------------------------------------------------------
  const FUENTES = [
    { id: 'ideam', ent: 'IDEAM', t: 'Clima en estaciones', q: 'Lluvia, temperatura, viento, humedad del aire y del suelo, presión, nivel del río y radiación; normales climatológicas', f: 'API Socrata · datos.gov.co', p: 'Últimos 30 días, lecturas de 10 min, y en vivo', ic: 'cloud-rain' },
    { id: 'chirps', ent: 'UC Santa Barbara (CHC)', t: 'Lluvia por satélite CHIRPS v3', q: 'Lluvia mensual en celdas de ~5 km, para medir la anomalía frente a lo normal', f: 'GeoTIFF optimizado (COG)', p: 'Mensual desde 1991', ic: 'satellite' },
    { id: 'municipios', ent: 'DANE', t: 'Municipios (MGN 2024) y DIVIPOLA', q: 'Límites y códigos de los 15 municipios; la llave que une todo lo demás', f: 'ArcGIS REST · geoportal DANE', p: 'Vigente', ic: 'map' },
    { id: 'social', ent: 'DANE · INS · ART', t: 'Censo 2018, agua potable y PDET', q: 'Pobreza (IPM, NBI), población étnica, calidad del agua (IRCA) y municipios PDET', f: 'CSV · datos.gov.co', p: 'Censo 2018; IRCA anual', ic: 'users' },
    { id: 'resguardos', ent: 'ANT · Ministerio del Interior', t: 'Resguardos indígenas', q: 'Polígonos formalizados y su población', f: 'ArcGIS REST · ANT', p: 'Vigente; población 2020', ic: 'tent' },
    { id: 'runap', ent: 'Parques Nacionales', t: 'Áreas protegidas (RUNAP)', q: 'Áreas que tocan La Guajira, con ámbito y categoría', f: 'ArcGIS REST · RUNAP', p: 'Vigente', ic: 'trees' },
    { id: 'invias', ent: 'INVIAS', t: 'Red vial nacional', q: 'Rutas nacionales y su superficie', f: 'API Socrata · datos.gov.co', p: 'Vigente', ic: 'route' },
    { id: 'vias_igac', ent: 'IGAC', t: 'Red vial 1:100.000', q: 'Vías, superficie y accesibilidad: todo el año o solo en tiempo seco', f: 'ArcGIS REST · servicio del IDEAM', p: 'Cartografía básica', ic: 'signpost' },
    { id: 'hidrografia', ent: 'IGAC', t: 'Hidrografía 1:100.000', q: 'Ríos, ciénagas, lagunas y embalses', f: 'ArcGIS REST · servicio del IDEAM', p: 'Cartografía básica', ic: 'waves' },
    { id: 'seguridad', ent: 'Ministerio de Defensa', t: 'Delitos por municipio', q: '11 delitos: homicidio, extorsión, secuestro, terrorismo, voladuras, piratería terrestre y otros', f: 'API Socrata · datos.gov.co', p: 'Mensual desde 2003', ic: 'shield-alert' },
    { id: 'emergencias', ent: 'UNGRD', t: 'Emergencias atendidas', q: 'Eventos y afectación por municipio', f: 'API Socrata · datos.gov.co', p: '2019, 2020 y 2023 en adelante', ic: 'siren' },
    { id: 'sinteticos', ent: 'Generador propio · semilla 42', t: 'Registro de riesgos y proyectos', q: 'Riesgos con texto libre, RAM, estado y coordenadas; 3 proyectos, 14 paquetes y 84 actividades con fechas planeadas y proyectadas. Sucio a propósito', f: 'Excel y CSV', p: 'Mismas cifras con la misma semilla; las fechas se cuentan desde el día de la corrida', ic: 'file-spreadsheet', sintetico: true },
  ];

  function pintarFuentes(meta) {
    $('#grid-fuentes').innerHTML = FUENTES.map((f) => {
      const m = meta[f.id] || {};
      return `<article class="fuente ${f.sintetico ? 'sint' : ''}">
        <div class="f-top">
          <span class="tile"><i data-lucide="${f.ic}"></i></span>
          <div class="grow"><div class="f-ent">${esc(f.ent)}</div><div class="f-t">${esc(f.t)}</div></div>
          <span class="chip ${f.sintetico ? 'warn' : 'ok'}">${f.sintetico ? 'Sintético' : 'Real'}</span>
        </div>
        <p class="f-q">${esc(f.q)}</p>
        <div class="f-kv"><span>Cómo llega</span><b>${esc(f.f)}</b></div>
        <div class="f-kv"><span>Periodo</span><b>${esc(f.p)}</b></div>
        ${f.sintetico ? '' : `<div class="f-kv"><span>Licencia</span><b>${esc(m.licencia || '-')}</b></div>
        <div class="f-kv"><span>Descargado</span><b>${fechaHora(m.descargado_en)}</b></div>`}
        <button class="btn btn-outline sm f-ver" data-id="bronce.${f.id}"><i data-lucide="git-fork"></i> Ver su recorrido</button>
      </article>`;
    }).join('');
    document.querySelectorAll('.f-ver').forEach((b) => b.addEventListener('click', () => irAlPaso(b.dataset.id)));
  }

  function irAlPaso(id) {
    seleccionar(id);
    $('#pipeline').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ---- Modelos ---------------------------------------------------------------------------------------------------
  function modelos(params) {
    const w = params?.pesos || {};
    const pct = (k) => (w[k] != null ? `${Math.round(w[k] * 100)} %` : '');
    return [
      {
        ic: 'grid-3x3', t: 'Matriz RAM de Ecopetrol', s: 'Calificación de cada riesgo', paso: 'plata.sinteticos', span: 4,
        entra: ['Consecuencia por dimensión', 'Probabilidad (escrita de varias formas)', 'Controles'],
        como: 'Consecuencia 0-5 en Personas, Económica, Ambiental, Clientes e Imagen × probabilidad A-E. El cruce da N, L, M, H o VH y manda la peor dimensión. Inherente y residual.',
        sale: ['nivel_ram_residual', 'decisión y quién decide'], tec: ['parametros.yaml', 'pandas'],
      },
      {
        ic: 'brain', t: 'IA sobre el texto del registro', s: 'Clasificador explicable', paso: 'plata.sinteticos', span: 4,
        entra: ['Descripción, causa y acción en texto libre', 'Categorías existentes', 'Nombres de municipios'],
        como: 'Bayes ingenuo multinomial con palabras y pares de palabras, suavizado de Laplace. Completa la categoría (confianza ≥ 0,6), marca contradicciones (≥ 0,8) y ubicaciones a más de 15 km.',
        sale: ['categoria_ia', 'confianza_ia', 'palabras_ia', 'revisar_*'], tec: ['NumPy', 'validación cruzada'],
      },
      {
        ic: 'radar', t: 'Índice de Criticidad Territorial', s: 'ICT = 100 × Σ wₖ · Cₖ', paso: 'oro.ict', span: 4, verde: true,
        entra: ['Riesgos con RAM y estado', 'Territorio real (ANT, DANE, RUNAP, vías)', 'IDEAM, CHIRPS, UNGRD, MinDefensa'],
        como: `Cinco criterios en escala fija 0-1: severidad ${pct('severidad_riesgo')}, exposición ${pct('exposicion_proyecto')}, vulnerabilidad ${pct('vulnerabilidad_territorial')}, amenazas externas ${pct('amenazas_externas')} y convergencia ${pct('convergencia')}. Alcance espacial que decae con la distancia; lo que falta no se imputa: lo mide el índice de confianza.`,
        sale: ['paquetes_ict', 'aporte por criterio', 'indice_confianza'], tec: ['GeoPandas', 'NumPy'],
      },
      {
        ic: 'triangle-alert', t: 'Escalamiento a crisis', s: 'Dónde un riesgo podría escalar', paso: 'oro.ict', span: 4,
        entra: ['ICT y RAM', 'Ruta crítica', 'Resguardos y áreas protegidas reales', 'Acciones vencidas'],
        como: 'Seis reglas configurables (ICT crítico, RAM VH, H en ruta crítica, área sensible, convergencia, acciones vencidas). Cada punto trae causa, decisión de la RAM y responsable; la zona es la unión de las áreas de influencia.',
        sale: ['puntos_crisis', 'zonas_intervencion'], tec: ['GeoPandas', 'Shapely'],
      },
      {
        ic: 'flame', t: 'Mapa de calor', s: 'Multicriterio y estadística espacial', paso: 'oro.ict', span: 4,
        entra: ['Amenazas ponderadas por RAM y estado', 'Oportunidades', 'Grilla de 0,02° (~2 km)'],
        como: 'ICT en cada celda; densidad kernel gaussiana (banda de 4 km) de amenazas y de oportunidades; Getis-Ord Gi* con 8 vecinas: z ≥ 1,96 es un conglomerado significativo al 95 %.',
        sale: ['grid_calor'], tec: ['NumPy', 'EPSG:3116'],
      },
      {
        ic: 'bell-ring', t: 'Alertas y tendencia', s: 'Qué cambió y qué hacer', paso: 'consumo.alertas', span: 4,
        entra: ['ICT de hoy y de hace 7 días', 'Reglas activas', 'Corte anterior'],
        como: 'Una alerta por paquete en escalamiento o al alza (+10 puntos en 7 días), con prioridad, causas y acciones. Se compara con el corte anterior: nuevas, suben, siguen y resueltas.',
        sale: ['alertas.json', 'boletín HTML/MD', 'Teams · correo'], tec: ['smtplib', 'Adaptive Cards'],
      },
      {
        ic: 'timer', t: 'Riesgo de ejecución', s: 'Del riesgo a días y dólares', paso: 'oro.ejecucion', span: 6,
        entra: ['RAM residual y estado', 'Cronograma: holgura y costo diario', 'Territorio real'],
        como: 'Frecuencia por letra RAM × multiplicador territorial; Poisson con choque común Gamma (clima y social); duración triangular; solapamiento de eventos α = 0,5; 10.000 escenarios. IRE = probabilidad de que el atraso pase la holgura.',
        sale: ['P50 · P80 · P90 de atraso y costo', 'IRE', 'aporte por amenaza'], tec: ['NumPy'],
      },
      {
        ic: 'scale', t: 'Validación y gobierno del modelo', s: 'Robustez y control de cambios', paso: 'oro.validacion', span: 6,
        entra: ['Parámetros vigentes', 'ICT', 'Riesgos materializados'],
        como: 'Sensibilidad: cada peso ±20 % y correlación del ranking (Spearman). Pesos derivables con AHP (razón de consistencia ≤ 0,10). Cada cambio queda versionado con autor, fecha y motivo.',
        sale: ['validacion_*.csv', 'historial_parametros.jsonl'], tec: ['SciPy', 'AHP'],
      },
    ];
  }

  function pintarModelos(params) {
    $('#grid-modelos').innerHTML = modelos(params).map((m) => `
      <section class="card span-${m.span} modelo ${m.verde ? 'card-green' : ''}">
        <div class="card-head">
          ${m.verde ? '' : `<div class="card-icon"><i data-lucide="${m.ic}"></i></div>`}
          <div class="grow"><div class="card-title">${m.t}</div><div class="card-sub">${m.s}</div></div>
          ${m.verde ? `<span class="icon-btn glass"><i data-lucide="${m.ic}"></i></span>` : ''}
        </div>
        <div class="m-fila"><span class="m-k">Entra</span><div class="chips">${m.entra.map((t) => `<span class="chip ${m.verde ? 'glass-chip' : 'white'}">${esc(t)}</span>`).join('')}</div></div>
        <p class="m-como">${m.como}</p>
        <div class="m-fila"><span class="m-k">Sale</span><div class="chips">${m.sale.map((t) => `<span class="chip ${m.verde ? 'glass-chip' : 'mono-chip'}">${esc(t)}</span>`).join('')}</div></div>
        <div class="m-pie">
          <span class="muted">${m.tec.map(esc).join(' · ')}</span>
          <button class="chip ${m.verde ? 'glass-chip' : 'outline'} m-paso" data-id="${m.paso}"><i data-lucide="git-fork"></i>${m.paso}</button>
        </div>
      </section>`).join('');
    document.querySelectorAll('.m-paso').forEach((b) => b.addEventListener('click', () => irAlPaso(b.dataset.id)));
  }

  // ---- Ciclo diario ----------------------------------------------------------------------------------------------
  function pintarCiclo(estado) {
    const pasos = [
      ['alarm-clock', '06:00', 'Se dispara', 'La aplicación la programa sola, o el Programador de tareas con alertas_diarias.py'],
      ['cloud-download', 'bronce.ideam', 'Descarga', 'Lluvia y clima de los últimos 30 días del IDEAM'],
      ['eraser', 'plata.ideam', 'Limpia', 'Sensores, duplicados, unidades y lluvia por día'],
      ['radar', 'oro.ict', 'Recalcula', 'ICT, escalamiento, crisis, calor y alertas'],
      ['git-compare', 'consumo.alertas', 'Compara', 'Nuevas, suben, siguen y resueltas frente a ayer'],
      ['send', 'Teams · correo', 'Avisa', 'Solo si hay novedades; el boletín queda siempre en archivo'],
    ];
    $('#ciclo-pasos').innerHTML = pasos.map(([ic, cod, t, s], i) => `
      <div class="c-paso">
        <span class="c-ic"><i data-lucide="${ic}"></i></span>
        <div class="c-t">${i + 1}. ${t}</div>
        <div class="c-cod mono">${esc(cod)}</div>
        <div class="c-s">${s}</div>
      </div>`).join('');
    const prog = estado?.programada;
    if (!estado) {
      $('#ciclo-estado').innerHTML = '<span class="dot"></span> Estado no disponible';
      $('#ciclo-pie').innerHTML = '<span class="muted">El servidor no respondió con el estado de la tarea diaria.</span>';
      return;
    }
    $('#ciclo-estado').innerHTML = prog?.activa
      ? `<span class="dot bajo"></span> Programada a las ${esc(prog.hora || '06:00')}`
      : `<span class="dot"></span> Programación apagada en este servidor`;
    if (prog && !prog.activa) $('#ciclo-estado').title = prog.motivo || '';
    const u = estado?.ultima;
    if (!u) { $('#ciclo-pie').innerHTML = '<span class="muted">Todavía no se ha corrido la tarea diaria.</span>'; return; }
    const envios = (u.envios || []).map((e) => `${e.canal} ${e.estado === 'ok' ? '✓' : '✗'}`).join(' · ') || 'sin envíos';
    const nov = estado?.novedades;
    $('#ciclo-pie').innerHTML = `
      <span><b>Última corrida</b> ${fechaHora(u.inicio)} → ${fechaHora(u.fin)} (${esc(u.origen)})</span>
      <span>${(u.pasos || []).length} pasos · ${(u.fallos || []).length ? `<b class="mal">${u.fallos.length} con falla</b>` : 'sin fallas'}</span>
      <span>Envíos: ${esc(envios)}</span>
      ${nov ? `<span>${nov.total} alertas · ${nov.nuevas.length} nuevas, ${nov.suben.length} suben, ${nov.resueltas.length} resueltas</span>` : ''}
      <a class="btn btn-outline sm" href="/api/alertas/boletin" target="_blank" rel="noopener"><i data-lucide="file-text"></i> Ver boletín</a>`;
  }

  // ---- Tecnologias -----------------------------------------------------------------------------------------------
  function pintarTecnologias(v) {
    const grupos = [
      ['code', 'Lenguaje y entorno', [['Python', '3.12'], ['entorno virtual (.venv)'], ['iniciar.py: instala, descarga, corre y abre']]],
      ['table', 'Datos tabulares', [['pandas', v.pandas], ['NumPy', v.numpy], ['PyArrow (Parquet)', v.pyarrow], ['openpyxl (Excel)', v.openpyxl]]],
      ['map', 'Geoespacial', [['GeoPandas', v.geopandas], ['Shapely', v.shapely], ['pyproj', v.pyproj], ['pyogrio', v.pyogrio], ['Fiona', v.fiona]]],
      ['satellite', 'Raster', [['rasterio', v.rasterio], ['GeoTIFF optimizado (COG)']]],
      ['sigma', 'Estadística y modelos', [['SciPy', v.scipy], ['KDE, Gi*, Monte Carlo, AHP y Bayes propios en NumPy']]],
      ['server', 'API y servidor', [['FastAPI', v.fastapi], ['Starlette', v.starlette], ['uvicorn', v.uvicorn], ['Pydantic', v.pydantic]]],
      ['layout-dashboard', 'Interfaz web', [['Leaflet', '1.9.4'], ['Chart.js', '4.4.4'], ['Lucide', '0.460.0'], ['Outfit + Inter'], ['HTML, CSS y JS sin compilación']]],
      ['globe', 'Mapas base', [['Esri World Imagery'], ['OpenStreetMap'], ['sin claves']]],
      ['settings-2', 'Configuración', [['PyYAML', v.pyyaml], ['parametros.yaml + capas personalizadas versionadas']]],
      ['flask-conical', 'Pruebas y auditoría', [['pytest', v.pytest], ['auditoria.py: reglas, linaje y conciliación']]],
      ['file-json', 'Formatos abiertos', [['GeoJSON'], ['Parquet'], ['GeoTIFF'], ['GeoPackage'], ['CSV · JSON']]],
      ['send', 'Notificaciones', [['Microsoft Teams (webhook, Adaptive Card)'], ['Correo SMTP con STARTTLS']]],
    ];
    $('#grid-tec').innerHTML = grupos.map(([ic, t, items]) => `
      <div class="tec">
        <div class="tec-h"><span class="tile"><i data-lucide="${ic}"></i></span><b>${t}</b></div>
        <div class="chips">${items.map(([n, ve]) => `<span class="chip white">${esc(n)}${ve ? `<span class="t-v">${esc(ve)}</span>` : ''}</span>`).join('')}</div>
      </div>`).join('');
  }

  // ---- Calidad, trazabilidad y seguridad -------------------------------------------------------------------------
  const GRUPOS_AUD = {
    reglas: ['Reglas entre capas', 'Nadie lee lo que no le toca; solo Bronce sale a internet'],
    artefactos: ['Artefactos', 'Cada archivo existe, se lee, está en EPSG:4326, con geometrías válidas y sin NaN'],
    trazabilidad: ['Trazabilidad', 'Cada producto dice su fuente, licencia y fecha de descarga'],
    conciliacion: ['Conciliación', 'Las cuentas cuadran entre capas; el ICT es la suma de sus aportes'],
    geografia: ['Geografía', 'Todo lo inventado cae dentro de La Guajira y en tierra firme'],
    huerfanos: ['Huérfanos', 'No sobran archivos de versiones anteriores'],
  };

  function pintarCalidad(aud, pruebas, mensaje) {
    if (mensaje) {
      $('#auditoria').innerHTML = `<p class="muted">${mensaje}</p>`;
    } else if (!aud) {
      $('#auditoria').innerHTML = '<p class="muted">Aún no hay auditoría: corre <span class="mono">python ejecutar_pipeline.py --auditar</span>.</p>';
    } else {
      $('#aud-sub').textContent = `Última auditoría: ${fechaHora(aud.fecha)} · ${aud.total} comprobaciones`;
      $('#auditoria').innerHTML = Object.entries(GRUPOS_AUD).map(([g, [t, s]]) => {
        const c = aud.por_grupo[g] || {};
        const total = Object.values(c).reduce((a, b) => a + b, 0);
        const ok = c.OK || 0, malos = total - ok;
        return `<div class="aud">
          <div class="aud-h"><b>${t}</b><span class="${malos ? 'mal' : 'bien'}">${ok}/${total}</span></div>
          <div class="meter"><span style="width:${total ? (ok / total) * 100 : 0}%"></span></div>
          <div class="aud-s">${s}</div>
        </div>`;
      }).join('') + `<div class="aud aud-pruebas"><div class="aud-h"><b>Pruebas automáticas</b><span class="bien">${pruebas.casos}</span></div>
        <div class="aud-s">${pruebas.archivos} archivos: limpieza, modelos, arquitectura, API, alertas y seguridad (<span class="mono">python -m pytest tests/</span>)</div></div>`;
    }
    const traza = [
      ['download', 'Bronce', '<span class="mono">*_meta.json</span>: fuente, licencia, servicio, fecha'],
      ['eraser', 'Plata', '<span class="mono">proveniencia_*.json</span> y <span class="mono">reporte_calidad_*.csv</span>'],
      ['sigma', 'Oro', 'bloque <span class="mono">metadata</span> en cada producto'],
      ['package', 'GeoPackage', 'tabla <span class="mono">leeme</span>: origen y uso permitido de cada capa'],
      ['history', 'Parámetros', '<span class="mono">historial_parametros.jsonl</span>: quién, cuándo y por qué'],
    ];
    $('#traza').innerHTML = traza.map(([ic, t, s]) => `
      <div class="tr-paso"><span class="tile"><i data-lucide="${ic}"></i></span><div><b>${t}</b><div class="tr-s">${s}</div></div></div>`).join('');

    const piloto = [
      ['house', 'Escucha solo en el propio equipo (127.0.0.1) por defecto'],
      ['key-round', 'Abierta a la red, editar exige la clave <span class="mono">RETO5_CLAVE_EDICION</span>; consultar es libre'],
      ['variable', 'Credenciales de Teams y correo solo en variables de entorno, nunca en archivos'],
      ['globe-lock', 'Solo Bronce sale a internet, y la auditoría lo verifica en el código'],
      ['history', 'Parámetros versionados: cualquier resultado se reproduce con los de su fecha'],
    ];
    const prod = [
      ['network', 'Red virtual privada, sin exposición directa de servicios a internet'],
      ['shield', 'Publicación indirecta por Azure Front Door + WAF, con prevención y detección de ataques'],
      ['database-backup', 'Copias de seguridad, versionado y recuperación ante desastres con el RTO/RPO de Ecopetrol'],
      ['hard-drive', 'Datos en el almacenamiento de Ecopetrol y en formatos abiertos: retorno y portabilidad'],
      ['clipboard-check', 'Gobierno del dato (calidad, linaje, ciclo de vida) y validación ATAM con arquitectura empresarial'],
    ];
    const lista = (xs) => xs.map(([ic, t]) => `<div class="seg-item"><span class="tile"><i data-lucide="${ic}"></i></span><span>${t}</span></div>`).join('');
    $('#seguridad').innerHTML = `
      <div class="sub-titulo" style="margin-top:0">Hoy, en el piloto</div>${lista(piloto)}
      <div class="sub-titulo">En producción (propuesta)</div>${lista(prod)}`;
  }

  function pintarProduccion() {
    const filas = [
      ['Registro de riesgos', 'Sintético, sucio a propósito (semilla 42)', 'Registro real, Geodatabase y capas ArcGIS de Ecopetrol'],
      ['Almacenamiento', 'Carpetas data/bronze, silver y gold (Parquet, GeoJSON)', 'Azure Data Lake Storage Gen2 con tablas Delta'],
      ['Ingesta y orquestación', 'ejecutar_pipeline.py y la tarea diaria de la aplicación', 'Azure Data Factory'],
      ['Procesamiento y cruces espaciales', 'Python con GeoPandas', 'Azure Databricks con Apache Sedona'],
      ['API y aplicación', 'FastAPI + uvicorn en el equipo', 'Servicio en red privada publicado por Azure Front Door + WAF'],
      ['Visualización', 'Tablero web propio (Leaflet, Chart.js)', 'El mismo tablero, más ArcGIS Enterprise o Power BI si están licenciados'],
      ['Alertas', 'Webhook de Teams y SMTP por variables de entorno', 'Teams y correo corporativos'],
      ['Configuración', 'parametros.yaml + capas personalizadas e historial', 'Tablas de configuración versionadas'],
    ];
    $('#tabla-prod').innerHTML = `<thead><tr><th>Pieza</th><th>En el piloto</th><th>En producción (propuesta)</th></tr></thead>
      <tbody>${filas.map(([a, b, c]) => `<tr><td><b>${a}</b></td><td class="wrap">${b}</td><td class="wrap">${c}</td></tr>`).join('')}</tbody>`;
  }

  // ---- Arranque --------------------------------------------------------------------------------------------------
  // Sin /api/flujo (servidor de una version anterior, o caido) la pagina igual explica el flujo y dice que hacer.
  function sinFlujo(error) {
    const viejo = / -> 404$/.test(error.message);
    const texto = viejo
      ? `El servidor que está abierto es de una versión anterior y no tiene <span class="mono">/api/flujo</span>.
         Detenlo (Ctrl+C en su ventana) y vuelve a abrirlo desde la carpeta <span class="mono">piloto</span> con
         <span class="mono">py -3.12 iniciar.py</span>. Usa la dirección <span class="mono">http://127.0.0.1:8000</span>.`
      : `No se pudo leer el flujo del servidor (${esc(error.message)}). Revisa que la aplicación siga abierta y recarga la página.`;
    $('#pipeline .dag-wrap').innerHTML = `
      <div class="aviso-flujo"><i data-lucide="plug-zap"></i>
        <div><b>El grafo del pipeline se arma con datos del servidor</b><p>${texto}</p></div></div>`;
    $('#ultima').textContent = 'sin datos';
    pintarCalidad(null, null, 'Sin datos del servidor: la auditoría aparece cuando la aplicación responde.');
  }

  async function iniciar() {
    // Lo que no depende de una corrida se pinta de una vez, antes de consultar al servidor.
    pintarProduccion();
    pintarRecorrido(null);
    pintarFuentes({});
    pintarModelos(null);
    pintarTecnologias({});
    pintarCalidad(null, null, 'Leyendo la última auditoría…');
    ui.icons();

    const [flujo, params, estado] = await Promise.all([
      ui.json('/api/flujo').catch((error) => ({ error })),
      ui.json('/api/parametros').catch(() => null),
      ui.json('/api/alertas/estado').catch(() => null),
    ]);
    pintarModelos(params);
    pintarCiclo(estado);
    if (flujo.error) {
      console.warn('flujo:', flujo.error.message);
      sinFlujo(flujo.error);
      ui.icons();
      return;
    }
    const capas = flujo.capas;
    $('#s-pasos').textContent = flujo.pasos.length;
    $('#s-artefactos').textContent = flujo.artefactos;
    $('#s-pruebas').textContent = flujo.pruebas.casos;
    $('#s-arch-pruebas').textContent = flujo.pruebas.archivos;
    if (flujo.auditoria) {
      const ok = flujo.auditoria.por_estado.OK || 0;
      $('#s-auditoria').innerHTML = `${ok}<span class="dec">/${flujo.auditoria.total}</span>`;
      $('#s-auditoria-sub').textContent = 'Comprobaciones de auditoría en verde';
    }
    const ultima = flujo.pasos.map((p) => p.actualizado).filter(Boolean).sort().pop();
    $('#ultima').textContent = fechaHora(ultima);

    pintarRecorrido(capas);
    prepararGrafo(flujo.pasos);
    pintarGrafo();
    pintarFuentes(flujo.fuentes);
    pintarTecnologias(flujo.versiones);
    pintarCalidad(flujo.auditoria, flujo.pruebas);
    ui.icons();
    seleccionar('oro.ict');
    // Las aristas dependen de la posicion de cada nodo: se dibujan ya, al terminar de cargar las fuentes tipograficas
    // (cambian la altura de los nodos) y cada vez que cambia el tamano del grafo.
    dibujarAristas();
    if (document.fonts) document.fonts.ready.then(dibujarAristas);
    new ResizeObserver(() => dibujarAristas()).observe($('#dag'));
    window.addEventListener('resize', dibujarAristas);
  }

  iniciar().catch((e) => {
    console.error(e);
    sinFlujo(e);
  });
})();
