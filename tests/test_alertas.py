"""Alertas tempranas: novedades frente al corte anterior, boletin y envio (Teams se prueba contra un servidor local)."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consumo import alertas as boletin  # noqa: E402
import notificaciones  # noqa: E402


def _alerta(idp, prioridad, ict=60.0):
    return {"id_paquete": idp, "nombre_paquete": f"Paquete {idp}", "prioridad": prioridad, "ict": ict, "nivel": "alto",
            "municipio": "Maicao", "puntos_crisis": 2, "causas": [{"regla": "ram_vh", "texto": f"causa de {idp}"}],
            "acciones": ["Escalar a la alta dirección."], "generada_en": "2026-10-08T00:00:00"}


def test_novedades_frente_al_corte_anterior():
    ayer = [_alerta("A", "alta"), _alerta("B", "alta"), _alerta("C", "critica")]
    hoy = [_alerta("A", "alta"), _alerta("B", "critica"), _alerta("D", "media")]
    c = boletin.comparar(hoy, ayer)
    assert c == {"nuevas": ["D"], "suben": ["B"], "siguen": ["A"], "resueltas": ["C"]}
    assert boletin.comparar(hoy, None)["nuevas"] == ["A", "B", "D"]       # sin historial, todo es nuevo


def test_el_boletin_dice_que_es_nuevo_y_que_se_resolvio():
    hoy = [_alerta("A", "critica")]
    md = boletin.boletin_md("2026-10-08", hoy, {"nuevas": ["A"], "suben": [], "siguen": [], "resueltas": ["C"]},
                            {"C": {"nombre_paquete": "Paquete C"}})
    assert "NUEVA" in md and "causa de A" in md and "Paquete C" in md and "SINTÉTICO" in md
    html = boletin.boletin_html("2026-10-08", hoy, {"nuevas": [], "suben": ["A"], "siguen": [], "resueltas": []}, {})
    assert "SUBE" in html and "prioridad crítica" in html


def test_solo_se_avisa_si_hay_novedades():
    cfg = {"notificar": ["nuevas", "suben"]}
    assert not notificaciones.hay_que_avisar({"nuevas": [], "suben": [], "total": 3}, cfg)
    assert notificaciones.hay_que_avisar({"nuevas": ["A"], "suben": [], "total": 3}, cfg)
    assert notificaciones.hay_que_avisar({"nuevas": [], "suben": [], "total": 3}, {"notificar": ["todas"]})


def test_el_estado_de_los_canales_no_revela_secretos(monkeypatch):
    monkeypatch.setenv("RETO5_TEAMS_WEBHOOK", "https://secreto.example/webhook")
    estado = notificaciones.estado_canales({"canales": {"teams": True}})
    assert estado["teams"] == {"activo": True, "configurado": True}
    assert "secreto" not in json.dumps(estado)


def test_un_canal_activo_sin_variables_no_falla(tmp_path, monkeypatch):
    monkeypatch.delenv("RETO5_TEAMS_WEBHOOK", raising=False)
    (tmp_path / "novedades.json").write_text(json.dumps({"fecha": "2026-10-08", "total": 1, "nuevas": ["A"], "suben": [],
                                                         "siguen": [], "resueltas": [], "boletin_html": "b.html", "boletin_md": "b.md"}), encoding="utf-8")
    r = notificaciones.notificar(tmp_path, [_alerta("A", "alta")], {"canales": {"teams": True}})
    assert {"canal": "teams", "estado": "sin_configurar", "detalle": "falta RETO5_TEAMS_WEBHOOK"} in r


def test_teams_recibe_una_tarjeta_adaptable(tmp_path, monkeypatch):
    recibido = {}

    class Webhook(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            recibido["cuerpo"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Webhook)
    hilo = threading.Thread(target=servidor.handle_request, daemon=True)
    hilo.start()
    monkeypatch.setenv("RETO5_TEAMS_WEBHOOK", f"http://127.0.0.1:{servidor.server_port}/")
    (tmp_path / "novedades.json").write_text(json.dumps({"fecha": "2026-10-08", "total": 2, "nuevas": ["A"], "suben": [],
                                                         "siguen": ["B"], "resueltas": [], "boletin_html": "b.html", "boletin_md": "b.md"}), encoding="utf-8")
    r = notificaciones.notificar(tmp_path, [_alerta("A", "critica", 72), _alerta("B", "alta", 55)], {"canales": {"teams": True}})
    hilo.join(5)
    servidor.server_close()
    assert {"canal": "teams", "estado": "ok", "detalle": "tarjeta enviada"} in r
    tarjeta = recibido["cuerpo"]["attachments"][0]
    assert tarjeta["contentType"] == "application/vnd.microsoft.card.adaptive"
    textos = " ".join(b.get("text", "") for b in tarjeta["content"]["body"])
    assert "Alertas tempranas · 2026-10-08" in textos and "Paquete A · prioridad critica · ICT 72 · NUEVA" in textos
