"""
Motor del Indice de Criticidad Territorial (ICT).

Implementa el calculo de la Seccion 6 de la propuesta para cualquier unidad de analisis (paquete de trabajo o celda de
la grilla): cinco criterios en una escala FIJA de 0 a 1, ponderacion configurable y clasificacion en niveles.

  severidad_riesgo            nivel RAM residual de las amenazas que alcanzan la unidad x factor de estado
  exposicion_proyecto         ruta critica + cuantas amenazas abiertas alcanzan la unidad
  vulnerabilidad_territorial  territorio etnico (ANT), pobreza (DANE), areas protegidas (RUNAP), acceso (INVIAS + IGAC)
  amenazas_externas           lluvia reciente (IDEAM), anomalia de lluvia (CHIRPS), emergencias (UNGRD), delitos (MinDefensa)
  convergencia                categorias de amenaza del registro + factores del territorio que coinciden

La escala es absoluta (1 = el peor caso que define parametros.yaml), no relativa entre unidades: el ICT de un paquete no
cambia porque se agregue otro, y dos fechas se comparan sin reescalar. Un componente sin dato no se imputa: el criterio
se calcula con los demas y la falta baja el indice de confianza.

Las funciones que miden distancias reciben datos en un CRS metrico (config.CRS_METRICO).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd

ORDEN_RAM = ["N", "L", "M", "H", "VH"]

CRITERIOS = [
    "severidad_riesgo", "exposicion_proyecto", "vulnerabilidad_territorial",
    "amenazas_externas", "convergencia",
]
COMPONENTES_VULNERABILIDAD = ("etnico", "pobreza", "ambiental", "acceso")
COMPONENTES_EXTERNAS = ("lluvia_reciente", "anomalia_lluvia", "emergencias", "seguridad")
# Como se nombran en los textos de convergencia y escalamiento
NOMBRES = {
    "seguridad_fisica": "seguridad física", "climatico": "climático", "social_comunidad": "social",
    "logistico_acceso": "logístico y de acceso", "ambiental": "ambiental", "contractual": "contractual",
    "lluvia_reciente": "lluvia reciente (IDEAM)", "anomalia_lluvia": "lluvia anómala (CHIRPS)",
    "emergencias": "emergencias (UNGRD)", "seguridad": "delitos (MinDefensa)",
}


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------

def decaimiento_lineal(distancia_m: np.ndarray, radio_m: float) -> np.ndarray:
    """1.0 en distancia=0, decrece linealmente a 0.0 en distancia=radio."""
    valor = 1.0 - np.asarray(distancia_m, dtype=float) / radio_m
    return np.clip(valor, 0.0, 1.0)


def normalizar_minmax(serie: pd.Series) -> pd.Series:
    if serie.empty:
        return serie
    minimo, maximo = serie.min(), serie.max()
    if maximo == minimo:
        return pd.Series(0.0, index=serie.index)
    return (serie - minimo) / (maximo - minimo)


def saturar(valor, maximo) -> float:
    return float(min(valor / maximo, 1.0)) if maximo else 0.0


def escala(serie: pd.Series, maximo: float) -> pd.Series:
    """Lleva una variable cruda a 0-1 con un tope fijo: maximo o mas = 1. Conserva los NaN (sin dato)."""
    if not maximo:
        return serie * np.nan
    return (pd.to_numeric(serie, errors="coerce") / maximo).clip(0.0, 1.0)


def estado_efectivo(row: pd.Series, fecha_corte: pd.Timestamp) -> str | None:
    """Estado de un riesgo tal como se veria en `fecha_corte` (para backtest/tendencia).

    Devuelve None si el riesgo aun no habia sido identificado en esa fecha.
    """
    if pd.isna(row["fecha_identificacion"]) or row["fecha_identificacion"] > fecha_corte:
        return None
    if pd.notna(row["fecha_materializacion"]) and row["fecha_materializacion"] <= fecha_corte:
        return "materializado"
    if row["estado"] == "materializado":
        # se materializara despues de fecha_corte -> en esa fecha aun no lo estaba
        return "proximo_a_materializarse"
    return row["estado"]


def combinar(componentes: pd.DataFrame, pesos: dict) -> tuple[pd.Series, pd.Series]:
    """Promedio ponderado de los componentes CON dato, y que fraccion del peso tuvo dato (disponibilidad).

    Un componente sin dato (NaN) queda inactivo: no cuenta como cero, se reparte su peso entre los demas.
    """
    cols = [c for c in pesos if c in componentes]
    w = pd.Series({c: float(pesos[c]) for c in cols})
    if not len(cols) or w.sum() <= 0:
        cero = pd.Series(0.0, index=componentes.index)
        return cero, cero
    v = componentes[cols].astype(float)
    con_dato = v.notna()
    peso_con_dato = con_dato.mul(w, axis=1).sum(axis=1)
    suma = v.fillna(0.0).mul(w, axis=1).sum(axis=1)
    valor = (suma / peso_con_dato.replace(0, np.nan)).fillna(0.0).clip(0.0, 1.0)
    return valor, (peso_con_dato / w.sum()).clip(0.0, 1.0)


# ---------------------------------------------------------------------------
# Amenazas del registro: cuales estan vigentes en una fecha y a que unidades alcanzan
# ---------------------------------------------------------------------------

def amenazas_en_fecha(riesgos: pd.DataFrame, fecha_corte: pd.Timestamp | None = None) -> pd.DataFrame:
    """Amenazas del registro con su estado en `fecha_corte` (columna estado_calc). Sin fecha: el estado actual."""
    df = riesgos[riesgos["tipo"] == "amenaza"].copy()
    if fecha_corte is not None:
        df["estado_calc"] = df.apply(lambda r: estado_efectivo(r, fecha_corte), axis=1)
        df = df[df["estado_calc"].notna()]
    else:
        df["estado_calc"] = df["estado"]
    return df


def pesos_alcance(
    unidades_m: gpd.GeoSeries,
    amenazas_m: gpd.GeoDataFrame,
    radios_m: dict,
    asignacion: pd.Series | None = None,
) -> np.ndarray:
    """Matriz (unidades x amenazas) con cuanto alcanza cada amenaza a cada unidad, de 0 a 1.

    Vale 1 si el registro asigna la amenaza a la unidad (`asignacion`: id de la unidad de cada amenaza). Si no, decae
    linealmente con la distancia desde la ubicacion de la amenaza hasta la unidad, y llega a 0 en el radio de influencia
    de su categoria (parametros.yaml -> radios_influencia_m).
    """
    n_u, n_a = len(unidades_m), len(amenazas_m)
    w = np.zeros((n_u, n_a))
    if not n_u or not n_a:
        return w
    ids = list(unidades_m.index)
    pos = {u: i for i, u in enumerate(ids)}
    defecto = float(radios_m.get("default", 2500))
    for j, (_, a) in enumerate(amenazas_m.iterrows()):
        radio = float(radios_m.get(a.get("categoria"), defecto))
        w[:, j] = decaimiento_lineal(unidades_m.distance(a.geometry).to_numpy(), radio)
        if asignacion is not None:
            u = asignacion.iloc[j]
            if u in pos:
                w[pos[u], j] = 1.0
    return w


def severidad_amenazas(amenazas: pd.DataFrame, factores_estado: dict) -> np.ndarray:
    """Puntaje del nivel RAM residual (N=1 ... VH=5) x factor de su estado (latente, proximo, materializado)."""
    factor = amenazas["estado_calc"].map(factores_estado).fillna(1.0).to_numpy(dtype=float)
    return amenazas["puntaje_ram"].fillna(1).to_numpy(dtype=float) * factor


# ---------------------------------------------------------------------------
# Criterios (todos devuelven valores en 0-1)
# ---------------------------------------------------------------------------

def criterio_severidad(w: np.ndarray, sev: np.ndarray, peso_maximo: float, peso_promedio: float,
                       maximo_teorico: float, ids) -> pd.Series:
    """0,7 x la amenaza mas severa que alcanza la unidad + 0,3 x el promedio ponderado por severidad, sobre el maximo
    posible (VH materializado). Las amenazas que alcanzan solo en parte pesan segun su alcance."""
    if not w.size:
        return pd.Series(0.0, index=ids)
    alcanzada = w * sev[None, :]
    maximo = alcanzada.max(axis=1)
    suma = alcanzada.sum(axis=1)
    promedio = np.divide((alcanzada * sev[None, :]).sum(axis=1), suma, out=np.zeros_like(suma), where=suma > 0)
    crudo = maximo * peso_maximo + promedio * peso_promedio
    return pd.Series(np.clip(crudo / maximo_teorico, 0.0, 1.0), index=ids)


def criterio_exposicion(w_abiertas: np.ndarray, ruta_critica: pd.Series, cfg: dict, ids) -> pd.DataFrame:
    """Peso de la ruta critica + cuantas amenazas abiertas alcanzan la unidad (saturado)."""
    n = w_abiertas.sum(axis=1) if w_abiertas.size else np.zeros(len(ids))
    rc = ruta_critica.reindex(ids).fillna(False).astype(float).to_numpy()
    peso_rc = float(cfg.get("peso_ruta_critica", 0.5))
    valor = peso_rc * rc + (1 - peso_rc) * np.clip(n / float(cfg.get("amenazas_para_saturar", 20)), 0.0, 1.0)
    return pd.DataFrame({"exposicion_proyecto": valor, "amenazas_que_alcanzan": np.round(n, 1)}, index=ids)


def criterio_vulnerabilidad(terr: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Componentes reales de la vulnerabilidad (0-1) y el criterio combinado.

    etnico     fraccion de la unidad dentro de resguardos; si solo colinda (dentro del radio), cuenta la mitad
    pobreza    IPM del municipio (DANE, censo 2018) / 100
    ambiental  dentro de un area protegida = 1, decae hasta 0 en el radio
    acceso     fraccion de los km de vias cercanas que solo se transitan en tiempo seco
    """
    c = pd.DataFrame(index=terr.index)
    cerca_resguardo = 0.5 * decaimiento_lineal(terr["distancia_resguardo_km"].fillna(np.inf), float(cfg.get("radio_resguardo_km", 5)))
    c["etnico"] = np.where(terr["distancia_resguardo_km"].isna(), np.nan,
                           np.maximum(terr["fraccion_resguardo"].fillna(0.0), cerca_resguardo))
    c["pobreza"] = terr["ipm"] / 100.0
    cerca_area = decaimiento_lineal(terr["distancia_area_protegida_km"].fillna(np.inf), float(cfg.get("radio_area_protegida_km", 10)))
    c["ambiental"] = np.where(terr["distancia_area_protegida_km"].isna(), np.nan,
                              np.maximum(terr["fraccion_area_protegida"].fillna(0.0), cerca_area))
    c["acceso"] = terr["vias_tiempo_seco"]
    c = c.clip(0.0, 1.0)
    valor, disponible = combinar(c, cfg.get("componentes", {}))
    return c.add_prefix("vul_").assign(vulnerabilidad_territorial=valor, disp_vulnerabilidad=disponible)


def criterio_amenazas_externas(terr: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Componentes reales de las amenazas externas (0-1) y el criterio combinado."""
    c = pd.DataFrame(index=terr.index)
    c["lluvia_reciente"] = escala(terr["lluvia_mm"], float(cfg.get("lluvia_mm_para_saturar", 80)))
    c["anomalia_lluvia"] = escala(terr["anomalia_lluvia"], float(cfg.get("anomalia_para_saturar", 1.0)))
    c["emergencias"] = escala(terr["emergencias_por_ano"], float(cfg.get("emergencias_por_ano_para_saturar", 15)))
    c["seguridad"] = escala(terr["delitos_100k"], float(cfg.get("delitos_100k_para_saturar", 80)))
    valor, disponible = combinar(c, cfg.get("componentes", {}))
    return c.add_prefix("ext_").assign(amenazas_externas=valor, disp_amenazas_externas=disponible)


def criterio_convergencia(amenazas: pd.DataFrame, w: np.ndarray, externas: pd.DataFrame, cfg: dict, ids) -> pd.DataFrame:
    """Cuantas amenazas distintas coinciden en la unidad: categorias del registro (abiertas y con nivel RAM residual
    >= nivel_minimo_registro, que alcanzan la unidad al menos en `alcance_minimo`) + factores del territorio por encima
    de su umbral. Satura en `amenazas_para_saturar`."""
    minimo = ORDEN_RAM.index(cfg.get("nivel_minimo_registro", "M"))
    rango = amenazas["nivel_residual"].map(lambda n: ORDEN_RAM.index(n) if n in ORDEN_RAM else -1).to_numpy()
    abierta = (amenazas["estado_calc"] != "materializado").to_numpy()
    relevante = abierta & (rango >= minimo)
    categorias = amenazas["categoria"].to_numpy()
    alcance = float(cfg.get("alcance_minimo", 0.5))
    umbral = float(cfg.get("umbral_factor_territorio", 0.6))
    cols_ext = [f"ext_{c}" for c in COMPONENTES_EXTERNAS if f"ext_{c}" in externas]
    filas = []
    for i, u in enumerate(ids):
        cats = sorted(set(categorias[(w[i] >= alcance) & relevante])) if w.size else []
        fila_ext = externas.loc[u, cols_ext] if u in externas.index else pd.Series(dtype=float)
        factores = [c.removeprefix("ext_") for c, v in fila_ext.items() if pd.notna(v) and v >= umbral]
        total = len(cats) + len(factores)
        filas.append({"convergencia": min(total / float(cfg.get("amenazas_para_saturar", 5)), 1.0),
                      "n_categorias_registro": len(cats), "n_factores_territorio": len(factores),
                      "amenazas_convergentes": ", ".join(NOMBRES.get(x, x) for x in cats + factores)})
    return pd.DataFrame(filas, index=ids)


def alcance_sensible(amenazas_m: gpd.GeoDataFrame, resguardos_m: gpd.GeoDataFrame | None,
                     areas_m: gpd.GeoDataFrame | None, radios_m: dict, cfg: dict) -> pd.DataFrame:
    """Para cada amenaza: el resguardo indigena y el area protegida que alcanza su area de influencia (radio de su
    categoria), si su categoria puede afectarlos segun parametros.yaml -> escalamiento. Vacio = no alcanza ninguno."""
    out = pd.DataFrame({"alcanza_resguardo": None, "alcanza_area_protegida": None}, index=amenazas_m.index, dtype=object)
    defecto = float(radios_m.get("default", 2500))
    capas = (("alcanza_resguardo", resguardos_m, set(cfg.get("categorias_que_alcanzan_resguardos", []))),
             ("alcanza_area_protegida", areas_m, set(cfg.get("categorias_que_alcanzan_areas_protegidas", []))))
    for col, capa, cats in capas:
        if capa is None or not len(capa) or not cats:
            continue
        indice = capa.sindex
        for idx, a in amenazas_m.iterrows():
            if a.get("categoria") not in cats:
                continue
            zona = a.geometry.buffer(float(radios_m.get(a.get("categoria"), defecto)))
            cerca = indice.query(zona, predicate="intersects")
            if len(cerca):
                d = capa.geometry.iloc[cerca].distance(a.geometry)
                out.at[idx, col] = str(capa["nombre"].iloc[cerca[int(np.argmin(d.to_numpy()))]])
    return out


def indice_oportunidad(riesgos: pd.DataFrame, peso_maximo: float, peso_promedio: float, ids) -> pd.Series:
    """0-100 sobre las oportunidades ABIERTAS de cada paquete (la materializada ya es un beneficio logrado): misma
    agregacion que la severidad, sobre el nivel RAM del beneficio (5 = maximo)."""
    df = riesgos[(riesgos["tipo"] == "oportunidad") & (riesgos["estado"] != "materializado")].copy()
    if df.empty:
        return pd.Series(0.0, index=ids)
    df["s"] = df["puntaje_ram"].fillna(1).astype(float)

    def agregar(g: pd.DataFrame) -> float:
        return g["s"].max() * peso_maximo + np.average(g["s"], weights=g["s"]) * peso_promedio

    crudo = df.groupby("id_paquete_trabajo").apply(agregar, include_groups=False)
    return (crudo.reindex(ids).fillna(0.0) / 5.0 * 100).clip(0, 100).round(1)


# ---------------------------------------------------------------------------
# Ensamble del ICT
# ---------------------------------------------------------------------------

LIMITES_ABSOLUTOS = {c: (0.0, 1.0) for c in CRITERIOS}


def ensamblar_ict(
    criterios_crudos: dict[str, pd.Series],
    pesos: dict[str, float],
    ids_paquete: list[str],
    bounds: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    """Normaliza cada criterio a 0-1 y calcula el ICT ponderado (0-100), con la contribucion por criterio.

    `bounds` fija el minimo/maximo de cada criterio. El piloto pasa LIMITES_ABSOLUTOS (los criterios ya vienen en una
    escala fija de 0 a 1); sin `bounds` se usa min-max sobre las unidades recibidas, que hace el ICT relativo al
    conjunto (un paquete nuevo cambiaria el de los demas). Devuelve (tabla, bounds_usados).
    """
    tabla = pd.DataFrame(index=pd.Index(ids_paquete, name="id_paquete"))
    contribuciones = pd.DataFrame(index=pd.Index(ids_paquete, name="id_paquete"))
    bounds_usados: dict[str, tuple[float, float]] = {}

    for criterio in CRITERIOS:
        crudo = criterios_crudos.get(criterio, pd.Series(dtype=float)).reindex(ids_paquete).fillna(0.0)
        if bounds and criterio in bounds:
            minimo, maximo = bounds[criterio]
        else:
            minimo, maximo = float(crudo.min()), float(crudo.max())
        bounds_usados[criterio] = (minimo, maximo)

        if maximo > minimo:
            normalizado = ((crudo - minimo) / (maximo - minimo)).clip(0.0, 1.0)
        else:
            normalizado = crudo * 0.0
        tabla[criterio] = normalizado
        contribuciones[criterio] = normalizado * pesos[criterio] * 100

    tabla["ICT"] = contribuciones[CRITERIOS].sum(axis=1).round(1)
    for criterio in CRITERIOS:
        contribuciones[criterio] = contribuciones[criterio].round(1)

    return tabla.join(contribuciones, rsuffix="_contrib"), bounds_usados


def clasificar_ict(valor: float, umbrales: dict) -> str:
    if valor >= umbrales["alto"]:
        return "critico"
    if valor >= umbrales["medio"]:
        return "alto"
    if valor >= umbrales["bajo"]:
        return "medio"
    return "bajo"


def indice_confianza(disponibilidad: pd.DataFrame, pesos: dict) -> pd.Series:
    """Fraccion de la informacion del modelo que esta disponible y al dia para cada unidad (0-1), ponderada por el peso
    de cada criterio. Distingue una zona tranquila (con datos, valores bajos) de una zona sin informacion."""
    w = pd.Series({c: float(pesos[c]) for c in CRITERIOS})
    d = disponibilidad.reindex(columns=CRITERIOS).fillna(0.0)
    return (d.mul(w, axis=1).sum(axis=1) / w.sum()).round(2)
