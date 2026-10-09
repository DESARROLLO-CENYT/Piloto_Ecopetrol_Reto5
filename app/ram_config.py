"""Edicion de la matriz RAM desde la aplicacion (vista "Matriz RAM").

La matriz oficial vive en parametros.yaml y no se toca: lo que se edita se guarda en ram_personalizada.yaml (ver
comun.config.cargar_parametros, que la superpone). Borrar ese archivo devuelve la oficial.

Se puede editar: el nivel de cada celda, la descripcion de cada probabilidad, de cada nivel de consecuencia por dimension,
la decision, quien aprueba y el puntaje de cada nivel, y las dos reglas de escalamiento de la RAM. La validacion rechaza lo
que romperia el modelo (celdas con niveles desconocidos, puntajes no numericos) y avisa de lo que es valido pero raro (un
nivel que baja cuando la consecuencia o la probabilidad suben).

Recalcular corre los pasos del pipeline que dependen del registro de riesgos (plata.sinteticos y lo que le sigue), en un
hilo aparte, sin descargas.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

import yaml

from comun.config import CLAVES_ESCALAMIENTO_RAM, RAM_PERSONALIZADA_PATH, cargar_parametros

NIVELES = ("N", "L", "M", "H", "VH")
LETRAS = ("A", "B", "C", "D", "E")
DIMENSIONES = ("PE", "EC", "MA", "CL", "IM")
MAX_TEXTO = 300


class ErrorRam(ValueError):
    pass


def _texto(v, campo: str) -> str:
    s = " ".join(str(v or "").split())
    if not s:
        raise ErrorRam(f"{campo}: no puede quedar vacío")
    if len(s) > MAX_TEXTO:
        raise ErrorRam(f"{campo}: máximo {MAX_TEXTO} caracteres")
    return s


def validar(cuerpo: dict) -> tuple[dict, list[str]]:
    """Limpia y valida lo que envia la vista. Devuelve (contenido del archivo, advertencias)."""
    try:
        m = cuerpo["matriz"]
        matriz = {c: [str(m[str(c)][i] if str(c) in m else m[c][i]).upper() for i in range(5)] for c in range(6)}
    except (KeyError, IndexError, TypeError) as e:
        raise ErrorRam("La matriz debe tener 6 filas (consecuencia 0 a 5) y 5 columnas (probabilidad A a E)") from e
    for c, fila in matriz.items():
        malos = [n for n in fila if n not in NIVELES]
        if malos:
            raise ErrorRam(f"Fila {c}: niveles desconocidos {malos} (válidos: {', '.join(NIVELES)})")

    probabilidades = {l: _texto((cuerpo.get("probabilidades") or {}).get(l), f"Probabilidad {l}") for l in LETRAS}
    consecuencias = {}
    for d in DIMENSIONES:
        tabla = (cuerpo.get("consecuencias") or {}).get(d) or {}
        consecuencias[d] = {c: _texto(tabla.get(str(c), tabla.get(c)), f"Consecuencia {d} {c}") for c in range(6)}
    niveles = {}
    for n in NIVELES:
        v = (cuerpo.get("niveles") or {}).get(n) or {}
        try:
            puntaje = float(v.get("puntaje"))
        except (TypeError, ValueError) as e:
            raise ErrorRam(f"Nivel {n}: el puntaje debe ser un número") from e
        if not 0 < puntaje <= 100:
            raise ErrorRam(f"Nivel {n}: el puntaje debe estar entre 0 y 100")
        niveles[n] = {"nombre": _texto(v.get("nombre"), f"Nivel {n}, nombre"), "puntaje": int(puntaje) if puntaje.is_integer() else puntaje,
                      "decision": _texto(v.get("decision"), f"Nivel {n}, decisión"), "aprueba": _texto(v.get("aprueba"), f"Nivel {n}, quién aprueba")}
    esc = {k: bool((cuerpo.get("escalamiento") or {}).get(k, True)) for k in CLAVES_ESCALAMIENTO_RAM}

    advertencias = []
    orden = {n: i for i, n in enumerate(NIVELES)}
    for c in range(6):
        for i in range(4):
            if orden[matriz[c][i + 1]] < orden[matriz[c][i]]:
                advertencias.append(f"Consecuencia {c}: el nivel baja de {LETRAS[i]} ({matriz[c][i]}) a {LETRAS[i + 1]} ({matriz[c][i + 1]}) aunque la probabilidad sube")
    for i in range(5):
        for c in range(5):
            if orden[matriz[c + 1][i]] < orden[matriz[c][i]]:
                advertencias.append(f"Probabilidad {LETRAS[i]}: el nivel baja de {c} ({matriz[c][i]}) a {c + 1} ({matriz[c + 1][i]}) aunque la consecuencia sube")
    pts = [niveles[n]["puntaje"] for n in NIVELES]
    if any(b <= a for a, b in zip(pts, pts[1:])):
        advertencias.append("Los puntajes no crecen de N a VH: el ICT trataría un nivel más grave como menos severo")

    contenido = {
        "version": {"editado_en": datetime.now().isoformat(timespec="seconds"),
                    "editado_por": " ".join(str(cuerpo.get("editado_por") or "").split())[:80] or None,
                    "nota": " ".join(str(cuerpo.get("nota") or "").split())[:MAX_TEXTO] or None},
        "ram": {"matriz": matriz, "probabilidades": probabilidades, "consecuencias": consecuencias, "niveles": niveles},
        "escalamiento": esc,
    }
    return contenido, advertencias


def guardar(contenido: dict) -> None:
    texto = ("# Matriz RAM editada desde la aplicacion (vista Matriz RAM). Reemplaza a la oficial de parametros.yaml.\n"
             "# Borrar este archivo (o 'Restaurar la oficial' en la vista) devuelve la oficial.\n")
    texto += yaml.safe_dump(contenido, allow_unicode=True, sort_keys=False)
    RAM_PERSONALIZADA_PATH.write_text(texto, encoding="utf-8")


def borrar() -> bool:
    if RAM_PERSONALIZADA_PATH.exists():
        RAM_PERSONALIZADA_PATH.unlink()
        return True
    return False


def resumen() -> dict:
    """Lo que necesita la vista: la oficial y la vigente (con las reglas de escalamiento de la RAM)."""
    def parte(p):
        return {"ram": p["ram"], "escalamiento": {k: p["escalamiento"].get(k, True) for k in CLAVES_ESCALAMIENTO_RAM}}
    return {"oficial": parte(cargar_parametros(oficial=True)), "vigente": parte(cargar_parametros()),
            "personalizada": RAM_PERSONALIZADA_PATH.exists()}


# ---------------------------------------------------------------------------
# Recalculo en segundo plano
# ---------------------------------------------------------------------------

_trabajo: dict = {"estado": "inactivo"}
_candado = threading.Lock()


def estado_recalculo() -> dict:
    return dict(_trabajo)


def ocupado() -> bool:
    return _trabajo.get("estado") == "corriendo"


def correr_trabajo(pasos, al_terminar=None, nombre: str = "recalculo", despues=None) -> dict:
    """Corre esos pasos del pipeline en segundo plano. Hay un solo trabajo a la vez para toda la aplicacion (matriz RAM,
    supuestos, modelo, tarea diaria): dos recalculos a la vez se pisarian los archivos. `despues(estado)` corre al final,
    antes de recargar (por ejemplo, enviar las alertas)."""
    import pipeline
    with _candado:
        if ocupado():
            raise ErrorRam("Ya hay un recálculo en curso")
        _trabajo.clear()
        _trabajo.update(estado="corriendo", nombre=nombre, inicio=datetime.now().isoformat(timespec="seconds"),
                        pasos=[p.id for p in pasos], hechos=[], fallos=[])

    def correr():
        t0 = time.time()
        for p in pasos:
            ok = pipeline.correr(p)
            _trabajo["hechos"].append(p.id)
            if not ok:
                _trabajo["fallos"].append(p.id)
                if p.obligatorio:
                    break
        if despues:
            try:
                _trabajo["resultado"] = despues(dict(_trabajo))
            except Exception as e:  # noqa: BLE001 - se reporta en el estado
                _trabajo["fallos"].append(f"{nombre}: {e}")
        if al_terminar:
            try:
                al_terminar()
            except Exception as e:  # noqa: BLE001 - se reporta en el estado
                _trabajo["fallos"].append(f"recargar: {e}")
        _trabajo.update(estado="error" if _trabajo["fallos"] else "listo", fin=datetime.now().isoformat(timespec="seconds"),
                        segundos=round(time.time() - t0))

    threading.Thread(target=correr, daemon=True).start()
    return estado_recalculo()


def recalcular(al_terminar=None, fuentes: tuple[str, ...] = ("sinteticos",)) -> dict:
    """Corre los pasos de esas fuentes (sin Bronce) y todo lo que depende de ellos, sin descargas. Uno a la vez.
    Por defecto, plata.sinteticos y lo que le sigue (la matriz RAM cambia el registro); para los supuestos del modelo de
    riesgo de ejecucion basta ("ejecucion",); para los pesos y umbrales del ICT, ("ict",)."""
    import pipeline
    pasos = [p for p in pipeline.seleccionar(fuentes=list(fuentes), sin_red=True) if p.capa != "bronce"]
    return correr_trabajo(pasos, al_terminar, nombre="recalculo")
