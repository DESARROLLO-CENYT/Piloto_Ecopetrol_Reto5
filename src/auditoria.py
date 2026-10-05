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
    for nombre in ("clima_estaciones", "rios", "cuerpos_agua", "municipios", "limite_departamental", "red_vial"):
        ruta = ORO / f"{nombre}.geojson"
        if not ruta.exists():
            continue
        meta = json.loads(ruta.read_text(encoding="utf-8")).get("metadata") or {}
        origen = meta.get("fuente") or meta.get("fuentes")
        licencia = meta.get("licencia") or meta.get("fuentes")
        fecha = meta.get("descargado_en") or "descargada el" in json.dumps(meta.get("fuentes", {}))
        faltan = [k for k, v in (("fuente", origen), ("licencia", licencia), ("fecha de descarga", fecha)) if not v]
        out.append(fila("trazabilidad", f"gold/{nombre}.geojson", "dice su fuente, licencia y fecha", ERROR if faltan else OK, f"falta: {', '.join(faltan)}" if faltan else ""))
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
