"""Indicadores sociales y de riesgo por municipio: Plata -> Oro (lo que consume el mapa).

Entradas (Plata): municipios.geojson, indicadores_censo2018.parquet, irca_anual.parquet, seguridad_municipio_mensual.parquet,
                  emergencias.parquet, resguardos.geojson, areas_protegidas_runap.geojson y sus proveniencias. Las que falten
                  quedan vacias: cada fuente es opcional.
Salida (Oro):     data/gold/indicadores_municipio.json

Para cada municipio (y el departamento, codigo 44):
  * censo 2018: poblacion, % rural disperso, % indigena y afro, IPM, NBI y sus componentes, miseria, deficit habitacional,
    hogares sin acueducto; PDET.
  * IRCA por ano y el ultimo.
  * territorio: km2 y % del municipio en resguardos indigenas y en areas protegidas; pueblos.
  * seguridad: victimas por mes de cada delito (desde PRIMER_MES) y resumen de 12 meses con tasa por 100.000 habitantes
    (base: poblacion del censo 2018, la unica oficial por municipio en este piloto).
  * emergencias: por ano y por tipo, personas afectadas y las ultimas.
Ademas, `indicadores`: la lista de lo que el mapa puede pintar, con unidad, fuente, cortes de la escala y si cambia con el tiempo.

Uso:  python -m oro.indicadores
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from comun.config import CRS_METRICO, ORO, PLATA, asegurar_directorios
from comun.serializacion import escribir_json, leer_proveniencia

PRIMER_MES = "2016-01"          # mismos anos que la lluvia de CHIRPS en el mapa
CENSO = ("poblacion_2018", "poblacion_rural_dispersa", "pct_rural_disperso", "indigenas", "pct_indigena", "afro", "pct_afro", "ipm", "nbi",
         "nbi_vivienda", "nbi_servicios", "nbi_hacinamiento", "nbi_inasistencia", "nbi_dependencia", "miseria",
         "deficit_habitacional", "hogares_sin_acueducto")
DELITOS = {"homicidio": "Homicidio", "extorsion": "Extorsión", "secuestro": "Secuestro", "terrorismo": "Terrorismo", "masacres": "Masacres",
           "voladura_oleoductos": "Voladura de oleoductos", "voladura_puentes_vias": "Voladura de puentes y vías",
           "pirateria_terrestre": "Piratería terrestre", "invasion_tierras": "Invasión de tierras",
           "delitos_ambientales": "Delitos ambientales", "afectacion_fuerza_publica": "Afectación de la fuerza pública"}

# Lo que el mapa puede pintar. `valor`: donde esta el numero dentro de cada municipio. Cortes: 4 limites, 5 clases.
INDICADORES = [
    {"id": "ipm", "nombre": "Pobreza multidimensional", "unidad": "% de personas", "grupo": "Pobreza", "fuente": "DANE, censo 2018",
     "valor": "censo.ipm", "cortes": [35, 45, 60, 80], "descripcion": "Personas con privaciones en al menos un tercio de 15 indicadores (educación, niñez, trabajo, salud, vivienda)."},
    {"id": "nbi", "nombre": "Necesidades básicas insatisfechas", "unidad": "% de personas", "grupo": "Pobreza", "fuente": "DANE, censo 2018",
     "valor": "censo.nbi", "cortes": [20, 35, 50, 70], "descripcion": "Personas con al menos una necesidad sin cubrir: vivienda, servicios, hacinamiento, inasistencia escolar o dependencia económica."},
    {"id": "miseria", "nombre": "Miseria", "unidad": "% de personas", "grupo": "Pobreza", "fuente": "DANE, censo 2018",
     "valor": "censo.miseria", "cortes": [10, 20, 35, 50], "descripcion": "Personas con dos o más necesidades básicas insatisfechas."},
    {"id": "hogares_sin_acueducto", "nombre": "Hogares sin acueducto", "unidad": "% de hogares", "grupo": "Servicios", "fuente": "DANE, censo 2018",
     "valor": "censo.hogares_sin_acueducto", "cortes": [15, 30, 50, 70], "descripcion": "Componente de acueducto del déficit habitacional."},
    {"id": "pct_indigena", "nombre": "Población indígena", "unidad": "% de la población", "grupo": "Población", "fuente": "DANE, censo 2018",
     "valor": "censo.pct_indigena", "cortes": [10, 30, 50, 80], "descripcion": "Personas que se reconocen indígenas. Indica dónde aplica la consulta previa y el enfoque diferencial; no es una amenaza."},
    {"id": "pct_resguardo", "nombre": "Territorio en resguardo", "unidad": "% del área", "grupo": "Territorio", "fuente": "ANT",
     "valor": "territorio.pct_resguardo", "cortes": [5, 20, 50, 80], "descripcion": "Parte del municipio dentro de resguardos indígenas formalizados."},
    {"id": "pct_area_protegida", "nombre": "Territorio en áreas protegidas", "unidad": "% del área", "grupo": "Territorio", "fuente": "RUNAP",
     "valor": "territorio.pct_area_protegida", "cortes": [1, 5, 15, 30], "descripcion": "Parte del municipio en áreas protegidas (nacionales, regionales o privadas)."},
    {"id": "homicidio", "nombre": "Homicidios", "unidad": "por 100.000 hab., 12 meses", "grupo": "Seguridad", "fuente": "Ministerio de Defensa",
     "valor": "tasa:homicidio", "temporal": True, "cortes": [10, 25, 40, 60], "descripcion": "Víctimas de homicidio en los 12 meses que terminan en el mes elegido, por 100.000 habitantes (población del censo 2018)."},
    {"id": "extorsion", "nombre": "Extorsión", "unidad": "por 100.000 hab., 12 meses", "grupo": "Seguridad", "fuente": "Ministerio de Defensa",
     "valor": "tasa:extorsion", "temporal": True, "cortes": [5, 10, 20, 40], "descripcion": "Denuncias de extorsión en los 12 meses que terminan en el mes elegido, por 100.000 habitantes."},
    {"id": "emergencias", "nombre": "Emergencias atendidas", "unidad": "emergencias", "grupo": "Desastres", "fuente": "UNGRD",
     "valor": "emergencias.total", "cortes": [5, 15, 30, 60], "descripcion": "Emergencias reportadas a la UNGRD (2019, 2020 y 2023 en adelante): incendios forestales, inundaciones, vendavales, sequía."},
    {"id": "irca", "nombre": "Riesgo en la calidad del agua (IRCA)", "unidad": "IRCA, último año", "grupo": "Servicios", "fuente": "INS",
     "valor": "irca.ultimo.valor", "cortes": [5, 14, 35, 80], "descripcion": "0-5 sin riesgo, 5-14 bajo, 14-35 medio, 35-80 alto, más de 80 inviable sanitariamente. Solo mide donde hay sistema de suministro."},
]


def _r(x, nd=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def _lee(nombre):
    ruta = PLATA / nombre
    if not ruta.exists():
        return None
    return gpd.read_file(ruta) if ruta.suffix == ".geojson" else pd.read_parquet(ruta)


def territorio(mun: gpd.GeoDataFrame, resg, ap) -> dict:
    out = {c: {"km2": _r(a, 1)} for c, a in zip(mun["codigo"], mun.to_crs(CRS_METRICO).area / 1e6)}
    out["44"] = {"km2": _r(sum(v["km2"] for v in out.values()), 1)}
    mm = mun[["codigo", "geometry"]].to_crs(CRS_METRICO)
    for nombre, capa in (("resguardo", resg), ("area_protegida", ap)):
        if capa is None or capa.empty:
            continue
        c = capa.to_crs(CRS_METRICO)
        disuelto = gpd.GeoDataFrame(geometry=[c.geometry.union_all()], crs=CRS_METRICO)   # sin contar dos veces lo que se solapa
        cruce = gpd.overlay(mm, disuelto, how="intersection", keep_geom_type=True)
        km2 = dict(zip(cruce["codigo"], cruce.area / 1e6))
        cuantos = gpd.sjoin(c[["geometry"]], mm, predicate="intersects")["codigo"].value_counts()
        for cod, v in out.items():
            k = sum(km2.values()) if cod == "44" else km2.get(cod, 0.0)
            v[f"{nombre}_km2"] = _r(k, 1)
            v[f"pct_{nombre}"] = _r(k / v["km2"] * 100 if v["km2"] else None, 1)
            v[f"{nombre}s_n"] = int(len(capa)) if cod == "44" else int(cuantos.get(cod, 0))
        if nombre == "resguardo":
            por_mun = gpd.sjoin(c[["pueblo", "geometry"]], mm, predicate="intersects")
            for cod, v in out.items():
                sel = por_mun if cod == "44" else por_mun[por_mun["codigo"] == cod]
                v["pueblos"] = sorted(sel["pueblo"].dropna().unique().tolist())
    return out


def seguridad(seg: pd.DataFrame, poblacion: dict) -> tuple[list[str], dict]:
    seg = seg.assign(mes=pd.to_datetime(seg["mes"]))
    hasta = seg["mes"].max()
    meses = pd.date_range(PRIMER_MES, hasta, freq="MS")
    depto = seg.groupby(["mes", "delito"], as_index=False)[["casos", "victimas"]].sum().assign(codigo="44")
    todo = pd.concat([seg, depto], ignore_index=True)
    out: dict = {}
    for cod, g in todo.groupby("codigo"):
        serie, resumen = {}, {}
        pob = poblacion.get(cod)
        for d in DELITOS:
            s = g[g["delito"] == d].set_index("mes")["victimas"]
            completa = s.reindex(pd.date_range(min(s.index.min(), meses[0]) if len(s) else meses[0], hasta, freq="MS"), fill_value=0)
            serie[d] = [int(v) for v in completa.reindex(meses, fill_value=0).values]
            u12, a12 = int(completa.iloc[-12:].sum()), int(completa.iloc[-24:-12].sum())
            resumen[d] = {"ultimos_12m": u12, "12m_anteriores": a12, "tasa_12m": _r(u12 / pob * 1e5 if pob else None, 1),
                          "total_desde_2003": int(s.sum())}
        out[cod] = {"serie": serie, "resumen": resumen}
    return [m.strftime("%Y-%m") for m in meses], out


def emergencias(em: pd.DataFrame) -> dict:
    em = em.assign(fecha=pd.to_datetime(em["fecha"]))
    out = {}
    grupos = list(em.groupby("codigo")) + [("44", em)]
    for cod, g in grupos:
        ult = g.sort_values("fecha", ascending=False).head(8)
        out[cod] = {
            "total": int(len(g)), "personas": int(g["personas"].sum()), "fallecidos": int(g["fallecidos"].sum()),
            "viviendas": int(g["viviendas_destruidas"].sum() + g["viviendas_averiadas"].sum()), "hectareas": int(g["hectareas"].sum()),
            "por_anio": {str(a): int(n) for a, n in g["anio"].value_counts().sort_index().items()},
            "por_tipo": {t: int(n) for t, n in g["tipo"].value_counts().items()},
            "ultimas": [{"fecha": f.strftime("%Y-%m-%d"), "tipo": t, "evento": e.capitalize(), "personas": int(p)}
                        for f, t, e, p in zip(ult["fecha"], ult["tipo"], ult["evento"], ult["personas"])],
        }
    return out


def construir() -> dict:
    mun = _lee("municipios.geojson")
    censo, irca, seg, em = _lee("indicadores_censo2018.parquet"), _lee("irca_anual.parquet"), _lee("seguridad_municipio_mensual.parquet"), _lee("emergencias.parquet")
    resg, ap = _lee("resguardos.geojson"), _lee("areas_protegidas_runap.geojson")
    nombres = {**dict(zip(mun["codigo"], mun["nombre"])), "44": "La Guajira"}
    zonas: dict = {c: {"codigo": c, "nombre": n} for c, n in nombres.items()}

    poblacion = {}
    if censo is not None:
        for _, f in censo.iterrows():
            z = zonas.get(f["codigo"])
            if z is None:
                continue
            z["censo"] = {c: _r(f.get(c), 2 if c.startswith(("pct", "nbi", "ipm")) else 1) for c in CENSO if c in censo}
            z["pdet"] = bool(f.get("pdet")) if f.get("pdet") is not None else False
            z["subregion_pdet"] = f.get("subregion_pdet") if isinstance(f.get("subregion_pdet"), str) else None
            poblacion[f["codigo"]] = f.get("poblacion_2018")
    if irca is not None:
        for cod, g in irca.groupby("codigo"):
            if cod in zonas:
                g = g.sort_values("anio")
                u = g.dropna(subset=["irca"]).iloc[-1] if g["irca"].notna().any() else None
                zonas[cod]["irca"] = {"anios": g["anio"].tolist(), "valores": [_r(v) for v in g["irca"]],
                                      "ultimo": {"anio": int(u["anio"]), "valor": _r(u["irca"]), "nivel": u["nivel"]} if u is not None else None}
    for cod, t in territorio(mun, resg, ap).items():
        zonas[cod]["territorio"] = t
    meses = []
    if seg is not None and len(seg):
        meses, s = seguridad(seg, poblacion)
        for cod, v in s.items():
            if cod in zonas:
                zonas[cod]["seguridad"] = v
    if em is not None and len(em):
        for cod, v in emergencias(em).items():
            if cod in zonas:
                zonas[cod]["emergencias"] = v

    fuentes = {}
    for f in ("social", "seguridad", "emergencias", "resguardos", "runap"):
        try:
            b = leer_proveniencia(f)["bronce"]
            fuentes[f] = {"fuente": b["fuente"], "licencia": b["licencia"], "descargado_en": b["descargado_en"]}
        except FileNotFoundError:
            pass
    disponibles = {"censo": censo is not None, "irca": irca is not None, "tasa": seg is not None, "emergencias": em is not None,
                   "territorio": resg is not None or ap is not None}
    indicadores = [i for i in INDICADORES if disponibles.get(i["valor"].split(".")[0].split(":")[0], True)]
    return {
        "metadata": {"fuente": "; ".join(v["fuente"] for v in fuentes.values()), "fuentes": fuentes,
                     "licencia": "Datos abiertos (ver cada fuente)",
                     "descargado_en": max((v["descargado_en"] for v in fuentes.values()), default=None),
                     "meses": meses, "delitos": DELITOS,
                     "poblacion_base": "Censo 2018 (DANE): las tasas por 100.000 habitantes usan esa población."},
        "indicadores": indicadores,
        "departamento": zonas.pop("44"),
        "municipios": zonas,
    }


def main() -> int:
    asegurar_directorios()
    if not (PLATA / "municipios.geojson").exists():
        print("Falta data/silver/municipios.geojson: corre primero plata.municipios")
        return 1
    oro = construir()
    escribir_json(ORO / "indicadores_municipio.json", oro)
    d = oro["departamento"]
    print(f"Oro de indicadores generado: {len(oro['municipios'])} municipios, {len(oro['indicadores'])} indicadores para el mapa, "
          f"{len(oro['metadata']['meses'])} meses de seguridad")
    if "censo" in d:
        print(f"  La Guajira: {d['censo'].get('poblacion_2018'):,.0f} hab. (2018), IPM {d['censo'].get('ipm')} %, indígena {d['censo'].get('pct_indigena')} %")
    if "seguridad" in d:
        h = d["seguridad"]["resumen"]["homicidio"]
        print(f"  Homicidios últimos 12 meses: {h['ultimos_12m']} (tasa {h['tasa_12m']} por 100.000; 12 meses anteriores: {h['12m_anteriores']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
