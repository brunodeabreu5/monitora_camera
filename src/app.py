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
        self.tab_users = UsersTab(); self.tab_users.set_main_window(self); self.tab_users.set_logged_user(logged_user)
        # Create history and report tabs
        self.tab_history = HistoryTab(); self.tab_history.set_main_window(self)
        self.tab_report = ReportTab(); self.tab_report.set_main_window(self)
        self.tab_cameras = QWidget(); self.tab_monitor = QWidget(); self.tab_evolution = QWidget()
        tabs.addTab(self.build_scroll_tab(self.tab_dashboard), "Dashboard")
        tabs.addTab(self.build_scroll_tab(self.tab_cameras), "Cameras")
        tabs.addTab(self.build_scroll_tab(self.tab_monitor), "Monitor")
        tabs.addTab(self.build_scroll_tab(self.tab_history), "Historico")
        tabs.addTab(self.build_scroll_tab(self.tab_report), "Excesso de velocidade")
        tabs.addTab(self.build_scroll_tab(self.tab_evolution), "Evolution API")
        tabs.addTab(self.build_scroll_tab(self.tab_users), "Usuarios")

        self.build_cameras_tab(); self.build_monitor_tab(); self.build_evolution_tab()
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

    def build_cameras_tab(self):
        layout = QVBoxLayout(self.tab_cameras); splitter = QSplitter(Qt.Horizontal); splitter.setChildrenCollapsible(False)
        left_panel = QGroupBox("Cameras cadastradas"); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(10,10,10,10)
        self.camera_list = QListWidget(); self.camera_list.currentTextChanged.connect(self.load_selected_camera); left_layout.addWidget(self.camera_list)

        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel); right_layout.setContentsMargins(0,0,0,0)
        form_box = QGroupBox("Configuracao da camera"); form = QFormLayout(form_box)
        self.cam_name = QLineEdit(); self.cam_ip = QLineEdit(); self.cam_port = QSpinBox(); self.cam_port.setRange(1,65535); self.cam_port.setValue(80)
        self.cam_user = QLineEdit(); self.cam_pass = PasswordField()
        self.cam_channel = QSpinBox(); self.cam_channel.setRange(1,999); self.cam_channel.setValue(101)
        self.cam_timeout = QSpinBox(); self.cam_timeout.setRange(1,120); self.cam_timeout.setValue(15)
        self.cam_rtsp_enabled = QCheckBox("Habilitar video ao vivo (RTSP)"); self.cam_rtsp_enabled.setChecked(True)
        self.cam_rtsp_port = QSpinBox(); self.cam_rtsp_port.setRange(1,65535); self.cam_rtsp_port.setValue(554)
        self.cam_rtsp_transport = QComboBox(); self.cam_rtsp_transport.addItems(["tcp", "udp"])
        self.cam_rtsp_url = QLineEdit()
        self.cam_live_fallback = QComboBox(); self.cam_live_fallback.addItems(["snapshot", "none"])
        self.cam_speed_limit_enabled = QCheckBox("Habilitar aviso de velocidade"); self.cam_speed_limit_enabled.setChecked(True)
        self.cam_speed_limit = QSpinBox(); self.cam_speed_limit.setRange(1,300); self.cam_speed_limit.setValue(int(self.config.data.get("speed_limit", 60)))
        self.cam_speed_alert_visual = QCheckBox("Mostrar aviso visual na tela"); self.cam_speed_alert_visual.setChecked(True)
        self.cam_evolution_enabled = QCheckBox("Enviar excesso pela Evolution API")
        self.cam_output = QLineEdit(); self.cam_enabled = QCheckBox("Ativa para monitoramento"); self.cam_snapshot = QCheckBox("Salvar snapshot automatico por evento")
        self.cam_mode = QComboBox(); self.cam_mode.addItems(["auto", "traffic", "normal"])
        browse = QPushButton("Escolher pasta"); browse.clicked.connect(self.choose_output_dir)
        out_wrap = QWidget(); out_row = QHBoxLayout(out_wrap); out_row.setContentsMargins(0,0,0,0); out_row.addWidget(self.cam_output,1); out_row.addWidget(browse,0)
        form.addRow("Nome:", self.cam_name); form.addRow("IP:", self.cam_ip); form.addRow("Porta HTTP:", self.cam_port); form.addRow("Usuario:", self.cam_user)
        form.addRow("Senha:", self.cam_pass); form.addRow("Canal:", self.cam_channel); form.addRow("Timeout:", self.cam_timeout); form.addRow("Modo da camera:", self.cam_mode)
        form.addRow("", self.cam_rtsp_enabled); form.addRow("Porta RTSP:", self.cam_rtsp_port); form.addRow("Preferencia RTSP:", self.cam_rtsp_transport); form.addRow("URL RTSP:", self.cam_rtsp_url); form.addRow("Fallback live:", self.cam_live_fallback)
        form.addRow("", self.cam_speed_limit_enabled); form.addRow("Limite veloc. (km/h):", self.cam_speed_limit); form.addRow("", self.cam_speed_alert_visual)
        form.addRow("", self.cam_evolution_enabled)
        form.addRow("Pasta:", out_wrap); form.addRow("", self.cam_enabled); form.addRow("", self.cam_snapshot)
        right_layout.addWidget(form_box)
        note = QLabel("Para iDS-TCM403-GIR, use 'traffic' ou 'auto'. Video ao vivo usa RTSP embutido; se o player falhar, o app pode cair para snapshots ao vivo. Esta versão usa apenas o alertStream padrão /ISAPI/Event/notification/alertStream para eventos."); note.setWordWrap(True); note.setStyleSheet("padding: 8px; border: 1px solid #d7dee6; background: #f7fafc; border-radius: 6px; color: #486581;"); right_layout.addWidget(note)
        btns_wrap = QWidget(); btns = QHBoxLayout(btns_wrap); btns.setContentsMargins(0,0,0,0)
        for text, slot in [("Nova camera", self.new_camera), ("Salvar camera", self.save_camera), ("Excluir camera", self.delete_camera), ("Testar conexao", self.test_camera_connection), ("Snapshot manual", self.manual_snapshot)]:
            b = QPushButton(text); b.clicked.connect(slot); btns.addWidget(b)
        btns.addStretch(1); right_layout.addWidget(btns_wrap); right_layout.addStretch(1)
        splitter.addWidget(left_panel); splitter.addWidget(right_panel); splitter.setStretchFactor(0,1); splitter.setStretchFactor(1,3); layout.addWidget(splitter)

    def build_monitor_tab(self):
        layout = QVBoxLayout(self.tab_monitor)
        layout.setSpacing(10)

        toolbar_box = QGroupBox("Controle de monitoramento")
        toolbar = QHBoxLayout(toolbar_box)
        toolbar.setContentsMargins(10, 8, 10, 8)
        self.live_camera_combo = QComboBox(); self.live_camera_combo.currentTextChanged.connect(self.on_live_camera_changed)
        self.live_status = QLabel("Video ao vivo parado")
        self.live_status.setStyleSheet("padding: 4px 8px; border: 1px solid #c9d2dc; background: #f4f7fa; color: #243447; border-radius: 4px;")
        btn_live_start = QPushButton("Iniciar video"); btn_live_start.clicked.connect(self.start_live_view)
        btn_live_stop = QPushButton("Parar video"); btn_live_stop.clicked.connect(self.stop_live_view)
        btn_start = QPushButton("Iniciar todas"); btn_start.clicked.connect(self.start_all_monitors)
        btn_stop = QPushButton("Parar todas"); btn_stop.clicked.connect(self.stop_all_monitors)
        self.monitor_count_summary = QLabel("Online: 0 | Offline: 0")
        self.monitor_count_summary.setStyleSheet("padding: 4px 8px; border: 1px solid #d7dee6; background: #ffffff; color: #243447; border-radius: 4px;")
        toolbar.addWidget(QLabel("Camera ao vivo"))
        toolbar.addWidget(self.live_camera_combo, 1)
        toolbar.addWidget(btn_live_start)
        toolbar.addWidget(btn_live_stop)
        toolbar.addSpacing(12)
        toolbar.addWidget(btn_start)
        toolbar.addWidget(btn_stop)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.monitor_count_summary)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.live_status, 1)
        layout.addWidget(toolbar_box)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setChildrenCollapsible(False)

        live_panel = QGroupBox("Visualizacao ao vivo")
        live_layout = QVBoxLayout(live_panel)
        live_layout.setContentsMargins(10, 10, 10, 10)
        self.live_view = LiveViewController(); self.live_view.status_changed.connect(self.on_live_view_status_changed)
        self.live_view.setMinimumHeight(420)
        live_layout.addWidget(self.live_view, 1)

        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)

        right_box = QGroupBox("Ultimo evento")
        right_layout = QHBoxLayout(right_box)
        form_wrap = QWidget()
        form = QFormLayout(form_wrap)
        self.lbl_cam = QLabel("-"); self.lbl_plate = QLabel("-"); self.lbl_speed = QLabel("-"); self.lbl_lane = QLabel("-"); self.lbl_direction = QLabel("-"); self.lbl_type = QLabel("-"); self.lbl_image_status = QLabel("-")
        self.lbl_cam.setStyleSheet("font-weight: 600; color: #1f2d3d;")
        self.lbl_plate.setStyleSheet("font-weight: 700; font-size: 18px; color: #0f4c5c;")
        self.lbl_speed.setStyleSheet("font-weight: 700; font-size: 18px; color: #8a3b12;")
        self.lbl_image_status.setWordWrap(True)
        form.addRow("Camera:", self.lbl_cam); form.addRow("Placa:", self.lbl_plate); form.addRow("Velocidade:", self.lbl_speed); form.addRow("Faixa:", self.lbl_lane); form.addRow("Direcao:", self.lbl_direction); form.addRow("Tipo:", self.lbl_type); form.addRow("Imagem:", self.lbl_image_status)
        self.monitor_alert = QLabel("Sem alerta de velocidade")
        self.monitor_alert.setWordWrap(True)
        self.monitor_alert.setMinimumHeight(78)
        self.monitor_alert.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.monitor_alert.setStyleSheet("padding: 10px; border: 1px solid #c9d2dc; background: #f4f7fa; color: #243447; border-radius: 6px;")
        form.addRow("Aviso:", self.monitor_alert)
        self.monitor_thumbnail = QLabel("Sem imagem")
        self.monitor_thumbnail.setAlignment(Qt.AlignCenter)
        self.monitor_thumbnail.setMinimumSize(180, 120)
        self.monitor_thumbnail.setStyleSheet("border: 1px solid #d7dee6; background: #fbfcfd; color: #687785;")
        right_layout.addWidget(form_wrap, 2)
        right_layout.addWidget(self.monitor_thumbnail, 1)

        state_box = QGroupBox("Estado das cameras")
        state_layout = QVBoxLayout(state_box)
        state_layout.setContentsMargins(10, 10, 10, 10)
        self.monitor_states = QTextEdit()
        self.monitor_states.setReadOnly(True)
        self.monitor_states.setMinimumWidth(320)
        self.monitor_states.setStyleSheet("background: #fbfcfd; border: 1px solid #d7dee6; color: #243447;")
        state_layout.addWidget(self.monitor_states)

        activity_box = QGroupBox("Atividade")
        activity_layout = QVBoxLayout(activity_box)
        activity_layout.setContentsMargins(10, 10, 10, 10)
        self.monitor_log = QTextEdit()
        self.monitor_log.setReadOnly(True)
        self.monitor_log.setMinimumHeight(140)
        self.monitor_log.setStyleSheet("background: white; border: 1px solid #d7dee6; color: #243447;")
        activity_layout.addWidget(self.monitor_log)

        side_layout.addWidget(right_box)
        side_layout.addWidget(state_box, 1)
        side_layout.addWidget(activity_box, 1)

        body_splitter.addWidget(live_panel)
        body_splitter.addWidget(side_panel)
        body_splitter.setStretchFactor(0, 5)
        body_splitter.setStretchFactor(1, 3)
        layout.addWidget(body_splitter, 3)

        table_box = QGroupBox("Eventos recentes")
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_filter = QHBoxLayout()
        self.realtime_filter_camera = QComboBox()
        self.realtime_filter_camera.addItem("")
        self.realtime_filter_camera.currentTextChanged.connect(self.apply_realtime_filter)
        table_filter.addWidget(QLabel("Filtrar camera"))
        table_filter.addWidget(self.realtime_filter_camera)
        table_filter.addStretch(1)
        table_layout.addLayout(table_filter)
        self.realtime_table = QTableWidget(0,6)
        self.realtime_table.setHorizontalHeaderLabels(["Camera","Data/Hora","Placa","Velocidade","Faixa","Tipo"])
        self.style_data_table(self.realtime_table)
        self.realtime_table.cellDoubleClicked.connect(self.open_realtime_event_image)
        table_layout.addWidget(self.realtime_table)
        layout.addWidget(table_box, 2)

    def build_evolution_tab(self):
        layout = QVBoxLayout(self.tab_evolution)
        layout.setSpacing(8)
        evo_tabs = QTabWidget()
        evo_tabs.setDocumentMode(True)
        tab_config = QWidget()
        tab_instance = QWidget()
        tab_template = QWidget()
        evo_tabs.addTab(tab_config, "Configuracao")
        evo_tabs.addTab(tab_instance, "Instancia e teste")
        evo_tabs.addTab(tab_template, "Template")

        config_layout = QVBoxLayout(tab_config)
        config_layout.setContentsMargins(0, 0, 0, 0)
        instance_layout_root = QVBoxLayout(tab_instance)
        instance_layout_root.setContentsMargins(0, 0, 0, 0)
        template_root_layout = QVBoxLayout(tab_template)
        template_root_layout.setContentsMargins(0, 0, 0, 0)

        form_box = QGroupBox("Configuracao da Evolution API")
        form = QFormLayout(form_box)
        form.setContentsMargins(10, 8, 10, 10)
        form.setVerticalSpacing(6)
        self.evo_enabled = QCheckBox("Habilitar integracao Evolution API")
        self.evo_url = QLineEdit()
        self.evo_token = PasswordField()
        self.evo_instance = QLineEdit()
        self.evo_mode = QComboBox(); self.evo_mode.addItems(["create_or_connect", "existing"])
        self.evo_recipients = QTextEdit(); self.evo_recipients.setPlaceholderText("5511999999999\n5511888888888"); self.evo_recipients.setMaximumHeight(90)
        self.evo_send_image = QCheckBox("Enviar imagem com legenda"); self.evo_send_image.setChecked(True)
        form.addRow("", self.evo_enabled)
        form.addRow("URL:", self.evo_url)
        form.addRow("Token:", self.evo_token)
        form.addRow("Instancia:", self.evo_instance)
        form.addRow("Modo:", self.evo_mode)
        form.addRow("Numeros:", self.evo_recipients)
        form.addRow("", self.evo_send_image)
        config_layout.addWidget(form_box)

        btns_wrap = QWidget()
        btns = QHBoxLayout(btns_wrap)
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(6)
        for text, slot in [("Salvar", self.save_evolution_settings), ("Testar API", self.test_evolution_connection), ("Conectar instancia", self.connect_evolution_instance), ("Atualizar QR", self.refresh_evolution_qr)]:
            button = QPushButton(text)
            button.setMinimumWidth(120)
            button.setMaximumWidth(150)
            button.clicked.connect(slot)
            btns.addWidget(button)
        btns.addStretch(1)
        config_layout.addWidget(btns_wrap)
        config_layout.addStretch(1)

        details_splitter = QSplitter(Qt.Horizontal)
        details_splitter.setChildrenCollapsible(False)

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
        self.evo_qr_label.setStyleSheet("border: 1px solid #d7dee6; background: #fbfcfd; color: #687785;")
        status_layout.addWidget(self.evo_status)
        status_layout.addWidget(self.evo_qr_label)

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
        btn_send_test.clicked.connect(self.send_evolution_test_message)
        test_form.addRow("Numero:", self.evo_test_number)
        test_form.addRow("Mensagem:", self.evo_test_message)
        test_form.addRow("", btn_send_test)
        details_splitter.addWidget(status_box)
        details_splitter.addWidget(test_box)
        details_splitter.setStretchFactor(0, 3)
        details_splitter.setStretchFactor(1, 2)
        instance_layout_root.addWidget(details_splitter, 1)

        template_box = QGroupBox("Template dos eventos")
        template_layout = QVBoxLayout(template_box)
        template_layout.setContentsMargins(10, 8, 10, 10)
        template_layout.setSpacing(6)
        self.evo_event_template = QTextEdit()
        self.evo_event_template.setMinimumHeight(110)
        self.evo_event_template.setMaximumHeight(160)
        self.evo_event_template.setPlaceholderText("Use variaveis como {camera}, {plate}, {speed}, {limit}, {ts}, {lane}, {direction}, {event_type}")
        self.evo_event_template.textChanged.connect(self.update_evolution_template_preview)
        variable_wrap = QWidget()
        variable_row = QHBoxLayout(variable_wrap)
        variable_row.setContentsMargins(0, 0, 0, 0)
        variable_row.setSpacing(4)
        for variable in ["{camera}", "{plate}", "{speed}", "{limit}", "{ts}", "{lane}", "{direction}", "{event_type}"]:
            button = QPushButton(variable)
            button.setMaximumWidth(92)
            button.clicked.connect(lambda _checked=False, value=variable: self.insert_evolution_template_variable(value))
            variable_row.addWidget(button)
        variable_row.addStretch(1)
        template_help = QLabel("Variaveis disponiveis: {camera}, {plate}, {speed}, {limit}, {ts}, {lane}, {direction}, {event_type}")
        template_help.setWordWrap(True)
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
        layout.addWidget(evo_tabs)
        self.load_evolution_settings_into_ui()

    def append_log(self, text):
        """Append a log message to the dashboard and monitor logs."""
        self.tab_dashboard.append_log(text)

    def reload_camera_lists(self):
        names = self.config.get_camera_names()
        self.camera_list.clear()
        for name in names: self.camera_list.addItem(QListWidgetItem(name))
        if names: self.camera_list.setCurrentRow(0)
        # Update camera lists in history and report tabs
        self.tab_history.set_camera_list(names)
        self.tab_report.set_camera_list(names)
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

    def load_selected_camera(self, name):
        cam = self.config.get_camera(name)
        if not cam: return
        self.cam_name.setText(cam.get("name", "")); self.cam_ip.setText(cam.get("camera_ip", "")); self.cam_port.setValue(int(cam.get("camera_port", 80)))
        self.cam_user.setText(cam.get("camera_user", "")); self.cam_pass.setText(cam.get("camera_pass", "")); self.cam_channel.setValue(int(cam.get("channel", 101))); self.cam_timeout.setValue(int(cam.get("timeout", 15)))
        self.cam_rtsp_enabled.setChecked(bool(cam.get("rtsp_enabled", True))); self.cam_rtsp_port.setValue(int(cam.get("rtsp_port", 554))); self.cam_rtsp_url.setText(cam.get("rtsp_url", "")); self.cam_live_fallback.setCurrentText(cam.get("live_fallback_mode", "snapshot"))
        self.cam_speed_limit_enabled.setChecked(bool(cam.get("speed_limit_enabled", True))); self.cam_speed_limit.setValue(int(cam.get("speed_limit_value", self.config.data.get("speed_limit", 60)))); self.cam_speed_alert_visual.setChecked(bool(cam.get("speed_alert_visual", True)))
        self.cam_evolution_enabled.setChecked(bool(cam.get("evolution_enabled", False)))
        rtsp_transport = cam.get("rtsp_transport", "tcp"); transport_idx = self.cam_rtsp_transport.findText(rtsp_transport); self.cam_rtsp_transport.setCurrentIndex(max(transport_idx, 0))
        self.cam_output.setText(cam.get("output_dir", str(app_dir() / "output"))); self.cam_enabled.setChecked(bool(cam.get("enabled", True))); self.cam_snapshot.setChecked(bool(cam.get("save_snapshot_on_event", True)))
        mode = cam.get("camera_mode", "auto"); idx = self.cam_mode.findText(mode); self.cam_mode.setCurrentIndex(max(idx, 0))

    def current_camera_form(self):
        return {"name": self.cam_name.text().strip() or "Camera", "enabled": self.cam_enabled.isChecked(), "camera_ip": self.cam_ip.text().strip(), "camera_port": int(self.cam_port.value()), "camera_user": self.cam_user.text().strip(), "camera_pass": self.cam_pass.text(), "channel": int(self.cam_channel.value()), "timeout": int(self.cam_timeout.value()), "rtsp_enabled": self.cam_rtsp_enabled.isChecked(), "rtsp_port": int(self.cam_rtsp_port.value()), "rtsp_transport": self.cam_rtsp_transport.currentText(), "rtsp_url": self.cam_rtsp_url.text().strip(), "live_fallback_mode": self.cam_live_fallback.currentText(), "speed_limit_enabled": self.cam_speed_limit_enabled.isChecked(), "speed_limit_value": int(self.cam_speed_limit.value()), "speed_alert_visual": self.cam_speed_alert_visual.isChecked(), "evolution_enabled": self.cam_evolution_enabled.isChecked(), "output_dir": self.cam_output.text().strip() or str(app_dir() / "output"), "save_snapshot_on_event": self.cam_snapshot.isChecked(), "camera_mode": self.cam_mode.currentText()}

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder: self.cam_output.setText(folder)

    def new_camera(self):
        self.cam_name.setText(f"Camera {len(self.config.get_camera_names()) + 1}"); self.cam_ip.clear(); self.cam_user.clear(); self.cam_pass.clear(); self.cam_rtsp_enabled.setChecked(True); self.cam_rtsp_port.setValue(554); self.cam_rtsp_transport.setCurrentText("tcp"); self.cam_rtsp_url.clear(); self.cam_live_fallback.setCurrentText("snapshot"); self.cam_speed_limit_enabled.setChecked(True); self.cam_speed_limit.setValue(int(self.config.data.get("speed_limit", 60))); self.cam_speed_alert_visual.setChecked(True); self.cam_evolution_enabled.setChecked(False); self.cam_output.setText(str(app_dir() / "output")); self.cam_enabled.setChecked(True); self.cam_snapshot.setChecked(True); self.cam_mode.setCurrentText("auto")

    def save_camera(self):
        cam = self.current_camera_form(); Path(cam["output_dir"]).mkdir(parents=True, exist_ok=True); self.config.upsert_camera(cam); self.config.save(); self.reload_camera_lists(); QMessageBox.information(self, APP_NAME, "Camera salva com sucesso.")
        if self.live_camera_combo.currentText().strip() == cam["name"]:
            self.on_live_camera_changed(cam["name"])

    def delete_camera(self):
        name = self.cam_name.text().strip()
        if not name: return
        if self.live_camera_combo.currentText().strip() == name:
            self.stop_live_view()
        self.config.delete_camera(name); self.config.save(); self.reload_camera_lists(); self.new_camera(); QMessageBox.information(self, APP_NAME, "Camera removida.")

    def test_camera_connection(self):
        try:
            ok, status, detail = CameraClient(self.current_camera_form()).test_connection()
            if ok: QMessageBox.information(self, APP_NAME, f"Conexao OK\nHTTP {status}\nDetalhe: {detail}")
            else: QMessageBox.warning(self, APP_NAME, f"Falha HTTP {status}\nDetalhe: {detail}")
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, str(e))

    def manual_snapshot(self):
        try:
            cam = self.current_camera_form(); img, used_url = CameraClient(cam).download_snapshot(); out = Path(cam["output_dir"]) / "manual"; out.mkdir(parents=True, exist_ok=True); file = out / f"{cam['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"; file.write_bytes(img); self.set_preview(str(file)); QMessageBox.information(self, APP_NAME, f"Snapshot salvo em:\n{file}\nURL: {used_url}")
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Snapshot nao suportado nesse firmware.\n\nDetalhe:\n{e}")

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
        self.camera_states[camera_name] = (connected, detail); self.update_camera_state_panel()

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

    def current_evolution_form(self) -> dict:
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

    def load_evolution_settings_into_ui(self):
        cfg = self.config.data.get("evolution_api", {})
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
        self.update_evolution_status_label()
        self.update_evolution_template_preview()

    def update_evolution_status_label(self, extra_text: str = ""):
        cfg = self.config.data.get("evolution_api", {})
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

    def evolution_preview_data(self) -> dict:
        return {
            "camera_name": self.lbl_cam.text().strip() if hasattr(self, "lbl_cam") and self.lbl_cam.text().strip() not in ("", "-") else "Camera 1",
            "plate": self.lbl_plate.text().strip() if hasattr(self, "lbl_plate") and self.lbl_plate.text().strip() not in ("", "-") else "ABC1D23",
            "speed": self.lbl_speed.text().strip() if hasattr(self, "lbl_speed") and self.lbl_speed.text().strip() not in ("", "-") else "72",
            "applied_speed_limit": 60.0,
            "ts": now_str(),
            "lane": self.lbl_lane.text().strip() if hasattr(self, "lbl_lane") and self.lbl_lane.text().strip() not in ("", "-") else "1",
            "direction": self.lbl_direction.text().strip() if hasattr(self, "lbl_direction") and self.lbl_direction.text().strip() not in ("", "-") else "Frente",
            "event_type": self.lbl_type.text().strip() if hasattr(self, "lbl_type") and self.lbl_type.text().strip() not in ("", "-") else "ANPR",
        }

    def update_evolution_template_preview(self):
        if not hasattr(self, "evo_template_preview"):
            return
        template = self.evo_event_template.toPlainText() if hasattr(self, "evo_event_template") else ""
        self.evo_template_preview.setPlainText(render_event_message(template, self.evolution_preview_data()))

    def insert_evolution_template_variable(self, variable: str):
        cursor = self.evo_event_template.textCursor()
        cursor.insertText(variable)
        self.evo_event_template.setFocus()
        self.update_evolution_template_preview()

    def save_evolution_settings(self):
        self.config.data["evolution_api"] = self.current_evolution_form()
        self.config.save()
        self.load_evolution_settings_into_ui()
        QMessageBox.information(self, APP_NAME, "Configuracao da Evolution API salva.")

    def evolution_client_from_form(self) -> EvolutionApiClient:
        cfg = self.current_evolution_form()
        self.config.data["evolution_api"] = cfg
        self.config._normalize_evolution_api()
        return EvolutionApiClient(self.config.data["evolution_api"])

    def test_evolution_connection(self):
        try:
            client = self.evolution_client_from_form()
            data = client.test_connection()
            count = len(data) if isinstance(data, list) else len(data.get("instances", [])) if isinstance(data, dict) else 0
            self.update_evolution_status_label(f"Evolution API conectada. Instancias encontradas: {count}")
            QMessageBox.information(self, APP_NAME, "Conexao com Evolution API validada.")
        except Exception as exc:
            self.update_evolution_status_label(f"Falha na Evolution API: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def show_evolution_qr(self, qr_payload: str):
        if not qr_payload:
            self.evo_qr_label.setPixmap(QPixmap())
            self.evo_qr_label.setText("QR Code indisponivel")
            return
        client = self.evolution_client_from_form()
        pixmap = client.build_qr_pixmap(qr_payload)
        if pixmap.isNull():
            self.evo_qr_label.setPixmap(QPixmap())
            self.evo_qr_label.setText(f"QR recebido, mas nao foi possivel renderizar.\n\nConteudo:\n{qr_payload[:300]}")
            return
        self.evo_qr_label.setText("")
        self.evo_qr_label.setPixmap(pixmap.scaled(self.evo_qr_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def connect_evolution_instance(self):
        try:
            client = self.evolution_client_from_form()
            create_if_missing = self.evo_mode.currentText() == "create_or_connect"
            state = client.ensure_instance(create_if_missing=create_if_missing)
            qr_payload = client.fetch_qr_payload()
            self.show_evolution_qr(qr_payload)
            self.update_evolution_status_label(f"Instancia pronta. Estado: {state}")
            self.save_evolution_settings()
        except Exception as exc:
            self.update_evolution_status_label(f"Falha ao conectar instancia: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def refresh_evolution_qr(self):
        try:
            client = self.evolution_client_from_form()
            qr_payload = client.fetch_qr_payload()
            self.show_evolution_qr(qr_payload)
            self.update_evolution_status_label("QR Code atualizado.")
        except Exception as exc:
            self.update_evolution_status_label(f"Falha ao atualizar QR: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def send_evolution_test_message(self):
        try:
            client = self.evolution_client_from_form()
            number = sanitize_phone_number(self.evo_test_number.text())
            message = self.evo_test_message.toPlainText().strip()
            if not number:
                raise RuntimeError("Informe o numero de teste.")
            if not message:
                raise RuntimeError("Informe a mensagem de teste.")
            client.send_text_message(number, message)
            self.update_evolution_status_label(f"Mensagem de teste enviada para {number}.")
            self.append_log(f"Evolution API: teste enviado para {number}.")
        except Exception as exc:
            self.update_evolution_status_label(f"Falha no teste Evolution: {exc}")
            QMessageBox.warning(self, APP_NAME, str(exc))

    def maybe_send_evolution_alert(self, data: dict):
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
        worker = EvolutionSendWorker(evolution_cfg, dict(data), recipients)
        worker.finished_status.connect(self.append_log)
        worker.finished_status.connect(lambda _text, w=worker: self._release_evolution_worker(w))
        self.evolution_workers.append(worker)
        worker.start()

    def _release_evolution_worker(self, worker):
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
        self.lbl_cam.setText(data.get("camera_name") or "-"); self.lbl_plate.setText(data.get("plate") or "-"); self.lbl_speed.setText(data.get("speed") or "-"); self.lbl_lane.setText(data.get("lane") or "-"); self.lbl_direction.setText(data.get("direction") or "-"); self.lbl_type.setText(data.get("event_type") or "-"); self.lbl_image_status.setText(data.get("image_status") or "-")
        if data.get("image_path"):
            self.set_preview(data["image_path"])
            pixmap = QPixmap(data["image_path"])
            if not pixmap.isNull():
                self.monitor_thumbnail.setPixmap(pixmap.scaled(self.monitor_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.monitor_thumbnail.setText("")
        elif self.live_view.current_mode != "rtsp": self.live_view.show_message("Sem imagem disponível por ISAPI neste firmware")
        else:
            self.monitor_thumbnail.setPixmap(QPixmap())
            self.monitor_thumbnail.setText("Sem imagem")
        speed_value = extract_speed_value(data.get("speed", "")); limit, visual_enabled = self.get_camera_speed_settings(data.get("camera_name", ""))
        data["applied_speed_limit"] = float(limit)
        data["is_overspeed"] = speed_value > float(limit)
        self.db.insert_event(data); self.prepend_realtime_event(data); self.refresh_dashboard(); self.refresh_history(); self.refresh_report()
        if data["is_overspeed"]:
            self.append_log(f"ALERTA: {data.get('camera_name')} placa {data.get('plate') or '-'} acima do limite ({speed_value} > {limit} km/h)")
            if visual_enabled:
                self.set_monitor_alert_state(f"ALERTA de velocidade: {data.get('camera_name')} | placa {data.get('plate') or '-'} | {speed_value} km/h | limite {limit} km/h", True)
            else:
                self.set_monitor_alert_state(f"Evento acima do limite sem aviso visual: limite {limit} km/h", False)
            self.maybe_send_evolution_alert(data)
        else:
            self.append_log(f"Evento: {data.get('camera_name')} / placa={data.get('plate') or '-'} / velocidade={data.get('speed') or '-'} / {data.get('image_status', '')}")
            self.set_monitor_alert_state(f"Velocidade dentro do limite: {speed_value} km/h de {data.get('camera_name')} (limite {limit} km/h)", False)

    def prepend_realtime_event(self, data):
        self.realtime_table.insertRow(0)
        values = [data.get("camera_name",""), data.get("ts",""), data.get("plate",""), data.get("speed",""), data.get("lane",""), data.get("event_type","")]
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if col == 0:
                item.setData(Qt.UserRole, data.get("image_path", ""))
                item.setData(Qt.UserRole + 1, data.get("json_path", ""))
            self.realtime_table.setItem(0, col, item)
        row_color = QColor("#fff0e2") if data.get("is_overspeed") else color_from_name(data.get("camera_name", ""))
        for col in range(self.realtime_table.columnCount()):
            item = self.realtime_table.item(0, col)
            if item is not None:
                item.setBackground(row_color)
        while self.realtime_table.rowCount() > 200: self.realtime_table.removeRow(self.realtime_table.rowCount() - 1)
        self.apply_realtime_filter()

    def apply_realtime_filter(self):
        selected_camera = self.realtime_filter_camera.currentText().strip() if hasattr(self, "realtime_filter_camera") else ""
        for row in range(self.realtime_table.rowCount()):
            item = self.realtime_table.item(row, 0)
            camera_name = item.text().strip() if item else ""
            self.realtime_table.setRowHidden(row, bool(selected_camera and camera_name != selected_camera))

    def open_realtime_event_image(self, row, _column):
        item = self.realtime_table.item(row, 0)
        if item is None:
            return
        image_path = item.data(Qt.UserRole) or ""
        if image_path and Path(image_path).exists():
            self.set_preview(str(image_path))
            return
        QMessageBox.information(self, APP_NAME, "Este evento nao possui imagem salva.")

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
