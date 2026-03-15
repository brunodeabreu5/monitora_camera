import os
import sys
import sqlite3
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Garantir que o projeto esteja no path ao rodar testes (ex.: python -m unittest discover)
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import requests
from PySide6.QtWidgets import QApplication, QLineEdit

from src.core.config import (
    AppConfig,
    EVT_IDX_APPLIED_LIMIT,
    EVT_IDX_CAMERA_NAME,
    EVT_IDX_IMAGE_PATH,
    EVT_IDX_IS_OVERSPEED,
    EVT_IDX_PLATE,
    EVT_IDX_SPEED,
    EVT_IDX_SPEED_VALUE,
    EVT_IDX_TS,
    format_datetime_br,
    render_event_message,
)
from src.core.camera_client import CameraClient
from src.core.database import Database
from src.core.evolution_client import EvolutionApiClient
from src.core.parsing import find_event_xml_end, looks_like_complete_event_xml, parse_event_xml
from ui.widgets import PasswordField
from ui.workers import EventWorker
from src.app import MainWindow


class FakeResponse:
    def __init__(self, status_code=200, headers=None, content=b"", text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.text = text


def build_camera_config(**overrides):
    config = {
        "name": "Portaria",
        "enabled": True,
        "camera_ip": "192.168.0.10",
        "camera_port": 80,
        "camera_user": "admin",
        "camera_pass": "segredo",
        "channel": 101,
        "timeout": 15,
        "rtsp_enabled": True,
        "rtsp_port": 554,
        "rtsp_transport": "tcp",
        "rtsp_url": "",
        "live_fallback_mode": "snapshot",
        "speed_limit_enabled": True,
        "speed_limit_value": 60,
        "speed_alert_visual": True,
        "evolution_enabled": False,
        "output_dir": "C:/temp/output",
        "save_snapshot_on_event": True,
        "camera_mode": "auto",
    }
    config.update(overrides)
    return config


class HikvisionAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_app_config_persists_camera_password(self):
        with self._temp_config_path() as cfg_path:
            camera = build_camera_config()

            config = AppConfig(filepath=cfg_path)
            config.upsert_camera(camera)
            config.save()

            reloaded = AppConfig(filepath=cfg_path)
            saved = reloaded.get_camera("Portaria")
            self.assertIsNotNone(saved)
            self.assertEqual(saved["name"], camera["name"])
            # FASE 1.2: Passwords are now encrypted - check if it's encrypted format
            self.assertIsInstance(saved["camera_pass"], dict)
            self.assertIn("encrypted", saved["camera_pass"])
            self.assertIn("nonce", saved["camera_pass"])
            # Verify we can decrypt it back
            from src.core.crypto import decrypt_password
            decrypted_pass = decrypt_password(saved["camera_pass"])
            self.assertEqual(decrypted_pass, camera["camera_pass"])
            self.assertEqual(saved["camera_ip"], camera["camera_ip"])
            self.assertEqual(saved["camera_user"], camera["camera_user"])
            self.assertEqual(saved["speed_limit_value"], camera["speed_limit_value"])

    def test_app_config_upsert_camera_updates_existing_entry(self):
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)

            config.upsert_camera(build_camera_config())
            config.upsert_camera(build_camera_config(camera_pass="nova-senha", timeout=30))

            cameras = [cam for cam in config.data["cameras"] if cam.get("name") == "Portaria"]
            self.assertEqual(len(cameras), 1)
            self.assertEqual(cameras[0]["camera_pass"], "nova-senha")
            self.assertEqual(cameras[0]["timeout"], 30)

    def test_app_config_persists_speed_limit_settings_per_camera(self):
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)
            config.upsert_camera(build_camera_config(speed_limit_enabled=False, speed_limit_value=45, speed_alert_visual=False))
            config.save()

            reloaded = AppConfig(filepath=cfg_path)
            camera = reloaded.get_camera("Portaria")

            self.assertFalse(camera["speed_limit_enabled"])
            self.assertEqual(camera["speed_limit_value"], 45)
            self.assertFalse(camera["speed_alert_visual"])

    def test_app_config_persists_evolution_settings(self):
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)
            config.data["evolution_api"] = {
                "enabled": True,
                "base_url": "http://localhost:8080",
                "api_token": "abc123",
                "instance_name": "radar",
                "instance_mode": "create_or_connect",
                "recipient_numbers": ["5511999999999", "5511888888888"],
                "send_image_with_caption": True,
                "test_target_number": "5511777777777",
                "test_message_text": "Teste Evolution",
                "event_message_template": "Camera {camera} placa {plate}",
            }
            config.upsert_camera(build_camera_config(evolution_enabled=True))
            config.save()

            reloaded = AppConfig(filepath=cfg_path)
            self.assertTrue(reloaded.data["evolution_api"]["enabled"])
            self.assertEqual(reloaded.data["evolution_api"]["instance_name"], "radar")
            self.assertEqual(reloaded.data["evolution_api"]["recipient_numbers"], ["5511999999999", "5511888888888"])
            self.assertEqual(reloaded.data["evolution_api"]["test_target_number"], "5511777777777")
            self.assertEqual(reloaded.data["evolution_api"]["event_message_template"], "Camera {camera} placa {plate}")
            self.assertTrue(reloaded.get_camera("Portaria")["evolution_enabled"])

    def test_password_field_toggles_visibility_without_losing_text(self):
        field = PasswordField()
        field.setText("segredo")

        self.assertEqual(field.line_edit.echoMode(), QLineEdit.Password)
        self.assertEqual(field.text(), "segredo")

        field.toggle_button.click()
        self.assertEqual(field.line_edit.echoMode(), QLineEdit.Normal)
        self.assertEqual(field.text(), "segredo")

        field.toggle_button.click()
        self.assertEqual(field.line_edit.echoMode(), QLineEdit.Password)
        self.assertEqual(field.text(), "segredo")

    def test_camera_client_connection_traffic_success(self):
        client = CameraClient(build_camera_config(camera_mode="traffic"))
        with patch.object(client, "request", return_value=FakeResponse(status_code=200, text="VehicleDetectCfg")):
            ok, status, detail = client.test_connection()

        self.assertTrue(ok)
        self.assertEqual(status, 200)
        self.assertIn("traffic via", detail)

    def test_camera_client_connection_snapshot_auth_failure(self):
        client = CameraClient(build_camera_config(camera_mode="normal"))
        with patch.object(client, "request", return_value=FakeResponse(status_code=401, headers={}, content=b"")):
            ok, status, detail = client.test_connection()

        self.assertFalse(ok)
        self.assertEqual(status, 401)
        self.assertIn("autenticacao falhou", detail)

    def test_camera_client_connection_timeout_reports_connection_error(self):
        client = CameraClient(build_camera_config(camera_mode="traffic"))
        with patch.object(client, "request", side_effect=requests.Timeout("tempo esgotado")):
            ok, status, detail = client.test_connection()

        self.assertFalse(ok)
        self.assertEqual(status, 0)
        self.assertIn("erro de conexao", detail)

    def test_camera_client_builds_default_rtsp_url(self):
        client = CameraClient(build_camera_config(camera_user="operador", camera_pass="s@nh a"))
        self.assertEqual(
            client.build_rtsp_url(),
            "rtsp://operador:s%40nh%20a@192.168.0.10:554/Streaming/Channels/101?rtsp_transport=tcp",
        )

    def test_camera_client_uses_custom_rtsp_url_when_provided(self):
        client = CameraClient(build_camera_config(rtsp_url="rtsp://custom/live"))
        self.assertEqual(client.build_rtsp_url(), "rtsp://custom/live")

    def test_camera_client_rtsp_url_udp_has_no_transport_param(self):
        client = CameraClient(build_camera_config(rtsp_transport="udp"))
        url = client.build_rtsp_url()
        self.assertNotIn("rtsp_transport", url)
        self.assertTrue(url.startswith("rtsp://"))

    def test_camera_client_download_snapshot_skips_empty_response_tries_next_url(self):
        """Se a primeira URL retornar 200 com corpo vazio, tenta a proxima e retorna imagem."""
        client = CameraClient(build_camera_config())
        jpeg_bytes = b"\xff\xd8\xff" + b"x" * 100

        def mock_request(url, **kwargs):
            if not hasattr(mock_request, "call_count"):
                mock_request.call_count = 0
            mock_request.call_count += 1
            if mock_request.call_count <= 2:
                return FakeResponse(status_code=200, content=b"", headers={"Content-Type": "image/jpeg"})
            return FakeResponse(status_code=200, content=jpeg_bytes, headers={"Content-Type": "image/jpeg"})

        with patch.object(client, "request", side_effect=mock_request):
            data, used_url = client.download_snapshot()
        self.assertEqual(data, jpeg_bytes)
        self.assertTrue(used_url is not None and ("picture" in used_url or "snapshot" in used_url))

    def test_camera_client_download_snapshot_raises_when_all_return_empty_or_non_image(self):
        client = CameraClient(build_camera_config())
        with patch.object(client, "request", return_value=FakeResponse(status_code=200, content=b"", headers={"Content-Type": "image/jpeg"})):
            with self.assertRaises(RuntimeError) as ctx:
                client.download_snapshot()
        self.assertIn("resposta vazia", str(ctx.exception))

    def test_evolution_client_send_media_message_uses_base64_payload(self):
        with self._temp_image_path() as image_path:
            image_path.write_bytes(b"fake-image")
            client = EvolutionApiClient({
                "base_url": "http://localhost:8080",
                "api_token": "token",
                "instance_name": "radar",
            })
            with patch.object(client, "request_json", return_value={"ok": True}) as request_json:
                client.send_media_message("55 11 99999-9999", "Legenda", str(image_path))

            _, path = request_json.call_args.args[:2]
            payload = request_json.call_args.kwargs["payload"]
            self.assertEqual(path, "/message/sendMedia/radar")
            self.assertEqual(payload["number"], "5511999999999")
            self.assertEqual(payload["caption"], "Legenda")
            self.assertTrue(payload["media"])

    def test_evolution_client_send_text_message_normalizes_number(self):
        client = EvolutionApiClient({
            "base_url": "http://localhost:8080",
            "api_token": "token",
            "instance_name": "radar",
        })
        with patch.object(client, "request_json", return_value={"ok": True}) as request_json:
            client.send_text_message("(11) 98888-7777", "Teste")

        payload = request_json.call_args.kwargs["payload"]
        self.assertEqual(payload["number"], "11988887777")
        self.assertEqual(payload["text"], "Teste")

    def test_render_event_message_replaces_template_variables(self):
        text = render_event_message(
            "Camera {camera} placa {plate} velocidade {speed} limite {limit}",
            {
                "camera_name": "Portaria",
                "plate": "ABC1234",
                "speed": "70",
                "applied_speed_limit": 60.0,
            },
        )
        self.assertEqual(text, "Camera Portaria placa ABC1234 velocidade 70 limite 60")

    def test_render_event_message_uses_defaults_for_missing_values(self):
        text = render_event_message("Placa {plate} faixa {lane}", {})
        self.assertEqual(text, "Placa - faixa -")

    def test_format_datetime_br_iso_with_timezone(self):
        self.assertEqual(format_datetime_br("2026-03-14T12:12:16.722-03:00"), "14/03/2026 12:12:16")

    def test_format_datetime_br_space_separated(self):
        self.assertEqual(format_datetime_br("2026-03-14 15:00:00"), "14/03/2026 15:00:00")

    def test_format_datetime_br_date_only(self):
        self.assertEqual(format_datetime_br("2026-03-14"), "14/03/2026 00:00:00")

    def test_format_datetime_br_empty_returns_empty(self):
        self.assertEqual(format_datetime_br(""), "")
        self.assertEqual(format_datetime_br(None), "")

    def test_format_datetime_br_invalid_returns_original(self):
        self.assertEqual(format_datetime_br("not-a-date"), "not-a-date")

    def test_parse_event_xml_reads_vehicle_plate(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert>
  <vehiclePlate>ABC1D23</vehiclePlate>
  <vehicleSpeed>72</vehicleSpeed>
  <laneNo>2</laneNo>
  <dateTime>2026-03-13 10:00:00</dateTime>
</EventNotificationAlert>"""
        parsed = parse_event_xml(xml_text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["plate"], "ABC1D23")
        self.assertEqual(parsed["speed"], "72")

    def test_parse_event_xml_returns_none_for_truncated_xml(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert>
  <vehiclePlate>ABC1D23</vehiclePlate>
"""
        self.assertIsNone(parse_event_xml(xml_text))

    def test_parse_event_xml_ignores_unknown_tags_returns_known_fields(self):
        """XML com tags desconhecidas ainda retorna placa, speed etc. quando presentes."""
        xml_text = """<?xml version="1.0"?>
<EventNotificationAlert xmlns="http://www.isapi.org/ver20/XMLSchema">
  <unknownTag>ignored</unknownTag>
  <licensePlate>XYZ9876</licensePlate>
  <vehicleInfo><speed>50</speed><extra>x</extra></vehicleInfo>
  <dateTime>2026-01-15T08:30:00</dateTime>
</EventNotificationAlert>"""
        parsed = parse_event_xml(xml_text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["plate"], "XYZ9876")
        self.assertEqual(parsed["speed"], "50")
        self.assertIn("15/01/2026", parsed["ts"])

    def test_parse_event_xml_anpr_line_speed_speed_limit(self):
        """ANPR XML com line, speed e speedLimit: parser retorna lane (line), speed, camera_speed_limit."""
        xml_anpr = """<?xml version="1.0" encoding="utf-8"?>
<EventNotificationAlert version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
<dateTime>2026-03-14T11:00:08.231-03:00</dateTime>
<eventType>ANPR</eventType>
<eventDescription>ANPR</eventDescription>
<ANPR>
<licensePlate>TAS4G25</licensePlate>
<line>1</line>
<direction>reverse</direction>
<speedLimit>30</speedLimit>
<vehicleInfo>
<speed>45</speed>
</vehicleInfo>
</ANPR>
</EventNotificationAlert>"""
        parsed = parse_event_xml(xml_anpr)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["plate"], "TAS4G25")
        self.assertEqual(parsed["lane"], "1")
        self.assertEqual(parsed["direction"], "reverse")
        self.assertEqual(parsed["ts"], "14/03/2026 11:00:08")
        self.assertEqual(parsed["speed"], "45")
        self.assertEqual(parsed["camera_speed_limit"], "30")
        self.assertEqual(parsed["event_type"], "ANPR")

    def test_complete_event_xml_detector_rejects_truncated_chunks(self):
        self.assertFalse(looks_like_complete_event_xml("<EventNotificationAlert><ANPR>"))
        self.assertTrue(looks_like_complete_event_xml("<EventNotificationAlert></EventNotificationAlert>"))

    def test_complete_event_xml_accepts_vehicle_detect_event_closing_tag(self):
        self.assertTrue(looks_like_complete_event_xml("<root></VehicleDetectEvent>"))
        # </ANPR> nao e tag de raiz; doc completo termina em </EventNotificationAlert>
        self.assertTrue(looks_like_complete_event_xml("<root><ANPR></ANPR></EventNotificationAlert>"))

    def test_find_event_xml_end_returns_end_at_root_tag_not_anpr(self):
        # Cortar em </ANPR> quebraria o XML; deve cortar no fim do root </EventNotificationAlert>
        buf = 'x<?xml version="1.0"?><EventNotificationAlert><ANPR><plate>A</plate></ANPR></EventNotificationAlert>y'
        start = buf.find("<?xml")
        end = find_event_xml_end(buf, start)
        self.assertIsNotNone(end)
        self.assertEqual(buf[start:end], '<?xml version="1.0"?><EventNotificationAlert><ANPR><plate>A</plate></ANPR></EventNotificationAlert>')

    def test_event_worker_emits_status_and_event_when_receiving_valid_xml(self):
        """Worker conectado a um stream que envia um XML EventNotificationAlert emite log 'evento processado' e event_received."""
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert>
  <vehiclePlate>ABC1234</vehiclePlate>
  <vehicleSpeed>72</vehicleSpeed>
  <laneNo>1</laneNo>
  <dateTime>2026-03-14 15:00:00</dateTime>
</EventNotificationAlert>"""

        class MockStreamResponse:
            def __init__(self, xml_body):
                self._first = True
                self._body = xml_body.encode("utf-8") if isinstance(xml_body, str) else xml_body

            def iter_content(self, chunk_size=1024, decode_unicode=False):
                if self._first:
                    self._first = False
                    yield self._body
                while True:
                    yield b""

        status_messages = []
        events_received = []

        def on_status(msg):
            status_messages.append(msg)

        def on_event(data):
            events_received.append(data)

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = build_camera_config(name="CamTest", output_dir=tmpdir)
            with patch("src.core.camera_client.CameraClient.connect_alert_stream", return_value=(MockStreamResponse(sample_xml), "http://mock/alertStream")):
                with patch("src.core.camera_client.CameraClient.download_snapshot", side_effect=RuntimeError("no snapshot")):
                    worker = EventWorker(cfg)
                    worker.status.connect(on_status)
                    worker.event_received.connect(on_event)
                    worker.start()
                    import time
                    app = QApplication.instance()
                    deadline = time.time() + 2.0
                    while time.time() < deadline and len(events_received) == 0:
                        app.processEvents()
                        time.sleep(0.05)
                    worker.stop()
                    worker.wait(3000)
                    for _ in range(20):
                        app.processEvents()
        self.assertGreater(len(events_received), 0, f"Worker deveria emitir event_received; status recebidos: {status_messages}")
        self.assertEqual(events_received[0].get("plate"), "ABC1234")
        self.assertEqual(events_received[0].get("speed"), "72")
        status_joined = " ".join(status_messages)
        self.assertIn("evento processado", status_joined, f"Log deveria conter 'evento processado'; status: {status_joined}")

    def test_event_flow_parse_then_insert_with_image_path_persists_photo_path(self):
        """Fluxo: XML de evento -> parse -> event_data com image_path (como se snapshot OK) -> insert_event -> leitura confirma image_path."""
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert>
  <vehiclePlate>XYZ9876</vehiclePlate>
  <vehicleSpeed>55</vehicleSpeed>
  <laneNo>1</laneNo>
  <dateTime>2026-03-14 14:30:00</dateTime>
</EventNotificationAlert>"""
        parsed = parse_event_xml(sample_xml)
        self.assertIsNotNone(parsed)
        event_data = dict(parsed)
        event_data["camera_name"] = "Camera Test"
        event_data["xml_path"] = "/tmp/out/xml/cam_ev.xml"
        event_data["json_path"] = "/tmp/out/json/cam_ev.json"
        event_data["image_path"] = "/tmp/out/images/Camera_Test_20260314_143000_123456.jpg"
        event_data["image_status"] = "imagem obtida por http://192.168.1.64/ISAPI/Streaming/channels/101/picture"
        event_data["applied_speed_limit"] = 60.0
        event_data["is_overspeed"] = False

        with self._temp_db_path() as db_path:
            db = Database(db_path)
            db.insert_event(event_data)
            rows = db.recent_events_with_speed(camera_name="Camera Test")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][EVT_IDX_PLATE], "XYZ9876")
            self.assertEqual(rows[0][EVT_IDX_SPEED], "55")
            self.assertEqual(rows[0][EVT_IDX_IMAGE_PATH], event_data["image_path"])

    def test_overspeed_triggers_evolution_alert_when_enabled(self):
        """Com Evolution habilitada na câmera e no app, evento acima do limite chama send_alert."""
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)
            config.data["evolution_api"] = {
                "enabled": True,
                "base_url": "http://evo.test",
                "api_token": "token",
                "instance_name": "inst",
                "recipient_numbers": ["5511999999999"],
            }
            config.data["cameras"] = [
                build_camera_config(
                    name="Camera 1",
                    speed_limit_value=50,
                    evolution_enabled=True,
                ),
            ]
            config.save()
            config._normalize_evolution_api()

            class FakeMainWindow:
                def __init__(self, app_config):
                    self.config = app_config
                    self.tab_evolution = MagicMock()

            fake = FakeMainWindow(config)
            event_data = {
                "camera_name": "Camera 1",
                "plate": "TAS4G25",
                "speed": "72",
                "ts": "2026-03-14 11:00:08",
                "lane": "1",
                "direction": "reverse",
                "event_type": "ANPR",
                "image_path": "",
                "applied_speed_limit": 50.0,
                "is_overspeed": True,
            }
            MainWindow.maybe_send_evolution_alert(fake, event_data)

            fake.tab_evolution.send_alert.assert_called_once()
            call_args = fake.tab_evolution.send_alert.call_args
            self.assertEqual(call_args[0][1], ["5511999999999"])
            self.assertEqual(call_args[0][0].get("plate"), "TAS4G25")
            self.assertEqual(call_args[0][0].get("speed"), "72")
            self.assertTrue(call_args[0][0].get("is_overspeed"))

    def test_main_window_uses_per_camera_speed_limit(self):
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)
            config.data["cameras"] = [
                build_camera_config(name="Camera A", speed_limit_enabled=True, speed_limit_value=50, speed_alert_visual=True),
                build_camera_config(name="Camera B", speed_limit_enabled=False, speed_limit_value=40, speed_alert_visual=False),
            ]
            config.save()

            class DummyWindow:
                def __init__(self, app_config):
                    self.config = app_config

                get_camera_speed_settings = MainWindow.get_camera_speed_settings
                resolve_row_overspeed = MainWindow.resolve_row_overspeed

                def filter_overspeed_rows(self, rows):
                    return [row for row in rows if self.resolve_row_overspeed(row)[1]]

            window = DummyWindow(config)
            self.assertEqual(window.get_camera_speed_settings("Camera A"), (50, True))
            self.assertEqual(window.get_camera_speed_settings("Camera B"), (60, False))

            rows = [
                ("Camera A", "2026-03-13 10:00:00", "ABC1234", "55", 55.0, "1", "N", "evento", "", "", None, None),
                ("Camera B", "2026-03-13 10:00:01", "XYZ9999", "55", 55.0, "1", "N", "evento", "", "", None, None),
            ]
            filtered = window.filter_overspeed_rows(rows)
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0][0], "Camera A")

    def test_database_persists_applied_speed_limit_and_is_overspeed(self):
        with self._temp_db_path() as db_path:
            db = Database(db_path)
            db.insert_event({
                "camera_name": "Camera A",
                "ts": "2026-03-13 10:00:00",
                "plate": "ABC1234",
                "speed": "72",
                "lane": "1",
                "direction": "N",
                "event_type": "evento",
                "image_path": "",
                "xml_path": "",
                "json_path": "",
                "raw_xml": "<xml />",
                "applied_speed_limit": 60.0,
                "is_overspeed": True,
            })

            rows = db.recent_events_with_speed(camera_name="Camera A")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][EVT_IDX_APPLIED_LIMIT], 60.0)
            self.assertEqual(rows[0][EVT_IDX_IS_OVERSPEED], 1)

    def test_database_insert_speed_text_and_overspeed_false(self):
        """Insert com texto de velocidade e is_overspeed False; verifica speed_value e colunas de excesso."""
        with self._temp_db_path() as db_path:
            db = Database(db_path)
            db.insert_event({
                "camera_name": "Camera A",
                "ts": "2026-03-13 11:00:00",
                "plate": "DEF5678",
                "speed": "45 km/h",
                "lane": "2",
                "direction": "S",
                "event_type": "evento",
                "image_path": "",
                "xml_path": "",
                "json_path": "",
                "raw_xml": "<xml />",
                "applied_speed_limit": 60.0,
                "is_overspeed": False,
            })
            rows = db.recent_events_with_speed(camera_name="Camera A")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][EVT_IDX_SPEED], "45 km/h")
            self.assertEqual(rows[0][EVT_IDX_SPEED_VALUE], 45.0)
            self.assertEqual(rows[0][EVT_IDX_APPLIED_LIMIT], 60.0)
            self.assertEqual(rows[0][EVT_IDX_IS_OVERSPEED], 0)

    def test_database_insert_and_read_back_verifies_save(self):
        """Verifica que os dados inseridos sao persistidos e recuperados do banco."""
        with self._temp_db_path() as db_path:
            db = Database(db_path)
            self.assertEqual(db.count_events(), 0)

            data = {
                "camera_name": "Camera Test",
                "ts": "2026-03-14 12:00:00",
                "plate": "TEST123",
                "speed": "80 km/h",
                "lane": "1",
                "direction": "N",
                "event_type": "overspeed",
                "image_path": "/path/img.jpg",
                "xml_path": "/path/ev.xml",
                "json_path": "/path/ev.json",
                "raw_xml": "<event />",
                "applied_speed_limit": 60.0,
                "is_overspeed": True,
            }
            db.insert_event(data)

            self.assertEqual(db.count_events(), 1)
            self.assertIsNotNone(db.last_event_id())

            rows = db.recent_events_with_speed(camera_name="Camera Test")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][EVT_IDX_CAMERA_NAME], "Camera Test")
            self.assertEqual(rows[0][EVT_IDX_TS], "2026-03-14 12:00:00")
            self.assertEqual(rows[0][EVT_IDX_PLATE], "TEST123")
            self.assertEqual(rows[0][EVT_IDX_SPEED], "80 km/h")
            self.assertEqual(rows[0][EVT_IDX_SPEED_VALUE], 80.0)
            self.assertEqual(rows[0][EVT_IDX_APPLIED_LIMIT], 60.0)
            self.assertEqual(rows[0][EVT_IDX_IS_OVERSPEED], 1)
            self.assertEqual(rows[0][EVT_IDX_IMAGE_PATH], "/path/img.jpg")

    def test_database_migrates_existing_events_table(self):
        with self._temp_db_path() as db_path:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_name TEXT,
                    ts TEXT,
                    plate TEXT,
                    speed TEXT,
                    speed_value REAL,
                    lane TEXT,
                    direction TEXT,
                    event_type TEXT,
                    image_path TEXT,
                    xml_path TEXT,
                    json_path TEXT,
                    raw_xml TEXT
                )
            """)
            conn.commit()
            conn.close()

            db = Database(db_path)
            columns = {row[1] for row in db.conn.execute("PRAGMA table_info(events)").fetchall()}

            self.assertIn("applied_speed_limit", columns)
            self.assertIn("is_overspeed", columns)

    def test_filter_overspeed_rows_uses_persisted_historical_limit(self):
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)
            config.data["speed_limit"] = 60
            config.data["cameras"] = [
                build_camera_config(name="Camera A", speed_limit_enabled=True, speed_limit_value=50, speed_alert_visual=True),
            ]
            config.save()

            class DummyWindow:
                def __init__(self, app_config):
                    self.config = app_config

                get_camera_speed_settings = MainWindow.get_camera_speed_settings
                resolve_row_overspeed = MainWindow.resolve_row_overspeed

                def filter_overspeed_rows(self, rows):
                    return [row for row in rows if self.resolve_row_overspeed(row)[1]]

            window = DummyWindow(config)
            rows = [
                ("Camera A", "2026-03-13 10:00:00", "ABC1234", "55", 55.0, "1", "N", "evento", "", "", 60.0, 0),
            ]

            filtered = window.filter_overspeed_rows(rows)
            self.assertEqual(filtered, [])

    def test_monitoramento_inicia_apenas_cameras_habilitadas_com_credenciais_salvas(self):
        """Com config com credenciais salvas, apenas cameras enabled entrariam no monitoramento (mesma logica de start_all_monitors)."""
        with self._temp_config_path() as cfg_path:
            config = AppConfig(filepath=cfg_path)
            config.data["cameras"] = [
                build_camera_config(name="Cam A", enabled=True, camera_ip="192.168.1.10", camera_user="admin", camera_pass="salva"),
                build_camera_config(name="Cam B", enabled=False, camera_ip="192.168.1.11", camera_user="op", camera_pass="outra"),
            ]
            config.save()

            reloaded = AppConfig(filepath=cfg_path)
            cameras_to_monitor = [c for c in reloaded.data.get("cameras", []) if c.get("enabled", True)]
            self.assertEqual(len(cameras_to_monitor), 1)
            self.assertEqual(cameras_to_monitor[0]["name"], "Cam A")
            # FASE 1.2: Passwords are now encrypted - verify format
            self.assertIsInstance(cameras_to_monitor[0]["camera_pass"], dict)
            self.assertIn("encrypted", cameras_to_monitor[0]["camera_pass"])
            # Verify we can decrypt it back
            from src.core.crypto import decrypt_password
            decrypted_pass = decrypt_password(cameras_to_monitor[0]["camera_pass"])
            self.assertEqual(decrypted_pass, "salva")
            self.assertEqual(cameras_to_monitor[0]["camera_user"], "admin")

    @contextmanager
    def _temp_config_path(self):
        workspace = Path(__file__).resolve().parents[1]
        config_path = workspace / f"test_config_{uuid4().hex}.json"
        try:
            yield config_path
        finally:
            try:
                config_path.unlink()
            except Exception:
                pass

    @contextmanager
    def _temp_db_path(self):
        workspace = Path(__file__).resolve().parents[1]
        db_path = workspace / f"test_events_{uuid4().hex}.db"
        try:
            yield db_path
        finally:
            try:
                db_path.unlink()
            except Exception:
                pass

    @contextmanager
    def _temp_image_path(self):
        workspace = Path(__file__).resolve().parents[1]
        image_path = workspace / f"test_image_{uuid4().hex}.jpg"
        try:
            yield image_path
        finally:
            try:
                image_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
