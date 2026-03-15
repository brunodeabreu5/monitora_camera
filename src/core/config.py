# Configuração e helpers para Hikvision Radar Pro V4.2
import sys
import json
import re
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Import crypto module for password encryption (FASE 1 - Security)
try:
    from .crypto import (
        encrypt_password,
        decrypt_password,
        is_encrypted_password,
        migrate_plaintext_to_encrypted,
        check_crypto_available,
        CryptoError
    )
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    CryptoError = Exception

APP_NAME = "Hikvision Radar Pro V4.2"
APP_VERSION = "4.2.0"
CONFIG_FILE = "hikvision_pro_v42_config.json"
DB_FILE = "events_v42.db"
# FASE 1.3 - Credenciais padrão removidas por segurança
# O usuário deve criar credenciais através do wizard de primeira execução
DEFAULT_ADMIN_USERNAME = None  # Must be set by user
DEFAULT_ADMIN_PASSWORD = None  # Must be set by user

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


def _sanitize_log_message(text: str) -> str:
    """Remove trechos que podem conter senha em URLs (ex.: http://user:senha@host) nos logs."""
    if not text:
        return text
    # Redact :senha@ em URLs para nao gravar credenciais no log
    return re.sub(r":([^@\s]+)@", ":***@", str(text))


def log_runtime_error(context: str, exc: Exception):
    stamp = now_str()
    raw = f"[{stamp}] {context}: {exc}"
    message = _sanitize_log_message(raw)
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


# Formato de data/hora exibido no app (padrão brasileiro)
DATETIME_FMT_BR = "%d/%m/%Y %H:%M:%S"


def format_datetime_br(ts_str: str | None) -> str:
    """Converte data/hora (ISO ou YYYY-MM-DD HH:MM:SS) para DD/MM/YYYY HH:MM:SS. Retorna o original se não conseguir parsear."""
    if not ts_str or not str(ts_str).strip():
        return ""
    raw = str(ts_str).strip()
    try:
        # ISO com T e opcional timezone: 2026-03-14T12:12:16.722-03:00
        if "T" in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.strftime(DATETIME_FMT_BR)
        # Espaço: 2026-03-14 12:12:16
        if " " in raw:
            dt = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
            return dt.strftime(DATETIME_FMT_BR)
        # Só data: 2026-03-14
        if len(raw) >= 10:
            dt = datetime.strptime(raw[:10], "%Y-%m-%d")
            return dt.strftime(DATETIME_FMT_BR)
    except (ValueError, TypeError):
        pass
    return raw


def now_str():
    return datetime.now().strftime(DATETIME_FMT_BR)


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
        "ts": format_datetime_br(event_data.get("ts")) or "-",
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


def _hash_legacy(password: str) -> str:
    """Hash without salt (legacy). Used only for verifying old users."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return (password_hash, salt). If salt is None, a new one is generated."""
    if salt is None:
        salt = secrets.token_hex(16)
    value = (salt + password).encode("utf-8")
    digest = hashlib.sha256(value).hexdigest()
    return digest, salt


def verify_password(user: dict, password: str) -> bool:
    stored = user.get("password_hash", "")
    if not stored:
        return user.get("password") == password
    salt = user.get("password_salt")
    if salt:
        h, _ = hash_password(password, salt)
        return h == stored
    return _hash_legacy(password) == stored


class AppConfig:
    def __init__(self, filepath: Path | None = None, skip_first_run_check: bool = False):
        """
        Inicializa configuração da aplicação.

        Args:
            filepath: Caminho para arquivo de configuração (opcional)
            skip_first_run_check: Se True, não verifica se é primeira execução
                (usado para testes e inicialização antes do wizard)

        Raises:
            RuntimeError: Se arquivo de config existe mas está corrompido
        """
        self.filepath = filepath or (app_dir() / CONFIG_FILE)
        self._is_first_run = not self.filepath.exists()

        # Initialize with empty structure - will be populated by load() or wizard
        self.data = {
            "speed_limit": 60,
            "users": [],
            "cameras": [],
            "evolution_api": {},
            "_version": APP_VERSION,
        }

        # Only try to load if config file exists
        if self.filepath.exists():
            self.load()
        elif not skip_first_run_check:
            # First run - no users yet, wizard will populate
            self.data["users"] = []
            self.data["cameras"] = []
            self.data["evolution_api"] = self._default_evolution_api()

    def is_first_run(self) -> bool:
        """
        Verifica se é a primeira execução da aplicação.

        Returns:
            bool: True se não há usuários configurados (primeira execução)
        """
        return len(self.data.get("users", [])) == 0

    def _default_admin_user(self, username: Optional[str] = None, password: Optional[str] = None) -> dict:
        """
        Cria usuário admin padrão com credenciais fornecidas.

        FASE 1.3 - Não usa mais credenciais hardcoded.
        As credenciais devem ser fornecidas pelo usuário através do
        wizard de primeira execução.

        Args:
            username: Nome de usuário do admin (obrigatório)
            password: Senha do admin (obrigatório)

        Returns:
            dict: Dicionário com dados do usuário admin

        Raises:
            ValueError: Se username ou password não forem fornecidos
        """
        if not username or not password:
            raise ValueError("Admin credentials must be provided for first-time setup")

        pwd_hash, pwd_salt = hash_password(password)
        return {
            "username": username,
            "password_hash": pwd_hash,
            "password_salt": pwd_salt,
            "role": "Administrador",
            "must_change_password": False,  # User just set it, no need to change
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
            "snapshot_url": "",
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
            # FASE 1.5 - SSL/TLS settings
            "verify_ssl": False,
            "ssl_fingerprint": "",
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
                pwd_hash, pwd_salt = hash_password(user["password"])
                user["password_hash"] = pwd_hash
                user["password_salt"] = pwd_salt
            user.pop("password", None)
            user.setdefault("role", "Operador")
            user["must_change_password"] = bool(user.get("must_change_password", False))
            if user.get("username"):
                normalized.append(user)

        # FASE 1.3 - Não criar usuário admin padrão automaticamente
        # O wizard de primeira execução deve criar o usuário admin
        # Se não há usuários normalizados, mantém vazio (indica primeira execução)
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

            # FASE 1.2 - Criptografia de senhas de câmeras
            # Processar senha: migrar para criptografada se necessário
            camera_pass_raw = camera.get("camera_pass", "")
            if isinstance(camera_pass_raw, str) and camera_pass_raw and CRYPTO_AVAILABLE:
                # Senha em texto claro - migrar para formato criptografado
                try:
                    if not is_encrypted_password(camera_pass_raw):
                        camera["camera_pass"] = migrate_plaintext_to_encrypted(camera_pass_raw)
                        log_runtime_error(
                            f"AppConfig: Senha da câmera '{camera['name']}' migrada para formato criptografado",
                            Exception("Migration info only")
                        )
                    else:
                        camera["camera_pass"] = camera_pass_raw
                except Exception as exc:
                    log_runtime_error(
                        f"AppConfig: Falha ao criptografar senha da câmera '{camera['name']}'",
                        exc
                    )
                    # Manter texto claro como fallback
                    camera["camera_pass"] = camera_pass_raw
            else:
                # Já é dict criptografado ou senha vazia ou crypto não disponível
                camera["camera_pass"] = camera_pass_raw if camera_pass_raw else ""

            camera["output_dir"] = str(camera.get("output_dir", defaults["output_dir"]))
            camera["save_snapshot_on_event"] = bool(camera.get("save_snapshot_on_event", True))
            camera["snapshot_url"] = str(camera.get("snapshot_url", "")).strip()
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
            # FASE 1.5 - SSL/TLS settings normalization
            camera["verify_ssl"] = bool(camera.get("verify_ssl", False))
            camera["ssl_fingerprint"] = str(camera.get("ssl_fingerprint", "")).strip()
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
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_camera_names(self):
        return [c.get("name", "Camera") for c in self.data.get("cameras", [])]

    def get_camera(self, name: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Recupera configuração de uma câmera pelo nome.

        Args:
            name: Nome único da câmera

        Returns:
            Dicionário com configuração da câmera ou None se não encontrada

        Raises:
            ValueError: Se name for None ou string vazia
        """
        if not name:
            return None

        for cam in self.data.get("cameras", []):
            if cam.get("name") == name:
                # Return a copy to avoid modifying original
                return dict(cam)
        return None

    def get_camera_decrypted(self, name: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Recupera configuração de câmera com senha descriptografada.

        Retorna uma cópia da configuração da câmera com o campo
        'camera_pass' contendo a senha em texto claro para uso
        em tempo de execução.

        Args:
            name: Nome único da câmera

        Returns:
            Dicionário com configuração da câmera e senha descriptografada,
            ou None se não encontrada

        Raises:
            CryptoError: Se falhar a descriptografia da senha
        """
        camera = self.get_camera(name)
        if not camera:
            return None

        # Descriptografar senha se necessário
        camera_pass = camera.get("camera_pass", "")
        if isinstance(camera_pass, dict) and CRYPTO_AVAILABLE:
            try:
                camera["camera_pass"] = decrypt_password(camera_pass)
            except Exception as exc:
                log_runtime_error(
                    f"AppConfig: Falha ao descriptografar senha da câmera '{name}'",
                    exc
                )
                # Retornar None para indicar erro
                return None
        elif isinstance(camera_pass, str):
            # Senha já está em texto claro
            camera["camera_pass"] = camera_pass
        else:
            # Tipo inválido ou vazio
            camera["camera_pass"] = ""

        return camera

    def load_camera_password(self, camera: Dict[str, Any]) -> str:
        """
        Helper para extrair senha descriptografada de um dict de câmera.

        Args:
            camera: Dicionário de configuração de câmera

        Returns:
            Senha em texto claro (string vazia se não houver senha)
        """
        if not camera:
            return ""

        camera_pass = camera.get("camera_pass", "")
        if isinstance(camera_pass, dict) and CRYPTO_AVAILABLE:
            try:
                return decrypt_password(camera_pass)
            except Exception as exc:
                log_runtime_error(
                    f"AppConfig: Falha ao descriptografar senha da câmera",
                    exc
                )
                return ""
        elif isinstance(camera_pass, str):
            return camera_pass
        return ""

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
        users = self.data.get("users", [])
        for i, user in enumerate(users):
            if user.get("username") != username or not verify_password(user, password):
                continue
            if not user.get("password_salt"):
                pwd_hash, pwd_salt = hash_password(password)
                users[i] = dict(user)
                users[i]["password_hash"] = pwd_hash
                users[i]["password_salt"] = pwd_salt
                self.save()
            return dict(users[i])
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
