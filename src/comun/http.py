"""Cliente comun de las fuentes abiertas (sin clave): portal Socrata de datos.gov.co y servicios ArcGIS REST.

Solo la capa Bronce descarga datos; este modulo concentra los reintentos, el User-Agent y los errores de red
para que cada ingesta no los repita.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from comun.config import CAJA_DESCARGA

USER_AGENT = "reto5-piloto/1.0 (piloto de demostracion, CEN&T; datos abiertos)"
ERRORES_RED = (urllib.error.URLError, TimeoutError, ConnectionError, OSError)
SOCRATA = "https://www.datos.gov.co/resource"


def socrata_url(dataset: str) -> str:
    return f"{SOCRATA}/{dataset}.json"


def soql(url_: str, timeout: int = 120, reintentos: int = 3, **params):
    """Consulta SoQL (`$where`, `$select`, `$limit`...) con reintentos; devuelve la lista de filas."""
    consulta = urllib.parse.urlencode({f"${k}": v for k, v in params.items()})
    req = urllib.request.Request(f"{url_}?{consulta}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for intento in range(1, reintentos + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except ERRORES_RED:
            if intento == reintentos:
                raise
            time.sleep(2 * intento)
    return []


def arcgis(url_: str, params: dict, timeout: int = 180, reintentos: int = 3) -> dict:
    """Pedido a un servicio ArcGIS REST. ArcGIS responde 200 con {"error": ...}: aqui se vuelve una excepcion."""
    req = urllib.request.Request(f"{url_}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    for intento in range(1, reintentos + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                datos = json.load(r)
            if "error" in datos:
                raise OSError(datos["error"].get("message", "error del servicio"))
            return datos
        except ERRORES_RED:
            if intento == reintentos:
                raise
            time.sleep(2 * intento)
    return {}


def _consulta_caja(caja: dict, **extra) -> dict:
    envolvente = {"xmin": caja["lon_oeste"], "ymin": caja["lat_sur"], "xmax": caja["lon_este"], "ymax": caja["lat_norte"],
                  "spatialReference": {"wkid": 4326}}
    return {"where": "1=1", "geometry": json.dumps(envolvente), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects", **extra}


def arcgis_capa(servicio: str, capa: int, caja: dict | None = None, pagina: int = 1000) -> list[dict]:
    """Descarga todos los objetos de una capa ArcGIS que cruzan la caja, por paginas, y verifica que llegaron todos."""
    caja = caja or CAJA_DESCARGA
    url_ = f"{servicio}/{capa}/query"
    total = arcgis(url_, _consulta_caja(caja, f="json", returnCountOnly="true"))["count"]
    objetos: list[dict] = []
    while len(objetos) < total:
        nuevos = arcgis(url_, _consulta_caja(
            caja, f="geojson", outSR=4326, outFields="*", orderByFields="objectid",
            resultOffset=len(objetos), resultRecordCount=pagina,
        )).get("features", [])
        if not nuevos:
            break
        objetos += nuevos
    if len(objetos) != total:
        raise OSError(f"Capa {capa}: el servicio anuncio {total} objetos y llegaron {len(objetos)}")
    return objetos
