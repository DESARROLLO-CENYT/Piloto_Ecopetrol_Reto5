import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oro import indicadores as oi  # noqa: E402
from plata import emergencias as pe  # noqa: E402
from plata import resguardos as pr  # noqa: E402
from plata import runap as pa  # noqa: E402
from plata import seguridad as ps  # noqa: E402
from plata import social as so  # noqa: E402

CODIGOS = {"44001", "44847"}


def _municipios():
    return gpd.GeoDataFrame({"codigo": ["44001", "44847"], "nombre": ["Riohacha", "Uribia"]},
                            geometry=[box(-73.0, 11.0, -72.5, 11.6), box(-72.5, 11.0, -71.5, 12.4)], crs=4326)


# ---- censo 2018 -------------------------------------------------------------------------------------------------

def test_el_censo_une_los_servicios_con_nombres_estables_y_descarta_porcentajes_imposibles():
    tablas = {
        "poblacion": pd.DataFrame({"MPIO_CCDGO": ["44001", "44847", "20001"], "CL0_TT_PERSN": [200000, 150000, 9]}),
        "etnia": pd.DataFrame({"U_MPIO": ["44001", "44847"], "TOTAL_UNIDADES_PA1_GRP_ETNIC_1": [60000, 145000],
                               "PARTICIPACION_PORCENTUAL_PA1_GRP_ETNIC_1": [30.0, 96.7], "TOTAL_UNIDADES_PA1_GRP_ETNIC_5": [20000, 100],
                               "PARTICIPACION_PORCENTUAL_PA1_GRP_ETNIC_5": [10.0, 0.07]}),
        "ipm": pd.DataFrame({"MPIO_CCDGO": ["44001", "44847"], "IPM": [45.1, 140.0]}),
    }
    t, rep = so.unir_censo(tablas, CODIGOS)
    t = t.set_index("codigo")
    assert t.loc["44001", "poblacion_2018"] == 200000 and t.loc["44847", "pct_indigena"] == 96.7
    assert np.isnan(t.loc["44847", "ipm"]) and rep["porcentajes_fuera_de_rango"] == 1      # un IPM de 140 % no existe
    assert rep["codigos_desconocidos"] == 1                                                 # el municipio del Cesar sale
    assert rep["indicadores_sin_tabla"] == len(so.CAMPOS) - 3
    assert rep["diferencia_maxima_indigenas_vs_pct"] <= 50


def test_el_departamento_suma_conteos_y_pondera_porcentajes_por_poblacion():
    m = pd.DataFrame({"codigo": ["a", "b"], "poblacion_2018": [100.0, 300.0], "indigenas": [10.0, 270.0], "afro": [0.0, 0.0],
                      "pct_indigena": [10.0, 90.0], "pct_afro": [0.0, 0.0], "ipm": [20.0, 60.0]})
    d = so.fila_departamento(m)
    assert d["poblacion_2018"] == 400 and d["ipm"] == pytest.approx(50.0)      # (20*100 + 60*300) / 400
    assert d["pct_indigena"] == pytest.approx(70.0)


def test_irca_reconoce_el_departamento_y_los_nombres_sin_tildes():
    irca = pd.DataFrame({"municipio": ["#TODOS", "Uribía", "Riohacha"], "municipiocodigo": ["#TODOS", "", "44001"],
                         "a_o": ["2024", "2024", "2024"], "irca": ["10.9", "3.2", "10.1"], "nivel_de_riesgo": ["Bajo", "Sin riesgo", "Bajo"]})
    t, rep = so.limpiar_irca(irca, {"RIOHACHA": "44001", "URIBIA": "44847"})
    assert set(t["codigo"]) == {"44", "44001", "44847"} and rep["irca_municipio_desconocido"] == 0


# ---- seguridad --------------------------------------------------------------------------------------------------

def test_seguridad_agrega_por_mes_y_descarta_lo_ajeno_o_futuro():
    hom = pd.DataFrame({"fecha_hecho": ["2025-01-05", "2025-01-20", "2025-02-01", "2099-01-01", "2025-03-01"],
                        "cod_muni": ["44001", "44001", "44847", "44001", "20001"], "cantidad": ["1", "2", "1", "1", "1"]})
    mas = pd.DataFrame({"fecha_hecho": ["2025-01-10"], "cod_muni": ["44847"], "casos": ["1"], "victimas": ["4"]})
    t, rep = ps.limpiar({"homicidio": hom, "masacres": mas}, CODIGOS, hoy=pd.Timestamp("2026-01-01"))
    assert rep["fecha_invalida"] == 1 and rep["municipio_desconocido"] == 1 and rep["registros_plata"] == 4
    ene = t[(t["codigo"] == "44001") & (t["mes"] == "2025-01-01")].iloc[0]
    assert ene["casos"] == 2 and ene["victimas"] == 3
    m = t[t["delito"] == "masacres"].iloc[0]
    assert m["casos"] == 1 and m["victimas"] == 4                          # las masacres traen casos y victimas por separado


def test_oro_alinea_la_serie_mensual_y_calcula_la_tasa_de_12_meses():
    seg = pd.DataFrame({"codigo": ["44001"] * 3, "mes": pd.to_datetime(["2016-01-01", "2026-07-01", "2026-08-01"]),
                        "delito": ["homicidio"] * 3, "casos": [1, 1, 1], "victimas": [2, 3, 5]})
    meses, out = oi.seguridad(seg, {"44001": 200000, "44": 800000})
    assert meses[0] == "2016-01" and meses[-1] == "2026-08"
    s = out["44001"]["serie"]["homicidio"]
    assert len(s) == len(meses) and s[0] == 2 and s[-1] == 5 and sum(s) == 10
    r = out["44001"]["resumen"]["homicidio"]
    assert r["ultimos_12m"] == 8 and r["tasa_12m"] == 4.0                   # 8 / 200.000 * 100.000
    assert out["44"]["serie"]["homicidio"] == s                             # el departamento suma sus municipios


# ---- emergencias ------------------------------------------------------------------------------------------------

def test_emergencias_quitan_filas_repetidas_y_corrigen_el_codigo_por_el_nombre():
    fila = {"fecha": "2025-10-21", "departamento": "LA GUAJIRA", "municipio": "RIOHACHA", "evento": "INUNDACION",
            "codificaci_n_segun_divipola": "20049", "muertos": "0", "personas": "608", "viv_destru": "0", "viv_aver": "3"}
    dep = {**fila, "municipio": "DEPARTAMENTO", "evento": "SEQUIA", "codificaci_n_segun_divipola": "44", "personas": "5000"}
    otro = {**fila, "municipio": "VALLEDUPAR", "evento": "VENDAVAL", "codificaci_n_segun_divipola": "20001"}
    crudo = pd.DataFrame([fila, fila, dep, otro])                         # Riohacha llega dos veces y con codigo del Cesar
    t, rep = pe.limpiar({"2025": crudo}, _municipios())
    assert rep["duplicados_removidos"] == 1 and rep["codigo_corregido_por_nombre"] == 1
    assert rep["emergencias_departamentales"] == 1 and rep["municipio_desconocido"] == 1
    assert sorted(t["codigo"]) == ["44", "44001"]
    assert t.set_index("codigo").loc["44001", "personas"] == 608 and t.set_index("codigo").loc["44001", "tipo"] == "Inundación o creciente"


@pytest.mark.parametrize("evento,tipo", [("INCENDIO DE COBERTURA VEGETAL", "Incendio forestal"), ("DESABASTECIMIENTO DE AGUA", "Sequía o desabastecimiento de agua"),
                                         ("TORMENTA ELECTRICA", "Vendaval o tormenta"), ("EROSIÓN COSTERA", "Erosión costera"), ("COVID-19", "Otro")])
def test_tipo_de_emergencia(evento, tipo):
    assert pe.tipo_evento(evento) == tipo


# ---- resguardos y areas protegidas ------------------------------------------------------------------------------

@pytest.mark.parametrize("crudo,esperado", [("WAYUU", "Wayuu"), ("WAYUÚ", "Wayuu"), ("WAYÚU", "Wayuu"), ("Wayuu", "Wayuu"),
                                            ("KOGUI MALAYO ARHUACO", "Kogui, Malayo y Arhuaco"), (None, None)])
def test_pueblo_normalizado(crudo, esperado):
    assert pr.pueblo(crudo) == esperado


def test_resguardos_se_recortan_al_departamento_y_suman_su_poblacion():
    bruto = gpd.GeoDataFrame({
        "ID": ["1", "2", "3"], "CODIGO_DANE": ["1324", "SIN ASIGNAR", "1190"], "NOMBRE": ["Alta Guajira", "Nuevo", "Sierra"],
        "PUEBLO": ["WAYUU", "WAYÚU", "KOGUI MALAYO ARHUACO"], "ULTIMO_TIPO_ACTO_ADMIN": ["RESOLUCION"] * 3,
        "ULTIMO_NUMERO_ACTO_ADMIN": ["28", "1", "2"], "ULTIMA_FECHA_ACTO_ADMIN": [757382400000, None, None]},
        geometry=[box(-72.4, 11.5, -71.6, 12.3), box(-72.9, 11.1, -72.8, 11.2), box(-74.0, 10.0, -73.2, 10.6)], crs=4326)
    pob = pd.DataFrame({"c_digo_del_resguardo_dane": ["1324", "1324"], "total_poblaci_n_proyecci": ["100", "50"]})
    g, rep = pr.limpiar(bruto, pob, _municipios())
    assert rep["fuera_de_la_guajira"] == 1 and len(g) == 2                  # el de la Sierra (fuera de la caja de prueba) sale
    alta = g.set_index("codigo_resguardo").loc["1324"]
    assert alta["poblacion_2020"] == 150 and alta["pueblo"] == "Wayuu" and alta["municipios"] == "44847"
    assert g["codigo_resguardo"].isna().sum() == 1                            # "SIN ASIGNAR" -> nulo


@pytest.mark.parametrize("categoria,organizacion,ambito", [
    ("Parque Nacional Natural", "Parques Nacionales Naturales de Colombia", "nacional"),
    ("Distritos Regionales de Manejo Integrado", "Corporación Autónoma Regional de la Guajira", "regional"),
    ("Reserva Natural de la Sociedad Civil", "Parques Nacionales Naturales de Colombia", "privada")])
def test_ambito_del_area_protegida(categoria, organizacion, ambito):
    assert pa.ambito(categoria, organizacion) == ambito
