"""Reglas de la arquitectura medallion: se comprueban sobre el codigo y sobre la definicion del pipeline."""
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import auditoria  # noqa: E402
import pipeline  # noqa: E402


# --------------------------------------------------------------------------- reglas de capas sobre el codigo real

def test_el_codigo_actual_respeta_las_capas():
    malos = [f for f in auditoria.reglas_de_capas(SRC) if f["estado"] != auditoria.OK]
    assert not malos, malos


@pytest.mark.parametrize("capa,codigo,debe_fallar", [
    ("oro", "from comun.config import BRONCE\nx = BRONCE / 'a'\n", True),          # Oro leyendo Bronce
    ("oro", "from plata import ideam\n", True),                                    # Oro importando una limpieza de Plata
    ("plata", "from comun.config import ORO\nx = ORO / 'a'\n", True),              # Plata leyendo Oro
    ("plata", "import urllib.request\n", True),                                    # solo Bronce toca la red
    ("plata", "from comun.http import soql\n", True),
    ("bronce", "from comun.config import PLATA\nx = PLATA\n", True),              # Bronce no depende de nada derivado
    ("bronce", "import urllib.request\nfrom comun.config import BRONCE\n", False),
    ("plata", "from comun.config import BRONCE, PLATA\nx = BRONCE, PLATA\n", False),
    ("oro", "from comun.config import ORO, PLATA\nx = ORO, PLATA\n", False),
])
def test_las_reglas_detectan_cruces_de_capa(tmp_path, capa, codigo, debe_fallar):
    (tmp_path / capa).mkdir()
    (tmp_path / capa / "modulo.py").write_text(codigo, encoding="utf-8")
    estados = {f["estado"] for f in auditoria.reglas_de_capas(tmp_path) if f["objeto"] == f"{capa}/modulo.py"}
    assert (auditoria.ERROR in estados) == debe_fallar


# --------------------------------------------------------------------------- definicion del pipeline

def test_cada_paso_vive_en_el_paquete_de_su_capa_y_se_puede_importar():
    import importlib
    for p in pipeline.PASOS:
        assert p.modulo.startswith(p.capa + "."), p.id
        assert hasattr(importlib.import_module(p.modulo), "main"), f"{p.id} no tiene main()"


def test_los_pasos_leen_y_escriben_artefactos_conocidos():
    for p in pipeline.PASOS:
        for a in (*p.lee, *p.escribe):
            assert a in pipeline.ARTEFACTOS, f"{p.id}: artefacto desconocido {a}"


def test_cada_artefacto_lo_escribe_un_solo_paso():
    escritores = {}
    for p in pipeline.PASOS:
        for a in p.escribe:
            assert a not in escritores, f"{a} lo escriben {escritores[a]} y {p.id}"
            escritores[a] = p.id


def test_un_paso_solo_lee_su_capa_o_las_anteriores():
    orden = {c: i for i, c in enumerate(pipeline.CAPAS)}
    for p in pipeline.PASOS:
        for a in p.lee:
            capa_lee = a.split(":")[0]
            if capa_lee == "oro" and p.capa == "oro":
                continue            # la validacion lee el ICT que acaba de calcular el paso oro.ict
            assert orden[capa_lee] <= orden[p.capa], f"{p.id} lee {a}"
    # y Oro y Consumo nunca leen Bronce; Plata nunca lee Oro
    for p in pipeline.PASOS:
        capas_leidas = {a.split(":")[0] for a in p.lee}
        if p.capa in ("oro", "consumo"):
            assert "bronce" not in capas_leidas, p.id
        if p.capa == "plata":
            assert "oro" not in capas_leidas, p.id


def test_el_orden_respeta_las_dependencias():
    vistos = set()
    escribe = {a: p.id for p in pipeline.PASOS for a in p.escribe}
    for p in pipeline.orden_topologico():
        for a in p.lee:
            assert escribe[a] in vistos or escribe[a] == p.id, f"{p.id} corre antes que {escribe[a]}"
        vistos.add(p.id)


def test_las_descargas_son_solo_de_bronce():
    assert {p.capa for p in pipeline.PASOS if p.requiere_red} == {"bronce"}


def test_una_fuente_arrastra_lo_que_depende_de_ella():
    ids = [p.id for p in pipeline.seleccionar(fuentes=["municipios"])]
    assert "plata.vias_igac" in ids and "oro.red_vial" in ids and "oro.municipios" in ids   # las vias se recortan con los municipios
    solo = [p.id for p in pipeline.seleccionar(fuentes=["municipios"], con_dependientes=False)]
    assert solo == ["bronce.municipios", "plata.municipios", "oro.municipios"]


def test_sin_red_no_descarga_nada():
    assert all(not p.requiere_red for p in pipeline.seleccionar(sin_red=True))
    assert any(p.id == "plata.ideam" for p in pipeline.seleccionar(sin_red=True))


def test_dependencias_circulares_se_detectan():
    a = pipeline.Paso("x.a", "plata", "a", "", lee=("plata:b",), escribe=("plata:a",))
    b = pipeline.Paso("x.b", "plata", "b", "", lee=("plata:a",), escribe=("plata:b",))
    with pytest.raises(ValueError):
        pipeline.orden_topologico([a, b])


# --------------------------------------------------------------------------- la auditoria detecta los problemas que dice detectar

def _geojson(ruta: Path, features: list, crs: str | None = None):
    import json
    ruta.parent.mkdir(exist_ok=True)
    cuerpo = {"type": "FeatureCollection", "features": features}
    if crs:
        cuerpo["crs"] = {"type": "name", "properties": {"name": crs}}
    ruta.write_text(json.dumps(cuerpo), encoding="utf-8")


PUNTO = {"type": "Feature", "properties": {"a": 1}, "geometry": {"type": "Point", "coordinates": [-72.5, 11.0]}}


def test_la_auditoria_acepta_un_archivo_sano(tmp_path):
    _geojson(tmp_path / "gold" / "ok.geojson", [PUNTO])
    r = auditoria.revisar_archivo(tmp_path / "gold" / "ok.geojson")
    assert r["estado"] == auditoria.OK and r["filas"] == 1


def test_la_auditoria_rechaza_nan_en_oro(tmp_path):
    ruta = tmp_path / "gold" / "nan.geojson"
    ruta.parent.mkdir()
    ruta.write_text('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"a":NaN},"geometry":{"type":"Point","coordinates":[-72.5,11.0]}}]}', encoding="utf-8")
    assert auditoria.revisar_archivo(ruta)["estado"] == auditoria.ERROR


def test_la_auditoria_rechaza_archivos_vacios(tmp_path):
    _geojson(tmp_path / "silver" / "vacio.geojson", [])
    assert auditoria.revisar_archivo(tmp_path / "silver" / "vacio.geojson")["estado"] == auditoria.ERROR
    import pandas as pd
    (tmp_path / "silver").mkdir(exist_ok=True)
    pd.DataFrame({"a": []}).to_parquet(tmp_path / "silver" / "vacio.parquet")
    assert auditoria.revisar_archivo(tmp_path / "silver" / "vacio.parquet")["estado"] == auditoria.ERROR


def test_la_auditoria_rechaza_crs_distinto_de_4326_y_geometrias_invalidas(tmp_path):
    _geojson(tmp_path / "silver" / "metros.geojson", [PUNTO], crs="urn:ogc:def:crs:EPSG::3116")
    assert auditoria.revisar_archivo(tmp_path / "silver" / "metros.geojson")["estado"] == auditoria.ERROR
    corbata = {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}}
    _geojson(tmp_path / "gold" / "corbata.geojson", [corbata])
    r = auditoria.revisar_archivo(tmp_path / "gold" / "corbata.geojson")
    assert r["estado"] == auditoria.ERROR and "invalidas" in r["detalle"]


def test_la_conciliacion_distingue_lo_que_cuadra_de_lo_que_no():
    assert auditoria._cuadra("x", "c", 100, 100)["estado"] == auditoria.OK
    assert auditoria._cuadra("x", "c", 100, 99)["estado"] == auditoria.ERROR
    assert auditoria._cuadra("x", "c", 100.0, 100.4, 0.5)["estado"] == auditoria.OK      # con tolerancia
    assert auditoria._cuadra("x", "c", None, 5)["estado"] == auditoria.ERROR


def test_la_auditoria_detecta_lo_inventado_que_cae_fuera_de_la_guajira(tmp_path, monkeypatch):
    import geopandas as gpd
    from shapely.geometry import Point
    silver = tmp_path / "silver"
    silver.mkdir()
    monkeypatch.setattr(auditoria, "PLATA", silver)       # sin municipios en Plata: se compara con el contorno de referencia
    gpd.GeoDataFrame({"a": [1, 2]}, geometry=[Point(-72.3, 11.4), Point(-72.7, 12.3)], crs=4326).to_file(silver / "comunidades.geojson", driver="GeoJSON")
    r = {f["objeto"]: f for f in auditoria.geografia()}
    assert r["silver/comunidades.geojson"]["estado"] == auditoria.ERROR and "1 de 2" in r["silver/comunidades.geojson"]["detalle"]   # el segundo punto esta en el mar
