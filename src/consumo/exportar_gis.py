"""
Exporta la capa Oro a un GeoPackage (.gpkg), una capa por tema, para abrir directamente en ArcGIS Pro / ArcGIS
Enterprise o QGIS, y a GeoJSON individuales como respaldo. Confirma que la estructura de datos del piloto es agnostica
del software SIG, tal como pide el Anexo 1 del reto.

Capas (en EPSG:4326):
  modelo       paquetes_ict, puntos_crisis, zonas_intervencion, grid_calor, riesgos, riesgo_ejecucion_paquetes,
               contexto_paquetes, proyectos
  territorio   municipios, limite_departamental, resguardos, areas_protegidas_runap, red_vial, rios, cuerpos_agua,
  (real)       estaciones_ideam
  sinteticas   comunidades_sinteticas, areas_protegidas_sinteticas, hidrologia_sintetica, vias_sinteticas (las que usaba
               la primera version del modelo; se nombran asi para no confundirlas con las reales)
  tablas       alertas (sin geometria) y leeme: origen, fuente y uso permitido de cada capa
"""
from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd
import pyogrio

from comun.config import EXPORTS, ORO, asegurar_directorios

# capa del GeoPackage -> (archivo de Oro, origen, fuente y uso)
CAPAS = {
    "paquetes_ict": ("paquetes_ict.geojson", "calculado", "ICT por paquete: registro de riesgos SINTÉTICO + territorio real"),
    "puntos_crisis": ("puntos_crisis.geojson", "calculado", "Dónde un evento podría escalar a crisis (reglas de parametros.yaml)"),
    "zonas_intervencion": ("zonas_intervencion.geojson", "calculado", "Zonas de intervención prioritaria (área de influencia de los puntos de crisis)"),
    "grid_calor": ("grid_calor.geojson", "calculado", "Densidad kernel de amenazas y oportunidades y puntos calientes Gi* (celdas de ~2 km)"),
    "riesgos": ("riesgos.geojson", "sintético", "Registro de riesgos SINTÉTICO, con su calificación RAM y lo que hizo la IA con el texto"),
    "proyectos": ("proyectos.geojson", "sintético", "Límites de los proyectos SINTÉTICOS"),
    "municipios": ("municipios.geojson", "real", "DANE, Marco Geoestadístico Nacional"),
    "limite_departamental": ("limite_departamental.geojson", "real", "DANE, Marco Geoestadístico Nacional"),
    "resguardos": ("resguardos.geojson", "real", "Agencia Nacional de Tierras; población: Ministerio del Interior"),
    "areas_protegidas_runap": ("areas_protegidas_runap.geojson", "real", "RUNAP, Parques Nacionales Naturales de Colombia"),
    "red_vial": ("red_vial.geojson", "real", "INVIAS (CC BY-SA 4.0) + IGAC 1:100.000 (uso libre sin fines comerciales)"),
    "rios": ("rios.geojson", "real", "IGAC 1:100.000 (uso libre sin fines comerciales)"),
    "cuerpos_agua": ("cuerpos_agua.geojson", "real", "IGAC 1:100.000 (uso libre sin fines comerciales)"),
    "estaciones_ideam": ("clima_estaciones.geojson", "real", "IDEAM, datos abiertos (CC BY-SA 4.0): lluvia acumulada 7, 14 y 30 días"),
    "comunidades_sinteticas": ("comunidades.geojson", "sintético", "Comunidades FICTICIAS de la primera versión (el ICT usa los resguardos reales)"),
    "areas_protegidas_sinteticas": ("areas.geojson", "sintético", "Áreas FICTICIAS de la primera versión (el ICT usa el RUNAP real)"),
    "hidrologia_sintetica": ("hidro.geojson", "sintético", "Cuerpos de agua FICTICIOS de la primera versión"),
    "vias_sinteticas": ("vias.geojson", "sintético", "Vías FICTICIAS de la primera versión (el ICT usa la red vial real)"),
}
# tablas de Oro que se unen a la geometria del paquete
POR_PAQUETE = {
    "riesgo_ejecucion_paquetes": ("ejecucion_paquetes.csv", "calculado", "Riesgo de ejecución (Monte Carlo): atraso y sobrecosto por paquete"),
    "contexto_paquetes": ("contexto_paquetes.csv", "calculado", "Contexto real de cada paquete: municipio, censo, resguardos, áreas protegidas, delitos"),
}


def _plano(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """GeoPackage no guarda listas ni diccionarios: se quitan las columnas anidadas y las fechas pasan a texto."""
    gdf = gdf.copy()
    for col in [c for c in gdf.columns if c != "geometry"]:
        muestra = gdf[col].dropna()
        if len(muestra) and isinstance(muestra.iloc[0], (list, dict)):
            gdf = gdf.drop(columns=col)
        elif len(muestra) and hasattr(muestra.iloc[0], "isoformat"):
            gdf[col] = gdf[col].astype(str)
    return gdf


def main():
    asegurar_directorios()
    gpkg = EXPORTS / "reto5_piloto.gpkg"
    # la exportacion se rehace entera: fuera las copias de la corrida anterior (incluidas capas que cambiaron de nombre)
    for viejo in [gpkg, *EXPORTS.glob("*.geojson"), EXPORTS / "alertas.csv", EXPORTS / "leeme_capas.csv"]:
        if viejo.is_file():
            viejo.unlink()
    leeme = []

    for capa, (archivo, origen, fuente) in CAPAS.items():
        ruta = ORO / archivo
        if not ruta.exists():
            print(f"  [omitido] {archivo} no existe (corre primero el pipeline)")
            continue
        gdf = _plano(gpd.read_file(ruta))
        if gdf.empty:
            print(f"  [vacío] {capa}: hoy no tiene filas")
            leeme.append({"capa": capa, "origen": origen, "fuente_y_uso": fuente, "filas": 0})
            continue
        gdf.to_file(gpkg, layer=capa, driver="GPKG")
        gdf.to_file(EXPORTS / f"{capa}.geojson", driver="GeoJSON")
        leeme.append({"capa": capa, "origen": origen, "fuente_y_uso": fuente, "filas": len(gdf)})
        print(f"  {capa}: {len(gdf)} ({origen})")

    paquetes = gpd.read_file(ORO / "paquetes_ict.geojson")[["id_paquete", "nombre", "geometry"]] if (ORO / "paquetes_ict.geojson").exists() else None
    for capa, (archivo, origen, fuente) in POR_PAQUETE.items():
        ruta = ORO / archivo
        if paquetes is None or not ruta.exists():
            continue
        tabla = pd.read_csv(ruta).drop(columns=["nombre"], errors="ignore")
        gdf = _plano(paquetes.merge(tabla, on="id_paquete", how="left"))
        gdf.to_file(gpkg, layer=capa, driver="GPKG")
        gdf.to_file(EXPORTS / f"{capa}.geojson", driver="GeoJSON")
        leeme.append({"capa": capa, "origen": origen, "fuente_y_uso": fuente, "filas": len(gdf)})
        print(f"  {capa}: {len(gdf)} ({origen})")

    al = ORO / "alertas.json"
    if al.exists():
        alertas = json.loads(al.read_text(encoding="utf-8"))
        tabla = pd.DataFrame([{**{k: a.get(k) for k in ("id_alerta", "id_paquete", "nombre_paquete", "id_proyecto", "prioridad", "ict",
                                                        "nivel", "municipio", "puntos_crisis", "generada_en")},
                               "causas": " | ".join(c["texto"] for c in a["causas"]), "acciones": " | ".join(a.get("acciones", []))}
                              for a in alertas])
        if len(tabla):
            pyogrio.write_dataframe(tabla, gpkg, layer="alertas", driver="GPKG")
            tabla.to_csv(EXPORTS / "alertas.csv", index=False, encoding="utf-8-sig")
        leeme.append({"capa": "alertas", "origen": "calculado", "fuente_y_uso": "Alertas tempranas del día (tabla, sin geometría)", "filas": len(tabla)})

    pyogrio.write_dataframe(pd.DataFrame(leeme), gpkg, layer="leeme", driver="GPKG")
    pd.DataFrame(leeme).to_csv(EXPORTS / "leeme_capas.csv", index=False, encoding="utf-8-sig")
    print(f"\nGeoPackage listo en: {gpkg} ({len(leeme)} capas y tablas; ver la tabla 'leeme')")
    print(f"GeoJSON de respaldo en: {EXPORTS}")


if __name__ == "__main__":
    main()
