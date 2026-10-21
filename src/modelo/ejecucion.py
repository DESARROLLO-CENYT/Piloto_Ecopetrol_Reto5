"""Modelo de riesgo de ejecucion: dias de atraso y USD de sobrecosto por paquete y proyecto, con su probabilidad.

Formulacion (detalle en docs/MODELO_EJECUCION.md; parametros en parametros.yaml -> ejecucion):

  1. Frecuencia de cada amenaza abierta i (eventos por ano):
         lambda_i = lambda0(letra RAM residual) * exp( gamma * sum_k beta_k * z_k ) * f_estado
     z = covariables del territorio del paquete (0 = promedio de La Guajira), beta segun la categoria del riesgo.
     El multiplicador territorial se limita a [1/m, m].
  2. Probabilidad en el horizonte T:  P_i = 1 - exp(-lambda_i * T)
     T = lo que le falta a la actividad a la que pega el riesgo: de la fecha de corte (o de su inicio proyectado, si aun
     no empieza) a su fin proyectado; 0 si ya termino. Sin actividad conocida, lo que le falta al paquete.
  3. Dias por evento: Triangular(0,5 D, D, 2 D), D = max_k dias(k, consecuencia RAM_ik)  (manda la peor dimension)
     Costo por evento: LogUniforme(banda USD de la consecuencia Economica) + costo diario de parada * dias
  4. Simulacion: N_i^s ~ Poisson(lambda_i * T * W_g^s); W_g = choque comun (Gamma, media 1) que comparten los riesgos
     de un grupo (clima por municipio, social por proyecto). La suma de N eventos se aproxima con una normal con la media
     y la varianza exactas (cortada en 0).
  5. Paquete: D_p = sum_i dias + atraso ya consumido (riesgos materializados).
     Proyecto: D = sum_p max(0, D_p - holgura_p)   (los paquetes de ruta critica tienen holgura 0)
  6. IRE (indice de riesgo de ejecucion, 0-100) = 100 * P(D > holgura + tolerancia).

Las amenazas materializadas no tienen probabilidad: una fraccion de su atraso y de su costo potenciales (la RAM registra la
peor consecuencia creible) cuenta como ya consumida.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

LETRAS = "ABCDE"
DIMS = {"PE": "cons_personas", "EC": "cons_economica", "MA": "cons_ambiental", "CL": "cons_clientes", "IM": "cons_imagen"}
TRI_MEDIA = (0.5 + 1 + 2) / 3                                  # media de Triangular(0,5, 1, 2)
TRI_VAR = (0.5 ** 2 + 1 + 4 - 0.5 - 1 - 2) / 18                 # varianza de Triangular(0,5, 1, 2)
CHOQUE = {"climatico": "clima", "logistico_acceso": "clima", "social_comunidad": "social"}


# ---------------------------------------------------------------------------
# Piezas
# ---------------------------------------------------------------------------

def multiplicador_territorial(categoria: str, z: dict, cfg: dict) -> float:
    betas = (cfg.get("covariables") or {}).get(categoria) or {}
    s = sum(b * float(z.get(k, 0.0) or 0.0) for k, b in betas.items())
    m = float(cfg.get("multiplicador_max", 3.0))
    return float(np.clip(math.exp(float(cfg.get("gamma", 0.5)) * s), 1 / m, m))


def dias_por_evento(consecuencias: dict, cfg: dict) -> float:
    """Valor mas probable de dias de atraso de un evento: la peor dimension."""
    tabla = cfg["dias_por_consecuencia"]
    return max((float(tabla[d][int(c)]) for d, c in consecuencias.items() if c is not None and not pd.isna(c)), default=0.0)


def momentos_costo_directo(nivel, cfg: dict) -> tuple[float, float]:
    """Media y varianza del costo directo (log-uniforme dentro de la banda USD del nivel economico)."""
    if nivel is None or pd.isna(nivel):
        return 0.0, 0.0
    lo, hi = (float(x) for x in cfg["costo_directo_usd"][int(nivel)])
    if hi <= 0:
        return 0.0, 0.0
    if hi <= lo * 1.0001:
        return lo, 0.0
    ln = math.log(hi / lo)
    media = (hi - lo) / ln
    m2 = (hi ** 2 - lo ** 2) / (2 * ln)
    return media, max(m2 - media ** 2, 0.0)


# ---------------------------------------------------------------------------
# Tabla de riesgos con todo lo que necesita la simulacion
# ---------------------------------------------------------------------------

def horizonte_actividad(act: pd.Series, corte: pd.Timestamp) -> float:
    """Anos durante los que un riesgo puede pegarle a su actividad: lo que le falta por ejecutarse desde el corte."""
    if act.get("estado") == "completada":
        return 0.0
    ini = max(pd.Timestamp(corte), pd.Timestamp(act["fecha_inicio_proyectada"]))
    return max(0.0, (pd.Timestamp(act["fecha_fin_proyectada"]) - ini).days) / 365.25


def preparar_riesgos(riesgos: pd.DataFrame, paquetes: pd.DataFrame, z: pd.DataFrame, cfg: dict,
                     piso_ambiental: pd.Series | None = None, escenario: dict | None = None,
                     actividades: pd.DataFrame | None = None, corte: pd.Timestamp | None = None) -> pd.DataFrame:
    """Una fila por amenaza (abierta o materializada) con frecuencia, probabilidad, dias, costo y valor esperado.

    paquetes: indice id_paquete; columnas meses_restantes, costo_dia_parada_usd, id_proyecto, codigo_municipio.
    z: indice id_paquete; una columna por covariable territorial.
    piso_ambiental: consecuencia ambiental minima que sugiere el territorio (area protegida cercana), por paquete.
    escenario: {"factor": {categoria: x}} multiplica la frecuencia; {"controles": "inherente"} ignora los controles.
    actividades: indice id_actividad; columnas nombre, estado, fecha_inicio_proyectada, fecha_fin_proyectada. Con ellas (y
    `corte`), el horizonte de cada riesgo es el de su actividad; sin ellas, el del paquete.
    """
    escenario = escenario or {}
    factor_cat = escenario.get("factor") or {}
    sin_controles = escenario.get("controles") == "inherente"
    lam0 = {k: float(v) for k, v in cfg["lambda_por_letra"].items()}
    f_estado = cfg.get("factor_estado") or {}
    horizonte_def = float(cfg.get("horizonte_meses_por_defecto", 12)) / 12
    frac_cons = float(cfg.get("fraccion_consumida_materializado", 0.35))

    filas = []
    amen = riesgos[(riesgos["tipo"] == "amenaza") & riesgos["probabilidad_residual"].notna()]
    for _, r in amen.iterrows():
        p = r["id_paquete_trabajo"]
        if p not in paquetes.index:
            continue
        info = paquetes.loc[p]
        cons = {d: r.get(col) for d, col in DIMS.items()}
        if r["categoria"] == "ambiental" and piso_ambiental is not None and pd.notna(piso_ambiental.get(p)):
            if cons["MA"] is None or pd.isna(cons["MA"]) or cons["MA"] < piso_ambiental[p]:
                cons["MA"] = int(piso_ambiental[p])            # el area protegida cercana sube la consecuencia ambiental
        dias = dias_por_evento(cons, cfg)
        cd_media, cd_var = momentos_costo_directo(cons.get("EC"), cfg)
        costo_dia = float(info.get("costo_dia_parada_usd", 0) or 0)
        zp = z.loc[p].to_dict() if p in z.index else {}
        mult = multiplicador_territorial(r["categoria"], zp, cfg)
        letra = r["probabilidad"] if sin_controles else r["probabilidad_residual"]
        estado = r["estado"]
        futuro = estado != "materializado"
        id_act = r.get("id_actividad")
        if actividades is not None and corte is not None and pd.notna(id_act) and id_act in actividades.index:
            T, origen_T = horizonte_actividad(actividades.loc[id_act], corte), "actividad"
        else:
            T = float(info.get("meses_restantes", np.nan)) / 12 if pd.notna(info.get("meses_restantes")) else horizonte_def
            origen_T = "paquete"
        fx = float(factor_cat.get(r["categoria"], 1.0))
        lam = lam0[letra] * mult * float(f_estado.get(estado, 1.0)) * fx if futuro else 0.0
        lam_inh = lam0[r["probabilidad"]] * mult * float(f_estado.get(estado, 1.0)) * fx if futuro else 0.0
        lam_res = lam0[r["probabilidad_residual"]] * mult * float(f_estado.get(estado, 1.0)) * fx if futuro else 0.0
        costo_evento = cd_media + costo_dia * dias * TRI_MEDIA
        grupo = CHOQUE.get(r["categoria"])
        filas.append({
            "id_riesgo": r["id_riesgo"], "id_paquete": p, "id_proyecto": info.get("id_proyecto"), "categoria": r["categoria"],
            "id_actividad": id_act if pd.notna(id_act) else None,
            "actividad": actividades.at[id_act, "nombre"] if origen_T == "actividad" else None,
            "estado": estado, "nivel_residual": r.get("nivel_residual"), "ram_residual": r.get("ram_residual"),
            "letra": letra, "lambda0": lam0[letra], "multiplicador_territorial": round(mult, 3), "lambda": lam,
            "horizonte_anios": round(T, 3), "horizonte_origen": origen_T, "probabilidad": 1 - math.exp(-lam * T) if futuro else 1.0,
            "dias_por_evento": dias, "costo_directo_medio": cd_media, "costo_directo_var": cd_var, "costo_dia": costo_dia,
            "atraso_esperado": lam * T * dias * TRI_MEDIA if futuro else 0.0,
            "costo_esperado": lam * T * costo_evento if futuro else 0.0,
            "atraso_evitado_por_controles": max(lam_inh - lam_res, 0.0) * T * dias * TRI_MEDIA,
            "consumido_dias": 0.0 if futuro else dias * frac_cons,
            "consumido_usd": 0.0 if futuro else (cd_media + costo_dia * dias) * frac_cons,
            "grupo_choque": None if grupo is None else (f"clima:{info.get('codigo_municipio')}" if grupo == "clima" else f"social:{info.get('id_proyecto')}"),
            "tipo_choque": grupo,
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Simulacion Monte Carlo
# ---------------------------------------------------------------------------

def _cuantiles(x: np.ndarray) -> dict:
    return {"media": float(x.mean()), "p50": float(np.percentile(x, 50)), "p80": float(np.percentile(x, 80)),
            "p90": float(np.percentile(x, 90))}


def simular(tabla: pd.DataFrame, paquetes: pd.DataFrame, cfg: dict, n: int | None = None, semilla: int | None = None,
            tolerancia_paquete: float | None = None, tolerancia_proyecto: float | None = None, bins: int = 30) -> dict:
    """Simula n escenarios. Devuelve resumen por paquete, por proyecto y del portafolio, con histogramas."""
    n = int(n or cfg.get("simulaciones", 10000))
    rng = np.random.default_rng(cfg.get("semilla", 42) if semilla is None else semilla)
    tol_p = float(cfg.get("tolerancia_dias_paquete", 15) if tolerancia_paquete is None else tolerancia_paquete)
    tol_y = float(cfg.get("tolerancia_dias_proyecto", 30) if tolerancia_proyecto is None else tolerancia_proyecto)
    ids_p = list(paquetes.index)
    pos = {p: k for k, p in enumerate(ids_p)}

    fut = tabla[tabla["lambda"] > 0].reset_index(drop=True) if len(tabla) else tabla
    I = len(fut)
    suma_pq = np.zeros((len(ids_p), n))      # sin solapamiento: lo que reproduce el valor esperado analitico
    mayor_pq = np.zeros((len(ids_p), n))     # el mayor atraso de un solo evento futuro en cada escenario
    costo_pq = np.zeros((len(ids_p), n))
    alfa = float(cfg.get("solapamiento", 1.0))
    if I:
        # choques comunes: un W por grupo y escenario
        W = np.ones((I, n))
        sigmas = cfg.get("choques") or {}
        for g, idx in fut.groupby("grupo_choque").groups.items():
            tipo = fut.loc[idx[0], "tipo_choque"]
            s = float(sigmas.get(tipo, 0) or 0)
            if s > 0:
                k = 1 / s ** 2
                W[list(idx), :] = rng.gamma(k, 1 / k, size=n)[None, :]
        mu = (fut["lambda"] * fut["horizonte_anios"]).to_numpy()[:, None] * W
        N = rng.poisson(mu).astype(float)
        D = fut["dias_por_evento"].to_numpy()[:, None]
        dias = np.clip(N * D * TRI_MEDIA + np.sqrt(N * TRI_VAR) * D * rng.standard_normal((I, n)), 0, None)
        directo = np.clip(N * fut["costo_directo_medio"].to_numpy()[:, None]
                          + np.sqrt(N * fut["costo_directo_var"].to_numpy()[:, None]) * rng.standard_normal((I, n)), 0, None)
        # Solapamiento: en un paquete, los atrasos de varios eventos no siempre van uno detras de otro. El paquete se
        # atrasa lo del mayor mas `solapamiento` x lo de los demas (1 = en fila, 0 = todos a la vez). El costo de tener
        # el paquete parado se cobra sobre esos dias, una sola vez; el costo directo de cada evento si se suma.
        cdia = fut.groupby("id_paquete")["costo_dia"].first()
        for p, filas in fut.groupby("id_paquete").groups.items():
            k = pos[p]
            sub = dias[list(filas)]
            suma_pq[k] = sub.sum(axis=0)
            mayor_pq[k] = sub.max(axis=0)
            futuro_pq = mayor_pq[k] + alfa * (suma_pq[k] - mayor_pq[k])
            costo_pq[k] = directo[list(filas)].sum(axis=0) + float(cdia.get(p, 0) or 0) * futuro_pq

    consumido_d = tabla.groupby("id_paquete")["consumido_dias"].sum().reindex(ids_p).fillna(0).to_numpy() if len(tabla) else np.zeros(len(ids_p))
    consumido_c = tabla.groupby("id_paquete")["consumido_usd"].sum().reindex(ids_p).fillna(0).to_numpy() if len(tabla) else np.zeros(len(ids_p))
    # el solapamiento cubre todos los eventos del paquete: los que ya ocurrieron (consumido) y los simulados
    mayor_consumido = (tabla[tabla["consumido_dias"] > 0].groupby("id_paquete")["consumido_dias"].max().reindex(ids_p).fillna(0).to_numpy()
                       if len(tabla) else np.zeros(len(ids_p)))
    suma_total = suma_pq + consumido_d[:, None]
    mayor_total = np.maximum(mayor_pq, mayor_consumido[:, None])
    total_d = mayor_total + alfa * (suma_total - mayor_total)
    total_c = costo_pq + consumido_c[:, None]
    holgura = paquetes["holgura_dias"].fillna(0).to_numpy()[:, None]
    pasa = np.clip(total_d - holgura, 0, None)                    # atraso que llega al proyecto

    out_p = []
    for k, p in enumerate(ids_p):
        d, c = total_d[k], total_c[k]
        out_p.append({"id_paquete": p, "id_proyecto": paquetes.loc[p, "id_proyecto"],
                      **{f"atraso_{q}": v for q, v in _cuantiles(d).items()}, "atraso_consumido": float(consumido_d[k]),
                      "atraso_sin_solapamiento_media": float(suma_total[k].mean()),
                      **{f"costo_{q}": v for q, v in _cuantiles(c).items()}, "costo_consumido": float(consumido_c[k]),
                      "holgura_dias": float(holgura[k, 0]),
                      "prob_atraso_al_proyecto": float((pasa[k] > 0).mean()),
                      "ire": 100 * float((d > holgura[k, 0] + tol_p).mean())})
    out_y, hist = [], {}
    for proy, g in paquetes.groupby("id_proyecto"):
        idx = [pos[p] for p in g.index]
        d = pasa[idx].sum(axis=0)
        c = total_c[idx].sum(axis=0)
        out_y.append({"id_proyecto": proy, **{f"atraso_{q}": v for q, v in _cuantiles(d).items()},
                      **{f"costo_{q}": v for q, v in _cuantiles(c).items()},
                      "ire": 100 * float((d > tol_y).mean()), "prob_sin_atraso": float((d == 0).mean())})
        hist[proy] = {"atraso": _histograma(d, bins), "costo": _histograma(c, bins)}
    cart_d, cart_c = pasa.sum(axis=0), total_c.sum(axis=0)
    return {"paquetes": pd.DataFrame(out_p), "proyectos": pd.DataFrame(out_y), "histogramas": hist,
            "portafolio": {**{f"atraso_{q}": v for q, v in _cuantiles(cart_d).items()},
                           **{f"costo_{q}": v for q, v in _cuantiles(cart_c).items()}},
            "simulaciones": n, "tolerancia_paquete": tol_p, "tolerancia_proyecto": tol_y, "solapamiento": alfa}


def _histograma(x: np.ndarray, bins: int) -> dict:
    hi = float(np.percentile(x, 99.5)) or 1.0
    cuentas, bordes = np.histogram(np.clip(x, 0, hi), bins=bins, range=(0, hi))
    return {"bordes": [round(float(b), 2) for b in bordes], "frecuencia": [round(float(c) / len(x), 5) for c in cuentas]}
