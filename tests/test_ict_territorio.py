"""ICT con el territorio real: escala fija, componentes sin dato, alcance espacial de las amenazas y lluvia reciente."""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from modelo import ict  # noqa: E402
from modelo import territorio  # noqa: E402

CRS = "EPSG:3116"
PESOS = {"severidad_riesgo": 0.28, "vulnerabilidad_territorial": 0.22, "amenazas_externas": 0.15,
         "exposicion_proyecto": 0.20, "convergencia": 0.15}


def _amenazas(filas):
    df = pd.DataFrame(filas)
    return gpd.GeoDataFrame(df, geometry=[Point(x, y) for x, y in zip(df.pop("x"), df.pop("y"))], crs=CRS)


# ---- componentes y escala fija -----------------------------------------------------------------------------------

def test_un_componente_sin_dato_queda_inactivo_y_baja_la_disponibilidad():
    comp = pd.DataFrame({"a": [1.0, np.nan], "b": [0.0, 0.5]}, index=["P1", "P2"])
    valor, disp = ict.combinar(comp, {"a": 0.75, "b": 0.25})
    assert valor["P1"] == pytest.approx(0.75)          # 0,75 x 1 + 0,25 x 0
    assert valor["P2"] == pytest.approx(0.5)           # sin "a": solo cuenta "b", no se toma "a" como 0
    assert disp["P1"] == 1.0 and disp["P2"] == pytest.approx(0.25)


def test_escala_fija_conserva_el_sin_dato_y_satura_en_uno():
    s = ict.escala(pd.Series([0, 40, 160, np.nan]), 80)
    assert list(s[:3]) == [0.0, 0.5, 1.0] and np.isnan(s.iloc[3])


def test_el_ict_de_un_paquete_no_cambia_si_se_agrega_otro():
    crudos = {c: pd.Series({"A": 0.4}) for c in ict.CRITERIOS}
    solo, _ = ict.ensamblar_ict(crudos, PESOS, ["A"], bounds=ict.LIMITES_ABSOLUTOS)
    crudos2 = {c: pd.Series({"A": 0.4, "B": 0.9}) for c in ict.CRITERIOS}
    con_otro, _ = ict.ensamblar_ict(crudos2, PESOS, ["A", "B"], bounds=ict.LIMITES_ABSOLUTOS)
    assert solo.loc["A", "ICT"] == con_otro.loc["A", "ICT"] == 40.0


def test_la_confianza_pondera_por_el_peso_de_cada_criterio():
    disp = pd.DataFrame({c: [1.0] for c in ict.CRITERIOS}, index=["A"])
    disp.loc["A", "amenazas_externas"] = 0.0          # sin ningun dato externo al dia
    assert ict.indice_confianza(disp, PESOS)["A"] == pytest.approx(0.85)


# ---- alcance espacial de las amenazas -------------------------------------------------------------------------------

def test_una_amenaza_asignada_alcanza_entera_y_una_vecina_decae_con_la_distancia():
    unidades = gpd.GeoSeries([box(0, 0, 1000, 1000), box(5000, 0, 6000, 1000)], index=["P1", "P2"], crs=CRS)
    amen = _amenazas([{"categoria": "social_comunidad", "x": 500, "y": 500, "paq": "P1"}])
    w = ict.pesos_alcance(unidades, amen, {"social_comunidad": 8000, "default": 2500}, asignacion=amen["paq"])
    assert w[0, 0] == 1.0
    assert w[1, 0] == pytest.approx(1 - 4500 / 8000)    # P2 empieza a 4,5 km del punto; radio de 8 km
    lejos = ict.pesos_alcance(unidades, amen, {"social_comunidad": 3000}, asignacion=amen["paq"])
    assert lejos[1, 0] == 0.0


def test_severidad_absoluta_vh_materializado_es_uno_y_sin_amenazas_es_cero():
    amen = pd.DataFrame({"puntaje_ram": [5], "estado_calc": ["materializado"]})
    sev = ict.severidad_amenazas(amen, {"latente": 1.0, "proximo_a_materializarse": 1.3, "materializado": 1.6})
    w = np.array([[1.0], [0.0]])
    s = ict.criterio_severidad(w, sev, 0.7, 0.3, 5 * 1.6, ["A", "B"])
    assert s["A"] == pytest.approx(1.0) and s["B"] == 0.0


def test_exposicion_suma_ruta_critica_y_amenazas_que_alcanzan():
    w = np.array([[1.0] * 10, [0.0] * 10])
    e = ict.criterio_exposicion(w, pd.Series({"A": True, "B": False}), {"peso_ruta_critica": 0.5, "amenazas_para_saturar": 20}, ["A", "B"])
    assert e.loc["A", "exposicion_proyecto"] == pytest.approx(0.5 + 0.5 * 10 / 20)
    assert e.loc["B", "exposicion_proyecto"] == 0.0


def test_convergencia_cuenta_categorias_abiertas_desde_m_y_factores_del_territorio():
    amen = pd.DataFrame({"categoria": ["social_comunidad", "climatico", "ambiental", "contractual"],
                         "nivel_residual": ["H", "M", "L", "VH"],
                         "estado_calc": ["latente", "latente", "latente", "materializado"]})
    w = np.ones((1, 4))
    externas = pd.DataFrame({"ext_lluvia_reciente": [np.nan], "ext_anomalia_lluvia": [0.2], "ext_emergencias": [0.9],
                             "ext_seguridad": [0.7]}, index=["A"])
    c = ict.criterio_convergencia(amen, w, externas, {"nivel_minimo_registro": "M", "alcance_minimo": 0.5,
                                                      "umbral_factor_territorio": 0.6, "amenazas_para_saturar": 5}, ["A"])
    # social (H) y climatico (M) cuentan; ambiental (L) no llega a M; contractual ya se materializo
    assert c.loc["A", "n_categorias_registro"] == 2
    assert c.loc["A", "n_factores_territorio"] == 2          # emergencias y delitos
    assert c.loc["A", "convergencia"] == pytest.approx(4 / 5)


def test_vulnerabilidad_resguardo_colindante_cuenta_la_mitad():
    terr = pd.DataFrame({"fraccion_resguardo": [1.0, 0.0, 0.0], "distancia_resguardo_km": [0.0, 0.0, np.nan],
                         "ipm": [90.0, 40.0, np.nan], "fraccion_area_protegida": [0.0, 0.0, 0.0],
                         "distancia_area_protegida_km": [20.0, 5.0, 3.0], "vias_tiempo_seco": [0.8, 0.3, np.nan]},
                        index=["dentro", "colinda", "sin_dato"])
    v = ict.criterio_vulnerabilidad(terr, {"componentes": {"etnico": 0.3, "pobreza": 0.25, "ambiental": 0.25, "acceso": 0.2},
                                           "radio_resguardo_km": 5, "radio_area_protegida_km": 10})
    assert v.loc["dentro", "vul_etnico"] == 1.0
    assert v.loc["colinda", "vul_etnico"] == pytest.approx(0.5)
    assert np.isnan(v.loc["sin_dato", "vul_etnico"]) and v.loc["sin_dato", "disp_vulnerabilidad"] == pytest.approx(0.25)
    assert v.loc["colinda", "vul_ambiental"] == pytest.approx(0.5)     # a 5 km de un radio de 10


# ---- territorio ----------------------------------------------------------------------------------------------------

def test_dentro_y_distancia_para_poligonos_y_puntos():
    capa = gpd.GeoDataFrame({"nombre": ["R"]}, geometry=[box(0, 0, 1000, 1000)], crs=CRS)
    unidades = gpd.GeoSeries([box(500, 0, 1500, 1000), Point(500, 500), Point(3000, 0)], index=["mitad", "dentro", "lejos"], crs=CRS)
    r = territorio.dentro_y_distancia(unidades, capa)
    assert r.loc["mitad", "fraccion_dentro"] == pytest.approx(0.5)
    assert r.loc["dentro", "fraccion_dentro"] == 1.0 and r.loc["lejos", "fraccion_dentro"] == 0.0
    assert r.loc["lejos", "distancia_km"] == pytest.approx(2.0)


def test_lluvia_reciente_exige_dias_con_dato_y_estacion_cercana():
    estaciones = gpd.GeoDataFrame({"codigo": ["E1", "E2"], "nombre": ["Cerca", "Lejos"]},
                                  geometry=[Point(0, 1000), Point(0, 50_000)], crs=CRS)
    dias = pd.date_range("2026-10-01", "2026-10-14")
    lluvia = pd.concat([
        pd.DataFrame({"codigoestacion": "E1", "dia": dias[:5], "mm": 10.0}),          # solo 5 dias: no alcanza
        pd.DataFrame({"codigoestacion": "E2", "dia": dias, "mm": 2.0}),               # completa pero a 50 km
    ])
    centros = gpd.GeoSeries([Point(0, 0)], index=["P"], crs=CRS)
    r = territorio.lluvia_reciente(centros, estaciones, lluvia, pd.Timestamp("2026-10-14"), 14, 10, 20)
    assert np.isnan(r.loc["P", "lluvia_mm"])                                          # ninguna sirve: sin dato
    r2 = territorio.lluvia_reciente(centros, estaciones, lluvia, pd.Timestamp("2026-10-14"), 14, 10, 60)
    assert r2.loc["P", "lluvia_mm"] == pytest.approx(28.0) and r2.loc["P", "lluvia_dias_con_dato"] == 14
