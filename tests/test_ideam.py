import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plata import ideam as ia
from comun.ideam import mapear_sensor, normalizar_unidad, promedio_circular, rumbo


def test_promedio_circular_cruza_el_norte():
    # 350 y 10 grados apuntan casi al norte; el promedio aritmetico daria 180 (sur)
    assert promedio_circular([350, 10]) == pytest.approx(0.0, abs=0.1)
    assert promedio_circular([0, 90]) == pytest.approx(45.0, abs=0.1)


def test_promedio_circular_sin_media_cuando_se_anulan():
    assert promedio_circular([90, 270]) is None
    assert promedio_circular([]) is None


def test_rumbo_16_vientos():
    assert rumbo(0) == "N"
    assert rumbo(90) == "E"
    assert rumbo(225) == "SO"
    assert rumbo(359) == "N"
    assert rumbo(None) is None


@pytest.mark.parametrize("texto,esperado", [
    ("TEMPERATURA DEL AIRE A 2 m", "temperatura"),
    ("TEMPERATURA DEL AIRE MÁXIMA A 2 m", "temp_max"),
    ("TEMPERATURA MÍNIMA DEL AIRE A 2 m", "temp_min"),
    ("Temperatura del suelo a 30 cm", "temp_suelo"),
    ("HUMEDAD DEL SUELO A 1 m Ó MAS", "humedad_suelo"),
    ("Humedad relativa del aire a 2 metros horaria", "humedad"),
    ("GPRS - PRESIÓN ATMOSFÉRICA", "presion"),
    ("DIRECCIÓN DEL VIENTO", "viento_dir"),
    ("VELOCIDAD DEL VIENTO", "viento_vel"),
    ("GPRS - PRECIPITACIÓN", "precipitacion"),
    ("Nivel horario por sensor automático", "nivel_rio"),
    ("Nivel máximo horario", None),
    ("Radiación global", None),
])
def test_mapear_sensor(texto, esperado):
    assert mapear_sensor(texto) == esperado


def test_normalizar_unidad():
    assert normalizar_unidad("hPA") == "hPa"
    assert normalizar_unidad("mt") == "m"
    assert normalizar_unidad("GN") == "°"
    assert normalizar_unidad("°C") == "°C"


def _fila(cod, t, valor, sensor, unidad, variable):
    return {"codigoestacion": cod, "fechaobservacion": t, "valorobservado": str(valor),
            "descripcionsensor": sensor, "unidadmedida": unidad, "variable": variable}


def test_limpiar_variables_clasifica_por_sensor_y_quita_basura():
    c = "15065040"  # sin ceros a la izquierda: debe quedar de 10 digitos
    bruto = pd.DataFrame([
        _fila(c, "2026-09-01T00:00:00", 30, "TEMPERATURA DEL AIRE A 2 m", "°C", "temperatura"),
        _fila(c, "2026-09-01T00:00:00", 30, "TEMPERATURA DEL AIRE A 2 m", "°C", "temperatura"),   # duplicado
        _fila(c, "2026-09-01T01:00:00", 32, "TEMPERATURA DEL AIRE A 2 m", "°C", "temperatura"),
        _fila(c, "2026-09-01T02:00:00", -999, "TEMPERATURA DEL AIRE A 2 m", "°C", "temperatura"),  # centinela
        _fila(c, "2026-09-01T00:00:00", 80, "HUMEDAD DEL SUELO A 1 m Ó MAS", "%", "humedad"),      # es suelo, no aire
        _fila(c, "2026-09-01T00:00:00", 350, "DIRECCIÓN DEL VIENTO", "GN", "viento_dir"),
        _fila(c, "2026-09-01T00:10:00", 10, "DIRECCIÓN DEL VIENTO", "GN", "viento_dir"),
        _fila(c, "2026-09-01T00:00:00", 5, "Nivel máximo horario", "cm", "nivel_rio"),             # sensor que no usamos
    ])
    lec, diaria, rep = ia.limpiar_variables(bruto)

    assert rep["var_duplicados_removidos"] == 1
    assert rep["var_fuera_de_rango"] == 1
    assert rep["var_reasignadas_por_sensor"] == 1
    assert rep["var_sensor_descartado"] == 1
    assert (lec["codigoestacion"] == "0015065040").all()

    d = diaria.set_index("var")
    assert d.loc["temperatura", "media"] == 31.0            # (30 + 32) / 2, sin el duplicado ni el -999
    assert d.loc["temperatura", "maximo"] == 32.0
    assert "humedad" not in d.index and "humedad_suelo" in d.index   # reclasificada
    assert d.loc["viento_dir", "media"] == pytest.approx(0.0, abs=0.1)  # 350 y 10 -> norte
    assert pd.isna(d.loc["viento_dir", "minimo"])           # minimo/maximo de una direccion no significan nada
    assert d.loc["viento_dir", "unidad"] == "°"
    assert "nivel_rio" not in d.index


def test_limpiar_lecturas_lluvia_dedup_por_maximo_y_descarta_imposibles():
    bruto = pd.DataFrame({
        "codigoestacion": ["15065040"] * 4,
        "fechaobservacion": ["2026-09-01T00:00:00", "2026-09-01T00:00:00", "2026-09-01T00:10:00", "2026-09-01T00:20:00"],
        "valorobservado": ["0.4", "0.4", "0.2", "999"],
    })
    _, diaria, rep = ia.limpiar_lecturas(bruto)
    assert rep["duplicados_removidos"] == 1
    assert rep["lecturas_imposibles"] == 1
    assert diaria.loc[0, "mm"] == pytest.approx(0.6)    # 0.4 + 0.2, sin doble conteo ni el 999


def test_limpiar_radiacion_empareja_por_nombre_y_municipio():
    est = pd.DataFrame({"codigo": ["0015065501", "0015085050"], "nombre": ["La Mina Cerrejon", "Toromana"], "municipio": ["Albania", "Uribia"]})
    rad = pd.DataFrame({
        "estacion": ["La Mina", "Toromaná", "Otra"], "municipio": ["Albania", "Uribía", "Maicao"],
        "tipo_de_estacion": ["Automática"] * 3, "latitud": ["11.0"] * 3, "longitud": ["-72.0"] * 3, "altitud": ["100"] * 3,
        "promedio_anual": ["5000", "5300", "5100"], **{m: ["5000"] * 3 for m in ia.MESES},
    })
    out = ia.limpiar_radiacion(rad, est)
    codigos = out.set_index("estacion")["codigo"]
    assert codigos["La Mina"] == "0015065501" and codigos["Toromaná"] == "0015085050"
    assert pd.isna(codigos["Otra"])
    assert (out["unidad"] == "Wh/m²/día").all()


def test_nivel_del_rio_se_lleva_a_metros():
    c = "15067200"
    bruto = pd.DataFrame([
        _fila(c, "2026-09-01T10:00:00", 1.06, "Nivel horario por sensor automático", "cm", "nivel_rio"),   # rotulado cm, ya en m
        _fila("15037010", "2026-09-01T06:00:00", 132, "Nivel del rio a las 600 y 1800 po limnímetro", "cm", "nivel_rio"),  # cm de verdad
    ])
    lec, _, rep = ia.limpiar_variables(bruto)
    v = lec.set_index("codigoestacion")["valor"]
    assert v["0015067200"] == pytest.approx(1.06)
    assert v["0015037010"] == pytest.approx(1.32)
    assert (lec["unidad"] == "m").all()
    assert rep["var_fuera_de_rango"] == 0


def test_limpiar_estaciones_deja_una_por_codigo_y_cuenta_las_contradicciones():
    base = {"nombre": "LA PAULINA - AUT [15065040]", "categoria": "Climatológica", "tecnologia": "Automática",
            "departamento": "La Guajira", "municipio": "Fonseca", "latitud": "10.9", "longitud": "-72.8", "altitud": "170"}
    est = pd.DataFrame([
        {**base, "codigo": "15065040", "estado": "Activa"},
        {**base, "codigo": "15065040", "estado": "Activa"},                          # copia identica
        {**base, "codigo": "15065040", "estado": "Suspendida"},                      # copia que se contradice
        {**base, "codigo": "15065041", "estado": "Activa", "nombre": "OTRA [15065041]"},
        {**base, "codigo": "99999999", "estado": "Activa", "latitud": "4.6", "longitud": "-74.1"},   # fuera de La Guajira
    ])
    gdf, rep = ia.limpiar_estaciones(est)
    assert sorted(gdf["codigo"]) == ["0015065040", "0015065041"]
    assert rep["estaciones_bronce"] == 5 and rep["estaciones_fuera_de_la_caja"] == 1
    assert rep["estaciones_duplicadas_removidas"] == 2 and rep["estaciones_con_estado_contradictorio"] == 1
    assert rep["estaciones_bronce"] - rep["estaciones_fuera_de_la_caja"] - rep["estaciones_duplicadas_removidas"] == rep["estaciones_plata"]
    assert gdf.set_index("codigo").loc["0015065040", "nombre"] == "La Paulina"
