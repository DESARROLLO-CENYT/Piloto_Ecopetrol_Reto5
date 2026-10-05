"""
Lecturas mas recientes del IDEAM "en vivo": consulta el flujo de las ultimas ~12 h
de datos.gov.co, lo limpia con las mismas reglas de Plata y lo sirve por estacion.

Si el portal no responde (sin internet o servicio caido) usa el ultimo respaldo
guardado en Plata, y lo dice. La respuesta se guarda 10 minutos en memoria: el
IDEAM actualiza cada 10 minutos o cada hora segun la variable, no tiene sentido
consultarlo en cada clic del mapa ni tumbarles el servicio.
"""
from __future__ import annotations

import time
from datetime import datetime

import pandas as pd

from bronce.ideam import PAGINA
from comun.config import PLATA
from comun.http import socrata_url as url, soql
from comun.ideam import DATASET_ULTIMAS_HORAS, VARIABLES_META, rumbo
from plata.ideam import limpiar_ultimas_horas

TTL_SEGUNDOS = 600
_cache: dict = {"t": 0.0, "valor": None}


def _a_estaciones(lecturas: pd.DataFrame) -> dict:
    out: dict = {}
    for (cod, var), g in lecturas.sort_values("fecha_hora").groupby(["codigoestacion", "var"]):
        u = g.iloc[-1]
        d = {"valor": round(float(u["valor"]), 2), "hora": u["fecha_hora"].isoformat(timespec="minutes"),
             "unidad": u["unidad"] or VARIABLES_META[var]["unidad"]}
        if var == "viento_dir":
            d["rumbo"] = rumbo(u["valor"])
        out.setdefault(cod, {})[var] = d
    return out


def _desde_api() -> pd.DataFrame:
    filas = soql(url(DATASET_ULTIMAS_HORAS), timeout=30, reintentos=1,
                 where="upper(departamento) like '%GUAJIRA%'", limit=PAGINA)
    if not filas:
        raise OSError("El IDEAM no devolvio lecturas")
    lecturas, _ = limpiar_ultimas_horas(pd.DataFrame(filas))
    return lecturas


def _desde_respaldo() -> pd.DataFrame | None:
    ruta = PLATA / "ideam_ultimas_horas.parquet"
    return pd.read_parquet(ruta) if ruta.exists() else None


def obtener_ahora(forzar: bool = False) -> dict:
    ahora = time.time()
    if not forzar and _cache["valor"] and ahora - _cache["t"] < TTL_SEGUNDOS:
        return _cache["valor"]

    origen, lecturas, aviso = "en_vivo", None, None
    try:
        lecturas = _desde_api()
    except (OSError, ValueError) as e:
        lecturas = _desde_respaldo()
        origen = "respaldo" if lecturas is not None else "sin_datos"
        aviso = f"No se pudo consultar el IDEAM ({type(e).__name__}); " + (
            "se muestra el ultimo respaldo guardado." if lecturas is not None else "no hay respaldo local.")

    valor = {
        "generado_en": datetime.now().isoformat(timespec="seconds"),
        "origen": origen, "aviso": aviso,
        "lectura_mas_reciente": None if lecturas is None or lecturas.empty else lecturas["fecha_hora"].max().isoformat(timespec="minutes"),
        "estaciones": {} if lecturas is None or lecturas.empty else _a_estaciones(lecturas),
    }
    if origen == "en_vivo":
        _cache.update(t=ahora, valor=valor)
    return valor
