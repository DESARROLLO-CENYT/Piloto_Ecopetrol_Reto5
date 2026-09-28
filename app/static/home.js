/* Landing: rellena el bento con datos vivos de la API. */
(async function iniciar() {
  try {
    const [paquetes, riesgos] = await Promise.all([ui.json('/api/paquetes'), ui.json('/api/riesgos')]);
    const feats = paquetes.features.map((f) => f.properties);
    const icts = feats.map((p) => p.ICT);
    const promedio = icts.reduce((a, b) => a + b, 0) / icts.length;

    document.getElementById('h-ict').innerHTML = ui.num(promedio);
    document.getElementById('h-paquetes').textContent = `${feats.length} paquetes de trabajo`;

    const lista = riesgos.features.map((f) => f.properties);
    document.getElementById('h-riesgos').textContent = `${lista.length} registrados`;
    const conteo = {};
    lista.forEach((r) => { conteo[r.categoria] = (conteo[r.categoria] || 0) + 1; });
    const claves = Object.keys(conteo);
    const max = Math.max(...Object.values(conteo));
    document.getElementById('h-barras').innerHTML = claves.map((k) => `
      <div class="bar${conteo[k] === max ? ' max' : ''}" data-v="${conteo[k]}" title="${ui.cat(k).label}: ${conteo[k]}">
        <div class="fill" style="height:${Math.max(12, (conteo[k] / max) * 100)}%"></div>
        <span class="lbl">${ui.cat(k).corto}</span>
      </div>`).join('');
  } catch (e) {
    // Sin API la portada sigue siendo navegable; las cifras quedan en "-".
  }
})();
