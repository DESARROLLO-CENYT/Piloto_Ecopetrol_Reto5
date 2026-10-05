# Diccionario de datos

> Generado automáticamente por `python -m documentar` a partir de los archivos que hay hoy en `data/` y de las descripciones de
> `app/catalogo.py`. No se edita a mano: para cambiar una descripción, cámbiala en el catálogo. El proceso que produce cada
> tabla está en [PIPELINE.md](PIPELINE.md).

## Bronce

### `areas_protegidas.geojson` — Áreas protegidas

*Vulnerabilidad* · origen **sintético** · GeoJSON · 6 filas · geometría: Polígonos

Áreas de interés ambiental con un índice de sensibilidad.

**Cómo se genera:** 6 círculos enteros dentro de tierra firme, con categorías ficticias (parque, reserva, humedal) y sensibilidad 0.4 a 1.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_area` | texto | 0 | Identificador del área protegida. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `categoria` | texto | 0 | Tipo de área protegida (ficticia). |
| `sensibilidad` | decimal | 0 | Índice de sensibilidad ambiental, 0 a 1. |

### `clima_sintetico.csv` — Clima simulado

*Amenaza externa (modelo ICT)* · origen **sintético** · CSV · 600 filas

Serie diaria simulada por estación: precipitación, temperatura y viento. Es la que alimenta el criterio climático del ICT; no proviene del IDEAM.

**Cómo se genera:** 5 estaciones × 120 días en lugares aleatorios de tierra firme. Se planta un evento de lluvia extrema (+60 a 120 mm) cerca del final de la serie para que existan alertas climáticas recientes.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_estacion` | texto | 0 | Estación meteorológica. |
| `fecha` | texto | 0 | Día de la medición. |
| `lon` | decimal | 0 | Longitud de la estación simulada (WGS84). |
| `lat` | decimal | 0 | Latitud de la estación simulada (WGS84). |
| `precipitacion_mm` | decimal | 0 | Precipitación diaria en mm. |
| `temperatura_c` | decimal | 0 | Temperatura media en grados C. |
| `viento_kmh` | decimal | 0 | Velocidad del viento en km/h. |

### `comunidades.geojson` — Comunidades

*Vulnerabilidad* · origen **sintético** · GeoJSON · 18 filas · geometría: Puntos

Asentamientos con población aproximada e índice de conflictividad social.

**Cómo se genera:** 18 puntos aleatorios sobre tierra firme (a más de 2 km de la costa y la frontera), con nombres genéricos; conflictividad sesgada a valores bajos (Beta 2,5).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_comunidad` | texto | 0 | Identificador de la comunidad. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `poblacion_aprox` | entero | 0 | Población aproximada. |
| `conflictividad` | decimal | 0 | Índice de conflictividad social, 0 a 1. |

### `dane_municipios.geojson` — Municipios del DANE (crudos)

*Límites (real)* · origen **DANE** · GeoJSON · 15 filas · geometría: Polígonos

Los 15 polígonos municipales de La Guajira del Marco Geoestadístico Nacional del DANE (versión 2005, base del IGAC), tal como los publica el servicio, con sus más de 200 atributos del censo y ~125 mil vértices.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `DPTO_CCDGO` | texto | 0 | Código del departamento. |
| `MPIO_CCDGO` | texto | 0 | Código del municipio dentro del departamento. |
| `MPIO_CNMBR` | texto | 0 | Nombre del municipio (mayúsculas, sin tildes). |
| `MPIO_NAREA` | decimal | 0 | Área oficial en m² según la fuente. |
| `MPIO_NANO` | entero | 0 | Año de la versión de la geometría. |
| `DEPTO` | texto | 0 | Departamento. |
| `MUNICIPIO` | texto | 0 | Municipio. |
| `COD_DEP_MP` | texto | 0 | Código DANE de 5 dígitos. |

*223 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `divipola_municipios.csv` — DIVIPOLA de La Guajira

*Códigos y nombres (real)* · origen **DANE** · CSV · 15 filas

Código DANE, nombre y coordenadas de la cabecera de cada municipio (datos.gov.co, DANE).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `cod_dpto` | entero | 0 | Código del departamento. |
| `dpto` | texto | 0 | Departamento. |
| `cod_mpio` | entero | 0 | Código DANE del municipio. |
| `nom_mpio` | texto | 0 | Nombre del municipio en DIVIPOLA. |
| `tipo_municipio` | texto | 0 | Municipio o área no municipalizada. |
| `longitud` | texto | 0 | Longitud de la cabecera (coma decimal en la fuente). |
| `latitud` | texto | 0 | Latitud de la cabecera (coma decimal en la fuente). |

### `hidrografia_meta.json` — Metadatos de la descarga de hidrografía

*Trazabilidad (real)* · origen **IGAC** · JSON · 1 filas

Servicio de origen, licencia (uso libre solo sin fines comerciales), fecha, caja de descarga y cuántos objetos y vértices llegaron por capa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `servicio` | texto | 0 | Dirección del servicio de origen. |

*26 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `hidrologia.geojson` — Hidrología

*Contexto* · origen **sintético** · GeoJSON · 8 filas · geometría: Líneas

Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en `rios` y `cuerpos_agua`.

**Cómo se genera:** 8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_cuerpo_agua` | texto | 0 | Identificador del cuerpo de agua. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `ideam_estaciones.csv` — Estaciones del IDEAM

*Catálogo (real)* · origen **IDEAM** · CSV · 219 filas

Catálogo Nacional de Estaciones del IDEAM filtrado a La Guajira: código, nombre, categoría, tecnología, estado, municipio, coordenadas y altitud. Incluye estaciones activas, en mantenimiento y suspendidas.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | entero | 0 | Código de la estación (10 dígitos). |
| `nombre` | texto | 0 | Nombre de la estación (en Plata sin el código entre corchetes ni el sufijo AUT). |
| `categoria` | texto | 0 | Tipo de estación: pluviométrica, climatológica, sinóptica, etc. |
| `tecnologia` | texto | 0 | Convencional, automática, con telemetría, etc. |
| `estado` | texto | 0 | Activa, en mantenimiento o suspendida. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `ubicaci_n` | texto | 0 | Ubicación como la entrega el IDEAM. Trae latitud y longitud invertidas, por eso Plata no la usa. |
| `altitud` | entero | 0 | Altitud en metros sobre el nivel del mar. |
| `longitud` | decimal | 0 | Longitud en grados decimales (WGS84). |
| `latitud` | decimal | 0 | Latitud en grados decimales (WGS84). |
| `fecha_instalacion` | texto | 0 | Fecha de instalación (texto dd/mm/aaaa). |
| `area_operativa` | texto | 0 | Área operativa del IDEAM. |
| `corriente` | texto | 153 | Corriente asociada. |
| `area_hidrografica` | texto | 0 | Área hidrográfica. |
| `zona_hidrografica` | texto | 0 | Zona hidrográfica. |
| `subzona_hidrografica` | texto | 0 | Subzona hidrográfica. |
| `entidad` | texto | 0 | Entidad propietaria de la estación. |
| `fecha_suspension` | texto | 102 | Fecha de suspensión, si aplica. |

### `ideam_meta.json` — Metadatos de la descarga

*Trazabilidad (real)* · origen **IDEAM** · JSON · 1 filas

Fuente, licencia, fecha de descarga, ventana de fechas y cuántas estaciones se sondearon, descargaron o fallaron.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Portal y conjuntos de datos de origen. |
| `licencia` | texto | 0 | Licencia de uso de los datos. |
| `descargado_en` | texto | 0 | Fecha y hora de la descarga. |
| `desde` | texto | 0 | Inicio de la ventana descargada. |
| `hasta` | texto | 0 | Fin de la ventana descargada. |
| `estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `estaciones_con_datos_recientes` | entero | 0 | Estaciones que respondieron con datos recientes. |
| `estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `estaciones_con_error` | lista | 0 | Estaciones cuya descarga falló. |
| `lecturas` | entero | 0 | Lecturas descargadas. |

*74 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `ideam_normales.csv` — Normales climatológicas

*Climatología (real)* · origen **IDEAM** · CSV · 420 filas

Valor típico de cada mes (periodo 1991-2020) por estación y parámetro: precipitación, temperatura media, máxima y mínima, humedad relativa, brillo solar, entre otros. Sirve para decir si un mes va más seco o más lluvioso de lo normal.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `periodo` | texto | 0 | Periodo de la normal (1991-2020). |
| `categoria` | texto | 0 | Tipo de estación: pluviométrica, climatológica, sinóptica, etc. |
| `municipio` | texto | 0 | Municipio. |
| `departamento` | texto | 0 | Departamento. |
| `altitud_m` | entero | 0 | Altitud en metros sobre el nivel del mar. |
| `longitud` | decimal | 0 | Longitud en grados decimales (WGS84). |
| `latitud` | decimal | 0 | Latitud en grados decimales (WGS84). |
| `ene` | decimal | 0 | Valor de enero. |
| `feb` | decimal | 0 | Valor de febrero. |
| `mar` | decimal | 0 | Valor de marzo. |
| `abr` | decimal | 0 | Valor de abril. |
| `may` | decimal | 0 | Valor de mayo. |
| `jun` | decimal | 0 | Valor de junio. |
| `jul` | decimal | 0 | Valor de julio. |
| `ago` | decimal | 0 | Valor de agosto. |
| `sep` | decimal | 0 | Valor de septiembre. |
| `oct` | decimal | 0 | Valor de octubre. |
| `nov` | decimal | 0 | Valor de noviembre. |
| `dic` | decimal | 0 | Valor de diciembre. |
| `anual` | decimal | 0 | Valor anual. |

*4 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `ideam_precipitacion.parquet` — Lecturas de precipitación (crudas)

*Lecturas (real)* · origen **IDEAM** · Parquet · 65.123 filas

Lecturas de lluvia tal como las entrega el IDEAM, cada ~10 minutos (~2 minutos en la estación del aeropuerto de Riohacha), de los últimos 30 días. Se guardan sin tocar, con duplicados y como texto.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `codigosensor` | texto | 0 | Código del sensor: 0240 precipitación, 0257 precipitación por GPRS (mismo dato por otro canal). |
| `fechaobservacion` | texto | 0 | Fecha y hora de la lectura. |
| `valorobservado` | texto | 0 | Lluvia caída en el intervalo de la lectura, en mm (resolución típica de 0,2 mm). |
| `nombreestacion` | texto | 0 | Nombre de la estación tal como viene en la lectura. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `zonahidrografica` | texto | 0 | Zona hidrográfica. |
| `latitud` | texto | 0 | Latitud en grados decimales (WGS84). |
| `longitud` | texto | 0 | Longitud en grados decimales (WGS84). |
| `descripcionsensor` | texto | 0 | Descripción del sensor. |
| `unidadmedida` | texto | 0 | Unidad de medida (mm). |

### `ideam_radiacion.csv` — Radiación solar (promedios)

*Climatología (real)* · origen **IDEAM** · CSV · 7 filas

Radiación global media por estación: un valor para cada mes y el promedio anual, en Wh/m² por día. El IDEAM la publica solo como promedio histórico, no como serie diaria.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `estacion` | texto | 0 | Nombre de la estación. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `latitud` | decimal | 0 | Latitud en grados decimales (WGS84). |
| `longitud` | decimal | 0 | Longitud en grados decimales (WGS84). |
| `altitud` | entero | 0 | Altitud en metros sobre el nivel del mar. |
| `tipo_de_estacion` | texto | 0 | Automática o convencional. |
| `promedio_anual` | decimal | 0 | Promedio anual de radiación global (Wh/m² por día). |
| `ene` | decimal | 0 | Valor de enero. |
| `feb` | decimal | 0 | Valor de febrero. |
| `mar` | decimal | 0 | Valor de marzo. |
| `abr` | decimal | 0 | Valor de abril. |
| `may` | decimal | 0 | Valor de mayo. |
| `jun` | decimal | 0 | Valor de junio. |
| `jul` | decimal | 0 | Valor de julio. |
| `ago` | decimal | 0 | Valor de agosto. |
| `sep` | decimal | 0 | Valor de septiembre. |
| `oct` | decimal | 0 | Valor de octubre. |
| `nov` | decimal | 0 | Valor de noviembre. |
| `dic` | decimal | 0 | Valor de diciembre. |

### `ideam_ultimas_horas.parquet` — Lecturas de las últimas horas

*Casi en tiempo real (real)* · origen **IDEAM** · Parquet · 3.041 filas

Flujo del IDEAM con las lecturas de las últimas ~12 horas de todas las variables. Es lo que el mapa muestra como valor de ahora; el backend lo consulta en vivo y guarda este respaldo por si no hay internet.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `codigosensor` | texto | 0 | Código del sensor: 0240 precipitación, 0257 precipitación por GPRS (mismo dato por otro canal). |
| `fechaobservacion` | texto | 0 | Fecha y hora de la lectura. |
| `valorobservado` | texto | 0 | Lluvia caída en el intervalo de la lectura, en mm (resolución típica de 0,2 mm). |
| `nombreestacion` | texto | 0 | Nombre de la estación tal como viene en la lectura. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `zonahidrografica` | texto | 0 | Zona hidrográfica. |
| `latitud` | texto | 0 | Latitud en grados decimales (WGS84). |
| `longitud` | texto | 0 | Longitud en grados decimales (WGS84). |
| `descripcionsensor` | texto | 0 | Descripción del sensor. |
| `unidadmedida` | texto | 0 | Unidad de medida (mm). |
| `entidad` | texto | 0 | Entidad propietaria de la estación. |

### `ideam_variables.parquet` — Otras variables (crudas)

*Lecturas (real)* · origen **IDEAM** · Parquet · 195.350 filas

Temperatura del aire (media, máxima y mínima), humedad, viento (velocidad y dirección), presión y nivel del río de los últimos 30 días, cada una de su conjunto de datos abiertos. Se guardan tal como llegan, con una columna que dice de qué conjunto vino cada fila.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `codigosensor` | texto | 0 | Código del sensor: 0240 precipitación, 0257 precipitación por GPRS (mismo dato por otro canal). |
| `fechaobservacion` | texto | 0 | Fecha y hora de la lectura. |
| `valorobservado` | texto | 0 | Lluvia caída en el intervalo de la lectura, en mm (resolución típica de 0,2 mm). |
| `nombreestacion` | texto | 0 | Nombre de la estación tal como viene en la lectura. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `zonahidrografica` | texto | 0 | Zona hidrográfica. |
| `latitud` | texto | 0 | Latitud en grados decimales (WGS84). |
| `longitud` | texto | 0 | Longitud en grados decimales (WGS84). |
| `descripcionsensor` | texto | 0 | Descripción del sensor. |
| `unidadmedida` | texto | 0 | Unidad de medida (mm). |
| `variable` | texto | 0 | Conjunto de datos de origen de la fila (temperatura, humedad, viento_vel...). |

### `igac_cienagas.geojson` — Ciénagas (crudas)

*Cuerpos de agua (real)* · origen **IGAC** · GeoJSON · 9 filas · geometría: Polígonos

Ciénagas como polígonos, según la cartografía básica del IGAC.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `nombre_geografico` | texto | 0 | Nombre geográfico tal como viene (a veces sin tildes o con espacios de más). |
| `fecha` | texto | 9 | Día de la medición. |

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_drenaje_doble.geojson` — Drenajes principales (crudos)

*Ríos anchos (real)* · origen **IGAC** · GeoJSON · 32 filas · geometría: Polígonos

Ríos lo bastante anchos para dibujarse como polígono (Palomino, Cesar, arroyos grandes).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `nombre_geografico` | texto | 0 | Nombre geográfico tal como viene (a veces sin tildes o con espacios de más). |
| `fecha` | decimal | 31 | Día de la medición. |

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_drenaje_sencillo.geojson` — Drenajes sencillos (crudos)

*Ríos y arroyos (real)* · origen **IGAC** · GeoJSON · 9.612 filas · geometría: Líneas

Ríos, arroyos y quebradas como líneas, tal como los publica el IGAC a escala 1:100.000: ~9.600 tramos y casi 590 mil vértices. Cada tramo trae nombre (solo 1 de cada 5 lo tiene) y un código de estado del cauce: 5101 permanente, 5102 intermitente.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `nombre_geografico` | texto | 7708 | Nombre geográfico tal como viene (a veces sin tildes o con espacios de más). |
| `estado_drenaje` | entero | 0 | 5101 cauce permanente, 5102 cauce intermitente (dominio del IGAC). |
| `fecha` | decimal | 9384 | Día de la medición. |

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_embalses.geojson` — Embalses (crudos)

*Cuerpos de agua (real)* · origen **IGAC** · GeoJSON · 3 filas · geometría: Polígonos

Embalses y represas como polígonos (El Cercado, Jojaipana).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `nombre_geografico` | texto | 1 | Nombre geográfico tal como viene (a veces sin tildes o con espacios de más). |
| `fecha` | texto | 3 | Día de la medición. |

*8 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_lagunas.geojson` — Lagunas (crudas)

*Cuerpos de agua (real)* · origen **IGAC** · GeoJSON · 174 filas · geometría: Polígonos

Lagunas como polígonos; solo un tercio tiene nombre. La cartografía marca el contorno, no si hoy hay agua.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `nombre_geografico` | texto | 117 | Nombre geográfico tal como viene (a veces sin tildes o con espacios de más). |
| `fecha` | decimal | 173 | Día de la medición. |

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_caminos.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 1.944 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 1944 | Nombre geográfico tal como viene. |
| `fecha` | texto | 1944 | Día de la medición. |
| `eje_vial` | texto | 1944 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_tipo1.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 35 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 33 | Nombre geográfico tal como viene. |
| `fecha` | texto | 35 | Día de la medición. |
| `eje_vial` | texto | 22 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_tipo2.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 13 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 13 | Nombre geográfico tal como viene. |
| `fecha` | texto | 13 | Día de la medición. |
| `eje_vial` | texto | 13 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_tipo3.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 241 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 240 | Nombre geográfico tal como viene. |
| `fecha` | texto | 241 | Día de la medición. |
| `eje_vial` | texto | 225 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_tipo4.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 73 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 73 | Nombre geográfico tal como viene. |
| `fecha` | texto | 73 | Día de la medición. |
| `eje_vial` | texto | 73 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_tipo5.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 256 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 256 | Nombre geográfico tal como viene. |
| `fecha` | decimal | 255 | Día de la medición. |
| `eje_vial` | texto | 256 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `igac_via_tipo6.geojson` — Vías del IGAC (crudas)

*Vías (real)* · origen **IGAC** · GeoJSON · 3.041 filas · geometría: Líneas

Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objectid` | entero | 0 | Número de objeto en el servicio del IGAC. |
| `tipo_via` | entero | 0 | Tipo de vía tal como viene (1 a 7). |
| `estado_superficie` | texto | 0 | Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción. |
| `numero_carriles` | texto | 0 | Código de ancho: 3501 dos o más carriles, 3502 angosta. |
| `accesibilidad` | texto | 0 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre_geografico` | texto | 3040 | Nombre geográfico tal como viene. |
| `fecha` | texto | 3041 | Día de la medición. |
| `eje_vial` | texto | 3041 | Eje vial al que pertenece. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `invias_meta.json` — Metadatos de la descarga de vías

*Trazabilidad (real)* · origen **INVIAS** · JSON · 1 filas

Fuente, licencia, fecha, caja de descarga y cuántos tramos del país se bajaron.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `dataset` | texto | 0 | Identificador del conjunto en datos.gov.co. |
| `tramos_en_el_pais` | entero | 0 | Tramos del conjunto completo. |
| `tramos_descargados` | entero | 0 | Tramos que cruzan la caja de descarga. |
| `vertices` | entero | 0 | Puntos de la geometría descargada. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `invias_red_vial.geojson` — Red vial nacional (INVIAS)

*Vías (real)* · origen **INVIAS** · GeoJSON · 11 filas · geometría: MultiLineString

Tramos de la Red Vial Nacional que cruzan La Guajira, tal como los publica INVIAS en datos.gov.co: códigos de dominio sin traducir, "Por Defnir" donde falta el dato y la geometría completa (hasta 14 mil vértices por tramo). En Plata: etiquetas legibles, sin tramos repetidos, recortada a la caja de descarga y simplificada a 15 m.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `codigo_tramo` | texto | 0 | Código del tramo en INVIAS. |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `nombre_ruta` | texto | 0 | Nombre de la ruta (p. ej. Transversal del Caribe). |
| `nombre_tramo` | texto | 0 | Nombre del tramo (casi siempre "Por Defnir" en la fuente). |
| `ruta` | texto | 0 | Número de la ruta nacional. |
| `sector` | texto | 0 | Sector del tramo (p. ej. Riohacha - Paraguachón). |

*10 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `municipios_meta.json` — Metadatos de la descarga de municipios

*Trazabilidad (real)* · origen **DANE** · JSON · 1 filas

Servicio de origen, versión de la geometría, licencia y fecha de descarga.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Fuente de los datos. |
| `servicio` | texto | 0 | Servicio de origen. |
| `version_geometria` | texto | 0 | Versión de la cartografía. |
| `licencia` | texto | 0 | Licencia o condición de uso. |
| `divipola` | texto | 0 | Conjunto DIVIPOLA usado para nombres y cabeceras. |
| `descargado_en` | texto | 0 | Fecha y hora de la descarga. |
| `municipios` | entero | 0 | Municipios descargados. |
| `divipola_filas` | entero | 0 | Filas de DIVIPOLA. |

### `paquetes_trabajo.geojson` — Paquetes de trabajo

*Unidad de análisis* · origen **sintético** · GeoJSON · 14 filas · geometría: Polígonos

Polígonos de los paquetes de trabajo. Son la unidad sobre la que se calcula el ICT.

**Cómo se genera:** 14 círculos (4 a 6 por proyecto), todos dentro de su proyecto y de tierra firme; ~30% marcados como ruta crítica.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |

### `proyectos.geojson` — Proyectos

*Contexto* · origen **sintético** · GeoJSON · 3 filas · geometría: Polígonos

Límites de los proyectos que agrupan los paquetes de trabajo.

**Cómo se genera:** 3 proyectos ficticios (Norte, Centro, Sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `registro_riesgos.xlsx` — Registro de riesgos

*Registro* · origen **sintético** · Excel · 212 filas

Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, con probabilidad, impacto, estado de materialización y acción de tratamiento.

**Cómo se genera:** 200 riesgos repartidos en los 14 paquetes. Tres paquetes 'calientes' reciben más riesgos y con probabilidad e impacto altos, para que el mapa muestre patrones. ~18% son oportunidades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_evento_riesgo` | texto | 6 | Identificador del evento de riesgo asociado. |
| `descripcion` | texto | 0 | Descripción textual del riesgo. |
| `causa` | texto | 10 | Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'. |
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `probabilidad` | entero | 0 | Escala de 1 a 5. |
| `impacto` | entero | 0 | Escala de 1 a 5. |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `id_paquete_trabajo` | texto | 0 | Paquete de trabajo al que pertenece (llave hacia paquetes). |
| `fecha_identificacion` | texto | 0 | Fecha en que se identificó el riesgo. |
| `fecha_materializacion` | texto | 172 | Fecha de materialización; vacía si no se ha materializado. |
| `accion_tratamiento` | texto | 0 | Acción de tratamiento definida. |
| `fecha_ejecucion_accion` | texto | 17 | Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida. |
| `lat` | decimal | 24 | Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `lon` | decimal | 24 | Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

### `vias.geojson` — Vías

*Contexto* · origen **sintético** · GeoJSON · 10 filas · geometría: Líneas

Red vial por tipo (primaria, secundaria, terciaria de difícil acceso). Es la inventada; la red real (INVIAS e IGAC) está en `red_vial` y aún no alimenta el ICT.

**Cómo se genera:** 10 segmentos rectos con tipo aleatorio, enteros dentro de tierra firme.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_via` | texto | 0 | Identificador de la vía. |
| `tipo` | texto | 0 | primaria, secundaria o terciaria de difícil acceso. |

### `vias_igac_meta.json` — Metadatos de la descarga de vías del IGAC

*Trazabilidad (real)* · origen **IGAC** · JSON · 1 filas

Servicio de origen, licencia (uso libre solo sin fines comerciales), fecha, caja y objetos por capa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Fuente de los datos. |
| `servicio` | texto | 0 | Servicio de origen. |
| `licencia` | texto | 0 | Licencia o condición de uso. |
| `descargado_en` | texto | 0 | Fecha y hora de la descarga. |

*32 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

## Plata

### `areas.geojson` — Áreas protegidas

*Vulnerabilidad* · origen **sintético** · GeoJSON · 6 filas · geometría: Polígonos

Áreas de interés ambiental con un índice de sensibilidad.

**Cómo se genera:** 6 círculos enteros dentro de tierra firme, con categorías ficticias (parque, reserva, humedal) y sensibilidad 0.4 a 1.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_area` | texto | 0 | Identificador del área protegida. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `categoria` | texto | 0 | Tipo de área protegida (ficticia). |
| `sensibilidad` | decimal | 0 | Índice de sensibilidad ambiental, 0 a 1. |

### `clima_sintetico.parquet` — Clima simulado

*Amenaza externa (modelo ICT)* · origen **sintético** · Parquet · 600 filas

Serie diaria simulada por estación: precipitación, temperatura y viento. Es la que alimenta el criterio climático del ICT; no proviene del IDEAM.

**Cómo se genera:** 5 estaciones × 120 días en lugares aleatorios de tierra firme. Se planta un evento de lluvia extrema (+60 a 120 mm) cerca del final de la serie para que existan alertas climáticas recientes.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_estacion` | texto | 0 | Estación meteorológica. |
| `fecha` | texto | 0 | Día de la medición. |
| `lon` | decimal | 0 | Longitud de la estación simulada (WGS84). |
| `lat` | decimal | 0 | Latitud de la estación simulada (WGS84). |
| `precipitacion_mm` | decimal | 0 | Precipitación diaria en mm. |
| `temperatura_c` | decimal | 0 | Temperatura media en grados C. |
| `viento_kmh` | decimal | 0 | Velocidad del viento en km/h. |

### `comunidades.geojson` — Comunidades

*Vulnerabilidad* · origen **sintético** · GeoJSON · 18 filas · geometría: Puntos

Asentamientos con población aproximada e índice de conflictividad social.

**Cómo se genera:** 18 puntos aleatorios sobre tierra firme (a más de 2 km de la costa y la frontera), con nombres genéricos; conflictividad sesgada a valores bajos (Beta 2,5).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_comunidad` | texto | 0 | Identificador de la comunidad. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `poblacion_aprox` | entero | 0 | Población aproximada. |
| `conflictividad` | decimal | 0 | Índice de conflictividad social, 0 a 1. |

### `hidro.geojson` — Hidrología

*Contexto* · origen **sintético** · GeoJSON · 8 filas · geometría: Líneas

Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en `rios` y `cuerpos_agua`.

**Cómo se genera:** 8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_cuerpo_agua` | texto | 0 | Identificador del cuerpo de agua. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `ideam_estaciones.geojson` — Estaciones del IDEAM

*Catálogo (real)* · origen **IDEAM** · GeoJSON · 219 filas · geometría: Puntos

Catálogo Nacional de Estaciones del IDEAM filtrado a La Guajira: código, nombre, categoría, tecnología, estado, municipio, coordenadas y altitud. Incluye estaciones activas, en mantenimiento y suspendidas.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código de la estación (10 dígitos). |
| `nombre` | texto | 0 | Nombre de la estación (en Plata sin el código entre corchetes ni el sufijo AUT). |
| `categoria` | texto | 0 | Tipo de estación: pluviométrica, climatológica, sinóptica, etc. |
| `tecnologia` | texto | 0 | Convencional, automática, con telemetría, etc. |
| `estado` | texto | 0 | Activa, en mantenimiento o suspendida. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `altitud` | entero | 0 | Altitud en metros sobre el nivel del mar. |
| `longitud` | decimal | 0 | Longitud en grados decimales (WGS84). |
| `latitud` | decimal | 0 | Latitud en grados decimales (WGS84). |
| `fecha_instalacion` | texto | 0 | Fecha de instalación (texto dd/mm/aaaa). |
| `area_operativa` | texto | 0 | Área operativa del IDEAM. |
| `corriente` | texto | 153 | Corriente asociada. |
| `area_hidrografica` | texto | 0 | Área hidrográfica. |
| `zona_hidrografica` | texto | 0 | Zona hidrográfica. |
| `subzona_hidrografica` | texto | 0 | Subzona hidrográfica. |
| `entidad` | texto | 0 | Entidad propietaria de la estación. |
| `fecha_suspension` | texto | 102 | Fecha de suspensión, si aplica. |

### `ideam_normales.parquet` — Normales climatológicas

*Climatología (real)* · origen **IDEAM** · Parquet · 101 filas

Valor típico de cada mes (periodo 1991-2020) por estación y parámetro: precipitación, temperatura media, máxima y mínima, humedad relativa, brillo solar, entre otros. Sirve para decir si un mes va más seco o más lluvioso de lo normal.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `periodo` | texto | 0 | Periodo de la normal (1991-2020). |
| `parametro` | texto | 0 | Parámetro climático tal como lo publica el IDEAM. |
| `codigo` | entero | 0 | Código de la estación (10 dígitos). |
| `categoria` | texto | 0 | Tipo de estación: pluviométrica, climatológica, sinóptica, etc. |
| `estacion` | texto | 0 | Nombre de la estación. |
| `municipio` | texto | 0 | Municipio. |
| `departamento` | texto | 0 | Departamento. |
| `altitud_m` | entero | 0 | Altitud en metros sobre el nivel del mar. |
| `longitud` | decimal | 0 | Longitud en grados decimales (WGS84). |
| `latitud` | decimal | 0 | Latitud en grados decimales (WGS84). |
| `ene` | decimal | 0 | Valor de enero. |
| `feb` | decimal | 0 | Valor de febrero. |
| `mar` | decimal | 0 | Valor de marzo. |
| `abr` | decimal | 0 | Valor de abril. |
| `may` | decimal | 0 | Valor de mayo. |
| `jun` | decimal | 0 | Valor de junio. |
| `jul` | decimal | 0 | Valor de julio. |
| `ago` | decimal | 0 | Valor de agosto. |
| `sep` | decimal | 0 | Valor de septiembre. |
| `oct` | decimal | 0 | Valor de octubre. |
| `nov` | decimal | 0 | Valor de noviembre. |
| `dic` | decimal | 0 | Valor de diciembre. |
| `anual` | decimal | 0 | Valor anual. |
| `parametro_clave` | texto | 0 | Parámetro ya mapeado a nuestra clave (precipitacion, temperatura_media, humedad_relativa...). |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |

*1 columnas sin descripción en el catálogo.*

### `ideam_precip_diaria.parquet` — Precipitación diaria por estación

*Lecturas limpias (real)* · origen **IDEAM** · Parquet · 310 filas

Lluvia diaria en mm por estación, calculada como la suma de las lecturas del día luego de quitar duplicados y valores imposibles. Incluye cuántas lecturas y horas con dato tuvo cada día.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `dia` | fecha | 0 | Día de la medición. |
| `mm` | decimal | 0 | Lluvia del día en mm: suma de las lecturas sin duplicados. |
| `lecturas` | entero | 0 | Cantidad de lecturas distintas del día. |
| `horas_con_dato` | entero | 0 | Horas del día (0 a 24) que tuvieron al menos una lectura; indica qué tan completo es el día. |

### `ideam_radiacion.parquet` — Radiación solar (promedios)

*Climatología (real)* · origen **IDEAM** · Parquet · 7 filas

Radiación global media por estación: un valor para cada mes y el promedio anual, en Wh/m² por día. El IDEAM la publica solo como promedio histórico, no como serie diaria.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `estacion` | texto | 0 | Nombre de la estación. |
| `departamento` | texto | 0 | Departamento. |
| `municipio` | texto | 0 | Municipio. |
| `latitud` | decimal | 0 | Latitud en grados decimales (WGS84). |
| `longitud` | decimal | 0 | Longitud en grados decimales (WGS84). |
| `altitud` | entero | 0 | Altitud en metros sobre el nivel del mar. |
| `tipo_de_estacion` | texto | 0 | Automática o convencional. |
| `promedio_anual` | decimal | 0 | Promedio anual de radiación global (Wh/m² por día). |
| `ene` | decimal | 0 | Valor de enero. |
| `feb` | decimal | 0 | Valor de febrero. |
| `mar` | decimal | 0 | Valor de marzo. |
| `abr` | decimal | 0 | Valor de abril. |
| `may` | decimal | 0 | Valor de mayo. |
| `jun` | decimal | 0 | Valor de junio. |
| `jul` | decimal | 0 | Valor de julio. |
| `ago` | decimal | 0 | Valor de agosto. |
| `sep` | decimal | 0 | Valor de septiembre. |
| `oct` | decimal | 0 | Valor de octubre. |
| `nov` | decimal | 0 | Valor de noviembre. |
| `dic` | decimal | 0 | Valor de diciembre. |
| `codigo` | texto | 1 | Código de la estación (10 dígitos). |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |

### `ideam_ultimas_horas.parquet` — Lecturas de las últimas horas

*Casi en tiempo real (real)* · origen **IDEAM** · Parquet · 2.849 filas

Flujo del IDEAM con las lecturas de las últimas ~12 horas de todas las variables. Es lo que el mapa muestra como valor de ahora; el backend lo consulta en vivo y guarda este respaldo por si no hay internet.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `var` | texto | 0 | Variable ya clasificada por su sensor: temperatura, temp_max, temp_min, humedad, humedad_suelo, viento_vel, viento_dir, presion, nivel_rio, precipitacion... |
| `fecha_hora` | fecha | 0 | Fecha y hora de la lectura. |
| `valor` | decimal | 0 | Valor medido, ya limpio. |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |

### `ideam_variables_diaria.parquet` — Otras variables por día

*Lecturas limpias (real)* · origen **IDEAM** · Parquet · 2.039 filas

Un valor por estación, variable y día (media, mínimo y máximo). Clasifica cada lectura por su sensor (el conjunto de humedad trae también humedad del suelo), quita duplicados y valores fuera de rango, unifica unidades y promedia la dirección del viento como vector.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `var` | texto | 0 | Variable ya clasificada por su sensor: temperatura, temp_max, temp_min, humedad, humedad_suelo, viento_vel, viento_dir, presion, nivel_rio, precipitacion... |
| `dia` | fecha | 0 | Día de la medición. |
| `media` | decimal | 0 | Promedio del día (para la dirección del viento, promedio circular en grados). |
| `minimo` | decimal | 279 | Menor lectura del día. |
| `maximo` | decimal | 279 | Mayor lectura del día. |
| `lecturas` | entero | 0 | Cantidad de lecturas distintas del día. |
| `horas_con_dato` | entero | 0 | Horas del día (0 a 24) que tuvieron al menos una lectura; indica qué tan completo es el día. |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |

### `ideam_variables_horaria.parquet` — Otras variables por hora (limpias)

*Lecturas limpias (real)* · origen **IDEAM** · Parquet · 189.646 filas

Las lecturas de temperatura, humedad, viento, presión y nivel ya clasificadas por sensor, sin duplicados y en unidades unificadas, una fila por estación, variable y hora. Oro calcula de aquí el promedio de las últimas 24 horas; por eso se guarda en Plata y no se vuelve a Bronce.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `var` | texto | 0 | Variable ya clasificada por su sensor: temperatura, temp_max, temp_min, humedad, humedad_suelo, viento_vel, viento_dir, presion, nivel_rio, precipitacion... |
| `fecha_hora` | fecha | 0 | Fecha y hora de la lectura. |
| `valor` | decimal | 0 | Valor medido, ya limpio. |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |
| `dia` | fecha | 0 | Día de la medición. |

*1 columnas sin descripción en el catálogo.*

### `igac_hidrografia.geojson` — Hidrografía unificada

*Ríos y agua (real)* · origen **IGAC** · GeoJSON · 9.823 filas · geometría: Polígonos

Las cinco capas en una sola tabla con la columna `tipo`. Geometrías reparadas, recortadas a la caja de descarga y simplificadas (25 m líneas, 20 m polígonos: de 661 mil a 119 mil vértices), con estado del cauce traducido y nombres normalizados.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_objeto` | texto | 0 | Identificador: tipo de objeto y número de objeto en el servicio del IGAC. |
| `tipo` | texto | 0 | drenaje_sencillo, drenaje_doble, cienaga, laguna o embalse. |
| `nombre` | texto | 7820 | Nombre del río, arroyo o cuerpo de agua, normalizado (vacío si no tiene). |
| `estado` | texto | 218 | Permanente o intermitente, según la clasificación del IGAC a 1:100.000 (no es una medición de caudal). |
| `longitud_km` | decimal | 218 | Longitud del tramo en km, calculada en metros (EPSG:3116). |
| `area_km2` | decimal | 9605 | Área del polígono en km², calculada en metros (EPSG:3116). |

### `igac_vias.geojson` — Vías del IGAC unificadas

*Vías (real)* · origen **IGAC** · GeoJSON · 5.326 filas · geometría: Líneas

Las siete capas en una tabla: clase de vía (pavimentada o no, ancho, accesibilidad), recortadas a los municipios del DANE y simplificadas a 20 m (197 mil a 59 mil vértices).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_via` | texto | 0 | Identificador: tipo de vía, número de objeto y parte (un recorte puede dejar varias). |
| `tipo` | entero | 0 | 1 a 7: 1 pavimentada de 2 o más carriles, 2 sin pavimentar de 2 o más, 3 pavimentada angosta, 4 sin pavimentar angosta, 5 sin pavimentar solo en tiempo seco, 6 sin afirmar (trocha), 7 camino o sendero. |
| `clase` | texto | 0 | Nombre de la clase según la combinación de atributos de cada tipo. |
| `superficie` | texto | 1846 | Pavimentada, sin pavimentar, en construcción o sin afirmar. |
| `carriles` | texto | 5003 | 2 o más carriles, o angosta. |
| `accesibilidad` | texto | 1846 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre` | texto | 5322 | Nombre de la vía; casi ninguna lo tiene (4 de 5.600). |
| `km` | decimal | 0 | Longitud recalculada en metros (EPSG:3116) tras recortar y simplificar. |

### `invias_red_vial.geojson` — Red vial nacional (INVIAS)

*Vías (real)* · origen **INVIAS** · GeoJSON · 9 filas · geometría: MultiLineString

Tramos de la Red Vial Nacional que cruzan La Guajira, tal como los publica INVIAS en datos.gov.co: códigos de dominio sin traducir, "Por Defnir" donde falta el dato y la geometría completa (hasta 14 mil vértices por tramo). En Plata: etiquetas legibles, sin tramos repetidos, recortada a la caja de descarga y simplificada a 15 m.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_tramo` | texto | 0 | Identificador del tramo: ruta, código y número de orden. |
| `codigo_tramo` | texto | 0 | Código del tramo en INVIAS. |
| `ruta` | texto | 0 | Número de la ruta nacional. |
| `nombre_ruta` | texto | 0 | Nombre de la ruta (p. ej. Transversal del Caribe). |
| `nombre_tramo` | texto | 9 | Nombre del tramo (casi siempre "Por Defnir" en la fuente). |
| `sector` | texto | 0 | Sector del tramo (p. ej. Riohacha - Paraguachón). |
| `categoria_txt` | texto | 1 | Primer, segundo o tercer orden; vacío si la fuente dice por definir. |
| `administrador_txt` | texto | 0 | Quién administra el tramo (INVIAS, ANI...). |
| `superficie_txt` | texto | 9 | Pavimentada o sin pavimentar; en La Guajira la fuente la deja sin definir. |
| `calzada_txt` | texto | 0 | Sencilla o doble. |
| `territorial_txt` | texto | 0 | Territorial de INVIAS (no es el límite departamental). |
| `en_guajira` | booleano | 0 | Verdadero si el tramo pertenece a la territorial Guajira. |
| `longitud_km` | decimal | 0 | Longitud del tramo en km, recalculada en metros tras recortar y simplificar. |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

### `municipios.geojson` — Municipios

*Límites (real)* · origen **DANE** · GeoJSON · 15 filas · geometría: Polígonos

Un polígono por municipio con nombre propio, código DANE y área recalculada en metros. La geometría se simplifica sin abrir huecos entre vecinos (125 mil a 14 mil vértices). En Oro suma, por municipio, las estaciones del IDEAM y los kilómetros de vías nacionales.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE (departamento + municipio, 5 dígitos). |
| `nombre` | texto | 0 | Nombre propio del municipio (el DANE lo escribe en mayúsculas y sin tildes). |
| `area_km2` | decimal | 0 | Área calculada en metros (EPSG:3116), en km². |
| `cabecera_lon` | decimal | 0 | Longitud de la cabecera municipal (DIVIPOLA). |
| `cabecera_lat` | decimal | 0 | Latitud de la cabecera municipal (DIVIPOLA). |
| `etiqueta_lon` | decimal | 0 | Longitud de un punto dentro del polígono donde se escribe el nombre en el mapa. |
| `etiqueta_lat` | decimal | 0 | Latitud de ese punto. |

### `paquetes.geojson` — Paquetes de trabajo

*Unidad de análisis* · origen **sintético** · GeoJSON · 14 filas · geometría: Polígonos

Polígonos de los paquetes de trabajo. Son la unidad sobre la que se calcula el ICT.

**Cómo se genera:** 14 círculos (4 a 6 por proyecto), todos dentro de su proyecto y de tierra firme; ~30% marcados como ruta crítica.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |

### `proveniencia_hidrografia.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*44 columnas sin descripción en el catálogo.*

### `proveniencia_ideam.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*115 columnas sin descripción en el catálogo.*

### `proveniencia_invias.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*26 columnas sin descripción en el catálogo.*

### `proveniencia_municipios.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*21 columnas sin descripción en el catálogo.*

### `proveniencia_red_vial.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*63 columnas sin descripción en el catálogo.*

### `proveniencia_vias_igac.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*53 columnas sin descripción en el catálogo.*

### `proyectos.geojson` — Proyectos

*Contexto* · origen **sintético** · GeoJSON · 3 filas · geometría: Polígonos

Límites de los proyectos que agrupan los paquetes de trabajo.

**Cómo se genera:** 3 proyectos ficticios (Norte, Centro, Sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `red_vial.geojson` — Red vial unificada

*Capa del mapa (real)* · origen **INVIAS + IGAC** · GeoJSON · 5.278 filas · geometría: Líneas

La red nacional de INVIAS (8 tramos, ~300 km, con ruta, administrador y categoría) y la red complementaria del IGAC (~18.300 km), en una sola tabla, sin duplicados: lo que el IGAC repite de la red nacional (~320 km, a menos de 50 m) se quitó. La columna `fuente` (INVIAS o IGAC) y `estilo` distinguen cada red. A los tramos de INVIAS, que no traen superficie, se les pone la del IGAC sobre el mismo trazado. Alimenta la capa de vías del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_tramo` | texto | 0 | Identificador: fuente y número de tramo. |
| `fuente` | texto | 0 | INVIAS (red nacional) o IGAC (red complementaria). |
| `grupo` | texto | 0 | Red nacional o Red complementaria. |
| `estilo` | texto | 0 | Clave de dibujo: n0 a n2 (categorías de INVIAS) e i1 a i7 (clases del IGAC). |
| `clase` | texto | 0 | Clase de vía: categoría de INVIAS o clase interpretada del IGAC. |
| `ruta` | texto | 5270 | Número de la ruta nacional (solo INVIAS). |
| `nombre_ruta` | texto | 5270 | Nombre de la ruta (solo INVIAS). |
| `sector` | texto | 5270 | Sector del tramo (solo INVIAS). |
| `administrador` | texto | 5270 | Quién administra el tramo (solo INVIAS). |
| `calzada` | texto | 5270 | Sencilla o doble (solo INVIAS). |
| `superficie` | texto | 1840 | Pavimentada, sin pavimentar... En INVIAS, tomada del IGAC sobre el mismo trazado. |
| `superficie_fuente` | texto | 1840 | De dónde sale la superficie: INVIAS, IGAC o IGAC (cruce espacial). |
| `carriles` | texto | 4985 | 2 o más carriles, o angosta (solo IGAC). |
| `accesibilidad` | texto | 1847 | Todo el año o solo en tiempo seco (solo IGAC). |
| `nombre` | texto | 5276 | Nombre de la vía, si lo tiene. |
| `km` | decimal | 0 | Longitud del tramo en km, recalculada en metros. |

### `reporte_calidad_bronce_a_plata.csv` — Reporte de calidad

*Control de calidad* · origen **sintético** · CSV · 1 filas

Resumen del paso Bronce a Plata: filas de entrada, duplicados removidos, registros sin coordenadas y filas resultantes.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `filas_bronce` | entero | 0 | Filas que llegaron en Bronce. |
| `duplicados_removidos` | entero | 0 | Registros repetidos eliminados. |
| `sin_coordenadas_originales` | entero | 0 | Registros sin lat/lon; se ubican por el centroide de su paquete. |
| `riesgos_sin_paquete_valido` | entero | 0 | Registros que no se pudieron ubicar y se descartan. |
| `filas_plata` | entero | 0 | Filas resultantes en Plata. |

### `reporte_calidad_hidrografia.csv` — Reporte de calidad de hidrografía

*Control de calidad (real)* · origen **IGAC** · CSV · 1 filas

Objetos y vértices antes y después, nombres vacíos y kilómetros de cauce por estado.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objetos_bronce` | entero | 0 | Objetos descargados. |
| `vertices_bronce` | entero | 0 | Vértices descargados. |
| `sin_geometria` | entero | 0 | Objetos sin geometría (descartados). |
| `geometrias_invalidas_reparadas` | entero | 0 | Geometrías inválidas que se repararon. |
| `sin_nombre` | entero | 0 | Objetos sin nombre geográfico. |
| `lineas_sin_estado` | entero | 0 | Líneas sin estado de cauce. |
| `objetos_plata` | entero | 0 | Objetos que quedan en Plata. |
| `vertices_plata` | entero | 0 | Vértices tras simplificar. |
| `km_rios` | entero | 0 | Kilómetros de cauce en la caja (incluye zonas de Cesar, Magdalena y frontera). |
| `km_permanentes` | entero | 0 | Kilómetros de cauce permanente. |
| `km_intermitentes` | entero | 0 | Kilómetros de cauce intermitente. |
| `km2_cuerpos_de_agua` | decimal | 0 | Área de ríos anchos, ciénagas, lagunas y embalses. |

*2 columnas sin descripción en el catálogo.*

### `reporte_calidad_ideam.csv` — Reporte de calidad del IDEAM

*Control de calidad (real)* · origen **IDEAM** · CSV · 1 filas

Duplicados removidos, lecturas descartadas y estaciones que quedaron con lluvia diaria.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `estaciones_bronce` | entero | 0 | Estaciones que llegaron del catálogo. |
| `estaciones_fuera_de_la_caja` | entero | 0 | Estaciones con coordenadas fuera de La Guajira (descartadas). |
| `estaciones_plata` | entero | 0 | Estaciones que pasaron la validación. |
| `lecturas_bronce` | entero | 0 | Lecturas descargadas. |
| `lecturas_sin_fecha_o_valor` | entero | 0 | Lecturas sin fecha o sin valor (descartadas). |
| `lecturas_imposibles` | entero | 0 | Lecturas negativas o de más de 200 mm en un solo registro (descartadas). |
| `duplicados_removidos` | entero | 0 | Registros repetidos eliminados. |
| `lecturas_plata` | entero | 0 | Lecturas que quedaron tras quitar duplicados. |
| `estaciones_con_lluvia_diaria` | entero | 0 | Estaciones con al menos un día de lluvia calculado. |
| `var_bronce` | entero | 0 | Lecturas de las otras variables descargadas. |
| `var_reasignadas_por_sensor` | entero | 0 | Lecturas cuyo sensor no correspondía al conjunto de origen (p. ej. humedad del suelo dentro del conjunto de humedad) y se reclasificaron. |
| `var_sensor_descartado` | entero | 0 | Lecturas de sensores que no usamos (nivel máximo/mínimo horario, etc.). |
| `var_sin_fecha_o_valor` | entero | 0 | Lecturas sin fecha o valor. |
| `var_fuera_de_rango` | entero | 0 | Lecturas fuera del rango físico posible (p. ej. -999). |
| `var_duplicados_removidos` | entero | 0 | Duplicados quitados (varios canales para el mismo sensor). |
| `var_plata` | entero | 0 | Lecturas que quedaron. |
| `var_estaciones` | entero | 0 | Estaciones con al menos una variable. |
| `ult_bronce` | entero | 0 | Lecturas del flujo de últimas horas antes de la limpieza. |
| `ult_sensor_descartado` | entero | 0 | Lecturas de últimas horas de sensores que no usamos. |
| `ult_sin_fecha_o_valor` | entero | 0 | Sin fecha o valor. |
| `ult_fuera_de_rango` | entero | 0 | Fuera de rango físico. |
| `ult_duplicados_removidos` | entero | 0 | Duplicados. |
| `ult_plata` | entero | 0 | Lecturas del flujo de últimas horas que quedaron. |
| `radiacion_registros` | entero | 0 | Estaciones con radiación en La Guajira. |
| `radiacion_con_estacion_en_catalogo` | entero | 0 | Las que se pudieron emparejar con el catálogo por nombre y municipio. |
| `normales_filas` | entero | 0 | Filas de normales climatológicas (una por estación, parámetro y periodo). |
| `normales_estaciones` | entero | 0 | Estaciones con normales. |

*2 columnas sin descripción en el catálogo.*

### `reporte_calidad_invias.csv` — Reporte de calidad de vías

*Control de calidad (real)* · origen **INVIAS** · CSV · 1 filas

Tramos y vértices antes y después, tramos repetidos quitados y datos sin definir en la fuente.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `tramos_bronce` | entero | 0 | Tramos descargados. |
| `vertices_bronce` | entero | 0 | Vértices descargados. |
| `sin_geometria` | entero | 0 | Tramos sin geometría (descartados). |
| `longitud_no_coincide` | entero | 0 | Tramos cuya longitud calculada difiere más de 5 % de la que trae la fuente. |
| `repetidos_removidos` | entero | 0 | Tramos cuya geometría ya estaba cubierta por otros (una geometría suma dos tramos). |
| `nombre_tramo_por_definir` | entero | 0 | Tramos con nombre "Por Defnir". |
| `superficie_por_definir` | entero | 0 | Tramos sin tipo de superficie. |
| `categoria_por_definir` | entero | 0 | Tramos sin categoría. |
| `tramos_plata` | entero | 0 | Tramos que quedan en Plata. |
| `vertices_plata` | entero | 0 | Vértices tras simplificar. |
| `km_plata` | decimal | 0 | Kilómetros en Plata (incluye tramos de otras territoriales). |

*2 columnas sin descripción en el catálogo.*

### `reporte_calidad_municipios.csv` — Reporte de calidad de municipios

*Control de calidad (real)* · origen **DANE** · CSV · 1 filas

Geometrías inválidas, diferencia de área con la fuente, partes del departamento y huecos entre municipios.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipios_bronce` | entero | 0 | Municipios descargados. |
| `vertices_bronce` | entero | 0 | Vértices descargados. |
| `geometrias_invalidas` | entero | 0 | Geometrías inválidas (se repararon). |
| `sin_divipola` | entero | 0 | Municipios sin fila en DIVIPOLA. |
| `nombre_distinto_en_divipola` | entero | 0 | Municipios cuyo nombre difiere del DIVIPOLA. |
| `diferencia_maxima_de_area_km2` | decimal | 0 | Mayor diferencia entre el área calculada y la que trae la fuente. |
| `partes_del_departamento` | entero | 0 | Partes en que queda la unión (1 = territorio continuo). |
| `huecos_entre_municipios` | entero | 0 | Huecos dentro de la unión (1 ya viene en el dato del DANE). |
| `municipios_plata` | entero | 0 | Municipios que quedan. |
| `vertices_plata` | entero | 0 | Vértices tras simplificar. |
| `km2_departamento` | decimal | 0 | Área total de La Guajira. |

### `reporte_calidad_red_vial.csv` — Reporte de calidad de la red vial

*Control de calidad (real)* · origen **INVIAS + IGAC** · CSV · 1 filas

Kilómetros de cada fuente, cuántos repetía el IGAC, cuántos tramos de INVIAS recibieron superficie del IGAC y el total unificado.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `tramos_invias` | entero | 0 | Tramos de INVIAS de entrada. |
| `tramos_igac` | entero | 0 | Tramos del IGAC de entrada. |
| `km_invias` | decimal | 0 | Kilómetros de INVIAS. |
| `km_igac` | decimal | 0 | Kilómetros del IGAC antes de quitar lo repetido. |
| `tramos_invias_con_superficie_del_igac` | entero | 0 | Tramos de INVIAS que recibieron superficie del IGAC. |
| `km_igac_repetido_con_invias` | decimal | 0 | Kilómetros del IGAC a menos de 50 m de una vía de INVIAS (se quitaron). |
| `km_igac_astillas_quitadas` | decimal | 0 | Kilómetros en pedazos menores a 100 m junto a la red nacional (se quitaron). |
| `tramos_red` | entero | 0 | Tramos de la red unificada. |
| `vertices_red` | entero | 0 | Vértices de la red unificada. |
| `km_red` | entero | 0 | Kilómetros totales. |
| `km_red_nacional` | decimal | 0 | Kilómetros de la red nacional. |
| `km_red_complementaria` | entero | 0 | Kilómetros de la red complementaria. |
| `km_solo_tiempo_seco` | entero | 0 | Kilómetros que solo se transitan en tiempo seco. |

*1 columnas sin descripción en el catálogo.*

### `reporte_calidad_vias_igac.csv` — Reporte de calidad de vías del IGAC

*Control de calidad (real)* · origen **IGAC** · CSV · 1 filas

Objetos y vértices antes y después, kilómetros por clase y atributos sin valor.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `objetos_bronce` | entero | 0 | Objetos descargados. |
| `vertices_bronce` | entero | 0 | Vértices descargados. |
| `sin_geometria` | entero | 0 | Objetos sin geometría. |
| `tipo_desconocido` | entero | 0 | Objetos con un tipo fuera de 1 a 7. |
| `recortada_a` | texto | 0 | Límite usado para recortar. |
| `atributos_sin_valor` | entero | 0 | Vías de tipo 1 a 6 sin superficie en la fuente. |
| `objetos_plata` | entero | 0 | Objetos que quedan. |
| `vertices_plata` | entero | 0 | Vértices tras recortar y simplificar. |
| `km_total` | entero | 0 | Kilómetros de vías dentro de La Guajira. |
| `km_pavimentadas` | entero | 0 | Kilómetros pavimentados (tipos 1 y 3). |
| `km_solo_tiempo_seco` | entero | 0 | Kilómetros que solo se transitan en tiempo seco. |
| `km_caminos` | entero | 0 | Kilómetros de caminos y senderos. |

*3 columnas sin descripción en el catálogo.*

### `riesgos.geojson` — Registro de riesgos

*Registro* · origen **sintético** · GeoJSON · 200 filas · geometría: Puntos

Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, con probabilidad, impacto, estado de materialización y acción de tratamiento.

**Cómo se genera:** 200 riesgos repartidos en los 14 paquetes. Tres paquetes 'calientes' reciben más riesgos y con probabilidad e impacto altos, para que el mapa muestre patrones. ~18% son oportunidades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_evento_riesgo` | texto | 6 | Identificador del evento de riesgo asociado. |
| `descripcion` | texto | 0 | Descripción textual del riesgo. |
| `causa` | texto | 0 | Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'. |
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `probabilidad` | entero | 0 | Escala de 1 a 5. |
| `impacto` | entero | 0 | Escala de 1 a 5. |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `id_paquete_trabajo` | texto | 0 | Paquete de trabajo al que pertenece (llave hacia paquetes). |
| `fecha_identificacion` | fecha | 0 | Fecha en que se identificó el riesgo. |
| `fecha_materializacion` | fecha | 161 | Fecha de materialización; vacía si no se ha materializado. |
| `accion_tratamiento` | texto | 0 | Acción de tratamiento definida. |
| `fecha_ejecucion_accion` | fecha | 16 | Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida. |
| `lat` | decimal | 0 | Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `lon` | decimal | 0 | Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `geolocalizacion_inferida` | booleano | 0 | Verdadero si la ubicación se tomó del centroide del paquete porque el registro no traía coordenadas. |
| `severidad` | entero | 0 | probabilidad × impacto (1 a 25). |

### `vias.geojson` — Vías

*Contexto* · origen **sintético** · GeoJSON · 10 filas · geometría: Líneas

Red vial por tipo (primaria, secundaria, terciaria de difícil acceso). Es la inventada; la red real (INVIAS e IGAC) está en `red_vial` y aún no alimenta el ICT.

**Cómo se genera:** 10 segmentos rectos con tipo aleatorio, enteros dentro de tierra firme.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_via` | texto | 0 | Identificador de la vía. |
| `tipo` | texto | 0 | primaria, secundaria o terciaria de difícil acceso. |

## Oro

### `alertas.json` — Alertas

*Resultado del modelo* · origen **sintético** · JSON · 4 filas

Paquetes que cumplen alguna regla de escalamiento o de tendencia, con sus motivos.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `nombre_paquete` | texto | 0 | Nombre del paquete. |
| `ict` | decimal | 0 | ICT del paquete en alerta. |
| `nivel` | texto | 0 | bajo, medio, alto o crítico según los umbrales. |
| `motivos` | lista | 0 | Lista de reglas que dispararon la alerta. |
| `generada_en` | texto | 0 | Fecha del corte que generó la alerta. |

### `areas.geojson` — Áreas protegidas

*Vulnerabilidad* · origen **sintético** · GeoJSON · 6 filas · geometría: Polígonos

Áreas de interés ambiental con un índice de sensibilidad.

**Cómo se genera:** 6 círculos enteros dentro de tierra firme, con categorías ficticias (parque, reserva, humedal) y sensibilidad 0.4 a 1.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_area` | texto | 0 | Identificador del área protegida. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `categoria` | texto | 0 | Tipo de área protegida (ficticia). |
| `sensibilidad` | decimal | 0 | Índice de sensibilidad ambiental, 0 a 1. |

### `clima_estaciones.geojson` — Estaciones con clima

*Capa del mapa (real)* · origen **IDEAM** · GeoJSON · 14 filas · geometría: Puntos

Un punto por estación que reportó: lluvia acumulada 7, 14 y 30 días, y para cada variable la última lectura, el resumen de 30 días y su serie diaria, más las lecturas de las últimas horas y las normales del mes. Alimenta la capa de clima del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código de la estación (10 dígitos). |
| `nombre` | texto | 0 | Nombre de la estación (en Plata sin el código entre corchetes ni el sufijo AUT). |
| `municipio` | texto | 0 | Municipio. |
| `categoria` | texto | 0 | Tipo de estación: pluviométrica, climatológica, sinóptica, etc. |
| `tecnologia` | texto | 0 | Convencional, automática, con telemetría, etc. |
| `estado` | texto | 0 | Activa, en mantenimiento o suspendida. |
| `altitud` | decimal | 0 | Altitud en metros sobre el nivel del mar. |
| `ultimo_dato` | fecha | 2 | Fecha de la última lectura de la estación. |
| `dias_sin_dato` | decimal | 2 | Días entre la última lectura de la estación y la más reciente de todas. |
| `mm_7d` | decimal | 2 | Lluvia acumulada en los últimos 7 días (mm). |
| `mm_14d` | decimal | 2 | Lluvia acumulada en los últimos 14 días (mm). |
| `mm_30d` | decimal | 2 | Lluvia acumulada en los últimos 30 días (mm). |
| `max_diario_mm` | decimal | 2 | Mayor lluvia en un solo día de la ventana (mm). |
| `dias_con_dato` | entero | 0 | Días de la ventana de 30 con al menos una lectura. |
| `cobertura` | decimal | 0 | Fracción del tiempo de la ventana con datos (0 a 1). Con menos de 0,5 el acumulado puede estar subestimado. |
| `serie` | lista | 0 | Lluvia diaria de los 30 días de la ventana (lista de día y mm). |
| `variables` | texto | 0 | Por variable: unidad, última lectura, promedio de 24 h, mín/media/máx de 30 días, cobertura y serie diaria. |
| `ahora` | texto | 0 | Última lectura de cada variable en las últimas horas. |
| `normales` | texto | 0 | Normal climatológica mensual de la estación (lluvia, temperatura, humedad). |
| `radiacion` | texto | 11 | Radiación media mensual de la estación, si tiene sensor calibrado. |

### `clima_radiacion.geojson` — Estaciones con radiación

*Capa del mapa (real)* · origen **IDEAM** · GeoJSON · 7 filas · geometría: Puntos

Un punto por estación con radiación media mensual y anual. Alimenta la vista de radiación del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `estacion` | texto | 0 | Nombre de la estación. |
| `municipio` | texto | 0 | Municipio. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `altitud` | decimal | 0 | Altitud en metros sobre el nivel del mar. |
| `anual` | decimal | 0 | Valor anual. |
| `meses` | texto | 0 | Doce valores mensuales (enero a diciembre). |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |
| `codigo` | texto | 1 | Código de la estación (10 dígitos). |

### `comunidades.geojson` — Comunidades

*Vulnerabilidad* · origen **sintético** · GeoJSON · 18 filas · geometría: Puntos

Asentamientos con población aproximada e índice de conflictividad social.

**Cómo se genera:** 18 puntos aleatorios sobre tierra firme (a más de 2 km de la costa y la frontera), con nombres genéricos; conflictividad sesgada a valores bajos (Beta 2,5).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_comunidad` | texto | 0 | Identificador de la comunidad. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `poblacion_aprox` | entero | 0 | Población aproximada. |
| `conflictividad` | decimal | 0 | Índice de conflictividad social, 0 a 1. |

### `cuerpos_agua.geojson` — Cuerpos de agua para el mapa

*Capa del mapa (real)* · origen **IGAC** · GeoJSON · 218 filas · geometría: Polígonos

Ríos anchos, ciénagas, lagunas y embalses como polígonos con su área en km².

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_objeto` | texto | 0 | Identificador: tipo de objeto y número de objeto en el servicio del IGAC. |
| `tipo` | texto | 0 | drenaje_sencillo, drenaje_doble, cienaga, laguna o embalse. |
| `nombre` | texto | 118 | Nombre del río, arroyo o cuerpo de agua, normalizado (vacío si no tiene). |
| `area_km2` | decimal | 0 | Área del polígono en km², calculada en metros (EPSG:3116). |

### `grid_calor.geojson` — Superficie de calor

*Resultado del modelo* · origen **sintético** · GeoJSON · 620 filas · geometría: Puntos

Grilla de puntos con la densidad kernel de los riesgos ponderada por severidad. Alimenta el mapa de calor.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `celda_id` | texto | 0 | Identificador de la celda de la grilla. |
| `intensidad` | decimal | 0 | Densidad kernel normalizada 0 a 1 (ponderada por severidad). |

### `hidro.geojson` — Hidrología

*Contexto* · origen **sintético** · GeoJSON · 8 filas · geometría: Líneas

Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en `rios` y `cuerpos_agua`.

**Cómo se genera:** 8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_cuerpo_agua` | texto | 0 | Identificador del cuerpo de agua. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `limite_departamental.geojson` — Contorno de La Guajira

*Límites (real)* · origen **DANE** · GeoJSON · 1 filas · geometría: Polígonos

La unión de los 15 municipios: un solo polígono de ~20.670 km². Sirve para recortar otras capas al departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `nombre` | texto | 0 | Nombre propio del municipio (el DANE lo escribe en mayúsculas y sin tildes). |
| `codigo` | texto | 0 | Código DANE (departamento + municipio, 5 dígitos). |
| `area_km2` | decimal | 0 | Área calculada en metros (EPSG:3116), en km². |

### `municipios.geojson` — Municipios

*Límites (real)* · origen **DANE** · GeoJSON · 15 filas · geometría: Polígonos

Un polígono por municipio con nombre propio, código DANE y área recalculada en metros. La geometría se simplifica sin abrir huecos entre vecinos (125 mil a 14 mil vértices). En Oro suma, por municipio, las estaciones del IDEAM y los kilómetros de vías nacionales.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE (departamento + municipio, 5 dígitos). |
| `nombre` | texto | 0 | Nombre propio del municipio (el DANE lo escribe en mayúsculas y sin tildes). |
| `area_km2` | decimal | 0 | Área calculada en metros (EPSG:3116), en km². |
| `cabecera_lon` | decimal | 0 | Longitud de la cabecera municipal (DIVIPOLA). |
| `cabecera_lat` | decimal | 0 | Latitud de la cabecera municipal (DIVIPOLA). |
| `etiqueta_lon` | decimal | 0 | Longitud de un punto dentro del polígono donde se escribe el nombre en el mapa. |
| `etiqueta_lat` | decimal | 0 | Latitud de ese punto. |
| `estaciones_catalogo` | entero | 0 | Estaciones del catálogo del IDEAM ubicadas dentro del polígono. |
| `estaciones_con_datos` | entero | 0 | Estaciones con datos recientes (las del mapa de clima) dentro del polígono. |
| `km_vias` | entero | 0 | Kilómetros de la red vial unificada (INVIAS + IGAC, sin duplicados) dentro del municipio. |
| `km_vias_nacionales` | decimal | 0 | Kilómetros de la red vial nacional (INVIAS) que pasan por el municipio. |
| `km_vias_solo_tiempo_seco` | entero | 0 | De esos, los que solo se transitan en tiempo seco (según el IGAC). |

### `paquetes_ict.geojson` — Paquetes con ICT

*Resultado del modelo* · origen **sintético** · GeoJSON · 14 filas · geometría: Polígonos

Tabla principal de consumo: cada paquete con sus 5 criterios normalizados, la contribución de cada uno, el ICT, el nivel, las reglas de escalamiento, la tendencia y el resultado de Getis-Ord.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |
| `severidad_riesgo` | decimal | 0 | Criterio normalizado 0 a 1: severidad agregada de las amenazas. |
| `exposicion_proyecto` | decimal | 0 | Criterio normalizado 0 a 1: ruta crítica y cantidad de riesgos. |
| `vulnerabilidad_territorial` | decimal | 0 | Criterio normalizado 0 a 1: cercanía a comunidades y áreas protegidas. |
| `amenazas_externas` | decimal | 0 | Criterio normalizado 0 a 1: lluvia acumulada en la estación más cercana. |
| `convergencia` | decimal | 0 | Criterio normalizado 0 a 1: categorías distintas de amenaza en el paquete. |
| `ICT` | decimal | 0 | Índice de Criticidad Territorial, 0 a 100. |
| `severidad_riesgo_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `exposicion_proyecto_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `vulnerabilidad_territorial_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `amenazas_externas_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `convergencia_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `nivel` | texto | 0 | bajo, medio, alto o crítico según los umbrales. |
| `indice_confianza` | decimal | 0 | Fracción de criterios con dato disponible (0 a 1). |
| `indice_oportunidad` | decimal | 0 | Índice equivalente al ICT calculado sobre las oportunidades, 0 a 100. |
| `escalamiento` | booleano | 0 | Verdadero si el paquete cumple alguna regla de escalamiento a crisis. |
| `causas_escalamiento` | texto | 0 | Reglas que se cumplieron, separadas por punto y coma. |
| `ict_hace_ndias` | decimal | 0 | ICT recalculado con los datos de hace 7 días (mismos límites de normalización). |
| `tendencia_delta` | decimal | 0 | Cambio del ICT en los últimos 7 días. |
| `tendencia_alerta` | booleano | 0 | Verdadero si el ICT subió más que el umbral de tendencia. |
| `z_score` | decimal | 0 | Estadístico z de Getis-Ord Gi*. |
| `clasificacion` | texto | 0 | Punto caliente, punto frío o sin patrón significativo (95%). |

### `proyectos.geojson` — Proyectos

*Contexto* · origen **sintético** · GeoJSON · 3 filas · geometría: Polígonos

Límites de los proyectos que agrupan los paquetes de trabajo.

**Cómo se genera:** 3 proyectos ficticios (Norte, Centro, Sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `red_vial.geojson` — Red vial unificada

*Capa del mapa (real)* · origen **INVIAS + IGAC** · GeoJSON · 5.278 filas · geometría: Líneas

La red nacional de INVIAS (8 tramos, ~300 km, con ruta, administrador y categoría) y la red complementaria del IGAC (~18.300 km), en una sola tabla, sin duplicados: lo que el IGAC repite de la red nacional (~320 km, a menos de 50 m) se quitó. La columna `fuente` (INVIAS o IGAC) y `estilo` distinguen cada red. A los tramos de INVIAS, que no traen superficie, se les pone la del IGAC sobre el mismo trazado. Alimenta la capa de vías del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_tramo` | texto | 0 | Identificador: fuente y número de tramo. |
| `fuente` | texto | 0 | INVIAS (red nacional) o IGAC (red complementaria). |
| `grupo` | texto | 0 | Red nacional o Red complementaria. |
| `estilo` | texto | 0 | Clave de dibujo: n0 a n2 (categorías de INVIAS) e i1 a i7 (clases del IGAC). |
| `clase` | texto | 0 | Clase de vía: categoría de INVIAS o clase interpretada del IGAC. |
| `ruta` | texto | 5270 | Número de la ruta nacional (solo INVIAS). |
| `nombre_ruta` | texto | 5270 | Nombre de la ruta (solo INVIAS). |
| `sector` | texto | 5270 | Sector del tramo (solo INVIAS). |
| `administrador` | texto | 5270 | Quién administra el tramo (solo INVIAS). |
| `calzada` | texto | 5270 | Sencilla o doble (solo INVIAS). |
| `superficie` | texto | 1840 | Pavimentada, sin pavimentar... En INVIAS, tomada del IGAC sobre el mismo trazado. |
| `superficie_fuente` | texto | 1840 | De dónde sale la superficie: INVIAS, IGAC o IGAC (cruce espacial). |
| `carriles` | texto | 4985 | 2 o más carriles, o angosta (solo IGAC). |
| `accesibilidad` | texto | 1847 | Todo el año o solo en tiempo seco (solo IGAC). |
| `nombre` | texto | 5276 | Nombre de la vía, si lo tiene. |
| `km` | decimal | 0 | Longitud del tramo en km, recalculada en metros. |

### `reporte_cruces_municipios.csv` — Cruces espaciales de municipios

*Control de calidad (real)* · origen **DANE** · CSV · 1 filas

Lo que encontró el cruce de los municipios con otras fuentes: estaciones del IDEAM fuera de los polígonos o en un municipio distinto del declarado, y kilómetros de vías dentro de los municipios.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `estaciones_catalogo` | entero | 0 | Estaciones del catálogo del IDEAM ubicadas dentro del polígono. |
| `estaciones_fuera_de_la_guajira` | entero | 0 | Estaciones del catálogo que caen fuera de los 15 polígonos (casi todas en la costa o el mar). |
| `estaciones_en_otro_municipio_que_el_declarado` | entero | 0 | Estaciones cuyo municipio en el catálogo no coincide con el polígono donde caen. |
| `km_vias_en_municipios` | entero | 0 | Kilómetros de la red vial unificada dentro de los municipios. |

*1 columnas sin descripción en el catálogo.*

### `riesgos.geojson` — Registro de riesgos

*Registro* · origen **sintético** · GeoJSON · 200 filas · geometría: Puntos

Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, con probabilidad, impacto, estado de materialización y acción de tratamiento.

**Cómo se genera:** 200 riesgos repartidos en los 14 paquetes. Tres paquetes 'calientes' reciben más riesgos y con probabilidad e impacto altos, para que el mapa muestre patrones. ~18% son oportunidades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_evento_riesgo` | texto | 6 | Identificador del evento de riesgo asociado. |
| `descripcion` | texto | 0 | Descripción textual del riesgo. |
| `causa` | texto | 0 | Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'. |
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `probabilidad` | entero | 0 | Escala de 1 a 5. |
| `impacto` | entero | 0 | Escala de 1 a 5. |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `id_paquete_trabajo` | texto | 0 | Paquete de trabajo al que pertenece (llave hacia paquetes). |
| `fecha_identificacion` | fecha | 0 | Fecha en que se identificó el riesgo. |
| `fecha_materializacion` | fecha | 161 | Fecha de materialización; vacía si no se ha materializado. |
| `accion_tratamiento` | texto | 0 | Acción de tratamiento definida. |
| `fecha_ejecucion_accion` | fecha | 16 | Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida. |
| `lat` | decimal | 0 | Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `lon` | decimal | 0 | Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `geolocalizacion_inferida` | booleano | 0 | Verdadero si la ubicación se tomó del centroide del paquete porque el registro no traía coordenadas. |
| `severidad` | entero | 0 | probabilidad × impacto (1 a 25). |

### `rios.geojson` — Ríos para el mapa

*Capa del mapa (real)* · origen **IGAC** · GeoJSON · 9.605 filas · geometría: Líneas

Tramos de ríos, arroyos y quebradas con nombre (si tiene), estado del cauce y longitud. Alimenta la capa de ríos del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_objeto` | texto | 0 | Identificador: tipo de objeto y número de objeto en el servicio del IGAC. |
| `nombre` | texto | 7702 | Nombre del río, arroyo o cuerpo de agua, normalizado (vacío si no tiene). |
| `estado` | texto | 0 | Permanente o intermitente, según la clasificación del IGAC a 1:100.000 (no es una medición de caudal). |
| `longitud_km` | decimal | 0 | Longitud del tramo en km, calculada en metros (EPSG:3116). |

### `validacion_backtest.csv` — Validación: backtest

*Validación* · origen **sintético** · CSV · 14 filas

ICT de cada paquete frente al número de riesgos que ya se materializaron.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `ICT` | decimal | 0 | ICT del paquete en el corte actual. |
| `nivel` | texto | 0 | Nivel del paquete. |
| `n_riesgos_materializados` | entero | 0 | Riesgos materializados dentro del paquete. |

### `validacion_sensibilidad.csv` — Validación: sensibilidad

*Validación* · origen **sintético** · CSV · 10 filas

Cuánto cambia el ranking de paquetes si cada peso se mueve +/-20%.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `criterio` | texto | 0 | Criterio cuyo peso se perturba. |
| `variacion` | texto | 0 | Perturbación aplicada al peso (+20% o -20%). |
| `correlacion_ranking_spearman` | decimal | 0 | Correlación de Spearman entre el ranking original y el perturbado. |
| `paquetes_que_cambian_de_nivel` | entero | 0 | Paquetes que cambian de nivel con la perturbación. |

### `vias.geojson` — Vías

*Contexto* · origen **sintético** · GeoJSON · 10 filas · geometría: Líneas

Red vial por tipo (primaria, secundaria, terciaria de difícil acceso). Es la inventada; la red real (INVIAS e IGAC) está en `red_vial` y aún no alimenta el ICT.

**Cómo se genera:** 10 segmentos rectos con tipo aleatorio, enteros dentro de tierra firme.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_via` | texto | 0 | Identificador de la vía. |
| `tipo` | texto | 0 | primaria, secundaria o terciaria de difícil acceso. |
