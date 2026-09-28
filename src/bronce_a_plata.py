"""
Paso 2 del piloto: Bronce -> Plata.

Limpieza, deduplicacion, estandarizacion de taxonomia y validacion de
geometrias sobre el registro de riesgos sintetico. Los riesgos sin
coordenadas no se descartan: se ubican por el centroide de su paquete de
trabajo y quedan marcados con geolocalizacion_inferida=True, para que el
modelo los use pero el reporte de brechas los distinga.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios

CATEGORIAS_VALIDAS = {
    "social_comunidad", "ambiental", "seguridad_fisica",
    "logistico_acceso", "climatico", "contractual",
}
ESTADOS_VALIDOS = {"latente", "proximo_a_materializarse", "materializado"}


def _normalizar_texto(serie: pd.Series) -> pd.Series:
    return (
        serie.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("__", "_", regex=False)
    )


def cargar_bronce():
    df_riesgos = pd.read_excel(BRONCE / "registro_riesgos.xlsx")
    gdf_paquetes = gpd.read_file(BRONCE / "paquetes_trabajo.geojson")
    gdf_proyectos = gpd.read_file(BRONCE / "proyectos.geojson")
    gdf_comunidades = gpd.read_file(BRONCE / "comunidades.geojson")
    gdf_areas = gpd.read_file(BRONCE / "areas_protegidas.geojson")
    gdf_hidro = gpd.read_file(BRONCE / "hidrologia.geojson")
    gdf_vias = gpd.read_file(BRONCE / "vias.geojson")
    df_clima = pd.read_csv(BRONCE / "clima_ideam.csv")
    return {
        "riesgos": df_riesgos, "paquetes": gdf_paquetes, "proyectos": gdf_proyectos,
        "comunidades": gdf_comunidades, "areas": gdf_areas, "hidro": gdf_hidro,
        "vias": gdf_vias, "clima": df_clima,
    }


def limpiar_riesgos(df: pd.DataFrame, gdf_paquetes: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    reporte = {"filas_bronce": len(df)}

    # 1) Estandarizar taxonomia (categoria, estado, tipo)
    df["categoria"] = _normalizar_texto(df["categoria"])
    df["categoria"] = df["categoria"].where(df["categoria"].isin(CATEGORIAS_VALIDAS), "sin_clasificar")
    df["estado"] = _normalizar_texto(df["estado"])
    df["estado"] = df["estado"].where(df["estado"].isin(ESTADOS_VALIDOS), "latente")
    df["tipo"] = _normalizar_texto(df["tipo"])

    # 2) Deduplicar: mismo riesgo reportado varias veces (id base sin sufijo -DUP,
    #    y ademas por combinacion de campos clave para duplicados "reales")
    df["id_riesgo_base"] = df["id_riesgo"].str.replace(r"-DUP\d*$", "", regex=True)
    antes = len(df)
    df = df.sort_values("id_riesgo").drop_duplicates(
        subset=["id_riesgo_base", "id_paquete_trabajo", "categoria", "probabilidad", "impacto"],
        keep="first",
    )
    reporte["duplicados_removidos"] = antes - len(df)

    # 3) Tipos y fechas
    for col in ["fecha_identificacion", "fecha_materializacion", "fecha_ejecucion_accion"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["probabilidad"] = pd.to_numeric(df["probabilidad"], errors="coerce").clip(1, 5)
    df["impacto"] = pd.to_numeric(df["impacto"], errors="coerce").clip(1, 5)
    df["causa"] = df["causa"].fillna("sin_causa_registrada")

    # 4) Geolocalizacion: usar lat/lon si existen; si no, inferir por el
    #    centroide del paquete de trabajo y marcarlo.
    df["geolocalizacion_inferida"] = df["lat"].isna() | df["lon"].isna()
    centroides = (
        gdf_paquetes.set_index("id_paquete").geometry.to_crs(CRS_METRICO).centroid.to_crs(CRS_GEOGRAFICO)
    )
    faltantes = df["geolocalizacion_inferida"]
    df.loc[faltantes, "lon"] = df.loc[faltantes, "id_paquete_trabajo"].map(lambda p: centroides.get(p).x if centroides.get(p) is not None else None)
    df.loc[faltantes, "lat"] = df.loc[faltantes, "id_paquete_trabajo"].map(lambda p: centroides.get(p).y if centroides.get(p) is not None else None)

    reporte["sin_coordenadas_originales"] = int(faltantes.sum())
    df_sin_geom = df[df["lat"].isna() | df["lon"].isna()]
    reporte["riesgos_sin_paquete_valido"] = int(len(df_sin_geom))
    df = df.dropna(subset=["lat", "lon"])

    # 5) Severidad y geometria
    df["severidad"] = (df["probabilidad"] * df["impacto"]).clip(1, 25)
    geometry = [Point(xy) for xy in zip(df["lon"], df["lat"])]
    gdf = gpd.GeoDataFrame(df.drop(columns=["id_riesgo_base"]), geometry=geometry, crs=CRS_GEOGRAFICO)

    reporte["filas_plata"] = len(gdf)
    return gdf, reporte


def main():
    asegurar_directorios()
    datos = cargar_bronce()

    gdf_riesgos, reporte = limpiar_riesgos(datos["riesgos"], datos["paquetes"])

    gdf_riesgos.to_file(PLATA / "riesgos.geojson", driver="GeoJSON")
    for nombre in ["paquetes", "proyectos", "comunidades", "areas", "hidro", "vias"]:
        datos[nombre].to_file(PLATA / f"{nombre}.geojson", driver="GeoJSON")
    datos["clima"].to_parquet(PLATA / "clima.parquet", index=False)

    reporte_df = pd.DataFrame([reporte])
    reporte_df.to_csv(PLATA / "reporte_calidad_bronce_a_plata.csv", index=False)

    print("Plata generada en:", PLATA)
    for k, v in reporte.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
