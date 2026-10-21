"""Fechas del registro de riesgos: leerlas como las escribe la gente y revisar que cuenten una historia posible.

Funciones puras (sin leer archivos). Un riesgo tiene tres fechas: cuando se identifico, cuando se materializo (solo si ya
ocurrio) y cuando se ejecuta su accion de tratamiento. Reglas:

  * Se leen en formato ISO (2026-05-16) o dia/mes/ano (16/05/2026), que es como se escribe a mano en un Excel.
  * Un riesgo materializado tiene fecha de materializacion, no posterior a la fecha de corte y no anterior a la de
    identificacion. Si llega antes de la identificacion, las dos se cruzaron al escribirlas: se intercambian. Si llega en el
    futuro, se prueba con un ano menos (el error mas comun); si tampoco cuadra, queda sin fecha. En todos estos casos el
    riesgo se marca para revisar (`revisar_fechas`) y `problema_fechas` dice por que.
  * Un riesgo abierto no tiene fecha de materializacion (si la trae, se marca).
  * La accion no puede ser anterior a la identificacion, ni la identificacion posterior al corte (se marcan, no se cambian).
"""
from __future__ import annotations

import pandas as pd

COLUMNAS = ("fecha_identificacion", "fecha_materializacion", "fecha_ejecucion_accion")


def leer(serie: pd.Series) -> tuple[pd.Series, int]:
    """Fechas ISO o dia/mes/ano en una misma columna. Devuelve las fechas y cuantas venian dia/mes/ano."""
    texto = serie.astype("string").str.strip()
    iso = pd.to_datetime(texto.where(~texto.str.contains("/", na=False)), format="ISO8601", errors="coerce")
    dma = pd.to_datetime(texto.where(texto.str.contains("/", na=False)), format="%d/%m/%Y", errors="coerce")
    return iso.fillna(dma).dt.normalize(), int(dma.notna().sum())


def revisar(df: pd.DataFrame, corte: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Lee las tres fechas, corrige lo que tiene una sola explicacion y marca lo que hay que revisar.
    `df` con `estado` ya normalizado (latente, proximo_a_materializarse, materializado)."""
    df = df.copy()
    corte = pd.Timestamp(corte).normalize()
    rep = {"fechas_dia_mes_ano": 0}
    for c in COLUMNAS:
        df[c], n = leer(df[c])
        rep["fechas_dia_mes_ano"] += n
    problemas = pd.Series([[] for _ in range(len(df))], index=df.index)

    def anotar(mascara, texto):
        for i in df.index[mascara]:
            problemas[i] = problemas[i] + [texto]
        return int(mascara.sum())

    mat = df["estado"] == "materializado"
    ident, fm = df["fecha_identificacion"], df["fecha_materializacion"]

    cruzadas = mat & fm.notna() & ident.notna() & (fm < ident)
    rep["fechas_materializacion_antes_de_identificacion"] = anotar(cruzadas, "materialización anotada antes de la identificación (se intercambiaron)")
    df.loc[cruzadas, ["fecha_identificacion", "fecha_materializacion"]] = df.loc[cruzadas, ["fecha_materializacion", "fecha_identificacion"]].to_numpy()

    fm = df["fecha_materializacion"]
    futura = mat & fm.notna() & (fm > corte)
    un_ano_menos = fm - pd.DateOffset(years=1)
    arreglable = futura & (un_ano_menos <= corte) & (df["fecha_identificacion"].isna() | (un_ano_menos >= df["fecha_identificacion"]))
    rep["fechas_materializacion_futura_corregida"] = anotar(arreglable, "materialización en el futuro: se le quitó un año")
    rep["fechas_materializacion_futura_sin_corregir"] = anotar(futura & ~arreglable, "materialización en el futuro sin explicación (queda sin fecha)")
    df.loc[arreglable, "fecha_materializacion"] = un_ano_menos[arreglable]
    df.loc[futura & ~arreglable, "fecha_materializacion"] = pd.NaT

    rep["fechas_materializado_sin_fecha"] = anotar(mat & df["fecha_materializacion"].isna() & ~(futura & ~arreglable),
                                                   "materializado sin fecha de materialización")
    rep["fechas_abierto_con_materializacion"] = anotar(~mat & df["fecha_materializacion"].notna(), "abierto pero con fecha de materialización")
    rep["fechas_identificacion_futura"] = anotar(df["fecha_identificacion"] > corte, "identificado después de la fecha de corte")
    rep["fechas_accion_antes_de_identificacion"] = anotar(
        df["fecha_ejecucion_accion"].notna() & df["fecha_identificacion"].notna() & (df["fecha_ejecucion_accion"] < df["fecha_identificacion"]),
        "acción anterior a la identificación")

    df["problema_fechas"] = problemas.map(lambda p: "; ".join(p) if p else None)
    df["revisar_fechas"] = df["problema_fechas"].notna()
    rep["riesgos_fechas_por_revisar"] = int(df["revisar_fechas"].sum())
    return df, rep
