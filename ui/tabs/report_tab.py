# Report tab - overspeed events report with export
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QSpinBox
)

from src.core.config import EVT_IDX_CAMERA_NAME, EVT_IDX_TS, EVT_IDX_PLATE, EVT_IDX_SPEED
from src.core.config import EVT_IDX_LANE, EVT_IDX_DIRECTION, EVT_IDX_EVENT_TYPE
from src.core.config import EVT_IDX_IMAGE_PATH, EVT_IDX_JSON_PATH, EVT_IDX_APPLIED_LIMIT, EVT_IDX_IS_OVERSPEED
from .base_tab import BaseTab


class ReportTab(BaseTab):
    """Report tab for viewing overspeed events and exporting to CSV."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_limit_spin = None
        self.report_camera = None
        self.report_date = None
        self.report_summary = None
        self.report_table = None
        self.build_ui()

    def build_ui(self):
        """Build the report tab UI."""
        layout = super().build_ui()

        # Parameters section
        top_box = QGroupBox("Parametros do relatorio")
        top = QHBoxLayout(top_box)

        config = self.get_config()
        default_limit = config.data.get("speed_limit", 60) if config else 60

        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(1, 300)
        self.speed_limit_spin.setValue(int(default_limit))

        self.report_camera = QComboBox()
        self.report_camera.addItem("")

        self.report_date = QLineEdit()

        btn_apply = QPushButton("Aplicar")
        btn_apply.clicked.connect(self.apply_and_refresh)

        btn_export = QPushButton("Exportar CSV")
        btn_export.clicked.connect(self.export_csv)

        for widget in [
            QLabel("Limite (km/h)"), self.speed_limit_spin,
            QLabel("Camera"), self.report_camera,
            QLabel("Data"), self.report_date,
            btn_apply, btn_export
        ]:
            top.addWidget(widget)

        top.addStretch(1)
        layout.addWidget(top_box)

        # Summary section
        summary_box = QGroupBox("Resumo")
        summary_layout = QVBoxLayout(summary_box)

        self.report_summary = QLabel("-")
        self.report_summary.setWordWrap(True)
        self.report_summary.setStyleSheet("font-weight: 600; color: #486581;")
        summary_layout.addWidget(self.report_summary)
        layout.addWidget(summary_box)

        # Report table
        self.report_table = QTableWidget(0, 9)
        self.report_table.setHorizontalHeaderLabels([
            "Camera", "Data/Hora", "Placa", "Velocidade",
            "Faixa", "Direcao", "Tipo", "Imagem", "JSON"
        ])
        self._style_table()
        self.report_table.cellDoubleClicked.connect(self.open_item)
        layout.addWidget(self.report_table)

        return layout

    def _style_table(self):
        """Apply styling to the table."""
        self.report_table.setColumnWidth(0, 140)
        self.report_table.setColumnWidth(1, 140)
        self.report_table.setColumnWidth(2, 100)
        self.report_table.setColumnWidth(3, 80)
        self.report_table.setColumnWidth(4, 60)
        self.report_table.setColumnWidth(5, 80)
        self.report_table.setColumnWidth(6, 140)
        self.report_table.setColumnWidth(7, 280)
        self.report_table.setColumnWidth(8, 280)

        header = self.report_table.horizontalHeader()
        from PySide6.QtWidgets import QHeaderView
        header.setStretchLastSection(True)
        header.setSectionResizeMode(7, QHeaderView.Interactive)
        header.setSectionResizeMode(8, QHeaderView.Interactive)

    def set_camera_list(self, camera_names: list):
        """Update the camera filter dropdown with available cameras."""
        if self.report_camera:
            current = self.report_camera.currentText()
            self.report_camera.clear()
            self.report_camera.addItem("")
            self.report_camera.addItems(camera_names)
            if current:
                idx = self.report_camera.findText(current)
                if idx >= 0:
                    self.report_camera.setCurrentIndex(idx)

    def apply_and_refresh(self):
        """Apply speed limit settings and refresh the report."""
        config = self.get_config()
        if config:
            config.data["speed_limit"] = int(self.speed_limit_spin.value())
            config.save()

        self.refresh()

        # Also refresh dashboard if available
        if self.main_window and hasattr(self.main_window, "refresh_dashboard"):
            self.main_window.refresh_dashboard()

    def refresh(self):
        """Refresh the report table with overspeed data."""
        db = self.get_database()
        if not db:
            return

        selected_camera = self.report_camera.currentText().strip()
        rows = db.recent_events_with_speed(
            camera_name=selected_camera,
            date_text=self.report_date.text().strip()
        )

        # Filter overspeed rows
        overspeed_rows = self._filter_overspeed_rows(rows, selected_camera)

        self.report_table.setRowCount(len(overspeed_rows))
        for r, row in enumerate(overspeed_rows):
            display_row = (
                row[EVT_IDX_CAMERA_NAME], row[EVT_IDX_TS], row[EVT_IDX_PLATE],
                row[EVT_IDX_SPEED], row[EVT_IDX_LANE], row[EVT_IDX_DIRECTION],
                row[EVT_IDX_EVENT_TYPE], row[EVT_IDX_IMAGE_PATH], row[EVT_IDX_JSON_PATH]
            )
            for c, val in enumerate(display_row):
                self.report_table.setItem(r, c, QTableWidgetItem(str(val or "")))

        # Update summary
        summary_limit = self.speed_limit_spin.value() if not selected_camera else self._get_camera_speed_limit(selected_camera)
        self.report_summary.setText(
            f"Limite base: {summary_limit} km/h | Eventos acima do limite efetivo: {len(overspeed_rows)}"
        )

    def _filter_overspeed_rows(self, rows, selected_camera=""):
        """Filter rows to only include overspeed events."""
        filtered = []
        for row in rows:
            camera_name = row[EVT_IDX_CAMERA_NAME]
            if selected_camera and camera_name != selected_camera:
                continue

            _, is_overspeed = self._resolve_row_overspeed(row)
            if is_overspeed:
                filtered.append(row)

        return filtered

    def _resolve_row_overspeed(self, row):
        """Determine if a row represents an overspeed event."""
        from src.core.config import extract_speed_value

        applied_limit = row[EVT_IDX_APPLIED_LIMIT]
        is_overspeed = row[EVT_IDX_IS_OVERSPEED]

        if applied_limit is not None and is_overspeed is not None:
            return applied_limit, bool(is_overspeed)

        # Fallback: calculate from camera settings
        limit, _ = self._get_camera_speed_settings(row[EVT_IDX_CAMERA_NAME])
        speed_value = extract_speed_value(row[EVT_IDX_SPEED] or "")
        return limit, speed_value > float(limit)

    def _get_camera_speed_limit(self, camera_name: str) -> float:
        """Get the speed limit for a specific camera."""
        limit, _ = self._get_camera_speed_settings(camera_name)
        return float(limit)

    def _get_camera_speed_settings(self, camera_name: str):
        """Get camera speed settings from config."""
        if not self.main_window or not hasattr(self.main_window, "get_camera_speed_settings"):
            # Fallback to global config
            config = self.get_config()
            if config:
                return config.data.get("speed_limit", 60), True
            return 60, True

        return self.main_window.get_camera_speed_settings(camera_name)

    def open_item(self, row: int, _column: int):
        """Open the event artifact (image or JSON) for the selected row."""
        image_item = self.report_table.item(row, 7)
        json_item = self.report_table.item(row, 8)

        image_path = image_item.text().strip() if image_item else ""
        json_path = json_item.text().strip() if json_item else ""

        self._open_event_artifact(image_path, json_path)

    def _open_event_artifact(self, image_path: str, json_path: str):
        """Open an event artifact (image preview or show JSON path)."""
        from pathlib import Path
        from PySide6.QtWidgets import QMessageBox
        from src.core.config import APP_NAME

        if image_path and Path(image_path).exists():
            if self.main_window and hasattr(self.main_window, "set_preview"):
                self.main_window.set_preview(image_path)
            return

        if json_path and Path(json_path).exists():
            QMessageBox.information(
                self, APP_NAME,
                f"Evento sem imagem salva.\nJSON disponivel em:\n{json_path}"
            )
            return

        QMessageBox.information(
            self, APP_NAME,
            "Este registro nao possui imagem ou JSON disponivel."
        )

    def export_csv(self):
        """Export the overspeed report to a CSV file."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import csv
        from src.core.config import APP_NAME, app_dir

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar CSV",
            str(app_dir() / "excesso_velocidade_v42.csv"),
            "CSV (*.csv)"
        )
        if not path:
            return

        db = self.get_database()
        if not db:
            return

        selected_camera = self.report_camera.currentText().strip()
        rows = db.recent_events_with_speed(
            camera_name=selected_camera,
            date_text=self.report_date.text().strip()
        )
        overspeed_rows = self._filter_overspeed_rows(rows, selected_camera)

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Câmera", "Data/Hora", "Placa", "Velocidade",
                "Faixa", "Direção", "Tipo", "Imagem", "JSON"
            ])
            for row in overspeed_rows:
                display_row = (
                    row[EVT_IDX_CAMERA_NAME], row[EVT_IDX_TS], row[EVT_IDX_PLATE],
                    row[EVT_IDX_SPEED], row[EVT_IDX_LANE], row[EVT_IDX_DIRECTION],
                    row[EVT_IDX_EVENT_TYPE], row[EVT_IDX_IMAGE_PATH], row[EVT_IDX_JSON_PATH]
                )
                writer.writerow(display_row)

        QMessageBox.information(self, APP_NAME, f"CSV de excesso exportado:\n{path}")
