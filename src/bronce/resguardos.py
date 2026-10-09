"""Descarga los resguardos indigenas de La Guajira a Bronce.

Fuentes, sin clave:
  - Agencia Nacional de Tierras (ANT), capa "Resguardo Indigena Formalizado" (datos abiertos de la ANT, ArcGIS):
    poligonos con nombre, pueblo, ultimo acto administrativo, area y municipio. Se piden los que cruzan la caja de
    descarga (algunos siguen hacia Cesar o Magdalena; Plata los recorta al departamento).
  - Ministerio del Interior, "Resguardos Indigenas a Nivel Nacional 2020" (datos.gov.co `epzt-64uw`): poblacion
    proyectada de cada resguardo.

Uso:  python -m bronce.resguardos
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd

from comun.config import BRONCE, asegurar_directorios
from comun.http import arcgis_capa, soql, socrata_url

ANT = "https://utility.arcgis.com/usrsvcs/servers/8944116ccfd34a7189c4bc44b8e19186/rest/services/DatosAbiertos/Resguardo_Indigena_Formalizado/FeatureServer"
MININTERIOR = "epzt-64uw"


def main() -> int:
    asegurar_directorios()
    print("Resguardos indígenas (ANT) y su población (Ministerio del Interior) - sin clave")
    feats = arcgis_capa(ANT, 0)
    if not feats:
        print("La ANT no devolvio resguardos en la caja de La Guajira.")
        return 1
    (BRONCE / "ant_resguardos.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    pob = soql(socrata_url(MININTERIOR), where="upper(nombre_del_departamento) like '%GUAJIRA%'", limit=5000)
    pd.DataFrame(pob).to_csv(BRONCE / "mininterior_resguardos_poblacion.csv", index=False, encoding="utf-8")

    meta = {
        "fuente": "Agencia Nacional de Tierras (polígonos) y Ministerio del Interior (población 2020)",
        "servicio": f"{ANT}/0", "dataset_poblacion": f"datos.gov.co/{MININTERIOR}",
        "licencia": "Datos abiertos de la ANT; población: CC BY-SA 4.0 (datos.gov.co)",
        "descargado_en": datetime.now().isoformat(timespec="seconds"),
        "resguardos_en_la_caja": len(feats), "filas_poblacion": len(pob),
    }
    (BRONCE / "resguardos_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(feats)} resguardos cruzan la caja de descarga; {len(pob)} con población en La Guajira")
    return 0


if __name__ == "__main__":
    sys.exit(main())
