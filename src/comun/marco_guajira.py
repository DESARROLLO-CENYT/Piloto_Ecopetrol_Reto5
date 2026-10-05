"""Marco geografico de La Guajira para ubicar los datos INVENTADOS sobre tierra firme.

El generador de datos sinteticos (`bronce.sinteticos`) necesita saber donde esta la tierra para no poner proyectos,
comunidades, areas protegidas, rios o vias en el mar, en Venezuela o en otro departamento. Aqui vive el contorno
de La Guajira como un archivo WKT (`contorno_guajira.wkt`): los 15 municipios del DANE unidos y simplificados a ~1 km
(140 vertices; el area difiere 0,02 % del oficial). Se guarda como archivo y no se baja de internet para que los datos
sinteticos sigan siendo reproducibles y se puedan generar sin conexion.

Este contorno es solo un marco de referencia para lo inventado; los limites municipales reales y su version completa
se descargan y limpian en la cadena `municipios` (bronce/plata/oro).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import shapely
from shapely import wkt
from shapely.geometry.base import BaseGeometry

RUTA_CONTORNO = Path(__file__).with_name("contorno_guajira.wkt")
MARGEN_BORDE = 0.012   # grados: el contorno esta simplificado a 0,01; con este margen lo ubicado queda dentro del limite oficial


@lru_cache(maxsize=1)
def tierra() -> BaseGeometry:
    """Poligono de La Guajira (EPSG:4326)."""
    return wkt.loads(RUTA_CONTORNO.read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def tierra_interior(margen_grados: float) -> BaseGeometry:
    """La tierra achicada `margen_grados` hacia adentro: un punto aqui queda a esa distancia de la costa o la frontera.
    1 grado de latitud son ~111 km, asi que 0,02 son ~2 km."""
    interior = tierra().buffer(-margen_grados) if margen_grados else tierra()
    if interior.is_empty:
        raise ValueError(f"Un margen de {margen_grados} grados no deja tierra donde ubicar nada")
    return interior


def esta_en_tierra(geom: BaseGeometry, margen_grados: float = 0.0) -> bool:
    return bool(tierra_interior(margen_grados).contains(geom))


def punto_en_tierra(rng: np.random.Generator, margen_grados: float = 0.02, intentos: int = 10_000) -> tuple[float, float]:
    """Punto aleatorio (lon, lat) dentro de La Guajira, a `margen_grados` de la costa y la frontera."""
    zona = tierra_interior(margen_grados)
    x0, y0, x1, y1 = zona.bounds
    for _ in range(intentos):
        lon, lat = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if shapely.contains_xy(zona, lon, lat):
            return float(lon), float(lat)
    raise RuntimeError("No se encontro un punto en tierra (margen demasiado grande?)")


def centro_factible_mas_cercano(objetivo: tuple[float, float], radio_grados: float, paso: float = 0.02) -> tuple[float, float] | None:
    """El punto mas cercano a `objetivo` donde cabe un circulo de `radio_grados` entero dentro de La Guajira
    (None si no cabe en ningun lado). Determinista: recorre una cuadricula y no usa azar."""
    try:
        zona = tierra_interior(radio_grados + MARGEN_BORDE)   # el circulo entero, mas el margen que absorbe la simplificacion del contorno
    except ValueError:
        return None                                            # el circulo es mas grande que el departamento
    x0, y0, x1, y1 = zona.bounds
    xs, ys = np.meshgrid(np.arange(x0, x1 + paso, paso), np.arange(y0, y1 + paso, paso))
    xs, ys = xs.ravel(), ys.ravel()
    dentro = shapely.contains_xy(zona, xs, ys)
    if not dentro.any():
        return None
    xs, ys = xs[dentro], ys[dentro]
    i = int(np.argmin((xs - objetivo[0]) ** 2 + (ys - objetivo[1]) ** 2))
    return float(xs[i]), float(ys[i])

