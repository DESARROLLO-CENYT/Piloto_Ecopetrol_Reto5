import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from modelo import ict


def test_decaimiento_lineal_extremos():
    d = ict.decaimiento_lineal(np.array([0, 500, 1000, 2000]), radio_m=1000)
    assert d[0] == 1.0
    assert d[2] == 0.0
    assert d[3] == 0.0  # mas alla del radio, se satura en 0
    assert 0 < d[1] < 1


def test_normalizar_minmax_rango():
    serie = pd.Series([10, 20, 30, 40])
    norm = ict.normalizar_minmax(serie)
    assert norm.min() == 0.0
    assert norm.max() == 1.0
    assert norm.iloc[1] == pytest.approx(1 / 3)


def test_normalizar_minmax_constante_no_rompe():
    serie = pd.Series([5, 5, 5])
    norm = ict.normalizar_minmax(serie)
    assert (norm == 0.0).all()


def test_saturar():
    assert ict.saturar(0, 10) == 0.0
    assert ict.saturar(5, 10) == 0.5
    assert ict.saturar(15, 10) == 1.0  # se satura, no supera 1
    assert ict.saturar(5, 0) == 0.0    # maximo 0 no debe dividir por cero


def test_clasificar_ict_umbrales():
    umbrales = {"bajo": 25, "medio": 50, "alto": 75}
    assert ict.clasificar_ict(10, umbrales) == "bajo"
    assert ict.clasificar_ict(25, umbrales) == "medio"
    assert ict.clasificar_ict(60, umbrales) == "alto"
    assert ict.clasificar_ict(80, umbrales) == "critico"


def test_ensamblar_ict_caso_manual():
    """Dos paquetes, un solo criterio activo con peso 1: el ICT debe ser
    exactamente 0 y 100 tras la normalizacion min-max, sin importar el resto
    de criterios (que quedan en cero porque no hay datos).
    """
    ids = ["A", "B"]
    crudos = {"severidad_riesgo": pd.Series({"A": 2.0, "B": 10.0})}
    pesos = {
        "severidad_riesgo": 1.0, "exposicion_proyecto": 0.0,
        "vulnerabilidad_territorial": 0.0, "amenazas_externas": 0.0, "convergencia": 0.0,
    }
    tabla, bounds = ict.ensamblar_ict(crudos, pesos, ids)
    assert tabla.loc["A", "ICT"] == 0.0
    assert tabla.loc["B", "ICT"] == 100.0
    assert bounds["severidad_riesgo"] == (2.0, 10.0)


def test_ensamblar_ict_reutiliza_bounds_externos():
    """Si se fijan bounds externos (como al comparar con una fecha pasada),
    un valor crudo igual al del caso anterior debe dar el mismo ICT que en
    el corte donde se calcularon esos bounds, no uno recalculado localmente.
    """
    ids = ["A"]
    crudos_hoy = {"severidad_riesgo": pd.Series({"A": 10.0})}
    pesos = {
        "severidad_riesgo": 1.0, "exposicion_proyecto": 0.0,
        "vulnerabilidad_territorial": 0.0, "amenazas_externas": 0.0, "convergencia": 0.0,
    }
    _, bounds_hoy = ict.ensamblar_ict(crudos_hoy, pesos, ["A", "B"], )  # bounds reales: min=?, usemos dataset con A y B
    crudos_hoy2 = {"severidad_riesgo": pd.Series({"A": 2.0, "B": 10.0})}
    _, bounds_hoy2 = ict.ensamblar_ict(crudos_hoy2, pesos, ids_paquete=["A", "B"])

    crudos_ayer = {"severidad_riesgo": pd.Series({"A": 6.0, "B": 6.0})}
    tabla_ayer, _ = ict.ensamblar_ict(crudos_ayer, pesos, ["A", "B"], bounds=bounds_hoy2)
    # 6 esta a mitad de camino entre 2 y 10 -> ICT 50, usando los bounds de "hoy"
    assert tabla_ayer.loc["A", "ICT"] == 50.0


def test_estado_efectivo_antes_de_identificacion():
    fila = pd.Series({
        "fecha_identificacion": pd.Timestamp("2026-06-01"),
        "fecha_materializacion": pd.NaT,
        "estado": "latente",
    })
    assert ict.estado_efectivo(fila, pd.Timestamp("2026-05-01")) is None


def test_estado_efectivo_materializado_en_el_pasado_era_proximo():
    fila = pd.Series({
        "fecha_identificacion": pd.Timestamp("2026-05-01"),
        "fecha_materializacion": pd.Timestamp("2026-06-10"),
        "estado": "materializado",
    })
    assert ict.estado_efectivo(fila, pd.Timestamp("2026-06-01")) == "proximo_a_materializarse"
    assert ict.estado_efectivo(fila, pd.Timestamp("2026-06-15")) == "materializado"
