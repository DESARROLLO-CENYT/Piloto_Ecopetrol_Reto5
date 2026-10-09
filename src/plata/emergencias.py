"""Emergencias atendidas por la UNGRD: Bronce -> Plata.

Entradas (Bronce): ungrd_emergencias_<periodo>.parquet (uno por reporte anual, con columnas distintas), emergencias_meta.json.
Entrada (Plata):   municipios.geojson (codigos y nombres de los 15 municipios).
Salidas (Plata):   emergencias.parquet (una fila por emergencia), reporte_calidad_emergencias.csv, proveniencia_emergencias.json.

Reglas:
  * Se armonizan las columnas de los reportes (p. ej. `fallecidos`/`muertos`, `viviendas_destruidas`/`viv_destru`,
    `divipola`/`codificaci_n_segun_divipola`) y los numeros llegan como texto ("0.00", "$ 0.00").
  * Codigo de municipio: si el de la fuente no es de La Guajira (pasa: Riohacha con el codigo 20049 de Cesar en 2025),
    se toma el del nombre del municipio; si tampoco se encuentra, la fila sale. Ambos casos se cuentan.
  * `tipo`: el evento de la fuente en grupos estables (inundacion y creciente, incendio forestal, vendaval y tormenta,
    sequia y desabastecimiento de agua, erosion costera, movimiento en masa, incendio estructural, otros).
  * Las emergencias declaradas para todo el departamento ("DEPARTAMENTO", codigo 44) quedan con codigo 44.
  * Filas repetidas en todas sus columnas se quitan (el reporte de 2025 trae cada emergencia dos veces).
"""
from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd

from comun.config import BRONCE, PLATA, asegurar_directorios
from comun.ideam import sin_tildes
from comun.serializacion import escribir_proveniencia, leer_json

COLUMNAS = {        # nombre en Plata -> nombres posibles en los reportes
    "codigo_fuente": ("divipola", "codificaci_n_segun_divipola"),
    "fallecidos": ("fallecidos", "muertos"),
    "heridos": ("heridos",),
    "desaparecidos": ("desaparecidos", "desapa"),
    "personas": ("personas",),
    "familias": ("familias",),
    "viviendas_destruidas": ("viviendas_destruidas", "viv_destru"),
    "viviendas_averiadas": ("viviendas_averiadas", "viv_aver"),
    "vias": ("vias", "vias_averiadas"),
    "hectareas": ("hectareas",),
}
NUMEROS = [c for c in COLUMNAS if c != "codigo_fuente"]
TIPOS = [   # (palabras del evento, tipo)
    (("INUNDACION", "CRECIENTE", "AVENIDA TORRENCIAL", "TEMPORAL"), "Inundación o creciente"),
    (("INCENDIO FORESTAL", "INCENDIO DE COBERTURA"), "Incendio forestal"),
    (("VENDAVAL", "TORMENTA", "HURACAN", "TORNADO"), "Vendaval o tormenta"),
    (("SEQUIA", "DESABASTECIMIENTO"), "Sequía o desabastecimiento de agua"),
    (("EROSION", "MAR DE LEVA", "MAREJADA"), "Erosión costera"),
    (("MOVIMIENTO EN MASA", "DESLIZAMIENTO"), "Movimiento en masa"),
    (("INCENDIO ESTRUCTURAL", "COLAPSO", "EXPLOSION"), "Incendio o colapso estructural"),
]


def tipo_evento(evento: str) -> str:
    e = sin_tildes(str(evento)).upper()
    return next((t for palabras, t in TIPOS if any(p in e for p in palabras)), "Otro")


def numero(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[$\s,]", "", regex=True), errors="coerce").fillna(0)


def _clave(nombre) -> str:
    return sin_tildes(str(nombre)).upper().replace(" ", "")


def armonizar(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"fecha": pd.to_datetime(df["fecha"], errors="coerce"), "municipio_fuente": df["municipio"].astype(str),
                        "evento": df["evento"].astype(str).str.strip().str.upper()})
    for destino, origen in COLUMNAS.items():
        col = next((c for c in origen if c in df.columns), None)
        if destino == "codigo_fuente":
            out[destino] = df[col].astype(str).str.split(".").str[0].str.zfill(5) if col else None
        else:
            out[destino] = numero(df[col]) if col else 0.0
    return out


def limpiar(crudos: dict[str, pd.DataFrame], municipios: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    codigos = set(municipios["codigo"])
    por_nombre = {_clave(n): c for c, n in zip(municipios["codigo"], municipios["nombre"])}
    rep: dict = {"filas_bronce": int(sum(len(d) for d in crudos.values()))}
    # filas identicas en todas sus columnas: el reporte de 2025 llega con cada emergencia dos veces. Dos emergencias del
    # mismo dia, municipio y evento con distinto codigo de emergencia son distintas y se conservan.
    unicos = {p: d.drop_duplicates() for p, d in crudos.items()}
    rep["duplicados_removidos"] = int(rep["filas_bronce"] - sum(len(d) for d in unicos.values()))
    t = pd.concat([armonizar(d).assign(reporte=p) for p, d in unicos.items() if len(d)], ignore_index=True)
    rep["fecha_invalida"] = int(t["fecha"].isna().sum())
    t = t[t["fecha"].notna()].copy()
    ok = t["codigo_fuente"].isin(codigos)
    departamental = t["codigo_fuente"].isin(["00044", "44000"]) | (t["municipio_fuente"].str.upper().str.strip() == "DEPARTAMENTO")
    t["codigo"] = t["codigo_fuente"].where(ok, t["municipio_fuente"].map(lambda n: por_nombre.get(_clave(n))))
    t.loc[departamental & ~ok, "codigo"] = "44"          # emergencias declaradas para todo el departamento
    rep["emergencias_departamentales"] = int((departamental & ~ok).sum())
    rep["codigo_corregido_por_nombre"] = int((~ok & ~departamental & t["codigo"].notna()).sum())
    rep["municipio_desconocido"] = int(t["codigo"].isna().sum())
    t = t[t["codigo"].notna()].copy()
    t["tipo"] = t["evento"].map(tipo_evento)
    t["anio"] = t["fecha"].dt.year
    t[NUMEROS] = t[NUMEROS].astype(float)
    t = t[["fecha", "anio", "codigo", "evento", "tipo", *NUMEROS, "reporte"]].sort_values(["fecha", "codigo"]).reset_index(drop=True)
    rep.update(emergencias_plata=int(len(t)), anios=",".join(str(a) for a in sorted(t["anio"].unique())),
               personas_afectadas=int(t["personas"].sum()), fallecidos=int(t["fallecidos"].sum()),
               tipo_otro=int((t["tipo"] == "Otro").sum()))
    return t, rep


def main() -> int:
    asegurar_directorios()
    if not (BRONCE / "emergencias_meta.json").exists() or not (PLATA / "municipios.geojson").exists():
        print("Faltan Bronce de emergencias o los municipios en Plata: corre antes bronce.emergencias y plata.municipios")
        return 1
    meta = leer_json(BRONCE / "emergencias_meta.json")
    crudos = {p: pd.read_parquet(BRONCE / f"ungrd_emergencias_{p}.parquet") for p in meta["reportes"]
              if (BRONCE / f"ungrd_emergencias_{p}.parquet").exists()}
    t, rep = limpiar(crudos, gpd.read_file(PLATA / "municipios.geojson"))
    t.to_parquet(PLATA / "emergencias.parquet", index=False)
    pd.DataFrame([rep]).to_csv(PLATA / "reporte_calidad_emergencias.csv", index=False)
    escribir_proveniencia("emergencias", meta, rep)
    print("Plata de emergencias generada")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
