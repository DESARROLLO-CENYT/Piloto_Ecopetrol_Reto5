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


# Matriz RAM editada desde la aplicacion (vista "Matriz RAM"). Si existe, reemplaza a la de parametros.yaml (la oficial,
# que no se toca). Borrarla devuelve la oficial.
RAM_PERSONALIZADA_PATH = RAIZ / "ram_personalizada.yaml"
# Supuestos del modelo de riesgo de ejecucion editados desde la aplicacion (vista "Riesgo de ejecucion").
EJECUCION_PERSONALIZADA_PATH = RAIZ / "ejecucion_personalizada.yaml"
# Pesos, umbrales, reglas de escalamiento y topes del ICT editados desde la aplicacion (vista "Ajustar el modelo").
MODELO_PERSONALIZADO_PATH = RAIZ / "modelo_personalizado.yaml"
# Historial de versiones de los parametros: quien cambio que y cuando, con los parametros vigentes de cada version.
HISTORIAL_PARAMETROS_PATH = RAIZ / "historial_parametros.jsonl"
CLAVES_ESCALAMIENTO_RAM = ("ram_vh_escala", "ram_h_en_ruta_critica")
# Lo que la vista del modelo puede cambiar (el resto de parametros.yaml solo se cambia en el archivo)
CLAVES_MODELO = ("pesos", "umbrales_criticidad", "escalamiento", "criterios", "factores_estado")


def _fusionar(base: dict, cambios: dict) -> dict:
    out = dict(base)
    for k, v in cambios.items():
        out[k] = _fusionar(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def cargar_parametros(oficial: bool = False) -> dict:
    """Parametros del modelo. Con `oficial=True` ignora la matriz RAM personalizada (las pruebas usan la oficial)."""
    with open(PARAMETROS_PATH, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)
    params["ram"]["version"] = {"tipo": "oficial"}
    if not oficial and RAM_PERSONALIZADA_PATH.exists():
        with open(RAM_PERSONALIZADA_PATH, "r", encoding="utf-8") as f:
            propia = yaml.safe_load(f) or {}
        params["ram"] = _fusionar(params["ram"], propia.get("ram") or {})
        params["escalamiento"] = _fusionar(params["escalamiento"],
                                           {k: v for k, v in (propia.get("escalamiento") or {}).items() if k in CLAVES_ESCALAMIENTO_RAM})
        params["ram"]["version"] = {"tipo": "personalizada", **(propia.get("version") or {})}
    params["ejecucion"]["version"] = {"tipo": "oficial"}
    if not oficial and EJECUCION_PERSONALIZADA_PATH.exists():
        with open(EJECUCION_PERSONALIZADA_PATH, "r", encoding="utf-8") as f:
            propia = yaml.safe_load(f) or {}
        params["ejecucion"] = _fusionar(params["ejecucion"], propia.get("ejecucion") or {})
        params["ejecucion"]["version"] = {"tipo": "personalizada", **(propia.get("version") or {})}
    params["modelo_version"] = {"tipo": "oficial", "version": params.get("version")}
    if not oficial and MODELO_PERSONALIZADO_PATH.exists():
        with open(MODELO_PERSONALIZADO_PATH, "r", encoding="utf-8") as f:
            propio = yaml.safe_load(f) or {}
        for clave in CLAVES_MODELO:
            cambios = propio.get(clave) or {}
            if clave == "escalamiento":       # las reglas de la RAM las cambia la vista de la matriz, no esta
                cambios = {k: v for k, v in cambios.items() if k not in CLAVES_ESCALAMIENTO_RAM}
            if cambios:
                params[clave] = _fusionar(params[clave], cambios)
        params["modelo_version"] = {"tipo": "personalizado", "base": params.get("version"), **(propio.get("version") or {})}
    return params


def asegurar_directorios() -> None:
    for d in (BRONCE, PLATA, ORO, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)
