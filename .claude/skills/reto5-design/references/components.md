# Snippets y recetas - reto5-design v2

Indice: 1. Head de pagina · 2. Shell y topbar · 3. Tarjetas · 4. Botones y
seleccion · 5. Datos · 6. Tabla y listas · 7. Formularios · 8. Mapa ·
9. Chart.js · 10. Leaflet

Todos los iconos son Lucide: `<i data-lucide="nombre"></i>`. Despues de
insertar HTML con iconos por JS, llama `ui.icons()` (envuelve
`lucide.createIcons()`).

## 1. Head de pagina

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="components.css">
<link rel="stylesheet" href="PAGINA.css">
...
<script src="https://unpkg.com/lucide@0.460.0/dist/umd/lucide.min.js"></script>
<script src="ui.js"></script>
<script src="PAGINA.js"></script>
```

## 2. Shell y topbar

La topbar la dibuja `ui.js` en `<header id="topbar" data-active="mapa">`
(valores: `inicio`, `mapa`, `explorar`, `datos`). No la copies a mano en cada
pagina; para agregar una pagina nueva, suma su entrada a `items` en `ui.js`.

```html
<body>
  <div class="shell">            <!-- .shell.fixed en paginas sin scroll (mapa) -->
    <header id="topbar" data-active="explorar"></header>
    <div class="page-head">
      <h1>Explorar datos, <span>La Guajira</span></h1>
      <div class="acciones">
        <span class="chip white"><i data-lucide="calendar"></i> Corte 28 sep 2026</span>
        <a class="btn btn-outline sm" href="mapa.html"><i data-lucide="map"></i> Ver mapa</a>
      </div>
    </div>
    <div class="bento"> ... </div>
  </div>
</body>
```

## 3. Tarjetas

Cabecera estandar (Ejemplo_1): icono opcional, titulo + subtitulo, accion
circular a la derecha.

```html
<section class="card span-5">
  <div class="card-head">
    <div class="card-icon"><i data-lucide="bar-chart-3"></i></div>
    <div class="grow">
      <div class="card-title">Riesgos por categoria</div>
      <div class="card-sub">Registro consolidado del portafolio</div>
    </div>
    <a class="icon-btn" href="#"><i data-lucide="arrow-up-right"></i></a>
  </div>
  ...
</section>
```

Hero verde tipo "VISA" (un solo por vista):

```html
<section class="card card-green">
  <div class="card-head">
    <div class="grow"><div class="card-title">Indice de criticidad</div><div class="card-sub">Promedio del portafolio</div></div>
    <span class="icon-btn glass"><i data-lucide="radar"></i></span>
  </div>
  <div class="num xl">35<span class="dec">.4</span> <span class="unit" style="font-size:var(--fs-18)">/ 100</span></div>
</section>
```

## 4. Botones y seleccion

```html
<a class="btn btn-primary btn-arrow" href="mapa.html">Ver el mapa <span class="arrow"><i data-lucide="arrow-up-right"></i></span></a>
<a class="btn btn-outline" href="explorar.html"><i data-lucide="table-2"></i> Explorar los datos</a>
<button class="btn btn-lime sm">Abrir mapa</button>

<div class="seg" role="tablist">           <!-- .seg.light para navegacion -->
  <button class="on" data-v="amenaza">Amenazas</button>
  <button data-v="oportunidad">Oportunidades</button>
</div>

<div class="chips">
  <button class="chip on">Todas</button><button class="chip">Ambiental</button>
</div>
<span class="chip warn"><i data-lucide="flask-conical"></i><span class="txt">Datos sinteticos</span></span>
```

## 5. Datos

```html
<div class="num lg">200</div>
<div class="num xl">35<span class="dec">.4</span></div>   <!-- usa ui.num(35.4) -->
<span class="trend">+12 esta semana</span>  <span class="trend down">+14.6</span>
<span class="lvl alto">Alto</span>            <!-- chip solido, listas cortas -->
<span class="lvl-soft critico"><span class="dot critico"></span>Critico</span>
<span class="status"><span class="dot alto"></span>Proximo a materializarse</span>

<div class="ring" style="--p:54;--c:var(--lvl-alto)">
  <div><div class="num md">54</div><div class="muted" style="font-size:11px">ICT</div></div>
</div>

<div class="meter"><span style="width:62%"></span></div>
<div class="kv"><span class="k">Confianza</span><span class="v">80%</span></div>
```

## 6. Tabla y listas

```html
<div class="table-wrap" style="max-height:420px">
  <table class="table">
    <thead><tr><th class="sortable" data-col="id_riesgo">Riesgo</th><th>Estado</th></tr></thead>
    <tbody>
      <tr>
        <td><div class="cell-main"><span class="tile" style="background:#e6f6ec;color:#1d7a42"><i data-lucide="leaf"></i></span>
          <div><div class="t">RSK-0016</div><div class="s">Ambiental</div></div></div></td>
        <td><span class="status"><span class="dot bajo"></span>Latente</span></td>
      </tr>
    </tbody>
  </table>
</div>

<a class="list-item">
  <span class="tile"><i data-lucide="triangle-alert"></i></span>
  <div class="grow"><div class="t">Paquete 4 - Centro</div><div class="s">Convergen 6 categorias</div></div>
  <i data-lucide="arrow-up-right"></i>
</a>
```

## 7. Formularios

```html
<label class="label">Categoria</label>
<select class="field">...</select>

<input type="range" class="range" min="0" max="1" step="0.01" value="0.28" style="--val:28">
<!-- JS: el.style.setProperty('--val', el.value * 100) en cada 'input' -->

<label class="switch"><input type="checkbox" checked><span></span></label>
```

## 8. Mapa

```html
<div class="map-card">
  <div id="mapa"></div>
  <div class="map-overlay" style="top:16px;left:16px">
    <div class="map-search"><i data-lucide="search"></i><input placeholder="Buscar paquete"></div>
  </div>
  <div class="map-overlay map-ctrls" style="top:16px;right:16px">
    <button class="map-btn on" title="Satelite"><i data-lucide="satellite"></i></button>
    <button class="map-btn" title="Capas"><i data-lucide="layers"></i></button>
  </div>
  <div class="map-overlay map-zoom" style="bottom:16px;right:16px">
    <button><i data-lucide="plus"></i></button><button><i data-lucide="minus"></i></button>
  </div>
  <div class="map-overlay pop-card" style="top:16px;right:72px"> ... </div>
</div>
```

Popover de capas (oscuro):

```html
<div class="pop-dark">
  <div class="ttl">Capas</div>
  <label class="row"><i data-lucide="hexagon"></i><span class="grow">Paquetes (ICT)</span>
    <span class="switch"><input type="checkbox" checked><span></span></span></label>
</div>
```

## 9. Chart.js (v4)

Leer colores con `ui.css('--green-600')`. Registrar los helpers de `ui.js`:
`ui.hatch(ctx, fondo, raya)` crea el patron rayado; `ui.bubblePlugin`
dibuja la burbuja sobre la barra maxima.

```js
const valores = [33, 28, 34, 40, 35, 30];
const max = Math.max(...valores);
const ctx = canvas.getContext('2d');
const base = ui.hatch(ctx, ui.css('--green-200'), ui.css('--green-300'));
const top  = ui.hatch(ctx, ui.css('--green-700'), ui.css('--green-800'));
new Chart(canvas, {
  type: 'bar',
  data: { labels, datasets: [{ data: valores,
    backgroundColor: valores.map(v => v === max ? top : base),
    borderRadius: 999, borderSkipped: false, barPercentage: 0.78, categoryPercentage: 0.9 }] },
  options: {
    maintainAspectRatio: false,
    layout: { padding: { top: 28 } },
    plugins: { legend: { display: false }, tooltip: ui.tooltip() },
    scales: {
      x: { grid: { display: false }, border: { display: false }, ticks: { color: ui.css('--muted') } },
      y: { grid: { color: ui.css('--line') }, border: { display: false, dash: [4, 4] },
           ticks: { color: ui.css('--muted'), maxTicksLimit: 5, precision: 0 } },
    },
  },
  plugins: [ui.bubblePlugin],
});
```

Area con degradado:

```js
const g = ctx.createLinearGradient(0, 0, 0, canvas.height);
g.addColorStop(0, ui.alpha(ui.css('--green-600'), .28)); g.addColorStop(1, ui.alpha(ui.css('--green-600'), 0));
dataset = { data, borderColor: ui.css('--green-600'), borderWidth: 2, fill: true, backgroundColor: g, tension: .4, pointRadius: 0 };
```

Radar (seleccion vs promedio):

```js
{ type: 'radar', data: { labels, datasets: [
  { label: 'Este paquete', data: a, borderColor: ui.css('--green-600'), backgroundColor: ui.alpha(ui.css('--green-600'), .18), pointRadius: 2 },
  { label: 'Promedio', data: b, borderColor: ui.css('--orange'), backgroundColor: ui.alpha(ui.css('--orange'), .12), pointRadius: 2 } ] },
  options: { plugins: { legend: { display: false } }, scales: { r: { min: 0, max: 1, ticks: { display: false },
    grid: { color: ui.css('--line') }, angleLines: { color: ui.css('--line') },
    pointLabels: { color: ui.css('--ink-2'), font: { size: 11 } } } } } }
```

## 10. Leaflet

```js
const mapa = L.map('mapa', { zoomControl: false, attributionControl: true });
const bases = {
  satelite: L.layerGroup([
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 18, attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics' }),
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 18, opacity: .85 }),
  ]),
  claro: L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    { maxZoom: 19, subdomains: 'abcd', attribution: '&copy; OpenStreetMap &copy; CARTO' }),
};

// Paquete: borde blanco, relleno por nivel, etiqueta tag permanente
L.geoJSON(fc, {
  style: f => ({ color: '#fff', weight: 2, fillColor: ui.nivelColor(f.properties.nivel), fillOpacity: .45 }),
  onEachFeature: (f, layer) => layer.bindTooltip(f.properties.id_paquete,
    { permanent: true, direction: 'center', className: 'map-tag' }),
});

// Heat con gradiente de niveles (nunca el arcoiris por defecto)
L.heatLayer(puntos, { radius: 30, blur: 24, minOpacity: .25, gradient: {
  0.25: ui.css('--lime'), 0.5: ui.css('--lvl-medio'), 0.75: ui.css('--lvl-alto'), 1: ui.css('--lvl-critico') } });
```
