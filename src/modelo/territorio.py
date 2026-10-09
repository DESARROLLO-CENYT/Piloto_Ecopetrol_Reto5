"""
Territorio REAL de cualquier unidad de analisis: un paquete de trabajo (poligono) o una celda de la grilla (punto).

Funciones puras: reciben capas ya leidas y, cuando miden distancias o areas, proyectadas a un CRS metrico
(config.CRS_METRICO). Devuelven tablas indexadas por la unidad, con el valor CRUDO de cada variable (km, %, casos por
100.000 habitantes...). La traduccion a una escala 0-1 la hace el ICT (modelo/ict.py) con los parametros de
parametros.yaml -> criterios.

Una variable que no se puede medir para una unidad queda en NaN: no se imputa (el ICT la deja inactiva y la cuenta en
el indice de confianza).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd

# Delitos que pueden alcanzar a un proyecto (a su personal, su carga o su infraestructura). El homicidio no entra: en
# su mayoria es violencia interpersonal y saturaria cualquier municipio. Misma lista que oro.contexto y oro.ejecucion.
DELITOS_CONTRA_PROYECTOS = ("extorsion", "secuestro", "terrorismo", "masacres", "voladura_oleoductos",
                            "voladura_puentes_vias", "pirateria_terrestre", "afectacion_fuerza_publica")


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------

def municipio_de(centros_m: gpd.GeoSeries, municipios_m: gpd.GeoDataFrame) -> pd.Series:
    """Codigo DANE del municipio que contiene cada centro; si cae fuera (costa, frontera), el mas cercano."""
    puntos = gpd.GeoDataFrame(geometry=centros_m.values, index=centros_m.index, crs=centros_m.crs)
    dentro = gpd.sjoin(puntos, municipios_m[["codigo", "geometry"]], how="left", predicate="within")
    codigo = dentro[~dentro.index.duplicated()]["codigo"].reindex(centros_m.index)
    faltan = codigo[codigo.isna()].index
    if len(faltan):
        cerca = gpd.sjoin_nearest(puntos.loc[faltan], municipios_m[["codigo", "geometry"]], how="left")
        codigo.loc[faltan] = cerca[~cerca.index.duplicated()]["codigo"].reindex(faltan)
    return codigo.astype("string")


def dentro_y_distancia(unidades_m: gpd.GeoSeries, capa_m: gpd.GeoDataFrame) -> pd.DataFrame:
    """Para cada unidad: fraccion dentro de la capa (0 a 1) y distancia en km al objeto mas cercano (0 si se tocan).

    Un poligono usa la fraccion de su area; un punto vale 1 si cae dentro y 0 si no.
    """
    if capa_m is None or not len(capa_m):
        return pd.DataFrame({"fraccion_dentro": np.nan, "distancia_km": np.nan}, index=unidades_m.index)
    union = capa_m.geometry.union_all()
    distancia = unidades_m.distance(union) / 1000
    area = unidades_m.area
    con_area = area > 0
    fraccion = pd.Series(0.0, index=unidades_m.index)
    if con_area.any():
        fraccion[con_area] = (unidades_m[con_area].intersection(union).area / area[con_area]).clip(0, 1)
    if (~con_area).any():
        fraccion[~con_area] = unidades_m[~con_area].intersects(union).astype(float)
    return pd.DataFrame({"fraccion_dentro": fraccion.round(4), "distancia_km": distancia.round(2)})


def fraccion_vias_tiempo_seco(centros_m: gpd.GeoSeries, red_m: gpd.GeoDataFrame, radio_m: float) -> pd.Series:
    """Fraccion de los km de vias a menos de `radio_m` de cada centro que solo se transitan en tiempo seco.

    Las vias sin dato de accesibilidad (sobre todo la red nacional, pavimentada) cuentan como transitables todo el ano.
    Sin vias en el radio: NaN (no se sabe como se llega).
    """
    if red_m is None or not len(red_m) or "accesibilidad" not in red_m:
        return pd.Series(np.nan, index=centros_m.index)
    seco = red_m["accesibilidad"].eq("Solo en tiempo seco").to_numpy()
    indice = red_m.sindex
    salida = {}
    for idx, centro in centros_m.items():
        zona = centro.buffer(radio_m)
        cerca = indice.query(zona, predicate="intersects")
        if not len(cerca):
            salida[idx] = np.nan
            continue
        largos = red_m.geometry.iloc[cerca].intersection(zona).length.to_numpy()
        total = largos.sum()
        salida[idx] = float(largos[seco[cerca]].sum() / total) if total > 0 else np.nan
    return pd.Series(salida).reindex(centros_m.index)


def lluvia_reciente(
    centros_m: gpd.GeoSeries,
    estaciones_m: gpd.GeoDataFrame,
    lluvia_diaria: pd.DataFrame,
    fecha_corte: pd.Timestamp,
    ventana_dias: int,
    dias_minimos: int,
    distancia_max_km: float,
) -> pd.DataFrame:
    """Lluvia acumulada en la ventana que termina en `fecha_corte`, en la estacion del IDEAM mas cercana que tenga
    al menos `dias_minimos` dias con dato en esa ventana y este a menos de `distancia_max_km`.

    `lluvia_diaria`: columnas codigoestacion, dia, mm (Plata del IDEAM). `estaciones_m`: columnas codigo, nombre.
    Si ninguna estacion cumple, la unidad queda sin dato (mm = NaN): una serie vieja o una estacion lejana no
    representan la lluvia de hoy en ese lugar.
    """
    vacia = pd.DataFrame({"lluvia_mm": np.nan, "lluvia_estacion": None, "lluvia_distancia_km": np.nan,
                          "lluvia_dias_con_dato": 0}, index=centros_m.index)
    if lluvia_diaria is None or not len(lluvia_diaria) or estaciones_m is None or not len(estaciones_m):
        return vacia
    fin = pd.Timestamp(fecha_corte).normalize()
    inicio = fin - pd.Timedelta(days=ventana_dias)
    dias = pd.to_datetime(lluvia_diaria["dia"])
    ventana = lluvia_diaria[(dias > inicio) & (dias <= fin)]
    resumen = ventana.groupby("codigoestacion").agg(mm=("mm", "sum"), dias=("mm", "count"))
    validas = resumen[resumen["dias"] >= dias_minimos]
    candidatas = estaciones_m[estaciones_m["codigo"].isin(validas.index)]
    if not len(candidatas):
        return vacia
    filas = {}
    for idx, centro in centros_m.items():
        d = candidatas.geometry.distance(centro) / 1000
        j = d.idxmin()
        if d[j] > distancia_max_km:
            filas[idx] = {"lluvia_mm": np.nan, "lluvia_estacion": None, "lluvia_distancia_km": round(float(d[j]), 1),
                          "lluvia_dias_con_dato": 0}
            continue
        codigo = candidatas.loc[j, "codigo"]
        filas[idx] = {"lluvia_mm": round(float(validas.loc[codigo, "mm"]), 1),
                      "lluvia_estacion": f"{candidatas.loc[j, 'nombre']} ({codigo})",
                      "lluvia_distancia_km": round(float(d[j]), 1),
                      "lluvia_dias_con_dato": int(validas.loc[codigo, "dias"])}
    return pd.DataFrame.from_dict(filas, orient="index").reindex(centros_m.index)


# ---------------------------------------------------------------------------
# Indicadores por municipio
# ---------------------------------------------------------------------------

def indicadores_municipales(
    censo: pd.DataFrame | None,
    seguridad: pd.DataFrame | None,
    emergencias: pd.DataFrame | None,
    chirps: pd.DataFrame | None,
    meses_anomalia: int = 3,
) -> tuple[pd.DataFrame, dict]:
    """Una fila por municipio (codigo DANE) con: ipm (%), delitos_100k (12 meses, contra personas e infraestructura),
    emergencias_por_ano (UNGRD) y anomalia_lluvia (|desviacion| media de los ultimos meses de CHIRPS frente a su
    normal 1991-2020, en fraccion). Devuelve tambien un texto por variable con su fuente y su periodo.
    """
    t = pd.DataFrame()
    fuentes: dict[str, str] = {}
    if censo is not None and len(censo):
        c = censo.set_index("codigo")
        t["ipm"] = c["ipm"]
        fuentes["ipm"] = "DANE, censo 2018 (IPM municipal)"
        poblacion = c["poblacion_2018"]
    else:
        poblacion = None

    if seguridad is not None and len(seguridad) and poblacion is not None:
        s = seguridad[seguridad["delito"].isin(DELITOS_CONTRA_PROYECTOS)].assign(mes=lambda d: pd.to_datetime(d["mes"]))
        ultimo = s["mes"].max()
        casos = s[s["mes"] > ultimo - pd.DateOffset(months=12)].groupby("codigo")["casos"].sum()
        t = t.reindex(t.index.union(casos.index))
        t["delitos_100k"] = (casos.reindex(t.index).fillna(0) / poblacion.reindex(t.index) * 1e5).round(1)
        fuentes["delitos_100k"] = f"Ministerio de Defensa, 12 meses hasta {ultimo:%Y-%m}"

    if emergencias is not None and len(emergencias):
        anios = emergencias["anio"].nunique()
        por_ano = emergencias.groupby("codigo").size() / max(anios, 1)
        t = t.reindex(t.index.union(por_ano.index))
        base = por_ano.reindex(t.index)
        # un municipio sin emergencias reportadas en los anos publicados tiene 0, no "sin dato"
        t["emergencias_por_ano"] = base.fillna(0.0).round(2)
        fuentes["emergencias_por_ano"] = f"UNGRD ({', '.join(str(a) for a in sorted(emergencias['anio'].unique()))})"

    if chirps is not None and len(chirps):
        ch = chirps.assign(mes=pd.to_datetime(chirps["mes"]))
        normal = ch[ch["mes"].dt.year.between(1991, 2020)].groupby([ch["codigo"], ch["mes"].dt.month])["mm"].mean()
        ultimo = ch["mes"].max()
        recientes = ch[ch["mes"] > ultimo - pd.DateOffset(months=meses_anomalia)].copy()
        claves = list(zip(recientes["codigo"], recientes["mes"].dt.month))
        ref = np.array([normal.get(k, np.nan) for k in claves], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            recientes["a"] = np.where(ref > 0, np.abs(recientes["mm"].to_numpy() / ref - 1), np.nan)
        anomalia = recientes.groupby("codigo")["a"].mean()
        t = t.reindex(t.index.union(anomalia.index))
        t["anomalia_lluvia"] = anomalia.reindex(t.index).round(3)
        fuentes["anomalia_lluvia"] = f"CHIRPS v3, {meses_anomalia} meses hasta {ultimo:%Y-%m} frente a la normal 1991-2020"
    t.index = t.index.astype(str)
    return t, fuentes
