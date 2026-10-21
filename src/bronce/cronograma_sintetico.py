"""Cronograma sintetico: actividades de cada paquete, con su peso, sus fechas planeadas y proyectadas y su avance.

Es lo que exportaria una herramienta de planeacion (Primavera, MS Project o un Excel con WBS): para cada paquete de
trabajo, una lista ordenada de actividades. Todo lo demas (avance del paquete, avance del proyecto, fechas proyectadas
de cada nivel) se calcula hacia arriba a partir de estas filas.

Como se construye (todo con su propio generador aleatorio, para no alterar el resto de los datos sinteticos):
  * Cada proyecto termina en una fecha base (`fecha_fin_plan`). Cada paquete termina `holgura_dias` antes que su
    proyecto (los de ruta critica, el mismo dia): asi la holgura y las fechas cuentan la misma historia.
  * La duracion de cada paquete sale hacia atras desde su fecha de fin; asi se sabe cuanto deberia llevar hecho hoy.
  * El avance real va un poco por detras del planeado (lo normal en obra) y se reparte entre las actividades en orden:
    las primeras estan completadas, una esta en curso y las demas por iniciar.
  * Las fechas proyectadas de lo que falta salen del ritmo real del paquete (dias de calendario por unidad de trabajo).
El registro llega "sucio" como un export real: estados escritos de varias formas, algunos avances en porcentaje (0 a 100)
y alguna fila repetida. Plata lo normaliza.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

DIAS_POR_MES = 30.4375

# (clave, nombre, disciplina, peso base). El orden es el de ejecucion.
ACTIVIDADES = [
    ("ingenieria", "Ingeniería de detalle", "Ingeniería", 0.10),
    ("social", "Gestión social y consulta previa", "Social", 0.12),
    ("ambiental", "Licencias y permisos ambientales", "Ambiental", 0.08),
    ("compras", "Adquisición de equipos y materiales", "Compras", 0.20),
    ("civil", "Obras civiles y cimentaciones", "Civil", 0.20),
    ("montaje", "Montaje electromecánico", "Electromecánica", 0.18),
    ("pruebas", "Pruebas y puesta en servicio", "Puesta en servicio", 0.08),
    ("cierre", "Cierre, documentación y entrega", "Gestión", 0.04),
]
OBLIGATORIAS = {"compras", "montaje", "pruebas"}      # todo paquete las tiene; las demas se sortean


def _sumar(f: date, dias: float) -> date:
    return f + timedelta(days=int(round(dias)))


def _ensuciar_estado(valor: str, r: np.random.Generator, prob: float = 0.18) -> str:
    if r.random() < prob:
        return random.Random(int(r.integers(1_000_000))).choice([valor.upper(), valor.replace("_", " ").title(), f" {valor} ", valor.capitalize()])
    return valor


def generar(gdf_paquetes: pd.DataFrame, hoy: date, semilla: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Devuelve (cronograma por paquete, actividades, fechas planeadas por proyecto).

    `hoy` es la fecha de corte del dato: el avance y las fechas proyectadas son las de ese dia.
    """
    base = np.random.default_rng(semilla + 7)     # misma secuencia que el cronograma anterior: duracion, avance, holgura, costo, presupuesto
    r = np.random.default_rng(semilla + 13)       # todo lo nuevo (fechas, actividades) usa su propio generador

    paquetes = []
    for _, p in gdf_paquetes.iterrows():
        duracion = int(base.integers(8, 25))
        base.uniform(0.1, 0.7)                    # el avance ya no se sortea: sale de las actividades (se conserva la secuencia)
        critico = bool(p["ruta_critica"])
        holgura = 0 if critico else int(base.integers(10, 46))
        paquetes.append({
            "id_paquete": p["id_paquete"], "id_proyecto": p["id_proyecto"], "critico": critico, "duracion_meses": duracion,
            "holgura_dias": holgura, "costo_dia_parada_usd": int(base.integers(15, 91)) * 1000,
            "presupuesto_usd": int(base.integers(8, 61)) * 1_000_000,
        })
    paquetes = pd.DataFrame(paquetes)

    filas_cron, filas_act, filas_proy = [], [], []
    for id_proyecto, grupo in paquetes.groupby("id_proyecto", sort=True):
        dias_min = float((grupo["duracion_meses"] * DIAS_POR_MES).min())
        fin_proyecto = _sumar(hoy, r.uniform(0.40, 0.62) * dias_min)       # el paquete mas corto lleva entre ~40 y ~60 % hecho
        inicio_proyecto = fin_proyecto
        for _, q in grupo.iterrows():
            dias = int(round(q["duracion_meses"] * DIAS_POR_MES))
            fin = fin_proyecto - timedelta(days=int(q["holgura_dias"]))
            inicio = fin - timedelta(days=dias)
            inicio_proyecto = min(inicio_proyecto, inicio)
            planeado = (hoy - inicio).days / dias                                   # fraccion del tiempo transcurrida
            avance = float(np.clip(planeado - r.uniform(-0.02, 0.09), 0.03, 0.97))   # casi siempre un poco por detras
            retraso_inicio = int(min(r.integers(0, 21), max((hoy - inicio).days - 1, 0)))
            inicio_real = inicio + timedelta(days=retraso_inicio)
            transcurrido = max((hoy - inicio_real).days, 1)
            ritmo = float(np.clip(transcurrido / (avance * dias), 0.9, 1.35))       # dias de calendario por dia de trabajo planeado

            # actividades del paquete, en orden de ejecucion
            extra = [a for a in ACTIVIDADES if a[0] not in OBLIGATORIAS]
            n = int(r.integers(5, 8))
            elegidas = {a[0] for a in ACTIVIDADES if a[0] in OBLIGATORIAS}
            for a in r.permutation(len(extra))[: n - len(elegidas)]:
                elegidas.add(extra[int(a)][0])
            lista = [a for a in ACTIVIDADES if a[0] in elegidas]
            pesos = np.array([a[3] * r.uniform(0.8, 1.25) for a in lista])
            pesos = np.round(pesos / pesos.sum(), 4)
            pesos[-1] = round(1 - pesos[:-1].sum(), 4)

            acum = 0.0
            for orden, (a, w) in enumerate(zip(lista, pesos), start=1):
                c0, c1 = acum, acum + float(w)
                acum = c1
                ini_plan, fin_plan = _sumar(inicio, c0 * dias), _sumar(inicio, c1 * dias)
                if c1 <= avance:
                    av, estado = 1.0, "completada"
                elif c0 >= avance:
                    av, estado = 0.0, "por_iniciar"
                else:
                    av, estado = round((avance - c0) / float(w), 3), "en_curso"
                a_real = lambda c: _sumar(inicio_real, c / avance * transcurrido)   # tiempo en que se alcanzo la fraccion c
                a_fut = lambda c: _sumar(hoy, (c - avance) * dias * ritmo)          # tiempo proyectado para la fraccion c
                ini_real = fin_real = None
                if estado == "completada":
                    ini_real, fin_real = a_real(c0), a_real(c1)
                    ini_proy, fin_proy = ini_real, fin_real
                elif estado == "en_curso":
                    ini_real = a_real(c0)
                    ini_proy, fin_proy = ini_real, a_fut(c1)
                else:
                    ini_proy, fin_proy = a_fut(c0), a_fut(c1)
                filas_act.append({
                    "id_actividad": f"{q['id_paquete']}-A{orden:02d}", "id_paquete": q["id_paquete"], "id_proyecto": id_proyecto,
                    "orden": orden, "nombre": a[1], "disciplina": a[2], "peso_en_paquete": float(w),
                    "fecha_inicio_plan": ini_plan.isoformat(), "fecha_fin_plan": fin_plan.isoformat(),
                    "avance": av, "estado": estado,
                    "fecha_inicio_real": ini_real.isoformat() if ini_real else None,
                    "fecha_fin_real": fin_real.isoformat() if fin_real else None,
                    "fecha_inicio_proyectada": ini_proy.isoformat(), "fecha_fin_proyectada": fin_proy.isoformat(),
                    "fecha_corte": hoy.isoformat(),
                })
            filas_cron.append({
                "id_paquete": q["id_paquete"], "fecha_inicio_plan": inicio.isoformat(), "fecha_fin_plan": fin.isoformat(),
                "holgura_dias": int(q["holgura_dias"]), "costo_dia_parada_usd": int(q["costo_dia_parada_usd"]),
                "presupuesto_usd": int(q["presupuesto_usd"]), "fecha_corte": hoy.isoformat(),
            })
        filas_proy.append({"id_proyecto": id_proyecto, "fecha_inicio_plan": inicio_proyecto.isoformat(), "fecha_fin_plan": fin_proyecto.isoformat()})

    act = pd.DataFrame(filas_act)
    # el export llega sucio: estado escrito de varias formas, algunos avances en porcentaje (0 a 100) y filas repetidas
    act["estado"] = [_ensuciar_estado(v, r) for v in act["estado"]]
    en_pct = r.random(len(act)) < 0.06
    act["avance"] = np.where(en_pct, (act["avance"] * 100).round(1), act["avance"])
    repetidas = act.sample(n=max(2, int(len(act) * 0.03)), random_state=semilla)
    act = pd.concat([act, repetidas], ignore_index=True).sort_values(["id_paquete", "orden"], kind="stable").reset_index(drop=True)
    return pd.DataFrame(filas_cron), act, pd.DataFrame(filas_proy)
