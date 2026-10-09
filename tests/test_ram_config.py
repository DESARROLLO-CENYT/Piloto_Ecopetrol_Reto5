import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "app"))

import ram_config  # noqa: E402
from comun import config  # noqa: E402


def _cuerpo():
    oficial = config.cargar_parametros(oficial=True)
    r = oficial["ram"]
    return {"matriz": {str(k): list(v) for k, v in r["matriz"].items()}, "probabilidades": dict(r["probabilidades"]),
            "consecuencias": {d: {str(k): v for k, v in t.items()} for d, t in r["consecuencias"].items()},
            "niveles": {n: dict(v) for n, v in r["niveles"].items()},
            "escalamiento": {"ram_vh_escala": True, "ram_h_en_ruta_critica": False}, "editado_por": " Ana ", "nota": "prueba"}


def test_la_oficial_editada_sin_cambios_no_tiene_advertencias():
    contenido, adv = ram_config.validar(_cuerpo())
    assert adv == []
    assert contenido["ram"]["matriz"][5] == ["M", "M", "H", "H", "VH"]
    assert contenido["escalamiento"] == {"ram_vh_escala": True, "ram_h_en_ruta_critica": False}
    assert contenido["version"]["editado_por"] == "Ana"


def test_avisa_si_el_nivel_baja_cuando_sube_la_probabilidad_o_la_consecuencia():
    c = _cuerpo()
    c["matriz"]["5"] = ["H", "M", "H", "H", "VH"]          # baja de A a B
    _, adv = ram_config.validar(c)
    assert any("baja de A (H) a B (M)" in a for a in adv)
    c = _cuerpo()
    c["matriz"]["4"][4] = "VH"                              # 4E = VH pero 5E = VH: bien; ahora 5E = H baja
    c["matriz"]["5"][4] = "H"
    _, adv = ram_config.validar(c)
    assert any("Probabilidad E: el nivel baja de 4 (VH) a 5 (H)" in a for a in adv)
    c = _cuerpo()
    c["niveles"]["H"]["puntaje"] = 2                        # igual que L
    _, adv = ram_config.validar(c)
    assert any("puntajes" in a for a in adv)


@pytest.mark.parametrize("cambio,mensaje", [
    (lambda c: c["matriz"].__setitem__("3", ["N", "L", "X", "M", "H"]), "niveles desconocidos"),
    (lambda c: c["matriz"].pop("0"), "6 filas"),
    (lambda c: c["probabilidades"].__setitem__("C", "  "), "Probabilidad C"),
    (lambda c: c["niveles"]["M"].__setitem__("puntaje", "tres"), "puntaje debe ser un número"),
    (lambda c: c["consecuencias"]["PE"].__setitem__("5", "x" * 400), "máximo"),
])
def test_rechaza_lo_que_romperia_el_modelo(cambio, mensaje):
    c = _cuerpo()
    cambio(c)
    with pytest.raises(ram_config.ErrorRam, match=mensaje):
        ram_config.validar(c)


def test_guardar_superpone_la_personalizada_y_borrar_devuelve_la_oficial(tmp_path, monkeypatch):
    destino = tmp_path / "ram_personalizada.yaml"
    monkeypatch.setattr(config, "RAM_PERSONALIZADA_PATH", destino)
    monkeypatch.setattr(ram_config, "RAM_PERSONALIZADA_PATH", destino)
    c = _cuerpo()
    c["matriz"]["5"] = ["H", "H", "VH", "VH", "VH"]
    contenido, _ = ram_config.validar(c)
    ram_config.guardar(contenido)
    p = config.cargar_parametros()
    assert p["ram"]["matriz"][5] == ["H", "H", "VH", "VH", "VH"] and p["ram"]["version"]["tipo"] == "personalizada"
    assert p["ram"]["fuente"] and p["ram"]["sugerencias"]                     # lo no editable sigue viniendo de la oficial
    assert p["escalamiento"]["ram_h_en_ruta_critica"] is False and p["escalamiento"]["ict_critico"] == 75
    assert config.cargar_parametros(oficial=True)["ram"]["matriz"][5] == ["M", "M", "H", "H", "VH"]
    assert ram_config.borrar() is True and not destino.exists()
    assert config.cargar_parametros()["ram"]["version"]["tipo"] == "oficial"
