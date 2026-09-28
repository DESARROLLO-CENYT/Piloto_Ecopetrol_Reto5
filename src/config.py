"""Rutas y constantes compartidas del piloto. DATOS SINTETICOS."""
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
BRONCE = DATA / "bronze"
PLATA = DATA / "silver"
ORO = DATA / "gold"
EXPORTS = RAIZ / "exports"
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

SEMILLA_ALEATORIA = 42


def cargar_parametros() -> dict:
    with open(PARAMETROS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def asegurar_directorios() -> None:
    for d in (BRONCE, PLATA, ORO, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)
