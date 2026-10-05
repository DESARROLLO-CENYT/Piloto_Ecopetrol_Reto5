/* Datos y modelo: descripcion de las capas, tablas y el modelo ICT. DATOS SINTETICOS. */

const D = { cat: null, params: null, capa: 'gold', sel: { gold: 'paquetes_ict.geojson' } };

const ORDEN = [
  'riesgos', 'paquetes_ict', 'paquetes', 'alertas', 'grid_calor', 'clima_estaciones', 'clima_sintetico',
  'municipios', 'limite_departamental', 'dane_municipios', 'divipola_municipios', 'municipios_meta', 'municipios_reporte_calidad', 'municipios_reporte_cruces',
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
        '<b>Sintético</b>: proyectos, paquetes, comunidades, áreas, hidrología, vías y el registro de riesgos en Excel (semilla 42, siempre igual)',
        '<b>Real</b>: clima del IDEAM, red vial de INVIAS, ríos del IGAC y municipios del DANE, todos de fuentes abiertas sin clave',
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
        'Suma la lluvia por día y estación',
        'Recorta al departamento, simplifica sin abrir huecos y une las dos redes viales sin duplicar kilómetros',
        'Deja junto a cada fuente su proveniencia y su reporte de calidad',
      ], archivos('silver')),
    etapa('oro', '<span class="medal oro">Oro</span>', 'Listos para usar',
      tablas('gold').length, `tablas · ${filas('gold')} filas`, 'src/oro/*.py · lee solo Plata', [
        'Cinco criterios e ICT por paquete, con su contribución',
        'Reglas de escalamiento, tendencia y alertas',
        'Una ficha por estación del IDEAM con todas sus variables, lecturas de ahora y normales',
        'Ríos, municipios con sus cifras y la red vial unificada para el mapa',
        'Backtest y análisis de sensibilidad',
      ], archivos('gold')),
    etapa('', '<span class="chip white"><i data-lucide="monitor"></i> Consumo</span>', 'Quién lo usa',
      4, 'salidas', 'app/main.py · src/consumo/', [
        'API FastAPI <span class="mono">/api/…</span>',
        '<a href="mapa.html">Mapa interactivo</a> y <a href="explorar.html">Explorar datos</a>',
        'GeoPackage para ArcGIS o QGIS',
        'Alertas para el equipo de riesgos',
      ]),
  ].join('');
}

// ---------------------------------------------------------------------------
// Datos creados e imperfecciones
// ---------------------------------------------------------------------------

const ORIGEN_REAL = { ideam: 'IDEAM', invias: 'INVIAS', igac: 'IGAC', dane: 'DANE', invias_igac: 'INVIAS + IGAC' };
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

function infoCriterios(p) {
  const r = p.radios_influencia_m;
  return {
    severidad_riesgo: {
      icon: 'flame', nombre: 'Severidad del riesgo', mide: 'Qué tan graves son las amenazas del paquete.',
      calc: `probabilidad × impacto × factor de estado; se combina el máximo (${pct(p.agregacion.peso_maximo)}) con el promedio ponderado (${pct(p.agregacion.peso_promedio)}).`,
      fuentes: ['Registro de riesgos'],
    },
    vulnerabilidad_territorial: {
      icon: 'users', nombre: 'Vulnerabilidad territorial', mide: 'Qué tan sensible es el entorno del paquete.',
      calc: `mitad cercanía a comunidades (radio ${miles(r.social_comunidad)} m, × conflictividad) y mitad cercanía a áreas protegidas (radio ${miles(r.ambiental)} m, × sensibilidad).`,
      fuentes: ['Comunidades', 'Áreas protegidas'],
    },
    exposicion_proyecto: {
      icon: 'route', nombre: 'Exposición del proyecto', mide: 'Qué tanto pesa el paquete dentro del proyecto.',
      calc: '60% si está en ruta crítica + 40% cantidad de riesgos que recibe (normalizada).',
      fuentes: ['Paquetes', 'Registro de riesgos'],
    },
    amenazas_externas: {
      icon: 'cloud-rain', nombre: 'Amenazas externas (clima)', mide: 'Presión climática reciente sobre la zona.',
      calc: `lluvia acumulada ${p.amenazas_externas.ventana_dias} días en la estación más cercana; ${p.amenazas_externas.precipitacion_extrema_mm_14d} mm o más cuenta como 1.`,
      fuentes: ['Clima'],
    },
    convergencia: {
      icon: 'git-merge', nombre: 'Convergencia de amenazas', mide: 'Cuántos tipos de amenaza coinciden en el paquete.',
      calc: `categorías distintas de amenaza ÷ ${p.convergencia.categorias_para_saturar} (satura en 1).`,
      fuentes: ['Registro de riesgos'],
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
    [`${e.min_amenazas_convergentes}+ categorías de amenaza juntas`, `Solo cuenta si el ICT es al menos ${u.medio} (medio-alto).`],
    [`${e.min_acciones_vencidas}+ acciones de tratamiento vencidas`, `Acciones con fecha pasada en riesgos activos; también exige ICT de ${u.medio} o más.`],
    [`Sube ${e.incremento_tendencia_alerta}+ puntos en ${e.ventana_tendencia_dias} días`, 'Alerta de tendencia, aunque el nivel todavía no sea alto.'],
  ];
  document.getElementById('reglas').innerHTML = reglas.map(([t, s], i) => `
    <div class="regla"><span class="n">${i + 1}</span><div><div class="t">${t}</div><div class="s">${s}</div></div></div>`).join('') +
    '<p class="regla-nota">Las reglas 2 y 3 exigen un ICT medio para que una coincidencia aislada en una zona tranquila no dispare una alerta.</p>';

  renderEjemplo(paquetes, info);

  document.getElementById('salidas').innerHTML = [
    ['Índice de oportunidad', 'Mismo cálculo de severidad, sobre los riesgos positivos; 0 a 100. Se muestra aparte, no se resta del ICT.'],
    ['Índice de confianza', 'Fracción de los cinco criterios con dato para el paquete: distingue una zona segura de una zona sin información.'],
    ['Getis-Ord Gi*', `Puntos calientes con los ${p.hotspot.k_vecinos} paquetes vecinos; |z| ≥ ${p.hotspot.z_score_significativo} es significativo al 95%.`],
    ['Mapa de calor (KDE)', `Kernel gaussiano con banda de ${miles(p.kde.bandwidth_m)} m sobre una grilla de ${p.grid.resolucion_grados}° (~2 km), ponderado por severidad.`],
    ['Tendencia', `ICT de hace ${e.ventana_tendencia_dias} días calculado con los mismos límites de normalización, para que el cambio sea real y no un reescalado.`],
  ].map(([k, v]) => `<div class="kv" style="align-items:flex-start"><span class="k" style="min-width:150px;color:var(--ink);font-weight:600">${k}</span><span class="ink-2" style="font-size:var(--fs-12);line-height:1.5">${v}</span></div>`).join('');

  const v = D.cat.validacion;
  const nombreCrit = (k) => info[k]?.nombre || k;
  document.getElementById('validacion').innerHTML = [
    v.backtest ? [v.backtest.spearman.toFixed(2), 'Correlación de Spearman entre el ICT y los riesgos ya materializados'] : null,
    v.backtest ? [pct(v.backtest.precision_top), `De los ${v.backtest.top_k} paquetes con mayor ICT tienen al menos un riesgo materializado`] : null,
    v.sensibilidad ? [v.sensibilidad.spearman_min.toFixed(2), `Correlación mínima del ranking al mover cada peso ±20% (más sensible: ${nombreCrit(v.sensibilidad.criterio_mas_sensible).toLowerCase()})`] : null,
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
