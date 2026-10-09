"""Matriz de Valoracion de Riesgos (RAM) de Ecopetrol.

Fuente: instructivo ECP-DRI-I-007 "Uso de la Matriz de Valoracion de Riesgos - RAM" (version 01, 2008). Las escalas y la
matriz viven en parametros.yaml (`ram`), para poder cambiarlas por la version vigente sin tocar codigo.

Como funciona:
  * Consecuencia de 0 a 5 en cinco dimensiones: Personas (PE), Economica (EC), Ambiental (MA), Clientes (CL), Imagen (IM).
  * Probabilidad de A (no ha ocurrido en la industria) a E (sucede varias veces al ano en la unidad). Es la probabilidad
    de que ocurra ESA consecuencia, no de que exista el peligro.
  * El cruce consecuencia x probabilidad da el nivel: N, L, M, H, VH. No es un producto: la tabla es asimetrica
    (5A = M, pero 3E = H).
  * Se califica cada dimension y manda la peor: PE 5C, EC 2C, MA 1D -> el riesgo es 5C (H).
"""
from __future__ import annotations

import re

import pandas as pd

LETRAS = "ABCDE"
ORDEN_NIVEL = ["N", "L", "M", "H", "VH"]


class Ram:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.dimensiones: dict[str, str] = cfg["dimensiones"]
        self.matriz = {int(k): list(v) for k, v in cfg["matriz"].items()}
        self.niveles: dict[str, dict] = cfg["niveles"]

    # ---- una celda ------------------------------------------------------------------------------------------
    def nivel(self, consecuencia: int, probabilidad: str) -> str:
        """Nivel de la celda (consecuencia 0-5, probabilidad A-E)."""
        return self.matriz[int(consecuencia)][LETRAS.index(probabilidad)]

    def puntaje(self, nivel: str) -> int:
        return int(self.niveles[nivel]["puntaje"])

    # ---- un riesgo ------------------------------------------------------------------------------------------
    def clasificar(self, consecuencias: dict[str, int], probabilidad: str) -> dict:
        """Clasifica un riesgo: cada dimension con la misma probabilidad y manda la peor celda.
        Empate de nivel: gana la mayor consecuencia (y luego el orden PE, EC, MA, CL, IM)."""
        mejor = None
        for dim in self.dimensiones:
            c = consecuencias.get(dim)
            if c is None or pd.isna(c):
                continue
            c = int(c)
            n = self.nivel(c, probabilidad)
            clave = (ORDEN_NIVEL.index(n), c)
            if mejor is None or clave > mejor[0]:
                mejor = (clave, dim, c, n)
        if mejor is None:
            return {"codigo": None, "nivel": None, "dimension": None, "consecuencia": None}
        _, dim, c, n = mejor
        return {"codigo": f"{c}{probabilidad}", "nivel": n, "dimension": dim, "consecuencia": c}


def normalizar_probabilidad(valor) -> str | None:
    """'c', ' C ', 'C - Ha ocurrido en la empresa', '3' -> 'C'. Lo que no se entiende -> None."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    s = str(valor).strip().upper()
    if not s:
        return None
    if s[0] in LETRAS and (len(s) == 1 or not s[1].isalpha()):
        return s[0]
    m = re.fullmatch(r"([1-5])(\.0)?", s)
    if m:
        return LETRAS[int(m.group(1)) - 1]
    return None


def normalizar_consecuencia(valor) -> int | None:
    """'4', 4.0, ' 4 ' -> 4; fuera de 0-5 o ilegible -> None."""
    try:
        c = int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None
    return c if 0 <= c <= 5 else None


def probabilidad_por_frecuencia(eventos_por_ano: float, hubo_alguno: bool, umbrales: dict) -> str:
    """Letra sugerida por la frecuencia de eventos en el territorio (sugerencia para el equipo evaluador)."""
    for letra in ("E", "D", "C"):
        if eventos_por_ano >= umbrales[letra]:
            return letra
    return "B" if hubo_alguno else "A"
