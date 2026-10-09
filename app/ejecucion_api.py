"""Riesgo de ejecucion en la aplicacion: resultados guardados, escenarios en vivo y supuestos editables.

* Los resultados vienen de la capa Oro (paso oro.ejecucion).
* Un escenario ("¿y si llueve mas?", "¿y sin controles?") vuelve a simular en memoria con las mismas entradas, sin
  guardar nada: tarda menos de un segundo.
* Los supuestos editados se guardan en ejecucion_personalizada.yaml (los de parametros.yaml no se tocan); para que el
  mapa y Explorar los usen hay que recalcular el paso oro.ejecucion.
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import yaml

from comun.config import EJECUCION_PERSONALIZADA_PATH, ORO, cargar_parametros
from comun.serializacion import sin_nan

LETRAS = ("A", "B", "C", "D", "E")
DIMS = ("PE", "EC", "MA", "CL", "IM")
CATEGORIAS = ("seguridad_fisica", "climatico", "social_comunidad", "logistico_acceso", "ambiental", "contractual")
_entradas: dict = {}


class ErrorSupuestos(ValueError):
    pass


def _num(v, campo, lo, hi) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError) as e:
        raise ErrorSupuestos(f"{campo}: debe ser un número") from e
    if not lo <= x <= hi:
        raise ErrorSupuestos(f"{campo}: debe estar entre {lo} y {hi}")
    return int(x) if x.is_integer() else x


def validar(s: dict) -> tuple[dict, list[str]]:
    """Valida los supuestos editables. Devuelve (bloque `ejecucion` a guardar, advertencias)."""
    out: dict = {}
    adv: list[str] = []
    if "lambda_por_letra" in s:
        lam = {l: _num(s["lambda_por_letra"].get(l), f"Frecuencia {l}", 0, 20) for l in LETRAS}
        if any(lam[b] < lam[a] for a, b in zip(LETRAS, LETRAS[1:])):
            adv.append("La frecuencia no crece de A a E: una letra más probable daría menos eventos")
        out["lambda_por_letra"] = lam
    for k, lo, hi in (("gamma", 0, 2), ("multiplicador_max", 1, 20), ("tolerancia_dias_paquete", 0, 730),
                      ("tolerancia_dias_proyecto", 0, 730), ("fraccion_consumida_materializado", 0, 1),
                      ("simulaciones", 1000, 50000), ("radio_vias_km", 1, 50), ("solapamiento", 0, 1)):
        if k in s:
            out[k] = _num(s[k], k, lo, hi)
    if "simulaciones" in out:
        out["simulaciones"] = int(out["simulaciones"])
    if "factor_estado" in s:
        out["factor_estado"] = {"latente": 1.0, "proximo_a_materializarse": _num(s["factor_estado"].get("proximo_a_materializarse"), "Factor próximo a materializarse", 1, 10)}
    if "choques" in s:
        out["choques"] = {g: _num(s["choques"].get(g), f"Choque {g}", 0, 3) for g in ("clima", "social")}
    if "dias_por_consecuencia" in s:
        tabla = {}
        for d in DIMS:
            fila = s["dias_por_consecuencia"].get(d)
            if not isinstance(fila, list) or len(fila) != 6:
                raise ErrorSupuestos(f"Días {d}: se esperan 6 valores (consecuencia 0 a 5)")
            tabla[d] = [_num(x, f"Días {d} nivel {i}", 0, 730) for i, x in enumerate(fila)]
            if any(b < a for a, b in zip(tabla[d], tabla[d][1:])):
                adv.append(f"Días {d}: una consecuencia más grave daría menos días")
        out["dias_por_consecuencia"] = tabla
    if "covariables" in s:
        cov = {}
        for c in CATEGORIAS:
            betas = (s["covariables"] or {}).get(c) or {}
            cov[c] = {k: _num(v, f"Peso {k} ({c})", -5, 5) for k, v in betas.items()}
        out["covariables"] = cov
    return out, adv


def guardar(bloque: dict, editado_por: str | None, nota: str | None) -> None:
    contenido = {"version": {"editado_en": datetime.now().isoformat(timespec="seconds"),
                             "editado_por": " ".join(str(editado_por or "").split())[:80] or None,
                             "nota": " ".join(str(nota or "").split())[:300] or None},
                 "ejecucion": bloque}
    EJECUCION_PERSONALIZADA_PATH.write_text(
        "# Supuestos del modelo de riesgo de ejecucion editados desde la aplicacion. Reemplazan a los de parametros.yaml.\n"
        "# Borrar este archivo (o 'Volver a los supuestos base' en la vista) devuelve los de parametros.yaml.\n"
        + yaml.safe_dump(contenido, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _entradas.clear()


def borrar() -> bool:
    _entradas.clear()
    if EJECUCION_PERSONALIZADA_PATH.exists():
        EJECUCION_PERSONALIZADA_PATH.unlink()
        return True
    return False


def resultados() -> dict:
    """Lo que publico el paso oro.ejecucion, mas los supuestos vigentes y los base."""
    if not (ORO / "ejecucion_paquetes.csv").exists():
        return {"disponible": False}
    leer = lambda n: json.loads(pd.read_csv(ORO / n).to_json(orient="records"))  # noqa: E731
    return sin_nan({
        "disponible": True,
        "resumen": json.loads((ORO / "ejecucion_resumen.json").read_text(encoding="utf-8")),
        "proyectos": leer("ejecucion_proyectos.csv"), "paquetes": leer("ejecucion_paquetes.csv"), "riesgos": leer("ejecucion_riesgos.csv"),
        "supuestos": cargar_parametros()["ejecucion"], "supuestos_base": cargar_parametros(oficial=True)["ejecucion"],
        "personalizados": EJECUCION_PERSONALIZADA_PATH.exists(),
    })


def simular(cuerpo: dict) -> dict:
    """Escenario en memoria: supuestos editados (sin guardar) + factores por categoria + con o sin controles."""
    from oro import ejecucion as paso
    base = cargar_parametros()["ejecucion"]
    cambios, adv = validar(cuerpo.get("supuestos") or {})
    cfg = {**base, **cambios}
    if "entradas" not in _entradas or _entradas.get("radio") != cfg.get("radio_vias_km"):
        _entradas.update(entradas=paso.cargar_entradas(cfg), radio=cfg.get("radio_vias_km"))
    esc_in = cuerpo.get("escenario") or {}
    escenario = {"factor": {c: _num(v, f"Factor {c}", 0, 10) for c, v in (esc_in.get("factor") or {}).items() if c in CATEGORIAS},
                 "controles": "inherente" if esc_in.get("controles") == "inherente" else "residual"}
    res = paso.correr(_entradas["entradas"], cfg, escenario, n=min(int(cfg.get("simulaciones", 10000)), 10000))
    t = res["tabla"]
    top = t[t["lambda"] > 0].sort_values("atraso_esperado", ascending=False).head(12)
    return sin_nan({"proyectos": json.loads(res["proyectos"].round(2).to_json(orient="records")),
                    "paquetes": json.loads(res["paquetes"].round(2).to_json(orient="records")),
                    "portafolio": res["portafolio"], "histogramas": res["histogramas"], "advertencias": adv,
                    "top_riesgos": json.loads(top[["id_riesgo", "id_paquete", "categoria", "ram_residual", "probabilidad",
                                                   "dias_por_evento", "atraso_esperado", "multiplicador_territorial"]].round(4).to_json(orient="records"))})


def olvidar_entradas() -> None:
    _entradas.clear()
