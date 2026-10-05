"""Hidrografia basica (IGAC 1:100.000): Plata -> Oro.

Entradas (Plata): data/silver/igac_hidrografia.geojson y proveniencia_hidrografia.json. Oro no lee Bronce.
Salidas (Oro):    data/gold/rios.geojson (lineas) y cuerpos_agua.geojson (poligonos), para el mapa.

Uso:  python -m oro.hidrografia   (despues de plata.hidrografia)
"""
from __future__ import annotations

import sys

import geopandas as gpd

from comun.config import ORO, PLATA, asegurar_directorios
from comun.serializacion import escribir_coleccion, leer_proveniencia


def construir(plata: gpd.GeoDataFrame, prov: dict) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict, dict]:
    base = {"fuente": prov["bronce"]["fuente"], "licencia": prov["bronce"]["licencia"], "descargado_en": prov["bronce"]["descargado_en"]}
    rios = plata[plata["tipo"] == "drenaje_sencillo"].drop(columns=["tipo", "area_km2"])
    agua = plata[plata["tipo"] != "drenaje_sencillo"].drop(columns=["longitud_km", "estado"])
    return rios, agua, {**base, "km": round(float(rios["longitud_km"].sum()))}, {**base, "km2": round(float(agua.geometry.to_crs(3116).area.sum() / 1e6), 1)}


def main() -> int:
    asegurar_directorios()
    ruta = PLATA / "igac_hidrografia.geojson"
    if not ruta.exists():
        print("Falta data/silver/igac_hidrografia.geojson: corre primero plata.hidrografia")
        return 1
    rios, agua, meta_rios, meta_agua = construir(gpd.read_file(ruta), leer_proveniencia("hidrografia"))
    escribir_coleccion(ORO / "rios.geojson", rios, meta_rios)
    escribir_coleccion(ORO / "cuerpos_agua.geojson", agua, meta_agua)
    print(f"Oro de la hidrografía generado: {len(rios)} tramos de río ({meta_rios['km']} km) y {len(agua)} cuerpos de agua ({meta_agua['km2']} km2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
