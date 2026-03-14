#!/usr/bin/env python3
"""
Testa a conexao com o alertStream da camera Hikvision e imprime os eventos recebidos.

Uso:
  python scripts/test_alertstream.py
  (usa hikvision_pro_v42_config.json na pasta do projeto)

  python scripts/test_alertstream.py --url http://192.168.1.64:80 --user admin --password 'sua_senha'
  (conecta em uma camera sem config file)

O endpoint /ISAPI/Event/notification/alertStream envia eventos em XML, por exemplo:
- EventNotificationAlert (eventos gerais)
- ANPR (reconhecimento de placa, velocidade, faixa, etc.)

O script mantem a conexao aberta e imprime cada bloco XML completo recebido.
Para sair: Ctrl+C.
"""

import argparse
import sys
from pathlib import Path

# project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from requests.auth import HTTPDigestAuth

from src.core.parsing import find_event_xml_end, looks_like_complete_event_xml, parse_event_xml


def connect_alertstream(base_url: str, user: str, password: str, timeout_connect: int = 10):
    url = f"{base_url.rstrip('/')}/ISAPI/Event/notification/alertStream"
    r = requests.get(
        url,
        auth=HTTPDigestAuth(user, password),
        stream=True,
        timeout=(timeout_connect, None),
        headers={"Accept": "multipart/x-mixed-replace, text/xml, */*"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} em {url}")
    return r


def run_from_config():
    from src.core.config import app_dir
    config_path = app_dir() / "hikvision_pro_v42_config.json"
    if not config_path.exists():
        print(f"Config nao encontrado: {config_path}")
        print("Use --url, --user e --password para testar sem config.")
        return 1
    import json
    data = json.loads(config_path.read_text(encoding="utf-8"))
    cameras = data.get("cameras", [])
    if not cameras:
        print("Nenhuma camera no config.")
        return 1
    cam = cameras[0]
    base = f"http://{cam['camera_ip']}:{cam['camera_port']}"
    user = cam.get("camera_user", "admin")
    password = cam.get("camera_pass", "")
    return run_stream(base, user, password, cam.get("name", "Camera 1"))


def run_stream(base_url: str, user: str, password: str, label: str = "Camera"):
    print(f"Conectando ao alertStream: {base_url}/ISAPI/Event/notification/alertStream")
    try:
        resp = connect_alertstream(base_url, user, password)
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return 1
    print("Conectado. Aguardando eventos (Ctrl+C para sair)...\n")
    buffer = ""
    count = 0
    try:
        for chunk in resp.iter_content(chunk_size=1024, decode_unicode=False):
            if not chunk:
                continue
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="ignore")
            buffer += chunk
            while True:
                start = buffer.find("<?xml")
                if start == -1:
                    break
                end = find_event_xml_end(buffer, start)
                if end is None:
                    break
                xml_text = buffer[start:end]
                buffer = buffer[end:]
                if not xml_text.strip():
                    continue
                if not looks_like_complete_event_xml(xml_text):
                    print(f"[{label}] XML ignorado (formato nao reconhecido), fim: ...{xml_text.strip()[-50:]}")
                    continue
                count += 1
                parsed = parse_event_xml(xml_text)
                if parsed:
                    plate = parsed.get("plate") or "-"
                    speed = parsed.get("speed") or "-"
                    ts = parsed.get("ts") or "-"
                    print(f"[{label}] Evento #{count}: placa={plate} velocidade={speed} ts={ts}")
                else:
                    print(f"[{label}] Evento #{count}: XML nao parseado")
                print(xml_text.strip()[:500] + ("..." if len(xml_text) > 500 else ""))
                print("-" * 60)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")
    print(f"Total de eventos exibidos: {count}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Testa alertStream da camera Hikvision e imprime eventos XML.")
    ap.add_argument("--url", help="URL base da camera (ex: http://192.168.1.64:80)")
    ap.add_argument("--user", default="admin", help="Usuario HTTP")
    ap.add_argument("--password", default="", help="Senha HTTP")
    args = ap.parse_args()
    if args.url:
        return run_stream(args.url, args.user, args.password, "Camera")
    return run_from_config()


if __name__ == "__main__":
    sys.exit(main())
