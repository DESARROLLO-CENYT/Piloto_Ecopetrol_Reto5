"""
Alertas tempranas diarias: descarga lo que cambia cada dia, recalcula el ICT y las alertas, arma el boletin y avisa.

    python alertas_diarias.py                 # todo: descarga el IDEAM, recalcula, boletin y envio
    python alertas_diarias.py --sin-red       # sin descargas: recalcula con lo que hay (sirve sin internet)
    python alertas_diarias.py --sin-enviar    # solo el boletin, sin Teams ni correo
    python alertas_diarias.py --forzar-envio  # envia aunque no haya alertas nuevas
    python alertas_diarias.py --programar     # muestra como programarla cada dia (Windows o Linux)

El boletin queda en exports/alertas/. Los canales (Teams, correo) se activan en parametros.yaml -> alertas.canales y se
configuran con variables de entorno (ver src/notificaciones.py). Si la aplicacion esta encendida, ella misma corre esta
tarea a la hora de alertas.hora_diaria; este comando sirve para un servidor sin la aplicacion.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))


def instrucciones(hora: str) -> str:
    py = Path(sys.executable)
    script = RAIZ / "alertas_diarias.py"
    return (
        "Para correrla todos los dias a las " + hora + ":\n\n"
        "Windows (Programador de tareas), en una consola:\n"
        f'  schtasks /Create /SC DAILY /ST {hora} /TN "Reto5 alertas diarias" /TR "\\"{py}\\" \\"{script}\\""\n\n'
        "Linux o Mac (cron), con crontab -e:\n"
        f"  {hora.split(':')[1]} {hora.split(':')[0]} * * * cd \"{RAIZ}\" && \"{py}\" alertas_diarias.py >> exports/alertas/tarea.log 2>&1\n\n"
        "Este comando no crea la tarea: la crea quien administre el equipo."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Alertas tempranas diarias (descarga, recalculo, boletin y envio).")
    ap.add_argument("--sin-red", action="store_true", help="no descarga nada; recalcula con lo que ya hay")
    ap.add_argument("--sin-enviar", action="store_true", help="solo el boletin, sin Teams ni correo")
    ap.add_argument("--forzar-envio", action="store_true", help="envia aunque no haya novedades")
    ap.add_argument("--programar", action="store_true", help="muestra como programar la tarea y sale")
    args = ap.parse_args(argv)

    import tarea_diaria
    if args.programar:
        print(instrucciones(str(tarea_diaria.config().get("hora_diaria", "06:00"))))
        return 0
    r = tarea_diaria.ejecutar(con_descargas=not args.sin_red, notificar=not args.sin_enviar, forzar=args.forzar_envio)
    nov = tarea_diaria.novedades() or {}
    print(f"\nBoletín del {nov.get('fecha', '-')}: {nov.get('total', 0)} alertas, {len(nov.get('nuevas', []))} nuevas, "
          f"{len(nov.get('suben', []))} suben, {len(nov.get('resueltas', []))} resueltas.")
    for e in r["envios"]:
        print(f"  {e['canal']}: {e['estado']} ({e['detalle']})")
    if r["fallos"]:
        print(f"Pasos con aviso: {', '.join(r['fallos'])}")
    return 1 if "oro.ict" in r["fallos"] or "consumo.alertas" in r["fallos"] else 0


if __name__ == "__main__":
    sys.exit(main())
