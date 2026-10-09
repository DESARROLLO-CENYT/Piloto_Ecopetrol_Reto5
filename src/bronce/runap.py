"""Descarga las areas protegidas de La Guajira (RUNAP) a Bronce.

Fuente: Registro Unico Nacional de Areas Protegidas (RUNAP), Parques Nacionales Naturales de Colombia, servicio ArcGIS
`pnn/runap` (sin clave). Incluye las areas nacionales (parques, santuarios), las regionales de las corporaciones
autonomas (distritos de manejo integrado, reservas forestales) y las reservas naturales de la sociedad civil. Se piden
las que cruzan la caja de descarga; Plata deja las que tocan La Guajira.

Uso:  python -m bronce.runap
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

from comun.config import BRONCE, asegurar_directorios
from comun.http import arcgis_capa

SERVICIO = "https://mapas.parquesnacionales.gov.co/arcgis/rest/services/pnn/runap/MapServer"


def main() -> int:
    asegurar_directorios()
    print("Áreas protegidas del RUNAP (Parques Nacionales) - sin clave")
    feats = arcgis_capa(SERVICIO, 0)
    if not feats:
        print("El servicio no devolvio áreas protegidas.")
        return 1
    (BRONCE / "runap_areas_protegidas.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    meta = {
        "fuente": "Parques Nacionales Naturales de Colombia - Registro Único Nacional de Áreas Protegidas (RUNAP)",
        "servicio": f"{SERVICIO}/0", "licencia": "Datos abiertos de Parques Nacionales; citar la fuente",
        "descargado_en": datetime.now().isoformat(timespec="seconds"), "areas_en_la_caja": len(feats),
    }
    (BRONCE / "runap_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(feats)} áreas protegidas cruzan la caja de descarga")
    return 0


if __name__ == "__main__":
    sys.exit(main())
