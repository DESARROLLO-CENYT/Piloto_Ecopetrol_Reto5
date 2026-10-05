"""Escritura y lectura de los artefactos de cada capa, con las garantias que el resto del pipeline asume."""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import shapely


def sin_nan(obj):
    """NaN -> None, recursivamente: `NaN` no es JSON valido y rompe la API y el mapa."""
    if isinstance(obj, float) and obj != obj:
        return None
    if isinstance(obj, dict):
        return {k: sin_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sin_nan(v) for v in obj]
    return obj


def escribir_json(ruta: Path, objeto) -> None:
    """JSON estricto (UTF-8, sin NaN): si algo no es serializable falla aqui, no en el navegador."""
    ruta.write_text(json.dumps(sin_nan(objeto), ensure_ascii=False, allow_nan=False), encoding="utf-8")


def leer_json(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_coleccion(ruta: Path, gdf: gpd.GeoDataFrame, metadata: dict | None = None) -> None:
    """GeoDataFrame -> FeatureCollection con un bloque `metadata` (fuente, licencia, fecha...) para la trazabilidad."""
    coleccion = json.loads(gdf.to_json(drop_id=True))
    if metadata is not None:
        coleccion["metadata"] = metadata
    escribir_json(ruta, coleccion)


def vertices(gdf) -> int:
    return int(shapely.get_num_coordinates(gdf.geometry.values).sum())


# ---------------------------------------------------------------------------
# Proveniencia: lo que Oro necesita saber del origen sin volver a Bronce
# ---------------------------------------------------------------------------

def escribir_proveniencia(fuente: str, meta_bronce: dict, calidad: dict) -> None:
    """Plata guarda, junto a sus tablas, de donde vienen (meta de la descarga) y que control de calidad paso.
    Oro lee esto para su bloque `metadata`: asi Oro depende solo de Plata, nunca de Bronce."""
    from datetime import datetime

    from comun.config import PLATA
    escribir_json(PLATA / f"proveniencia_{fuente}.json", {
        "fuente_id": fuente, "bronce": meta_bronce, "calidad": calidad,
        "plata_generada_en": datetime.now().isoformat(timespec="seconds"),
    })


def leer_proveniencia(fuente: str) -> dict:
    from comun.config import PLATA
    return leer_json(PLATA / f"proveniencia_{fuente}.json")
