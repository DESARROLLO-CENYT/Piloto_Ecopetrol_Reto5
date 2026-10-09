"""Lluvia mensual CHIRPS v3 por municipio: Plata -> Oro (lo que consume el mapa y su controlador de tiempo).

Entradas (Plata): data/silver/chirps_municipio_mensual.parquet y proveniencia_chirps.json. Oro no lee Bronce.
Salida (Oro):     data/gold/lluvia_chirps.json

Para cada municipio (y el departamento, codigo 44):
  * mm de cada mes de los ultimos anos (los que muestra el mapa; ANIOS_VISIBLES),
  * la normal climatologica de cada mes del ano (promedio 1991-2020, periodo de referencia de la OMM),
  * cuanto se aparto cada mes de su normal, en % (`anomalia_pct`: 0 = lo normal; -50 = la mitad de lo normal; +100 = el doble).
Si Bronce no alcanza los 30 anos de la normal, se usa el periodo que haya y el metadata lo dice.

Uso:  python -m oro.chirps   (despues de plata.chirps)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from comun.config import ORO, PLATA, asegurar_directorios
from comun.serializacion import escribir_json, leer_proveniencia

ANIOS_VISIBLES = 10            # el mapa muestra los ultimos 10 anos completos mas el ano en curso
NORMAL = (1991, 2020)


def _r(x, nd=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def construir(tabla: pd.DataFrame, prov: dict) -> dict:
    tabla = tabla.copy()
    tabla["mes"] = pd.to_datetime(tabla["mes"])
    tabla["anio"], tabla["m"] = tabla["mes"].dt.year, tabla["mes"].dt.month
    hasta = tabla["mes"].max()
    desde_visible = pd.Timestamp(hasta.year - ANIOS_VISIBLES, 1, 1)
    meses = pd.date_range(desde_visible, hasta, freq="MS")

    en_normal = tabla[tabla["anio"].between(*NORMAL)]
    anios_normal = sorted(en_normal["anio"].unique())
    if len(anios_normal) < 30:                       # no hay 30 anos: se dice cual periodo se uso
        en_normal = tabla[tabla["mes"] < desde_visible] if (tabla["mes"] < desde_visible).any() else tabla
        anios_normal = sorted(en_normal["anio"].unique())
    periodo_normal = f"{anios_normal[0]}-{anios_normal[-1]}"
    normales = en_normal.groupby(["codigo", "m"])["mm"].mean()

    zonas = {}
    for (codigo, nombre), g in tabla.groupby(["codigo", "municipio"]):
        serie = g.set_index("mes")["mm"].reindex(meses)
        normal = [_r(normales.get((codigo, m))) for m in range(1, 13)]
        anomalia = [None if v is None or np.isnan(v) or not normal[d.month - 1] else _r((v / normal[d.month - 1] - 1) * 100, 0)
                    for d, v in serie.items()]
        anual = g[g["anio"].between(*NORMAL)].groupby("anio")["mm"].sum()
        zonas[codigo] = {"nombre": nombre, "mm": [_r(v) for v in serie.values], "normal": normal, "anomalia_pct": anomalia,
                         "normal_anual": _r(anual.mean(), 0) if len(anual) else None}
    b = prov["bronce"]
    return {
        "metadata": {
            "fuente": b["fuente"], "licencia": b["licencia"], "cita": b["cita"], "descargado_en": b["descargado_en"],
            "unidad": "mm/mes", "resolucion": "0,05 grados (~5,5 km), promedio ponderado por area de las celdas de cada municipio",
            "meses": [d.strftime("%Y-%m") for d in meses], "desde": meses[0].strftime("%Y-%m"), "hasta": meses[-1].strftime("%Y-%m"),
            "normal": periodo_normal, "normal_completa": len(anios_normal) >= 30,
        },
        "departamento": zonas.pop("44", None),
        "municipios": zonas,
    }


def main() -> int:
    asegurar_directorios()
    ruta = PLATA / "chirps_municipio_mensual.parquet"
    if not ruta.exists():
        print("Falta data/silver/chirps_municipio_mensual.parquet: corre primero plata.chirps")
        return 1
    oro = construir(pd.read_parquet(ruta), leer_proveniencia("chirps"))
    escribir_json(ORO / "lluvia_chirps.json", oro)
    m = oro["metadata"]
    d = oro["departamento"]
    print(f"Oro de CHIRPS generado: {len(oro['municipios'])} municipios, {len(m['meses'])} meses ({m['desde']} a {m['hasta']}), normal {m['normal']}")
    if d:
        print(f"  La Guajira: normal anual {d['normal_anual']} mm; ultimo mes {m['hasta']}: {d['mm'][-1]} mm ({d['anomalia_pct'][-1]:+.0f} % frente a lo normal)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
