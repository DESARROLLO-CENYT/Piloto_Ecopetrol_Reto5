"""Cronograma por actividades: el generador cuenta una sola historia (fechas, holgura, avance), Plata limpia lo sucio y el
avance de paquetes y proyectos es la suma de lo que aporta cada actividad."""
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from bronce import cronograma_sintetico as gen  # noqa: E402
from modelo import cronograma as m  # noqa: E402
from oro import cronograma as oro  # noqa: E402
from plata import sinteticos as plata  # noqa: E402

HOY = date(2026, 10, 13)
CORTE = pd.Timestamp(HOY)


def _paquetes():
    filas = []
    for i, (proy, n) in enumerate((("PRY-01", 4), ("PRY-02", 6), ("PRY-03", 4))):
        for k in range(1, n + 1):
            filas.append({"id_paquete": f"{proy}-PT{k:02d}", "id_proyecto": proy, "ruta_critica": k == 1, "nombre": f"Paquete {k}"})
    return pd.DataFrame(filas)


@pytest.fixture(scope="module")
def sintetico():
    return gen.generar(_paquetes(), HOY, 42)


def _limpias(sintetico):
    """Lo que dejaria Plata sobre el generador."""
    cron, act, _ = sintetico
    gdf = gpd.GeoDataFrame(_paquetes())
    a, rep_a = plata.limpiar_actividades(act, gdf, cron)
    c, rep_c = plata.limpiar_cronograma(cron, gdf, a)
    return a, c, rep_a, rep_c


# --- generador ------------------------------------------------------------------------------------------------------

def test_el_generador_es_reproducible():
    a = gen.generar(_paquetes(), HOY, 42)
    b = gen.generar(_paquetes(), HOY, 42)
    for x, y in zip(a, b):
        pd.testing.assert_frame_equal(x, y)


def test_cada_paquete_tiene_entre_5_y_7_actividades_con_las_obligatorias(sintetico):
    _, act, _ = sintetico
    por_paq = act.drop_duplicates("id_actividad").groupby("id_paquete")
    assert por_paq.size().between(5, 7).all()
    assert por_paq["nombre"].apply(lambda s: {"Adquisición de equipos y materiales", "Montaje electromecánico", "Pruebas y puesta en servicio"} <= set(s)).all()


def test_la_holgura_y_las_fechas_cuentan_la_misma_historia(sintetico):
    cron, _, fechas = sintetico
    fin_proy = pd.to_datetime(fechas.set_index("id_proyecto")["fecha_fin_plan"])
    c = cron.set_index("id_paquete")
    proyecto = _paquetes().set_index("id_paquete")["id_proyecto"]
    fin_del_proyecto = pd.Series(pd.to_datetime(c.index.map(proyecto).map(fin_proy)), index=c.index)
    dias_antes = (fin_del_proyecto - pd.to_datetime(c["fecha_fin_plan"])).dt.days
    assert (dias_antes == c["holgura_dias"]).all()
    critico = _paquetes().set_index("id_paquete")["ruta_critica"].reindex(c.index)
    assert (c.loc[critico, "holgura_dias"] == 0).all()


def test_ningun_proyecto_ha_terminado_ni_empieza_en_el_futuro(sintetico):
    _, _, fechas = sintetico
    assert (pd.to_datetime(fechas["fecha_fin_plan"]) > CORTE).all()
    assert (pd.to_datetime(fechas["fecha_inicio_plan"]) < CORTE).all()


def test_lo_pendiente_se_proyecta_desde_hoy_en_adelante_y_lo_hecho_tiene_fecha_real(sintetico):
    _, act, _ = sintetico
    a = act.drop_duplicates("id_actividad").copy()
    a["avance"] = pd.to_numeric(a["avance"]).where(pd.to_numeric(a["avance"]) <= 1, pd.to_numeric(a["avance"]) / 100)
    pendientes = a[a["avance"] < 1]
    assert (pd.to_datetime(pendientes["fecha_fin_proyectada"]) >= CORTE).all()
    hechas = a[a["avance"] >= 1]
    assert hechas["fecha_fin_real"].notna().all()
    assert (pd.to_datetime(hechas["fecha_fin_real"]) <= CORTE).all()


def test_el_export_viene_sucio_a_proposito(sintetico):
    _, act, _ = sintetico
    assert act["id_actividad"].duplicated().any()                       # filas repetidas
    assert (pd.to_numeric(act["avance"]) > 1).any()                     # avances en porcentaje
    assert act["estado"].isin(["por_iniciar", "en_curso", "completada"]).sum() < len(act)   # estados con formato distinto


# --- modelo ---------------------------------------------------------------------------------------------------------

def test_estados_con_distinto_formato_se_normalizan():
    s = pd.Series(["Completada", " EN_CURSO ", "en curso", "Por Iniciar", "terminada", "???", None])
    assert m.normalizar_estado(s).tolist()[:5] == ["completada", "en_curso", "en_curso", "por_iniciar", "completada"]
    assert m.normalizar_estado(s).isna().tolist()[5:] == [True, True]


def test_el_estado_sale_del_avance():
    assert m.estado_por_avance(pd.Series([0.0, 0.4, 1.0])).tolist() == ["por_iniciar", "en_curso", "completada"]


def test_el_avance_en_porcentaje_se_pasa_a_fraccion():
    a, n = m.normalizar_avance(pd.Series([0.5, 50, 100, 1.0, -3, "x"]))
    assert n == 2
    assert a.dropna().tolist() == [0.5, 0.5, 1.0, 1.0, 0.0]


def test_los_pesos_se_renormalizan_para_que_sumen_uno():
    df = pd.DataFrame({"id_paquete": ["A", "A", "A", "B", "B"], "peso_en_paquete": [1, 1, 2, 0.5, 0.5]})
    w, n_mal = m.normalizar_pesos(df)
    assert w.groupby(df["id_paquete"]).sum().tolist() == pytest.approx([1, 1])
    assert n_mal == 1                                  # solo A estaba mal
    assert w.tolist()[:3] == pytest.approx([0.25, 0.25, 0.5])


def test_el_peso_en_el_proyecto_es_el_del_paquete_por_su_presupuesto():
    act = pd.DataFrame({"id_paquete": ["A", "A", "B", "B"], "peso_en_paquete": [0.5, 0.5, 0.25, 0.75]})
    presupuesto = pd.Series({"A": 30.0, "B": 10.0})
    proyecto = pd.Series({"A": "P1", "B": "P1"})
    w = m.peso_en_proyecto(act, presupuesto, proyecto)
    assert w.tolist() == pytest.approx([0.375, 0.375, 0.0625, 0.1875])
    assert w.sum() == pytest.approx(1)


def _act_pequena():
    """Un proyecto, dos paquetes (60 % / 40 % del presupuesto), dos actividades cada uno. Corte a mitad del plan."""
    f = lambda s: pd.Timestamp(s)  # noqa: E731
    return pd.DataFrame({
        "id_actividad": ["A1", "A2", "B1", "B2"], "id_paquete": ["A", "A", "B", "B"], "id_proyecto": ["P"] * 4, "orden": [1, 2, 1, 2],
        "estado": ["completada", "por_iniciar", "en_curso", "por_iniciar"], "avance": [1.0, 0.0, 0.5, 0.0],
        "peso_en_paquete": [0.5, 0.5, 0.5, 0.5], "peso_en_proyecto": [0.3, 0.3, 0.2, 0.2],
        "fecha_inicio_plan": [f("2026-01-01"), f("2026-04-11"), f("2026-01-01"), f("2026-04-11")],
        "fecha_fin_plan": [f("2026-04-11"), f("2026-07-20"), f("2026-04-11"), f("2026-07-20")],
        "fecha_inicio_proyectada": [f("2026-01-01"), f("2026-04-20"), f("2026-01-01"), f("2026-04-20")],
        "fecha_fin_proyectada": [f("2026-04-11"), f("2026-08-01"), f("2026-04-30"), f("2026-08-10")],
    })


def test_valor_planeado_va_de_cero_a_uno_segun_el_calendario():
    a = _act_pequena()
    pv = m.valor_planeado(a, pd.Timestamp("2026-04-11"))
    assert pv.tolist() == pytest.approx([1.0, 0.0, 1.0, 0.0])
    pv = m.valor_planeado(a, pd.Timestamp("2026-08-30"))
    assert (pv == 1).all()
    pv = m.valor_planeado(a, pd.Timestamp("2025-12-01"))
    assert (pv == 0).all()


def test_el_avance_de_paquetes_y_proyectos_es_la_suma_de_peso_por_avance():
    a = _act_pequena()
    corte = pd.Timestamp("2026-04-11")
    paq = m.consolidar_paquetes(a, corte)
    assert paq["avance"].to_dict() == pytest.approx({"A": 0.5, "B": 0.25})
    assert paq["avance_plan"].to_dict() == pytest.approx({"A": 0.5, "B": 0.5})
    assert paq["indice_cumplimiento"].to_dict() == pytest.approx({"A": 1.0, "B": 0.5})
    assert paq.loc["B", "atraso_proyectado_dias"] == 21
    pq = paq.assign(id_proyecto="P", presupuesto_usd=[60.0, 40.0], holgura_dias=[0, 10])
    proy = m.consolidar_proyectos(a, pq, corte)
    assert proy.loc["P", "avance"] == pytest.approx(0.3 + 0.1)          # 0,3 de A1 + 0,2 * 0,5 de B1
    assert proy.loc["P", "paquete_que_define_el_fin"] == "B"
    assert proy.loc["P", "paquetes_sobre_su_holgura"] == 2              # A: +12 d con holgura 0; B: +21 d con holgura 10
    assert proy.loc["P", "n_completadas"] == 1


# --- plata y oro ----------------------------------------------------------------------------------------------------

def test_plata_deja_actividades_limpias_y_pesos_que_suman_uno(sintetico):
    a, c, rep_a, _ = _limpias(sintetico)
    assert not a["id_actividad"].duplicated().any()
    assert rep_a["actividades_repetidas_removidas"] > 0
    assert a["avance"].between(0, 1).all()
    assert a["estado"].isin(m.ESTADOS).all()
    assert ((a["estado"] == "completada") == (a["avance"] >= 1)).all()
    assert a.groupby("id_paquete")["peso_en_paquete"].sum().to_numpy() == pytest.approx(1, abs=1e-4)
    assert a.groupby("id_proyecto")["peso_en_proyecto"].sum().to_numpy() == pytest.approx(1, abs=1e-4)
    assert (a["fecha_inicio_plan"] <= a["fecha_fin_plan"]).all()
    assert set(c["id_paquete"]) == set(_paquetes()["id_paquete"])


def test_el_cronograma_de_plata_toma_avance_y_fechas_de_las_actividades(sintetico):
    a, c, _, _ = _limpias(sintetico)
    c = c.set_index("id_paquete")
    esperado = (a["peso_en_paquete"] * a["avance"]).groupby(a["id_paquete"]).sum()
    assert c["avance"].reindex(esperado.index).to_numpy() == pytest.approx(esperado.to_numpy(), abs=1e-3)
    assert (c["fecha_fin_proyectada"] >= c["fecha_inicio_proyectada"]).all()
    assert (c.loc[c["ruta_critica"], "holgura_dias"] == 0).all()
    assert (c["meses_restantes"] > 0).all()


def test_oro_une_los_tres_niveles_y_el_avance_del_proyecto_es_la_suma_de_aportes(sintetico):
    a, c, _, _ = _limpias(sintetico)
    paq = _paquetes()
    proyectos = pd.DataFrame({"id_proyecto": ["PRY-01", "PRY-02", "PRY-03"], "nombre": ["Proyecto 1", "Proyecto 2", "Proyecto 3"]})
    t = oro.construir(a, c, paq, proyectos)
    assert len(t["actividades"]) == len(a) and len(t["paquetes"]) == len(c) and len(t["proyectos"]) == 3
    proy = t["proyectos"].set_index("id_proyecto")
    aporte = t["actividades"].groupby("id_proyecto")["aporte_avance_pp"].sum() / 100
    assert proy["avance"].reindex(aporte.index).to_numpy() == pytest.approx(aporte.to_numpy(), abs=2e-3)
    assert t["paquetes"].groupby("id_proyecto")["peso_en_proyecto"].sum().to_numpy() == pytest.approx(1, abs=1e-3)
    assert (t["paquetes"]["atraso_sobre_holgura_dias"] >= 0).all()
    # el paquete que define el fin del proyecto es el que mas tarde termina segun las fechas proyectadas
    fin_max = t["paquetes"].loc[t["paquetes"].groupby("id_proyecto")["fecha_fin_proyectada"].idxmax(), ["id_proyecto", "id_paquete"]].set_index("id_proyecto")["id_paquete"]
    assert proy["paquete_que_define_el_fin"].to_dict() == fin_max.to_dict()
