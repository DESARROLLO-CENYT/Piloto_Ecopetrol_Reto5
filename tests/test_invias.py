import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plata import invias as iv

CAJA = {"lon_oeste": -73.7, "lat_sur": 10.5, "lon_este": -71.0, "lat_norte": 12.7}


def _bruto(filas):
    """Tramos como los entrega la fuente: propiedades en texto, geometria en grados."""
    base = {"administrador": "1", "calzada": "1", "categoria": "1", "superficie": "3", "territorial": "13",
            "nombre_tramo": "Por Defnir", "sector": "A - B", "nombre_ruta": "Ruta X", "ruta": "88",
            "distancia_inicial": "0", "fuente": "IGAC"}
    props = [{**base, **f["p"], "shape__length": "0"} for f in filas]
    return gpd.GeoDataFrame(props, geometry=[f["g"] for f in filas], crs="EPSG:4326")


def test_traduce_dominios_y_deja_vacio_lo_por_definir():
    g, rep = iv.limpiar(_bruto([
        {"p": {"codigo_tramo": "T1", "administrador": "2", "categoria": "4"}, "g": LineString([(-72.5, 11.0), (-72.4, 11.1)])},
    ]), CAJA)
    fila = g.iloc[0]
    assert fila["administrador_txt"] == "ANI"
    assert fila["calzada_txt"] == "Sencilla"
    assert fila["categoria_txt"] is None or fila["categoria_txt"] != fila["categoria_txt"]   # 4 = por definir
    assert fila["superficie_txt"] is None or fila["superficie_txt"] != fila["superficie_txt"]  # 3 = por definir
    assert rep["nombre_tramo_por_definir"] == 1 and rep["categoria_por_definir"] == 1
    assert bool(fila["en_guajira"])


def test_quita_el_tramo_que_solo_repite_a_otros():
    a = LineString([(-72.5, 11.0), (-72.4, 11.0)])
    b = LineString([(-72.4, 11.0), (-72.3, 11.0)])
    suma = LineString([(-72.5, 11.0), (-72.4, 11.0), (-72.3, 11.0)])   # geometria de a + b
    g, rep = iv.limpiar(_bruto([
        {"p": {"codigo_tramo": "A"}, "g": a}, {"p": {"codigo_tramo": "B"}, "g": b}, {"p": {"codigo_tramo": "SUMA"}, "g": suma},
    ]), CAJA)
    assert rep["repetidos_removidos"] == 1
    assert sorted(g["codigo_tramo"]) == ["A", "B"]


def test_recorta_a_la_caja_y_recalcula_la_longitud():
    largo = LineString([(-72.5, 12.0), (-72.5, 13.5)])   # sale de la caja por el norte
    g, _ = iv.limpiar(_bruto([{"p": {"codigo_tramo": "L"}, "g": largo}]), CAJA)
    assert g.total_bounds[3] == pytest.approx(12.7, abs=1e-3)
    assert g.iloc[0]["longitud_km"] == pytest.approx(0.7 * 111.0, rel=0.03)   # 0,7 grados de latitud


def test_no_marca_como_guajira_otras_territoriales():
    g, _ = iv.limpiar(_bruto([
        {"p": {"codigo_tramo": "C", "territorial": "9"}, "g": LineString([(-73.2, 10.6), (-73.1, 10.7)])},
    ]), CAJA)
    assert not bool(g.iloc[0]["en_guajira"]) and g.iloc[0]["territorial_txt"] == "Cesar"
