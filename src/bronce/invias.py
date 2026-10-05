"""Descarga la Red Vial Nacional de INVIAS (datos abiertos) a la capa Bronce.

Fuente: datos.gov.co, conjunto `ie7y-asdn` (Red Vial), CC BY-SA 4.0. Son 715 tramos
de todo el pais con la geometria completa (~260 MB), asi que se le pide al portal
solo lo que cruza la caja de La Guajira (`within_box`, un solo pedido, ~1 s).
No requiere clave.

Bronce guarda los tramos tal como llegan: propiedades como texto (con los codigos
de dominio sin traducir y los "Por Defnir" de la fuente) y la geometria sin
simplificar. La limpieza esta en `invias_a_oro.py`.

Uso:  python ingesta_invias.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

from comun.config import BRONCE, CAJA_DESCARGA as CAJA, asegurar_directorios
from comun.http import soql, socrata_url as url

DATASET = "ie7y-asdn"


def main() -> int:
    asegurar_directorios()
    print("Red Vial Nacional (INVIAS) - datos abiertos, sin clave")

    total = int(soql(url(DATASET), select="count(*)")[0]["count"])
    filas = soql(
        url(DATASET), timeout=300, limit=1000,
        where=f"within_box(multiline, {CAJA['lat_sur']}, {CAJA['lon_oeste']}, {CAJA['lat_norte']}, {CAJA['lon_este']})",
    )
    if not filas:
        print("El portal no devolvio tramos en la caja de La Guajira.")
        return 1

    features = []
    for f in filas:
        geom = f.pop("multiline", None)
        features.append({"type": "Feature", "geometry": geom, "properties": f})
    coleccion = {"type": "FeatureCollection", "features": features}
    (BRONCE / "invias_red_vial.geojson").write_text(json.dumps(coleccion), encoding="utf-8")

    vertices = sum(len(l) for f in features if f["geometry"] for l in f["geometry"]["coordinates"])
    meta = {
        "fuente": "INVIAS - datos.gov.co", "dataset": DATASET, "licencia": "CC BY-SA 4.0",
        "descargado_en": datetime.now().isoformat(timespec="seconds"),
        "tramos_en_el_pais": total, "tramos_descargados": len(features), "vertices": vertices,
        "caja": CAJA,
    }
    (BRONCE / "invias_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(features)} tramos de {total} en el pais, {vertices:,} vertices -> data/bronze/invias_red_vial.geojson")
    return 0


if __name__ == "__main__":
    sys.exit(main())
