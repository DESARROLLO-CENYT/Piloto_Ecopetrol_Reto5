"""Red vial unificada: Plata -> Oro.

Entradas (Plata): data/silver/red_vial.geojson y proveniencia_red_vial.json. Oro no lee Bronce.
Salidas (Oro):    data/gold/red_vial.geojson, la capa de vias del mapa: red nacional (INVIAS) y complementaria (IGAC),
                  sin duplicados, distinguidas por la columna `fuente`.

Uso:  python -m oro.red_vial   (despues de plata.red_vial)
"""
from __future__ import annotations

import sys

import geopandas as gpd

from comun.config import ORO, PLATA, asegurar_directorios
from comun.serializacion import escribir_coleccion, leer_proveniencia


def main() -> int:
    asegurar_directorios()
    ruta = PLATA / "red_vial.geojson"
    if not ruta.exists():
        print("Falta data/silver/red_vial.geojson: corre primero plata.red_vial")
        return 1
    red = gpd.read_file(ruta)
    prov = leer_proveniencia("red_vial")
    por_fuente = red.groupby("fuente")["km"].sum()
    metadata = {
        "fuentes": {
            "INVIAS": f"Red Vial Nacional, datos.gov.co (CC BY-SA 4.0), descargada el {prov['bronce']['invias']['descargado_en']}",
            "IGAC": f"Cartografía básica 1:100.000, servicio del IDEAM (uso libre solo sin fines comerciales), descargada el {prov['bronce']['igac']['descargado_en']}",
        },
        "km": round(float(red["km"].sum())), "km_nacional": round(float(por_fuente.get("INVIAS", 0)), 1),
        "km_complementaria": round(float(por_fuente.get("IGAC", 0))),
    }
    escribir_coleccion(ORO / "red_vial.geojson", red, metadata)
    print(f"Oro de la red vial generado: {len(red)} tramos, {metadata['km']} km ({metadata['km_nacional']} nacionales)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
