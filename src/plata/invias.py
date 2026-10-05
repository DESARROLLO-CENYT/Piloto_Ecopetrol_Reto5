"""Red Vial Nacional (INVIAS): Bronce -> Plata -> Oro.

Plata: traduce los codigos de dominio, cambia los "Por Defnir" por vacio, quita los
tramos cuya geometria ya esta cubierta por otros, recorta a la caja de descarga,
simplifica la geometria (15 m) y recalcula la longitud en metros.
Oro: los tramos de la territorial Guajira de INVIAS, listos para el mapa.

Uso:  python invias_a_oro.py   (despues de ingesta_invias.py)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import box

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json

TERRITORIAL_GUAJIRA = 13
TOLERANCIA_M = 15          # simplificacion: menor que el ancho de una calzada en el mapa
BUFFER_SOLAPE_M = 30       # holgura para decidir si dos lineas son la misma via
UMBRAL_SOLAPE = 0.95       # fraccion de un tramo cubierta por los demas para considerarlo repetido

# Dominios de la fuente (descripcion de cada columna en datos.gov.co)
ADMINISTRADOR = {1: "INVIAS", 2: "ANI", 3: "Concesión departamental", 4: "FINDETER", 5: "Vía en desuso", 6: "INVIAS - convenios"}
CALZADA = {1: "Sencilla", 2: "Doble"}
CATEGORIA = {1: "Primer orden", 2: "Segundo orden", 3: "Tercer orden"}
SUPERFICIE = {1: "Pavimentada", 2: "Sin pavimentar"}
TERRITORIAL = {
    1: "Antioquia", 2: "Atlántico", 3: "Bolívar", 4: "Boyacá", 5: "Caldas", 6: "Caquetá", 7: "Casanare", 8: "Cauca",
    9: "Cesar", 10: "Chocó", 11: "Córdoba", 12: "Cundinamarca", 13: "Guajira", 14: "Huila", 15: "Magdalena",
    16: "Meta", 17: "Nariño", 18: "Norte de Santander", 19: "Putumayo", 20: "Quindío", 21: "Risaralda",
    22: "Santander", 23: "Sucre", 24: "Tolima", 25: "Valle del Cauca", 26: "Ocaña",
}
POR_DEFINIR = {"por defnir", "por definir", ""}


def _vertices(gdf: gpd.GeoDataFrame) -> int:
    return int(shapely.get_num_coordinates(gdf.geometry.values).sum())


def _traducir(serie: pd.Series, dominio: dict) -> pd.Series:
    """Codigo numerico -> etiqueta; los codigos "por definir" (3 o 4 segun la columna) quedan vacios."""
    return pd.to_numeric(serie, errors="coerce").map(dominio)


def quitar_repetidos(g: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, int]:
    """La fuente trae un tramo que es la suma de otros dos (misma via, geometria repetida).
    De mas largo a mas corto, se descarta el que ya esta cubierto >= 95 % por los demas que quedan."""
    g = g.assign(_len=g.length).sort_values("_len", ascending=False)
    conservar = set(g.index)
    for i in g.index:
        resto = [j for j in conservar if j != i]
        if not resto:
            continue
        cubierto = g.loc[resto].geometry.union_all().buffer(BUFFER_SOLAPE_M).intersection(g.geometry[i]).length
        if g["_len"][i] > 0 and cubierto / g["_len"][i] >= UMBRAL_SOLAPE:
            conservar.discard(i)
    quitados = len(g) - len(conservar)
    return g.loc[sorted(conservar)].drop(columns="_len"), quitados


def limpiar(bruto: gpd.GeoDataFrame, caja: dict) -> tuple[gpd.GeoDataFrame, dict]:
    rep: dict = {"tramos_bronce": int(len(bruto)), "vertices_bronce": _vertices(bruto)}
    g = bruto[bruto.geometry.notna() & ~bruto.geometry.is_empty].copy()
    rep["sin_geometria"] = int(len(bruto) - len(g))

    g = g.to_crs(CRS_METRICO)
    # se compara con la longitud original (sin recortar) que trae la fuente
    rep["longitud_no_coincide"] = int(
        ((g.length - pd.to_numeric(g["shape__length"], errors="coerce")).abs() > 0.05 * g.length).sum()
    )

    # simplificar primero: comparar lineas de 10 mil vertices entre si tarda minutos
    g["geometry"] = g.geometry.simplify(TOLERANCIA_M, preserve_topology=True)
    g, rep["repetidos_removidos"] = quitar_repetidos(g)

    # recorte en grados: una caja reproyectada a metros deja de ser un rectangulo y corta torcido
    g = g.to_crs(CRS_GEOGRAFICO)
    g["geometry"] = g.geometry.intersection(box(caja["lon_oeste"], caja["lat_sur"], caja["lon_este"], caja["lat_norte"]))
    g = g[~g.geometry.is_empty].to_crs(CRS_METRICO).copy()

    g["longitud_km"] = (g.length / 1000).round(2)

    for col in ("nombre_tramo", "sector", "nombre_ruta"):
        g[col] = g[col].astype("string").str.strip()
    rep["nombre_tramo_por_definir"] = int(g["nombre_tramo"].str.lower().isin(POR_DEFINIR).sum())
    g["nombre_tramo"] = g["nombre_tramo"].mask(g["nombre_tramo"].str.lower().isin(POR_DEFINIR))

    g["administrador_txt"] = _traducir(g["administrador"], ADMINISTRADOR)
    g["categoria_txt"] = _traducir(g["categoria"], CATEGORIA)
    g["superficie_txt"] = _traducir(g["superficie"], SUPERFICIE)
    g["calzada_txt"] = _traducir(g["calzada"], CALZADA)
    g["territorial_txt"] = _traducir(g["territorial"], TERRITORIAL)
    rep["superficie_por_definir"] = int(g["superficie_txt"].isna().sum())
    rep["categoria_por_definir"] = int(g["categoria_txt"].isna().sum())

    g["territorial"] = pd.to_numeric(g["territorial"], errors="coerce").astype("Int64")
    g["en_guajira"] = g["territorial"] == TERRITORIAL_GUAJIRA
    g = g.to_crs(CRS_GEOGRAFICO)
    g["geometry"] = shapely.set_precision(g.geometry.values, 1e-5)   # ~1 m: quita decimales de mas

    g = g.sort_values(["ruta", "codigo_tramo", "distancia_inicial"]).reset_index(drop=True)
    g.insert(0, "id_tramo", [f"{r.ruta}-{r.codigo_tramo}-{i + 1}" for i, r in g.iterrows()])
    rep.update(tramos_plata=int(len(g)), vertices_plata=_vertices(g), km_plata=round(float(g["longitud_km"].sum()), 1))
    return g, rep


def main() -> int:
    asegurar_directorios()
    ruta = BRONCE / "invias_red_vial.geojson"
    if not ruta.exists():
        print("Falta data/bronze/invias_red_vial.geojson: corre primero bronce.invias")
        return 1
    meta = leer_json(BRONCE / "invias_meta.json")
    g, rep = limpiar(gpd.read_file(ruta), meta["caja"])

    columnas = [
        "id_tramo", "codigo_tramo", "ruta", "nombre_ruta", "nombre_tramo", "sector", "categoria_txt", "administrador_txt",
        "superficie_txt", "calzada_txt", "territorial_txt", "en_guajira", "longitud_km", "fuente",
    ]
    g[columnas + ["geometry"]].to_file(PLATA / "invias_red_vial.geojson", driver="GeoJSON")
    rep["tramos_territorial_guajira"] = int(g["en_guajira"].sum())
    rep["km_territorial_guajira"] = round(float(g.loc[g["en_guajira"], "longitud_km"].sum()), 1)
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_invias.csv", index=False)
    escribir_proveniencia("invias", meta, rep)

    print("Plata de la red vial de INVIAS generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
