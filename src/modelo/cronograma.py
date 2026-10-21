"""Cronograma por actividades: pesos, avance y fechas, de la actividad al paquete y al proyecto.

Funciones puras (sin leer archivos). La idea: la actividad es la unica fuente. Cada una pesa una fraccion de su paquete
(`peso_en_paquete`, suma 1) y cada paquete pesa en su proyecto segun su presupuesto; el producto es el aporte de la
actividad al proyecto (`peso_en_proyecto`, suma 1 por proyecto). Con eso:

    avance del paquete    = sum(peso_en_paquete  * avance)      avance del proyecto = sum(peso_en_proyecto * avance)

Dos avances se comparan siempre: el REAL (lo que dicen las actividades) y el PLANEADO (lo que deberia llevar hecho el
calendario a la fecha de corte). Su cociente es el indice de cumplimiento (como el SPI del valor ganado): 1 va al dia,
menos de 1 va atrasado.

Las fechas son de tres clases: planeadas (la linea base), reales (lo que ya paso) y proyectadas (reales si ya ocurrio,
pronostico si falta). El atraso proyectado es la fecha de fin proyectada menos la planeada.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DIAS_POR_MES = 30.4375
ESTADOS = ("por_iniciar", "en_curso", "completada")
SINONIMOS = {
    "por iniciar": "por_iniciar", "no iniciada": "por_iniciar", "pendiente": "por_iniciar",
    "en curso": "en_curso", "en ejecucion": "en_curso", "en ejecución": "en_curso", "iniciada": "en_curso",
    "completada": "completada", "terminada": "completada", "finalizada": "completada", "cerrada": "completada",
}


def normalizar_estado(s: pd.Series) -> pd.Series:
    """'Completada', ' COMPLETADA ', 'En Curso' -> 'completada', 'en_curso'. Lo que no se reconoce queda vacio."""
    t = s.astype("string").str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
    t = t.map(lambda v: SINONIMOS.get(v, v) if pd.notna(v) else v)
    t = t.str.replace(" ", "_")
    return t.where(t.isin(ESTADOS))


def estado_por_avance(avance: pd.Series) -> pd.Series:
    return pd.Series(np.where(avance >= 1, "completada", np.where(avance > 0, "en_curso", "por_iniciar")), index=avance.index)


def normalizar_avance(s: pd.Series) -> tuple[pd.Series, int]:
    """Avance de 0 a 1. Algunos exports lo traen en porcentaje (0 a 100): lo que pasa de 1 se divide por 100."""
    a = pd.to_numeric(s, errors="coerce")
    en_pct = a > 1
    a = a.where(~en_pct, a / 100)
    return a.clip(lower=0, upper=1), int(en_pct.sum())


def normalizar_pesos(act: pd.DataFrame, columna: str = "peso_en_paquete", por: str = "id_paquete") -> tuple[pd.Series, int]:
    """Hace que los pesos de cada grupo sumen exactamente 1. Devuelve los pesos y cuantos grupos hubo que corregir."""
    w = pd.to_numeric(act[columna], errors="coerce").fillna(0).clip(lower=0)
    suma = w.groupby(act[por]).transform("sum")
    n_grupos = int((w.groupby(act[por]).sum().sub(1).abs() > 0.001).sum())
    return (w / suma.replace(0, np.nan)).fillna(0), n_grupos


def peso_en_proyecto(act: pd.DataFrame, presupuesto: pd.Series, proyecto_de: pd.Series) -> pd.Series:
    """Aporte de cada actividad al proyecto: su peso en el paquete por el peso del paquete (su presupuesto sobre el del proyecto)."""
    pres = presupuesto.reindex(proyecto_de.index).fillna(0)
    total = pres.groupby(proyecto_de).transform("sum")
    peso_paq = (pres / total.replace(0, np.nan)).fillna(0)
    return act["peso_en_paquete"] * act["id_paquete"].map(peso_paq).fillna(0)


def valor_planeado(act: pd.DataFrame, corte: pd.Timestamp) -> pd.Series:
    """Fraccion de cada actividad que el calendario planeado dice que ya deberia estar hecha en la fecha de corte."""
    ini, fin = act["fecha_inicio_plan"], act["fecha_fin_plan"]
    dur = (fin - ini).dt.days.clip(lower=1)
    return (((corte - ini).dt.days) / dur).clip(0, 1).where(corte < fin, 1.0).where(corte > ini, 0.0)


def _indice(avance: pd.Series, plan: pd.Series) -> pd.Series:
    return (avance / plan.replace(0, np.nan)).round(3)


def consolidar_paquetes(act: pd.DataFrame, corte: pd.Timestamp) -> pd.DataFrame:
    """Un renglon por paquete: avances, fechas y atraso proyectado, todo calculado desde sus actividades."""
    a = act.assign(_pv=valor_planeado(act, corte))
    g = a.groupby("id_paquete")
    out = pd.DataFrame({
        "avance": g.apply(lambda d: float((d["peso_en_paquete"] * d["avance"]).sum()), include_groups=False),
        "avance_plan": g.apply(lambda d: float((d["peso_en_paquete"] * d["_pv"]).sum()), include_groups=False),
        "fecha_inicio_plan": g["fecha_inicio_plan"].min(), "fecha_fin_plan": g["fecha_fin_plan"].max(),
        "fecha_inicio_proyectada": g["fecha_inicio_proyectada"].min(), "fecha_fin_proyectada": g["fecha_fin_proyectada"].max(),
        "n_actividades": g.size(), "n_completadas": g["estado"].apply(lambda s: int((s == "completada").sum())),
        "n_en_curso": g["estado"].apply(lambda s: int((s == "en_curso").sum())),
    })
    out["indice_cumplimiento"] = _indice(out["avance"], out["avance_plan"])
    out["duracion_meses"] = ((out["fecha_fin_plan"] - out["fecha_inicio_plan"]).dt.days / DIAS_POR_MES).round(1)
    out["meses_restantes"] = (((out["fecha_fin_proyectada"] - corte).dt.days.clip(lower=0)) / DIAS_POR_MES).round(1)
    out["atraso_proyectado_dias"] = (out["fecha_fin_proyectada"] - out["fecha_fin_plan"]).dt.days
    out[["avance", "avance_plan"]] = out[["avance", "avance_plan"]].round(4)
    return out


def consolidar_proyectos(act: pd.DataFrame, paquetes: pd.DataFrame, corte: pd.Timestamp) -> pd.DataFrame:
    """Un renglon por proyecto. `paquetes`: indice id_paquete con id_proyecto, presupuesto_usd, holgura_dias y las columnas
    de consolidar_paquetes. El avance del proyecto usa el peso de cada actividad en el proyecto."""
    a = act.assign(_pv=valor_planeado(act, corte))
    g = a.groupby("id_proyecto")
    por_proy = paquetes.groupby("id_proyecto")
    out = pd.DataFrame({
        "avance": g.apply(lambda d: float((d["peso_en_proyecto"] * d["avance"]).sum()), include_groups=False),
        "avance_plan": g.apply(lambda d: float((d["peso_en_proyecto"] * d["_pv"]).sum()), include_groups=False),
        "fecha_inicio_plan": g["fecha_inicio_plan"].min(), "fecha_fin_plan": g["fecha_fin_plan"].max(),
        "fecha_inicio_proyectada": g["fecha_inicio_proyectada"].min(), "fecha_fin_proyectada": g["fecha_fin_proyectada"].max(),
        "n_paquetes": por_proy.size(), "n_actividades": g.size(),
        "n_completadas": g["estado"].apply(lambda s: int((s == "completada").sum())),
        "presupuesto_usd": por_proy["presupuesto_usd"].sum(),
        "paquete_que_define_el_fin": por_proy["fecha_fin_proyectada"].idxmax(),
        "paquetes_sobre_su_holgura": por_proy.apply(lambda d: int((d["atraso_proyectado_dias"] > d["holgura_dias"]).sum()), include_groups=False),
    })
    out["indice_cumplimiento"] = _indice(out["avance"], out["avance_plan"])
    out["duracion_meses"] = ((out["fecha_fin_plan"] - out["fecha_inicio_plan"]).dt.days / DIAS_POR_MES).round(1)
    out["meses_restantes"] = (((out["fecha_fin_proyectada"] - corte).dt.days.clip(lower=0)) / DIAS_POR_MES).round(1)
    out["atraso_proyectado_dias"] = (out["fecha_fin_proyectada"] - out["fecha_fin_plan"]).dt.days
    out[["avance", "avance_plan"]] = out[["avance", "avance_plan"]].round(4)
    return out
