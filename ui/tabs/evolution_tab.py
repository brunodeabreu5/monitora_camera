# Evolution API tab - integrate with Evolution API for WhatsApp alerts
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QPushButton, QLabel, QCheckBox, QComboBox,
    QMessageBox, QProgressBar, QTextEdit, QSplitter, QWidget, QTabWidget
)

from src.core.config import (
    APP_NAME, now_str, parse_recipient_numbers, render_event_message, sanitize_phone_number
)
from src.core.evolution_client import EvolutionApiClient, EvolutionSendWorker, EvolutionTestSendWorker
from ui.widgets import PasswordField
from .base_tab import BaseTab


class EvolutionTab(BaseTab):
    """Evolution API tab for WhatsApp integration configuration and testing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # UI elements - Config
        self.evo_enabled = None
        self.evo_url = None
        self.evo_token = None
        self.evo_instance = None
        self.evo_mode = None
        self.evo_recipients = None
        self.evo_send_image = None

        # UI elements - Instance/Test
        self.evo_status = None
        self.evo_qr_label = None
        self.evo_test_number = None
        self.evo_test_message = None
        self.evo_sending_widget = None
        self.evo_sending_progress = None
        self.evo_sending_label = None
        self._test_send_worker = None

        # UI elements - Template
        self.evo_event_template = None
        self.evo_template_preview = None

        self.build_ui()

    def build_ui(self):
        """Build the Evolution API tab UI with sub-tabs."""
        layout = super().build_ui()

        evo_tabs = QTabWidget()
        evo_tabs.setDocumentMode(True)

        tab_config = QWidget()
        tab_instance = QWidget()
        tab_template = QWidget()

        evo_tabs.addTab(tab_config, "Configuracao")
        evo_tabs.addTab(tab_instance, "Instancia e teste")
        evo_tabs.addTab(tab_template, "Template")

        # Build sub-tabs
        self._build_config_tab(tab_config)
        self._build_instance_tab(tab_instance)
        self._build_template_tab(tab_template)

        layout.addWidget(evo_tabs)

        # Load settings after UI is built
        self.load_settings_into_ui()

        return layout

    def _build_config_tab(self, tab):
        """Build the configuration sub-tab."""
        config_layout = QVBoxLayout(tab)
        config_layout.setContentsMargins(0, 0, 0, 0)

        form_box = QGroupBox("Configuracao da Evolution API")
        form = QFormLayout(form_box)
        form.setContentsMargins(10, 8, 10, 10)
        form.setVerticalSpacing(6)

        self.evo_enabled = QCheckBox("Habilitar integracao Evolution API")
        self.evo_url = QLineEdit()
        self.evo_token = PasswordField()
        self.evo_instance = QLineEdit()
        self.evo_mode = QComboBox()
        self.evo_mode.addItems(["create_or_connect", "existing"])
        self.evo_recipients = QTextEdit()
        self.evo_recipients.setPlaceholderText("5511999999999\n5511888888888")
        self.evo_recipients.setMaximumHeight(90)
        self.evo_send_image = QCheckBox("Enviar foto com a mensagem (snapshot da camera no momento do evento)")
        self.evo_send_image.setChecked(True)
        self.evo_send_image.setToolTip("Ative tambem 'Salvar snapshot no evento' na aba Cameras para cada camera que deve enviar imagem.")

        form.addRow("", self.evo_enabled)
        form.addRow("URL:", self.evo_url)
        form.addRow("Token:", self.evo_token)
        form.addRow("Instancia:", self.evo_instance)
        form.addRow("Modo:", self.evo_mode)
        form.addRow("Numeros:", self.evo_recipients)
        form.addRow("", self.evo_send_image)

        config_layout.addWidget(form_box)

        # Buttons
        btns_wrap = QWidget()
        btns = QHBoxLayout(btns_wrap)
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(6)

        for text, slot in [
            ("Salvar", self.save_settings),
            ("Testar API", self.test_connection),
            ("Conectar instancia", self.connect_instance),
            ("Atualizar QR", self.refresh_qr)
        ]:
            button = QPushButton(text)
            button.setMinimumWidth(120)
            button.setMaximumWidth(150)
            button.clicked.connect(slot)
            btns.addWidget(button)

        btns.addStretch(1)
        config_layout.addWidget(btns_wrap)
        config_layout.addStretch(1)

    def _build_instance_tab(self, tab):
        """Build the instance and test sub-tab."""
        instance_layout_root = QVBoxLayout(tab)
        instance_layout_root.setContentsMargins(0, 0, 0, 0)

        # Indicador de envio (spinner)
        self.evo_sending_widget = QWidget()
        sending_layout = QHBoxLayout(self.evo_sending_widget)
        sending_layout.setContentsMargins(0, 6, 0, 6)
        self.evo_sending_progress = QProgressBar()
        self.evo_sending_progress.setRange(0, 0)
        self.evo_sending_progress.setMaximumHeight(22)
        self.evo_sending_progress.setMaximumWidth(200)
        self.evo_sending_label = QLabel("Enviando pela Evolution API...")
        self.evo_sending_label.setStyleSheet("color: #687785;")
        sending_layout.addWidget(self.evo_sending_progress)
        sending_layout.addWidget(self.evo_sending_label)
        sending_layout.addStretch(1)
        self.evo_sending_widget.setVisible(False)
        instance_layout_root.addWidget(self.evo_sending_widget)

        details_splitter = QSplitter(Qt.Horizontal)
        details_splitter.setChildrenCollapsible(False)

        # Status section
        status_box = QGroupBox("Status da instancia")
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(10, 8, 10, 10)
        status_layout.setSpacing(6)

        self.evo_status = QLabel("Evolution API nao configurada.")
        self.evo_status.setWordWrap(True)

        self.evo_qr_label = QLabel("QR Code indisponivel")
        self.evo_qr_label.setAlignment(Qt.AlignCenter)
        self.evo_qr_label.setMinimumHeight(150)
        self.evo_qr_label.setMaximumHeight(180)
        self.evo_qr_label.setStyleSheet(
            "border: 1px solid #d7dee6; background: #fbfcfd; color: #687785;"
        )

        status_layout.addWidget(self.evo_status)
        status_layout.addWidget(self.evo_qr_label)

        # Test message section
        test_box = QGroupBox("Mensagem de teste")
        test_form = QFormLayout(test_box)
        test_form.setContentsMargins(10, 8, 10, 10)
        test_form.setVerticalSpacing(6)

        self.evo_test_number = QLineEdit()
        self.evo_test_message = QTextEdit()
        self.evo_test_message.setMinimumHeight(72)
        self.evo_test_message.setMaximumHeight(96)
        self.evo_test_message.setPlaceholderText("Mensagem de teste da Evolution API")

        btn_send_test = QPushButton("Enviar teste")
        btn_send_test.setMaximumWidth(120)
        btn_send_test.clicked.connect(self.send_test_message)

        test_form.addRow("Numero:", self.evo_test_number)
        test_form.addRow("Mensagem:", self.evo_test_message)
        test_form.addRow("", btn_send_test)

        details_splitter.addWidget(status_box)
        details_splitter.addWidget(test_box)
        details_splitter.setStretchFactor(0, 3)
        details_splitter.setStretchFactor(1, 2)

        instance_layout_root.addWidget(details_splitter, 1)

    def _build_template_tab(self, tab):
        """Build the message template sub-tab."""
        template_root_layout = QVBoxLayout(tab)
        template_root_layout.setContentsMargins(0, 0, 0, 0)

        template_box = QGroupBox("Template dos eventos")
        template_layout = QVBoxLayout(template_box)
        template_layout.setContentsMargins(10, 8, 10, 10)
        template_layout.setSpacing(6)

        self.evo_event_template = QTextEdit()
        self.evo_event_template.setMinimumHeight(110)
        self.evo_event_template.setMaximumHeight(160)
        self.evo_event_template.setPlaceholderText(
            "Use variaveis como {camera}, {plate}, {speed}, {limit}, {ts}, {lane}, {direction}, {event_type}"
        )
        self.evo_event_template.textChanged.connect(self._update_template_preview)

        # Variable buttons
        variable_wrap = QWidget()
        variable_row = QHBoxLayout(variable_wrap)
        variable_row.setContentsMargins(0, 0, 0, 0)
        variable_row.setSpacing(4)

        for variable in [
            "{camera}", "{plate}", "{speed}", "{limit}",
            "{ts}", "{lane}", "{direction}", "{event_type}"
        ]:
            button = QPushButton(variable)
            button.setMaximumWidth(92)
            button.clicked.connect(
                lambda _checked=False, value=variable: self._insert_template_variable(value)
            )
            variable_row.addWidget(button)

        variable_row.addStretch(1)

        template_help = QLabel(
            "Variaveis disponiveis: {camera}, {plate}, {speed}, {limit}, {ts}, {lane}, {direction}, {event_type}"
        )
        template_help.setWordWrap(True)

        # Preview section
        preview_box = QGroupBox("Preview da mensagem")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(10, 8, 10, 10)

        self.evo_template_preview = QTextEdit()
        self.evo_template_preview.setReadOnly(True)
        self.evo_template_preview.setMinimumHeight(110)
        self.evo_template_preview.setMaximumHeight(160)
        preview_layout.addWidget(self.evo_template_preview)

        template_splitter = QSplitter(Qt.Horizontal)
        template_splitter.setChildrenCollapsible(False)

        template_editor_wrap = QWidget()
        template_editor_layout = QVBoxLayout(template_editor_wrap)
        template_editor_layout.setContentsMargins(0, 0, 0, 0)
        template_editor_layout.setSpacing(6)
        template_editor_layout.addWidget(self.evo_event_template)
        template_editor_layout.addWidget(variable_wrap)

        template_splitter.addWidget(template_editor_wrap)
        template_splitter.addWidget(preview_box)
        template_splitter.setStretchFactor(0, 3)
        template_splitter.setStretchFactor(1, 2)

        template_layout.addWidget(template_splitter)
        template_layout.addWidget(template_help)

        template_root_layout.addWidget(template_box)
        template_root_layout.addStretch(1)

    def current_form(self) -> dict:
        """Get Evolution API configuration from the form."""
        return {
            "enabled": self.evo_enabled.isChecked(),
            "base_url": self.evo_url.text().strip(),
            "api_token": self.evo_token.text().strip(),
            "instance_name": self.evo_instance.text().strip(),
            "instance_mode": self.evo_mode.currentText(),
            "recipient_numbers": parse_recipient_numbers(self.evo_recipients.toPlainText()),
            "send_image_with_caption": self.evo_send_image.isChecked(),
            "test_target_number": sanitize_phone_number(self.evo_test_number.text()),
            "test_message_text": self.evo_test_message.toPlainText(),
            "event_message_template": self.evo_event_template.toPlainText(),
        }

    def load_settings_into_ui(self):
        """Load Evolution API settings from config into the UI."""
        config = self.get_config()
        if not config:
            return

        cfg = config.data.get("evolution_api", {})

        self.evo_enabled.setChecked(bool(cfg.get("enabled", False)))
        self.evo_url.setText(cfg.get("base_url", ""))
        self.evo_token.setText(cfg.get("api_token", ""))
        self.evo_instance.setText(cfg.get("instance_name", ""))

        mode = cfg.get("instance_mode", "create_or_connect")
        idx = self.evo_mode.findText(mode)
        self.evo_mode.setCurrentIndex(max(idx, 0))

        self.evo_recipients.setPlainText("\n".join(cfg.get("recipient_numbers", [])))
        self.evo_send_image.setChecked(bool(cfg.get("send_image_with_caption", True)))
        self.evo_test_number.setText(cfg.get("test_target_number", ""))
        self.evo_test_message.setPlainText(cfg.get("test_message_text", ""))
        self.evo_event_template.setPlainText(cfg.get("event_message_template", ""))

        self._update_status_label()
        self._update_template_preview()

    def _persist_evolution_config(self) -> bool:
        """Write current form to config and save to disk. Returns True on success."""
        config = self.get_config()
        if not config:
            QMessageBox.warning(self, APP_NAME, "Configuracao indisponivel. Reinicie o aplicativo.")
            return False
        form = self.current_form()
        if form.get("enabled"):
            if not (form.get("base_url") or "").strip():
                QMessageBox.warning(self, APP_NAME, "Com a integracao habilitada, informe a URL da Evolution API.")
                return False
            if not (form.get("api_token") or "").strip():
                QMessageBox.warning(self, APP_NAME, "Com a integracao habilitada, informe o Token da Evolution API.")
                return False
            if not (form.get("instance_name") or "").strip():
                QMessageBox.warning(self, APP_NAME, "Com a integracao habilitada, informe o nome da Instancia.")
                return False
        config.data["evolution_api"] = form
        try:
            config.save()
            return True
        except Exception as e:
            QMessageBox.critical(
                self, APP_NAME,
                f"Nao foi possivel salvar a configuracao em disco:\n{config.filepath}\n\n{e}"
            )
            return False

    def save_settings(self):
        """Salva a configuracao da Evolution API em disco (mesmo arquivo das cameras: hikvision_pro_v42_config.json)."""
        if not self._persist_evolution_config():
            return
        self.load_settings_into_ui()
        config = self.get_config()
        path_msg = str(config.filepath) if config else ""
        QMessageBox.information(
            self, APP_NAME,
            f"Configuracao da Evolution API salva com sucesso em:\n{path_msg}"
        )

    def _update_status_label(self, extra_text: str = ""):
        """Update the status label with current Evolution API status."""
        config = self.get_config()
        if not config:
            return

        cfg = config.data.get("evolution_api", {})
        recipients = cfg.get("recipient_numbers", [])

        style = "padding: 8px; border: 1px solid #d7dee6; background: #fbfcfd; color: #425466; border-radius: 6px;"

        if extra_text:
            self.evo_status.setText(extra_text)
            extra_lower = extra_text.lower()
            if "validada" in extra_lower or "conectada" in extra_lower or "pronta" in extra_lower:
                style = "padding: 8px; border: 1px solid #b8dfc5; background: #eefaf2; color: #1d6b3a; border-radius: 6px; font-weight: 600;"
            elif "qr" in extra_lower:
                style = "padding: 8px; border: 1px solid #e6d39b; background: #fff8e1; color: #8a6d1a; border-radius: 6px; font-weight: 600;"
            elif "falha" in extra_lower or "erro" in extra_lower:
                style = "padding: 8px; border: 1px solid #e2b4b4; background: #fdecec; color: #9c2f2f; border-radius: 6px; font-weight: 600;"
            self.evo_status.setStyleSheet(style)
            return

        enabled_text = "habilitada" if cfg.get("enabled") else "desabilitada"
        self.evo_status.setText(
            f"Integracao {enabled_text} | Instancia: {cfg.get('instance_name') or '-'} | "
            f"Destinatarios: {len(recipients)}"
        )
        if cfg.get("enabled"):
            style = "padding: 8px; border: 1px solid #d7dee6; background: #f4f7fa; color: #243447; border-radius: 6px; font-weight: 600;"
        self.evo_status.setStyleSheet(style)

    def _preview_data(self) -> dict:
        """Get preview data for template preview."""
        # Try to get real data from main window if available
        if self.main_window:
            data = {}
            if hasattr(self.main_window, "lbl_cam"):
                cam_text = self.main_window.lbl_cam.text().strip()
                data["camera_name"] = cam_text if cam_text and cam_text not in ("", "-") else "Camera 1"
            if hasattr(self.main_window, "lbl_plate"):
                plate_text = self.main_window.lbl_plate.text().strip()
                data["plate"] = plate_text if plate_text and plate_text not in ("", "-") else "ABC1D23"
            if hasattr(self.main_window, "lbl_speed"):
                speed_text = self.main_window.lbl_speed.text().strip()
                data["speed"] = speed_text if speed_text and speed_text not in ("", "-") else "72"

        # Fallback to default preview data
        if not data.get("camera_name"):
            data = {
                "camera_name": "Camera 1",
                "plate": "ABC1D23",
                "speed": "72",
                "applied_speed_limit": 60.0,
                "ts": now_str(),
                "lane": "1",
                "direction": "Entrada",
                "event_type": "velocity",
            }

        return data

    def _update_template_preview(self):
        """Update the template preview with current template and preview data."""
        if not self.evo_template_preview:
            return

        template = self.evo_event_template.toPlainText() if hasattr(self, "evo_event_template") else ""
        preview_text = render_event_message(template, self._preview_data())
        self.evo_template_preview.setPlainText(preview_text)

    def _insert_template_variable(self, variable: str):
        """Insert a template variable at cursor position."""
        cursor = self.evo_event_template.textCursor()
        cursor.insertText(variable)
        self.evo_event_template.setFocus()
        self._update_template_preview()

    def _client_from_form(self) -> EvolutionApiClient:
        """Create an EvolutionApiClient from the current form data."""
        config = self.get_config()
        if not config:
            raise RuntimeError("Configuration not available")

        cfg = self.current_form()
        config.data["evolution_api"] = cfg
        config._normalize_evolution_api()
        return EvolutionApiClient(config.data["evolution_api"])

    def test_connection(self):
        """Test the connection to Evolution API."""
        try:
            client = self._client_from_form()
            data = client.test_connection()
            count = len(data) if isinstance(data, list) else len(data.get("instances", [])) if isinstance(data, dict) else 0
            self._update_status_label(f"Evolution API conectada. Instancias encontradas: {count}")
            QMessageBox.information(self, APP_NAME, "Conexao com Evolution API validada.")
        except Exception as exc:
            self._update_status_label(f"Falha na Evolution API: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def _show_qr(self, qr_payload: str):
        """Display the QR code for WhatsApp connection."""
        if not qr_payload:
            self.evo_qr_label.setPixmap(QPixmap())
            self.evo_qr_label.setText("QR Code indisponivel")
            return

        try:
            client = self._client_from_form()
            pixmap = client.build_qr_pixmap(qr_payload)
            if pixmap.isNull():
                self.evo_qr_label.setPixmap(QPixmap())
                self.evo_qr_label.setText(f"QR recebido, mas nao foi possivel renderizar.\n\nConteudo:\n{qr_payload[:300]}")
                return
            self.evo_qr_label.setText("")
            self.evo_qr_label.setPixmap(pixmap.scaled(self.evo_qr_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            self.evo_qr_label.setText(f"Erro ao renderizar QR: {e}")

    def connect_instance(self):
        """Connect to or create an Evolution API instance."""
        try:
            client = self._client_from_form()
            create_if_missing = self.evo_mode.currentText() == "create_or_connect"
            state = client.ensure_instance(create_if_missing=create_if_missing)
            qr_payload = client.fetch_qr_payload()
            self._show_qr(qr_payload)
            self._update_status_label(f"Instancia pronta. Estado: {state}")
            self.save_settings()
        except Exception as exc:
            self._update_status_label(f"Falha ao conectar instancia: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def refresh_qr(self):
        """Refresh the QR code for the Evolution API instance."""
        try:
            client = self._client_from_form()
            qr_payload = client.fetch_qr_payload()
            self._show_qr(qr_payload)
            self._update_status_label("QR Code atualizado.")
        except Exception as exc:
            self._update_status_label(f"Falha ao atualizar QR: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def send_test_message(self):
        """Send a test message through Evolution API (em thread, com spinner)."""
        number = sanitize_phone_number(self.evo_test_number.text())
        message = self.evo_test_message.toPlainText().strip()

        if not number:
            QMessageBox.warning(self, APP_NAME, "Informe o numero de teste.")
            return
        if not message:
            QMessageBox.warning(self, APP_NAME, "Informe a mensagem de teste.")
            return

        config = self.get_config()
        if not config:
            return
        cfg = self.current_form()
        config.data["evolution_api"] = cfg
        config._normalize_evolution_api()
        evolution_cfg = dict(config.data.get("evolution_api", {}))

        if self._test_send_worker is not None and self._test_send_worker.isRunning():
            return

        self._test_send_worker = EvolutionTestSendWorker(evolution_cfg, number, message)
        self._test_send_worker.finished.connect(self._on_test_send_finished)
        self._show_sending_indicator()
        self._test_send_worker.start()

    def _on_test_send_finished(self, error_msg):
        """Chamado quando o envio de teste termina."""
        worker = self._test_send_worker
        self._test_send_worker = None
        if worker is not None:
            worker.wait(5000)
        self._hide_sending_indicator()
        number = sanitize_phone_number(self.evo_test_number.text())

        if error_msg is None:
            self._update_status_label(f"Mensagem de teste enviada para {number}.")
            if self.main_window and hasattr(self.main_window, "append_log"):
                self.main_window.append_log(f"Evolution API: teste enviado para {number}.")
            QMessageBox.information(self, APP_NAME, "Mensagem de teste enviada.")
        else:
            self._update_status_label(f"Falha no teste Evolution: {error_msg}")
            QMessageBox.warning(self, APP_NAME, error_msg)

    def _show_sending_indicator(self):
        """Exibe o spinner de envio da Evolution API."""
        if self.evo_sending_widget is not None:
            self.evo_sending_widget.setVisible(True)

    def _hide_sending_indicator(self):
        """Esconde o spinner quando não há envios em andamento."""
        if self.evo_sending_widget is None:
            return
        if self.main_window and hasattr(self.main_window, "evolution_workers"):
            if len(self.main_window.evolution_workers) > 0:
                return
        if self._test_send_worker is not None and self._test_send_worker.isRunning():
            return
        self.evo_sending_widget.setVisible(False)

    def send_alert(self, event_data: dict, recipients: list):
        """Send an alert through Evolution API (called from main window)."""
        config = self.get_config()
        if not config:
            return

        evolution_cfg = dict(config.data.get("evolution_api", {}))
        worker = EvolutionSendWorker(evolution_cfg, event_data, recipients)

        # Connect signals
        if self.main_window and hasattr(self.main_window, "append_log"):
            worker.finished_status.connect(self.main_window.append_log)
        else:
            # Fallback: just print
            print(f"Evolution API: Alert sent for event {event_data.get('plate')}")

        # Clean up worker when done
        worker.finished_status.connect(
            lambda _text, w=worker: self._release_worker(w)
        )

        # Store worker reference (main window should track this)
        if self.main_window and hasattr(self.main_window, "evolution_workers"):
            self.main_window.evolution_workers.append(worker)

        self._show_sending_indicator()
        worker.start()

    def _release_worker(self, worker):
        """Remove worker from tracking when done; wait for thread to avoid QThread destroyed while running."""
        if worker is not None:
            worker.wait(5000)
        if self.main_window and hasattr(self.main_window, "evolution_workers"):
            if worker in self.main_window.evolution_workers:
                self.main_window.evolution_workers.remove(worker)
        self._hide_sending_indicator()
