/* Datos y modelo: descripcion de las capas, tablas y el modelo ICT. DATOS SINTETICOS. */

const D = { cat: null, params: null, capa: 'gold', sel: { gold: 'paquetes_ict.geojson' } };

const ORDEN = [
  'riesgos', 'paquetes_ict', 'paquetes', 'alertas', 'puntos_crisis', 'zonas_intervencion', 'grid_calor', 'clima_estaciones', 'clima_sintetico',
  'ejecucion_proyectos', 'ejecucion_paquetes', 'ejecucion_riesgos', 'ejecucion_resumen', 'cronograma', 'cronograma_proyectos', 'actividades',
  'contexto_paquetes', 'indicadores_municipio', 'indicadores_censo2018', 'irca_anual', 'dane_censo2018', 'ins_irca', 'art_pdet', 'social_meta', 'social_reporte_calidad',
  'resguardos', 'ant_resguardos', 'mininterior_resguardos_poblacion', 'resguardos_meta', 'resguardos_reporte_calidad',
  'areas_protegidas', 'runap_crudo', 'runap_meta', 'runap_reporte_calidad',
  'seguridad_municipio_mensual', 'mindefensa_delitos', 'seguridad_meta', 'seguridad_reporte_calidad',
  'emergencias', 'ungrd_emergencias', 'emergencias_meta', 'emergencias_reporte_calidad',
  'cobertura_estaciones', 'cobertura_paquetes', 'lluvia_chirps', 'chirps_municipio_mensual', 'chirps_meta', 'chirps_reporte_calidad', 'municipios', 'limite_departamental', 'dane_municipios', 'divipola_municipios', 'municipios_meta', 'municipios_reporte_calidad', 'municipios_reporte_cruces',
  'rios', 'cuerpos_agua', 'igac_hidrografia', 'igac_drenaje_sencillo', 'igac_drenaje_doble', 'igac_cienagas',
  'igac_embalses', 'igac_lagunas', 'hidrografia_meta', 'hidrografia_reporte_calidad', 'proveniencia',
  'red_vial', 'red_vial_reporte_calidad', 'vias_igac', 'igac_vias', 'igac_vias_crudas', 'vias_igac_meta', 'vias_igac_reporte_calidad',
  'invias_red_vial', 'invias_meta', 'invias_reporte_calidad',
  'ideam_estaciones', 'ideam_precipitacion', 'ideam_precip_diaria', 'ideam_variables', 'ideam_variables_horaria', 'ideam_variables_diaria',
  'ideam_ultimas_horas', 'ideam_radiacion', 'clima_radiacion', 'ideam_normales', 'ideam_meta', 'ideam_reporte_calidad',
  'comunidades', 'areas', 'hidro', 'vias', 'proyectos', 'reporte_calidad', 'validacion_backtest', 'validacion_sensibilidad',
];
const MEDAL = { bronze: 'bronce', silver: 'plata', gold: 'oro' };
const NOMBRE_CAPA = { bronze: 'Bronce', silver: 'Plata', gold: 'Oro' };

const capa = (id) => D.cat.capas.find((c) => c.id === id);
const meta = (ds) => D.cat.datasets[ds] || { titulo: ds, icono: 'file', rol: '', descripcion: '' };
const miles = (n) => Number(n).toLocaleString('es-CO');
const pct = (v) => `${Math.round(v * 100)}%`;

// ---------------------------------------------------------------------------
// Arquitectura medallion
// ---------------------------------------------------------------------------

function renderFlujo() {
  const cal = D.cat.calidad;
  const etapa = (clase, chip, titulo, cifra, unidad, script, items, archivos = []) => `
    <div class="etapa ${clase}">
      <div class="top">${chip}<span class="script mono">${script}</span></div>
      <h3>${titulo}</h3>
      <div class="cifra"><span class="num">${cifra}</span>${unidad}</div>
      <ul>${items.map((i) => `<li>${i}</li>`).join('')}</ul>
      ${archivos.length ? `<div class="archivos">${archivos.map((a) => `<span class="chip mono">${a}</span>`).join('')}</div>` : ''}
    </div>`;
  const tablas = (id) => capa(id).tablas;
  const filas = (id) => miles(tablas(id).reduce((s, t) => s + t.filas, 0));
  const archivos = (id) => tablas(id).map((t) => t.archivo);
  const ide = D.cat.ideam || {};
  const dupIdeam = ide.calidad?.duplicados_removidos;

  document.getElementById('flujo').innerHTML = [
    etapa('', '<span class="chip white"><i data-lucide="sparkles"></i> Origen</span>', 'Dos orígenes',
      2, 'fuentes de datos', 'src/bronce/*.py', [
        '<b>Sintético</b>: proyectos, paquetes, sus actividades con fechas y avance, y el registro de riesgos en Excel con texto libre (semilla 42; las fechas se cuentan desde el día en que se genera)',
        '<b>Real</b>: clima (IDEAM, CHIRPS), vías (INVIAS, IGAC), ríos (IGAC), municipios y censo (DANE), resguardos (ANT), áreas protegidas (RUNAP), delitos (MinDefensa) y emergencias (UNGRD), de fuentes abiertas sin clave',
      ]),
    etapa('bronce', '<span class="medal bronce">Bronce</span>', 'Datos crudos',
      tablas('bronze').length, `tablas · ${filas('bronze')} filas`, 'sin transformar', [
        'Se guardan tal cual llegan, en su formato original; solo esta capa descarga de internet',
        `${cal.filas_bronce} filas en el registro de riesgos, con duplicados y vacíos`,
        ide.calidad ? `${miles(ide.calidad.lecturas_bronce)} lecturas del IDEAM, con duplicados y como texto` : 'Lecturas del IDEAM aún sin descargar',
      ], archivos('bronze')),
    etapa('plata', '<span class="medal plata">Plata</span>', 'Datos limpios',
      tablas('silver').length, `tablas · ${filas('silver')} filas`, 'src/plata/*.py · lee Bronce', [
        'Normaliza categorías, estados y tipos; clasifica cada lectura del IDEAM por su sensor y unifica unidades',
        `Quita ${cal.duplicados_removidos} duplicados del registro${dupIdeam != null ? ` y ${miles(dupIdeam)} de las lecturas del IDEAM` : ''}`,
        `Ubica ${cal.sin_coordenadas_originales} riesgos sin coordenadas en el centroide de su paquete`,
        cal.ia_exactitud_validacion_cruzada != null ? `IA sobre el texto: asigna ${cal.ia_categorias_asignadas} categorías faltantes y marca ${(cal.ia_categoria_por_revisar || 0) + (cal.ia_ubicacion_por_revisar || 0)} riesgos para revisar` : 'IA sobre el texto del registro',
        'Suma la lluvia por día y estación',
        'Recorta al departamento, simplifica sin abrir huecos y une las dos redes viales sin duplicar kilómetros',
        'Deja junto a cada fuente su proveniencia y su reporte de calidad',
      ], archivos('silver')),
    etapa('oro', '<span class="medal oro">Oro</span>', 'Listos para usar',
      tablas('gold').length, `tablas · ${filas('gold')} filas`, 'src/oro/*.py · lee solo Plata', [
        'ICT por paquete y por celda: cinco criterios con el territorio real, su contribución y su confianza',
        'Escalamiento a crisis, puntos de crisis, zonas de intervención, tendencia y alertas',
        'Riesgo de ejecución: días de atraso y USD de sobrecosto (Monte Carlo)',
        'Una ficha por estación del IDEAM con todas sus variables, lecturas de ahora y normales',
        'Ríos, municipios con sus cifras y la red vial unificada para el mapa',
        'Prueba de consistencia y análisis de sensibilidad',
      ], archivos('gold')),
    etapa('', '<span class="chip white"><i data-lucide="monitor"></i> Consumo</span>', 'Quién lo usa',
      4, 'salidas', 'app/main.py · src/consumo/', [
        'API FastAPI <span class="mono">/api/…</span>',
        '<a href="mapa.html">Mapa interactivo</a> y <a href="explorar.html">Explorar datos</a>',
        'GeoPackage para ArcGIS o QGIS, con el origen de cada capa',
        'Boletín diario de alertas (archivo, Teams o correo)',
      ]),
  ].join('');
}

// ---------------------------------------------------------------------------
// Datos creados e imperfecciones
// ---------------------------------------------------------------------------

const ORIGEN_REAL = { ideam: 'IDEAM', invias: 'INVIAS', igac: 'IGAC', dane: 'DANE', invias_igac: 'INVIAS + IGAC', chirps: 'CHIRPS',
  social: 'DANE · INS · ART', ant: 'ANT', runap: 'RUNAP', mindefensa: 'MinDefensa', ungrd: 'UNGRD', varias: 'Varias fuentes' };
const esReal = (dataset) => meta(dataset).origen in ORIGEN_REAL;

function renderCreados() {
  const tablas = [...capa('bronze').tablas]
    .filter((t) => !esReal(t.dataset) && meta(t.dataset).origen !== 'meta')
    .sort((a, b) => ORDEN.indexOf(a.dataset) - ORDEN.indexOf(b.dataset));
  document.getElementById('grid-datos').innerHTML = tablas.map((t) => {
    const m = meta(t.dataset);
    return `
      <div class="dato">
        <span class="tile"><i data-lucide="${m.icono}"></i></span>
        <div>
          <div class="t">${m.titulo}<span class="n">${miles(t.filas)} ${t.geometria ? t.geometria.toLowerCase() : 'filas'}</span></div>
          <div class="s">${m.generacion || m.descripcion}</div>
        </div>
      </div>`;
  }).join('');

  const cal = D.cat.calidad;
  const riesgosBronce = capa('bronze').tablas.find((t) => t.dataset === 'riesgos');
  const nulos = riesgosBronce.columnas
    .filter((c) => ['causa', 'fecha_ejecucion_accion', 'id_evento_riesgo'].includes(c.nombre))
    .reduce((s, c) => s + c.nulos, 0);
  const imps = [
    ['copy-x', 'Registros duplicados con pequeñas variaciones', cal.duplicados_removidos],
    ['map-pin-off', 'Riesgos reportados sin coordenadas', cal.sin_coordenadas_originales],
    ['case-sensitive', 'Categorías y estados escritos distinto (mayúsculas, espacios, guiones)', '~35%'],
    ['circle-slash', 'Vacíos en causa, fecha de la acción e ID de evento', nulos],
    ['sparkles', 'Riesgos sin categoría (los clasifica la IA leyendo el texto)', cal.ia_riesgos_sin_categoria ?? '-'],
    ['shuffle', 'Riesgos con la categoría equivocada (la IA marca los que el texto contradice)', cal.ia_categorias_mal_sembradas ?? cal.ia_categoria_por_revisar ?? '-'],
    ['map', 'Riesgos que mencionan un municipio lejano a su paquete', cal.ia_ubicaciones_sembradas ?? cal.ia_ubicacion_por_revisar ?? '-'],
    ['flame', 'Paquetes "calientes" plantados con riesgos más graves', 3],
    ['cloud-lightning', 'Evento de lluvia extrema al final de la serie de clima', 1],
  ];
  document.getElementById('imperfecciones').innerHTML = imps.map(([ic, txt, n]) => `
    <div class="imp"><span class="tile"><i data-lucide="${ic}"></i></span><span class="grow">${txt}</span><span class="chip">${n}</span></div>`).join('');

  const ancho = (cal.filas_plata / cal.filas_bronce) * 100;
  document.getElementById('embudo').innerHTML = `
    <div class="fila"><span class="medal bronce">Bronce</span><div class="barra bronce" style="width:100%">registro_riesgos.xlsx</div><span class="v">${cal.filas_bronce}</span></div>
    <div class="fila"><span class="medal plata">Plata</span><div class="barra plata" style="width:${ancho}%">riesgos.geojson</div><span class="v">${cal.filas_plata}</span></div>
    <p class="nota">Salen ${cal.filas_bronce - cal.filas_plata} filas duplicadas y ningún riesgo se pierde por falta de ubicación
      (${cal.riesgos_sin_paquete_valido} descartados): los ${cal.sin_coordenadas_originales} sin coordenadas quedan marcados con
      <span class="mono">geolocalizacion_inferida</span> para que el reporte los distinga.</p>`;
}

// ---------------------------------------------------------------------------
// Clima real: IDEAM
// ---------------------------------------------------------------------------

const TITULO_TABLA = { radiacion: 'Radiación global (promedios)', normales: 'Normales climatológicas', ultimas_horas: 'Últimas horas (casi en tiempo real)' };

function renderIdeam() {
  const ide = D.cat.ideam || {};
  const el = document.getElementById('ideam-hechos');
  if (!ide.meta) {
    el.innerHTML = '<p class="nota-vacia">Aún no se descargó el clima del IDEAM. Ejecuta <span class="mono">python ejecutar_pipeline.py --fuente ideam</span> (necesita internet).</p>';
    document.getElementById('ideam-pasos').innerHTML = '';
    return;
  }
  const m = ide.meta, c = ide.calidad || {}, cat = ide.catalogo || {};
  const kv = (k, v) => `<div class="kv" style="align-items:flex-start"><span class="k" style="min-width:150px">${k}</span><span class="v" style="text-align:right;font-weight:500">${v}</span></div>`;
  const dias = Math.round((new Date(m.hasta) - new Date(m.desde)) / 86400000);
  el.innerHTML = [
    kv('Fuente', 'IDEAM · portal datos.gov.co (API Socrata), sin clave'),
    kv('Conjuntos', `${Object.keys(m.variables || {}).length + 1} conjuntos de lecturas (uno por variable) + catálogo <span class="mono">hp9r-jxuu</span>, radiación, normales y el flujo de últimas horas`),
    kv('Licencia', 'Creative Commons BY-SA 4.0 (quien redistribuya datos derivados debe conservar esa licencia)'),
    kv('Variables', `Lluvia, ${Object.keys(m.variables || {}).length} más de la tabla de abajo, radiación y normales`),
    kv('Granularidad temporal', 'Una lectura cada ~10 minutos (lluvia, viento) o cada hora (temperatura, humedad, presión, nivel); en Plata, un valor por día; además, las últimas ~12 horas casi en tiempo real'),
    kv('Granularidad espacial', `Puntos: estaciones fijas. ${cat.estaciones ?? '-'} en el catálogo de La Guajira, ${m.estaciones_sondeadas} candidatas sondeadas, <b>${m.estaciones_con_datos_recientes} reportando</b>`),
    kv('Ventana', `${dias} días, hasta la lectura más reciente (${ui.fecha(m.hasta.slice(0, 10) + 'T12:00:00')}); el IDEAM actualiza a diario`),
    kv('Volumen', `${miles(m.lecturas)} lecturas crudas → ${miles(c.lecturas_plata ?? 0)} sin duplicados → ${c.estaciones_con_lluvia_diaria ?? '-'} estaciones con lluvia diaria`),
    kv('Formato', 'JSON (API) → Parquet en Bronce → GeoJSON en Oro'),
    kv('Descargado', ui.fecha(m.descargado_en)),
  ].join('');

  document.getElementById('ideam-pasos').innerHTML = [
    ['Catálogo', `Se pide el catálogo de estaciones de La Guajira (${cat.estaciones ?? '-'} filas en un solo pedido).`],
    ['Sondeo', `A cada estación candidata se le pide su última lectura de los últimos 60 días, para saber cuáles reportan.`],
    ['Descarga', `De las ${m.estaciones_descargadas} que reportan se bajan las lecturas crudas, estación por estación y en bloques de 4 días.`],
    ['Limpieza', 'Plata clasifica cada lectura por su sensor, quita duplicados y valores imposibles, unifica unidades, suma la lluvia por día y promedia el viento como vector.'],
    ['En vivo', 'El backend consulta el flujo de últimas horas del IDEAM (cada 10 minutos como máximo) y, si no hay internet, usa el último respaldo.'],
  ].map(([t, s], i) => `<div class="regla"><span class="n">${i + 1}</span><div><div class="t">${t}</div><div class="s">${s}</div></div></div>`).join('');

  const prob = [
    ['copy-x', `${miles(c.duplicados_removidos ?? 0)} lecturas duplicadas (${((c.duplicados_removidos / Math.max(c.lecturas_bronce, 1)) * 100).toFixed(1)}%): varias estaciones traen dos sensores para la misma lluvia (0240 y 0257 GPRS). Sumarlas inflaría los totales.`],
    ['map-pin-off', 'La columna de ubicación trae latitud y longitud invertidas; se usan las columnas latitud y longitud.'],
    ['timer-off', 'Las consultas agregadas sobre todo el histórico (165 millones de filas) se agotan; solo funcionan filtradas por estación y fecha.'],
    ['droplets', `El conjunto de humedad trae sobre todo <b>humedad del suelo</b>, no del aire (${miles(c.var_reasignadas_por_sensor ?? 0)} lecturas reclasificadas); la humedad del aire solo tiene serie de 30 días en 1 estación, en las demás solo hay las últimas horas.`],
    ['ban', `${miles(c.ult_fuera_de_rango ?? 0)} lecturas de las últimas horas fuera del rango físico, casi todas el valor centinela 999 o 1000 del viento, descartadas. Unidades mezcladas (hPA/hPa, mt/m, GN/deg) unificadas.`],
    ['gauge', `Cobertura desigual: ${m.estaciones_con_datos_recientes} de ${m.estaciones_sondeadas} estaciones activas reportan, y algunas con huecos (se marcan con borde punteado en el mapa).`],
  ];
  document.getElementById('ideam-problemas').innerHTML = prob.map(([ic, t]) => `
    <div class="imp"><span class="tile"><i data-lucide="${ic}"></i></span><span class="grow" style="font-size:var(--fs-12);line-height:1.5">${t}</span></div>`).join('');

  const vs = Object.values(m.variables || {});
  const fila = (t, ds, n, l) => `<tr><td>${t}</td><td class="mono">${ds}</td><td class="num-c">${n}</td><td class="num-c">${l}</td></tr>`;
  document.getElementById('ideam-vars').innerHTML = `
    <table class="tabla-mini"><thead><tr><th>Variable</th><th>Conjunto</th><th>Estaciones</th><th>Lecturas</th></tr></thead><tbody>
    ${fila('Lluvia', 's54a-sgyg', m.estaciones_con_datos_recientes, miles(m.lecturas))}
    ${vs.map((v) => fila(v.titulo, v.dataset, v.estaciones_con_datos, miles(v.lecturas))).join('')}
    ${Object.entries(m.tablas || {}).map(([k, v]) => fila(TITULO_TABLA[k] || k, v.dataset || '', '-', miles(v.filas ?? v.lecturas ?? 0))).join('')}
    </tbody></table>
    <p class="nota-vacia" style="margin-top:8px">Nivel del mar: el conjunto existe (<span class="mono">ia8x-22em</span>) pero no tiene estaciones en La Guajira.</p>`;
}

// ---------------------------------------------------------------------------
// Catalogo de tablas
// ---------------------------------------------------------------------------

function tablasOrdenadas(id) {
  return [...capa(id).tablas].sort((a, b) => ORDEN.indexOf(a.dataset) - ORDEN.indexOf(b.dataset));
}

function renderCatalogo() {
  const tablas = tablasOrdenadas(D.capa);
  if (!D.sel[D.capa]) D.sel[D.capa] = tablas[0].archivo;
  document.getElementById('cat-lista').innerHTML = tablas.map((t) => {
    const m = meta(t.dataset);
    return `
      <a class="list-item${t.archivo === D.sel[D.capa] ? ' on' : ''}" data-archivo="${t.archivo}">
        <span class="tile"><i data-lucide="${m.icono}"></i></span>
        <div class="grow"><div class="t">${m.titulo}</div><div class="s mono">${t.archivo} · ${miles(t.filas)} filas</div></div>
      </a>`;
  }).join('');
  document.querySelectorAll('#cat-lista .list-item').forEach((el) => el.addEventListener('click', () => {
    D.sel[D.capa] = el.dataset.archivo;
    renderCatalogo();
  }));
  renderDetalleTabla(tablas.find((t) => t.archivo === D.sel[D.capa]));
}

function renderDetalleTabla(t) {
  const m = meta(t.dataset);
  const linaje = D.cat.capas
    .map((c) => ({ capa: c.id, t: c.tablas.find((x) => x.dataset === t.dataset) }))
    .filter((x) => x.t);
  document.getElementById('cat-detalle').innerHTML = `
    <div class="det-top">
      <span class="tile"><i data-lucide="${m.icono}"></i></span>
      <div class="grow"><h3>${m.titulo}</h3><div class="card-sub mono">data/${D.capa}/${t.archivo}</div></div>
    </div>
    <div class="meta-chips">
      <span class="medal ${MEDAL[D.capa]}">${NOMBRE_CAPA[D.capa]}</span>
      ${esReal(t.dataset) ? `<span class="chip ok">Real · ${ORIGEN_REAL[meta(t.dataset).origen]}</span>` : meta(t.dataset).origen === 'meta' ? '<span class="chip white">Metadatos</span>' : '<span class="chip warn">Sintético</span>'}
      <span class="chip">${t.formato}</span>
      ${t.geometria ? `<span class="chip"><i data-lucide="map-pin"></i> ${t.geometria}</span>` : ''}
      <span class="chip">${miles(t.filas)} filas</span>
      <span class="chip">${t.columnas.length} columnas</span>
      ${m.rol ? `<span class="chip outline">${m.rol}</span>` : ''}
    </div>
    <p class="desc">${m.descripcion}</p>
    ${linaje.length > 1 ? `
      <div class="linaje"><span class="lbl">Linaje</span>
        ${linaje.map((l, i) => `
          ${i ? '<span class="flecha"><i data-lucide="arrow-right"></i></span>' : ''}
          <span class="paso${l.capa === D.capa ? ' on' : ''}"><span class="medal ${MEDAL[l.capa]}" style="height:20px">${NOMBRE_CAPA[l.capa]}</span><span class="mono">${l.t.archivo}</span><b>${miles(l.t.filas)}</b></span>`).join('')}
      </div>` : ''}
    <div class="table-wrap">
      <table class="table">
        <thead><tr><th>Columna</th><th>Tipo</th><th>Vacíos</th><th>Descripción</th></tr></thead>
        <tbody>${t.columnas.map((c) => `
          <tr>
            <td class="mono">${c.nombre}</td>
            <td><span class="tipo ${c.tipo}">${c.tipo}</span></td>
            <td>${c.nulos ? `<span class="nulos">${c.nulos}</span>` : '<span class="muted">0</span>'}</td>
            <td class="wrap ink-2">${c.descripcion || '<span class="muted">-</span>'}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  ui.icons();
}

document.querySelectorAll('#seg-capa button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#seg-capa button').forEach((x) => x.classList.toggle('on', x === b));
  D.capa = b.dataset.capa;
  renderCatalogo();
}));

// ---------------------------------------------------------------------------
// Modelo
// ---------------------------------------------------------------------------

const NOMBRE_COMP = {
  etnico: 'territorio étnico', pobreza: 'pobreza', ambiental: 'áreas protegidas', acceso: 'acceso',
  lluvia_reciente: 'lluvia reciente', anomalia_lluvia: 'lluvia anómala', emergencias: 'emergencias', seguridad: 'delitos',
};
const pesosComp = (comp) => Object.entries(comp || {}).map(([k, w]) => `${NOMBRE_COMP[k] || k} ${pct(w)}`).join(', ');

function infoCriterios(p) {
  const c = p.criterios || {};
  const v = c.vulnerabilidad_territorial || {};
  const e = c.amenazas_externas || {};
  const x = c.exposicion_proyecto || {};
  const cv = c.convergencia || {};
  return {
    severidad_riesgo: {
      icon: 'flame', nombre: 'Severidad del riesgo', mide: 'Qué tan graves son las amenazas que alcanzan el paquete, según la matriz RAM de Ecopetrol.',
      calc: `nivel RAM residual (N=1 ... VH=5) × factor de estado; el máximo (${pct(p.agregacion.peso_maximo)}) más el promedio ponderado (${pct(p.agregacion.peso_promedio)}), sobre el peor caso posible (VH materializado = 1). Las amenazas de paquetes vecinos cuentan según su radio de influencia.`,
      fuentes: ['Registro de riesgos', 'Matriz RAM'],
    },
    vulnerabilidad_territorial: {
      icon: 'users', nombre: 'Vulnerabilidad territorial', mide: 'Qué tan sensible es el territorio real del paquete.',
      calc: `${pesosComp(v.componentes)}: fracción en resguardo (colindante a menos de ${v.radio_resguardo_km} km cuenta la mitad), IPM del municipio, cercanía a áreas protegidas (hasta ${v.radio_area_protegida_km} km) y vías cercanas solo transitables en tiempo seco (${v.radio_vias_km} km).`,
      fuentes: ['ANT', 'DANE censo 2018', 'RUNAP', 'INVIAS + IGAC'],
    },
    exposicion_proyecto: {
      icon: 'route', nombre: 'Exposición del proyecto', mide: 'Qué tanto pesa el paquete en el cronograma y cuántas amenazas abiertas lo alcanzan.',
      calc: `${pct(x.peso_ruta_critica)} si está en ruta crítica + ${pct(1 - x.peso_ruta_critica)} según las amenazas abiertas que lo alcanzan (${x.amenazas_para_saturar} o más = 1).`,
      fuentes: ['Cronograma', 'Registro de riesgos'],
    },
    amenazas_externas: {
      icon: 'cloud-rain', nombre: 'Amenazas externas', mide: 'Presión del entorno: lluvia, emergencias y delitos.',
      calc: `${pesosComp(e.componentes)}: lluvia de ${e.ventana_dias} días en la estación del IDEAM más cercana (${e.lluvia_mm_para_saturar} mm = 1), desviación de la lluvia frente a lo normal (CHIRPS), emergencias por año (${e.emergencias_por_ano_para_saturar} = 1) y delitos contra proyectos (${e.delitos_100k_para_saturar} por 100.000 = 1).`,
      fuentes: ['IDEAM', 'CHIRPS', 'UNGRD', 'MinDefensa'],
    },
    convergencia: {
      icon: 'git-merge', nombre: 'Convergencia de amenazas', mide: 'Cuántas amenazas distintas coinciden en el paquete.',
      calc: `categorías de amenaza abiertas con nivel RAM ${cv.nivel_minimo_registro} o más que lo alcanzan, más factores del territorio de ${cv.umbral_factor_territorio} o más; ${cv.amenazas_para_saturar} o más = 1.`,
      fuentes: ['Registro de riesgos', 'Territorio real'],
    },
  };
}

function renderModelo(paquetes) {
  const p = D.params;
  const info = infoCriterios(p);
  const pesos = Object.entries(p.pesos).sort((a, b) => b[1] - a[1]);
  const maxPeso = Math.max(...pesos.map(([, w]) => w));

  document.getElementById('criterios').innerHTML = pesos.map(([k, w]) => {
    const c = info[k];
    return `
      <div class="crit">
        <span class="tile"><i data-lucide="${c.icon}"></i></span>
        <div>
          <div class="t">${c.nombre}</div>
          <div class="s">${c.mide} <span class="muted">Cálculo:</span> ${c.calc}</div>
          <div class="fuentes">${c.fuentes.map((f) => `<span class="chip">${f}</span>`).join('')}</div>
        </div>
        <div class="peso">
          <div class="v">${Math.round(w * 100)}<span>%</span></div>
          <div class="meter"><span style="width:${(w / maxPeso) * 100}%"></span></div>
        </div>
      </div>`;
  }).join('');

  const u = p.umbrales_criticidad;
  const tramos = [['bajo', 0, u.bajo], ['medio', u.bajo, u.medio], ['alto', u.medio, u.alto], ['critico', u.alto, 100]];
  document.getElementById('escala').outerHTML = `
    <div class="escala">${tramos.map(([n, a, b]) => `<div class="${n}" style="width:${b - a}%;background:var(--lvl-${n})">${ui.NIVEL[n]}</div>`).join('')}</div>
    <div class="escala-ticks">${[0, u.bajo, u.medio, u.alto, 100].map((v) => `<span style="left:${v}%">${v}</span>`).join('')}</div>`;

  const f = p.factores_estado;
  document.getElementById('factores').innerHTML = Object.entries(f).map(([k, v]) => `
    <div class="kv"><span class="k"><span class="status"><span class="dot ${ui.ESTADO[k]?.lvl}"></span>${ui.ESTADO[k]?.label || k}</span></span><span class="v">× ${v.toFixed(1)}</span></div>`).join('');
  document.getElementById('agregacion').innerHTML = `
    <div class="kv"><span class="k">Riesgo más severo del paquete</span><span class="v">${pct(p.agregacion.peso_maximo)}</span></div>
    <div class="kv"><span class="k">Promedio ponderado del resto</span><span class="v">${pct(p.agregacion.peso_promedio)}</span></div>`;

  const e = p.escalamiento;
  const reglas = [
    [`ICT de ${e.ict_critico} o más`, 'La zona es crítica por sí sola.'],
    ['Una amenaza RAM muy alta (VH) sin materializar', 'Intolerable según la RAM de Ecopetrol: escala el paquete sin importar el ICT.'],
    ['Una amenaza RAM alta (H) en ruta crítica', 'La RAM exige que decida la gerencia; en un paquete de ruta crítica escala.'],
    ['Una amenaza alta que alcanza un territorio sensible', `Riesgo ${(e.niveles_area_sensible || ['H', 'VH']).join(' o ')} cuya área de influencia toca un resguardo indígena (ANT) o un área protegida (RUNAP) reales.`],
    [`${e.min_amenazas_convergentes}+ amenazas convergen`, `Categorías del registro más factores del territorio; solo cuenta con un ICT de ${u.medio} o más.`],
    [`${e.min_acciones_vencidas}+ acciones de tratamiento vencidas`, `En riesgos activos; también exige un ICT de ${u.medio} o más.`],
    [`Sube ${e.incremento_tendencia_alerta}+ puntos en ${e.ventana_tendencia_dias} días`, 'Alerta de tendencia, aunque el nivel todavía no sea alto.'],
  ];
  document.getElementById('reglas').innerHTML = reglas.map(([t, s], i) => `
    <div class="regla"><span class="n">${i + 1}</span><div><div class="t">${t}</div><div class="s">${s}</div></div></div>`).join('') +
    '<p class="regla-nota">Las reglas 5 y 6 exigen un ICT alto para que una coincidencia aislada en una zona tranquila no dispare una alerta. Cada regla se ubica en el mapa: en la amenaza que la dispara o en el centro del paquete, con su zona de intervención.</p>';

  renderEjemplo(paquetes, info);

  document.getElementById('salidas').innerHTML = [
    ['Matriz RAM', `Cada riesgo se califica de 0 a 5 en Personas, Económica, Ambiental, Clientes e Imagen y de A a E en probabilidad; el cruce da N, L, M, H o VH y manda la peor dimensión. Se publica sin controles (inherente) y con controles (residual); el ICT usa el residual. Fuente: ${p.ram?.fuente || 'instructivo ECP-DRI-I-007'}.`],
    ['Sugerencias del territorio', 'Para cada paquete, la probabilidad y la consecuencia que sugieren los delitos, las emergencias, los resguardos y las áreas protegidas reales, y las amenazas calificadas por debajo de esa evidencia.'],
    ['Índice de oportunidad', 'Mismo cálculo de severidad (nivel RAM del beneficio), sobre los riesgos positivos; 0 a 100. Se muestra aparte, no se resta del ICT.'],
    ['Índice de confianza', 'Qué fracción de la información del modelo está disponible y al día, ponderada por el peso de cada criterio: distingue una zona tranquila de una zona sin información. Un dato faltante no se imputa.'],
    ['Escala fija', 'Cada criterio vale de 0 a 1 contra un tope definido en parametros.yaml, no contra los demás paquetes: el ICT de un paquete no cambia porque se agregue otro.'],
    ['Getis-Ord Gi*', `Puntos calientes sobre las celdas de la grilla del área de estudio (${p.hotspot.k_vecinos} vecinas por celda); z ≥ ${p.hotspot.z_score_significativo} es un conglomerado significativo al 95 %. No se aplica a los 14 paquetes: con tan pocas unidades nada sería significativo.`],
    ['Mapa de calor (KDE)', `Kernel gaussiano con banda de ${miles(p.kde.bandwidth_m)} m sobre una grilla de ${p.grid.resolucion_grados}° (~2 km): amenazas ponderadas por nivel RAM y estado; aparte, las oportunidades.`],
    ['Puntos de crisis', 'Donde un evento podría escalar: la amenaza que dispara la regla (o el centro del paquete), con el radio de influencia de su categoría como zona de intervención prioritaria.'],
    ['Alertas', 'Una por paquete en escalamiento o con el ICT al alza: causas, puntos de crisis, qué exige la RAM y quién decide.'],
    ['Tendencia', `ICT de hace ${e.ventana_tendencia_dias} días con la misma escala fija: el cambio viene de los riesgos y de la lluvia, no de un reescalado.`],
  ].map(([k, v]) => `<div class="kv" style="align-items:flex-start"><span class="k" style="min-width:150px;color:var(--ink);font-weight:600">${k}</span><span class="ink-2" style="font-size:var(--fs-12);line-height:1.5">${v}</span></div>`).join('');

  const v = D.cat.validacion;
  const nombreCrit = (k) => info[k]?.nombre || k;
  document.getElementById('validacion').innerHTML = [
    v.backtest ? [v.backtest.spearman.toFixed(2), 'Prueba de consistencia (circular, no es validación): correlación entre el ICT y los riesgos ya materializados'] : null,
    v.backtest ? [pct(v.backtest.precision_top), `De los ${v.backtest.top_k} paquetes con mayor ICT tienen al menos un riesgo materializado`] : null,
    v.sensibilidad ? [v.sensibilidad.spearman_min.toFixed(2), `Correlación mínima del ranking al mover cada peso ±20% (más sensible: ${nombreCrit(v.sensibilidad.criterio_mas_sensible).toLowerCase()})`] : null,
    D.cat.calidad?.ia_exactitud_validacion_cruzada != null ? [pct(D.cat.calidad.ia_exactitud_validacion_cruzada), 'Acierto de la IA al clasificar riesgos que no vio (validación cruzada en 5 partes)'] : null,
    D.cat.calidad?.ia_exactitud_sin_categoria != null ? [pct(D.cat.calidad.ia_exactitud_sin_categoria), `Acierto de la IA en los ${D.cat.calidad.ia_categorias_asignadas} riesgos que llegaron sin categoría (contra la clave sintética)`] : null,
    D.cat.calidad?.ia_categorias_mal_sembradas ? [`${D.cat.calidad.ia_categorias_mal_detectadas}/${D.cat.calidad.ia_categorias_mal_sembradas}`, `Categorías equivocadas que la IA detecta, con ${D.cat.calidad.ia_categorias_falsas_alarmas} falsas alarmas (contra la clave sintética)`] : null,
    D.cat.calidad?.ia_ubicaciones_sembradas ? [`${D.cat.calidad.ia_ubicaciones_detectadas}/${D.cat.calidad.ia_ubicaciones_sembradas}`, `Ubicaciones dudosas que la IA detecta, con ${D.cat.calidad.ia_ubicaciones_falsas_alarmas} falsas alarmas (contra la clave sintética)`] : null,
  ].filter(Boolean).map(([n, l]) => `<div class="val"><div class="num">${n}</div><div class="l">${l}</div></div>`).join('');
}

function renderEjemplo(paquetes, info) {
  const top = [...paquetes].sort((a, b) => b.ICT - a.ICT)[0];
  const colores = ['--green-800', '--green-600', '--green-500', '--green-300', '--lime'];
  const partes = Object.keys(D.params.pesos)
    .map((k) => ({ k, pts: top[`${k}_contrib`] ?? 0, val: top[k] ?? 0, w: D.params.pesos[k] }))
    .sort((a, b) => b.pts - a.pts);
  document.getElementById('ej-sub').textContent = `Cómo se compone el ICT de ${ui.nombreCorto(top.nombre)}`;
  document.getElementById('ejemplo').innerHTML = `
    <div class="cab">
      <div><div class="t">${ui.nombreCorto(top.nombre)}</div><div class="s">${top.id_paquete}</div></div>
      <div style="text-align:right"><span class="lvl ${top.nivel}">${ui.NIVEL[top.nivel]}</span><div class="num lg">${ui.num(top.ICT)}</div></div>
    </div>
    <div class="apilada">${partes.map((x, i) => `<div title="${info[x.k].nombre}: ${x.pts}" style="width:${x.pts}%;background:var(${colores[i]})"></div>`).join('')}</div>
    ${partes.map((x, i) => `
      <div class="ley">
        <span class="sw" style="background:var(${colores[i]})"></span>
        <span>${info[x.k].nombre}<br><span class="calc">peso ${x.w.toFixed(2)} × valor ${x.val.toFixed(2)} × 100</span></span>
        <b>${x.pts.toFixed(1)}</b>
      </div>`).join('')}`;
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

(async function iniciar() {
  const [cat, params, paquetes] = await Promise.all([ui.json('/api/catalogo'), ui.json('/api/parametros'), ui.json('/api/paquetes')]);
  D.cat = cat;
  D.params = params;

  document.getElementById('param-version').textContent = `v${params.version.split('-')[0]}`;
  document.getElementById('s-tablas').textContent = cat.capas.reduce((s, c) => s + c.tablas.length, 0);
  document.getElementById('s-filas').innerHTML = miles(capa('gold').tablas.reduce((s, t) => s + t.filas, 0));

  renderFlujo();
  renderCreados();
  renderIdeam();
  renderCatalogo();
  renderModelo(paquetes.features.map((f) => f.properties));
  ui.icons();
})();
