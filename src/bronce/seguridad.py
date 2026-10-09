"""Descarga los delitos que afectan a un proyecto en La Guajira (Ministerio de Defensa) a Bronce.

Fuente: Ministerio de Defensa Nacional / Policia Nacional, conjuntos de datos.gov.co (CC BY-SA 4.0, sin clave), uno por
delito, con fecha del hecho, municipio y cantidad. Se actualizan cada mes y vienen desde 2003. Se bajan solo las filas
del departamento 44, tal como llegan.

Delitos elegidos por su relacion con la seguridad de un proyecto y de su entorno: homicidio, extorsion, secuestro,
terrorismo, masacres, voladura de oleoductos, voladura de puentes y vias, pirateria terrestre (robo de carga),
invasion y usurpacion de tierras, delitos contra el medio ambiente y afectacion de la fuerza publica.

Uso:  python -m bronce.seguridad
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd

from comun.config import BRONCE, asegurar_directorios
from comun.http import ERRORES_RED, soql, socrata_url

DEPARTAMENTO = "44"
DELITOS = {
    "homicidio": ("m8fd-ahd9", "Homicidio"),
    "extorsion": ("q2ib-t9am", "Extorsión"),
    "secuestro": ("d7zw-hpf4", "Secuestro"),
    "terrorismo": ("yi5j-5fe9", "Terrorismo"),
    "masacres": ("u8eq-92tb", "Masacres"),
    "voladura_oleoductos": ("ec2r-4byk", "Voladura de oleoductos"),
    "voladura_puentes_vias": ("m98b-cdys", "Voladura de puentes y vías"),
    "pirateria_terrestre": ("sutf-7dyz", "Piratería terrestre"),
    "invasion_tierras": ("kvjj-d2ay", "Invasión y usurpación de tierras"),
    "delitos_ambientales": ("9zck-qfvc", "Delitos contra el medio ambiente"),
    "afectacion_fuerza_publica": ("8rpn-wpty", "Afectación de la fuerza pública"),
}


def main() -> int:
    asegurar_directorios()
    print("Delitos por municipio (Ministerio de Defensa, datos.gov.co) - sin clave")
    resumen, fallidos = {}, []
    for clave, (dataset, titulo) in DELITOS.items():
        try:
            filas = soql(socrata_url(dataset), where=f"cod_depto='{DEPARTAMENTO}'", limit=100000, order="fecha_hecho")
        except ERRORES_RED as e:
            fallidos.append(f"{clave}: {type(e).__name__}: {e}"[:200])
            continue
        df = pd.DataFrame(filas).astype(str)
        df.to_parquet(BRONCE / f"mindefensa_{clave}.parquet", index=False)
        fechas = df["fecha_hecho"].sort_values() if len(df) else pd.Series(dtype=str)
        resumen[clave] = {"dataset": dataset, "titulo": titulo, "filas": len(df),
                          "desde": fechas.iloc[0][:10] if len(df) else None, "hasta": fechas.iloc[-1][:10] if len(df) else None}
        print(f"  {titulo}: {len(df)} filas")

    meta = {
        "fuente": "Ministerio de Defensa Nacional - Policía Nacional (datos.gov.co)", "licencia": "CC BY-SA 4.0",
        "descargado_en": datetime.now().isoformat(timespec="seconds"), "departamento": DEPARTAMENTO,
        "delitos": resumen, "delitos_fallidos": fallidos,
    }
    (BRONCE / "seguridad_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in fallidos:
        print(f"  [aviso] {f}")
    return 0 if resumen else 1


if __name__ == "__main__":
    sys.exit(main())
