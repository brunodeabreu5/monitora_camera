# Workers de monitoramento e snapshot ao vivo
import json
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.core.camera_client import CameraClient
from src.core.config import log_runtime_error, sanitize_filename
from src.core.parsing import looks_like_complete_event_xml, parse_event_xml


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
                log_runtime_error(f"EventWorker {cfg['name']}", e)
                self.connection_state.emit(cfg["name"], False, str(e))
                self.status.emit(f"{cfg['name']}: erro {e}")
                time.sleep(5)

        self.connection_state.emit(cfg["name"], False, "monitor parado")
        self.status.emit(f"{cfg['name']}: monitor parado.")


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
