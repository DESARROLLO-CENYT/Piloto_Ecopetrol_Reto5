"""Riesgo de ejecucion por paquete y proyecto: Plata (+ contexto de Oro) -> Oro.

Entradas:
  Plata: riesgos.geojson (con la RAM), paquetes.geojson, cronograma.parquet (sinteticos); seguridad_municipio_mensual,
         emergencias, chirps_municipio_mensual, indicadores_censo2018, red_vial, reporte_calidad_resguardos (reales).
  Oro:   contexto_paquetes.csv (municipio del paquete, % en resguardo, consecuencia ambiental sugerida).
Salidas (Oro): ejecucion_paquetes.csv, ejecucion_proyectos.csv, ejecucion_riesgos.csv, ejecucion_resumen.json

Covariables del territorio de cada paquete (z = 0 en el promedio de La Guajira; ver parametros.yaml -> ejecucion):
  tasa_delitos_rel   ln((tasa del municipio + 1) / (tasa del departamento + 1)); delitos contra personas e infraestructura
                     de los ultimos 12 meses por 100.000 habitantes (sin homicidio)
  emergencias_rel    ln((emergencias por ano del municipio + 0,5) / (promedio por municipio + 0,5)), UNGRD
  anomalia_lluvia    |anomalia| media de los ultimos meses de CHIRPS en el municipio menos la del departamento (fraccion)
  en_resguardo       fraccion del paquete en resguardo menos la del departamento
  ipm_rel            (IPM del municipio - IPM del departamento) / IPM del departamento
  pdet               1 si el municipio es PDET, menos la fraccion de municipios PDET
  vias_tiempo_seco   fraccion de km de vias "solo en tiempo seco" a menos de radio_vias_km del paquete, menos la del departamento
Si falta una fuente, su covariable queda en 0 (neutra) y el resumen lo dice.

Uso:  python -m oro.ejecucion
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from comun.config import CRS_METRICO, ORO, PLATA, asegurar_directorios, cargar_parametros
from comun.serializacion import escribir_json
from modelo import ejecucion as m

DELITOS_CONTRA_PROYECTOS = ("extorsion", "secuestro", "terrorismo", "masacres", "voladura_oleoductos",
                            "voladura_puentes_vias", "pirateria_terrestre", "afectacion_fuerza_publica")
COVARIABLES = ("tasa_delitos_rel", "emergencias_rel", "anomalia_lluvia", "en_resguardo", "ipm_rel", "pdet", "vias_tiempo_seco")


def _lee(ruta):
    if not ruta.exists():
        return None
    return gpd.read_file(ruta) if ruta.suffix == ".geojson" else pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)


def covariables(paquetes: gpd.GeoDataFrame, ctx: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Una fila por paquete con las covariables z (y los valores crudos para mostrarlos). Fuentes de Plata."""
    z = pd.DataFrame(index=paquetes["id_paquete"])
    crudo = pd.DataFrame(index=paquetes["id_paquete"])
    mun = ctx.set_index("id_paquete")["codigo_municipio"].astype(str).str.zfill(5).reindex(z.index)
    usadas: dict[str, str] = {}
    censo = _lee(PLATA / "indicadores_censo2018.parquet")
    pob = censo.set_index("codigo")["poblacion_2018"] if censo is not None else None

    seg = _lee(PLATA / "seguridad_municipio_mensual.parquet")
    if seg is not None and pob is not None and len(seg):
        seg = seg[seg["delito"].isin(DELITOS_CONTRA_PROYECTOS)].assign(mes=lambda d: pd.to_datetime(d["mes"]))
        ult = seg[seg["mes"] > seg["mes"].max() - pd.DateOffset(months=12)]
        casos = ult.groupby("codigo")["casos"].sum()
        tasa_m = mun.map(lambda c: casos.get(c, 0) / pob.get(c, np.nan) * 1e5)
        tasa_d = casos.sum() / pob.get("44", np.nan) * 1e5
        crudo["tasa_delitos_100k"] = tasa_m.round(1)
        z["tasa_delitos_rel"] = np.log((tasa_m + 1) / (tasa_d + 1))
        usadas["tasa_delitos_rel"] = f"Ministerio de Defensa, 12 meses hasta {seg['mes'].max():%Y-%m}; departamento {tasa_d:.1f} por 100.000"

    em = _lee(PLATA / "emergencias.parquet")
    if em is not None and len(em):
        em = em[em["codigo"] != "44"]
        por_ano = em.groupby("codigo").size() / max(em["anio"].nunique(), 1)
        ref = por_ano.reindex([c for c in pob.index if c != "44"] if pob is not None else por_ano.index).fillna(0).mean()
        e_m = mun.map(lambda c: por_ano.get(c, 0.0))
        crudo["emergencias_por_ano"] = e_m.round(1)
        z["emergencias_rel"] = np.log((e_m + 0.5) / (ref + 0.5))
        usadas["emergencias_rel"] = f"UNGRD ({', '.join(str(a) for a in sorted(em['anio'].unique()))}); promedio {ref:.1f} por municipio y año"

    ch = _lee(PLATA / "chirps_municipio_mensual.parquet")
    if ch is not None and len(ch):
        ch = ch.assign(mes=pd.to_datetime(ch["mes"]))
        normal = ch[ch["mes"].dt.year.between(1991, 2020)].groupby([ch["codigo"], ch["mes"].dt.month])["mm"].mean()
        k = int(cfg.get("meses_anomalia_lluvia", 3))
        recientes = ch[ch["mes"] > ch["mes"].max() - pd.DateOffset(months=k)]
        an = recientes.apply(lambda r: abs(r["mm"] / normal.get((r["codigo"], r["mes"].month), np.nan) - 1)
                             if normal.get((r["codigo"], r["mes"].month), 0) > 0 else np.nan, axis=1)
        anom = recientes.assign(a=an).groupby("codigo")["a"].mean()
        a_m = mun.map(lambda c: anom.get(c, np.nan))
        crudo["anomalia_lluvia_pct"] = (a_m * 100).round(0)
        z["anomalia_lluvia"] = (a_m - anom.get("44", anom.mean())).fillna(0)
        usadas["anomalia_lluvia"] = f"CHIRPS, {k} meses hasta {ch['mes'].max():%Y-%m}; departamento {anom.get('44', np.nan) * 100:.0f} % de desviación"

    rep_r = _lee(PLATA / "reporte_calidad_resguardos.csv")
    if "pct_en_resguardo" in ctx:
        ref = float(rep_r.iloc[0]["pct_departamento_en_resguardo"]) / 100 if rep_r is not None else 0.0
        pr = ctx.set_index("id_paquete")["pct_en_resguardo"].reindex(z.index).fillna(0) / 100
        crudo["pct_en_resguardo"] = (pr * 100).round(0)
        z["en_resguardo"] = pr - ref
        usadas["en_resguardo"] = f"ANT; {ref * 100:.0f} % del departamento está en resguardo"
    if censo is not None and "ipm" in censo:
        ipm = censo.set_index("codigo")["ipm"]
        i_m = mun.map(lambda c: ipm.get(c, np.nan))
        crudo["ipm"] = i_m.round(1)
        z["ipm_rel"] = ((i_m - ipm.get("44")) / ipm.get("44")).fillna(0)
        usadas["ipm_rel"] = f"DANE censo 2018; departamento {ipm.get('44'):.1f} %"
        if "pdet" in censo:
            municipal = censo[censo["codigo"] != "44"]
            pdet = municipal.set_index("codigo")["pdet"].astype(bool)
            p_m = mun.map(lambda c: float(pdet.get(c, False)))
            crudo["pdet"] = p_m.astype(bool)
            z["pdet"] = p_m - pdet.mean()
            usadas["pdet"] = f"ART; {pdet.mean() * 100:.0f} % de los municipios son PDET"

    red = _lee(PLATA / "red_vial.geojson")
    if red is not None and len(red):
        rm = red.to_crs(CRS_METRICO)
        seco = rm["accesibilidad"].eq("Solo en tiempo seco")
        ref = float(rm[seco].length.sum() / rm.length.sum())
        radio = float(cfg.get("radio_vias_km", 10)) * 1000
        cent = paquetes.to_crs(CRS_METRICO).set_index("id_paquete").geometry.centroid
        fr = {}
        for p, c in cent.items():
            zona = c.buffer(radio)
            cerca = rm[rm.intersects(zona)]
            largo = cerca.geometry.intersection(zona).length
            fr[p] = float(largo[seco.loc[cerca.index]].sum() / largo.sum()) if largo.sum() > 0 else ref
        v = pd.Series(fr).reindex(z.index)
        crudo["vias_tiempo_seco_pct"] = (v * 100).round(0)
        z["vias_tiempo_seco"] = v - ref
        usadas["vias_tiempo_seco"] = f"INVIAS + IGAC; {ref * 100:.0f} % de los km del departamento son solo en tiempo seco"

    for c in COVARIABLES:
        if c not in z:
            z[c] = 0.0
    return z[list(COVARIABLES)].astype(float).round(4), {"fuentes": usadas, "crudo": crudo}


def cargar_entradas(cfg: dict | None = None) -> dict:
    """Todo lo que necesita el modelo, ya armado (lo usa tambien la API para los escenarios)."""
    cfg = cfg or cargar_parametros()["ejecucion"]
    riesgos = gpd.read_file(PLATA / "riesgos.geojson")
    paquetes = gpd.read_file(PLATA / "paquetes.geojson")
    cron = _lee(PLATA / "cronograma.parquet")
    ctx = pd.read_csv(ORO / "contexto_paquetes.csv", dtype={"codigo_municipio": str})
    info = paquetes[["id_paquete", "id_proyecto", "nombre", "ruta_critica"]].set_index("id_paquete")
    if cron is not None:
        info = info.join(cron.set_index("id_paquete")[["meses_restantes", "holgura_dias", "costo_dia_parada_usd", "presupuesto_usd", "avance"]])
    else:
        info = info.assign(meses_restantes=np.nan, holgura_dias=0, costo_dia_parada_usd=0, presupuesto_usd=np.nan, avance=np.nan)
    info["codigo_municipio"] = ctx.set_index("id_paquete")["codigo_municipio"].reindex(info.index)
    info["municipio"] = ctx.set_index("id_paquete")["municipio"].reindex(info.index)
    z, extra = covariables(paquetes, ctx, cfg)
    piso = ctx.set_index("id_paquete")["ram_cons_ambiental"] if "ram_cons_ambiental" in ctx else None
    return {"riesgos": riesgos, "paquetes": info, "z": z, "crudo": extra["crudo"], "fuentes_z": extra["fuentes"], "piso_ambiental": piso}


def correr(entradas: dict, cfg: dict, escenario: dict | None = None, n: int | None = None) -> dict:
    tabla = m.preparar_riesgos(entradas["riesgos"], entradas["paquetes"], entradas["z"], cfg, entradas["piso_ambiental"], escenario)
    sim = m.simular(tabla, entradas["paquetes"], cfg, n=n,
                    tolerancia_paquete=(escenario or {}).get("tolerancia_paquete"),
                    tolerancia_proyecto=(escenario or {}).get("tolerancia_proyecto"))
    return {"tabla": tabla, **sim}


def main() -> int:
    asegurar_directorios()
    if not (PLATA / "cronograma.parquet").exists() or not (ORO / "contexto_paquetes.csv").exists():
        print("Faltan el cronograma (plata.sinteticos) o el contexto de los paquetes (oro.contexto)")
        return 1
    params = cargar_parametros()
    cfg = params["ejecucion"]
    ent = cargar_entradas(cfg)
    res = correr(ent, cfg)
    tabla = res["tabla"]

    # contribucion de cada riesgo al atraso esperado de su paquete y valor de los controles
    tot = tabla.groupby("id_paquete")["atraso_esperado"].transform("sum").replace(0, np.nan)
    tabla["contribucion_pct"] = (tabla["atraso_esperado"] / tot * 100).round(1)
    pq = res["paquetes"].merge(ent["paquetes"][["nombre", "ruta_critica", "meses_restantes", "costo_dia_parada_usd", "presupuesto_usd", "municipio"]],
                               left_on="id_paquete", right_index=True, how="left")
    pq = pq.merge(tabla.groupby("id_paquete").agg(amenazas_abiertas=("lambda", lambda s: int((s > 0).sum())),
                                                  atraso_evitado_por_controles=("atraso_evitado_por_controles", "sum")),
                  left_on="id_paquete", right_index=True, how="left")
    top = tabla[tabla["lambda"] > 0].sort_values("atraso_esperado", ascending=False).groupby("id_paquete").head(1).set_index("id_paquete")
    pq["riesgo_principal"] = pq["id_paquete"].map(top["id_riesgo"])
    pq["categoria_principal"] = pq["id_paquete"].map(top["categoria"])
    pq = pq.merge(ent["z"].add_prefix("z_"), left_on="id_paquete", right_index=True, how="left")
    pq = pq.merge(ent["crudo"], left_on="id_paquete", right_index=True, how="left")
    num = pq.select_dtypes("number").columns
    pq[num] = pq[num].round(2)
    pr = res["proyectos"].round(2)

    tabla.drop(columns=["costo_directo_var"]).round(4).to_csv(ORO / "ejecucion_riesgos.csv", index=False)
    pq.to_csv(ORO / "ejecucion_paquetes.csv", index=False)
    pr.to_csv(ORO / "ejecucion_proyectos.csv", index=False)
    escribir_json(ORO / "ejecucion_resumen.json", {
        "metadata": {"fuente": "Modelo de riesgo de ejecución (Monte Carlo) sobre la matriz RAM y el territorio real",
                     "licencia": "Resultado del piloto; registro y cronograma SINTÉTICOS", "simulaciones": res["simulaciones"],
                     "tolerancia_paquete": res["tolerancia_paquete"], "tolerancia_proyecto": res["tolerancia_proyecto"],
                     "ram": params["ram"].get("version", {}).get("tipo", "oficial"), "fuentes_covariables": ent["fuentes_z"]},
        "parametros": cfg, "portafolio": res["portafolio"], "histogramas": res["histogramas"],
    })
    print(f"Oro de riesgo de ejecución generado: {len(tabla)} amenazas, {len(pq)} paquetes, {len(pr)} proyectos, {res['simulaciones']} escenarios")
    for _, f in pr.iterrows():
        print(f"  {f['id_proyecto']}: atraso esperado {f['atraso_media']:.0f} días (P90 {f['atraso_p90']:.0f}); "
              f"sobrecosto P90 USD {f['costo_p90'] / 1e6:.1f} M; IRE {f['ire']:.0f}")
    print(f"  covariables: {', '.join(ent['fuentes_z'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
