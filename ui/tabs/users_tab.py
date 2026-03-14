# Users tab - manage application users
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QListWidget, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox, QSplitter, QWidget
)

from src.core.config import APP_NAME, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, hash_password
from ui.widgets import PasswordField
from .base_tab import BaseTab


class UsersTab(BaseTab):
    """Users tab for managing application users."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_list = None
        self.sys_user = None
        self.sys_pass = None
        self.sys_role = None
        self.logged_user = None
        self.build_ui()

    def set_logged_user(self, user_data: dict):
        """Set the currently logged user data."""
        self.logged_user = user_data

    def build_ui(self):
        """Build the users tab UI."""
        layout = super().build_ui()

        # Check if user is admin
        if self.get_logged_user() and self.get_logged_user().get("role") != "Administrador":
            msg = QLabel("Somente administradores podem gerenciar usuarios.")
            msg.setWordWrap(True)
            layout.addWidget(msg)
            layout.addStretch(1)
            return layout

        # Create splitter for list and form
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # User list (left panel)
        self.user_list = QListWidget()
        self.user_list.setMinimumWidth(220)
        self.user_list.currentTextChanged.connect(self.load_selected_user)
        splitter.addWidget(self.user_list)

        # User form (right panel)
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
        layout.addWidget(splitter)

        # Buttons
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
        layout.addWidget(btns_wrap)
        layout.addStretch(1)

        # Reload user list
        self.reload_user_list()

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
                self.sys_pass.clear()
                self.sys_pass.setPlaceholderText("Digite uma nova senha para alterar")
                idx = self.sys_role.findText(user.get("role", "Operador"))
                self.sys_role.setCurrentIndex(max(idx, 0))
                return

    def new_user(self):
        """Clear the form to create a new user."""
        self.sys_user.clear()
        self.sys_pass.clear()
        self.sys_pass.setPlaceholderText("")
        self.sys_role.setCurrentIndex(1)  # Default to "Operador"

    def save_user(self):
        """Save the current user data from the form."""
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

        password_hash = existing_user.get("password_hash") if existing_user else ""
        must_change_password = bool(existing_user.get("must_change_password")) if existing_user else False

        if password:
            password_hash = hash_password(password)
            must_change_password = username == DEFAULT_ADMIN_USERNAME and password == DEFAULT_ADMIN_PASSWORD

        config.upsert_user({
            "username": username,
            "password_hash": password_hash,
            "role": self.sys_role.currentText(),
            "must_change_password": must_change_password,
        })
        config.save()
        self.reload_user_list()
        QMessageBox.information(self, APP_NAME, "Usuario salvo.")

    def delete_user(self):
        """Delete the current user."""
        username = self.sys_user.text().strip()
        if not username:
            return

        if self.get_logged_user() and username == self.get_logged_user().get("username"):
            QMessageBox.warning(self, APP_NAME, "Você não pode excluir o usuário logado.")
            return

        config = self.get_config()
        if not config:
            return

        config.delete_user(username)
        config.save()
        self.reload_user_list()
        self.new_user()
        QMessageBox.information(self, APP_NAME, "Usuário excluído.")
