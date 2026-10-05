import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plata import vias_igac as va

CAJA = {"lon_oeste": -73.7, "lat_sur": 10.5, "lon_este": -71.0, "lat_norte": 12.7}


def _capa(tipo, geoms, **atributos):
    n = len(geoms)
    datos = {"objectid": list(range(1, n + 1)), "tipo_via": [tipo] * n, "nombre_geografico": [None] * n,
             "estado_superficie": ["3301"] * n, "numero_carriles": ["3501"] * n, "accesibilidad": ["3600"] * n}
    datos.update(atributos)
    return gpd.GeoDataFrame(datos, geometry=geoms, crs="EPSG:4326")


def test_traduce_clase_y_dominios():
    capas = [
        _capa(1, [LineString([(-72.5, 11.0), (-72.5, 11.1)])]),
        _capa(5, [LineString([(-72.4, 11.0), (-72.4, 11.1)])], estado_superficie=["3306"], numero_carriles=["Sin Valor"], accesibilidad=["3601"]),
        _capa(7, [LineString([(-72.3, 11.0), (-72.3, 11.1)])], estado_superficie=["Sin Valor"], numero_carriles=["Sin Valor"], accesibilidad=["Sin Valor"]),
    ]
    g, rep = va.limpiar(capas, None, CAJA)
    d = g.set_index("tipo")
    assert d.loc[1, "clase"] == "Pavimentada, 2 o más carriles" and d.loc[1, "accesibilidad"] == "Todo el año"
    assert d.loc[5, "superficie"] == "Sin pavimentar" and d.loc[5, "accesibilidad"] == "Solo en tiempo seco"
    assert d.loc[5, "carriles"] is None or d.loc[5, "carriles"] != d.loc[5, "carriles"]    # "Sin Valor" queda vacio
    assert rep["km_solo_tiempo_seco"] == pytest.approx(11.1, rel=0.03)
    assert rep["km_pavimentadas"] == pytest.approx(11.1, rel=0.03)
    assert rep["km_caminos"] == pytest.approx(11.1, rel=0.03)
    assert rep["recortada_a"] == "caja de descarga"


def test_recorta_al_limite_y_descarta_astillas():
    limite = box(-72.6, 10.9, -72.4, 11.2)
    cruza = LineString([(-72.5, 10.0), (-72.5, 11.1)])                 # solo 0,2 grados (~22 km) caen dentro
    astilla = LineString([(-72.4002, 11.0), (-72.3998, 11.0)])        # ~44 m, de los cuales ~22 m quedan dentro: menos del minimo
    fuera = LineString([(-71.5, 11.0), (-71.5, 11.1)])
    g, rep = va.limpiar([_capa(3, [cruza, astilla, fuera], estado_superficie=["3301"] * 3)], limite, CAJA)
    assert len(g) == 1 and g.iloc[0]["km"] == pytest.approx(0.2 * 111.0, rel=0.03)
    assert rep["recortada_a"] == "municipios del DANE"


def test_ignora_tipos_desconocidos():
    g, rep = va.limpiar([_capa(9, [LineString([(-72.5, 11.0), (-72.5, 11.1)])])], None, CAJA)
    assert g.empty and rep["tipo_desconocido"] == 1
