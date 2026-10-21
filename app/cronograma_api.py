"""Cronograma por actividades para la vista de ejecucion: lo que publico el paso oro.cronograma."""
from __future__ import annotations

import json

import pandas as pd

from comun.config import ORO
from comun.serializacion import sin_nan

ARCHIVOS = ("cronograma_proyectos.csv", "cronograma_paquetes.csv", "cronograma_actividades.csv")


def resultados() -> dict:
    """Proyectos, paquetes y actividades con su avance (real y planeado), su peso y sus fechas (planeadas y proyectadas)."""
    if not all((ORO / a).exists() for a in ARCHIVOS):
        return {"disponible": False}
    leer = lambda n: json.loads(pd.read_csv(ORO / n).to_json(orient="records"))  # noqa: E731
    proyectos, paquetes, actividades = (leer(a) for a in ARCHIVOS)
    return sin_nan({
        "disponible": True,
        "fecha_corte": proyectos[0]["fecha_corte"] if proyectos else None,
        "proyectos": proyectos, "paquetes": paquetes, "actividades": actividades,
    })
