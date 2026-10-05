import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plata import hidrografia as h

CAJA = {"lon_oeste": -73.7, "lat_sur": 10.5, "lon_este": -71.0, "lat_norte": 12.7}


def _capa(geoms, **columnas):
    return gpd.GeoDataFrame({"objectid": range(1, len(geoms) + 1), **columnas}, geometry=geoms, crs="EPSG:4326")


@pytest.mark.parametrize("crudo,esperado", [
    ("Rio  Negro", "Río Negro"),                 # espacio doble y sin tilde
    ("Quebrada Los Presos", "Quebrada Los Presos"),
    ("Cienaga El Pantano", "Ciénaga El Pantano"),
    ("  ", None), (None, None),
])
def test_normalizar_nombre(crudo, esperado):
    assert h.normalizar_nombre(crudo) == esperado


def test_traduce_estado_y_calcula_longitud_y_area():
    linea = LineString([(-72.5, 11.0), (-72.5, 11.1)])                       # ~11 km
    lago = Polygon([(-72.5, 11.5), (-72.4, 11.5), (-72.4, 11.6), (-72.5, 11.6)])  # ~0,1 x 0,1 grados
    capas = {
        "drenaje_sencillo": _capa([linea, linea], nombre_geografico=["Rio Palomino", None], estado_drenaje=[5101, 5102]),
        "laguna": _capa([lago], nombre_geografico=[None]),
    }
    g, rep = h.limpiar(capas, CAJA)
    rios = g[g["tipo"] == "drenaje_sencillo"].set_index("nombre", drop=False)
    assert rios.loc["Río Palomino", "estado"] == "Permanente"
    assert (g[g["tipo"] == "drenaje_sencillo"]["estado"] == "Intermitente").sum() == 1
    assert rios["longitud_km"].iloc[0] == pytest.approx(11.1, rel=0.03)
    assert g[g["tipo"] == "laguna"]["area_km2"].iloc[0] == pytest.approx(0.1 * 0.1 * 111 * 108, rel=0.05)
    assert rep["sin_nombre"] == 2 and rep["km_permanentes"] == pytest.approx(11, abs=1)


def test_recorta_a_la_caja_y_repara_poligonos_invalidos():
    fuera = LineString([(-72.5, 12.0), (-72.5, 14.0)])
    corbata = Polygon([(-72.5, 11.0), (-72.4, 11.1), (-72.4, 11.0), (-72.5, 11.1)])   # se cruza a si mismo
    g, rep = h.limpiar({
        "drenaje_sencillo": _capa([fuera], nombre_geografico=["Rio X"], estado_drenaje=[5101]),
        "cienaga": _capa([corbata], nombre_geografico=["Cienaga Y"]),
    }, CAJA)
    assert g.total_bounds[3] <= 12.7 + 1e-3
    assert rep["geometrias_invalidas_reparadas"] == 1
    assert g.geometry.is_valid.all()
