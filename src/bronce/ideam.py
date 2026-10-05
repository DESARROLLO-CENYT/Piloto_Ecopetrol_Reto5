"""
Ingesta del clima REAL del IDEAM desde datos abiertos (capa Bronce).

Fuente: portal datos.gov.co (Socrata), sin clave ni registro. Licencia de todos
los conjuntos: Creative Commons Attribution-ShareAlike 4.0.

Que se descarga:
  * Catalogo Nacional de Estaciones (hp9r-jxuu), filtrado a La Guajira.
  * Series por estacion: precipitacion (s54a-sgyg), temperatura del aire,
    maxima y minima, humedad, velocidad y direccion del viento, presion, nivel
    del rio y nivel del mar (ver ideam_comun.VARIABLES).
  * Radiacion global (promedios mensuales), normales climatologicas de 30 anos
    y el flujo de las ultimas ~12 h de todas las variables.

Como se hace (y por que):
  * Las consultas a nivel de departamento o agregadas sobre todo el historico
    (decenas o cientos de millones de filas) se agotan o devuelven resultados
    incompletos. Las consultas filtradas por estacion y fecha responden en
    segundos, asi que todo se hace estacion por estacion.
  * Para cada (variable, estacion) se "sondea" primero si tiene alguna fila
    (rapido) y luego cual es su ultima lectura reciente. Solo se descargan las
    que reportan dentro de la ventana.
  * Bronce guarda lo recibido tal cual (con duplicados y como texto), mas una
    columna `variable` con la clave interna; la limpieza es trabajo de Plata.

Uso:  python ingesta_ideam.py [--dias 30] [--hilos 6] [--solo precipitacion variables tablas]
Necesita internet.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pandas as pd

from comun.config import BRONCE, asegurar_directorios
from comun.http import ERRORES_RED, SOCRATA, USER_AGENT, socrata_url as url, soql
from comun.ideam import (
    DATASET_NORMALES, DATASET_RADIACION, DATASET_ULTIMAS_HORAS, VARIABLES, sin_tildes,
)

BASE = SOCRATA
CATALOGO = f"{BASE}/hp9r-jxuu.json"
PRECIPITACION = f"{BASE}/s54a-sgyg.json"
DEPARTAMENTO_CATALOGO = "La Guajira"

ESTADOS_SONDEO = ("Activa", "En Mantenimiento")
VENTANA_SONDEO_DIAS = 60
PAGINA = 50000
BLOQUE_DIAS_LLUVIA = 4


def descripcion_conjunto(dataset: str) -> str:
    """Descripcion oficial del conjunto (metadatos del portal); vacia si no responde."""
    try:
        req = urllib.request.Request(f"https://www.datos.gov.co/api/views/{dataset}.json", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            return (json.load(r).get("description") or "").strip()
    except ERRORES_RED + (ValueError,):
        return ""


# ---------------------------------------------------------------------------
# Catalogo y candidatas
# ---------------------------------------------------------------------------

def descargar_catalogo() -> pd.DataFrame:
    filas = soql(CATALOGO, where=f"departamento='{DEPARTAMENTO_CATALOGO}'", limit=5000)
    df = pd.DataFrame(filas)
    # 'ubicaci_n' llega con latitud y longitud invertidas; se descarta y se usan
    # las columnas 'latitud' y 'longitud' (Plata documenta y valida esto).
    if "ubicaci_n" in df.columns:
        df["ubicaci_n"] = df["ubicaci_n"].map(lambda v: json.dumps(v, ensure_ascii=False))
    return df


def _categoria(catalogo: pd.DataFrame) -> pd.Series:
    return catalogo["categoria"].fillna("")


def candidatas_lluvia(catalogo: pd.DataFrame) -> list[str]:
    """Estaciones que pueden medir lluvia: activas o en mantenimiento, sin las de nivel de rio o mar."""
    ok = catalogo["estado"].isin(ESTADOS_SONDEO)
    ok &= ~_categoria(catalogo).str.startswith(("Limn", "Marina", "Radio Sonda"))
    return sorted(catalogo.loc[ok, "codigo"].dropna().unique())


def candidatas_variable(catalogo: pd.DataFrame, clave: str) -> list[str]:
    ok = catalogo["estado"].isin(ESTADOS_SONDEO)
    cat = _categoria(catalogo)
    if clave == "nivel_rio":
        ok &= cat.str.startswith("Limn")
    elif clave == "nivel_mar":
        ok &= cat.str.startswith("Marina")
    else:
        ok &= ~cat.str.startswith(("Limn", "Radio Sonda"))
    return sorted(catalogo.loc[ok, "codigo"].dropna().unique())


# ---------------------------------------------------------------------------
# Sondeo y descarga por estacion
# ---------------------------------------------------------------------------

def sondear(url_: str, codigo: str, desde: datetime) -> tuple[str, str | None]:
    """Ultima lectura de la estacion desde `desde`, o None.

    Dos pasos: (1) hay alguna fila de esa estacion? Es rapido siempre. (2) solo
    si la hay, cual es la ultima dentro de la ventana; esa consulta ordenada se
    agota cuando la estacion no tiene filas recientes, por eso no se hace a ciegas.
    """
    try:
        alguna = soql(url_, timeout=25, reintentos=2, select="fechaobservacion", where=f"codigoestacion='{codigo}'", limit=1)
        if not alguna:
            return codigo, None
        r = soql(
            url_, timeout=40, reintentos=2, select="fechaobservacion",
            where=f"codigoestacion='{codigo}' AND fechaobservacion >= '{desde:%Y-%m-%dT%H:%M:%S}'",
            order="fechaobservacion DESC", limit=1,
        )
        return codigo, (r[0]["fechaobservacion"] if r else None)
    except ERRORES_RED:
        return codigo, None


def descargar_estacion(url_: str, codigo: str, desde: datetime, hasta: datetime, bloque_dias: int) -> list[dict]:
    filas: list[dict] = []
    ini = desde
    while ini < hasta:
        fin = min(ini + timedelta(days=bloque_dias), hasta)
        offset = 0
        while True:
            pagina = soql(
                url_,
                where=(f"codigoestacion='{codigo}' AND fechaobservacion >= '{ini:%Y-%m-%dT%H:%M:%S}' "
                       f"AND fechaobservacion < '{fin:%Y-%m-%dT%H:%M:%S}'"),
                limit=PAGINA, offset=offset,
            )
            filas.extend(pagina)
            if len(pagina) < PAGINA:
                break
            offset += PAGINA
        ini = fin
    return filas


def _paralelo(hilos: int, funcion, elementos):
    with ThreadPoolExecutor(hilos) as ex:
        return list(ex.map(funcion, elementos))


# ---------------------------------------------------------------------------
# Bloques de la ingesta
# ---------------------------------------------------------------------------

def ingestar_precipitacion(catalogo: pd.DataFrame, dias: int, hilos: int) -> dict:
    cand = candidatas_lluvia(catalogo)
    desde_sondeo = datetime.now() - timedelta(days=VENTANA_SONDEO_DIAS)
    print(f"2) Precipitacion: sondeando {len(cand)} estaciones candidatas (ultima lectura en {VENTANA_SONDEO_DIAS} dias)...", flush=True)
    ultimas = dict(_paralelo(hilos, lambda c: sondear(PRECIPITACION, c, desde_sondeo), cand))
    con_datos = {c: pd.Timestamp(u) for c, u in ultimas.items() if u}
    if not con_datos:
        print("   Ninguna estacion respondio con datos recientes (sin internet o servicio caido).")
        return {}
    hasta = max(con_datos.values()).to_pydatetime() + timedelta(minutes=1)
    desde = hasta - timedelta(days=dias)
    print(f"   {len(con_datos)} estaciones con datos. Lectura mas reciente: {hasta - timedelta(minutes=1):%Y-%m-%d %H:%M}")

    a_bajar = sorted(c for c, u in con_datos.items() if u >= desde)
    print(f"   Descargando lecturas crudas de {len(a_bajar)} estaciones ({desde:%Y-%m-%d} a {hasta:%Y-%m-%d})...", flush=True)

    def tarea(c):
        try:
            return c, descargar_estacion(PRECIPITACION, c, desde, hasta, BLOQUE_DIAS_LLUVIA), None
        except ERRORES_RED as e:
            return c, [], str(e)

    filas, fallos = [], []
    for i, (c, f, err) in enumerate(_paralelo(hilos, tarea, a_bajar), 1):
        filas.extend(f)
        if err:
            fallos.append(c)
        print(f"   [{i}/{len(a_bajar)}] {c}: {len(f):,} lecturas" + (f"  ERROR: {err}" if err else ""), flush=True)

    df = pd.DataFrame(filas)
    if df.empty:
        print("   No se descargo ninguna lectura de lluvia.")
        return {}
    df.to_parquet(BRONCE / "ideam_precipitacion.parquet", index=False)
    return {
        "desde": f"{desde:%Y-%m-%dT%H:%M:%S}", "hasta": f"{hasta:%Y-%m-%dT%H:%M:%S}",
        "estaciones_sondeadas": len(cand), "estaciones_con_datos_recientes": len(con_datos),
        "estaciones_descargadas": len(a_bajar), "estaciones_con_error": fallos, "lecturas": int(len(df)),
    }


def ingestar_variables(catalogo: pd.DataFrame, desde: datetime, hasta: datetime, hilos: int) -> dict:
    """Todas las demas series por estacion, en la misma ventana que la lluvia."""
    desde_sondeo = datetime.now() - timedelta(days=VENTANA_SONDEO_DIAS)
    pares = [(clave, cod) for clave in VARIABLES for cod in candidatas_variable(catalogo, clave)]
    print(f"3) Otras variables: sondeando {len(pares)} pares (variable, estacion)...", flush=True)
    sondeos = _paralelo(hilos, lambda p: (p, sondear(url(VARIABLES[p[0]]["dataset"]), p[1], desde_sondeo)[1]), pares)
    con_datos = {p: pd.Timestamp(u) for p, u in sondeos if u}
    a_bajar = sorted(p for p, u in con_datos.items() if u >= desde)
    print(f"   {len(con_datos)} pares con datos recientes; se descargan {len(a_bajar)} ({desde:%Y-%m-%d} a {hasta:%Y-%m-%d})...", flush=True)

    def tarea(p):
        clave, cod = p
        try:
            return p, descargar_estacion(url(VARIABLES[clave]["dataset"]), cod, desde, hasta, VARIABLES[clave]["bloque_dias"]), None
        except ERRORES_RED as e:
            return p, [], str(e)

    partes, fallos = [], {}
    stats = {clave: {"dataset": v["dataset"], "titulo": v["titulo"], "estaciones_sondeadas": 0, "estaciones_con_datos": 0,
                     "estaciones_descargadas": 0, "lecturas": 0, "estaciones": []} for clave, v in VARIABLES.items()}
    for clave, cod in pares:
        stats[clave]["estaciones_sondeadas"] += 1
    for p in con_datos:
        stats[p[0]]["estaciones_con_datos"] += 1

    for i, ((clave, cod), filas, err) in enumerate(_paralelo(hilos, tarea, a_bajar), 1):
        if err:
            fallos.setdefault(clave, []).append(cod)
        if filas:
            d = pd.DataFrame(filas)
            d["variable"] = clave
            partes.append(d)
            stats[clave]["estaciones_descargadas"] += 1
            stats[clave]["lecturas"] += len(d)
            stats[clave]["estaciones"].append(cod)
        if i % 10 == 0 or i == len(a_bajar):
            print(f"   [{i}/{len(a_bajar)}] descargados", flush=True)

    if partes:
        pd.concat(partes, ignore_index=True).to_parquet(BRONCE / "ideam_variables.parquet", index=False)
    for clave, s in stats.items():
        print(f"   {s['titulo']:24s} {s['estaciones_con_datos']:2d} estaciones con datos, {s['lecturas']:,} lecturas")
    for clave, s in stats.items():
        if clave in fallos:
            s["estaciones_con_error"] = fallos[clave]
    return stats


def _contiene_guajira(serie: pd.Series) -> pd.Series:
    return serie.fillna("").map(lambda t: "GUAJIRA" in sin_tildes(t).upper())


def ingestar_tablas(hilos: int) -> dict:
    """Radiacion (promedios), normales climatologicas y flujo de las ultimas horas."""
    print("4) Tablas complementarias (radiacion, normales, ultimas horas)...", flush=True)
    out: dict = {}

    rad = pd.DataFrame(soql(url(DATASET_RADIACION), limit=5000))
    if not rad.empty:
        rad = rad[_contiene_guajira(rad["departamento"])]
        rad.to_csv(BRONCE / "ideam_radiacion.csv", index=False)
    out["radiacion"] = {"dataset": DATASET_RADIACION, "filas": int(len(rad)), "descripcion": descripcion_conjunto(DATASET_RADIACION)}
    print(f"   Radiacion: {len(rad)} registros en La Guajira")

    nor = pd.DataFrame(soql(url(DATASET_NORMALES), where="upper(departamento) like '%GUAJIRA%'", limit=PAGINA))
    if not nor.empty:
        nor.to_csv(BRONCE / "ideam_normales.csv", index=False)
    out["normales"] = {"dataset": DATASET_NORMALES, "filas": int(len(nor)), "descripcion": descripcion_conjunto(DATASET_NORMALES)}
    print(f"   Normales climatologicas: {len(nor)} filas")

    ult = pd.DataFrame(soql(url(DATASET_ULTIMAS_HORAS), where="upper(departamento) like '%GUAJIRA%'", limit=PAGINA))
    if not ult.empty:
        ult.to_parquet(BRONCE / "ideam_ultimas_horas.parquet", index=False)
        out["ultimas_horas"] = {
            "dataset": DATASET_ULTIMAS_HORAS, "filas": int(len(ult)), "estaciones": int(ult["codigoestacion"].nunique()),
            "desde": str(ult["fechaobservacion"].min()), "hasta": str(ult["fechaobservacion"].max()),
        }
    else:
        out["ultimas_horas"] = {"dataset": DATASET_ULTIMAS_HORAS, "filas": 0}
    print(f"   Ultimas horas: {len(ult):,} lecturas")
    return out


# ---------------------------------------------------------------------------

def _leer_meta() -> dict:
    ruta = BRONCE / "ideam_meta.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Descarga clima real del IDEAM (datos abiertos) a Bronce.")
    ap.add_argument("--dias", type=int, default=30, help="dias de historia hasta la lectura mas reciente (30)")
    ap.add_argument("--hilos", type=int, default=6, help="descargas en paralelo (6)")
    ap.add_argument("--solo", nargs="+", choices=["precipitacion", "variables", "tablas"],
                    help="corre solo esos bloques (por defecto, todos). 'variables' reutiliza la ventana de la ultima descarga.")
    args = ap.parse_args()
    bloques = set(args.solo or ["precipitacion", "variables", "tablas"])
    asegurar_directorios()
    t0 = time.time()
    meta = _leer_meta()

    print("1) Catalogo de estaciones (IDEAM, datos.gov.co)...", flush=True)
    catalogo = descargar_catalogo()
    catalogo.to_csv(BRONCE / "ideam_estaciones.csv", index=False)
    print(f"   {len(catalogo)} estaciones en {DEPARTAMENTO_CATALOGO}: {catalogo['estado'].value_counts().to_dict()}")

    if "precipitacion" in bloques:
        r = ingestar_precipitacion(catalogo, args.dias, args.hilos)
        if not r:
            return 1
        meta.update(r)
    if "variables" in bloques:
        if "desde" not in meta:
            print("   Falta la ventana de fechas: corre primero el bloque 'precipitacion'.")
            return 1
        meta["variables"] = ingestar_variables(
            catalogo, datetime.fromisoformat(meta["desde"]), datetime.fromisoformat(meta["hasta"]), args.hilos)
    if "tablas" in bloques:
        meta["tablas"] = ingestar_tablas(args.hilos)

    meta.update({
        "fuente": "IDEAM - datos.gov.co", "licencia": "CC BY-SA 4.0",
        "descargado_en": datetime.now().isoformat(timespec="seconds"),
    })
    (BRONCE / "ideam_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nListo en {time.time() - t0:.0f} s. Bronce actualizado en data/bronze/ (ideam_*).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
