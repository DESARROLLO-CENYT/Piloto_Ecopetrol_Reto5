---
name: reto5-design
description: >
  Sistema de diseno (v2) del frontend del piloto Reto 5 - mapa de riesgos
  Ecopetrol / CEN&T. Define la estructura (app-shell flotante, topbar en
  pill, bento grid de tarjetas), tokens (color, tipografia Outfit+Inter,
  radios, sombras), componentes (botones pill, segmented control, chips de
  nivel, tarjetas con cabecera, tablas, sliders, controles de mapa oscuros,
  tarjeta flotante de alerta, gauge ICT) y recetas de graficos Chart.js y
  mapas Leaflet, todo derivado de las 4 referencias en piloto/multimedia/.
  Usa esta skill SIEMPRE que crees, edites o revises cualquier HTML, CSS o
  JS de interfaz en piloto/app/static/ (index, mapa, explorar o paginas
  nuevas), cuando agregues un grafico o una capa/control al mapa, o cuando
  el usuario hable de estilo, look, diseno, colores, "que se vea moderno",
  "como las fotos" o de reconfigurar la interfaz -- aunque no mencione la
  skill. No aplica al pipeline Python (src/).
---

# Sistema de diseno v2 - Piloto Reto 5

## Para que sirve y por que asi

El usuario puso 4 dashboards de Dribbble en `piloto/multimedia/` como
referencia de "moderno". La v1 de esta skill copio solo la paleta y los
radios, y el resultado seguia viendose como un formulario administrativo:
banner amarillo a todo el ancho, enlaces azules subrayados, etiquetas en
MAYUSCULAS espaciadas, numeros en peso 800, controles grises de Leaflet y
tiles de OpenStreetMap. Lo que hace modernas a las referencias no es el
color: es la **estructura** (app flotante dentro de un lienzo, barra
superior en pill, tarjetas con cabecera consistente, tipografia liviana con
jerarquia por tamano y tono) y el **detalle** (iconos en circulos, un solo
acento fuerte por vista, graficos tono-sobre-tono con un valor destacado).

Esta v2 describe esas estructuras como recetas. Antes de escribir CSS nuevo,
revisa si ya existe el componente en `components.css`; casi todo lo que una
pagina necesita deberia salir de ahi, y cada pagina solo aporta su layout.

Abre las imagenes de referencia (`Read` sobre el .jpg) cuando dudes de un
detalle visual: son la fuente de verdad, esta skill es su traduccion.

## Mapa de referencias: que tomar de cada una

| Referencia | Tomar | No tomar |
|---|---|---|
| **Ejemplo_1** (Quixotic, fintech) | App-shell gris con tarjetas blancas, topbar pill con nav segmentada, rail de iconos, cabecera de tarjeta (titulo + subtitulo gris + boton circular ↗), tarjeta verde tipo "VISA", barras redondeadas rayadas con burbuja de valor, area con degradado, numeros con decimales grises, trend pills "+12.8%", tabla sin bordes con fila resaltada como banda redondeada, estado con punto | Avatares de personas, tema financiero |
| **Ejemplo_2** (mapa de perfiles) | Barra de busqueda blanca en pill flotando sobre el mapa, marcadores con anillo, carrusel de tarjetas sobre el borde inferior del mapa con la seleccionada rellena en verde, chips tipo "skills", slider de rango | Sidebar verde oscuro texturizado (demasiado pesado junto al resto) |
| **Ejemplo_3** (GIS agricola) - **la mas cercana al dominio** | Panel izquierdo blanco (titulo grande + segmented + chip de fecha + "Parametros"), mapa satelital con contornos blancos y etiquetas en tag blanco, pila de botones oscuros cuadrados arriba a la derecha, zoom oscuro vertical abajo a la derecha, tarjeta flotante de alerta (icono de aviso, chip de fecha, pill navy con el problema, fila de parametros, botones Cancel/Delete), radar comparativo, tabla de zonas con chips de color | Minimap (no aporta con nuestras escalas) |
| **Ejemplo_4** (Harvesta) | Pastillas de vidrio sobre el mapa con icono en circulo, acento lima para UNA llamada a la accion, tarjetas oscuras translucidas, anillo de progreso grande | La foto de persona, el verde oliva general |

## Principios (en orden de importancia)

1. **La app es un objeto flotante.** Lienzo `--canvas` gris, y encima un
   `.shell` redondeado (`--r-xl`) con padding de 14px que contiene todo. Las
   tarjetas blancas viven dentro con 14px de separacion. Esto es lo que mas
   "moderniza" -- sin shell, todo se ve pegado al navegador.
2. **Todo lo interactivo es pill o circulo.** Botones, inputs, selects,
   chips, tabs, nav. Nunca un boton rectangular al lado de uno redondeado.
   Excepcion: los controles del mapa son cuadrados redondeados (`--r-sm`)
   oscuros, como en Ejemplo_3, porque son herramientas, no acciones.
3. **Jerarquia por tamano y tono, no por peso.** Titulos y numeros en
   `Outfit` peso 500 (600 maximo). La segunda parte de un titulo y los
   decimales de un numero van en `--muted` ("Riesgos, *La Guajira*",
   "35.*4*"). Etiquetas en minuscula de oracion y `--muted`, nunca en
   MAYUSCULAS con letter-spacing.
4. **Un acento fuerte por vista.** El verde lleno (`--green-600`) marca lo
   activo/seleccionado/destacado: el tab activo, la barra maxima, la tarjeta
   hero, el boton primario. El lima (`--lime`) solo para UNA llamada a la
   accion sobre fondo oscuro. Si hay tres cosas verdes compitiendo, sobra
   alguna.
5. **Oscuro solo para herramientas sobre el mapa** (controles, popover de
   capas, tarjeta de teaser). Datos, formularios y tablas van en claro.
6. **Iconos en todas partes, siempre dentro de un circulo o tile.** Lucide
   (ver "Iconos"). Una tarjeta sin icono ni boton ↗ en la cabecera se ve
   incompleta junto a las demas.
7. **Graficos tono-sobre-tono con un solo valor destacado.** Nunca la paleta
   por defecto de Chart.js ni el arcoiris por defecto de leaflet.heat.
8. **Sin sombras pesadas en tarjetas** (casi planas, blanco sobre gris).
   La sombra fuerte (`--sh-float`, `--sh-pop`) es solo para lo que flota
   sobre el mapa.

## Archivos del sistema

| Archivo | Rol |
|---|---|
| `assets/tokens.css` | Variables CSS. Copiar a `piloto/app/static/tokens.css` |
| `assets/components.css` | Componentes compartidos (shell, topbar, card, btn, seg, chips, tabla, slider, controles de mapa...). Copiar a `piloto/app/static/components.css` |
| `references/components.md` | Snippets HTML de cada componente y recetas JS (Chart.js, Leaflet). Leelo antes de construir una pagina o un grafico nuevo |

Toda pagina carga, en este orden: fuentes de Google (Outfit + Inter),
`tokens.css`, `components.css`, luego su CSS propio (`home.css`,
`mapa.css`, `explorar.css`) que solo define layout. Y al final Lucide +
`ui.js` (topbar compartida, helpers de formato y color).

Si cambias un token o un componente, hazlo en la skill (`assets/`) y copia
a `static/`; asi la skill sigue siendo la fuente de verdad.

## Tokens clave (valores completos en `assets/tokens.css`)

- Lienzo/superficies: `--canvas #e6e9e6`, `--shell #f3f4f2`, `--surface #fff`, `--surface-muted #f4f5f3`, `--line #eaecea`.
- Texto: `--ink #121814`, `--ink-2 #4a524d`, `--muted #8a928d`.
- Verde marca (escala de Ejemplo_1): `--green-50 #eef7f1` ... `--green-600 #178a58` (primario) ... `--green-900 #083d27`.
- Acentos: `--lime #cdf04a`, `--navy #1f3864` (CEN&T, pills de problema como en Ejemplo_3), `--orange #f2751f` (CEN&T, avisos).
- Oscuro (controles de mapa): `--night #141a17`, `--night-2 #222a26`.
- Niveles ICT: `--lvl-bajo #3fb56b`, `--lvl-medio #f1c232` (texto oscuro encima), `--lvl-alto #f28a30`, `--lvl-critico #e2483a`, cada uno con su `-bg` suave.
- Tipografia: `--font-display 'Outfit'` (titulos, numeros), `--font-ui 'Inter'` (todo lo demas). Escala `--fs-11` ... `--fs-64`.
- Radios: `--r-xs 8`, `--r-sm 12`, `--r-md 16`, `--r-lg 24` (tarjetas), `--r-xl 32` (shell), `--r-pill`.
- Sombras: `--sh-card` (casi nula), `--sh-float` (sobre mapa), `--sh-pop` (tarjeta de detalle).

## Catalogo de componentes (clases en `components.css`)

- **Estructura**: `.shell`, `.topbar` (con `.brand`, `.nav-seg`, `.topbar-right`), `.page-head` (titulo de dos tonos + acciones a la derecha), `.bento` (grid de 12 columnas, `.span-3` ... `.span-12`).
- **Tarjeta**: `.card` + `.card-head` (`.card-icon`, `.card-title`, `.card-sub`, `.icon-btn` ↗ a la derecha). Variantes `.card-green` (hero tipo VISA, con rayado), `.card-night` (oscura).
- **Acciones**: `.btn` + `.btn-primary` / `.btn-outline` / `.btn-dark` / `.btn-lime`; `.btn-arrow` (circulo interno con flecha, CTA principal). `.icon-btn` (circulo 40px), `.icon-btn.sm`, `.icon-btn.glass`.
- **Seleccion**: `.seg` (track gris, activo verde) y `.seg.light` (activo blanco, para navegacion). `.chip`, `.chip.on`, `.chip.warn`, `.chips` (grupo).
- **Datos**: `.num` (+ `<span class="dec">`), `.trend` / `.trend.down`, `.lvl.bajo|medio|alto|critico` (chip solido, Ejemplo_3), `.lvl-soft`, `.status` (punto + texto, Ejemplo_1), `.dot`, `.ring` (gauge conico con `--p` y `--c`), `.meter` (barra fina), `.medal.bronce|plata|oro` (capa medallion), `.mono` (nombres de archivo/columna).
- **Tabla**: `.table` (cabeceras en minuscula gris, sin bordes, fila hover como banda redondeada), `.cell-main` (tile de icono + titulo + subtitulo).
- **Listas**: `.list-item` (tile + titulo/sub + ↗, como "Plant Stress" de Ejemplo_3).
- **Formularios**: `.field` (select/input en pill gris), `.range` (slider con relleno verde, usar `--val`), `.switch`.
- **Mapa**: `.map-card`, `.map-ctrls` + `.map-btn` (oscuros cuadrados), `.map-search`, `.glass` / `.glass-dark`, `.pop-card` (tarjeta de alerta/detalle), `.map-tag` (tooltip permanente de Leaflet como tag blanco), `.carousel` + `.alert-card`.

Snippets listos para copiar en `references/components.md`.

## Recetas por pagina

### Landing (`index.html`)
```
shell
 ├ topbar (Inicio activo)
 ├ hero: grid 7/5
 │   ├ card grande: chip outline de convocatoria · H1 64px dos tonos ·
 │   │  parrafo · [btn-primary + btn-arrow "Ver el mapa"] [btn-outline
 │   │  "Explorar los datos"] · fila "Desarrollado por [CEN&T] para [Ecopetrol]"
 │   └ bento 2x2 con datos vivos de la API: card-green (ICT promedio),
 │      card (zonas en alerta + puntos de nivel), card (mini barras por
 │      categoria, CSS puro), card-night (teaser del mapa + btn-lime)
 └ pie: una linea `--muted` con el aviso de datos sinteticos
```
El aviso de datos sinteticos vive como `.chip.warn` en la topbar de todas
las paginas; no uses banners de ancho completo.

### Mapa (`mapa.html`) - basado en Ejemplo_3
```
shell (alto fijo 100vh, sin scroll de pagina)
 ├ topbar (Mapa activo)
 └ fila: panel 360px | map-card (flex 1)
     panel: titulo pequeno + sub · H1 "Zonas de riesgo" · .seg
            [Modelo | Filtros | Alertas] · fila chip-fecha + "Parametros" ·
            contenido del tab · seccion "Zonas prioritarias" (tabla con .lvl)
     map-card, capas flotantes:
       arriba-izq: .map-search + fila glass de leyenda
       arriba-der: .map-ctrls (base satelital/clara, capas, recentrar)
       abajo-der:  .map-ctrls zoom (+/−)
       abajo:      .carousel de .alert-card (la seleccionada en verde)
       derecha:    .pop-card de detalle (gauge ICT, pill navy con la causa,
                   radar criterios vs promedio, filas de parametros,
                   [Cerrar] [Ver en datos])
```
Leaflet: `zoomControl:false`, sin `L.control.layers`; los controles son
HTML propio encima del mapa que llaman a la API de Leaflet. Base por defecto
satelital de Esri + etiquetas de referencia; alternativa CARTO Positron.
Paquetes con borde blanco 2px, relleno del color de nivel al 40-50%, y
etiqueta permanente `.map-tag`. Heat con gradiente de niveles (ver
references). Nunca OSM estandar ni el control de capas de Leaflet.

### Explorar (`explorar.html`) - basado en Ejemplo_1
```
shell
 ├ topbar (Explorar activo)
 ├ page-head: "Explorar datos, <muted>La Guajira</muted>" · chip fecha · btn-outline mapa
 └ bento
    fila 1: [card-green ICT promedio (4) + card stat riesgos con trend]
            [card barras por categoria con .seg de tipo (5)]
            [card area "identificados por semana" (3)]
    fila 2: [card tabla "Registro de riesgos" con filtros en .field (8)]
            [card "Paquetes prioritarios" lista con .lvl y ICT (4)
             + card "Estado de los riesgos" con .meter por estado]
```

### Datos y modelo (`datos.html`) - pagina descriptiva, no EDA
```
shell
 ├ topbar (Datos y modelo activo)
 ├ page-head + fila de anclas (.anclas) a las 4 secciones
 ├ bento de 4 stat cards (capas, tablas, registros en Oro, semilla)
 ├ card "Arquitectura medallion": .flujo de 5 .etapa (origen, bronce,
 │   plata, oro, consumo) con flecha circular entre etapas; cada capa usa
 │   su chip .medal y fondo --medal-*-bg
 ├ bento 7/5: "Que datos creamos" (grid de .dato) | "Imperfecciones a
 │   proposito" (.imp + embudo Bronce -> Plata)
 ├ card "Catalogo de tablas": .seg de capa + lista (list-item) | detalle
 │   (chips de metadatos, linaje entre capas, tabla de columnas con .tipo)
 └ page-head "El modelo" + bento: card-green formula, criterios con
     .meter de peso, escala de niveles, reglas, ejemplo con barra apilada,
     salidas complementarias, validacion
```
Todo numero de esta pagina sale de `/api/catalogo` y `/api/parametros`
(inventario vivo de los archivos), nunca escrito a mano en el HTML: si el
pipeline se vuelve a correr, la pagina sigue siendo verdadera. Los colores
`--medal-*` solo identifican capas medallion; no los uses como acento.

## Graficos y mapas (resumen; codigo en references)

- Barras: `borderRadius: 999`, `borderSkipped: false`, `barPercentage ~0.72`,
  relleno con patron rayado diagonal (`--green-300` sobre `--green-100`) y la
  barra maxima en `--green-700` con rayado oscuro + burbuja "valor" encima
  (plugin `bubbleOnMax`). Grilla horizontal punteada, sin eje vertical.
- Area: linea `--green-600` 2px, `tension 0.4`, relleno degradado vertical
  `--green-600` 25% -> 0%, sin puntos.
- Radar: dos series (seleccion en `--green-600`, promedio en `--orange`), como
  "This month / Last month" de Ejemplo_3.
- Gauge ICT: `.ring` con conic-gradient, nunca un Chart.js doughnut para un
  solo valor.
- Colores en JS: leelos de las variables CSS con `ui.css(name)` (en `ui.js`),
  no dupliques hex en JavaScript.

## Anti-patrones (errores reales de la v1, no repetir)

- Banner de color a todo el ancho para avisos -> usar `.chip.warn`.
- Enlaces azules subrayados para navegar -> topbar `.nav-seg`.
- `text-transform: uppercase` + `letter-spacing` en etiquetas -> minuscula `--muted`.
- `font-weight: 800` en numeros -> `Outfit` 500 con decimales grises.
- Controles por defecto de Leaflet, tiles OSM, gradiente arcoiris del heat.
- Badges solidos repetidos en 200 filas -> `.status` (punto + texto); el
  chip solido `.lvl` solo en listas cortas (<= 20 filas) o un unico valor.
- Tarjetas sin cabecera, o con `h3` suelto sin subtitulo ni icono.
- Sidebars largos que obligan a hacer scroll para llegar al boton principal
  -> dividir con `.seg` en tabs.

## Verificacion antes de dar por terminado

1. Abrir cada pagina en el navegador (preview) y tomar screenshot.
2. Ponerla al lado de su referencia (Landing/Explorar vs Ejemplo_1, Mapa vs
   Ejemplo_3) y revisar: shell flotante, topbar pill, cabeceras de tarjeta,
   un solo acento verde fuerte por vista, numeros livianos, iconos en
   circulos.
3. Revisar consola sin errores y probar las interacciones (tabs, filtros,
   sliders, clic en mapa, carrusel).
4. Revisar en ancho de 1280 y en 390 (movil): el bento colapsa a una columna
   y el panel del mapa pasa arriba del mapa.
