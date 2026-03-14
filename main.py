# Ponto de entrada Hikvision Radar Pro V4.2
import sys

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
