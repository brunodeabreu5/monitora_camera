# Hikvision Radar Pro V4.2 – MainWindow e entry point (resto nos módulos config, database, etc.)
import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QAction, QColor, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QSpinBox, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QGroupBox,
    QHeaderView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QListWidget,
    QListWidgetItem, QSplitter, QScrollArea, QSystemTrayIcon, QMenu, QStyle,
)

from src.core.camera_client import CameraClient
from src.core.config import (
    APP_NAME,
    DB_FILE,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD,
    EVT_IDX_APPLIED_LIMIT,
    EVT_IDX_CAMERA_NAME,
    EVT_IDX_DIRECTION,
    EVT_IDX_EVENT_TYPE,
    EVT_IDX_IMAGE_PATH,
    EVT_IDX_JSON_PATH,
    EVT_IDX_LANE,
    EVT_IDX_PLATE,
    EVT_IDX_SPEED,
    EVT_IDX_SPEED_VALUE,
    EVT_IDX_TS,
    EVT_IDX_IS_OVERSPEED,
    AppConfig,
    app_dir,
    extract_speed_value,
    hash_password,
    log_runtime_error,
    now_str,
    parse_recipient_numbers,
    render_event_message,
    sanitize_phone_number,
)
from src.core.database import Database
from src.core.evolution_client import EvolutionApiClient, EvolutionSendWorker
from ui.widgets import LiveViewController, PasswordField
from ui.workers import EventWorker, LiveSnapshotWorker
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.users_tab import UsersTab
from ui.tabs.history_tab import HistoryTab
from ui.tabs.report_tab import ReportTab
from ui.tabs.cameras_tab import CamerasTab
from ui.tabs.evolution_tab import EvolutionTab
from ui.tabs.monitor_tab import MonitorTab


def color_from_name(text: str) -> QColor:
    palette = ["#f7fbff", "#eefaf2", "#fff7e8", "#f7f0ff", "#eef7fb", "#fff0f0"]
    index = sum(ord(ch) for ch in text) % len(palette)
    return QColor(palette[index])


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, logged_user: dict):
        super().__init__()
        self.config = config
        self.logged_user = logged_user
        self.setWindowTitle(f"{APP_NAME} - {logged_user.get('username')} ({logged_user.get('role')})")
        self.resize(1360, 900)
        self.setMinimumSize(QSize(1100, 740))
        default_output = Path(app_dir() / "output")
        default_output.mkdir(parents=True, exist_ok=True)
        self.db = Database(default_output / DB_FILE)
        self.workers = {}
        self.evolution_workers = []
        self.camera_states = {}
        self.last_image_path = ""
        self.live_view_running = False
        self._allow_close = False
        self._tray_message_shown = False
        self.build_ui()
        # Set references to monitor tab UI elements for event processing
        self._setup_monitor_tab_references()
        self.setup_tray_icon()
        self.reload_camera_lists()
        self.refresh_dashboard(); self.refresh_history(); self.refresh_report()
        if self.config.user_requires_password_change(self.logged_user.get("username", "")):
            QMessageBox.warning(self, APP_NAME, "Este usuario ainda usa a senha padrao. Abra a aba Usuarios e defina uma nova senha.")

    def build_scroll_tab(self, inner_widget):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame); scroll.setWidget(inner_widget); return scroll

    def apply_app_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #f3f6f8;
                color: #243447;
            }
            QTabWidget::pane {
                border: 1px solid #d7dee6;
                background: #f3f6f8;
            }
            QTabBar::tab {
                background: #e8eef3;
                color: #425466;
                padding: 8px 14px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #102a43;
                font-weight: 600;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d7dee6;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #486581;
            }
            QPushButton {
                background: #e6eef5;
                border: 1px solid #c6d2de;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #dbe7f1;
            }
            QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget, QTableWidget {
                background: #ffffff;
                border: 1px solid #d7dee6;
                border-radius: 6px;
                padding: 4px;
            }
            QHeaderView::section {
                background: #eef3f7;
                color: #425466;
                padding: 6px;
                border: none;
                border-right: 1px solid #d7dee6;
                border-bottom: 1px solid #d7dee6;
                font-weight: 600;
            }
        """)

    def style_data_table(self, table: QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setStyleSheet("alternate-background-color: #f7fafc; background: #ffffff;")

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        self.apply_app_theme()
        main = QVBoxLayout(root); main.setContentsMargins(8, 8, 8, 8); main.setSpacing(8)
        tabs = QTabWidget(); tabs.setDocumentMode(True); main.addWidget(tabs)

        # Create dashboard tab
        self.tab_dashboard = DashboardTab(); self.tab_dashboard.set_main_window(self)
        # Create users tab
        self.tab_users = UsersTab(); self.tab_users.set_main_window(self); self.tab_users.set_logged_user(self.logged_user)
        # Create history and report tabs
        self.tab_history = HistoryTab(); self.tab_history.set_main_window(self)
        self.tab_report = ReportTab(); self.tab_report.set_main_window(self)
        # Create cameras tab
        self.tab_cameras = CamerasTab(); self.tab_cameras.set_main_window(self)
        # Create evolution tab
        self.tab_evolution = EvolutionTab(); self.tab_evolution.set_main_window(self)
        # Create monitor tab
        self.tab_monitor = MonitorTab(); self.tab_monitor.set_main_window(self)
        tabs.addTab(self.build_scroll_tab(self.tab_dashboard), "Dashboard")
        tabs.addTab(self.build_scroll_tab(self.tab_cameras), "Cameras")
        tabs.addTab(self.build_scroll_tab(self.tab_monitor), "Monitor")
        tabs.addTab(self.build_scroll_tab(self.tab_history), "Historico")
        tabs.addTab(self.build_scroll_tab(self.tab_report), "Excesso de velocidade")
        tabs.addTab(self.build_scroll_tab(self.tab_evolution), "Evolution API")
        tabs.addTab(self.build_scroll_tab(self.tab_users), "Usuarios")

        file_menu = self.menuBar().addMenu("Arquivo")
        act_export = QAction("Exportar historico CSV", self); act_export.triggered.connect(self.export_csv); file_menu.addAction(act_export)
        act_export_over = QAction("Exportar excesso CSV", self); act_export_over.triggered.connect(self.export_overspeed_csv); file_menu.addAction(act_export_over)
        act_hide = QAction("Enviar para bandeja", self); act_hide.triggered.connect(self.hide_to_tray); file_menu.addAction(act_hide)
        act_exit = QAction("Sair", self); act_exit.triggered.connect(self.quit_application); file_menu.addAction(act_exit)

    def setup_tray_icon(self):
        self.tray_icon = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        self.tray_icon.setToolTip(APP_NAME)
        tray_menu = QMenu(self)
        tray_menu.addAction("Abrir painel", self.show_window_from_tray)
        tray_menu.addAction("Iniciar monitoramento", self.start_all_monitors)
        tray_menu.addAction("Parar monitoramento", self.stop_all_monitors)
        tray_menu.addSeparator()
        tray_menu.addAction("Sair", self.quit_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.show_window_from_tray()

    def show_window_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self):
        if self.tray_icon is None:
            return
        self.hide()
        if not self._tray_message_shown:
            self.tray_icon.showMessage(APP_NAME, "O monitoramento continua em segundo plano na bandeja do sistema.", QSystemTrayIcon.Information, 3000)
            self._tray_message_shown = True

    def quit_application(self):
        self._allow_close = True
        self.close()

    def append_log(self, text):
        """Append a log message to the dashboard and monitor logs."""
        self.tab_dashboard.append_log(text)

    def reload_camera_lists(self):
        """Reload camera lists in all tabs - delegates to cameras tab and notifies other tabs."""
        names = self.config.get_camera_names()
        # Update camera lists in history and report tabs
        self.tab_history.set_camera_list(names)
        self.tab_report.set_camera_list(names)
        # Also reload the cameras tab list
        self.tab_cameras.reload_camera_list()
        # Update monitor tab camera lists
        self.tab_monitor.set_camera_list(names)

    def _setup_monitor_tab_references(self):
        """Set up references to monitor tab UI elements for event processing."""
        # Get references to monitor tab UI elements
        self.live_camera_combo = self.tab_monitor.live_camera_combo
        self.live_status = self.tab_monitor.live_status
        self.monitor_count_summary = self.tab_monitor.monitor_count_summary
        self.live_view = self.tab_monitor.live_view
        self.lbl_cam = self.tab_monitor.lbl_cam
        self.lbl_plate = self.tab_monitor.lbl_plate
        self.lbl_speed = self.tab_monitor.lbl_speed
        self.lbl_lane = self.tab_monitor.lbl_lane
        self.lbl_direction = self.tab_monitor.lbl_direction
        self.lbl_type = self.tab_monitor.lbl_type
        self.lbl_image_status = self.tab_monitor.lbl_image_status
        self.monitor_alert = self.tab_monitor.monitor_alert
        self.monitor_thumbnail = self.tab_monitor.monitor_thumbnail
        self.monitor_states = self.tab_monitor.monitor_states
        self.monitor_log = self.tab_monitor.monitor_log
        self.realtime_filter_camera = self.tab_monitor.realtime_filter_camera
        self.realtime_table = self.tab_monitor.realtime_table

        # Update live view status connection
        self.live_view.status_changed.connect(self.on_live_view_status_changed)
        names = self.config.get_camera_names()
        if hasattr(self, "live_camera_combo"):
            selected = self.live_camera_combo.currentText().strip()
            self.live_camera_combo.blockSignals(True)
            self.live_camera_combo.clear(); self.live_camera_combo.addItems(names)
            if selected and selected in names:
                self.live_camera_combo.setCurrentText(selected)
            elif names:
                self.live_camera_combo.setCurrentIndex(0)
            self.live_camera_combo.blockSignals(False)
            self.on_live_camera_changed(self.live_camera_combo.currentText())
        if hasattr(self, "realtime_filter_camera"):
            selected_filter = self.realtime_filter_camera.currentText().strip()
            self.realtime_filter_camera.blockSignals(True)
            self.realtime_filter_camera.clear()
            self.realtime_filter_camera.addItem("")
            self.realtime_filter_camera.addItems(names)
            if selected_filter and selected_filter in names:
                self.realtime_filter_camera.setCurrentText(selected_filter)
            self.realtime_filter_camera.blockSignals(False)
            self.apply_realtime_filter()
        if hasattr(self, "evo_status"):
            self.update_evolution_status_label()

    def start_all_monitors(self):
        self.stop_all_monitors(log_message=False); started = 0
        for cam in self.config.data.get("cameras", []):
            if not cam.get("enabled", True): continue
            worker = EventWorker(cam); worker.status.connect(self.append_log); worker.connection_state.connect(self.on_connection_state); worker.event_received.connect(self.on_event_received); self.workers[cam["name"]] = worker; worker.start(); started += 1
        self.append_log(f"Monitoramento iniciado para {started} camera(s).")

    def stop_all_monitors(self, log_message=True):
        for _, worker in list(self.workers.items()): worker.stop(); worker.wait(3000)
        self.workers = {}; self.camera_states = {}; self.update_camera_state_panel()
        if log_message: self.append_log("Todos os monitores foram parados.")

    def on_connection_state(self, camera_name, connected, detail):
        """Handle camera connection state change - delegates to monitor tab."""
        self.camera_states[camera_name] = (connected, detail)
        self.tab_monitor.update_camera_state(camera_name, connected, detail)

    def update_camera_state_panel(self):
        cards = []
        online = 0
        offline = 0
        for cam in self.config.data.get("cameras", []):
            name = cam.get("name", "Camera")
            connected, detail = self.camera_states.get(name, (False, "sem conexão"))
            if connected:
                online += 1
            else:
                offline += 1
            badge_bg = "#e7f6ec" if connected else "#fdecec"
            badge_fg = "#1d6b3a" if connected else "#9c2f2f"
            badge_text = "Conectada" if connected else "Desconectada"
            cards.append(
                f"<div style='margin:0 0 8px 0; padding:8px 10px; border:1px solid #d7dee6; border-radius:6px; background:#ffffff;'>"
                f"<div style='font-weight:600; color:#1f2d3d; margin-bottom:4px;'>{name}</div>"
                f"<span style='display:inline-block; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:{badge_fg}; font-weight:600;'>{badge_text}</span>"
                f"<div style='margin-top:6px; color:#4b5b6b;'>{detail}</div>"
                f"</div>"
            )
        self.monitor_states.setHtml("".join(cards) if cards else "<div style='color:#4b5b6b;'>Sem câmeras configuradas.</div>")
        if hasattr(self, "monitor_count_summary"):
            self.monitor_count_summary.setText(f"Online: {online} | Offline: {offline}")

    def on_live_camera_changed(self, name):
        cam = self.config.get_camera(name) if name else None
        self.live_view.set_camera(cam)
        if not cam:
            self.live_status.setText("Video ao vivo parado")
            return
        if self.live_view_running:
            self.start_live_view()

    def start_live_view(self):
        name = self.live_camera_combo.currentText().strip()
        cam = self.config.get_camera(name) if name else None
        self.live_view.set_camera(cam)
        self.live_view_running = bool(cam)
        if cam:
            self.live_view.start()
        else:
            self.live_status.setText("Selecione uma camera para video ao vivo")

    def stop_live_view(self):
        self.live_view_running = False
        self.live_view.stop()
        self.live_status.setText("Video ao vivo parado")

    def on_live_view_status_changed(self, text):
        self.live_status.setText(text)

    def maybe_send_evolution_alert(self, data: dict):
        """Send Evolution API alert if configured - delegates to evolution tab."""
        evolution_cfg = dict(self.config.data.get("evolution_api", {}))
        if not evolution_cfg.get("enabled"):
            return

        camera_cfg = self.config.get_camera(data.get("camera_name", ""))
        if not camera_cfg or not camera_cfg.get("evolution_enabled", False):
            return

        recipients = evolution_cfg.get("recipient_numbers", [])
        if not recipients:
            self.append_log("Evolution API: nenhum destinatario configurado.")
            return

        # Delegate to evolution tab
        self.tab_evolution.send_alert(dict(data), recipients)

    def _release_evolution_worker(self, worker):
        """Remove completed evolution worker from tracking."""
        self.evolution_workers = [item for item in self.evolution_workers if item is not worker]

    def get_camera_speed_settings(self, camera_name: str):
        camera = self.config.get_camera(camera_name) if camera_name else None
        global_limit = int(self.config.data.get("speed_limit", 60))
        if not camera:
            return global_limit, True
        limit_enabled = bool(camera.get("speed_limit_enabled", True))
        limit_value = int(camera.get("speed_limit_value", global_limit))
        visual_enabled = bool(camera.get("speed_alert_visual", True))
        return (limit_value if limit_enabled else global_limit), visual_enabled

    def resolve_row_overspeed(self, row):
        applied_limit = row[EVT_IDX_APPLIED_LIMIT]
        is_overspeed = row[EVT_IDX_IS_OVERSPEED]
        if applied_limit is not None and is_overspeed is not None:
            return float(applied_limit), bool(is_overspeed)
        limit, _ = self.get_camera_speed_settings(row[EVT_IDX_CAMERA_NAME])
        return float(limit), float(row[EVT_IDX_SPEED_VALUE] or 0) > float(limit)

    def set_monitor_alert_state(self, text: str, is_alert: bool):
        if is_alert:
            self.monitor_alert.setStyleSheet("padding: 10px; border: 1px solid #c96a28; background: #fff0e2; color: #7a2f0b; font-weight: bold; border-radius: 6px;")
        else:
            self.monitor_alert.setStyleSheet("padding: 10px; border: 1px solid #c9d2dc; background: #f4f7fa; color: #243447; border-radius: 6px;")
        self.monitor_alert.setText(text)

    def on_event_received(self, data):
        """Process received event - updates monitor tab and handles alerts."""
        # Update monitor tab event info
        self.tab_monitor.update_event_info(data)

        # Handle image preview
        if data.get("image_path"):
            self.set_preview(data["image_path"])
            pixmap = QPixmap(data["image_path"])
            if not pixmap.isNull():
                self.monitor_thumbnail.setPixmap(pixmap.scaled(self.monitor_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.monitor_thumbnail.setText("")
        elif self.live_view.current_mode != "rtsp":
            self.live_view.show_message("Sem imagem disponível por ISAPI neste firmware")
        else:
            self.monitor_thumbnail.setPixmap(QPixmap())
            self.monitor_thumbnail.setText("Sem imagem")

        # Process speed and trigger actions
        speed_text = (data.get("speed") or "").strip()
        if not speed_text:
            log_runtime_error(
                "Evento sem velocidade parseada",
                RuntimeError(
                    f"camera={data.get('camera_name')!r} event_type={data.get('event_type')!r} plate={data.get('plate')!r}; "
                    "verifique se o XML da camera usa tags speed/vehicleSpeed/vehicleSpeedValue ou acrescente em parsing.py"
                )
            )
        speed_value = extract_speed_value(data.get("speed", ""))
        limit, visual_enabled = self.get_camera_speed_settings(data.get("camera_name", ""))
        data["applied_speed_limit"] = float(limit)
        data["is_overspeed"] = speed_value > float(limit)

        # Save to database and update UI
        try:
            self.db.insert_event(data)
            self.append_log(f"Evento gravado no banco: {data.get('camera_name')} / placa {data.get('plate') or '-'} / {data.get('ts')}")
        except Exception as e:
            log_runtime_error("Falha ao gravar evento no banco", e)
            self.append_log(f"ERRO: evento nao gravado no banco ({e})")
        self.prepend_realtime_event(data)
        self.refresh_dashboard()
        self.refresh_history()
        self.refresh_report()

        # Handle overspeed alert
        if data["is_overspeed"]:
            self.append_log(f"ALERTA: {data.get('camera_name')} placa {data.get('plate') or '-'} acima do limite ({speed_value} > {limit} km/h)")
            if visual_enabled:
                self.tab_monitor.set_monitor_alert_state(
                    f"ALERTA de velocidade: {data.get('camera_name')} | placa {data.get('plate') or '-'} | {speed_value} km/h | limite {limit} km/h",
                    True
                )
            else:
                self.tab_monitor.set_monitor_alert_state(
                    f"Evento acima do limite sem aviso visual: limite {limit} km/h",
                    False
                )
            self.maybe_send_evolution_alert(data)
        else:
            self.append_log(f"Evento: {data.get('camera_name')} / placa={data.get('plate') or '-'} / velocidade={data.get('speed') or '-'} / {data.get('image_status', '')}")
            self.tab_monitor.set_monitor_alert_state(
                f"Velocidade dentro do limite: {speed_value} km/h de {data.get('camera_name')} (limite {limit} km/h)",
                False
            )

    def prepend_realtime_event(self, data):
        """Append event to realtime table - delegates to monitor tab."""
        self.tab_monitor.append_realtime_event(data)

    def apply_realtime_filter(self):
        """Apply realtime filter - delegates to monitor tab."""
        self.tab_monitor.apply_realtime_filter()

    def open_realtime_event_image(self, row, _column):
        """Open realtime event image - delegates to monitor tab."""
        self.tab_monitor.open_realtime_event_image(row, _column)

    def open_history_item(self, row, _column):
        """Open history item - delegates to history tab."""
        self.tab_history.open_item(row, _column)

    def open_report_item(self, row, _column):
        """Open report item - delegates to report tab."""
        self.tab_report.open_item(row, _column)

    def open_event_artifact(self, image_path: str, json_path: str):
        if image_path and Path(image_path).exists():
            self.set_preview(image_path)
            return
        if json_path and Path(json_path).exists():
            QMessageBox.information(self, APP_NAME, f"Evento sem imagem salva.\nJSON disponivel em:\n{json_path}")
            return
        QMessageBox.information(self, APP_NAME, "Este registro nao possui imagem ou JSON disponivel.")

    def set_preview(self, path):
        self.last_image_path = path
        self.live_view.show_image_path(path)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.last_image_path: self.set_preview(self.last_image_path)
        thumb = self.monitor_thumbnail.pixmap() if hasattr(self, "monitor_thumbnail") else None
        if thumb is not None and not thumb.isNull() and self.last_image_path and Path(self.last_image_path).exists():
            pixmap = QPixmap(self.last_image_path)
            if not pixmap.isNull():
                self.monitor_thumbnail.setPixmap(pixmap.scaled(self.monitor_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        evo_qr = self.evo_qr_label.pixmap() if hasattr(self, "evo_qr_label") else None
        if evo_qr is not None and not evo_qr.isNull():
            self.evo_qr_label.setPixmap(evo_qr.scaled(self.evo_qr_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def refresh_dashboard(self):
        """Refresh dashboard statistics."""
        self.tab_dashboard.refresh()

    def refresh_history(self):
        """Refresh history table - delegates to history tab."""
        self.tab_history.refresh()

    def apply_speed_limit_and_refresh_report(self):
        """Apply speed limit and refresh report - delegates to report tab."""
        self.tab_report.apply_and_refresh()

    def refresh_report(self):
        """Refresh report table - delegates to report tab."""
        self.tab_report.refresh()

    def export_csv(self):
        """Export history to CSV - delegates to history tab."""
        self.tab_history.export_csv()

    def export_overspeed_csv(self):
        """Export overspeed report to CSV - delegates to report tab."""
        self.tab_report.export_csv()

    def closeEvent(self, event):
        if self._allow_close or self.tray_icon is None:
            self.stop_live_view()
            self.stop_all_monitors(log_message=False)
            if self.tray_icon is not None:
                self.tray_icon.hide()
            self.db.close()
            event.accept()
            return
        self.hide_to_tray()
        event.ignore()

def main():
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setQuitOnLastWindowClosed(False)
    config = AppConfig(); login = LoginDialog(config)
    if login.exec() != QDialog.Accepted: sys.exit(0)
    win = MainWindow(config, login.user_data); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
