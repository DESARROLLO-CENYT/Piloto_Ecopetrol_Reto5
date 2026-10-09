"""
Arranca el piloto con un solo comando, en cualquier PC:

    py -3.12 iniciar.py            (Windows)
    python3.12 iniciar.py          (Mac / Linux)

Hace, en orden y solo lo que haga falta:
  1. Crea el entorno virtual en una carpeta local de este PC (no dentro del
     proyecto: si el proyecto esta en una carpeta de red, cada PC necesita su
     propio entorno, porque un entorno guarda rutas de la maquina que lo creo).
  2. Instala requirements.txt (solo la primera vez o si el archivo cambia).
  3. Genera los datos sinteticos y calcula el ICT si no existe la capa Oro.
  4. Descarga los datos abiertos que falten (clima del IDEAM, vias de INVIAS e
     IGAC, rios del IGAC, municipios del DANE; unos minutos, necesita internet).
     Si falla, el piloto arranca igual con lo que haya.
  5. Levanta la aplicacion y abre el navegador.

Opciones:
  --regenerar       vuelve a correr el pipeline completo (incluidas las descargas)
  --sin-ideam       no descarga datos abiertos (no necesita internet)
  --red             acepta conexiones de otros PC de la red local
  --puerto N        puerto del servidor (por defecto 8000)
  --sin-navegador   no abre el navegador

Solo usa la biblioteca estandar, porque corre antes de que exista el entorno.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REQUISITOS = RAIZ / "requirements.txt"
ARCHIVO_ORO = RAIZ / "data" / "gold" / "paquetes_ict.geojson"
# fuente del pipeline -> producto Oro que muestra que ya se descargó
FUENTES_ABIERTAS = {
    "ideam": RAIZ / "data" / "gold" / "clima_estaciones.geojson",
    "invias,vias_igac": RAIZ / "data" / "gold" / "red_vial.geojson",   # las dos redes se unen en una sola capa
    "hidrografia": RAIZ / "data" / "gold" / "rios.geojson",
    "municipios": RAIZ / "data" / "gold" / "municipios.geojson",
    "chirps": RAIZ / "data" / "gold" / "lluvia_chirps.json",
    "social,seguridad,emergencias": RAIZ / "data" / "gold" / "indicadores_municipio.json",
    "resguardos,runap": RAIZ / "data" / "gold" / "resguardos.geojson",
}


def paso(msg: str) -> None:
    print(f"\n>> {msg}", flush=True)


def carpeta_entorno() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "reto5-piloto" / "venv"


def python_del_entorno(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ejecutar(cmd: list, **kw) -> None:
    resultado = subprocess.run([str(c) for c in cmd], **kw)
    if resultado.returncode != 0:
        sys.exit(f"\nFallo el comando: {' '.join(str(c) for c in cmd)}")


def preparar_entorno() -> Path:
    venv = carpeta_entorno()
    py = python_del_entorno(venv)
    if not py.exists():
        paso(f"Creando entorno virtual en {venv}")
        venv.parent.mkdir(parents=True, exist_ok=True)
        ejecutar([sys.executable, "-m", "venv", venv])

    marca = venv / "requirements.sha256"
    huella = hashlib.sha256(REQUISITOS.read_bytes()).hexdigest()
    if not marca.exists() or marca.read_text().strip() != huella:
        paso("Instalando dependencias (la primera vez tarda unos minutos)")
        ejecutar([py, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
        ejecutar([py, "-m", "pip", "install", "-r", REQUISITOS, "--quiet"])
        marca.write_text(huella)
    else:
        paso("Dependencias al dia")
    return py


def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.1.1", 80))
            return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def puerto_ocupado(host: str, puerto: int) -> bool:
    """True si otro programa ya escucha en ese puerto, por ejemplo un piloto anterior que sigue abierto.

    Sin esta comprobacion, uvicorn falla al arrancar pero el navegador se abre igual sobre el servidor viejo, y
    parece que los cambios no funcionan.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if os.name != "nt":  # en Linux/Mac evita un falso "ocupado" justo despues de cerrar el anterior
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, puerto))
        except OSError:
            return True
    return False


def abrir_cuando_responda(url: str) -> None:
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "api/parametros", timeout=2)
            webbrowser.open(url)
            return
        except OSError:
            time.sleep(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Arranca el piloto Reto 5 con un solo comando.")
    ap.add_argument("--regenerar", action="store_true", help="vuelve a generar los datos aunque existan")
    ap.add_argument("--red", action="store_true", help="permite abrir la app desde otros PC de la red")
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--sin-ideam", action="store_true", help="no descarga datos abiertos (no necesita internet)")
    ap.add_argument("--sin-navegador", action="store_true")
    args = ap.parse_args()

    if sys.version_info < (3, 11):
        sys.exit(f"Se necesita Python 3.11 o superior (recomendado 3.12); este es {sys.version.split()[0]}.")

    print(f"Piloto Reto 5 · proyecto en {RAIZ}")
    host = "0.0.0.0" if args.red else "127.0.0.1"
    if puerto_ocupado(host, args.puerto):
        sys.exit(
            f"\nEl puerto {args.puerto} ya está en uso: lo más probable es que siga abierto un piloto anterior.\n"
            f"   Ciérralo con Ctrl+C en su ventana y vuelve a correr este comando,\n"
            f"   o abre este en otro puerto:  py -3.12 iniciar.py --puerto {args.puerto + 1}"
        )
    py = preparar_entorno()

    if args.regenerar or not ARCHIVO_ORO.exists():
        paso("Generando los datos sintéticos y calculando el ICT (sin descargar nada)")
        ejecutar([py, "ejecutar_pipeline.py", "--sin-red"], cwd=RAIZ)
    else:
        paso("Datos sintéticos ya generados (usa --regenerar para rehacerlos)")

    # Fuentes abiertas (sin clave): solo se descarga la que falte, o todas con --regenerar.
    # ejecutar_pipeline.py --fuente X corre Bronce -> Plata -> Oro de X y de lo que depende de X.
    if args.sin_ideam:
        paso("Datos abiertos omitidos (--sin-ideam): el mapa abrirá sin clima, vías, ríos ni municipios")
    else:
        faltan = [fuente for fuente, archivo in FUENTES_ABIERTAS.items() if args.regenerar or not archivo.exists()]
        if faltan:
            paso(f"Descargando datos abiertos: {', '.join(faltan)} (unos minutos; necesita internet; ríos y vías de uso no comercial)")
            subprocess.run([str(py), "ejecutar_pipeline.py", "--fuente", ",".join(faltan)], cwd=RAIZ)
            for fuente, archivo in FUENTES_ABIERTAS.items():
                if fuente in faltan and not archivo.exists():
                    print(f"   No se pudo obtener «{fuente}». El piloto arranca igual; reintenta luego con --regenerar.")
        else:
            paso("Datos abiertos ya descargados (usa --regenerar para actualizarlos)")

    url = f"http://127.0.0.1:{args.puerto}/"
    paso(f"Aplicación en {url}")
    if args.red:
        print(f"   Desde otros PC de la red: http://{ip_local()}:{args.puerto}/")
        print("   (si Windows pregunta por el firewall, permite el acceso en redes privadas)")
    print("   Ctrl+C para detener.", flush=True)

    if not args.sin_navegador:
        threading.Thread(target=abrir_cuando_responda, args=(url,), daemon=True).start()

    servidor = subprocess.Popen(
        [str(py), "-m", "uvicorn", "main:app", "--app-dir", "app", "--host", host, "--port", str(args.puerto)],
        cwd=RAIZ,
    )
    try:
        servidor.wait()
    except KeyboardInterrupt:
        servidor.terminate()
        servidor.wait()


if __name__ == "__main__":
    main()
