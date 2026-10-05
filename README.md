# Piloto Reto 5 · Mapa de riesgos multicriterio

Piloto del **Índice de Criticidad Territorial (ICT)** para la convocatoria
*Transforma la Energía* (Reto 5, Grupo Ecopetrol), desarrollado por CEN&T
Ingenieros Consultores. Recorre de punta a punta el flujo de la propuesta:
arquitectura medallion (Bronce → Plata → Oro), modelo multicriterio explicable,
mapa de calor, alertas tempranas y una aplicación web para explorarlo.

> **Datos sintéticos.** Nada de lo que hay aquí es información real de
> Ecopetrol, de La Guajira ni de ninguna comunidad. Proyectos, paquetes de
> trabajo, comunidades, áreas protegidas, clima y el registro de riesgos los
> genera `src/bronce/sinteticos.py`. El piloto sirve para validar el mecanismo del
> modelo y el flujo de datos, no para sacar conclusiones sobre riesgos reales.

## Inicio rápido

Requisitos: [Git](https://git-scm.com/downloads), **Python 3.12** e internet
(la interfaz carga fuentes, mapas base, gráficos e iconos desde CDN).

```bash
git clone https://github.com/DESARROLLO-CENYT/Piloto_Ecopetrol_Reto5.git
cd Piloto_Ecopetrol_Reto5
py -3.12 iniciar.py
```

En Mac o Linux el último comando es `python3.12 iniciar.py`. En Windows también
sirve doble clic sobre `iniciar.bat`.

`iniciar.py` hace solo lo que falte, en este orden:

1. Crea el entorno virtual en una carpeta local del PC
   (`%LOCALAPPDATA%\reto5-piloto` en Windows, `~/.cache/reto5-piloto` en Mac/Linux).
2. Instala `requirements.txt` la primera vez (unos minutos) o cuando cambie.
3. Genera los datos sintéticos si no existe la capa Oro (menos de un minuto).
4. Descarga los **datos abiertos** que falten (sin clave): clima del IDEAM, vías
   de INVIAS e IGAC, ríos del IGAC y municipios del DANE. Unos minutos y
   necesita internet. Si algo falla, el piloto arranca igual con lo que haya.
5. Levanta la aplicación en `http://127.0.0.1:8000` y abre el navegador.

| Opción | Para qué |
|---|---|
| `--regenerar` | Vuelve a correr el pipeline completo, incluidas las descargas de datos abiertos |
| `--sin-ideam` | No descarga datos abiertos (no necesita internet para los datos) |
| `--red` | Permite abrir la aplicación desde otros PC de la red local (muestra la IP) |
| `--puerto 8001` | Usa otro puerto si el 8000 está ocupado |
| `--sin-navegador` | No abre el navegador |

`Ctrl+C` en la terminal detiene el servidor.

### Actualizar a la última versión

Desde la carpeta del repositorio:

```bash
git pull
py -3.12 iniciar.py
```

Si cambió `requirements.txt`, `iniciar.py` reinstala las dependencias solo.
Si cambió el modelo o el generador de datos, agrega `--regenerar`.

## Qué incluye

**Aplicación** (`app/`, FastAPI + Leaflet + Chart.js, sin paso de compilación):

- **Inicio**: resumen con el ICT promedio y la distribución de riesgos.
- **Mapa**: versión simple, sin el modelo. Dos mapas base sin clave (satélite
  de Esri y calles de OpenStreetMap) y capas que se apilan con un
  interruptor cada una: proyectos y paquetes (sintéticos), los 15 municipios
  con su nombre (reales, del DANE), una sola capa de vías (reales: la red
  nacional de INVIAS en naranja grueso y la complementaria del IGAC en rosa,
  en siete clases con leyenda y kilómetros de cada una), ríos y cuerpos de
  agua (reales, del IGAC), riesgos (sintéticos, con filtros)
  y clima real del IDEAM, con cada variable como su propia capa: lluvia
  (acumulada a 7, 14 o 30 días), temperatura, viento (con flecha de dirección),
  humedad del aire y del suelo, presión, nivel del río y radiación. Muestra la
  lectura de las últimas horas (consultada en vivo) y, al hacer clic en una
  estación, todas sus variables, la serie de 30 días y la comparación con la
  normal climatológica del mes.
- **Explorar**: registro de riesgos ordenable y filtrable, riesgos por
  categoría y por semana, paquetes prioritarios.
- **Datos y modelo**: arquitectura medallion, qué datos se crearon, catálogo
  de tablas con su linaje y la explicación del ICT, todo leído en vivo de los
  archivos.

**Pipeline de datos** (`src/`), organizado por capa medallion. La explicación
completa (reglas de cada capa, limpieza por fuente, auditoría, cómo agregar una
fuente) está en **[docs/PIPELINE.md](docs/PIPELINE.md)**.

```
src/
  comun/      rutas de las capas, CRS, cliente HTTP, serialización, utilidades del IDEAM
  bronce/     descarga o genera los datos TAL COMO LLEGAN (solo esta capa usa internet)
  plata/      limpia, valida y concilia: lee Bronce, escribe Plata
  oro/        productos para consumir (mapa, API, modelo): lee SOLO Plata
  consumo/    salidas para otros programas (GeoPackage)
  modelo/     motor del ICT, derivación de pesos por AHP y estadística espacial
  pipeline.py definición de los pasos (capa, qué lee, qué escribe) y su orden
  auditoria.py, documentar.py
```

| Fuente | Bronce | Plata | Oro | En el mapa |
|---|---|---|---|---|
| **Datos sintéticos** (semilla 42) | `bronce.sinteticos` | `plata.sinteticos` | `oro.ict`, `oro.validacion` | proyectos y riesgos |
| **Clima del IDEAM** (datos.gov.co) | `bronce.ideam` | `plata.ideam` | `oro.ideam` | clima, una capa por variable |
| **Red vial** INVIAS + IGAC | `bronce.invias`, `bronce.vias_igac` | `plata.invias`, `plata.vias_igac`, `plata.red_vial` | `oro.red_vial` | vías (una sola red, dos fuentes) |
| **Ríos** del IGAC | `bronce.hidrografia` | `plata.hidrografia` | `oro.hidrografia` | ríos y agua |
| **Municipios** del DANE | `bronce.municipios` | `plata.municipios` | `oro.municipios` | municipios |

Reglas que el código hace cumplir: solo Bronce toca la red; Oro no lee Bronce
(lo que necesita del origen viaja en `proveniencia_<fuente>.json`, que escribe
Plata); Plata no lee Oro; cada archivo lo escribe un solo paso; y cada paso
reemplaza sus salidas completas. `python ejecutar_pipeline.py --auditar`
comprueba además que las tres capas están completas, que las cuentas cuadran
(lo que entra menos lo descartado es lo que sale) y que no sobran archivos.

El resto del código: `app/clima_vivo.py` consulta el flujo de las últimas horas
del IDEAM en vivo (caché de 10 minutos, con la misma limpieza de Plata y el
respaldo local si no hay internet); `modelo/ict.py`, `modelo/ahp.py` y
`modelo/espacial.py` son el motor del ICT.

Los parámetros del modelo (pesos, umbrales, radios de influencia) viven en
[`parametros.yaml`](parametros.yaml), separados del código.

## Comandos individuales

Con el entorno que crea `iniciar.py` (en Windows,
`%LOCALAPPDATA%\reto5-piloto\venv\Scripts\python.exe`; abajo abreviado como `python`):

```bash
python ejecutar_pipeline.py                    # todo, en orden de dependencias (descarga datos abiertos)
python ejecutar_pipeline.py --sin-red          # todo lo local, con el Bronce que ya hay
python ejecutar_pipeline.py --capa plata       # solo una capa: bronce, plata, oro o consumo
python ejecutar_pipeline.py --fuente ideam     # una fuente y todo lo que depende de ella
python ejecutar_pipeline.py --lista            # muestra el plan (pasos, orden, qué lee y escribe)
python ejecutar_pipeline.py --auditar          # al terminar, revisa la coherencia de las tres capas
python ejecutar_pipeline.py --limpiar-huerfanos  # borra archivos de data/ que ningún paso declara
python run_app.py                              # solo el servidor
python -m pytest tests/ -v                     # pruebas de limpieza, modelo y arquitectura
cd src && python -m plata.ideam                # un paso suelto (cualquier módulo de bronce, plata, oro)
cd src && python -m auditoria                  # solo la auditoría
cd src && python -m documentar                 # regenera las tablas automáticas de docs/PIPELINE.md
```

Fuentes: `sinteticos`, `ideam`, `invias`, `vias_igac`, `hidrografia`,
`municipios`, `red_vial`, `ict`, `validacion`. Para probar el pipeline sin tocar
`data/`, define `PILOTO_DATA` con otra carpeta.

### Instalación manual (sin `iniciar.py`)

```bash
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe ejecutar_pipeline.py
.venv/Scripts/python.exe run_app.py
```

En Mac o Linux: `python3.12 -m venv .venv` y `.venv/bin/python` en lugar de
`.venv/Scripts/python.exe`.

## Guion de demo (5 a 7 minutos)

1. **Inicio** (`http://127.0.0.1:8000`): ICT promedio y riesgos por categoría
   con datos vivos. Señalar el chip "Datos sintéticos" de la barra superior.
2. **Mapa, capa por capa**: el mapa abre con solo los municipios (con su
   nombre) y los proyectos; el resto está apagado. Con "Elegir municipios" se
   quitan o ponen municipios uno a uno. Luego encender las vías, los ríos, los
   riesgos (con filtros) y el clima, y alternar entre satélite y mapa de calles.
   Cada capa lleva su etiqueta: "Sintético" o el nombre de la fuente real.
3. **Clima real**: encender una o varias variables. Con una sola, cada estación
   muestra una pastilla de color; con dos o más, una ficha (tabla con una celda
   por variable) que se coloca sin taparse con las demás, unida a su estación
   por una línea. En lluvia, elegir entre 7, 14 y 30 días; el indicador dice si la lectura es en vivo.
   Clic en una estación: todas sus variables, la serie de 30 días y cuánto
   llovió frente a lo normal del mes. Aclarar que es clima medido por el IDEAM
   sobre proyectos y riesgos inventados.
4. **Datos y modelo → "Clima real: IDEAM"**: qué se descarga, en qué formato y
   granularidad, cómo se obtiene y los problemas hallados en la fuente
   (duplicados, coordenadas invertidas, consultas que se agotan).
5. **Datos y modelo, resto**: qué entra en Bronce, qué limpia Plata, qué produce
   Oro, las imperfecciones plantadas y el catálogo de tablas con su linaje.
6. **Explorar**: registro de riesgos ordenable y filtrable; un clic en una
   barra de categoría filtra la tabla.
7. **El modelo ICT** (sección al final de Datos y modelo): la fórmula, los cinco
   criterios y el ejemplo del paquete más crítico. Ya no está en el mapa; queda
   como base para decidir cómo construirlo de nuevo.
8. **Cierre**: el GeoPackage (`exports/reto5_piloto.gpkg`) abierto en QGIS o
   ArcGIS, para mostrar que la salida no depende de un software SIG.

## Limitaciones (leer antes de mostrar el piloto)

- **Backtest circular**: los eventos materializados sintéticos se generaron
  con las mismas variables que usa el modelo. Confirma que el mecanismo
  funciona, **no** que los pesos o criterios sean los correctos; eso requiere
  el histórico real de Ecopetrol.
- **Pesos supuestos**: los de `parametros.yaml` son un punto de partida, no
  una calibración con expertos (Fase 2 de la propuesta).
- **El clima del mapa es real, el del ICT no.** La capa de clima muestra datos
  medidos por el IDEAM, pero el criterio climático del ICT sigue usando la serie
  simulada (`clima_sintetico.*`). Conectarlo a los datos reales es un paso
  pendiente.
- **Otras variables del IDEAM.** El conjunto de "humedad" trae sobre todo humedad
  del suelo; la del aire tiene serie de 30 días solo en 1 estación (en las demás
  hay únicamente las últimas horas). El nivel del mar no tiene estaciones en La
  Guajira y el del río, solo 2 con serie. La radiación solo existe como promedio
  mensual en 7 estaciones. Presión y nivel se muestran sin escala de color: el
  valor depende de la altitud o del cauce. Las lecturas en vivo dependen de
  que el portal responda; si no, se muestra el respaldo y se avisa.
- **Lluvia del IDEAM: alcance y supuestos.** Solo una fracción de las
  estaciones activas de La Guajira reporta lectura reciente (cuántas cambia con
  cada descarga y se ve en *Datos y modelo*), algunas con huecos (borde punteado en el
  mapa: cobertura menor a 50 %, acumulado posiblemente subestimado). Se
  interpreta cada lectura como los mm caídos en su intervalo (verificado en las
  estaciones descargadas: pasos de 0,2 mm, no acumulados). Las consultas al
  portal pueden tardar o agotarse; la descarga reintenta y sigue con las
  estaciones que responden.
- **Vías: una red, dos fuentes.** La red vial unificada suma ~18.630 km sin
  contar nada dos veces. La parte nacional de INVIAS son solo 8 tramos (~300 km:
  rutas 80, 88, 90 y 49), con la superficie "por definir" (se completó con la
  del IGAC, que puede estar desactualizada: dos tramos de primer orden figuran
  "sin pavimentar") y el nombre "Por Defnir"; su territorial no coincide exacta
  con el límite departamental. La parte complementaria del IGAC (1:100.000) trae
  ~18.300 km, incluida
  la alta Guajira: solo 782 km pavimentados, 11.500 km que únicamente se
  transitan en tiempo seco y 5.800 km de caminos y senderos; casi ninguna vía
  tiene nombre (4 de 5.600). La clase de vía (tipos 1 a 7) la fuente no la
  explica: se interpretó de sus atributos (cada tipo trae siempre la misma
  combinación de superficie, ancho y accesibilidad). Es cartografía a escala
  1:100.000: puede faltar lo reciente y no dice el estado de hoy. Licencia del
  IGAC: uso libre solo sin fines comerciales. Las vías reales aún no alimentan
  el criterio de accesibilidad del ICT, que usa las vías sintéticas.
- **Municipios: versión de los límites.** La geometría es del MGN con año 2005
  (campo `MPIO_NANO`), base del IGAC: los bordes pueden diferir de los
  vigentes, y no verifiqué la licencia del servicio (el DANE publica el MGN
  como dato abierto; hay que citar la fuente). Algunas estaciones del
  catálogo caen fuera de los 15 polígonos (casi todas en la costa o el mar) y
  otras en un municipio distinto del que declaran; el mapa las cuenta por su
  ubicación y el conteo exacto queda en `reporte_cruces_municipios.csv`.
- **Ríos: licencia y alcance.** La cartografía del IGAC es de uso libre **solo
  sin fines comerciales** (Resolución 364 de 2012); para un uso comercial hay
  que acordar una licencia con el IGAC o cambiar a otra fuente (HydroRIVERS,
  CC BY 4.0, más gruesa). El mapa dibuja todo cauce cartografiado, no si lleva
  agua hoy: "permanente" e "intermitente" es la clasificación del IGAC a
  1:100.000, y en La Guajira el 92 % de los kilómetros figura como
  permanente, algo que conviene contrastar en campo. Solo 1 de cada 5 tramos
  tiene nombre. La caja de descarga incluye zonas de Cesar y Magdalena.
- **Geografía de lo inventado.** Proyectos, paquetes, comunidades, áreas
  protegidas, arroyos, vías y estaciones simuladas se ubican siempre sobre
  tierra firme de La Guajira (a más de 2 km de la costa y de la frontera), con
  el contorno de referencia `src/comun/contorno_guajira.wkt` (los 15 municipios
  del DANE simplificados a ~1 km). La auditoría lo verifica contra el límite
  completo. Siguen siendo ficticios: no representan ubicaciones de Ecopetrol,
  y no se han alineado con la red vial real. La silueta de la portada es un
  contorno aproximado, no el límite oficial.
- **IA y ML fuera de alcance**, a propósito: están en la sección de opciones de
  mejora de la propuesta.
- **Este stack no es la arquitectura de producción.** La propuesta plantea
  Azure Data Lake Storage Gen2, Databricks con Sedona, ArcGIS Enterprise y
  Power BI; el piloto usa archivos locales y Python / GeoPandas con la misma
  lógica, para poder migrarla sin reescribirla.

## Estructura

```
iniciar.py / iniciar.bat     arranque con un solo comando
parametros.yaml              pesos, umbrales y radios del modelo
ejecutar_pipeline.py         corre el pipeline de datos (orden, capas y auditoría)
run_app.py                   levanta solo el servidor
requirements.txt             dependencias con versiones fijas
docs/PIPELINE.md             documentación del pipeline medallion (tablas automáticas)
src/                         pipeline de datos y modelo
  comun/ bronce/ plata/ oro/ consumo/   una carpeta por capa medallion
  modelo/                    ICT, AHP y estadística espacial
  pipeline.py                pasos, dependencias y orden de ejecución
  auditoria.py, documentar.py
app/
  main.py                    API (FastAPI)
  catalogo.py                inventario vivo de las capas para /api/catalogo
  static/                    interfaz: HTML, CSS y JS sin compilación
tests/                       pruebas de cada limpieza, del modelo y de las reglas de capas
multimedia/                  logos e imágenes de referencia de diseño
.claude/skills/reto5-design/ sistema de diseño de la interfaz
data/, exports/              se generan al correr el pipeline (no se versionan)
```

El diseño de la interfaz sigue la skill de proyecto
`.claude/skills/reto5-design/` (tokens, componentes y recetas derivados de las
imágenes de `multimedia/`). Si cambias `tokens.css` o `components.css`, hazlo
en la skill y cópialo a `app/static/`.
