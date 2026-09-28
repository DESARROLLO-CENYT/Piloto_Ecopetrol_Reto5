"""
Paso 7 del piloto: exporta la capa Oro a un GeoPackage (.gpkg) con una capa
por tema, para abrir directamente en ArcGIS Pro / ArcGIS Enterprise o QGIS,
y a GeoJSON individuales como respaldo. Confirma que la estructura de datos
del piloto es agnostica del software SIG, tal como pide el Anexo 1 del reto.
"""
from __future__ import annotations

import geopandas as gpd

from config import EXPORTS, ORO, asegurar_directorios

CAPAS = {
    "paquetes_ict": "paquetes_ict.geojson",
    "riesgos": "riesgos.geojson",
    "proyectos": "proyectos.geojson",
    "comunidades": "comunidades.geojson",
    "areas_protegidas": "areas.geojson",
    "hidrologia": "hidro.geojson",
    "vias": "vias.geojson",
    "grid_calor": "grid_calor.geojson",
}


def main():
    asegurar_directorios()
    gpkg_path = EXPORTS / "reto5_piloto.gpkg"
    if gpkg_path.exists():
        gpkg_path.unlink()

    for nombre_capa, archivo in CAPAS.items():
        ruta = ORO / archivo
        if not ruta.exists():
            print(f"  [omitido] {archivo} no existe (corre primero el pipeline)")
            continue
        gdf = gpd.read_file(ruta)
        # las columnas de fecha llegan como Timestamp; GeoPackage/GDAL no las
        # admite en ese tipo dentro de este flujo simplificado, se pasan a texto
        for col in gdf.columns:
            if col == "geometry":
                continue
            if gdf[col].map(lambda v: hasattr(v, "isoformat")).any():
                gdf[col] = gdf[col].astype(str)
        gdf.to_file(gpkg_path, layer=nombre_capa, driver="GPKG")
        gdf.to_file(EXPORTS / f"{nombre_capa}.geojson", driver="GeoJSON")
        print(f"  {nombre_capa}: {len(gdf)} features")

    print(f"\nGeoPackage listo en: {gpkg_path}")
    print(f"GeoJSON de respaldo en: {EXPORTS}")


if __name__ == "__main__":
    main()
