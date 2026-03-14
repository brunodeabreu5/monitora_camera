# Users tab - manage application users
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QListWidget, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox, QSplitter, QWidget,
    QStackedWidget
)

from src.core.config import APP_NAME, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, hash_password
from ui.widgets import PasswordField
from .base_tab import BaseTab


class UsersTab(BaseTab):
    """Users tab for managing application users. Restricted to Administrators."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_list = None
        self.sys_user = None
        self.sys_pass = None
        self.sys_role = None
        self.logged_user = None
        self.stacked = None
        self.msg_restricted = None
        self.admin_panel = None
        self.build_ui()

    def set_logged_user(self, user_data: dict):
        """Set the currently logged user data."""
        self.logged_user = user_data

    def refresh_for_logged_user(self):
        """Show admin panel or restricted message based on logged user role. Call after set_main_window/set_logged_user."""
        if not self.stacked:
            return
        user = self.get_logged_user()
        if user and user.get("role") == "Administrador":
            self.stacked.setCurrentWidget(self.admin_panel)
            self.reload_user_list()
        else:
            self.stacked.setCurrentWidget(self.msg_restricted)

    def build_ui(self):
        """Build the users tab UI. Content visibility is set in refresh_for_logged_user()."""
        layout = super().build_ui()

        self.stacked = QStackedWidget()

        # Page 0: message for non-admin
        self.msg_restricted = QLabel("Somente administradores podem gerenciar usuarios.")
        self.msg_restricted.setWordWrap(True)
        self.stacked.addWidget(self.msg_restricted)

        # Page 1: list + form + buttons (admin only)
        self.admin_panel = QWidget()
        admin_layout = QVBoxLayout(self.admin_panel)
        admin_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.user_list = QListWidget()
        self.user_list.setMinimumWidth(220)
        self.user_list.currentTextChanged.connect(self.load_selected_user)
        splitter.addWidget(self.user_list)

        box = QGroupBox("Cadastro de usuario")
        form = QFormLayout(box)

        self.sys_user = QLineEdit()
        self.sys_pass = PasswordField()
        self.sys_role = QComboBox()
        self.sys_role.addItems(["Administrador", "Operador"])

        form.addRow("Usuario:", self.sys_user)
        form.addRow("Senha:", self.sys_pass)
        form.addRow("Perfil:", self.sys_role)

        splitter.addWidget(box)
        admin_layout.addWidget(splitter)

        btns_wrap = QWidget()
        btns = QHBoxLayout(btns_wrap)
        btns.setContentsMargins(0, 0, 0, 0)
        for text, slot in [
            ("Novo usuario", self.new_user),
            ("Salvar usuario", self.save_user),
            ("Excluir usuario", self.delete_user)
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch(1)
        admin_layout.addWidget(btns_wrap)
        admin_layout.addStretch(1)

        self.stacked.addWidget(self.admin_panel)
        layout.addWidget(self.stacked)
        return layout

    def reload_user_list(self):
        """Reload the list of users from config."""
        if not self.user_list:
            return

        config = self.get_config()
        if not config:
            return

        self.user_list.clear()
        for user in config.data.get("users", []):
            self.user_list.addItem(user.get("username", ""))

    def _is_admin(self):
        """True if current logged user is Administrator."""
        u = self.get_logged_user()
        return u and u.get("role") == "Administrador"

    def _count_admins(self, config):
        """Number of users with role Administrador."""
        return sum(1 for u in config.data.get("users", []) if u.get("role") == "Administrador")

    def load_selected_user(self, username: str):
        """Load user data into the form when a user is selected."""
        if not self.user_list:
            return

        config = self.get_config()
        if not config:
            return

        for user in config.data.get("users", []):
            if user.get("username") == username:
                self.sys_user.setText(user.get("username", ""))
                self.sys_user.setReadOnly(True)
                self.sys_pass.clear()
                self.sys_pass.setPlaceholderText("Digite uma nova senha para alterar")
                idx = self.sys_role.findText(user.get("role", "Operador"))
                self.sys_role.setCurrentIndex(max(idx, 0))
                return

    def new_user(self):
        """Clear the form to create a new user."""
        self.sys_user.clear()
        self.sys_user.setReadOnly(False)
        self.sys_pass.clear()
        self.sys_pass.setPlaceholderText("")
        self.sys_role.setCurrentIndex(1)  # Default to "Operador"

    def save_user(self):
        """Save the current user data from the form."""
        if not self._is_admin():
            return

        username = self.sys_user.text().strip()
        password = self.sys_pass.text()

        config = self.get_config()
        if not config:
            return

        existing_user = config.get_user(username)

        if not username:
            QMessageBox.warning(self, APP_NAME, "Informe o usuario.")
            return

        if not password and not existing_user:
            QMessageBox.warning(self, APP_NAME, "Informe a senha para novos usuarios.")
            return

        new_role = self.sys_role.currentText()
        if existing_user and existing_user.get("role") == "Administrador" and new_role == "Operador":
            if self._count_admins(config) <= 1:
                QMessageBox.warning(
                    self, APP_NAME,
                    "Nao e possivel rebaixar o unico administrador. Mantenha pelo menos um perfil Administrador."
                )
                return

        password_hash = existing_user.get("password_hash") if existing_user else ""
        password_salt = existing_user.get("password_salt") if existing_user else None
        must_change_password = bool(existing_user.get("must_change_password")) if existing_user else False

        if password:
            password_hash, password_salt = hash_password(password, password_salt)
            must_change_password = username == DEFAULT_ADMIN_USERNAME and password == DEFAULT_ADMIN_PASSWORD

        user_payload = {
            "username": username,
            "password_hash": password_hash,
            "role": new_role,
            "must_change_password": must_change_password,
        }
        if password_salt is not None:
            user_payload["password_salt"] = password_salt
        config.upsert_user(user_payload)
        config.save()
        self.reload_user_list()
        QMessageBox.information(self, APP_NAME, "Usuario salvo.")

    def delete_user(self):
        """Delete the current user."""
        if not self._is_admin():
            return

        username = self.sys_user.text().strip()
        if not username:
            return

        if self.get_logged_user() and username == self.get_logged_user().get("username"):
            QMessageBox.warning(self, APP_NAME, "Você não pode excluir o usuário logado.")
            return

        config = self.get_config()
        if not config:
            return

        user_to_delete = config.get_user(username)
        if user_to_delete and user_to_delete.get("role") == "Administrador" and self._count_admins(config) <= 1:
            QMessageBox.warning(
                self, APP_NAME,
                "Nao e possivel excluir o unico administrador. Mantenha pelo menos um usuario com perfil Administrador."
            )
            return

        reply = QMessageBox.question(
            self, APP_NAME,
            f"Excluir usuario \"{username}\"? Esta acao nao pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        config.delete_user(username)
        config.save()
        self.reload_user_list()
        self.new_user()
        QMessageBox.information(self, APP_NAME, "Usuário excluído.")
