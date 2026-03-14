# Configuração e helpers para Hikvision Radar Pro V4.2
import sys
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

APP_NAME = "Hikvision Radar Pro V4.2"
CONFIG_FILE = "hikvision_pro_v42_config.json"
DB_FILE = "events_v42.db"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"

# Índices da tupla retornada por Database.recent_events_with_speed()
EVT_IDX_CAMERA_NAME = 0
EVT_IDX_TS = 1
EVT_IDX_PLATE = 2
EVT_IDX_SPEED = 3
EVT_IDX_SPEED_VALUE = 4
EVT_IDX_LANE = 5
EVT_IDX_DIRECTION = 6
EVT_IDX_EVENT_TYPE = 7
EVT_IDX_IMAGE_PATH = 8
EVT_IDX_JSON_PATH = 9
EVT_IDX_APPLIED_LIMIT = 10
EVT_IDX_IS_OVERSPEED = 11


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
    # When running from source, go from src/core/ back to project root
    return Path(__file__).resolve().parent.parent.parent


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sanitize_filename(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', text)


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
            "live_detection_enabled": False,
            "detection_confidence_threshold": 0.5,
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
            camera["live_detection_enabled"] = bool(camera.get("live_detection_enabled", False))
            try:
                camera["detection_confidence_threshold"] = float(camera.get("detection_confidence_threshold", 0.5))
            except (TypeError, ValueError):
                camera["detection_confidence_threshold"] = 0.5
            camera["detection_confidence_threshold"] = max(0.0, min(1.0, camera["detection_confidence_threshold"]))
            try:
                camera["camera_port"] = int(camera.get("camera_port", defaults["camera_port"]))
            except Exception as exc:
                log_runtime_error("AppConfig normalizacao camera_port", exc)
                camera["camera_port"] = defaults["camera_port"]
            try:
                camera["channel"] = int(camera.get("channel", defaults["channel"]))
            except Exception as exc:
                log_runtime_error("AppConfig normalizacao channel", exc)
                camera["channel"] = defaults["channel"]
            try:
                camera["timeout"] = int(camera.get("timeout", defaults["timeout"]))
            except Exception as exc:
                log_runtime_error("AppConfig normalizacao timeout", exc)
                camera["timeout"] = defaults["timeout"]
            try:
                camera["speed_limit_value"] = int(camera.get("speed_limit_value", self.data.get("speed_limit", defaults["speed_limit_value"])))
            except Exception as exc:
                log_runtime_error("AppConfig normalizacao speed_limit_value", exc)
                camera["speed_limit_value"] = int(self.data.get("speed_limit", defaults["speed_limit_value"]))
            try:
                camera["rtsp_port"] = int(camera.get("rtsp_port", defaults["rtsp_port"]))
            except Exception as exc:
                log_runtime_error("AppConfig normalizacao rtsp_port", exc)
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
