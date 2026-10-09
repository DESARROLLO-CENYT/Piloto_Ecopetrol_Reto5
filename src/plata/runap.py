"""Areas protegidas (RUNAP): Bronce -> Plata.

Entradas (Bronce): runap_areas_protegidas.geojson, runap_meta.json.
Entrada (Plata):   municipios.geojson (el departamento).
Salidas (Plata):   areas_protegidas_runap.geojson, reporte_calidad_runap.csv, proveniencia_runap.json.

Reglas:
  * Se conservan las areas que tocan tierra de La Guajira o su franja costera (2 km): las marinas costeras
    (Bahia Portete, Pastos Marinos Sawairu) quedan completas, con su parte de mar; las de Cesar o Magdalena que no
    llegan al departamento salen. La geometria se recorta solo a la caja de descarga.
  * `ambito`: nacional (Parques Nacionales), regional (corporaciones autonomas) o privada (reservas de la sociedad civil).
  * Area total y area dentro del departamento (tierra) en km2, calculadas en metros (EPSG:3116).
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from comun.config import BRONCE, CAJA_DESCARGA, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json, vertices

FRANJA_COSTERA_M = 2000
TOLERANCIA_GRADOS = 0.0002


def ambito(categoria: str, organizacion: str) -> str:
    c, o = str(categoria).lower(), str(organizacion).lower()
    if "sociedad civil" in c:
        return "privada"
    if "corporación" in o or "corporacion" in o or "regional" in c:
        return "regional"
    return "nacional"


def limpiar(bruto: gpd.GeoDataFrame, municipios: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    rep: dict = {"areas_bronce": int(len(bruto)), "vertices_bronce": vertices(bruto)}
    g = bruto.rename(columns={c: c.lower() for c in bruto.columns if c != "geometry"}).copy()
    rep["sin_geometria"] = int(g.geometry.isna().sum())
    g = g[g.geometry.notna()].copy()
    rep["geometrias_invalidas_reparadas"] = int((~g.is_valid).sum())
    g["geometry"] = g.geometry.make_valid()

    depto_m = municipios.to_crs(CRS_METRICO).geometry.union_all()
    zona = gpd.GeoSeries([depto_m.buffer(FRANJA_COSTERA_M)], crs=CRS_METRICO).to_crs(CRS_GEOGRAFICO).iloc[0]
    toca = g.geometry.intersects(zona)
    rep["fuera_de_la_guajira"] = int((~toca).sum())
    g = g[toca].copy()
    caja = box(CAJA_DESCARGA["lon_oeste"], CAJA_DESCARGA["lat_sur"], CAJA_DESCARGA["lon_este"], CAJA_DESCARGA["lat_norte"])
    g["geometry"] = g.geometry.intersection(caja)

    m = g.to_crs(CRS_METRICO)
    g["area_km2"] = (m.area / 1e6).round(2)
    g["area_en_guajira_km2"] = (m.geometry.intersection(depto_m).area / 1e6).round(2)
    g["nombre"] = g["ap_nombre"].astype(str).str.split().str.join(" ")
    g["categoria"] = g["ap_categoria"].astype(str).str.strip()
    g["organizacion"] = g["organizacion"].astype(str).str.strip()
    g["ambito"] = [ambito(c, o) for c, o in zip(g["categoria"], g["organizacion"])]
    g["inscrita"] = pd.to_datetime(pd.to_numeric(g.get("fecha_inscrita"), errors="coerce"), unit="ms", errors="coerce").dt.year.astype("Int64")
    g["geometry"] = g.geometry.simplify(TOLERANCIA_GRADOS, preserve_topology=True).make_valid()
    g["id_area"] = g["ap_id"].astype(str)
    g = gpd.GeoDataFrame(g[["id_area", "nombre", "categoria", "ambito", "organizacion", "area_km2", "area_en_guajira_km2", "inscrita", "geometry"]],
                         geometry="geometry", crs=CRS_GEOGRAFICO).sort_values("area_km2", ascending=False).reset_index(drop=True)
    rep.update(areas_plata=int(len(g)), vertices_plata=vertices(g),
               nacionales=int((g["ambito"] == "nacional").sum()), regionales=int((g["ambito"] == "regional").sum()),
               privadas=int((g["ambito"] == "privada").sum()), km2_en_guajira=round(float(g["area_en_guajira_km2"].sum()), 1))
    return g, rep


def main() -> int:
    asegurar_directorios()
    if not (BRONCE / "runap_meta.json").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan Bronce del RUNAP o los municipios en Plata: corre antes bronce.runap y plata.municipios")
        return 1
    g, rep = limpiar(gpd.read_file(BRONCE / "runap_areas_protegidas.geojson"), gpd.read_file(PLATA / "municipios.geojson"))
    g.to_file(PLATA / "areas_protegidas_runap.geojson", driver="GeoJSON")
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_runap.csv", index=False)
    escribir_proveniencia("runap", leer_json(BRONCE / "runap_meta.json"), rep)
    print("Plata de áreas protegidas generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
