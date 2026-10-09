"""Limites municipales de La Guajira (DANE MGN 2024): Bronce -> Plata.

Entradas (Bronce): data/bronze/dane_municipios.geojson, divipola_municipios.csv y municipios_meta.json.
Salidas (Plata):   data/silver/municipios.geojson, reporte_calidad_municipios.csv, proveniencia_municipios.json.

15 poligonos con nombre propio (del DIVIPOLA), codigo DANE, area recalculada en metros y geometria simplificada
SIN abrir huecos entre vecinos (coverage_simplify comparte cada borde).

Uso:  python -m plata.municipios   (despues de bronce.municipios)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.ideam import sin_tildes
from comun.serializacion import escribir_proveniencia, leer_json

TOLERANCIA_GRADOS = 0.0004      # ~45 m: invisible a la escala del mapa, quita ~90 % de los vertices
MINUSCULAS = {"de", "del", "la", "las", "los", "el"}
ACENTOS = {"DISTRACCION": "Distracción"}   # el DANE escribe en mayusculas y sin tildes; solo este las necesita


def nombre_propio(nombre: str) -> str:
    """'LA JAGUA DEL PILAR' -> 'La Jagua del Pilar'."""
    n = " ".join(str(nombre).split())
    if n.upper() in ACENTOS:
        return ACENTOS[n.upper()]
    palabras = n.lower().split(" ")
    return " ".join(p if (i > 0 and p in MINUSCULAS) else p.capitalize() for i, p in enumerate(palabras))


def _vertices(gdf) -> int:
    return int(shapely.get_num_coordinates(gdf.geometry.values).sum())


def limpiar(bruto: gpd.GeoDataFrame, divipola: pd.DataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    rep: dict = {"municipios_bronce": int(len(bruto)), "vertices_bronce": _vertices(bruto)}
    # el MGN 2024 del DANE trae los campos en minusculas; el de 2005 (Esri) en mayusculas
    g = bruto.rename(columns={c: c.upper() for c in bruto.columns if c != "geometry"})
    rep["geometrias_invalidas"] = int((~g.is_valid).sum())
    g["geometry"] = g.geometry.make_valid()

    g["codigo"] = g["DPTO_CCDGO"].astype(str).str.zfill(2) + g["MPIO_CCDGO"].astype(str).str.zfill(3)
    d = divipola.assign(codigo=divipola["cod_mpio"].astype(str)).set_index("codigo")
    rep["sin_divipola"] = int((~g["codigo"].isin(d.index)).sum())
    rep["nombre_distinto_en_divipola"] = int(sum(
        sin_tildes(str(n)).upper() != sin_tildes(str(d["nom_mpio"].get(c, n))).upper() for c, n in zip(g["codigo"], g["MPIO_CNMBR"])
    ))
    g["nombre"] = g["MPIO_CNMBR"].map(nombre_propio)
    # cabecera municipal segun DIVIPOLA (coordenadas con coma decimal)
    g["cabecera_lon"] = g["codigo"].map(lambda c: float(str(d["longitud"].get(c, "nan")).replace(",", ".")))
    g["cabecera_lat"] = g["codigo"].map(lambda c: float(str(d["latitud"].get(c, "nan")).replace(",", ".")))

    # un solo pase sobre todos los poligonos: comparten cada borde y no quedan huecos ni solapes
    g["geometry"] = shapely.coverage_simplify(g.geometry.values, TOLERANCIA_GRADOS)
    g = g.to_crs(CRS_METRICO)
    g["area_km2"] = (g.area / 1e6).round(1)
    oficial = g["MPIO_NAREA"].astype(float)
    oficial = oficial / 1e6 if oficial.median() > 1e5 else oficial      # 2005 en m2; 2024 ya en km2
    rep["diferencia_maxima_de_area_km2"] = round(float((g["area_km2"] - oficial).abs().max()), 1)
    union = g.union_all()
    rep["partes_del_departamento"] = int(len(getattr(union, "geoms", [union])))
    rep["huecos_entre_municipios"] = int(sum(len(p.interiors) for p in getattr(union, "geoms", [union])))
    g = g.to_crs(CRS_GEOGRAFICO)
    g["geometry"] = shapely.set_precision(g.geometry.values, 1e-5)

    # punto para escribir el nombre: siempre cae dentro del poligono (el centro de la caja a veces cae afuera)
    interior = g.geometry.representative_point()
    g["etiqueta_lon"] = interior.x.round(5)
    g["etiqueta_lat"] = interior.y.round(5)

    g = g.sort_values("codigo").reset_index(drop=True)
    g = g[["codigo", "nombre", "area_km2", "cabecera_lon", "cabecera_lat", "etiqueta_lon", "etiqueta_lat", "geometry"]]
    rep.update(municipios_plata=int(len(g)), vertices_plata=_vertices(g), km2_departamento=round(float(g["area_km2"].sum()), 1))
    return g, rep


def main() -> int:
    asegurar_directorios()
    meta_ruta = BRONCE / "municipios_meta.json"
    if not meta_ruta.exists():
        print("Falta data/bronze/municipios_meta.json: corre primero bronce.municipios")
        return 1
    meta = leer_json(meta_ruta)
    g, rep = limpiar(gpd.read_file(BRONCE / "dane_municipios.geojson"), pd.read_csv(BRONCE / "divipola_municipios.csv", dtype=str))
    g.to_file(PLATA / "municipios.geojson", driver="GeoJSON")
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_municipios.csv", index=False)
    escribir_proveniencia("municipios", meta, rep)

    print("Plata de los municipios generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
