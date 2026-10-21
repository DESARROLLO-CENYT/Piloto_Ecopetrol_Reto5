"""Actividad del cronograma a la que pega cada riesgo del registro sintetico, y como queda escrita en el Excel.

Primero se decide la actividad y despues el texto (el texto se adapta a la actividad, no al reves):
  * un riesgo latente pega en algo que falta por hacer: una actividad en curso o por iniciar, con mas probabilidad cuanto
    mas trabajo le falta (peso en el paquete x lo que le falta);
  * uno proximo a materializarse, en algo que se esta ejecutando o que arranca en los proximos 45 dias;
  * uno materializado pego en una actividad que ya se ejecuto o se esta ejecutando, con mas probabilidad cuanto mas tiempo
    se ejecuto en los ultimos seis meses (sus fechas salen despues de esa ventana, ver fechas_riesgo_sintetico.py);
  * en los dos casos pesan mas las actividades que su categoria puede afectar (ver textos_sinteticos.ACTIVIDADES_DE): un
    riesgo contractual pega en compras o ingenieria antes que en la consulta previa.

En el Excel la columna `actividad_afectada` llega como la escribe cada quien: el codigo de la actividad (~55 %), su nombre o
su disciplina con otra ortografia (~25 %), vacia (~12 %), el codigo de una actividad de otro paquete (~4 %) o, en las
abiertas, el de una actividad ya terminada del mismo paquete (~4 %). Plata la reconstruye; la clave guarda la verdadera
para medir cuanto acierta.

Usa su propio generador aleatorio: no altera el resto de los datos sinteticos.
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd

from bronce.cronograma_sintetico import ACTIVIDADES
from bronce.textos_sinteticos import ACTIVIDADES_DE, AMENAZAS, OPORTUNIDADES

CLAVE_DE_NOMBRE = {nombre: clave for clave, nombre, _, _ in ACTIVIDADES}
PESO_SIN_AFINIDAD = 0.03         # una actividad que la categoria no suele afectar tambien puede salir, pero rara vez


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def afines(categoria: str, tipo: str) -> set[str]:
    """Actividades (claves) que puede afectar un riesgo de esa categoria y tipo, segun sus plantillas de texto."""
    plantillas = (AMENAZAS if tipo == "amenaza" else OPORTUNIDADES).get(categoria, [])
    return {k for p in plantillas for k in ACTIVIDADES_DE.get(p, ())}


def actividades_limpias(df_actividades: pd.DataFrame) -> pd.DataFrame:
    """El export de actividades sin repetidas y con el avance en fraccion (se decide sobre la verdad, no sobre lo sucio)."""
    a = df_actividades.drop_duplicates("id_actividad").copy()
    av = pd.to_numeric(a["avance"], errors="coerce").fillna(0)
    a["avance"] = av.where(av <= 1, av / 100)
    a["peso_en_paquete"] = pd.to_numeric(a["peso_en_paquete"], errors="coerce").fillna(0)
    for c in ("fecha_inicio_real", "fecha_fin_real", "fecha_inicio_proyectada", "fecha_fin_proyectada"):
        a[c] = pd.to_datetime(a[c], errors="coerce")
    a["clave"] = a["nombre"].map(CLAVE_DE_NOMBRE)
    return a.sort_values(["id_paquete", "orden"]).reset_index(drop=True)


VENTANA_DIAS = 180          # los materializados ocurrieron, de preferencia, en los ultimos seis meses
PROXIMO_DIAS = 45           # "proximo a materializarse": su actividad se ejecuta ya o arranca en menos de 45 dias


def elegir(acts: pd.DataFrame, compatibles: set[str], estado: str, hoy: pd.Timestamp, r: np.random.Generator) -> str:
    """Actividad (id) de un paquete a la que pega un riesgo. `acts`: actividades limpias del paquete, en orden."""
    if estado != "materializado":
        cand = acts[acts["avance"] < 1]
        if estado == "proximo_a_materializarse":
            pronto = cand[(cand["avance"] > 0) | (cand["fecha_inicio_proyectada"] <= hoy + pd.Timedelta(days=PROXIMO_DIAS))]
            cand = pronto if len(pronto) else cand.head(1)
        if cand.empty:
            cand = acts.tail(1)
        base = (cand["peso_en_paquete"] * (1 - cand["avance"])).to_numpy() + 1e-3
    else:
        cand = acts[acts["fecha_inicio_real"].notna() & (acts["fecha_inicio_real"] <= hoy)]
        if cand.empty:
            cand = acts.head(1)
        ini = cand["fecha_inicio_real"].fillna(hoy).clip(lower=hoy - pd.Timedelta(days=VENTANA_DIAS))
        fin = cand["fecha_fin_real"].fillna(hoy).clip(upper=hoy)
        base = ((fin - ini).dt.days.clip(lower=0) + 3).to_numpy(dtype=float)   # dias que se ejecuto en la ventana
    afinidad = np.array([1.0 if k in compatibles else PESO_SIN_AFINIDAD for k in cand["clave"]])
    w = base * afinidad
    return str(cand["id_actividad"].iloc[int(r.choice(len(cand), p=w / w.sum()))])


def elegir_todas(df: pd.DataFrame, categorias: list[str], tipos: list[str], df_actividades: pd.DataFrame, hoy,
                 r: np.random.Generator) -> list[str]:
    """La actividad verdadera de cada fila del registro (antes de redactar el texto y de ensuciarlo)."""
    acts = actividades_limpias(df_actividades)
    por_paquete = {p: g.reset_index(drop=True) for p, g in acts.groupby("id_paquete")}
    corte = pd.Timestamp(hoy)
    return [elegir(por_paquete[df.at[i, "id_paquete_trabajo"]], afines(categorias[i], tipos[i]),
                   str(df.at[i, "estado"]).strip().lower().replace(" ", "_"), corte, r)
            for i in range(len(df))]


def clave_de(id_actividad: str, df_actividades: pd.DataFrame) -> str | None:
    fila = df_actividades.loc[df_actividades["id_actividad"] == id_actividad, "nombre"]
    return CLAVE_DE_NOMBRE.get(fila.iloc[0]) if len(fila) else None


def como_la_escriben(df: pd.DataFrame, verdad: dict[str, str], df_actividades: pd.DataFrame, r: np.random.Generator) -> list:
    """`actividad_afectada` tal como llega en el Excel (los duplicados la escriben cada uno a su manera)."""
    acts = actividades_limpias(df_actividades).set_index("id_actividad")
    salida = []
    for _, fila in df.iterrows():
        id_act = verdad[str(fila["id_riesgo"]).split("-DUP")[0]]
        a = acts.loc[id_act]
        abierto = str(fila["estado"]).strip().lower().replace(" ", "_") != "materializado"
        s = r.random()
        if s < 0.55:
            salida.append(id_act)
        elif s < 0.80:
            n, d = a["nombre"], a["disciplina"]
            salida.append([n, n.lower(), _sin_tildes(n).lower(), n.upper(), d, f" {d.lower()} "][int(r.integers(6))])
        elif s < 0.92:
            salida.append(None)
        elif s < 0.96 or not abierto:
            otros = acts.index[acts["id_paquete"] != a["id_paquete"]]
            salida.append(str(otros[int(r.integers(len(otros)))]))           # codigo de una actividad de otro paquete
        else:
            hechas = acts[(acts["id_paquete"] == a["id_paquete"]) & (acts["avance"] >= 1)].index
            salida.append(str(hechas[-1]) if len(hechas) else id_act)         # la ultima que ya termino, por costumbre
    return salida
