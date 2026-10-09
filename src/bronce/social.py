"""Descarga los indicadores sociales por municipio de La Guajira a Bronce.

Fuentes, todas abiertas y sin clave:
  - DANE, Censo Nacional de Poblacion y Vivienda (CNPV) 2018, publicados por municipio en el geoportal del DANE
    (portalgis.dane.gov.co, carpetas INDICADORES_*): poblacion total y rural dispersa, poblacion indigena y afro,
    Indice de Pobreza Multidimensional (IPM), Necesidades Basicas Insatisfechas (NBI) y sus componentes, miseria,
    deficit habitacional y su componente de acueducto. Reemplazan los atributos del censo 2005.
  - INS, Indice de Riesgo de la Calidad del Agua para consumo humano (IRCA), datos.gov.co `nxt2-39c3`: un valor por
    municipio y ano (y el del departamento, "#TODOS").
  - ART, municipios PDET (Programas de Desarrollo con Enfoque Territorial), datos.gov.co `idrk-ba8y`.

Bronce guarda cada tabla tal como llega (los campos con el nombre del servicio). La limpieza esta en plata.social.

Uso:  python -m bronce.social
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd

from comun.config import BRONCE, asegurar_directorios
from comun.http import ERRORES_RED, arcgis, soql, socrata_url

DANE = "https://portalgis.dane.gov.co/mparcgis/rest/services"
DEPARTAMENTO = "44"

# clave -> (servicio, campo con el codigo del municipio). Todas las capas de indicadores son la 4 del servicio.
CENSO_2018 = {
    "poblacion": ("INDICADORES_DE_POBLACION/Serv_Mpios_DistribucionPoblacionTotalCen_2018", "MPIO_CCDGO"),
    "poblacion_rural_dispersa": ("INDICADORES_DE_POBLACION/Serv_Mpios_DistribucionPoblacion_RuralDisper_2018", "MPIO_CCDGO"),
    "etnia": ("INDICADORES_GRUPOS_ETNICOS/Serv_Mpios_PoblacionIndigena_2018", "U_MPIO"),
    "ipm": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_IndPobrezaMultidimensional_2018", "MPIO_CCDGO"),
    "nbi": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_PropPersonasEnNBI_Total_2018", "MPIO_CCDGO"),
    "nbi_vivienda": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_ComponenteVivienda_Total_2018", "MPIO_CCDGO"),
    "nbi_servicios": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_ComponenteServicios_Total_2018", "MPIO_CCDGO"),
    "nbi_hacinamiento": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_ComponenteHacinamiento_Total_2018", "MPIO_CCDGO"),
    "nbi_inasistencia": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_ComponenteInasistenciaEscolar_Total_2018", "MPIO_CCDGO"),
    "nbi_dependencia": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_ComponenteDependenciaEconomica_Total_2018", "MPIO_CCDGO"),
    "miseria": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_NBI_PropPersonasEnMiseria_Total_2018", "MPIO_CCDGO"),
    "deficit_habitacional": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_DeficitHab_DeficitHabitacional_2018", "MPIO_CCDGO"),
    "deficit_acueducto": ("INDICADORES_COND_DE_VIDA/Serv_Mpios_DeficitHab_CompAcueducto_2018", "MPIO_CCDGO"),
}
IRCA = "nxt2-39c3"
PDET = "idrk-ba8y"


def bajar_indicador(servicio: str, campo: str) -> pd.DataFrame:
    datos = arcgis(f"{DANE}/{servicio}/MapServer/4/query", {
        "where": f"{campo} LIKE '{DEPARTAMENTO}%'", "outFields": "*", "returnGeometry": "false", "f": "json"})
    return pd.DataFrame([f["attributes"] for f in datos.get("features", [])])


def main() -> int:
    asegurar_directorios()
    print("Indicadores sociales por municipio (DANE censo 2018, INS, ART) - sin clave")
    tablas, fallidas = {}, []
    for clave, (servicio, campo) in CENSO_2018.items():
        try:
            df = bajar_indicador(servicio, campo)
        except ERRORES_RED as e:
            fallidas.append(f"{clave}: {type(e).__name__}: {e}"[:200])
            continue
        df.to_csv(BRONCE / f"dane_censo2018_{clave}.csv", index=False, encoding="utf-8")
        tablas[clave] = len(df)
        print(f"  censo 2018 · {clave}: {len(df)} municipios")

    irca = soql(socrata_url(IRCA), where="upper(departamento) like '%GUAJIRA%'", limit=5000)
    pd.DataFrame(irca).to_csv(BRONCE / "ins_irca.csv", index=False, encoding="utf-8")
    pdet = soql(socrata_url(PDET), limit=1000)
    pd.DataFrame(pdet).to_csv(BRONCE / "art_pdet.csv", index=False, encoding="utf-8")
    print(f"  IRCA: {len(irca)} filas · PDET: {len(pdet)} municipios del país")

    meta = {
        "fuente": "DANE (CNPV 2018), INS (IRCA) y ART (PDET)",
        "fuentes": {
            "censo_2018": {"fuente": "DANE - Censo Nacional de Población y Vivienda 2018, geoportal", "servicio": DANE,
                           "licencia": "Datos abiertos del DANE; citar la fuente", "tablas": tablas},
            "irca": {"fuente": "Instituto Nacional de Salud - SIVICAP", "dataset": f"datos.gov.co/{IRCA}", "licencia": "CC BY-SA 4.0", "filas": len(irca)},
            "pdet": {"fuente": "Agencia de Renovación del Territorio", "dataset": f"datos.gov.co/{PDET}", "licencia": "CC BY-SA 4.0", "filas": len(pdet)},
        },
        "licencia": "Datos abiertos (DANE; CC BY-SA 4.0 en datos.gov.co)",
        "descargado_en": datetime.now().isoformat(timespec="seconds"),
        "tablas_fallidas": fallidas,
    }
    (BRONCE / "social_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in fallidas:
        print(f"  [aviso] {f}")
    return 0 if tablas else 1


if __name__ == "__main__":
    sys.exit(main())
