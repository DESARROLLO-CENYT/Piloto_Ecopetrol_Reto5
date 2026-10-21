"""Auditoria del pipeline: comprueba que las tres capas medallion estan completas, son coherentes y cumplen las reglas.

Seis grupos de comprobaciones (cada una da OK, ALERTA o ERROR):

  reglas        El codigo respeta las capas: bronce no lee Plata ni Oro; plata no lee Oro; oro no lee Bronce;
                solo bronce toca la red (internet).
  artefactos    Cada artefacto que declara un paso existe, se puede leer, no esta vacio, tiene CRS EPSG:4326 (si es
                geografico) y geometrias validas y no vacias en Plata y Oro; los JSON de Oro no traen NaN.
  trazabilidad  Los productos Oro de fuentes externas dicen de donde vienen (fuente, licencia, fecha de descarga).
  conciliacion  Las cuentas cuadran entre capas: lo que entra menos lo descartado es lo que sale.
  geografia     Lo inventado (proyectos, paquetes, comunidades, areas, arroyos, vias, riesgos y estaciones
                simuladas) cae dentro de La Guajira: no en el mar ni en otro departamento.
  huerfanos     Archivos en data/ que ningun paso declara (restos de versiones anteriores).

Uso:  python -m auditoria     (o  python ejecutar_pipeline.py --auditar)
Escribe data/auditoria_pipeline.csv y termina con codigo 1 si hay algun ERROR.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from comun.config import BRONCE, DATA, ORO, PLATA
from pipeline import ARTEFACTOS, PASOS, SRC, _base, archivos_de, huerfanos

OK, ALERTA, ERROR = "OK", "ALERTA", "ERROR"


def fila(grupo: str, objeto: str, chequeo: str, estado: str, detalle: str = "", filas=None) -> dict:
    return {"grupo": grupo, "objeto": objeto, "chequeo": chequeo, "estado": estado, "detalle": detalle, "filas": filas}


# ---------------------------------------------------------------------------
# 1. Reglas de capas (analisis estatico del codigo)
# ---------------------------------------------------------------------------

# Que constantes de ruta y paquetes no puede usar cada capa
PROHIBIDO = {
    "bronce": {"constantes": {"PLATA", "ORO"}, "paquetes": {"plata", "oro"}},
    "plata": {"constantes": {"ORO"}, "paquetes": {"oro"}},
    "oro": {"constantes": {"BRONCE"}, "paquetes": {"bronce", "plata"}},
    "consumo": {"constantes": {"BRONCE", "PLATA"}, "paquetes": {"bronce", "plata"}},
}
RED = {"urllib", "requests", "http", "socket"}      # solo la capa bronce puede descargar
RED_COMUN = {"comun.http"}


def _usos(archivo: Path) -> tuple[set[str], set[str]]:
    """(nombres usados, modulos importados) de un archivo .py."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres, modulos = set(), set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Name):
            nombres.add(n.id)
        elif isinstance(n, ast.Import):
            modulos |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            modulos.add(n.module)
    return nombres, modulos


def reglas_de_capas(src: Path = SRC) -> list[dict]:
    out = []
    for capa, prohibido in PROHIBIDO.items():
        for archivo in sorted((src / capa).glob("*.py")):
            if archivo.name == "__init__.py":
                continue
            nombres, modulos = _usos(archivo)
            raices = {m.split(".")[0] for m in modulos}
            problemas = []
            if nombres & prohibido["constantes"]:
                problemas.append(f"usa rutas de {sorted(nombres & prohibido['constantes'])}")
            if raices & prohibido["paquetes"]:
                problemas.append(f"importa {sorted(raices & prohibido['paquetes'])}")
            if capa != "bronce" and (raices & RED or modulos & RED_COMUN):
                problemas.append("accede a la red (solo bronce puede)")
            out.append(fila("reglas", f"{capa}/{archivo.name}", f"respeta la capa {capa}", ERROR if problemas else OK, "; ".join(problemas)))
    return out


# ---------------------------------------------------------------------------
# 2. Artefactos: existen y estan sanos
# ---------------------------------------------------------------------------

def _estricto(texto: str):
    def rechazar(c):
        raise ValueError(f"valor no valido en JSON: {c}")
    return json.loads(texto, parse_constant=rechazar)


# productos que pueden estar vacios un dia cualquiera sin que sea un error
PUEDEN_ESTAR_VACIOS = {"puntos_crisis.geojson", "zonas_intervencion.geojson"}


def revisar_archivo(ruta: Path) -> dict:
    """Lee un archivo segun su formato y devuelve {estado, detalle, filas}."""
    capa = ruta.parent.name           # bronze | silver | gold | exports
    estricto = capa in ("silver", "gold")
    try:
        if ruta.suffix == ".geojson":
            texto = ruta.read_text(encoding="utf-8")
            if capa == "gold":
                _estricto(texto)      # sin NaN ni Infinity: romperian la API
            gdf = gpd.read_file(ruta)
            if gdf.empty and ruta.name in PUEDEN_ESTAR_VACIOS:
                return {"estado": OK, "detalle": "sin filas: hoy ningun paquete escala a crisis", "filas": 0}
            if gdf.empty:
                return {"estado": ERROR, "detalle": "sin filas", "filas": 0}
            if estricto:
                if gdf.crs is None or gdf.crs.to_epsg() != 4326:
                    return {"estado": ERROR, "detalle": f"CRS {gdf.crs} (se esperaba EPSG:4326)", "filas": len(gdf)}
                if gdf.geometry.isna().any() or gdf.geometry.is_empty.any():
                    return {"estado": ERROR, "detalle": "geometrias vacias", "filas": len(gdf)}
                invalidas = int((~gdf.geometry.is_valid).sum())
                if invalidas:
                    return {"estado": ERROR, "detalle": f"{invalidas} geometrias invalidas", "filas": len(gdf)}
            return {"estado": OK, "detalle": "", "filas": len(gdf)}
        if ruta.suffix == ".tif":
            import rasterio
            with rasterio.open(ruta) as r:
                n = r.width * r.height
                if r.crs is None or r.crs.to_epsg() != 4326:
                    return {"estado": ERROR, "detalle": f"CRS {r.crs} (se esperaba EPSG:4326)", "filas": n}
            return {"estado": OK if n else ERROR, "detalle": "" if n else "sin celdas", "filas": n}
        if ruta.suffix == ".parquet":
            n = len(pd.read_parquet(ruta))
        elif ruta.suffix == ".csv":
            n = len(pd.read_csv(ruta))
        elif ruta.suffix == ".xlsx":
            n = len(pd.read_excel(ruta))
        elif ruta.suffix == ".json":
            datos = _estricto(ruta.read_text(encoding="utf-8")) if estricto else json.loads(ruta.read_text(encoding="utf-8"))
            n = len(datos) if isinstance(datos, list) else 1
        else:
            return {"estado": OK, "detalle": "formato no inspeccionado", "filas": None}
        return {"estado": OK if n else ERROR, "detalle": "" if n else "sin filas", "filas": n}
    except Exception as e:  # noqa: BLE001 - cualquier fallo de lectura es un hallazgo
        return {"estado": ERROR, "detalle": f"no se pudo leer: {type(e).__name__}: {e}"[:160], "filas": None}


def artefactos() -> list[dict]:
    out = []
    for p in PASOS:
        for art in p.escribe:
            archivos = archivos_de(art)
            if not archivos:
                out.append(fila("artefactos", art, f"lo escribe {p.id}", ERROR, "no hay ningun archivo"))
                continue
            faltan = [pat for pat in ARTEFACTOS[art] if "*" not in pat and not _base(pat).exists()]
            if faltan:
                out.append(fila("artefactos", art, f"lo escribe {p.id}", ERROR, f"faltan: {', '.join(faltan)}"))
            for ruta in archivos:
                r = revisar_archivo(ruta)
                out.append(fila("artefactos", f"{ruta.parent.name}/{ruta.name}", f"existe y es legible ({p.id})", r["estado"], r["detalle"], r["filas"]))
    return out


# ---------------------------------------------------------------------------
# 3. Trazabilidad de los productos Oro de fuentes externas
# ---------------------------------------------------------------------------

def trazabilidad() -> list[dict]:
    out = []
    for nombre in ("clima_estaciones.geojson", "rios.geojson", "cuerpos_agua.geojson", "municipios.geojson", "limite_departamental.geojson",
                   "red_vial.geojson", "resguardos.geojson", "areas_protegidas_runap.geojson", "lluvia_chirps.json", "indicadores_municipio.json"):
        ruta = ORO / nombre
        nombre = nombre.rsplit(".", 1)[0]
        if not ruta.exists():
            continue
        meta = json.loads(ruta.read_text(encoding="utf-8")).get("metadata") or {}
        origen = meta.get("fuente") or meta.get("fuentes")
        licencia = meta.get("licencia") or meta.get("fuentes")
        fecha = meta.get("descargado_en") or "descargada el" in json.dumps(meta.get("fuentes", {}))
        faltan = [k for k, v in (("fuente", origen), ("licencia", licencia), ("fecha de descarga", fecha)) if not v]
        out.append(fila("trazabilidad", f"gold/{ruta.name}", "dice su fuente, licencia y fecha", ERROR if faltan else OK, f"falta: {', '.join(faltan)}" if faltan else ""))
    return out


# ---------------------------------------------------------------------------
# 4. Conciliacion: las cuentas cuadran entre capas
# ---------------------------------------------------------------------------

def _reporte(nombre: str) -> dict | None:
    ruta = PLATA / nombre
    return pd.read_csv(ruta).iloc[0].to_dict() if ruta.exists() else None


def _filas(ruta: Path) -> int | None:
    if not ruta.exists():
        return None
    return len(pd.read_parquet(ruta)) if ruta.suffix == ".parquet" else len(gpd.read_file(ruta)) if ruta.suffix == ".geojson" else len(pd.read_csv(ruta))


def _cuadra(objeto: str, chequeo: str, esperado, obtenido, tolerancia: float = 0) -> dict:
    ok = esperado is not None and obtenido is not None and abs(esperado - obtenido) <= tolerancia
    detalle = f"esperado {esperado:,.1f} y hay {obtenido:,.1f}" if not ok and None not in (esperado, obtenido) else ("" if ok else "falta un dato")
    return fila("conciliacion", objeto, chequeo, OK if ok else ERROR, detalle)


def conciliacion() -> list[dict]:
    out = []
    r = _reporte("reporte_calidad_ideam.csv")
    if r:
        out.append(_cuadra("ideam lluvia", "lecturas Bronce - duplicados - imposibles - sin dato = lecturas Plata",
                           r["lecturas_bronce"] - r["duplicados_removidos"] - r["lecturas_sin_fecha_o_valor"] - r["lecturas_imposibles"], r["lecturas_plata"]))
        if "estaciones_duplicadas_removidas" in r:
            out.append(_cuadra("ideam estaciones", "estaciones Bronce - fuera de la caja - repetidas = estaciones Plata",
                               r["estaciones_bronce"] - r["estaciones_fuera_de_la_caja"] - r["estaciones_duplicadas_removidas"], r["estaciones_plata"]))
        out.append(_cuadra("ideam lluvia", "las lecturas de Bronce son las que dice el reporte", r["lecturas_bronce"], _filas(BRONCE / "ideam_precipitacion.parquet")))
        if "var_bronce" in r:
            out.append(_cuadra("ideam variables", "lecturas Bronce - descartadas = lecturas Plata",
                               r["var_bronce"] - r["var_sensor_descartado"] - r["var_sin_fecha_o_valor"] - r["var_fuera_de_rango"] - r["var_duplicados_removidos"], r["var_plata"]))
        if "ult_bronce" in r:
            out.append(_cuadra("ideam ultimas horas", "lecturas Bronce - descartadas = lecturas Plata",
                               r["ult_bronce"] - r["ult_sensor_descartado"] - r["ult_sin_fecha_o_valor"] - r["ult_fuera_de_rango"] - r["ult_duplicados_removidos"], r["ult_plata"]))
        # Oro: una ficha por estacion con algun dato diario en Plata
        con_datos = set(pd.read_parquet(PLATA / "ideam_precip_diaria.parquet", columns=["codigoestacion"])["codigoestacion"])
        if (PLATA / "ideam_variables_diaria.parquet").exists():
            con_datos |= set(pd.read_parquet(PLATA / "ideam_variables_diaria.parquet", columns=["codigoestacion"])["codigoestacion"])
        if (ORO / "clima_estaciones.geojson").exists():
            out.append(_cuadra("ideam Oro", "una ficha por estacion con datos en Plata", len(con_datos), len(json.loads((ORO / "clima_estaciones.geojson").read_text(encoding="utf-8"))["features"])))
    r = _reporte("reporte_calidad_bronce_a_plata.csv")
    if r:
        out.append(_cuadra("riesgos sinteticos", "filas Bronce - duplicados = filas Plata", r["filas_bronce"] - r["duplicados_removidos"], r["filas_plata"]))
        out.append(_cuadra("riesgos sinteticos", "las filas de Plata estan en el archivo", r["filas_plata"], _filas(PLATA / "riesgos.geojson")))
        if "ram_sin_clasificar" in r:
            out.append(_cuadra("matriz RAM", "todo riesgo queda ubicado en la matriz (sin probabilidad legible = 0)", 0, r["ram_sin_clasificar"]))
            riesgos = gpd.read_file(PLATA / "riesgos.geojson")
            abiertas = int(((riesgos["tipo"] == "amenaza") & (riesgos["estado"] != "materializado") & riesgos["nivel_residual"].notna()).sum())
            paq = ORO / "paquetes_ict.geojson"
            if paq.exists():
                p = gpd.read_file(paq)
                cols = [f"ram_{n}" for n in ("N", "L", "M", "H", "VH")]
                if set(cols) <= set(p.columns):
                    out.append(_cuadra("matriz RAM", "Oro: amenazas abiertas por nivel en los paquetes = las de Plata", abiertas, int(p[cols].sum().sum())))
    out += conciliacion_ict()
    out += conciliacion_cronograma()
    out += conciliacion_riesgo_actividad()
    out += conciliacion_fechas_riesgos()
    r = _reporte("reporte_calidad_invias.csv")
    if r:
        out.append(_cuadra("invias", "tramos Bronce - sin geometria - repetidos = tramos Plata", r["tramos_bronce"] - r["sin_geometria"] - r["repetidos_removidos"], r["tramos_plata"]))
    r = _reporte("reporte_calidad_hidrografia.csv")
    if r:
        out.append(_cuadra("hidrografia", "objetos Bronce - sin geometria - fuera de la caja - vacios = objetos Plata",
                           r["objetos_bronce"] - r["sin_geometria"] - r["fuera_de_la_caja"] - r["vacias_tras_simplificar"], r["objetos_plata"]))
        n_oro = (_filas(ORO / "rios.geojson") or 0) + (_filas(ORO / "cuerpos_agua.geojson") or 0)
        out.append(_cuadra("hidrografia", "rios + cuerpos de agua en Oro = objetos Plata", r["objetos_plata"], n_oro))
    r = _reporte("reporte_calidad_vias_igac.csv")
    if r:
        out.append(_cuadra("vias igac", "objetos Bronce - descartados + partes nuevas = objetos Plata",
                           r["objetos_bronce"] - r["sin_geometria"] - r["tipo_desconocido"] - r["fuera_del_limite"] + r["partes_nuevas_por_recorte"] - r["astillas_descartadas"], r["objetos_plata"]))
    r = _reporte("reporte_calidad_municipios.csv")
    if r:
        out.append(_cuadra("municipios", "municipios Bronce = Plata = Oro", r["municipios_bronce"], _filas(ORO / "municipios.geojson")))
        out.append(_cuadra("municipios", "los municipios cubren un solo territorio sin huecos nuevos", 1, r["partes_del_departamento"]))
    r = _reporte("reporte_calidad_chirps.csv")
    if r:
        out.append(_cuadra("chirps", "meses en Bronce = meses en Plata", r["meses_bronce"], r["meses_plata"]))
        out.append(_cuadra("chirps", "una fila por zona (15 municipios + departamento) y mes", r["zonas"] * r["meses_plata"], r["filas_plata"]))
        if (ORO / "lluvia_chirps.json").exists():
            o = json.loads((ORO / "lluvia_chirps.json").read_text(encoding="utf-8"))
            out.append(_cuadra("chirps", "Oro tiene los 15 municipios con una cifra por mes visible", 15 * len(o["metadata"]["meses"]),
                               sum(len(z["mm"]) for z in o["municipios"].values())))
    out += conciliacion_social()
    cob = ORO / "cobertura_paquetes.csv"
    if cob.exists() and (PLATA / "paquetes.geojson").exists():
        out.append(_cuadra("cobertura", "cada paquete de Plata tiene su cobertura de estaciones",
                           len(gpd.read_file(PLATA / "paquetes.geojson")), pd.read_csv(cob)["id_paquete"].nunique()))
    r = _reporte("reporte_calidad_red_vial.csv")
    if r:
        out.append(_cuadra("red vial", "km INVIAS + km IGAC - repetidos - astillas = km de la red (+-1 km)",
                           r["km_invias"] + r["km_igac"] - r["km_igac_repetido_con_invias"] - r["km_igac_astillas_quitadas"], r["km_red"], 1))
        out.append(_cuadra("red vial", "tramos INVIAS + tramos IGAC conservados = tramos de la red", r["tramos_invias"] + r["tramos_igac_conservados"], r["tramos_red"]))
        out.append(_cuadra("red vial", "Oro tiene los mismos tramos que Plata", r["tramos_red"], _filas(ORO / "red_vial.geojson")))
        mun = ORO / "municipios.geojson"
        if mun.exists():
            km_mun = gpd.read_file(mun)["km_vias"].sum() if "km_vias" in gpd.read_file(mun) else None
            out.append(_cuadra("red vial", "la suma de km por municipio es la de la red (+-0,5 %)", r["km_red"], km_mun, r["km_red"] * 0.005))
    return out


def conciliacion_ict() -> list[dict]:
    """El ICT cuadra: suma de aportes, escalas, puntos de crisis y alertas."""
    out = []
    paq = ORO / "paquetes_ict.geojson"
    if not paq.exists() or not (PLATA / "paquetes.geojson").exists():
        return out
    p = gpd.read_file(paq)
    criterios = ["severidad_riesgo", "exposicion_proyecto", "vulnerabilidad_territorial", "amenazas_externas", "convergencia"]
    out.append(_cuadra("ict", "un paquete en Oro por cada paquete de Plata", len(gpd.read_file(PLATA / "paquetes.geojson")), len(p)))
    suma = p[[f"{c}_contrib" for c in criterios]].sum(axis=1)
    out.append(_cuadra("ict", "el ICT es la suma de los aportes de los 5 criterios (+-0,3 por paquete)", 0.0,
                       float((p["ICT"] - suma).abs().max()), 0.3))
    fuera = int(((p[criterios] < 0) | (p[criterios] > 1)).sum().sum())
    out.append(_cuadra("ict", "los 5 criterios estan en su escala fija de 0 a 1", 0, fuera))
    out.append(_cuadra("ict", "ICT entre 0 y 100 y confianza entre 0 y 1", 0,
                       int(((p["ICT"] < 0) | (p["ICT"] > 100) | (p["indice_confianza"] < 0) | (p["indice_confianza"] > 1)).sum())))
    if "municipio" in p:
        out.append(_cuadra("ict", "cada paquete tiene el municipio real que lo contiene", 0, int(p["municipio"].isna().sum())))
    pc = ORO / "puntos_crisis.geojson"
    if pc.exists():
        puntos = gpd.read_file(pc)
        escalados = set(p.loc[p["escalamiento"].astype(bool), "id_paquete"])
        out.append(_cuadra("ict", "todo punto de crisis es de un paquete en escalamiento", 0,
                           int((~puntos["id_paquete"].isin(escalados)).sum()) if len(puntos) else 0))
        out.append(_cuadra("ict", "puntos de crisis en el mapa = los que cuenta cada paquete", int(p["puntos_crisis"].sum()), len(puntos)))
    al = ORO / "alertas.json"
    if al.exists():
        alertas = json.loads(al.read_text(encoding="utf-8"))
        esperadas = int((p["escalamiento"].astype(bool) | p["tendencia_alerta"].astype(bool)).sum())
        out.append(_cuadra("ict", "una alerta por paquete en escalamiento o con tendencia al alza", esperadas, len(alertas)))
    return out


def conciliacion_cronograma() -> list[dict]:
    """El cronograma cuadra: pesos que suman 1, avances entre 0 y 1, estados coherentes y fechas en orden."""
    out = []
    arch = {n: ORO / f"cronograma_{n}.csv" for n in ("actividades", "paquetes", "proyectos")}
    if not all(a.exists() for a in arch.values()) or not (PLATA / "actividades.parquet").exists():
        return out
    a = pd.read_csv(arch["actividades"], parse_dates=["fecha_inicio_plan", "fecha_fin_plan", "fecha_inicio_proyectada", "fecha_fin_proyectada", "fecha_corte"])
    p = pd.read_csv(arch["paquetes"], parse_dates=["fecha_inicio_plan", "fecha_fin_plan", "fecha_fin_proyectada", "fecha_corte"])
    pr = pd.read_csv(arch["proyectos"])
    plata = pd.read_parquet(PLATA / "actividades.parquet")
    r = _reporte("reporte_calidad_bronce_a_plata.csv")
    if r and "actividades_bronce" in r:
        out.append(_cuadra("cronograma", "actividades Bronce - repetidas - sin paquete = actividades Plata",
                           r["actividades_bronce"] - r["actividades_repetidas_removidas"] - r["actividades_sin_paquete_valido"], len(plata)))
    out.append(_cuadra("cronograma", "las actividades de Oro son las de Plata", len(plata), len(a)))
    pesos = a.groupby("id_paquete")["peso_en_paquete"].sum()
    out.append(_cuadra("cronograma", "los pesos de las actividades de cada paquete suman 1 (+-0,001)", 0.0, float((pesos - 1).abs().max()), 0.001))
    por_proy = a.groupby("id_proyecto")["peso_en_proyecto"].sum()
    out.append(_cuadra("cronograma", "los pesos de las actividades de cada proyecto suman 1 (+-0,001)", 0.0, float((por_proy - 1).abs().max()), 0.001))
    out.append(_cuadra("cronograma", "avances entre 0 y 1", 0, int(((a["avance"] < 0) | (a["avance"] > 1)).sum())))
    estado_ok = ((a["estado"] == "completada") == (a["avance"] >= 1)) & ((a["estado"] == "por_iniciar") == (a["avance"] <= 0))
    out.append(_cuadra("cronograma", "el estado de cada actividad coincide con su avance", 0, int((~estado_ok).sum())))
    fechas = int((a["fecha_inicio_plan"] > a["fecha_fin_plan"]).sum() + (a["fecha_inicio_proyectada"] > a["fecha_fin_proyectada"]).sum())
    out.append(_cuadra("cronograma", "toda actividad empieza antes de terminar (plan y proyectado)", 0, fechas))
    pendientes = a[a["estado"] != "completada"]
    out.append(_cuadra("cronograma", "lo que falta por hacer se proyecta desde la fecha de corte en adelante", 0,
                       int((pendientes["fecha_fin_proyectada"] < pendientes["fecha_corte"]).sum())))
    av_paq = (a["peso_en_paquete"] * a["avance"]).groupby(a["id_paquete"]).sum()
    out.append(_cuadra("cronograma", "el avance de cada paquete es la suma de sus actividades por su peso (+-0,001)", 0.0,
                       float((p.set_index("id_paquete")["avance"] - av_paq).abs().max()), 0.001))
    av_proy = (a["peso_en_proyecto"] * a["avance"]).groupby(a["id_proyecto"]).sum()
    out.append(_cuadra("cronograma", "el avance de cada proyecto es la suma de sus actividades por su peso en el proyecto (+-0,001)", 0.0,
                       float((pr.set_index("id_proyecto")["avance"] - av_proy).abs().max()), 0.001))
    criticos = p[p["ruta_critica"].astype(bool)]
    fin_proy = pr.set_index("id_proyecto")["fecha_fin_plan"]
    desfase = int((criticos["fecha_fin_plan"].dt.strftime("%Y-%m-%d") != criticos["id_proyecto"].map(fin_proy)).sum())
    out.append(_cuadra("cronograma", "un paquete de ruta critica termina el mismo dia que su proyecto (sin holgura)", 0, desfase))
    return out


def conciliacion_riesgo_actividad() -> list[dict]:
    """Cada riesgo apunta a una actividad de su paquete que cuadra con su momento, y los conteos de Oro lo reflejan."""
    out = []
    rp, ap = PLATA / "riesgos.geojson", PLATA / "actividades.parquet"
    if not rp.exists() or not ap.exists():
        return out
    r = gpd.read_file(rp)
    if "id_actividad" not in r:
        return out
    a = pd.read_parquet(ap).set_index("id_actividad")
    corte = pd.to_datetime(a["fecha_corte"]).max()
    rep = _reporte("reporte_calidad_bronce_a_plata.csv")
    if rep and "riesgos_actividad_por_codigo" in rep:
        partes = sum(rep[k] for k in ("riesgos_actividad_por_codigo", "riesgos_actividad_por_nombre", "riesgos_actividad_inferidas",
                                      "riesgos_actividad_codigo_de_otro_paquete"))
        out.append(_cuadra("riesgos", "por código + por nombre + inferidas + código de otro paquete = riesgos de Plata", rep["filas_plata"], partes))
    out.append(_cuadra("riesgos", "todo riesgo tiene actividad", 0, int(r["id_actividad"].isna().sum())))
    de_otro = r["id_actividad"].map(a["id_paquete"]) != r["id_paquete_trabajo"]
    out.append(_cuadra("riesgos", "la actividad de cada riesgo es de su mismo paquete", 0, int(de_otro.sum())))
    abiertos = r[r["estado"] != "materializado"]
    out.append(_cuadra("riesgos", "ningún riesgo abierto apunta a una actividad ya terminada", 0,
                       int((abiertos["id_actividad"].map(a["estado"]) == "completada").sum())))
    mat = r[(r["estado"] == "materializado") & r["fecha_materializacion"].notna()]
    fm = pd.to_datetime(mat["fecha_materializacion"])
    inicio = pd.to_datetime(mat["id_actividad"].map(a["fecha_inicio_real"]))
    fin = pd.to_datetime(mat["id_actividad"].map(a["fecha_fin_real"])).fillna(corte)
    out.append(_cuadra("riesgos", "todo riesgo materializado ocurrió mientras se ejecutaba su actividad", 0,
                       int((inicio.isna() | (inicio > fm) | (fm > fin)).sum())))
    prox = r[r["estado"] == "proximo_a_materializarse"]
    pronto = (prox["id_actividad"].map(a["estado"]) == "en_curso") | \
        (pd.to_datetime(prox["id_actividad"].map(a["fecha_inicio_proyectada"])) <= corte + pd.Timedelta(days=45))
    out.append(_cuadra("riesgos", "todo riesgo próximo a materializarse pega en algo que se ejecuta o arranca en 45 días", 0, int((~pronto).sum())))
    ca = ORO / "cronograma_actividades.csv"
    if ca.exists():
        c = pd.read_csv(ca)
        if "riesgos" in c:
            out.append(_cuadra("cronograma", "los riesgos contados por actividad son los del registro", len(r), int(c["riesgos"].sum())))
            amen = int(((r["tipo"] == "amenaza") & (r["estado"] != "materializado")).sum())
            out.append(_cuadra("cronograma", "las amenazas abiertas por actividad suman las del registro", amen, int(c["amenazas_abiertas"].sum())))
    er = ORO / "ejecucion_riesgos.csv"
    cron = PLATA / "cronograma.parquet"
    if er.exists() and cron.exists():
        e = pd.read_csv(er)
        if "horizonte_origen" in e:
            meses = pd.read_parquet(cron).set_index("id_paquete")["meses_restantes"]
            por_act = e[e["horizonte_origen"] == "actividad"]
            mas_largo = por_act["horizonte_anios"] * 12 > por_act["id_paquete"].map(meses) + 0.2
            out.append(_cuadra("ejecucion", "el horizonte de una amenaza (su actividad) no pasa lo que le falta a su paquete", 0, int(mas_largo.sum())))
    return out


def conciliacion_fechas_riesgos() -> list[dict]:
    """Las fechas de cada riesgo cuentan una historia posible (lo que no, queda marcado para revisar)."""
    out = []
    rp = PLATA / "riesgos.geojson"
    if not rp.exists():
        return out
    r = gpd.read_file(rp)
    if "revisar_fechas" not in r:
        return out
    ap = PLATA / "actividades.parquet"
    corte = pd.to_datetime(pd.read_parquet(ap)["fecha_corte"]).max() if ap.exists() else pd.Timestamp.today().normalize()
    ident, fm, acc = (pd.to_datetime(r[c]) for c in ("fecha_identificacion", "fecha_materializacion", "fecha_ejecucion_accion"))
    mat = r["estado"] == "materializado"
    rep = _reporte("reporte_calidad_bronce_a_plata.csv")
    if rep and "riesgos_fechas_por_revisar" in rep:
        out.append(_cuadra("riesgos", "los riesgos con fechas por revisar son los que dice el reporte", rep["riesgos_fechas_por_revisar"], int(r["revisar_fechas"].sum())))
    out.append(_cuadra("riesgos", "ningún riesgo se materializó después de la fecha de corte", 0, int((fm > corte).sum())))
    out.append(_cuadra("riesgos", "ningún riesgo se materializó antes de identificarse", 0, int((fm < ident).sum())))
    out.append(_cuadra("riesgos", "ningún riesgo abierto tiene fecha de materialización", 0, int((~mat & fm.notna()).sum())))
    out.append(_cuadra("riesgos", "todo materializado sin fecha está marcado para revisar", 0, int((mat & fm.isna() & ~r["revisar_fechas"]).sum())))
    out.append(_cuadra("riesgos", "ninguna acción es anterior a la identificación sin estar marcada", 0,
                       int(((acc < ident) & ~r["revisar_fechas"]).sum())))
    return out


def conciliacion_social() -> list[dict]:
    """Censo, resguardos, areas protegidas, seguridad, emergencias y contexto de los paquetes."""
    out = []
    indicadores = ORO / "indicadores_municipio.json"
    oro = json.loads(indicadores.read_text(encoding="utf-8")) if indicadores.exists() else None
    r = _reporte("reporte_calidad_social.csv")
    if r:
        out.append(_cuadra("social", "un registro del censo 2018 por municipio (15) y uno del departamento", 16, _filas(PLATA / "indicadores_censo2018.parquet")))
        out.append(_cuadra("social", "los 13 indicadores del censo llegaron", 0, r["indicadores_sin_tabla"]))
        out.append(_cuadra("social", "IRCA: filas Bronce = filas Plata (sin municipios desconocidos)", r["irca_bronce"] - r["irca_municipio_desconocido"], r["irca_plata"]))
    for fuente, archivo, oro_archivo in (("resguardos", "resguardos.geojson", "resguardos.geojson"),
                                         ("runap", "areas_protegidas_runap.geojson", "areas_protegidas_runap.geojson")):
        r = _reporte(f"reporte_calidad_{fuente}.csv")
        if r:
            clave = "resguardos" if fuente == "resguardos" else "areas"
            out.append(_cuadra(fuente, "Bronce - sin geometria - fuera de La Guajira = Plata",
                               r[f"{clave}_bronce"] - r["sin_geometria"] - r["fuera_de_la_guajira"], r[f"{clave}_plata"]))
            out.append(_cuadra(fuente, "Oro tiene los mismos objetos que Plata", r[f"{clave}_plata"], _filas(ORO / oro_archivo)))
    r = _reporte("reporte_calidad_seguridad.csv")
    if r:
        out.append(_cuadra("seguridad", "registros Bronce - fecha invalida - otro municipio - cantidad invalida = registros Plata",
                           r["filas_bronce"] - r["fecha_invalida"] - r["municipio_desconocido"] - r["cantidad_invalida"], r["registros_plata"]))
        out.append(_cuadra("seguridad", "las filas de Bronce son las que dice el reporte", r["filas_bronce"],
                           sum(len(pd.read_parquet(p)) for p in BRONCE.glob("mindefensa_*.parquet"))))
        if oro and "seguridad" in oro.get("departamento", {}):
            seg = pd.read_parquet(PLATA / "seguridad_municipio_mensual.parquet")
            visibles = seg[pd.to_datetime(seg["mes"]).dt.strftime("%Y-%m").isin(oro["metadata"]["meses"])]
            out.append(_cuadra("seguridad", "Oro: víctimas del departamento en los meses visibles = suma de Plata",
                               int(visibles["victimas"].sum()), sum(sum(v) for v in oro["departamento"]["seguridad"]["serie"].values())))
    r = _reporte("reporte_calidad_emergencias.csv")
    if r:
        out.append(_cuadra("emergencias", "filas Bronce - repetidas - fecha invalida - municipio desconocido = emergencias Plata",
                           r["filas_bronce"] - r["duplicados_removidos"] - r["fecha_invalida"] - r["municipio_desconocido"], r["emergencias_plata"]))
        if oro and "emergencias" in oro.get("departamento", {}):
            out.append(_cuadra("emergencias", "Oro: total del departamento = emergencias de Plata", r["emergencias_plata"], oro["departamento"]["emergencias"]["total"]))
    ej = ORO / "ejecucion_paquetes.csv"
    if ej.exists() and (PLATA / "paquetes.geojson").exists():
        pq, rg = pd.read_csv(ej), pd.read_csv(ORO / "ejecucion_riesgos.csv")
        out.append(_cuadra("ejecucion", "una fila de riesgo de ejecucion por paquete de Plata", len(gpd.read_file(PLATA / "paquetes.geojson")), len(pq)))
        riesgos = gpd.read_file(PLATA / "riesgos.geojson")
        out.append(_cuadra("ejecucion", "cada amenaza calificada de Plata entra al modelo",
                           int(((riesgos["tipo"] == "amenaza") & riesgos["probabilidad_residual"].notna()).sum()), len(rg)))
        # la simulacion (Monte Carlo) debe reproducir el valor esperado analitico: sum(lambda * T * dias medios), antes de
        # aplicar el solapamiento (que es una transformacion por escenario)
        col = "atraso_sin_solapamiento_media" if "atraso_sin_solapamiento_media" in pq else "atraso_media"
        simulado = float((pq[col] - pq["atraso_consumido"]).sum())
        analitico = float(rg["atraso_esperado"].sum())
        out.append(_cuadra("ejecucion", "atraso esperado simulado = analitico (+-5 % + 1 dia)", analitico, simulado, analitico * 0.05 + 1))
        out.append(_cuadra("ejecucion", "atraso consumido de los paquetes = el de las amenazas materializadas (+-0,1 dia)",
                           float(rg["consumido_dias"].sum()), float(pq["atraso_consumido"].sum()), 0.1 * len(pq)))
    ctx = ORO / "contexto_paquetes.csv"
    if ctx.exists() and (PLATA / "paquetes.geojson").exists():
        out.append(_cuadra("contexto", "una fila de contexto por paquete de Plata", len(gpd.read_file(PLATA / "paquetes.geojson")), _filas(ctx)))
    return out


# ---------------------------------------------------------------------------
# 5. Geografia de lo inventado
# ---------------------------------------------------------------------------

SINTETICOS_GEOGRAFICOS = ("proyectos", "paquetes", "comunidades", "areas", "hidro", "vias", "riesgos")


def geografia() -> list[dict]:
    """Todo lo inventado debe caer dentro de La Guajira (no en el mar ni en otro departamento). Se compara con el limite
    completo de los municipios del DANE si ya se proceso; si no, con el contorno de referencia."""
    from comun.marco_guajira import tierra

    mun = PLATA / "municipios.geojson"
    limite = gpd.read_file(mun).geometry.union_all() if mun.exists() else tierra()
    contra = "limite de los municipios del DANE" if mun.exists() else "contorno de referencia"
    out = []
    for nombre in SINTETICOS_GEOGRAFICOS:
        ruta = PLATA / f"{nombre}.geojson"
        if not ruta.exists():
            continue
        g = gpd.read_file(ruta)
        fuera = int((~g.geometry.within(limite)).sum())
        out.append(fila("geografia", f"silver/{nombre}.geojson", f"todo cae dentro de La Guajira ({contra})",
                        ERROR if fuera else OK, f"{fuera} de {len(g)} quedan fuera" if fuera else "", len(g)))
    clima = PLATA / "clima_sintetico.parquet"
    if clima.exists():
        est = pd.read_parquet(clima, columns=["id_estacion", "lon", "lat"]).drop_duplicates("id_estacion")
        fuera = int((~gpd.GeoSeries.from_xy(est["lon"], est["lat"], crs=4326).within(limite)).sum())
        out.append(fila("geografia", "silver/clima_sintetico.parquet", f"las estaciones simuladas caen dentro de La Guajira ({contra})",
                        ERROR if fuera else OK, f"{fuera} de {len(est)} quedan fuera" if fuera else "", len(est)))
    return out


# ---------------------------------------------------------------------------
# 6. Huerfanos
# ---------------------------------------------------------------------------

def hallar_huerfanos() -> list[dict]:
    lista = huerfanos()
    if not lista:
        return [fila("huerfanos", "data/", "todo archivo lo declara un paso", OK)]
    return [fila("huerfanos", f"{f.parent.name}/{f.name}", "todo archivo lo declara un paso", ALERTA, "ningun paso lo escribe: resto de una version anterior") for f in lista]


# ---------------------------------------------------------------------------

def auditar(guardar: bool = True) -> int:
    filas = reglas_de_capas() + artefactos() + trazabilidad() + conciliacion() + geografia() + hallar_huerfanos()
    df = pd.DataFrame(filas)
    if guardar:
        df.to_csv(DATA / "auditoria_pipeline.csv", index=False, encoding="utf-8")

    print(f"\n{'=' * 78}\nAUDITORIA DEL PIPELINE\n{'=' * 78}")
    resumen = df.groupby(["grupo", "estado"]).size().unstack(fill_value=0).reindex(columns=[OK, ALERTA, ERROR], fill_value=0)
    print(resumen.to_string())
    malos = df[df["estado"] != OK]
    for _, f in malos.iterrows():
        print(f"  [{f['estado']}] {f['grupo']} · {f['objeto']} · {f['chequeo']}: {f['detalle']}")
    errores = int((df["estado"] == ERROR).sum())
    print(f"\n{len(df)} comprobaciones: {int((df['estado'] == OK).sum())} OK, {int((df['estado'] == ALERTA).sum())} alertas, {errores} errores."
          + (f" Detalle en {DATA / 'auditoria_pipeline.csv'}" if guardar else ""))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(auditar())
