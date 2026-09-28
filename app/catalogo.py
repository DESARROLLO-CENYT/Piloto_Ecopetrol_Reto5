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

from config import BRONCE, ORO, PLATA

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
    "clima_ideam.csv": "clima",
    "clima.parquet": "clima",
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
        "generacion": "14 círculos (4 a 6 por proyecto) dentro de cada proyecto; ~30% marcados como ruta crítica.",
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
        "generacion": "3 proyectos ficticios (Norte, Centro, Sur) ubicados dentro del marco geográfico de La Guajira.",
    },
    "comunidades": {
        "titulo": "Comunidades", "icono": "users", "rol": "Vulnerabilidad",
        "descripcion": "Asentamientos con población aproximada e índice de conflictividad social.",
        "generacion": "18 puntos aleatorios con nombres genéricos; conflictividad sesgada a valores bajos (Beta 2,5).",
    },
    "areas": {
        "titulo": "Áreas protegidas", "icono": "trees", "rol": "Vulnerabilidad",
        "descripcion": "Áreas de interés ambiental con un índice de sensibilidad.",
        "generacion": "6 círculos con categorías ficticias (parque, reserva, humedal) y sensibilidad 0.4 a 1.",
    },
    "hidro": {
        "titulo": "Hidrología", "icono": "waves", "rol": "Contexto",
        "descripcion": "Cuerpos de agua (arroyos) como líneas.",
        "generacion": "8 líneas quebradas generadas con pasos aleatorios.",
    },
    "vias": {
        "titulo": "Vías", "icono": "route", "rol": "Contexto",
        "descripcion": "Red vial por tipo (primaria, secundaria, terciaria de difícil acceso).",
        "generacion": "10 segmentos rectos con tipo aleatorio.",
    },
    "clima": {
        "titulo": "Clima diario (tipo IDEAM)", "icono": "cloud-rain", "rol": "Amenaza externa",
        "descripcion": "Serie diaria por estación: precipitación, temperatura y viento.",
        "generacion": "5 estaciones × 120 días. Se planta un evento de lluvia extrema (+60 a 120 mm) "
                      "cerca del final de la serie para que existan alertas climáticas recientes.",
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
    "lat": "Latitud (WGS84). ~12% vacía en Bronce.",
    "lon": "Longitud (WGS84). ~12% vacía en Bronce.",
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

COLUMNAS_POR_DATASET = {
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
        return pd.DataFrame(json.loads(ruta.read_text(encoding="utf-8")))
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

    valor = {"capas": capas, "datasets": DATASETS, "calidad": calidad, "validacion": _validacion()}
    _cache.update(firma=firma, valor=valor)
    return valor
