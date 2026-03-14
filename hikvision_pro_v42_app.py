
# Arquivo gerado para Hikvision Radar Pro V4.2
import sys
import json
import csv
import sqlite3
import threading
import time
import re
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

import requests
from requests.auth import HTTPDigestAuth

from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl, QTimer
from PySide6.QtGui import QAction, QColor, QPixmap
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QSpinBox, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QGroupBox,
    QHeaderView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QListWidget,
    QListWidgetItem, QSplitter, QSizePolicy, QScrollArea, QToolButton, QStackedLayout,
    QSystemTrayIcon, QMenu, QStyle
)

APP_NAME = "Hikvision Radar Pro V4.2"
CONFIG_FILE = "hikvision_pro_v42_config.json"
DB_FILE = "events_v42.db"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"

def log_runtime_error(context: str, exc: Exception):
    stamp = now_str()
    message = f"[{stamp}] {context}: {exc}"
    print(message, file=sys.stderr)
    try:
        log_path = app_dir() / "hikvision_pro_v42.log"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")
    except Exception:
        pass

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def sanitize_filename(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', text)

def color_from_name(text: str) -> QColor:
    palette = ["#f7fbff", "#eefaf2", "#fff7e8", "#f7f0ff", "#eef7fb", "#fff0f0"]
    index = sum(ord(ch) for ch in text) % len(palette)
    return QColor(palette[index])

def extract_speed_value(speed_text: str) -> float:
    if not speed_text:
        return 0.0
    m = re.search(r'(\d+(?:\.\d+)?)', str(speed_text))
    return float(m.group(1)) if m else 0.0

def sanitize_phone_number(text: str) -> str:
    return re.sub(r"\D+", "", str(text or ""))

def parse_recipient_numbers(text: str) -> list[str]:
    parts = re.split(r"[\s,;]+", text or "")
    numbers = []
    for part in parts:
        normalized = sanitize_phone_number(part)
        if normalized:
            numbers.append(normalized)
    return numbers

def first_nested(data, *paths):
    for path in paths:
        current = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current not in (None, ""):
            return current
    return None

def render_event_message(template: str, event_data: dict) -> str:
    default_template = (
        "Alerta de velocidade\n"
        "Camera: {camera}\n"
        "Placa: {plate}\n"
        "Velocidade: {speed} km/h\n"
        "Limite: {limit} km/h\n"
        "Data/Hora: {ts}\n"
        "Faixa: {lane}\n"
        "Direcao: {direction}\n"
        "Tipo: {event_type}"
    )
    safe_data = {
        "camera": str(event_data.get("camera_name") or "-"),
        "plate": str(event_data.get("plate") or "-"),
        "speed": str(event_data.get("speed") or "-"),
        "limit": str(int(float(event_data.get("applied_speed_limit") or 0))) if event_data.get("applied_speed_limit") is not None else "-",
        "ts": str(event_data.get("ts") or "-"),
        "lane": str(event_data.get("lane") or "-"),
        "direction": str(event_data.get("direction") or "-"),
        "event_type": str(event_data.get("event_type") or "-"),
    }
    text = str(template or "").strip()
    if not text:
        text = default_template
    for key, value in safe_data.items():
        text = text.replace(f"{{{key}}}", value)
    return text

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(user: dict, password: str) -> bool:
    password_hash = user.get("password_hash", "")
    if password_hash:
        return hash_password(password) == password_hash
    legacy_password = user.get("password")
    return legacy_password == password

class AppConfig:
    def __init__(self, filepath: Path | None = None):
        self.filepath = filepath or (app_dir() / CONFIG_FILE)
        self.data = {
            "speed_limit": 60,
            "users": [self._default_admin_user()],
            "cameras": [self._default_camera()],
            "evolution_api": self._default_evolution_api(),
        }
        self.load()

    def _default_admin_user(self) -> dict:
        return {
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
            "role": "Administrador",
            "must_change_password": True,
        }

    def _default_camera(self) -> dict:
        return {
            "name": "Camera 1",
            "enabled": True,
            "camera_ip": "192.168.1.64",
            "camera_port": 80,
            "camera_user": "admin",
            "camera_pass": "",
            "channel": 101,
            "timeout": 15,
            "output_dir": str(app_dir() / "output"),
            "save_snapshot_on_event": True,
            "camera_mode": "auto",
            "speed_limit_enabled": True,
            "speed_limit_value": 60,
            "speed_alert_visual": True,
            "rtsp_enabled": True,
            "rtsp_port": 554,
            "rtsp_transport": "tcp",
            "rtsp_url": "",
            "live_fallback_mode": "snapshot",
            "evolution_enabled": False,
        }

    def _default_evolution_api(self) -> dict:
        return {
            "enabled": False,
            "base_url": "",
            "api_token": "",
            "instance_name": "",
            "instance_mode": "create_or_connect",
            "recipient_numbers": [],
            "send_image_with_caption": True,
            "test_target_number": "",
            "test_message_text": "Teste de conexao Evolution API",
            "event_message_template": (
                "Alerta de velocidade\n"
                "Camera: {camera}\n"
                "Placa: {plate}\n"
                "Velocidade: {speed} km/h\n"
                "Limite: {limit} km/h\n"
                "Data/Hora: {ts}\n"
                "Faixa: {lane}\n"
                "Direcao: {direction}\n"
                "Tipo: {event_type}"
            ),
        }

    def _normalize_users(self):
        normalized = []
        for raw_user in self.data.get("users", []):
            if not isinstance(raw_user, dict):
                continue
            user = dict(raw_user)
            if user.get("password") and not user.get("password_hash"):
                user["password_hash"] = hash_password(user["password"])
            user.pop("password", None)
            user.setdefault("role", "Operador")
            user["must_change_password"] = bool(user.get("must_change_password", False))
            if user.get("username"):
                normalized.append(user)
        if not normalized:
            normalized.append(self._default_admin_user())
        self.data["users"] = normalized

    def _normalize_cameras(self):
        normalized = []
        defaults = self._default_camera()
        for raw_camera in self.data.get("cameras", []):
            if not isinstance(raw_camera, dict):
                continue
            camera = dict(defaults)
            camera.update(raw_camera)
            camera["name"] = str(camera.get("name", defaults["name"]))
            camera["enabled"] = bool(camera.get("enabled", True))
            camera["camera_ip"] = str(camera.get("camera_ip", "")).strip()
            camera["camera_user"] = str(camera.get("camera_user", "")).strip()
            camera["camera_pass"] = str(camera.get("camera_pass", ""))
            camera["output_dir"] = str(camera.get("output_dir", defaults["output_dir"]))
            camera["save_snapshot_on_event"] = bool(camera.get("save_snapshot_on_event", True))
            camera["camera_mode"] = str(camera.get("camera_mode", "auto"))
            camera["speed_limit_enabled"] = bool(camera.get("speed_limit_enabled", True))
            camera["speed_alert_visual"] = bool(camera.get("speed_alert_visual", True))
            camera["rtsp_enabled"] = bool(camera.get("rtsp_enabled", True))
            camera["rtsp_url"] = str(camera.get("rtsp_url", "")).strip()
            camera["rtsp_transport"] = str(camera.get("rtsp_transport", "tcp"))
            camera["live_fallback_mode"] = str(camera.get("live_fallback_mode", "snapshot"))
            camera["evolution_enabled"] = bool(camera.get("evolution_enabled", False))
            try:
                camera["camera_port"] = int(camera.get("camera_port", defaults["camera_port"]))
            except Exception:
                camera["camera_port"] = defaults["camera_port"]
            try:
                camera["channel"] = int(camera.get("channel", defaults["channel"]))
            except Exception:
                camera["channel"] = defaults["channel"]
            try:
                camera["timeout"] = int(camera.get("timeout", defaults["timeout"]))
            except Exception:
                camera["timeout"] = defaults["timeout"]
            try:
                camera["speed_limit_value"] = int(camera.get("speed_limit_value", self.data.get("speed_limit", defaults["speed_limit_value"])))
            except Exception:
                camera["speed_limit_value"] = int(self.data.get("speed_limit", defaults["speed_limit_value"]))
            try:
                camera["rtsp_port"] = int(camera.get("rtsp_port", defaults["rtsp_port"]))
            except Exception:
                camera["rtsp_port"] = defaults["rtsp_port"]
            normalized.append(camera)
        if not normalized:
            normalized.append(defaults)
        self.data["cameras"] = normalized

    def _normalize_evolution_api(self):
        defaults = self._default_evolution_api()
        config = dict(defaults)
        raw = self.data.get("evolution_api", {})
        if isinstance(raw, dict):
            config.update(raw)
        config["enabled"] = bool(config.get("enabled", False))
        config["base_url"] = str(config.get("base_url", "")).strip().rstrip("/")
        config["api_token"] = str(config.get("api_token", "")).strip()
        config["instance_name"] = str(config.get("instance_name", "")).strip()
        mode = str(config.get("instance_mode", defaults["instance_mode"])).strip() or defaults["instance_mode"]
        config["instance_mode"] = mode if mode in ("existing", "create_or_connect") else defaults["instance_mode"]
        recipients = config.get("recipient_numbers", [])
        if isinstance(recipients, str):
            recipients = parse_recipient_numbers(recipients)
        elif isinstance(recipients, list):
            recipients = [sanitize_phone_number(number) for number in recipients]
        else:
            recipients = []
        config["recipient_numbers"] = [number for number in recipients if number]
        config["send_image_with_caption"] = bool(config.get("send_image_with_caption", True))
        config["test_target_number"] = sanitize_phone_number(config.get("test_target_number", ""))
        config["test_message_text"] = str(config.get("test_message_text", defaults["test_message_text"]))
        template = str(config.get("event_message_template", defaults["event_message_template"]))
        config["event_message_template"] = template.strip() or defaults["event_message_template"]
        self.data["evolution_api"] = config

    def load(self):
        if self.filepath.exists():
            try:
                loaded = json.loads(self.filepath.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except Exception as exc:
                log_runtime_error(f"Falha ao carregar configuracao {self.filepath}", exc)
        self._normalize_users()
        self._normalize_cameras()
        self._normalize_evolution_api()

    def save(self):
        self._normalize_users()
        self._normalize_cameras()
        self._normalize_evolution_api()
        self.filepath.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_camera_names(self):
        return [c.get("name", "Camera") for c in self.data.get("cameras", [])]

    def get_camera(self, name):
        for cam in self.data.get("cameras", []):
            if cam.get("name") == name:
                return cam
        return None

    def upsert_camera(self, camera_data):
        cameras = self.data.setdefault("cameras", [])
        for i, cam in enumerate(cameras):
            if cam.get("name") == camera_data.get("name"):
                cameras[i] = camera_data
                return
        cameras.append(camera_data)

    def delete_camera(self, name):
        self.data["cameras"] = [c for c in self.data.get("cameras", []) if c.get("name") != name]

    def authenticate(self, username, password):
        for user in self.data.get("users", []):
            if user.get("username") == username and verify_password(user, password):
                return dict(user)
        return None

    def upsert_user(self, user_data):
        users = self.data.setdefault("users", [])
        sanitized_user = dict(user_data)
        sanitized_user.pop("password", None)
        for i, user in enumerate(users):
            if user.get("username") == sanitized_user.get("username"):
                users[i] = sanitized_user
                return
        users.append(sanitized_user)

    def delete_user(self, username):
        self.data["users"] = [u for u in self.data.get("users", []) if u.get("username") != username]

    def get_user(self, username):
        for user in self.data.get("users", []):
            if user.get("username") == username:
                return user
        return None

    def user_requires_password_change(self, username: str) -> bool:
        user = self.get_user(username)
        return bool(user and user.get("must_change_password"))

class Database:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
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
            raw_xml TEXT,
            applied_speed_limit REAL,
            is_overspeed INTEGER
        )""")
        self._ensure_event_columns()
        self.conn.commit()

    def _ensure_event_columns(self):
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(events)").fetchall()}
        if "applied_speed_limit" not in existing:
            self.conn.execute("ALTER TABLE events ADD COLUMN applied_speed_limit REAL")
        if "is_overspeed" not in existing:
            self.conn.execute("ALTER TABLE events ADD COLUMN is_overspeed INTEGER")

    def insert_event(self, data: dict):
        with self.lock:
            self.conn.execute("""
            INSERT INTO events (camera_name, ts, plate, speed, speed_value, lane, direction, event_type, image_path, xml_path, json_path, raw_xml, applied_speed_limit, is_overspeed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("camera_name"), data.get("ts"), data.get("plate"), data.get("speed"),
                extract_speed_value(data.get("speed", "")), data.get("lane"), data.get("direction"),
                data.get("event_type"), data.get("image_path"), data.get("xml_path"),
                data.get("json_path"), data.get("raw_xml"), data.get("applied_speed_limit"),
                1 if data.get("is_overspeed") else 0
            ))
            self.conn.commit()

    def filtered_events(self, camera_name="", plate="", date_text="", min_speed="", over_limit=None):
        with self.lock:
            query = """SELECT camera_name, ts, plate, speed, lane, direction, event_type, image_path, json_path FROM events WHERE 1=1"""
            params = []
            if camera_name:
                query += " AND camera_name = ?"; params.append(camera_name)
            if plate:
                query += " AND upper(plate) LIKE ?"; params.append(f"%{plate.upper()}%")
            if date_text:
                query += " AND ts LIKE ?"; params.append(f"%{date_text}%")
            if min_speed:
                try:
                    query += " AND speed_value >= ?"; params.append(float(min_speed))
                except Exception:
                    pass
            if over_limit is not None:
                query += " AND speed_value > ?"; params.append(float(over_limit))
            query += " ORDER BY id DESC LIMIT 1000"
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def recent_events_with_speed(self, camera_name="", date_text=""):
        with self.lock:
            query = """SELECT camera_name, ts, plate, speed, speed_value, lane, direction, event_type, image_path, json_path, applied_speed_limit, is_overspeed FROM events WHERE 1=1"""
            params = []
            if camera_name:
                query += " AND camera_name = ?"; params.append(camera_name)
            if date_text:
                query += " AND ts LIKE ?"; params.append(f"%{date_text}%")
            query += " ORDER BY id DESC LIMIT 1000"
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def dashboard_event_speeds(self):
        with self.lock:
            today = datetime.now().strftime("%Y-%m-%d")
            cur = self.conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            today_count = cur.execute("SELECT COUNT(*) FROM events WHERE ts LIKE ?", (f"{today}%",)).fetchone()[0]
            rows = cur.execute("SELECT camera_name, speed_value, applied_speed_limit, is_overspeed FROM events").fetchall()
            last_plate = cur.execute("SELECT plate FROM events ORDER BY id DESC LIMIT 1").fetchone()
            return {"total": total, "today": today_count, "rows": rows, "last_plate": last_plate[0] if last_plate else "-"}

    def dashboard_counts(self, speed_limit=60):
        with self.lock:
            today = datetime.now().strftime("%Y-%m-%d")
            cur = self.conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            today_count = cur.execute("SELECT COUNT(*) FROM events WHERE ts LIKE ?", (f"{today}%",)).fetchone()[0]
            overspeed = cur.execute("SELECT COUNT(*) FROM events WHERE speed_value > ?", (float(speed_limit),)).fetchone()[0]
            last_plate = cur.execute("SELECT plate FROM events ORDER BY id DESC LIMIT 1").fetchone()
            return {"total": total, "today": today_count, "overspeed": overspeed, "last_plate": last_plate[0] if last_plate else "-"}

def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag

def detect_text(root, names):
    wanted = {n.lower() for n in names}
    for elem in root.iter():
        tag = strip_ns(elem.tag).lower()
        if tag in wanted and elem.text and elem.text.strip():
            return elem.text.strip()
    return ""

def parse_event_xml(xml_text: str) -> dict | None:
    xml_text = xml_text.strip()
    if not xml_text:
        return None
    data = {"ts": now_str(), "plate": "", "speed": "", "lane": "", "direction": "", "event_type": "", "raw_xml": xml_text}
    try:
        root = ET.fromstring(xml_text)
        data["event_type"] = detect_text(root, ["eventType", "eventDescription", "eventName", "type", "eventTypeEx", "alarmType", "vehicleDetectType"])
        data["plate"] = detect_text(root, ["licensePlate", "plateNo", "vehiclePlate", "plateNumber", "license", "plate"])
        data["speed"] = detect_text(root, ["speed", "vehicleSpeed", "vehicleSpeedValue"])
        data["lane"] = detect_text(root, ["laneNo", "lane", "driveLane"])
        data["direction"] = detect_text(root, ["direction", "driveDirection", "vehicleDirection"])
        date_part = detect_text(root, ["dateTime", "time", "captureTime", "occurTime"])
        if date_part:
            data["ts"] = date_part
        return data
    except ET.ParseError:
        return None


def looks_like_complete_event_xml(xml_text: str) -> bool:
    xml_text = xml_text.strip()
    if not xml_text or "</" not in xml_text:
        return False
    return (
        xml_text.endswith("</EventNotificationAlert>")
        or xml_text.endswith("</ANPR>")
    )



class CameraClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.ip = cfg["camera_ip"].strip()
        self.port = int(cfg["camera_port"])
        self.user = cfg["camera_user"]
        self.password = cfg["camera_pass"]
        self.timeout = int(cfg["timeout"])
        self.session = requests.Session()
        self.auth = HTTPDigestAuth(self.user, self.password)

    def base_http(self):
        return f"http://{self.ip}:{self.port}"

    def build_rtsp_url(self):
        custom_url = str(self.cfg.get("rtsp_url", "")).strip()
        if custom_url:
            return custom_url
        rtsp_port = int(self.cfg.get("rtsp_port", 554))
        channel = int(self.cfg.get("channel", 101))
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        return f"rtsp://{user}:{password}@{self.ip}:{rtsp_port}/Streaming/Channels/{channel}"

    def is_traffic_mode(self):
        mode = self.cfg.get("camera_mode", "auto")
        return mode in ("traffic", "auto")

    def snapshot_candidates(self):
        ch = int(self.cfg["channel"])
        return [
            f"{self.base_http()}/ISAPI/Streaming/channels/{ch}/picture",
            f"{self.base_http()}/ISAPI/Streaming/channels/1/picture",
            f"{self.base_http()}/ISAPI/Traffic/channels/1/snapshot",
            f"{self.base_http()}/ISAPI/Traffic/channels/1/vehicleDetect/picture",
        ]

    def alert_stream_candidates(self):
        return [f"{self.base_http()}/ISAPI/Event/notification/alertStream"]

    def traffic_probe_url(self):
        return f"{self.base_http()}/ISAPI/Traffic/channels/1/vehicleDetect"

    def request(self, url, stream=False, timeout=None):
        if timeout is None:
            timeout = self.timeout
        return self.session.get(url, auth=self.auth, timeout=timeout, stream=stream, headers={"Accept": "multipart/x-mixed-replace, text/xml, */*"})

    def describe_connection_result(self, status_code: int, detail: str):
        if status_code in (401, 403):
            return False, status_code, f"autenticacao falhou: {detail}"
        return False, status_code, detail

    def detect_mode(self):
        if self.cfg.get("camera_mode") in ("traffic", "normal"):
            return self.cfg["camera_mode"]
        try:
            r = self.request(self.traffic_probe_url(), timeout=self.timeout)
            if r.status_code == 200 and "VehicleDetectCfg" in r.text:
                return "traffic"
        except Exception:
            pass
        return "normal"

    def test_connection(self):
        mode = self.detect_mode()
        if mode == "traffic":
            url = self.traffic_probe_url()
            try:
                r = self.request(url, timeout=self.timeout)
            except requests.RequestException as exc:
                return False, 0, f"erro de conexao em {url}: {exc}"
            if r.status_code == 200:
                return True, 200, f"traffic via {url}"
            return self.describe_connection_result(r.status_code, url)
        for url in self.snapshot_candidates():
            try:
                r = self.request(url, timeout=self.timeout)
                ctype = r.headers.get("Content-Type", "")
                if r.status_code == 200 and ("image" in ctype.lower() or r.content[:2] == b"\xff\xd8"):
                    return True, 200, url
                if r.status_code in (401, 403):
                    return self.describe_connection_result(r.status_code, url)
            except Exception:
                pass
        return False, 500, "snapshot not supported"

    def download_snapshot(self):
        last_error = "snapshot not supported"
        for url in self.snapshot_candidates():
            try:
                r = self.request(url, timeout=self.timeout)
                ctype = r.headers.get("Content-Type", "")
                if r.status_code == 200 and ("image" in ctype.lower() or r.content[:2] == b"\xff\xd8"):
                    return r.content, url
                last_error = f"HTTP {r.status_code} em {url}"
            except Exception as e:
                last_error = f"{url}: {e}"
        raise RuntimeError(last_error)

    def connect_alert_stream(self):
        last_error = "alert stream indisponível"
        for url in self.alert_stream_candidates():
            try:
                r = self.request(url, stream=True, timeout=(10, None))
                if r.status_code == 200:
                    return r, url
                last_error = f"HTTP {r.status_code} em {url}"
            except Exception as e:
                last_error = f"{url}: {e}"
        raise RuntimeError(last_error)

class EvolutionApiClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.base_url = str(self.cfg.get("base_url", "")).strip().rstrip("/")
        self.api_token = str(self.cfg.get("api_token", "")).strip()
        self.instance_name = str(self.cfg.get("instance_name", "")).strip()
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_token and self.instance_name)

    def headers(self) -> dict:
        return {
            "apikey": self.api_token,
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def request_json(self, method: str, path: str, payload=None, timeout=20):
        if not self.is_configured():
            raise RuntimeError("Evolution API nao configurada.")
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, json=payload, headers=self.headers(), timeout=timeout)
        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code} em {url}: {data}")
        return data

    def test_connection(self):
        data = self.request_json("GET", "/instance/fetchInstances")
        return data

    def fetch_instances(self):
        return self.request_json("GET", "/instance/fetchInstances")

    def connection_state(self):
        return self.request_json("GET", f"/instance/connectionState/{self.instance_name}")

    def create_instance(self):
        payload = {
            "instanceName": self.instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        return self.request_json("POST", "/instance/create", payload=payload)

    def connect_instance(self):
        return self.request_json("GET", f"/instance/connect/{self.instance_name}")

    def ensure_instance(self, create_if_missing=True):
        try:
            state = self.connection_state()
        except RuntimeError:
            if not create_if_missing:
                raise
            self.create_instance()
            state = self.connection_state()
        return state

    def fetch_qr_payload(self):
        data = self.connect_instance()
        return first_nested(
            data,
            ("base64",),
            ("qrcode", "base64"),
            ("qrcode",),
            ("qr",),
            ("code",),
            ("data", "qrcode"),
            ("data", "code"),
        ) or ""

    def build_qr_pixmap(self, qr_payload: str) -> QPixmap:
        pixmap = QPixmap()
        if not qr_payload:
            return pixmap
        if qr_payload.startswith("data:image"):
            encoded = qr_payload.split(",", 1)[-1]
            pixmap.loadFromData(base64.b64decode(encoded))
            return pixmap
        if re.fullmatch(r"[A-Za-z0-9+/=\s]+", qr_payload) and len(qr_payload.strip()) > 128:
            try:
                pixmap.loadFromData(base64.b64decode(qr_payload))
                if not pixmap.isNull():
                    return pixmap
            except Exception:
                pass
        return pixmap

    def send_media_message(self, number: str, caption: str, image_path: str):
        image_bytes = Path(image_path).read_bytes()
        payload = {
            "number": sanitize_phone_number(number),
            "mediatype": "image",
            "mimetype": "image/jpeg",
            "caption": caption,
            "fileName": Path(image_path).name,
            "media": base64.b64encode(image_bytes).decode("ascii"),
        }
        return self.request_json("POST", f"/message/sendMedia/{self.instance_name}", payload=payload)

    def send_text_message(self, number: str, text: str):
        payload = {
            "number": sanitize_phone_number(number),
            "text": text,
        }
        return self.request_json("POST", f"/message/sendText/{self.instance_name}", payload=payload)

class EvolutionSendWorker(QThread):
    finished_status = Signal(str)

    def __init__(self, evolution_cfg: dict, event_data: dict, recipients: list[str], override_text: str = ""):
        super().__init__()
        self.evolution_cfg = evolution_cfg
        self.event_data = event_data
        self.recipients = recipients
        self.override_text = str(override_text or "")

    def build_caption(self) -> str:
        if self.override_text.strip():
            return self.override_text.strip()
        return render_event_message(self.evolution_cfg.get("event_message_template", ""), self.event_data)

    def run(self):
        try:
            client = EvolutionApiClient(self.evolution_cfg)
            caption = self.build_caption()
            image_path = str(self.event_data.get("image_path", "") or "")
            sent = 0
            for number in self.recipients:
                try:
                    if image_path and Path(image_path).exists() and self.evolution_cfg.get("send_image_with_caption", True):
                        client.send_media_message(number, caption, image_path)
                    else:
                        client.send_text_message(number, caption)
                    sent += 1
                except Exception:
                    client.send_text_message(number, caption)
                    sent += 1
            self.finished_status.emit(f"Evolution API: alerta enviado para {sent} destinatario(s).")
        except Exception as exc:
            self.finished_status.emit(f"Evolution API: falha no envio ({exc})")

class EventWorker(QThread):
    status = Signal(str)
    event_received = Signal(dict)
    connection_state = Signal(str, bool, str)

    def __init__(self, camera_cfg: dict):
        super().__init__()
        self.camera_cfg = camera_cfg
        self.running = False

    def stop(self):
        self.running = False

    def save_snapshot_if_possible(self, client: CameraClient, cfg: dict, img_dir: Path, ts_label: str):
        if not cfg.get("save_snapshot_on_event", True):
            return "", "snapshot desativado"
        try:
            img_bytes, used_url = client.download_snapshot()
            img_path = img_dir / f"{cfg['name']}_{ts_label}.jpg"
            img_path.write_bytes(img_bytes)
            return str(img_path), f"imagem obtida por {used_url}"
        except Exception as e:
            return "", f"imagem não suportada: {e}"

    def run(self):
        self.running = True
        cfg = self.camera_cfg
        out_dir = Path(cfg["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        client = CameraClient(cfg)

        while self.running:
            try:
                self.status.emit(f"{cfg['name']}: conectando ao stream de eventos...")
                resp, used_url = client.connect_alert_stream()
                self.connection_state.emit(cfg["name"], True, f"eventos OK via {used_url}")
                self.status.emit(f"{cfg['name']}: conectado em {used_url}")

                buffer = ""
                for chunk in resp.iter_content(chunk_size=1024, decode_unicode=False):
                    if not self.running:
                        break
                    if not chunk:
                        continue
                    if isinstance(chunk, bytes):
                        chunk = chunk.decode("utf-8", errors="ignore")
                    buffer += chunk

                    while True:
                        start = buffer.find("<?xml")
                        if start == -1:
                            break
                        end = buffer.find("</EventNotificationAlert>")
                        if end == -1:
                            alt_end = buffer.find("</ANPR>")
                            if alt_end != -1:
                                end = alt_end + len("</ANPR>")
                            else:
                                break
                        else:
                            end += len("</EventNotificationAlert>")
                        xml_text = buffer[start:end]
                        buffer = buffer[end:]
                        if not xml_text.strip():
                            continue

                        if not looks_like_complete_event_xml(xml_text):
                            continue

                        event_data = parse_event_xml(xml_text)
                        if not event_data:
                            continue
                        event_data["camera_name"] = cfg["name"]
                        ts_label = sanitize_filename(datetime.now().strftime("%Y%m%d_%H%M%S_%f"))

                        xml_dir = out_dir / "xml"; json_dir = out_dir / "json"; img_dir = out_dir / "images"
                        xml_dir.mkdir(parents=True, exist_ok=True); json_dir.mkdir(parents=True, exist_ok=True); img_dir.mkdir(parents=True, exist_ok=True)

                        xml_path = xml_dir / f"{cfg['name']}_{ts_label}.xml"
                        json_path = json_dir / f"{cfg['name']}_{ts_label}.json"
                        xml_path.write_text(xml_text, encoding="utf-8")
                        event_data["xml_path"] = str(xml_path)

                        image_path, image_status = self.save_snapshot_if_possible(client, cfg, img_dir, ts_label)
                        event_data["image_path"] = image_path
                        event_data["image_status"] = image_status

                        json_path.write_text(json.dumps(event_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        event_data["json_path"] = str(json_path)
                        self.event_received.emit(event_data)
            except Exception as e:
                self.connection_state.emit(cfg["name"], False, str(e))
                self.status.emit(f"{cfg['name']}: erro {e}")
                time.sleep(5)

        self.connection_state.emit(cfg["name"], False, "monitor parado")
        self.status.emit(f"{cfg['name']}: monitor parado.")

class PasswordField(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.line_edit = QLineEdit()
        self.line_edit.setEchoMode(QLineEdit.Password)
        self.toggle_button = QToolButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setText("Ver")
        self.toggle_button.setToolTip("Mostrar senha")
        self.toggle_button.clicked.connect(self.toggle_password_visibility)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.toggle_button, 0)

    def toggle_password_visibility(self, checked: bool):
        self.line_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.toggle_button.setToolTip("Ocultar senha" if checked else "Mostrar senha")

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)

    def setFocus(self):
        self.line_edit.setFocus()

class LiveSnapshotWorker(QThread):
    frame_ready = Signal(bytes)
    status = Signal(str)

    def __init__(self, camera_cfg: dict, interval_ms: int = 1500):
        super().__init__()
        self.camera_cfg = dict(camera_cfg)
        self.interval_ms = max(500, int(interval_ms))
        self.running = False

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        snapshot_cfg = dict(self.camera_cfg)
        snapshot_cfg["timeout"] = min(int(snapshot_cfg.get("timeout", 15)), 5)
        client = CameraClient(snapshot_cfg)
        while self.running:
            try:
                img_bytes, used_url = client.download_snapshot()
                self.frame_ready.emit(img_bytes)
                self.status.emit(f"snapshot ao vivo via {used_url}")
            except Exception as exc:
                self.status.emit(f"fallback snapshot indisponivel: {exc}")
            self.msleep(self.interval_ms)

class LiveViewController(QWidget):
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_cfg = None
        self.current_mode = "idle"
        self._switching_mode = False
        self.last_snapshot = QPixmap()
        self.snapshot_worker = None
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.snapshot_label = QLabel("Video ao vivo parado")
        self.snapshot_label.setAlignment(Qt.AlignCenter)
        self.snapshot_label.setStyleSheet("border: 1px solid #888; background: #111; color: white;")
        self.snapshot_label.setMinimumHeight(280)
        self.video_widget.setMinimumHeight(280)
        self.player.setVideoOutput(self.video_widget)
        if hasattr(self.player, "errorOccurred"):
            self.player.errorOccurred.connect(self.on_player_error)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.addWidget(self.video_widget)
        self.stack.addWidget(self.snapshot_label)
        self.stack.setCurrentWidget(self.snapshot_label)

    def set_camera(self, camera_cfg: dict | None):
        self.camera_cfg = dict(camera_cfg) if camera_cfg else None

    def start(self):
        self._switching_mode = True
        self.stop()
        if not self.camera_cfg:
            self.show_message("Selecione uma camera para video ao vivo")
            self._switching_mode = False
            return
        if not self.camera_cfg.get("rtsp_enabled", True):
            self._switching_mode = False
            self.start_snapshot_fallback("RTSP desativado para esta camera")
            return
        client = CameraClient(self.camera_cfg)
        self.current_mode = "rtsp"
        self.stack.setCurrentWidget(self.video_widget)
        self.status_changed.emit(f"abrindo video ao vivo: {client.build_rtsp_url()}")
        self.player.setSource(QUrl(client.build_rtsp_url()))
        self.player.play()
        self._switching_mode = False

    def stop(self):
        if self.snapshot_worker:
            self.snapshot_worker.stop()
            self.snapshot_worker.wait(2000)
            self.snapshot_worker = None
        self.player.stop()
        self.player.setSource(QUrl())
        self.current_mode = "idle"
        self.stack.setCurrentWidget(self.snapshot_label)

    def start_snapshot_fallback(self, reason: str):
        if self._switching_mode:
            return
        self._switching_mode = True
        self.stop()
        self.current_mode = "snapshot"
        self.stack.setCurrentWidget(self.snapshot_label)
        self.show_message("Carregando snapshots ao vivo...")
        self.status_changed.emit(reason)
        if not self.camera_cfg or self.camera_cfg.get("live_fallback_mode", "snapshot") != "snapshot":
            self._switching_mode = False
            return
        self.snapshot_worker = LiveSnapshotWorker(self.camera_cfg)
        self.snapshot_worker.frame_ready.connect(self.on_snapshot_frame)
        self.snapshot_worker.status.connect(self.status_changed.emit)
        self.snapshot_worker.start()
        self._switching_mode = False

    def show_message(self, text: str):
        self.snapshot_label.setPixmap(QPixmap())
        self.snapshot_label.setText(text)

    def show_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self.show_message("Falha ao carregar imagem")
            return
        self.last_snapshot = pixmap
        scaled = pixmap.scaled(self.snapshot_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.snapshot_label.setPixmap(scaled)
        self.snapshot_label.setText("")

    def show_image_path(self, path: str):
        if self.current_mode == "rtsp":
            return
        self.stack.setCurrentWidget(self.snapshot_label)
        self.show_pixmap(QPixmap(path))

    def on_snapshot_frame(self, img_bytes: bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        self.stack.setCurrentWidget(self.snapshot_label)
        self.show_pixmap(pixmap)

    def on_player_error(self, *_):
        if self._switching_mode:
            return
        detail = self.player.errorString() or "falha ao abrir RTSP"
        self.start_snapshot_fallback(f"video ao vivo indisponivel: {detail}")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.start_snapshot_fallback("video ao vivo indisponivel: midia invalida")
        elif status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.BufferingMedia):
            self.status_changed.emit("video ao vivo conectado")

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.status_changed.emit("video ao vivo em reproducao")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.last_snapshot.isNull() and self.stack.currentWidget() is self.snapshot_label:
            self.show_pixmap(self.last_snapshot)

class LoginDialog(QDialog):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.user_data = None
        self.setWindowTitle("Login do sistema")
        self.setMinimumWidth(380)
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.pass_edit = PasswordField()
        form.addRow("Usuario:", self.user_edit)
        form.addRow("Senha:", self.pass_edit)
        layout.addLayout(form)
        info = QLabel("Primeiro acesso: admin / admin. Altere a senha padrao apos entrar.")
        info.setWordWrap(True)
        layout.addWidget(info)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.try_login)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def try_login(self):
        user = self.config.authenticate(self.user_edit.text().strip(), self.pass_edit.text())
        if user:
            self.user_data = user
            self.accept()
        else:
            QMessageBox.warning(self, APP_NAME, "Usuario ou senha invalidos.")

class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, logged_user: dict):
        super().__init__()
        self.config = config
        self.logged_user = logged_user
        self.setWindowTitle(f"{APP_NAME} - {logged_user.get('username')} ({logged_user.get('role')})")
        self.resize(1360, 900)
        self.setMinimumSize(QSize(1100, 740))
        default_output = Path(app_dir() / "output")
        default_output.mkdir(parents=True, exist_ok=True)
        self.db = Database(default_output / DB_FILE)
        self.workers = {}
        self.evolution_workers = []
        self.camera_states = {}
        self.last_image_path = ""
        self.live_view_running = False
        self._allow_close = False
        self._tray_message_shown = False
        self.build_ui()
        self.setup_tray_icon()
        self.reload_camera_lists()
        self.refresh_dashboard(); self.refresh_history(); self.refresh_report()
        if self.config.user_requires_password_change(self.logged_user.get("username", "")):
            QMessageBox.warning(self, APP_NAME, "Este usuario ainda usa a senha padrao. Abra a aba Usuarios e defina uma nova senha.")

    def build_scroll_tab(self, inner_widget):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame); scroll.setWidget(inner_widget); return scroll

    def apply_app_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #f3f6f8;
                color: #243447;
            }
            QTabWidget::pane {
                border: 1px solid #d7dee6;
                background: #f3f6f8;
            }
            QTabBar::tab {
                background: #e8eef3;
                color: #425466;
                padding: 8px 14px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #102a43;
                font-weight: 600;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d7dee6;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #486581;
            }
            QPushButton {
                background: #e6eef5;
                border: 1px solid #c6d2de;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #dbe7f1;
            }
            QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget, QTableWidget {
                background: #ffffff;
                border: 1px solid #d7dee6;
                border-radius: 6px;
                padding: 4px;
            }
            QHeaderView::section {
                background: #eef3f7;
                color: #425466;
                padding: 6px;
                border: none;
                border-right: 1px solid #d7dee6;
                border-bottom: 1px solid #d7dee6;
                font-weight: 600;
            }
        """)

    def style_data_table(self, table: QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setStyleSheet("alternate-background-color: #f7fafc; background: #ffffff;")

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        self.apply_app_theme()
        main = QVBoxLayout(root); main.setContentsMargins(8, 8, 8, 8); main.setSpacing(8)
        tabs = QTabWidget(); tabs.setDocumentMode(True); main.addWidget(tabs)

        self.tab_dashboard = QWidget(); self.tab_cameras = QWidget(); self.tab_monitor = QWidget(); self.tab_history = QWidget(); self.tab_report = QWidget(); self.tab_evolution = QWidget(); self.tab_users = QWidget()
        tabs.addTab(self.build_scroll_tab(self.tab_dashboard), "Dashboard")
        tabs.addTab(self.build_scroll_tab(self.tab_cameras), "Cameras")
        tabs.addTab(self.build_scroll_tab(self.tab_monitor), "Monitor")
        tabs.addTab(self.build_scroll_tab(self.tab_history), "Historico")
        tabs.addTab(self.build_scroll_tab(self.tab_report), "Excesso de velocidade")
        tabs.addTab(self.build_scroll_tab(self.tab_evolution), "Evolution API")
        tabs.addTab(self.build_scroll_tab(self.tab_users), "Usuarios")

        self.build_dashboard_tab(); self.build_cameras_tab(); self.build_monitor_tab(); self.build_history_tab(); self.build_report_tab(); self.build_evolution_tab(); self.build_users_tab()
        file_menu = self.menuBar().addMenu("Arquivo")
        act_export = QAction("Exportar historico CSV", self); act_export.triggered.connect(self.export_csv); file_menu.addAction(act_export)
        act_export_over = QAction("Exportar excesso CSV", self); act_export_over.triggered.connect(self.export_overspeed_csv); file_menu.addAction(act_export_over)
        act_hide = QAction("Enviar para bandeja", self); act_hide.triggered.connect(self.hide_to_tray); file_menu.addAction(act_hide)
        act_exit = QAction("Sair", self); act_exit.triggered.connect(self.quit_application); file_menu.addAction(act_exit)

    def setup_tray_icon(self):
        self.tray_icon = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        self.tray_icon.setToolTip(APP_NAME)
        tray_menu = QMenu(self)
        tray_menu.addAction("Abrir painel", self.show_window_from_tray)
        tray_menu.addAction("Iniciar monitoramento", self.start_all_monitors)
        tray_menu.addAction("Parar monitoramento", self.stop_all_monitors)
        tray_menu.addSeparator()
        tray_menu.addAction("Sair", self.quit_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.show_window_from_tray()

    def show_window_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self):
        if self.tray_icon is None:
            return
        self.hide()
        if not self._tray_message_shown:
            self.tray_icon.showMessage(APP_NAME, "O monitoramento continua em segundo plano na bandeja do sistema.", QSystemTrayIcon.Information, 3000)
            self._tray_message_shown = True

    def quit_application(self):
        self._allow_close = True
        self.close()

    def build_dashboard_tab(self):
        layout = QVBoxLayout(self.tab_dashboard); top = QHBoxLayout()
        self.lbl_total = QLabel("0"); self.lbl_today = QLabel("0"); self.lbl_overspeed = QLabel("0"); self.lbl_last_plate = QLabel("-")
        for title, widget in [("Total de eventos", self.lbl_total), ("Eventos hoje", self.lbl_today), ("Acima do limite", self.lbl_overspeed), ("Ultima placa", self.lbl_last_plate)]:
            box = QGroupBox(title); vb = QVBoxLayout(box); widget.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;"); vb.addWidget(widget); top.addWidget(box)
        layout.addLayout(top)
        log_box = QGroupBox("Atividade do sistema")
        log_layout = QVBoxLayout(log_box)
        self.dashboard_log = QTextEdit(); self.dashboard_log.setReadOnly(True); self.dashboard_log.setMinimumHeight(320); log_layout.addWidget(self.dashboard_log)
        layout.addWidget(log_box)

    def build_cameras_tab(self):
        layout = QVBoxLayout(self.tab_cameras); splitter = QSplitter(Qt.Horizontal); splitter.setChildrenCollapsible(False)
        left_panel = QGroupBox("Cameras cadastradas"); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(10,10,10,10)
        self.camera_list = QListWidget(); self.camera_list.currentTextChanged.connect(self.load_selected_camera); left_layout.addWidget(self.camera_list)

        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel); right_layout.setContentsMargins(0,0,0,0)
        form_box = QGroupBox("Configuracao da camera"); form = QFormLayout(form_box)
        self.cam_name = QLineEdit(); self.cam_ip = QLineEdit(); self.cam_port = QSpinBox(); self.cam_port.setRange(1,65535); self.cam_port.setValue(80)
        self.cam_user = QLineEdit(); self.cam_pass = PasswordField()
        self.cam_channel = QSpinBox(); self.cam_channel.setRange(1,999); self.cam_channel.setValue(101)
        self.cam_timeout = QSpinBox(); self.cam_timeout.setRange(1,120); self.cam_timeout.setValue(15)
        self.cam_rtsp_enabled = QCheckBox("Habilitar video ao vivo (RTSP)"); self.cam_rtsp_enabled.setChecked(True)
        self.cam_rtsp_port = QSpinBox(); self.cam_rtsp_port.setRange(1,65535); self.cam_rtsp_port.setValue(554)
        self.cam_rtsp_transport = QComboBox(); self.cam_rtsp_transport.addItems(["tcp", "udp"])
        self.cam_rtsp_url = QLineEdit()
        self.cam_live_fallback = QComboBox(); self.cam_live_fallback.addItems(["snapshot", "none"])
        self.cam_speed_limit_enabled = QCheckBox("Habilitar aviso de velocidade"); self.cam_speed_limit_enabled.setChecked(True)
        self.cam_speed_limit = QSpinBox(); self.cam_speed_limit.setRange(1,300); self.cam_speed_limit.setValue(int(self.config.data.get("speed_limit", 60)))
        self.cam_speed_alert_visual = QCheckBox("Mostrar aviso visual na tela"); self.cam_speed_alert_visual.setChecked(True)
        self.cam_evolution_enabled = QCheckBox("Enviar excesso pela Evolution API")
        self.cam_output = QLineEdit(); self.cam_enabled = QCheckBox("Ativa para monitoramento"); self.cam_snapshot = QCheckBox("Salvar snapshot automatico por evento")
        self.cam_mode = QComboBox(); self.cam_mode.addItems(["auto", "traffic", "normal"])
        browse = QPushButton("Escolher pasta"); browse.clicked.connect(self.choose_output_dir)
        out_wrap = QWidget(); out_row = QHBoxLayout(out_wrap); out_row.setContentsMargins(0,0,0,0); out_row.addWidget(self.cam_output,1); out_row.addWidget(browse,0)
        form.addRow("Nome:", self.cam_name); form.addRow("IP:", self.cam_ip); form.addRow("Porta HTTP:", self.cam_port); form.addRow("Usuario:", self.cam_user)
        form.addRow("Senha:", self.cam_pass); form.addRow("Canal:", self.cam_channel); form.addRow("Timeout:", self.cam_timeout); form.addRow("Modo da camera:", self.cam_mode)
        form.addRow("", self.cam_rtsp_enabled); form.addRow("Porta RTSP:", self.cam_rtsp_port); form.addRow("Preferencia RTSP:", self.cam_rtsp_transport); form.addRow("URL RTSP:", self.cam_rtsp_url); form.addRow("Fallback live:", self.cam_live_fallback)
        form.addRow("", self.cam_speed_limit_enabled); form.addRow("Limite veloc. (km/h):", self.cam_speed_limit); form.addRow("", self.cam_speed_alert_visual)
        form.addRow("", self.cam_evolution_enabled)
        form.addRow("Pasta:", out_wrap); form.addRow("", self.cam_enabled); form.addRow("", self.cam_snapshot)
        right_layout.addWidget(form_box)
        note = QLabel("Para iDS-TCM403-GIR, use 'traffic' ou 'auto'. Video ao vivo usa RTSP embutido; se o player falhar, o app pode cair para snapshots ao vivo. Esta versão usa apenas o alertStream padrão /ISAPI/Event/notification/alertStream para eventos."); note.setWordWrap(True); note.setStyleSheet("padding: 8px; border: 1px solid #d7dee6; background: #f7fafc; border-radius: 6px; color: #486581;"); right_layout.addWidget(note)
        btns_wrap = QWidget(); btns = QHBoxLayout(btns_wrap); btns.setContentsMargins(0,0,0,0)
        for text, slot in [("Nova camera", self.new_camera), ("Salvar camera", self.save_camera), ("Excluir camera", self.delete_camera), ("Testar conexao", self.test_camera_connection), ("Snapshot manual", self.manual_snapshot)]:
            b = QPushButton(text); b.clicked.connect(slot); btns.addWidget(b)
        btns.addStretch(1); right_layout.addWidget(btns_wrap); right_layout.addStretch(1)
        splitter.addWidget(left_panel); splitter.addWidget(right_panel); splitter.setStretchFactor(0,1); splitter.setStretchFactor(1,3); layout.addWidget(splitter)

    def build_monitor_tab(self):
        layout = QVBoxLayout(self.tab_monitor)
        layout.setSpacing(10)

        toolbar_box = QGroupBox("Controle de monitoramento")
        toolbar = QHBoxLayout(toolbar_box)
        toolbar.setContentsMargins(10, 8, 10, 8)
        self.live_camera_combo = QComboBox(); self.live_camera_combo.currentTextChanged.connect(self.on_live_camera_changed)
        self.live_status = QLabel("Video ao vivo parado")
        self.live_status.setStyleSheet("padding: 4px 8px; border: 1px solid #c9d2dc; background: #f4f7fa; color: #243447; border-radius: 4px;")
        btn_live_start = QPushButton("Iniciar video"); btn_live_start.clicked.connect(self.start_live_view)
        btn_live_stop = QPushButton("Parar video"); btn_live_stop.clicked.connect(self.stop_live_view)
        btn_start = QPushButton("Iniciar todas"); btn_start.clicked.connect(self.start_all_monitors)
        btn_stop = QPushButton("Parar todas"); btn_stop.clicked.connect(self.stop_all_monitors)
        self.monitor_count_summary = QLabel("Online: 0 | Offline: 0")
        self.monitor_count_summary.setStyleSheet("padding: 4px 8px; border: 1px solid #d7dee6; background: #ffffff; color: #243447; border-radius: 4px;")
        toolbar.addWidget(QLabel("Camera ao vivo"))
        toolbar.addWidget(self.live_camera_combo, 1)
        toolbar.addWidget(btn_live_start)
        toolbar.addWidget(btn_live_stop)
        toolbar.addSpacing(12)
        toolbar.addWidget(btn_start)
        toolbar.addWidget(btn_stop)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.monitor_count_summary)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.live_status, 1)
        layout.addWidget(toolbar_box)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setChildrenCollapsible(False)

        live_panel = QGroupBox("Visualizacao ao vivo")
        live_layout = QVBoxLayout(live_panel)
        live_layout.setContentsMargins(10, 10, 10, 10)
        self.live_view = LiveViewController(); self.live_view.status_changed.connect(self.on_live_view_status_changed)
        self.live_view.setMinimumHeight(420)
        live_layout.addWidget(self.live_view, 1)

        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)

        right_box = QGroupBox("Ultimo evento")
        right_layout = QHBoxLayout(right_box)
        form_wrap = QWidget()
        form = QFormLayout(form_wrap)
        self.lbl_cam = QLabel("-"); self.lbl_plate = QLabel("-"); self.lbl_speed = QLabel("-"); self.lbl_lane = QLabel("-"); self.lbl_direction = QLabel("-"); self.lbl_type = QLabel("-"); self.lbl_image_status = QLabel("-")
        self.lbl_cam.setStyleSheet("font-weight: 600; color: #1f2d3d;")
        self.lbl_plate.setStyleSheet("font-weight: 700; font-size: 18px; color: #0f4c5c;")
        self.lbl_speed.setStyleSheet("font-weight: 700; font-size: 18px; color: #8a3b12;")
        self.lbl_image_status.setWordWrap(True)
        form.addRow("Camera:", self.lbl_cam); form.addRow("Placa:", self.lbl_plate); form.addRow("Velocidade:", self.lbl_speed); form.addRow("Faixa:", self.lbl_lane); form.addRow("Direcao:", self.lbl_direction); form.addRow("Tipo:", self.lbl_type); form.addRow("Imagem:", self.lbl_image_status)
        self.monitor_alert = QLabel("Sem alerta de velocidade")
        self.monitor_alert.setWordWrap(True)
        self.monitor_alert.setMinimumHeight(78)
        self.monitor_alert.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.monitor_alert.setStyleSheet("padding: 10px; border: 1px solid #c9d2dc; background: #f4f7fa; color: #243447; border-radius: 6px;")
        form.addRow("Aviso:", self.monitor_alert)
        self.monitor_thumbnail = QLabel("Sem imagem")
        self.monitor_thumbnail.setAlignment(Qt.AlignCenter)
        self.monitor_thumbnail.setMinimumSize(180, 120)
        self.monitor_thumbnail.setStyleSheet("border: 1px solid #d7dee6; background: #fbfcfd; color: #687785;")
        right_layout.addWidget(form_wrap, 2)
        right_layout.addWidget(self.monitor_thumbnail, 1)

        state_box = QGroupBox("Estado das cameras")
        state_layout = QVBoxLayout(state_box)
        state_layout.setContentsMargins(10, 10, 10, 10)
        self.monitor_states = QTextEdit()
        self.monitor_states.setReadOnly(True)
        self.monitor_states.setMinimumWidth(320)
        self.monitor_states.setStyleSheet("background: #fbfcfd; border: 1px solid #d7dee6; color: #243447;")
        state_layout.addWidget(self.monitor_states)

        activity_box = QGroupBox("Atividade")
        activity_layout = QVBoxLayout(activity_box)
        activity_layout.setContentsMargins(10, 10, 10, 10)
        self.monitor_log = QTextEdit()
        self.monitor_log.setReadOnly(True)
        self.monitor_log.setMinimumHeight(140)
        self.monitor_log.setStyleSheet("background: white; border: 1px solid #d7dee6; color: #243447;")
        activity_layout.addWidget(self.monitor_log)

        side_layout.addWidget(right_box)
        side_layout.addWidget(state_box, 1)
        side_layout.addWidget(activity_box, 1)

        body_splitter.addWidget(live_panel)
        body_splitter.addWidget(side_panel)
        body_splitter.setStretchFactor(0, 5)
        body_splitter.setStretchFactor(1, 3)
        layout.addWidget(body_splitter, 3)

        table_box = QGroupBox("Eventos recentes")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_filter = QHBoxLayout()
        self.realtime_filter_camera = QComboBox()
        self.realtime_filter_camera.addItem("")
        self.realtime_filter_camera.currentTextChanged.connect(self.apply_realtime_filter)
        table_filter.addWidget(QLabel("Filtrar camera"))
        table_filter.addWidget(self.realtime_filter_camera)
        table_filter.addStretch(1)
        table_layout.addLayout(table_filter)
        self.realtime_table = QTableWidget(0,6)
        self.realtime_table.setHorizontalHeaderLabels(["Camera","Data/Hora","Placa","Velocidade","Faixa","Tipo"])
        self.style_data_table(self.realtime_table)
        self.realtime_table.cellDoubleClicked.connect(self.open_realtime_event_image)
        table_layout.addWidget(self.realtime_table)
        layout.addWidget(table_box, 2)

    def build_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        filters_box = QGroupBox("Filtros"); filters_layout = QHBoxLayout(filters_box)
        self.hist_camera = QComboBox(); self.hist_camera.addItem(""); self.hist_plate = QLineEdit(); self.hist_date = QLineEdit(); self.hist_min_speed = QLineEdit()
        btn_filter = QPushButton("Filtrar"); btn_filter.clicked.connect(self.refresh_history)
        for widget in [QLabel("Camera"), self.hist_camera, QLabel("Placa"), self.hist_plate, QLabel("Data"), self.hist_date, QLabel("Veloc. min."), self.hist_min_speed, btn_filter]:
            filters_layout.addWidget(widget)
        layout.addWidget(filters_box)
        self.history_table = QTableWidget(0,9); self.history_table.setHorizontalHeaderLabels(["Camera","Data/Hora","Placa","Velocidade","Faixa","Direcao","Tipo","Imagem","JSON"]); self.style_data_table(self.history_table); self.history_table.cellDoubleClicked.connect(self.open_history_item); layout.addWidget(self.history_table)

    def build_report_tab(self):
        layout = QVBoxLayout(self.tab_report)
        top_box = QGroupBox("Parametros do relatorio"); top = QHBoxLayout(top_box)
        self.speed_limit_spin = QSpinBox(); self.speed_limit_spin.setRange(1,300); self.speed_limit_spin.setValue(int(self.config.data.get("speed_limit", 60)))
        self.report_camera = QComboBox(); self.report_camera.addItem(""); self.report_date = QLineEdit()
        btn_apply = QPushButton("Aplicar"); btn_apply.clicked.connect(self.apply_speed_limit_and_refresh_report)
        btn_export = QPushButton("Exportar CSV"); btn_export.clicked.connect(self.export_overspeed_csv)
        for widget in [QLabel("Limite (km/h)"), self.speed_limit_spin, QLabel("Camera"), self.report_camera, QLabel("Data"), self.report_date, btn_apply, btn_export]:
            top.addWidget(widget)
        top.addStretch(1); layout.addWidget(top_box)
        summary_box = QGroupBox("Resumo")
        summary_layout = QVBoxLayout(summary_box)
        self.report_summary = QLabel("-"); self.report_summary.setWordWrap(True); self.report_summary.setStyleSheet("font-weight: 600; color: #486581;"); summary_layout.addWidget(self.report_summary); layout.addWidget(summary_box)
        self.report_table = QTableWidget(0,9); self.report_table.setHorizontalHeaderLabels(["Camera","Data/Hora","Placa","Velocidade","Faixa","Direcao","Tipo","Imagem","JSON"]); self.style_data_table(self.report_table); self.report_table.cellDoubleClicked.connect(self.open_report_item); layout.addWidget(self.report_table)

    def build_evolution_tab(self):
        layout = QVBoxLayout(self.tab_evolution)
        layout.setSpacing(8)
        evo_tabs = QTabWidget()
        evo_tabs.setDocumentMode(True)
        tab_config = QWidget()
        tab_instance = QWidget()
        tab_template = QWidget()
        evo_tabs.addTab(tab_config, "Configuracao")
        evo_tabs.addTab(tab_instance, "Instancia e teste")
        evo_tabs.addTab(tab_template, "Template")

        config_layout = QVBoxLayout(tab_config)
        config_layout.setContentsMargins(0, 0, 0, 0)
        instance_layout_root = QVBoxLayout(tab_instance)
        instance_layout_root.setContentsMargins(0, 0, 0, 0)
        template_root_layout = QVBoxLayout(tab_template)
        template_root_layout.setContentsMargins(0, 0, 0, 0)

        form_box = QGroupBox("Configuracao da Evolution API")
        form = QFormLayout(form_box)
        form.setContentsMargins(10, 8, 10, 10)
        form.setVerticalSpacing(6)
        self.evo_enabled = QCheckBox("Habilitar integracao Evolution API")
        self.evo_url = QLineEdit()
        self.evo_token = PasswordField()
        self.evo_instance = QLineEdit()
        self.evo_mode = QComboBox(); self.evo_mode.addItems(["create_or_connect", "existing"])
        self.evo_recipients = QTextEdit(); self.evo_recipients.setPlaceholderText("5511999999999\n5511888888888"); self.evo_recipients.setMaximumHeight(90)
        self.evo_send_image = QCheckBox("Enviar imagem com legenda"); self.evo_send_image.setChecked(True)
        form.addRow("", self.evo_enabled)
        form.addRow("URL:", self.evo_url)
        form.addRow("Token:", self.evo_token)
        form.addRow("Instancia:", self.evo_instance)
        form.addRow("Modo:", self.evo_mode)
        form.addRow("Numeros:", self.evo_recipients)
        form.addRow("", self.evo_send_image)
        config_layout.addWidget(form_box)

        btns_wrap = QWidget()
        btns = QHBoxLayout(btns_wrap)
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(6)
        for text, slot in [("Salvar", self.save_evolution_settings), ("Testar API", self.test_evolution_connection), ("Conectar instancia", self.connect_evolution_instance), ("Atualizar QR", self.refresh_evolution_qr)]:
            button = QPushButton(text)
            button.setMinimumWidth(120)
            button.setMaximumWidth(150)
            button.clicked.connect(slot)
            btns.addWidget(button)
        btns.addStretch(1)
        config_layout.addWidget(btns_wrap)
        config_layout.addStretch(1)

        details_splitter = QSplitter(Qt.Horizontal)
        details_splitter.setChildrenCollapsible(False)

        status_box = QGroupBox("Status da instancia")
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(10, 8, 10, 10)
        status_layout.setSpacing(6)
        self.evo_status = QLabel("Evolution API nao configurada.")
        self.evo_status.setWordWrap(True)
        self.evo_qr_label = QLabel("QR Code indisponivel")
        self.evo_qr_label.setAlignment(Qt.AlignCenter)
        self.evo_qr_label.setMinimumHeight(150)
        self.evo_qr_label.setMaximumHeight(180)
        self.evo_qr_label.setStyleSheet("border: 1px solid #d7dee6; background: #fbfcfd; color: #687785;")
        status_layout.addWidget(self.evo_status)
        status_layout.addWidget(self.evo_qr_label)

        test_box = QGroupBox("Mensagem de teste")
        test_form = QFormLayout(test_box)
        test_form.setContentsMargins(10, 8, 10, 10)
        test_form.setVerticalSpacing(6)
        self.evo_test_number = QLineEdit()
        self.evo_test_message = QTextEdit()
        self.evo_test_message.setMinimumHeight(72)
        self.evo_test_message.setMaximumHeight(96)
        self.evo_test_message.setPlaceholderText("Mensagem de teste da Evolution API")
        btn_send_test = QPushButton("Enviar teste")
        btn_send_test.setMaximumWidth(120)
        btn_send_test.clicked.connect(self.send_evolution_test_message)
        test_form.addRow("Numero:", self.evo_test_number)
        test_form.addRow("Mensagem:", self.evo_test_message)
        test_form.addRow("", btn_send_test)
        details_splitter.addWidget(status_box)
        details_splitter.addWidget(test_box)
        details_splitter.setStretchFactor(0, 3)
        details_splitter.setStretchFactor(1, 2)
        instance_layout_root.addWidget(details_splitter, 1)

        template_box = QGroupBox("Template dos eventos")
        template_layout = QVBoxLayout(template_box)
        template_layout.setContentsMargins(10, 8, 10, 10)
        template_layout.setSpacing(6)
        self.evo_event_template = QTextEdit()
        self.evo_event_template.setMinimumHeight(110)
        self.evo_event_template.setMaximumHeight(160)
        self.evo_event_template.setPlaceholderText("Use variaveis como {camera}, {plate}, {speed}, {limit}, {ts}, {lane}, {direction}, {event_type}")
        self.evo_event_template.textChanged.connect(self.update_evolution_template_preview)
        variable_wrap = QWidget()
        variable_row = QHBoxLayout(variable_wrap)
        variable_row.setContentsMargins(0, 0, 0, 0)
        variable_row.setSpacing(4)
        for variable in ["{camera}", "{plate}", "{speed}", "{limit}", "{ts}", "{lane}", "{direction}", "{event_type}"]:
            button = QPushButton(variable)
            button.setMaximumWidth(92)
            button.clicked.connect(lambda _checked=False, value=variable: self.insert_evolution_template_variable(value))
            variable_row.addWidget(button)
        variable_row.addStretch(1)
        template_help = QLabel("Variaveis disponiveis: {camera}, {plate}, {speed}, {limit}, {ts}, {lane}, {direction}, {event_type}")
        template_help.setWordWrap(True)
        preview_box = QGroupBox("Preview da mensagem")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(10, 8, 10, 10)
        self.evo_template_preview = QTextEdit()
        self.evo_template_preview.setReadOnly(True)
        self.evo_template_preview.setMinimumHeight(110)
        self.evo_template_preview.setMaximumHeight(160)
        preview_layout.addWidget(self.evo_template_preview)
        template_splitter = QSplitter(Qt.Horizontal)
        template_splitter.setChildrenCollapsible(False)
        template_editor_wrap = QWidget()
        template_editor_layout = QVBoxLayout(template_editor_wrap)
        template_editor_layout.setContentsMargins(0, 0, 0, 0)
        template_editor_layout.setSpacing(6)
        template_editor_layout.addWidget(self.evo_event_template)
        template_editor_layout.addWidget(variable_wrap)
        template_splitter.addWidget(template_editor_wrap)
        template_splitter.addWidget(preview_box)
        template_splitter.setStretchFactor(0, 3)
        template_splitter.setStretchFactor(1, 2)
        template_layout.addWidget(template_splitter)
        template_layout.addWidget(template_help)
        template_root_layout.addWidget(template_box)
        template_root_layout.addStretch(1)
        layout.addWidget(evo_tabs)
        self.load_evolution_settings_into_ui()

    def build_users_tab(self):
        layout = QVBoxLayout(self.tab_users)
        if self.logged_user.get("role") != "Administrador":
            msg = QLabel("Somente administradores podem gerenciar usuarios."); msg.setWordWrap(True); layout.addWidget(msg); layout.addStretch(1); return
        splitter = QSplitter(Qt.Horizontal); self.user_list = QListWidget(); self.user_list.currentTextChanged.connect(self.load_selected_user)
        self.user_list.setMinimumWidth(220)
        box = QGroupBox("Cadastro de usuario"); form = QFormLayout(box); self.sys_user = QLineEdit(); self.sys_pass = PasswordField(); self.sys_role = QComboBox(); self.sys_role.addItems(["Administrador", "Operador"])
        form.addRow("Usuario:", self.sys_user); form.addRow("Senha:", self.sys_pass); form.addRow("Perfil:", self.sys_role)
        splitter.addWidget(self.user_list); splitter.addWidget(box); layout.addWidget(splitter)
        btns_wrap = QWidget(); btns = QHBoxLayout(btns_wrap); btns.setContentsMargins(0,0,0,0)
        for text, slot in [("Novo usuario", self.new_user), ("Salvar usuario", self.save_user), ("Excluir usuario", self.delete_user)]:
            b = QPushButton(text); b.clicked.connect(slot); btns.addWidget(b)
        btns.addStretch(1); layout.addWidget(btns_wrap); layout.addStretch(1); self.reload_user_list()

    def append_log(self, text):
        stamp = now_str()
        line = f"[{stamp}] {text}"
        self.dashboard_log.append(line)
        if hasattr(self, "monitor_log"):
            self.monitor_log.append(line)

    def reload_camera_lists(self):
        names = self.config.get_camera_names()
        self.camera_list.clear()
        for name in names: self.camera_list.addItem(QListWidgetItem(name))
        if names: self.camera_list.setCurrentRow(0)
        self.hist_camera.clear(); self.hist_camera.addItem(""); self.hist_camera.addItems(names)
        self.report_camera.clear(); self.report_camera.addItem(""); self.report_camera.addItems(names)
        if hasattr(self, "live_camera_combo"):
            selected = self.live_camera_combo.currentText().strip()
            self.live_camera_combo.blockSignals(True)
            self.live_camera_combo.clear(); self.live_camera_combo.addItems(names)
            if selected and selected in names:
                self.live_camera_combo.setCurrentText(selected)
            elif names:
                self.live_camera_combo.setCurrentIndex(0)
            self.live_camera_combo.blockSignals(False)
            self.on_live_camera_changed(self.live_camera_combo.currentText())
        if hasattr(self, "realtime_filter_camera"):
            selected_filter = self.realtime_filter_camera.currentText().strip()
            self.realtime_filter_camera.blockSignals(True)
            self.realtime_filter_camera.clear()
            self.realtime_filter_camera.addItem("")
            self.realtime_filter_camera.addItems(names)
            if selected_filter and selected_filter in names:
                self.realtime_filter_camera.setCurrentText(selected_filter)
            self.realtime_filter_camera.blockSignals(False)
            self.apply_realtime_filter()
        if hasattr(self, "evo_status"):
            self.update_evolution_status_label()

    def load_selected_camera(self, name):
        cam = self.config.get_camera(name)
        if not cam: return
        self.cam_name.setText(cam.get("name", "")); self.cam_ip.setText(cam.get("camera_ip", "")); self.cam_port.setValue(int(cam.get("camera_port", 80)))
        self.cam_user.setText(cam.get("camera_user", "")); self.cam_pass.setText(cam.get("camera_pass", "")); self.cam_channel.setValue(int(cam.get("channel", 101))); self.cam_timeout.setValue(int(cam.get("timeout", 15)))
        self.cam_rtsp_enabled.setChecked(bool(cam.get("rtsp_enabled", True))); self.cam_rtsp_port.setValue(int(cam.get("rtsp_port", 554))); self.cam_rtsp_url.setText(cam.get("rtsp_url", "")); self.cam_live_fallback.setCurrentText(cam.get("live_fallback_mode", "snapshot"))
        self.cam_speed_limit_enabled.setChecked(bool(cam.get("speed_limit_enabled", True))); self.cam_speed_limit.setValue(int(cam.get("speed_limit_value", self.config.data.get("speed_limit", 60)))); self.cam_speed_alert_visual.setChecked(bool(cam.get("speed_alert_visual", True)))
        self.cam_evolution_enabled.setChecked(bool(cam.get("evolution_enabled", False)))
        rtsp_transport = cam.get("rtsp_transport", "tcp"); transport_idx = self.cam_rtsp_transport.findText(rtsp_transport); self.cam_rtsp_transport.setCurrentIndex(max(transport_idx, 0))
        self.cam_output.setText(cam.get("output_dir", str(app_dir() / "output"))); self.cam_enabled.setChecked(bool(cam.get("enabled", True))); self.cam_snapshot.setChecked(bool(cam.get("save_snapshot_on_event", True)))
        mode = cam.get("camera_mode", "auto"); idx = self.cam_mode.findText(mode); self.cam_mode.setCurrentIndex(max(idx, 0))

    def current_camera_form(self):
        return {"name": self.cam_name.text().strip() or "Camera", "enabled": self.cam_enabled.isChecked(), "camera_ip": self.cam_ip.text().strip(), "camera_port": int(self.cam_port.value()), "camera_user": self.cam_user.text().strip(), "camera_pass": self.cam_pass.text(), "channel": int(self.cam_channel.value()), "timeout": int(self.cam_timeout.value()), "rtsp_enabled": self.cam_rtsp_enabled.isChecked(), "rtsp_port": int(self.cam_rtsp_port.value()), "rtsp_transport": self.cam_rtsp_transport.currentText(), "rtsp_url": self.cam_rtsp_url.text().strip(), "live_fallback_mode": self.cam_live_fallback.currentText(), "speed_limit_enabled": self.cam_speed_limit_enabled.isChecked(), "speed_limit_value": int(self.cam_speed_limit.value()), "speed_alert_visual": self.cam_speed_alert_visual.isChecked(), "evolution_enabled": self.cam_evolution_enabled.isChecked(), "output_dir": self.cam_output.text().strip() or str(app_dir() / "output"), "save_snapshot_on_event": self.cam_snapshot.isChecked(), "camera_mode": self.cam_mode.currentText()}

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder: self.cam_output.setText(folder)

    def new_camera(self):
        self.cam_name.setText(f"Camera {len(self.config.get_camera_names()) + 1}"); self.cam_ip.clear(); self.cam_user.clear(); self.cam_pass.clear(); self.cam_rtsp_enabled.setChecked(True); self.cam_rtsp_port.setValue(554); self.cam_rtsp_transport.setCurrentText("tcp"); self.cam_rtsp_url.clear(); self.cam_live_fallback.setCurrentText("snapshot"); self.cam_speed_limit_enabled.setChecked(True); self.cam_speed_limit.setValue(int(self.config.data.get("speed_limit", 60))); self.cam_speed_alert_visual.setChecked(True); self.cam_evolution_enabled.setChecked(False); self.cam_output.setText(str(app_dir() / "output")); self.cam_enabled.setChecked(True); self.cam_snapshot.setChecked(True); self.cam_mode.setCurrentText("auto")

    def save_camera(self):
        cam = self.current_camera_form(); Path(cam["output_dir"]).mkdir(parents=True, exist_ok=True); self.config.upsert_camera(cam); self.config.save(); self.reload_camera_lists(); QMessageBox.information(self, APP_NAME, "Camera salva com sucesso.")
        if self.live_camera_combo.currentText().strip() == cam["name"]:
            self.on_live_camera_changed(cam["name"])

    def delete_camera(self):
        name = self.cam_name.text().strip()
        if not name: return
        if self.live_camera_combo.currentText().strip() == name:
            self.stop_live_view()
        self.config.delete_camera(name); self.config.save(); self.reload_camera_lists(); self.new_camera(); QMessageBox.information(self, APP_NAME, "Camera removida.")

    def test_camera_connection(self):
        try:
            ok, status, detail = CameraClient(self.current_camera_form()).test_connection()
            if ok: QMessageBox.information(self, APP_NAME, f"Conexao OK\nHTTP {status}\nDetalhe: {detail}")
            else: QMessageBox.warning(self, APP_NAME, f"Falha HTTP {status}\nDetalhe: {detail}")
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, str(e))

    def manual_snapshot(self):
        try:
            cam = self.current_camera_form(); img, used_url = CameraClient(cam).download_snapshot(); out = Path(cam["output_dir"]) / "manual"; out.mkdir(parents=True, exist_ok=True); file = out / f"{cam['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"; file.write_bytes(img); self.set_preview(str(file)); QMessageBox.information(self, APP_NAME, f"Snapshot salvo em:\n{file}\nURL: {used_url}")
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Snapshot nao suportado nesse firmware.\n\nDetalhe:\n{e}")

    def start_all_monitors(self):
        self.stop_all_monitors(log_message=False); started = 0
        for cam in self.config.data.get("cameras", []):
            if not cam.get("enabled", True): continue
            worker = EventWorker(cam); worker.status.connect(self.append_log); worker.connection_state.connect(self.on_connection_state); worker.event_received.connect(self.on_event_received); self.workers[cam["name"]] = worker; worker.start(); started += 1
        self.append_log(f"Monitoramento iniciado para {started} camera(s).")

    def stop_all_monitors(self, log_message=True):
        for _, worker in list(self.workers.items()): worker.stop(); worker.wait(3000)
        self.workers = {}; self.camera_states = {}; self.update_camera_state_panel()
        if log_message: self.append_log("Todos os monitores foram parados.")

    def on_connection_state(self, camera_name, connected, detail):
        self.camera_states[camera_name] = (connected, detail); self.update_camera_state_panel()

    def update_camera_state_panel(self):
        cards = []
        online = 0
        offline = 0
        for cam in self.config.data.get("cameras", []):
            name = cam.get("name", "Camera")
            connected, detail = self.camera_states.get(name, (False, "sem conexão"))
            if connected:
                online += 1
            else:
                offline += 1
            badge_bg = "#e7f6ec" if connected else "#fdecec"
            badge_fg = "#1d6b3a" if connected else "#9c2f2f"
            badge_text = "Conectada" if connected else "Desconectada"
            cards.append(
                f"<div style='margin:0 0 8px 0; padding:8px 10px; border:1px solid #d7dee6; border-radius:6px; background:#ffffff;'>"
                f"<div style='font-weight:600; color:#1f2d3d; margin-bottom:4px;'>{name}</div>"
                f"<span style='display:inline-block; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:{badge_fg}; font-weight:600;'>{badge_text}</span>"
                f"<div style='margin-top:6px; color:#4b5b6b;'>{detail}</div>"
                f"</div>"
            )
        self.monitor_states.setHtml("".join(cards) if cards else "<div style='color:#4b5b6b;'>Sem câmeras configuradas.</div>")
        if hasattr(self, "monitor_count_summary"):
            self.monitor_count_summary.setText(f"Online: {online} | Offline: {offline}")

    def on_live_camera_changed(self, name):
        cam = self.config.get_camera(name) if name else None
        self.live_view.set_camera(cam)
        if not cam:
            self.live_status.setText("Video ao vivo parado")
            return
        if self.live_view_running:
            self.start_live_view()

    def start_live_view(self):
        name = self.live_camera_combo.currentText().strip()
        cam = self.config.get_camera(name) if name else None
        self.live_view.set_camera(cam)
        self.live_view_running = bool(cam)
        if cam:
            self.live_view.start()
        else:
            self.live_status.setText("Selecione uma camera para video ao vivo")

    def stop_live_view(self):
        self.live_view_running = False
        self.live_view.stop()
        self.live_status.setText("Video ao vivo parado")

    def on_live_view_status_changed(self, text):
        self.live_status.setText(text)

    def current_evolution_form(self) -> dict:
        return {
            "enabled": self.evo_enabled.isChecked(),
            "base_url": self.evo_url.text().strip(),
            "api_token": self.evo_token.text().strip(),
            "instance_name": self.evo_instance.text().strip(),
            "instance_mode": self.evo_mode.currentText(),
            "recipient_numbers": parse_recipient_numbers(self.evo_recipients.toPlainText()),
            "send_image_with_caption": self.evo_send_image.isChecked(),
            "test_target_number": sanitize_phone_number(self.evo_test_number.text()),
            "test_message_text": self.evo_test_message.toPlainText(),
            "event_message_template": self.evo_event_template.toPlainText(),
        }

    def load_evolution_settings_into_ui(self):
        cfg = self.config.data.get("evolution_api", {})
        self.evo_enabled.setChecked(bool(cfg.get("enabled", False)))
        self.evo_url.setText(cfg.get("base_url", ""))
        self.evo_token.setText(cfg.get("api_token", ""))
        self.evo_instance.setText(cfg.get("instance_name", ""))
        mode = cfg.get("instance_mode", "create_or_connect")
        idx = self.evo_mode.findText(mode)
        self.evo_mode.setCurrentIndex(max(idx, 0))
        self.evo_recipients.setPlainText("\n".join(cfg.get("recipient_numbers", [])))
        self.evo_send_image.setChecked(bool(cfg.get("send_image_with_caption", True)))
        self.evo_test_number.setText(cfg.get("test_target_number", ""))
        self.evo_test_message.setPlainText(cfg.get("test_message_text", ""))
        self.evo_event_template.setPlainText(cfg.get("event_message_template", ""))
        self.update_evolution_status_label()
        self.update_evolution_template_preview()

    def update_evolution_status_label(self, extra_text: str = ""):
        cfg = self.config.data.get("evolution_api", {})
        recipients = cfg.get("recipient_numbers", [])
        style = "padding: 8px; border: 1px solid #d7dee6; background: #fbfcfd; color: #425466; border-radius: 6px;"
        if extra_text:
            self.evo_status.setText(extra_text)
            extra_lower = extra_text.lower()
            if "validada" in extra_lower or "conectada" in extra_lower or "pronta" in extra_lower:
                style = "padding: 8px; border: 1px solid #b8dfc5; background: #eefaf2; color: #1d6b3a; border-radius: 6px; font-weight: 600;"
            elif "qr" in extra_lower:
                style = "padding: 8px; border: 1px solid #e6d39b; background: #fff8e1; color: #8a6d1a; border-radius: 6px; font-weight: 600;"
            elif "falha" in extra_lower or "erro" in extra_lower:
                style = "padding: 8px; border: 1px solid #e2b4b4; background: #fdecec; color: #9c2f2f; border-radius: 6px; font-weight: 600;"
            self.evo_status.setStyleSheet(style)
            return
        enabled_text = "habilitada" if cfg.get("enabled") else "desabilitada"
        self.evo_status.setText(
            f"Integracao {enabled_text} | Instancia: {cfg.get('instance_name') or '-'} | "
            f"Destinatarios: {len(recipients)}"
        )
        if cfg.get("enabled"):
            style = "padding: 8px; border: 1px solid #d7dee6; background: #f4f7fa; color: #243447; border-radius: 6px; font-weight: 600;"
        self.evo_status.setStyleSheet(style)

    def evolution_preview_data(self) -> dict:
        return {
            "camera_name": self.lbl_cam.text().strip() if hasattr(self, "lbl_cam") and self.lbl_cam.text().strip() not in ("", "-") else "Camera 1",
            "plate": self.lbl_plate.text().strip() if hasattr(self, "lbl_plate") and self.lbl_plate.text().strip() not in ("", "-") else "ABC1D23",
            "speed": self.lbl_speed.text().strip() if hasattr(self, "lbl_speed") and self.lbl_speed.text().strip() not in ("", "-") else "72",
            "applied_speed_limit": 60.0,
            "ts": now_str(),
            "lane": self.lbl_lane.text().strip() if hasattr(self, "lbl_lane") and self.lbl_lane.text().strip() not in ("", "-") else "1",
            "direction": self.lbl_direction.text().strip() if hasattr(self, "lbl_direction") and self.lbl_direction.text().strip() not in ("", "-") else "Frente",
            "event_type": self.lbl_type.text().strip() if hasattr(self, "lbl_type") and self.lbl_type.text().strip() not in ("", "-") else "ANPR",
        }

    def update_evolution_template_preview(self):
        if not hasattr(self, "evo_template_preview"):
            return
        template = self.evo_event_template.toPlainText() if hasattr(self, "evo_event_template") else ""
        self.evo_template_preview.setPlainText(render_event_message(template, self.evolution_preview_data()))

    def insert_evolution_template_variable(self, variable: str):
        cursor = self.evo_event_template.textCursor()
        cursor.insertText(variable)
        self.evo_event_template.setFocus()
        self.update_evolution_template_preview()

    def save_evolution_settings(self):
        self.config.data["evolution_api"] = self.current_evolution_form()
        self.config.save()
        self.load_evolution_settings_into_ui()
        QMessageBox.information(self, APP_NAME, "Configuracao da Evolution API salva.")

    def evolution_client_from_form(self) -> EvolutionApiClient:
        cfg = self.current_evolution_form()
        self.config.data["evolution_api"] = cfg
        self.config._normalize_evolution_api()
        return EvolutionApiClient(self.config.data["evolution_api"])

    def test_evolution_connection(self):
        try:
            client = self.evolution_client_from_form()
            data = client.test_connection()
            count = len(data) if isinstance(data, list) else len(data.get("instances", [])) if isinstance(data, dict) else 0
            self.update_evolution_status_label(f"Evolution API conectada. Instancias encontradas: {count}")
            QMessageBox.information(self, APP_NAME, "Conexao com Evolution API validada.")
        except Exception as exc:
            self.update_evolution_status_label(f"Falha na Evolution API: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def show_evolution_qr(self, qr_payload: str):
        if not qr_payload:
            self.evo_qr_label.setPixmap(QPixmap())
            self.evo_qr_label.setText("QR Code indisponivel")
            return
        client = self.evolution_client_from_form()
        pixmap = client.build_qr_pixmap(qr_payload)
        if pixmap.isNull():
            self.evo_qr_label.setPixmap(QPixmap())
            self.evo_qr_label.setText(f"QR recebido, mas nao foi possivel renderizar.\n\nConteudo:\n{qr_payload[:300]}")
            return
        self.evo_qr_label.setText("")
        self.evo_qr_label.setPixmap(pixmap.scaled(self.evo_qr_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def connect_evolution_instance(self):
        try:
            client = self.evolution_client_from_form()
            create_if_missing = self.evo_mode.currentText() == "create_or_connect"
            state = client.ensure_instance(create_if_missing=create_if_missing)
            qr_payload = client.fetch_qr_payload()
            self.show_evolution_qr(qr_payload)
            self.update_evolution_status_label(f"Instancia pronta. Estado: {state}")
            self.save_evolution_settings()
        except Exception as exc:
            self.update_evolution_status_label(f"Falha ao conectar instancia: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def refresh_evolution_qr(self):
        try:
            client = self.evolution_client_from_form()
            qr_payload = client.fetch_qr_payload()
            self.show_evolution_qr(qr_payload)
            self.update_evolution_status_label("QR Code atualizado.")
        except Exception as exc:
            self.update_evolution_status_label(f"Falha ao atualizar QR: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def send_evolution_test_message(self):
        try:
            client = self.evolution_client_from_form()
            number = sanitize_phone_number(self.evo_test_number.text())
            message = self.evo_test_message.toPlainText().strip()
            if not number:
                raise RuntimeError("Informe o numero de teste.")
            if not message:
                raise RuntimeError("Informe a mensagem de teste.")
            client.send_text_message(number, message)
            self.update_evolution_status_label(f"Mensagem de teste enviada para {number}.")
            self.append_log(f"Evolution API: teste enviado para {number}.")
        except Exception as exc:
            self.update_evolution_status_label(f"Falha no teste Evolution: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def maybe_send_evolution_alert(self, data: dict):
        evolution_cfg = dict(self.config.data.get("evolution_api", {}))
        if not evolution_cfg.get("enabled"):
            return
        camera_cfg = self.config.get_camera(data.get("camera_name", ""))
        if not camera_cfg or not camera_cfg.get("evolution_enabled", False):
            return
        recipients = evolution_cfg.get("recipient_numbers", [])
        if not recipients:
            self.append_log("Evolution API: nenhum destinatario configurado.")
            return
        worker = EvolutionSendWorker(evolution_cfg, dict(data), recipients)
        worker.finished_status.connect(self.append_log)
        worker.finished_status.connect(lambda _text, w=worker: self._release_evolution_worker(w))
        self.evolution_workers.append(worker)
        worker.start()

    def _release_evolution_worker(self, worker):
        self.evolution_workers = [item for item in self.evolution_workers if item is not worker]

    def get_camera_speed_settings(self, camera_name: str):
        camera = self.config.get_camera(camera_name) if camera_name else None
        global_limit = int(self.config.data.get("speed_limit", 60))
        if not camera:
            return global_limit, True
        limit_enabled = bool(camera.get("speed_limit_enabled", True))
        limit_value = int(camera.get("speed_limit_value", global_limit))
        visual_enabled = bool(camera.get("speed_alert_visual", True))
        return (limit_value if limit_enabled else global_limit), visual_enabled

    def resolve_row_overspeed(self, row):
        applied_limit = row[10]
        is_overspeed = row[11]
        if applied_limit is not None and is_overspeed is not None:
            return float(applied_limit), bool(is_overspeed)
        limit, _ = self.get_camera_speed_settings(row[0])
        return float(limit), float(row[4] or 0) > float(limit)

    def set_monitor_alert_state(self, text: str, is_alert: bool):
        if is_alert:
            self.monitor_alert.setStyleSheet("padding: 10px; border: 1px solid #c96a28; background: #fff0e2; color: #7a2f0b; font-weight: bold; border-radius: 6px;")
        else:
            self.monitor_alert.setStyleSheet("padding: 10px; border: 1px solid #c9d2dc; background: #f4f7fa; color: #243447; border-radius: 6px;")
        self.monitor_alert.setText(text)

    def filter_overspeed_rows(self, rows, selected_camera=""):
        filtered = []
        for row in rows:
            camera_name = row[0]
            if selected_camera and camera_name != selected_camera:
                continue
            _, is_overspeed = self.resolve_row_overspeed(row)
            if is_overspeed:
                filtered.append(row)
        return filtered

    def on_event_received(self, data):
        self.lbl_cam.setText(data.get("camera_name") or "-"); self.lbl_plate.setText(data.get("plate") or "-"); self.lbl_speed.setText(data.get("speed") or "-"); self.lbl_lane.setText(data.get("lane") or "-"); self.lbl_direction.setText(data.get("direction") or "-"); self.lbl_type.setText(data.get("event_type") or "-"); self.lbl_image_status.setText(data.get("image_status") or "-")
        if data.get("image_path"):
            self.set_preview(data["image_path"])
            pixmap = QPixmap(data["image_path"])
            if not pixmap.isNull():
                self.monitor_thumbnail.setPixmap(pixmap.scaled(self.monitor_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.monitor_thumbnail.setText("")
        elif self.live_view.current_mode != "rtsp": self.live_view.show_message("Sem imagem disponível por ISAPI neste firmware")
        else:
            self.monitor_thumbnail.setPixmap(QPixmap())
            self.monitor_thumbnail.setText("Sem imagem")
        speed_value = extract_speed_value(data.get("speed", "")); limit, visual_enabled = self.get_camera_speed_settings(data.get("camera_name", ""))
        data["applied_speed_limit"] = float(limit)
        data["is_overspeed"] = speed_value > float(limit)
        self.db.insert_event(data); self.prepend_realtime_event(data); self.refresh_dashboard(); self.refresh_history(); self.refresh_report()
        if data["is_overspeed"]:
            self.append_log(f"ALERTA: {data.get('camera_name')} placa {data.get('plate') or '-'} acima do limite ({speed_value} > {limit} km/h)")
            if visual_enabled:
                self.set_monitor_alert_state(f"ALERTA de velocidade: {data.get('camera_name')} | placa {data.get('plate') or '-'} | {speed_value} km/h | limite {limit} km/h", True)
            else:
                self.set_monitor_alert_state(f"Evento acima do limite sem aviso visual: limite {limit} km/h", False)
            self.maybe_send_evolution_alert(data)
        else:
            self.append_log(f"Evento: {data.get('camera_name')} / placa={data.get('plate') or '-'} / velocidade={data.get('speed') or '-'} / {data.get('image_status', '')}")
            self.set_monitor_alert_state(f"Velocidade dentro do limite: {speed_value} km/h de {data.get('camera_name')} (limite {limit} km/h)", False)

    def prepend_realtime_event(self, data):
        self.realtime_table.insertRow(0)
        values = [data.get("camera_name",""), data.get("ts",""), data.get("plate",""), data.get("speed",""), data.get("lane",""), data.get("event_type","")]
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if col == 0:
                item.setData(Qt.UserRole, data.get("image_path", ""))
                item.setData(Qt.UserRole + 1, data.get("json_path", ""))
            self.realtime_table.setItem(0, col, item)
        row_color = QColor("#fff0e2") if data.get("is_overspeed") else color_from_name(data.get("camera_name", ""))
        for col in range(self.realtime_table.columnCount()):
            item = self.realtime_table.item(0, col)
            if item is not None:
                item.setBackground(row_color)
        while self.realtime_table.rowCount() > 200: self.realtime_table.removeRow(self.realtime_table.rowCount() - 1)
        self.apply_realtime_filter()

    def apply_realtime_filter(self):
        selected_camera = self.realtime_filter_camera.currentText().strip() if hasattr(self, "realtime_filter_camera") else ""
        for row in range(self.realtime_table.rowCount()):
            item = self.realtime_table.item(row, 0)
            camera_name = item.text().strip() if item else ""
            self.realtime_table.setRowHidden(row, bool(selected_camera and camera_name != selected_camera))

    def open_realtime_event_image(self, row, _column):
        item = self.realtime_table.item(row, 0)
        if item is None:
            return
        image_path = item.data(Qt.UserRole) or ""
        if image_path and Path(image_path).exists():
            self.set_preview(str(image_path))
            return
        QMessageBox.information(self, APP_NAME, "Este evento nao possui imagem salva.")

    def open_history_item(self, row, _column):
        image_item = self.history_table.item(row, 7)
        json_item = self.history_table.item(row, 8)
        image_path = image_item.text().strip() if image_item else ""
        json_path = json_item.text().strip() if json_item else ""
        self.open_event_artifact(image_path, json_path)

    def open_report_item(self, row, _column):
        image_item = self.report_table.item(row, 7)
        json_item = self.report_table.item(row, 8)
        image_path = image_item.text().strip() if image_item else ""
        json_path = json_item.text().strip() if json_item else ""
        self.open_event_artifact(image_path, json_path)

    def open_event_artifact(self, image_path: str, json_path: str):
        if image_path and Path(image_path).exists():
            self.set_preview(image_path)
            return
        if json_path and Path(json_path).exists():
            QMessageBox.information(self, APP_NAME, f"Evento sem imagem salva.\nJSON disponivel em:\n{json_path}")
            return
        QMessageBox.information(self, APP_NAME, "Este registro nao possui imagem ou JSON disponivel.")

    def set_preview(self, path):
        self.last_image_path = path
        self.live_view.show_image_path(path)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.last_image_path: self.set_preview(self.last_image_path)
        thumb = self.monitor_thumbnail.pixmap() if hasattr(self, "monitor_thumbnail") else None
        if thumb is not None and not thumb.isNull() and self.last_image_path and Path(self.last_image_path).exists():
            pixmap = QPixmap(self.last_image_path)
            if not pixmap.isNull():
                self.monitor_thumbnail.setPixmap(pixmap.scaled(self.monitor_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        evo_qr = self.evo_qr_label.pixmap() if hasattr(self, "evo_qr_label") else None
        if evo_qr is not None and not evo_qr.isNull():
            self.evo_qr_label.setPixmap(evo_qr.scaled(self.evo_qr_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def refresh_dashboard(self):
        stats = self.db.dashboard_event_speeds()
        overspeed = 0
        for row in stats["rows"]:
            applied_limit = row[2]
            is_overspeed = row[3]
            if applied_limit is not None and is_overspeed is not None:
                overspeed += 1 if is_overspeed else 0
                continue
            limit, _ = self.get_camera_speed_settings(row[0])
            if float(row[1] or 0) > float(limit):
                overspeed += 1
        self.lbl_total.setText(str(stats["total"])); self.lbl_today.setText(str(stats["today"])); self.lbl_overspeed.setText(str(overspeed)); self.lbl_last_plate.setText(stats["last_plate"] or "-")

    def refresh_history(self):
        rows = self.db.filtered_events(camera_name=self.hist_camera.currentText().strip(), plate=self.hist_plate.text().strip(), date_text=self.hist_date.text().strip(), min_speed=self.hist_min_speed.text().strip(), over_limit=None)
        self.history_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row): self.history_table.setItem(r, c, QTableWidgetItem(str(val or "")))

    def apply_speed_limit_and_refresh_report(self):
        self.config.data["speed_limit"] = int(self.speed_limit_spin.value()); self.config.save(); self.refresh_dashboard(); self.refresh_report()

    def refresh_report(self):
        selected_camera = self.report_camera.currentText().strip()
        rows = self.db.recent_events_with_speed(camera_name=selected_camera, date_text=self.report_date.text().strip())
        overspeed_rows = self.filter_overspeed_rows(rows, selected_camera=selected_camera)
        self.report_table.setRowCount(len(overspeed_rows))
        for r, row in enumerate(overspeed_rows):
            display_row = (row[0], row[1], row[2], row[3], row[5], row[6], row[7], row[8], row[9])
            for c, val in enumerate(display_row):
                self.report_table.setItem(r, c, QTableWidgetItem(str(val or "")))
        summary_limit = self.speed_limit_spin.value() if not selected_camera else self.get_camera_speed_settings(selected_camera)[0]
        self.report_summary.setText(f"Limite base: {summary_limit} km/h | Eventos acima do limite efetivo: {len(overspeed_rows)}")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", str(app_dir() / "historico_v42.csv"), "CSV (*.csv)")
        if not path: return
        rows = self.db.filtered_events(camera_name=self.hist_camera.currentText().strip(), plate=self.hist_plate.text().strip(), date_text=self.hist_date.text().strip(), min_speed=self.hist_min_speed.text().strip(), over_limit=None)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f); writer.writerow(["Câmera","Data/Hora","Placa","Velocidade","Faixa","Direção","Tipo","Imagem","JSON"]); writer.writerows(rows)
        QMessageBox.information(self, APP_NAME, f"CSV exportado:\n{path}")

    def export_overspeed_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", str(app_dir() / "excesso_velocidade_v42.csv"), "CSV (*.csv)")
        if not path: return
        rows = self.filter_overspeed_rows(self.db.recent_events_with_speed(camera_name=self.report_camera.currentText().strip(), date_text=self.report_date.text().strip()), selected_camera=self.report_camera.currentText().strip())
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f); writer.writerow(["Câmera","Data/Hora","Placa","Velocidade","Faixa","Direção","Tipo","Imagem","JSON"]); writer.writerows([(row[0], row[1], row[2], row[3], row[5], row[6], row[7], row[8], row[9]) for row in rows])
        QMessageBox.information(self, APP_NAME, f"CSV de excesso exportado:\n{path}")

    def reload_user_list(self):
        if not hasattr(self, "user_list"): return
        self.user_list.clear()
        for user in self.config.data.get("users", []): self.user_list.addItem(user.get("username", ""))

    def load_selected_user(self, username):
        if not hasattr(self, "user_list"): return
        for user in self.config.data.get("users", []):
            if user.get("username") == username:
                self.sys_user.setText(user.get("username", "")); self.sys_pass.clear(); self.sys_pass.setPlaceholderText("Digite uma nova senha para alterar"); idx = self.sys_role.findText(user.get("role", "Operador")); self.sys_role.setCurrentIndex(max(idx, 0)); return

    def new_user(self):
        self.sys_user.clear(); self.sys_pass.clear(); self.sys_pass.setPlaceholderText(""); self.sys_role.setCurrentIndex(1)

    def save_user(self):
        username = self.sys_user.text().strip()
        password = self.sys_pass.text()
        existing_user = self.config.get_user(username)
        if not username:
            QMessageBox.warning(self, APP_NAME, "Informe o usuario.")
            return
        if not password and not existing_user:
            QMessageBox.warning(self, APP_NAME, "Informe a senha para novos usuarios.")
            return
        password_hash = existing_user.get("password_hash") if existing_user else ""
        must_change_password = bool(existing_user.get("must_change_password")) if existing_user else False
        if password:
            password_hash = hash_password(password)
            must_change_password = username == DEFAULT_ADMIN_USERNAME and password == DEFAULT_ADMIN_PASSWORD
        self.config.upsert_user({
            "username": username,
            "password_hash": password_hash,
            "role": self.sys_role.currentText(),
            "must_change_password": must_change_password,
        })
        self.config.save()
        self.reload_user_list()
        QMessageBox.information(self, APP_NAME, "Usuario salvo.")

    def delete_user(self):
        username = self.sys_user.text().strip()
        if not username: return
        if username == self.logged_user.get("username"): QMessageBox.warning(self, APP_NAME, "Você não pode excluir o usuário logado."); return
        self.config.delete_user(username); self.config.save(); self.reload_user_list(); self.new_user(); QMessageBox.information(self, APP_NAME, "Usuário excluído.")

    def closeEvent(self, event):
        if self._allow_close or self.tray_icon is None:
            self.stop_live_view(); self.stop_all_monitors(log_message=False)
            if self.tray_icon is not None:
                self.tray_icon.hide()
            event.accept()
            return
        self.hide_to_tray()
        event.ignore()

def main():
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setQuitOnLastWindowClosed(False)
    config = AppConfig(); login = LoginDialog(config)
    if login.exec() != QDialog.Accepted: sys.exit(0)
    win = MainWindow(config, login.user_data); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
