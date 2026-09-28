"""
Backend del piloto (Paso 5). Sirve la capa Oro como GeoJSON/REST y expone un
endpoint de recalculo del ICT para que el frontend pueda mover los pesos del
modelo multicriterio sin volver a correr todo el pipeline geoespacial.

DATOS SINTETICOS. Correr con: uvicorn main:app --reload --app-dir app
(o usar run_app.py en la raiz del piloto).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from config import ORO, cargar_parametros  # noqa: E402
from modelo import ict as m_ict  # noqa: E402
import plata_a_oro as pipeline  # noqa: E402
from catalogo import construir_catalogo  # noqa: E402

app = FastAPI(title="Piloto Reto 5 - Mapa de riesgos (datos sinteticos)")


@app.middleware("http")
async def sin_cache_heuristica(request, call_next):
    # Sin Cache-Control el navegador reutiliza JS/CSS viejos tras un cambio;
    # "no-cache" obliga a revalidar (ETag -> 304 si no cambio nada).
    respuesta = await call_next(request)
    respuesta.headers.setdefault("Cache-Control", "no-cache")
    return respuesta

_cache: dict = {}


def _cargar_cache():
    params = cargar_parametros()
    datos = pipeline.cargar_plata()
    hoy = pd.Timestamp.now().normalize()
    tabla_ict, criterios_crudos, centroides_m, bounds = pipeline.calcular_ict_para_fecha(datos, params, hoy)

    _cache.update({
        "params": params, "datos": datos, "hoy": hoy,
        "criterios_crudos": criterios_crudos, "bounds": bounds,
        "ids_paquete": list(tabla_ict.index),
    })


@app.on_event("startup")
def startup():
    _cargar_cache()


def _tabla_completa(pesos: dict) -> gpd.GeoDataFrame:
    """Reconstruye la tabla ICT + oportunidad + escalamiento + nivel para un
    juego de pesos dado, reutilizando los criterios crudos ya calculados
    (evita recorrer los cruces espaciales en cada request)."""
    params = _cache["params"]
    datos = _cache["datos"]

    tabla, _ = m_ict.ensamblar_ict(_cache["criterios_crudos"], pesos, _cache["ids_paquete"], bounds=_cache["bounds"])
    tabla["nivel"] = tabla["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
    tabla["indice_confianza"] = [
        m_ict.indice_confianza(datos["riesgos"], m_ict.CRITERIOS, _cache["criterios_crudos"], idp)
        for idp in tabla.index
    ]
    indice_oport = m_ict.indice_oportunidad_por_paquete(
        datos["riesgos"], params["agregacion"]["peso_maximo"], params["agregacion"]["peso_promedio"]
    )
    tabla["indice_oportunidad"] = indice_oport.reindex(tabla.index).fillna(0.0)

    escalamiento = pipeline.calcular_escalamiento(datos, params, tabla, _cache["hoy"])
    tabla = tabla.join(escalamiento)

    gdf = datos["paquetes"].merge(tabla.reset_index(), on="id_paquete", how="left")
    return gdf


@app.get("/api/parametros")
def obtener_parametros():
    return _cache["params"]


@app.get("/api/paquetes")
def obtener_paquetes():
    """Capa Oro pre-calculada (con la tendencia y Gi* del ultimo run del pipeline)."""
    ruta = ORO / "paquetes_ict.geojson"
    if not ruta.exists():
        raise HTTPException(404, "Corre primero src/plata_a_oro.py")
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.post("/api/recalcular")
def recalcular(pesos: dict[str, float]):
    faltantes = set(m_ict.CRITERIOS) - set(pesos)
    if faltantes:
        raise HTTPException(422, f"Faltan pesos para: {sorted(faltantes)}")
    total = sum(pesos.values())
    if total <= 0:
        raise HTTPException(422, "La suma de los pesos debe ser mayor que 0")
    pesos_norm = {k: v / total for k, v in pesos.items()}

    gdf = _tabla_completa(pesos_norm)
    return json.loads(gdf.to_json())


@app.get("/api/grid")
def obtener_grid():
    ruta = ORO / "grid_calor.geojson"
    if not ruta.exists():
        raise HTTPException(404, "Corre primero src/plata_a_oro.py")
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/riesgos")
def obtener_riesgos(categoria: str | None = None, estado: str | None = None, tipo: str | None = None, id_paquete: str | None = None):
    ruta = ORO / "riesgos.geojson"
    gdf = gpd.read_file(ruta)
    if categoria:
        gdf = gdf[gdf["categoria"] == categoria]
    if estado:
        gdf = gdf[gdf["estado"] == estado]
    if tipo:
        gdf = gdf[gdf["tipo"] == tipo]
    if id_paquete:
        gdf = gdf[gdf["id_paquete_trabajo"] == id_paquete]
    # las columnas de fecha llegan como Timestamp al leer el geojson; to_json
    # las serializa con str() via default=str (json.dumps no sabe con Timestamp)
    return json.loads(gdf.to_json(default=str))


@app.get("/api/capas/{nombre}")
def obtener_capa(nombre: str):
    permitidas = {"comunidades", "areas", "hidro", "vias", "proyectos"}
    if nombre not in permitidas:
        raise HTTPException(404, f"Capa desconocida. Disponibles: {sorted(permitidas)}")
    ruta = ORO / f"{nombre}.geojson"
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/alertas")
def obtener_alertas():
    ruta = ORO / "alertas.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/catalogo")
def obtener_catalogo():
    """Inventario vivo de las capas Bronce/Plata/Oro con descripciones curadas."""
    return construir_catalogo()


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
