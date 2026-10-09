"""La aplicacion corre la tarea diaria de alertas tempranas (src/tarea_diaria.py) a la hora configurada mientras esta
encendida, y la deja correr a mano desde el mapa ("Actualizar ahora").

Usa el mismo trabajo en segundo plano que la matriz RAM y los supuestos (ram_config): nunca corren dos recalculos a la
vez. Se apaga con alertas.automatico: false en parametros.yaml o con la variable de entorno RETO5_SIN_TAREA_DIARIA=1.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta

import notificaciones
import ram_config
import tarea_diaria

_estado: dict = {"activa": False}


def proxima(hora: str, ahora: datetime) -> datetime:
    h, m = (int(x) for x in str(hora).split(":"))
    candidata = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
    return candidata if candidata > ahora else candidata + timedelta(days=1)


def lanzar(al_terminar=None, con_descargas: bool = True, origen: str = "manual", forzar: bool = False) -> dict:
    """Arranca la tarea en segundo plano. Error si ya hay un recalculo en curso."""
    cfg = tarea_diaria.config()
    pasos = tarea_diaria.plan(con_descargas)

    def despues(estado: dict) -> dict:
        envios = [] if "consumo.alertas" in estado["fallos"] else tarea_diaria.enviar(cfg.get("url_aplicacion"), forzar)
        tarea_diaria.registrar({"inicio": estado["inicio"], "fin": datetime.now().isoformat(timespec="seconds"),
                                "origen": origen, "con_descargas": con_descargas, "pasos": estado["pasos"],
                                "fallos": estado["fallos"], "envios": envios})
        return {"envios": envios}

    return ram_config.correr_trabajo(pasos, al_terminar, nombre="tarea_diaria", despues=despues)


def iniciar(al_terminar=None) -> None:
    cfg = tarea_diaria.config()
    if not cfg.get("automatico", True) or os.environ.get("RETO5_SIN_TAREA_DIARIA"):
        _estado.update(activa=False, motivo="desactivada en parametros.yaml o con RETO5_SIN_TAREA_DIARIA")
        return
    hora = str(cfg.get("hora_diaria", "06:00"))

    def bucle():
        while True:
            siguiente = proxima(hora, datetime.now())
            _estado.update(activa=True, hora=hora, proxima=siguiente.isoformat(timespec="minutes"))
            while datetime.now() < siguiente:
                time.sleep(min(60.0, max(1.0, (siguiente - datetime.now()).total_seconds())))
            for _ in range(240):                     # si hay otro recalculo en curso, esperar hasta 2 horas
                if not ram_config.ocupado():
                    break
                time.sleep(30)
            try:
                lanzar(al_terminar, con_descargas=True, origen="automatica")
            except ram_config.ErrorRam:
                pass
            time.sleep(61)

    threading.Thread(target=bucle, daemon=True, name="tarea-diaria").start()
    _estado.update(activa=True, hora=hora, proxima=proxima(hora, datetime.now()).isoformat(timespec="minutes"))


def estado() -> dict:
    return {"programada": dict(_estado), "ultima": tarea_diaria.ultima(), "novedades": tarea_diaria.novedades(),
            "trabajo": ram_config.estado_recalculo(), "canales": notificaciones.estado_canales(tarea_diaria.config())}
