"""Red vial unificada: INVIAS (red nacional) + IGAC (red completa) en una sola tabla, sin duplicados.

Entradas (Plata): data/silver/invias_red_vial.geojson e igac_vias.geojson.
Salidas (Plata):  data/silver/red_vial.geojson, reporte_calidad_red_vial.csv, proveniencia_red_vial.json.
(La capa Oro `red_vial` se arma en `oro/red_vial.py`.)

Las dos fuentes dibujan las mismas carreteras principales (la nacional de INVIAS viene de la misma
cartografia base del IGAC), asi que sumarlas tal cual contaria ~300 km dos veces. Aqui:

  1. Se conserva la red nacional de INVIAS completa: trae ruta, nombre de la ruta, sector,
     administrador y categoria, que el IGAC no tiene.
  2. Del IGAC se quita lo que ya esta dentro de 50 m de una via de INVIAS (los pedazos que
     quedan menores a 100 m son astillas y tambien se quitan). Queda la red complementaria:
     secundarias, terciarias, trochas y caminos.
  3. A cada tramo de INVIAS, cuya superficie viene "por definir", se le pone la que dice el
     IGAC en ese mismo trazado (si una sola clase cubre al menos el 60 % de su longitud).

La columna `fuente` (INVIAS / IGAC) y `estilo` permiten distinguir cada red en el mapa.

Uso:  python -m plata.red_vial   (despues de plata.invias y plata.vias_igac)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from comun.config import CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_proveniencia

BUFFER_SOLAPE_M = 50        # una via del IGAC a menos de esto de una de INVIAS es la misma via
LARGO_MINIMO_M = 100        # pedazos menores que quedan junto a la via nacional
COBERTURA_SUPERFICIE = 0.6  # fraccion de un tramo de INVIAS que debe compartir superficie en el IGAC

ESTILO_INVIAS = {"Primer orden": "n1", "Segundo orden": "n2"}   # sin categoria: "n0"


def _vertices(g) -> int:
    return int(shapely.get_num_coordinates(g.geometry.values).sum())


def superficie_desde_igac(inv: gpd.GeoDataFrame, igac: gpd.GeoDataFrame) -> pd.Series:
    """Superficie de cada tramo de INVIAS segun el IGAC que lo cubre; vacio si no hay una clase dominante."""
    out = []
    indice = igac.sindex
    for geom in inv.geometry:
        zona = geom.buffer(BUFFER_SOLAPE_M)
        cand = igac.iloc[indice.query(zona, predicate="intersects")]
        cand = cand[cand["superficie"].notna()]
        if cand.empty:
            out.append(None)
            continue
        largo = cand.geometry.intersection(zona).length.groupby(cand["superficie"].values).sum()
        out.append(largo.idxmax() if largo.max() >= COBERTURA_SUPERFICIE * geom.length else None)
    return pd.Series(out, index=inv.index, dtype="object")


def unir(inv: gpd.GeoDataFrame, igac: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    """`inv`: tramos de INVIAS de la territorial Guajira; `igac`: red del IGAC. Ambos en EPSG:4326."""
    rep: dict = {"tramos_invias": int(len(inv)), "tramos_igac": int(len(igac))}
    inv_m, igac_m = inv.to_crs(CRS_METRICO), igac.to_crs(CRS_METRICO)
    rep["km_invias"] = round(float(inv_m.length.sum()) / 1000, 1)
    rep["km_igac"] = round(float(igac_m.length.sum()) / 1000, 1)

    # 3. superficie de INVIAS tomada del IGAC
    inv_m = inv_m.copy()
    inv_m["superficie_igac"] = superficie_desde_igac(inv_m, igac_m)
    rep["tramos_invias_con_superficie_del_igac"] = int(inv_m["superficie_igac"].notna().sum())

    # 2. lo del IGAC que ya es red nacional
    zona = inv_m.union_all().buffer(BUFFER_SOLAPE_M)
    resto = igac_m.copy()
    resto["geometry"] = igac_m.geometry.difference(zona)
    resto = resto[~resto.geometry.is_empty].explode(index_parts=False)
    resto = resto[resto.geom_type.isin(["LineString", "MultiLineString"])]
    quitado = float(igac_m.length.sum() - resto.length.sum())
    resto = resto[resto.length >= LARGO_MINIMO_M].copy()
    rep["km_igac_repetido_con_invias"] = round(quitado / 1000, 1)
    rep["km_igac_astillas_quitadas"] = round(float(igac_m.length.sum() - quitado - resto.length.sum()) / 1000, 1)

    # tabla unificada
    a = pd.DataFrame({
        "id_tramo": "invias-" + inv_m["id_tramo"].astype(str), "fuente": "INVIAS", "grupo": "Red nacional",
        "estilo": inv_m["categoria_txt"].map(ESTILO_INVIAS).fillna("n0"),
        "clase": "Red nacional, " + inv_m["categoria_txt"].str.lower().fillna("sin categoría"),
        "ruta": inv_m["ruta"], "nombre_ruta": inv_m["nombre_ruta"], "sector": inv_m["sector"],
        "administrador": inv_m["administrador_txt"], "calzada": inv_m["calzada_txt"],
        "superficie": inv_m["superficie_txt"].fillna(inv_m["superficie_igac"]),
        "superficie_fuente": np.where(inv_m["superficie_txt"].notna(), "INVIAS", np.where(inv_m["superficie_igac"].notna(), "IGAC (cruce espacial)", None)),
        "carriles": None, "accesibilidad": None, "nombre": None,
        "geometry": inv_m.geometry,
    })
    b = pd.DataFrame({
        "id_tramo": "igac-" + resto["id_via"].astype(str), "fuente": "IGAC", "grupo": "Red complementaria",
        "estilo": "i" + resto["tipo"].astype(str), "clase": resto["clase"],
        "ruta": None, "nombre_ruta": None, "sector": None, "administrador": None, "calzada": None,
        "superficie": resto["superficie"], "superficie_fuente": resto["superficie"].notna().map({True: "IGAC", False: None}),
        "carriles": resto["carriles"], "accesibilidad": resto["accesibilidad"], "nombre": resto["nombre"],
        "geometry": resto.geometry,
    })
    # el IGAC va primero: en el mapa se dibuja debajo de la red nacional
    red = gpd.GeoDataFrame(pd.concat([b, a], ignore_index=True), geometry="geometry", crs=CRS_METRICO)
    red["km"] = (red.length / 1000).round(3)
    red = red.to_crs(CRS_GEOGRAFICO)
    red["geometry"] = shapely.set_precision(red.geometry.values, 1e-5)

    por_fuente = red.groupby("fuente")["km"].sum()
    rep["tramos_igac_conservados"] = int((red["fuente"] == "IGAC").sum())
    rep.update(
        tramos_red=int(len(red)), vertices_red=_vertices(red),
        km_red=round(float(red["km"].sum())), km_red_nacional=round(float(por_fuente.get("INVIAS", 0)), 1),
        km_red_complementaria=round(float(por_fuente.get("IGAC", 0))),
        km_solo_tiempo_seco=round(float(red.loc[red["accesibilidad"] == "Solo en tiempo seco", "km"].sum())),
    )
    return red, rep


def main() -> int:
    asegurar_directorios()
    f_inv, f_igac = PLATA / "invias_red_vial.geojson", PLATA / "igac_vias.geojson"
    if not (f_inv.exists() and f_igac.exists()):
        print("Faltan las vias de INVIAS o del IGAC en Plata: corre antes plata.invias y plata.vias_igac")
        return 1
    inv = gpd.read_file(f_inv)
    inv = inv[inv["en_guajira"]]
    red, rep = unir(inv, gpd.read_file(f_igac))
    red.to_file(PLATA / "red_vial.geojson", driver="GeoJSON")
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_red_vial.csv", index=False)
    escribir_proveniencia("red_vial", {"invias": leer_proveniencia("invias")["bronce"], "igac": leer_proveniencia("vias_igac")["bronce"]}, rep)

    print("Red vial unificada generada (Plata)")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
