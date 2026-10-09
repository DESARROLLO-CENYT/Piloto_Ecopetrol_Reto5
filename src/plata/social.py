"""Indicadores sociales por municipio: Bronce -> Plata.

Entradas (Bronce): dane_censo2018_*.csv (un archivo por indicador del censo 2018), ins_irca.csv, art_pdet.csv, social_meta.json.
Entrada (Plata):   municipios.geojson (para validar los codigos: los 15 municipios del DANE).
Salidas (Plata):   indicadores_censo2018.parquet (una fila por municipio y una del departamento, codigo 44),
                   irca_anual.parquet (municipio x ano), reporte_calidad_social.csv, proveniencia_social.json.

Reglas:
  * Cada indicador del censo llega en su propio servicio, con su propio nombre de campo: aqui se les da un nombre
    estable (`ipm`, `nbi`, `pct_indigena`...) y se unen por el codigo DANE de 5 digitos.
  * Los porcentajes deben quedar entre 0 y 100; lo que no, se descarta y se cuenta.
  * Control cruzado: indigenas = % indigena x poblacion (el servicio trae ambos); la diferencia maxima va al reporte.
  * La fila del departamento se calcula: los conteos se suman y los porcentajes se ponderan por la poblacion
    (el IPM y el NBI del departamento publicados por el DANE pueden diferir un poco por redondeo).
  * IRCA: el INS escribe "#TODOS" para el departamento (codigo 44); los municipios llegan con su nombre y codigo.
"""
from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from comun.config import BRONCE, PLATA, asegurar_directorios
from comun.serializacion import escribir_proveniencia, leer_json

# indicador de Bronce -> {campo del servicio: nombre en Plata}
CAMPOS = {
    "poblacion": {"CL0_TT_PERSN": "poblacion_2018"},
    "poblacion_rural_dispersa": {"CL3_TT_PERSN": "poblacion_rural_dispersa"},
    "etnia": {"TOTAL_UNIDADES_PA1_GRP_ETNIC_1": "indigenas", "PARTICIPACION_PORCENTUAL_PA1_GRP_ETNIC_1": "pct_indigena",
              "TOTAL_UNIDADES_PA1_GRP_ETNIC_5": "afro", "PARTICIPACION_PORCENTUAL_PA1_GRP_ETNIC_5": "pct_afro"},
    "ipm": {"IPM": "ipm"},
    "nbi": {"NBIC_Total_Prop_de_Personas_en_NBIPorc": "nbi"},
    "nbi_vivienda": {"NBIC_Total_PP_Comp_vivienda": "nbi_vivienda"},
    "nbi_servicios": {"NBIC_Total_PP_Comp_Servicios": "nbi_servicios"},
    "nbi_hacinamiento": {"NBIC_Total_PP_Comp_Hacinamiento": "nbi_hacinamiento"},
    "nbi_inasistencia": {"NBIC_Total_PP_Comp_Inasistencia": "nbi_inasistencia"},
    "nbi_dependencia": {"NBIC_Total_PP_Comp_dependencia_economica": "nbi_dependencia"},
    "miseria": {"NBIC_Total_Prop_de_Personas_en_miseria": "miseria"},
    "deficit_habitacional": {"PC_dvhabitat": "deficit_habitacional"},
    "deficit_acueducto": {"PC_N_agua": "hogares_sin_acueducto"},
}
CODIGO = ("MPIO_CCDGO", "U_MPIO", "COD_MPIO_1")
PORCENTAJES = ("pct_indigena", "pct_afro", "ipm", "nbi", "nbi_vivienda", "nbi_servicios", "nbi_hacinamiento", "nbi_inasistencia",
               "nbi_dependencia", "miseria", "deficit_habitacional", "hogares_sin_acueducto")
CONTEOS = ("poblacion_2018", "poblacion_rural_dispersa", "indigenas", "afro")


def unir_censo(tablas: dict[str, pd.DataFrame], codigos: set[str]) -> tuple[pd.DataFrame, dict]:
    """Une los indicadores (uno por servicio) en una fila por municipio."""
    rep: dict = {"tablas_censo": len(tablas), "indicadores_sin_tabla": 0, "codigos_desconocidos": 0, "porcentajes_fuera_de_rango": 0}
    base = pd.DataFrame({"codigo": sorted(codigos)})
    for clave, campos in CAMPOS.items():
        t = tablas.get(clave)
        if t is None or t.empty:
            rep["indicadores_sin_tabla"] += 1
            continue
        campo_codigo = next(c for c in CODIGO if c in t.columns)
        t = t.assign(codigo=t[campo_codigo].astype(str).str.zfill(5))
        rep["codigos_desconocidos"] += int((~t["codigo"].isin(codigos)).sum())
        t = t[t["codigo"].isin(codigos)].drop_duplicates("codigo")
        base = base.merge(t[["codigo", *campos]].rename(columns=campos), on="codigo", how="left")
    for c in PORCENTAJES:
        if c in base:
            malo = base[c].notna() & ~base[c].between(0, 100)
            rep["porcentajes_fuera_de_rango"] += int(malo.sum())
            base.loc[malo, c] = np.nan
    if {"poblacion_2018", "poblacion_rural_dispersa"} <= set(base.columns):
        base["pct_rural_disperso"] = base["poblacion_rural_dispersa"] / base["poblacion_2018"] * 100
    if {"indigenas", "pct_indigena", "poblacion_2018"} <= set(base.columns):
        esperado = base["pct_indigena"] / 100 * base["poblacion_2018"]
        rep["diferencia_maxima_indigenas_vs_pct"] = int((base["indigenas"] - esperado).abs().max())
    return base, rep


def fila_departamento(m: pd.DataFrame) -> dict:
    """Conteos sumados y porcentajes ponderados por poblacion."""
    fila: dict = {"codigo": "44"}
    w = m["poblacion_2018"] if "poblacion_2018" in m else None
    for c in m.columns:
        if c == "codigo":
            continue
        if c in CONTEOS:
            fila[c] = float(m[c].sum())
        elif w is not None and m[c].notna().any():
            ok = m[c].notna()
            fila[c] = float((m.loc[ok, c] * w[ok]).sum() / w[ok].sum())
    if "indigenas" in fila and fila.get("poblacion_2018"):
        fila["pct_indigena"] = fila["indigenas"] / fila["poblacion_2018"] * 100
        fila["pct_afro"] = fila["afro"] / fila["poblacion_2018"] * 100
    return fila


def limpiar_irca(irca: pd.DataFrame, nombres: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """Una fila por municipio y ano. `nombres`: nombre normalizado -> codigo."""
    from comun.ideam import sin_tildes
    rep = {"irca_bronce": int(len(irca))}
    if irca.empty:
        return pd.DataFrame(columns=["codigo", "anio", "irca", "nivel", "irca_urbano", "irca_rural"]), rep
    clave = irca["municipio"].astype(str).map(lambda n: "#TODOS" if n.strip() == "#TODOS" else sin_tildes(n).upper().replace(" ", ""))
    codigo = clave.map(lambda k: "44" if k == "#TODOS" else nombres.get(k))
    if "municipiocodigo" in irca:                     # el codigo del INS manda cuando es uno de los 15
        cod_ins = irca["municipiocodigo"].astype(str).str.strip().str.zfill(5)
        codigo = cod_ins.where(cod_ins.isin(set(nombres.values())), codigo)
    rep["irca_municipio_desconocido"] = int(codigo.isna().sum())
    t = pd.DataFrame({
        "codigo": codigo, "anio": pd.to_numeric(irca["a_o"], errors="coerce"),
        "irca": pd.to_numeric(irca["irca"], errors="coerce"), "nivel": irca.get("nivel_de_riesgo"),
        "irca_urbano": pd.to_numeric(irca.get("ircaurbano"), errors="coerce"),
        "irca_rural": pd.to_numeric(irca.get("ircarural"), errors="coerce"),
    }).dropna(subset=["codigo", "anio"])
    fuera = t["irca"].notna() & ~t["irca"].between(0, 100)
    rep["irca_fuera_de_rango"] = int(fuera.sum())
    t.loc[fuera, "irca"] = np.nan
    t = t.drop_duplicates(["codigo", "anio"]).sort_values(["codigo", "anio"]).reset_index(drop=True)
    t["anio"] = t["anio"].astype(int)
    rep.update(irca_plata=int(len(t)), irca_desde=int(t["anio"].min()), irca_hasta=int(t["anio"].max()))
    return t, rep


def main() -> int:
    asegurar_directorios()
    if not (BRONCE / "social_meta.json").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan Bronce de social o los municipios en Plata: corre antes bronce.social y plata.municipios")
        return 1
    from comun.ideam import sin_tildes
    mun = gpd.read_file(PLATA / "municipios.geojson")
    codigos = set(mun["codigo"])
    tablas = {c: pd.read_csv(BRONCE / f"dane_censo2018_{c}.csv", dtype={"MPIO_CCDGO": str, "U_MPIO": str, "COD_MPIO_1": str})
              for c in CAMPOS if (BRONCE / f"dane_censo2018_{c}.csv").exists()}
    censo, rep = unir_censo(tablas, codigos)
    censo["nombre"] = censo["codigo"].map(dict(zip(mun["codigo"], mun["nombre"])))

    pdet = pd.read_csv(BRONCE / "art_pdet.csv", dtype=str)
    pdet = pdet[pdet["cod_muni"].astype(str).str.zfill(5).isin(codigos)]
    censo["pdet"] = censo["codigo"].isin(pdet["cod_muni"].astype(str).str.zfill(5))
    censo["subregion_pdet"] = censo["codigo"].map(dict(zip(pdet["cod_muni"].astype(str).str.zfill(5), pdet["nom_subreg"])))
    rep["municipios_pdet"] = int(censo["pdet"].sum())

    depto = fila_departamento(censo.drop(columns=["nombre", "pdet", "subregion_pdet"]))
    depto.update(nombre="La Guajira", pdet=bool(censo["pdet"].any()), subregion_pdet=None)
    tabla = pd.concat([censo, pd.DataFrame([depto])], ignore_index=True)
    num = tabla.select_dtypes("number").columns
    tabla[num] = tabla[num].round(2)
    rep.update(municipios_plata=int(len(censo)), municipios_sin_ipm=int(censo["ipm"].isna().sum()) if "ipm" in censo else 15,
               poblacion_2018_departamento=int(depto.get("poblacion_2018", 0)))

    nombres = {sin_tildes(n).upper().replace(" ", ""): c for c, n in zip(mun["codigo"], mun["nombre"])}
    irca, rep_irca = limpiar_irca(pd.read_csv(BRONCE / "ins_irca.csv", dtype=str), nombres)
    rep.update(rep_irca)

    tabla.to_parquet(PLATA / "indicadores_censo2018.parquet", index=False)
    irca.to_parquet(PLATA / "irca_anual.parquet", index=False)
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_social.csv", index=False)
    escribir_proveniencia("social", leer_json(BRONCE / "social_meta.json"), rep)
    print("Plata de indicadores sociales generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
