/* Matriz RAM editable: la oficial (parametros.yaml) no se toca; lo editado se guarda en ram_personalizada.yaml. */

const M = {
  oficial: null,     // { ram, escalamiento } de parametros.yaml
  guardada: null,    // la vigente en el servidor (oficial o personalizada)
  edit: null,        // lo que se esta editando
  personalizada: false,
  riesgos: [],
  rutaCritica: new Set(),
  sel: null,         // celda abierta en el selector: { c, i }
};

const LETRAS = ['A', 'B', 'C', 'D', 'E'];
const NIVELES = ['N', 'L', 'M', 'H', 'VH'];
const DIMS = ['PE', 'EC', 'MA', 'CL', 'IM'];
const COL = { PE: 'cons_personas', EC: 'cons_economica', MA: 'cons_ambiental', CL: 'cons_clientes', IM: 'cons_imagen' };
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

// solo lo que se puede editar, en el formato que espera PUT /api/ram
function editable(c) {
  const r = c.ram;
  return {
    matriz: Object.fromEntries([0, 1, 2, 3, 4, 5].map((k) => [k, [...r.matriz[k]]])),
    probabilidades: { ...r.probabilidades },
    consecuencias: Object.fromEntries(DIMS.map((d) => [d, Object.fromEntries([0, 1, 2, 3, 4, 5].map((k) => [k, r.consecuencias[d][k]]))])),
    niveles: Object.fromEntries(NIVELES.map((n) => [n, { nombre: r.niveles[n].nombre, puntaje: r.niveles[n].puntaje, decision: r.niveles[n].decision, aprueba: r.niveles[n].aprueba }])),
    escalamiento: { ...c.escalamiento },
  };
}
const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ---------------------------------------------------------------------------
// Clasificacion (la misma regla que modelo/ram.py): manda la peor dimension
// ---------------------------------------------------------------------------

function clasificar(r, matriz, prob) {
  const p = r[prob];
  if (!p) return null;
  let mejor = null;
  DIMS.forEach((d) => {
    const c = r[COL[d]];
    if (c == null) return;
    const n = matriz[c][LETRAS.indexOf(p)];
    const clave = NIVELES.indexOf(n) * 10 + c;
    if (!mejor || clave > mejor.clave) mejor = { clave, nivel: n, codigo: `${c}${p}` };
  });
  return mejor;
}

const abiertas = () => M.riesgos.filter((r) => r.tipo === 'amenaza' && r.estado !== 'materializado');

// ---------------------------------------------------------------------------
// Matriz editable
// ---------------------------------------------------------------------------

function renderMatriz() {
  const e = M.edit, of = M.oficial.ram;
  const cab = LETRAS.map((l) => `<th title="${esc(e.probabilidades[l])}">${l}<small>${esc(e.probabilidades[l])}</small></th>`).join('');
  const filas = [5, 4, 3, 2, 1, 0].map((c) => {
    const tip = DIMS.map((d) => `${ui.DIM_RAM[d]}: ${e.consecuencias[d][c]}`).join('\n');
    return `<tr><th title="${esc(tip)}"><b>${c}</b><small>${esc(e.consecuencias.PE[c])}</small></th>${LETRAS.map((l, i) => {
      const n = e.matriz[c][i];
      const r = ui.RAM[n];
      const distinto = n !== of.matriz[c][i];
      const abierta = M.sel && M.sel.c === c && M.sel.i === i;
      return `<td><button class="celda${abierta ? ' abierta' : ''}" data-c="${c}" data-i="${i}" style="background:${r.bg};color:${r.fg}"
        title="${c}${l}: ${r.nombre}${distinto ? ` (oficial: ${of.matriz[c][i]})` : ''}">${n}${distinto ? '<span class="punto"></span>' : ''}</button></td>`;
    }).join('')}</tr>`;
  }).join('');
  document.getElementById('matriz').innerHTML = `<thead><tr><th class="eje">C \\ P</th>${cab}</tr></thead><tbody>${filas}</tbody>`;
  document.querySelectorAll('#matriz .celda').forEach((b) => b.addEventListener('click', (ev) => {
    ev.stopPropagation();
    abrirSelector(Number(b.dataset.c), Number(b.dataset.i), b);
  }));
}

function abrirSelector(c, i, boton) {
  M.sel = { c, i };
  const s = document.getElementById('selector');
  const actual = M.edit.matriz[c][i];
  const oficial = M.oficial.ram.matriz[c][i];
  s.innerHTML = `<div class="sel-t">Celda ${c}${LETRAS[i]}</div>${NIVELES.map((n) => `<button class="opc${n === actual ? ' on' : ''}" data-n="${n}">${ui.ramChip(n)}<span>${ui.RAM[n].nombre}</span>${n === oficial ? '<small>oficial</small>' : ''}</button>`).join('')}`;
  const card = boton.closest('.card').getBoundingClientRect();
  const r = boton.getBoundingClientRect();
  s.style.left = `${Math.min(r.left - card.left, card.width - 190)}px`;
  s.style.top = `${r.bottom - card.top + 6}px`;
  s.hidden = false;
  s.querySelectorAll('.opc').forEach((o) => o.addEventListener('click', (ev) => {
    ev.stopPropagation();
    M.edit.matriz[c][i] = o.dataset.n;
    cerrarSelector();
    refrescar();
  }));
  renderMatriz();
}
function cerrarSelector() {
  M.sel = null;
  document.getElementById('selector').hidden = true;
}
document.addEventListener('click', (ev) => { if (M.sel && !ev.target.closest('#selector')) { cerrarSelector(); renderMatriz(); } });
document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && M.sel) { cerrarSelector(); renderMatriz(); } });

function advertencias(e) {
  const o = (n) => NIVELES.indexOf(n);
  const out = [];
  for (let c = 0; c <= 5; c += 1) for (let i = 0; i < 4; i += 1) {
    if (o(e.matriz[c][i + 1]) < o(e.matriz[c][i])) out.push(`Consecuencia ${c}: el nivel baja de ${LETRAS[i]} (${e.matriz[c][i]}) a ${LETRAS[i + 1]} (${e.matriz[c][i + 1]}) aunque la probabilidad sube.`);
  }
  for (let i = 0; i < 5; i += 1) for (let c = 0; c < 5; c += 1) {
    if (o(e.matriz[c + 1][i]) < o(e.matriz[c][i])) out.push(`Probabilidad ${LETRAS[i]}: el nivel baja de ${c} (${e.matriz[c][i]}) a ${c + 1} (${e.matriz[c + 1][i]}) aunque la consecuencia sube.`);
  }
  const pts = NIVELES.map((n) => Number(e.niveles[n].puntaje));
  if (pts.some((p, k) => k > 0 && p <= pts[k - 1])) out.push('Los puntajes no crecen de N a VH: el ICT trataría un nivel más grave como menos severo.');
  return out;
}

// ---------------------------------------------------------------------------
// Efecto en el registro (antes de guardar)
// ---------------------------------------------------------------------------

function renderEfecto() {
  const lista = abiertas();
  const antes = lista.map((r) => clasificar(r, M.guardada.ram.matriz, 'probabilidad_residual'));
  const despues = lista.map((r) => clasificar(r, M.edit.matriz, 'probabilidad_residual'));
  const cuenta = (arr) => Object.fromEntries(NIVELES.map((n) => [n, arr.filter((x) => x?.nivel === n).length]));
  const a = cuenta(antes), d = cuenta(despues);
  const max = Math.max(1, ...NIVELES.map((n) => Math.max(a[n], d[n])));
  const cambios = lista.map((r, k) => ({ r, de: antes[k]?.nivel, a: despues[k]?.nivel })).filter((x) => x.de !== x.a);
  const sube = cambios.filter((x) => NIVELES.indexOf(x.a) > NIVELES.indexOf(x.de)).length;

  // paquetes que escalarian por la RAM (solo estas dos reglas; el ICT y las demas reglas no se recalculan aqui)
  const escalan = (niveles, reglas) => {
    const s = new Set();
    lista.forEach((r, k) => {
      const n = niveles[k]?.nivel;
      if ((reglas.ram_vh_escala && n === 'VH') || (reglas.ram_h_en_ruta_critica && n === 'H' && M.rutaCritica.has(r.id_paquete_trabajo))) s.add(r.id_paquete_trabajo);
    });
    return s;
  };
  const pa = escalan(antes, M.guardada.escalamiento), pd = escalan(despues, M.edit.escalamiento);

  document.getElementById('efecto').innerHTML = `
    <div class="ef-barras">${[...NIVELES].reverse().map((n) => `
      <div class="ef-fila">${ui.ramChip(n)}
        <div class="ef-track"><span class="antes" style="width:${(a[n] / max) * 100}%"></span><span class="despues" style="width:${(d[n] / max) * 100}%;background:${ui.RAM[n].bg}"></span></div>
        <span class="ef-n">${a[n]} → <b>${d[n]}</b></span></div>`).join('')}
    </div>
    <div class="ef-leyenda"><span><i class="sw antes"></i> guardada</span><span><i class="sw despues"></i> con tus cambios</span></div>
    <div class="ef-kpis">
      <div><div class="num md">${cambios.length}</div><div class="card-sub">amenazas cambian de nivel${cambios.length ? ` (${sube} suben, ${cambios.length - sube} bajan)` : ''}</div></div>
      <div><div class="num md">${pa.size} → ${pd.size}</div><div class="card-sub">paquetes escalarían por la RAM (VH, o H en ruta crítica)</div></div>
    </div>
    ${cambios.length ? `<div class="ef-lista">${cambios.slice(0, 8).map((x) => `<div><span>${x.r.id_riesgo} · ${ui.cat(x.r.categoria).corto}</span><span>${ui.ramChip(x.de)} → ${ui.ramChip(x.a)}</span></div>`).join('')}${cambios.length > 8 ? `<div class="mas">y ${cambios.length - 8} más</div>` : ''}</div>` : ''}
    <p class="nota">El ICT, el mapa y Explorar cambian cuando guardas y recalculas.</p>`;
}

// ---------------------------------------------------------------------------
// Niveles, probabilidades, consecuencias
// ---------------------------------------------------------------------------

function renderNiveles() {
  document.getElementById('niveles').innerHTML = [...NIVELES].reverse().map((n) => {
    const v = M.edit.niveles[n];
    return `<div class="nivel">
      ${ui.ramChip(n)}
      <label>Nombre<input class="field" data-n="${n}" data-k="nombre" value="${esc(v.nombre)}" maxlength="300"></label>
      <label class="pts">Puntaje<input class="field" type="number" min="0.1" max="100" step="0.5" data-n="${n}" data-k="puntaje" value="${v.puntaje}"></label>
      <label class="dec">Qué exige<textarea class="field" rows="2" data-n="${n}" data-k="decision" maxlength="300">${esc(v.decision)}</textarea></label>
      <label class="apr">Quién aprueba<input class="field" data-n="${n}" data-k="aprueba" value="${esc(v.aprueba)}" maxlength="300"></label>
    </div>`;
  }).join('');
  document.querySelectorAll('#niveles [data-n]').forEach((el) => el.addEventListener('input', () => {
    M.edit.niveles[el.dataset.n][el.dataset.k] = el.dataset.k === 'puntaje' ? Number(el.value) : el.value;
    refrescar(false);
  }));
}

function renderProbabilidades() {
  document.getElementById('probabilidades').innerHTML = LETRAS.map((l) => `
    <label class="prob"><b>${l}</b><input class="field" data-l="${l}" value="${esc(M.edit.probabilidades[l])}" maxlength="300"></label>`).join('');
  document.querySelectorAll('#probabilidades [data-l]').forEach((el) => el.addEventListener('input', () => {
    M.edit.probabilidades[el.dataset.l] = el.value;
    refrescar(false);
  }));
  document.getElementById('esc-vh').checked = !!M.edit.escalamiento.ram_vh_escala;
  document.getElementById('esc-h').checked = !!M.edit.escalamiento.ram_h_en_ruta_critica;
}

function renderConsecuencias() {
  document.getElementById('consecuencias').innerHTML = `<table><thead><tr><th></th>${DIMS.map((d) => `<th>${ui.DIM_RAM[d]}</th>`).join('')}</tr></thead><tbody>${
    [5, 4, 3, 2, 1, 0].map((c) => `<tr><th>${c}</th>${DIMS.map((d) => `<td><input class="field" data-d="${d}" data-c="${c}" value="${esc(M.edit.consecuencias[d][c])}" maxlength="300"></td>`).join('')}</tr>`).join('')
  }</tbody></table>`;
  document.querySelectorAll('#consecuencias [data-d]').forEach((el) => el.addEventListener('input', () => {
    M.edit.consecuencias[el.dataset.d][el.dataset.c] = el.value;
    refrescar(false);
  }));
}

['esc-vh', 'esc-h'].forEach((id) => document.getElementById(id).addEventListener('change', () => {
  M.edit.escalamiento.ram_vh_escala = document.getElementById('esc-vh').checked;
  M.edit.escalamiento.ram_h_en_ruta_critica = document.getElementById('esc-h').checked;
  refrescar(false);
}));

// ---------------------------------------------------------------------------
// Estado, guardar, recalcular
// ---------------------------------------------------------------------------

function renderEstado() {
  const v = M.guardada.ram.version || {};
  const chip = document.getElementById('chip-version');
  chip.innerHTML = M.personalizada
    ? `<i data-lucide="pencil"></i> Personalizada · ${v.editado_en ? ui.fecha(v.editado_en) : ''}${v.editado_por ? ` · ${v.editado_por}` : ''}`
    : '<i data-lucide="badge-check"></i> Oficial · ECP-DRI-I-007';
  chip.title = M.personalizada ? (v.nota || 'Matriz editada en esta aplicación') : M.oficial.ram.fuente;

  const guardada = editable(M.guardada);
  const sucio = !igual(M.edit, guardada);
  const celdasOf = [0, 1, 2, 3, 4, 5].reduce((s, c) => s + M.edit.matriz[c].filter((n, i) => n !== M.oficial.ram.matriz[c][i]).length, 0);
  document.getElementById('estado-edicion').textContent = sucio ? 'Cambios sin guardar' : (M.personalizada ? 'Matriz personalizada guardada' : 'Matriz oficial, sin cambios');
  document.getElementById('estado-sub').textContent = `${celdasOf} celda${celdasOf === 1 ? '' : 's'} distinta${celdasOf === 1 ? '' : 's'} de la oficial. `
    + (sucio ? 'Guarda para que la use el modelo; recalcula para ver el efecto en el ICT, el mapa y Explorar.' : 'Haz clic en una celda para cambiar su nivel.');
  document.getElementById('b-guardar').disabled = !sucio;
  document.getElementById('b-descartar').disabled = !sucio;
  document.getElementById('b-oficial').disabled = !M.personalizada && igual(M.edit, editable(M.oficial));
  document.getElementById('barra').classList.toggle('sucio', sucio);
  const adv = advertencias(M.edit);
  document.getElementById('advertencias').innerHTML = adv.length
    ? `<div class="adv-t"><i data-lucide="triangle-alert"></i> Válido, pero revisa:</div>${adv.map((a) => `<div>${a}</div>`).join('')}` : '';
  ui.icons();
}

function refrescar(redibujarMatriz = true) {
  if (redibujarMatriz) renderMatriz();
  renderEfecto();
  renderEstado();
}

function aviso(texto, tipo = 'ok') {
  const a = document.getElementById('aviso');
  a.className = `aviso ${tipo}`;
  a.innerHTML = texto;
  a.hidden = !texto;
  ui.icons();
}

function cargar(res) {
  M.oficial = res.oficial;
  M.guardada = res.vigente;
  M.personalizada = res.personalizada;
  M.edit = editable(res.vigente);
  renderNiveles();
  renderProbabilidades();
  renderConsecuencias();
  refrescar();
}

async function pedir(metodo, cuerpo) {
  const r = await ui.escribir('/api/ram', { method: metodo, headers: { 'Content-Type': 'application/json' }, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const datos = await r.json();
  if (!r.ok) throw new Error(datos.detail || `Error ${r.status}`);
  return datos;
}

async function guardar() {
  const cuerpo = { ...M.edit, editado_por: document.getElementById('f-autor').value, nota: document.getElementById('f-nota').value };
  const res = await pedir('PUT', cuerpo);
  cargar(res);
  return res;
}

document.getElementById('b-guardar').addEventListener('click', async () => {
  try {
    const res = await guardar();
    aviso(`<i data-lucide="check"></i> Matriz guardada.${res.advertencias.length ? ` Con ${res.advertencias.length} advertencia(s).` : ''} El ICT y el mapa la usarán cuando recalcules.`);
  } catch (e) { aviso(`<i data-lucide="x"></i> ${e.message}`, 'error'); }
});

document.getElementById('b-recalcular').addEventListener('click', async () => {
  const b = document.getElementById('b-recalcular');
  try {
    if (!igual(M.edit, editable(M.guardada))) await guardar();
    const r = await ui.escribir('/api/ram/recalcular', { method: 'POST' });
    const est = await r.json();
    if (!r.ok) throw new Error(est.detail || `Error ${r.status}`);
    b.disabled = true;
    seguirRecalculo(est.pasos.length);
  } catch (e) { aviso(`<i data-lucide="x"></i> ${e.message}`, 'error'); b.disabled = false; }
});

async function seguirRecalculo(total) {
  const b = document.getElementById('b-recalcular');
  const est = await ui.json('/api/ram/recalcular');
  if (est.estado === 'corriendo') {
    aviso(`<i data-lucide="loader"></i> Recalculando el registro de riesgos, el ICT y lo que depende de ellos (${est.hechos.length} de ${total} pasos)…`, 'info');
    setTimeout(() => seguirRecalculo(total), 1500);
    return;
  }
  b.disabled = false;
  if (est.estado === 'listo') {
    aviso(`<i data-lucide="check"></i> Recalculado en ${est.segundos} s: el registro, el ICT, las alertas y el contexto ya usan esta matriz. <a href="explorar.html#riesgos">Ver en Explorar</a>`);
    M.riesgos = (await ui.json('/api/riesgos')).features.map((f) => f.properties);
    refrescar();
  } else {
    aviso(`<i data-lucide="x"></i> El recálculo terminó con fallos en: ${est.fallos.join(', ')}. Revisa la consola del servidor.`, 'error');
  }
}

document.getElementById('b-descartar').addEventListener('click', () => {
  M.edit = editable(M.guardada);
  renderNiveles();
  renderProbabilidades();
  renderConsecuencias();
  refrescar();
  aviso('');
});

document.getElementById('b-oficial').addEventListener('click', async () => {
  if (!window.confirm('¿Volver a la matriz oficial de Ecopetrol? Se borra la matriz personalizada guardada.')) return;
  try {
    cargar(await pedir('DELETE'));
    aviso('<i data-lucide="rotate-ccw"></i> De vuelta a la matriz oficial. Recalcula para que el ICT y el mapa la usen.');
  } catch (e) { aviso(`<i data-lucide="x"></i> ${e.message}`, 'error'); }
});

window.addEventListener('beforeunload', (ev) => {
  if (M.edit && M.guardada && !igual(M.edit, editable(M.guardada))) { ev.preventDefault(); ev.returnValue = ''; }
});

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------

(async function iniciar() {
  const [ram, riesgos, paquetes] = await Promise.all([ui.json('/api/ram'), ui.json('/api/riesgos'), ui.json('/api/paquetes')]);
  M.riesgos = riesgos.features.map((f) => f.properties);
  M.rutaCritica = new Set(paquetes.features.filter((f) => f.properties.ruta_critica).map((f) => f.properties.id_paquete));
  cargar(ram);
  const est = await ui.json('/api/ram/recalcular');
  if (est.estado === 'corriendo') { document.getElementById('b-recalcular').disabled = true; seguirRecalculo(est.pasos.length); }
})();
