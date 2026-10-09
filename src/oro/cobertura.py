"""Cobertura de las estaciones del IDEAM: Plata -> Oro.

Una estacion mide en un punto. Para poder ver el clima sobre un territorio (por ejemplo, sobre un proyecto) este paso
construye, para cada variable, dos maneras de extender cada estacion a un area:

  * area mas cercana  Cada punto de La Guajira se asigna a su estacion mas cercana (poligonos de Voronoi recortados al departamento).
                      Responde "que estacion representa este lugar", sin decir que tan bueno es el dato.
  * radio de influencia  Un circulo alrededor de cada estacion, recortado a tierra, con un radio por variable. Lo que cae fuera de
                      todos los circulos no tiene cobertura.

Y para cada paquete de trabajo y variable, que estacion lo representa, a cuantos km esta y si queda **cubierto** (dentro del radio),
**parcial** (hasta el doble del radio) o **sin cobertura**.

Los radios son SUPUESTOS DE TRABAJO (reglas practicas, no cifras oficiales del IDEAM) y viven en `parametros.yaml`
(`cobertura_estaciones.radios_km`): la lluvia pide radios cortos, la temperatura largos, el nivel del rio solo es valido en su punto.

Entradas (Plata): ideam_estaciones.geojson, ideam_precip_diaria.parquet, ideam_variables_diaria.parquet, ideam_ultimas_horas.parquet,
                  municipios.geojson (para recortar al departamento) y paquetes.geojson.
Salidas (Oro):    data/gold/cobertura_estaciones.geojson (areas para el mapa) y cobertura_paquetes.csv (una fila por paquete y variable).

Uso:  python -m oro.cobertura   (despues de plata.ideam, plata.municipios y plata.sinteticos)
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import MultiPoint

from comun.config import CRS_GEOGRAFICO, CRS_METRICO, ORO, PLATA, asegurar_directorios, cargar_parametros
from comun.serializacion import escribir_coleccion

# variable de Plata -> clave que usa el mapa
CLAVE = {"precipitacion": "lluvia", "temperatura": "temperatura", "humedad": "humedad", "humedad_suelo": "humedad_suelo",
         "viento_vel": "viento", "presion": "presion", "nivel_rio": "nivel"}
RADIOS_POR_DEFECTO_KM = {"precipitacion": 10, "temperatura": 25, "humedad": 25, "humedad_suelo": 5, "viento_vel": 15, "presion": 40}
TOLERANCIA_M = 200          # simplificacion del limite y de los poligonos resultantes: sobra a la escala del mapa
ESTADOS = ("cubierto", "parcial", "sin_cobertura")


def radios_km() -> dict[str, float]:
    """Radios de parametros.yaml (en km); los que falten usan los valores por defecto. El nivel del rio no tiene area: solo vale en su punto."""
    configurados = (cargar_parametros().get("cobertura_estaciones") or {}).get("radios_km") or {}
    inverso = {v: k for k, v in CLAVE.items()}
    radios = dict(RADIOS_POR_DEFECTO_KM)
    for clave, km in configurados.items():
        radios[inverso.get(clave, clave)] = float(km)
    return radios


def estaciones_por_variable(estaciones: gpd.GeoDataFrame, lluvia: pd.DataFrame, diaria: pd.DataFrame | None, ultimas: pd.DataFrame | None
                            ) -> dict[str, gpd.GeoDataFrame]:
    """Estaciones con datos (lluvia o alguna variable diaria) que miden cada variable, en metros (EPSG:3116)."""
    con_datos = set(lluvia["codigoestacion"]) | (set(diaria["codigoestacion"]) if diaria is not None else set())
    mide: dict[str, set] = {"precipitacion": set(lluvia["codigoestacion"])}
    for tabla in (diaria, ultimas):
        if tabla is not None:
            for var, g in tabla.groupby("var"):
                mide.setdefault(var, set()).update(g["codigoestacion"])
    base = estaciones[estaciones["codigo"].isin(con_datos)][["codigo", "nombre", "geometry"]].to_crs(CRS_METRICO)
    return {var: base[base["codigo"].isin(codigos)].reset_index(drop=True) for var, codigos in mide.items() if var in CLAVE and codigos & con_datos}


def area_mas_cercana(est: gpd.GeoDataFrame, limite) -> gpd.GeoDataFrame:
    """Poligonos de Voronoi (cada punto a su estacion mas cercana) recortados al departamento. Con una sola estacion no hay reparto que hacer."""
    if len(est) < 2:
        return gpd.GeoDataFrame(columns=["codigo", "nombre", "geometry"], geometry="geometry", crs=est.crs)
    celdas = shapely.voronoi_polygons(MultiPoint(est.geometry.tolist()), extend_to=limite.buffer(1e5))
    celdas = gpd.GeoSeries(list(celdas.geoms), crs=est.crs)
    # cada celda contiene a exactamente una estacion
    asignada = gpd.sjoin(est, gpd.GeoDataFrame(geometry=celdas), predicate="within", how="left").dropna(subset=["index_right"]).copy()
    asignada["geometry"] = celdas.loc[asignada["index_right"].astype(int)].values
    out = gpd.GeoDataFrame(asignada[["codigo", "nombre", "geometry"]].reset_index(drop=True), crs=est.crs)
    out["geometry"] = out.geometry.intersection(limite)
    return out[~out.geometry.is_empty].reset_index(drop=True)


def radio_de_influencia(est: gpd.GeoDataFrame, radio_km: float, limite) -> gpd.GeoDataFrame:
    """Circulo de `radio_km` alrededor de cada estacion, recortado al departamento."""
    out = est[["codigo", "nombre", "geometry"]].copy()
    out["geometry"] = out.geometry.buffer(radio_km * 1000, quad_segs=24).intersection(limite)
    return out[~out.geometry.is_empty].reset_index(drop=True)


def estado_de(distancia_km: float, radio_km: float) -> str:
    if distancia_km <= radio_km:
        return "cubierto"
    return "parcial" if distancia_km <= 2 * radio_km else "sin_cobertura"


def cobertura_de_paquetes(paquetes: gpd.GeoDataFrame, por_variable: dict[str, gpd.GeoDataFrame], radios: dict[str, float]) -> dict[str, list[dict]]:
    """Para cada paquete (desde su centroide) y cada variable con area: estacion mas cercana, distancia y estado."""
    centros = paquetes.geometry.centroid
    out: dict[str, list[dict]] = {}
    for (_, p), centro in zip(paquetes.iterrows(), centros):
        filas = []
        for var, est in por_variable.items():
            if var not in radios or est.empty:
                continue
            d = est.geometry.distance(centro) / 1000
            i = int(d.idxmin())
            filas.append({"variable": CLAVE[var], "codigo": est.loc[i, "codigo"], "estacion": est.loc[i, "nombre"],
                          "distancia_km": round(float(d[i]), 1), "radio_km": radios[var], "estado": estado_de(float(d[i]), radios[var]),
                          "estaciones_en_el_radio": int((d <= radios[var]).sum())})
        out[p["id_paquete"]] = filas
    return out


def construir(estaciones, lluvia, diaria, ultimas, limite_4326, paquetes, radios) -> tuple[gpd.GeoDataFrame, dict, dict]:
    """(areas en 4326 para el mapa, cobertura por paquete, resumen)."""
    limite = gpd.GeoSeries([limite_4326], crs=CRS_GEOGRAFICO).to_crs(CRS_METRICO).iloc[0].simplify(TOLERANCIA_M)
    por_variable = estaciones_por_variable(estaciones, lluvia, diaria, ultimas)
    partes = []
    for var, est in por_variable.items():
        if var in radios:                    # el nivel del rio no tiene area
            for modo, g in (("cercana", area_mas_cercana(est, limite)), ("radio", radio_de_influencia(est, radios[var], limite))):
                if g.empty:
                    continue
                g = g.assign(variable=CLAVE[var], modo=modo, radio_km=radios[var] if modo == "radio" else None)
                g["area_km2"] = (g.area / 1e6).round(1)
                partes.append(g)
    areas = pd.concat(partes, ignore_index=True)
    areas = gpd.GeoDataFrame(areas, geometry="geometry", crs=CRS_METRICO)
    areas["geometry"] = areas.geometry.simplify(TOLERANCIA_M)
    areas = areas.to_crs(CRS_GEOGRAFICO)
    areas["geometry"] = shapely.set_precision(areas.geometry.values, 1e-5)
    pq = cobertura_de_paquetes(paquetes.to_crs(CRS_METRICO), por_variable, radios)
    resumen = {CLAVE[v]: int(len(e)) for v, e in por_variable.items()}
    return areas, pq, resumen


def main() -> int:
    asegurar_directorios()
    necesarios = [PLATA / n for n in ("ideam_estaciones.geojson", "ideam_precip_diaria.parquet", "municipios.geojson", "paquetes.geojson")]
    faltan = [p.name for p in necesarios if not p.exists()]
    if faltan:
        print(f"Faltan en Plata: {', '.join(faltan)}. Corre antes plata.ideam, plata.municipios y plata.sinteticos")
        return 1

    def opcional(nombre):
        return pd.read_parquet(PLATA / nombre) if (PLATA / nombre).exists() else None

    estaciones = gpd.read_file(PLATA / "ideam_estaciones.geojson")
    limite = gpd.read_file(PLATA / "municipios.geojson").geometry.union_all()
    paquetes = gpd.read_file(PLATA / "paquetes.geojson")
    radios = radios_km()
    areas, pq, resumen = construir(estaciones, pd.read_parquet(PLATA / "ideam_precip_diaria.parquet"), opcional("ideam_variables_diaria.parquet"),
                                   opcional("ideam_ultimas_horas.parquet"), limite, paquetes, radios)

    meta = {
        "supuesto": "Los radios de influencia son reglas practicas de trabajo, no cifras oficiales del IDEAM: ajustarlos con un especialista.",
        "radios_km": {CLAVE[v]: r for v, r in radios.items() if v in CLAVE}, "estaciones_por_variable": resumen,
        "estados": {"cubierto": "dentro del radio", "parcial": "hasta el doble del radio", "sin_cobertura": "mas lejos que el doble del radio"},
    }
    escribir_coleccion(ORO / "cobertura_estaciones.geojson", areas, meta)
    filas = [{"id_paquete": idp, **f} for idp, fs in pq.items() for f in fs]
    pd.DataFrame(filas, columns=["id_paquete", "variable", "codigo", "estacion", "distancia_km", "radio_km", "estado", "estaciones_en_el_radio"]
                 ).to_csv(ORO / "cobertura_paquetes.csv", index=False)

    estados = pd.Series([f["estado"] for fs in pq.values() for f in fs]).value_counts()
    print(f"Oro de la cobertura generado: {len(areas)} areas, {len(pq)} paquetes")
    print("  estaciones por variable:", resumen)
    print("  paquete x variable:", {e: int(estados.get(e, 0)) for e in ESTADOS})
    return 0


if __name__ == "__main__":
    sys.exit(main())
