# Piloto Reto 5 · Mapa de riesgos multicriterio

Piloto del **Índice de Criticidad Territorial (ICT)** para la convocatoria
*Transforma la Energía* (Reto 5, Grupo Ecopetrol), desarrollado por CEN&T
Ingenieros Consultores. Recorre de punta a punta el flujo de la propuesta:
arquitectura medallion (Bronce → Plata → Oro), modelo multicriterio explicable,
mapa de calor, alertas tempranas y una aplicación web para explorarlo.

> **Registro sintético, territorio real.** Los proyectos, los paquetes de trabajo,
> su cronograma y el registro de riesgos son inventados (`src/bronce/sinteticos.py`):
> no son información de Ecopetrol ni de ninguna comunidad. El territorio sí es
> real y sale de datos abiertos oficiales: clima (IDEAM, CHIRPS), municipios y censo
> (DANE), resguardos (ANT), áreas protegidas (RUNAP), vías (INVIAS, IGAC), ríos
> (IGAC), delitos (Ministerio de Defensa) y emergencias (UNGRD). El ICT cruza los
> dos. El piloto demuestra el mecanismo y el flujo de datos; sus cifras no son el
> riesgo real de ningún proyecto.

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
   de INVIAS e IGAC, ríos del IGAC, municipios del DANE (MGN 2024), lluvia mensual de
   CHIRPS desde 1991, censo 2018 del DANE, resguardos (ANT), áreas protegidas
   (RUNAP), delitos (Ministerio de Defensa) y emergencias (UNGRD). Unos minutos y
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

- Abre siempre `http://127.0.0.1:8000`, no `localhost:8000`: si otro programa usa
  el puerto 8000 (por ejemplo, un contenedor de Docker o WSL), `localhost` puede
  llegar a ese programa en lugar del piloto.
- Si el puerto ya está en uso (por ejemplo, quedó abierto un piloto anterior),
  `iniciar.py` lo dice y se detiene en lugar de abrir el navegador sobre el
  servidor viejo: ciérralo con `Ctrl+C` en su ventana o usa `--puerto`.

### Actualizar a la última versión

Desde la carpeta del repositorio:

```bash
git pull
py -3.12 iniciar.py
```

Antes, cierra el servidor que esté abierto (`Ctrl+C`): el servidor no recarga el
código solo, y una vista nueva puede quedar vacía si la API sigue siendo la vieja.
Si cambió `requirements.txt`, `iniciar.py` reinstala las dependencias solo.
Si cambió el modelo o el generador de datos, agrega `--regenerar`.

## Qué incluye

**Aplicación** (`app/`, FastAPI + Leaflet + Chart.js, sin paso de compilación):

- **Inicio**: resumen con el ICT promedio y la distribución de riesgos.
- **Mapa**: el modelo sobre el territorio. Los paquetes se colorean por su
  **ICT** (o por su riesgo de ejecución); de lejos, cada proyecto muestra su ICT
  máximo. La capa **Escalamiento a crisis** marca, con puntos que laten, dónde un
  riesgo puede escalar (la amenaza que dispara la regla o el centro del paquete) y
  su **zona de intervención prioritaria**; el **mapa de calor** muestra la densidad
  de amenazas u oportunidades con los **puntos calientes** estadísticamente
  significativos (Gi*); la campana abre las **alertas tempranas** del día. La
  ficha de cada paquete explica su ICT: aporte de cada criterio, componentes del
  territorio real con su valor, confianza, tendencia y causas de escalamiento.
  Además, dos mapas base sin clave (satélite de Esri y calles de OpenStreetMap) y
  capas que se apilan con un interruptor cada una: proyectos y paquetes (sintéticos), los 15 municipios
  con su nombre (reales, del DANE), una sola capa de vías (reales: la red
  nacional de INVIAS en naranja grueso y la complementaria del IGAC en rosa,
  en siete clases con leyenda y kilómetros de cada una), ríos y cuerpos de
  agua (reales, del IGAC), riesgos (sintéticos, con filtros)
  y clima real del IDEAM, con cada variable como su propia capa: lluvia
  (acumulada a 7, 14 o 30 días), temperatura, viento (con flecha de dirección),
  humedad del aire y del suelo, presión, nivel del río y radiación. Muestra la
  lectura de las últimas horas (consultada en vivo) y, al hacer clic en una
  estación, todas sus variables, la serie de 30 días y la comparación con la
  normal climatológica del mes. En el mismo grupo, la **lluvia por satélite
  (CHIRPS)** colorea cada municipio por los mm del mes o por cuánto se apartó
  de lo normal (1991-2020), con la gráfica de cada mes en la ficha del municipio.
  Un **controlador de tiempo** abajo del mapa recorre el pasado hasta hoy (o lo
  reproduce): por **días** (las estaciones, últimos 30 días) o por **meses**
  (CHIRPS y delitos, últimos 10 años).
  **Contexto social y territorial (real)**: la capa de indicadores sociales
  colorea los municipios por pobreza multidimensional, NBI, miseria, hogares sin
  acueducto, calidad del agua, población indígena, territorio en resguardos o en
  áreas protegidas, homicidios, extorsión (estos dos cambian con el tiempo) o
  emergencias; hay capas de resguardos indígenas y de áreas protegidas, la ficha
  de cada municipio reúne todo (con la serie de delitos por mes) y la de cada
  paquete dice su entorno real (municipio, resguardo y área protegida más
  cercanos, delitos y emergencias).
- **Explorar**: registro de riesgos ordenable y filtrable (también por el texto
  de la descripción y por lo que marcó la IA), riesgos por categoría y por semana,
  paquetes prioritarios y la **matriz RAM de Ecopetrol** (amenazas abiertas en
  cada celda, residual o inherente, con lo que exige cada nivel; clic en una
  celda para filtrar el registro).
- **Alertas tempranas diarias**: cada día (a las 06:00 si la aplicación está
  encendida, o con `alertas_diarias.py` desde el Programador de tareas) se
  descarga la lluvia del IDEAM, se recalcula el ICT y se arma un boletín con las
  alertas nuevas, las que suben de prioridad, las que siguen y las resueltas, con
  sus causas, sus puntos de crisis y qué hacer según la RAM. Se puede enviar por
  Microsoft Teams o por correo (credenciales solo en variables de entorno; ver
  `src/notificaciones.py`). "Actualizar ahora" en el panel de alertas lo corre a mano.
- **IA sobre el texto del registro**: un clasificador de texto aprende la
  taxonomía de los riesgos que traen categoría y la sugiere para los que no (con
  su confianza y las palabras que pesaron), marca los riesgos cuyo texto
  contradice la categoría registrada y los que nombran un municipio lejano a su
  paquete. Nada se cambia sin dejar rastro (`categoria_registrada`,
  `categoria_origen`).
- **Ajustar**: pesos del ICT (directos o por comparación de pares con AHP y su
  razón de consistencia), umbrales de nivel, reglas de escalamiento y topes de
  los componentes, con vista previa del efecto en cada paquete antes de guardar.
  Lo guardado va a `modelo_personalizado.yaml` (la base de `parametros.yaml` no se
  toca) y queda en el historial de versiones con quién, cuándo y por qué.
- **Flujo**: el recorrido de la aplicación de punta a punta, de la fuente pública
  al tablero: el grafo vivo del pipeline (leído de `src/pipeline.py`, con el
  linaje de cada paso), las fuentes con su licencia y fecha de descarga, los
  modelos, el ciclo diario, las tecnologías con sus versiones, la auditoría, la
  ciberseguridad y el paso a producción (`/api/flujo`).
- **Matriz RAM**: cada riesgo se califica como lo hace Ecopetrol (instructivo
  ECP-DRI-I-007): consecuencia de 0 a 5 en Personas, Económica, Ambiental,
  Clientes e Imagen, probabilidad de A a E sin y con controles, y manda la peor
  dimensión. La severidad del ICT sale del nivel RAM residual, un riesgo VH
  escala el paquete y la ficha de cada paquete compara su calificación con lo
  que sugiere el territorio real (delitos, emergencias, resguardos, áreas
  protegidas). Escalas y matriz en `parametros.yaml` → `ram`.
- **Riesgo de ejecución**: modelo matemático (Monte Carlo) que convierte la
  matriz RAM y el territorio real en días de atraso y dólares de sobrecosto por
  paquete y proyecto: atraso esperado, P50/P90, IRE (probabilidad de pasar la
  holgura más una tolerancia), qué riesgo aporta más y cuánto evitan los
  controles. Tiene escenarios en vivo ("¿y si llueve el doble?", "¿y sin
  controles?") y supuestos editables. Formulación completa en
  **[docs/MODELO_EJECUCION.md](docs/MODELO_EJECUCION.md)**.
- **Matriz RAM (vista editable)**: cambia el nivel de cada celda, lo que
  significa cada probabilidad y cada nivel de consecuencia, la decisión, quién
  aprueba y el puntaje de cada nivel, y las reglas de escalamiento de la RAM.
  Antes de guardar muestra cuántas amenazas cambiarían de nivel y cuántos
  paquetes escalarían, y avisa si el nivel baja cuando sube la consecuencia o la
  probabilidad. Lo editado se guarda en `ram_personalizada.yaml`: la oficial
  de `parametros.yaml` no se toca, y "Volver a la oficial" borra ese archivo.
  "Guardar y recalcular" corre el registro, el ICT y lo que depende de ellos
  (unos 20 s, sin descargas).
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
| **Municipios** del DANE (MGN 2024) | `bronce.municipios` | `plata.municipios` | `oro.municipios` | municipios |
| **Lluvia CHIRPS v3** (UCSB, CC BY 4.0) | `bronce.chirps` | `plata.chirps` | `oro.chirps` | lluvia por satélite y escala de meses |
| **Censo 2018** (DANE), **IRCA** (INS), **PDET** (ART) | `bronce.social` | `plata.social` | `oro.indicadores`, `oro.contexto` | indicadores sociales y fichas |
| **Resguardos** (ANT, Ministerio del Interior) | `bronce.resguardos` | `plata.resguardos` | `oro.territorios` | resguardos indígenas |
| **Áreas protegidas** (RUNAP) | `bronce.runap` | `plata.runap` | `oro.territorios` | áreas protegidas |
| **Delitos** (Ministerio de Defensa, 11 delitos desde 2003) | `bronce.seguridad` | `plata.seguridad` | `oro.indicadores` | homicidios y extorsión por mes |
| **Emergencias** (UNGRD) | `bronce.emergencias` | `plata.emergencias` | `oro.indicadores` | emergencias por municipio |

Reglas que el código hace cumplir: solo Bronce toca la red; Oro no lee Bronce
(lo que necesita del origen viaja en `proveniencia_<fuente>.json`, que escribe
Plata); Plata no lee Oro; cada archivo lo escribe un solo paso; y cada paso
reemplaza sus salidas completas. `python ejecutar_pipeline.py --auditar`
comprueba además que las tres capas están completas, que las cuentas cuadran
(lo que entra menos lo descartado es lo que sale) y que no sobran archivos.

**Cobertura de estaciones** (`oro.cobertura`): cada estación se extiende a un área
(la más cercana y un radio de influencia por variable) para ver el clima sobre
los proyectos. Los radios son supuestos de trabajo editables en
`parametros.yaml`, no cifras oficiales del IDEAM; la ficha de cada paquete dice
qué estación lo representa, a cuántos km y si queda cubierto, parcial o sin cobertura.

El resto del código: `app/clima_vivo.py` consulta el flujo de las últimas horas
del IDEAM en vivo (caché de 10 minutos, con la misma limpieza de Plata y el
respaldo local si no hay internet); `modelo/ict.py`, `modelo/ahp.py` y
`modelo/espacial.py` son el motor del ICT.

Los parámetros del modelo (pesos, umbrales, reglas, topes, radios de influencia)
viven en [`parametros.yaml`](parametros.yaml), separados del código; lo que se
edita desde la aplicación (matriz RAM, supuestos de ejecución, modelo) se guarda
aparte y deja su versión en `historial_parametros.jsonl`. La formulación completa
del ICT está en **[docs/MODELO_ICT.md](docs/MODELO_ICT.md)** y la del riesgo de
ejecución en **[docs/MODELO_EJECUCION.md](docs/MODELO_EJECUCION.md)**.

Seguridad: la aplicación escucha solo en el propio equipo. Con `iniciar.py --red`
otros equipos pueden consultarla, pero editar (matriz, supuestos, modelo) o
disparar la actualización exige la clave de la variable de entorno
`RETO5_CLAVE_EDICION`; sin ella, solo se edita desde el equipo donde corre.

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
python alertas_diarias.py                      # tarea diaria: descarga el IDEAM, recalcula, boletín y avisos
python alertas_diarias.py --sin-red --sin-enviar   # solo recalcular y armar el boletín
python alertas_diarias.py --programar          # cómo programarla en Windows (schtasks) o Linux (cron)
python run_app.py                              # solo el servidor
python -m pytest tests/ -v                     # pruebas de limpieza, modelo y arquitectura
cd src && python -m plata.ideam                # un paso suelto (cualquier módulo de bronce, plata, oro)
cd src && python -m auditoria                  # solo la auditoría
cd src && python -m documentar                 # regenera las tablas automáticas de docs/PIPELINE.md
```

Fuentes: `sinteticos`, `ideam`, `invias`, `vias_igac`, `hidrografia`,
`municipios`, `red_vial`, `chirps`, `social`, `resguardos`, `runap`, `seguridad`, `emergencias`,
`territorios`, `indicadores`, `contexto`, `ejecucion`, `cobertura`, `ict`, `validacion`, `gis`, `alertas`. Para probar el pipeline sin tocar
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

1. **Inicio** (`http://127.0.0.1:8000`): ICT promedio y riesgos por categoría.
   Señalar el chip "Datos sintéticos": el registro es inventado, el territorio es real.
2. **Mapa, la criticidad**: los paquetes por color de ICT y, de lejos, el ICT
   máximo de cada proyecto. Los puntos que laten son donde un riesgo puede
   escalar a crisis, con su zona de intervención. Encender el mapa de calor y
   mostrar los puntos calientes (borde punteado).
3. **Por qué**: clic en el paquete más crítico. Aporte de cada criterio, el
   territorio real detrás (resguardo, pobreza, áreas protegidas, vías, lluvia del
   IDEAM, emergencias, delitos), confianza, tendencia y causas de escalamiento.
   Clic en un punto de crisis: qué exige la RAM y quién decide.
4. **Alertas**: la campana. Corte del día, novedades frente al día anterior,
   próxima actualización automática, "Boletín del día" y "Actualizar ahora".
5. **IA**: en Explorar, el filtro "IA" y la búsqueda en el texto; en la ficha de
   un riesgo, lo que la IA asignó o marcó para revisar.
6. **Ajustar**: subir el peso de la vulnerabilidad o derivar los pesos por AHP y
   ver en la vista previa qué paquetes cambian de nivel; guardar deja la versión
   en el historial.
7. **Riesgo de ejecución**: días de atraso y USD de sobrecosto por proyecto, y un
   escenario ("¿y sin controles?").
8. **Matriz RAM**, **Datos** y **Flujo**: la matriz editable, la arquitectura
   medallion, el catálogo con el linaje de cada tabla y el grafo vivo del
   pipeline, de la fuente al tablero.
9. **Cierre**: el GeoPackage (`exports/reto5_piloto.gpkg`) en QGIS o ArcGIS, con
   la tabla `leeme` que dice el origen de cada capa.

## Limitaciones (leer antes de mostrar el piloto)

- **Prueba de consistencia circular**: los riesgos materializados entran al
  ICT y luego se comparan con él. Confirma que el mecanismo funciona, **no** que
  los pesos o criterios sean los correctos; eso requiere el histórico real de
  Ecopetrol (Fase 4).
- **Pesos supuestos**: los de `parametros.yaml` son un punto de partida, no
  una calibración con expertos (Fase 2 de la propuesta).
- **Lluvia del ICT.** El componente de lluvia reciente usa la estación del
  IDEAM más cercana con al menos 10 de los últimos 14 días con dato y a menos de
  20 km; los paquetes sin una estación así quedan sin ese dato (no se imputa) y
  su índice de confianza lo muestra. La anomalía de lluvia (CHIRPS) cubre todos.
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
  IGAC: uso libre solo sin fines comerciales. El componente de acceso del ICT usa
  esta red (fracción de km solo transitables en tiempo seco a menos de 10 km).
- **Municipios: versión de los límites.** La geometría es del MGN 2024, del
  geoportal del propio DANE (dato abierto; hay que citar la fuente). Algunas estaciones del
  catálogo caen fuera de los 15 polígonos (casi todas en la costa o el mar) y
  otras en un municipio distinto del que declaran; el mapa las cuenta por su
  ubicación y el conteo exacto queda en `reporte_cruces_municipios.csv`.
- **Contexto social: alcance.** Pobreza, etnia y población son del censo 2018
  (estructura del territorio, no la situación de hoy) y las tasas de delitos
  usan esa población. Los delitos son los registrados por la Policía
  (subregistro rural). La UNGRD no publica 2021 ni 2022, y su reporte de 2025
  llega duplicado y con códigos de municipio del Cesar (Plata lo corrige). El
  IRCA solo mide donde hay acueducto. Un resguardo cerca indica dónde aplica la
  consulta previa, no una amenaza. Este contexto entra al ICT en la
  vulnerabilidad del territorio y en las amenazas externas.
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
- **IA sobre texto sintético.** El clasificador del registro aprende de textos
  redactados con plantillas, así que su acierto (validación cruzada y clave
  sintética) es optimista; el real se sabrá al reentrenarlo con el registro de
  Ecopetrol. Es un modelo pequeño y explicable (bayesiano ingenuo); si hace falta,
  se cambia por uno más grande sin tocar el resto del pipeline.
- **Avisos sin configurar.** Teams y correo vienen apagados: hay que activarlos en
  `parametros.yaml` → `alertas.canales` y definir sus variables de entorno. El
  boletín en `exports/alertas/` se genera siempre.
- **Este stack no es la arquitectura de producción.** La propuesta plantea
  Azure Data Lake Storage Gen2, Databricks con Sedona, ArcGIS Enterprise y
  Power BI; el piloto usa archivos locales y Python / GeoPandas con la misma
  lógica, para poder migrarla sin reescribirla.

## Estructura

```
iniciar.py / iniciar.bat     arranque con un solo comando
parametros.yaml              pesos, umbrales, reglas, topes y radios del modelo (la base)
ejecutar_pipeline.py         corre el pipeline de datos (orden, capas y auditoría)
alertas_diarias.py           tarea diaria de alertas tempranas (descarga, recálculo, boletín, avisos)
run_app.py                   levanta solo el servidor
requirements.txt             dependencias con versiones fijas
docs/PIPELINE.md             documentación del pipeline medallion (tablas automáticas)
docs/MODELO_ICT.md           formulación del ICT, escalamiento, mapa de calor, alertas e IA
docs/MODELO_EJECUCION.md     formulación del riesgo de ejecución (Monte Carlo)
src/                         pipeline de datos y modelo
  comun/ bronce/ plata/ oro/ consumo/   una carpeta por capa medallion
  modelo/                    ICT, territorio real, AHP, estadística espacial, IA sobre texto, riesgo de ejecución
  pipeline.py                pasos, dependencias y orden de ejecución
  tarea_diaria.py, notificaciones.py   alertas diarias y su envío por Teams o correo
  auditoria.py, documentar.py
app/
  main.py                    API (FastAPI) y protección de la edición
  catalogo.py                inventario vivo de las capas para /api/catalogo
  modelo_api.py, ram_config.py, ejecucion_api.py, historial.py   edición versionada de parámetros
  tarea_programada.py        corre la tarea diaria de alertas mientras la aplicación está encendida
  static/                    interfaz: HTML, CSS y JS sin compilación
tests/                       pruebas de cada limpieza, del modelo y de las reglas de capas
multimedia/                  logos e imágenes de referencia de diseño
.claude/skills/reto5-design/ sistema de diseño de la interfaz
data/, exports/              se generan al correr el pipeline (no se versionan); exports/alertas/ guarda los boletines
*_personalizad*.yaml, historial_parametros.jsonl   lo editado desde la aplicación (local, no se versiona)
```

El diseño de la interfaz sigue la skill de proyecto
`.claude/skills/reto5-design/` (tokens, componentes y recetas derivados de las
imágenes de `multimedia/`). Si cambias `tokens.css` o `components.css`, hazlo
en la skill y cópialo a `app/static/`.
