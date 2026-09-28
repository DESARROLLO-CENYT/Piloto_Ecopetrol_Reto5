"""
Paso 3 del piloto: Plata -> Oro.

Calcula el Indice de Criticidad Territorial (ICT) y el indice de oportunidad
por paquete de trabajo, las reglas de escalamiento a crisis, la superficie
de calor (KDE) y el analisis de puntos calientes (Getis-Ord Gi*), y publica
todo en la capa Oro para que la API y el frontend lo consuman.
"""
from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd

from config import CRS_GEOGRAFICO, CRS_METRICO, ORO, PLATA, asegurar_directorios, cargar_parametros
from modelo import ict as m_ict
from modelo import espacial as m_esp


def cargar_plata():
    return {
        "riesgos": gpd.read_file(PLATA / "riesgos.geojson"),
        "paquetes": gpd.read_file(PLATA / "paquetes.geojson"),
        "proyectos": gpd.read_file(PLATA / "proyectos.geojson"),
        "comunidades": gpd.read_file(PLATA / "comunidades.geojson"),
        "areas": gpd.read_file(PLATA / "areas.geojson"),
        "hidro": gpd.read_file(PLATA / "hidro.geojson"),
        "vias": gpd.read_file(PLATA / "vias.geojson"),
        "clima": pd.read_parquet(PLATA / "clima.parquet"),
    }


def calcular_ict_para_fecha(datos, params, fecha_corte: pd.Timestamp, bounds=None):
    paquetes = datos["paquetes"]
    ids_paquete = paquetes["id_paquete"].tolist()

    paquetes_m = paquetes.to_crs(CRS_METRICO)
    centroides_m = gpd.GeoSeries(paquetes_m.geometry.centroid.values, index=paquetes_m["id_paquete"], crs=CRS_METRICO)
    comunidades_m = datos["comunidades"].to_crs(CRS_METRICO)
    areas_m = datos["areas"].to_crs(CRS_METRICO)

    df_estaciones = datos["clima"][["id_estacion", "lon", "lat"]].drop_duplicates()
    gdf_estaciones_m = gpd.GeoDataFrame(
        df_estaciones, geometry=gpd.points_from_xy(df_estaciones["lon"], df_estaciones["lat"]), crs=CRS_GEOGRAFICO
    ).to_crs(CRS_METRICO)

    conteo_riesgos = datos["riesgos"].groupby("id_paquete_trabajo").size()

    criterios_crudos = {
        "severidad_riesgo": m_ict.severidad_por_paquete(
            datos["riesgos"], params["factores_estado"],
            params["agregacion"]["peso_maximo"], params["agregacion"]["peso_promedio"],
            fecha_corte=fecha_corte,
        ),
        "exposicion_proyecto": m_ict.exposicion_por_paquete(paquetes, conteo_riesgos),
        "vulnerabilidad_territorial": m_ict.vulnerabilidad_por_paquete(
            centroides_m, comunidades_m, areas_m,
            params["radios_influencia_m"]["social_comunidad"], params["radios_influencia_m"]["ambiental"],
        ),
        "amenazas_externas": m_ict.amenazas_externas_por_paquete(
            centroides_m, gdf_estaciones_m, datos["clima"],
            params["amenazas_externas"]["precipitacion_extrema_mm_14d"],
            params["amenazas_externas"]["ventana_dias"],
            fecha_corte=fecha_corte,
        ),
        "convergencia": m_ict.convergencia_por_paquete(
            datos["riesgos"], params["convergencia"]["categorias_para_saturar"], fecha_corte=fecha_corte
        ),
    }

    tabla, bounds_usados = m_ict.ensamblar_ict(criterios_crudos, params["pesos"], ids_paquete, bounds=bounds)
    return tabla, criterios_crudos, centroides_m, bounds_usados


def calcular_escalamiento(datos, params, tabla_ict, hoy: pd.Timestamp) -> pd.DataFrame:
    """Una zona escala a "posible crisis" si el ICT ya es critico por si solo,
    o si una causa secundaria (convergencia de amenazas, acciones vencidas)
    coincide con un ICT al menos "medio". Esto evita que una coincidencia
    aislada (p. ej. 3 categorias distintas en una zona de baja criticidad)
    dispare una alerta sin respaldo del indice.
    """
    riesgos = datos["riesgos"]
    umbral_critico = params["escalamiento"]["ict_critico"]
    umbral_medio = params["umbrales_criticidad"]["medio"]
    min_conv = params["escalamiento"]["min_amenazas_convergentes"]

    n_categorias_real = riesgos[riesgos["tipo"] == "amenaza"].groupby("id_paquete_trabajo")["categoria"].nunique()

    acciones_vencidas = (
        riesgos[(riesgos["tipo"] == "amenaza") & (riesgos["estado"] != "materializado") & (riesgos["fecha_ejecucion_accion"] < hoy)]
        .groupby("id_paquete_trabajo").size()
    )

    filas = []
    for id_paquete, fila in tabla_ict.iterrows():
        causas = []
        ict = fila["ICT"]
        if ict >= umbral_critico:
            causas.append(f"ICT >= {umbral_critico}")

        n_cat = int(n_categorias_real.get(id_paquete, 0))
        if n_cat >= min_conv and ict >= umbral_medio:
            causas.append(f"convergen {n_cat} categorias de amenaza con ICT medio-alto")

        n_venc = int(acciones_vencidas.get(id_paquete, 0))
        if n_venc >= params["escalamiento"]["min_acciones_vencidas"] and ict >= umbral_medio:
            causas.append(f"{n_venc} acciones de tratamiento vencidas con ICT medio-alto")

        filas.append({"id_paquete": id_paquete, "escalamiento": len(causas) > 0, "causas_escalamiento": "; ".join(causas)})
    return pd.DataFrame(filas).set_index("id_paquete")


def calcular_tendencia(datos, params, hoy: pd.Timestamp, ict_hoy: pd.Series, bounds: dict) -> pd.DataFrame:
    """Recalcula el ICT `ventana_tendencia_dias` atras usando los MISMOS
    bounds de normalizacion que el corte de hoy, para que el delta refleje
    cambios reales en los riesgos y no un efecto de reescalado relativo.
    """
    dias = params["escalamiento"]["ventana_tendencia_dias"]
    fecha_anterior = hoy - pd.Timedelta(days=dias)
    tabla_antes, _, _, _ = calcular_ict_para_fecha(datos, params, fecha_anterior, bounds=bounds)
    ict_antes = tabla_antes["ICT"]

    delta = (ict_hoy - ict_antes.reindex(ict_hoy.index).fillna(0)).round(1)
    umbral = params["escalamiento"]["incremento_tendencia_alerta"]
    return pd.DataFrame({
        "id_paquete": ict_hoy.index,
        "ict_hace_ndias": ict_antes.reindex(ict_hoy.index).fillna(0).round(1),
        "tendencia_delta": delta,
        "tendencia_alerta": delta >= umbral,
    }).set_index("id_paquete")


def main():
    asegurar_directorios()
    params = cargar_parametros()
    datos = cargar_plata()
    hoy = pd.Timestamp.now().normalize()

    tabla_ict, criterios_crudos, centroides_m, bounds_hoy = calcular_ict_para_fecha(datos, params, hoy)
    tabla_ict["nivel"] = tabla_ict["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
    tabla_ict["indice_confianza"] = [
        m_ict.indice_confianza(datos["riesgos"], m_ict.CRITERIOS, criterios_crudos, idp) for idp in tabla_ict.index
    ]

    indice_oportunidad = m_ict.indice_oportunidad_por_paquete(
        datos["riesgos"], params["agregacion"]["peso_maximo"], params["agregacion"]["peso_promedio"]
    )
    tabla_ict["indice_oportunidad"] = indice_oportunidad.reindex(tabla_ict.index).fillna(0.0)

    escalamiento = calcular_escalamiento(datos, params, tabla_ict, hoy)
    tendencia = calcular_tendencia(datos, params, hoy, tabla_ict["ICT"], bounds_hoy)

    tabla_final = tabla_ict.join(escalamiento).join(tendencia)

    # --- Estadistica espacial complementaria ---
    gi_star = m_esp.getis_ord_gi_star(centroides_m, tabla_ict["ICT"], params["hotspot"]["k_vecinos"])
    tabla_final = tabla_final.join(gi_star)

    riesgos_m = datos["riesgos"].to_crs(CRS_METRICO)
    grid = m_esp.generar_grid(params["grid"]["resolucion_grados"])
    grid_m = grid.to_crs(CRS_METRICO)
    intensidad = m_esp.kde_superficie(riesgos_m, grid_m, "severidad", params["kde"]["bandwidth_m"])
    grid["intensidad"] = grid["celda_id"].map(intensidad).fillna(0.0).round(4)
    grid = grid[grid["intensidad"] > 0.01]  # descartar celdas irrelevantes para aligerar el geojson

    # --- Publicar en Oro ---
    gdf_paquetes_oro = datos["paquetes"].merge(tabla_final.reset_index(), on="id_paquete", how="left")
    gdf_paquetes_oro.to_file(ORO / "paquetes_ict.geojson", driver="GeoJSON")
    grid.to_file(ORO / "grid_calor.geojson", driver="GeoJSON")

    for nombre in ["riesgos", "proyectos", "comunidades", "areas", "hidro", "vias"]:
        datos[nombre].to_file(ORO / f"{nombre}.geojson", driver="GeoJSON")

    alertas = []
    for id_paquete, fila in tabla_final.iterrows():
        nombre_paquete = datos["paquetes"].set_index("id_paquete").loc[id_paquete, "nombre"]
        motivos = []
        if fila["escalamiento"]:
            motivos.append(fila["causas_escalamiento"])
        if fila.get("tendencia_alerta"):
            motivos.append(f"tendencia +{fila['tendencia_delta']} pts en {params['escalamiento']['ventana_tendencia_dias']} dias")
        if motivos:
            alertas.append({
                "id_paquete": id_paquete,
                "nombre_paquete": nombre_paquete,
                "ict": float(fila["ICT"]),
                "nivel": fila["nivel"],
                "motivos": motivos,
                "generada_en": hoy.isoformat(),
            })

    with open(ORO / "alertas.json", "w", encoding="utf-8") as f:
        json.dump(alertas, f, ensure_ascii=False, indent=2)

    print("Oro generado en:", ORO)
    print(tabla_final[["ICT", "nivel", "indice_oportunidad", "indice_confianza", "escalamiento", "clasificacion"]])
    print(f"\nAlertas activas: {len(alertas)}")


if __name__ == "__main__":
    main()
