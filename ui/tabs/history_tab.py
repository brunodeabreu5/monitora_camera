# History tab - view and filter event history
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem
)

from .base_tab import BaseTab


class HistoryTab(BaseTab):
    """History tab for viewing and filtering event history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist_camera = None
        self.hist_plate = None
        self.hist_date = None
        self.hist_min_speed = None
        self.history_table = None
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
        self.hist_min_speed = QLineEdit()

        btn_filter = QPushButton("Filtrar")
        btn_filter.clicked.connect(self.refresh)

        for widget in [
            QLabel("Camera"), self.hist_camera,
            QLabel("Placa"), self.hist_plate,
            QLabel("Data"), self.hist_date,
            QLabel("Veloc. min."), self.hist_min_speed,
            btn_filter
        ]:
            filters_layout.addWidget(widget)

        layout.addWidget(filters_box)

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

    def refresh(self):
        """Refresh the history table with filtered data."""
        db = self.get_database()
        if not db:
            return

        rows = db.filtered_events(
            camera_name=self.hist_camera.currentText().strip(),
            plate=self.hist_plate.text().strip(),
            date_text=self.hist_date.text().strip(),
            min_speed=self.hist_min_speed.text().strip(),
            over_limit=None
        )

        self.history_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.history_table.setItem(r, c, QTableWidgetItem(str(val or "")))

        # Apply styling after refresh
        self._style_table()

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

        rows = db.filtered_events(
            camera_name=self.hist_camera.currentText().strip(),
            plate=self.hist_plate.text().strip(),
            date_text=self.hist_date.text().strip(),
            min_speed=self.hist_min_speed.text().strip(),
            over_limit=None
        )

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Câmera", "Data/Hora", "Placa", "Velocidade",
                "Faixa", "Direção", "Tipo", "Imagem", "JSON"
            ])
            writer.writerows(rows)

        QMessageBox.information(self, APP_NAME, f"CSV exportado:\n{path}")
