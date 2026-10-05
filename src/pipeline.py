"""Definicion y ejecucion del pipeline de datos (arquitectura medallion).

Este modulo es la unica fuente de verdad de COMO esta armado el pipeline: que pasos existen, a que capa
pertenecen, que artefactos leen y cuales escriben. De aqui salen el orden de ejecucion, la auditoria, la
documentacion y la deteccion de archivos huerfanos.

Capas (ver comun/config.py):
  bronce  data/bronze  datos tal como llegan; solo los pasos `bronce.*` los escriben (y descargan de internet).
  plata   data/silver  limpios y conformados; los pasos `plata.*` leen Bronce (o Plata de otra fuente) y escriben Plata.
  oro     data/gold    productos para consumir; los pasos `oro.*` leen SOLO Plata y escriben Oro.
  consumo exports/     salidas para otros programas (GeoPackage); lee solo Oro.

Cada paso es un modulo ejecutable (`python -m plata.ideam`, con la carpeta src como directorio de trabajo).
El orden sale de las dependencias: un paso corre despues de los que escriben lo que el lee.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from comun.config import DATA, EXPORTS

SRC = Path(__file__).resolve().parent
CAPAS = ("bronce", "plata", "oro", "consumo")


@dataclass(frozen=True)
class Paso:
    id: str                   # "plata.ideam"
    capa: str                 # bronce | plata | oro | consumo
    fuente: str               # sinteticos, ideam, invias, vias_igac, hidrografia, municipios, red_vial, ict, validacion
    descripcion: str
    lee: tuple[str, ...] = ()       # artefactos que necesita (ids de ARTEFACTOS)
    escribe: tuple[str, ...] = ()   # artefactos que produce
    requiere_red: bool = False      # descarga de internet
    obligatorio: bool = False       # si falla, el pipeline se detiene (las fuentes abiertas no lo son)

    @property
    def modulo(self) -> str:
        return self.id


# Artefactos: conjuntos de archivos que un paso escribe y otro lee. Rutas relativas a data/ (o exports/).
# El patron `*` sirve para detectar archivos que ningun paso declara (huerfanos).
ARTEFACTOS: dict[str, tuple[str, ...]] = {
    "bronce:sinteticos": ("bronze/proyectos.geojson", "bronze/paquetes_trabajo.geojson", "bronze/comunidades.geojson",
                          "bronze/areas_protegidas.geojson", "bronze/hidrologia.geojson", "bronze/vias.geojson",
                          "bronze/clima_sintetico.csv", "bronze/registro_riesgos.xlsx"),
    "bronce:ideam": ("bronze/ideam_*",),
    "bronce:invias": ("bronze/invias_*",),
    "bronce:vias_igac": ("bronze/igac_via_*", "bronze/vias_igac_meta.json"),
    "bronce:hidrografia": ("bronze/igac_drenaje_*", "bronze/igac_cienagas.geojson", "bronze/igac_embalses.geojson",
                           "bronze/igac_lagunas.geojson", "bronze/hidrografia_meta.json"),
    "bronce:municipios": ("bronze/dane_municipios.geojson", "bronze/divipola_municipios.csv", "bronze/municipios_meta.json"),
    "plata:sinteticos": ("silver/riesgos.geojson", "silver/paquetes.geojson", "silver/proyectos.geojson", "silver/comunidades.geojson",
                         "silver/areas.geojson", "silver/hidro.geojson", "silver/vias.geojson", "silver/clima_sintetico.parquet",
                         "silver/reporte_calidad_bronce_a_plata.csv"),
    "plata:ideam": ("silver/ideam_*", "silver/reporte_calidad_ideam.csv", "silver/proveniencia_ideam.json"),
    "plata:invias": ("silver/invias_red_vial.geojson", "silver/reporte_calidad_invias.csv", "silver/proveniencia_invias.json"),
    "plata:vias_igac": ("silver/igac_vias.geojson", "silver/reporte_calidad_vias_igac.csv", "silver/proveniencia_vias_igac.json"),
    "plata:hidrografia": ("silver/igac_hidrografia.geojson", "silver/reporte_calidad_hidrografia.csv", "silver/proveniencia_hidrografia.json"),
    "plata:municipios": ("silver/municipios.geojson", "silver/reporte_calidad_municipios.csv", "silver/proveniencia_municipios.json"),
    "plata:red_vial": ("silver/red_vial.geojson", "silver/reporte_calidad_red_vial.csv", "silver/proveniencia_red_vial.json"),
    "oro:ict": ("gold/paquetes_ict.geojson", "gold/grid_calor.geojson", "gold/alertas.json", "gold/riesgos.geojson", "gold/proyectos.geojson",
                "gold/comunidades.geojson", "gold/areas.geojson", "gold/hidro.geojson", "gold/vias.geojson"),
    "oro:validacion": ("gold/validacion_backtest.csv", "gold/validacion_sensibilidad.csv"),
    "oro:ideam": ("gold/clima_estaciones.geojson", "gold/clima_radiacion.geojson"),
    "oro:hidrografia": ("gold/rios.geojson", "gold/cuerpos_agua.geojson"),
    "oro:red_vial": ("gold/red_vial.geojson",),
    "oro:municipios": ("gold/municipios.geojson", "gold/limite_departamental.geojson", "gold/reporte_cruces_municipios.csv"),
    "consumo:gis": ("exports/*",),
}

PASOS: tuple[Paso, ...] = (
    # ---- Bronce: datos tal como llegan -------------------------------------------------------------------------
    Paso("bronce.sinteticos", "bronce", "sinteticos", "Genera los datos sintéticos de entrada (proyectos, riesgos, clima simulado), sucios a propósito",
         escribe=("bronce:sinteticos",), obligatorio=True),
    Paso("bronce.ideam", "bronce", "ideam", "Descarga el clima real del IDEAM: catálogo, lluvia, temperatura, humedad, viento, presión, nivel, radiación y normales",
         escribe=("bronce:ideam",), requiere_red=True),
    Paso("bronce.invias", "bronce", "invias", "Descarga la Red Vial Nacional de INVIAS (solo lo que cruza La Guajira)",
         escribe=("bronce:invias",), requiere_red=True),
    Paso("bronce.vias_igac", "bronce", "vias_igac", "Descarga la red vial completa del IGAC 1:100.000 (7 capas)",
         escribe=("bronce:vias_igac",), requiere_red=True),
    Paso("bronce.hidrografia", "bronce", "hidrografia", "Descarga ríos, ciénagas, lagunas y embalses del IGAC 1:100.000",
         escribe=("bronce:hidrografia",), requiere_red=True),
    Paso("bronce.municipios", "bronce", "municipios", "Descarga los límites municipales del DANE y el DIVIPOLA",
         escribe=("bronce:municipios",), requiere_red=True),
    # ---- Plata: limpio y conformado ----------------------------------------------------------------------------
    Paso("plata.sinteticos", "plata", "sinteticos", "Limpia el registro de riesgos: duplicados, taxonomía y geolocalización inferida",
         lee=("bronce:sinteticos",), escribe=("plata:sinteticos",), obligatorio=True),
    Paso("plata.ideam", "plata", "ideam", "Clasifica lecturas por sensor, quita duplicados e imposibles, unifica unidades y agrega por día",
         lee=("bronce:ideam",), escribe=("plata:ideam",)),
    Paso("plata.invias", "plata", "invias", "Traduce dominios, quita tramos repetidos, recorta y simplifica la red nacional",
         lee=("bronce:invias",), escribe=("plata:invias",)),
    Paso("plata.hidrografia", "plata", "hidrografia", "Une las 5 capas, repara y recorta geometrías y traduce el estado del cauce",
         lee=("bronce:hidrografia",), escribe=("plata:hidrografia",)),
    Paso("plata.municipios", "plata", "municipios", "Nombres propios, código DANE, área en metros y geometría simplificada sin huecos",
         lee=("bronce:municipios",), escribe=("plata:municipios",)),
    Paso("plata.vias_igac", "plata", "vias_igac", "Une las 7 capas de vías, traduce dominios y recorta al departamento (municipios del DANE)",
         lee=("bronce:vias_igac", "plata:municipios"), escribe=("plata:vias_igac",)),
    Paso("plata.red_vial", "plata", "red_vial", "Une INVIAS e IGAC en una red sin duplicados y completa la superficie de INVIAS",
         lee=("plata:invias", "plata:vias_igac"), escribe=("plata:red_vial",)),
    # ---- Oro: productos para consumir --------------------------------------------------------------------------
    Paso("oro.ict", "oro", "ict", "Calcula el ICT, el índice de oportunidad, el escalamiento, el mapa de calor y los puntos calientes",
         lee=("plata:sinteticos",), escribe=("oro:ict",), obligatorio=True),
    Paso("oro.validacion", "oro", "validacion", "Backtest (circular) y sensibilidad de los pesos del modelo",
         lee=("plata:sinteticos", "oro:ict"), escribe=("oro:validacion",), obligatorio=True),
    Paso("oro.ideam", "oro", "ideam", "Una ficha por estación con todas sus variables, lo de ahora y las normales; puntos de radiación",
         lee=("plata:ideam",), escribe=("oro:ideam",)),
    Paso("oro.hidrografia", "oro", "hidrografia", "Capas de ríos (líneas) y cuerpos de agua (polígonos) para el mapa",
         lee=("plata:hidrografia",), escribe=("oro:hidrografia",)),
    Paso("oro.red_vial", "oro", "red_vial", "Capa de vías para el mapa: red nacional y complementaria, distinguidas por fuente",
         lee=("plata:red_vial",), escribe=("oro:red_vial",)),
    Paso("oro.municipios", "oro", "municipios", "Municipios con estaciones del IDEAM y km de vías dentro; contorno departamental",
         lee=("plata:municipios", "plata:ideam", "plata:red_vial"), escribe=("oro:municipios",)),
    # ---- Consumo -----------------------------------------------------------------------------------------------
    Paso("consumo.exportar_gis", "consumo", "gis", "Exporta la capa Oro del modelo a GeoPackage y GeoJSON para ArcGIS o QGIS",
         lee=("oro:ict",), escribe=("consumo:gis",)),
)
POR_ID = {p.id: p for p in PASOS}


# ---------------------------------------------------------------------------
# Orden y seleccion
# ---------------------------------------------------------------------------

def orden_topologico(pasos: tuple[Paso, ...] | list[Paso] = PASOS) -> list[Paso]:
    """Un paso va despues de los que escriben algo que el lee. Estable respecto al orden declarado."""
    escritor = {a: p.id for p in pasos for a in p.escribe}
    pendientes, listos, hechos = list(pasos), [], set()
    while pendientes:
        for p in pendientes:
            previos = {escritor[a] for a in p.lee if a in escritor and escritor[a] != p.id}
            if previos <= hechos:
                listos.append(p)
                hechos.add(p.id)
                pendientes.remove(p)
                break
        else:
            raise ValueError(f"Dependencias circulares entre: {[p.id for p in pendientes]}")
    return listos


def aguas_abajo(ids: set[str]) -> set[str]:
    """Pasos que leen (directa o indirectamente) lo que escriben los pasos `ids`: hay que repetirlos si algo cambio."""
    seleccion, cambio = set(ids), True
    while cambio:
        cambio = False
        escrito = {a for i in seleccion for a in POR_ID[i].escribe}
        for p in PASOS:
            if p.id not in seleccion and escrito & set(p.lee):
                seleccion.add(p.id)
                cambio = True
    return seleccion


def seleccionar(capa: str | None = None, fuentes: list[str] | None = None, sin_red: bool = False,
                con_dependientes: bool = True) -> list[Paso]:
    elegidos = {p.id for p in PASOS
                if (capa in (None, "todo") or p.capa == capa) and (not fuentes or p.fuente in fuentes)}
    if fuentes and con_dependientes:
        elegidos = aguas_abajo(elegidos)
    if sin_red:
        elegidos = {i for i in elegidos if not POR_ID[i].requiere_red}
    return [p for p in orden_topologico() if p.id in elegidos]


# ---------------------------------------------------------------------------
# Archivos declarados
# ---------------------------------------------------------------------------

def _base(patron: str) -> Path:
    return EXPORTS / patron.split("/", 1)[1] if patron.startswith("exports/") else DATA / patron


def archivos_de(artefacto: str) -> list[Path]:
    """Archivos que existen hoy para un artefacto (expande los patrones con `*`)."""
    salida: list[Path] = []
    for patron in ARTEFACTOS[artefacto]:
        ruta = _base(patron)
        salida += sorted(ruta.parent.glob(ruta.name)) if "*" in patron else ([ruta] if ruta.exists() else [])
    return [r for r in salida if r.is_file()]


def declarados() -> set[str]:
    return {a for p in PASOS for a in p.escribe}


def huerfanos() -> list[Path]:
    """Archivos en data/ que ningun paso declara (restos de versiones anteriores del pipeline)."""
    patrones = [pat for art in ARTEFACTOS.values() for pat in art if not pat.startswith("exports/")]
    out = []
    for capa in ("bronze", "silver", "gold"):
        for f in sorted((DATA / capa).glob("*")):
            rel = f"{capa}/{f.name}"
            if f.is_file() and not any(fnmatch(rel, p) for p in patrones):
                out.append(f)
    return out


# ---------------------------------------------------------------------------
# Ejecucion
# ---------------------------------------------------------------------------

def correr(paso: Paso) -> bool:
    print(f"\n{'=' * 78}\n[{paso.capa.upper()}] {paso.id}: {paso.descripcion}\n{'=' * 78}", flush=True)
    inicio = time.time()
    r = subprocess.run([sys.executable, "-m", paso.modulo], cwd=SRC, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    ok = r.returncode == 0
    print(f"-- {paso.id}: {'listo' if ok else 'FALLO (codigo ' + str(r.returncode) + ')'} en {time.time() - inicio:.0f} s", flush=True)
    return ok


def ejecutar(pasos: list[Paso]) -> list[tuple[Paso, bool]]:
    """Corre los pasos en orden. Un paso obligatorio que falla detiene todo; uno opcional (fuentes abiertas) avisa y sigue
    con lo ultimo descargado."""
    resultados: list[tuple[Paso, bool]] = []
    for p in pasos:
        ok = correr(p)
        resultados.append((p, ok))
        if not ok and p.obligatorio:
            print(f"\nFallo en el paso obligatorio {p.id}; se detiene el pipeline.")
            break
        if not ok:
            print(f"[aviso] {p.id} no termino bien; se sigue con lo ultimo disponible de esa fuente.")
    return resultados


def mostrar_plan(pasos: list[Paso]) -> None:
    print(f"{'#':>2}  {'paso':22s} {'capa':8s} {'lee':44s} escribe")
    for i, p in enumerate(pasos, 1):
        print(f"{i:>2}  {p.id:22s} {p.capa:8s} {', '.join(p.lee) or '-':44s} {', '.join(p.escribe)}{'  [red]' if p.requiere_red else ''}")


# Atajos de versiones anteriores del comando -> fuentes
ATAJOS = {"solo_ideam": ["ideam"], "solo_vias": ["invias", "vias_igac"], "solo_rios": ["hidrografia"], "solo_municipios": ["municipios"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Pipeline de datos medallion. Sin opciones corre todo en orden de dependencias.",
        epilog="Ejemplos:\n  python ejecutar_pipeline.py --capa plata        # recalcula Plata y lo que depende, sin internet\n"
               "  python ejecutar_pipeline.py --fuente ideam      # actualiza el clima y todo lo que se alimenta de el\n"
               "  python ejecutar_pipeline.py --sin-red --auditar # todo lo local y revisa los datos",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capa", choices=["bronce", "plata", "oro", "consumo"], help="solo los pasos de una capa")
    ap.add_argument("--fuente", help="fuentes separadas por coma: " + ", ".join(sorted({p.fuente for p in PASOS})))
    ap.add_argument("--solo-esto", action="store_true", help="con --fuente: no repetir los pasos que dependen de lo que cambia")
    ap.add_argument("--sin-red", "--sin-ideam", dest="sin_red", action="store_true",
                    help="omite las descargas (usa el Bronce que ya hay); no necesita internet")
    ap.add_argument("--solo-ideam", action="store_true", help="atajo de --fuente ideam")
    ap.add_argument("--solo-vias", action="store_true", help="atajo de --fuente invias,vias_igac")
    ap.add_argument("--solo-rios", action="store_true", help="atajo de --fuente hidrografia")
    ap.add_argument("--solo-municipios", action="store_true", help="atajo de --fuente municipios")
    ap.add_argument("--lista", action="store_true", help="muestra el plan (pasos, orden, lo que lee y escribe) y sale")
    ap.add_argument("--auditar", action="store_true", help="al terminar, revisa la coherencia de las tres capas")
    ap.add_argument("--limpiar-huerfanos", action="store_true", help="borra los archivos de data/ que ningun paso declara (restos de versiones anteriores) y sale")
    args = ap.parse_args(argv)

    fuentes = [f.strip() for f in args.fuente.split(",")] if args.fuente else []
    for atajo, fs in ATAJOS.items():
        if getattr(args, atajo):
            fuentes += fs
    desconocidas = set(fuentes) - {p.fuente for p in PASOS}
    if desconocidas:
        ap.error(f"fuente desconocida: {sorted(desconocidas)}")

    if args.limpiar_huerfanos:
        sobrantes = huerfanos()
        for f in sobrantes:
            f.unlink()
            print(f"borrado: {f.relative_to(DATA)}")
        print(f"{len(sobrantes)} archivos huerfanos borrados." if sobrantes else "No hay archivos huerfanos.")
        return 0

    plan = seleccionar(args.capa, fuentes or None, args.sin_red, con_dependientes=not args.solo_esto)
    if args.lista or not plan:
        mostrar_plan(plan)
        return 0
    mostrar_plan(plan)
    resultados = ejecutar(plan)
    fallos = [p.id for p, ok in resultados if not ok]

    codigo = 0
    if args.auditar:
        from auditoria import auditar
        codigo = auditar()
    print("\nPipeline terminado." + (f" Con avisos en: {', '.join(fallos)}." if fallos else " Sin fallos.") +
          " Para ver el mapa: python run_app.py")
    return codigo or (1 if any(not ok and p.obligatorio for p, ok in resultados) else 0)


if __name__ == "__main__":
    sys.exit(main())
