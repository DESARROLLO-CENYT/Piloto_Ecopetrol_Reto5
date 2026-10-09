"""Resguardos indigenas: Bronce -> Plata.

Entradas (Bronce): ant_resguardos.geojson (ANT), mininterior_resguardos_poblacion.csv, resguardos_meta.json.
Entrada (Plata):   municipios.geojson (el departamento, para recortar y para saber que municipios toca cada resguardo).
Salidas (Plata):   resguardos.geojson, reporte_calidad_resguardos.csv, proveniencia_resguardos.json.

Reglas:
  * Geometrias reparadas (make_valid) y recortadas a La Guajira: un resguardo compartido con Cesar o Magdalena (el
    Kogui-Malayo-Arhuaco de la Sierra Nevada) queda solo con su parte guajira; los que no tocan el departamento salen.
  * Pueblo normalizado: la ANT escribe WAYUU, WAYUÚ, WAYÚU o Wayuu -> "Wayuu".
  * Codigo del resguardo: "SIN ASIGNAR" o vacio -> nulo. La poblacion (Ministerio del Interior, proyeccion 2020) viene
    por resguardo y municipio: se suma la de los municipios de La Guajira y se une por ese codigo.
  * Area en km2 calculada en metros (EPSG:3116), total dentro del departamento; municipios que toca (lista de codigos).
  * Simplificacion a ~20 m conservando la topologia de cada poligono.
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios
from comun.ideam import sin_tildes
from comun.serializacion import escribir_proveniencia, leer_json, vertices

TOLERANCIA_GRADOS = 0.0002     # ~20 m
AREA_MINIMA_KM2 = 0.01          # menos que esto dentro del departamento es un roce de bordes
PUEBLOS = {"WAYUU": "Wayuu", "KOGUIMALAYOARHUACO": "Kogui, Malayo y Arhuaco", "IJKA": "Arhuaco (Ijka)", "KANKUAMO": "Kankuamo",
           "SIJONA": "Wayuu"}     # "Sijona" es un clan wayuu (el nombre del resguardo lo dice)


def pueblo(p) -> str | None:
    if p is None or (isinstance(p, float) and pd.isna(p)):
        return None
    clave = sin_tildes(str(p)).upper().replace(" ", "").replace("-", "")
    return PUEBLOS.get(clave, str(p).strip().title())


def codigo_resguardo(c) -> str | None:
    s = str(c).strip()
    return s.split(".")[0] if s and s.upper() not in ("NAN", "NONE", "SIN ASIGNAR") else None


def limpiar(bruto: gpd.GeoDataFrame, poblacion: pd.DataFrame, municipios: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    rep: dict = {"resguardos_bronce": int(len(bruto)), "vertices_bronce": vertices(bruto)}
    g = bruto.rename(columns={c: c.upper() for c in bruto.columns if c != "geometry"}).copy()
    rep["sin_geometria"] = int(g.geometry.isna().sum())
    g = g[g.geometry.notna()].copy()
    rep["geometrias_invalidas_reparadas"] = int((~g.is_valid).sum())
    g["geometry"] = g.geometry.make_valid()

    depto = municipios.geometry.union_all()
    g["geometry"] = g.geometry.intersection(depto)
    g = g[~g.geometry.is_empty].copy()
    g["geometry"] = g.geometry.apply(lambda x: shapely.union_all([p for p in getattr(x, "geoms", [x]) if p.geom_type in ("Polygon", "MultiPolygon")]))
    m = g.to_crs(CRS_METRICO)
    g["area_km2"] = (m.area / 1e6).round(2)
    rep["fuera_de_la_guajira"] = int(len(bruto) - rep["sin_geometria"] - (g["area_km2"] >= AREA_MINIMA_KM2).sum())
    g = g[g["area_km2"] >= AREA_MINIMA_KM2].copy()

    g["codigo_resguardo"] = g["CODIGO_DANE"].map(codigo_resguardo)
    rep["sin_codigo_resguardo"] = int(g["codigo_resguardo"].isna().sum())
    pob = poblacion.assign(codigo_resguardo=poblacion["c_digo_del_resguardo_dane"].map(codigo_resguardo),
                           poblacion=pd.to_numeric(poblacion["total_poblaci_n_proyecci"], errors="coerce"))
    total = pob.groupby("codigo_resguardo")["poblacion"].sum()
    g["poblacion_2020"] = g["codigo_resguardo"].map(total)
    rep["resguardos_con_poblacion"] = int(g["poblacion_2020"].notna().sum())
    rep["poblacion_sin_poligono"] = int(total[~total.index.isin(g["codigo_resguardo"])].sum())

    mm = municipios[["codigo", "geometry"]].to_crs(CRS_METRICO)
    toca = gpd.overlay(g[["geometry"]].assign(i=range(len(g))).to_crs(CRS_METRICO), mm, how="intersection", keep_geom_type=True)
    toca = toca[toca.area > AREA_MINIMA_KM2 * 1e6]
    g["municipios"] = [",".join(sorted(toca.loc[toca["i"] == i, "codigo"])) for i in range(len(g))]

    g["nombre"] = g["NOMBRE"].astype(str).str.replace("Resguardo Indigena", "Resguardo Indígena").str.strip()
    g["pueblo"] = g["PUEBLO"].map(pueblo)
    fecha = pd.to_datetime(pd.to_numeric(g["ULTIMA_FECHA_ACTO_ADMIN"], errors="coerce"), unit="ms", errors="coerce")
    g["ultimo_acto"] = (g["ULTIMO_TIPO_ACTO_ADMIN"].astype(str).str.capitalize() + " " + g["ULTIMO_NUMERO_ACTO_ADMIN"].astype(str)
                        + fecha.dt.strftime(" de %Y").fillna(""))
    g["anio_ultimo_acto"] = fecha.dt.year.astype("Int64")
    g["geometry"] = g.geometry.simplify(TOLERANCIA_GRADOS, preserve_topology=True).make_valid()
    g = g.reset_index(drop=True)
    g["id_resguardo"] = g["ID"].astype(str)
    g = gpd.GeoDataFrame(g[["id_resguardo", "codigo_resguardo", "nombre", "pueblo", "area_km2", "poblacion_2020", "municipios",
                            "ultimo_acto", "anio_ultimo_acto", "geometry"]], geometry="geometry", crs=CRS_GEOGRAFICO)
    g = g.sort_values("area_km2", ascending=False).reset_index(drop=True)
    rep.update(resguardos_plata=int(len(g)), vertices_plata=vertices(g), km2_resguardos=round(float(g["area_km2"].sum()), 1),
               km2_departamento=round(float(municipios.to_crs(CRS_METRICO).area.sum() / 1e6), 1))
    rep["pct_departamento_en_resguardo"] = round(rep["km2_resguardos"] / rep["km2_departamento"] * 100, 1)
    return g, rep


def main() -> int:
    asegurar_directorios()
    if not (BRONCE / "resguardos_meta.json").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan Bronce de resguardos o los municipios en Plata: corre antes bronce.resguardos y plata.municipios")
        return 1
    g, rep = limpiar(gpd.read_file(BRONCE / "ant_resguardos.geojson"),
                     pd.read_csv(BRONCE / "mininterior_resguardos_poblacion.csv", dtype=str),
                     gpd.read_file(PLATA / "municipios.geojson"))
    g.to_file(PLATA / "resguardos.geojson", driver="GeoJSON")
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_resguardos.csv", index=False)
    escribir_proveniencia("resguardos", leer_json(BRONCE / "resguardos_meta.json"), rep)
    print("Plata de resguardos generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
