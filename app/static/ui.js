/* Helpers compartidos del frontend (ver .claude/skills/reto5-design). */
const ui = (() => {
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  const alpha = (color, a) => {
    const h = color.replace('#', '');
    const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  };

  const icons = () => { if (window.lucide) window.lucide.createIcons(); };

  async function json(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(`${url} -> ${r.status}`);
    return r.json();
  }

  // Llamadas que cambian datos (matriz RAM, supuestos, modelo, actualizar alertas). Desde el mismo equipo pasan sin
  // clave; desde otro equipo de la red el servidor pide la clave de edicion (RETO5_CLAVE_EDICION) y se pregunta una vez.
  async function escribir(url, opts = {}) {
    const leer = () => { try { return sessionStorage.getItem('reto5-clave') || ''; } catch (e) { return ''; } };
    const llamar = (clave) => fetch(url, { ...opts, headers: { ...(opts.headers || {}), ...(clave ? { 'X-Clave-Edicion': clave } : {}) } });
    let r = await llamar(leer());
    if (r.status === 401) {
      const clave = window.prompt('Para editar desde otro equipo se necesita la clave de edición de la aplicación:');
      if (!clave) return r;
      try { sessionStorage.setItem('reto5-clave', clave); } catch (e) { /* sin almacenamiento: se pregunta de nuevo */ }
      r = await llamar(clave);
    }
    return r;
  }

  // 35.4 -> "35<span class=dec>.4</span>" (decimales en gris, como Ejemplo_1)
  function num(v, dec = 1) {
    if (v == null || Number.isNaN(Number(v))) return '-';
    const [ent, frac] = Number(v).toFixed(dec).split('.');
    const entFmt = Number(ent).toLocaleString('es-CO');
    return frac ? `${entFmt}<span class="dec">.${frac}</span>` : entFmt;
  }

  const fecha = (d) => new Date(d).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });

  const NIVEL = { bajo: 'Bajo', medio: 'Medio', alto: 'Alto', critico: 'Crítico' };
  const nivelColor = (n) => css(`--lvl-${n}`) || css('--muted');

  const CATEGORIA = {
    social_comunidad: { label: 'Social / comunidad', corto: 'Social', icon: 'users', bg: '#eef1fb', fg: '#2d4a9a' },
    ambiental: { label: 'Ambiental', corto: 'Ambiental', icon: 'leaf', bg: '#e6f6ec', fg: '#1d7a42' },
    seguridad_fisica: { label: 'Seguridad física', corto: 'Seguridad', icon: 'shield-alert', bg: '#fce6e3', fg: '#a3261a' },
    logistico_acceso: { label: 'Logístico / acceso', corto: 'Logística', icon: 'truck', bg: '#fdeede', fg: '#a14f0c' },
    climatico: { label: 'Climático', corto: 'Clima', icon: 'cloud-rain', bg: '#e3f2fb', fg: '#1f6f99' },
    contractual: { label: 'Contractual', corto: 'Contrato', icon: 'file-text', bg: '#f1eefb', fg: '#5b3fa6' },
    sin_clasificar: { label: 'Sin clasificar', corto: 'Otro', icon: 'circle-dot', bg: '#f4f5f3', fg: '#4a524d' },
  };
  const cat = (k) => CATEGORIA[k] || CATEGORIA.sin_clasificar;

  const ESTADO = {
    latente: { label: 'Latente', lvl: 'bajo' },
    proximo_a_materializarse: { label: 'Próximo a materializarse', lvl: 'alto' },
    materializado: { label: 'Materializado', lvl: 'critico' },
  };

  // Matriz RAM de Ecopetrol: colores del formato ECP-DRI-F-045 (verde, amarillo claro, amarillo, naranja, rojo)
  const RAM = {
    N: { nombre: 'Ninguno', bg: '#5cbf6b', fg: '#0f3d1a' },
    L: { nombre: 'Bajo', bg: '#fbeea6', fg: '#5c4a00' },
    M: { nombre: 'Medio', bg: '#f6c945', fg: '#4d3b00' },
    H: { nombre: 'Alto', bg: '#f07d1a', fg: '#ffffff' },
    VH: { nombre: 'Muy alto', bg: '#d7191c', fg: '#ffffff' },
  };
  const DIM_RAM = { PE: 'Personas', EC: 'Económica', MA: 'Ambiental', CL: 'Clientes', IM: 'Imagen' };
  const ramChip = (nivel) => (nivel ? `<span class="ram-chip" style="background:${RAM[nivel].bg};color:${RAM[nivel].fg}" title="RAM ${RAM[nivel].nombre}">${nivel}</span>` : '<span class="ram-chip vacio">-</span>');

  const CRITERIOS = {
    severidad_riesgo: 'Severidad',
    vulnerabilidad_territorial: 'Vulnerabilidad',
    amenazas_externas: 'Amenazas externas',
    exposicion_proyecto: 'Exposición',
    convergencia: 'Convergencia',
  };

  // "Paquete 3 - Proyecto 1" -> "Paquete 3 · Proyecto 1" (ficha) y "Proy. 1 · P3" (etiqueta del mapa)
  const nombreCorto = (nombre) => {
    const m = /Paquete (\d+) - Proyecto (\d+)/.exec(nombre || '');
    return m ? `Paquete ${m[1]} · Proyecto ${m[2]}` : nombre;
  };
  const tagCorto = (nombre) => {
    const m = /Paquete (\d+) - Proyecto (\d+)/.exec(nombre || '');
    return m ? `Proy. ${m[2]} · P${m[1]}` : nombre;
  };

  // Patron rayado diagonal para barras (Ejemplo_1)
  function hatch(ctx, fondo, raya) {
    const c = document.createElement('canvas');
    c.width = c.height = 10;
    const x = c.getContext('2d');
    x.fillStyle = fondo;
    x.fillRect(0, 0, 10, 10);
    x.strokeStyle = raya;
    x.lineWidth = 2;
    x.beginPath();
    x.moveTo(-1, 11); x.lineTo(11, -1);
    x.moveTo(-1, 1); x.lineTo(1, -1);
    x.moveTo(9, 11); x.lineTo(11, 9);
    x.stroke();
    return ctx.createPattern(c, 'repeat');
  }

  function roundRect(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  // Burbuja con el valor sobre la barra maxima + punto en su tope (Ejemplo_1)
  const bubblePlugin = {
    id: 'bubbleOnMax',
    afterDatasetsDraw(chart) {
      const ds = chart.data.datasets[0];
      if (!ds || !ds.data.length) return;
      const valores = ds.data.map(Number);
      const i = valores.indexOf(Math.max(...valores));
      const bar = chart.getDatasetMeta(0).data[i];
      if (!bar) return;
      const c = chart.ctx;
      const fmt = chart.options.plugins?.bubbleOnMax?.format || ((v) => v);
      const texto = String(fmt(valores[i]));
      const verde = css('--green-600');
      c.save();
      c.font = `600 11px ${css('--font-ui') || 'Inter'}`;
      const w = c.measureText(texto).width + 16, h = 22;
      const bx = bar.x - w / 2, by = bar.y - h - 10;
      c.fillStyle = verde;
      roundRect(c, bx, by, w, h, 11);
      c.fill();
      c.beginPath();
      c.moveTo(bar.x - 4, by + h); c.lineTo(bar.x + 4, by + h); c.lineTo(bar.x, by + h + 5);
      c.fill();
      c.fillStyle = '#fff';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText(texto, bar.x, by + h / 2 + 0.5);
      const rDot = Math.min(6, (bar.width || 20) / 4);
      c.beginPath();
      c.arc(bar.x, bar.y + rDot + 3, rDot, 0, Math.PI * 2);
      c.fillStyle = '#fff';
      c.fill();
      c.lineWidth = 2.5;
      c.strokeStyle = verde;
      c.stroke();
      c.restore();
    },
  };

  const tooltip = () => ({
    backgroundColor: css('--night'),
    titleColor: css('--night-ink'),
    bodyColor: css('--night-ink'),
    padding: 10,
    cornerRadius: 10,
    displayColors: false,
    titleFont: { weight: '600' },
  });

  function topbar() {
    const el = document.getElementById('topbar');
    if (!el) return;
    const activo = el.dataset.active;
    const items = [
      ['inicio', 'index.html', 'house', 'Inicio'],
      ['mapa', 'mapa.html', 'map', 'Mapa'],
      ['explorar', 'explorar.html', 'chart-column', 'Explorar'],
      ['ram', 'matriz.html', 'grid-3x3', 'Matriz RAM'],
      ['ejecucion', 'ejecucion.html', 'timer', 'Ejecución'],
      ['modelo', 'modelo.html', 'sliders-horizontal', 'Ajustar'],
      ['datos', 'datos.html', 'database', 'Datos'],
      ['flujo', 'flujo.html', 'workflow', 'Flujo'],
    ];
    el.className = 'topbar';
    el.innerHTML = `
      <a class="brand" href="index.html">
        <span class="brand-mark"><i data-lucide="radar"></i></span>
        <span class="brand-name">Reto 5 <span>· ICT</span></span>
      </a>
      <nav class="nav-seg" aria-label="Secciones">
        ${items.map(([k, href, ic, txt]) => `
          <a href="${href}" class="${k === activo ? 'on' : ''}"${k === activo ? ' aria-current="page"' : ''}>
            <i data-lucide="${ic}"></i><span class="txt">${txt}</span></a>`).join('')}
      </nav>
      <div class="topbar-right">
        <span class="chip warn" title="Piloto de demostración: todos los datos son inventados y no representan proyectos, comunidades ni información real de Ecopetrol.">
          <i data-lucide="flask-conical"></i><span class="txt">Datos sintéticos</span></span>
        <span class="avatar-logo" title="Grupo Ecopetrol"><img src="img/logo-ecopetrol.png" alt="Grupo Ecopetrol"></span>
      </div>`;
  }

  if (window.Chart) {
    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = css('--muted');
  }
  topbar();
  icons();

  return {
    css, alpha, icons, json, escribir, num, fecha, NIVEL, nivelColor, CATEGORIA, cat, ESTADO, CRITERIOS, RAM, DIM_RAM, ramChip,
    nombreCorto, tagCorto, hatch, bubblePlugin, tooltip,
  };
})();
