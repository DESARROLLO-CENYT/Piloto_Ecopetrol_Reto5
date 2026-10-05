"""
Catalogo de datos del piloto: inventaria en vivo las tablas de las capas
Bronce, Plata y Oro (filas, geometria, columnas y tipos) y les une
descripciones curadas. Asi la pagina "Datos y modelo" no queda con cifras
escritas a mano que se desactualizan al volver a correr el pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from scipy.stats import spearmanr

from comun.config import BRONCE, ORO, PLATA

CAPAS = [
    ("bronze", "Bronce", BRONCE),
    ("silver", "Plata", PLATA),
    ("gold", "Oro", ORO),
]

# archivo -> dataset logico (el mismo dataset cambia de nombre entre capas)
ARCHIVO_A_DATASET = {
    "registro_riesgos.xlsx": "riesgos",
    "riesgos.geojson": "riesgos",
    "paquetes_trabajo.geojson": "paquetes",
    "paquetes.geojson": "paquetes",
    "paquetes_ict.geojson": "paquetes_ict",
    "proyectos.geojson": "proyectos",
    "comunidades.geojson": "comunidades",
    "areas_protegidas.geojson": "areas",
    "areas.geojson": "areas",
    "hidrologia.geojson": "hidro",
    "hidro.geojson": "hidro",
    "vias.geojson": "vias",
    "clima_sintetico.csv": "clima_sintetico",
    "clima_sintetico.parquet": "clima_sintetico",
    "ideam_estaciones.csv": "ideam_estaciones",
    "ideam_estaciones.geojson": "ideam_estaciones",
    "ideam_precipitacion.parquet": "ideam_precipitacion",
    "ideam_precip_diaria.parquet": "ideam_precip_diaria",
    "ideam_variables.parquet": "ideam_variables",
    "ideam_variables_diaria.parquet": "ideam_variables_diaria",
    "ideam_variables_horaria.parquet": "ideam_variables_horaria",
    "ideam_ultimas_horas.parquet": "ideam_ultimas_horas",
    "ideam_radiacion.csv": "ideam_radiacion",
    "ideam_radiacion.parquet": "ideam_radiacion",
    "ideam_normales.csv": "ideam_normales",
    "ideam_normales.parquet": "ideam_normales",
    "clima_radiacion.geojson": "clima_radiacion",
    "ideam_meta.json": "ideam_meta",
    "dane_municipios.geojson": "dane_municipios",
    "divipola_municipios.csv": "divipola_municipios",
    "municipios_meta.json": "municipios_meta",
    "municipios.geojson": "municipios",
    "limite_departamental.geojson": "limite_departamental",
    "reporte_calidad_municipios.csv": "municipios_reporte_calidad",
    "reporte_cruces_municipios.csv": "municipios_reporte_cruces",
    "igac_drenaje_sencillo.geojson": "igac_drenaje_sencillo",
    "igac_drenaje_doble.geojson": "igac_drenaje_doble",
    "igac_cienagas.geojson": "igac_cienagas",
    "igac_embalses.geojson": "igac_embalses",
    "igac_lagunas.geojson": "igac_lagunas",
    "hidrografia_meta.json": "hidrografia_meta",
    "igac_hidrografia.geojson": "igac_hidrografia",
    "reporte_calidad_hidrografia.csv": "hidrografia_reporte_calidad",
    "rios.geojson": "rios",
    "cuerpos_agua.geojson": "cuerpos_agua",
    "igac_via_tipo1.geojson": "igac_vias_crudas", "igac_via_tipo2.geojson": "igac_vias_crudas",
    "igac_via_tipo3.geojson": "igac_vias_crudas", "igac_via_tipo4.geojson": "igac_vias_crudas",
    "igac_via_tipo5.geojson": "igac_vias_crudas", "igac_via_tipo6.geojson": "igac_vias_crudas",
    "igac_via_caminos.geojson": "igac_vias_crudas",
    "vias_igac_meta.json": "vias_igac_meta",
    "igac_vias.geojson": "igac_vias",
    "reporte_calidad_vias_igac.csv": "vias_igac_reporte_calidad",
    "red_vial.geojson": "red_vial",
    "proveniencia_ideam.json": "proveniencia",
    "proveniencia_invias.json": "proveniencia",
    "proveniencia_vias_igac.json": "proveniencia",
    "proveniencia_hidrografia.json": "proveniencia",
    "proveniencia_municipios.json": "proveniencia",
    "proveniencia_red_vial.json": "proveniencia",
    "reporte_calidad_red_vial.csv": "red_vial_reporte_calidad",
    "invias_red_vial.geojson": "invias_red_vial",
    "invias_meta.json": "invias_meta",
    "reporte_calidad_invias.csv": "invias_reporte_calidad",
    "reporte_calidad_ideam.csv": "ideam_reporte_calidad",
    "clima_estaciones.geojson": "clima_estaciones",
    "reporte_calidad_bronce_a_plata.csv": "reporte_calidad",
    "grid_calor.geojson": "grid_calor",
    "alertas.json": "alertas",
    "validacion_backtest.csv": "validacion_backtest",
    "validacion_sensibilidad.csv": "validacion_sensibilidad",
}

DATASETS = {
    "riesgos": {
        "titulo": "Registro de riesgos", "icono": "file-spreadsheet", "rol": "Registro",
        "descripcion": "Cada fila es un riesgo identificado en un paquete de trabajo: amenaza u oportunidad, "
                       "con probabilidad, impacto, estado de materialización y acción de tratamiento.",
        "generacion": "200 riesgos repartidos en los 14 paquetes. Tres paquetes 'calientes' reciben más "
                      "riesgos y con probabilidad e impacto altos, para que el mapa muestre patrones. "
                      "~18% son oportunidades.",
    },
    "paquetes": {
        "titulo": "Paquetes de trabajo", "icono": "hexagon", "rol": "Unidad de análisis",
        "descripcion": "Polígonos de los paquetes de trabajo. Son la unidad sobre la que se calcula el ICT.",
        "generacion": "14 círculos (4 a 6 por proyecto), todos dentro de su proyecto y de tierra firme; ~30% marcados como ruta crítica.",
    },
    "paquetes_ict": {
        "titulo": "Paquetes con ICT", "icono": "radar", "rol": "Resultado del modelo",
        "descripcion": "Tabla principal de consumo: cada paquete con sus 5 criterios normalizados, la "
                       "contribución de cada uno, el ICT, el nivel, las reglas de escalamiento, la tendencia "
                       "y el resultado de Getis-Ord.",
    },
    "proyectos": {
        "titulo": "Proyectos", "icono": "briefcase", "rol": "Contexto",
        "descripcion": "Límites de los proyectos que agrupan los paquetes de trabajo.",
        "generacion": "3 proyectos ficticios (Norte, Centro, Sur) en tierra firme de La Guajira: cada uno queda en el punto más cercano a su zona donde cabe entero dentro del departamento.",
    },
    "comunidades": {
        "titulo": "Comunidades", "icono": "users", "rol": "Vulnerabilidad",
        "descripcion": "Asentamientos con población aproximada e índice de conflictividad social.",
        "generacion": "18 puntos aleatorios sobre tierra firme (a más de 2 km de la costa y la frontera), con nombres genéricos; conflictividad sesgada a valores bajos (Beta 2,5).",
    },
    "areas": {
        "titulo": "Áreas protegidas", "icono": "trees", "rol": "Vulnerabilidad",
        "descripcion": "Áreas de interés ambiental con un índice de sensibilidad.",
        "generacion": "6 círculos enteros dentro de tierra firme, con categorías ficticias (parque, reserva, humedal) y sensibilidad 0.4 a 1.",
    },
    "hidro": {
        "titulo": "Hidrología", "icono": "waves", "rol": "Contexto",
        "descripcion": "Cuerpos de agua (arroyos) como líneas. Es la inventada; la hidrografía real del IGAC está en "
                       "`rios` y `cuerpos_agua`.",
        "generacion": "8 líneas quebradas generadas con pasos aleatorios; lo que se sale del departamento se corta.",
    },
    "vias": {
        "titulo": "Vías", "icono": "route", "rol": "Contexto",
        "descripcion": "Red vial por tipo (primaria, secundaria, terciaria de difícil acceso). Es la inventada; "
                       "la red real (INVIAS e IGAC) está en `red_vial` y aún no alimenta el ICT.",
        "generacion": "10 segmentos rectos con tipo aleatorio, enteros dentro de tierra firme.",
    },
    "dane_municipios": {
        "titulo": "Municipios del DANE (crudos)", "icono": "map-pinned", "rol": "Límites (real)", "origen": "dane",
        "descripcion": "Los 15 polígonos municipales de La Guajira del Marco Geoestadístico Nacional del DANE (versión 2005, "
                       "base del IGAC), tal como los publica el servicio, con sus más de 200 atributos del censo y ~125 mil vértices.",
    },
    "divipola_municipios": {
        "titulo": "DIVIPOLA de La Guajira", "icono": "list", "rol": "Códigos y nombres (real)", "origen": "dane",
        "descripcion": "Código DANE, nombre y coordenadas de la cabecera de cada municipio (datos.gov.co, DANE).",
    },
    "municipios_meta": {
        "titulo": "Metadatos de la descarga de municipios", "icono": "info", "rol": "Trazabilidad (real)", "origen": "dane",
        "descripcion": "Servicio de origen, versión de la geometría, licencia y fecha de descarga.",
    },
    "municipios": {
        "titulo": "Municipios", "icono": "map-pinned", "rol": "Límites (real)", "origen": "dane",
        "descripcion": "Un polígono por municipio con nombre propio, código DANE y área recalculada en metros. La geometría se "
                       "simplifica sin abrir huecos entre vecinos (125 mil a 14 mil vértices). En Oro suma, por municipio, las "
                       "estaciones del IDEAM y los kilómetros de vías nacionales.",
    },
    "limite_departamental": {
        "titulo": "Contorno de La Guajira", "icono": "map-pinned", "rol": "Límites (real)", "origen": "dane",
        "descripcion": "La unión de los 15 municipios: un solo polígono de ~20.670 km². Sirve para recortar otras capas al "
                       "departamento.",
    },
    "ideam_variables_horaria": {
        "titulo": "Otras variables por hora (limpias)", "icono": "clock", "rol": "Lecturas limpias (real)", "origen": "ideam",
        "descripcion": "Las lecturas de temperatura, humedad, viento, presión y nivel ya clasificadas por sensor, sin duplicados y "
                       "en unidades unificadas, una fila por estación, variable y hora. Oro calcula de aquí el promedio de las "
                       "últimas 24 horas; por eso se guarda en Plata y no se vuelve a Bronce.",
    },
    "proveniencia": {
        "titulo": "Proveniencia de cada fuente", "icono": "file-search", "rol": "Trazabilidad", "origen": "meta",
        "descripcion": "Un archivo por fuente con lo que Plata sabe de su origen: la descarga de Bronce (fuente, licencia, fecha, caja) y "
                       "el control de calidad que pasó. Oro lee esto para decir de dónde viene cada producto, sin tener que volver a Bronce.",
    },
    "municipios_reporte_cruces": {
        "titulo": "Cruces espaciales de municipios", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "dane",
        "descripcion": "Lo que encontró el cruce de los municipios con otras fuentes: estaciones del IDEAM fuera de los polígonos o en un "
                       "municipio distinto del declarado, y kilómetros de vías dentro de los municipios.",
    },
    "municipios_reporte_calidad": {
        "titulo": "Reporte de calidad de municipios", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "dane",
        "descripcion": "Geometrías inválidas, diferencia de área con la fuente, partes del departamento y huecos entre municipios.",
    },
    "igac_drenaje_sencillo": {
        "titulo": "Drenajes sencillos (crudos)", "icono": "waves", "rol": "Ríos y arroyos (real)", "origen": "igac",
        "descripcion": "Ríos, arroyos y quebradas como líneas, tal como los publica el IGAC a escala 1:100.000: ~9.600 "
                       "tramos y casi 590 mil vértices. Cada tramo trae nombre (solo 1 de cada 5 lo tiene) y un código "
                       "de estado del cauce: 5101 permanente, 5102 intermitente.",
    },
    "igac_drenaje_doble": {
        "titulo": "Drenajes principales (crudos)", "icono": "waves", "rol": "Ríos anchos (real)", "origen": "igac",
        "descripcion": "Ríos lo bastante anchos para dibujarse como polígono (Palomino, Cesar, arroyos grandes).",
    },
    "igac_cienagas": {
        "titulo": "Ciénagas (crudas)", "icono": "waves", "rol": "Cuerpos de agua (real)", "origen": "igac",
        "descripcion": "Ciénagas como polígonos, según la cartografía básica del IGAC.",
    },
    "igac_embalses": {
        "titulo": "Embalses (crudos)", "icono": "waves", "rol": "Cuerpos de agua (real)", "origen": "igac",
        "descripcion": "Embalses y represas como polígonos (El Cercado, Jojaipana).",
    },
    "igac_lagunas": {
        "titulo": "Lagunas (crudas)", "icono": "waves", "rol": "Cuerpos de agua (real)", "origen": "igac",
        "descripcion": "Lagunas como polígonos; solo un tercio tiene nombre. La cartografía marca el contorno, no si "
                       "hoy hay agua.",
    },
    "hidrografia_meta": {
        "titulo": "Metadatos de la descarga de hidrografía", "icono": "info", "rol": "Trazabilidad (real)", "origen": "igac",
        "descripcion": "Servicio de origen, licencia (uso libre solo sin fines comerciales), fecha, caja de descarga y "
                       "cuántos objetos y vértices llegaron por capa.",
    },
    "igac_hidrografia": {
        "titulo": "Hidrografía unificada", "icono": "waves", "rol": "Ríos y agua (real)", "origen": "igac",
        "descripcion": "Las cinco capas en una sola tabla con la columna `tipo`. Geometrías reparadas, recortadas a la "
                       "caja de descarga y simplificadas (25 m líneas, 20 m polígonos: de 661 mil a 119 mil vértices), "
                       "con estado del cauce traducido y nombres normalizados.",
    },
    "hidrografia_reporte_calidad": {
        "titulo": "Reporte de calidad de hidrografía", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "igac",
        "descripcion": "Objetos y vértices antes y después, nombres vacíos y kilómetros de cauce por estado.",
    },
    "rios": {
        "titulo": "Ríos para el mapa", "icono": "waves", "rol": "Capa del mapa (real)", "origen": "igac",
        "descripcion": "Tramos de ríos, arroyos y quebradas con nombre (si tiene), estado del cauce y longitud. Alimenta la "
                       "capa de ríos del mapa.",
    },
    "cuerpos_agua": {
        "titulo": "Cuerpos de agua para el mapa", "icono": "waves", "rol": "Capa del mapa (real)", "origen": "igac",
        "descripcion": "Ríos anchos, ciénagas, lagunas y embalses como polígonos con su área en km².",
    },
    "igac_vias_crudas": {
        "titulo": "Vías del IGAC (crudas)", "icono": "route", "rol": "Vías (real)", "origen": "igac",
        "descripcion": "Siete archivos, uno por capa del servicio: seis tipos de vía y los caminos y senderos, tal como los "
                       "publica el IGAC a 1:100.000 (5.600 objetos y 197 mil vértices en La Guajira y alrededores). "
                       "El tipo (1 a 7) no viene explicado; se interpreta por sus atributos.",
    },
    "vias_igac_meta": {
        "titulo": "Metadatos de la descarga de vías del IGAC", "icono": "info", "rol": "Trazabilidad (real)", "origen": "igac",
        "descripcion": "Servicio de origen, licencia (uso libre solo sin fines comerciales), fecha, caja y objetos por capa.",
    },
    "igac_vias": {
        "titulo": "Vías del IGAC unificadas", "icono": "route", "rol": "Vías (real)", "origen": "igac",
        "descripcion": "Las siete capas en una tabla: clase de vía (pavimentada o no, ancho, accesibilidad), recortadas a los "
                       "municipios del DANE y simplificadas a 20 m (197 mil a 59 mil vértices).",
    },
    "vias_igac_reporte_calidad": {
        "titulo": "Reporte de calidad de vías del IGAC", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "igac",
        "descripcion": "Objetos y vértices antes y después, kilómetros por clase y atributos sin valor.",
    },
    "red_vial": {
        "titulo": "Red vial unificada", "icono": "route", "rol": "Capa del mapa (real)", "origen": "invias_igac",
        "descripcion": "La red nacional de INVIAS (8 tramos, ~300 km, con ruta, administrador y categoría) y la red "
                       "complementaria del IGAC (~18.300 km), en una sola tabla, sin duplicados: lo que el IGAC repite de la "
                       "red nacional (~320 km, a menos de 50 m) se quitó. La columna `fuente` (INVIAS o IGAC) y `estilo` "
                       "distinguen cada red. A los tramos de INVIAS, que no traen superficie, se les pone la del IGAC sobre "
                       "el mismo trazado. Alimenta la capa de vías del mapa.",
    },
    "red_vial_reporte_calidad": {
        "titulo": "Reporte de calidad de la red vial", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "invias_igac",
        "descripcion": "Kilómetros de cada fuente, cuántos repetía el IGAC, cuántos tramos de INVIAS recibieron superficie "
                       "del IGAC y el total unificado.",
    },
    "invias_red_vial": {
        "titulo": "Red vial nacional (INVIAS)", "icono": "route", "rol": "Vías (real)", "origen": "invias",
        "descripcion": "Tramos de la Red Vial Nacional que cruzan La Guajira, tal como los publica INVIAS en datos.gov.co: "
                       "códigos de dominio sin traducir, \"Por Defnir\" donde falta el dato y la geometría completa "
                       "(hasta 14 mil vértices por tramo). En Plata: etiquetas legibles, sin tramos repetidos, recortada "
                       "a la caja de descarga y simplificada a 15 m.",
    },
    "invias_meta": {
        "titulo": "Metadatos de la descarga de vías", "icono": "info", "rol": "Trazabilidad (real)", "origen": "invias",
        "descripcion": "Fuente, licencia, fecha, caja de descarga y cuántos tramos del país se bajaron.",
    },
    "invias_reporte_calidad": {
        "titulo": "Reporte de calidad de vías", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "invias",
        "descripcion": "Tramos y vértices antes y después, tramos repetidos quitados y datos sin definir en la fuente.",
    },
    "clima_sintetico": {
        "titulo": "Clima simulado", "icono": "cloud-rain", "rol": "Amenaza externa (modelo ICT)",
        "descripcion": "Serie diaria simulada por estación: precipitación, temperatura y viento. "
                       "Es la que alimenta el criterio climático del ICT; no proviene del IDEAM.",
        "generacion": "5 estaciones × 120 días en lugares aleatorios de tierra firme. Se planta un evento de lluvia extrema "
                      "(+60 a 120 mm) cerca del final de la serie para que existan alertas climáticas recientes.",
    },
    "ideam_estaciones": {
        "titulo": "Estaciones del IDEAM", "icono": "radio-tower", "rol": "Catálogo (real)", "origen": "ideam",
        "descripcion": "Catálogo Nacional de Estaciones del IDEAM filtrado a La Guajira: código, nombre, categoría, "
                       "tecnología, estado, municipio, coordenadas y altitud. Incluye estaciones activas, en "
                       "mantenimiento y suspendidas.",
    },
    "ideam_precipitacion": {
        "titulo": "Lecturas de precipitación (crudas)", "icono": "cloud-rain", "rol": "Lecturas (real)", "origen": "ideam",
        "descripcion": "Lecturas de lluvia tal como las entrega el IDEAM, cada ~10 minutos (~2 minutos en la estación "
                       "del aeropuerto de Riohacha), de los últimos 30 días. Se guardan sin tocar, con duplicados y "
                       "como texto.",
    },
    "ideam_precip_diaria": {
        "titulo": "Precipitación diaria por estación", "icono": "calendar", "rol": "Lecturas limpias (real)", "origen": "ideam",
        "descripcion": "Lluvia diaria en mm por estación, calculada como la suma de las lecturas del día luego de "
                       "quitar duplicados y valores imposibles. Incluye cuántas lecturas y horas con dato tuvo cada día.",
    },
    "ideam_variables": {
        "titulo": "Otras variables (crudas)", "icono": "thermometer", "rol": "Lecturas (real)", "origen": "ideam",
        "descripcion": "Temperatura del aire (media, máxima y mínima), humedad, viento (velocidad y dirección), presión y "
                       "nivel del río de los últimos 30 días, cada una de su conjunto de datos abiertos. Se guardan tal "
                       "como llegan, con una columna que dice de qué conjunto vino cada fila.",
    },
    "ideam_variables_diaria": {
        "titulo": "Otras variables por día", "icono": "calendar", "rol": "Lecturas limpias (real)", "origen": "ideam",
        "descripcion": "Un valor por estación, variable y día (media, mínimo y máximo). Clasifica cada lectura por su "
                       "sensor (el conjunto de humedad trae también humedad del suelo), quita duplicados y valores "
                       "fuera de rango, unifica unidades y promedia la dirección del viento como vector.",
    },
    "ideam_ultimas_horas": {
        "titulo": "Lecturas de las últimas horas", "icono": "activity", "rol": "Casi en tiempo real (real)", "origen": "ideam",
        "descripcion": "Flujo del IDEAM con las lecturas de las últimas ~12 horas de todas las variables. Es lo que el "
                       "mapa muestra como valor de ahora; el backend lo consulta en vivo y guarda este respaldo por si "
                       "no hay internet.",
    },
    "ideam_radiacion": {
        "titulo": "Radiación solar (promedios)", "icono": "sun", "rol": "Climatología (real)", "origen": "ideam",
        "descripcion": "Radiación global media por estación: un valor para cada mes y el promedio anual, en Wh/m² por día. "
                       "El IDEAM la publica solo como promedio histórico, no como serie diaria.",
    },
    "ideam_normales": {
        "titulo": "Normales climatológicas", "icono": "chart-line", "rol": "Climatología (real)", "origen": "ideam",
        "descripcion": "Valor típico de cada mes (periodo 1991-2020) por estación y parámetro: precipitación, temperatura "
                       "media, máxima y mínima, humedad relativa, brillo solar, entre otros. Sirve para decir si un mes "
                       "va más seco o más lluvioso de lo normal.",
    },
    "clima_radiacion": {
        "titulo": "Estaciones con radiación", "icono": "sun", "rol": "Capa del mapa (real)", "origen": "ideam",
        "descripcion": "Un punto por estación con radiación media mensual y anual. Alimenta la vista de radiación del mapa.",
    },
    "ideam_meta": {
        "titulo": "Metadatos de la descarga", "icono": "info", "rol": "Trazabilidad (real)", "origen": "ideam",
        "descripcion": "Fuente, licencia, fecha de descarga, ventana de fechas y cuántas estaciones se sondearon, "
                       "descargaron o fallaron.",
    },
    "ideam_reporte_calidad": {
        "titulo": "Reporte de calidad del IDEAM", "icono": "clipboard-check", "rol": "Control de calidad (real)", "origen": "ideam",
        "descripcion": "Duplicados removidos, lecturas descartadas y estaciones que quedaron con lluvia diaria.",
    },
    "clima_estaciones": {
        "titulo": "Estaciones con clima", "icono": "map-pin", "rol": "Capa del mapa (real)", "origen": "ideam",
        "descripcion": "Un punto por estación que reportó: lluvia acumulada 7, 14 y 30 días, y para cada variable la última "
                       "lectura, el resumen de 30 días y su serie diaria, más las lecturas de las últimas horas y las "
                       "normales del mes. Alimenta la capa de clima del mapa.",
    },
    "reporte_calidad": {
        "titulo": "Reporte de calidad", "icono": "clipboard-check", "rol": "Control de calidad",
        "descripcion": "Resumen del paso Bronce a Plata: filas de entrada, duplicados removidos, "
                       "registros sin coordenadas y filas resultantes.",
    },
    "grid_calor": {
        "titulo": "Superficie de calor", "icono": "flame", "rol": "Resultado del modelo",
        "descripcion": "Grilla de puntos con la densidad kernel de los riesgos ponderada por severidad. "
                       "Alimenta el mapa de calor.",
    },
    "alertas": {
        "titulo": "Alertas", "icono": "triangle-alert", "rol": "Resultado del modelo",
        "descripcion": "Paquetes que cumplen alguna regla de escalamiento o de tendencia, con sus motivos.",
    },
    "validacion_backtest": {
        "titulo": "Validación: backtest", "icono": "target", "rol": "Validación",
        "descripcion": "ICT de cada paquete frente al número de riesgos que ya se materializaron.",
    },
    "validacion_sensibilidad": {
        "titulo": "Validación: sensibilidad", "icono": "sliders-horizontal", "rol": "Validación",
        "descripcion": "Cuánto cambia el ranking de paquetes si cada peso se mueve +/-20%.",
    },
}

COLUMNAS = {
    "id_riesgo": "Identificador del riesgo (RSK-0001). En Bronce los duplicados llevan el sufijo -DUP.",
    "id_evento_riesgo": "Identificador del evento de riesgo asociado.",
    "descripcion": "Descripción textual del riesgo.",
    "causa": "Causa registrada. En Plata los vacíos quedan como 'sin_causa_registrada'.",
    "categoria": "Una de 6 categorías. En Bronce llega con mayúsculas y espacios inconsistentes; Plata la normaliza.",
    "tipo": "amenaza u oportunidad (riesgo positivo).",
    "probabilidad": "Escala de 1 a 5.",
    "impacto": "Escala de 1 a 5.",
    "estado": "latente, proximo_a_materializarse o materializado.",
    "id_proyecto": "Proyecto al que pertenece.",
    "id_paquete_trabajo": "Paquete de trabajo al que pertenece (llave hacia paquetes).",
    "fecha_identificacion": "Fecha en que se identificó el riesgo.",
    "fecha_materializacion": "Fecha de materialización; vacía si no se ha materializado.",
    "accion_tratamiento": "Acción de tratamiento definida.",
    "fecha_ejecucion_accion": "Fecha comprometida de la acción. Si ya pasó y el riesgo sigue activo, la acción está vencida.",
    "lat": "Latitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida).",
    "lon": "Longitud (WGS84). En Bronce ~12 % viene vacía; en Plata se ubica en el centroide de su paquete (ver geolocalizacion_inferida).",
    "fuente": "Archivo de origen del registro (simula varios Excel dispersos).",
    "geolocalizacion_inferida": "Verdadero si la ubicación se tomó del centroide del paquete porque el registro no traía coordenadas.",
    "severidad": "probabilidad × impacto (1 a 25).",
    "id_paquete": "Identificador del paquete (PRY-01-PT03).",
    "nombre": "Nombre descriptivo.",
    "ruta_critica": "Si el paquete está en la ruta crítica del cronograma.",
    "id_comunidad": "Identificador de la comunidad.",
    "poblacion_aprox": "Población aproximada.",
    "conflictividad": "Índice de conflictividad social, 0 a 1.",
    "id_area": "Identificador del área protegida.",
    "sensibilidad": "Índice de sensibilidad ambiental, 0 a 1.",
    "id_cuerpo_agua": "Identificador del cuerpo de agua.",
    "id_via": "Identificador de la vía.",
    "id_estacion": "Estación meteorológica.",
    "fecha": "Día de la medición.",
    "precipitacion_mm": "Precipitación diaria en mm.",
    "temperatura_c": "Temperatura media en grados C.",
    "viento_kmh": "Velocidad del viento en km/h.",
    "celda_id": "Identificador de la celda de la grilla.",
    "intensidad": "Densidad kernel normalizada 0 a 1 (ponderada por severidad).",
    "severidad_riesgo": "Criterio normalizado 0 a 1: severidad agregada de las amenazas.",
    "exposicion_proyecto": "Criterio normalizado 0 a 1: ruta crítica y cantidad de riesgos.",
    "vulnerabilidad_territorial": "Criterio normalizado 0 a 1: cercanía a comunidades y áreas protegidas.",
    "amenazas_externas": "Criterio normalizado 0 a 1: lluvia acumulada en la estación más cercana.",
    "convergencia": "Criterio normalizado 0 a 1: categorías distintas de amenaza en el paquete.",
    "ICT": "Índice de Criticidad Territorial, 0 a 100.",
    "nivel": "bajo, medio, alto o crítico según los umbrales.",
    "indice_confianza": "Fracción de criterios con dato disponible (0 a 1).",
    "indice_oportunidad": "Índice equivalente al ICT calculado sobre las oportunidades, 0 a 100.",
    "escalamiento": "Verdadero si el paquete cumple alguna regla de escalamiento a crisis.",
    "causas_escalamiento": "Reglas que se cumplieron, separadas por punto y coma.",
    "ict_hace_ndias": "ICT recalculado con los datos de hace 7 días (mismos límites de normalización).",
    "tendencia_delta": "Cambio del ICT en los últimos 7 días.",
    "tendencia_alerta": "Verdadero si el ICT subió más que el umbral de tendencia.",
    "z_score": "Estadístico z de Getis-Ord Gi*.",
    "clasificacion": "Punto caliente, punto frío o sin patrón significativo (95%).",
    "filas_bronce": "Filas que llegaron en Bronce.",
    "duplicados_removidos": "Registros repetidos eliminados.",
    "sin_coordenadas_originales": "Registros sin lat/lon; se ubican por el centroide de su paquete.",
    "riesgos_sin_paquete_valido": "Registros que no se pudieron ubicar y se descartan.",
    "filas_plata": "Filas resultantes en Plata.",
    "n_riesgos_materializados": "Riesgos materializados dentro del paquete.",
    "criterio": "Criterio cuyo peso se perturba.",
    "variacion": "Perturbación aplicada al peso (+20% o -20%).",
    "correlacion_ranking_spearman": "Correlación de Spearman entre el ranking original y el perturbado.",
    "paquetes_que_cambian_de_nivel": "Paquetes que cambian de nivel con la perturbación.",
    "ict": "ICT del paquete en alerta.",
    "nombre_paquete": "Nombre del paquete.",
    "motivos": "Lista de reglas que dispararon la alerta.",
    "generada_en": "Fecha del corte que generó la alerta.",
}

COLUMNAS_IDEAM = {
    'codigo': 'Código de la estación (10 dígitos).',
    'categoria': 'Tipo de estación: pluviométrica, climatológica, sinóptica, etc.',
    'tecnologia': 'Convencional, automática, con telemetría, etc.',
    'departamento': 'Departamento.',
    'municipio': 'Municipio.',
    'ubicaci_n': 'Ubicación como la entrega el IDEAM. Trae latitud y longitud invertidas, por eso Plata no la usa.',
    'altitud': 'Altitud en metros sobre el nivel del mar.',
    'longitud': 'Longitud en grados decimales (WGS84).',
    'latitud': 'Latitud en grados decimales (WGS84).',
    'fecha_instalacion': 'Fecha de instalación (texto dd/mm/aaaa).',
    'fecha_suspension': 'Fecha de suspensión, si aplica.',
    'area_operativa': 'Área operativa del IDEAM.',
    'corriente': 'Corriente asociada.',
    'area_hidrografica': 'Área hidrográfica.',
    'zona_hidrografica': 'Zona hidrográfica.',
    'subzona_hidrografica': 'Subzona hidrográfica.',
    'entidad': 'Entidad propietaria de la estación.',
    'codigoestacion': 'Código de la estación (llave hacia el catálogo).',
    'codigosensor': 'Código del sensor: 0240 precipitación, 0257 precipitación por GPRS (mismo dato por otro canal).',
    'fechaobservacion': 'Fecha y hora de la lectura.',
    'valorobservado': 'Lluvia caída en el intervalo de la lectura, en mm (resolución típica de 0,2 mm).',
    'nombreestacion': 'Nombre de la estación tal como viene en la lectura.',
    'zonahidrografica': 'Zona hidrográfica.',
    'descripcionsensor': 'Descripción del sensor.',
    'unidadmedida': 'Unidad de medida (mm).',
    'dia': 'Día de la medición.',
    'mm': 'Lluvia del día en mm: suma de las lecturas sin duplicados.',
    'lecturas': 'Cantidad de lecturas distintas del día.',
    'horas_con_dato': 'Horas del día (0 a 24) que tuvieron al menos una lectura; indica qué tan completo es el día.',
    'estaciones_bronce': 'Estaciones que llegaron del catálogo.',
    'estaciones_fuera_de_la_caja': 'Estaciones con coordenadas fuera de La Guajira (descartadas).',
    'estaciones_plata': 'Estaciones que pasaron la validación.',
    'lecturas_bronce': 'Lecturas descargadas.',
    'lecturas_sin_fecha_o_valor': 'Lecturas sin fecha o sin valor (descartadas).',
    'lecturas_imposibles': 'Lecturas negativas o de más de 200 mm en un solo registro (descartadas).',
    'lecturas_plata': 'Lecturas que quedaron tras quitar duplicados.',
    'estaciones_con_lluvia_diaria': 'Estaciones con al menos un día de lluvia calculado.',
    'mm_7d': 'Lluvia acumulada en los últimos 7 días (mm).',
    'mm_14d': 'Lluvia acumulada en los últimos 14 días (mm).',
    'mm_30d': 'Lluvia acumulada en los últimos 30 días (mm).',
    'max_diario_mm': 'Mayor lluvia en un solo día de la ventana (mm).',
    'ultimo_dato': 'Fecha de la última lectura de la estación.',
    'dias_sin_dato': 'Días entre la última lectura de la estación y la más reciente de todas.',
    'dias_con_dato': 'Días de la ventana de 30 con al menos una lectura.',
    'cobertura': 'Fracción del tiempo de la ventana con datos (0 a 1). Con menos de 0,5 el acumulado puede estar subestimado.',
    'serie': 'Lluvia diaria de los 30 días de la ventana (lista de día y mm).',
    'fuente': 'Portal y conjuntos de datos de origen.',
    'licencia': 'Licencia de uso de los datos.',
    'descargado_en': 'Fecha y hora de la descarga.',
    'desde': 'Inicio de la ventana descargada.',
    'hasta': 'Fin de la ventana descargada.',
    'estaciones_sondeadas': 'Estaciones candidatas a las que se les pidió su última lectura.',
    'estaciones_con_datos_recientes': 'Estaciones que respondieron con datos recientes.',
    'estaciones_descargadas': 'Estaciones de las que se bajaron lecturas.',
    'estaciones_con_error': 'Estaciones cuya descarga falló.',
    'variable': 'Conjunto de datos de origen de la fila (temperatura, humedad, viento_vel...).',
    'var': 'Variable ya clasificada por su sensor: temperatura, temp_max, temp_min, humedad, humedad_suelo, viento_vel, viento_dir, presion, nivel_rio, precipitacion...',
    'media': 'Promedio del día (para la dirección del viento, promedio circular en grados).',
    'minimo': 'Menor lectura del día.',
    'maximo': 'Mayor lectura del día.',
    'unidad': 'Unidad ya unificada (°C, %, m/s, °, hPa, m, mm, Wh/m²/día).',
    'fecha_hora': 'Fecha y hora de la lectura.',
    'valor': 'Valor medido, ya limpio.',
    'estacion': 'Nombre de la estación.',
    'tipo_de_estacion': 'Automática o convencional.',
    'promedio_anual': 'Promedio anual de radiación global (Wh/m² por día).',
    'ene': 'Valor de enero.',
    'feb': 'Valor de febrero.',
    'mar': 'Valor de marzo.',
    'abr': 'Valor de abril.',
    'may': 'Valor de mayo.',
    'jun': 'Valor de junio.',
    'jul': 'Valor de julio.',
    'ago': 'Valor de agosto.',
    'sep': 'Valor de septiembre.',
    'oct': 'Valor de octubre.',
    'nov': 'Valor de noviembre.',
    'dic': 'Valor de diciembre.',
    'anual': 'Valor anual.',
    'periodo': 'Periodo de la normal (1991-2020).',
    'parametro': 'Parámetro climático tal como lo publica el IDEAM.',
    'parametro_clave': 'Parámetro ya mapeado a nuestra clave (precipitacion, temperatura_media, humedad_relativa...).',
    'altitud_m': 'Altitud en metros sobre el nivel del mar.',
    'variables': 'Por variable: unidad, última lectura, promedio de 24 h, mín/media/máx de 30 días, cobertura y serie diaria.',
    'ahora': 'Última lectura de cada variable en las últimas horas.',
    'normales': 'Normal climatológica mensual de la estación (lluvia, temperatura, humedad).',
    'radiacion': 'Radiación media mensual de la estación, si tiene sensor calibrado.',
    'meses': 'Doce valores mensuales (enero a diciembre).',
    'ult_bronce': 'Lecturas del flujo de últimas horas antes de la limpieza.',
    'ult_plata': 'Lecturas del flujo de últimas horas que quedaron.',
    'var_bronce': 'Lecturas de las otras variables descargadas.',
    'var_reasignadas_por_sensor': 'Lecturas cuyo sensor no correspondía al conjunto de origen (p. ej. humedad del suelo dentro del conjunto de humedad) y se reclasificaron.',
    'var_sensor_descartado': 'Lecturas de sensores que no usamos (nivel máximo/mínimo horario, etc.).',
    'var_sin_fecha_o_valor': 'Lecturas sin fecha o valor.',
    'var_fuera_de_rango': 'Lecturas fuera del rango físico posible (p. ej. -999).',
    'var_duplicados_removidos': 'Duplicados quitados (varios canales para el mismo sensor).',
    'var_plata': 'Lecturas que quedaron.',
    'var_estaciones': 'Estaciones con al menos una variable.',
    'ult_sensor_descartado': 'Lecturas de últimas horas de sensores que no usamos.',
    'ult_sin_fecha_o_valor': 'Sin fecha o valor.',
    'ult_fuera_de_rango': 'Fuera de rango físico.',
    'ult_duplicados_removidos': 'Duplicados.',
    'radiacion_registros': 'Estaciones con radiación en La Guajira.',
    'radiacion_con_estacion_en_catalogo': 'Las que se pudieron emparejar con el catálogo por nombre y municipio.',
    'normales_filas': 'Filas de normales climatológicas (una por estación, parámetro y periodo).',
    'normales_estaciones': 'Estaciones con normales.',
    'nombre': 'Nombre de la estación (en Plata sin el código entre corchetes ni el sufijo AUT).',
    'estado': 'Activa, en mantenimiento o suspendida.',
}

COLUMNAS_INVIAS = {
    'id_tramo': 'Identificador del tramo: ruta, código y número de orden.',
    'codigo_tramo': 'Código del tramo en INVIAS.',
    'ruta': 'Número de la ruta nacional.',
    'nombre_ruta': 'Nombre de la ruta (p. ej. Transversal del Caribe).',
    'nombre_tramo': 'Nombre del tramo (casi siempre "Por Defnir" en la fuente).',
    'sector': 'Sector del tramo (p. ej. Riohacha - Paraguachón).',
    'categoria_txt': 'Primer, segundo o tercer orden; vacío si la fuente dice por definir.',
    'administrador_txt': 'Quién administra el tramo (INVIAS, ANI...).',
    'superficie_txt': 'Pavimentada o sin pavimentar; en La Guajira la fuente la deja sin definir.',
    'calzada_txt': 'Sencilla o doble.',
    'territorial_txt': 'Territorial de INVIAS (no es el límite departamental).',
    'en_guajira': 'Verdadero si el tramo pertenece a la territorial Guajira.',
    'longitud_km': 'Longitud del tramo en km, recalculada en metros tras recortar y simplificar.',
    'tramos_en_el_pais': 'Tramos del conjunto completo.',
    'tramos_descargados': 'Tramos que cruzan la caja de descarga.',
    'vertices': 'Puntos de la geometría descargada.',
    'caja': 'Caja (lat/lon) usada para pedir solo La Guajira.',
    'dataset': 'Identificador del conjunto en datos.gov.co.',
    'tramos_bronce': 'Tramos descargados.',
    'vertices_bronce': 'Vértices descargados.',
    'sin_geometria': 'Tramos sin geometría (descartados).',
    'longitud_no_coincide': 'Tramos cuya longitud calculada difiere más de 5 % de la que trae la fuente.',
    'repetidos_removidos': 'Tramos cuya geometría ya estaba cubierta por otros (una geometría suma dos tramos).',
    'nombre_tramo_por_definir': 'Tramos con nombre "Por Defnir".',
    'superficie_por_definir': 'Tramos sin tipo de superficie.',
    'categoria_por_definir': 'Tramos sin categoría.',
    'tramos_plata': 'Tramos que quedan en Plata.',
    'vertices_plata': 'Vértices tras simplificar.',
    'km_plata': 'Kilómetros en Plata (incluye tramos de otras territoriales).',
    'tramos_oro': 'Tramos de la territorial Guajira.',
    'km_oro': 'Kilómetros de la territorial Guajira.',
    'km': 'Kilómetros de la capa.',
    'rutas': 'Rutas nacionales que la componen.',
}

COLUMNAS_HIDROGRAFIA = {
    'id_objeto': 'Identificador: tipo de objeto y número de objeto en el servicio del IGAC.',
    'objectid': 'Número de objeto en el servicio del IGAC.',
    'nombre_geografico': 'Nombre geográfico tal como viene (a veces sin tildes o con espacios de más).',
    'estado_drenaje': '5101 cauce permanente, 5102 cauce intermitente (dominio del IGAC).',
    'tipo': 'drenaje_sencillo, drenaje_doble, cienaga, laguna o embalse.',
    'estado': 'Permanente o intermitente, según la clasificación del IGAC a 1:100.000 (no es una medición de caudal).',
    'area_km2': 'Área del polígono en km², calculada en metros (EPSG:3116).',
    'capa_servicio': 'Número de la capa en el servicio ArcGIS.',
    'servicio': 'Dirección del servicio de origen.',
    'objetos': 'Objetos descargados.',
    'capas': 'Por capa: título, objetos y vértices descargados.',
    'objetos_bronce': 'Objetos descargados.',
    'objetos_plata': 'Objetos que quedan en Plata.',
    'geometrias_invalidas_reparadas': 'Geometrías inválidas que se repararon.',
    'sin_nombre': 'Objetos sin nombre geográfico.',
    'lineas_sin_estado': 'Líneas sin estado de cauce.',
    'km_rios': 'Kilómetros de cauce en la caja (incluye zonas de Cesar, Magdalena y frontera).',
    'km_permanentes': 'Kilómetros de cauce permanente.',
    'km_intermitentes': 'Kilómetros de cauce intermitente.',
    'km2_cuerpos_de_agua': 'Área de ríos anchos, ciénagas, lagunas y embalses.',
    'rios_oro': 'Tramos de río en Oro.',
    'cuerpos_agua_oro': 'Polígonos de agua en Oro.',
    'longitud_km': 'Longitud del tramo en km, calculada en metros (EPSG:3116).',
    'vertices_bronce': 'Vértices descargados.',
    'vertices_plata': 'Vértices tras simplificar.',
    'sin_geometria': 'Objetos sin geometría (descartados).',
    'caja': 'Caja (lat/lon) usada para pedir solo La Guajira.',
    'nombre': 'Nombre del río, arroyo o cuerpo de agua, normalizado (vacío si no tiene).',
}

COLUMNAS_MUNICIPIOS = {
    "codigo": "Código DANE (departamento + municipio, 5 dígitos).",
    "nombre": "Nombre propio del municipio (el DANE lo escribe en mayúsculas y sin tildes).",
    "area_km2": "Área calculada en metros (EPSG:3116), en km².",
    "cabecera_lon": "Longitud de la cabecera municipal (DIVIPOLA).", "cabecera_lat": "Latitud de la cabecera municipal (DIVIPOLA).",
    "etiqueta_lon": "Longitud de un punto dentro del polígono donde se escribe el nombre en el mapa.",
    "etiqueta_lat": "Latitud de ese punto.",
    "estaciones_catalogo": "Estaciones del catálogo del IDEAM ubicadas dentro del polígono.",
    "estaciones_con_datos": "Estaciones con datos recientes (las del mapa de clima) dentro del polígono.",
    "km_vias_nacionales": "Kilómetros de la red vial nacional (INVIAS) que pasan por el municipio.",
    "km_vias": "Kilómetros de la red vial unificada (INVIAS + IGAC, sin duplicados) dentro del municipio.",
    "km_vias_solo_tiempo_seco": "De esos, los que solo se transitan en tiempo seco (según el IGAC).",
    "cod_dpto": "Código del departamento.", "dpto": "Departamento.", "cod_mpio": "Código DANE del municipio.",
    "nom_mpio": "Nombre del municipio en DIVIPOLA.", "tipo_municipio": "Municipio o área no municipalizada.",
    "longitud": "Longitud de la cabecera (coma decimal en la fuente).", "latitud": "Latitud de la cabecera (coma decimal en la fuente).",
    "DPTO_CCDGO": "Código del departamento.", "MPIO_CCDGO": "Código del municipio dentro del departamento.",
    "MPIO_CNMBR": "Nombre del municipio (mayúsculas, sin tildes).", "MPIO_NAREA": "Área oficial en m² según la fuente.",
    "MPIO_NANO": "Año de la versión de la geometría.", "DEPTO": "Departamento.", "MUNICIPIO": "Municipio.",
    "COD_DEP_MP": "Código DANE de 5 dígitos.",
    "fuente": "Fuente de los datos.", "licencia": "Licencia o condición de uso.", "servicio": "Servicio de origen.",
    "version_geometria": "Versión de la cartografía.", "divipola": "Conjunto DIVIPOLA usado para nombres y cabeceras.",
    "descargado_en": "Fecha y hora de la descarga.", "municipios": "Municipios descargados.", "divipola_filas": "Filas de DIVIPOLA.",
    "municipios_bronce": "Municipios descargados.", "vertices_bronce": "Vértices descargados.",
    "geometrias_invalidas": "Geometrías inválidas (se repararon).",
    "sin_divipola": "Municipios sin fila en DIVIPOLA.", "nombre_distinto_en_divipola": "Municipios cuyo nombre difiere del DIVIPOLA.",
    "diferencia_maxima_de_area_km2": "Mayor diferencia entre el área calculada y la que trae la fuente.",
    "partes_del_departamento": "Partes en que queda la unión (1 = territorio continuo).",
    "huecos_entre_municipios": "Huecos dentro de la unión (1 ya viene en el dato del DANE).",
    "municipios_plata": "Municipios que quedan.", "vertices_plata": "Vértices tras simplificar.",
    "km2_departamento": "Área total de La Guajira.",
    "estaciones_fuera_de_la_guajira": "Estaciones del catálogo que caen fuera de los 15 polígonos (casi todas en la costa o el mar).",
    "estaciones_en_otro_municipio_que_el_declarado": "Estaciones cuyo municipio en el catálogo no coincide con el polígono donde caen.",
    "estaciones_catalogo_total": "Estaciones del catálogo.",
    "km_vias_en_municipios": "Kilómetros de la red vial unificada dentro de los municipios.",
    "km_vias_fuera_del_limite": "Kilómetros de vías que quedan fuera (por el margen de simplificación).",
}

COLUMNAS_VIAS_IGAC = {
    "id_via": "Identificador: tipo de vía, número de objeto y parte (un recorte puede dejar varias).",
    "tipo": "1 a 7: 1 pavimentada de 2 o más carriles, 2 sin pavimentar de 2 o más, 3 pavimentada angosta, 4 sin pavimentar angosta, 5 sin pavimentar solo en tiempo seco, 6 sin afirmar (trocha), 7 camino o sendero.",
    "tipo_via": "Tipo de vía tal como viene (1 a 7).",
    "clase": "Nombre de la clase según la combinación de atributos de cada tipo.",
    "superficie": "Pavimentada, sin pavimentar, en construcción o sin afirmar.",
    "carriles": "2 o más carriles, o angosta.",
    "accesibilidad": "Todo el año, o solo en tiempo seco (puede quedar intransitable con lluvia).",
    "nombre": "Nombre de la vía; casi ninguna lo tiene (4 de 5.600).",
    "km": "Longitud recalculada en metros (EPSG:3116) tras recortar y simplificar.",
    "objectid": "Número de objeto en el servicio del IGAC.",
    "estado_superficie": "Código de superficie: 3301 pavimentada, 3306 sin pavimentar, 3350 sin afirmar, 1302 en construcción.",
    "numero_carriles": "Código de ancho: 3501 dos o más carriles, 3502 angosta.",
    "accesibilidad_codigo": "Código: 3600 todo el año, 3601 solo en tiempo seco.",
    "nombre_geografico": "Nombre geográfico tal como viene.", "eje_vial": "Eje vial al que pertenece.",
    "fuente": "Fuente de los datos.", "licencia": "Licencia o condición de uso.", "servicio": "Servicio de origen.",
    "descargado_en": "Fecha y hora de la descarga.", "caja": "Caja (lat/lon) usada para pedir solo La Guajira.",
    "capas": "Por capa: título, objetos y vértices descargados.", "recortada_a": "Límite usado para recortar.",
    "objetos_bronce": "Objetos descargados.", "vertices_bronce": "Vértices descargados.",
    "sin_geometria": "Objetos sin geometría.", "tipo_desconocido": "Objetos con un tipo fuera de 1 a 7.",
    "atributos_sin_valor": "Vías de tipo 1 a 6 sin superficie en la fuente.",
    "objetos_plata": "Objetos que quedan.", "vertices_plata": "Vértices tras recortar y simplificar.",
    "km_total": "Kilómetros de vías dentro de La Guajira.", "km_pavimentadas": "Kilómetros pavimentados (tipos 1 y 3).",
    "km_solo_tiempo_seco": "Kilómetros que solo se transitan en tiempo seco.", "km_caminos": "Kilómetros de caminos y senderos.",
}

COLUMNAS_RED_VIAL = {
    "id_tramo": "Identificador: fuente y número de tramo.", "fuente": "INVIAS (red nacional) o IGAC (red complementaria).",
    "grupo": "Red nacional o Red complementaria.",
    "estilo": "Clave de dibujo: n0 a n2 (categorías de INVIAS) e i1 a i7 (clases del IGAC).",
    "clase": "Clase de vía: categoría de INVIAS o clase interpretada del IGAC.",
    "ruta": "Número de la ruta nacional (solo INVIAS).", "nombre_ruta": "Nombre de la ruta (solo INVIAS).",
    "sector": "Sector del tramo (solo INVIAS).", "administrador": "Quién administra el tramo (solo INVIAS).",
    "calzada": "Sencilla o doble (solo INVIAS).",
    "superficie": "Pavimentada, sin pavimentar... En INVIAS, tomada del IGAC sobre el mismo trazado.",
    "superficie_fuente": "De dónde sale la superficie: INVIAS, IGAC o IGAC (cruce espacial).",
    "carriles": "2 o más carriles, o angosta (solo IGAC).",
    "accesibilidad": "Todo el año o solo en tiempo seco (solo IGAC).", "nombre": "Nombre de la vía, si lo tiene.",
    "km": "Longitud del tramo en km, recalculada en metros.",
    "fuentes": "Fuentes y licencias de cada red.", "km_nacional": "Kilómetros de la red nacional.",
    "km_complementaria": "Kilómetros de la red complementaria.",
    "tramos_invias": "Tramos de INVIAS de entrada.", "tramos_igac": "Tramos del IGAC de entrada.",
    "km_invias": "Kilómetros de INVIAS.", "km_igac": "Kilómetros del IGAC antes de quitar lo repetido.",
    "tramos_invias_con_superficie_del_igac": "Tramos de INVIAS que recibieron superficie del IGAC.",
    "km_igac_repetido_con_invias": "Kilómetros del IGAC a menos de 50 m de una vía de INVIAS (se quitaron).",
    "km_igac_astillas_quitadas": "Kilómetros en pedazos menores a 100 m junto a la red nacional (se quitaron).",
    "tramos_red": "Tramos de la red unificada.", "vertices_red": "Vértices de la red unificada.",
    "km_red": "Kilómetros totales.", "km_red_nacional": "Kilómetros de la red nacional.",
    "km_red_complementaria": "Kilómetros de la red complementaria.", "km_solo_tiempo_seco": "Kilómetros que solo se transitan en tiempo seco.",
}

COLUMNAS_POR_DATASET = {
    "red_vial": COLUMNAS_RED_VIAL, "red_vial_reporte_calidad": COLUMNAS_RED_VIAL,
    "igac_vias_crudas": COLUMNAS_VIAS_IGAC, "vias_igac_meta": COLUMNAS_VIAS_IGAC, "igac_vias": COLUMNAS_VIAS_IGAC,
    "vias_igac_reporte_calidad": COLUMNAS_VIAS_IGAC,
    "ideam_estaciones": COLUMNAS_IDEAM, "ideam_precipitacion": COLUMNAS_IDEAM, "ideam_precip_diaria": COLUMNAS_IDEAM,
    "ideam_meta": {**COLUMNAS_IDEAM, "lecturas": "Lecturas descargadas."}, "ideam_reporte_calidad": COLUMNAS_IDEAM, "clima_estaciones": COLUMNAS_IDEAM,
    "ideam_variables": COLUMNAS_IDEAM, "ideam_variables_diaria": COLUMNAS_IDEAM, "ideam_variables_horaria": COLUMNAS_IDEAM, "ideam_ultimas_horas": COLUMNAS_IDEAM,
    "dane_municipios": COLUMNAS_MUNICIPIOS, "divipola_municipios": COLUMNAS_MUNICIPIOS, "municipios_meta": COLUMNAS_MUNICIPIOS,
    "municipios": COLUMNAS_MUNICIPIOS, "limite_departamental": COLUMNAS_MUNICIPIOS, "municipios_reporte_calidad": COLUMNAS_MUNICIPIOS, "municipios_reporte_cruces": COLUMNAS_MUNICIPIOS,
    "igac_drenaje_sencillo": COLUMNAS_HIDROGRAFIA, "igac_drenaje_doble": COLUMNAS_HIDROGRAFIA, "igac_cienagas": COLUMNAS_HIDROGRAFIA,
    "igac_embalses": COLUMNAS_HIDROGRAFIA, "igac_lagunas": COLUMNAS_HIDROGRAFIA, "hidrografia_meta": COLUMNAS_HIDROGRAFIA,
    "igac_hidrografia": COLUMNAS_HIDROGRAFIA, "hidrografia_reporte_calidad": COLUMNAS_HIDROGRAFIA,
    "rios": COLUMNAS_HIDROGRAFIA, "cuerpos_agua": COLUMNAS_HIDROGRAFIA,
    "invias_red_vial": COLUMNAS_INVIAS, "invias_meta": COLUMNAS_INVIAS, "invias_reporte_calidad": COLUMNAS_INVIAS,
    "ideam_radiacion": COLUMNAS_IDEAM, "ideam_normales": COLUMNAS_IDEAM, "clima_radiacion": COLUMNAS_IDEAM,
    "clima_sintetico": {"lat": "Latitud de la estación simulada (WGS84).", "lon": "Longitud de la estación simulada (WGS84)."},
    "areas": {"categoria": "Tipo de área protegida (ficticia)."},
    "vias": {"tipo": "primaria, secundaria o terciaria de difícil acceso."},
    "validacion_backtest": {"ICT": "ICT del paquete en el corte actual.", "nivel": "Nivel del paquete."},
}

FORMATOS = {".xlsx": "Excel", ".csv": "CSV", ".parquet": "Parquet", ".geojson": "GeoJSON", ".json": "JSON"}

GEOMETRIAS = {"Point": "Puntos", "Polygon": "Polígonos", "LineString": "Líneas", "MultiPolygon": "Polígonos"}


def _tipo_amigable(serie: pd.Series) -> str:
    if serie.name == "geometry":
        return "geometria"
    d = serie.dtype
    if pd.api.types.is_bool_dtype(d):
        return "booleano"
    if pd.api.types.is_integer_dtype(d):
        return "entero"
    if pd.api.types.is_float_dtype(d):
        return "decimal"
    if pd.api.types.is_datetime64_any_dtype(d):
        return "fecha"
    no_nulos = serie.dropna()
    if len(no_nulos) and hasattr(no_nulos.iloc[0], "isoformat"):
        return "fecha"
    if len(no_nulos) and isinstance(no_nulos.iloc[0], list):
        return "lista"
    return "texto"


def _leer(ruta: Path) -> pd.DataFrame:
    if ruta.suffix == ".geojson":
        return gpd.read_file(ruta)
    if ruta.suffix == ".xlsx":
        return pd.read_excel(ruta)
    if ruta.suffix == ".csv":
        return pd.read_csv(ruta)
    if ruta.suffix == ".parquet":
        return pd.read_parquet(ruta)
    if ruta.suffix == ".json":
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        # un JSON de un solo objeto (metadatos) cuenta como una fila
        return pd.json_normalize(contenido) if isinstance(contenido, dict) else pd.DataFrame(contenido)
    raise ValueError(ruta)


def _describir_tabla(ruta: Path) -> dict:
    df = _leer(ruta)
    dataset = ARCHIVO_A_DATASET.get(ruta.name, ruta.stem)
    geom = None
    if isinstance(df, gpd.GeoDataFrame) and len(df):
        tipos = df.geom_type.dropna().unique().tolist()
        geom = GEOMETRIAS.get(tipos[0], tipos[0]) if tipos else None
    overrides = COLUMNAS_POR_DATASET.get(dataset, {})
    columnas = [
        {
            "nombre": c,
            "tipo": _tipo_amigable(df[c]),
            "nulos": int(df[c].isna().sum()) if c != "geometry" else 0,
            "descripcion": overrides.get(c) or COLUMNAS.get(c) or (
                "Puntos que aporta el criterio al ICT (peso × valor normalizado × 100)." if c.endswith("_contrib") else ""),
        }
        for c in df.columns if c != "geometry"
    ]
    return {
        "archivo": ruta.name,
        "dataset": dataset,
        "formato": FORMATOS.get(ruta.suffix, ruta.suffix),
        "filas": int(len(df)),
        "geometria": geom,
        "columnas": columnas,
    }


def _validacion() -> dict:
    out = {}
    bt = ORO / "validacion_backtest.csv"
    if bt.exists():
        df = pd.read_csv(bt)
        rho, _ = spearmanr(df["ICT"], df["n_riesgos_materializados"])
        top = df.sort_values("ICT", ascending=False).head(max(1, round(len(df) * 0.3)))
        out["backtest"] = {
            "spearman": round(float(rho), 2),
            "top_k": int(len(top)),
            "precision_top": round(float((top["n_riesgos_materializados"] > 0).mean()), 2),
        }
    sens = ORO / "validacion_sensibilidad.csv"
    if sens.exists():
        df = pd.read_csv(sens)
        out["sensibilidad"] = {
            "spearman_min": round(float(df["correlacion_ranking_spearman"].min()), 3),
            "max_cambios_nivel": int(df["paquetes_que_cambian_de_nivel"].max()),
            "criterio_mas_sensible": str(df.loc[df["correlacion_ranking_spearman"].idxmin(), "criterio"]),
        }
    return out


def _ideam() -> dict:
    """Cifras de la ultima descarga del IDEAM (vacio si aun no se hizo)."""
    out: dict = {}
    meta = BRONCE / "ideam_meta.json"
    if meta.exists():
        out["meta"] = json.loads(meta.read_text(encoding="utf-8"))
    rep = PLATA / "reporte_calidad_ideam.csv"
    if rep.exists():
        out["calidad"] = {k: int(v) for k, v in pd.read_csv(rep).iloc[0].to_dict().items()}
    est = BRONCE / "ideam_estaciones.csv"
    if est.exists():
        e = pd.read_csv(est, dtype=str)
        out["catalogo"] = {"estaciones": int(len(e)), "por_estado": e["estado"].value_counts().to_dict()}
    oro = ORO / "clima_estaciones.geojson"
    if oro.exists():
        g = json.loads(oro.read_text(encoding="utf-8"))
        out["oro"] = {"estaciones": len(g["features"]), **(g.get("metadata") or {})}
    return out


_cache: dict = {"firma": None, "valor": None}


def _firma() -> tuple:
    return tuple(sorted((str(p), p.stat().st_mtime) for _, _, d in CAPAS for p in d.iterdir() if p.is_file()))


def construir_catalogo() -> dict:
    firma = _firma()
    if _cache["firma"] == firma:
        return _cache["valor"]

    capas = []
    for clave, nombre, carpeta in CAPAS:
        tablas = [_describir_tabla(p) for p in sorted(carpeta.iterdir()) if p.suffix in FORMATOS]
        capas.append({"id": clave, "nombre": nombre, "tablas": tablas})

    calidad = {}
    rep = PLATA / "reporte_calidad_bronce_a_plata.csv"
    if rep.exists():
        calidad = {k: int(v) for k, v in pd.read_csv(rep).iloc[0].to_dict().items()}

    valor = {"capas": capas, "datasets": DATASETS, "calidad": calidad, "validacion": _validacion(), "ideam": _ideam()}
    _cache.update(firma=firma, valor=valor)
    return valor
