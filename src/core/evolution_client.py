# Cliente Evolution API e worker de envio
import base64
import re
from pathlib import Path

import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap

from .config import (
    first_nested,
    log_runtime_error,
    render_event_message,
    sanitize_phone_number,
)


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
            log_runtime_error("EvolutionSendWorker", exc)
            self.finished_status.emit(f"Evolution API: falha no envio ({exc})")


class EvolutionTestSendWorker(QThread):
    """Worker para envio de mensagem de teste (não bloqueia a UI)."""
    finished = Signal(object)  # None = sucesso, str = mensagem de erro

    def __init__(self, evolution_cfg: dict, number: str, message: str):
        super().__init__()
        self.evolution_cfg = evolution_cfg
        self.number = number
        self.message = message

    def run(self):
        try:
            client = EvolutionApiClient(self.evolution_cfg)
            client.send_text_message(self.number, self.message)
            self.finished.emit(None)
        except Exception as exc:
            log_runtime_error("EvolutionTestSendWorker", exc)
            self.finished.emit(str(exc))
