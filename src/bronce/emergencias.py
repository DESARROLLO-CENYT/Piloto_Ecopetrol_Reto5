"""Descarga las emergencias atendidas en La Guajira (UNGRD) a Bronce.

Fuente: Unidad Nacional para la Gestion del Riesgo de Desastres (UNGRD), reportes anuales de emergencias en datos.gov.co
(CC BY-SA 4.0, sin clave): fecha, municipio, tipo de evento y afectacion (personas, familias, viviendas, vias...).
La UNGRD publica un conjunto por periodo y cada uno con columnas distintas; 2021 y 2022 no estan publicados en el portal.
Se bajan solo las filas de La Guajira, tal como llegan; plata.emergencias las armoniza.

Uso:  python -m bronce.emergencias
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd

from comun.config import BRONCE, asegurar_directorios
from comun.http import ERRORES_RED, soql, socrata_url

REPORTES = {        # periodo -> conjunto de datos.gov.co
    "2019": "4fd8-ptcr",
    "2020": "4t8v-ywmw",
    "2023_2024": "rgre-6ak4",
    "2025_en_adelante": "2343-nuqp",
}


def main() -> int:
    asegurar_directorios()
    print("Emergencias atendidas por la UNGRD (datos.gov.co) - sin clave")
    resumen, fallidos = {}, []
    for periodo, dataset in REPORTES.items():
        try:
            filas = soql(socrata_url(dataset), where="upper(departamento) like '%GUAJIRA%'", limit=50000)
        except ERRORES_RED as e:
            fallidos.append(f"{periodo}: {type(e).__name__}: {e}"[:200])
            continue
        pd.DataFrame(filas).astype(str).to_parquet(BRONCE / f"ungrd_emergencias_{periodo}.parquet", index=False)
        resumen[periodo] = {"dataset": dataset, "filas": len(filas)}
        print(f"  {periodo}: {len(filas)} emergencias")
    meta = {
        "fuente": "Unidad Nacional para la Gestión del Riesgo de Desastres (UNGRD), datos.gov.co", "licencia": "CC BY-SA 4.0",
        "descargado_en": datetime.now().isoformat(timespec="seconds"), "reportes": resumen, "reportes_fallidos": fallidos,
        "periodos_sin_publicar": ["2021", "2022"],
    }
    (BRONCE / "emergencias_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in fallidos:
        print(f"  [aviso] {f}")
    return 0 if resumen else 1


if __name__ == "__main__":
    sys.exit(main())
