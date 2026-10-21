"""Las fechas de cada riesgo cuentan una historia posible: el generador las saca del estado, el nivel RAM y la actividad, y
Plata lee las que llegan escritas de otra forma, corrige lo que tiene una sola explicacion y marca el resto."""
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from bronce import cronograma_sintetico, fechas_riesgo_sintetico as gen, riesgo_actividad_sintetico as gen_act, sinteticos as s  # noqa: E402
from comun.config import cargar_parametros  # noqa: E402
from modelo import fechas_riesgo as m  # noqa: E402
from plata import sinteticos as plata  # noqa: E402

CORTE = pd.Timestamp("2026-10-14")
T = pd.Timestamp
MATRIZ = {int(k): list(v) for k, v in cargar_parametros(oficial=True)["ram"]["matriz"].items()}


# --------------------------------------------------------------------------- Plata: leer y revisar

def test_lee_fechas_iso_y_dia_mes_ano_en_la_misma_columna():
    f, n = m.leer(pd.Series(["2026-05-16", "16/05/2026", "2026-05-16 00:00:00", None, "basura"]))
    assert f.tolist()[:3] == [T("2026-05-16")] * 3
    assert f.isna().tolist()[3:] == [True, True]
    assert n == 1


def _r(estado, ident, fm=None, accion=None):
    return {"estado": estado, "fecha_identificacion": ident, "fecha_materializacion": fm, "fecha_ejecucion_accion": accion}


def test_revisar_corrige_lo_que_tiene_una_sola_explicacion_y_marca_lo_demas():
    df = pd.DataFrame([
        _r("materializado", "2026-06-10", "2026-05-01", "2026-06-20"),     # 0 cruzadas: se intercambian
        _r("materializado", "2026-06-10", "2027-07-01", "2026-07-10"),     # 1 un ano de mas: 2026-07-01
        _r("materializado", "2026-09-30", "2027-09-01"),                   # 2 en el futuro y con un ano menos queda antes de identificar
        _r("materializado", "2026-06-10", None),                           # 3 sin fecha
        _r("latente", "2026-06-10", "2026-07-01"),                         # 4 abierto con materializacion
        _r("latente", "2026-06-10", None, "2026-05-01"),                   # 5 accion antes de identificar
        _r("latente", "10/06/2026", None, "2026-07-01"),                   # 6 bien (dia/mes/ano)
    ])
    out, rep = m.revisar(df, CORTE)
    assert (out.loc[0, "fecha_identificacion"], out.loc[0, "fecha_materializacion"]) == (T("2026-05-01"), T("2026-06-10"))
    assert out.loc[1, "fecha_materializacion"] == T("2026-07-01")
    assert pd.isna(out.loc[2, "fecha_materializacion"])
    assert out["revisar_fechas"].tolist() == [True] * 6 + [False]
    assert out.loc[6, "fecha_identificacion"] == T("2026-06-10")
    assert rep == {"fechas_dia_mes_ano": 1, "fechas_materializacion_antes_de_identificacion": 1, "fechas_materializacion_futura_corregida": 1,
                   "fechas_materializacion_futura_sin_corregir": 1, "fechas_materializado_sin_fecha": 1, "fechas_abierto_con_materializacion": 1,
                   "fechas_identificacion_futura": 0, "fechas_accion_antes_de_identificacion": 1, "riesgos_fechas_por_revisar": 6}
    assert "intercambiaron" in out.loc[0, "problema_fechas"] and "un año" in out.loc[1, "problema_fechas"]


# --------------------------------------------------------------------------- generador

def _act(inicio_real, fin_real, ini_proy="2026-01-01", fin_proy="2027-01-01"):
    return pd.Series({"fecha_inicio_real": T(inicio_real) if inicio_real else pd.NaT, "fecha_fin_real": T(fin_real) if fin_real else pd.NaT,
                      "fecha_inicio_proyectada": T(ini_proy), "fecha_fin_proyectada": T(fin_proy)})


def test_un_materializado_ocurre_mientras_se_ejecuta_su_actividad_y_nunca_en_el_futuro():
    r = np.random.default_rng(1)
    for act in (_act("2026-03-01", "2026-06-30"), _act("2026-08-01", None), _act("2025-01-01", "2025-04-01")):
        for _ in range(50):
            f = gen.fechas("materializado", "H", act, T("2025-01-01"), CORTE, r)
            fin = act["fecha_fin_real"] if pd.notna(act["fecha_fin_real"]) else CORTE
            assert act["fecha_inicio_real"] <= f["fecha_materializacion"] <= min(fin, CORTE)
            assert f["fecha_identificacion"] < f["fecha_materializacion"] < f["fecha_ejecucion_accion"]


def test_la_accion_de_un_riesgo_abierto_es_mas_urgente_cuanto_mas_grave():
    r = np.random.default_rng(2)
    act = _act("2026-08-01", None)

    def dias_hasta_la_accion(nivel):
        f = [gen.fechas("latente", nivel, act, T("2025-01-01"), CORTE, r) for _ in range(300)]
        d = np.array([(x["fecha_ejecucion_accion"] - CORTE).days for x in f])
        assert all(CORTE - pd.Timedelta(days=180) <= x["fecha_identificacion"] < CORTE for x in f)
        return np.median(d[d >= 0]), np.mean(d < 0)

    vh, n = dias_hasta_la_accion("VH"), dias_hasta_la_accion("N")
    assert vh[0] < n[0]                       # lo que falta para la accion
    assert 0.1 < vh[1] < 0.5                  # una parte queda vencida


def test_el_nivel_residual_lee_la_probabilidad_como_llegue():
    fila = {"probabilidad_residual": "4", "cons_personas": 3, "cons_economica": 1, "cons_ambiental": 0, "cons_clientes": None, "cons_imagen": 1}
    assert gen.nivel_residual(pd.Series(fila), MATRIZ) == gen.nivel_residual(pd.Series({**fila, "probabilidad_residual": "D - Sucede"}), MATRIZ)


def test_un_riesgo_proximo_a_materializarse_pega_en_algo_que_se_ejecuta_o_arranca_pronto():
    acts = pd.DataFrame({
        "id_actividad": ["A1", "A2", "A3"], "avance": [1.0, 0.3, 0.0], "peso_en_paquete": [0.3, 0.4, 0.3], "clave": ["civil", "montaje", "pruebas"],
        "fecha_inicio_real": [T("2026-01-01"), T("2026-08-01"), pd.NaT], "fecha_fin_real": [T("2026-07-31"), pd.NaT, pd.NaT],
        "fecha_inicio_proyectada": [T("2026-01-01"), T("2026-08-01"), T("2027-03-01")],
    })
    r = np.random.default_rng(3)
    elegidas = {gen_act.elegir(acts, {"pruebas"}, "proximo_a_materializarse", CORTE, r) for _ in range(40)}
    assert elegidas == {"A2"}                 # las pruebas arrancan en marzo: todavia no estan "proximas"
    latentes = {gen_act.elegir(acts, {"pruebas"}, "latente", CORTE, r) for _ in range(40)}
    assert "A3" in latentes and "A1" not in latentes


# --------------------------------------------------------------------------- registro completo

@pytest.fixture(scope="module")
def plata_limpia():
    hoy = date.today()
    _, paq = s.generar_proyectos_y_paquetes()
    _, act, _ = cronograma_sintetico.generar(paq, hoy, 42)
    df, clave = s.generar_registro_riesgos(paq, s.generar_comunidades(), s.generar_areas_protegidas(), actividades=act)
    acts, _ = plata.limpiar_actividades(act, gpd.GeoDataFrame(paq), pd.DataFrame({"id_paquete": paq["id_paquete"], "presupuesto_usd": 1}))
    gdf, rep = plata.limpiar_riesgos(df, gpd.GeoDataFrame(paq), clave=clave, actividades=acts)
    return gdf, rep, acts


def test_despues_de_plata_ninguna_fecha_es_imposible(plata_limpia):
    gdf, rep, acts = plata_limpia
    corte = pd.to_datetime(acts["fecha_corte"]).max()
    fm, ident = pd.to_datetime(gdf["fecha_materializacion"]), pd.to_datetime(gdf["fecha_identificacion"])
    assert not (fm > corte).any() and not (fm < ident).any()
    assert not ((gdf["estado"] != "materializado") & fm.notna()).any()
    assert rep["fechas_dia_mes_ano"] > 0                                   # llegaron fechas escritas dia/mes/ano
    assert rep["riesgos_fechas_por_revisar"] == int(gdf["revisar_fechas"].sum())


def test_cada_materializado_ocurrio_durante_su_actividad(plata_limpia):
    gdf, _, acts = plata_limpia
    a = acts.set_index("id_actividad")
    mat = gdf[(gdf["estado"] == "materializado") & gdf["fecha_materializacion"].notna()]
    fm = pd.to_datetime(mat["fecha_materializacion"])
    corte = pd.to_datetime(acts["fecha_corte"]).max()
    assert (mat["id_actividad"].map(a["fecha_inicio_real"]) <= fm).all()
    assert (fm <= mat["id_actividad"].map(a["fecha_fin_real"]).fillna(corte)).all()
