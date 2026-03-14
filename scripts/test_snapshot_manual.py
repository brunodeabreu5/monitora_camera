#!/usr/bin/env python3
"""
Testa o snapshot manual usando a configuracao da camera do app.
Verifica se a imagem e retornada e salva em output/manual/ para inspecao.

Uso (na raiz do projeto):
  python scripts/test_snapshot_manual.py
  python scripts/test_snapshot_manual.py "Camera 1"
"""

import sys
from datetime import datetime
from pathlib import Path

# project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import app_dir
from src.core.camera_client import CameraClient


def main():
    from src.core.config import AppConfig

    config_path = app_dir() / "hikvision_pro_v42_config.json"
    if not config_path.exists():
        print(f"Config nao encontrada: {config_path}")
        print("Execute o app uma vez e configure uma camera, ou crie o arquivo de config.")
        return 1

    config = AppConfig(config_path)
    cameras = config.data.get("cameras", [])
    if not cameras:
        print("Nenhuma camera na config.")
        return 1

    name = sys.argv[1] if len(sys.argv) > 1 else None
    cam = config.get_camera(name) if name else cameras[0]
    if not cam:
        print(f"Camera '{name}' nao encontrada. Disponiveis: {[c.get('name') for c in cameras]}")
        return 1

    print(f"Testando snapshot: {cam.get('name')} ({cam.get('camera_ip')}:{cam.get('camera_port')})")
    print("Tentando Digest e, se 403, Basic auth...")

    try:
        client = CameraClient(cam)
        img_bytes, used_url = client.download_snapshot()
    except Exception as e:
        print(f"ERRO: {e}")
        return 1

    if not img_bytes:
        print("ERRO: resposta vazia.")
        return 1

    # Verifica se parece JPEG
    if len(img_bytes) >= 2 and img_bytes[:2] == b"\xff\xd8":
        fmt = "JPEG"
    else:
        fmt = "outro (primeiros bytes: {})".format(img_bytes[:8].hex() if len(img_bytes) >= 8 else img_bytes.hex())

    out_dir = Path(cam.get("output_dir", str(app_dir() / "output"))) / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = out_dir / f"{cam.get('name', 'camera')}_test_{timestamp}.jpg"
    file_path.write_bytes(img_bytes)

    print(f"OK: imagem recebida ({len(img_bytes)} bytes, {fmt})")
    print(f"URL usada: {used_url}")
    print(f"Salvo em: {file_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
