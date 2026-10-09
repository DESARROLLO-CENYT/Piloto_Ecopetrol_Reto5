"""
Paso 2 del piloto: Bronce -> Plata.

Limpieza, deduplicacion, estandarizacion de taxonomia y validacion de
geometrias sobre el registro de riesgos sintetico. Los riesgos sin
coordenadas no se descartan: se ubican por el centroide de su paquete de
trabajo y quedan marcados con geolocalizacion_inferida=True, para que el
modelo los use pero el reporte de brechas los distinga.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from comun.config import BRONCE, CRS_GEOGRAFICO, CRS_METRICO, PLATA, asegurar_directorios, cargar_parametros
from modelo.ram import Ram, normalizar_consecuencia, normalizar_probabilidad
from modelo import texto as m_texto

COLUMNAS_RAM = {"PE": "cons_personas", "EC": "cons_economica", "MA": "cons_ambiental", "CL": "cons_clientes", "IM": "cons_imagen"}


def clasificar_ram(df: pd.DataFrame, ram: Ram) -> tuple[pd.DataFrame, dict]:
    """Normaliza la calificacion RAM de cada riesgo y lo ubica en la matriz, inherente (sin controles) y residual.

    * Consecuencias: 0 a 5 por dimension; lo ilegible o fuera de rango queda sin calificar (la dimension no cuenta).
    * Probabilidad: 'C', 'c', 'C - Ha ocurrido...', '3' -> 'C'. Sin probabilidad residual se usa la inherente.
    * Manda la peor dimension (codigo como '4D'); `puntaje_ram` (N=1 ... VH=5) es el del nivel residual.
    """
    rep = {}
    for col in COLUMNAS_RAM.values():
        df[col] = df[col].map(normalizar_consecuencia).astype("Int64")
    rep["ram_dimensiones_sin_calificar"] = int(df[list(COLUMNAS_RAM.values())].isna().sum().sum())
    df["probabilidad"] = df["probabilidad"].map(normalizar_probabilidad)
    df["probabilidad_residual"] = df["probabilidad_residual"].map(normalizar_probabilidad)
    rep["ram_sin_probabilidad"] = int(df["probabilidad"].isna().sum())
    sin_residual = df["probabilidad_residual"].isna() & df["probabilidad"].notna()
    rep["ram_residual_igual_a_inherente"] = int(sin_residual.sum())
    df.loc[sin_residual, "probabilidad_residual"] = df.loc[sin_residual, "probabilidad"]
    # los controles no pueden subir la probabilidad: si el registro dice lo contrario, se corrige y se cuenta
    sube = df["probabilidad_residual"].notna() & df["probabilidad"].notna() & (df["probabilidad_residual"] > df["probabilidad"])
    rep["ram_residual_mayor_corregido"] = int(sube.sum())
    df.loc[sube, "probabilidad_residual"] = df.loc[sube, "probabilidad"]

    for etapa, prob in (("inherente", "probabilidad"), ("residual", "probabilidad_residual")):
        res = [ram.clasificar({d: f[c] for d, c in COLUMNAS_RAM.items()}, f[prob]) if isinstance(f[prob], str) else
               {"codigo": None, "nivel": None, "dimension": None}
               for _, f in df.iterrows()]
        df[f"ram_{etapa}"] = [r["codigo"] for r in res]
        df[f"nivel_{etapa}"] = [r["nivel"] for r in res]
        if etapa == "residual":
            df["dimension_dominante"] = [r["dimension"] for r in res]
    df["puntaje_ram"] = df["nivel_residual"].map(lambda n: ram.puntaje(n) if n else None)
    rep["ram_sin_clasificar"] = int(df["nivel_residual"].isna().sum())
    return df, rep

CATEGORIAS_VALIDAS = {
    "social_comunidad", "ambiental", "seguridad_fisica",
    "logistico_acceso", "climatico", "contractual",
}
ESTADOS_VALIDOS = {"latente", "proximo_a_materializarse", "materializado"}


def _normalizar_texto(serie: pd.Series) -> pd.Series:
    return (
        serie.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("__", "_", regex=False)
    )


def clasificar_con_ia(df: pd.DataFrame, gdf_paquetes: gpd.GeoDataFrame, municipios: gpd.GeoDataFrame | None,
                      clave: pd.DataFrame | None, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """IA sobre el texto del registro (descripcion + causa):
      * aprende la taxonomia de los riesgos que traen categoria (sin los duplicados) y mide su acierto con validacion
        cruzada; sugiere la categoria de los que no la traen si la confianza alcanza `confianza_para_asignar`;
      * marca los riesgos cuya categoria registrada contradice el texto con confianza `confianza_para_revisar`;
      * busca municipios mencionados en el texto y marca los que quedan lejos del paquete (error de ubicacion).
    La categoria original queda en categoria_registrada y el origen de la final en categoria_origen."""
    rep: dict = {}
    textos = (df["descripcion"].fillna("") + ". " + df["causa"].fillna("")).tolist()
    df["categoria_registrada"] = df["categoria"]
    base = ~df["id_riesgo"].str.contains("-DUP", regex=False)
    etiquetado = df["categoria"].isin(CATEGORIAS_VALIDAS) & base
    entreno = [textos[i] for i in range(len(df)) if etiquetado.iloc[i]]
    etiquetas = df.loc[etiquetado, "categoria"].tolist()
    if len(set(etiquetas)) < 2:
        df["categoria_origen"] = "registro"
        return df, {"ia_sin_modelo": 1}
    vc = m_texto.validacion_cruzada(entreno, etiquetas)
    modelo = m_texto.ClasificadorTexto().entrenar(entreno, etiquetas)
    pred = [modelo.predecir(x) for x in textos]
    df["categoria_ia"] = [c for c, _ in pred]
    df["confianza_ia"] = [round(p, 3) for _, p in pred]
    df["palabras_ia"] = [", ".join(modelo.explicar(x, c)) for x, (c, _) in zip(textos, pred)]

    sin_categoria = ~df["categoria"].isin(CATEGORIAS_VALIDAS)
    asignable = sin_categoria & (df["confianza_ia"] >= float(cfg.get("confianza_para_asignar", 0.6)))
    df["categoria_origen"] = "registro"
    df.loc[asignable, "categoria"] = df.loc[asignable, "categoria_ia"]
    df.loc[asignable, "categoria_origen"] = "ia"
    df.loc[sin_categoria & ~asignable, "categoria_origen"] = "pendiente"
    df["revisar_categoria"] = (~sin_categoria & (df["categoria_ia"] != df["categoria"])
                               & (df["confianza_ia"] >= float(cfg.get("confianza_para_revisar", 0.8))))
    rep.update(ia_exactitud_validacion_cruzada=vc["exactitud"], ia_riesgos_sin_categoria=int(sin_categoria.sum()),
               ia_categorias_asignadas=int(asignable.sum()), ia_categorias_pendientes=int((sin_categoria & ~asignable).sum()),
               ia_categoria_por_revisar=int(df["revisar_categoria"].sum()))
    if clave is not None and len(clave):
        verdad = df["id_riesgo"].str.replace(r"-DUP\d*$", "", regex=True).map(clave.set_index("id_riesgo")["categoria_real"])
        if asignable.any():
            rep["ia_exactitud_sin_categoria"] = round(float((df.loc[asignable, "categoria"] == verdad[asignable]).mean()), 3)

    # lugares mencionados en el texto frente a la ubicacion del paquete
    df["municipio_mencionado"] = None
    df["revisar_ubicacion"] = False
    if municipios is not None and len(municipios):
        nombres = dict(zip(municipios["codigo"], municipios["nombre"]))
        mun_m = municipios.to_crs(CRS_METRICO).set_index("codigo")
        paq_m = gdf_paquetes.to_crs(CRS_METRICO).set_index("id_paquete")
        lejos = float(cfg.get("distancia_lugar_km", 15)) * 1000
        for i, idx in enumerate(df.index):
            codigos = m_texto.lugares_mencionados(textos[i], nombres)
            if not codigos:
                continue
            df.at[idx, "municipio_mencionado"] = ", ".join(nombres[c] for c in codigos)
            paquete = df.at[idx, "id_paquete_trabajo"]
            if paquete in paq_m.index:
                distancia = min(float(mun_m.loc[c].geometry.distance(paq_m.loc[paquete].geometry)) for c in codigos)
                df.at[idx, "revisar_ubicacion"] = distancia > lejos
        rep["ia_lugar_mencionado"] = int(df["municipio_mencionado"].notna().sum())
        rep["ia_ubicacion_por_revisar"] = int(df["revisar_ubicacion"].sum())
    return df, rep


def resumen_ia(df: pd.DataFrame, clave: pd.DataFrame | None) -> dict:
    """Cifras de la IA sobre el registro final, ya sin duplicados (lo que se entrega, no lo que llego). Con la clave
    sintetica ademas cuenta cuantos errores sembrados detecta y cuantas falsas alarmas da: solo es posible porque los
    datos son inventados; con el registro real esa evaluacion la hacen los expertos."""
    if "categoria_ia" not in df:
        return {}
    sin_categoria = ~df["categoria_registrada"].isin(CATEGORIAS_VALIDAS)
    asignadas = df["categoria_origen"].eq("ia")
    marcada_cat = df["revisar_categoria"].astype(bool)
    marcada_ubi = df["revisar_ubicacion"].astype(bool)
    rep = {
        "ia_riesgos_sin_categoria": int(sin_categoria.sum()),
        "ia_categorias_asignadas": int(asignadas.sum()),
        "ia_categorias_pendientes": int(df["categoria_origen"].eq("pendiente").sum()),
        "ia_categoria_por_revisar": int(marcada_cat.sum()),
        "ia_lugar_mencionado": int(df["municipio_mencionado"].notna().sum()),
        "ia_ubicacion_por_revisar": int(marcada_ubi.sum()),
    }
    if clave is None or not len(clave):
        return rep
    c = clave.set_index("id_riesgo")
    base = df["id_riesgo"].str.replace(r"-DUP\d*$", "", regex=True)
    real = base.map(c["categoria_real"])
    if asignadas.any():
        rep["ia_exactitud_sin_categoria"] = round(float((df.loc[asignadas, "categoria"] == real[asignadas]).mean()), 3)
    mal = ~sin_categoria & (df["categoria_registrada"] != real)
    rep.update(ia_categorias_mal_sembradas=int(mal.sum()), ia_categorias_mal_detectadas=int((mal & marcada_cat).sum()),
               ia_categorias_falsas_alarmas=int((~mal & marcada_cat).sum()))
    if "ubicacion_lejana" in c:
        lejana = base.map(c["ubicacion_lejana"]).fillna(False).astype(bool)
        rep.update(ia_ubicaciones_sembradas=int(lejana.sum()), ia_ubicaciones_detectadas=int((lejana & marcada_ubi).sum()),
                   ia_ubicaciones_falsas_alarmas=int((~lejana & marcada_ubi).sum()))
    return rep


def cargar_bronce():
    df_riesgos = pd.read_excel(BRONCE / "registro_riesgos.xlsx")
    gdf_paquetes = gpd.read_file(BRONCE / "paquetes_trabajo.geojson")
    gdf_proyectos = gpd.read_file(BRONCE / "proyectos.geojson")
    gdf_comunidades = gpd.read_file(BRONCE / "comunidades.geojson")
    gdf_areas = gpd.read_file(BRONCE / "areas_protegidas.geojson")
    gdf_hidro = gpd.read_file(BRONCE / "hidrologia.geojson")
    gdf_vias = gpd.read_file(BRONCE / "vias.geojson")
    df_clima = pd.read_csv(BRONCE / "clima_sintetico.csv")
    df_cron = pd.read_csv(BRONCE / "cronograma_paquetes.csv")
    clave = BRONCE / "clave_categorias_sinteticas.csv"
    municipios = PLATA / "municipios.geojson"     # diccionario geografico para la IA (si ya se descargo)
    return {
        "riesgos": df_riesgos, "paquetes": gdf_paquetes, "proyectos": gdf_proyectos,
        "comunidades": gdf_comunidades, "areas": gdf_areas, "hidro": gdf_hidro,
        "vias": gdf_vias, "clima": df_clima, "cronograma": df_cron,
        "clave": pd.read_csv(clave) if clave.exists() else None,
        "municipios": gpd.read_file(municipios) if municipios.exists() else None,
    }


def limpiar_riesgos(df: pd.DataFrame, gdf_paquetes: gpd.GeoDataFrame, ram: Ram | None = None,
                    municipios: gpd.GeoDataFrame | None = None, clave: pd.DataFrame | None = None) -> tuple[gpd.GeoDataFrame, dict]:
    params = cargar_parametros()
    ram = ram or Ram(params["ram"])
    reporte = {"filas_bronce": len(df)}

    # 1) Estandarizar taxonomia (categoria, estado, tipo); lo que no se reconoce lo lee la IA en el texto
    df["categoria"] = _normalizar_texto(df["categoria"].fillna(""))
    df["categoria"] = df["categoria"].where(df["categoria"].isin(CATEGORIAS_VALIDAS), "sin_clasificar")
    df, rep_ia = clasificar_con_ia(df, gdf_paquetes, municipios, clave, params.get("ia_texto", {}))
    reporte.update(rep_ia)
    df["estado"] = _normalizar_texto(df["estado"])
    df["estado"] = df["estado"].where(df["estado"].isin(ESTADOS_VALIDOS), "latente")
    df["tipo"] = _normalizar_texto(df["tipo"])

    # 2) Deduplicar: mismo riesgo reportado varias veces (id base sin sufijo -DUP,
    #    y ademas por combinacion de campos clave para duplicados "reales")
    # 3) Matriz RAM (antes de deduplicar: la probabilidad llega escrita de varias formas)
    df, rep_ram = clasificar_ram(df, ram)

    df["id_riesgo_base"] = df["id_riesgo"].str.replace(r"-DUP\d*$", "", regex=True)
    antes = len(df)
    df = df.sort_values("id_riesgo").drop_duplicates(
        subset=["id_riesgo_base", "id_paquete_trabajo", "categoria", "ram_inherente"],
        keep="first",
    )
    reporte["duplicados_removidos"] = antes - len(df)
    reporte.update(rep_ram)

    # 4) Tipos y fechas
    for col in ["fecha_identificacion", "fecha_materializacion", "fecha_ejecucion_accion"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["causa"] = df["causa"].fillna("sin_causa_registrada")

    # 4) Geolocalizacion: usar lat/lon si existen; si no, inferir por el
    #    centroide del paquete de trabajo y marcarlo.
    df["geolocalizacion_inferida"] = df["lat"].isna() | df["lon"].isna()
    centroides = (
        gdf_paquetes.set_index("id_paquete").geometry.to_crs(CRS_METRICO).centroid.to_crs(CRS_GEOGRAFICO)
    )
    faltantes = df["geolocalizacion_inferida"]
    df.loc[faltantes, "lon"] = df.loc[faltantes, "id_paquete_trabajo"].map(lambda p: centroides.get(p).x if centroides.get(p) is not None else None)
    df.loc[faltantes, "lat"] = df.loc[faltantes, "id_paquete_trabajo"].map(lambda p: centroides.get(p).y if centroides.get(p) is not None else None)

    reporte["sin_coordenadas_originales"] = int(faltantes.sum())
    df_sin_geom = df[df["lat"].isna() | df["lon"].isna()]
    reporte["riesgos_sin_paquete_valido"] = int(len(df_sin_geom))
    df = df.dropna(subset=["lat", "lon"])

    # 5) Severidad (para el mapa de calor) = puntaje del nivel RAM residual, 1 a 5; y geometria
    df["severidad"] = df["puntaje_ram"].fillna(1).astype(int)
    geometry = [Point(xy) for xy in zip(df["lon"], df["lat"])]
    gdf = gpd.GeoDataFrame(df.drop(columns=["id_riesgo_base"]), geometry=geometry, crs=CRS_GEOGRAFICO)

    reporte["filas_plata"] = len(gdf)
    reporte.update(resumen_ia(gdf, clave))   # las cifras de la IA se reportan sobre el registro final, sin duplicados
    return gdf, reporte


def limpiar_cronograma(cron: pd.DataFrame, gdf_paquetes: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict]:
    """Un paquete por fila, numeros validos y coherencia con la ruta critica (un paquete critico no tiene holgura)."""
    rep = {"cronograma_bronce": int(len(cron))}
    c = cron.drop_duplicates("id_paquete").copy()
    c = c[c["id_paquete"].isin(gdf_paquetes["id_paquete"])]
    for col in ("duracion_meses", "avance", "meses_restantes", "holgura_dias", "costo_dia_parada_usd", "presupuesto_usd"):
        c[col] = pd.to_numeric(c[col], errors="coerce").clip(lower=0)
    c["avance"] = c["avance"].clip(upper=1)
    critico = c["id_paquete"].map(gdf_paquetes.set_index("id_paquete")["ruta_critica"].astype(bool))
    rep["cronograma_holgura_en_ruta_critica_corregida"] = int((critico & (c["holgura_dias"] > 0)).sum())
    c.loc[critico, "holgura_dias"] = 0
    c["ruta_critica"] = critico.values
    rep["cronograma_plata"] = int(len(c))
    rep["paquetes_sin_cronograma"] = int((~gdf_paquetes["id_paquete"].isin(c["id_paquete"])).sum())
    return c.reset_index(drop=True), rep


def main():
    asegurar_directorios()
    datos = cargar_bronce()

    gdf_riesgos, reporte = limpiar_riesgos(datos["riesgos"], datos["paquetes"], municipios=datos["municipios"], clave=datos["clave"])
    cron, rep_cron = limpiar_cronograma(datos["cronograma"], datos["paquetes"])
    reporte.update(rep_cron)
    cron.to_parquet(PLATA / "cronograma.parquet", index=False)

    gdf_riesgos.to_file(PLATA / "riesgos.geojson", driver="GeoJSON")
    for nombre in ["paquetes", "proyectos", "comunidades", "areas", "hidro", "vias"]:
        datos[nombre].to_file(PLATA / f"{nombre}.geojson", driver="GeoJSON")
    datos["clima"].to_parquet(PLATA / "clima_sintetico.parquet", index=False)

    reporte_df = pd.DataFrame([reporte])
    reporte_df.to_csv(PLATA / "reporte_calidad_bronce_a_plata.csv", index=False)

    print("Plata generada en:", PLATA)
    for k, v in reporte.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
