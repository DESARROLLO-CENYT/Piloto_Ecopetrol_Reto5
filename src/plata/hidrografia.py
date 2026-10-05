"""Hidrografia basica (IGAC 1:100.000): Bronce -> Plata.

Entradas (Bronce): data/bronze/igac_{drenaje_sencillo,drenaje_doble,cienagas,embalses,lagunas}.geojson e hidrografia_meta.json.
Salidas (Plata):   data/silver/igac_hidrografia.geojson, reporte_calidad_hidrografia.csv, proveniencia_hidrografia.json.

Une las cinco capas en una tabla con la columna `tipo`, arregla geometrias invalidas, recorta a la caja de
descarga, simplifica (25 m las lineas, 20 m los poligonos), traduce el estado del cauce (5101 permanente,
5102 intermitente) y normaliza los nombres.

Uso:  python -m plata.hidrografia   (despues de bronce.hidrografia)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import box

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json

TOL_LINEA_M = 25
TOL_POLIGONO_M = 20

# archivo de Bronce -> tipo en Plata
TIPOS = {
    "igac_drenaje_sencillo": "drenaje_sencillo", "igac_drenaje_doble": "drenaje_doble",
    "igac_cienagas": "cienaga", "igac_embalses": "embalse", "igac_lagunas": "laguna",
}
ESTADO = {5101: "Permanente", 5102: "Intermitente"}   # dominio del IGAC para estado del drenaje
# La fuente escribe "Rio", "Cienaga" o "Quebrada" sin tildes; se corrigen las dos que las necesitan
PREFIJOS = {"rio": "Río", "cienaga": "Ciénaga"}


def normalizar_nombre(nombre) -> str | None:
    if nombre is None or pd.isna(nombre):
        return None
    limpio = " ".join(str(nombre).split())          # espacios dobles
    if not limpio:
        return None
    primera, _, resto = limpio.partition(" ")
    primera = PREFIJOS.get(primera.lower().replace("í", "i").replace("é", "e"), primera)
    return f"{primera} {resto}".strip()


def _vertices(gdf: gpd.GeoDataFrame) -> int:
    return int(shapely.get_num_coordinates(gdf.geometry.values).sum())


def limpiar(capas: dict[str, gpd.GeoDataFrame], caja: dict) -> tuple[gpd.GeoDataFrame, dict]:
    """`capas`: tipo -> GeoDataFrame en EPSG:4326 tal como llego de Bronce."""
    rep: dict = {}
    partes = []
    for tipo, g in capas.items():
        g = g.copy()
        g["tipo"] = tipo
        if "estado_drenaje" not in g:
            g["estado_drenaje"] = pd.NA
        partes.append(g[["objectid", "nombre_geografico", "estado_drenaje", "tipo", "geometry"]])
    todo = pd.concat(partes, ignore_index=True)
    rep["objetos_bronce"] = int(len(todo))
    rep["vertices_bronce"] = _vertices(todo)

    con_geometria = todo[todo.geometry.notna() & ~todo.geometry.is_empty]
    rep["sin_geometria"] = int(len(todo) - len(con_geometria))
    todo = con_geometria
    invalidas = ~todo.geometry.is_valid
    rep["geometrias_invalidas_reparadas"] = int(invalidas.sum())
    todo = todo.copy()
    todo.loc[invalidas, "geometry"] = todo.loc[invalidas, "geometry"].make_valid()

    # recorte en grados (una caja reproyectada a metros deja de ser rectangulo)
    todo["geometry"] = todo.geometry.intersection(box(caja["lon_oeste"], caja["lat_sur"], caja["lon_este"], caja["lat_norte"]))
    dentro = todo[~todo.geometry.is_empty]
    rep["fuera_de_la_caja"] = int(len(todo) - len(dentro))
    todo = dentro.to_crs(CRS_METRICO)

    es_poligono = todo["tipo"] != "drenaje_sencillo"
    todo.loc[es_poligono, "geometry"] = todo.loc[es_poligono].geometry.simplify(TOL_POLIGONO_M, preserve_topology=True)
    todo.loc[~es_poligono, "geometry"] = todo.loc[~es_poligono].geometry.simplify(TOL_LINEA_M, preserve_topology=True)
    no_vacias = todo[~todo.geometry.is_empty]
    rep["vacias_tras_simplificar"] = int(len(todo) - len(no_vacias))
    todo = no_vacias.copy()

    todo["longitud_km"] = (todo.length / 1000).where(~es_poligono).round(2)
    todo["area_km2"] = (todo.area / 1e6).where(es_poligono).round(3)
    todo = todo.to_crs(CRS_GEOGRAFICO)
    todo["geometry"] = shapely.set_precision(todo.geometry.values, 1e-5)   # ~1 m

    todo["nombre"] = todo["nombre_geografico"].map(normalizar_nombre)
    todo["estado"] = pd.to_numeric(todo["estado_drenaje"], errors="coerce").map(ESTADO)
    rep["sin_nombre"] = int(todo["nombre"].isna().sum())
    rep["lineas_sin_estado"] = int((todo["estado"].isna() & (todo["tipo"] == "drenaje_sencillo")).sum())

    todo = todo.sort_values(["tipo", "objectid"]).reset_index(drop=True)
    todo.insert(0, "id_objeto", todo["tipo"].map({t: t[:3] for t in TIPOS.values()}) + "-" + todo["objectid"].astype(str))
    todo = todo[["id_objeto", "tipo", "nombre", "estado", "longitud_km", "area_km2", "geometry"]]

    rios = todo[todo["tipo"] == "drenaje_sencillo"]
    rep.update(
        objetos_plata=int(len(todo)), vertices_plata=_vertices(todo),
        km_rios=round(float(rios["longitud_km"].sum())),
        km_permanentes=round(float(rios.loc[rios["estado"] == "Permanente", "longitud_km"].sum())),
        km_intermitentes=round(float(rios.loc[rios["estado"] == "Intermitente", "longitud_km"].sum())),
        km2_cuerpos_de_agua=round(float(todo["area_km2"].sum()), 1),
    )
    return todo, rep


def main() -> int:
    asegurar_directorios()
    meta_ruta = BRONCE / "hidrografia_meta.json"
    if not meta_ruta.exists():
        print("Falta data/bronze/hidrografia_meta.json: corre primero bronce.hidrografia")
        return 1
    meta = leer_json(meta_ruta)
    capas = {tipo: gpd.read_file(BRONCE / f"{archivo}.geojson") for archivo, tipo in TIPOS.items()}
    plata, rep = limpiar(capas, meta["caja"])
    plata.to_file(PLATA / "igac_hidrografia.geojson", driver="GeoJSON")
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_hidrografia.csv", index=False)
    escribir_proveniencia("hidrografia", meta, rep)

    print("Plata de la hidrografía generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
