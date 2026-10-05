"""Municipios de La Guajira: Plata -> Oro.

Entradas (Plata): municipios.geojson; para las cifras, ideam_estaciones.geojson, ideam_precip_diaria.parquet,
                  ideam_variables_diaria.parquet y red_vial.geojson (las cifras que falten quedan vacias).
Salidas (Oro):    data/gold/municipios.geojson (con sus cifras), limite_departamental.geojson y
                  reporte_cruces_municipios.csv (que encontro el cruce espacial entre fuentes).

Las cifras por municipio salen de cruzar espacialmente fuentes distintas: cuantas estaciones del IDEAM caen
dentro (segun su ubicacion, no segun el municipio que declara el catalogo) y cuantos km de vias lo cruzan.

Uso:  python -m oro.municipios   (despues de plata.municipios, plata.ideam y plata.red_vial)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely

from comun.config import CRS_GEOGRAFICO, CRS_METRICO, ORO, PLATA, asegurar_directorios
from comun.ideam import sin_tildes
from comun.serializacion import escribir_coleccion, leer_proveniencia


def _clave(m) -> str:
    return sin_tildes(str(m)).lower().replace(" ", "")   # "Hato Nuevo" y "Hatonuevo" son el mismo


def cifras(g: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    """Suma por municipio lo que ya esta en Plata (si existe)."""
    rep: dict = {}
    g = g.copy()
    est = PLATA / "ideam_estaciones.geojson"
    if est.exists():
        e = gpd.read_file(est)
        dentro = gpd.sjoin(e, g[["codigo", "nombre", "geometry"]], how="left", predicate="within")
        rep["estaciones_catalogo"] = int(len(e))
        rep["estaciones_fuera_de_la_guajira"] = int(dentro["codigo_right"].isna().sum())
        ok = dentro[dentro["codigo_right"].notna()]
        rep["estaciones_en_otro_municipio_que_el_declarado"] = int((ok["municipio"].map(_clave) != ok["nombre_right"].map(_clave)).sum())
        g["estaciones_catalogo"] = g["codigo"].map(ok["codigo_right"].value_counts()).fillna(0).astype(int)

        # estaciones con datos: las que tienen lluvia o alguna otra variable diaria en Plata
        con_datos: set = set()
        for nombre in ("ideam_precip_diaria.parquet", "ideam_variables_diaria.parquet"):
            if (PLATA / nombre).exists():
                con_datos |= set(pd.read_parquet(PLATA / nombre, columns=["codigoestacion"])["codigoestacion"])
        if con_datos:
            cc = dentro[dentro["codigo_left"].isin(con_datos) & dentro["codigo_right"].notna()]
            g["estaciones_con_datos"] = g["codigo"].map(cc["codigo_right"].value_counts()).fillna(0).astype(int)

    red = PLATA / "red_vial.geojson"
    if red.exists():
        vi = gpd.read_file(red).to_crs(CRS_METRICO)
        gm = g.to_crs(CRS_METRICO)
        seco = vi["accesibilidad"].eq("Solo en tiempo seco")
        nacional = vi["fuente"].eq("INVIAS")
        g["km_vias"] = [round(float(vi.geometry.intersection(p).length.sum()) / 1000) for p in gm.geometry]
        g["km_vias_nacionales"] = [round(float(vi[nacional].geometry.intersection(p).length.sum()) / 1000, 1) for p in gm.geometry]
        g["km_vias_solo_tiempo_seco"] = [round(float(vi[seco].geometry.intersection(p).length.sum()) / 1000) for p in gm.geometry]
        rep["km_vias_en_municipios"] = int(g["km_vias"].sum())
        rep["km_vias_red_unificada"] = round(float(vi.length.sum()) / 1000)
    return g, rep


def main() -> int:
    asegurar_directorios()
    ruta = PLATA / "municipios.geojson"
    if not ruta.exists():
        print("Falta data/silver/municipios.geojson: corre primero plata.municipios")
        return 1
    prov = leer_proveniencia("municipios")
    g, rep = cifras(gpd.read_file(ruta))
    km2 = round(float(g["area_km2"].sum()), 1)
    base = {"fuente": prov["bronce"]["fuente"], "licencia": prov["bronce"]["licencia"], "version_geometria": prov["bronce"]["version_geometria"],
            "descargado_en": prov["bronce"]["descargado_en"], "km2": km2}
    escribir_coleccion(ORO / "municipios.geojson", g, base)

    contorno = gpd.GeoDataFrame({"nombre": ["La Guajira"], "codigo": ["44"], "area_km2": [km2]},
                                geometry=[shapely.union_all(g.geometry.values)], crs=CRS_GEOGRAFICO)
    escribir_coleccion(ORO / "limite_departamental.geojson", contorno, base)
    pd.DataFrame([rep]).to_csv(ORO / "reporte_cruces_municipios.csv", index=False)

    print("Oro de los municipios generado")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
