import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from affine import Affine
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oro import chirps as oro_chirps  # noqa: E402
from plata import chirps as plata_chirps  # noqa: E402

# rejilla de 2 x 2 celdas de 0,05 grados, como la de CHIRPS, sobre La Guajira
TRANSFORM = Affine(0.05, 0, -72.5, 0, -0.05, 11.5)
NODATA = -9999.0


def _municipios():
    """A cubre la columna izquierda entera; B solo la mitad izquierda de la columna derecha."""
    return gpd.GeoDataFrame({"codigo": ["44001", "44002"], "nombre": ["A", "B"]},
                            geometry=[box(-72.5, 11.4, -72.45, 11.5), box(-72.45, 11.4, -72.425, 11.5)], crs=4326)


def test_cada_municipio_recibe_sus_celdas_con_el_area_que_cae_adentro():
    pesos = plata_chirps.pesos_por_municipio(TRANSFORM, 2, 2, _municipios())
    a, b = pesos[pesos["codigo"] == "44001"], pesos[pesos["codigo"] == "44002"]
    assert sorted(a["col"]) == [0, 0] and sorted(a["fila"]) == [0, 1]
    assert sorted(b["col"]) == [1, 1]
    # B tiene la mitad de cada celda (en metros, casi exacto a esta escala)
    assert b["area_m2"].sum() / a["area_m2"].sum() == pytest.approx(0.5, rel=1e-3)
    assert a["area_m2"].sum() == pytest.approx(2 * 5_470 * 5_530, rel=0.02)     # dos celdas de ~5,5 x 5,5 km


def test_la_lluvia_es_el_promedio_ponderado_por_area_sin_contar_el_mar():
    pesos = pd.DataFrame({"codigo": ["X", "X", "X"], "nombre": ["X"] * 3, "fila": [0, 0, 1], "col": [0, 1, 0],
                          "area_m2": [3.0, 1.0, 4.0]})
    valores = np.array([[10.0, 50.0], [NODATA, 0.0]])
    z = plata_chirps.lluvia_por_zona(valores, pesos, NODATA).iloc[0]
    assert z["mm"] == pytest.approx((10 * 3 + 50 * 1) / 4)                         # la celda de mar no cuenta
    assert z["fraccion_con_dato"] == pytest.approx(0.5)                              # 4 de 8 m2 con dato


def test_valores_imposibles_se_descartan_y_sin_dato_queda_vacio():
    pesos = pd.DataFrame({"codigo": ["X", "X", "Y"], "nombre": ["X", "X", "Y"], "fila": [0, 0, 1], "col": [0, 1, 1],
                          "area_m2": [1.0, 1.0, 1.0]})
    valores = np.array([[20.0, 9_000.0], [0.0, NODATA]])
    z = plata_chirps.lluvia_por_zona(valores, pesos, NODATA).set_index("codigo")
    assert z.loc["X", "mm"] == pytest.approx(20.0)
    assert np.isnan(z.loc["Y", "mm"]) and z.loc["Y", "fraccion_con_dato"] == 0


PROV = {"bronce": {"fuente": "CHIRPS v3.0", "licencia": "CC BY 4.0", "cita": "doi", "descargado_en": "2026-10-01T00:00:00"}}


def _tabla(desde: str, hasta: str) -> pd.DataFrame:
    """Lluvia de prueba: cada mes llueve 10 x el numero del mes; agosto de 2026 llueve la mitad."""
    filas = []
    for codigo, nombre in [("44", "La Guajira"), ("44001", "Riohacha")]:
        for mes in pd.date_range(desde, hasta, freq="MS"):
            mm = 10.0 * mes.month * (0.5 if mes == pd.Timestamp(2026, 8, 1) else 1)
            filas.append({"codigo": codigo, "municipio": nombre, "mes": mes, "mm": mm, "fraccion_con_dato": 1.0})
    return pd.DataFrame(filas)


def test_oro_da_normal_anomalia_y_los_ultimos_anos():
    oro = oro_chirps.construir(_tabla("1991-01-01", "2026-08-01"), PROV)
    m = oro["metadata"]
    assert m["desde"] == "2016-01" and m["hasta"] == "2026-08" and len(m["meses"]) == 128
    assert m["normal"] == "1991-2020" and m["normal_completa"] is True
    assert oro["departamento"]["nombre"] == "La Guajira" and "44" not in oro["municipios"]
    r = oro["municipios"]["44001"]
    assert r["normal"] == [10.0 * k for k in range(1, 13)]
    assert r["normal_anual"] == 780
    assert len(r["mm"]) == len(r["anomalia_pct"]) == 128
    assert r["mm"][-1] == 40.0 and r["anomalia_pct"][-1] == -50                      # agosto 2026: la mitad de lo normal
    assert r["anomalia_pct"][0] == 0


def test_sin_30_anos_la_normal_usa_lo_que_hay_y_lo_dice():
    oro = oro_chirps.construir(_tabla("2012-01-01", "2026-08-01"), PROV)
    m = oro["metadata"]
    assert m["normal_completa"] is False
    assert m["normal"] == "2012-2015"                                                 # los anos antes de los visibles
