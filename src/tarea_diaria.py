"""
Tarea diaria de alertas tempranas: descarga lo que cambia cada dia, recalcula el ICT y las alertas, arma el boletin y
lo envia por los canales configurados.

  1. Bronce -> Plata -> Oro de las fuentes diarias (parametros.yaml -> alertas.fuentes_diarias; por defecto el IDEAM:
     la lluvia de las ultimas dos semanas entra a las amenazas externas del ICT).
  2. oro.ict y lo que depende de el, aunque ninguna fuente haya cambiado: con la fecha cambian la tendencia, las
     acciones de tratamiento vencidas y la ventana de lluvia.
  3. consumo.alertas: compara con el corte anterior (nuevas, suben, siguen, resueltas) y escribe el boletin.
  4. notificaciones: Teams o correo, si estan activos y configurados (solo si hay novedades).

La corre el servidor de la aplicacion a la hora configurada (alertas.hora_diaria) o el comando alertas_diarias.py desde
el Programador de tareas de Windows o cron.
"""
from __future__ import annotations

import json
from datetime import datetime

import pipeline
from comun.config import EXPORTS, ORO, cargar_parametros

CARPETA = EXPORTS / "alertas"


def config() -> dict:
    return cargar_parametros().get("alertas", {}) or {}


def plan(con_descargas: bool = True) -> list:
    """Pasos de la tarea, en orden: fuentes diarias y todo lo que depende del ICT."""
    cfg = config()
    ids = {p.id for p in pipeline.seleccionar(fuentes=list(cfg.get("fuentes_diarias", ["ideam"])), sin_red=not con_descargas)}
    ids |= {p.id for p in pipeline.seleccionar(fuentes=["ict"])}
    return [p for p in pipeline.orden_topologico() if p.id in ids]


def enviar(url_app: str | None = None, forzar: bool = False) -> list[dict]:
    """Notifica el ultimo boletin (despues de correr los pasos)."""
    import notificaciones
    alertas = json.loads((ORO / "alertas.json").read_text(encoding="utf-8")) if (ORO / "alertas.json").exists() else []
    return notificaciones.notificar(CARPETA, alertas, config(), url_app=url_app, forzar=forzar)


def registrar(resumen: dict) -> None:
    """Deja constancia de la ultima ejecucion (la lee la aplicacion para mostrar el estado)."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    (CARPETA / "ultima_tarea.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def ultima() -> dict | None:
    ruta = CARPETA / "ultima_tarea.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def novedades() -> dict | None:
    ruta = CARPETA / "novedades.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def ejecutar(con_descargas: bool = True, notificar: bool = True, url_app: str | None = None, forzar: bool = False) -> dict:
    """Corre la tarea completa en este proceso (para el comando de consola)."""
    inicio = datetime.now()
    pasos = plan(con_descargas)
    pipeline.mostrar_plan(pasos)
    resultados = pipeline.ejecutar(pasos)
    fallos = [p.id for p, ok in resultados if not ok]
    envios = enviar(url_app, forzar) if notificar and "consumo.alertas" not in fallos else []
    resumen = {"inicio": inicio.isoformat(timespec="seconds"), "fin": datetime.now().isoformat(timespec="seconds"),
               "origen": "consola", "con_descargas": con_descargas, "pasos": [p.id for p in pasos], "fallos": fallos,
               "envios": envios}
    registrar(resumen)
    return resumen
