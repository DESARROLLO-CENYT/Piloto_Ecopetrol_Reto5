"""Descarga los limites municipales de La Guajira (DANE, Marco Geoestadistico Nacional) a Bronce.

Fuentes, ambas sin clave:
  - Poligonos: servicio ArcGIS `datosabiertos/MGN_Municipios` de Esri Colombia, que publica la
    capa de municipios del DANE (MGN, version 2005, base cartografica del IGAC). Se filtra por
    departamento 44 (La Guajira): 15 municipios.
  - Nombres y cabeceras: conjunto DIVIPOLA `gdxc-w37w` de datos.gov.co (DANE), CC BY-SA 4.0.

Bronce guarda los poligonos tal como llegan (todos los atributos, sin simplificar).
La limpieza esta en `municipios_a_oro.py`.

Uso:  python ingesta_municipios.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd

from comun.config import BRONCE, asegurar_directorios
from comun.http import arcgis as _pedir, soql, socrata_url as url

SERVICIO = "https://ags.esri.co/arcgis/rest/services/datosabiertos/MGN_Municipios/MapServer/0"
DIVIPOLA = "gdxc-w37w"
DEPARTAMENTO = "44"   # codigo DANE de La Guajira


def main() -> int:
    asegurar_directorios()
    print("Municipios de La Guajira (DANE MGN) - sin clave")

    pagina = _pedir(f"{SERVICIO}/query", {
        "f": "geojson", "where": f"DPTO_CCDGO='{DEPARTAMENTO}'", "outFields": "*", "outSR": 4326, "returnGeometry": "true",
    })
    feats = pagina.get("features", [])
    if not feats:
        print("El servicio no devolvio municipios.")
        return 1
    (BRONCE / "dane_municipios.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")

    filas = soql(url(DIVIPOLA), where=f"cod_dpto='{DEPARTAMENTO}'", limit=200)
    pd.DataFrame(filas).to_csv(BRONCE / "divipola_municipios.csv", index=False, encoding="utf-8")

    meta = {
        "fuente": "DANE - Marco Geoestadístico Nacional (MGN), vía Esri Colombia", "servicio": SERVICIO,
        "version_geometria": "MGN 2005 (campo MPIO_NANO)",
        "licencia": "Datos abiertos del DANE; citar la fuente (licencia no verificada)",
        "divipola": f"datos.gov.co/{DIVIPOLA} (CC BY-SA 4.0)",
        "descargado_en": datetime.now().isoformat(timespec="seconds"),
        "municipios": len(feats), "divipola_filas": len(filas),
    }
    (BRONCE / "municipios_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(feats)} municipios (polígonos) y {len(filas)} filas DIVIPOLA -> data/bronze/dane_municipios.geojson")
    return 0


if __name__ == "__main__":
    sys.exit(main())
