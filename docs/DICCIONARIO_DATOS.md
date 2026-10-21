# Diccionario de datos

> Generado automáticamente por `python -m documentar` a partir de los archivos que hay hoy en `data/` y de las descripciones de
> `app/catalogo.py`. No se edita a mano: para cambiar una descripción, cámbiala en el catálogo. El proceso que produce cada
> tabla está en [PIPELINE.md](PIPELINE.md).

## Bronce

### `actividades_cronograma.csv` — Actividades de los paquetes

*Ejecución (fuente única del avance y las fechas)* · origen **sintético** · CSV · 86 filas

Entre 5 y 7 actividades por paquete (ingeniería, gestión social, licencias, compras, obra civil, montaje, pruebas, cierre), en secuencia. Cada una pesa una fracción de su paquete (suma 1) y, por el peso del paquete en el proyecto, una fracción del proyecto (suma 1). Lleva fechas planeadas, reales y proyectadas: la proyectada es la real si ya ocurrió y, si falta, un pronóstico al ritmo que lleva el paquete.

**Cómo se genera:** Sintético y sucio a propósito: estado escrito de varias formas, algunos avances en porcentaje (0 a 100) y filas repetidas. Plata las limpia: el estado se deriva del avance, los pesos se renormalizan a 1 y las fechas invertidas se corrigen.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_actividad` | texto | 0 | Identificador de la actividad (paquete + número). |
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `orden` | entero | 0 | Posición de la actividad dentro del paquete (van en secuencia). |
| `nombre` | texto | 0 | Nombre de la actividad. |
| `disciplina` | texto | 0 | Disciplina que la ejecuta. |
| `peso_en_paquete` | decimal | 0 | Fracción del paquete que representa la actividad (suma 1 por paquete). |
| `fecha_inicio_plan` | texto | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | texto | 0 | Fin planeado (línea base). |
| `avance` | decimal | 0 | Fracción ejecutada (0 a 1); en un paquete o proyecto es la suma de peso × avance de sus actividades. |
| `estado` | texto | 0 | por_iniciar, en_curso o completada (se deriva del avance). |
| `fecha_inicio_real` | texto | 26 | Inicio real (solo si ya empezó). |
| `fecha_fin_real` | texto | 40 | Fin real (solo si ya terminó). |
| `fecha_inicio_proyectada` | texto | 0 | Inicio proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_fin_proyectada` | texto | 0 | Fin proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_corte` | texto | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |

### `ant_resguardos.geojson` — Resguardos indígenas (crudos)

*Territorio étnico (real)* · origen **sintético** · GeoJSON · 41 filas · geometría: Polígonos

Polígonos de los resguardos formalizados de la Agencia Nacional de Tierras que cruzan la caja de La Guajira, tal como llegan.

*13 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

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

### `art_pdet.csv` — Municipios PDET (crudo)

*Contexto (real)* · origen **sintético** · CSV · 170 filas

Los 170 municipios de los Programas de Desarrollo con Enfoque Territorial (ART). En La Guajira: Dibulla, Fonseca y San Juan del Cesar.

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `chirps_meta.json` — Metadatos de la descarga de CHIRPS

*Trazabilidad (real)* · origen **sintético** · JSON · 1 filas

Fuente (CHIRPS v3.0 del Climate Hazards Center, UC Santa Barbara), licencia CC BY 4.0, cita, fecha, caja de descarga y meses bajados. Los meses quedan en Bronce como un GeoTIFF cada uno (carpeta `bronze/chirps/`, rejilla de 0,05° con los valores tal como vienen; -9999 en el mar).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Producto y organización que lo publica. |
| `licencia` | texto | 0 | CC BY 4.0: uso libre citando la fuente. |
| `cita` | texto | 0 | Cómo citar CHIRPS (DOI). |
| `servicio` | texto | 0 | Carpeta de los archivos mensuales (COG) en el servidor de UC Santa Barbara. |
| `resolucion_grados` | decimal | 0 | Tamaño de la celda en grados (0,05 ≈ 5,5 km). |
| `unidad` | texto | 0 | Unidad de los valores. |
| `nodata` | decimal | 0 | Valor de las celdas sin dato (mar). |
| `descargado_en` | texto | 0 | Fecha y hora de la última descarga. |
| `desde` | texto | 0 | Primer mes. |
| `hasta` | texto | 0 | Último mes (CHIRPS publica ~3 semanas después de terminar el mes). |
| `meses` | entero | 0 | Meses guardados en Bronce. |
| `meses_fallidos` | lista | 0 | Meses que no se pudieron bajar. |
| `caja.lat_sur` | decimal | 0 | Caja de descarga: latitud sur. |
| `caja.lon_oeste` | decimal | 0 | Caja de descarga: longitud oeste. |
| `caja.lat_norte` | decimal | 0 | Caja de descarga: latitud norte. |
| `caja.lon_este` | decimal | 0 | Caja de descarga: longitud este. |

### `clave_categorias_sinteticas.csv` — Clave de evaluación de la IA

*Evaluación (sintético)* · origen **sintético** · CSV · 200 filas

Categoría verdadera de cada riesgo y si su texto nombra un municipio lejano. Solo existe porque los datos son sintéticos: con ella se mide cuánto acierta la IA y cuántos errores sembrados detecta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `categoria_real` | texto | 0 | Categoría verdadera del riesgo (solo existe porque los datos son sintéticos). |
| `ubicacion_lejana` | booleano | 0 | Verdadero si el texto se redactó nombrando un municipio lejano a su paquete (error sembrado). |
| `actividad_real` | texto | 0 | Actividad verdadera a la que pega el riesgo (solo existe porque los datos son sintéticos). |

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

### `cronograma_paquetes.csv` — Cronograma de los paquetes

*Ejecución (avance. fechas y modelo de riesgo de ejecución)* · origen **sintético** · CSV · 14 filas

Un paquete por fila: fechas de inicio y fin planeadas y proyectadas, avance real y planeado, índice de cumplimiento, meses que faltan, holgura (0 en ruta crítica), costo diario de parada y presupuesto. En Plata y Oro, el avance, las fechas y los meses que faltan se calculan desde las actividades del paquete.

**Cómo se genera:** Sintético. Cada proyecto termina entre 0,4 y 0,6 veces la duración de su paquete más corto desde hoy; cada paquete termina su holgura antes que el proyecto (la ruta crítica, el mismo día). Duración, holgura (10 a 45 días fuera de ruta crítica), costo de parada (USD 15 mil a 90 mil por día) y presupuesto conservan los sorteos de siempre; el avance sale de las actividades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `fecha_inicio_plan` | texto | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | texto | 0 | Fin planeado (línea base). |
| `holgura_dias` | entero | 0 | Días que el paquete puede atrasarse sin atrasar el proyecto (0 en ruta crítica). |
| `costo_dia_parada_usd` | entero | 0 | Costo de un día de paquete parado (equipos, personal, contratistas en espera). |
| `presupuesto_usd` | entero | 0 | Presupuesto del paquete. |
| `fecha_corte` | texto | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |

### `dane_censo2018_deficit_acueducto.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_deficit_habitacional.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*24 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_etnia.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_ipm.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_miseria.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_nbi.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_nbi_dependencia.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_nbi_hacinamiento.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_nbi_inasistencia.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_nbi_servicios.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_nbi_vivienda.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_poblacion.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_censo2018_poblacion_rural_dispersa.csv` — Censo 2018 por municipio (crudo)

*Población y pobreza (real)* · origen **sintético** · CSV · 15 filas

Trece archivos, uno por indicador del Censo Nacional de Población y Vivienda 2018 que el DANE publica por municipio en su geoportal: población total y rural dispersa, población indígena y afro, IPM, NBI y sus cinco componentes, miseria, déficit habitacional y su componente de acueducto. Cada uno con el nombre de campo del servicio.

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `dane_municipios.geojson` — Municipios del DANE (crudos)

*Límites (real)* · origen **DANE** · GeoJSON · 15 filas · geometría: Polígonos

Los 15 polígonos municipales de La Guajira del Marco Geoestadístico Nacional 2024, tal como los publica el geoportal del DANE (~104 mil vértices). Reemplazan la versión 2005 con atributos del censo 2005; los indicadores sociales vienen ahora del censo 2018 (`indicadores_censo2018`).

*10 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

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

### `emergencias_meta.json` — Metadatos de emergencias

*Trazabilidad (real)* · origen **sintético** · JSON · 1 filas

Conjuntos de cada periodo, filas descargadas y periodos sin publicar.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

*12 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `hidrografia_meta.json` — Metadatos de la descarga de hidrografía

*Trazabilidad (real)* · origen **IGAC** · JSON · 1 filas

Servicio de origen, licencia (uso libre solo sin fines comerciales), fecha, caja de descarga y cuántos objetos y vértices llegaron por capa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `servicio` | texto | 0 | Dirección del servicio de origen. |
| `capas.igac_drenaje_sencillo.capa_servicio` | entero | 0 | Número de la capa en el servicio ArcGIS. |
| `capas.igac_drenaje_sencillo.objetos` | entero | 0 | Objetos descargados. |
| `capas.igac_drenaje_doble.capa_servicio` | entero | 0 | Número de la capa en el servicio ArcGIS. |
| `capas.igac_drenaje_doble.objetos` | entero | 0 | Objetos descargados. |
| `capas.igac_cienagas.capa_servicio` | entero | 0 | Número de la capa en el servicio ArcGIS. |
| `capas.igac_cienagas.objetos` | entero | 0 | Objetos descargados. |
| `capas.igac_embalses.capa_servicio` | entero | 0 | Número de la capa en el servicio ArcGIS. |
| `capas.igac_embalses.objetos` | entero | 0 | Objetos descargados. |
| `capas.igac_lagunas.capa_servicio` | entero | 0 | Número de la capa en el servicio ArcGIS. |
| `capas.igac_lagunas.objetos` | entero | 0 | Objetos descargados. |

*16 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `hidrologia.geojson` — Hidrología

*Contexto* · origen **sintético** · GeoJSON · 8 filas · geometría: Líneas

Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en `rios` y `cuerpos_agua`.

**Cómo se genera:** 8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_cuerpo_agua` | texto | 0 | Identificador del cuerpo de agua. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `ideam_estaciones.csv` — Estaciones del IDEAM

*Catálogo (real)* · origen **IDEAM** · CSV · 259 filas

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
| `corriente` | texto | 188 | Corriente asociada. |
| `area_hidrografica` | texto | 0 | Área hidrográfica. |
| `zona_hidrografica` | texto | 0 | Zona hidrográfica. |
| `subzona_hidrografica` | texto | 0 | Subzona hidrográfica. |
| `entidad` | texto | 0 | Entidad propietaria de la estación. |
| `fecha_suspension` | texto | 136 | Fecha de suspensión, si aplica. |

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
| `variables.temperatura.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.temperatura.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.temperatura.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.temp_max.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.temp_max.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.temp_max.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.temp_min.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.temp_min.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.temp_min.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.humedad.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.humedad.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.humedad.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.viento_vel.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.viento_vel.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.viento_vel.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.viento_dir.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.viento_dir.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.viento_dir.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.presion.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.presion.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.presion.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.nivel_rio.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.nivel_rio.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.nivel_rio.lecturas` | entero | 0 | Lecturas descargadas. |
| `variables.nivel_mar.estaciones_sondeadas` | entero | 0 | Estaciones candidatas a las que se les pidió su última lectura. |
| `variables.nivel_mar.estaciones_descargadas` | entero | 0 | Estaciones de las que se bajaron lecturas. |
| `variables.nivel_mar.lecturas` | entero | 0 | Lecturas descargadas. |
| `tablas.ultimas_horas.desde` | texto | 0 | Inicio de la ventana descargada. |
| `tablas.ultimas_horas.hasta` | texto | 0 | Fin de la ventana descargada. |

*45 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

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

*Lecturas (real)* · origen **IDEAM** · Parquet · 70.635 filas

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

*Casi en tiempo real (real)* · origen **IDEAM** · Parquet · 3.221 filas

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

*Lecturas (real)* · origen **IDEAM** · Parquet · 211.342 filas

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

### `ins_irca.csv` — Calidad del agua, IRCA (crudo)

*Servicios (real)* · origen **sintético** · CSV · 257 filas

Índice de Riesgo de la Calidad del Agua para consumo humano (INS, SIVICAP) por municipio y año, total, urbano y rural.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |
| `irca` | decimal | 0 | Índice de Riesgo de la Calidad del Agua (0-100). |

*9 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

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

### `mindefensa_afectacion_fuerza_publica.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 169 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_delitos_ambientales.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 926 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*7 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_extorsion.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 1.904 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_homicidio.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 5.313 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*10 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_invasion_tierras.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 172 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_masacres.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 10 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |
| `casos` | texto | 0 | Registros (casos). |
| `victimas` | texto | 0 | Víctimas (o cantidad que reporta la fuente). |

*4 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_pirateria_terrestre.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 90 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_secuestro.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 247 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_terrorismo.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 238 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_voladura_oleoductos.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 6 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mindefensa_voladura_puentes_vias.parquet` — Delitos (crudos)

*Seguridad (real)* · origen **sintético** · Parquet · 3 filas

Once archivos, uno por delito (homicidio, extorsión, secuestro, terrorismo, masacres, voladuras, piratería terrestre, invasión de tierras, delitos ambientales, afectación de la fuerza pública), con las filas de La Guajira desde 2003.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `municipio` | texto | 0 | Municipio. |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `mininterior_resguardos_poblacion.csv` — Población de los resguardos (crudo)

*Territorio étnico (real)* · origen **sintético** · CSV · 31 filas

Proyección de población 2020 de cada resguardo por municipio (Ministerio del Interior, datos.gov.co).

*5 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

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

**Cómo se genera:** 3 proyectos ficticios (Proyecto 1 al norte, 2 al centro y 3 al sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `fecha_inicio_plan` | fecha | 0 | Inicio planeado (línea base): el de su primera actividad. |
| `fecha_fin_plan` | fecha | 0 | Fin planeado (línea base): el de su última actividad. |

### `registro_riesgos.xlsx` — Registro de riesgos

*Registro* · origen **sintético** · Excel · 212 filas

Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, calificado con la matriz RAM de Ecopetrol (consecuencia 0-5 en Personas, Económica, Ambiental, Clientes e Imagen; probabilidad A-E sin y con controles), estado de materialización y acción de tratamiento. En Plata cada riesgo queda ubicado en la matriz (celda y nivel N, L, M, H o VH, inherente y residual).

**Cómo se genera:** 200 riesgos repartidos en los 14 paquetes. La consecuencia por dimensión sigue el perfil de su categoría (un riesgo social pesa en Imagen; uno de seguridad, en Personas). Tres paquetes 'calientes' reciben más riesgos, con consecuencias y probabilidades más altas, para que el mapa muestre patrones. Los controles bajan la probabilidad 0 a 2 letras. ~18% son oportunidades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_evento_riesgo` | texto | 6 | Identificador del evento de riesgo asociado. |
| `descripcion` | texto | 0 | Descripción textual del riesgo. |
| `causa` | texto | 11 | Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'. |
| `categoria` | texto | 10 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `cons_personas` | entero | 0 | Matriz RAM: consecuencia potencial para las personas, 0 a 5. |
| `cons_economica` | entero | 0 | Matriz RAM: consecuencia económica, 0 a 5 (5 = más de USD 10 M). |
| `cons_ambiental` | entero | 0 | Matriz RAM: consecuencia ambiental, 0 a 5 (5 = contaminación irreparable). |
| `cons_clientes` | decimal | 9 | Matriz RAM: consecuencia para los clientes, 0 a 5. Vacía si el evaluador no la calificó. |
| `cons_imagen` | entero | 0 | Matriz RAM: consecuencia en la imagen, 0 a 5 (5 = internacional). |
| `probabilidad` | texto | 0 | Matriz RAM: probabilidad inherente (sin controles), A a E. En Bronce llega como 'C', 'c', 'C - Ha ocurrido...' o '3'. |
| `probabilidad_residual` | texto | 0 | Matriz RAM: probabilidad con los controles actuales, A a E. |
| `controles` | texto | 0 | Controles que reducen la probabilidad (de inherente a residual). |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `id_paquete_trabajo` | texto | 0 | Paquete de trabajo al que pertenece (llave hacia paquetes). |
| `actividad_afectada` | texto | 18 | Actividad afectada tal como la escribió quien llenó el registro: código, nombre o disciplina con cualquier ortografía, o vacía. |
| `fecha_identificacion` | texto | 0 | Fecha en que se identificó el riesgo. |
| `fecha_materializacion` | texto | 165 | Fecha de materialización; vacía si no se ha materializado. |
| `accion_tratamiento` | texto | 0 | Acción de tratamiento definida. |
| `fecha_ejecucion_accion` | texto | 18 | Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida. |
| `lat` | decimal | 25 | Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `lon` | decimal | 25 | Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

### `resguardos_meta.json` — Metadatos de los resguardos

*Trazabilidad (real)* · origen **sintético** · JSON · 1 filas

Servicio de la ANT, conjunto del Ministerio del Interior, licencias y fecha de descarga.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

*6 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `runap_areas_protegidas.geojson` — Áreas protegidas (crudas)

*Territorio protegido (real)* · origen **sintético** · GeoJSON · 28 filas · geometría: Polígonos

Polígonos del Registro Único Nacional de Áreas Protegidas que cruzan la caja de La Guajira, tal como llegan.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `organizacion` | texto | 0 | Entidad que la administra. |

*24 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `runap_meta.json` — Metadatos del RUNAP

*Trazabilidad (real)* · origen **sintético** · JSON · 1 filas

Servicio de Parques Nacionales, licencia y fecha de descarga.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

*4 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `seguridad_meta.json` — Metadatos de seguridad

*Trazabilidad (real)* · origen **sintético** · JSON · 1 filas

Conjunto de datos.gov.co de cada delito, filas y rango de fechas descargado.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |

*59 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `social_meta.json` — Metadatos de los indicadores sociales

*Trazabilidad (real)* · origen **sintético** · JSON · 1 filas

Servicios y conjuntos de origen (DANE, INS, ART), licencias, fecha de descarga y tablas que llegaron.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `fuentes.censo_2018.tablas.poblacion` | entero | 0 | Población. |
| `fuentes.censo_2018.tablas.poblacion_rural_dispersa` | entero | 0 | Personas en el área rural dispersa. |
| `fuentes.censo_2018.tablas.ipm` | entero | 0 | Índice de Pobreza Multidimensional: % de personas pobres. |
| `fuentes.censo_2018.tablas.nbi` | entero | 0 | % de personas con necesidades básicas insatisfechas. |
| `fuentes.censo_2018.tablas.nbi_vivienda` | entero | 0 | NBI: vivienda inadecuada (%). |
| `fuentes.censo_2018.tablas.nbi_servicios` | entero | 0 | NBI: servicios inadecuados (%). |
| `fuentes.censo_2018.tablas.nbi_hacinamiento` | entero | 0 | NBI: hacinamiento crítico (%). |
| `fuentes.censo_2018.tablas.nbi_inasistencia` | entero | 0 | NBI: niños que no asisten a la escuela (%). |
| `fuentes.censo_2018.tablas.nbi_dependencia` | entero | 0 | NBI: alta dependencia económica (%). |
| `fuentes.censo_2018.tablas.miseria` | entero | 0 | % de personas con dos o más NBI. |
| `fuentes.censo_2018.tablas.deficit_habitacional` | entero | 0 | % de hogares en déficit habitacional. |

*16 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `ungrd_emergencias_2019.parquet` — Emergencias de la UNGRD (crudas)

*Desastres (real)* · origen **sintético** · Parquet · 55 filas

Un archivo por reporte anual (2019, 2020, 2023-2024 y 2025 en adelante), con columnas distintas en cada uno. 2021 y 2022 no están publicados en el portal.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fecha` | texto | 0 | Fecha. |
| `municipio` | texto | 0 | Municipio. |
| `evento` | texto | 0 | Evento como lo escribe la UNGRD. |
| `fallecidos` | texto | 0 | Personas fallecidas. |
| `heridos` | texto | 0 | Personas heridas. |
| `desaparecidos` | texto | 0 | Personas desaparecidas. |
| `personas` | texto | 0 | Personas afectadas. |
| `familias` | texto | 0 | Familias afectadas. |
| `viviendas_destruidas` | texto | 0 | Viviendas destruidas. |
| `viviendas_averiadas` | texto | 0 | Viviendas averiadas. |
| `vias` | texto | 0 | Vías afectadas. |
| `hectareas` | texto | 0 | Hectáreas afectadas. |

*61 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `ungrd_emergencias_2020.parquet` — Emergencias de la UNGRD (crudas)

*Desastres (real)* · origen **sintético** · Parquet · 61 filas

Un archivo por reporte anual (2019, 2020, 2023-2024 y 2025 en adelante), con columnas distintas en cada uno. 2021 y 2022 no están publicados en el portal.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fecha` | texto | 0 | Fecha. |
| `municipio` | texto | 0 | Municipio. |
| `evento` | texto | 0 | Evento como lo escribe la UNGRD. |
| `fallecidos` | texto | 0 | Personas fallecidas. |
| `heridos` | texto | 0 | Personas heridas. |
| `desaparecidos` | texto | 0 | Personas desaparecidas. |
| `personas` | texto | 0 | Personas afectadas. |
| `familias` | texto | 0 | Familias afectadas. |
| `viviendas_destruidas` | texto | 0 | Viviendas destruidas. |
| `viviendas_averiadas` | texto | 0 | Viviendas averiadas. |
| `vias` | texto | 0 | Vías afectadas. |
| `hectareas` | texto | 0 | Hectáreas afectadas. |

*62 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `ungrd_emergencias_2023_2024.parquet` — Emergencias de la UNGRD (crudas)

*Desastres (real)* · origen **sintético** · Parquet · 294 filas

Un archivo por reporte anual (2019, 2020, 2023-2024 y 2025 en adelante), con columnas distintas en cada uno. 2021 y 2022 no están publicados en el portal.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fecha` | texto | 0 | Fecha. |
| `municipio` | texto | 0 | Municipio. |
| `evento` | texto | 0 | Evento como lo escribe la UNGRD. |
| `fallecidos` | texto | 1 | Personas fallecidas. |
| `heridos` | texto | 0 | Personas heridas. |
| `desaparecidos` | texto | 0 | Personas desaparecidas. |
| `personas` | texto | 0 | Personas afectadas. |
| `familias` | texto | 0 | Familias afectadas. |
| `viviendas_destruidas` | texto | 0 | Viviendas destruidas. |
| `viviendas_averiadas` | texto | 0 | Viviendas averiadas. |
| `hectareas` | texto | 0 | Hectáreas afectadas. |

*58 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

### `ungrd_emergencias_2025_en_adelante.parquet` — Emergencias de la UNGRD (crudas)

*Desastres (real)* · origen **sintético** · Parquet · 226 filas

Un archivo por reporte anual (2019, 2020, 2023-2024 y 2025 en adelante), con columnas distintas en cada uno. 2021 y 2022 no están publicados en el portal.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fecha` | texto | 0 | Fecha. |
| `municipio` | texto | 0 | Municipio. |
| `evento` | texto | 0 | Evento como lo escribe la UNGRD. |
| `heridos` | texto | 0 | Personas heridas. |
| `personas` | texto | 0 | Personas afectadas. |
| `familias` | texto | 0 | Familias afectadas. |
| `vias` | texto | 0 | Vías afectadas. |
| `hectareas` | texto | 0 | Hectáreas afectadas. |

*53 columnas más sin descripción (tal como las entrega la fuente en Bronce).*

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

### `actividades.parquet` — Actividades de los paquetes

*Ejecución (fuente única del avance y las fechas)* · origen **sintético** · Parquet · 84 filas

Entre 5 y 7 actividades por paquete (ingeniería, gestión social, licencias, compras, obra civil, montaje, pruebas, cierre), en secuencia. Cada una pesa una fracción de su paquete (suma 1) y, por el peso del paquete en el proyecto, una fracción del proyecto (suma 1). Lleva fechas planeadas, reales y proyectadas: la proyectada es la real si ya ocurrió y, si falta, un pronóstico al ritmo que lleva el paquete.

**Cómo se genera:** Sintético y sucio a propósito: estado escrito de varias formas, algunos avances en porcentaje (0 a 100) y filas repetidas. Plata las limpia: el estado se deriva del avance, los pesos se renormalizan a 1 y las fechas invertidas se corrigen.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_actividad` | texto | 0 | Identificador de la actividad (paquete + número). |
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `orden` | entero | 0 | Posición de la actividad dentro del paquete (van en secuencia). |
| `nombre` | texto | 0 | Nombre de la actividad. |
| `disciplina` | texto | 0 | Disciplina que la ejecuta. |
| `peso_en_paquete` | decimal | 0 | Fracción del paquete que representa la actividad (suma 1 por paquete). |
| `fecha_inicio_plan` | fecha | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | fecha | 0 | Fin planeado (línea base). |
| `avance` | decimal | 0 | Fracción ejecutada (0 a 1); en un paquete o proyecto es la suma de peso × avance de sus actividades. |
| `estado` | texto | 0 | por_iniciar, en_curso o completada (se deriva del avance). |
| `fecha_inicio_real` | fecha | 26 | Inicio real (solo si ya empezó). |
| `fecha_fin_real` | fecha | 40 | Fin real (solo si ya terminó). |
| `fecha_inicio_proyectada` | fecha | 0 | Inicio proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_fin_proyectada` | fecha | 0 | Fin proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_corte` | fecha | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |
| `peso_en_proyecto` | decimal | 0 | Fracción del proyecto que representa: su peso en el paquete por el peso del paquete (presupuesto) en el proyecto. Suma 1 por proyecto. |

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

### `areas_protegidas_runap.geojson` — Áreas protegidas (RUNAP)

*Capa del mapa (real)* · origen **sintético** · GeoJSON · 25 filas · geometría: Polígonos

Áreas que tocan La Guajira o su franja costera: nacionales (Macuira, Los Flamencos, Bahía Portete, Sierra Nevada), regionales de Corpoguajira y reservas de la sociedad civil, con ámbito, área total y área en tierra guajira. Las del modelo ICT siguen siendo las sintéticas (`areas`).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_area` | texto | 0 | Identificador del RUNAP. |
| `nombre` | texto | 0 | Nombre. |
| `categoria` | texto | 0 | Categoría del área protegida. |
| `ambito` | texto | 0 | nacional, regional o privada. |
| `organizacion` | texto | 0 | Entidad que la administra. |
| `area_km2` | decimal | 0 | Área en km² (en La Guajira para los resguardos; total para las áreas protegidas). |
| `area_en_guajira_km2` | decimal | 0 | Área en tierra de La Guajira (km²). |
| `inscrita` | entero | 0 | Año de inscripción. |

### `chirps_municipio_mensual.parquet` — Lluvia mensual por municipio (CHIRPS)

*Lluvia por satélite (real)* · origen **sintético** · Parquet · 6.848 filas

Lluvia de cada mes desde 1991 en cada municipio y en el departamento (código 44): el promedio de las celdas de CHIRPS que lo cubren, ponderado por el área de cada celda que cae adentro (calculada en metros, EPSG:3116). CHIRPS combina satélite con estaciones, entre ellas las del IDEAM.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento entero. |
| `municipio` | texto | 0 | Nombre del municipio. |
| `mes` | fecha | 0 | Primer día del mes. |
| `mm` | decimal | 0 | Lluvia del mes en mm (en Oro, una lista: un valor por mes de `metadata.meses`). |
| `fraccion_con_dato` | decimal | 0 | Parte del área del municipio cubierta por celdas con dato (0 a 1); en la costa, el mar no tiene dato. |

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

### `cronograma.parquet` — Cronograma de los paquetes

*Ejecución (avance. fechas y modelo de riesgo de ejecución)* · origen **sintético** · Parquet · 14 filas

Un paquete por fila: fechas de inicio y fin planeadas y proyectadas, avance real y planeado, índice de cumplimiento, meses que faltan, holgura (0 en ruta crítica), costo diario de parada y presupuesto. En Plata y Oro, el avance, las fechas y los meses que faltan se calculan desde las actividades del paquete.

**Cómo se genera:** Sintético. Cada proyecto termina entre 0,4 y 0,6 veces la duración de su paquete más corto desde hoy; cada paquete termina su holgura antes que el proyecto (la ruta crítica, el mismo día). Duración, holgura (10 a 45 días fuera de ruta crítica), costo de parada (USD 15 mil a 90 mil por día) y presupuesto conservan los sorteos de siempre; el avance sale de las actividades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `holgura_dias` | entero | 0 | Días que el paquete puede atrasarse sin atrasar el proyecto (0 en ruta crítica). |
| `costo_dia_parada_usd` | entero | 0 | Costo de un día de paquete parado (equipos, personal, contratistas en espera). |
| `presupuesto_usd` | entero | 0 | Presupuesto del paquete. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |
| `avance` | decimal | 0 | Fracción ejecutada (0 a 1); en un paquete o proyecto es la suma de peso × avance de sus actividades. |
| `avance_plan` | decimal | 0 | Fracción que el calendario planeado dice que ya debería estar hecha a la fecha de corte. |
| `fecha_inicio_plan` | fecha | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | fecha | 0 | Fin planeado (línea base). |
| `fecha_inicio_proyectada` | fecha | 0 | Inicio proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_fin_proyectada` | fecha | 0 | Fin proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `n_actividades` | entero | 0 | Número de actividades. |
| `n_completadas` | entero | 0 | Actividades completadas. |
| `n_en_curso` | entero | 0 | Actividades en curso. |
| `indice_cumplimiento` | decimal | 0 | Avance real / avance planeado (como el SPI del valor ganado): 1 va al día, menos de 1 va atrasado. |
| `duracion_meses` | decimal | 0 | Duración total del paquete (meses). |
| `meses_restantes` | decimal | 0 | Meses que faltan: el horizonte T. |
| `atraso_proyectado_dias` | entero | 0 | Fin proyectado menos fin planeado (días). |
| `fecha_corte` | fecha | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |

### `emergencias.parquet` — Emergencias atendidas

*Desastres (real)* · origen **sintético** · Parquet · 523 filas

Una fila por emergencia con columnas armonizadas: fecha, municipio, evento, tipo (inundación, incendio forestal, vendaval, sequía...) y afectación. Corrige los códigos de municipio de 2025 y quita la duplicación de ese reporte.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `fecha` | fecha | 0 | Fecha. |
| `anio` | entero | 0 | Año. |
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento. |
| `evento` | texto | 0 | Evento como lo escribe la UNGRD. |
| `tipo` | texto | 0 | Tipo de evento agrupado. |
| `fallecidos` | decimal | 0 | Personas fallecidas. |
| `heridos` | decimal | 0 | Personas heridas. |
| `desaparecidos` | decimal | 0 | Personas desaparecidas. |
| `personas` | decimal | 0 | Personas afectadas. |
| `familias` | decimal | 0 | Familias afectadas. |
| `viviendas_destruidas` | decimal | 0 | Viviendas destruidas. |
| `viviendas_averiadas` | decimal | 0 | Viviendas averiadas. |
| `vias` | decimal | 0 | Vías afectadas. |
| `hectareas` | decimal | 0 | Hectáreas afectadas. |
| `reporte` | texto | 0 | Reporte de origen. |

### `hidro.geojson` — Hidrología

*Contexto* · origen **sintético** · GeoJSON · 8 filas · geometría: Líneas

Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en `rios` y `cuerpos_agua`.

**Cómo se genera:** 8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_cuerpo_agua` | texto | 0 | Identificador del cuerpo de agua. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `ideam_estaciones.geojson` — Estaciones del IDEAM

*Catálogo (real)* · origen **IDEAM** · GeoJSON · 259 filas · geometría: Puntos

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
| `corriente` | texto | 188 | Corriente asociada. |
| `area_hidrografica` | texto | 0 | Área hidrográfica. |
| `zona_hidrografica` | texto | 0 | Zona hidrográfica. |
| `subzona_hidrografica` | texto | 0 | Subzona hidrográfica. |
| `entidad` | texto | 0 | Entidad propietaria de la estación. |
| `fecha_suspension` | texto | 136 | Fecha de suspensión, si aplica. |

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

*Lecturas limpias (real)* · origen **IDEAM** · Parquet · 351 filas

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

*Casi en tiempo real (real)* · origen **IDEAM** · Parquet · 3.063 filas

Flujo del IDEAM con las lecturas de las últimas ~12 horas de todas las variables. Es lo que el mapa muestra como valor de ahora; el backend lo consulta en vivo y guarda este respaldo por si no hay internet.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `var` | texto | 0 | Variable ya clasificada por su sensor: temperatura, temp_max, temp_min, humedad, humedad_suelo, viento_vel, viento_dir, presion, nivel_rio, precipitacion... |
| `fecha_hora` | fecha | 0 | Fecha y hora de la lectura. |
| `valor` | decimal | 0 | Valor medido, ya limpio. |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |

### `ideam_variables_diaria.parquet` — Otras variables por día

*Lecturas limpias (real)* · origen **IDEAM** · Parquet · 2.335 filas

Un valor por estación, variable y día (media, mínimo y máximo). Clasifica cada lectura por su sensor (el conjunto de humedad trae también humedad del suelo), quita duplicados y valores fuera de rango, unifica unidades y promedia la dirección del viento como vector.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigoestacion` | texto | 0 | Código de la estación (llave hacia el catálogo). |
| `var` | texto | 0 | Variable ya clasificada por su sensor: temperatura, temp_max, temp_min, humedad, humedad_suelo, viento_vel, viento_dir, presion, nivel_rio, precipitacion... |
| `dia` | fecha | 0 | Día de la medición. |
| `media` | decimal | 0 | Promedio del día (para la dirección del viento, promedio circular en grados). |
| `minimo` | decimal | 322 | Menor lectura del día. |
| `maximo` | decimal | 322 | Mayor lectura del día. |
| `lecturas` | entero | 0 | Cantidad de lecturas distintas del día. |
| `horas_con_dato` | entero | 0 | Horas del día (0 a 24) que tuvieron al menos una lectura; indica qué tan completo es el día. |
| `unidad` | texto | 0 | Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día). |

### `ideam_variables_horaria.parquet` — Otras variables por hora (limpias)

*Lecturas limpias (real)* · origen **IDEAM** · Parquet · 205.598 filas

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

*Vías (real)* · origen **IGAC** · GeoJSON · 5.322 filas · geometría: Líneas

Las siete capas en una tabla: clase de vía (pavimentada o no, ancho, accesibilidad), recortadas a los municipios del DANE y simplificadas a 20 m (197 mil a 59 mil vértices).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_via` | texto | 0 | Identificador: tipo de vía, número de objeto y parte (un recorte puede dejar varias). |
| `tipo` | entero | 0 | 1 a 7: 1 pavimentada de 2 o más carriles, 2 sin pavimentar de 2 o más, 3 pavimentada angosta, 4 sin pavimentar angosta, 5 sin pavimentar solo en tiempo seco, 6 sin afirmar (trocha), 7 camino o sendero. |
| `clase` | texto | 0 | Nombre de la clase según la combinación de atributos de cada tipo. |
| `superficie` | texto | 1849 | Pavimentada, sin pavimentar, en construcción o sin afirmar. |
| `carriles` | texto | 4999 | 2 o más carriles, o angosta. |
| `accesibilidad` | texto | 1849 | Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia). |
| `nombre` | texto | 5318 | Nombre de la vía; casi ninguna lo tiene (4 de 5.600). |
| `km` | decimal | 0 | Longitud recalculada en metros (EPSG:3116) tras recortar y simplificar. |

### `indicadores_censo2018.parquet` — Indicadores sociales por municipio

*Población y pobreza (real)* · origen **sintético** · Parquet · 16 filas

Una fila por municipio y una del departamento (código 44) con nombres estables: población, % rural disperso, % indígena y afro, IPM, NBI y componentes, miseria, déficit habitacional, hogares sin acueducto y PDET. Reemplaza los atributos del censo 2005 que traía la capa de municipios anterior.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento. |
| `poblacion_2018` | decimal | 0 | Personas censadas en 2018. |
| `poblacion_rural_dispersa` | decimal | 0 | Personas en el área rural dispersa. |
| `indigenas` | decimal | 0 | Personas que se reconocen indígenas. |
| `pct_indigena` | decimal | 0 | % de la población que se reconoce indígena. |
| `afro` | decimal | 0 | Personas negras, mulatas o afrodescendientes. |
| `pct_afro` | decimal | 0 | % afrodescendiente. |
| `ipm` | decimal | 0 | Índice de Pobreza Multidimensional: % de personas pobres. |
| `nbi` | decimal | 0 | % de personas con necesidades básicas insatisfechas. |
| `nbi_vivienda` | decimal | 0 | NBI: vivienda inadecuada (%). |
| `nbi_servicios` | decimal | 0 | NBI: servicios inadecuados (%). |
| `nbi_hacinamiento` | decimal | 0 | NBI: hacinamiento crítico (%). |
| `nbi_inasistencia` | decimal | 0 | NBI: niños que no asisten a la escuela (%). |
| `nbi_dependencia` | decimal | 0 | NBI: alta dependencia económica (%). |
| `miseria` | decimal | 0 | % de personas con dos o más NBI. |
| `deficit_habitacional` | decimal | 0 | % de hogares en déficit habitacional. |
| `hogares_sin_acueducto` | decimal | 0 | % de hogares sin acueducto (componente del déficit habitacional). |
| `pct_rural_disperso` | decimal | 0 | % de la población en el área rural dispersa. |
| `nombre` | texto | 0 | Nombre. |
| `pdet` | booleano | 0 | Municipio PDET. |
| `subregion_pdet` | texto | 13 | Subregión PDET. |

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

### `irca_anual.parquet` — IRCA por municipio y año

*Servicios (real)* · origen **sintético** · Parquet · 257 filas

Índice de riesgo de la calidad del agua 2007-2024, una fila por municipio y año. Solo mide donde hay sistema de suministro: la zona rural wayuu sin acueducto no aparece.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento. |
| `anio` | entero | 0 | Año. |
| `irca` | decimal | 0 | Índice de Riesgo de la Calidad del Agua (0-100). |
| `nivel` | texto | 0 | Nivel de riesgo del IRCA. |
| `irca_urbano` | decimal | 43 | IRCA urbano. |
| `irca_rural` | decimal | 208 | IRCA rural. |

### `municipios.geojson` — Municipios

*Límites (real)* · origen **DANE** · GeoJSON · 15 filas · geometría: Polígonos

Un polígono por municipio con nombre propio, código DANE y área recalculada en metros. La geometría se simplifica sin abrir huecos entre vecinos (104 mil a 15 mil vértices). En Oro suma, por municipio, las estaciones del IDEAM y los kilómetros de vías nacionales.

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

### `proveniencia_chirps.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*31 columnas sin descripción en el catálogo.*

### `proveniencia_emergencias.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*26 columnas sin descripción en el catálogo.*

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

### `proveniencia_resguardos.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*22 columnas sin descripción en el catálogo.*

### `proveniencia_runap.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*18 columnas sin descripción en el catálogo.*

### `proveniencia_seguridad.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*72 columnas sin descripción en el catálogo.*

### `proveniencia_social.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*45 columnas sin descripción en el catálogo.*

### `proveniencia_vias_igac.json` — Proveniencia de cada fuente

*Trazabilidad* · origen **metadatos** · JSON · 1 filas

Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.

*53 columnas sin descripción en el catálogo.*

### `proyectos.geojson` — Proyectos

*Contexto* · origen **sintético** · GeoJSON · 3 filas · geometría: Polígonos

Límites de los proyectos que agrupan los paquetes de trabajo.

**Cómo se genera:** 3 proyectos ficticios (Proyecto 1 al norte, 2 al centro y 3 al sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `fecha_inicio_plan` | fecha | 0 | Inicio planeado (línea base): el de su primera actividad. |
| `fecha_fin_plan` | fecha | 0 | Fin planeado (línea base): el de su última actividad. |

### `red_vial.geojson` — Red vial unificada

*Capa del mapa (real)* · origen **INVIAS + IGAC** · GeoJSON · 5.273 filas · geometría: Líneas

La red nacional de INVIAS (8 tramos, ~300 km, con ruta, administrador y categoría) y la red complementaria del IGAC (~18.300 km), en una sola tabla, sin duplicados: lo que el IGAC repite de la red nacional (~320 km, a menos de 50 m) se quitó. La columna `fuente` (INVIAS o IGAC) y `estilo` distinguen cada red. A los tramos de INVIAS, que no traen superficie, se les pone la del IGAC sobre el mismo trazado. Alimenta la capa de vías del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_tramo` | texto | 0 | Identificador: fuente y número de tramo. |
| `fuente` | texto | 0 | INVIAS (red nacional) o IGAC (red complementaria). |
| `grupo` | texto | 0 | Red nacional o Red complementaria. |
| `estilo` | texto | 0 | Clave de dibujo: n0 a n2 (categorías de INVIAS) e i1 a i7 (clases del IGAC). |
| `clase` | texto | 0 | Clase de vía: categoría de INVIAS o clase interpretada del IGAC. |
| `ruta` | texto | 5265 | Número de la ruta nacional (solo INVIAS). |
| `nombre_ruta` | texto | 5265 | Nombre de la ruta (solo INVIAS). |
| `sector` | texto | 5265 | Sector del tramo (solo INVIAS). |
| `administrador` | texto | 5265 | Quién administra el tramo (solo INVIAS). |
| `calzada` | texto | 5265 | Sencilla o doble (solo INVIAS). |
| `superficie` | texto | 1840 | Pavimentada, sin pavimentar... En INVIAS, tomada del IGAC sobre el mismo trazado. |
| `superficie_fuente` | texto | 1840 | De dónde sale la superficie: INVIAS, IGAC o IGAC (cruce espacial). |
| `carriles` | texto | 4979 | 2 o más carriles, o angosta (solo IGAC). |
| `accesibilidad` | texto | 1847 | Todo el año o solo en tiempo seco (solo IGAC). |
| `nombre` | texto | 5271 | Nombre de la vía, si lo tiene. |
| `km` | decimal | 0 | Longitud del tramo en km, recalculada en metros. |

### `reporte_calidad_bronce_a_plata.csv` — Reporte de calidad

*Control de calidad* · origen **sintético** · CSV · 1 filas

Resumen del paso Bronce a Plata: filas de entrada, duplicados removidos, registros sin coordenadas, filas resultantes y las cifras de la IA sobre el registro final.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `filas_bronce` | entero | 0 | Filas que llegaron en Bronce. |
| `ia_exactitud_validacion_cruzada` | decimal | 0 | Acierto de la IA al clasificar riesgos que no vio (validación cruzada en 5 partes). |
| `ia_riesgos_sin_categoria` | entero | 0 | Riesgos del registro final que llegaron sin categoría. |
| `ia_categorias_asignadas` | entero | 0 | Categorías faltantes que la IA asignó con confianza suficiente. |
| `ia_categorias_pendientes` | entero | 0 | Categorías faltantes que la IA no asignó por confianza baja. |
| `ia_categoria_por_revisar` | entero | 0 | Riesgos cuyo texto contradice la categoría registrada (la IA los marca, no los cambia). |
| `ia_exactitud_sin_categoria` | decimal | 0 | Acierto de las categorías asignadas por la IA, contra la clave sintética. |
| `ia_lugar_mencionado` | entero | 0 | Riesgos cuyo texto nombra un municipio. |
| `ia_ubicacion_por_revisar` | entero | 0 | Riesgos que nombran un municipio lejano a su paquete. |
| `duplicados_removidos` | entero | 0 | Registros repetidos eliminados. |
| `ram_dimensiones_sin_calificar` | entero | 0 | Consecuencias RAM (riesgo por dimensión) que llegaron en blanco. |
| `ram_sin_probabilidad` | entero | 0 | Riesgos sin probabilidad RAM reconocible. |
| `ram_residual_igual_a_inherente` | entero | 0 | Riesgos sin probabilidad residual: se toma la inherente (los controles no la bajan). |
| `ram_residual_mayor_corregido` | entero | 0 | Riesgos con la probabilidad residual mayor que la inherente (se iguala: los controles no la suben). |
| `ram_sin_clasificar` | entero | 0 | Riesgos que quedaron sin nivel RAM. |
| `fechas_dia_mes_ano` | entero | 0 | Fechas que llegaron escritas día/mes/año en vez de año-mes-día (se leen igual). |
| `fechas_materializacion_antes_de_identificacion` | entero | 0 | Materializados con la fecha de materialización antes que la de identificación (se intercambian). |
| `fechas_materializacion_futura_corregida` | entero | 0 | Materializados con fecha en el futuro que cuadran con un año menos (se corrige). |
| `fechas_materializacion_futura_sin_corregir` | entero | 0 | Materializados con fecha en el futuro sin explicación (quedan sin fecha). |
| `fechas_materializado_sin_fecha` | entero | 0 | Materializados sin fecha de materialización. |
| `fechas_abierto_con_materializacion` | entero | 0 | Riesgos abiertos que traen fecha de materialización. |
| `fechas_identificacion_futura` | entero | 0 | Riesgos identificados después de la fecha de corte. |
| `fechas_accion_antes_de_identificacion` | entero | 0 | Riesgos con la acción anterior a su identificación. |
| `riesgos_fechas_por_revisar` | entero | 0 | Riesgos con alguna fecha corregida o por revisar. |
| `riesgos_actividad_por_codigo` | entero | 0 | Riesgos cuya actividad llegó con un código válido de su paquete. |
| `riesgos_actividad_por_nombre` | entero | 0 | Riesgos cuya actividad llegó escrita por su nombre o su disciplina. |
| `riesgos_actividad_inferidas` | entero | 0 | Riesgos sin actividad (o irreconocible): se infirió por su momento y su texto. |
| `riesgos_actividad_codigo_de_otro_paquete` | entero | 0 | Riesgos con el código de una actividad de otro paquete (se infirió la correcta). |
| `riesgos_actividad_no_cuadra_con_el_estado` | entero | 0 | Riesgos cuya actividad registrada no cuadra con su momento: abiertos en una actividad terminada o materializados en una que no había empezado. |
| `riesgos_actividad_corregidas` | entero | 0 | Riesgos con la actividad corregida (código de otro paquete o que no cuadra con el estado). |
| `riesgos_sin_actividad` | entero | 0 | Riesgos que quedaron sin actividad (debe ser 0). |
| `sin_coordenadas_originales` | entero | 0 | Registros sin lat/lon; se ubican por el centroide de su paquete. |
| `riesgos_sin_paquete_valido` | entero | 0 | Registros que no se pudieron ubicar y se descartan. |
| `filas_plata` | entero | 0 | Filas resultantes en Plata. |
| `ia_categorias_mal_sembradas` | entero | 0 | Categorías equivocadas sembradas a propósito en el registro sintético. |
| `ia_categorias_mal_detectadas` | entero | 0 | De las categorías equivocadas sembradas, cuántas detecta la IA. |
| `ia_categorias_falsas_alarmas` | entero | 0 | Categorías correctas que la IA marcó por error. |
| `ia_ubicaciones_sembradas` | entero | 0 | Riesgos sembrados con un municipio lejano en el texto. |
| `ia_ubicaciones_detectadas` | entero | 0 | De las ubicaciones lejanas sembradas, cuántas detecta la IA. |
| `ia_ubicaciones_falsas_alarmas` | entero | 0 | Ubicaciones correctas que la IA marcó por error. |
| `actividad_exactitud_inferidas` | decimal | 0 | Acierto de la actividad inferida o corregida, contra la clave sintética. |
| `actividad_exactitud_a_ciegas` | decimal | 0 | Acierto de la inferencia si ningún riesgo trajera su actividad (se infiere para todos y se compara con la clave). |
| `actividades_bronce` | entero | 0 | Filas de actividades que llegaron del cronograma (con repetidas). |
| `actividades_repetidas_removidas` | entero | 0 | Actividades repetidas que se quitaron. |
| `actividades_sin_paquete_valido` | entero | 0 | Actividades de un paquete que no existe. |
| `actividades_plan_fechas_invertidas` | entero | 0 | Actividades con la fecha de fin planeada antes del inicio (se invierten). |
| `actividades_proyectada_fechas_invertidas` | entero | 0 | Actividades con la fecha de fin proyectada antes del inicio (se invierten). |
| `actividades_avance_en_porcentaje` | entero | 0 | Avances que llegaron de 0 a 100 en vez de 0 a 1. |
| `actividades_avance_sin_dato` | entero | 0 | Actividades sin avance (se toman como no iniciadas). |
| `actividades_estado_con_formato_distinto` | entero | 0 | Estados escritos de otra forma ('Completada', ' EN_CURSO '). |
| `actividades_estado_corregido` | entero | 0 | Estados que no coincidían con el avance (manda el avance). |
| `actividades_paquetes_con_pesos_corregidos` | entero | 0 | Paquetes cuyos pesos de actividad no sumaban 1 (se renormalizan). |
| `actividades_plata` | entero | 0 | Actividades que pasan a Plata. |
| `cronograma_bronce` | entero | 0 | Paquetes en el cronograma de Bronce. |
| `cronograma_holgura_en_ruta_critica_corregida` | entero | 0 | Paquetes de ruta crítica con holgura declarada (se lleva a 0). |
| `cronograma_fechas_corregidas_con_actividades` | entero | 0 | Paquetes cuyas fechas declaradas no coincidían con las de sus actividades (mandan las actividades). |
| `cronograma_sin_actividades` | entero | 0 | Paquetes sin actividades. |
| `cronograma_plata` | entero | 0 | Paquetes con cronograma en Plata. |
| `paquetes_sin_cronograma` | entero | 0 | Paquetes que no aparecen en el cronograma. |

### `reporte_calidad_chirps.csv` — Reporte de calidad de CHIRPS

*Control de calidad (real)* · origen **sintético** · CSV · 1 filas

Meses recibidos y procesados, celdas de la ventana y dentro de los municipios, valores fuera de rango y celdas sin dato.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `meses_bronce` | entero | 0 | Meses en Bronce. |
| `celdas_ventana` | entero | 0 | Celdas de la ventana descargada. |
| `celdas_en_municipios` | entero | 0 | Celdas que tocan algún municipio. |
| `meses_con_otra_rejilla` | entero | 0 | Meses con una rejilla distinta (se descartan). |
| `valores_fuera_de_rango` | entero | 0 | Celdas de tierra con valores negativos o mayores a 2.500 mm (se descartan). |
| `celdas_municipio_sin_dato` | entero | 0 | Celdas de municipio sin dato, sumadas en todos los meses. |
| `meses_plata` | entero | 0 | Meses procesados en Plata. |
| `zonas` | entero | 0 | Municipios más el departamento. |
| `filas_plata` | entero | 0 | Filas de la tabla de Plata. |
| `filas_sin_lluvia` | entero | 0 | Filas sin valor de lluvia. |
| `mm_maximo_mensual` | decimal | 0 | La lluvia mensual más alta encontrada. |
| `desde` | texto | 0 | Primer mes. |
| `hasta` | texto | 0 | Último mes (CHIRPS publica ~3 semanas después de terminar el mes). |

### `reporte_calidad_emergencias.csv` — Reporte de calidad de emergencias

*Control de calidad (real)* · origen **sintético** · CSV · 1 filas

Filas repetidas, códigos corregidos por el nombre, emergencias departamentales y tipos sin clasificar.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `filas_bronce` | entero | 0 | Filas en Bronce. |
| `duplicados_removidos` | entero | 0 | Filas repetidas quitadas. |
| `fecha_invalida` | entero | 0 | Fechas inválidas o futuras. |
| `emergencias_departamentales` | entero | 0 | Emergencias de todo el departamento (código 44). |
| `codigo_corregido_por_nombre` | entero | 0 | Códigos de municipio corregidos por el nombre. |
| `municipio_desconocido` | entero | 0 | Filas de un municipio que no es de La Guajira. |
| `emergencias_plata` | entero | 0 | Emergencias en Plata. |
| `anios` | texto | 0 | Años con emergencias. |
| `personas_afectadas` | entero | 0 | Personas afectadas (suma). |
| `fallecidos` | entero | 0 | Personas fallecidas. |
| `tipo_otro` | entero | 0 | Emergencias sin tipo conocido. |

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

### `reporte_calidad_resguardos.csv` — Reporte de calidad de los resguardos

*Control de calidad (real)* · origen **sintético** · CSV · 1 filas

Resguardos que llegaron, reparados, fuera del departamento, sin código y con población.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `resguardos_bronce` | entero | 0 | Resguardos que llegaron. |
| `vertices_bronce` | entero | 0 | Vértices en Bronce. |
| `sin_geometria` | entero | 0 | Objetos sin geometría. |
| `geometrias_invalidas_reparadas` | entero | 0 | Geometrías inválidas reparadas. |
| `fuera_de_la_guajira` | entero | 0 | Objetos que no tocan La Guajira (salen). |
| `sin_codigo_resguardo` | entero | 0 | Resguardos sin código DANE. |
| `resguardos_con_poblacion` | entero | 0 | Resguardos con población del Ministerio del Interior. |
| `poblacion_sin_poligono` | entero | 0 | Población de resguardos que no tienen polígono (debe ser 0). |
| `resguardos_plata` | entero | 0 | Resguardos en Plata. |
| `vertices_plata` | entero | 0 | Vértices en Plata. |
| `km2_resguardos` | decimal | 0 | km² en resguardos. |
| `km2_departamento` | decimal | 0 | km² del departamento. |
| `pct_departamento_en_resguardo` | decimal | 0 | % del departamento en resguardos. |

### `reporte_calidad_runap.csv` — Reporte de calidad del RUNAP

*Control de calidad (real)* · origen **sintético** · CSV · 1 filas

Áreas que llegaron, reparadas, fuera de La Guajira y por ámbito.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `areas_bronce` | entero | 0 | Áreas que llegaron. |
| `vertices_bronce` | entero | 0 | Vértices en Bronce. |
| `sin_geometria` | entero | 0 | Objetos sin geometría. |
| `geometrias_invalidas_reparadas` | entero | 0 | Geometrías inválidas reparadas. |
| `fuera_de_la_guajira` | entero | 0 | Objetos que no tocan La Guajira (salen). |
| `areas_plata` | entero | 0 | Áreas en Plata. |
| `vertices_plata` | entero | 0 | Vértices en Plata. |
| `nacionales` | entero | 0 | Áreas nacionales. |
| `regionales` | entero | 0 | Áreas regionales. |
| `privadas` | entero | 0 | Reservas de la sociedad civil. |
| `km2_en_guajira` | decimal | 0 | km² protegidos en tierra guajira. |

### `reporte_calidad_seguridad.csv` — Reporte de calidad de seguridad

*Control de calidad (real)* · origen **sintético** · CSV · 1 filas

Registros que llegaron, fechas inválidas, municipios ajenos y rango de meses.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `filas_bronce` | entero | 0 | Filas en Bronce. |
| `fecha_invalida` | entero | 0 | Fechas inválidas o futuras. |
| `municipio_desconocido` | entero | 0 | Filas de un municipio que no es de La Guajira. |
| `cantidad_invalida` | entero | 0 | Cantidades inválidas. |
| `registros_plata` | entero | 0 | Registros que pasan a Plata. |
| `filas_plata` | entero | 0 | Filas de Plata. |
| `delitos` | entero | 0 | Delitos con datos. |
| `victimas_plata` | entero | 0 | Víctimas en Plata. |
| `primer_mes` | texto | 0 | Primer mes. |
| `ultimo_mes` | texto | 0 | Último mes publicado. |

### `reporte_calidad_social.csv` — Reporte de calidad de los indicadores sociales

*Control de calidad (real)* · origen **sintético** · CSV · 1 filas

Tablas que llegaron, códigos desconocidos, porcentajes fuera de rango y control cruzado de la población indígena.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `tablas_censo` | entero | 0 | Indicadores del censo que llegaron. |
| `indicadores_sin_tabla` | entero | 0 | Indicadores que no llegaron. |
| `codigos_desconocidos` | entero | 0 | Filas con un código que no es de los 15 municipios. |
| `porcentajes_fuera_de_rango` | entero | 0 | Porcentajes fuera de 0-100 (descartados). |
| `diferencia_maxima_indigenas_vs_pct` | entero | 0 | Mayor diferencia entre indígenas y % indígena × población (control cruzado). |
| `municipios_pdet` | entero | 0 | Municipios PDET. |
| `municipios_plata` | entero | 0 | Municipios en Plata. |
| `municipios_sin_ipm` | entero | 0 | Municipios sin IPM. |
| `poblacion_2018_departamento` | entero | 0 | Población del departamento (suma). |
| `irca_bronce` | entero | 0 | Filas de IRCA en Bronce. |
| `irca_municipio_desconocido` | entero | 0 | Filas de IRCA sin municipio reconocible. |
| `irca_fuera_de_rango` | entero | 0 | IRCA fuera de 0-100. |
| `irca_plata` | entero | 0 | Filas de IRCA en Plata. |
| `irca_desde` | entero | 0 | Primer año de IRCA. |
| `irca_hasta` | entero | 0 | Último año de IRCA. |

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

### `resguardos.geojson` — Resguardos indígenas

*Capa del mapa (real)* · origen **sintético** · GeoJSON · 39 filas · geometría: Polígonos

Los resguardos que tocan La Guajira, recortados al departamento, con pueblo normalizado, área, población 2020 (parte guajira), municipios que tocan y último acto administrativo. Cubren cerca del 63 % del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_resguardo` | texto | 0 | Identificador de la ANT. |
| `codigo_resguardo` | texto | 8 | Código DANE del resguardo. |
| `nombre` | texto | 0 | Nombre. |
| `pueblo` | texto | 0 | Pueblo indígena. |
| `area_km2` | decimal | 0 | Área en km² (en La Guajira para los resguardos; total para las áreas protegidas). |
| `poblacion_2020` | decimal | 15 | Población proyectada a 2020 (Ministerio del Interior), parte guajira. |
| `municipios` | texto | 0 | Códigos de los municipios que toca. |
| `ultimo_acto` | texto | 0 | Último acto administrativo. |
| `anio_ultimo_acto` | entero | 0 | Año del último acto. |

### `riesgos.geojson` — Registro de riesgos

*Registro* · origen **sintético** · GeoJSON · 200 filas · geometría: Puntos

Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, calificado con la matriz RAM de Ecopetrol (consecuencia 0-5 en Personas, Económica, Ambiental, Clientes e Imagen; probabilidad A-E sin y con controles), estado de materialización y acción de tratamiento. En Plata cada riesgo queda ubicado en la matriz (celda y nivel N, L, M, H o VH, inherente y residual).

**Cómo se genera:** 200 riesgos repartidos en los 14 paquetes. La consecuencia por dimensión sigue el perfil de su categoría (un riesgo social pesa en Imagen; uno de seguridad, en Personas). Tres paquetes 'calientes' reciben más riesgos, con consecuencias y probabilidades más altas, para que el mapa muestre patrones. Los controles bajan la probabilidad 0 a 2 letras. ~18% son oportunidades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_evento_riesgo` | texto | 6 | Identificador del evento de riesgo asociado. |
| `descripcion` | texto | 0 | Descripción textual del riesgo. |
| `causa` | texto | 0 | Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'. |
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `cons_personas` | entero | 0 | Matriz RAM: consecuencia potencial para las personas, 0 a 5. |
| `cons_economica` | entero | 0 | Matriz RAM: consecuencia económica, 0 a 5 (5 = más de USD 10 M). |
| `cons_ambiental` | entero | 0 | Matriz RAM: consecuencia ambiental, 0 a 5 (5 = contaminación irreparable). |
| `cons_clientes` | decimal | 8 | Matriz RAM: consecuencia para los clientes, 0 a 5. Vacía si el evaluador no la calificó. |
| `cons_imagen` | entero | 0 | Matriz RAM: consecuencia en la imagen, 0 a 5 (5 = internacional). |
| `probabilidad` | texto | 0 | Matriz RAM: probabilidad inherente (sin controles), A a E. En Bronce llega como 'C', 'c', 'C - Ha ocurrido...' o '3'. |
| `probabilidad_residual` | texto | 0 | Matriz RAM: probabilidad con los controles actuales, A a E. |
| `controles` | texto | 0 | Controles que reducen la probabilidad (de inherente a residual). |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `id_paquete_trabajo` | texto | 0 | Paquete de trabajo al que pertenece (llave hacia paquetes). |
| `actividad_registrada` | texto | 17 | Actividad afectada tal como llegó en el registro (sin corregir), para trazabilidad. |
| `fecha_identificacion` | fecha | 0 | Fecha en que se identificó el riesgo. |
| `fecha_materializacion` | fecha | 154 | Fecha de materialización; vacía si no se ha materializado. |
| `accion_tratamiento` | texto | 0 | Acción de tratamiento definida. |
| `fecha_ejecucion_accion` | fecha | 16 | Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida. |
| `lat` | decimal | 0 | Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `lon` | decimal | 0 | Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `categoria_registrada` | texto | 0 | Categoría tal como llegó en el registro (sin_clasificar si faltaba o era ilegible). |
| `categoria_ia` | texto | 0 | Categoría que sugiere la IA leyendo la descripción y la causa. |
| `confianza_ia` | decimal | 0 | Probabilidad que la IA le da a su categoría (0 a 1). |
| `palabras_ia` | texto | 0 | Palabras del texto que más pesaron en la decisión de la IA (explicación). |
| `categoria_origen` | texto | 0 | De dónde sale la categoría final: registro, ia (la asignó el clasificador de texto) o pendiente. |
| `revisar_categoria` | booleano | 0 | Verdadero si el texto contradice la categoría registrada con alta confianza. |
| `municipio_mencionado` | texto | 132 | Municipios que nombra el texto (diccionario geográfico del DANE). |
| `revisar_ubicacion` | booleano | 0 | Verdadero si el texto nombra un municipio a más de 15 km del paquete del riesgo. |
| `ram_inherente` | texto | 0 | Celda RAM sin controles: consecuencia de la peor dimensión + probabilidad (p. ej. 5D). |
| `nivel_inherente` | texto | 0 | Nivel RAM sin controles: N, L, M, H o VH. |
| `ram_residual` | texto | 0 | Celda RAM con controles (p. ej. 5B). |
| `nivel_residual` | texto | 0 | Nivel RAM con controles: N, L, M, H o VH. Es el que usa el ICT. |
| `dimension_dominante` | texto | 0 | Dimensión que manda en la calificación residual: PE, EC, MA, CL o IM. |
| `puntaje_ram` | entero | 0 | Puntaje del nivel residual: N=1, L=2, M=3, H=4, VH=5. |
| `problema_fechas` | texto | 195 | Qué pasó con las fechas del riesgo (cruzadas, un año de más, sin fecha de materialización...). |
| `revisar_fechas` | booleano | 0 | Verdadero si alguna fecha del riesgo se corrigió o no cuadra: alguien debería revisarla. |
| `id_actividad` | texto | 0 | Actividad del cronograma a la que pega el riesgo (o de la que es parte la fila). |
| `actividad` | texto | 0 | Nombre de la actividad del cronograma a la que pega el riesgo. |
| `actividad_origen` | texto | 0 | De dónde sale la actividad: registro (código válido), nombre (se reconoció el nombre o la disciplina), inferida (venía vacía) o corregida (código de otro paquete, o una actividad que no cuadra con el momento del riesgo). |
| `revisar_actividad` | booleano | 0 | Verdadero si la actividad registrada se tuvo que corregir: alguien debería revisarla. |
| `geolocalizacion_inferida` | booleano | 0 | Verdadero si la ubicación se tomó del centroide del paquete porque el registro no traía coordenadas. |
| `severidad` | entero | 0 | Puntaje del nivel RAM residual (1 a 5); pondera el mapa de calor. |

### `seguridad_municipio_mensual.parquet` — Delitos por municipio y mes

*Seguridad (real)* · origen **sintético** · Parquet · 3.924 filas

Casos y víctimas por municipio, mes y delito desde 2003. Los meses sin fila son cero.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento. |
| `mes` | fecha | 0 | Primer día del mes. |
| `delito` | texto | 0 | Delito. |
| `casos` | entero | 0 | Registros (casos). |
| `victimas` | entero | 0 | Víctimas (o cantidad que reporta la fuente). |

### `vias.geojson` — Vías

*Contexto* · origen **sintético** · GeoJSON · 10 filas · geometría: Líneas

Red vial por tipo (primaria, secundaria, terciaria de difícil acceso). Es la inventada; la red real (INVIAS e IGAC) está en `red_vial` y aún no alimenta el ICT.

**Cómo se genera:** 10 segmentos rectos con tipo aleatorio, enteros dentro de tierra firme.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_via` | texto | 0 | Identificador de la vía. |
| `tipo` | texto | 0 | primaria, secundaria o terciaria de difícil acceso. |

## Oro

### `alertas.json` — Alertas tempranas

*Resultado del modelo* · origen **sintético** · JSON · 5 filas

Una alerta por paquete en escalamiento o con el ICT al alza: prioridad, causas, puntos de crisis, qué exige la RAM, quién decide y qué hacer con las comunidades y áreas protegidas que alcanza.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `nombre_paquete` | texto | 0 | Nombre del paquete. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `ict` | decimal | 0 | ICT del paquete en alerta. |
| `nivel` | texto | 0 | bajo, medio, alto o crítico según los umbrales. |
| `motivos` | lista | 0 | Lista de reglas que dispararon la alerta. |
| `puntos_crisis` | entero | 0 | Puntos de crisis del paquete en el mapa. |
| `municipio` | texto | 0 | Municipio (DANE) donde cae: las coordenadas del riesgo o el centro del paquete. |
| `generada_en` | texto | 0 | Fecha del corte que generó la alerta. |

*4 columnas sin descripción en el catálogo.*

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

### `areas_protegidas_runap.geojson` — Áreas protegidas (RUNAP)

*Capa del mapa (real)* · origen **sintético** · GeoJSON · 25 filas · geometría: Polígonos

Áreas que tocan La Guajira o su franja costera: nacionales (Macuira, Los Flamencos, Bahía Portete, Sierra Nevada), regionales de Corpoguajira y reservas de la sociedad civil, con ámbito, área total y área en tierra guajira. Las del modelo ICT siguen siendo las sintéticas (`areas`).

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_area` | texto | 0 | Identificador del RUNAP. |
| `nombre` | texto | 0 | Nombre. |
| `categoria` | texto | 0 | Categoría del área protegida. |
| `ambito` | texto | 0 | nacional, regional o privada. |
| `organizacion` | texto | 0 | Entidad que la administra. |
| `area_km2` | decimal | 0 | Área en km² (en La Guajira para los resguardos; total para las áreas protegidas). |
| `area_en_guajira_km2` | decimal | 0 | Área en tierra de La Guajira (km²). |
| `inscrita` | entero | 0 | Año de inscripción. |

### `clima_estaciones.geojson` — Estaciones con clima

*Capa del mapa (real)* · origen **IDEAM** · GeoJSON · 16 filas · geometría: Puntos

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
| `radiacion` | texto | 13 | Radiación media mensual de la estación, si tiene sensor calibrado. |

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

### `cobertura_estaciones.geojson` — Cobertura de las estaciones

*Capa del mapa (calculado)* · origen **IDEAM** · GeoJSON · 160 filas · geometría: Polígonos

Cada estación del IDEAM extendida a un área, para cada variable: el área más cercana (cada punto del departamento con su estación más cercana, polígonos de Voronoi recortados al departamento) y el radio de influencia (un círculo alrededor de la estación, recortado a tierra). Los radios son supuestos de trabajo editables en `parametros.yaml`, no cifras oficiales del IDEAM. Alimenta la capa "Cobertura de estaciones" del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código de la estación del IDEAM (10 dígitos). |
| `nombre` | texto | 0 | Nombre de la estación. |
| `variable` | texto | 0 | Variable del mapa: lluvia, temperatura, humedad, humedad_suelo, viento o presion. |
| `modo` | texto | 0 | cercana (área más cercana, Voronoi) o radio (radio de influencia). |
| `radio_km` | decimal | 80 | Radio de influencia en km (solo en modo radio); supuesto de trabajo de parametros.yaml. |
| `area_km2` | decimal | 0 | Área del polígono, ya recortado al departamento. |

### `cobertura_paquetes.csv` — Estación que representa a cada paquete

*Cruce espacial (calculado)* · origen **IDEAM** · CSV · 84 filas

Para cada paquete de trabajo y variable: la estación más cercana (desde el centro del paquete), a cuántos km, cuántas estaciones hay dentro del radio y si el paquete queda cubierto, parcial o sin cobertura. Se muestra en la ficha del paquete.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Paquete de trabajo. |
| `variable` | texto | 0 | Variable del mapa: lluvia, temperatura, humedad, humedad_suelo, viento o presion. |
| `codigo` | entero | 0 | Código de la estación del IDEAM (10 dígitos). |
| `estacion` | texto | 0 | Nombre de la estación más cercana al centro del paquete. |
| `distancia_km` | decimal | 0 | Distancia del centro del paquete a esa estación. |
| `radio_km` | decimal | 0 | Radio de influencia en km (solo en modo radio); supuesto de trabajo de parametros.yaml. |
| `estado` | texto | 0 | cubierto (dentro del radio), parcial (hasta el doble) o sin_cobertura. |
| `estaciones_en_el_radio` | entero | 0 | Cuántas estaciones de esa variable hay dentro del radio del paquete. |

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

### `contexto_paquetes.csv` — Contexto real de cada paquete

*Cruce espacial (calculado)* · origen **sintético** · CSV · 14 filas

Cada paquete de trabajo (sintético) cruzado con las fuentes reales: municipio, pobreza, % dentro de resguardos y áreas protegidas y el más cercano, delitos de 12 meses, emergencias e IRCA. No cambia el ICT; se muestra en la ficha del paquete.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Paquete de trabajo. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `codigo_municipio` | entero | 0 | Municipio donde cae el centro del paquete. |
| `municipio` | texto | 0 | Municipio. |
| `ipm` | decimal | 0 | Índice de Pobreza Multidimensional: % de personas pobres. |
| `nbi` | decimal | 0 | % de personas con necesidades básicas insatisfechas. |
| `miseria` | decimal | 0 | % de personas con dos o más NBI. |
| `pct_indigena` | decimal | 0 | % de la población que se reconoce indígena. |
| `hogares_sin_acueducto` | decimal | 0 | % de hogares sin acueducto (componente del déficit habitacional). |
| `pdet` | booleano | 0 | Municipio PDET. |
| `irca_ultimo` | decimal | 0 | IRCA del último año. |
| `irca_anio` | entero | 0 | Año del IRCA. |
| `pct_en_resguardo` | decimal | 0 | % del paquete dentro de resguardos. |
| `resguardo_cercano` | texto | 0 | Resguardo más cercano (o el que cruza). |
| `resguardo_pueblo` | texto | 0 | Pueblo del resguardo más cercano. |
| `distancia_resguardo_km` | decimal | 0 | Distancia al resguardo más cercano (0 si se cruzan). |
| `pct_en_area_protegida` | decimal | 0 | % del paquete dentro de áreas protegidas. |
| `area_protegida_cercano` | texto | 0 | Área protegida más cercana. |
| `area_protegida_categoria` | texto | 0 | Categoría del área protegida más cercana. |
| `distancia_area_protegida_km` | decimal | 0 | Distancia al área protegida más cercana (0 si se cruzan). |
| `homicidio_12m_municipio` | entero | 0 | Víctimas de homicidio en el municipio, últimos 12 meses. |
| `tasa_homicidio_12m` | decimal | 0 | Por 100.000 habitantes (censo 2018). |
| `extorsion_12m_municipio` | entero | 0 | Denuncias de extorsión en el municipio, últimos 12 meses. |
| `tasa_extorsion_12m` | decimal | 0 | Por 100.000 habitantes. |
| `emergencias_municipio` | entero | 0 | Emergencias del municipio en los años publicados. |
| `emergencias_tipo_principal` | texto | 0 | Tipo de emergencia más frecuente. |
| `ram_prob_seguridad` | texto | 0 | Probabilidad RAM que sugieren los delitos contra personas e infraestructura en el municipio (sin homicidio). |
| `ram_prob_desastres` | texto | 0 | Probabilidad RAM que sugieren las emergencias de la UNGRD en el municipio. |
| `ram_cons_imagen` | entero | 0 | Consecuencia mínima sugerida en Imagen (resguardo, PDET). |
| `ram_cons_ambiental` | entero | 0 | Consecuencia mínima sugerida en Ambiental (área protegida). |
| `ram_por_revisar` | entero | 0 | Amenazas abiertas calificadas por debajo de lo que sugiere el territorio. |
| `ram_por_revisar_ids` | texto | 2 | Cuáles son. |

### `cronograma_actividades.csv` — Actividades de los paquetes

*Ejecución (fuente única del avance y las fechas)* · origen **sintético** · CSV · 84 filas

Entre 5 y 7 actividades por paquete (ingeniería, gestión social, licencias, compras, obra civil, montaje, pruebas, cierre), en secuencia. Cada una pesa una fracción de su paquete (suma 1) y, por el peso del paquete en el proyecto, una fracción del proyecto (suma 1). Lleva fechas planeadas, reales y proyectadas: la proyectada es la real si ya ocurrió y, si falta, un pronóstico al ritmo que lleva el paquete.

**Cómo se genera:** Sintético y sucio a propósito: estado escrito de varias formas, algunos avances en porcentaje (0 a 100) y filas repetidas. Plata las limpia: el estado se deriva del avance, los pesos se renormalizan a 1 y las fechas invertidas se corrigen.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_actividad` | texto | 0 | Identificador de la actividad (paquete + número). |
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `nombre_paquete` | texto | 0 | Nombre del paquete. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre_proyecto` | texto | 0 | Nombre del proyecto. |
| `orden` | entero | 0 | Posición de la actividad dentro del paquete (van en secuencia). |
| `nombre` | texto | 0 | Nombre de la actividad. |
| `disciplina` | texto | 0 | Disciplina que la ejecuta. |
| `estado` | texto | 0 | por_iniciar, en_curso o completada (se deriva del avance). |
| `avance` | decimal | 0 | Fracción ejecutada (0 a 1); en un paquete o proyecto es la suma de peso × avance de sus actividades. |
| `peso_en_paquete` | decimal | 0 | Fracción del paquete que representa la actividad (suma 1 por paquete). |
| `peso_en_proyecto` | decimal | 0 | Fracción del proyecto que representa: su peso en el paquete por el peso del paquete (presupuesto) en el proyecto. Suma 1 por proyecto. |
| `aporte_avance_pp` | decimal | 0 | Puntos de avance (de 100) que la actividad ya aporta al proyecto. |
| `aporte_total_pp` | decimal | 0 | Puntos que aportará al proyecto al terminar. |
| `por_ejecutar` | booleano | 0 | Verdadero si la actividad aún no está completada. |
| `fecha_inicio_plan` | texto | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | texto | 0 | Fin planeado (línea base). |
| `fecha_inicio_real` | texto | 26 | Inicio real (solo si ya empezó). |
| `fecha_fin_real` | texto | 40 | Fin real (solo si ya terminó). |
| `fecha_inicio_proyectada` | texto | 0 | Inicio proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_fin_proyectada` | texto | 0 | Fin proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `atraso_proyectado_dias` | entero | 0 | Fin proyectado menos fin planeado (días). |
| `riesgos` | entero | 0 | Riesgos del registro que pegan en la actividad. |
| `amenazas_abiertas` | entero | 0 | Amenazas abiertas (latentes o próximas a materializarse) que pegan en la actividad. |
| `amenazas_altas` | entero | 0 | De esas, las de nivel RAM residual alto o muy alto. |
| `riesgos_materializados` | entero | 0 | Riesgos que ya se materializaron en la actividad. |
| `fecha_corte` | texto | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |

### `cronograma_paquetes.csv` — Cronograma de los paquetes

*Ejecución (avance. fechas y modelo de riesgo de ejecución)* · origen **sintético** · CSV · 14 filas

Un paquete por fila: fechas de inicio y fin planeadas y proyectadas, avance real y planeado, índice de cumplimiento, meses que faltan, holgura (0 en ruta crítica), costo diario de parada y presupuesto. En Plata y Oro, el avance, las fechas y los meses que faltan se calculan desde las actividades del paquete.

**Cómo se genera:** Sintético. Cada proyecto termina entre 0,4 y 0,6 veces la duración de su paquete más corto desde hoy; cada paquete termina su holgura antes que el proyecto (la ruta crítica, el mismo día). Duración, holgura (10 a 45 días fuera de ruta crítica), costo de parada (USD 15 mil a 90 mil por día) y presupuesto conservan los sorteos de siempre; el avance sale de las actividades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `nombre` | texto | 0 | Nombre de la actividad. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |
| `presupuesto_usd` | entero | 0 | Presupuesto del paquete. |
| `peso_en_proyecto` | decimal | 0 | Fracción del proyecto que representa: su peso en el paquete por el peso del paquete (presupuesto) en el proyecto. Suma 1 por proyecto. |
| `holgura_dias` | entero | 0 | Días que el paquete puede atrasarse sin atrasar el proyecto (0 en ruta crítica). |
| `avance` | decimal | 0 | Fracción ejecutada (0 a 1); en un paquete o proyecto es la suma de peso × avance de sus actividades. |
| `avance_plan` | decimal | 0 | Fracción que el calendario planeado dice que ya debería estar hecha a la fecha de corte. |
| `indice_cumplimiento` | decimal | 0 | Avance real / avance planeado (como el SPI del valor ganado): 1 va al día, menos de 1 va atrasado. |
| `fecha_inicio_plan` | texto | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | texto | 0 | Fin planeado (línea base). |
| `fecha_inicio_proyectada` | texto | 0 | Inicio proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_fin_proyectada` | texto | 0 | Fin proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `atraso_proyectado_dias` | entero | 0 | Fin proyectado menos fin planeado (días). |
| `atraso_sobre_holgura_dias` | entero | 0 | Días de atraso proyectado que pasan la holgura del paquete: lo que ya atrasa al proyecto. |
| `duracion_meses` | decimal | 0 | Duración total del paquete (meses). |
| `meses_restantes` | decimal | 0 | Meses que faltan: el horizonte T. |
| `n_actividades` | entero | 0 | Número de actividades. |
| `n_completadas` | entero | 0 | Actividades completadas. |
| `n_en_curso` | entero | 0 | Actividades en curso. |
| `actividad_en_curso` | texto | 0 | Actividad que se está ejecutando. |
| `siguiente_actividad` | texto | 0 | Primera actividad por iniciar. |
| `fecha_corte` | texto | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |

### `cronograma_proyectos.csv` — Cronograma de los proyectos

*Ejecución (avance y fechas del proyecto)* · origen **sintético** · CSV · 3 filas

Un proyecto por fila: avance ponderado de todas sus actividades (cada una pesa lo de su paquete por el peso del paquete en el presupuesto), avance planeado a la fecha de corte, índice de cumplimiento, fechas planeadas y proyectadas, atraso proyectado y el paquete que define el fin.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre de la actividad. |
| `avance` | decimal | 0 | Fracción ejecutada (0 a 1); en un paquete o proyecto es la suma de peso × avance de sus actividades. |
| `avance_plan` | decimal | 0 | Fracción que el calendario planeado dice que ya debería estar hecha a la fecha de corte. |
| `fecha_inicio_plan` | texto | 0 | Inicio planeado (línea base). |
| `fecha_fin_plan` | texto | 0 | Fin planeado (línea base). |
| `fecha_inicio_proyectada` | texto | 0 | Inicio proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `fecha_fin_proyectada` | texto | 0 | Fin proyectado: el real si ya ocurrió; si no, pronóstico al ritmo actual. |
| `n_paquetes` | entero | 0 | Número de paquetes. |
| `n_actividades` | entero | 0 | Número de actividades. |
| `n_completadas` | entero | 0 | Actividades completadas. |
| `presupuesto_usd` | entero | 0 | Presupuesto del paquete. |
| `paquete_que_define_el_fin` | texto | 0 | Paquete que termina último según las fechas proyectadas. |
| `paquetes_sobre_su_holgura` | entero | 0 | Paquetes del proyecto cuyo atraso proyectado ya pasa su holgura. |
| `indice_cumplimiento` | decimal | 0 | Avance real / avance planeado (como el SPI del valor ganado): 1 va al día, menos de 1 va atrasado. |
| `duracion_meses` | decimal | 0 | Duración total del paquete (meses). |
| `meses_restantes` | decimal | 0 | Meses que faltan: el horizonte T. |
| `atraso_proyectado_dias` | entero | 0 | Fin proyectado menos fin planeado (días). |
| `fecha_corte` | texto | 0 | Fecha a la que están medidos el avance y las fechas proyectadas (día en que se generó el dato). |

### `cuerpos_agua.geojson` — Cuerpos de agua para el mapa

*Capa del mapa (real)* · origen **IGAC** · GeoJSON · 218 filas · geometría: Polígonos

Ríos anchos, ciénagas, lagunas y embalses como polígonos con su área en km².

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_objeto` | texto | 0 | Identificador: tipo de objeto y número de objeto en el servicio del IGAC. |
| `tipo` | texto | 0 | drenaje_sencillo, drenaje_doble, cienaga, laguna o embalse. |
| `nombre` | texto | 118 | Nombre del río, arroyo o cuerpo de agua, normalizado (vacío si no tiene). |
| `area_km2` | decimal | 0 | Área del polígono en km², calculada en metros (EPSG:3116). |

### `ejecucion_paquetes.csv` — Riesgo de ejecución por paquete

*Resultado del modelo* · origen **sintético** · CSV · 14 filas

Atraso esperado, P50/P80/P90 de atraso y sobrecosto, lo ya consumido, el IRE (probabilidad de pasar la holgura más la tolerancia), el riesgo principal, los días que evitan los controles y las covariables del territorio (z) con sus valores.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `atraso_media` | decimal | 0 | Atraso esperado en días (consumido + por venir). |
| `atraso_p50` | decimal | 0 | Mediana del atraso. |
| `atraso_p80` | decimal | 0 | Atraso que no se supera en el 80 % de los escenarios. |
| `atraso_p90` | decimal | 0 | Atraso que no se supera en el 90 % de los escenarios. |
| `atraso_consumido` | decimal | 0 | Atraso de las amenazas ya materializadas. |
| `costo_media` | decimal | 0 | Sobrecosto esperado (USD). |
| `costo_p50` | decimal | 0 | Mediana del sobrecosto. |
| `costo_p80` | decimal | 0 | Sobrecosto P80. |
| `costo_p90` | decimal | 0 | Sobrecosto P90 (reserva de contingencia). |
| `costo_consumido` | decimal | 0 | Sobrecosto de lo ya materializado. |
| `holgura_dias` | decimal | 0 | Días que el paquete puede atrasarse sin atrasar el proyecto (0 en ruta crítica). |
| `prob_atraso_al_proyecto` | decimal | 0 | Probabilidad de que el paquete pase su holgura y atrase el proyecto. |
| `ire` | decimal | 0 | Índice de riesgo de ejecución: 100 × P(atraso > holgura + tolerancia). |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |
| `meses_restantes` | decimal | 0 | Meses que faltan: el horizonte T. |
| `costo_dia_parada_usd` | entero | 0 | Costo de un día de paquete parado (equipos, personal, contratistas en espera). |
| `presupuesto_usd` | entero | 0 | Presupuesto del paquete. |
| `municipio` | texto | 0 | Municipio (DANE) donde cae: las coordenadas del riesgo o el centro del paquete. |
| `amenazas_abiertas` | entero | 0 | Amenazas latentes o próximas a materializarse. |
| `atraso_evitado_por_controles` | decimal | 0 | Días de atraso esperado que evitan los controles (inherente − residual). |
| `riesgo_principal` | texto | 0 | Amenaza que más atraso esperado aporta. |
| `categoria_principal` | texto | 0 | Su categoría. |
| `z_tasa_delitos_rel` | decimal | 0 | Covariable: delitos contra proyectos frente al departamento (ln). |
| `z_emergencias_rel` | decimal | 0 | Covariable: emergencias frente al promedio (ln). |
| `z_anomalia_lluvia` | decimal | 0 | Covariable: lluvia fuera de lo normal frente al departamento. |
| `z_en_resguardo` | decimal | 0 | Covariable: fracción en resguardo frente al departamento. |
| `z_ipm_rel` | decimal | 0 | Covariable: IPM relativo al departamento. |
| `z_pdet` | decimal | 0 | Covariable: municipio PDET (centrada). |
| `z_vias_tiempo_seco` | decimal | 0 | Covariable: vías solo en tiempo seco cerca (relativa). |
| `tasa_delitos_100k` | decimal | 0 | Delitos contra proyectos en 12 meses por 100.000 hab. |
| `emergencias_por_ano` | decimal | 0 | Emergencias UNGRD por año en el municipio. |
| `anomalia_lluvia_pct` | decimal | 0 | Desviación media de la lluvia frente a lo normal (últimos meses). |
| `vias_tiempo_seco_pct` | decimal | 0 | % de km cercanos solo en tiempo seco. |

*4 columnas sin descripción en el catálogo.*

### `ejecucion_proyectos.csv` — Riesgo de ejecución por proyecto

*Resultado del modelo* · origen **sintético** · CSV · 3 filas

Atraso del proyecto (lo que los paquetes no absorben con su holgura), sobrecosto, IRE y probabilidad de terminar sin atraso.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `atraso_media` | decimal | 0 | Atraso esperado en días (consumido + por venir). |
| `atraso_p50` | decimal | 0 | Mediana del atraso. |
| `atraso_p80` | decimal | 0 | Atraso que no se supera en el 80 % de los escenarios. |
| `atraso_p90` | decimal | 0 | Atraso que no se supera en el 90 % de los escenarios. |
| `costo_media` | decimal | 0 | Sobrecosto esperado (USD). |
| `costo_p50` | decimal | 0 | Mediana del sobrecosto. |
| `costo_p80` | decimal | 0 | Sobrecosto P80. |
| `costo_p90` | decimal | 0 | Sobrecosto P90 (reserva de contingencia). |
| `ire` | decimal | 0 | Índice de riesgo de ejecución: 100 × P(atraso > holgura + tolerancia). |
| `prob_sin_atraso` | decimal | 0 | Probabilidad de que el proyecto no se atrase. |

### `ejecucion_resumen.json` — Resumen de la simulación

*Resultado del modelo* · origen **sintético** · JSON · 1 filas

Supuestos usados, fuentes de las covariables, resumen del portafolio e histogramas de atraso y sobrecosto por proyecto.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `portafolio.atraso_media` | decimal | 0 | Atraso esperado en días (consumido + por venir). |
| `portafolio.atraso_p50` | decimal | 0 | Mediana del atraso. |
| `portafolio.atraso_p80` | decimal | 0 | Atraso que no se supera en el 80 % de los escenarios. |
| `portafolio.atraso_p90` | decimal | 0 | Atraso que no se supera en el 90 % de los escenarios. |
| `portafolio.costo_media` | decimal | 0 | Sobrecosto esperado (USD). |
| `portafolio.costo_p50` | decimal | 0 | Mediana del sobrecosto. |
| `portafolio.costo_p80` | decimal | 0 | Sobrecosto P80. |
| `portafolio.costo_p90` | decimal | 0 | Sobrecosto P90 (reserva de contingencia). |

*65 columnas sin descripción en el catálogo.*

### `ejecucion_riesgos.csv` — Riesgo de ejecución por amenaza

*Resultado del modelo* · origen **sintético** · CSV · 168 filas

Cada amenaza con su frecuencia (letra RAM → eventos por año), el multiplicador del territorio, la probabilidad en lo que falta, los días y el costo por evento, el atraso y costo esperados y su aporte al paquete.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `id_actividad` | texto | 0 | Actividad del cronograma a la que pega el riesgo (o de la que es parte la fila). |
| `actividad` | texto | 0 | Nombre de la actividad del cronograma a la que pega el riesgo. |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `nivel_residual` | texto | 0 | Nivel RAM con controles: N, L, M, H o VH. Es el que usa el ICT. |
| `ram_residual` | texto | 0 | Celda RAM con controles (p. ej. 5B). |
| `letra` | texto | 0 | Letra RAM usada (residual o, en el escenario sin controles, la inherente). |
| `lambda0` | decimal | 0 | Eventos por año de esa letra en un paquete. |
| `multiplicador_territorial` | decimal | 0 | Cuánto multiplica el territorio la frecuencia (1 = promedio de La Guajira). |
| `lambda` | decimal | 0 | Frecuencia final (eventos por año). |
| `horizonte_anios` | decimal | 0 | Años de exposición: lo que le falta por ejecutarse a la actividad a la que pega la amenaza (o a su paquete, si no se sabe). |
| `horizonte_origen` | texto | 0 | De dónde sale el horizonte: actividad (lo que le falta a su actividad) o paquete. |
| `probabilidad` | decimal | 0 | Probabilidad de que ocurra en lo que falta (1 si ya ocurrió). |
| `dias_por_evento` | decimal | 0 | Días de atraso más probables por evento (la peor dimensión). |
| `costo_directo_medio` | decimal | 0 | Costo directo medio por evento (banda USD económica). |
| `costo_dia` | decimal | 0 | Costo diario de parada del paquete. |
| `atraso_esperado` | decimal | 0 | λ · T · días medios. |
| `costo_esperado` | decimal | 0 | λ · T · costo medio por evento. |
| `atraso_evitado_por_controles` | decimal | 0 | Días de atraso esperado que evitan los controles (inherente − residual). |
| `consumido_dias` | decimal | 0 | Días ya consumidos (materializado). |
| `consumido_usd` | decimal | 0 | USD ya consumidos. |
| `grupo_choque` | texto | 78 | Grupo con el que comparte el choque común. |
| `tipo_choque` | texto | 78 | clima o social. |
| `contribucion_pct` | decimal | 0 | Parte del atraso esperado de su paquete. |

### `grid_calor.geojson` — Superficie de calor

*Resultado del modelo* · origen **sintético** · GeoJSON · 686 filas · geometría: Puntos

Grilla de ~2 km con la densidad kernel de las amenazas (ponderada por nivel RAM y estado) y, aparte, de las oportunidades; y los puntos calientes significativos (Getis-Ord Gi*, 95 %). Alimenta el mapa de calor.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `celda_id` | texto | 0 | Identificador de la celda de la grilla. |
| `intensidad` | decimal | 0 | Densidad kernel de las amenazas, 0 a 1 (ponderada por nivel RAM y estado). |
| `intensidad_oportunidades` | decimal | 0 | Densidad kernel de las oportunidades abiertas, 0 a 1. |
| `severidad_celda` | decimal | 0 | Severidad de las amenazas que caen en la celda, sin suavizar (entrada del Gi*). |
| `gi_z` | decimal | 0 | Estadístico z de Getis-Ord Gi* de la celda (8 vecinas). |
| `punto_caliente` | booleano | 0 | Verdadero si la celda es un conglomerado significativo al 95 % (z >= 1,96). |
| `ict` | decimal | 0 | ICT del paquete en alerta. |
| `nivel` | texto | 0 | bajo, medio, alto o crítico según los umbrales. |

### `hidro.geojson` — Hidrología

*Contexto* · origen **sintético** · GeoJSON · 8 filas · geometría: Líneas

Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en `rios` y `cuerpos_agua`.

**Cómo se genera:** 8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_cuerpo_agua` | texto | 0 | Identificador del cuerpo de agua. |
| `nombre` | texto | 0 | Nombre descriptivo. |

### `indicadores_municipio.json` — Indicadores por municipio para el mapa

*Capa del mapa (real)* · origen **sintético** · JSON · 16 filas

Una fila por municipio (y el departamento) con su censo 2018, IRCA, territorio en resguardos y áreas protegidas, delitos por mes desde 2016 con resumen de 12 meses y tasas, y emergencias. Incluye la lista de indicadores que el mapa puede pintar. Alimenta la capa "Indicadores sociales" y la ficha de cada municipio.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento. |
| `nombre` | texto | 0 | Nombre. |
| `pdet` | booleano | 0 | Municipio PDET. |
| `subregion_pdet` | texto | 13 | Subregión PDET. |
| `censo.poblacion_2018` | decimal | 0 | Personas censadas en 2018. |
| `censo.poblacion_rural_dispersa` | decimal | 0 | Personas en el área rural dispersa. |
| `censo.pct_rural_disperso` | decimal | 0 | % de la población en el área rural dispersa. |
| `censo.indigenas` | decimal | 0 | Personas que se reconocen indígenas. |
| `censo.pct_indigena` | decimal | 0 | % de la población que se reconoce indígena. |
| `censo.afro` | decimal | 0 | Personas negras, mulatas o afrodescendientes. |
| `censo.pct_afro` | decimal | 0 | % afrodescendiente. |
| `censo.ipm` | decimal | 0 | Índice de Pobreza Multidimensional: % de personas pobres. |
| `censo.nbi` | decimal | 0 | % de personas con necesidades básicas insatisfechas. |
| `censo.nbi_vivienda` | decimal | 0 | NBI: vivienda inadecuada (%). |
| `censo.nbi_servicios` | decimal | 0 | NBI: servicios inadecuados (%). |
| `censo.nbi_hacinamiento` | decimal | 0 | NBI: hacinamiento crítico (%). |
| `censo.nbi_inasistencia` | decimal | 0 | NBI: niños que no asisten a la escuela (%). |
| `censo.nbi_dependencia` | decimal | 0 | NBI: alta dependencia económica (%). |
| `censo.miseria` | decimal | 0 | % de personas con dos o más NBI. |
| `censo.deficit_habitacional` | decimal | 0 | % de hogares en déficit habitacional. |
| `censo.hogares_sin_acueducto` | decimal | 0 | % de hogares sin acueducto (componente del déficit habitacional). |
| `irca.anios` | lista | 0 | Años con IRCA. |
| `irca.valores` | lista | 0 | IRCA de cada año. |
| `irca.ultimo` | texto | 0 | Último IRCA publicado. |
| `territorio.km2` | decimal | 0 | Área del municipio (km²). |
| `territorio.resguardo_km2` | decimal | 0 | km² del municipio en resguardos (sin contar solapes). |
| `territorio.pct_resguardo` | decimal | 0 | % del municipio en resguardos. |
| `territorio.resguardos_n` | entero | 0 | Resguardos que tocan el municipio. |
| `territorio.pueblos` | lista | 0 | Pueblos de esos resguardos. |
| `territorio.area_protegida_km2` | decimal | 0 | km² del municipio en áreas protegidas. |
| `territorio.pct_area_protegida` | decimal | 0 | % del municipio en áreas protegidas. |
| `territorio.area_protegidas_n` | entero | 0 | Áreas protegidas que tocan el municipio. |
| `seguridad.serie` | texto | 0 | Víctimas por mes de cada delito (desde 2016). |
| `seguridad.resumen` | texto | 0 | Últimos 12 meses, 12 anteriores, tasa y total desde 2003. |
| `emergencias.personas` | entero | 0 | Personas afectadas. |
| `emergencias.fallecidos` | entero | 0 | Personas fallecidas. |
| `emergencias.hectareas` | entero | 0 | Hectáreas afectadas. |

*5 columnas sin descripción en el catálogo.*

### `limite_departamental.geojson` — Contorno de La Guajira

*Límites (real)* · origen **DANE** · GeoJSON · 1 filas · geometría: Polígonos

La unión de los 15 municipios: un solo polígono de ~20.670 km². Sirve para recortar otras capas al departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `nombre` | texto | 0 | Nombre propio del municipio (el DANE lo escribe en mayúsculas y sin tildes). |
| `codigo` | texto | 0 | Código DANE (departamento + municipio, 5 dígitos). |
| `area_km2` | decimal | 0 | Área calculada en metros (EPSG:3116), en km². |

### `lluvia_chirps.json` — Lluvia por municipio para el mapa

*Capa del mapa (real)* · origen **sintético** · JSON · 16 filas

Una fila por municipio (y el departamento): la lluvia de cada mes de los últimos 10 años, la normal de cada mes del año (1991-2020) y cuánto se apartó cada mes de su normal, en %. Alimenta la capa "Lluvia por municipio" (CHIRPS) y la escala de meses del controlador de tiempo del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `nombre` | texto | 0 | Nombre del municipio o del departamento. |
| `mm` | lista | 0 | Lluvia del mes en mm (en Oro, una lista: un valor por mes de `metadata.meses`). |
| `normal` | lista | 0 | Lluvia normal de cada mes del año (enero a diciembre), promedio 1991-2020, en mm. |
| `anomalia_pct` | lista | 0 | Cuánto se apartó cada mes de su normal, en %: 0 es lo normal, -50 la mitad, +100 el doble. |
| `normal_anual` | decimal | 0 | Lluvia normal de un año completo (1991-2020), en mm. |
| `codigo` | texto | 0 | Código DANE del municipio (5 dígitos); 44 es el departamento entero. |

### `municipios.geojson` — Municipios

*Límites (real)* · origen **DANE** · GeoJSON · 15 filas · geometría: Polígonos

Un polígono por municipio con nombre propio, código DANE y área recalculada en metros. La geometría se simplifica sin abrir huecos entre vecinos (104 mil a 15 mil vértices). En Oro suma, por municipio, las estaciones del IDEAM y los kilómetros de vías nacionales.

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

Tabla principal de consumo: cada paquete con sus 5 criterios en escala fija de 0 a 1, la contribución de cada uno, el ICT, el nivel, los componentes del territorio REAL (resguardos, pobreza, áreas protegidas, vías, lluvia del IDEAM y de CHIRPS, emergencias, delitos) con su valor crudo, la confianza, la oportunidad, la tendencia, el escalamiento y el perfil RAM.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `ruta_critica` | booleano | 0 | Si el paquete está en la ruta crítica del cronograma. |
| `severidad_riesgo` | decimal | 0 | Criterio 0 a 1 (escala fija): severidad de las amenazas que alcanzan el paquete; 1 = VH materializado. |
| `exposicion_proyecto` | decimal | 0 | Criterio 0 a 1 (escala fija): ruta crítica y amenazas abiertas que alcanzan el paquete. |
| `vulnerabilidad_territorial` | decimal | 0 | Criterio 0 a 1 (escala fija): territorio étnico, pobreza, áreas protegidas y acceso (datos reales). |
| `amenazas_externas` | decimal | 0 | Criterio 0 a 1 (escala fija): lluvia reciente, lluvia anómala, emergencias y delitos (datos reales). |
| `convergencia` | decimal | 0 | Criterio 0 a 1 (escala fija): amenazas distintas que coinciden (registro + territorio). |
| `ICT` | decimal | 0 | Índice de Criticidad Territorial, 0 a 100. |
| `severidad_riesgo_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `exposicion_proyecto_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `vulnerabilidad_territorial_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `amenazas_externas_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `convergencia_contrib` | decimal | 0 | Puntos que aporta el criterio al ICT (peso × valor normalizado × 100). |
| `nivel` | texto | 0 | bajo, medio, alto o crítico según los umbrales. |
| `indice_confianza` | decimal | 0 | Fracción de la información del modelo disponible y al día (0 a 1), ponderada por el peso de cada criterio. |
| `indice_oportunidad` | decimal | 0 | Índice de 0 a 100 sobre las oportunidades abiertas (nivel RAM del beneficio; 100 = VH). |
| `municipio` | texto | 0 | Municipio (DANE) donde cae: las coordenadas del riesgo o el centro del paquete. |
| `delitos_100k` | decimal | 0 | Delitos contra personas e infraestructura en 12 meses por 100.000 hab. (sin homicidio). |
| `emergencias_por_ano` | decimal | 0 | Emergencias atendidas por la UNGRD por año en el municipio. |
| `anomalia_lluvia` | decimal | 0 | Desviación media de la lluvia de los últimos meses frente a la normal 1991-2020 (fracción). |
| `fraccion_resguardo` | decimal | 0 | Fracción del paquete dentro de resguardos indígenas (ANT). |
| `distancia_resguardo_km` | decimal | 0 | Distancia al resguardo más cercano en km (0 si se tocan). |
| `fraccion_area_protegida` | decimal | 0 | Fracción del paquete dentro de áreas protegidas (RUNAP). |
| `distancia_area_protegida_km` | decimal | 0 | Distancia al área protegida más cercana en km (0 si se tocan). |
| `vias_tiempo_seco` | decimal | 0 | Fracción de los km de vías a menos de 10 km solo transitables en tiempo seco. |
| `lluvia_mm` | decimal | 3 | Lluvia acumulada en la ventana en la estación del IDEAM elegida (vacío = sin dato al día). |
| `lluvia_estacion` | texto | 3 | Estación del IDEAM más cercana con datos suficientes en la ventana. |
| `lluvia_distancia_km` | decimal | 0 | Distancia a esa estación en km. |
| `lluvia_dias_con_dato` | entero | 0 | Días con dato de esa estación dentro de la ventana. |
| `vul_etnico` | decimal | 0 | Componente 0 a 1: fracción del paquete en resguardo (colindante cuenta la mitad). ANT. |
| `vul_pobreza` | decimal | 0 | Componente 0 a 1: IPM del municipio / 100. DANE, censo 2018. |
| `vul_ambiental` | decimal | 0 | Componente 0 a 1: dentro de un área protegida = 1, decae con la distancia. RUNAP. |
| `vul_acceso` | decimal | 0 | Componente 0 a 1: fracción de los km de vías cercanas solo transitables en tiempo seco. INVIAS + IGAC. |
| `ext_lluvia_reciente` | decimal | 3 | Componente 0 a 1: lluvia acumulada en la ventana / tope. IDEAM; vacío si no hay estación al día. |
| `ext_anomalia_lluvia` | decimal | 0 | Componente 0 a 1: desviación de la lluvia de los últimos meses frente a la normal. CHIRPS. |
| `ext_emergencias` | decimal | 0 | Componente 0 a 1: emergencias por año en el municipio / tope. UNGRD. |
| `ext_seguridad` | decimal | 0 | Componente 0 a 1: delitos contra proyectos por 100.000 hab. / tope. MinDefensa. |
| `amenazas_que_alcanzan` | decimal | 0 | Amenazas abiertas que alcanzan el paquete (las de otros paquetes cuentan según su radio). |
| `n_categorias_registro` | entero | 0 | Categorías de amenaza abiertas (nivel RAM M o más) que coinciden en el paquete. |
| `n_factores_territorio` | entero | 0 | Factores del territorio por encima de su umbral (lluvia, emergencias, delitos). |
| `amenazas_convergentes` | texto | 0 | Las amenazas que coinciden, del registro y del territorio. |
| `disp_severidad_riesgo` | decimal | 0 | 1 si el paquete tiene riesgos en el registro (está evaluado). |
| `disp_exposicion_proyecto` | decimal | 0 | 1 si el paquete tiene riesgos en el registro. |
| `disp_convergencia` | decimal | 0 | 1 si el paquete tiene riesgos en el registro. |
| `disp_vulnerabilidad_territorial` | decimal | 0 | Fracción del peso de la vulnerabilidad con dato real. |
| `disp_amenazas_externas` | decimal | 0 | Fracción del peso de las amenazas externas con dato real y al día. |
| `ram_N` | entero | 0 | Amenazas abiertas con nivel residual N. |
| `ram_L` | entero | 0 | Amenazas abiertas con nivel residual L. |
| `ram_M` | entero | 0 | Amenazas abiertas con nivel residual M. |
| `ram_H` | entero | 0 | Amenazas abiertas con nivel residual H. |
| `ram_VH` | entero | 0 | Amenazas abiertas con nivel residual VH (intolerable). |
| `ram_peor_inherente` | texto | 0 | Peor nivel RAM sin controles entre las amenazas abiertas. |
| `ram_peor_residual` | texto | 0 | Peor nivel RAM con controles. |
| `escalamiento` | booleano | 0 | Verdadero si el paquete cumple alguna regla de escalamiento a crisis. |
| `reglas_escalamiento` | texto | 0 | Identificadores de las reglas que se cumplieron (ict_critico, ram_vh, ram_h_ruta_critica, area_sensible, convergencia, acciones_vencidas). |
| `causas_escalamiento` | texto | 0 | Reglas que se cumplieron, separadas por punto y coma. |
| `ict_hace_ndias` | decimal | 0 | ICT recalculado con los datos de hace 7 días (misma escala fija). |
| `tendencia_delta` | decimal | 0 | Cambio del ICT en los últimos 7 días. |
| `tendencia_alerta` | booleano | 0 | Verdadero si el ICT subió más que el umbral de tendencia. |
| `en_punto_caliente` | booleano | 0 | Verdadero si una celda de punto caliente (Gi*) cae en el paquete o a menos de media celda. |
| `puntos_crisis` | entero | 0 | Puntos de crisis del paquete en el mapa. |

*1 columnas sin descripción en el catálogo.*

### `proyectos.geojson` — Proyectos

*Contexto* · origen **sintético** · GeoJSON · 3 filas · geometría: Polígonos

Límites de los proyectos que agrupan los paquetes de trabajo.

**Cómo se genera:** 3 proyectos ficticios (Proyecto 1 al norte, 2 al centro y 3 al sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `nombre` | texto | 0 | Nombre descriptivo. |
| `fecha_inicio_plan` | fecha | 0 | Inicio planeado (línea base): el de su primera actividad. |
| `fecha_fin_plan` | fecha | 0 | Fin planeado (línea base): el de su última actividad. |

### `puntos_crisis.geojson` — Puntos de crisis

*Resultado del modelo* · origen **sintético** · GeoJSON · 18 filas · geometría: Puntos

Dónde un evento podría escalar a crisis: la amenaza que dispara una regla de escalamiento (o el centro del paquete si la causa es del paquete entero), con su causa, su prioridad, la decisión que exige la RAM, quién decide y el radio de su zona de intervención.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_punto` | texto | 0 | Identificador del punto (PC- + riesgo o paquete). |
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `nombre_paquete` | texto | 0 | Nombre del paquete. |
| `tipo` | texto | 0 | riesgo (la amenaza dispara la regla) o paquete (causa del paquete entero). |
| `id_riesgo` | texto | 5 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `categoria` | texto | 5 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `nivel_ram` | texto | 0 | Nivel RAM residual de la amenaza (o el peor del paquete). |
| `ram` | texto | 5 | Código RAM residual (consecuencia + probabilidad). |
| `estado` | texto | 5 | latente, proximo_a_materializarse o materializado. |
| `reglas` | texto | 0 | Reglas de escalamiento que dispara. |
| `causas` | texto | 0 | Por qué puede escalar, en texto. |
| `n_causas` | entero | 0 | Cuántas reglas dispara. |
| `prioridad` | texto | 0 | critica (VH o ICT crítico) o alta. |
| `radio_m` | decimal | 0 | Radio de la zona de intervención: el de influencia de su categoría (m). |
| `decision` | texto | 0 | Qué exige la RAM para ese nivel. |
| `aprueba` | texto | 0 | Quién decide según la RAM. |
| `accion_tratamiento` | texto | 5 | Acción de tratamiento registrada. |
| `fecha_accion` | fecha | 8 | Fecha de ejecución de la acción. |
| `accion_vencida` | booleano | 0 | Verdadero si la acción ya debió ejecutarse. |

### `red_vial.geojson` — Red vial unificada

*Capa del mapa (real)* · origen **INVIAS + IGAC** · GeoJSON · 5.273 filas · geometría: Líneas

La red nacional de INVIAS (8 tramos, ~300 km, con ruta, administrador y categoría) y la red complementaria del IGAC (~18.300 km), en una sola tabla, sin duplicados: lo que el IGAC repite de la red nacional (~320 km, a menos de 50 m) se quitó. La columna `fuente` (INVIAS o IGAC) y `estilo` distinguen cada red. A los tramos de INVIAS, que no traen superficie, se les pone la del IGAC sobre el mismo trazado. Alimenta la capa de vías del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_tramo` | texto | 0 | Identificador: fuente y número de tramo. |
| `fuente` | texto | 0 | INVIAS (red nacional) o IGAC (red complementaria). |
| `grupo` | texto | 0 | Red nacional o Red complementaria. |
| `estilo` | texto | 0 | Clave de dibujo: n0 a n2 (categorías de INVIAS) e i1 a i7 (clases del IGAC). |
| `clase` | texto | 0 | Clase de vía: categoría de INVIAS o clase interpretada del IGAC. |
| `ruta` | texto | 5265 | Número de la ruta nacional (solo INVIAS). |
| `nombre_ruta` | texto | 5265 | Nombre de la ruta (solo INVIAS). |
| `sector` | texto | 5265 | Sector del tramo (solo INVIAS). |
| `administrador` | texto | 5265 | Quién administra el tramo (solo INVIAS). |
| `calzada` | texto | 5265 | Sencilla o doble (solo INVIAS). |
| `superficie` | texto | 1840 | Pavimentada, sin pavimentar... En INVIAS, tomada del IGAC sobre el mismo trazado. |
| `superficie_fuente` | texto | 1840 | De dónde sale la superficie: INVIAS, IGAC o IGAC (cruce espacial). |
| `carriles` | texto | 4979 | 2 o más carriles, o angosta (solo IGAC). |
| `accesibilidad` | texto | 1847 | Todo el año o solo en tiempo seco (solo IGAC). |
| `nombre` | texto | 5271 | Nombre de la vía, si lo tiene. |
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

### `resguardos.geojson` — Resguardos indígenas

*Capa del mapa (real)* · origen **sintético** · GeoJSON · 39 filas · geometría: Polígonos

Los resguardos que tocan La Guajira, recortados al departamento, con pueblo normalizado, área, población 2020 (parte guajira), municipios que tocan y último acto administrativo. Cubren cerca del 63 % del departamento.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_resguardo` | texto | 0 | Identificador de la ANT. |
| `codigo_resguardo` | texto | 8 | Código DANE del resguardo. |
| `nombre` | texto | 0 | Nombre. |
| `pueblo` | texto | 0 | Pueblo indígena. |
| `area_km2` | decimal | 0 | Área en km² (en La Guajira para los resguardos; total para las áreas protegidas). |
| `poblacion_2020` | decimal | 15 | Población proyectada a 2020 (Ministerio del Interior), parte guajira. |
| `municipios` | texto | 0 | Códigos de los municipios que toca. |
| `ultimo_acto` | texto | 0 | Último acto administrativo. |
| `anio_ultimo_acto` | entero | 0 | Año del último acto. |

### `riesgos.geojson` — Registro de riesgos

*Registro* · origen **sintético** · GeoJSON · 200 filas · geometría: Puntos

Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, calificado con la matriz RAM de Ecopetrol (consecuencia 0-5 en Personas, Económica, Ambiental, Clientes e Imagen; probabilidad A-E sin y con controles), estado de materialización y acción de tratamiento. En Plata cada riesgo queda ubicado en la matriz (celda y nivel N, L, M, H o VH, inherente y residual).

**Cómo se genera:** 200 riesgos repartidos en los 14 paquetes. La consecuencia por dimensión sigue el perfil de su categoría (un riesgo social pesa en Imagen; uno de seguridad, en Personas). Tres paquetes 'calientes' reciben más riesgos, con consecuencias y probabilidades más altas, para que el mapa muestre patrones. Los controles bajan la probabilidad 0 a 2 letras. ~18% son oportunidades.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_riesgo` | texto | 0 | Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP. |
| `id_evento_riesgo` | texto | 6 | Identificador del evento de riesgo asociado. |
| `descripcion` | texto | 0 | Descripción textual del riesgo. |
| `causa` | texto | 0 | Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'. |
| `categoria` | texto | 0 | Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza. |
| `tipo` | texto | 0 | amenaza u oportunidad (riesgo positivo). |
| `cons_personas` | entero | 0 | Matriz RAM: consecuencia potencial para las personas, 0 a 5. |
| `cons_economica` | entero | 0 | Matriz RAM: consecuencia económica, 0 a 5 (5 = más de USD 10 M). |
| `cons_ambiental` | entero | 0 | Matriz RAM: consecuencia ambiental, 0 a 5 (5 = contaminación irreparable). |
| `cons_clientes` | decimal | 8 | Matriz RAM: consecuencia para los clientes, 0 a 5. Vacía si el evaluador no la calificó. |
| `cons_imagen` | entero | 0 | Matriz RAM: consecuencia en la imagen, 0 a 5 (5 = internacional). |
| `probabilidad` | texto | 0 | Matriz RAM: probabilidad inherente (sin controles), A a E. En Bronce llega como 'C', 'c', 'C - Ha ocurrido...' o '3'. |
| `probabilidad_residual` | texto | 0 | Matriz RAM: probabilidad con los controles actuales, A a E. |
| `controles` | texto | 0 | Controles que reducen la probabilidad (de inherente a residual). |
| `estado` | texto | 0 | latente, proximo_a_materializarse o materializado. |
| `id_proyecto` | texto | 0 | Proyecto al que pertenece. |
| `id_paquete_trabajo` | texto | 0 | Paquete de trabajo al que pertenece (llave hacia paquetes). |
| `actividad_registrada` | texto | 17 | Actividad afectada tal como llegó en el registro (sin corregir), para trazabilidad. |
| `fecha_identificacion` | fecha | 0 | Fecha en que se identificó el riesgo. |
| `fecha_materializacion` | fecha | 154 | Fecha de materialización; vacía si no se ha materializado. |
| `accion_tratamiento` | texto | 0 | Acción de tratamiento definida. |
| `fecha_ejecucion_accion` | fecha | 16 | Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida. |
| `lat` | decimal | 0 | Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `lon` | decimal | 0 | Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida). |
| `fuente` | texto | 0 | Archivo de origen del registro (simula varios Excel dispersos). |
| `categoria_registrada` | texto | 0 | Categoría tal como llegó en el registro (sin_clasificar si faltaba o era ilegible). |
| `categoria_ia` | texto | 0 | Categoría que sugiere la IA leyendo la descripción y la causa. |
| `confianza_ia` | decimal | 0 | Probabilidad que la IA le da a su categoría (0 a 1). |
| `palabras_ia` | texto | 0 | Palabras del texto que más pesaron en la decisión de la IA (explicación). |
| `categoria_origen` | texto | 0 | De dónde sale la categoría final: registro, ia (la asignó el clasificador de texto) o pendiente. |
| `revisar_categoria` | booleano | 0 | Verdadero si el texto contradice la categoría registrada con alta confianza. |
| `municipio_mencionado` | texto | 132 | Municipios que nombra el texto (diccionario geográfico del DANE). |
| `revisar_ubicacion` | booleano | 0 | Verdadero si el texto nombra un municipio a más de 15 km del paquete del riesgo. |
| `ram_inherente` | texto | 0 | Celda RAM sin controles: consecuencia de la peor dimensión + probabilidad (p. ej. 5D). |
| `nivel_inherente` | texto | 0 | Nivel RAM sin controles: N, L, M, H o VH. |
| `ram_residual` | texto | 0 | Celda RAM con controles (p. ej. 5B). |
| `nivel_residual` | texto | 0 | Nivel RAM con controles: N, L, M, H o VH. Es el que usa el ICT. |
| `dimension_dominante` | texto | 0 | Dimensión que manda en la calificación residual: PE, EC, MA, CL o IM. |
| `puntaje_ram` | entero | 0 | Puntaje del nivel residual: N=1, L=2, M=3, H=4, VH=5. |
| `problema_fechas` | texto | 195 | Qué pasó con las fechas del riesgo (cruzadas, un año de más, sin fecha de materialización...). |
| `revisar_fechas` | booleano | 0 | Verdadero si alguna fecha del riesgo se corrigió o no cuadra: alguien debería revisarla. |
| `id_actividad` | texto | 0 | Actividad del cronograma a la que pega el riesgo (o de la que es parte la fila). |
| `actividad` | texto | 0 | Nombre de la actividad del cronograma a la que pega el riesgo. |
| `actividad_origen` | texto | 0 | De dónde sale la actividad: registro (código válido), nombre (se reconoció el nombre o la disciplina), inferida (venía vacía) o corregida (código de otro paquete, o una actividad que no cuadra con el momento del riesgo). |
| `revisar_actividad` | booleano | 0 | Verdadero si la actividad registrada se tuvo que corregir: alguien debería revisarla. |
| `geolocalizacion_inferida` | booleano | 0 | Verdadero si la ubicación se tomó del centroide del paquete porque el registro no traía coordenadas. |
| `severidad` | entero | 0 | Puntaje del nivel RAM residual (1 a 5); pondera el mapa de calor. |
| `punto_crisis` | booleano | 0 | Verdadero si la amenaza es un punto donde el paquete puede escalar a crisis. |
| `causa_crisis` | texto | 187 | Por qué esa amenaza es un punto de crisis. |
| `alcanza_resguardo` | texto | 173 | Resguardo indígena (ANT) que alcanza el área de influencia de la amenaza, si su categoría puede afectarlo. |
| `alcanza_area_protegida` | texto | 193 | Área protegida (RUNAP) que alcanza el área de influencia de la amenaza, si su categoría puede afectarla. |
| `codigo_municipio` | texto | 0 | Código DANE de 5 dígitos de ese municipio. |
| `municipio` | texto | 0 | Municipio (DANE) donde cae: las coordenadas del riesgo o el centro del paquete. |

### `rios.geojson` — Ríos para el mapa

*Capa del mapa (real)* · origen **IGAC** · GeoJSON · 9.605 filas · geometría: Líneas

Tramos de ríos, arroyos y quebradas con nombre (si tiene), estado del cauce y longitud. Alimenta la capa de ríos del mapa.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_objeto` | texto | 0 | Identificador: tipo de objeto y número de objeto en el servicio del IGAC. |
| `nombre` | texto | 7702 | Nombre del río, arroyo o cuerpo de agua, normalizado (vacío si no tiene). |
| `estado` | texto | 0 | Permanente o intermitente, según la clasificación del IGAC a 1:100.000 (no es una medición de caudal). |
| `longitud_km` | decimal | 0 | Longitud del tramo en km, calculada en metros (EPSG:3116). |

### `validacion_backtest.csv` — Prueba de consistencia (circular)

*Validación* · origen **sintético** · CSV · 14 filas

ICT de cada paquete frente al número de riesgos que ya se materializaron. Es circular (los materializados entran al ICT): comprueba el mecanismo, no valida el modelo; la validación real necesita el historial de Ecopetrol (Fase 4).

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

### `zonas_intervencion.geojson` — Zonas de intervención prioritaria

*Resultado del modelo* · origen **sintético** · GeoJSON · 5 filas · geometría: Polígonos

Unión, por paquete, de las áreas de influencia de sus puntos de crisis: dónde intervenir primero.

| Columna | Tipo | Nulos | Descripción |
|---|---|---:|---|
| `id_paquete` | texto | 0 | Identificador del paquete (PRY-01-PT03). |
| `nombre_paquete` | texto | 0 | Nombre del paquete. |
| `prioridad` | texto | 0 | critica (VH o ICT crítico) o alta. |
| `n_puntos` | entero | 0 | Puntos de crisis que forman la zona. |
| `area_km2` | decimal | 0 | Área de la zona de intervención en km². |
