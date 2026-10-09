import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from comun.config import cargar_parametros  # noqa: E402
from modelo.ram import Ram, normalizar_consecuencia, normalizar_probabilidad, probabilidad_por_frecuencia  # noqa: E402
from oro import contexto as ctx  # noqa: E402
from plata import sinteticos as ps  # noqa: E402

RAM = Ram(cargar_parametros(oficial=True)["ram"])


# ---- la matriz tal como la publica el instructivo ECP-DRI-I-007 --------------------------------------------------

@pytest.mark.parametrize("c,p,nivel", [
    (5, "A", "M"), (5, "C", "H"), (5, "E", "VH"), (4, "A", "L"), (4, "D", "H"), (3, "A", "N"), (3, "E", "H"),
    (2, "C", "L"), (2, "E", "M"), (1, "D", "L"), (1, "C", "N"), (0, "E", "N"),
])
def test_cada_celda_de_la_matriz(c, p, nivel):
    assert RAM.nivel(c, p) == nivel


def test_la_matriz_no_es_un_producto():
    # una consecuencia catastrofica rara (5A) pesa mas que una leve frecuente (1E), aunque 5x1 = 1x5
    assert RAM.nivel(5, "A") == "M" and RAM.nivel(1, "E") == "L"


def test_manda_la_peor_dimension_como_en_el_ejemplo_del_instructivo():
    # "personas 5C, economico 2C, medio ambiente 1D, clientes 2D e imagen 1C: el riesgo es 5C" (misma probabilidad aqui)
    r = RAM.clasificar({"PE": 5, "EC": 2, "MA": 1, "CL": 2, "IM": 1}, "C")
    assert r == {"codigo": "5C", "nivel": "H", "dimension": "PE", "consecuencia": 5}


def test_una_dimension_sin_calificar_no_cuenta_y_sin_ninguna_no_hay_nivel():
    assert RAM.clasificar({"PE": None, "EC": 3}, "D")["codigo"] == "3D"
    assert RAM.clasificar({}, "D")["nivel"] is None


@pytest.mark.parametrize("crudo,letra", [("C", "C"), ("c", "C"), (" d ", "D"), ("E - Sucede varias veces al año en la unidad", "E"),
                                         ("3", "C"), (3.0, "C"), ("Alta", None), ("", None), (None, None), ("7", None)])
def test_normalizar_probabilidad(crudo, letra):
    assert normalizar_probabilidad(crudo) == letra


@pytest.mark.parametrize("crudo,valor", [("4", 4), (" 2 ", 2), (5.0, 5), (6, None), ("x", None), (None, None)])
def test_normalizar_consecuencia(crudo, valor):
    assert normalizar_consecuencia(crudo) == valor


def test_probabilidad_por_frecuencia():
    u = {"E": 12, "D": 4, "C": 1}
    assert [probabilidad_por_frecuencia(n, h, u) for n, h in [(20, True), (5, True), (1, True), (0, True), (0, False)]] == ["E", "D", "C", "B", "A"]


# ---- Plata: el registro queda ubicado en la matriz ----------------------------------------------------------------

def _registro():
    base = {"tipo": "amenaza", "estado": "latente", "categoria": "seguridad_fisica", "id_paquete_trabajo": "P1",
            "cons_personas": 4, "cons_economica": "2", "cons_ambiental": 0, "cons_clientes": None, "cons_imagen": 1}
    return pd.DataFrame([
        {**base, "id_riesgo": "R1", "probabilidad": "d", "probabilidad_residual": "B - Ha ocurrido en la industria"},
        {**base, "id_riesgo": "R2", "probabilidad": "C", "probabilidad_residual": "E"},      # los controles no pueden subirla
        {**base, "id_riesgo": "R3", "probabilidad": "5", "probabilidad_residual": None},     # sin residual: igual a la inherente
    ])


def test_plata_clasifica_inherente_y_residual():
    df, rep = ps.clasificar_ram(_registro(), RAM)
    r = df.set_index("id_riesgo")
    assert r.loc["R1", "ram_inherente"] == "4D" and r.loc["R1", "nivel_inherente"] == "H"
    assert r.loc["R1", "ram_residual"] == "4B" and r.loc["R1", "nivel_residual"] == "M" and r.loc["R1", "puntaje_ram"] == 3
    assert r.loc["R1", "dimension_dominante"] == "PE"
    assert r.loc["R2", "probabilidad_residual"] == "C" and rep["ram_residual_mayor_corregido"] == 1
    assert r.loc["R3", "ram_residual"] == "4E" and r.loc["R3", "nivel_residual"] == "H" and rep["ram_residual_igual_a_inherente"] == 1
    assert rep["ram_dimensiones_sin_calificar"] == 3                     # cons_clientes vacia en las tres


# ---- Oro: sugerencias del territorio --------------------------------------------------------------------------------

def test_las_sugerencias_marcan_los_riesgos_calificados_por_debajo_de_la_evidencia():
    cfg = cargar_parametros(oficial=True)["ram"]["sugerencias"]
    t = pd.DataFrame({"id_paquete": ["P1"], "codigo_municipio": ["44430"], "municipio": ["Maicao"], "pdet": [False],
                      "distancia_resguardo_km": [0.0], "distancia_area_protegida_km": [1.5]})
    seg = pd.DataFrame({"codigo": ["44430"] * 2, "mes": pd.to_datetime(["2026-07-01", "2026-08-01"]),
                        "delito": ["extorsion", "homicidio"], "casos": [15, 40], "victimas": [15, 40]})
    em = pd.DataFrame({"codigo": ["44430"] * 3, "anio": [2024, 2025, 2025], "tipo": ["Inundación o creciente"] * 3})
    riesgos = gpd.GeoDataFrame({
        "id_riesgo": ["R1", "R2", "R3", "R4"], "id_paquete_trabajo": ["P1"] * 4, "tipo": ["amenaza"] * 4, "estado": ["latente"] * 4,
        "categoria": ["seguridad_fisica", "social_comunidad", "ambiental", "ambiental"],
        "probabilidad": ["B", "C", "C", "C"], "cons_imagen": [1, 2, 0, 0], "cons_ambiental": [0, 0, 4, 2]},
        geometry=[Point(0, 0)] * 4)
    s, rep = ctx.sugerencias_ram(t, seg, em, riesgos, cfg)
    f = s.iloc[0]
    assert f["ram_prob_seguridad"] == "E"                  # 15 extorsiones al ano (el homicidio no cuenta)
    assert f["ram_prob_desastres"] == "C"                  # 3 emergencias en 2 anos = 1,5 al ano
    assert f["ram_cons_imagen"] == 4 and f["ram_cons_ambiental"] == 4
    assert f["ram_por_revisar_ids"] == "R1,R2,R4"          # R3 ya tiene ambiental 4
    assert rep["riesgos_ram_por_revisar"] == 3


def test_parametros_de_la_matriz_completos():
    cfg = cargar_parametros(oficial=True)["ram"]
    assert set(cfg["matriz"]) == {0, 1, 2, 3, 4, 5} and all(len(f) == 5 for f in cfg["matriz"].values())
    assert {n for f in cfg["matriz"].values() for n in f} <= set(cfg["niveles"])
