import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oro import cobertura as cb  # noqa: E402

LIMITE = box(0, 0, 30_000, 20_000)      # un "departamento" de 30 x 20 km, en metros


def _estaciones():
    return gpd.GeoDataFrame({"codigo": ["A", "B", "C"], "nombre": ["Alta", "Baja", "Costa"]},
                            geometry=[Point(5_000, 5_000), Point(25_000, 5_000), Point(15_000, 17_000)], crs=3116)


def test_el_area_mas_cercana_reparte_todo_el_territorio_sin_huecos_ni_solapes():
    celdas = cb.area_mas_cercana(_estaciones(), LIMITE)
    assert len(celdas) == 3
    assert celdas.area.sum() == pytest.approx(LIMITE.area, rel=1e-9)               # cubre todo el departamento
    assert celdas.union_all().symmetric_difference(LIMITE).area == pytest.approx(0, abs=1e-3)
    for _, c in celdas.iterrows():                                                   # cada estacion queda en su propia celda
        assert c.geometry.contains(_estaciones().set_index("codigo").geometry[c["codigo"]])


def test_cada_punto_queda_con_su_estacion_mas_cercana():
    celdas = cb.area_mas_cercana(_estaciones(), LIMITE).set_index("codigo")
    assert celdas.geometry["B"].contains(Point(28_000, 2_000))
    assert celdas.geometry["C"].contains(Point(14_000, 19_000))
    assert celdas.geometry["A"].contains(Point(1_000, 1_000))


def test_con_una_sola_estacion_no_hay_reparto():
    una = _estaciones().iloc[:1]
    assert cb.area_mas_cercana(una, LIMITE).empty


def test_el_radio_de_influencia_se_recorta_al_departamento():
    areas = cb.radio_de_influencia(_estaciones(), 8, LIMITE)                         # 8 km
    assert areas.geometry.apply(LIMITE.contains).all()
    esquina = areas.set_index("codigo").geometry["A"]                                # la estacion A esta a 5 km de dos bordes: el circulo se corta
    assert esquina.area < 3.14159 * 8_000 ** 2 * 0.999


@pytest.mark.parametrize("distancia,estado", [(0, "cubierto"), (10, "cubierto"), (10.1, "parcial"), (20, "parcial"), (20.1, "sin_cobertura"), (80, "sin_cobertura")])
def test_estado_segun_el_radio(distancia, estado):
    assert cb.estado_de(distancia, 10) == estado


def test_cada_paquete_se_asigna_a_su_estacion_mas_cercana_con_distancia_y_estado():
    paquetes = gpd.GeoDataFrame({"id_paquete": ["P1", "P2"]}, geometry=[Point(7_000, 5_000).buffer(500), Point(15_000, 10_000).buffer(500)], crs=3116)
    r = cb.cobertura_de_paquetes(paquetes, {"precipitacion": _estaciones(), "presion": _estaciones()}, {"precipitacion": 3, "presion": 40})
    p1 = {f["variable"]: f for f in r["P1"]}
    assert p1["lluvia"]["codigo"] == "A" and p1["lluvia"]["distancia_km"] == 2.0 and p1["lluvia"]["estado"] == "cubierto"
    p2 = {f["variable"]: f for f in r["P2"]}
    assert p2["lluvia"]["codigo"] == "C" and p2["lluvia"]["distancia_km"] == 7.0 and p2["lluvia"]["estado"] == "sin_cobertura"   # a 7 km con radio de 3 km (limite parcial: 6 km)
    assert p2["presion"]["estado"] == "cubierto"                                                                             # el mismo paquete, con un radio de 40 km
    assert {f["variable"] for f in r["P1"]} == {"lluvia", "presion"}                                                       # el nivel del rio no tiene area


def test_los_radios_vienen_de_parametros_y_el_resto_usa_valores_por_defecto(monkeypatch):
    monkeypatch.setattr(cb, "cargar_parametros", lambda: {"cobertura_estaciones": {"radios_km": {"lluvia": 7, "viento": 12}}})
    r = cb.radios_km()
    assert r["precipitacion"] == 7 and r["viento_vel"] == 12 and r["presion"] == cb.RADIOS_POR_DEFECTO_KM["presion"]
    monkeypatch.setattr(cb, "cargar_parametros", lambda: {})
    assert cb.radios_km() == cb.RADIOS_POR_DEFECTO_KM
