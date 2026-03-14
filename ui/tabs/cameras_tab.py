# Cameras tab - manage camera configurations
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QListWidget, QLineEdit, QPushButton, QLabel, QSpinBox,
    QCheckBox, QComboBox, QMessageBox, QSplitter, QWidget, QListWidgetItem, QFileDialog
)

from src.core.camera_client import CameraClient
from src.core.config import APP_NAME, app_dir
from ui.widgets import PasswordField
from .base_tab import BaseTab


class CamerasTab(BaseTab):
    """Cameras tab for managing camera configurations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # UI elements
        self.camera_list = None
        self.cam_name = None
        self.cam_ip = None
        self.cam_port = None
        self.cam_user = None
        self.cam_pass = None
        self.cam_channel = None
        self.cam_timeout = None
        self.cam_rtsp_enabled = None
        self.cam_rtsp_port = None
        self.cam_rtsp_transport = None
        self.cam_rtsp_url = None
        self.cam_live_fallback = None
        self.cam_speed_limit_enabled = None
        self.cam_speed_limit = None
        self.cam_speed_alert_visual = None
        self.cam_evolution_enabled = None
        self.cam_output = None
        self.cam_enabled = None
        self.cam_snapshot = None
        self.cam_mode = None

        self.build_ui()

    def build_ui(self):
        """Build the cameras tab UI."""
        layout = super().build_ui()

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel - camera list
        left_panel = QGroupBox("Cameras cadastradas")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        self.camera_list = QListWidget()
        self.camera_list.currentTextChanged.connect(self.load_selected_camera)
        left_layout.addWidget(self.camera_list)

        # Right panel - camera form
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        form_box = QGroupBox("Configuracao da camera")
        form = QFormLayout(form_box)

        # Basic camera settings
        self.cam_name = QLineEdit()
        self.cam_ip = QLineEdit()
        self.cam_port = QSpinBox()
        self.cam_port.setRange(1, 65535)
        self.cam_port.setValue(80)

        self.cam_user = QLineEdit()
        self.cam_pass = PasswordField()

        self.cam_channel = QSpinBox()
        self.cam_channel.setRange(1, 999)
        self.cam_channel.setValue(101)

        self.cam_timeout = QSpinBox()
        self.cam_timeout.setRange(1, 120)
        self.cam_timeout.setValue(15)

        self.cam_mode = QComboBox()
        self.cam_mode.addItems(["auto", "traffic", "normal"])

        # RTSP settings
        self.cam_rtsp_enabled = QCheckBox("Habilitar video ao vivo (RTSP)")
        self.cam_rtsp_enabled.setChecked(True)

        self.cam_rtsp_port = QSpinBox()
        self.cam_rtsp_port.setRange(1, 65535)
        self.cam_rtsp_port.setValue(554)

        self.cam_rtsp_transport = QComboBox()
        self.cam_rtsp_transport.addItems(["tcp", "udp"])

        self.cam_rtsp_url = QLineEdit()

        self.cam_live_fallback = QComboBox()
        self.cam_live_fallback.addItems(["snapshot", "none"])

        # Speed limit settings
        self.cam_speed_limit_enabled = QCheckBox("Habilitar aviso de velocidade")
        self.cam_speed_limit_enabled.setChecked(True)

        self.cam_speed_limit = QSpinBox()
        config = self.get_config()
        default_limit = config.data.get("speed_limit", 60) if config else 60
        self.cam_speed_limit.setRange(1, 300)
        self.cam_speed_limit.setValue(int(default_limit))

        self.cam_speed_alert_visual = QCheckBox("Mostrar aviso visual na tela")
        self.cam_speed_alert_visual.setChecked(True)

        # Evolution API
        self.cam_evolution_enabled = QCheckBox("Enviar excesso pela Evolution API")

        # Output directory
        self.cam_output = QLineEdit()
        browse = QPushButton("Escolher pasta")
        browse.clicked.connect(self.choose_output_dir)

        out_wrap = QWidget()
        out_row = QHBoxLayout(out_wrap)
        out_row.setContentsMargins(0, 0, 0, 0)
        out_row.addWidget(self.cam_output, 1)
        out_row.addWidget(browse, 0)

        # Additional settings
        self.cam_enabled = QCheckBox("Ativa para monitoramento")
        self.cam_snapshot = QCheckBox("Salvar snapshot automatico por evento")

        # Add all form fields
        form.addRow("Nome:", self.cam_name)
        form.addRow("IP:", self.cam_ip)
        form.addRow("Porta HTTP:", self.cam_port)
        form.addRow("Usuario:", self.cam_user)
        form.addRow("Senha:", self.cam_pass)
        form.addRow("Canal:", self.cam_channel)
        form.addRow("Timeout:", self.cam_timeout)
        form.addRow("Modo da camera:", self.cam_mode)
        form.addRow("", self.cam_rtsp_enabled)
        form.addRow("Porta RTSP:", self.cam_rtsp_port)
        form.addRow("Preferencia RTSP:", self.cam_rtsp_transport)
        form.addRow("URL RTSP:", self.cam_rtsp_url)
        form.addRow("Fallback live:", self.cam_live_fallback)
        form.addRow("", self.cam_speed_limit_enabled)
        form.addRow("Limite veloc. (km/h):", self.cam_speed_limit)
        form.addRow("", self.cam_speed_alert_visual)
        form.addRow("", self.cam_evolution_enabled)
        form.addRow("Pasta:", out_wrap)
        form.addRow("", self.cam_enabled)
        form.addRow("", self.cam_snapshot)

        right_layout.addWidget(form_box)

        # Info note
        note = QLabel(
            "Para iDS-TCM403-GIR, use 'traffic' ou 'auto'. Video ao vivo usa RTSP embutido; "
            "se o player falhar, o app pode cair para snapshots ao vivo. Esta versão usa apenas "
            "o alertStream padrão /ISAPI/Event/notification/alertStream para eventos."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "padding: 8px; border: 1px solid #d7dee6; background: #f7fafc; "
            "border-radius: 6px; color: #486581;"
        )
        right_layout.addWidget(note)

        # Buttons
        btns_wrap = QWidget()
        btns = QHBoxLayout(btns_wrap)
        btns.setContentsMargins(0, 0, 0, 0)

        for text, slot in [
            ("Nova camera", self.new_camera),
            ("Salvar camera", self.save_camera),
            ("Excluir camera", self.delete_camera),
            ("Testar conexao", self.test_camera_connection),
            ("Snapshot manual", self.manual_snapshot)
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)

        btns.addStretch(1)
        right_layout.addWidget(btns_wrap)
        right_layout.addStretch(1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Load initial camera list
        self.reload_camera_list()

        return layout

    def reload_camera_list(self):
        """Reload the list of cameras from config."""
        if not self.camera_list:
            return

        config = self.get_config()
        if not config:
            return

        names = config.get_camera_names()
        self.camera_list.clear()
        for name in names:
            self.camera_list.addItem(QListWidgetItem(name))

        if names:
            self.camera_list.setCurrentRow(0)

    def load_selected_camera(self, name: str):
        """Load camera data into the form when a camera is selected."""
        if not self.camera_list:
            return

        config = self.get_config()
        if not config:
            return

        cam = config.get_camera(name)
        if not cam:
            return

        self.cam_name.setText(cam.get("name", ""))
        self.cam_ip.setText(cam.get("camera_ip", ""))
        self.cam_port.setValue(int(cam.get("camera_port", 80)))
        self.cam_user.setText(cam.get("camera_user", ""))
        self.cam_pass.setText(cam.get("camera_pass", ""))
        self.cam_channel.setValue(int(cam.get("channel", 101)))
        self.cam_timeout.setValue(int(cam.get("timeout", 15)))
        self.cam_mode.setCurrentText(cam.get("camera_mode", "auto"))
        self.cam_rtsp_enabled.setChecked(bool(cam.get("rtsp_enabled", True)))
        self.cam_rtsp_port.setValue(int(cam.get("rtsp_port", 554)))
        self.cam_rtsp_transport.setCurrentText(cam.get("rtsp_transport", "tcp"))
        self.cam_rtsp_url.setText(cam.get("rtsp_url", ""))
        self.cam_live_fallback.setCurrentText(cam.get("live_fallback_mode", "snapshot"))
        self.cam_speed_limit_enabled.setChecked(bool(cam.get("speed_limit_enabled", True)))
        self.cam_speed_limit.setValue(int(cam.get("speed_limit_value", 60)))
        self.cam_speed_alert_visual.setChecked(bool(cam.get("speed_alert_visual", True)))
        self.cam_evolution_enabled.setChecked(bool(cam.get("evolution_enabled", False)))
        self.cam_output.setText(cam.get("output_dir", str(app_dir() / "output")))
        self.cam_enabled.setChecked(bool(cam.get("enabled", True)))
        self.cam_snapshot.setChecked(bool(cam.get("save_snapshot_on_event", True)))

    def current_camera_form(self) -> dict:
        """Get camera data from the form."""
        config = self.get_config()
        default_output = str(app_dir() / "output") if not config else config.data.get("output_dir", str(app_dir() / "output"))

        return {
            "name": self.cam_name.text().strip() or "Camera",
            "enabled": self.cam_enabled.isChecked(),
            "camera_ip": self.cam_ip.text().strip(),
            "camera_port": int(self.cam_port.value()),
            "camera_user": self.cam_user.text().strip(),
            "camera_pass": self.cam_pass.text(),
            "channel": int(self.cam_channel.value()),
            "timeout": int(self.cam_timeout.value()),
            "rtsp_enabled": self.cam_rtsp_enabled.isChecked(),
            "rtsp_port": int(self.cam_rtsp_port.value()),
            "rtsp_transport": self.cam_rtsp_transport.currentText(),
            "rtsp_url": self.cam_rtsp_url.text().strip(),
            "live_fallback_mode": self.cam_live_fallback.currentText(),
            "speed_limit_enabled": self.cam_speed_limit_enabled.isChecked(),
            "speed_limit_value": int(self.cam_speed_limit.value()),
            "speed_alert_visual": self.cam_speed_alert_visual.isChecked(),
            "evolution_enabled": self.cam_evolution_enabled.isChecked(),
            "output_dir": self.cam_output.text().strip() or default_output,
            "save_snapshot_on_event": self.cam_snapshot.isChecked(),
            "camera_mode": self.cam_mode.currentText()
        }

    def choose_output_dir(self):
        """Open dialog to choose output directory."""
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.cam_output.setText(folder)

    def new_camera(self):
        """Clear the form to create a new camera."""
        config = self.get_config()
        count = len(config.get_camera_names()) if config else 0

        self.cam_name.setText(f"Camera {count + 1}")
        self.cam_ip.clear()
        self.cam_user.clear()
        self.cam_pass.clear()
        self.cam_rtsp_enabled.setChecked(True)
        self.cam_rtsp_port.setValue(554)
        self.cam_rtsp_transport.setCurrentText("tcp")
        self.cam_rtsp_url.clear()
        self.cam_live_fallback.setCurrentText("snapshot")
        self.cam_speed_limit_enabled.setChecked(True)
        self.cam_speed_limit.setValue(int(config.data.get("speed_limit", 60)) if config else 60)
        self.cam_speed_alert_visual.setChecked(True)
        self.cam_evolution_enabled.setChecked(False)
        self.cam_output.setText(str(app_dir() / "output"))
        self.cam_enabled.setChecked(True)
        self.cam_snapshot.setChecked(True)
        self.cam_mode.setCurrentText("auto")

    def save_camera(self):
        """Save the current camera data from the form."""
        cam = self.current_camera_form()
        Path(cam["output_dir"]).mkdir(parents=True, exist_ok=True)

        config = self.get_config()
        if not config:
            return

        config.upsert_camera(cam)
        config.save()
        self.reload_camera_list()

        # Notify main window to update camera lists in other tabs
        if self.main_window and hasattr(self.main_window, "reload_camera_lists"):
            self.main_window.reload_camera_lists()

        # Update live view if this camera is currently selected
        if self.main_window and hasattr(self.main_window, "live_camera_combo"):
            if self.main_window.live_camera_combo.currentText().strip() == cam["name"]:
                if hasattr(self.main_window, "on_live_camera_changed"):
                    self.main_window.on_live_camera_changed(cam["name"])

        QMessageBox.information(self, APP_NAME, "Camera salva com sucesso.")

    def delete_camera(self):
        """Delete the current camera."""
        name = self.cam_name.text().strip()
        if not name:
            return

        # Stop live view if this camera is active
        if self.main_window and hasattr(self.main_window, "live_camera_combo"):
            if self.main_window.live_camera_combo.currentText().strip() == name:
                if hasattr(self.main_window, "stop_live_view"):
                    self.main_window.stop_live_view()

        config = self.get_config()
        if not config:
            return

        config.delete_camera(name)
        config.save()
        self.reload_camera_list()
        self.new_camera()

        # Notify main window to update camera lists in other tabs
        if self.main_window and hasattr(self.main_window, "reload_camera_lists"):
            self.main_window.reload_camera_lists()

        QMessageBox.information(self, APP_NAME, "Camera removida.")

    def test_camera_connection(self):
        """Test connection to the current camera."""
        try:
            cam = self.current_camera_form()
            ok, status, detail = CameraClient(cam).test_connection()

            if ok:
                QMessageBox.information(
                    self, APP_NAME,
                    f"Conexao OK\nHTTP {status}\nDetalhe: {detail}"
                )
            else:
                QMessageBox.warning(
                    self, APP_NAME,
                    f"Falha HTTP {status}\nDetalhe: {detail}"
                )
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, str(e))

    def manual_snapshot(self):
        """Capture a manual snapshot from the current camera."""
        try:
            cam = self.current_camera_form()
            img, used_url = CameraClient(cam).download_snapshot()

            out = Path(cam["output_dir"]) / "manual"
            out.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file = out / f"{cam['name']}_{timestamp}.jpg"
            file.write_bytes(img)

            if self.main_window and hasattr(self.main_window, "set_preview"):
                self.main_window.set_preview(str(file))

            QMessageBox.information(
                self, APP_NAME,
                f"Snapshot salvo em:\n{file}\nURL: {used_url}"
            )
        except Exception as e:
            QMessageBox.warning(
                self, APP_NAME,
                f"Snapshot nao suportado nesse firmware.\n\nDetalhe:\n{e}"
            )
