import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plata import red_vial as rv


def _invias():
    """Una via nacional de ~11 km hacia el norte, sin superficie."""
    return gpd.GeoDataFrame({
        "id_tramo": ["90-9010-1"], "ruta": ["90"], "nombre_ruta": ["Transversal del Caribe"], "sector": ["Riohacha - Paraguachon"],
        "categoria_txt": ["Primer orden"], "administrador_txt": ["ANI"], "calzada_txt": ["Sencilla"], "superficie_txt": [None],
    }, geometry=[LineString([(-72.5, 11.0), (-72.5, 11.1)])], crs="EPSG:4326")


def _igac():
    """La misma via nacional (con ~20 m de desfase), una via que sale de ella, una trocha lejana y una astilla."""
    filas = [
        ("v1-1-1", 1, "Pavimentada, 2 o más carriles", "Pavimentada", LineString([(-72.5002, 11.0), (-72.5002, 11.1)])),   # repetida
        ("v3-2-1", 3, "Pavimentada, angosta", "Pavimentada", LineString([(-72.5, 11.05), (-72.4, 11.05)])),                # sale de la nacional
        ("v6-3-1", 6, "Trocha sin afirmar, solo en tiempo seco", "Sin afirmar", LineString([(-72.3, 11.0), (-72.3, 11.1)])),
        ("v5-4-1", 5, "Sin pavimentar, solo en tiempo seco", "Sin pavimentar", LineString([(-72.5, 11.2), (-72.4995, 11.2)])),   # 55 m
    ]
    return gpd.GeoDataFrame({
        "id_via": [f[0] for f in filas], "tipo": [f[1] for f in filas], "clase": [f[2] for f in filas], "superficie": [f[3] for f in filas],
        "carriles": [None] * 4, "accesibilidad": [None, None, "Solo en tiempo seco", None], "nombre": [None] * 4,
    }, geometry=[f[4] for f in filas], crs="EPSG:4326")


def test_no_cuenta_dos_veces_la_misma_via():
    red, rep = rv.unir(_invias(), _igac())
    assert 11.0 < rep["km_igac_repetido_con_invias"] < 11.5       # la via repetida (11,1 km) + los primeros 50 m de la que sale de ella
    por_fuente = red.groupby("fuente")["km"].sum()
    assert por_fuente["INVIAS"] == pytest.approx(11.1, rel=0.03)
    # del IGAC quedan la via que sale de la nacional (~11 km) y la trocha (~11 km); no la repetida ni la astilla
    assert sorted(red[red["fuente"] == "IGAC"]["id_tramo"]) == ["igac-v3-2-1", "igac-v6-3-1"]
    assert rep["km_red"] == pytest.approx(11.1 + 10.9 + 11.1, abs=1.0)


def test_las_dos_redes_se_distinguen():
    red, _ = rv.unir(_invias(), _igac())
    nac = red[red["fuente"] == "INVIAS"].iloc[0]
    assert nac["estilo"] == "n1" and nac["grupo"] == "Red nacional" and nac["ruta"] == "90"
    assert set(red[red["fuente"] == "IGAC"]["estilo"]) == {"i3", "i6"} and (red[red["fuente"] == "IGAC"]["grupo"] == "Red complementaria").all()
    # el IGAC va primero para que el mapa lo dibuje debajo de la red nacional
    assert list(red["fuente"])[-1] == "INVIAS"


def test_la_superficie_de_invias_sale_del_igac():
    red, rep = rv.unir(_invias(), _igac())
    nac = red[red["fuente"] == "INVIAS"].iloc[0]
    assert nac["superficie"] == "Pavimentada" and nac["superficie_fuente"] == "IGAC (cruce espacial)"
    assert rep["tramos_invias_con_superficie_del_igac"] == 1
