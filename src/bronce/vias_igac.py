"""Descarga las vias de la cartografia basica del IGAC (1:100.000) a la capa Bronce.

Fuente: servicio ArcGIS `Cartografia_Basica/Vias` del IDEAM (dhime.ideam.gov.co), que publica la
cartografia basica del IGAC: seis tipos de via y los caminos y senderos. A diferencia de la Red
Vial Nacional de INVIAS (solo troncales, transversales y accesos a capitales), incluye las vias
secundarias, terciarias y los caminos. No requiere clave.

LICENCIA: igual que la hidrografia, el IGAC permite su uso libre y gratuito solo SIN fines
comerciales (Resolucion 364 de 2012). Este piloto es de demostracion.

Bronce guarda cada capa tal como llega (GeoJSON en grados, todos los atributos, sin simplificar).
La limpieza esta en `vias_igac_a_oro.py`.

Uso:  python ingesta_vias_igac.py
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

SERVICIO = "https://dhime.ideam.gov.co/server/rest/services/Cartografia_Basica/Vias/MapServer"
CAPAS = {  # id de capa en el servicio -> (archivo de Bronce, titulo)
    6: ("igac_via_tipo1", "Vía tipo 1"), 5: ("igac_via_tipo2", "Vía tipo 2"), 4: ("igac_via_tipo3", "Vía tipo 3"),
    3: ("igac_via_tipo4", "Vía tipo 4"), 2: ("igac_via_tipo5", "Vía tipo 5"), 1: ("igac_via_tipo6", "Vía tipo 6"),
    0: ("igac_via_caminos", "Caminos y senderos"),
}


def main() -> int:
    asegurar_directorios()
    print("Vías de la cartografía básica (IGAC 1:100.000, vía IDEAM) - sin clave")
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
    (BRONCE / "vias_igac_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo en {time.time() - inicio:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
