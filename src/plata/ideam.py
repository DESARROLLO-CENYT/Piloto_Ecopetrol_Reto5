"""
Bronce -> Plata del clima real del IDEAM (datos.gov.co).

Entradas (Bronce): data/bronze/ideam_*.csv|parquet y ideam_meta.json.
Salidas (Plata):   data/silver/ideam_estaciones.geojson, ideam_precip_diaria.parquet, ideam_variables_horaria.parquet,
                   ideam_variables_diaria.parquet, ideam_ultimas_horas.parquet, ideam_radiacion.parquet,
                   ideam_normales.parquet, reporte_calidad_ideam.csv, proveniencia_ideam.json.

Limpieza:
  * Tipos: numeros y fechas; codigo de estacion de 10 digitos; unidades normalizadas.
  * Cada lectura se clasifica por su SENSOR, no por el conjunto de donde vino:
    el conjunto "Humedad" trae tambien humedad del suelo, y el de temperatura
    puede traer temperatura del suelo. Se descartan los sensores que no usamos.
  * Deduplicacion por (estacion, variable, marca de tiempo): la fuente repite
    filas (varios canales del mismo sensor, cargas repetidas), y sumar o
    promediar duplicados distorsiona los resultados.
  * Rango fisico por variable: lo que cae fuera (o es un centinela como -999)
    se descarta.
  * Agregacion diaria por estacion y variable: media, minimo, maximo, lecturas y
    horas con dato. La direccion del viento se promedia como vector (350 y 10
    grados dan 0, no 180). La lluvia se SUMA.

Supuestos a tener presentes: `valorobservado` de lluvia son los mm caidos en el
intervalo de la lectura; las unidades de las normales no vienen en la tabla y
se asignan las habituales del IDEAM.
"""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd

from comun.config import BBOX_GUAJIRA, BRONCE, PLATA, asegurar_directorios
from comun.ideam import VARIABLES_META, mapear_sensor, normalizar_unidad, promedio_circular, sin_tildes
from comun.serializacion import escribir_proveniencia

LIMITE_MM_LECTURA = 200.0     # mm en una sola lectura: por encima se considera error
MARGEN_BBOX = 0.6             # grados: tolerancia alrededor de la caja de La Guajira

# Parametro de las normales -> (clave interna, unidad habitual del IDEAM)
NORMALES_PARAMETROS = {
    "PRECIPITACION": ("precipitacion", "mm"), "TEMPERATURA MEDIA": ("temperatura_media", "°C"),
    "TEMPERATURA MAXIMA": ("temperatura_max", "°C"), "TEMPERATURA MINIMA": ("temperatura_min", "°C"),
    "HUMEDAD RELATIVA": ("humedad_relativa", "%"), "BRILLO SOLAR": ("brillo_solar", "h"),
    "EVAPORACION": ("evaporacion", "mm"), "No. DE DIAS CON LLUVIA": ("dias_lluvia", "días"),
}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _leer_opcional(ruta, lector):
    return lector(ruta) if ruta.exists() else None


def cargar_bronce() -> dict:
    return {
        "est": pd.read_csv(BRONCE / "ideam_estaciones.csv", dtype=str),
        "lec": pd.read_parquet(BRONCE / "ideam_precipitacion.parquet"),
        "var": _leer_opcional(BRONCE / "ideam_variables.parquet", pd.read_parquet),
        "rad": _leer_opcional(BRONCE / "ideam_radiacion.csv", lambda p: pd.read_csv(p, dtype=str)),
        "nor": _leer_opcional(BRONCE / "ideam_normales.csv", lambda p: pd.read_csv(p, dtype=str)),
        "ult": _leer_opcional(BRONCE / "ideam_ultimas_horas.parquet", pd.read_parquet),
        "meta": json.loads((BRONCE / "ideam_meta.json").read_text(encoding="utf-8")),
    }


# ---------------------------------------------------------------------------
# Estaciones y lluvia
# ---------------------------------------------------------------------------

def limpiar_estaciones(est: pd.DataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    rep = {"estaciones_bronce": len(est)}
    est = est.copy()
    est["codigo"] = est["codigo"].str.zfill(10)
    for c in ("latitud", "longitud", "altitud"):
        est[c] = pd.to_numeric(est[c], errors="coerce")
    b = BBOX_GUAJIRA
    dentro = (
        est["latitud"].between(b["lat_min"] - MARGEN_BBOX, b["lat_max"] + MARGEN_BBOX)
        & est["longitud"].between(b["lon_min"] - MARGEN_BBOX, b["lon_max"] + MARGEN_BBOX)
    )
    rep["estaciones_fuera_de_la_caja"] = int((~dentro).sum())
    est = est[dentro].drop(columns=["ubicaci_n"], errors="ignore")
    # el catalogo del portal llega con filas repetidas (hasta 3 copias de la misma estacion) y a veces con copias que se
    # contradicen en el estado (una "Activa" y otra "Suspendida"): se deja una por codigo y se cuentan ambas cosas
    rep["estaciones_con_estado_contradictorio"] = int((est.groupby("codigo")["estado"].nunique() > 1).sum())
    antes = len(est)
    est = est.drop_duplicates("codigo")
    rep["estaciones_duplicadas_removidas"] = antes - len(est)
    # "LA PAULINA - AUT [15065040]" -> "La Paulina": se quita el codigo entre corchetes,
    # el sufijo "- AUT" (la tecnologia ya esta en otra columna) y los espacios repetidos
    est["nombre"] = (
        est["nombre"].str.replace(r"\s*\[\d+\]\s*$", "", regex=True)
        .str.replace(r"[\s-]+$", "", regex=True)
        .str.replace(r"(?:\s*-\s*|\s+)AUT\.?\s*$", "", regex=True, case=False)
        .str.replace(r"[\s-]+$", "", regex=True)
        .str.replace(r"\s+", " ", regex=True).str.strip().str.title()
    )
    gdf = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est["longitud"], est["latitud"]), crs="EPSG:4326")
    rep["estaciones_plata"] = len(gdf)
    return gdf, rep


def limpiar_lecturas(lec: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rep = {"lecturas_bronce": len(lec)}
    lec = lec.copy()
    lec["codigoestacion"] = lec["codigoestacion"].str.zfill(10)
    lec["fecha_hora"] = pd.to_datetime(lec["fechaobservacion"], errors="coerce")
    lec["mm"] = pd.to_numeric(lec["valorobservado"], errors="coerce")

    invalidas = lec["fecha_hora"].isna() | lec["mm"].isna()
    rep["lecturas_sin_fecha_o_valor"] = int(invalidas.sum())
    lec = lec[~invalidas]

    imposibles = (lec["mm"] < 0) | (lec["mm"] > LIMITE_MM_LECTURA)
    rep["lecturas_imposibles"] = int(imposibles.sum())
    lec = lec[~imposibles]

    antes = len(lec)
    lec = lec.groupby(["codigoestacion", "fecha_hora"], as_index=False)["mm"].max()
    rep["duplicados_removidos"] = antes - len(lec)
    rep["lecturas_plata"] = len(lec)

    lec["dia"] = lec["fecha_hora"].dt.normalize()
    lec["hora"] = lec["fecha_hora"].dt.floor("h")
    diaria = (
        lec.groupby(["codigoestacion", "dia"])
        .agg(mm=("mm", "sum"), lecturas=("mm", "size"), horas_con_dato=("hora", "nunique"))
        .reset_index()
    )
    diaria["mm"] = diaria["mm"].round(1)
    return lec, diaria, rep


# ---------------------------------------------------------------------------
# Otras variables por estacion
# ---------------------------------------------------------------------------

def _limpiar_series(df: pd.DataFrame, prefijo: str) -> tuple[pd.DataFrame, dict]:
    """Nucleo comun a las series por estacion y al flujo de ultimas horas: clasifica por sensor,
    quita invalidos, fuera de rango y duplicados. Devuelve lecturas limpias con columna `var`."""
    rep: dict = {f"{prefijo}_bronce": len(df)}
    d = df.copy()
    d["codigoestacion"] = d["codigoestacion"].astype(str).str.zfill(10)
    d["fecha_hora"] = pd.to_datetime(d["fechaobservacion"], errors="coerce")
    d["valor"] = pd.to_numeric(d["valorobservado"], errors="coerce")
    d["var"] = d["descripcionsensor"].fillna("").map(mapear_sensor)

    if "variable" in d.columns:  # conjunto de origen (solo en las series descargadas por conjunto)
        rep[f"{prefijo}_reasignadas_por_sensor"] = int(((d["var"].notna()) & (d["var"] != d["variable"])).sum())
    rep[f"{prefijo}_sensor_descartado"] = int(d["var"].isna().sum())
    d = d[d["var"].notna()]

    sin_dato = d["fecha_hora"].isna() | d["valor"].isna()
    rep[f"{prefijo}_sin_fecha_o_valor"] = int(sin_dato.sum())
    d = d[~sin_dato].copy()

    # Nivel del rio: el sensor automatico viene rotulado "cm" pero sus valores estan en metros
    # (coinciden con la serie historica en m de la misma estacion); solo el limnimetro de las 6 y 18 h
    # entrega centimetros de verdad. Se lleva todo a metros ANTES de validar rangos.
    es_nivel = d["var"].isin(["nivel_rio", "nivel_mar"]) & d["unidadmedida"].fillna("").str.lower().eq("cm")
    es_limnimetro = es_nivel & d["descripcionsensor"].fillna("").map(sin_tildes).str.lower().str.contains("limnimetro")
    d.loc[es_limnimetro, "valor"] = d.loc[es_limnimetro, "valor"] / 100
    d.loc[es_nivel, "unidadmedida"] = "m"

    lo = d["var"].map(lambda v: VARIABLES_META[v]["rango"][0])
    hi = d["var"].map(lambda v: VARIABLES_META[v]["rango"][1])
    fuera = (d["valor"] < lo) | (d["valor"] > hi)
    rep[f"{prefijo}_fuera_de_rango"] = int(fuera.sum())
    d = d[~fuera]

    d["unidad"] = d["unidadmedida"].map(normalizar_unidad)
    antes = len(d)
    d = (
        d.groupby(["codigoestacion", "var", "fecha_hora"], as_index=False)
        .agg(valor=("valor", "mean"), unidad=("unidad", "first"))
    )
    rep[f"{prefijo}_duplicados_removidos"] = antes - len(d)
    rep[f"{prefijo}_plata"] = len(d)
    return d, rep


def limpiar_variables(bruto: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Devuelve (lecturas limpias, agregado diario, reporte)."""
    lec, rep = _limpiar_series(bruto, "var")
    lec["dia"] = lec["fecha_hora"].dt.normalize()
    lec["hora"] = lec["fecha_hora"].dt.floor("h")

    diaria = (
        lec.groupby(["codigoestacion", "var", "dia"])
        .agg(media=("valor", "mean"), minimo=("valor", "min"), maximo=("valor", "max"),
             lecturas=("valor", "size"), horas_con_dato=("hora", "nunique"), unidad=("unidad", "first"))
        .reset_index()
    )
    # la direccion se promedia como vector y no tiene minimo/maximo con sentido
    es_dir = diaria["var"] == "viento_dir"
    if es_dir.any():
        circ = (lec[lec["var"] == "viento_dir"].groupby(["codigoestacion", "dia"])["valor"]
                .apply(lambda s: promedio_circular(s.tolist())).rename("circ").reset_index())
        diaria = diaria.merge(circ, on=["codigoestacion", "dia"], how="left")
        diaria.loc[es_dir, "media"] = diaria.loc[es_dir, "circ"]
        diaria.loc[es_dir, ["minimo", "maximo"]] = np.nan
        diaria = diaria.drop(columns="circ")
    for c in ("media", "minimo", "maximo"):
        diaria[c] = diaria[c].round(2)
    return lec, diaria, rep


def limpiar_ultimas_horas(ult: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Flujo de las ultimas ~12 h; incluye lluvia (10 min), humedad y temperatura del suelo."""
    lec, rep = _limpiar_series(ult, "ult")
    return lec, rep


# ---------------------------------------------------------------------------
# Radiacion y normales
# ---------------------------------------------------------------------------

def _clave_nombre(texto: str) -> str:
    t = sin_tildes(texto).lower()
    t = "".join(c if c.isalnum() else " " for c in t)
    return " ".join(p for p in t.split() if p != "aut")


def limpiar_radiacion(rad: pd.DataFrame, estaciones: gpd.GeoDataFrame) -> pd.DataFrame:
    """Radiacion global media mensual y anual (Wh/m2 por dia), con el codigo de la estacion
    del catalogo cuando el nombre y el municipio coinciden."""
    d = rad.copy()
    for c in ["latitud", "longitud", "altitud", "promedio_anual", *MESES]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["estacion"] = d["estacion"].str.strip()
    d["tipo_de_estacion"] = d["tipo_de_estacion"].str.strip()
    cat = estaciones.assign(_n=estaciones["nombre"].map(_clave_nombre), _m=estaciones["municipio"].map(_clave_nombre))

    def buscar(fila) -> str | None:
        n, m = _clave_nombre(fila["estacion"]), _clave_nombre(fila["municipio"])
        cand = cat[(cat["_m"] == m) & (cat["_n"].str.startswith(n) | cat["_n"].apply(lambda x: n.startswith(x)))]
        return cand["codigo"].iloc[0] if len(cand) else None

    d["codigo"] = d.apply(buscar, axis=1)
    d["unidad"] = "Wh/m²/día"
    return d.drop_duplicates(["estacion", "municipio", "tipo_de_estacion"]).reset_index(drop=True)


def limpiar_normales(nor: pd.DataFrame) -> pd.DataFrame:
    """Normales de 30 anos por estacion y parametro; deja el periodo mas reciente disponible."""
    d = nor.rename(columns={"par_metro": "parametro", "c_digo": "codigo", "estaci_n": "estacion"}).copy()
    for c in [*MESES, "anual", "altitud_m", "latitud", "longitud"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d["codigo"] = pd.to_numeric(d["codigo"], errors="coerce").astype("Int64")
    d["parametro_clave"] = d["parametro"].map(lambda p: NORMALES_PARAMETROS.get(sin_tildes(str(p)).upper().strip(), (None, None))[0])
    d["unidad"] = d["parametro"].map(lambda p: NORMALES_PARAMETROS.get(sin_tildes(str(p)).upper().strip(), (None, None))[1])
    d = d[d["parametro_clave"].notna() & d["codigo"].notna()]
    d["_fin"] = d["periodo"].str.extract(r"-(\d{4})$")[0].astype(float)
    d = d.sort_values("_fin", ascending=False).drop_duplicates(["codigo", "parametro_clave"]).drop(columns="_fin")
    return d.reset_index(drop=True)


def main() -> None:
    asegurar_directorios()
    b = cargar_bronce()
    reporte: dict = {}

    estaciones, rep = limpiar_estaciones(b["est"])
    reporte.update(rep)
    _, diaria_lluvia, rep = limpiar_lecturas(b["lec"])
    reporte.update(rep)
    diaria_lluvia = diaria_lluvia[diaria_lluvia["codigoestacion"].isin(estaciones["codigo"])]
    reporte["estaciones_con_lluvia_diaria"] = int(diaria_lluvia["codigoestacion"].nunique())

    estaciones.to_file(PLATA / "ideam_estaciones.geojson", driver="GeoJSON")
    diaria_lluvia.to_parquet(PLATA / "ideam_precip_diaria.parquet", index=False)

    if b["var"] is not None and len(b["var"]):
        lec_var, diaria_var, rep = limpiar_variables(b["var"])
        reporte.update(rep)
        lec_var = lec_var[lec_var["codigoestacion"].isin(estaciones["codigo"])]
        diaria_var = diaria_var[diaria_var["codigoestacion"].isin(estaciones["codigo"])]
        lec_var.to_parquet(PLATA / "ideam_variables_horaria.parquet", index=False)   # Oro calcula el promedio de 24 h desde aqui
        diaria_var.to_parquet(PLATA / "ideam_variables_diaria.parquet", index=False)
        reporte["var_estaciones"] = int(diaria_var["codigoestacion"].nunique())
    if b["ult"] is not None and len(b["ult"]):
        ult, rep = limpiar_ultimas_horas(b["ult"])
        reporte.update(rep)
        ult = ult[ult["codigoestacion"].isin(estaciones["codigo"])]
        ult.to_parquet(PLATA / "ideam_ultimas_horas.parquet", index=False)
    if b["rad"] is not None and len(b["rad"]):
        rad = limpiar_radiacion(b["rad"], estaciones)
        rad.to_parquet(PLATA / "ideam_radiacion.parquet", index=False)
        reporte["radiacion_registros"] = int(len(rad))
        reporte["radiacion_con_estacion_en_catalogo"] = int(rad["codigo"].notna().sum())
    if b["nor"] is not None and len(b["nor"]):
        nor = limpiar_normales(b["nor"])
        nor.to_parquet(PLATA / "ideam_normales.parquet", index=False)
        reporte["normales_filas"] = int(len(nor))
        reporte["normales_estaciones"] = int(nor["codigo"].nunique())

    pd.DataFrame([reporte]).to_csv(PLATA / "reporte_calidad_ideam.csv", index=False)
    escribir_proveniencia("ideam", b["meta"], reporte)

    print("Plata del IDEAM generada")
    for k, v in reporte.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
