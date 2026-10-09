"""Contexto social y territorial de cada paquete de trabajo: Plata -> Oro.

Entradas (Plata): paquetes.geojson (sinteticos), municipios.geojson, indicadores_censo2018.parquet, irca_anual.parquet,
                  seguridad_municipio_mensual.parquet, emergencias.parquet, resguardos.geojson, areas_protegidas_runap.geojson.
Salida (Oro):     data/gold/contexto_paquetes.csv (una fila por paquete)

Cruza cada paquete (un poligono) con las fuentes reales:
  * municipio: el que contiene el centro del paquete, con su IPM, NBI, % indigena, PDET e IRCA;
  * resguardos: % del paquete dentro de resguardos, el mas cercano (nombre, pueblo) y la distancia (0 si se cruzan);
  * areas protegidas: lo mismo;
  * seguridad: victimas de homicidio y denuncias de extorsion de los ultimos 12 meses en el municipio y su tasa;
  * emergencias del municipio en los anos publicados.
Las distancias y areas se calculan en metros (EPSG:3116).

Este cruce no cambia el ICT: describe el entorno real de cada paquete para leerlo junto al indice.

Ademas, sugerencias para la matriz RAM (parametros.yaml -> ram.sugerencias): evidencia del territorio para que el equipo
evaluador revise la calificacion, no un reemplazo de su juicio:
  * probabilidad sugerida para riesgos de seguridad fisica (delitos contra personas e infraestructura en el municipio) y
    para riesgos climaticos (emergencias de la UNGRD en el municipio), por eventos al ano;
  * consecuencia sugerida en Imagen (resguardo, PDET) y en Ambiental (area protegida);
  * riesgos del paquete calificados POR DEBAJO de esa evidencia ("por revisar").

Uso:  python -m oro.contexto
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd

from comun.config import CRS_METRICO, ORO, PLATA, asegurar_directorios, cargar_parametros
from modelo.ram import probabilidad_por_frecuencia

# Delitos que pueden alcanzar a un proyecto (a su personal, su carga o su infraestructura). El homicidio no entra:
# en su mayoria es violencia interpersonal y saturaria la probabilidad en cualquier municipio.
DELITOS_SEGURIDAD_FISICA = ("extorsion", "secuestro", "terrorismo", "masacres", "voladura_oleoductos",
                            "voladura_puentes_vias", "pirateria_terrestre", "afectacion_fuerza_publica")


def sugerencias_ram(t: pd.DataFrame, seg, em, riesgos, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Probabilidad y consecuencia que sugiere el territorio, y los riesgos calificados por debajo."""
    t = t.copy()
    umbrales = cfg["eventos_por_ano_para_probabilidad"]
    if seg is not None and len(seg):
        seg = seg[seg["delito"].isin(DELITOS_SEGURIDAD_FISICA)].assign(mes=lambda d: pd.to_datetime(d["mes"]))
        desde = seg["mes"].max() - pd.DateOffset(months=11)
        al_ano = seg[seg["mes"] >= desde].groupby("codigo")["casos"].sum()
        historia = seg.groupby("codigo")["casos"].sum()
        t["ram_prob_seguridad"] = [probabilidad_por_frecuencia(float(al_ano.get(c, 0)), bool(historia.get(c, 0)), umbrales)
                                   for c in t["codigo_municipio"]]
    if em is not None and len(em):
        anios = em["anio"].nunique()
        por_ano = em[em["tipo"].isin(["Inundación o creciente", "Vendaval o tormenta", "Sequía o desabastecimiento de agua",
                                      "Incendio forestal", "Movimiento en masa", "Erosión costera"])].groupby("codigo").size() / max(anios, 1)
        t["ram_prob_desastres"] = [probabilidad_por_frecuencia(float(por_ano.get(c, 0)), bool(por_ano.get(c, 0)), umbrales)
                                   for c in t["codigo_municipio"]]
    ci, ca = cfg["consecuencia_imagen"], cfg["consecuencia_ambiental"]
    if "distancia_resguardo_km" in t:
        t["ram_cons_imagen"] = [max(ci["en_resguardo"] if d == 0 else ci["resguardo_a_5km"] if d <= 5 else 0,
                                    ci["municipio_pdet"] if bool(p) else 0)
                                for d, p in zip(t["distancia_resguardo_km"], t.get("pdet", pd.Series(False, index=t.index)))]
    if "distancia_area_protegida_km" in t:
        t["ram_cons_ambiental"] = [ca["en_area_protegida"] if d == 0 else ca["area_protegida_a_2km"] if d <= 2
                                   else ca["area_protegida_a_10km"] if d <= 10 else 0 for d in t["distancia_area_protegida_km"]]

    # riesgos abiertos del paquete calificados por debajo de lo que sugiere el territorio
    reglas = [("seguridad_fisica", "probabilidad", "ram_prob_seguridad"), ("climatico", "probabilidad", "ram_prob_desastres"),
              ("social_comunidad", "cons_imagen", "ram_cons_imagen"), ("ambiental", "cons_ambiental", "ram_cons_ambiental")]
    abiertos = riesgos[(riesgos["tipo"] == "amenaza") & (riesgos["estado"] != "materializado")]
    por_revisar: dict[str, list[str]] = {p: [] for p in t["id_paquete"]}
    sug = t.set_index("id_paquete")
    for _, r in abiertos.iterrows():
        p = r["id_paquete_trabajo"]
        for cat, campo, col in reglas:
            if r["categoria"] != cat or col not in sug or p not in sug.index:
                continue
            esperado, actual = sug.loc[p, col], r[campo]
            if pd.notna(esperado) and esperado and pd.notna(actual) and actual < esperado:
                por_revisar[p].append(r["id_riesgo"])
    t["ram_por_revisar"] = t["id_paquete"].map(lambda p: len(por_revisar[p]))
    t["ram_por_revisar_ids"] = t["id_paquete"].map(lambda p: ",".join(por_revisar[p]))
    return t, {"riesgos_ram_por_revisar": int(t["ram_por_revisar"].sum())}


def _lee(nombre):
    ruta = PLATA / nombre
    if not ruta.exists():
        return None
    return gpd.read_file(ruta) if ruta.suffix == ".geojson" else pd.read_parquet(ruta)


def cercano(paquetes_m: gpd.GeoDataFrame, capa_m: gpd.GeoDataFrame, prefijo: str, etiqueta: str) -> pd.DataFrame:
    """Para cada paquete: % dentro de la capa, el objeto mas cercano y la distancia en km (0 si se cruzan)."""
    union = capa_m.geometry.union_all()
    filas = []
    for _, p in paquetes_m.iterrows():
        d = capa_m.distance(p.geometry)
        i = d.idxmin()
        filas.append({"id_paquete": p["id_paquete"],
                      f"pct_en_{prefijo}": round(p.geometry.intersection(union).area / p.geometry.area * 100, 1),
                      f"{prefijo}_cercano": capa_m.loc[i, "nombre"], f"{prefijo}_{etiqueta}": capa_m.loc[i, etiqueta],
                      f"distancia_{prefijo}_km": round(float(d.min()) / 1000, 1)})
    return pd.DataFrame(filas)


def construir() -> tuple[pd.DataFrame, dict]:
    paq, mun = _lee("paquetes.geojson"), _lee("municipios.geojson")
    pm = paq.to_crs(CRS_METRICO)
    centros = gpd.GeoDataFrame(paq[["id_paquete"]], geometry=pm.geometry.centroid, crs=CRS_METRICO)
    en = gpd.sjoin(centros, mun[["codigo", "nombre", "geometry"]].to_crs(CRS_METRICO), how="left", predicate="within")
    t = pd.DataFrame({"id_paquete": paq["id_paquete"], "id_proyecto": paq["id_proyecto"],
                      "codigo_municipio": en["codigo"].values, "municipio": en["nombre"].values})
    rep = {"paquetes": int(len(t)), "paquetes_sin_municipio": int(t["codigo_municipio"].isna().sum())}

    censo = _lee("indicadores_censo2018.parquet")
    if censo is not None:
        cols = ["codigo", "ipm", "nbi", "miseria", "pct_indigena", "hogares_sin_acueducto", "pdet", "poblacion_2018"]
        t = t.merge(censo[[c for c in cols if c in censo]].rename(columns={"codigo": "codigo_municipio"}), on="codigo_municipio", how="left")
    irca = _lee("irca_anual.parquet")
    if irca is not None:
        u = irca.dropna(subset=["irca"]).sort_values("anio").groupby("codigo").last()
        t["irca_ultimo"] = t["codigo_municipio"].map(u["irca"])
        t["irca_anio"] = t["codigo_municipio"].map(u["anio"]).astype("Int64")
    resg, ap = _lee("resguardos.geojson"), _lee("areas_protegidas_runap.geojson")
    if resg is not None and len(resg):
        t = t.merge(cercano(pm, resg.to_crs(CRS_METRICO), "resguardo", "pueblo"), on="id_paquete", how="left")
        rep["paquetes_que_cruzan_resguardos"] = int((t["distancia_resguardo_km"] == 0).sum())
    if ap is not None and len(ap):
        t = t.merge(cercano(pm, ap.to_crs(CRS_METRICO), "area_protegida", "categoria"), on="id_paquete", how="left")
        rep["paquetes_que_cruzan_areas_protegidas"] = int((t["distancia_area_protegida_km"] == 0).sum())
    seg = _lee("seguridad_municipio_mensual.parquet")
    if seg is not None and len(seg):
        seg = seg.assign(mes=pd.to_datetime(seg["mes"]))
        desde = seg["mes"].max() - pd.DateOffset(months=11)
        ult = seg[seg["mes"] >= desde].groupby(["codigo", "delito"])["victimas"].sum().unstack(fill_value=0)
        for d in ("homicidio", "extorsion"):
            t[f"{d}_12m_municipio"] = t["codigo_municipio"].map(ult[d] if d in ult else {}).fillna(0).astype(int)
            if "poblacion_2018" in t:
                t[f"tasa_{d}_12m"] = (t[f"{d}_12m_municipio"] / t["poblacion_2018"] * 1e5).round(1)
        rep["seguridad_hasta"] = seg["mes"].max().strftime("%Y-%m")
    em = _lee("emergencias.parquet")
    if em is not None and len(em):
        t["emergencias_municipio"] = t["codigo_municipio"].map(em["codigo"].value_counts()).fillna(0).astype(int)
        t["emergencias_tipo_principal"] = t["codigo_municipio"].map(em.groupby("codigo")["tipo"].agg(lambda s: s.value_counts().index[0]))
    for c in ("ipm", "nbi", "miseria", "pct_indigena", "hogares_sin_acueducto"):
        if c in t:
            t[c] = t[c].round(1)
    riesgos = _lee("riesgos.geojson")
    if riesgos is not None and "nivel_residual" in riesgos:
        t, rep_ram = sugerencias_ram(t, seg, em, riesgos, cargar_parametros()["ram"]["sugerencias"])
        rep.update(rep_ram)
    return t.drop(columns=[c for c in ("poblacion_2018",) if c in t]), rep


def main() -> int:
    asegurar_directorios()
    if not (PLATA / "paquetes.geojson").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan paquetes o municipios en Plata: corre antes plata.sinteticos y plata.municipios")
        return 1
    t, rep = construir()
    t.to_csv(ORO / "contexto_paquetes.csv", index=False, encoding="utf-8")
    print("Oro del contexto de los paquetes generado")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
