"""Lluvia mensual CHIRPS v3: Bronce -> Plata (lluvia por municipio y por mes).

Entradas (Bronce): data/bronze/chirps/chirps_v3_AAAA_MM.tif (rejilla de 0,05 grados, mm del mes; -9999 en el mar) y chirps_meta.json.
Entrada (Plata):   data/silver/municipios.geojson (los 15 municipios del DANE).
Salidas (Plata):   data/silver/chirps_municipio_mensual.parquet, reporte_calidad_chirps.csv, proveniencia_chirps.json.

La lluvia de un municipio en un mes es el promedio de las celdas que lo cubren, ponderado por el AREA de cada celda que cae
dentro del municipio (una celda en el borde cuenta solo por la parte que esta adentro). Las areas se calculan en metros
(EPSG:3116). Las celdas sin dato (mar) no cuentan; la columna `fraccion_con_dato` dice que parte del municipio tuvo dato.
Tambien se calcula el departamento completo (codigo 44).

Uso:  python -m plata.chirps   (despues de bronce.chirps y plata.municipios)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import box

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json

CARPETA = BRONCE / "chirps"
MAXIMO_MM_MES = 2500.0      # por encima es un error (el mes mas lluvioso de La Guajira no pasa de unos cientos de mm)
AREA_MINIMA_M2 = 10_000.0   # 1 ha de una celda de ~3.000 ha: menos que eso es un roce de bordes al reproyectar


def pesos_por_municipio(transform, alto: int, ancho: int, municipios: gpd.GeoDataFrame) -> pd.DataFrame:
    """Para cada municipio, que celdas lo cubren y con cuanta area (m2). Una fila por (codigo, fila, columna)."""
    filas, cols = np.meshgrid(np.arange(alto), np.arange(ancho), indexing="ij")
    filas, cols = filas.ravel(), cols.ravel()
    x0, y0 = transform.c + transform.a * cols, transform.f + transform.e * filas         # rejilla sin rotacion
    x1, y1 = x0 + transform.a, y0 + transform.e
    celdas = gpd.GeoDataFrame({"fila": filas, "col": cols},
                              geometry=[box(a, d, c, b) for a, b, c, d in zip(x0, y0, x1, y1)], crs=CRS_GEOGRAFICO).to_crs(CRS_METRICO)
    mun = municipios[["codigo", "nombre", "geometry"]].to_crs(CRS_METRICO)
    cruce = gpd.overlay(celdas, mun, how="intersection", keep_geom_type=True)
    cruce["area_m2"] = cruce.area
    cruce = cruce[cruce["area_m2"] >= AREA_MINIMA_M2]     # astillas del borde compartido: no son cobertura real
    return cruce[["codigo", "nombre", "fila", "col", "area_m2"]].reset_index(drop=True)


def lluvia_por_zona(valores: np.ndarray, pesos: pd.DataFrame, nodata: float) -> pd.DataFrame:
    """Promedio ponderado por area de las celdas con dato, por zona (`codigo`). Devuelve mm y fraccion del area con dato."""
    v = valores[pesos["fila"].to_numpy(), pesos["col"].to_numpy()].astype(float)
    valido = np.isfinite(v) & (v != nodata) & (v >= 0) & (v <= MAXIMO_MM_MES)
    p = pesos.assign(v=np.where(valido, v, 0.0), w_valido=np.where(valido, pesos["area_m2"], 0.0))
    g = p.assign(vw=p["v"] * p["w_valido"]).groupby(["codigo", "nombre"]).agg(vw=("vw", "sum"), w=("w_valido", "sum"), w_total=("area_m2", "sum"))
    g["mm"] = np.where(g["w"] > 0, g["vw"] / g["w"].where(g["w"] > 0), np.nan)
    g["fraccion_con_dato"] = (g["w"] / g["w_total"]).round(4)
    return g[["mm", "fraccion_con_dato"]].reset_index()


def procesar(archivos: list, municipios: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict]:
    rep: dict = {"meses_bronce": len(archivos)}
    if not archivos:
        return pd.DataFrame(columns=["codigo", "municipio", "mes", "mm", "fraccion_con_dato"]), rep
    with rasterio.open(archivos[0]) as r0:
        transform, forma, nodata = r0.transform, (r0.height, r0.width), r0.nodata if r0.nodata is not None else -9999.0
    pesos = pesos_por_municipio(transform, *forma, municipios)
    departamento = pesos.assign(codigo="44", nombre="La Guajira")   # el departamento entero, con los mismos pesos
    pesos_todos = pd.concat([pesos, departamento], ignore_index=True)
    rep["celdas_ventana"] = forma[0] * forma[1]
    rep["celdas_en_municipios"] = int(pesos[["fila", "col"]].drop_duplicates().shape[0])

    partes, distinta, invalidas, sin_dato = [], 0, 0, 0
    for ruta in archivos:
        with rasterio.open(ruta) as r:
            if (r.height, r.width) != forma or r.transform != transform:
                distinta += 1          # no deberia pasar: todas las ventanas salen de la misma caja
                continue
            a = r.read(1)
        tierra = a[pesos["fila"].to_numpy(), pesos["col"].to_numpy()]
        invalidas += int(((tierra != nodata) & ((tierra < 0) | (tierra > MAXIMO_MM_MES) | ~np.isfinite(tierra))).sum())
        sin_dato += int((tierra == nodata).sum())
        anio, mes = ruta.stem.split("_")[-2:]
        z = lluvia_por_zona(a, pesos_todos, nodata).assign(mes=pd.Timestamp(int(anio), int(mes), 1))
        partes.append(z)
    tabla = pd.concat(partes, ignore_index=True).rename(columns={"nombre": "municipio"})
    tabla["mm"] = tabla["mm"].round(1)
    tabla = tabla.sort_values(["codigo", "mes"]).reset_index(drop=True)[["codigo", "municipio", "mes", "mm", "fraccion_con_dato"]]
    rep.update(meses_con_otra_rejilla=distinta, valores_fuera_de_rango=invalidas, celdas_municipio_sin_dato=sin_dato,
               meses_plata=int(tabla["mes"].nunique()), zonas=int(tabla["codigo"].nunique()),
               filas_plata=int(len(tabla)), filas_sin_lluvia=int(tabla["mm"].isna().sum()),
               mm_maximo_mensual=float(tabla["mm"].max()),
               desde=tabla["mes"].min().strftime("%Y-%m"), hasta=tabla["mes"].max().strftime("%Y-%m"))
    return tabla, rep


def main() -> int:
    asegurar_directorios()
    if not (BRONCE / "chirps_meta.json").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan Bronce de CHIRPS o los municipios en Plata: corre antes bronce.chirps y plata.municipios")
        return 1
    archivos = sorted(CARPETA.glob("chirps_v3_*.tif"))
    tabla, rep = procesar(archivos, gpd.read_file(PLATA / "municipios.geojson"))
    tabla.to_parquet(PLATA / "chirps_municipio_mensual.parquet", index=False)
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_chirps.csv", index=False)
    escribir_proveniencia("chirps", leer_json(BRONCE / "chirps_meta.json"), rep)
    print("Plata de CHIRPS generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
