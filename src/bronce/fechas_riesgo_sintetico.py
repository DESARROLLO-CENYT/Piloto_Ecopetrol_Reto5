"""Fechas de cada riesgo del registro sintetico, coherentes con su estado, su nivel RAM y la actividad a la que pega.

Antes las fechas se sorteaban sueltas: un riesgo podia materializarse en el futuro, y la fecha de la accion no dependia de
nada. Ahora, una vez decidida la actividad (bronce/riesgo_actividad_sintetico.py):

  * Materializado: ocurrio mientras se ejecutaba su actividad (entre su inicio y su fin reales, o el corte si sigue en
    curso), de preferencia en los ultimos seis meses, y nunca despues de la fecha de corte. Se habia identificado entre 3 y
    60 dias antes. La accion es la respuesta: entre 1 y 20 dias despues de que ocurrio.
  * Abierto (latente o proximo a materializarse): se identifico en los ultimos seis meses (no antes de que arrancara su
    paquete, menos un mes de planeacion). La accion se programo con un plazo que depende del nivel RAM residual: cuanto
    mas grave, mas corto (VH 5 a 15 dias, H 10 a 30, M 20 a 60, L 45 a 90, N 60 a 120; la mitad si esta proxima a
    materializarse). Si ese plazo ya paso, la accion se reprogramo hacia adelante o quedo vencida: vencida con mas
    probabilidad si el riesgo esta proximo a materializarse (45 %) que si esta latente (25 %).

Despues se ensucian como en un Excel real (ver `ensuciar`): fechas escritas dia/mes/ano, una materializacion anotada antes
de la identificacion (fechas cruzadas), un ano de mas (materializacion en el futuro) y materializados sin fecha.

Usa su propio generador aleatorio: no altera el resto de los datos sinteticos.
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

VENTANA_DIAS = 180
PLANEACION_DIAS = 30
PLAZO_ACCION_DIAS = {"VH": (5, 15), "H": (10, 30), "M": (20, 60), "L": (45, 90), "N": (60, 120)}
PROB_ACCION_VENCIDA = {"latente": 0.25, "proximo_a_materializarse": 0.45}
LETRAS = "ABCDE"
DIMS = {"PE": "cons_personas", "EC": "cons_economica", "MA": "cons_ambiental", "CL": "cons_clientes", "IM": "cons_imagen"}
ORDEN_NIVEL = ["N", "L", "M", "H", "VH"]


def nivel_residual(fila: pd.Series, matriz: dict) -> str:
    """Nivel RAM residual, como lo calificaria quien llena el registro (manda la peor dimension)."""
    letra = str(fila["probabilidad_residual"]).strip().upper()[:1]
    if letra.isdigit() and 1 <= int(letra) <= 5:          # en el Excel la probabilidad a veces llega como numero (1 = A)
        letra = LETRAS[int(letra) - 1]
    if letra not in LETRAS:
        letra = "C"
    niveles = [matriz[int(fila[c])][LETRAS.index(letra)] for c in DIMS.values() if pd.notna(fila.get(c))]
    return max(niveles, key=ORDEN_NIVEL.index) if niveles else "M"


def _entre(r: np.random.Generator, ini: pd.Timestamp, fin: pd.Timestamp) -> pd.Timestamp:
    dias = max(0, (fin - ini).days)
    return ini + timedelta(days=int(r.integers(0, dias + 1)))


def fechas(estado: str, nivel: str, act: pd.Series, inicio_paquete: pd.Timestamp, corte: pd.Timestamp,
           r: np.random.Generator) -> dict:
    """Identificacion, materializacion y accion de un riesgo. `act`: su actividad (fechas reales y proyectadas)."""
    desde = max(corte - timedelta(days=VENTANA_DIAS), inicio_paquete - timedelta(days=PLANEACION_DIAS))
    if estado == "materializado":
        ini = act["fecha_inicio_real"] if pd.notna(act["fecha_inicio_real"]) else corte
        fin = min(act["fecha_fin_real"], corte) if pd.notna(act["fecha_fin_real"]) else corte
        a = max(ini, corte - timedelta(days=VENTANA_DIAS))
        fm = _entre(r, a, fin) if a <= fin else _entre(r, ini, fin)        # si la actividad termino hace mucho, cuando fue
        ident = max(fm - timedelta(days=int(r.integers(3, 61))), inicio_paquete - timedelta(days=PLANEACION_DIAS))
        accion = fm + timedelta(days=int(r.integers(1, 21)))
        return {"fecha_identificacion": ident, "fecha_materializacion": fm, "fecha_ejecucion_accion": accion}

    ident = _entre(r, desde, corte - timedelta(days=1))
    lo, hi = PLAZO_ACCION_DIAS.get(nivel, (20, 60))
    if estado == "proximo_a_materializarse":
        lo, hi = max(2, lo // 2), max(4, hi // 2)
    accion = ident + timedelta(days=int(r.integers(lo, hi + 1)))
    if accion < corte and r.random() >= PROB_ACCION_VENCIDA.get(estado, 0.25):
        accion = corte + timedelta(days=int(r.integers(3, hi + 1)))       # se reprogramo
    return {"fecha_identificacion": ident, "fecha_materializacion": None, "fecha_ejecucion_accion": accion}


def asignar(df: pd.DataFrame, verdad: list[str], actividades_limpias: pd.DataFrame, matriz: dict, corte,
            r: np.random.Generator) -> pd.DataFrame:
    """Reemplaza las tres fechas de cada fila del registro (antes de ensuciarlo) por unas coherentes."""
    corte = pd.Timestamp(corte)
    acts = actividades_limpias.set_index("id_actividad")
    inicio_paquete = actividades_limpias.groupby("id_paquete")["fecha_inicio_real"].min()
    df = df.copy()
    for i, id_act in enumerate(verdad):
        fila = df.iloc[i]
        estado = str(fila["estado"]).strip().lower().replace(" ", "_")
        a = acts.loc[id_act]
        f = fechas(estado, nivel_residual(fila, matriz), a, inicio_paquete.get(a["id_paquete"], corte), corte, r)
        for col, v in f.items():
            df.iat[i, df.columns.get_loc(col)] = None if v is None else pd.Timestamp(v).date().isoformat()
    return df


def _dma(iso: str) -> str:
    d = pd.Timestamp(iso)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def ensuciar(df: pd.DataFrame, r: np.random.Generator) -> pd.DataFrame:
    """Errores de fecha como los de un Excel real (Plata los detecta y corrige o los marca para revisar):
      ~6 % de las fechas escritas dia/mes/ano; en los materializados, ~5 % con la fecha de materializacion antes que la de
      identificacion (cruzadas), ~4 % con un ano de mas (quedan en el futuro) y ~4 % sin fecha de materializacion."""
    df = df.copy()
    for col in ("fecha_identificacion", "fecha_materializacion", "fecha_ejecucion_accion"):
        for i in np.flatnonzero(df[col].notna().to_numpy() & (r.random(len(df)) < 0.06)):
            df.iat[i, df.columns.get_loc(col)] = _dma(df.iat[i, df.columns.get_loc(col)])
    mat = np.flatnonzero((df["estado"].astype(str).str.strip().str.lower() == "materializado").to_numpy() & df["fecha_materializacion"].notna().to_numpy())
    for i in mat:
        s = r.random()
        ci, cm = df.columns.get_loc("fecha_identificacion"), df.columns.get_loc("fecha_materializacion")
        if s < 0.05:
            df.iat[i, ci], df.iat[i, cm] = df.iat[i, cm], df.iat[i, ci]                     # cruzadas
        elif s < 0.09:
            texto = str(df.iat[i, cm])
            fm = pd.to_datetime(texto, format="%d/%m/%Y") if "/" in texto else pd.Timestamp(texto)
            df.iat[i, cm] = (fm + pd.DateOffset(years=1)).date().isoformat()                # un ano de mas
        elif s < 0.13:
            df.iat[i, cm] = None                                                            # sin fecha
    return df
