import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "app"))

from comun.config import cargar_parametros  # noqa: E402
from modelo import ejecucion as m  # noqa: E402

CFG = cargar_parametros(oficial=True)["ejecucion"]


def _riesgo(**k):
    base = {"id_riesgo": "R1", "id_paquete_trabajo": "P1", "tipo": "amenaza", "estado": "latente", "categoria": "contractual",
            "probabilidad": "E", "probabilidad_residual": "D", "nivel_residual": "H", "ram_residual": "4D",
            "cons_personas": 0, "cons_economica": 4, "cons_ambiental": 0, "cons_clientes": 1, "cons_imagen": 1}
    return {**base, **k}


def _paquetes(holgura=0, meses=12):
    return pd.DataFrame({"id_proyecto": ["Y1"], "meses_restantes": [meses], "costo_dia_parada_usd": [10000],
                         "holgura_dias": [holgura], "codigo_municipio": ["44001"]}, index=pd.Index(["P1"], name="id_paquete"))


Z0 = pd.DataFrame({c: [0.0] for c in ("tasa_delitos_rel", "emergencias_rel", "anomalia_lluvia", "en_resguardo", "ipm_rel", "pdet", "vias_tiempo_seco")},
                  index=pd.Index(["P1"], name="id_paquete"))


# ---- piezas ------------------------------------------------------------------------------------------------------

def test_el_territorio_promedio_no_cambia_la_frecuencia_y_el_multiplicador_tiene_tope():
    assert m.multiplicador_territorial("seguridad_fisica", {"tasa_delitos_rel": 0}, CFG) == 1.0
    assert m.multiplicador_territorial("seguridad_fisica", {"tasa_delitos_rel": 100}, CFG) == pytest.approx(3.0)
    assert m.multiplicador_territorial("seguridad_fisica", {"tasa_delitos_rel": -100}, CFG) == pytest.approx(1 / 3)
    assert m.multiplicador_territorial("contractual", {"tasa_delitos_rel": 5}, CFG) == 1.0        # no le aplica
    assert m.multiplicador_territorial("seguridad_fisica", {"tasa_delitos_rel": 1}, {**CFG, "gamma": 0}) == 1.0
    assert m.multiplicador_territorial("seguridad_fisica", {"tasa_delitos_rel": 1}, CFG) == pytest.approx(math.exp(0.5 * 0.6))


def test_los_dias_por_evento_los_pone_la_peor_dimension():
    assert m.dias_por_evento({"PE": 2, "EC": 4, "IM": 3}, CFG) == 20       # EC 4 = 20 dias > IM 3 = 7 > PE 2 = 0,5
    assert m.dias_por_evento({"PE": None, "IM": 4}, CFG) == 30


def test_momentos_del_costo_log_uniforme():
    media, var = m.momentos_costo_directo(3, CFG)                          # banda 100 mil a 1 M
    assert media == pytest.approx(900000 / math.log(10))
    x = np.exp(np.random.default_rng(0).uniform(math.log(1e5), math.log(1e6), 200000))
    assert media == pytest.approx(x.mean(), rel=0.01) and var == pytest.approx(x.var(), rel=0.02)
    assert m.momentos_costo_directo(0, CFG) == (0.0, 0.0)


# ---- tabla de riesgos ------------------------------------------------------------------------------------------------

def test_frecuencia_probabilidad_y_valor_esperado_de_una_amenaza():
    t = m.preparar_riesgos(pd.DataFrame([_riesgo()]), _paquetes(meses=6), Z0, CFG).iloc[0]
    lam = CFG["lambda_por_letra"]["D"]
    assert t["lambda"] == pytest.approx(lam) and t["horizonte_anios"] == 0.5
    assert t["probabilidad"] == pytest.approx(1 - math.exp(-lam * 0.5))
    assert t["dias_por_evento"] == 20
    assert t["atraso_esperado"] == pytest.approx(lam * 0.5 * 20 * m.TRI_MEDIA)
    inh = CFG["lambda_por_letra"]["E"]
    assert t["atraso_evitado_por_controles"] == pytest.approx((inh - lam) * 0.5 * 20 * m.TRI_MEDIA)


def test_lo_materializado_cuenta_como_consumido_y_no_como_probabilidad():
    t = m.preparar_riesgos(pd.DataFrame([_riesgo(estado="materializado")]), _paquetes(), Z0, CFG).iloc[0]
    assert t["lambda"] == 0 and t["atraso_esperado"] == 0
    assert t["consumido_dias"] == pytest.approx(20 * CFG["fraccion_consumida_materializado"])


def test_proximo_a_materializarse_multiplica_y_sin_controles_usa_la_inherente():
    prox = m.preparar_riesgos(pd.DataFrame([_riesgo(estado="proximo_a_materializarse")]), _paquetes(), Z0, CFG).iloc[0]
    assert prox["lambda"] == pytest.approx(CFG["lambda_por_letra"]["D"] * CFG["factor_estado"]["proximo_a_materializarse"])
    sin = m.preparar_riesgos(pd.DataFrame([_riesgo()]), _paquetes(), Z0, CFG, escenario={"controles": "inherente"}).iloc[0]
    assert sin["lambda"] == pytest.approx(CFG["lambda_por_letra"]["E"])
    x2 = m.preparar_riesgos(pd.DataFrame([_riesgo()]), _paquetes(), Z0, CFG, escenario={"factor": {"contractual": 2}}).iloc[0]
    assert x2["lambda"] == pytest.approx(2 * CFG["lambda_por_letra"]["D"])


def test_el_area_protegida_cercana_sube_la_consecuencia_ambiental():
    r = _riesgo(categoria="ambiental", cons_ambiental=2, cons_economica=1)
    sin = m.preparar_riesgos(pd.DataFrame([r]), _paquetes(), Z0, CFG).iloc[0]
    con = m.preparar_riesgos(pd.DataFrame([r]), _paquetes(), Z0, CFG, piso_ambiental=pd.Series({"P1": 4})).iloc[0]
    assert sin["dias_por_evento"] == 1 and con["dias_por_evento"] == 20


# ---- simulacion ------------------------------------------------------------------------------------------------------

def test_la_simulacion_reproduce_el_valor_esperado_analitico():
    cfg = {**CFG, "choques": {"clima": 0, "social": 0}}
    t = m.preparar_riesgos(pd.DataFrame([_riesgo(probabilidad_residual="E")]), _paquetes(), Z0, cfg)
    s = m.simular(t, _paquetes(), cfg, n=40000, semilla=1)
    assert s["paquetes"].iloc[0]["atraso_media"] == pytest.approx(t.iloc[0]["atraso_esperado"], rel=0.03)
    assert s["paquetes"].iloc[0]["costo_media"] == pytest.approx(t.iloc[0]["costo_esperado"], rel=0.05)


def test_la_holgura_absorbe_atraso_y_la_tolerancia_define_el_ire():
    cfg = {**CFG, "choques": {"clima": 0, "social": 0}}
    t = m.preparar_riesgos(pd.DataFrame([_riesgo(probabilidad_residual="E", estado="materializado")]), _paquetes(holgura=5), Z0, cfg)
    s = m.simular(t, _paquetes(holgura=5), cfg, n=2000, tolerancia_paquete=0, tolerancia_proyecto=0)
    consumido = 20 * cfg["fraccion_consumida_materializado"]                       # 7 dias, deterministico
    assert s["paquetes"].iloc[0]["atraso_media"] == pytest.approx(consumido)
    assert s["proyectos"].iloc[0]["atraso_media"] == pytest.approx(consumido - 5)  # la holgura se come 5 dias
    assert s["paquetes"].iloc[0]["ire"] == 100
    s2 = m.simular(t, _paquetes(holgura=5), cfg, n=2000, tolerancia_paquete=10, tolerancia_proyecto=10)
    assert s2["paquetes"].iloc[0]["ire"] == 0 and s2["proyectos"].iloc[0]["ire"] == 0


def test_el_choque_comun_ensancha_la_cola_sin_mover_la_media():
    riesgos = pd.DataFrame([_riesgo(id_riesgo=f"R{i}", categoria="climatico", probabilidad_residual="E") for i in range(6)])
    ind = {**CFG, "choques": {"clima": 0, "social": 0}, "solapamiento": 1.0}
    dep = {**CFG, "choques": {"clima": 1.0, "social": 0}, "solapamiento": 1.0}
    a = m.simular(m.preparar_riesgos(riesgos, _paquetes(), Z0, ind), _paquetes(), ind, n=30000, semilla=3)["paquetes"].iloc[0]
    b = m.simular(m.preparar_riesgos(riesgos, _paquetes(), Z0, dep), _paquetes(), dep, n=30000, semilla=3)["paquetes"].iloc[0]
    assert b["atraso_media"] == pytest.approx(a["atraso_media"], rel=0.05)
    assert b["atraso_p90"] > a["atraso_p90"]


# ---- supuestos editables (app) ---------------------------------------------------------------------------------------

def test_los_supuestos_editados_se_validan():
    import ejecucion_api as api
    ok, adv = api.validar({"lambda_por_letra": {"A": 0.1, "B": 0.05, "C": 0.2, "D": 0.5, "E": 1}, "gamma": 0.3})
    assert ok["gamma"] == 0.3 and any("no crece" in a for a in adv)
    with pytest.raises(api.ErrorSupuestos, match="gamma"):
        api.validar({"gamma": 7})
    with pytest.raises(api.ErrorSupuestos, match="6 valores"):
        api.validar({"dias_por_consecuencia": {d: [0, 1] for d in ("PE", "EC", "MA", "CL", "IM")}})


def test_el_solapamiento_cuenta_el_mayor_atraso_y_una_fraccion_del_resto():
    riesgos = pd.DataFrame([_riesgo(id_riesgo=f"R{i}", probabilidad_residual="E") for i in range(4)])
    tabla = m.preparar_riesgos(riesgos, _paquetes(), Z0, {**CFG, "choques": {"clima": 0, "social": 0}})
    medias = {}
    for alfa in (0.0, 0.5, 1.0):
        cfg = {**CFG, "choques": {"clima": 0, "social": 0}, "solapamiento": alfa}
        medias[alfa] = m.simular(tabla, _paquetes(), cfg, n=20000, semilla=5)["paquetes"].iloc[0]
    assert medias[0.0]["atraso_media"] < medias[0.5]["atraso_media"] < medias[1.0]["atraso_media"]
    # sin solapamiento (1) la media es la suma analitica; la columna de control la reproduce siempre
    assert medias[1.0]["atraso_media"] == pytest.approx(tabla["atraso_esperado"].sum(), rel=0.03)
    assert medias[0.0]["atraso_sin_solapamiento_media"] == pytest.approx(tabla["atraso_esperado"].sum(), rel=0.03)
    # con 0,5 queda a mitad de camino entre el mayor y la suma
    assert medias[0.5]["atraso_media"] == pytest.approx((medias[0.0]["atraso_media"] + medias[1.0]["atraso_media"]) / 2, rel=0.03)
