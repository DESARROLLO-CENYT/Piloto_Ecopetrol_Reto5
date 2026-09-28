# Piloto Reto 5 - Mapa de riesgos (DATOS SINTETICOS)

Demostracion end-to-end del modelo multicriterio descrito en `Propuesta_Reto_5_v2.docx`:
Bronce -> Plata -> Oro, calculo del Indice de Criticidad Territorial (ICT), mapa de
calor y alertas, sobre datos **completamente inventados**.

**Nada de lo que hay aqui es informacion real de Ecopetrol, de La Guajira ni de
ninguna comunidad.** Los proyectos, paquetes de trabajo, comunidades, areas
protegidas y el registro de riesgos son generados por `src/generar_datos.py`.
Sirve para validar el mecanismo del modelo y el flujo de datos, no para sacar
conclusiones sobre riesgos reales.

## Que incluye

- **Motor multicriterio** (`src/modelo/ict.py`): Indice de Criticidad Territorial
  (ICT) 0-100 por paquete de trabajo, con normalizacion, decaimiento por
  distancia, agregacion configurable y contribucion por criterio.
- **AHP** (`src/modelo/ahp.py`): ejemplo de derivacion de pesos por comparacion
  por pares, con razon de consistencia.
- **Estadistica espacial** (`src/modelo/espacial.py`): kernel density para el
  mapa de calor y Getis-Ord Gi* para puntos calientes significativos.
- **Pipeline Bronce/Plata/Oro** (`src/generar_datos.py`, `src/bronce_a_plata.py`,
  `src/plata_a_oro.py`).
- **Validacion** (`src/validacion.py`): backtest contra eventos materializados
  y analisis de sensibilidad de los pesos.
- **API + frontend** (`app/`): FastAPI + Leaflet + Chart.js, sin build step.
  El diseno sigue la skill de proyecto `.claude/skills/reto5-design/`
  (tokens, componentes y recetas derivados de las referencias en `multimedia/`).
- **Exportacion SIG** (`src/exportar_gis.py`): GeoPackage listo para ArcGIS/QGIS.

Los parametros del modelo (pesos, umbrales, radios de influencia) estan en
[`parametros.yaml`](parametros.yaml), versionados y separados del codigo.

## Arranque con un solo comando

Desde la carpeta del proyecto (local o de red), con Python 3.12 instalado:

```bash
py -3.12 iniciar.py
```

Crea el entorno virtual en una carpeta local de cada PC (`%LOCALAPPDATA%\reto5-piloto`),
instala dependencias solo la primera vez, genera los datos si faltan, levanta
el servidor y abre el navegador. Opciones: `--regenerar`, `--red` (para abrirlo
desde otros PC de la red), `--puerto 8001`, `--sin-navegador`. En Windows
tambien sirve doble clic sobre `iniciar.bat`.

Copia compartida del equipo: `\\192.168.1.2\cenyt-desarollo\RETO-ECOPETROL\piloto`
(`py -3.12 \\192.168.1.2\cenyt-desarollo\RETO-ECOPETROL\piloto\iniciar.py`).

## Como correrlo en otro PC (paso a paso manual)

Requisitos: **Python 3.12** e **internet** (el frontend carga fuentes, Leaflet,
Chart.js, iconos y los mapas base desde CDN; sin conexion la pagina abre pero
sin mapa ni graficos).

1. Copiar la carpeta `piloto/` completa **sin** `.venv/` (el entorno virtual
   guarda rutas de este equipo y no funciona en otro; OneDrive lo sincroniza
   igual, asi que si llega, borrarlo en el otro PC y recrearlo).
2. Crear el entorno e instalar dependencias (una sola vez), desde `piloto/`:

   Windows:
   ```bash
   py -3.12 -m venv .venv
   .venv/Scripts/python.exe -m pip install -r requirements.txt
   ```
   Mac / Linux:
   ```bash
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```
3. Datos: si `data/gold/` ya viene copiada se puede saltar este paso. Para
   regenerar todo (Pasos 1-4; tarda menos de un minuto):
   ```bash
   .venv/Scripts/python.exe ejecutar_pipeline.py
   ```
   Los datos salen iguales por la semilla 42, salvo las fechas, que se
   calculan desde el dia en que se corre.
4. Levantar la aplicacion y abrir `http://127.0.0.1:8000`:
   ```bash
   .venv/Scripts/python.exe run_app.py
   ```
   (en Mac / Linux cambiar `.venv/Scripts/python.exe` por `.venv/bin/python`)

Opcional, GeoPackage para ArcGIS/QGIS (Paso 7):
```bash
cd src && ../.venv/Scripts/python.exe exportar_gis.py && cd ..
```

### Pruebas

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

## Guion de demo (5-7 minutos)

1. **Portada** (`http://127.0.0.1:8000`): ICT promedio, zonas en alerta y
   distribucion por categoria con datos vivos. Senalar el chip "Datos
   sinteticos" de la barra superior.
2. **Mapa** (base satelital): los 14 paquetes coloreados por nivel sobre el
   mapa de calor. Clic en una tarjeta del carrusel de alertas (abajo) o en
   un paquete: la tarjeta de detalle muestra el ICT como indicador circular,
   la causa de escalamiento y el **radar de criterios frente al promedio del
   portafolio** - el punto central de la propuesta: el modelo es explicable.
3. **Tab "Alertas"** del panel: las causas estan encadenadas al ICT para
   evitar falsos positivos.
4. **Tab "Modelo"**: mover los pesos y pulsar "Recalcular": cambian el
   ranking de "Zonas prioritarias", los colores y las alertas en vivo, sin
   tocar codigo. "Restablecer" vuelve a los pesos por defecto.
5. **Tab "Filtros"** y boton de capas (arriba a la derecha): puntos de riesgo
   por categoria/estado/tipo, comunidades, areas protegidas, hidrologia y
   vias. El boton de mapa alterna entre satelite y mapa claro.
6. **"Ver en datos"** desde la tarjeta de detalle abre Explorar filtrado por
   ese paquete: registro de riesgos ordenable, barras por categoria (clic en
   una barra filtra el registro) y riesgos identificados por semana.
7. **Datos y modelo**: recorrer la arquitectura medallion (que entra en
   Bronce, que limpia Plata, que produce Oro), las imperfecciones plantadas
   en los datos sinteticos, el catalogo de tablas con su linaje entre capas
   y la explicacion del ICT con el ejemplo del paquete mas critico.
8. **Terminal**: correr `validacion.py` en vivo (o mostrar su salida ya
   generada) para explicar el backtest y el analisis de sensibilidad, dejando
   claro que en este piloto es circular (eventos sinteticos generados con las
   mismas variables) y que la validacion real requiere el historial de
   Ecopetrol.
9. **Cerrar con el GeoPackage** (`exports/reto5_piloto.gpkg`) abierto en
   QGIS/ArcGIS, mostrando que la salida es agnostica del software SIG, tal
   como exige el Anexo 1 del reto.

## Limitaciones (leer antes de mostrar el piloto)

- **Backtest circular**: los eventos materializados sinteticos se generaron
  con las mismas variables que usa el modelo (zonas "calientes" plantadas a
  proposito). El backtest confirma que el mecanismo funciona, **no** que los
  pesos o criterios sean los correctos.
- **Pesos supuestos**: los valores en `parametros.yaml` son un punto de
  partida razonable, no una calibracion con expertos. Eso ocurre en la
  Fase 2 de la propuesta.
- **Geografia de referencia, entidades ficticias**: se usa la caja
  geografica de La Guajira solo para ubicar objetos inventados; ninguna
  comunidad, area protegida o via representa algo real.
- **IA/ML fuera de alcance**: intencionalmente, ver Seccion 12 de la
  propuesta ("Opciones de mejora y evolucion").
- **Stack de este piloto (local, FastAPI + Leaflet) no es la arquitectura de
  produccion propuesta** (Azure Data Factory + Databricks + ArcGIS Enterprise
  + Power BI, ver `Arquitectura.html`). Aqui se prioriza velocidad de
  demostracion; el modelo (`src/modelo/`) esta escrito para poder migrarse a
  PySpark/Sedona sin rehacer la logica.

## Estructura

```
piloto/
  parametros.yaml          # pesos, umbrales, radios - editable sin tocar codigo
  ejecutar_pipeline.py      # corre los pasos 1-4 en orden
  run_app.py                 # levanta la API + frontend
  src/
    generar_datos.py        # Paso 1: datos sinteticos (Bronce)
    bronce_a_plata.py        # Paso 2: limpieza y estandarizacion
    plata_a_oro.py            # Paso 3: modelo ICT + KDE + Getis-Ord
    validacion.py              # Paso 4: backtest + sensibilidad
    exportar_gis.py            # Paso 7: GeoPackage para ArcGIS/QGIS
    modelo/
      ict.py                    # motor del Indice de Criticidad Territorial
      ahp.py                     # derivacion de pesos por AHP
      espacial.py                # KDE y Getis-Ord Gi*
  app/
    main.py                   # FastAPI (Paso 5)
    static/                     # frontend sin build step
      tokens.css, components.css  # sistema de diseno (copiado de la skill)
      ui.js                        # topbar compartida y helpers de formato/graficos
      index.html  + home.*          # portada
      mapa.html   + mapa.*          # mapa (Leaflet)
      explorar.html + explorar.*    # exploracion de datos (Chart.js)
      datos.html  + datos.*         # descripcion de capas, tablas y modelo ICT
    catalogo.py                 # inventario vivo de Bronce/Plata/Oro para /api/catalogo
  .claude/skills/reto5-design/   # skill del sistema de diseno del frontend
  data/{bronze,silver,gold}/    # capas medallion (generadas, no versionar)
  exports/                       # GeoPackage y GeoJSON de salida
  tests/test_ict.py              # pruebas unitarias del modelo
```
#   P i l o t o _ E c o p e t r o l _ R e t o 5  
 