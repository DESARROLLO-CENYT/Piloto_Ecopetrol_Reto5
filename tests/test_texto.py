"""IA sobre el texto del registro: clasificador explicable, validacion cruzada, lugares y su uso en Plata."""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from modelo import texto  # noqa: E402
from plata import sinteticos as plata  # noqa: E402

CORPUS = [
    ("Bloqueo de la vía por la comunidad que exige empleo local", "social_comunidad"),
    ("Protesta de la comunidad por compromisos sociales incumplidos", "social_comunidad"),
    ("La comunidad no permite el ingreso sin acuerdo de consulta previa", "social_comunidad"),
    ("Inundación del frente de obra por crecientes de arroyos", "climatico"),
    ("Lluvias intensas que suspenden las excavaciones", "climatico"),
    ("Creciente del arroyo que inunda el campamento", "climatico"),
    ("Retraso del proveedor en la entrega de transformadores", "contractual"),
    ("Incumplimiento del contratista en la ingeniería de detalle", "contractual"),
    ("Reclamación del contratista por mayores cantidades de obra", "contractual"),
]


def test_normaliza_tildes_y_quita_palabras_vacias():
    assert texto.normalizar("Inundación del CAMPAMENTO!") == "inundacion del campamento "
    r = texto.rasgos("Bloqueo de la vía por la comunidad")
    assert "bloqueo" in r and "comunidad" in r and "de" not in r and "bloqueo via" in r


def test_el_clasificador_aprende_y_explica():
    m = texto.ClasificadorTexto().entrenar([t for t, _ in CORPUS], [c for _, c in CORPUS])
    clase, conf = m.predecir("La comunidad bloquea la vía y exige empleo")
    assert clase == "social_comunidad" and conf > 0.5
    p = m.probabilidades("Lluvias e inundación del frente")
    assert max(p, key=p.get) == "climatico" and sum(p.values()) == pytest.approx(1, abs=1e-3)
    assert "comunidad" in m.explicar("La comunidad bloquea la vía", "social_comunidad")


def test_validacion_cruzada_evalua_cada_registro_una_vez():
    textos, etiquetas = [t for t, _ in CORPUS] * 2, [c for _, c in CORPUS] * 2
    r = texto.validacion_cruzada(textos, etiquetas, k=3)
    assert r["evaluados"] == len(textos) and 0 <= r["exactitud"] <= 1
    assert set(r["por_categoria"]) == {"social_comunidad", "climatico", "contractual"}


def test_lugares_mencionados_respeta_palabras_completas():
    nombres = {"44847": "Uribia", "44650": "San Juan del Cesar", "44430": "Maicao"}
    assert texto.lugares_mencionados("Paro en San Juan del César y en Maicao", nombres) == ["44650", "44430"]
    assert texto.lugares_mencionados("Personal uribiano contratado", nombres) == []


def test_en_plata_la_ia_asigna_lo_que_falta_y_marca_lo_que_contradice_el_texto():
    filas = [(t, c) for t, c in CORPUS] * 3
    df = pd.DataFrame({"id_riesgo": [f"R{i}" for i in range(len(filas))], "descripcion": [t for t, _ in filas],
                       "causa": ["" for _ in filas], "categoria": [c for _, c in filas], "id_paquete_trabajo": "P1"})
    df.loc[0, "categoria"] = "sin_clasificar"                       # texto social sin categoria
    df.loc[3, "categoria"] = "contractual"                          # texto climatico registrado como contractual
    paquetes = gpd.GeoDataFrame({"id_paquete": ["P1"]}, geometry=[box(-72.9, 11.3, -72.8, 11.4)], crs="EPSG:4326")
    out, rep = plata.clasificar_con_ia(df, paquetes, None, None, {"confianza_para_asignar": 0.5, "confianza_para_revisar": 0.6})
    assert out.loc[0, "categoria"] == "social_comunidad" and out.loc[0, "categoria_origen"] == "ia"
    assert out.loc[0, "categoria_registrada"] == "sin_clasificar"
    assert bool(out.loc[3, "revisar_categoria"]) and out.loc[3, "categoria_ia"] == "climatico"
    assert out.loc[3, "categoria"] == "contractual"                 # no se cambia sin revision humana
    assert rep["ia_categorias_asignadas"] == 1 and rep["ia_categoria_por_revisar"] >= 1


def test_el_resumen_de_la_ia_mide_detecciones_y_falsas_alarmas_contra_la_clave():
    # R1 llego sin categoria y la IA acierta; R2 y R3 traen la categoria equivocada (la IA detecta solo R2);
    # R4 esta bien pero la IA la marca: falsa alarma. R2 y R4 nombran un municipio lejano; la IA marca solo R4.
    df = pd.DataFrame({
        "id_riesgo": ["R1", "R2", "R3", "R4"],
        "categoria_registrada": ["sin_clasificar", "ambiental", "climatico", "climatico"],
        "categoria": ["social_comunidad", "ambiental", "climatico", "climatico"],
        "categoria_origen": ["ia", "registro", "registro", "registro"],
        "categoria_ia": ["social_comunidad", "climatico", "climatico", "ambiental"],
        "revisar_categoria": [False, True, False, True],
        "municipio_mencionado": [None, "Fonseca", None, "Urumita"],
        "revisar_ubicacion": [False, False, False, True],
    })
    clave = pd.DataFrame({"id_riesgo": ["R1", "R2", "R3", "R4"],
                          "categoria_real": ["social_comunidad", "climatico", "ambiental", "climatico"],
                          "ubicacion_lejana": [False, True, False, True]})
    rep = plata.resumen_ia(df, clave)
    assert rep["ia_categorias_asignadas"] == 1 and rep["ia_exactitud_sin_categoria"] == 1.0
    assert (rep["ia_categorias_mal_sembradas"], rep["ia_categorias_mal_detectadas"], rep["ia_categorias_falsas_alarmas"]) == (2, 1, 1)
    assert (rep["ia_ubicaciones_sembradas"], rep["ia_ubicaciones_detectadas"], rep["ia_ubicaciones_falsas_alarmas"]) == (2, 1, 0)
    assert rep["ia_categoria_por_revisar"] == 2 and rep["ia_ubicacion_por_revisar"] == 1
    assert "ia_categorias_mal_sembradas" not in plata.resumen_ia(df, None)   # sin clave no se inventa la evaluacion
