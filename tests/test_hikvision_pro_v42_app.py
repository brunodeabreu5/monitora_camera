import os
import sqlite3
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import requests
from PySide6.QtWidgets import QApplication, QLineEdit

from src.core.config import AppConfig, render_event_message
from src.core.camera_client import CameraClient
from src.core.database import Database
from src.core.evolution_client import EvolutionApiClient
from src.core.parsing import looks_like_complete_event_xml, parse_event_xml
from ui.widgets import PasswordField
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
            self.assertEqual(reloaded.get_camera("Portaria"), camera)

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
            "rtsp://operador:s%40nh%20a@192.168.0.10:554/Streaming/Channels/101",
        )

    def test_camera_client_uses_custom_rtsp_url_when_provided(self):
        client = CameraClient(build_camera_config(rtsp_url="rtsp://custom/live"))
        self.assertEqual(client.build_rtsp_url(), "rtsp://custom/live")

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

    def test_complete_event_xml_detector_rejects_truncated_chunks(self):
        self.assertFalse(looks_like_complete_event_xml("<EventNotificationAlert><ANPR>"))
        self.assertTrue(looks_like_complete_event_xml("<EventNotificationAlert></EventNotificationAlert>"))

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
                filter_overspeed_rows = MainWindow.filter_overspeed_rows

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
            self.assertEqual(rows[0][10], 60.0)
            self.assertEqual(rows[0][11], 1)

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
                filter_overspeed_rows = MainWindow.filter_overspeed_rows

            window = DummyWindow(config)
            rows = [
                ("Camera A", "2026-03-13 10:00:00", "ABC1234", "55", 55.0, "1", "N", "evento", "", "", 60.0, 0),
            ]

            filtered = window.filter_overspeed_rows(rows)
            self.assertEqual(filtered, [])

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
