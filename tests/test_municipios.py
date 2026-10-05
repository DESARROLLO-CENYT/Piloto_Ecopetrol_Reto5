import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plata import municipios as mo


@pytest.mark.parametrize("crudo,esperado", [
    ("RIOHACHA", "Riohacha"), ("LA JAGUA DEL PILAR", "La Jagua del Pilar"), ("EL MOLINO", "El Molino"),
    ("SAN JUAN DEL CESAR", "San Juan del Cesar"), ("DISTRACCION", "Distracción"), ("  HATONUEVO ", "Hatonuevo"),
])
def test_nombre_propio(crudo, esperado):
    assert mo.nombre_propio(crudo) == esperado


def _bruto():
    """Dos municipios vecinos que comparten un borde con muchos vertices."""
    borde = [(-72.5, 11.0 + i * 0.01 + (0.0002 if i % 2 else 0)) for i in range(11)]       # borde zigzag compartido
    a = Polygon([(-72.6, 11.0), *borde, (-72.6, 11.1)])
    b = Polygon([*borde, (-72.4, 11.1), (-72.4, 11.0)][::1])
    return gpd.GeoDataFrame(
        {"DPTO_CCDGO": ["44", "44"], "MPIO_CCDGO": ["001", "035"], "MPIO_CNMBR": ["RIOHACHA", "ALBANIA"], "MPIO_NAREA": [1.0, 1.0]},
        geometry=[a, b], crs="EPSG:4326",
    )


def _divipola():
    return pd.DataFrame({"cod_mpio": ["44001", "44035"], "nom_mpio": ["RIOHACHA", "ALBANIA"],
                         "longitud": ["-72,9", "-72,6"], "latitud": ["11,5", "11,1"]})


def test_limpia_nombres_codigos_y_cabeceras():
    g, rep = mo.limpiar(_bruto(), _divipola())
    assert g["codigo"].tolist() == ["44001", "44035"]
    assert g["nombre"].tolist() == ["Riohacha", "Albania"]
    assert g.loc[0, "cabecera_lon"] == pytest.approx(-72.9)        # la coma decimal de DIVIPOLA se convierte
    assert rep["sin_divipola"] == 0 and rep["nombre_distinto_en_divipola"] == 0


def test_simplificar_no_abre_huecos_ni_solapes_entre_vecinos():
    g, rep = mo.limpiar(_bruto(), _divipola())
    u = g.to_crs(3116).union_all()
    assert rep["partes_del_departamento"] == 1 and rep["huecos_entre_municipios"] == 0
    assert g.to_crs(3116).area.sum() == pytest.approx(u.area, rel=1e-6)     # si se solaparan, la suma superaria a la union
    assert rep["vertices_plata"] < rep["vertices_bronce"] + 1


def test_el_punto_de_la_etiqueta_cae_dentro_del_poligono():
    g, _ = mo.limpiar(_bruto(), _divipola())
    from shapely.geometry import Point
    assert all(p.contains(Point(x, y)) for p, x, y in zip(g.geometry, g["etiqueta_lon"], g["etiqueta_lat"]))
