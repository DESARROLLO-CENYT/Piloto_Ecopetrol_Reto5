"""Cada riesgo pega en una actividad del cronograma: el generador lo decide de forma coherente, Plata la reconstruye de lo
que trae el registro (o la infiere), Oro la cuenta y el modelo de ejecucion usa lo que le falta a esa actividad como
horizonte."""
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from bronce import cronograma_sintetico, riesgo_actividad_sintetico as gen_act, sinteticos as s  # noqa: E402
from bronce.textos_sinteticos import ACTIVIDADES_DE, AMENAZAS, OPORTUNIDADES  # noqa: E402
from comun.config import cargar_parametros  # noqa: E402
from modelo import actividad_riesgo as m  # noqa: E402
from modelo import ejecucion as m_ej  # noqa: E402
from oro import cronograma as oro_cron  # noqa: E402
from plata import sinteticos as plata  # noqa: E402

CORTE = pd.Timestamp("2026-10-14")
T = pd.Timestamp


# --------------------------------------------------------------------------- generador (Bronce)

@pytest.fixture(scope="module")
def registro():
    hoy = date.today()
    _, paq = s.generar_proyectos_y_paquetes()
    _, act, _ = cronograma_sintetico.generar(paq, hoy, 42)
    df, clave = s.generar_registro_riesgos(paq, s.generar_comunidades(), s.generar_areas_protegidas(), actividades=act)
    return df, clave, act, paq


def test_todas_las_plantillas_dicen_que_actividades_afectan():
    todas = [p for d in (AMENAZAS, OPORTUNIDADES) for lista in d.values() for p in lista]
    claves = {k for k, *_ in cronograma_sintetico.ACTIVIDADES}
    assert all(p in ACTIVIDADES_DE for p in todas)
    assert all(set(ACTIVIDADES_DE[p]) <= claves for p in todas)


def test_la_actividad_verdadera_es_de_su_paquete_y_cuadra_con_el_momento_del_riesgo(registro):
    df, clave, act, _ = registro
    a = gen_act.actividades_limpias(act).set_index("id_actividad")
    v = clave.merge(df[["id_riesgo", "estado", "id_paquete_trabajo", "fecha_materializacion"]], on="id_riesgo")
    assert (v["actividad_real"].map(a["id_paquete"]) == v["id_paquete_trabajo"]).all()
    abierto = v["estado"].str.strip().str.lower() != "materializado"
    assert (v.loc[abierto, "actividad_real"].map(a["avance"]) < 1).all()                  # lo abierto pega en lo que falta
    mat = v[~abierto]          # lo materializado, en algo que ya empezo (que fuera durante su ejecucion: test_fechas_riesgo)
    assert (mat["actividad_real"].map(a["fecha_inicio_real"]) <= pd.Timestamp(date.today())).all()


def test_el_texto_casi_siempre_habla_de_la_actividad(registro):
    df, clave, act, _ = registro
    nombre = gen_act.actividades_limpias(act).set_index("id_actividad")["clave"]
    v = clave.merge(df[["id_riesgo", "descripcion"]], on="id_riesgo")

    def plantilla(d):
        return next((p for p in ACTIVIDADES_DE if d.startswith(p.split("{municipio}")[0])), None)

    coherente = [nombre[a] in ACTIVIDADES_DE.get(plantilla(d), ()) for a, d in zip(v["actividad_real"], v["descripcion"])]
    assert np.mean(coherente) > 0.85


def test_el_registro_escribe_la_actividad_de_varias_formas(registro):
    df, *_ = registro
    col = df["actividad_afectada"]
    codigos = col.dropna().astype(str).str.fullmatch(r"PRY-\d\d-PT\d\d-A\d\d")
    assert col.isna().sum() > 0                                       # vacias
    assert codigos.sum() > len(df) * 0.4                              # la mayoria con codigo
    assert (~codigos).sum() > len(df) * 0.1                           # y otras por nombre o disciplina
    de_otro = col.dropna().astype(str).str[:11] != df.loc[col.notna(), "id_paquete_trabajo"].astype(str)
    assert (de_otro & codigos).any()                                  # alguna con el codigo de otro paquete


# --------------------------------------------------------------------------- resolver (Plata)

def _actividades():
    """Paquete PRY-01-PT01: civil terminada, montaje en curso, pruebas por iniciar. PRY-01-PT02: una de compras."""
    return pd.DataFrame({
        "id_actividad": ["PRY-01-PT01-A01", "PRY-01-PT01-A02", "PRY-01-PT01-A03", "PRY-01-PT02-A01"],
        "id_paquete": ["PRY-01-PT01"] * 3 + ["PRY-01-PT02"], "orden": [1, 2, 3, 1],
        "nombre": ["Obras civiles y cimentaciones", "Montaje electromecánico", "Pruebas y puesta en servicio", "Adquisición de equipos y materiales"],
        "disciplina": ["Civil", "Electromecánica", "Puesta en servicio", "Compras"],
        "estado": ["completada", "en_curso", "por_iniciar", "en_curso"], "avance": [1.0, 0.4, 0.0, 0.5],
        "peso_en_paquete": [0.4, 0.4, 0.2, 1.0],
        "fecha_inicio_real": [T("2026-01-10"), T("2026-06-01"), pd.NaT, T("2026-05-01")],
        "fecha_fin_real": [T("2026-05-30"), pd.NaT, pd.NaT, pd.NaT],
        "fecha_inicio_proyectada": [T("2026-01-10"), T("2026-06-01"), T("2026-12-20"), T("2026-05-01")],
        "fecha_fin_proyectada": [T("2026-05-30"), T("2026-12-19"), T("2027-02-15"), T("2026-12-01")],
        "fecha_corte": [CORTE] * 4,
    })


def _riesgo(registrada, estado="latente", texto="Riesgo sin pistas", categoria="contractual", fm=None, paquete="PRY-01-PT01"):
    return {"id_riesgo": "R", "id_paquete_trabajo": paquete, "actividad_afectada": registrada, "estado": estado,
            "descripcion": texto, "causa": "", "categoria": categoria, "fecha_materializacion": T(fm) if fm else pd.NaT}


def _resolver(*riesgos):
    out, rep = m.resolver(pd.DataFrame(list(riesgos)), _actividades())
    return out, rep


def test_codigo_valido_y_nombre_con_otra_ortografia_se_respetan():
    out, rep = _resolver(_riesgo("PRY-01-PT01-A02"), _riesgo(" MONTAJE ELECTROMECANICO "), _riesgo("electromecánica"),
                         _riesgo("pry-01-pt01-a03 "))
    assert out["id_actividad"].tolist() == ["PRY-01-PT01-A02"] * 3 + ["PRY-01-PT01-A03"]
    assert out["actividad_origen"].tolist() == ["registro", "nombre", "nombre", "registro"]
    assert rep["riesgos_actividad_por_codigo"] == 2 and rep["riesgos_actividad_por_nombre"] == 2
    assert not out["revisar_actividad"].any()


def test_vacia_se_infiere_por_el_texto_entre_lo_que_falta():
    out, rep = _resolver(_riesgo(None, texto="Tormenta eléctrica que obliga a detener los trabajos en altura", categoria="climatico"),
                         _riesgo(None, texto="Falla en las pruebas de energización", categoria="contractual"))
    assert out["id_actividad"].tolist() == ["PRY-01-PT01-A02", "PRY-01-PT01-A03"]
    assert (out["actividad_origen"] == "inferida").all() and rep["riesgos_actividad_inferidas"] == 2


def test_lo_que_no_cuadra_se_corrige_y_se_marca_para_revisar():
    out, rep = _resolver(
        _riesgo("PRY-01-PT02-A01"),                                                    # codigo de otro paquete
        _riesgo("PRY-01-PT01-A01", texto="Lluvias que suspenden las excavaciones"),     # abierta en una actividad terminada
        _riesgo("PRY-01-PT01-A03", estado="materializado", fm="2026-03-15"),            # materializada antes de que empezara
    )
    assert (out["actividad_origen"] == "corregida").all() and out["revisar_actividad"].all()
    assert out["id_actividad"].iloc[0] in ("PRY-01-PT01-A02", "PRY-01-PT01-A03")      # lo que falta en su paquete
    assert out["id_actividad"].iloc[1] != "PRY-01-PT01-A01"
    assert out["id_actividad"].iloc[2] == "PRY-01-PT01-A01"                             # lo unico empezado ese dia
    assert rep["riesgos_actividad_codigo_de_otro_paquete"] == 1 and rep["riesgos_actividad_no_cuadra_con_el_estado"] == 2


def test_la_exactitud_se_mide_contra_la_verdad():
    riesgos = pd.DataFrame([_riesgo(None, texto="Vendaval que daña torres en montaje", categoria="climatico")])
    resueltos, _ = m.resolver(riesgos, _actividades())
    riesgos = riesgos.join(resueltos)
    rep = m.exactitud(riesgos, _actividades(), pd.Series({"R": "PRY-01-PT01-A02"}))
    assert rep == {"actividad_exactitud_inferidas": 1.0, "actividad_exactitud_a_ciegas": 1.0}


def test_plata_deja_cada_riesgo_con_una_actividad_posible(registro):
    df, clave, act, paq = registro
    acts, _ = plata.limpiar_actividades(act, gpd.GeoDataFrame(paq), pd.DataFrame({"id_paquete": paq["id_paquete"], "presupuesto_usd": 1}))
    gdf, rep = plata.limpiar_riesgos(df.copy(), gpd.GeoDataFrame(paq), clave=clave, actividades=acts)
    a = acts.set_index("id_actividad")
    assert gdf["id_actividad"].notna().all() and rep["riesgos_sin_actividad"] == 0
    assert (gdf["id_actividad"].map(a["id_paquete"]) == gdf["id_paquete_trabajo"]).all()
    abiertos = gdf[gdf["estado"] != "materializado"]
    assert (abiertos["id_actividad"].map(a["estado"]) != "completada").all()
    assert rep["actividad_exactitud_a_ciegas"] > 0.6                                 # la inferencia acierta bastante mas que el azar


# --------------------------------------------------------------------------- Oro y modelo de ejecucion

def test_oro_cuenta_los_riesgos_de_cada_actividad():
    r = pd.DataFrame({"id_actividad": ["A", "A", "A", "B"], "tipo": ["amenaza", "amenaza", "oportunidad", "amenaza"],
                      "estado": ["latente", "materializado", "latente", "proximo_a_materializarse"], "nivel_residual": ["H", "VH", "M", "L"]})
    c = oro_cron.riesgos_por_actividad(r, pd.Index(["A", "B", "C"]))
    assert c.loc["A"].tolist() == [3, 1, 1, 1] and c.loc["B"].tolist() == [1, 1, 0, 0] and c.loc["C"].sum() == 0


def test_el_horizonte_es_lo_que_le_falta_a_la_actividad():
    a = _actividades().set_index("id_actividad")
    assert m_ej.horizonte_actividad(a.loc["PRY-01-PT01-A01"], CORTE) == 0                          # ya termino
    assert m_ej.horizonte_actividad(a.loc["PRY-01-PT01-A02"], CORTE) == pytest.approx(66 / 365.25)  # en curso: del corte al fin
    assert m_ej.horizonte_actividad(a.loc["PRY-01-PT01-A03"], CORTE) == pytest.approx(57 / 365.25)  # por iniciar: toda su ventana


def test_el_modelo_de_ejecucion_usa_el_horizonte_de_la_actividad():
    cfg = cargar_parametros(oficial=True)["ejecucion"]
    paquetes = pd.DataFrame({"id_proyecto": ["Y1"], "meses_restantes": [6], "costo_dia_parada_usd": [10000], "holgura_dias": [0],
                             "codigo_municipio": ["44001"]}, index=pd.Index(["PRY-01-PT01"], name="id_paquete"))
    z = pd.DataFrame({c: [0.0] for c in ("tasa_delitos_rel", "emergencias_rel", "anomalia_lluvia", "en_resguardo", "ipm_rel", "pdet", "vias_tiempo_seco")},
                     index=pd.Index(["PRY-01-PT01"], name="id_paquete"))
    r = {"id_riesgo": "R1", "id_paquete_trabajo": "PRY-01-PT01", "id_actividad": "PRY-01-PT01-A03", "tipo": "amenaza", "estado": "latente",
         "categoria": "contractual", "probabilidad": "E", "probabilidad_residual": "D", "nivel_residual": "H", "ram_residual": "4D",
         "cons_personas": 0, "cons_economica": 4, "cons_ambiental": 0, "cons_clientes": 1, "cons_imagen": 1}
    acts = _actividades().set_index("id_actividad")
    con = m_ej.preparar_riesgos(pd.DataFrame([r]), paquetes, z, cfg, actividades=acts, corte=CORTE).iloc[0]
    sin = m_ej.preparar_riesgos(pd.DataFrame([r]), paquetes, z, cfg).iloc[0]
    assert con["horizonte_origen"] == "actividad" and con["actividad"] == "Pruebas y puesta en servicio"
    assert con["horizonte_anios"] == pytest.approx(57 / 365.25, abs=1e-3)
    assert sin["horizonte_origen"] == "paquete" and sin["horizonte_anios"] == 0.5
    assert con["atraso_esperado"] < sin["atraso_esperado"]
