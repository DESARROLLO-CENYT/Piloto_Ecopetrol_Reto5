"""
Plata -> Oro del clima real del IDEAM: lo que consume el mapa.

Entradas (Plata): data/silver/ideam_*.parquet|geojson y proveniencia_ideam.json. Oro no lee Bronce.
Salidas (Oro):    data/gold/clima_estaciones.geojson y clima_radiacion.geojson.

  * Un punto por estacion con todo lo que mide: lluvia acumulada 7/14/30 dias, y para cada variable la ultima
    lectura, el promedio de 24 h, los extremos de 30 dias y la serie diaria; lo ultimo de las ultimas horas
    ("ahora"); la normal climatologica; y la radiacion media si la estacion la mide.
  * Un archivo aparte con los puntos de radiacion.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from comun.config import ORO, PLATA, asegurar_directorios
from comun.ideam import VARIABLES_META, promedio_circular, rumbo
from comun.serializacion import escribir_json, leer_proveniencia

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _num(x, nd: int = 1):
    """Numero redondeado, o None si es NaN (para JSON valido)."""
    if x is None:
        return None
    try:
        if np.isnan(x):
            return None
    except TypeError:
        return None
    return round(float(x), nd)



def _serie_variable(lec: pd.DataFrame, diaria: pd.DataFrame, cod: str, var: str, ventana: pd.DatetimeIndex) -> dict | None:
    gd = diaria[(diaria["codigoestacion"] == cod) & (diaria["var"] == var)]
    if gd.empty:
        return None
    serie = gd.set_index("dia").reindex(ventana)
    lecs = lec[(lec["codigoestacion"] == cod) & (lec["var"] == var)].sort_values("fecha_hora")
    ultima = lecs.iloc[-1]
    ult24 = lecs[lecs["fecha_hora"] > ultima["fecha_hora"] - pd.Timedelta(hours=24)]["valor"]
    es_dir = var == "viento_dir"
    prom24 = promedio_circular(ult24.tolist()) if es_dir else ult24.mean()
    media30 = promedio_circular(lecs["valor"].tolist()) if es_dir else lecs["valor"].mean()
    out = {
        "unidad": ultima["unidad"] or VARIABLES_META[var]["unidad"],
        "ultimo": _num(ultima["valor"], 2), "ultima_hora": ultima["fecha_hora"].isoformat(timespec="minutes"),
        "prom_24h": _num(prom24, 2), "media_30d": _num(media30, 2),
        "min_30d": None if es_dir else _num(lecs["valor"].min(), 2), "max_30d": None if es_dir else _num(lecs["valor"].max(), 2),
        "dias_con_dato": int(serie["media"].notna().sum()),
        "cobertura": round(float((serie["horas_con_dato"].fillna(0) / 24).mean()), 3),
        "serie": [{"dia": d.strftime("%Y-%m-%d"), "media": _num(r["media"], 2), "min": _num(r["minimo"], 2), "max": _num(r["maximo"], 2)}
                  for d, r in serie.iterrows()],
    }
    if es_dir:
        out["rumbo_ultimo"] = rumbo(ultima["valor"])
    return out


def _ahora(ult: pd.DataFrame | None, cod: str) -> dict:
    if ult is None or ult.empty:
        return {}
    g = ult[ult["codigoestacion"] == cod].sort_values("fecha_hora")
    out = {}
    for var, gv in g.groupby("var"):
        u = gv.iloc[-1]
        d = {"valor": _num(u["valor"], 2), "hora": u["fecha_hora"].isoformat(timespec="minutes"), "unidad": u["unidad"] or VARIABLES_META[var]["unidad"]}
        if var == "viento_dir":
            d["rumbo"] = rumbo(u["valor"])
        out[var] = d
    return out


def _normales(nor: pd.DataFrame | None, cod: str) -> dict:
    if nor is None or nor.empty:
        return {}
    g = nor[nor["codigo"] == int(cod)]
    return {r["parametro_clave"]: {"periodo": r["periodo"], "unidad": r["unidad"], "anual": _num(r["anual"], 1),
                                   "meses": [_num(r[m], 1) for m in MESES]} for _, r in g.iterrows()}


def construir_oro(estaciones, diaria_lluvia, lec_var, diaria_var, ult, nor, rad, meta) -> tuple[dict, dict]:
    hasta = pd.Timestamp(meta["hasta"]).normalize()
    ventana = pd.date_range(hasta - pd.Timedelta(days=29), hasta, freq="D")
    codigos = set(diaria_lluvia["codigoestacion"]) | (set(diaria_var["codigoestacion"]) if diaria_var is not None else set())
    features = []
    for cod in sorted(codigos):
        fila = estaciones[estaciones["codigo"] == cod]
        if fila.empty:
            continue
        e = fila.iloc[0]
        props = {
            "codigo": cod, "nombre": e["nombre"], "municipio": e["municipio"], "categoria": e["categoria"],
            "tecnologia": e["tecnologia"], "estado": e["estado"], "altitud": None if pd.isna(e["altitud"]) else float(e["altitud"]),
            "ultimo_dato": None, "dias_sin_dato": None, "mm_7d": None, "mm_14d": None, "mm_30d": None,
            "max_diario_mm": None, "dias_con_dato": 0, "cobertura": 0.0, "serie": [],
        }
        g = diaria_lluvia[diaria_lluvia["codigoestacion"] == cod]
        if not g.empty:
            serie = g.set_index("dia").reindex(ventana)
            mm = serie["mm"]
            ultimo = g["dia"].max()
            props.update({
                "ultimo_dato": ultimo.strftime("%Y-%m-%d"), "dias_sin_dato": int((hasta - ultimo).days),
                "mm_7d": round(float(mm.iloc[-7:].sum()), 1), "mm_14d": round(float(mm.iloc[-14:].sum()), 1),
                "mm_30d": round(float(mm.iloc[-30:].sum()), 1), "max_diario_mm": float(mm.max()),
                "dias_con_dato": int(mm.notna().sum()), "cobertura": round(float((serie["horas_con_dato"].fillna(0) / 24).mean()), 3),
                "serie": [{"dia": d.strftime("%Y-%m-%d"), "mm": None if pd.isna(v) else float(v)} for d, v in mm.items()],
            })
        variables = {}
        if diaria_var is not None:
            for var in sorted(diaria_var[diaria_var["codigoestacion"] == cod]["var"].unique()):
                s = _serie_variable(lec_var, diaria_var, cod, var, ventana)
                if s:
                    variables[var] = s
        props["variables"] = variables
        props["ahora"] = _ahora(ult, cod)
        props["normales"] = _normales(nor, cod)
        if rad is not None:
            r = rad[rad["codigo"] == cod]
            if len(r):
                r0 = r.iloc[0]
                props["radiacion"] = {"anual": _num(r0["promedio_anual"], 0), "meses": [_num(r0[m], 0) for m in MESES], "unidad": r0["unidad"]}
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(e["longitud"]), float(e["latitud"])]}, "properties": props})

    features.sort(key=lambda f: -(f["properties"]["mm_14d"] or 0))
    presentes = sorted({v for f in features for v in f["properties"]["variables"]} | ({"precipitacion"} if not diaria_lluvia.empty else set()))
    oro = {
        "type": "FeatureCollection",
        "metadata": {
            "fuente": meta.get("fuente"), "licencia": meta.get("licencia"), "descargado_en": meta.get("descargado_en"),
            "desde": ventana[0].strftime("%Y-%m-%d"), "hasta": hasta.strftime("%Y-%m-%d"),
            "mes_actual": int(hasta.month),
            "variables": {v: {"titulo": VARIABLES_META[v]["titulo"], "unidad": VARIABLES_META[v]["unidad"],
                              "estaciones": int(sum(1 for f in features if v in f["properties"]["variables"] or (v == "precipitacion" and f["properties"]["mm_14d"] is not None)))}
                          for v in presentes},
            "ahora_hasta": None if ult is None or ult.empty else ult["fecha_hora"].max().isoformat(timespec="minutes"),
        },
        "features": features,
    }

    rad_oro = {"type": "FeatureCollection", "features": []}
    if rad is not None:
        for _, r in rad.dropna(subset=["latitud", "longitud"]).iterrows():
            rad_oro["features"].append({
                "type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r["longitud"]), float(r["latitud"])]},
                "properties": {"estacion": r["estacion"], "municipio": r["municipio"], "tipo": r["tipo_de_estacion"], "altitud": _num(r["altitud"], 0),
                               "anual": _num(r["promedio_anual"], 0), "meses": [_num(r[m], 0) for m in MESES], "unidad": r["unidad"], "codigo": r["codigo"]},
            })
    return oro, rad_oro


def _leer_opcional(nombre: str):
    ruta = PLATA / nombre
    return pd.read_parquet(ruta) if ruta.exists() else None


def cargar_plata() -> dict:
    return {
        "estaciones": gpd.read_file(PLATA / "ideam_estaciones.geojson"),
        "diaria_lluvia": pd.read_parquet(PLATA / "ideam_precip_diaria.parquet"),
        "lec_var": _leer_opcional("ideam_variables_horaria.parquet"),
        "diaria_var": _leer_opcional("ideam_variables_diaria.parquet"),
        "ult": _leer_opcional("ideam_ultimas_horas.parquet"),
        "nor": _leer_opcional("ideam_normales.parquet"),
        "rad": _leer_opcional("ideam_radiacion.parquet"),
        "meta": leer_proveniencia("ideam")["bronce"],
    }


def main() -> None:
    asegurar_directorios()
    p = cargar_plata()
    oro, rad_oro = construir_oro(p["estaciones"], p["diaria_lluvia"], p["lec_var"], p["diaria_var"], p["ult"], p["nor"], p["rad"], p["meta"])
    escribir_json(ORO / "clima_estaciones.geojson", oro)
    escribir_json(ORO / "clima_radiacion.geojson", rad_oro)

    m = oro["metadata"]
    print("Oro del IDEAM generado")
    print(f"  ventana: {m['desde']} a {m['hasta']} | ultimas horas hasta: {m['ahora_hasta']}")
    for v, d in m["variables"].items():
        print(f"  {d['titulo']:24s} {d['estaciones']:2d} estaciones ({d['unidad']})")
    print(f"  estaciones en Oro: {len(oro['features'])} | puntos de radiacion: {len(rad_oro['features'])}")


if __name__ == "__main__":
    main()
