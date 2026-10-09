"""
Envio de las alertas tempranas por Microsoft Teams o por correo.

No es un paso del pipeline (el pipeline solo sale a internet en Bronce, para descargar datos): lo llama la tarea diaria
(alertas_diarias.py o el servidor de la aplicacion) despues de recalcular, con las novedades del boletin
(exports/alertas/novedades.json).

Que canales se usan lo dice parametros.yaml -> alertas.canales. Las credenciales NUNCA van en archivos del proyecto,
solo en variables de entorno del equipo que envia:
  Teams   RETO5_TEAMS_WEBHOOK   URL de un flujo de Workflows "cuando se recibe una solicitud de webhook" o de un webhook
                                entrante del canal; recibe una tarjeta adaptable (Adaptive Card)
  Correo  RETO5_SMTP_HOST, RETO5_SMTP_PUERTO (587), RETO5_SMTP_USUARIO, RETO5_SMTP_CLAVE,
          RETO5_CORREO_DE, RETO5_CORREO_PARA (varios separados por coma)
Un canal activado sin sus variables no falla: se reporta como "sin configurar". Por defecto solo se avisa lo que cambio
(alertas nuevas o que suben de prioridad), para no repetir cada dia lo mismo.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from pathlib import Path


def _variables(nombres: tuple[str, ...]) -> dict:
    return {n: os.environ.get(n, "").strip() for n in nombres}


VARS_TEAMS = ("RETO5_TEAMS_WEBHOOK",)
VARS_CORREO = ("RETO5_SMTP_HOST", "RETO5_SMTP_USUARIO", "RETO5_SMTP_CLAVE", "RETO5_CORREO_DE", "RETO5_CORREO_PARA")


def estado_canales(cfg: dict) -> dict:
    """Que canal esta activo y si tiene sus variables (sin revelar ningun valor)."""
    canales = (cfg or {}).get("canales", {})
    teams, correo = _variables(VARS_TEAMS), _variables(VARS_CORREO)
    return {
        "archivo": {"activo": True, "configurado": True},
        "teams": {"activo": bool(canales.get("teams")), "configurado": all(teams.values())},
        "correo": {"activo": bool(canales.get("correo")), "configurado": all(correo.values()),
                   "destinatarios": len([d for d in correo["RETO5_CORREO_PARA"].split(",") if d.strip()])},
    }


def hay_que_avisar(novedades: dict, cfg: dict) -> bool:
    avisar = set((cfg or {}).get("notificar", ["nuevas", "suben"]))
    if "todas" in avisar:
        return novedades.get("total", 0) > 0
    return any(novedades.get(k) for k in avisar)


def tarjeta_teams(novedades: dict, alertas: list[dict], url_app: str | None = None) -> dict:
    """Adaptive Card con el resumen del dia y las alertas nuevas o que suben primero."""
    nuevas, suben = set(novedades.get("nuevas", [])), set(novedades.get("suben", []))
    orden = sorted(alertas, key=lambda a: (a["id_paquete"] not in nuevas | suben, -a["ict"]))
    cuerpo = [
        {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": f"Alertas tempranas · {novedades['fecha']}"},
        {"type": "TextBlock", "wrap": True, "text": f"{novedades['total']} paquetes en alerta: {len(nuevas)} nuevas, {len(suben)} suben de "
                                                    f"prioridad, {len(novedades.get('siguen', []))} siguen, "
                                                    f"{len(novedades.get('resueltas', []))} resueltas."},
    ]
    for a in orden[:8]:
        marca = " · NUEVA" if a["id_paquete"] in nuevas else " · SUBE" if a["id_paquete"] in suben else ""
        cuerpo.append({"type": "TextBlock", "wrap": True, "weight": "Bolder", "spacing": "Medium",
                       "color": "Attention" if a["prioridad"] == "critica" else "Warning",
                       "text": f"{a['nombre_paquete']} · prioridad {a['prioridad']} · ICT {a['ict']:.0f}{marca}"})
        cuerpo.append({"type": "TextBlock", "wrap": True, "isSubtle": True, "spacing": "None",
                       "text": " · ".join(c["texto"] for c in a.get("causas", [])[:3])})
    cuerpo.append({"type": "TextBlock", "wrap": True, "isSubtle": True, "size": "Small",
                   "text": "Piloto Reto 5: registro de riesgos sintético, territorio real."})
    tarjeta = {"type": "AdaptiveCard", "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "version": "1.4", "body": cuerpo}
    if url_app:
        tarjeta["actions"] = [{"type": "Action.OpenUrl", "title": "Ver en el mapa", "url": url_app}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": tarjeta}]}


def enviar_teams(carga: dict, url: str, timeout: int = 20) -> None:
    peticion = urllib.request.Request(url, data=json.dumps(carga).encode("utf-8"), method="POST",
                                      headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=timeout) as r:  # noqa: S310 - URL configurada por el usuario
        if r.status >= 300:
            raise RuntimeError(f"Teams respondió {r.status}")


def enviar_correo(asunto: str, texto: str, cuerpo_html: str, v: dict, timeout: int = 30) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"] = asunto, v["RETO5_CORREO_DE"]
    msg["To"] = ", ".join(d.strip() for d in v["RETO5_CORREO_PARA"].split(",") if d.strip())
    msg.set_content(texto)
    msg.add_alternative(cuerpo_html, subtype="html")
    puerto = int(os.environ.get("RETO5_SMTP_PUERTO", "587") or 587)
    with smtplib.SMTP(v["RETO5_SMTP_HOST"], puerto, timeout=timeout) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(v["RETO5_SMTP_USUARIO"], v["RETO5_SMTP_CLAVE"])
        s.send_message(msg)


def notificar(carpeta: Path, alertas: list[dict], cfg: dict, url_app: str | None = None, forzar: bool = False) -> list[dict]:
    """Envia el boletin del ultimo corte por los canales activos y configurados. Devuelve el resultado de cada canal."""
    novedades = json.loads((carpeta / "novedades.json").read_text(encoding="utf-8"))
    canales = estado_canales(cfg)
    resultados = [{"canal": "archivo", "estado": "ok", "detalle": novedades["boletin_html"]}]
    if not forzar and not hay_que_avisar(novedades, cfg):
        for canal in ("teams", "correo"):
            if canales[canal]["activo"]:
                resultados.append({"canal": canal, "estado": "sin_novedades", "detalle": "nada nuevo que avisar hoy"})
        return resultados
    if canales["teams"]["activo"]:
        if not canales["teams"]["configurado"]:
            resultados.append({"canal": "teams", "estado": "sin_configurar", "detalle": "falta RETO5_TEAMS_WEBHOOK"})
        else:
            try:
                enviar_teams(tarjeta_teams(novedades, alertas, url_app), os.environ["RETO5_TEAMS_WEBHOOK"])
                resultados.append({"canal": "teams", "estado": "ok", "detalle": "tarjeta enviada"})
            except Exception as e:  # noqa: BLE001 - se reporta, no detiene la tarea
                resultados.append({"canal": "teams", "estado": "error", "detalle": f"{type(e).__name__}: {e}"[:200]})
    if canales["correo"]["activo"]:
        if not canales["correo"]["configurado"]:
            faltan = [k for k, v in _variables(VARS_CORREO).items() if not v]
            resultados.append({"canal": "correo", "estado": "sin_configurar", "detalle": f"faltan {', '.join(faltan)}"})
        else:
            try:
                texto = (carpeta / novedades["boletin_md"]).read_text(encoding="utf-8")
                cuerpo = (carpeta / novedades["boletin_html"]).read_text(encoding="utf-8")
                asunto = (f"Alertas tempranas {novedades['fecha']}: {len(novedades['nuevas'])} nuevas, "
                          f"{novedades['total']} en total")
                enviar_correo(asunto, texto, cuerpo, _variables(VARS_CORREO))
                resultados.append({"canal": "correo", "estado": "ok", "detalle": f"enviado a {canales['correo']['destinatarios']} destinatario(s)"})
            except Exception as e:  # noqa: BLE001
                resultados.append({"canal": "correo", "estado": "error", "detalle": f"{type(e).__name__}: {e}"[:200]})
    return resultados
