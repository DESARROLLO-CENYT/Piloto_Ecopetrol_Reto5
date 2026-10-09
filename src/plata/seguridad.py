"""Delitos por municipio (Ministerio de Defensa): Bronce -> Plata.

Entradas (Bronce): mindefensa_<delito>.parquet (uno por delito, tal como llegan), seguridad_meta.json.
Entrada (Plata):   municipios.geojson (los 15 codigos validos).
Salidas (Plata):   seguridad_municipio_mensual.parquet (codigo, mes, delito, casos, victimas),
                   reporte_calidad_seguridad.csv, proveniencia_seguridad.json.

Reglas:
  * Cada fila de la fuente es un registro con `cantidad` (victimas o casos segun el delito). Las masacres traen
    `casos` y `victimas` por separado; para las demas, casos = filas y victimas = suma de `cantidad`.
  * Codigo de municipio a 5 digitos; los que no son de los 15 municipios se descartan y se cuentan.
  * Fechas invalidas o futuras se descartan. La fuente publica el mes anterior completo: el mes en curso puede estar
    incompleto y se marca en el reporte (`ultimo_mes`).
  * Se agrega por municipio, mes y delito. Los meses sin registros no aparecen (son cero).
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd

from comun.config import BRONCE, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json


def limpiar(crudos: dict[str, pd.DataFrame], codigos: set[str], hoy: pd.Timestamp | None = None) -> tuple[pd.DataFrame, dict]:
    hoy = hoy or pd.Timestamp.now()
    rep: dict = {"filas_bronce": 0, "fecha_invalida": 0, "municipio_desconocido": 0, "cantidad_invalida": 0}
    partes = []
    for delito, df in crudos.items():
        rep["filas_bronce"] += len(df)
        if df.empty:
            continue
        t = pd.DataFrame({"delito": delito, "fecha": pd.to_datetime(df["fecha_hecho"], errors="coerce"),
                          "codigo": df["cod_muni"].astype(str).str.split(".").str[0].str.zfill(5)})
        if "victimas" in df and "casos" in df:
            t["casos"] = pd.to_numeric(df["casos"], errors="coerce")
            t["victimas"] = pd.to_numeric(df["victimas"], errors="coerce")
        else:
            t["casos"] = 1.0
            t["victimas"] = pd.to_numeric(df["cantidad"], errors="coerce")
        mala_fecha = t["fecha"].isna() | (t["fecha"] > hoy)
        rep["fecha_invalida"] += int(mala_fecha.sum())
        t = t[~mala_fecha]
        otro = ~t["codigo"].isin(codigos)
        rep["municipio_desconocido"] += int(otro.sum())
        t = t[~otro]
        mala = t["victimas"].isna() | (t["victimas"] < 0) | t["casos"].isna()
        rep["cantidad_invalida"] += int(mala.sum())
        partes.append(t[~mala])
    eventos = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["delito", "fecha", "codigo", "casos", "victimas"])
    eventos["mes"] = eventos["fecha"].dt.to_period("M").dt.to_timestamp()
    tabla = (eventos.groupby(["codigo", "mes", "delito"], as_index=False)[["casos", "victimas"]].sum()
             .sort_values(["delito", "codigo", "mes"]).reset_index(drop=True))
    tabla[["casos", "victimas"]] = tabla[["casos", "victimas"]].astype(int)
    rep.update(registros_plata=int(len(eventos)), filas_plata=int(len(tabla)), delitos=int(tabla["delito"].nunique()),
               victimas_plata=int(tabla["victimas"].sum()),
               primer_mes=tabla["mes"].min().strftime("%Y-%m") if len(tabla) else None,
               ultimo_mes=tabla["mes"].max().strftime("%Y-%m") if len(tabla) else None)
    return tabla, rep


def main() -> int:
    asegurar_directorios()
    if not (BRONCE / "seguridad_meta.json").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan Bronce de seguridad o los municipios en Plata: corre antes bronce.seguridad y plata.municipios")
        return 1
    meta = leer_json(BRONCE / "seguridad_meta.json")
    crudos = {d: pd.read_parquet(BRONCE / f"mindefensa_{d}.parquet") for d in meta["delitos"] if (BRONCE / f"mindefensa_{d}.parquet").exists()}
    tabla, rep = limpiar(crudos, set(gpd.read_file(PLATA / "municipios.geojson")["codigo"]))
    tabla.to_parquet(PLATA / "seguridad_municipio_mensual.parquet", index=False)
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_seguridad.csv", index=False)
    escribir_proveniencia("seguridad", meta, rep)
    print("Plata de seguridad generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
