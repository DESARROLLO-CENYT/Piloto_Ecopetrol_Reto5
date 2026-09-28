"""
Motor del Indice de Criticidad Territorial (ICT) - piloto con datos sinteticos.

Implementa el calculo descrito en la Seccion 6 de la propuesta:
normalizacion de criterios, decaimiento por distancia, agregacion por
paquete de trabajo, ponderacion configurable y clasificacion en niveles.

Todas las funciones reciben datos ya proyectados a un CRS metrico
(config.CRS_METRICO) cuando trabajan con distancias, para que los radios
de influencia (en metros) sean correctos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------

def decaimiento_lineal(distancia_m: np.ndarray, radio_m: float) -> np.ndarray:
    """1.0 en distancia=0, decrece linealmente a 0.0 en distancia=radio."""
    valor = 1.0 - np.asarray(distancia_m, dtype=float) / radio_m
    return np.clip(valor, 0.0, 1.0)


def normalizar_minmax(serie: pd.Series) -> pd.Series:
    if serie.empty:
        return serie
    minimo, maximo = serie.min(), serie.max()
    if maximo == minimo:
        return pd.Series(0.0, index=serie.index)
    return (serie - minimo) / (maximo - minimo)


def saturar(valor, maximo) -> float:
    return float(min(valor / maximo, 1.0)) if maximo else 0.0


def estado_efectivo(row: pd.Series, fecha_corte: pd.Timestamp) -> str | None:
    """Estado de un riesgo tal como se veria en `fecha_corte` (para backtest/tendencia).

    Devuelve None si el riesgo aun no habia sido identificado en esa fecha.
    """
    if pd.isna(row["fecha_identificacion"]) or row["fecha_identificacion"] > fecha_corte:
        return None
    if pd.notna(row["fecha_materializacion"]) and row["fecha_materializacion"] <= fecha_corte:
        return "materializado"
    if row["estado"] == "materializado":
        # se materializara despues de fecha_corte -> en esa fecha aun no lo estaba
        return "proximo_a_materializarse"
    return row["estado"]


# ---------------------------------------------------------------------------
# Criterio 1: severidad de los riesgos (amenazas) por paquete de trabajo
# ---------------------------------------------------------------------------

def severidad_por_paquete(
    df_riesgos: pd.DataFrame,
    factores_estado: dict,
    peso_maximo: float,
    peso_promedio: float,
    fecha_corte: pd.Timestamp | None = None,
) -> pd.Series:
    """Agrega la severidad de las AMENAZAS de cada paquete de trabajo.

    regla: severidad_paquete = max(severidad_ajustada) * peso_maximo
                              + promedio_ponderado(severidad_ajustada) * peso_promedio
    severidad_ajustada = probabilidad * impacto * factor_estado(estado)
    """
    df = df_riesgos[df_riesgos["tipo"] == "amenaza"].copy()
    if fecha_corte is not None:
        df["estado_calc"] = df.apply(lambda r: estado_efectivo(r, fecha_corte), axis=1)
        df = df[df["estado_calc"].notna()]
    else:
        df["estado_calc"] = df["estado"]

    df["factor_estado"] = df["estado_calc"].map(factores_estado).fillna(1.0)
    df["severidad_ajustada"] = df["probabilidad"] * df["impacto"] * df["factor_estado"]

    def agregar(grupo: pd.DataFrame) -> float:
        maximo = grupo["severidad_ajustada"].max()
        promedio = np.average(grupo["severidad_ajustada"], weights=grupo["severidad_ajustada"])
        return maximo * peso_maximo + promedio * peso_promedio

    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("id_paquete_trabajo").apply(agregar, include_groups=False)


# ---------------------------------------------------------------------------
# Criterio 2: exposicion del proyecto
# ---------------------------------------------------------------------------

def exposicion_por_paquete(gdf_paquetes: gpd.GeoDataFrame, conteo_riesgos: pd.Series) -> pd.Series:
    """Combina si el paquete es de ruta critica con la densidad de riesgos que recibe."""
    conteo_norm = normalizar_minmax(conteo_riesgos.reindex(gdf_paquetes["id_paquete"]).fillna(0))
    ruta_critica = gdf_paquetes.set_index("id_paquete")["ruta_critica"].astype(float)
    exposicion = 0.6 * ruta_critica + 0.4 * conteo_norm
    return exposicion


# ---------------------------------------------------------------------------
# Criterio 3: vulnerabilidad territorial (comunidades + areas protegidas)
# ---------------------------------------------------------------------------

def vulnerabilidad_por_paquete(
    centroides_paquetes_m: gpd.GeoSeries,
    gdf_comunidades_m: gpd.GeoDataFrame,
    gdf_areas_m: gpd.GeoDataFrame,
    radio_comunidad_m: float,
    radio_area_m: float,
) -> pd.Series:
    resultado = {}
    for id_paquete, centro in centroides_paquetes_m.items():
        dist_com = gdf_comunidades_m.geometry.distance(centro).to_numpy()
        score_com = decaimiento_lineal(dist_com, radio_comunidad_m) * gdf_comunidades_m["conflictividad"].to_numpy()
        valor_com = min(score_com.sum(), 1.0) if len(score_com) else 0.0

        dist_area = gdf_areas_m.geometry.distance(centro).to_numpy()
        score_area = decaimiento_lineal(dist_area, radio_area_m) * gdf_areas_m["sensibilidad"].to_numpy()
        valor_area = min(score_area.sum(), 1.0) if len(score_area) else 0.0

        resultado[id_paquete] = 0.5 * valor_com + 0.5 * valor_area
    return pd.Series(resultado)


# ---------------------------------------------------------------------------
# Criterio 4: amenazas externas (clima)
# ---------------------------------------------------------------------------

def amenazas_externas_por_paquete(
    centroides_paquetes_m: gpd.GeoSeries,
    gdf_estaciones_m: gpd.GeoDataFrame,
    df_clima: pd.DataFrame,
    precipitacion_extrema_mm: float,
    ventana_dias: int,
    fecha_corte: pd.Timestamp,
) -> pd.Series:
    fecha_ini = fecha_corte - pd.Timedelta(days=ventana_dias)
    clima_ventana = df_clima[(pd.to_datetime(df_clima["fecha"]) > fecha_ini) & (pd.to_datetime(df_clima["fecha"]) <= fecha_corte)]
    precip_por_estacion = clima_ventana.groupby("id_estacion")["precipitacion_mm"].sum()

    resultado = {}
    for id_paquete, centro in centroides_paquetes_m.items():
        # estacion mas cercana
        distancias = gdf_estaciones_m.geometry.distance(centro)
        id_estacion_cercana = gdf_estaciones_m.loc[distancias.idxmin(), "id_estacion"]
        precip_acumulada = precip_por_estacion.get(id_estacion_cercana, 0.0)
        resultado[id_paquete] = saturar(precip_acumulada, precipitacion_extrema_mm)
    return pd.Series(resultado)


# ---------------------------------------------------------------------------
# Criterio 5: convergencia de amenazas
# ---------------------------------------------------------------------------

def convergencia_por_paquete(df_riesgos: pd.DataFrame, categorias_para_saturar: int, fecha_corte: pd.Timestamp | None = None) -> pd.Series:
    df = df_riesgos[df_riesgos["tipo"] == "amenaza"].copy()
    if fecha_corte is not None:
        df["estado_calc"] = df.apply(lambda r: estado_efectivo(r, fecha_corte), axis=1)
        df = df[df["estado_calc"].notna()]
    if df.empty:
        return pd.Series(dtype=float)
    n_categorias = df.groupby("id_paquete_trabajo")["categoria"].nunique()
    return n_categorias.apply(lambda n: saturar(n, categorias_para_saturar))


# ---------------------------------------------------------------------------
# Indice de oportunidad (misma estructura, sobre tipo == 'oportunidad')
# ---------------------------------------------------------------------------

def indice_oportunidad_por_paquete(df_riesgos: pd.DataFrame, peso_maximo: float, peso_promedio: float) -> pd.Series:
    df = df_riesgos[df_riesgos["tipo"] == "oportunidad"].copy()
    if df.empty:
        return pd.Series(dtype=float)
    df["severidad_ajustada"] = df["probabilidad"] * df["impacto"]

    def agregar(grupo: pd.DataFrame) -> float:
        maximo = grupo["severidad_ajustada"].max()
        promedio = np.average(grupo["severidad_ajustada"], weights=grupo["severidad_ajustada"])
        return maximo * peso_maximo + promedio * peso_promedio

    crudo = df.groupby("id_paquete_trabajo").apply(agregar, include_groups=False)
    return (normalizar_minmax(crudo) * 100).round(1)


# ---------------------------------------------------------------------------
# Ensamble del ICT
# ---------------------------------------------------------------------------

CRITERIOS = [
    "severidad_riesgo", "exposicion_proyecto", "vulnerabilidad_territorial",
    "amenazas_externas", "convergencia",
]


def ensamblar_ict(
    criterios_crudos: dict[str, pd.Series],
    pesos: dict[str, float],
    ids_paquete: list[str],
    bounds: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    """Normaliza cada criterio crudo a 0-1 y calcula el ICT ponderado (0-100),
    con la contribucion por criterio.

    `bounds` fija el minimo/maximo usado para normalizar cada criterio. Si no
    se pasa, se calcula min-max sobre los valores crudos recibidos aqui (uso
    normal, capa Oro del dia). Para comparar dos fechas (tendencia) hay que
    normalizar ambas con los MISMOS bounds -- de lo contrario un cambio en el
    minimo/maximo del conjunto, y no en los riesgos, se leeria como tendencia.
    Devuelve (tabla, bounds_usados) para que el llamador pueda reutilizarlos.
    """
    tabla = pd.DataFrame(index=pd.Index(ids_paquete, name="id_paquete"))
    contribuciones = pd.DataFrame(index=pd.Index(ids_paquete, name="id_paquete"))
    bounds_usados: dict[str, tuple[float, float]] = {}

    for criterio in CRITERIOS:
        crudo = criterios_crudos.get(criterio, pd.Series(dtype=float)).reindex(ids_paquete).fillna(0.0)
        if bounds and criterio in bounds:
            minimo, maximo = bounds[criterio]
        else:
            minimo, maximo = float(crudo.min()), float(crudo.max())
        bounds_usados[criterio] = (minimo, maximo)

        if maximo > minimo:
            normalizado = ((crudo - minimo) / (maximo - minimo)).clip(0.0, 1.0)
        else:
            normalizado = crudo * 0.0
        tabla[criterio] = normalizado
        contribuciones[criterio] = normalizado * pesos[criterio] * 100

    tabla["ICT"] = contribuciones[CRITERIOS].sum(axis=1).round(1)
    for criterio in CRITERIOS:
        contribuciones[criterio] = contribuciones[criterio].round(1)

    return tabla.join(contribuciones, rsuffix="_contrib"), bounds_usados


def clasificar_ict(valor: float, umbrales: dict) -> str:
    if valor >= umbrales["alto"]:
        return "critico"
    if valor >= umbrales["medio"]:
        return "alto"
    if valor >= umbrales["bajo"]:
        return "medio"
    return "bajo"


def indice_confianza(df_riesgos_paquete: pd.DataFrame, criterios_activos: list[str], criterios_crudos: dict, id_paquete: str) -> float:
    """Fraccion de criterios con dato real (no cero/ausente) para esa unidad."""
    disponibles = 0
    for criterio in criterios_activos:
        serie = criterios_crudos.get(criterio)
        if serie is not None and id_paquete in serie.index and serie.loc[id_paquete] > 0:
            disponibles += 1
    return round(disponibles / len(criterios_activos), 2) if criterios_activos else 0.0
