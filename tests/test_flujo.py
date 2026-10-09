"""Vista Flujo: lo que entrega /api/flujo debe ser fiel a src/pipeline.py."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "app"))

import pipeline  # noqa: E402
import flujo_api  # noqa: E402


def test_pasos_fieles_al_pipeline_y_en_orden():
    pasos = flujo_api.pasos()
    assert [p["id"] for p in pasos] == [p.id for p in pipeline.orden_topologico()]
    posicion = {p["id"]: i for i, p in enumerate(pasos)}
    for p in pasos:
        # cada dependencia existe y corre antes: el grafo de la vista es el mismo que ejecuta el pipeline
        for d in p["depende_de"]:
            assert posicion[d] < posicion[p["id"]], (d, p["id"])
        assert p["capa"] in pipeline.CAPAS
        assert p["comando"] == f"python -m {p['id']}"


def test_dependencias_respetan_las_capas():
    capa = {p.id: p.capa for p in pipeline.PASOS}
    orden = {c: i for i, c in enumerate(pipeline.CAPAS)}
    for p in flujo_api.pasos():
        for d in p["depende_de"]:
            # nadie depende de una capa posterior a la suya
            assert orden[capa[d]] <= orden[p["capa"]], (d, p["id"])


def test_resumen_de_capas_suma_los_pasos():
    datos = flujo_api.construir_flujo()
    assert sum(datos["capas"].values()) == len(datos["pasos"]) == len(pipeline.PASOS)
    assert datos["artefactos"] == len(pipeline.ARTEFACTOS)


def test_cuenta_de_pruebas_incluye_casos_parametrizados(tmp_path, monkeypatch):
    (tmp_path / "test_a.py").write_text(
        "import pytest\n"
        "def test_uno():\n    pass\n"
        "@pytest.mark.parametrize('x', [1, 2, 3])\n"
        "def test_tres(x):\n    pass\n"
        "def ayuda():\n    pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(flujo_api, "TESTS", tmp_path)
    assert flujo_api.pruebas() == {"archivos": 1, "casos": 4}


def test_versiones_leidas_de_requirements(tmp_path, monkeypatch):
    req = tmp_path / "requirements.txt"
    req.write_text("FastAPI==0.141.1\n# comentario\npandas==3.0.6  # tablas\nsin-version\n", encoding="utf-8")
    monkeypatch.setattr(flujo_api, "REQUISITOS", req)
    assert flujo_api.versiones() == {"fastapi": "0.141.1", "pandas": "3.0.6"}
