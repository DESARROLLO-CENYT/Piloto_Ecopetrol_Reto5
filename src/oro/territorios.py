"""Resguardos indigenas y areas protegidas: Plata -> Oro (capas del mapa).

Entradas (Plata): resguardos.geojson, areas_protegidas_runap.geojson y sus proveniencias.
Salidas (Oro):    data/gold/resguardos.geojson, data/gold/areas_protegidas_runap.geojson.

Uso:  python -m oro.territorios   (despues de plata.resguardos y plata.runap)
"""
from __future__ import annotations

import sys

import geopandas as gpd

from comun.config import ORO, PLATA, asegurar_directorios
from comun.serializacion import escribir_coleccion, leer_proveniencia


def _base(fuente: str) -> dict:
    b = leer_proveniencia(fuente)["bronce"]
    return {"fuente": b["fuente"], "licencia": b["licencia"], "descargado_en": b["descargado_en"]}


def main() -> int:
    asegurar_directorios()
    hechos = 0
    if (PLATA / "resguardos.geojson").exists():
        r = gpd.read_file(PLATA / "resguardos.geojson")
        escribir_coleccion(ORO / "resguardos.geojson", r, {**_base("resguardos"), "km2": round(float(r["area_km2"].sum()), 1),
                                                           "nota": "Población: proyección 2020 del Ministerio del Interior, solo la parte en La Guajira."})
        print(f"  resguardos: {len(r)} ({r['area_km2'].sum():,.0f} km² en La Guajira)")
        hechos += 1
    if (PLATA / "areas_protegidas_runap.geojson").exists():
        a = gpd.read_file(PLATA / "areas_protegidas_runap.geojson")
        escribir_coleccion(ORO / "areas_protegidas_runap.geojson", a, {**_base("runap"), "km2_en_guajira": round(float(a["area_en_guajira_km2"].sum()), 1)})
        print(f"  áreas protegidas: {len(a)} ({a['area_en_guajira_km2'].sum():,.0f} km² en tierra de La Guajira)")
        hechos += 1
    if not hechos:
        print("Faltan resguardos y áreas protegidas en Plata: corre antes plata.resguardos y plata.runap")
        return 1
    print("Oro de territorios generado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
