"""Datos vivos para la vista Flujo (flujo.html): el pipeline tal como lo declara src/pipeline.py, el estado de cada
paso en disco, los metadatos de cada fuente descargada, la ultima auditoria y el inventario de pruebas.

Nada de esto se escribe a mano en la pagina: si cambia el pipeline o se vuelve a correr, la vista sigue siendo cierta.
"""
from __future__ import annotations

import ast
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

import pipeline as definicion  # src/pipeline.py (src esta en sys.path desde main.py)
from comun.config import DATA

RAIZ = Path(__file__).resolve().parent.parent
TESTS = RAIZ / "tests"
REQUISITOS = RAIZ / "requirements.txt"


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds") if ts else None


def pasos() -> list[dict]:
    """Cada paso en orden de ejecucion, con los pasos de los que depende y la fecha de su ultima salida."""
    escritor = {a: p.id for p in definicion.PASOS for a in p.escribe}
    out = []
    for p in definicion.orden_topologico():
        # un solo stat por archivo: en carpetas sincronizadas (OneDrive) cada consulta al disco cuesta
        estados = [f.stat() for a in p.escribe for f in definicion.archivos_de(a)]
        out.append({
            "id": p.id,
            "capa": p.capa,
            "fuente": p.fuente,
            "descripcion": p.descripcion,
            "depende_de": sorted({escritor[a] for a in p.lee if a in escritor}),
            "lee": list(p.lee),
            "escribe": list(p.escribe),
            "archivos": len(estados),
            "megabytes": round(sum(s.st_size for s in estados) / 1e6, 2),
            "actualizado": _iso(max((s.st_mtime for s in estados), default=None)),
            "requiere_red": p.requiere_red,
            "obligatorio": p.obligatorio,
            "comando": f"python -m {p.modulo}",
        })
    return out


def fuentes() -> dict[str, dict]:
    """Lo que cada descarga de Bronce dejo escrito en su <fuente>_meta.json."""
    out = {}
    for ruta in sorted((DATA / "bronze").glob("*_meta.json")):
        try:
            meta = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out[ruta.name.removesuffix("_meta.json")] = {
            "fuente": meta.get("fuente"),
            "licencia": meta.get("licencia"),
            "servicio": meta.get("servicio") or meta.get("url"),
            "descargado_en": meta.get("descargado_en") or _iso(ruta.stat().st_mtime),
        }
    return out


def auditoria() -> dict | None:
    """Resumen de la ultima auditoria (python ejecutar_pipeline.py --auditar)."""
    ruta = DATA / "auditoria_pipeline.csv"
    if not ruta.exists():
        return None
    df = pd.read_csv(ruta)
    por_grupo = df.groupby("grupo")["estado"].value_counts().unstack(fill_value=0)
    return {
        "fecha": _iso(ruta.stat().st_mtime),
        "total": int(len(df)),
        "por_estado": {k: int(v) for k, v in df["estado"].value_counts().items()},
        "por_grupo": {g: {k: int(v) for k, v in fila.items()} for g, fila in por_grupo.iterrows()},
    }


def pruebas() -> dict:
    """Cuenta los casos de prueba sin ejecutarlos: cada test_* vale 1, o el numero de casos de su parametrize."""
    archivos, casos = 0, 0
    for ruta in sorted(TESTS.glob("test_*.py")):
        archivos += 1
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                n = 1
                for d in nodo.decorator_list:
                    if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "parametrize" and len(d.args) > 1 \
                            and isinstance(d.args[1], (ast.List, ast.Tuple)):
                        n *= len(d.args[1].elts)
                casos += n
    return {"archivos": archivos, "casos": casos}


def versiones() -> dict[str, str]:
    """Versiones fijadas en requirements.txt (lo que se instala de verdad)."""
    out = {}
    if REQUISITOS.exists():
        for linea in REQUISITOS.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;#]+)", linea.strip())
            if m:
                out[m.group(1).lower()] = m.group(2)
    return out


_CACHE: dict = {"cuando": 0.0, "datos": None}
VIGENCIA_S = 30  # el pipeline no cambia de un segundo a otro; evita recorrer el disco en cada visita


def construir_flujo(forzar: bool = False) -> dict:
    ahora = time.monotonic()
    if forzar or _CACHE["datos"] is None or ahora - _CACHE["cuando"] > VIGENCIA_S:
        _CACHE.update(datos=_construir(), cuando=ahora)
    return _CACHE["datos"]


def _construir() -> dict:
    lista = pasos()
    capas = {c: sum(1 for p in lista if p["capa"] == c) for c in definicion.CAPAS}
    return {
        "pasos": lista,
        "capas": capas,
        "artefactos": len(definicion.ARTEFACTOS),
        "fuentes": fuentes(),
        "auditoria": auditoria(),
        "pruebas": pruebas(),
        "versiones": versiones(),
    }
