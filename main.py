# Ponto de entrada Hikvision Radar Pro V4.2
import os
import sys

# Evita erro "Failed setup for format d3d11" no Windows: desativa aceleração por
# hardware na decodificação FFmpeg (Qt Multimedia), forçando decodificação em software.
if os.name == "nt" and "QT_FFMPEG_DECODING_HW_DEVICE_TYPES" not in os.environ:
    os.environ["QT_FFMPEG_DECODING_HW_DEVICE_TYPES"] = ","

# Reduzir mensagens do FFmpeg no terminal (RTP: missed, cbp too large, etc.)
if "AV_LOG_LEVEL" not in os.environ:
    os.environ["AV_LOG_LEVEL"] = "-8"

from PySide6.QtWidgets import QApplication, QDialog

from src.core.config import APP_NAME, AppConfig
from ui.widgets import LoginDialog
from src.app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    config = AppConfig()
    login = LoginDialog(config)
    if login.exec() != QDialog.Accepted:
        sys.exit(0)
    win = MainWindow(config, login.user_data)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
