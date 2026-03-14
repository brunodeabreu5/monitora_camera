# Widgets reutilizáveis: PasswordField, LiveViewController, LoginDialog
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QStackedLayout, QVBoxLayout, QWidget, QToolButton,
)

from src.core.camera_client import CameraClient
from src.core.config import APP_NAME, AppConfig

from .workers import LiveSnapshotWorker


class PasswordField(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.line_edit = QLineEdit()
        self.line_edit.setEchoMode(QLineEdit.Password)
        self.toggle_button = QToolButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setText("Ver")
        self.toggle_button.setToolTip("Mostrar senha")
        self.toggle_button.clicked.connect(self.toggle_password_visibility)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.toggle_button, 0)

    def toggle_password_visibility(self, checked: bool):
        self.line_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.toggle_button.setToolTip("Ocultar senha" if checked else "Mostrar senha")

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)

    def setFocus(self):
        self.line_edit.setFocus()


class LiveViewController(QWidget):
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_cfg = None
        self.current_mode = "idle"
        self._switching_mode = False
        self.last_snapshot = QPixmap()
        self.snapshot_worker = None
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.snapshot_label = QLabel("Video ao vivo parado")
        self.snapshot_label.setAlignment(Qt.AlignCenter)
        self.snapshot_label.setStyleSheet("border: 1px solid #888; background: #111; color: white;")
        self.snapshot_label.setMinimumHeight(280)
        self.video_widget.setMinimumHeight(280)
        self.player.setVideoOutput(self.video_widget)
        if hasattr(self.player, "errorOccurred"):
            self.player.errorOccurred.connect(self.on_player_error)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.addWidget(self.video_widget)
        self.stack.addWidget(self.snapshot_label)
        self.stack.setCurrentWidget(self.snapshot_label)

    def set_camera(self, camera_cfg: dict | None):
        self.camera_cfg = dict(camera_cfg) if camera_cfg else None

    def start(self):
        self._switching_mode = True
        self.stop()
        if not self.camera_cfg:
            self.show_message("Selecione uma camera para video ao vivo")
            self._switching_mode = False
            return
        if not self.camera_cfg.get("rtsp_enabled", True):
            self._switching_mode = False
            self.start_snapshot_fallback("RTSP desativado para esta camera")
            return
        if self.camera_cfg.get("live_detection_enabled", False):
            self._switching_mode = False
            self.start_snapshot_fallback("Detecção de carros ao vivo ativada")
            return
        client = CameraClient(self.camera_cfg)
        self.current_mode = "rtsp"
        self.stack.setCurrentWidget(self.video_widget)
        self.status_changed.emit(f"abrindo video ao vivo: {client.build_rtsp_url()}")
        self.player.setSource(QUrl(client.build_rtsp_url()))
        self.player.play()
        self._switching_mode = False

    def stop(self):
        if self.snapshot_worker:
            self.snapshot_worker.stop()
            self.snapshot_worker.wait(5000)
            self.snapshot_worker = None
        self.player.stop()
        self.player.setSource(QUrl())
        self.current_mode = "idle"
        self.stack.setCurrentWidget(self.snapshot_label)

    def start_snapshot_fallback(self, reason: str):
        if self._switching_mode:
            return
        self._switching_mode = True
        self.stop()
        self.current_mode = "snapshot"
        self.stack.setCurrentWidget(self.snapshot_label)
        self.show_message("Carregando snapshots ao vivo...")
        self.status_changed.emit(reason)
        use_snapshot = (
            self.camera_cfg.get("live_fallback_mode", "snapshot") == "snapshot"
            or self.camera_cfg.get("live_detection_enabled", False)
        )
        if not self.camera_cfg or not use_snapshot:
            self._switching_mode = False
            return
        self.snapshot_worker = LiveSnapshotWorker(self.camera_cfg)
        self.snapshot_worker.frame_ready.connect(self.on_snapshot_frame)
        self.snapshot_worker.status.connect(self.status_changed.emit)
        self.snapshot_worker.start()
        self._switching_mode = False

    def show_message(self, text: str):
        self.snapshot_label.setPixmap(QPixmap())
        self.snapshot_label.setText(text)

    def show_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self.show_message("Falha ao carregar imagem")
            return
        self.last_snapshot = pixmap
        scaled = pixmap.scaled(self.snapshot_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.snapshot_label.setPixmap(scaled)
        self.snapshot_label.setText("")

    def show_image_path(self, path: str):
        if self.current_mode == "rtsp":
            return
        self.stack.setCurrentWidget(self.snapshot_label)
        self.show_pixmap(QPixmap(path))

    def on_snapshot_frame(self, img_bytes: bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        self.stack.setCurrentWidget(self.snapshot_label)
        self.show_pixmap(pixmap)

    def on_player_error(self, *_):
        if self._switching_mode:
            return
        detail = self.player.errorString() or "falha ao abrir RTSP"
        self.start_snapshot_fallback(f"video ao vivo indisponivel: {detail}")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.start_snapshot_fallback("video ao vivo indisponivel: midia invalida")
        elif status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.BufferingMedia):
            self.status_changed.emit("video ao vivo conectado")

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.status_changed.emit("video ao vivo em reproducao")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.last_snapshot.isNull() and self.stack.currentWidget() is self.snapshot_label:
            self.show_pixmap(self.last_snapshot)


class LoginDialog(QDialog):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.user_data = None
        self.setWindowTitle("Login do sistema")
        self.setMinimumWidth(380)
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.pass_edit = PasswordField()
        form.addRow("Usuario:", self.user_edit)
        form.addRow("Senha:", self.pass_edit)
        layout.addLayout(form)
        info = QLabel("Primeiro acesso: admin / admin. Altere a senha padrao apos entrar.")
        info.setWordWrap(True)
        layout.addWidget(info)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.try_login)
        btns.rejected.connect(self.reject)
        ok_btn = btns.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setAutoDefault(True)
            ok_btn.setDefault(True)
        layout.addWidget(btns)

    def showEvent(self, event):
        super().showEvent(event)
        self.user_edit.setFocus()

    def try_login(self):
        user = self.config.authenticate(self.user_edit.text().strip(), self.pass_edit.text())
        if user:
            self.user_data = user
            self.accept()
        else:
            QMessageBox.warning(self, APP_NAME, "Usuario ou senha invalidos.")
