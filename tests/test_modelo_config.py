"""Modelo ICT editable desde la aplicacion (validacion, version personalizada, historial) y proteccion de la edicion."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "app"))

import comun.config as config  # noqa: E402
import historial  # noqa: E402
import modelo_api  # noqa: E402


@pytest.fixture
def archivos_temporales(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELO_PERSONALIZADO_PATH", tmp_path / "modelo_personalizado.yaml")
    monkeypatch.setattr(modelo_api, "MODELO_PERSONALIZADO_PATH", tmp_path / "modelo_personalizado.yaml")
    monkeypatch.setattr(historial, "HISTORIAL_PARAMETROS_PATH", tmp_path / "historial.jsonl")
    return tmp_path


def test_los_pesos_se_reparten_para_sumar_uno_y_los_umbrales_deben_crecer():
    b, adv = modelo_api.validar({"pesos": {"severidad_riesgo": 40, "vulnerabilidad_territorial": 20, "exposicion_proyecto": 20,
                                           "amenazas_externas": 20, "convergencia": 0}})
    assert sum(b["pesos"].values()) == pytest.approx(1.0) and b["pesos"]["severidad_riesgo"] == pytest.approx(0.4)
    assert any("peso 0" in a for a in adv)
    with pytest.raises(modelo_api.ErrorModelo, match="crecer"):
        modelo_api.validar({"umbrales_criticidad": {"bajo": 30, "medio": 20, "alto": 70}})


def test_las_reglas_de_la_ram_no_se_cambian_desde_esta_vista():
    b, adv = modelo_api.validar({"escalamiento": {"ict_critico": 80, "ram_vh_escala": False}})
    assert b["escalamiento"] == {"ict_critico": 80} and any("Matriz RAM" in a for a in adv)


def test_guardar_aplica_la_version_personalizada_y_queda_en_el_historial(archivos_temporales):
    base = config.cargar_parametros(oficial=True)
    modelo_api.guardar({"umbrales_criticidad": {"bajo": 20, "medio": 45, "alto": 70}}, "Analista", "taller de expertos")
    p = config.cargar_parametros()
    assert p["umbrales_criticidad"] == {"bajo": 20, "medio": 45, "alto": 70}
    assert p["modelo_version"]["tipo"] == "personalizado" and p["modelo_version"]["editado_por"] == "Analista"
    assert p["pesos"] == base["pesos"]                                   # lo que no se toco sigue igual
    h = historial.leer("modelo")
    assert h[0]["autor"] == "Analista" and h[0]["accion"] == "guardar"
    assert modelo_api.borrar("Analista") and config.cargar_parametros()["umbrales_criticidad"] == base["umbrales_criticidad"]
    assert historial.leer("modelo")[0]["accion"] == "volver a la base"


def test_ahp_da_pesos_y_razon_de_consistencia():
    n = len(modelo_api.CRITERIOS)
    r = modelo_api.ahp([[1] * n for _ in range(n)])
    assert all(w == pytest.approx(1 / n) for w in r["pesos"].values()) and r["consistente"]


# ---- proteccion de la edicion (ASGI directo, sin servidor) ----------------------------------------------------------

def _llamar(app, metodo, ruta, cliente, cabeceras=None):
    estado = {}

    async def recibir():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(msg):
        if msg["type"] == "http.response.start":
            estado["codigo"] = msg["status"]

    scope = {"type": "http", "http_version": "1.1", "method": metodo, "path": ruta, "raw_path": ruta.encode(),
             "query_string": b"", "headers": [(k.lower().encode(), v.encode()) for k, v in (cabeceras or {}).items()],
             "client": (cliente, 5000), "server": ("127.0.0.1", 8000), "scheme": "http", "root_path": ""}
    asyncio.run(app(scope, recibir, enviar))
    return estado["codigo"]


def test_desde_otro_equipo_no_se_edita_sin_la_clave(monkeypatch):
    import main
    monkeypatch.delenv("RETO5_CLAVE_EDICION", raising=False)
    assert _llamar(main.app, "PUT", "/api/ram", "10.0.0.7") == 403
    monkeypatch.setenv("RETO5_CLAVE_EDICION", "secreta")
    assert _llamar(main.app, "PUT", "/api/ram", "10.0.0.7") == 401
    assert _llamar(main.app, "PUT", "/api/ram", "10.0.0.7", {"X-Clave-Edicion": "otra"}) == 401
    # con la clave correcta pasa la proteccion y llega a la validacion del cuerpo (vacio: 422)
    assert _llamar(main.app, "PUT", "/api/ram", "10.0.0.7", {"X-Clave-Edicion": "secreta"}) == 422
    # desde el mismo equipo no se pide clave
    assert _llamar(main.app, "PUT", "/api/ram", "127.0.0.1") == 422
