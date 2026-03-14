# History tab - view and filter event history
import math
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox, QCheckBox,
    QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QSpinBox
)

from .base_tab import BaseTab


class HistoryTab(BaseTab):
    """History tab for viewing and filtering event history with pagination."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist_camera = None
        self.hist_plate = None
        self.hist_date = None
        self.hist_min_speed = None
        self.history_table = None
        self.hist_page = 1
        self.hist_total_count = 0
        self.hist_page_size = 100
        self.hist_label_page = None
        self.hist_btn_prev = None
        self.hist_btn_next = None
        self.hist_page_size_combo = None
        self.build_ui()

    def build_ui(self):
        """Build the history tab UI."""
        layout = super().build_ui()

        # Filters section
        filters_box = QGroupBox("Filtros")
        filters_layout = QHBoxLayout(filters_box)

        self.hist_camera = QComboBox()
        self.hist_camera.addItem("")

        self.hist_plate = QLineEdit()
        self.hist_date = QLineEdit()
        self.hist_date.setPlaceholderText("DD/MM/AAAA ou AAAA-MM-DD")
        self.hist_min_speed = QLineEdit()
        self.hist_over_limit = QCheckBox("So excesso de velocidade")

        btn_filter = QPushButton("Filtrar")
        btn_filter.clicked.connect(lambda: self.refresh(reset_page=True))

        for widget in [
            QLabel("Camera"), self.hist_camera,
            QLabel("Placa"), self.hist_plate,
            QLabel("Data"), self.hist_date,
            QLabel("Veloc. min."), self.hist_min_speed,
            self.hist_over_limit,
            btn_filter
        ]:
            filters_layout.addWidget(widget)

        layout.addWidget(filters_box)

        # Paginação
        pagination_layout = QHBoxLayout()
        self.hist_page_size_combo = QComboBox()
        self.hist_page_size_combo.addItems(["50", "100", "250", "500"])
        self.hist_page_size_combo.setCurrentText("100")
        self.hist_page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        self.hist_btn_prev = QPushButton("Anterior")
        self.hist_btn_prev.clicked.connect(self._prev_page)
        self.hist_label_page = QLabel("Pagina 1 de 1 (Total: 0)")
        self.hist_label_page.setStyleSheet("font-weight: 600; color: #486581;")
        self.hist_btn_next = QPushButton("Proxima")
        self.hist_btn_next.clicked.connect(self._next_page)
        pagination_layout.addWidget(QLabel("Registros por pagina:"))
        pagination_layout.addWidget(self.hist_page_size_combo)
        pagination_layout.addWidget(self.hist_btn_prev)
        pagination_layout.addWidget(self.hist_label_page)
        pagination_layout.addWidget(self.hist_btn_next)
        pagination_layout.addStretch(1)
        layout.addLayout(pagination_layout)

        # History table
        self.history_table = QTableWidget(0, 9)
        self.history_table.setHorizontalHeaderLabels([
            "Camera", "Data/Hora", "Placa", "Velocidade",
            "Faixa", "Direcao", "Tipo", "Imagem", "JSON"
        ])
        self._style_table()
        self.history_table.cellDoubleClicked.connect(self.open_item)
        layout.addWidget(self.history_table)

        return layout

    def _style_table(self):
        """Apply styling to the table."""
        self.history_table.setColumnWidth(0, 140)
        self.history_table.setColumnWidth(1, 140)
        self.history_table.setColumnWidth(2, 100)
        self.history_table.setColumnWidth(3, 80)
        self.history_table.setColumnWidth(4, 60)
        self.history_table.setColumnWidth(5, 80)
        self.history_table.setColumnWidth(6, 140)
        self.history_table.setColumnWidth(7, 280)
        self.history_table.setColumnWidth(8, 280)

        header = self.history_table.horizontalHeader()
        from PySide6.QtWidgets import QHeaderView
        header.setStretchLastSection(True)
        header.setSectionResizeMode(7, QHeaderView.Interactive)
        header.setSectionResizeMode(8, QHeaderView.Interactive)

        from PySide6.QtGui import QColor
        from src.app import color_from_name
        for row in range(self.history_table.rowCount()):
            item = self.history_table.item(row, 0)
            if item:
                color = color_from_name(item.text())
                for col in range(self.history_table.columnCount()):
                    cell = self.history_table.item(row, col)
                    if cell:
                        cell.setBackground(color)

    def set_camera_list(self, camera_names: list):
        """Update the camera filter dropdown with available cameras."""
        if self.hist_camera:
            current = self.hist_camera.currentText()
            self.hist_camera.clear()
            self.hist_camera.addItem("")
            self.hist_camera.addItems(camera_names)
            if current:
                idx = self.hist_camera.findText(current)
                if idx >= 0:
                    self.hist_camera.setCurrentIndex(idx)

    def _get_speed_limit_for_filter(self):
        """Limite de velocidade para o filtro 'apenas excesso' (camera selecionada ou global)."""
        config = self.get_config()
        if not config:
            return 60
        camera_name = self.hist_camera.currentText().strip() if self.hist_camera else ""
        if self.main_window and hasattr(self.main_window, "get_camera_speed_settings"):
            limit, _ = self.main_window.get_camera_speed_settings(camera_name or None)
            return float(limit)
        if camera_name:
            cam = config.get_camera(camera_name)
            if cam and cam.get("speed_limit_enabled", True):
                return float(cam.get("speed_limit_value", 60))
        return float(config.data.get("speed_limit", 60))

    def refresh(self, reset_page: bool = False):
        """Refresh the history table with filtered data."""
        db = self.get_database()
        if not db:
            return
        if reset_page:
            self.hist_page = 1

        over_limit = None
        if self.hist_over_limit.isChecked():
            over_limit = self._get_speed_limit_for_filter()

        self.hist_total_count = db.count_filtered_events(
            camera_name=self.hist_camera.currentText().strip(),
            plate=self.hist_plate.text().strip(),
            date_text=self.hist_date.text().strip(),
            min_speed=self.hist_min_speed.text().strip(),
            over_limit=over_limit
        )
        total_pages = max(1, math.ceil(self.hist_total_count / self.hist_page_size))
        self.hist_page = max(1, min(self.hist_page, total_pages))

        rows = db.filtered_events(
            camera_name=self.hist_camera.currentText().strip(),
            plate=self.hist_plate.text().strip(),
            date_text=self.hist_date.text().strip(),
            min_speed=self.hist_min_speed.text().strip(),
            over_limit=over_limit,
            limit=self.hist_page_size,
            offset=(self.hist_page - 1) * self.hist_page_size
        )

        self.history_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.history_table.setItem(r, c, QTableWidgetItem(str(val or "")))

        self._update_pagination_label(total_pages)
        self.hist_btn_prev.setEnabled(self.hist_page > 1)
        self.hist_btn_next.setEnabled(self.hist_page < total_pages)

        # Apply styling after refresh
        self._style_table()

    def _on_page_size_changed(self, text):
        try:
            self.hist_page_size = int(text)
        except ValueError:
            self.hist_page_size = 100
        self.hist_page = 1
        self.refresh()

    def _prev_page(self):
        if self.hist_page > 1:
            self.hist_page -= 1
            self.refresh()

    def _next_page(self):
        total_pages = max(1, math.ceil(self.hist_total_count / self.hist_page_size))
        if self.hist_page < total_pages:
            self.hist_page += 1
            self.refresh()

    def _update_pagination_label(self, total_pages: int):
        if self.hist_label_page:
            self.hist_label_page.setText(
                f"Pagina {self.hist_page} de {total_pages} (Total: {self.hist_total_count})"
            )

    def open_item(self, row: int, _column: int):
        """Open the event artifact (image or JSON) for the selected row."""
        image_item = self.history_table.item(row, 7)
        json_item = self.history_table.item(row, 8)

        image_path = image_item.text().strip() if image_item else ""
        json_path = json_item.text().strip() if json_item else ""

        self._open_event_artifact(image_path, json_path)

    def _open_event_artifact(self, image_path: str, json_path: str):
        """Open an event artifact (image preview or show JSON path)."""
        from pathlib import Path
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt

        if image_path and Path(image_path).exists():
            if self.main_window and hasattr(self.main_window, "set_preview"):
                self.main_window.set_preview(image_path)
            return

        if json_path and Path(json_path).exists():
            from src.core.config import APP_NAME
            QMessageBox.information(
                self, APP_NAME,
                f"Evento sem imagem salva.\nJSON disponivel em:\n{json_path}"
            )
            return

        from src.core.config import APP_NAME
        QMessageBox.information(
            self, APP_NAME,
            "Este registro nao possui imagem ou JSON disponivel."
        )

    def export_csv(self):
        """Export the history table to a CSV file."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import csv
        from src.core.config import APP_NAME, app_dir

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar CSV",
            str(app_dir() / "historico_v42.csv"),
            "CSV (*.csv)"
        )
        if not path:
            return

        db = self.get_database()
        if not db:
            return

        over_limit = None
        if self.hist_over_limit.isChecked():
            over_limit = self._get_speed_limit_for_filter()

        rows = db.filtered_events(
            camera_name=self.hist_camera.currentText().strip(),
            plate=self.hist_plate.text().strip(),
            date_text=self.hist_date.text().strip(),
            min_speed=self.hist_min_speed.text().strip(),
            over_limit=over_limit
        )

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Câmera", "Data/Hora", "Placa", "Velocidade",
                "Faixa", "Direção", "Tipo", "Imagem", "JSON"
            ])
            writer.writerows(rows)

        QMessageBox.information(self, APP_NAME, f"CSV exportado:\n{path}")
