"""
Definiciones compartidas del clima real del IDEAM: que variables se traen, de
que conjunto de datos abiertos, con que unidad y en que rango fisico es
creible una lectura. Lo usan la ingesta, el procesamiento (Plata/Oro) y la API
en vivo, para que los tres hablen igual de cada variable.
"""
from __future__ import annotations

import math
import unicodedata

# clave interna -> metadatos. `dataset` es el id en datos.gov.co (Socrata).
# `rango`: fuera de el, la lectura es un error del sensor o un valor centinela.
# `bloque_dias`: tamano de cada pedido de descarga (lecturas mas frecuentes, bloques mas cortos).
VARIABLES: dict[str, dict] = {
    "temperatura": {"dataset": "sbwg-7ju4", "titulo": "Temperatura del aire", "unidad": "°C", "rango": (-5, 50), "bloque_dias": 10},
    "temp_max": {"dataset": "ccvq-rp9s", "titulo": "Temperatura máxima", "unidad": "°C", "rango": (-5, 55), "bloque_dias": 10},
    "temp_min": {"dataset": "afdg-3zpb", "titulo": "Temperatura mínima", "unidad": "°C", "rango": (-5, 50), "bloque_dias": 10},
    "humedad": {"dataset": "uext-mhny", "titulo": "Humedad relativa", "unidad": "%", "rango": (0, 100), "bloque_dias": 10},
    "viento_vel": {"dataset": "sgfv-3yp8", "titulo": "Velocidad del viento", "unidad": "m/s", "rango": (0, 60), "bloque_dias": 6},
    "viento_dir": {"dataset": "kiw7-v9ta", "titulo": "Dirección del viento", "unidad": "°", "rango": (0, 360), "bloque_dias": 6},
    "presion": {"dataset": "62tk-nxj5", "titulo": "Presión atmosférica", "unidad": "hPa", "rango": (500, 1100), "bloque_dias": 10},
    "nivel_rio": {"dataset": "bdmn-sqnh", "titulo": "Nivel del río", "unidad": "m", "rango": (-1, 100), "bloque_dias": 10},
    "nivel_mar": {"dataset": "ia8x-22em", "titulo": "Nivel del mar", "unidad": "m", "rango": (-5, 10), "bloque_dias": 10},
}

# Otros conjuntos (no son series por estacion)
DATASET_RADIACION = "rv9s-8nv6"       # promedios mensuales y anual de radiacion global
DATASET_NORMALES = "nsz2-kzcq"        # normales climatologicas de 30 anos
DATASET_ULTIMAS_HORAS = "57sv-p2fu"   # ultimas ~12 h de todas las variables, IDEAM y terceros

# Variables finales (las que salen de clasificar cada lectura por su SENSOR, no por su
# conjunto de origen: el conjunto "Humedad" trae tambien humedad del suelo, por ejemplo).
# Incluye las que no tienen un conjunto propio en VARIABLES.
VARIABLES_META: dict[str, dict] = {
    "precipitacion": {"titulo": "Lluvia", "unidad": "mm", "rango": (0, 200)},
    **{k: {"titulo": v["titulo"], "unidad": v["unidad"], "rango": v["rango"]} for k, v in VARIABLES.items()},
    "humedad_suelo": {"titulo": "Humedad del suelo", "unidad": "%", "rango": (0, 100)},
    "temp_suelo": {"titulo": "Temperatura del suelo", "unidad": "°C", "rango": (0, 60)},
}

_RUMBOS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")


def mapear_sensor(descripcion: str) -> str | None:
    """Clasifica un sensor por su descripcion: 'TEMPERATURA DEL AIRE MÁXIMA A 2 m' -> 'temp_max',
    'HUMEDAD DEL SUELO A 1 m Ó MAS' -> 'humedad_suelo'. None si no es una variable que usemos
    (por ejemplo, el nivel maximo o minimo horario del rio)."""
    d = sin_tildes(descripcion).lower()
    if "precipitacion" in d:
        return "precipitacion"
    if "temperatura" in d:
        if "suelo" in d:
            return "temp_suelo"
        if "maxima" in d:
            return "temp_max"
        if "minima" in d:
            return "temp_min"
        return "temperatura"
    if "humedad" in d:
        return "humedad_suelo" if "suelo" in d else "humedad"
    if "presion" in d:
        return "presion"
    if "viento" in d:
        if "direccion" in d:
            return "viento_dir"
        if "velocidad" in d:
            return "viento_vel"
        return None
    if "nivel" in d:
        if "maximo" in d or "minimo" in d:
            return None
        return "nivel_mar" if " mar" in d or d.startswith("mar") else "nivel_rio"
    return None


def normalizar_unidad(unidad: str | None) -> str:
    """'hPA' y 'hPa' son lo mismo; 'mt' es metros; 'GN' son grados norte."""
    u = (unidad or "").strip()
    return {"hpa": "hPa", "mt": "m", "gn": "°", "deg": "°", "grados": "°"}.get(u.lower(), u)


def promedio_circular(grados) -> float | None:
    """Media de direcciones en grados (0-360) por vectores; 350 y 10 dan 0, no 180."""
    valores = [float(g) for g in grados if g is not None and not math.isnan(float(g))]
    if not valores:
        return None
    s = sum(math.sin(math.radians(g)) for g in valores) / len(valores)
    c = sum(math.cos(math.radians(g)) for g in valores) / len(valores)
    if abs(s) < 1e-9 and abs(c) < 1e-9:
        return None  # direcciones opuestas que se anulan: no hay media
    return round(math.degrees(math.atan2(s, c)) % 360, 1) % 360  # 359.96 se redondea a 360.0: debe ser 0


def rumbo(grados: float | None) -> str | None:
    """Grados -> punto cardinal de 16 vientos ('N', 'NE', 'SSO'...). Es de donde VIENE el viento."""
    if grados is None or (isinstance(grados, float) and math.isnan(grados)):
        return None
    return _RUMBOS[int((float(grados) % 360) / 22.5 + 0.5) % 16]
