"""
Boletin diario de alertas tempranas: Oro -> Consumo.

Lee las alertas del corte de hoy (oro.ict) y las compara con las del ultimo corte anterior del historial:
  nuevas     paquetes que hoy entran en alerta
  suben      paquetes que ya estaban en alerta y subieron de prioridad
  siguen     paquetes que siguen en alerta (misma prioridad o menor)
  resueltas  paquetes que estaban en alerta y hoy ya no

Salidas (exports/alertas/):
  historial.jsonl          un corte por linea (fecha y alertas resumidas); si se corre dos veces el mismo dia, se reemplaza
  novedades.json           el resumen del ultimo corte: lo que se notifica
  boletin_<fecha>.html     boletin para leer, imprimir o reenviar
  boletin_<fecha>.md       el mismo en texto, para Teams o correo

Enviar el boletin no es parte del pipeline (que solo sale a internet en Bronce, para descargar): lo hace
src/notificaciones.py desde la tarea diaria (alertas_diarias.py o el servidor de la aplicacion).

Uso:  python -m consumo.alertas
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime

from comun.config import EXPORTS, ORO, asegurar_directorios

CARPETA = EXPORTS / "alertas"
ORDEN = {"media": 0, "alta": 1, "critica": 2}
NOMBRE = {"critica": "crítica", "alta": "alta", "media": "media"}


def leer_historial() -> list[dict]:
    ruta = CARPETA / "historial.jsonl"
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def comparar(hoy: list[dict], anterior: list[dict] | None) -> dict:
    """Clasifica las alertas de hoy frente al corte anterior (por paquete)."""
    previas = {a["id_paquete"]: a for a in (anterior or [])}
    actuales = {a["id_paquete"]: a for a in hoy}
    nuevas, suben, siguen = [], [], []
    for idp, a in actuales.items():
        if idp not in previas:
            nuevas.append(idp)
        elif ORDEN[a["prioridad"]] > ORDEN[previas[idp]["prioridad"]]:
            suben.append(idp)
        else:
            siguen.append(idp)
    resueltas = [idp for idp in previas if idp not in actuales]
    return {"nuevas": nuevas, "suben": suben, "siguen": siguen, "resueltas": resueltas}


def _resumen(a: dict) -> dict:
    return {k: a.get(k) for k in ("id_paquete", "nombre_paquete", "prioridad", "ict", "nivel", "municipio")}


def boletin_md(fecha: str, alertas: list[dict], cambios: dict, previas: dict) -> str:
    lineas = [f"# Alertas tempranas · {fecha}", ""]
    lineas.append(f"**{len(alertas)} paquetes en alerta**: {len(cambios['nuevas'])} nuevas, {len(cambios['suben'])} suben de "
                  f"prioridad, {len(cambios['siguen'])} siguen, {len(cambios['resueltas'])} resueltas.")
    lineas.append("")
    for a in alertas:
        marca = " · **NUEVA**" if a["id_paquete"] in cambios["nuevas"] else " · **SUBE**" if a["id_paquete"] in cambios["suben"] else ""
        lineas.append(f"## {a['nombre_paquete']} · prioridad {NOMBRE[a['prioridad']]} · ICT {a['ict']:.0f}{marca}")
        if a.get("municipio"):
            lineas.append(f"{a['municipio']} · {a.get('puntos_crisis', 0)} punto(s) de crisis en el mapa")
        lineas += [f"- {c['texto']}" for c in a["causas"]]
        if a.get("acciones"):
            lineas.append("")
            lineas.append("Qué hacer:")
            lineas += [f"- {x}" for x in a["acciones"]]
        lineas.append("")
    if cambios["resueltas"]:
        lineas.append("## Ya no están en alerta")
        lineas += [f"- {previas[i].get('nombre_paquete', i)}" for i in cambios["resueltas"]]
        lineas.append("")
    lineas.append("_Piloto Reto 5. Registro de riesgos SINTÉTICO; territorio real (DANE, ANT, RUNAP, IDEAM, CHIRPS, UNGRD, "
                  "MinDefensa, INVIAS, IGAC). Reglas y umbrales en parametros.yaml._")
    return "\n".join(lineas)


def boletin_html(fecha: str, alertas: list[dict], cambios: dict, previas: dict) -> str:
    color = {"critica": "#e2483a", "alta": "#f28a30", "media": "#f1c232"}
    e = html.escape
    tarjetas = []
    for a in alertas:
        marca = "NUEVA" if a["id_paquete"] in cambios["nuevas"] else "SUBE" if a["id_paquete"] in cambios["suben"] else ""
        tarjetas.append(f"""
<div style="border:1px solid #eaecea;border-left:6px solid {color[a['prioridad']]};border-radius:12px;padding:12px 16px;margin:12px 0">
  <div style="font-size:16px;font-weight:600">{e(a['nombre_paquete'])} · ICT {a['ict']:.0f}
    <span style="background:{color[a['prioridad']]};color:#fff;border-radius:999px;padding:2px 10px;font-size:12px;margin-left:6px">prioridad {NOMBRE[a['prioridad']]}</span>
    {f'<span style="background:#121814;color:#fff;border-radius:999px;padding:2px 10px;font-size:12px;margin-left:4px">{marca}</span>' if marca else ''}</div>
  <div style="color:#8a928d;font-size:13px;margin:2px 0 6px">{e(a.get('municipio') or '')} · {a.get('puntos_crisis', 0)} punto(s) de crisis en el mapa</div>
  <ul style="margin:4px 0 8px;padding-left:20px;font-size:14px">{''.join(f'<li>{e(c["texto"])}</li>' for c in a['causas'])}</ul>
  {f'<div style="background:#eef7f1;border-radius:10px;padding:8px 12px;font-size:13px"><b>Qué hacer</b><ul style="margin:4px 0 0;padding-left:20px">{"".join(f"<li>{e(x)}</li>" for x in a["acciones"])}</ul></div>' if a.get('acciones') else ''}
</div>""")
    resueltas = "".join(f"<li>{e(previas[i].get('nombre_paquete', i))}</li>" for i in cambios["resueltas"])
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alertas tempranas · {fecha}</title></head>
<body style="font-family:Inter,Segoe UI,Arial,sans-serif;color:#121814;background:#f3f4f2;margin:0;padding:24px">
<div style="max-width:760px;margin:0 auto;background:#fff;border-radius:24px;padding:24px 28px">
  <div style="font-size:24px;font-weight:600">Alertas tempranas <span style="color:#8a928d">· {fecha}</span></div>
  <p style="font-size:15px">{len(alertas)} paquetes en alerta: <b>{len(cambios['nuevas'])} nuevas</b>, {len(cambios['suben'])} suben de prioridad,
     {len(cambios['siguen'])} siguen, {len(cambios['resueltas'])} resueltas.</p>
  {''.join(tarjetas) or '<p>No hay paquetes en alerta hoy.</p>'}
  {f'<h3>Ya no están en alerta</h3><ul>{resueltas}</ul>' if resueltas else ''}
  <p style="color:#8a928d;font-size:12px;margin-top:20px">Piloto Reto 5 · Mapa de riesgos La Guajira. Registro de riesgos SINTÉTICO;
  territorio real (DANE, ANT, RUNAP, IDEAM, CHIRPS, UNGRD, MinDefensa, INVIAS, IGAC). Reglas y umbrales en parametros.yaml.</p>
</div></body></html>"""


def main() -> int:
    asegurar_directorios()
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = ORO / "alertas.json"
    if not ruta.exists():
        print("Faltan las alertas de Oro: corre antes oro.ict")
        return 1
    alertas = json.loads(ruta.read_text(encoding="utf-8"))
    fecha = (alertas[0]["generada_en"] if alertas else datetime.now().isoformat())[:10]

    historial = [h for h in leer_historial() if h["fecha"] != fecha]
    anterior = max((h for h in historial if h["fecha"] < fecha), key=lambda h: h["fecha"], default=None)
    previas = {a["id_paquete"]: a for a in (anterior or {}).get("alertas", [])}
    cambios = comparar(alertas, (anterior or {}).get("alertas"))

    historial.append({"fecha": fecha, "alertas": [_resumen(a) for a in alertas]})
    historial.sort(key=lambda h: h["fecha"])
    (CARPETA / "historial.jsonl").write_text("".join(json.dumps(h, ensure_ascii=False) + "\n" for h in historial), encoding="utf-8")

    md = boletin_md(fecha, alertas, cambios, previas)
    (CARPETA / f"boletin_{fecha}.md").write_text(md, encoding="utf-8")
    (CARPETA / f"boletin_{fecha}.html").write_text(boletin_html(fecha, alertas, cambios, previas), encoding="utf-8")
    novedades = {"fecha": fecha, "generado_en": datetime.now().isoformat(timespec="seconds"),
                 "comparado_con": anterior["fecha"] if anterior else None, "total": len(alertas), **cambios,
                 "boletin_html": f"boletin_{fecha}.html", "boletin_md": f"boletin_{fecha}.md",
                 "alertas": [_resumen(a) for a in alertas]}
    (CARPETA / "novedades.json").write_text(json.dumps(novedades, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Boletín del {fecha}: {len(alertas)} alertas · {len(cambios['nuevas'])} nuevas · {len(cambios['suben'])} suben · "
          f"{len(cambios['resueltas'])} resueltas (frente a {anterior['fecha'] if anterior else 'ningún corte anterior'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
