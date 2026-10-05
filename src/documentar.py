"""Regenera las partes automaticas de docs/PIPELINE.md a partir de la definicion del pipeline (src/pipeline.py)
y de los archivos que hay hoy en data/. Asi la documentacion de pasos, dependencias y datos no puede quedar
desactualizada respecto al codigo.

Secciones automaticas (entre marcas `<!-- AUTO:nombre -->` y `<!-- /AUTO:nombre -->`):
  diagrama    flujo de artefactos entre capas (Mermaid)
  pasos       tabla de pasos: capa, que hace, que lee y que escribe, y si descarga de internet
  inventario  archivos de cada capa con su formato, filas y tamano

Ademas escribe docs/DICCIONARIO_DATOS.md completo (tablas y columnas de cada capa, con tipo, nulos y descripcion), que sale del
mismo catalogo que muestra la pagina "Datos y modelo".

Uso:  python -m documentar        (con la carpeta src como directorio de trabajo)
"""
from __future__ import annotations

import re
import sys

from auditoria import revisar_archivo
from comun.config import DATA, RAIZ
from pipeline import ARTEFACTOS, PASOS, archivos_de, orden_topologico

DOC = RAIZ / "docs" / "PIPELINE.md"
DICCIONARIO = RAIZ / "docs" / "DICCIONARIO_DATOS.md"
TITULO_CAPA = {"bronce": "Bronce", "plata": "Plata", "oro": "Oro", "consumo": "Consumo"}
CARPETA = {"bronce": "data/bronze", "plata": "data/silver", "oro": "data/gold", "consumo": "exports"}


def _nodo(art: str) -> str:
    return art.replace(":", "_")


def diagrama() -> str:
    """Mermaid: un nodo por artefacto, agrupado por capa; una flecha por cada paso (lee -> escribe)."""
    lineas = ["```mermaid", "flowchart LR"]
    for capa in ("bronce", "plata", "oro", "consumo"):
        arts = [a for a in ARTEFACTOS if a.startswith(capa + ":")]
        if not arts:
            continue
        lineas.append(f'  subgraph {capa}["{TITULO_CAPA[capa]}  ·  {CARPETA[capa]}"]')
        lineas += [f'    {_nodo(a)}["{a.split(":", 1)[1]}"]' for a in arts]
        lineas.append("  end")
    flechas, definidos = [], set()
    for p in orden_topologico():
        for dest in p.escribe:
            for origen in p.lee:
                flechas.append(f"  {_nodo(origen)} --> {_nodo(dest)}")
            if not p.lee:
                nodo, texto = ("internet", 'internet(("internet<br/>fuentes abiertas"))') if p.requiere_red else ("semilla", 'semilla(("semilla 42<br/>datos inventados"))')
                flechas.append(f"  {nodo if nodo in definidos else texto} --> {_nodo(dest)}")
                definidos.add(nodo)
    lineas += list(dict.fromkeys(flechas))   # sin flechas repetidas
    lineas.append("```")
    return "\n".join(lineas)


def pasos() -> str:
    filas = ["| # | Paso (módulo) | Capa | Qué hace | Lee | Escribe | Red |", "|---|---|---|---|---|---|---|"]
    for i, p in enumerate(orden_topologico(), 1):
        filas.append(f"| {i} | `{p.id}` | {TITULO_CAPA[p.capa]} | {p.descripcion} | {', '.join(f'`{a}`' for a in p.lee) or '—'} | "
                     f"{', '.join(f'`{a}`' for a in p.escribe)} | {'sí' if p.requiere_red else 'no'} |")
    return "\n".join(filas)


def _tamano(bytes_: int) -> str:
    return f"{bytes_ / 1e6:.1f} MB" if bytes_ >= 1e6 else f"{max(bytes_ / 1e3, 0.1):.0f} KB"


def inventario() -> str:
    """Archivos que existen hoy, por capa y artefacto. Si todavia no se corrio el pipeline lo dice."""
    salida = []
    for capa in ("bronce", "plata", "oro", "consumo"):
        arts = [a for a in ARTEFACTOS if a.startswith(capa + ":")]
        filas, total = [], 0
        for art in arts:
            for f in archivos_de(art):
                r = revisar_archivo(f) if f.parent.name != "exports" else {"filas": None}
                total += f.stat().st_size
                n = "" if r["filas"] is None else f"{r['filas']:,}".replace(",", ".")
                filas.append(f"| `{art.split(':', 1)[1]}` | `{f.name}` | {f.suffix[1:]} | {n} | {_tamano(f.stat().st_size)} |")
        salida.append(f"**{TITULO_CAPA[capa]}** (`{CARPETA[capa]}`): {len(filas)} archivos, {_tamano(total)}\n")
        if filas:
            salida += ["<details><summary>Ver archivos</summary>\n", "| Artefacto | Archivo | Formato | Filas | Tamaño |", "|---|---|---|---:|---:|", *filas, "\n</details>\n"]
    return "\n".join(salida)


def diccionario() -> str:
    """Markdown con todas las tablas de las tres capas: descripcion, linaje y columnas (tipo, nulos, descripcion)."""
    sys.path.insert(0, str(RAIZ / "app"))
    from catalogo import construir_catalogo   # el catalogo vive junto a la API; es de solo lectura sobre data/

    cat = construir_catalogo()
    nombres = {"bronze": "Bronce", "silver": "Plata", "gold": "Oro"}
    out = ["# Diccionario de datos", "",
           "> Generado automáticamente por `python -m documentar` a partir de los archivos que hay hoy en `data/` y de las descripciones de",
           "> `app/catalogo.py`. No se edita a mano: para cambiar una descripción, cámbiala en el catálogo. El proceso que produce cada",
           "> tabla está en [PIPELINE.md](PIPELINE.md).", ""]
    for capa in cat["capas"]:
        out += [f"## {nombres.get(capa['id'], capa['nombre'])}", ""]
        for tabla in capa["tablas"]:
            meta = cat["datasets"].get(tabla["dataset"], {})
            origen = {"ideam": "IDEAM", "invias": "INVIAS", "igac": "IGAC", "dane": "DANE", "invias_igac": "INVIAS + IGAC", "meta": "metadatos"}.get(meta.get("origen"), "sintético")
            out += [f"### `{tabla['archivo']}` — {meta.get('titulo', tabla['dataset'])}", "",
                    f"*{meta.get('rol', '')}* · origen **{origen}** · {tabla['formato']} · {tabla['filas']:,} filas".replace(",", ".") +
                    (f" · geometría: {tabla['geometria']}" if tabla.get("geometria") else ""), ""]
            if meta.get("descripcion"):
                out += [meta["descripcion"], ""]
            if meta.get("generacion"):
                out += [f"**Cómo se genera:** {meta['generacion']}", ""]
            con = [c for c in tabla["columnas"] if c["descripcion"]]
            sin = len(tabla["columnas"]) - len(con)
            if con:
                out += ["| Columna | Tipo | Nulos | Descripción |", "|---|---|---:|---|"]
                out += [f"| `{c['nombre']}` | {c['tipo']} | {c['nulos']} | {c['descripcion'].replace('|', '/')} |" for c in con]
                out.append("")
            if sin:
                out += [f"*{sin} columnas más sin descripción (tal como las entrega la fuente en Bronce).*" if capa["id"] == "bronze"
                        else f"*{sin} columnas sin descripción en el catálogo.*", ""]
    return "\n".join(out)


SECCIONES = {"diagrama": diagrama, "pasos": pasos, "inventario": inventario}


def reemplazar(texto: str, nombre: str, contenido: str) -> str:
    patron = re.compile(rf"(<!-- AUTO:{nombre} -->)(.*?)(<!-- /AUTO:{nombre} -->)", re.S)
    if not patron.search(texto):
        raise SystemExit(f"Falta la marca <!-- AUTO:{nombre} --> en {DOC}")
    return patron.sub(lambda m: f"{m.group(1)}\n{contenido}\n{m.group(3)}", texto)


def main() -> int:
    if not DOC.exists():
        print(f"No existe {DOC}")
        return 1
    texto = DOC.read_text(encoding="utf-8")
    for nombre, f in SECCIONES.items():
        texto = reemplazar(texto, nombre, f())
    DOC.write_text(texto, encoding="utf-8")
    DICCIONARIO.write_text(diccionario(), encoding="utf-8")
    print(f"Documentacion actualizada: {DOC}  ({len(PASOS)} pasos, datos de {DATA})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
