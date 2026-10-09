"""Descarga la lluvia mensual de CHIRPS v3 sobre La Guajira a la capa Bronce.

Fuente: Climate Hazards Center (UC Santa Barbara), CHIRPS v3.0, version final mensual, rejilla de 0,05 grados (~5,5 km).
Combina satelite con estaciones (entre ellas las del IDEAM) y cubre desde 1981 hasta ~3 semanas despues del fin de cada mes.
Licencia CC BY 4.0. Cita: Climate Hazards Center Infrared Precipitation with Stations version 3 (CHIRPS3), https://doi.org/10.15780/G2JQ0P

No se baja el archivo mundial (~30 MB por mes): los archivos son COG (GeoTIFF optimizado para la nube) y se lee por HTTP
solo la ventana de la caja de descarga de La Guajira (unos 50 x 45 celdas). Cada mes queda en Bronce como un GeoTIFF propio,
con los valores tal como vienen (mm del mes; -9999 en el mar). La descarga es incremental: los meses que ya estan no se
vuelven a pedir.

Se baja desde 1991: los 30 anos 1991-2020 dan la normal climatologica de cada mes (periodo de referencia de la OMM), contra la
que se compara la lluvia de los ultimos anos. El mapa muestra los ultimos anos; la normal sirve para decir si un mes fue seco o
lluvioso para lo que es usual alli.

Uso:  python -m bronce.chirps                 # desde enero de 1991 hasta el ultimo mes publicado
      python -m bronce.chirps --desde 2000    # otro inicio
      python -m bronce.chirps --rehacer       # vuelve a bajar todo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import rasterio
from rasterio.windows import from_bounds

from comun.config import BRONCE, CAJA_DESCARGA, asegurar_directorios
from comun.http import ERRORES_RED, USER_AGENT

BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs"
CARPETA = BRONCE / "chirps"
PRIMER_ANIO = 1991       # inicio de la normal climatologica 1991-2020
NODATA = -9999.0
ENTORNO_GDAL = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".cog",
                "GDAL_HTTP_USERAGENT": USER_AGENT, "GDAL_HTTP_MAX_RETRY": "3", "GDAL_HTTP_RETRY_DELAY": "2"}


def archivo_mes(anio: int, mes: int):
    return CARPETA / f"chirps_v3_{anio}_{mes:02d}.tif"


def meses_publicados() -> list[tuple[int, int]]:
    """Meses que el servidor ya publico (lista del directorio)."""
    req = urllib.request.Request(BASE + "/", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        html = r.read().decode("utf-8", "replace")
    return sorted({(int(a), int(m)) for a, m in re.findall(r"chirps-v3\.0\.(\d{4})\.(\d{2})\.cog", html)})


def bajar_mes(anio: int, mes: int, reintentos: int = 3) -> dict:
    """Lee la ventana de La Guajira del COG del mes y la guarda tal cual como GeoTIFF."""
    url = f"/vsicurl/{BASE}/chirps-v3.0.{anio}.{mes:02d}.cog"
    caja = CAJA_DESCARGA
    for intento in range(1, reintentos + 1):
        try:
            with rasterio.Env(**ENTORNO_GDAL), rasterio.open(url) as fuente:
                ventana = from_bounds(caja["lon_oeste"], caja["lat_sur"], caja["lon_este"], caja["lat_norte"], fuente.transform)
                ventana = ventana.round_offsets().round_lengths()
                datos = fuente.read(1, window=ventana)
                perfil = {"driver": "GTiff", "height": datos.shape[0], "width": datos.shape[1], "count": 1, "dtype": datos.dtype,
                          "crs": fuente.crs, "transform": fuente.window_transform(ventana), "nodata": NODATA, "compress": "deflate"}
            with rasterio.open(archivo_mes(anio, mes), "w", **perfil) as destino:
                destino.write(datos, 1)
                destino.update_tags(fuente="CHIRPS v3.0 final mensual", unidad="mm/mes", mes=f"{anio}-{mes:02d}")
            return {"mes": f"{anio}-{mes:02d}", "celdas": int(datos.size), "ok": True}
        except (rasterio.errors.RasterioIOError, *ERRORES_RED) as e:
            if intento == reintentos:
                return {"mes": f"{anio}-{mes:02d}", "ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
            time.sleep(3 * intento)
    return {"mes": f"{anio}-{mes:02d}", "ok": False}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lluvia mensual de CHIRPS v3 sobre La Guajira")
    ap.add_argument("--desde", type=int, default=PRIMER_ANIO, help="primer ano (por defecto 1991, para la normal 1991-2020)")
    ap.add_argument("--rehacer", action="store_true", help="vuelve a bajar los meses que ya estan")
    ap.add_argument("--hilos", type=int, default=4)
    args = ap.parse_args(argv)

    asegurar_directorios()
    CARPETA.mkdir(exist_ok=True)
    print("Lluvia mensual CHIRPS v3 (UCSB) - sin clave, CC BY 4.0")
    inicio = time.time()
    try:
        publicados = [m for m in meses_publicados() if m[0] >= args.desde]
    except ERRORES_RED as e:
        print(f"No se pudo leer la lista de meses publicados ({type(e).__name__}: {e})")
        return 1
    if not publicados:
        print("El servidor no publico meses en ese periodo")
        return 1
    pendientes = [m for m in publicados if args.rehacer or not archivo_mes(*m).exists()]
    print(f"  {len(publicados)} meses publicados desde {args.desde}; faltan {len(pendientes)} (los demas ya estan en Bronce)")

    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        resultados = list(pool.map(lambda m: bajar_mes(*m), pendientes))
    fallidos = [r for r in resultados if not r["ok"]]
    for r in fallidos:
        print(f"  [aviso] {r['mes']}: {r.get('error')}")

    en_disco = sorted(p.stem.replace("chirps_v3_", "").replace("_", "-") for p in CARPETA.glob("chirps_v3_*.tif"))
    meta = {
        "fuente": "CHIRPS v3.0 (Climate Hazards Center, UC Santa Barbara), version final mensual",
        "licencia": "CC BY 4.0",
        "cita": "Climate Hazards Center Infrared Precipitation with Stations version 3 (CHIRPS3) Data Repository, https://doi.org/10.15780/G2JQ0P",
        "servicio": BASE, "resolucion_grados": 0.05, "unidad": "mm/mes", "nodata": NODATA,
        "descargado_en": datetime.now().isoformat(timespec="seconds"), "caja": CAJA_DESCARGA,
        "desde": en_disco[0] if en_disco else None, "hasta": en_disco[-1] if en_disco else None,
        "meses": len(en_disco), "meses_fallidos": [r["mes"] for r in fallidos],
    }
    (BRONCE / "chirps_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(resultados) - len(fallidos)} meses bajados, {len(fallidos)} fallidos; en Bronce: {len(en_disco)} meses "
          f"({meta['desde']} a {meta['hasta']}) en {time.time() - inicio:.0f} s")
    return 0 if en_disco else 1


if __name__ == "__main__":
    sys.exit(main())
