"""
Indice de Criticidad Territorial (ICT): Plata -> Oro.

Entradas (Plata):
  registro y proyecto (SINTETICOS): riesgos, paquetes, proyectos
  territorio (REAL): municipios (DANE), indicadores del censo 2018 (DANE), delitos (MinDefensa), emergencias (UNGRD),
                     lluvia mensual (CHIRPS), resguardos (ANT), areas protegidas (RUNAP), red vial (INVIAS + IGAC),
                     lluvia diaria de las estaciones (IDEAM)
Salidas (Oro):
  paquetes_ict.geojson        ICT por paquete, sus cinco criterios y sus componentes, contribucion de cada criterio,
                              confianza, oportunidad, tendencia, escalamiento y perfil RAM
  puntos_crisis.geojson       donde un evento podria escalar a crisis: la amenaza que dispara la regla (o el centro del
                              paquete si la causa es del paquete entero), con su causa y quien debe decidir
  zonas_intervencion.geojson  area de influencia de esos puntos, por paquete: donde intervenir primero
  grid_calor.geojson          densidad (kernel) de amenazas y de oportunidades y puntos calientes (Gi*) en la grilla
  alertas.json                una alerta por paquete en escalamiento o con tendencia al alza: causas y acciones
  riesgos.geojson ...         el registro y las capas sinteticas de apoyo, para la API y la exportacion

Si falta una fuente real, sus componentes quedan sin dato: el ICT se calcula con lo demas y la confianza lo dice.
"""
from __future__ import annotations

import hashlib
import json

import geopandas as gpd
import numpy as np
import pandas as pd

from comun.config import CRS_GEOGRAFICO, CRS_METRICO, ORO, PLATA, asegurar_directorios, cargar_parametros
from modelo import espacial as m_esp
from modelo import ict as m_ict
from modelo import territorio as m_terr

ORDEN_RAM = m_ict.ORDEN_RAM


def _lee(nombre: str):
    ruta = PLATA / nombre
    if not ruta.exists():
        return None
    if ruta.suffix == ".geojson":
        return gpd.read_file(ruta)
    return pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)


def cargar_plata() -> dict:
    datos = {
        # registro de riesgos y proyectos (sinteticos)
        "riesgos": gpd.read_file(PLATA / "riesgos.geojson"),
        "paquetes": gpd.read_file(PLATA / "paquetes.geojson"),
        "proyectos": gpd.read_file(PLATA / "proyectos.geojson"),
        "comunidades": gpd.read_file(PLATA / "comunidades.geojson"),
        "areas": gpd.read_file(PLATA / "areas.geojson"),
        "hidro": gpd.read_file(PLATA / "hidro.geojson"),
        "vias": gpd.read_file(PLATA / "vias.geojson"),
    }
    # territorio real (datos abiertos); None si aun no se descargo
    for clave, archivo in (("municipios", "municipios.geojson"), ("censo", "indicadores_censo2018.parquet"),
                           ("seguridad", "seguridad_municipio_mensual.parquet"), ("emergencias", "emergencias.parquet"),
                           ("chirps", "chirps_municipio_mensual.parquet"), ("resguardos", "resguardos.geojson"),
                           ("runap", "areas_protegidas_runap.geojson"), ("red_vial", "red_vial.geojson"),
                           ("estaciones", "ideam_estaciones.geojson"), ("lluvia_diaria", "ideam_precip_diaria.parquet")):
        datos[clave] = _lee(archivo)
    return datos


# ---------------------------------------------------------------------------
# Unidades y territorio (lo que no depende de la fecha se calcula una vez)
# ---------------------------------------------------------------------------

def _metrico(datos: dict, clave: str):
    cache = datos.setdefault("_metrico", {})
    if clave not in cache:
        capa = datos.get(clave)
        cache[clave] = capa.to_crs(CRS_METRICO) if capa is not None and len(capa) else None
    return cache[clave]


def unidades_paquetes(datos: dict) -> tuple[gpd.GeoSeries, gpd.GeoSeries]:
    pm = _metrico(datos, "paquetes")
    poligonos = gpd.GeoSeries(pm.geometry.values, index=pm["id_paquete"], crs=CRS_METRICO)
    return poligonos, poligonos.centroid


def territorio_de(datos: dict, params: dict, unidades_m: gpd.GeoSeries, centros_m: gpd.GeoSeries) -> tuple[pd.DataFrame, dict]:
    """Variables reales (crudas) de cada unidad que no cambian de un dia a otro, y la fuente de cada una."""
    crit = params["criterios"]
    t = pd.DataFrame(index=unidades_m.index)
    fuentes: dict[str, str] = {}
    mun = _metrico(datos, "municipios")
    if mun is not None:
        t["codigo_municipio"] = m_terr.municipio_de(centros_m, mun)
        t["municipio"] = t["codigo_municipio"].map(mun.set_index("codigo")["nombre"])
        fuentes["municipio"] = "DANE, Marco Geoestadístico Nacional"
    else:
        t["codigo_municipio"], t["municipio"] = pd.NA, None
    ind, f_ind = m_terr.indicadores_municipales(datos.get("censo"), datos.get("seguridad"), datos.get("emergencias"),
                                                datos.get("chirps"), int(crit["amenazas_externas"].get("meses_anomalia", 3)))
    fuentes.update(f_ind)
    for col in ("ipm", "delitos_100k", "emergencias_por_ano", "anomalia_lluvia"):
        t[col] = t["codigo_municipio"].astype(object).map(ind[col]) if col in ind else np.nan
        t[col] = pd.to_numeric(t[col], errors="coerce")
    rg = m_terr.dentro_y_distancia(unidades_m, _metrico(datos, "resguardos"))
    t["fraccion_resguardo"], t["distancia_resguardo_km"] = rg["fraccion_dentro"], rg["distancia_km"]
    if _metrico(datos, "resguardos") is not None:
        fuentes["etnico"] = "Agencia Nacional de Tierras, resguardos formalizados"
    ap = m_terr.dentro_y_distancia(unidades_m, _metrico(datos, "runap"))
    t["fraccion_area_protegida"], t["distancia_area_protegida_km"] = ap["fraccion_dentro"], ap["distancia_km"]
    if _metrico(datos, "runap") is not None:
        fuentes["ambiental"] = "RUNAP, Parques Nacionales Naturales"
    radio_vias = float(crit["vulnerabilidad_territorial"].get("radio_vias_km", 10)) * 1000
    t["vias_tiempo_seco"] = m_terr.fraccion_vias_tiempo_seco(centros_m, _metrico(datos, "red_vial"), radio_vias)
    if _metrico(datos, "red_vial") is not None:
        fuentes["acceso"] = "INVIAS (red nacional) + IGAC 1:100.000"
    return t, fuentes


def lluvia_en_fecha(datos: dict, params: dict, centros_m: gpd.GeoSeries, fecha_corte: pd.Timestamp) -> pd.DataFrame:
    c = params["criterios"]["amenazas_externas"]
    return m_terr.lluvia_reciente(centros_m, _metrico(datos, "estaciones"), datos.get("lluvia_diaria"), fecha_corte,
                                  int(c.get("ventana_dias", 14)), int(c.get("dias_minimos_con_dato", 10)),
                                  float(c.get("distancia_maxima_estacion_km", 20)))


# ---------------------------------------------------------------------------
# ICT de los paquetes en una fecha
# ---------------------------------------------------------------------------

def criterios_de(datos, params, fecha_corte, unidades_m: gpd.GeoSeries, centros_m: gpd.GeoSeries, terr: pd.DataFrame,
                 asignar: bool = True, ruta_critica: pd.Series | None = None) -> dict:
    """Los cinco criterios (0-1) de cualquier unidad: paquetes (las amenazas asignadas los alcanzan enteras y cuenta la
    ruta critica) o celdas de la grilla (solo alcance por distancia y sin ruta critica, que es del paquete)."""
    ids = list(unidades_m.index)
    crit = params["criterios"]
    terr = terr.join(lluvia_en_fecha(datos, params, centros_m, fecha_corte))
    amen = m_ict.amenazas_en_fecha(datos["riesgos"], fecha_corte)
    amen_m = amen.to_crs(CRS_METRICO)
    w = m_ict.pesos_alcance(unidades_m, amen_m, params["radios_influencia_m"],
                            asignacion=amen["id_paquete_trabajo"] if asignar else None)
    sev = m_ict.severidad_amenazas(amen, params["factores_estado"])
    abiertas = (amen["estado_calc"] != "materializado").to_numpy()
    agr = params["agregacion"]
    severidad = m_ict.criterio_severidad(w, sev, agr["peso_maximo"], agr["peso_promedio"],
                                         5.0 * max(params["factores_estado"].values()), ids)
    cfg_expo = crit["exposicion_proyecto"] if ruta_critica is not None else {**crit["exposicion_proyecto"], "peso_ruta_critica": 0.0}
    expo = m_ict.criterio_exposicion(w[:, abiertas], ruta_critica if ruta_critica is not None else pd.Series(False, index=ids),
                                     cfg_expo, ids)
    vul = m_ict.criterio_vulnerabilidad(terr, crit["vulnerabilidad_territorial"])
    ext = m_ict.criterio_amenazas_externas(terr, crit["amenazas_externas"])
    conv = m_ict.criterio_convergencia(amen, w, ext, crit["convergencia"], ids)
    return {"crudos": {"severidad_riesgo": severidad, "exposicion_proyecto": expo["exposicion_proyecto"],
                       "vulnerabilidad_territorial": vul["vulnerabilidad_territorial"],
                       "amenazas_externas": ext["amenazas_externas"], "convergencia": conv["convergencia"]},
            "terr": terr, "vul": vul, "ext": ext, "expo": expo, "conv": conv}


def calcular_ict_para_fecha(datos, params, fecha_corte: pd.Timestamp, bounds=None):
    """ICT de cada paquete en `fecha_corte`. Devuelve (tabla, criterios_crudos, centroides_m, bounds).

    criterios_crudos trae, ademas de los cinco criterios, "detalle" (componentes y variables reales de cada paquete)
    y "disponibilidad" (que fraccion de cada criterio tuvo dato), que no entran al ensamble.
    """
    poligonos_m, centros_m = unidades_paquetes(datos)
    ids = list(poligonos_m.index)
    if "_territorio" not in datos:
        datos["_territorio"], datos["_fuentes_territorio"] = territorio_de(datos, params, poligonos_m, centros_m)
    ruta_critica = datos["paquetes"].set_index("id_paquete")["ruta_critica"].astype(bool)
    c = criterios_de(datos, params, fecha_corte, poligonos_m, centros_m, datos["_territorio"], asignar=True, ruta_critica=ruta_critica)
    crudos = dict(c["crudos"])
    tabla, bounds_usados = m_ict.ensamblar_ict(crudos, params["pesos"], ids, bounds=bounds or m_ict.LIMITES_ABSOLUTOS)

    # un paquete sin ningun riesgo en el registro no es "seguro": nadie lo ha evaluado
    evaluado = pd.Series(ids, index=ids).isin(datos["riesgos"]["id_paquete_trabajo"]).astype(float)
    crudos["disponibilidad"] = pd.DataFrame({
        "severidad_riesgo": evaluado, "exposicion_proyecto": evaluado, "convergencia": evaluado,
        "vulnerabilidad_territorial": c["vul"]["disp_vulnerabilidad"], "amenazas_externas": c["ext"]["disp_amenazas_externas"],
    })
    terr = c["terr"]
    crudos["detalle"] = (terr.drop(columns=[x for x in ("codigo_municipio",) if x in terr])
                         .join(c["vul"].drop(columns=["vulnerabilidad_territorial", "disp_vulnerabilidad"]))
                         .join(c["ext"].drop(columns=["amenazas_externas", "disp_amenazas_externas"]))
                         .join(c["expo"][["amenazas_que_alcanzan"]])
                         .join(c["conv"].drop(columns=["convergencia"])))
    return tabla, crudos, centros_m, bounds_usados


def superficie_ict(datos, params, grid: gpd.GeoDataFrame, fecha_corte: pd.Timestamp) -> pd.DataFrame:
    """ICT de cada celda de la grilla con los mismos criterios, pesos y topes: las amenazas del registro que la alcanzan
    (por distancia) y el territorio real de la celda. Es el mapa de calor multicriterio del territorio."""
    celdas_m = gpd.GeoSeries(grid.to_crs(CRS_METRICO).geometry.values, index=grid["celda_id"], crs=CRS_METRICO)
    terr, _ = territorio_de(datos, params, celdas_m, celdas_m)
    c = criterios_de(datos, params, fecha_corte, celdas_m, celdas_m, terr, asignar=False, ruta_critica=None)
    tabla, _ = m_ict.ensamblar_ict(c["crudos"], params["pesos"], list(celdas_m.index), bounds=m_ict.LIMITES_ABSOLUTOS)
    tabla["nivel"] = tabla["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
    return tabla[["ICT", "nivel"]]


# ---------------------------------------------------------------------------
# Escalamiento a crisis
# ---------------------------------------------------------------------------

def _rango(nivel) -> int:
    return ORDEN_RAM.index(nivel) if nivel in ORDEN_RAM else -1


def amenazas_abiertas(datos) -> gpd.GeoDataFrame:
    r = datos["riesgos"]
    return r[(r["tipo"] == "amenaza") & (r["estado"] != "materializado")]


def sensibles(datos, params) -> pd.DataFrame:
    """Que resguardo o area protegida alcanza cada amenaza abierta (calculado una vez)."""
    if "_sensibles" not in datos:
        abiertas = amenazas_abiertas(datos)
        datos["_sensibles"] = m_ict.alcance_sensible(abiertas.to_crs(CRS_METRICO), _metrico(datos, "resguardos"),
                                                     _metrico(datos, "runap"), params["radios_influencia_m"],
                                                     params["escalamiento"])
    return datos["_sensibles"]


def reglas_por_amenaza(datos, params) -> pd.DataFrame:
    """Para cada amenaza abierta, las reglas de escalamiento que dispara por si sola (RAM y area sensible)."""
    e = params["escalamiento"]
    abiertas = amenazas_abiertas(datos)
    ruta_critica = datos["paquetes"].set_index("id_paquete")["ruta_critica"].astype(bool)
    sens = sensibles(datos, params)
    niveles_sensibles = set(e.get("niveles_area_sensible", ["H", "VH"]))
    filas = []
    for idx, a in abiertas.iterrows():
        causas = []
        if e.get("ram_vh_escala", True) and a["nivel_residual"] == "VH":
            causas.append(("ram_vh", f"Riesgo RAM muy alto (VH, {a['ram_residual']}): intolerable"))
        if e.get("ram_h_en_ruta_critica", True) and a["nivel_residual"] == "H" and ruta_critica.get(a["id_paquete_trabajo"], False):
            causas.append(("ram_h_ruta_critica", f"Riesgo RAM alto (H, {a['ram_residual']}) en un paquete de ruta crítica"))
        if e.get("riesgo_en_area_sensible", True) and a["nivel_residual"] in niveles_sensibles:
            if sens.at[idx, "alcanza_resguardo"]:
                causas.append(("area_sensible", f"Riesgo {a['nivel_residual']} cuya área de influencia alcanza el {sens.at[idx, 'alcanza_resguardo']}"))
            if sens.at[idx, "alcanza_area_protegida"]:
                causas.append(("area_sensible", f"Riesgo {a['nivel_residual']} cuya área de influencia alcanza el área protegida {sens.at[idx, 'alcanza_area_protegida']}"))
        if causas:
            filas.append({"indice": idx, "id_riesgo": a["id_riesgo"], "id_paquete": a["id_paquete_trabajo"],
                          "reglas": [c[0] for c in causas], "causas": [c[1] for c in causas]})
    return pd.DataFrame(filas, columns=["indice", "id_riesgo", "id_paquete", "reglas", "causas"])


REGLAS_DE_PAQUETE = ("ict_critico", "convergencia", "acciones_vencidas")


def causas_por_paquete(datos, params, tabla_ict, hoy: pd.Timestamp) -> dict[str, list[tuple[str, str]]]:
    """(regla, texto) de cada causa de escalamiento de cada paquete. Ver calcular_escalamiento."""
    e = params["escalamiento"]
    umbral_medio = params["umbrales_criticidad"]["medio"]
    riesgos = datos["riesgos"]
    vencidas = (riesgos[(riesgos["tipo"] == "amenaza") & (riesgos["estado"] != "materializado")
                        & (riesgos["fecha_ejecucion_accion"] < hoy)].groupby("id_paquete_trabajo").size())
    por_amenaza = reglas_por_amenaza(datos, params)
    salida = {}
    for id_paquete, fila in tabla_ict.iterrows():
        causas: list[tuple[str, str]] = []
        ict = float(fila["ICT"])
        if ict >= e["ict_critico"]:
            causas.append(("ict_critico", f"ICT de {ict:.0f} (crítico, {e['ict_critico']} o más)"))
        propias = por_amenaza[por_amenaza["id_paquete"] == id_paquete]
        for regla, uno, varios in (
                ("ram_vh", "1 riesgo RAM muy alto (VH, intolerable) sin materializar", "{n} riesgos RAM muy altos (VH, intolerables) sin materializar"),
                ("ram_h_ruta_critica", "1 riesgo RAM alto (H) en ruta crítica", "{n} riesgos RAM altos (H) en ruta crítica"),
                ("area_sensible", "1 riesgo alto cuya área de influencia alcanza un resguardo o un área protegida",
                 "{n} riesgos altos cuya área de influencia alcanza un resguardo o un área protegida")):
            n = int(propias["reglas"].map(lambda rs, r=regla: r in rs).sum()) if len(propias) else 0
            if n:
                causas.append((regla, uno if n == 1 else varios.format(n=n)))
        n_conv = int(fila.get("n_categorias_registro", 0) or 0) + int(fila.get("n_factores_territorio", 0) or 0)
        if n_conv >= e["min_amenazas_convergentes"] and ict >= umbral_medio:
            lista = fila.get("amenazas_convergentes") or ""
            causas.append(("convergencia", f"convergen {n_conv} amenazas ({lista}) con un ICT de {umbral_medio} o más"))
        n_venc = int(vencidas.get(id_paquete, 0))
        if n_venc >= e["min_acciones_vencidas"] and ict >= umbral_medio:
            causas.append(("acciones_vencidas", f"{n_venc} acciones de tratamiento vencidas con un ICT de {umbral_medio} o más"))
        salida[id_paquete] = causas
    return salida


def calcular_escalamiento(datos, params, tabla_ict, hoy: pd.Timestamp) -> pd.DataFrame:
    """Un paquete escala a "posible crisis" si:
      - su ICT ya es critico, o
      - tiene una amenaza abierta que la RAM considera intolerable (VH), alta (H) en ruta critica, o alta cuya area de
        influencia alcanza un resguardo o un area protegida, o
      - una causa secundaria (convergencia de amenazas, acciones de tratamiento vencidas) coincide con un ICT al menos
        medio: asi una coincidencia aislada en una zona tranquila no dispara una alerta sin respaldo del indice.
    `tabla_ict` debe traer ICT y, para la regla de convergencia, n_categorias_registro y n_factores_territorio.
    """
    filas = []
    for id_paquete, causas in causas_por_paquete(datos, params, tabla_ict, hoy).items():
        filas.append({"id_paquete": id_paquete, "escalamiento": bool(causas),
                      "reglas_escalamiento": ",".join(dict.fromkeys(c[0] for c in causas)),
                      "causas_escalamiento": "; ".join(c[1] for c in causas)})
    return pd.DataFrame(filas).set_index("id_paquete")


def puntos_de_crisis(datos, params, tabla: pd.DataFrame, causas: dict) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Donde un evento podria escalar a crisis y la zona de intervencion prioritaria alrededor.

    Las reglas de una amenaza (RAM, area sensible) se ubican en la amenaza; las del paquete entero (ICT critico,
    convergencia, acciones vencidas) en su centro. El radio de la zona es el de influencia de la categoria.
    """
    radios = params["radios_influencia_m"]
    niveles = params["ram"]["niveles"]
    abiertas = amenazas_abiertas(datos)
    por_amenaza = reglas_por_amenaza(datos, params)
    paq = datos["paquetes"].set_index("id_paquete")
    _, centros_m = unidades_paquetes(datos)
    centros = gpd.GeoSeries(centros_m, crs=CRS_METRICO).to_crs(CRS_GEOGRAFICO)
    hoy = pd.Timestamp.now().normalize()
    filas = []
    for _, r in por_amenaza.iterrows():
        if not bool(tabla.at[r["id_paquete"], "escalamiento"]):
            continue
        a = abiertas.loc[r["indice"]]
        nivel = a["nivel_residual"]
        filas.append({
            "id_punto": f"PC-{a['id_riesgo']}", "id_paquete": r["id_paquete"], "nombre_paquete": paq.at[r["id_paquete"], "nombre"],
            "tipo": "riesgo", "id_riesgo": a["id_riesgo"], "categoria": a["categoria"], "nivel_ram": nivel,
            "ram": a["ram_residual"], "estado": a["estado"], "reglas": ",".join(r["reglas"]), "causas": "; ".join(r["causas"]),
            "n_causas": len(r["causas"]),
            "prioridad": "critica" if nivel == "VH" else "alta",
            "radio_m": float(radios.get(a["categoria"], radios.get("default", 2500))),
            "decision": niveles.get(nivel, {}).get("decision"), "aprueba": niveles.get(nivel, {}).get("aprueba"),
            "accion_tratamiento": a.get("accion_tratamiento"),
            "fecha_accion": None if pd.isna(a.get("fecha_ejecucion_accion")) else pd.Timestamp(a["fecha_ejecucion_accion"]).date().isoformat(),
            "accion_vencida": bool(pd.notna(a.get("fecha_ejecucion_accion")) and a["fecha_ejecucion_accion"] < hoy),
            "geometry": a.geometry,
        })
    for id_paquete, f in tabla[tabla["escalamiento"]].iterrows():
        propias = [c for c in causas.get(id_paquete, []) if c[0] in REGLAS_DE_PAQUETE]
        if not propias:
            continue
        reglas = [c[0] for c in propias]
        peor = f.get("ram_peor_residual")
        filas.append({
            "id_punto": f"PC-{id_paquete}", "id_paquete": id_paquete, "nombre_paquete": paq.at[id_paquete, "nombre"],
            "tipo": "paquete", "id_riesgo": None, "categoria": None, "nivel_ram": peor if isinstance(peor, str) else None,
            "ram": None, "estado": None, "reglas": ",".join(reglas), "causas": "; ".join(c[1] for c in propias),
            "n_causas": len(propias),
            "prioridad": "critica" if "ict_critico" in reglas else "alta",
            "radio_m": float(radios.get("default", 2500)),
            "decision": "Revisar el paquete completo: varias causas a la vez",
            "aprueba": niveles.get(peor, {}).get("aprueba") if isinstance(peor, str) else None,
            "accion_tratamiento": None, "fecha_accion": None, "accion_vencida": "acciones_vencidas" in reglas,
            "geometry": centros[id_paquete],
        })
    cols = ["id_punto", "id_paquete", "nombre_paquete", "tipo", "id_riesgo", "categoria", "nivel_ram", "ram", "estado",
            "reglas", "causas", "n_causas", "prioridad", "radio_m", "decision", "aprueba", "accion_tratamiento",
            "fecha_accion", "accion_vencida", "geometry"]
    puntos = gpd.GeoDataFrame(filas, columns=cols, geometry="geometry", crs=CRS_GEOGRAFICO)
    if not len(puntos):
        vacia = gpd.GeoDataFrame({"id_paquete": [], "prioridad": [], "n_puntos": []}, geometry=[], crs=CRS_GEOGRAFICO)
        return puntos, vacia
    pm = puntos.to_crs(CRS_METRICO)
    zonas = []
    for id_paquete, g in pm.groupby("id_paquete"):
        forma = g.geometry.buffer(g["radio_m"].to_numpy()).union_all()
        zonas.append({"id_paquete": id_paquete, "nombre_paquete": g["nombre_paquete"].iloc[0],
                      "prioridad": "critica" if (g["prioridad"] == "critica").any() else "alta",
                      "n_puntos": int(len(g)), "area_km2": round(forma.area / 1e6, 1), "geometry": forma})
    zonas = gpd.GeoDataFrame(zonas, geometry="geometry", crs=CRS_METRICO).to_crs(CRS_GEOGRAFICO)
    return puntos, zonas


def resumen_ram(riesgos: pd.DataFrame, ids_paquete: list[str]) -> pd.DataFrame:
    """Por paquete: amenazas abiertas en cada nivel RAM residual y el peor nivel (inherente y residual)."""
    amen = riesgos[(riesgos["tipo"] == "amenaza") & (riesgos["estado"] != "materializado")]
    t = pd.DataFrame(index=pd.Index(ids_paquete, name="id_paquete"))
    for n in ORDEN_RAM:
        t[f"ram_{n}"] = amen[amen["nivel_residual"] == n].groupby("id_paquete_trabajo").size().reindex(ids_paquete).fillna(0).astype(int)
    for etapa in ("inherente", "residual"):
        peor = amen.dropna(subset=[f"nivel_{etapa}"]).groupby("id_paquete_trabajo")[f"nivel_{etapa}"].agg(lambda s: max(s, key=ORDEN_RAM.index))
        t[f"ram_peor_{etapa}"] = peor.reindex(ids_paquete)
    return t


def calcular_tendencia(datos, params, hoy: pd.Timestamp, ict_hoy: pd.Series, bounds: dict) -> pd.DataFrame:
    """ICT de `ventana_tendencia_dias` atras con los MISMOS limites (la escala es fija): el delta refleja cambios reales
    en los riesgos y en la lluvia, no un reescalado."""
    dias = params["escalamiento"]["ventana_tendencia_dias"]
    tabla_antes, _, _, _ = calcular_ict_para_fecha(datos, params, hoy - pd.Timedelta(days=dias), bounds=bounds)
    antes = tabla_antes["ICT"].reindex(ict_hoy.index).fillna(0)
    delta = (ict_hoy - antes).round(1)
    return pd.DataFrame({"id_paquete": ict_hoy.index, "ict_hace_ndias": antes.round(1), "tendencia_delta": delta,
                         "tendencia_alerta": delta >= params["escalamiento"]["incremento_tendencia_alerta"]}).set_index("id_paquete")


# ---------------------------------------------------------------------------
# Superficie de calor y puntos calientes
# ---------------------------------------------------------------------------

def superficie_de_calor(datos, params) -> gpd.GeoDataFrame:
    """Densidad (kernel) de las amenazas, ponderada por nivel RAM y estado, y de las oportunidades, sobre la grilla.
    Puntos calientes (Gi*) con la severidad SIN suavizar que cae en cada celda del area de estudio."""
    res = float(params["grid"]["resolucion_grados"])
    grid = m_esp.generar_grid(res)
    grid_m = grid.to_crs(CRS_METRICO)
    r = datos["riesgos"]
    amen = r[r["tipo"] == "amenaza"].copy()
    amen["estado_calc"] = amen["estado"]
    amen["peso"] = m_ict.severidad_amenazas(amen, params["factores_estado"])
    opor = r[(r["tipo"] == "oportunidad") & (r["estado"] != "materializado")].copy()
    opor["peso"] = opor["puntaje_ram"].fillna(1).astype(float)
    bw = float(params["kde"]["bandwidth_m"])
    grid["intensidad"] = grid["celda_id"].map(m_esp.kde_superficie(amen.to_crs(CRS_METRICO), grid_m, "peso", bw)).fillna(0.0).round(4)
    grid["intensidad_oportunidades"] = grid["celda_id"].map(m_esp.kde_superficie(opor.to_crs(CRS_METRICO), grid_m, "peso", bw)).fillna(0.0).round(4)
    grid = grid[(grid["intensidad"] > 0.01) | (grid["intensidad_oportunidades"] > 0.01)].copy()

    # Gi*: severidad de las amenazas que caen en cada celda (la celda es el cuadrado alrededor de su punto)
    mitad = res / 2
    gx, gy = grid.geometry.x.to_numpy(), grid.geometry.y.to_numpy()
    suma = np.zeros(len(grid))
    for x, y, p in zip(amen.geometry.x, amen.geometry.y, amen["peso"]):
        dentro = np.where((np.abs(gx - x) <= mitad) & (np.abs(gy - y) <= mitad))[0]
        if len(dentro):
            suma[dentro[0]] += p
    grid["severidad_celda"] = suma.round(2)
    centros = gpd.GeoSeries(grid.to_crs(CRS_METRICO).geometry.values, index=grid["celda_id"], crs=CRS_METRICO)
    gi = m_esp.getis_ord_gi_star(centros, pd.Series(suma, index=grid["celda_id"]), params["hotspot"]["k_vecinos"])
    z_sig = float(params["hotspot"]["z_score_significativo"])
    grid["gi_z"] = grid["celda_id"].map(gi["z_score"]).astype(float)
    grid["punto_caliente"] = (grid["gi_z"] >= z_sig) & (grid["severidad_celda"] > 0)
    return grid


def paquetes_en_punto_caliente(datos, grid: gpd.GeoDataFrame, res_grados: float) -> pd.Series:
    """Si alguna celda de punto caliente cae dentro del paquete o a menos de media celda de el."""
    pm = _metrico(datos, "paquetes").set_index("id_paquete")
    calientes = grid[grid["punto_caliente"]].to_crs(CRS_METRICO)
    if not len(calientes):
        return pd.Series(False, index=pm.index)
    margen = res_grados * 111_000 / 2
    union = calientes.geometry.union_all()
    return pm.geometry.buffer(margen).intersects(union)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

def construir_alertas(tabla: pd.DataFrame, datos, params, puntos: gpd.GeoDataFrame, hoy: pd.Timestamp) -> list[dict]:
    """Una alerta por paquete en escalamiento o con tendencia al alza: causas, puntos de crisis y que hacer."""
    niveles = params["ram"]["niveles"]
    paq = datos["paquetes"].set_index("id_paquete")
    sens = sensibles(datos, params)
    abiertas = amenazas_abiertas(datos)
    alertas = []
    for id_paquete, f in tabla.iterrows():
        motivos, causas = [], []
        if f["escalamiento"]:
            motivos.append(f["causas_escalamiento"])
            causas += [{"regla": r, "texto": t} for r, t in zip(str(f["reglas_escalamiento"]).split(","), str(f["causas_escalamiento"]).split("; "))]
        if bool(f.get("tendencia_alerta")):
            t = f"el ICT subió {f['tendencia_delta']:+.1f} puntos en {params['escalamiento']['ventana_tendencia_dias']} días"
            motivos.append(t)
            causas.append({"regla": "tendencia", "texto": t})
        if not motivos:
            continue
        acciones = []
        peor = f.get("ram_peor_residual")
        if isinstance(peor, str) and peor in niveles and _rango(peor) >= _rango("H"):
            acciones.append(f"{niveles[peor]['decision'].rstrip('.')}. Decide: {niveles[peor]['aprueba']}.")
        propias = abiertas[abiertas["id_paquete_trabajo"] == id_paquete]
        resg = sorted({x for x in sens.loc[sens.index.intersection(propias.index), "alcanza_resguardo"] if x})
        if resg:
            acciones.append(f"Activar el relacionamiento y revisar la consulta previa con {', '.join(resg)}.")
        aps = sorted({x for x in sens.loc[sens.index.intersection(propias.index), "alcanza_area_protegida"] if x})
        if aps:
            acciones.append(f"Coordinar con la autoridad ambiental el manejo cerca de {', '.join(aps)}.")
        if "acciones_vencidas" in str(f["reglas_escalamiento"]):
            acciones.append("Actualizar las acciones de tratamiento vencidas y su responsable.")
        if bool(f.get("tendencia_alerta")):
            acciones.append("Revisar qué cambió esta semana (riesgos nuevos, lluvia) antes de que suba de nivel.")
        n_puntos = int((puntos["id_paquete"] == id_paquete).sum()) if len(puntos) else 0
        prioridad = "critica" if (f["nivel"] == "critico" or "ram_vh" in str(f["reglas_escalamiento"])) else "alta" if f["escalamiento"] else "media"
        clave = f"{id_paquete}|{','.join(sorted(c['regla'] for c in causas))}"
        alertas.append({
            "id_alerta": hashlib.sha1(clave.encode()).hexdigest()[:10],
            "id_paquete": id_paquete, "nombre_paquete": paq.at[id_paquete, "nombre"],
            "id_proyecto": paq.at[id_paquete, "id_proyecto"],
            "ict": float(f["ICT"]), "nivel": f["nivel"], "prioridad": prioridad,
            "motivos": motivos, "causas": causas, "acciones": acciones, "puntos_crisis": n_puntos,
            "municipio": f.get("municipio"), "generada_en": hoy.isoformat(),
        })
    orden = {"critica": 0, "alta": 1, "media": 2}
    return sorted(alertas, key=lambda a: (orden[a["prioridad"]], -a["ict"]))


# ---------------------------------------------------------------------------
# Paso
# ---------------------------------------------------------------------------

def main():
    asegurar_directorios()
    params = cargar_parametros()
    datos = cargar_plata()
    hoy = pd.Timestamp.now().normalize()

    tabla, crudos, _, bounds = calcular_ict_para_fecha(datos, params, hoy)
    ids = list(tabla.index)
    tabla["nivel"] = tabla["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
    tabla["indice_confianza"] = m_ict.indice_confianza(crudos["disponibilidad"], params["pesos"])
    tabla["indice_oportunidad"] = m_ict.indice_oportunidad(datos["riesgos"], params["agregacion"]["peso_maximo"],
                                                           params["agregacion"]["peso_promedio"], ids)
    tabla = tabla.join(crudos["detalle"]).join(crudos["disponibilidad"].add_prefix("disp_"))
    tabla = tabla.join(resumen_ram(datos["riesgos"], ids))
    causas = causas_por_paquete(datos, params, tabla, hoy)
    tabla = tabla.join(calcular_escalamiento(datos, params, tabla, hoy))
    tabla = tabla.join(calcular_tendencia(datos, params, hoy, tabla["ICT"], bounds))

    grid = superficie_de_calor(datos, params)
    ict_celdas = superficie_ict(datos, params, grid, hoy)
    grid["ict"] = grid["celda_id"].map(ict_celdas["ICT"]).round(1)
    grid["nivel"] = grid["celda_id"].map(ict_celdas["nivel"])
    tabla["en_punto_caliente"] = paquetes_en_punto_caliente(datos, grid, float(params["grid"]["resolucion_grados"])).reindex(ids).fillna(False)
    puntos, zonas = puntos_de_crisis(datos, params, tabla, causas)
    tabla["puntos_crisis"] = puntos.groupby("id_paquete").size().reindex(ids).fillna(0).astype(int) if len(puntos) else 0

    # --- Publicar en Oro ---
    num = tabla.select_dtypes("number").columns
    tabla[num] = tabla[num].round(4)
    gdf_paquetes = datos["paquetes"].merge(tabla.reset_index(), on="id_paquete", how="left")
    gdf_paquetes.to_file(ORO / "paquetes_ict.geojson", driver="GeoJSON")
    grid.to_file(ORO / "grid_calor.geojson", driver="GeoJSON")
    puntos.to_file(ORO / "puntos_crisis.geojson", driver="GeoJSON")
    zonas.to_file(ORO / "zonas_intervencion.geojson", driver="GeoJSON")

    # el registro en Oro dice tambien que amenaza es un punto de crisis
    riesgos = datos["riesgos"].copy()
    pc = puntos[puntos["tipo"] == "riesgo"].set_index("id_riesgo")["causas"] if len(puntos) else pd.Series(dtype=object)
    riesgos["punto_crisis"] = riesgos["id_riesgo"].isin(pc.index)
    riesgos["causa_crisis"] = riesgos["id_riesgo"].map(pc)
    sens = sensibles(datos, params)
    riesgos = riesgos.join(sens)
    # municipio donde esta cada riesgo (por sus coordenadas, no por su paquete): para contarlos por municipio
    mun = _metrico(datos, "municipios")
    if mun is not None and len(riesgos):
        con_punto = riesgos[riesgos.geometry.notna() & ~riesgos.geometry.is_empty]
        puntos_m = gpd.GeoSeries(con_punto.to_crs(CRS_METRICO).geometry.values, index=con_punto.index, crs=CRS_METRICO)
        riesgos["codigo_municipio"] = m_terr.municipio_de(puntos_m, mun).reindex(riesgos.index)
        riesgos["municipio"] = riesgos["codigo_municipio"].map(mun.set_index("codigo")["nombre"])
    riesgos.to_file(ORO / "riesgos.geojson", driver="GeoJSON")
    for nombre in ["proyectos", "comunidades", "areas", "hidro", "vias"]:
        datos[nombre].to_file(ORO / f"{nombre}.geojson", driver="GeoJSON")

    alertas = construir_alertas(tabla, datos, params, puntos, hoy)
    with open(ORO / "alertas.json", "w", encoding="utf-8") as f:
        json.dump(alertas, f, ensure_ascii=False, indent=2, default=str)

    print("Oro del ICT generado en:", ORO)
    print(tabla[["ICT", "nivel", "severidad_riesgo", "exposicion_proyecto", "vulnerabilidad_territorial",
                 "amenazas_externas", "convergencia", "indice_confianza", "escalamiento"]].round(2).to_string())
    fuentes = datos.get("_fuentes_territorio", {})
    print(f"\nTerritorio real usado: {', '.join(f'{k} ({v})' for k, v in fuentes.items()) or 'ninguno (faltan datos abiertos)'}")
    print(f"Puntos de crisis: {len(puntos)} · zonas de intervención: {len(zonas)} · celdas calientes (Gi*): {int(grid['punto_caliente'].sum())}")
    print(f"Alertas activas: {len(alertas)}")


if __name__ == "__main__":
    main()
