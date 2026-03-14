# Cliente HTTP/RTSP para câmeras Hikvision
from urllib.parse import quote

import requests
from requests.auth import HTTPDigestAuth


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
