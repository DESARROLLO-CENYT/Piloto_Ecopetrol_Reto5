"""Vias del IGAC (1:100.000): Bronce -> Plata.

Entradas (Bronce): data/bronze/igac_via_*.geojson y vias_igac_meta.json.
Entrada (Plata):   data/silver/municipios.geojson (para recortar al departamento; si no esta, se usa la caja).
Salidas (Plata):   data/silver/igac_vias.geojson, reporte_calidad_vias_igac.csv, proveniencia_vias_igac.json.
No hay Oro propio: se une con INVIAS en `plata/red_vial.py`.

El servicio publica siete capas: seis "tipos de via" y los caminos. No documenta que significa
cada tipo, pero sus atributos lo dejan claro (cada tipo tiene siempre la misma combinacion de
superficie, ancho y accesibilidad), asi que aqui se nombran por lo que son:

  1 pavimentada, 2 o mas carriles      4 sin pavimentar, angosta
  2 sin pavimentar, 2 o mas carriles   5 sin pavimentar, solo en tiempo seco
  3 pavimentada, angosta               6 sin afirmar (trocha), solo en tiempo seco
  7 camino o sendero

Plata: une las siete capas, traduce los dominios, recorta a La Guajira (union de los municipios
del DANE si ya se descargaron; si no, a la caja de descarga) y simplifica a 20 m.

Uso:  python -m plata.vias_igac   (despues de bronce.vias_igac y plata.municipios)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import box

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json

TOLERANCIA_M = 20
LARGO_MINIMO_M = 30        # tras recortar, los pedazos menores son astillas del borde

ARCHIVOS = ["igac_via_tipo1", "igac_via_tipo2", "igac_via_tipo3", "igac_via_tipo4", "igac_via_tipo5", "igac_via_tipo6", "igac_via_caminos"]
CLASE = {
    1: "Pavimentada, 2 o más carriles", 2: "Sin pavimentar, 2 o más carriles", 3: "Pavimentada, angosta",
    4: "Sin pavimentar, angosta", 5: "Sin pavimentar, solo en tiempo seco", 6: "Sin afirmar (trocha), solo en tiempo seco",
    7: "Camino o sendero",
}
# dominios de la fuente (codigo -> etiqueta); "Sin Valor" = vacio
SUPERFICIE = {"3301": "Pavimentada", "3306": "Sin pavimentar", "1302": "En construcción", "3350": "Sin afirmar"}
CARRILES = {"3501": "2 o más carriles", "3502": "Angosta"}
ACCESIBILIDAD = {"3600": "Todo el año", "3601": "Solo en tiempo seco"}


def _vertices(gdf) -> int:
    return int(shapely.get_num_coordinates(gdf.geometry.values).sum())


def _traducir(serie: pd.Series, dominio: dict) -> pd.Series:
    return serie.astype("string").str.strip().map(dominio)


def limpiar(capas: list[gpd.GeoDataFrame], limite, caja: dict) -> tuple[gpd.GeoDataFrame, dict]:
    """`capas`: las siete capas de Bronce en EPSG:4326. `limite`: poligono de recorte (EPSG:4326) o None."""
    rep: dict = {}
    g = pd.concat(capas, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=CRS_GEOGRAFICO)
    rep["objetos_bronce"] = int(len(g))
    rep["vertices_bronce"] = _vertices(g)

    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    rep["sin_geometria"] = rep["objetos_bronce"] - int(len(g))
    g["tipo"] = pd.to_numeric(g["tipo_via"], errors="coerce").astype("Int64")
    rep["tipo_desconocido"] = int((~g["tipo"].isin(CLASE)).sum())
    g = g[g["tipo"].isin(CLASE)].copy()

    # recorte en grados (una caja o un borde reproyectados a metros se corren)
    recorte = limite if limite is not None else box(caja["lon_oeste"], caja["lat_sur"], caja["lon_este"], caja["lat_norte"])
    rep["recortada_a"] = "municipios del DANE" if limite is not None else "caja de descarga"
    g["geometry"] = g.geometry.intersection(recorte)
    dentro = g[~g.geometry.is_empty]
    rep["fuera_del_limite"] = int(len(g) - len(dentro))
    g = dentro.copy()

    g = g.to_crs(CRS_METRICO)
    g["geometry"] = g.geometry.simplify(TOLERANCIA_M, preserve_topology=True)
    antes = len(g)
    g = g.explode(index_parts=False)                           # el recorte puede dejar varias partes
    rep["partes_nuevas_por_recorte"] = int(len(g) - antes)
    utiles = g[g.geom_type.isin(["LineString", "MultiLineString"]) & (g.length >= LARGO_MINIMO_M)]
    rep["astillas_descartadas"] = int(len(g) - len(utiles))
    g = utiles.copy()
    g["km"] = (g.length / 1000).round(3)
    g = g.to_crs(CRS_GEOGRAFICO)
    g["geometry"] = shapely.set_precision(g.geometry.values, 1e-5)

    g["clase"] = g["tipo"].map(CLASE)
    g["superficie"] = _traducir(g["estado_superficie"], SUPERFICIE)
    g["carriles"] = _traducir(g["numero_carriles"], CARRILES)
    g["accesibilidad"] = _traducir(g["accesibilidad"], ACCESIBILIDAD)
    g["nombre"] = g["nombre_geografico"].astype("string").str.strip().replace("", pd.NA)
    rep["atributos_sin_valor"] = int(((g["tipo"] < 7) & g["superficie"].isna()).sum())

    g = g.sort_values(["tipo", "objectid"]).reset_index(drop=True)
    g.insert(0, "id_via", "v" + g["tipo"].astype(str) + "-" + g["objectid"].astype(str) + "-" + (g.groupby(["tipo", "objectid"]).cumcount() + 1).astype(str))
    g = g[["id_via", "tipo", "clase", "superficie", "carriles", "accesibilidad", "nombre", "km", "geometry"]]

    por_tipo = g.groupby("tipo")["km"].sum()
    rep.update(
        objetos_plata=int(len(g)), vertices_plata=_vertices(g), km_total=round(float(g["km"].sum())),
        km_pavimentadas=round(float(por_tipo.reindex([1, 3]).sum())),
        km_solo_tiempo_seco=round(float(g.loc[g["accesibilidad"] == "Solo en tiempo seco", "km"].sum())),
        km_caminos=round(float(por_tipo.get(7, 0))),
    )
    return g, rep


def main() -> int:
    asegurar_directorios()
    meta_ruta = BRONCE / "vias_igac_meta.json"
    if not meta_ruta.exists():
        print("Falta data/bronze/vias_igac_meta.json: corre primero bronce.vias_igac")
        return 1
    meta = leer_json(meta_ruta)
    capas = [gpd.read_file(BRONCE / f"{a}.geojson") for a in ARCHIVOS]

    limite = None
    mun = PLATA / "municipios.geojson"
    if mun.exists():
        limite = gpd.read_file(mun).geometry.union_all()
    else:
        print("Aviso: sin municipios del DANE en Plata; se recorta a la caja (corre plata.municipios y vuelve a correr esto)")

    g, rep = limpiar(capas, limite, meta["caja"])
    g.to_file(PLATA / "igac_vias.geojson", driver="GeoJSON")
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_vias_igac.csv", index=False)
    escribir_proveniencia("vias_igac", meta, rep)

    print("Plata de las vías del IGAC generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
