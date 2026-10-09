"""
Backend del piloto (Paso 5). Sirve la capa Oro como GeoJSON/REST y expone un
endpoint de recalculo del ICT para que el frontend pueda mover los pesos del
modelo multicriterio sin volver a correr todo el pipeline geoespacial.

DATOS SINTETICOS. Correr con: uvicorn main:app --reload --app-dir app
(o usar run_app.py en la raiz del piloto).
"""
from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
import json
import os
import sys
import threading
from pathlib import Path

import geopandas as gpd
import pandas as pd
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from comun.config import ORO, cargar_parametros  # noqa: E402
from modelo import ict as m_ict  # noqa: E402
from oro import ict as pipeline  # noqa: E402
from catalogo import construir_catalogo  # noqa: E402
from clima_vivo import obtener_ahora  # noqa: E402
import ram_config  # noqa: E402
import ejecucion_api  # noqa: E402
import tarea_diaria  # noqa: E402
import tarea_programada  # noqa: E402
import historial  # noqa: E402
import modelo_api  # noqa: E402
from flujo_api import construir_flujo  # noqa: E402

@asynccontextmanager
async def ciclo_de_vida(_app):
    """Al arrancar: carga el ICT en memoria y programa la tarea diaria de alertas."""
    _cargar_cache()
    _calentar_catalogo()
    tarea_programada.iniciar(al_terminar=_recargar)
    yield


app = FastAPI(title="Piloto Reto 5 - Mapa de riesgos (datos sinteticos)", lifespan=ciclo_de_vida)


# Lo que cambia datos o dispara descargas. Desde el mismo equipo (127.0.0.1) pasa siempre; desde otro equipo de la red
# (iniciar.py --red) solo con la clave de la variable de entorno RETO5_CLAVE_EDICION, y si no esta definida, nunca.
# La simulacion de escenarios y la vista previa de pesos no guardan nada: no se protegen.
RUTAS_DE_EDICION = ("/api/ram", "/api/ejecucion/supuestos", "/api/alertas/actualizar", "/api/modelo")
SOLO_LECTURA = {"/api/modelo/vista_previa", "/api/modelo/ahp"}
EQUIPO_LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}


@app.middleware("http")
async def proteger_edicion(request, call_next):
    ruta = request.url.path
    if request.method in ("POST", "PUT", "DELETE", "PATCH") and ruta.startswith(RUTAS_DE_EDICION) and ruta not in SOLO_LECTURA:
        cliente = request.client.host if request.client else ""
        if cliente not in EQUIPO_LOCAL:
            clave = os.environ.get("RETO5_CLAVE_EDICION", "")
            if not clave:
                return JSONResponse({"detail": "Solo se puede editar desde el equipo donde corre la aplicación "
                                               "(o definiendo RETO5_CLAVE_EDICION en el servidor)."}, status_code=403)
            if not hmac.compare_digest(request.headers.get("x-clave-edicion", ""), clave):
                return JSONResponse({"detail": "Falta la clave de edición o no es correcta."}, status_code=401)
    return await call_next(request)


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


def _tabla_completa(pesos: dict) -> gpd.GeoDataFrame:
    """Reconstruye la tabla ICT + oportunidad + escalamiento + nivel para un
    juego de pesos dado, reutilizando los criterios ya calculados
    (evita recorrer los cruces espaciales en cada request)."""
    params = _cache["params"]
    datos = _cache["datos"]
    crudos = _cache["criterios_crudos"]
    ids = _cache["ids_paquete"]

    tabla, _ = m_ict.ensamblar_ict(crudos, pesos, ids, bounds=_cache["bounds"])
    tabla["nivel"] = tabla["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
    tabla["indice_confianza"] = m_ict.indice_confianza(crudos["disponibilidad"], pesos)
    tabla["indice_oportunidad"] = m_ict.indice_oportunidad(
        datos["riesgos"], params["agregacion"]["peso_maximo"], params["agregacion"]["peso_promedio"], ids
    )
    tabla = tabla.join(crudos["detalle"]).join(pipeline.resumen_ram(datos["riesgos"], ids))
    tabla = tabla.join(pipeline.calcular_escalamiento(datos, params, tabla, _cache["hoy"]))

    gdf = datos["paquetes"].merge(tabla.reset_index(), on="id_paquete", how="left")
    return gdf


@app.get("/api/parametros")
def obtener_parametros():
    return _cache["params"]


# ---- Matriz RAM editable (vista matriz.html) -------------------------------------------------------------------

@app.get("/api/ram")
def ram_obtener():
    """Matriz oficial (parametros.yaml) y la vigente (la personalizada si existe)."""
    return ram_config.resumen()


@app.put("/api/ram")
def ram_guardar(cuerpo: dict = Body(...)):
    """Guarda la matriz editada en ram_personalizada.yaml. No recalcula: para eso, POST /api/ram/recalcular."""
    try:
        contenido, advertencias = ram_config.validar(cuerpo)
    except ram_config.ErrorRam as e:
        raise HTTPException(422, str(e)) from e
    ram_config.guardar(contenido)
    _cache["params"] = cargar_parametros()
    historial.registrar("ram", "guardar", cuerpo.get("editado_por"), cuerpo.get("nota"), ram_config.resumen()["vigente"])
    return {**ram_config.resumen(), "advertencias": advertencias}


@app.delete("/api/ram")
def ram_restaurar():
    """Vuelve a la matriz oficial (borra la personalizada)."""
    borrada = ram_config.borrar()
    _cache["params"] = cargar_parametros()
    if borrada:
        historial.registrar("ram", "restaurar la oficial", None, None, ram_config.resumen()["vigente"])
    return {**ram_config.resumen(), "borrada": borrada}


@app.post("/api/ram/recalcular")
def ram_recalcular():
    """Recalcula el registro de riesgos, el ICT y lo que depende de ellos con la matriz vigente (en segundo plano)."""
    try:
        return ram_config.recalcular(al_terminar=_recargar)
    except ram_config.ErrorRam as e:
        raise HTTPException(409, str(e)) from e


def _calentar_catalogo():
    """El catalogo lee todos los archivos (decenas de segundos la primera vez): se arma en segundo plano para que la
    pagina Datos y modelo no espere. Antes se rehace el flujo (vista Flujo), que es rapido y cambia con cada corrida."""
    def calentar():
        construir_flujo(forzar=True)
        construir_catalogo()
    threading.Thread(target=calentar, daemon=True, name="catalogo").start()


def _recargar():
    _cargar_cache()
    _calentar_catalogo()
    ejecucion_api.olvidar_entradas()


# ---- Riesgo de ejecucion (vista ejecucion.html) ----------------------------------------------------------------

@app.get("/api/ejecucion")
def ejecucion_resultados():
    """Resultados del paso oro.ejecucion, con los supuestos vigentes y los base."""
    return ejecucion_api.resultados()


@app.post("/api/ejecucion/simular")
def ejecucion_simular(cuerpo: dict = Body(default={})):
    """Escenario en memoria (no guarda nada): supuestos editados, factores por categoria, con o sin controles."""
    try:
        return ejecucion_api.simular(cuerpo)
    except ejecucion_api.ErrorSupuestos as e:
        raise HTTPException(422, str(e)) from e


@app.put("/api/ejecucion/supuestos")
def ejecucion_guardar(cuerpo: dict = Body(...)):
    """Guarda los supuestos editados en ejecucion_personalizada.yaml y recalcula el paso oro.ejecucion."""
    try:
        bloque, adv = ejecucion_api.validar(cuerpo.get("supuestos") or {})
    except ejecucion_api.ErrorSupuestos as e:
        raise HTTPException(422, str(e)) from e
    ejecucion_api.guardar(bloque, cuerpo.get("editado_por"), cuerpo.get("nota"))
    _cache["params"] = cargar_parametros()
    historial.registrar("ejecucion", "guardar", cuerpo.get("editado_por"), cuerpo.get("nota"), _cache["params"]["ejecucion"])
    try:
        trabajo = ram_config.recalcular(al_terminar=_recargar, fuentes=("ejecucion",))
    except ram_config.ErrorRam as e:
        raise HTTPException(409, str(e)) from e
    return {"advertencias": adv, "recalculo": trabajo}


@app.delete("/api/ejecucion/supuestos")
def ejecucion_restaurar():
    """Vuelve a los supuestos de parametros.yaml y recalcula el paso oro.ejecucion."""
    borrado = ejecucion_api.borrar()
    _cache["params"] = cargar_parametros()
    if borrado:
        historial.registrar("ejecucion", "volver a la base", None, None, _cache["params"]["ejecucion"])
    try:
        trabajo = ram_config.recalcular(al_terminar=_recargar, fuentes=("ejecucion",))
    except ram_config.ErrorRam as e:
        raise HTTPException(409, str(e)) from e
    return {"borrado": borrado, "recalculo": trabajo}


@app.get("/api/ram/recalcular")
def ram_estado_recalculo():
    return ram_config.estado_recalculo()


# ---- Modelo ICT editable (vista modelo.html) -------------------------------------------------------------------

def _ict_actual() -> pd.DataFrame:
    ruta = ORO / "paquetes_ict.geojson"
    return gpd.read_file(ruta).set_index("id_paquete") if ruta.exists() else pd.DataFrame()


@app.get("/api/modelo")
def modelo_resumen():
    """Pesos, umbrales, reglas y topes vigentes y base, si hay version personalizada y el historial de versiones."""
    return modelo_api.resumen()


@app.post("/api/modelo/vista_previa")
def modelo_vista_previa(cuerpo: dict = Body(default={})):
    """ICT, nivel y escalamiento de cada paquete con los parametros propuestos (no guarda nada)."""
    try:
        bloque, adv = modelo_api.validar(cuerpo.get("cambios") or {})
    except modelo_api.ErrorModelo as e:
        raise HTTPException(422, str(e)) from e
    return {**modelo_api.vista_previa(_cache["datos"], _ict_actual(), bloque, _cache["hoy"]), "advertencias": adv}


@app.post("/api/modelo/ahp")
def modelo_ahp(cuerpo: dict = Body(...)):
    """Pesos y razon de consistencia a partir de una matriz de comparaciones por pares (AHP, escala de Saaty)."""
    try:
        return modelo_api.ahp(cuerpo.get("matriz"))
    except modelo_api.ErrorModelo as e:
        raise HTTPException(422, str(e)) from e


@app.put("/api/modelo")
def modelo_guardar(cuerpo: dict = Body(...)):
    """Guarda los parametros en modelo_personalizado.yaml, deja la version en el historial y recalcula el ICT."""
    try:
        bloque, adv = modelo_api.validar(cuerpo.get("cambios") or {})
    except modelo_api.ErrorModelo as e:
        raise HTTPException(422, str(e)) from e
    if not bloque:
        raise HTTPException(422, "No hay cambios que guardar")
    if ram_config.ocupado():
        raise HTTPException(409, "Ya hay un recálculo en curso")
    modelo_api.guardar(bloque, cuerpo.get("editado_por"), cuerpo.get("nota"))
    _cache["params"] = cargar_parametros()
    try:
        trabajo = ram_config.recalcular(al_terminar=_recargar, fuentes=("ict",))
    except ram_config.ErrorRam as e:
        raise HTTPException(409, str(e)) from e
    return {"advertencias": adv, "recalculo": trabajo, **modelo_api.resumen()}


@app.delete("/api/modelo")
def modelo_restaurar():
    """Vuelve a los parametros de parametros.yaml y recalcula el ICT."""
    if ram_config.ocupado():
        raise HTTPException(409, "Ya hay un recálculo en curso")
    borrado = modelo_api.borrar()
    _cache["params"] = cargar_parametros()
    try:
        trabajo = ram_config.recalcular(al_terminar=_recargar, fuentes=("ict",))
    except ram_config.ErrorRam as e:
        raise HTTPException(409, str(e)) from e
    return {"borrado": borrado, "recalculo": trabajo, **modelo_api.resumen()}


@app.get("/api/historial")
def historial_parametros(componente: str | None = None):
    """Versiones de los parametros editados desde la aplicacion (ram, ejecucion, modelo), la mas reciente primero."""
    return historial.leer(componente, n=50)


@app.get("/api/paquetes")
def obtener_paquetes():
    """Capa Oro pre-calculada (ICT, criterios, componentes reales, tendencia y escalamiento del ultimo run)."""
    ruta = ORO / "paquetes_ict.geojson"
    if not ruta.exists():
        raise HTTPException(404, "Aún no hay ICT: corre el pipeline (python ejecutar_pipeline.py)")
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
    permitidas = {"comunidades", "areas", "hidro", "vias", "proyectos", "rios", "cuerpos_agua", "municipios", "limite_departamental", "red_vial",
                  "cobertura_estaciones", "cobertura_paquetes", "lluvia_chirps", "resguardos", "areas_protegidas_runap", "indicadores_municipio",
                  "contexto_paquetes", "grid_calor", "puntos_crisis", "zonas_intervencion"}
    if nombre not in permitidas:
        raise HTTPException(404, f"Capa desconocida. Disponibles: {sorted(permitidas)}")
    if nombre == "contexto_paquetes":        # tabla (CSV): una fila por paquete
        ruta_csv = ORO / "contexto_paquetes.csv"
        if not ruta_csv.exists():
            return {"paquetes": {}}
        tabla = pd.read_csv(ruta_csv)
        return {"paquetes": {f["id_paquete"]: f for f in json.loads(tabla.to_json(orient="records"))}}
    if nombre == "cobertura_paquetes":      # tabla (CSV): se sirve agrupada por paquete
        ruta_csv = ORO / "cobertura_paquetes.csv"
        if not ruta_csv.exists():
            return {"paquetes": {}}
        tabla = pd.read_csv(ruta_csv)
        return {"paquetes": {idp: g.drop(columns="id_paquete").to_dict("records") for idp, g in tabla.groupby("id_paquete")}}
    ruta = ORO / f"{nombre}.geojson"
    if not ruta.exists() and (ORO / f"{nombre}.json").exists():     # productos que no son capas geograficas (lluvia_chirps)
        ruta = ORO / f"{nombre}.json"
    if not ruta.exists():  # capas de datos abiertos: vacias hasta que se descargan
        return {"type": "FeatureCollection", "features": []}
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/alertas")
def obtener_alertas():
    ruta = ORO / "alertas.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/alertas/estado")
def alertas_estado():
    """Tarea diaria: cuando corrio y cuando corre, las novedades del ultimo corte y los canales de aviso (sin secretos)."""
    return tarea_programada.estado()


@app.post("/api/alertas/actualizar")
def alertas_actualizar(cuerpo: dict = Body(default={})):
    """Corre ya la tarea diaria: descarga (si `descargas`), recalcula, arma el boletin y avisa si hay novedades."""
    try:
        return tarea_programada.lanzar(_recargar, con_descargas=bool(cuerpo.get("descargas", True)), origen="manual")
    except ram_config.ErrorRam as e:
        raise HTTPException(409, str(e)) from e


@app.get("/api/alertas/boletin")
def alertas_boletin():
    """El boletin del ultimo corte, para leer, imprimir o reenviar."""
    nov = tarea_diaria.novedades()
    ruta = tarea_diaria.CARPETA / nov["boletin_html"] if nov else None
    if not ruta or not ruta.exists():
        raise HTTPException(404, "Aún no hay boletín: corre el pipeline o la tarea diaria")
    return FileResponse(ruta, media_type="text/html")


@app.get("/api/clima")
def obtener_clima():
    """Estaciones del IDEAM (datos abiertos) con lluvia acumulada. Vacio si aun no se hizo la ingesta."""
    ruta = ORO / "clima_estaciones.geojson"
    if not ruta.exists():
        return {"type": "FeatureCollection", "features": [], "metadata": None}
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/clima/ahora")
def clima_ahora(forzar: bool = False):
    """Ultimas lecturas del IDEAM por estacion, consultadas en vivo (cache de 10 min) con respaldo local."""
    return obtener_ahora(forzar)


@app.get("/api/clima/radiacion")
def clima_radiacion():
    """Puntos de radiacion global media (promedios mensuales del IDEAM)."""
    ruta = ORO / "clima_radiacion.geojson"
    if not ruta.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(ruta.read_text(encoding="utf-8"))


@app.get("/api/catalogo")
def obtener_catalogo():
    """Inventario vivo de las capas Bronce/Plata/Oro con descripciones curadas."""
    return construir_catalogo()


@app.get("/api/flujo")
def obtener_flujo():
    """Flujo de la aplicacion para la vista flujo.html: pasos del pipeline, fuentes, auditoria, pruebas y versiones."""
    return construir_flujo()


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
