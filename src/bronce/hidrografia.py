"""Descarga la hidrografia basica de Colombia (IGAC, 1:100.000) a la capa Bronce.

Fuente: servicio ArcGIS `Cartografia_Basica/Hidrografia` del IDEAM (dhime.ideam.gov.co),
que publica la cartografia basica del IGAC: drenajes sencillos (rios, arroyos y quebradas
como lineas), drenajes principales (rios anchos como poligonos), cienagas, embalses y
lagunas. No requiere clave. Se pide solo lo que cruza la caja de La Guajira, en paginas
de 1.000 objetos.

LICENCIA: el IGAC permite su uso libre y gratuito siempre que NO sea comercial; para uso
comercial se debe acordar una licencia (Resolucion 364 de 2012). Este piloto es de
demostracion, sin fin comercial. Si el proyecto pasa a produccion, hay que resolverlo.

Bronce guarda cada capa tal como llega (GeoJSON en grados, todos los atributos, sin
simplificar). La limpieza esta en `hidrografia_a_oro.py`.

Uso:  python ingesta_hidrografia.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime

import shapely
from shapely.geometry import shape

from comun.config import BRONCE, CAJA_DESCARGA, asegurar_directorios
from comun.http import ERRORES_RED, arcgis_capa

SERVICIO = "https://dhime.ideam.gov.co/server/rest/services/Cartografia_Basica/Hidrografia/MapServer"
CAPAS = {  # id de capa en el servicio -> (archivo de Bronce, titulo)
    0: ("igac_drenaje_sencillo", "Drenajes sencillos"),
    1: ("igac_drenaje_doble", "Drenajes principales (doble)"),
    2: ("igac_cienagas", "Ciénagas"),
    3: ("igac_embalses", "Embalses"),
    4: ("igac_lagunas", "Lagunas"),
}


def main() -> int:
    asegurar_directorios()
    print("Hidrografía básica (IGAC 1:100.000, vía IDEAM) - sin clave")
    print("Licencia: uso libre NO comercial (Res. 364/2012 del IGAC). Demostración.")
    inicio = time.time()
    meta = {
        "fuente": "IGAC (cartografía básica 1:100.000), servicio del IDEAM", "servicio": SERVICIO,
        "licencia": "IGAC: uso libre y gratuito sin fines comerciales (Resolución 364 de 2012)",
        "descargado_en": datetime.now().isoformat(timespec="seconds"), "caja": CAJA_DESCARGA, "capas": {},
    }
    for capa, (archivo, titulo) in CAPAS.items():
        try:
            feats = arcgis_capa(SERVICIO, capa)
        except ERRORES_RED + (KeyError,) as e:
            print(f"  {titulo}: falló ({type(e).__name__}: {e})")
            return 1
        vertices = int(sum(shapely.get_num_coordinates(shape(f["geometry"])) for f in feats if f.get("geometry")))
        (BRONCE / f"{archivo}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
        meta["capas"][archivo] = {"titulo": titulo, "capa_servicio": capa, "objetos": len(feats), "vertices": vertices}
        print(f"  {titulo}: {len(feats):,} objetos, {vertices:,} vértices -> data/bronze/{archivo}.geojson")
    (BRONCE / "hidrografia_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo en {time.time() - inicio:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
