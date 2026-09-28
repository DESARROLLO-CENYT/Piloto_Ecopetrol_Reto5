"""
Estadistica espacial complementaria (Seccion 6.7 de la propuesta):
- Estimacion de densidad (kernel) para la superficie de calor.
- Analisis de puntos calientes (Getis-Ord Gi*) sobre el ICT por paquete,
  para distinguir conglomerados estadisticamente significativos de ruido.

Implementadas "a mano" con numpy (sin pysal) para mantener el piloto
liviano; la formula de Gi* es la estandar (Getis & Ord, 1992/1995).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from config import BBOX_GUAJIRA, CRS_GEOGRAFICO


def generar_grid(resolucion_grados: float, bbox: dict = BBOX_GUAJIRA) -> gpd.GeoDataFrame:
    lons = np.arange(bbox["lon_min"], bbox["lon_max"], resolucion_grados)
    lats = np.arange(bbox["lat_min"], bbox["lat_max"], resolucion_grados)
    puntos = [Point(lon, lat) for lon in lons for lat in lats]
    gdf = gpd.GeoDataFrame({"geometry": puntos}, crs=CRS_GEOGRAFICO)
    gdf["celda_id"] = [f"C-{i:05d}" for i in range(len(gdf))]
    return gdf


def kde_superficie(
    gdf_riesgos_m: gpd.GeoDataFrame,
    gdf_grid_m: gpd.GeoDataFrame,
    columna_peso: str,
    bandwidth_m: float,
) -> pd.Series:
    """Kernel gaussiano manual: intensidad en cada celda de la grilla como
    suma de contribuciones gaussianas de cada riesgo, ponderadas por severidad.
    Devuelve una serie normalizada 0-1 (para visualizar como mapa de calor).
    """
    coords_riesgos = np.column_stack([gdf_riesgos_m.geometry.x, gdf_riesgos_m.geometry.y])
    coords_grid = np.column_stack([gdf_grid_m.geometry.x, gdf_grid_m.geometry.y])
    pesos = gdf_riesgos_m[columna_peso].to_numpy()

    if len(coords_riesgos) == 0:
        return pd.Series(0.0, index=gdf_grid_m["celda_id"])

    # distancias grid x riesgos (n_grid, n_riesgos) - via broadcasting
    dx = coords_grid[:, 0][:, None] - coords_riesgos[:, 0][None, :]
    dy = coords_grid[:, 1][:, None] - coords_riesgos[:, 1][None, :]
    d2 = dx**2 + dy**2

    kernel = np.exp(-0.5 * d2 / (bandwidth_m**2))
    intensidad = (kernel * pesos[None, :]).sum(axis=1)

    maximo = intensidad.max()
    intensidad_norm = intensidad / maximo if maximo > 0 else intensidad
    return pd.Series(intensidad_norm, index=gdf_grid_m["celda_id"])


def getis_ord_gi_star(centroides_m: gpd.GeoSeries, valores: pd.Series, k_vecinos: int) -> pd.DataFrame:
    """Gi* con matriz de pesos binaria por k-vecinos mas cercanos (incluye la
    propia unidad, como es estandar en Gi*). Devuelve z-score y clasificacion.
    """
    ids = list(centroides_m.index)
    n = len(ids)
    coords = np.column_stack([centroides_m.geometry.x, centroides_m.geometry.y]) if hasattr(centroides_m, "geometry") else np.column_stack([centroides_m.x, centroides_m.y])
    x = valores.reindex(ids).fillna(0.0).to_numpy()

    if n < 3:
        return pd.DataFrame({"id_paquete": ids, "z_score": 0.0, "clasificacion": "muestra_insuficiente"}).set_index("id_paquete")

    k = min(k_vecinos, n - 1)
    dist = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(axis=2))

    w = np.zeros((n, n))
    for i in range(n):
        vecinos = np.argsort(dist[i])[: k + 1]  # incluye i mismo (dist 0)
        w[i, vecinos] = 1.0

    x_bar = x.mean()
    s = np.sqrt((x**2).mean() - x_bar**2)
    s = s if s > 1e-9 else 1e-9

    suma_w = w.sum(axis=1)
    suma_w2 = (w**2).sum(axis=1)
    numerador = (w * x[None, :]).sum(axis=1) - x_bar * suma_w
    denominador = s * np.sqrt(np.clip((n * suma_w2 - suma_w**2) / (n - 1), a_min=1e-9, a_max=None))
    z = numerador / denominador

    def clasificar(z_val):
        if z_val >= 1.96:
            return "punto_caliente_significativo"
        if z_val <= -1.96:
            return "punto_frio_significativo"
        return "sin_patron_significativo"

    return pd.DataFrame({"z_score": z.round(2), "clasificacion": [clasificar(v) for v in z]}, index=ids)
