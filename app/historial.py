"""Historial de versiones de los parametros editados desde la aplicacion (matriz RAM, supuestos de ejecucion, modelo ICT).

Cada vez que alguien guarda o restaura, queda una linea en historial_parametros.jsonl con quien, cuando, por que y los
parametros que quedaron vigentes: cualquier resultado se puede reproducir con los parametros de su fecha (seccion 6.4 de
la propuesta). El archivo solo crece; no se edita desde la aplicacion.
"""
from __future__ import annotations

import json
from datetime import datetime

from comun.config import HISTORIAL_PARAMETROS_PATH


def registrar(componente: str, accion: str, autor: str | None, nota: str | None, vigentes: dict) -> dict:
    entrada = {"fecha": datetime.now().isoformat(timespec="seconds"), "componente": componente, "accion": accion,
               "autor": " ".join(str(autor or "").split())[:80] or None, "nota": " ".join(str(nota or "").split())[:300] or None,
               "parametros": vigentes}
    with open(HISTORIAL_PARAMETROS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False, default=str) + "\n")
    return entrada


def leer(componente: str | None = None, n: int = 20, con_parametros: bool = False) -> list[dict]:
    if not HISTORIAL_PARAMETROS_PATH.exists():
        return []
    filas = [json.loads(l) for l in HISTORIAL_PARAMETROS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    if componente:
        filas = [f for f in filas if f["componente"] == componente]
    filas = filas[-n:][::-1]
    return filas if con_parametros else [{k: v for k, v in f.items() if k != "parametros"} for f in filas]
