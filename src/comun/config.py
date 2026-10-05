"""Rutas y constantes compartidas del piloto.

Una sola fuente de verdad para las tres capas medallion:
  BRONCE  data/bronze  datos tal como llegan de la fuente; no se editan, solo se reemplazan al volver a descargar.
  PLATA   data/silver  datos limpios, validados y conformados (tipos, unidades, CRS, sin duplicados).
  ORO     data/gold    productos listos para consumir (API, mapa, modelo): una tabla por uso.

Para probar el pipeline completo sin tocar los datos existentes se puede apuntar a otra carpeta con la
variable de entorno PILOTO_DATA (se crean ahi bronze/, silver/ y gold/).
"""
import os
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent.parent
DATA = Path(os.environ["PILOTO_DATA"]).resolve() if os.environ.get("PILOTO_DATA") else RAIZ / "data"
BRONCE = DATA / "bronze"
PLATA = DATA / "silver"
ORO = DATA / "gold"
EXPORTS = DATA / "exports" if os.environ.get("PILOTO_DATA") else RAIZ / "exports"
PARAMETROS_PATH = RAIZ / "parametros.yaml"

CRS_GEOGRAFICO = "EPSG:4326"   # lat/lon, para almacenar y servir al frontend
CRS_METRICO = "EPSG:3116"      # MAGNA-SIRGAS / Colombia Bogota, para distancias en metros

# Caja aproximada de La Guajira (grados decimales) usada solo como marco
# geografico para ubicar entidades FICTICIAS. No representa proyectos reales.
BBOX_GUAJIRA = {
    "lon_min": -73.1,
    "lon_max": -71.2,
    "lat_min": 10.6,
    "lat_max": 12.4,
}

# Caja de descarga de las fuentes abiertas: La Guajira con margen. Los objetos que la cruzan llegan completos
# (algunos siguen hacia Cesar, Magdalena o Venezuela); Plata los recorta a los municipios del DANE.
CAJA_DESCARGA = {"lat_sur": 10.5, "lon_oeste": -73.7, "lat_norte": 12.7, "lon_este": -71.0}

SEMILLA_ALEATORIA = 42


def cargar_parametros() -> dict:
    with open(PARAMETROS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def asegurar_directorios() -> None:
    for d in (BRONCE, PLATA, ORO, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)
