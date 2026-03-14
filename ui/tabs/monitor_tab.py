# Monitor tab - live camera monitoring and event streaming
from pathlib import Path

from PySide6.QtCore import Qt, QTimer

# Limite máximo de linhas na tabela de eventos recentes (configurável pela UI)
DEFAULT_MAX_REALTIME_ROWS = 200
REALTIME_MAX_ROWS_OPTIONS = (100, 200, 500)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox, QCheckBox,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QSplitter, QWidget,
    QTabWidget
)

from src.core.config import APP_NAME
from ui.widgets import LiveViewController
from ui.workers import EventWorker, LiveSnapshotWorker
from .base_tab import BaseTab


class MonitorTab(BaseTab):
    """Monitor tab for live camera monitoring and real-time event streaming."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # UI elements - Toolbar
        self.live_camera_combo = None
        self.live_status = None
        self.monitor_count_summary = None

        # UI elements - Live view and event info
        self.live_view = None
        self.lbl_cam = None
        self.lbl_plate = None
        self.lbl_speed = None
        self.lbl_lane = None
        self.lbl_direction = None
        self.lbl_type = None
        self.lbl_image_status = None
        self.monitor_alert = None
        self.monitor_thumbnail = None

        # UI elements - Camera states and activity
        self.monitor_states = None
        self.monitor_log = None

        # UI elements - Realtime events table
        self.realtime_filter_camera = None
        self.realtime_max_rows_combo = None
        self.realtime_table = None
        self.realtime_max_rows = DEFAULT_MAX_REALTIME_ROWS

        # State
        self.live_view_running = False
        self.camera_states = {}

        self.build_ui()

    def build_ui(self):
        """Build the monitor tab UI: toolbar + abas (Principal | Último evento | Estado)."""
        layout = super().build_ui()
        layout.setSpacing(8)

        # Toolbar única e compacta
        toolbar_box = QGroupBox("Controle de monitoramento")
        toolbar = QHBoxLayout(toolbar_box)
        toolbar.setContentsMargins(10, 6, 10, 6)

        self.live_camera_combo = QComboBox()
        self.live_camera_combo.currentTextChanged.connect(self._on_live_camera_changed)

        self.live_status = QLabel("Video ao vivo parado")
        self.live_status.setStyleSheet(
            "padding: 4px 8px; border: 1px solid #c9d2dc; "
            "background: #f4f7fa; color: #243447; border-radius: 4px;"
        )

        btn_live_start = QPushButton("Iniciar video")
        btn_live_start.clicked.connect(self.start_live_view)
        btn_live_stop = QPushButton("Parar video")
        btn_live_stop.clicked.connect(self.stop_live_view)
        self.live_detection_check = QCheckBox("Desenhar detecção ao vivo")
        self.live_detection_check.toggled.connect(self._on_live_detection_toggled)

        btn_start = QPushButton("Iniciar todas")
        btn_start.clicked.connect(self.start_all_monitors)
        btn_stop = QPushButton("Parar todas")
        btn_stop.clicked.connect(self.stop_all_monitors)

        self.monitor_count_summary = QLabel("Online: 0 | Offline: 0")
        self.monitor_count_summary.setStyleSheet(
            "padding: 4px 8px; border: 1px solid #d7dee6; "
            "background: #ffffff; color: #243447; border-radius: 4px;"
        )

        toolbar.addWidget(QLabel("Camera ao vivo"))
        toolbar.addWidget(self.live_camera_combo, 1)
        toolbar.addWidget(btn_live_start)
        toolbar.addWidget(btn_live_stop)
        toolbar.addWidget(self.live_detection_check)
        toolbar.addSpacing(16)
        toolbar.addWidget(btn_start)
        toolbar.addWidget(btn_stop)
        toolbar.addWidget(self.monitor_count_summary)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.live_status, 1)

        layout.addWidget(toolbar_box)

        # Abas: Principal | Último evento | Estado e atividade
        self.monitor_tabs = QTabWidget()

        # ---- Aba Principal: só vídeo + tabela de eventos recentes ----
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        live_panel = QGroupBox("Visualizacao ao vivo")
        live_layout = QVBoxLayout(live_panel)
        live_layout.setContentsMargins(8, 10, 8, 10)
        self.live_view = LiveViewController()
        self.live_view.status_changed.connect(self._on_live_view_status_changed)
        self.live_view.setMinimumHeight(360)
        live_layout.addWidget(self.live_view, 1)
        main_layout.addWidget(live_panel, 2)

        table_box = QGroupBox("Eventos recentes")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_filter = QHBoxLayout()
        self.realtime_filter_camera = QComboBox()
        self.realtime_filter_camera.addItem("")
        self.realtime_filter_camera.currentTextChanged.connect(self.apply_realtime_filter)
        self.realtime_max_rows_combo = QComboBox()
        self.realtime_max_rows_combo.addItems([str(n) for n in REALTIME_MAX_ROWS_OPTIONS])
        self.realtime_max_rows_combo.setCurrentText(str(DEFAULT_MAX_REALTIME_ROWS))
        self.realtime_max_rows_combo.currentTextChanged.connect(self._on_realtime_max_rows_changed)
        table_filter.addWidget(QLabel("Filtrar camera"))
        table_filter.addWidget(self.realtime_filter_camera)
        table_filter.addWidget(QLabel("Max. linhas"))
        table_filter.addWidget(self.realtime_max_rows_combo)
        table_filter.addStretch(1)
        table_layout.addLayout(table_filter)
        self.realtime_table = QTableWidget(0, 6)
        self.realtime_table.setHorizontalHeaderLabels([
            "Camera", "Data/Hora", "Placa", "Velocidade", "Faixa", "Tipo"
        ])
        self._style_data_table(self.realtime_table)
        self.realtime_table.cellDoubleClicked.connect(self.open_realtime_event_image)
        table_layout.addWidget(self.realtime_table)
        main_layout.addWidget(table_box, 3)

        self.monitor_tabs.addTab(main_tab, "Principal")

        # ---- Aba Último evento: thumbnail + dados do último evento ----
        event_tab = QWidget()
        event_layout = QVBoxLayout(event_tab)
        event_layout.setContentsMargins(10, 10, 10, 10)

        right_box = QGroupBox("Último evento")
        right_box.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 13px; "
            "border: 2px solid #0f4c5c; border-radius: 8px; margin-top: 10px; "
            "padding: 12px 12px 8px 12px; padding-top: 18px; "
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e8f4f8, stop:1 #f0f7fa); }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; "
            "color: #0f4c5c; background: transparent; }"
        )
        right_layout = QVBoxLayout(right_box)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(12, 16, 12, 12)

        self.monitor_thumbnail = QLabel("Sem imagem")
        self.monitor_thumbnail.setAlignment(Qt.AlignCenter)
        self.monitor_thumbnail.setMinimumSize(280, 180)
        self.monitor_thumbnail.setStyleSheet(
            "border: 2px solid #b0c4ce; border-radius: 6px; "
            "background: #fbfcfd; color: #687785; font-size: 12px;"
        )
        right_layout.addWidget(self.monitor_thumbnail)

        form_wrap = QWidget()
        self._create_form_layout(form_wrap)
        right_layout.addWidget(form_wrap)

        event_layout.addWidget(right_box)
        self.monitor_tabs.addTab(event_tab, "Último evento")

        # ---- Aba Estado e atividade: estado das câmeras + log ----
        state_tab = QWidget()
        state_tab_layout = QVBoxLayout(state_tab)
        state_tab_layout.setContentsMargins(10, 10, 10, 10)
        state_tab_layout.setSpacing(10)

        state_box = QGroupBox("Estado das cameras")
        state_layout = QVBoxLayout(state_box)
        state_layout.setContentsMargins(10, 10, 10, 10)
        self.monitor_states = self._create_text_edit()
        self.monitor_states.setMinimumHeight(120)
        self.monitor_states.setStyleSheet(
            "background: #fbfcfd; border: 1px solid #d7dee6; color: #243447;"
        )
        state_layout.addWidget(self.monitor_states)

        activity_box = QGroupBox("Atividade")
        activity_layout = QVBoxLayout(activity_box)
        activity_layout.setContentsMargins(10, 10, 10, 10)
        self.monitor_log = self._create_text_edit()
        self.monitor_log.setMinimumHeight(180)
        self.monitor_log.setStyleSheet(
            "background: white; border: 1px solid #d7dee6; color: #243447;"
        )
        activity_layout.addWidget(self.monitor_log)

        state_tab_layout.addWidget(state_box, 1)
        state_tab_layout.addWidget(activity_box, 1)
        self.monitor_tabs.addTab(state_tab, "Estado e atividade")

        layout.addWidget(self.monitor_tabs, 1)
        return layout

    def _create_form_layout(self, parent):
        """Create the form layout for event info."""
        from PySide6.QtWidgets import QFormLayout

        form = QFormLayout(parent)
        form.setSpacing(6)

        # Labels dos valores – placa e velocidade em destaque
        self.lbl_cam = QLabel("-")
        self.lbl_plate = QLabel("-")
        self.lbl_speed = QLabel("-")
        self.lbl_lane = QLabel("-")
        self.lbl_direction = QLabel("-")
        self.lbl_type = QLabel("-")
        self.lbl_image_status = QLabel("-")

        self.lbl_cam.setStyleSheet("font-weight: 600; font-size: 12px; color: #1f2d3d;")
        self.lbl_plate.setStyleSheet(
            "font-weight: 700; font-size: 20px; color: #0f4c5c; "
            "letter-spacing: 1px; padding: 2px 0;"
        )
        self.lbl_speed.setStyleSheet(
            "font-weight: 700; font-size: 20px; color: #8a3b12; padding: 2px 0;"
        )
        self.lbl_lane.setStyleSheet("font-weight: 600; color: #243447;")
        self.lbl_direction.setStyleSheet("font-weight: 600; color: #243447;")
        self.lbl_type.setStyleSheet("font-weight: 600; color: #243447;")
        self.lbl_image_status.setWordWrap(True)
        self.lbl_image_status.setStyleSheet("font-size: 11px; color: #52606d;")

        form.addRow("Câmera:", self.lbl_cam)
        form.addRow("Placa:", self.lbl_plate)
        form.addRow("Velocidade:", self.lbl_speed)
        form.addRow("Faixa:", self.lbl_lane)
        form.addRow("Direção:", self.lbl_direction)
        form.addRow("Tipo:", self.lbl_type)
        form.addRow("Imagem:", self.lbl_image_status)

        # Aviso de velocidade – mais visível
        self.monitor_alert = QLabel("Sem alerta de velocidade")
        self.monitor_alert.setWordWrap(True)
        self.monitor_alert.setMinimumHeight(56)
        self.monitor_alert.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.monitor_alert.setStyleSheet(
            "padding: 10px; border: 1px solid #c9d2dc; "
            "background: #f4f7fa; color: #243447; border-radius: 6px; font-size: 12px;"
        )

        form.addRow("Aviso:", self.monitor_alert)

        return parent

    def _create_text_edit(self):
        """Create a read-only text edit widget."""
        from PySide6.QtWidgets import QTextEdit

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        return text_edit

    def _style_data_table(self, table):
        """Apply styling to a data table."""
        table.setColumnWidth(0, 140)
        table.setColumnWidth(1, 140)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 80)
        table.setColumnWidth(4, 60)
        table.setColumnWidth(5, 140)

        from PySide6.QtWidgets import QHeaderView
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(5, QHeaderView.Interactive)

    def set_camera_list(self, camera_names: list):
        """Update the camera combo and filter dropdown."""
        if self.live_camera_combo:
            current_live = self.live_camera_combo.currentText()
            self.live_camera_combo.clear()
            self.live_camera_combo.addItems(camera_names)
            if current_live:
                idx = self.live_camera_combo.findText(current_live)
                if idx >= 0:
                    self.live_camera_combo.setCurrentIndex(idx)
            self._sync_live_detection_check()

        if self.realtime_filter_camera:
            current_filter = self.realtime_filter_camera.currentText()
            self.realtime_filter_camera.clear()
            self.realtime_filter_camera.addItem("")
            self.realtime_filter_camera.addItems(camera_names)
            if current_filter:
                idx = self.realtime_filter_camera.findText(current_filter)
                if idx >= 0:
                    self.realtime_filter_camera.setCurrentIndex(idx)

    def start_all_monitors(self):
        """Start monitoring for all enabled cameras."""
        if not self.main_window or not hasattr(self.main_window, "start_all_monitors"):
            return

        self.main_window.start_all_monitors()

    def stop_all_monitors(self):
        """Stop monitoring for all cameras."""
        if not self.main_window or not hasattr(self.main_window, "stop_all_monitors"):
            return

        self.main_window.stop_all_monitors()

    def _on_live_camera_changed(self, name: str):
        """Handle live camera combo change."""
        config = self.get_config()
        if not config:
            return

        cam = config.get_camera(name) if name else None
        self.live_view.set_camera(cam)

        self._sync_live_detection_check_from_cam(cam)

        if not cam:
            self.live_status.setText("Video ao vivo parado")
            return

        self.live_status.setText(f"Camera: {name}")

    def _sync_live_detection_check(self):
        """Sincroniza o checkbox de detecção com a câmera atualmente selecionada no combo."""
        config = self.get_config()
        name = self.live_camera_combo.currentText().strip() if self.live_camera_combo else ""
        cam = config.get_camera(name) if config and name else None
        self._sync_live_detection_check_from_cam(cam)

    def _sync_live_detection_check_from_cam(self, cam: dict | None):
        """Atualiza estado do checkbox a partir do config da câmera."""
        if self.live_detection_check is None:
            return
        self.live_detection_check.blockSignals(True)
        self.live_detection_check.setChecked(bool(cam.get("live_detection_enabled", False)) if cam else False)
        self.live_detection_check.setEnabled(bool(cam))
        self.live_detection_check.blockSignals(False)

    def _on_live_detection_toggled(self, checked: bool):
        """Persiste detecção ao vivo na câmera selecionada e reinicia o vídeo se estiver rodando."""
        config = self.get_config()
        if not config or not self.live_camera_combo:
            return
        name = self.live_camera_combo.currentText().strip()
        cam = config.get_camera(name) if name else None
        if not cam:
            return
        cam["live_detection_enabled"] = bool(checked)
        config.save()
        if self.live_view and self.live_view.current_mode != "idle":
            QTimer.singleShot(0, self.start_live_view)

    def start_live_view(self):
        """Start live video view for selected camera."""
        name = self.live_camera_combo.currentText().strip()
        config = self.get_config()
        if not config:
            return

        cam = config.get_camera(name) if name else None
        self.live_view.set_camera(cam)
        self.live_view_running = bool(cam)

        if cam:
            self.live_status.setText("Conectando ao video ao vivo...")
            self.live_view.start()
        else:
            self.live_status.setText("Selecione uma camera para video ao vivo")

    def stop_live_view(self):
        """Stop live video view."""
        self.live_view_running = False
        self.live_view.stop()
        self.live_status.setText("Video ao vivo parado")

    def _on_live_view_status_changed(self, text: str):
        """Handle live view status change."""
        self.live_status.setText(text)

    def update_event_info(self, data: dict):
        """Update the event info panel with new event data."""
        self.lbl_cam.setText(data.get("camera_name") or "-")
        self.lbl_plate.setText(data.get("plate") or "-")
        self.lbl_speed.setText(data.get("speed") or "-")
        self.lbl_lane.setText(data.get("lane") or "-")
        self.lbl_direction.setText(data.get("direction") or "-")
        self.lbl_type.setText(data.get("event_type") or "-")
        self.lbl_image_status.setText(data.get("image_status") or "-")

        if data.get("image_path"):
            self._set_preview(data["image_path"])
            pixmap = QPixmap(data["image_path"])
            if not pixmap.isNull():
                self.monitor_thumbnail.setPixmap(
                    pixmap.scaled(self.monitor_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.monitor_thumbnail.setText("")
        elif self.live_view and self.live_view.current_mode != "rtsp":
            self.live_view.show_message("Sem imagem disponível por ISAPI neste firmware")
        else:
            self.monitor_thumbnail.setPixmap(QPixmap())
            self.monitor_thumbnail.setText("Sem imagem")

    def set_monitor_alert_state(self, text: str, is_alert: bool):
        """Set the monitor alert state."""
        if is_alert:
            self.monitor_alert.setStyleSheet(
                "padding: 10px; border: 1px solid #c96a28; background: #fff0e2; "
                "color: #7a2f0b; font-weight: bold; border-radius: 6px;"
            )
        else:
            self.monitor_alert.setStyleSheet(
                "padding: 10px; border: 1px solid #c9d2dc; background: #f4f7fa; "
                "color: #243447; border-radius: 6px;"
            )
        self.monitor_alert.setText(text)

    def _set_preview(self, path: str):
        """Set the preview image path."""
        if self.main_window and hasattr(self.main_window, "set_preview"):
            self.main_window.set_preview(path)

    def update_camera_state(self, camera_name: str, connected: bool, detail: str):
        """Update camera state tracking."""
        self.camera_states[camera_name] = (connected, detail)
        self._update_camera_state_panel()

    def _update_camera_state_panel(self):
        """Update the camera state display panel."""
        if not self.monitor_states:
            return

        config = self.get_config()
        if not config:
            return

        cards = []
        online = 0
        offline = 0

        for cam in config.data.get("cameras", []):
            name = cam.get("name", "Camera")
            enabled = cam.get("enabled", True)

            if not enabled:
                continue

            connected, detail = self.camera_states.get(name, (False, "nao iniciado"))
            status = "🟢 Online" if connected else "🔴 Offline"
            if connected:
                online += 1
            else:
                offline += 1

            cards.append(f"{name}: {status} ({detail})")

        self.monitor_states.setPlainText("\n".join(cards) if cards else "Nenhuma camera configurada.")
        self.monitor_count_summary.setText(f"Online: {online} | Offline: {offline}")

    def append_realtime_event(self, data: dict):
        """Append an event to the realtime table."""
        self.realtime_table.insertRow(0)

        values = [
            data.get("camera_name", ""),
            data.get("ts", ""),
            data.get("plate", ""),
            data.get("speed", ""),
            data.get("lane", ""),
            data.get("event_type", "")
        ]

        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if col == 0:
                item.setData(Qt.UserRole, data.get("image_path", ""))
                item.setData(Qt.UserRole + 1, data.get("json_path", ""))

            self.realtime_table.setItem(0, col, item)

        # Color coding by camera
        from src.app import color_from_name
        row_color = self._get_row_color(data)
        for col in range(self.realtime_table.columnCount()):
            item = self.realtime_table.item(0, col)
            if item:
                item.setBackground(row_color)

        # Limit rows (valor configurável em "Max. linhas")
        while self.realtime_table.rowCount() > self.realtime_max_rows:
            self.realtime_table.removeRow(self.realtime_table.rowCount() - 1)

        self.apply_realtime_filter()

    def _get_row_color(self, data: dict):
        """Get row color based on event data."""
        from PySide6.QtGui import QColor

        if data.get("is_overspeed"):
            return QColor("#fff0e2")  # Light orange for overspeed

        palette = ["#f7fbff", "#eefaf2", "#fff7e8", "#f7f0ff", "#eef7fb", "#fff0f0"]
        camera_name = data.get("camera_name", "")
        index = sum(ord(ch) for ch in camera_name) % len(palette)
        return QColor(palette[index])

    def _on_realtime_max_rows_changed(self, text):
        """Atualiza o limite de linhas da tabela de eventos recentes e remove excedentes."""
        try:
            self.realtime_max_rows = int(text)
        except ValueError:
            self.realtime_max_rows = DEFAULT_MAX_REALTIME_ROWS
        while self.realtime_table.rowCount() > self.realtime_max_rows:
            self.realtime_table.removeRow(self.realtime_table.rowCount() - 1)

    def apply_realtime_filter(self):
        """Apply camera filter to realtime table."""
        selected_camera = self.realtime_filter_camera.currentText().strip() if self.realtime_filter_camera else ""

        for row in range(self.realtime_table.rowCount()):
            item = self.realtime_table.item(row, 0)
            camera_name = item.text().strip() if item else ""
            self.realtime_table.setRowHidden(row, bool(selected_camera and camera_name != selected_camera))

    def open_realtime_event_image(self, row: int, _column: int):
        """Open the event image for the selected realtime row."""
        item = self.realtime_table.item(row, 0)
        if item is None:
            return

        image_path = item.data(Qt.UserRole) or ""
        json_path = item.data(Qt.UserRole + 1) or ""

        if image_path and Path(image_path).exists():
            self._set_preview(image_path)
            return

        if json_path and Path(json_path).exists():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, APP_NAME,
                f"Evento sem imagem salva.\nJSON disponivel em:\n{json_path}"
            )
            return

        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, APP_NAME, "Este evento nao possui imagem salva.")
