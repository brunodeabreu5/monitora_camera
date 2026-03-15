# Cliente HTTP/RTSP para câmeras Hikvision
from urllib.parse import quote
from typing import Optional, Tuple
import urllib3

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth


class CameraClient:
    """
    Cliente HTTP/RTSP para câmeras Hikvision.

    FASE 1.5 - Implementado suporte a verificação SSL/TLS com warnings
    claros quando SSL está desabilitado.
    """

    def __init__(self, cfg: dict):
        """
        Inicializa cliente de câmera Hikvision.

        Args:
            cfg: Dicionário de configuração da câmera com campos:
                - camera_ip: Endereço IP
                - camera_port: Porta HTTP
                - camera_user: Nome de usuário
                - camera_pass: Senha (pode ser criptografada ou texto claro)
                - timeout: Timeout de requisição (segundos)
                - verify_ssl: Se True, verifica certificado SSL (default: False)
                - ssl_fingerprint: Fingerprint SHA256 esperado para cert autoassinado
        """
        self.cfg = cfg
        self.ip = cfg["camera_ip"].strip()
        self.port = int(cfg["camera_port"])
        self.user = cfg["camera_user"]

        # Descriptografar senha se necessário (FASE 1.2 - Crypto)
        password = cfg.get("camera_pass", "")
        if isinstance(password, dict):
            # Senha criptografada - precisa descriptografar
            try:
                from .crypto import decrypt_password
                self.password = decrypt_password(password)
            except Exception:
                # Fallback para string vazia se falhar
                self.password = ""
        else:
            self.password = str(password) if password else ""

        self.timeout = int(cfg["timeout"])

        # FASE 1.5 - Configuração SSL/TLS
        self.verify_ssl = bool(cfg.get("verify_ssl", False))
        self.ssl_fingerprint = str(cfg.get("ssl_fingerprint", "")).strip() or None

        # Warning se SSL estiver desabilitado
        if not self.verify_ssl:
            import sys
            print(
                f"[WARNING] SSL verification is DISABLED for camera {self.ip}. "
                f"This is a security risk. Enable verify_ssl in config.",
                file=sys.stderr
            )
            # Suprimir warnings do urllib3 sobre SSL
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = requests.Session()
        self.auth = HTTPDigestAuth(self.user, self.password)
        self.auth_basic = HTTPBasicAuth(self.user, self.password)

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
        base = f"rtsp://{user}:{password}@{self.ip}:{rtsp_port}/Streaming/Channels/{channel}"
        transport = str(self.cfg.get("rtsp_transport", "tcp")).strip().lower()
        if transport == "tcp":
            base = f"{base}?rtsp_transport=tcp"
        return base

    def is_traffic_mode(self):
        mode = self.cfg.get("camera_mode", "auto")
        return mode in ("traffic", "auto")

    def snapshot_candidates(self):
        """URLs de snapshot, na ordem tentada. Se cfg tiver snapshot_url, usa só ela (ou ela primeiro)."""
        custom = str(self.cfg.get("snapshot_url", "")).strip()
        if custom:
            return [custom]
        ch = int(self.cfg.get("channel", 101))
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

    def request(self, url: str, stream: bool = False, timeout: Optional[int] = None, auth: Optional[object] = None) -> requests.Response:
        """
        Faz requisição HTTP para a câmera.

        FASE 1.5 - Suporta verificação SSL/TLS com opção de desabilitar
        para compatibilidade com certificados autoassinados.

        Args:
            url: URL completa para requisição
            stream: Se True, usa streaming para resposta
            timeout: Timeout personalizado (usa default se None)
            auth: Objeto de autenticação personalizado (usa default se None)

        Returns:
            requests.Response: Resposta da requisição

        Raises:
            requests.RequestException: Em caso de erro de requisição
        """
        if timeout is None:
            timeout = self.timeout

        # FASE 1.5 - Verificar URL HTTPS e configurar SSL
        is_https = url.startswith("https://")
        verify = self.verify_ssl if is_https else True

        # Se fingerprint fornecido, usar validação personalizada
        if is_https and self.ssl_fingerprint:
            verify = self._verify_ssl_fingerprint

        return self.session.get(
            url,
            auth=auth or self.auth,
            timeout=timeout,
            stream=stream,
            verify=verify,
            headers={"Accept": "multipart/x-mixed-replace, text/xml, */*"},
        )

    def _verify_ssl_fingerprint(self, cert: dict, hostname: str) -> bool:
        """
        Valida certificado SSL usando fingerprint SHA256.

        Permite usar certificados autoassinados conhecidos sem
        comprometer a segurança.

        Args:
            cert: Dicionário com dados do certificado
            hostname: Nome do host sendo validado

        Returns:
            bool: True se fingerprint confere, False caso contrário
        """
        import hashlib

        if not self.ssl_fingerprint:
            return False

        # Calcular fingerprint do certificado recebido
        cert_der = cert.get("der")
        if not cert_der:
            return False

        fingerprint = hashlib.sha256(cert_der).digest()
        fingerprint_hex = fingerprint.hex().upper()

        # Comparar com fingerprint esperado
        expected = self.ssl_fingerprint.replace(":", "").upper()

        return fingerprint_hex == expected

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
            for auth in (self.auth, self.auth_basic):
                try:
                    r = self.request(url, timeout=self.timeout, auth=auth)
                    ctype = r.headers.get("Content-Type", "")
                    is_img = "image" in ctype.lower() or (len(r.content) >= 2 and r.content[:2] == b"\xff\xd8")
                    if r.status_code == 200 and is_img:
                        return True, 200, url
                    if r.status_code == 401:
                        return self.describe_connection_result(r.status_code, url)
                    if r.status_code == 403 and auth is self.auth_basic:
                        return self.describe_connection_result(r.status_code, url)
                    if r.status_code != 403:
                        break
                except Exception:
                    break
        return False, 500, "snapshot not supported"

    def download_snapshot(self):
        last_error = "snapshot not supported"
        for url in self.snapshot_candidates():
            for auth in (self.auth, self.auth_basic):
                try:
                    r = self.request(url, timeout=self.timeout, auth=auth)
                    ctype = r.headers.get("Content-Type", "")
                    has_bytes = len(r.content) >= 2
                    is_image = has_bytes and (
                        "image" in ctype.lower() or r.content[:2] == b"\xff\xd8"
                    )
                    if r.status_code == 200 and is_image:
                        return r.content, url
                    last_error = f"HTTP {r.status_code} em {url}" if r.status_code != 200 else f"resposta vazia ou nao e imagem em {url}"
                    if r.status_code != 403:
                        break
                except Exception as e:
                    last_error = f"{url}: {e}"
                    break
        raise RuntimeError(last_error)

    def connect_alert_stream(self):
        last_error = "alert stream indisponível"
        for url in self.alert_stream_candidates():
            try:
                r = self.request(url, stream=True, timeout=(10, None))
                if r.status_code == 200:
                    return r, url
                if r.status_code == 500:
                    last_error = (
                        "Câmera retornou erro 500 (erro interno). "
                        "Verifique o firmware da câmera e a configuração de eventos/alertStream."
                    )
                else:
                    last_error = f"HTTP {r.status_code} em {url}"
            except Exception as e:
                last_error = f"{url}: {e}"
        raise RuntimeError(last_error)
