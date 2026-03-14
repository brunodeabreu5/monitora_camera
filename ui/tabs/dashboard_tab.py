# Dashboard tab - shows event statistics and system activity log
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit
from PySide6.QtGui import QFont

from src.core.config import now_str
from .base_tab import BaseTab


class DashboardTab(BaseTab):
    """Dashboard tab showing event statistics and system activity log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lbl_total = None
        self.lbl_today = None
        self.lbl_overspeed = None
        self.lbl_last_plate = None
        self.dashboard_log = None
        self.build_ui()

    def build_ui(self):
        """Build the dashboard UI with statistics cards and activity log."""
        layout = super().build_ui()
        top = QHBoxLayout()

        # Create statistics labels
        self.lbl_total = QLabel("0")
        self.lbl_today = QLabel("0")
        self.lbl_overspeed = QLabel("0")
        self.lbl_last_plate = QLabel("-")

        # Create statistics cards
        for title, widget in [
            ("Total de eventos", self.lbl_total),
            ("Eventos hoje", self.lbl_today),
            ("Acima do limite", self.lbl_overspeed),
            ("Ultima placa", self.lbl_last_plate)
        ]:
            box = QGroupBox(title)
            vb = QVBoxLayout(box)
            widget.setStyleSheet("font-size: 28px; font-weight: 700; color: #102a43;")
            vb.addWidget(widget)
            top.addWidget(box)

        layout.addLayout(top)

        # Create system activity log
        log_box = QGroupBox("Atividade do sistema")
        log_layout = QVBoxLayout(log_box)
        self.dashboard_log = QTextEdit()
        self.dashboard_log.setReadOnly(True)
        self.dashboard_log.setMinimumHeight(320)
        log_layout.addWidget(self.dashboard_log)
        layout.addWidget(log_box)

        return layout

    def refresh(self):
        """Refresh dashboard statistics from database."""
        if not self.main_window:
            return

        db = self.get_database()
        if not db:
            return

        stats = db.dashboard_event_speeds()
        overspeed = 0

        for row in stats["rows"]:
            applied_limit = row[2]
            is_overspeed = row[3]
            if applied_limit is not None and is_overspeed is not None:
                overspeed += 1 if is_overspeed else 0
                continue
            # Fallback: calculate overspeed from camera settings
            limit, _ = self.main_window.get_camera_speed_settings(row[0])
            if float(row[1] or 0) > float(limit):
                overspeed += 1

        self.lbl_total.setText(str(stats["total"]))
        self.lbl_today.setText(str(stats["today"]))
        self.lbl_overspeed.setText(str(overspeed))
        self.lbl_last_plate.setText(stats["last_plate"] or "-")

    def append_log(self, text: str):
        """Append a log message to the dashboard activity log."""
        if self.dashboard_log:
            stamp = now_str()
            line = f"[{stamp}] {text}"
            self.dashboard_log.append(line)
            # Also append to monitor log if it exists
            if self.main_window and hasattr(self.main_window, "monitor_log"):
                self.main_window.monitor_log.append(line)
