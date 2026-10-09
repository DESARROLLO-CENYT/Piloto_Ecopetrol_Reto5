"""Pesos, umbrales, reglas de escalamiento y topes del ICT editables desde la aplicacion (vista "Ajustar el modelo").

* Lo editado se guarda en modelo_personalizado.yaml; parametros.yaml (la version base) no se toca.
* La vista previa recalcula el ICT y el escalamiento en memoria con los parametros propuestos, sin guardar nada.
* AHP: de una matriz de comparaciones por pares a pesos y razon de consistencia (src/modelo/ahp.py).
* Cada guardado o restauracion queda en el historial de versiones (historial.py).
"""
from __future__ import annotations

import copy
from datetime import datetime

import numpy as np
import pandas as pd
import yaml

import historial
from comun.config import CLAVES_ESCALAMIENTO_RAM, MODELO_PERSONALIZADO_PATH, cargar_parametros
from modelo import ahp as m_ahp
from modelo import ict as m_ict

CRITERIOS = list(m_ict.CRITERIOS)
ENTEROS_ESCALAMIENTO = {"ict_critico": (1, 100), "min_amenazas_convergentes": (1, 12), "incremento_tendencia_alerta": (1, 100),
                        "ventana_tendencia_dias": (1, 60), "min_acciones_vencidas": (1, 50)}
TOPES_EXTERNAS = {"lluvia_mm_para_saturar": (5, 1000), "emergencias_por_ano_para_saturar": (1, 200),
                  "delitos_100k_para_saturar": (1, 1000), "anomalia_para_saturar": (0.1, 5)}


class ErrorModelo(ValueError):
    pass


def _num(v, campo, lo, hi):
    try:
        x = float(v)
    except (TypeError, ValueError) as e:
        raise ErrorModelo(f"{campo}: debe ser un número") from e
    if not lo <= x <= hi:
        raise ErrorModelo(f"{campo}: debe estar entre {lo} y {hi}")
    return int(x) if float(x).is_integer() else round(x, 6)


def editables(p: dict) -> dict:
    """La parte de los parametros que la vista puede cambiar."""
    c = p["criterios"]
    return {
        "pesos": p["pesos"],
        "umbrales_criticidad": p["umbrales_criticidad"],
        "escalamiento": {k: v for k, v in p["escalamiento"].items() if k in ENTEROS_ESCALAMIENTO or k == "riesgo_en_area_sensible"},
        "factores_estado": p["factores_estado"],
        "criterios": {
            "vulnerabilidad_territorial": {"componentes": c["vulnerabilidad_territorial"]["componentes"]},
            "amenazas_externas": {"componentes": c["amenazas_externas"]["componentes"],
                                  **{k: c["amenazas_externas"][k] for k in TOPES_EXTERNAS if k in c["amenazas_externas"]}},
        },
    }


def resumen() -> dict:
    vig, base = cargar_parametros(), cargar_parametros(oficial=True)
    return {"vigente": editables(vig), "base": editables(base), "personalizado": MODELO_PERSONALIZADO_PATH.exists(),
            "version": vig.get("modelo_version"), "historial": historial.leer(n=15)}


def validar(cuerpo: dict) -> tuple[dict, list[str]]:
    """Valida los cambios propuestos. Devuelve (bloque a guardar, advertencias)."""
    out: dict = {}
    adv: list[str] = []
    if "pesos" in cuerpo:
        w = {k: _num(cuerpo["pesos"].get(k, 0), f"Peso de {k}", 0, 100) for k in CRITERIOS}
        total = sum(w.values())
        if total <= 0:
            raise ErrorModelo("Los pesos deben sumar más que cero")
        out["pesos"] = {k: round(v / total, 4) for k, v in w.items()}
        if min(out["pesos"].values()) == 0:
            adv.append("Un criterio con peso 0 queda fuera del ICT")
    if "umbrales_criticidad" in cuerpo:
        u = {k: _num(cuerpo["umbrales_criticidad"].get(k), f"Umbral {k}", 1, 99) for k in ("bajo", "medio", "alto")}
        if not u["bajo"] < u["medio"] < u["alto"]:
            raise ErrorModelo("Los umbrales deben crecer: bajo < medio < alto")
        out["umbrales_criticidad"] = u
    if "escalamiento" in cuerpo:
        e = {}
        for k, (lo, hi) in ENTEROS_ESCALAMIENTO.items():
            if k in cuerpo["escalamiento"]:
                e[k] = int(_num(cuerpo["escalamiento"][k], k, lo, hi))
        if "riesgo_en_area_sensible" in cuerpo["escalamiento"]:
            e["riesgo_en_area_sensible"] = bool(cuerpo["escalamiento"]["riesgo_en_area_sensible"])
        if any(k in CLAVES_ESCALAMIENTO_RAM for k in cuerpo["escalamiento"]):
            adv.append("Las reglas de la RAM (VH, H en ruta crítica) se cambian en la vista Matriz RAM")
        out["escalamiento"] = e
    if "factores_estado" in cuerpo:
        f = {k: _num(cuerpo["factores_estado"].get(k), f"Factor {k}", 0.1, 5) for k in ("latente", "proximo_a_materializarse", "materializado")}
        if not f["latente"] <= f["proximo_a_materializarse"] <= f["materializado"]:
            adv.append("Los factores no crecen de latente a materializado")
        out["factores_estado"] = f
    if "criterios" in cuerpo:
        cr = cuerpo["criterios"] or {}
        bloque: dict = {}
        for crit in ("vulnerabilidad_territorial", "amenazas_externas"):
            comp = (cr.get(crit) or {}).get("componentes")
            if comp:
                w = {k: _num(v, f"Peso de {k}", 0, 100) for k, v in comp.items()}
                total = sum(w.values())
                if total <= 0:
                    raise ErrorModelo(f"Los componentes de {crit} deben sumar más que cero")
                bloque.setdefault(crit, {})["componentes"] = {k: round(v / total, 4) for k, v in w.items()}
        ext = cr.get("amenazas_externas") or {}
        for k, (lo, hi) in TOPES_EXTERNAS.items():
            if k in ext:
                bloque.setdefault("amenazas_externas", {})[k] = _num(ext[k], k, lo, hi)
        if bloque:
            out["criterios"] = bloque
    return out, adv


def aplicar(params: dict, cambios: dict) -> dict:
    """Parametros vigentes con los cambios propuestos encima (sin guardar)."""
    from comun.config import _fusionar
    p = copy.deepcopy(params)
    for k, v in cambios.items():
        p[k] = _fusionar(p[k], v) if isinstance(v, dict) else v
    return p


def vista_previa(datos: dict, actual: pd.DataFrame, cambios: dict, hoy: pd.Timestamp) -> dict:
    """ICT, nivel y escalamiento de cada paquete con los parametros propuestos, junto a los actuales."""
    from oro import ict as paso
    params = aplicar(cargar_parametros(), cambios)
    tabla, crudos, _, _ = paso.calcular_ict_para_fecha(datos, params, hoy)
    ids = list(tabla.index)
    tabla["nivel"] = tabla["ICT"].apply(lambda v: m_ict.clasificar_ict(v, params["umbrales_criticidad"]))
    tabla = tabla.join(crudos["detalle"]).join(paso.resumen_ram(datos["riesgos"], ids))
    tabla = tabla.join(paso.calcular_escalamiento(datos, params, tabla, hoy))
    nombres = datos["paquetes"].set_index("id_paquete")["nombre"]
    filas = []
    for idp in ids:
        a = actual.loc[idp] if idp in actual.index else None
        filas.append({"id_paquete": idp, "nombre": nombres.get(idp),
                      "ict_actual": None if a is None else float(a["ICT"]), "nivel_actual": None if a is None else a["nivel"],
                      "escala_actual": None if a is None else bool(a["escalamiento"]),
                      "ict": float(tabla.at[idp, "ICT"]), "nivel": tabla.at[idp, "nivel"], "escala": bool(tabla.at[idp, "escalamiento"]),
                      "causas": tabla.at[idp, "causas_escalamiento"]})
    cambia = sum(1 for f in filas if f["nivel"] != f["nivel_actual"])
    return {"paquetes": sorted(filas, key=lambda f: -f["ict"]), "cambian_de_nivel": cambia,
            "en_escalamiento": sum(f["escala"] for f in filas), "pesos": params["pesos"]}


def ahp(matriz: list[list[float]]) -> dict:
    m = np.array(matriz, dtype=float)
    if m.shape != (len(CRITERIOS), len(CRITERIOS)) or (m <= 0).any():
        raise ErrorModelo(f"La matriz AHP debe ser {len(CRITERIOS)} x {len(CRITERIOS)} con valores positivos")
    pesos, cr = m_ahp.calcular_pesos_ahp(m)
    return {"pesos": {k: round(float(w), 4) for k, w in zip(CRITERIOS, pesos)}, "razon_consistencia": round(float(cr), 3),
            "consistente": bool(cr <= 0.10)}


def guardar(bloque: dict, autor: str | None, nota: str | None) -> None:
    contenido = {"version": {"editado_en": datetime.now().isoformat(timespec="seconds"),
                             "editado_por": " ".join(str(autor or "").split())[:80] or None,
                             "nota": " ".join(str(nota or "").split())[:300] or None},
                 **bloque}
    MODELO_PERSONALIZADO_PATH.write_text(
        "# Pesos, umbrales, reglas y topes del ICT editados desde la aplicacion (vista Ajustar el modelo).\n"
        "# Se aplican encima de parametros.yaml; borrar este archivo (o 'Volver a la base') devuelve la base.\n"
        + yaml.safe_dump(contenido, allow_unicode=True, sort_keys=False), encoding="utf-8")
    historial.registrar("modelo", "guardar", autor, nota, editables(cargar_parametros()))


def borrar(autor: str | None = None) -> bool:
    if not MODELO_PERSONALIZADO_PATH.exists():
        return False
    MODELO_PERSONALIZADO_PATH.unlink()
    historial.registrar("modelo", "volver a la base", autor, None, editables(cargar_parametros()))
    return True
