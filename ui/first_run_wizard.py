# First Run Setup Wizard (FASE 1.4 - Security)
"""
Wizard de primeira execução para configuração inicial do sistema.

Força o usuário a criar credenciais de administrador com validação de
força de senha antes de permitir o acesso ao sistema.
"""

import re
from typing import Optional, Tuple
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QFrame, QMessageBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor


class FirstRunWizard(QDialog):
    """
    Wizard de primeira execução para configuração de credenciais admin.

    Este wizard é exibido automaticamente quando o sistema é iniciado
    pela primeira vez (sem usuários configurados). O usuário deve criar
    uma conta de administrador com senha forte antes de prosseguir.

    Signals:
        credentials_created: Emitido quando as credenciais são criadas com sucesso
            (username: str, password: str)
    """

    credentials_created = Signal(str, str)

    def __init__(self, parent=None):
        """
        Inicializa o wizard de primeira execução.

        Args:
            parent: Widget pai (opcional)
        """
        super().__init__(parent)
        self._username = ""
        self._password = ""
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Configura a interface do wizard."""
        self.setWindowTitle("Configuração Inicial - Hikvision Radar Pro V4.2")
        self.setMinimumSize(500, 450)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_label = QLabel("Bem-vindo ao Hikvision Radar Pro")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Subtitle
        subtitle = QLabel("Primeira Execução - Configuração de Administrador")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Instructions
        instructions = QLabel(
            "Para começar, crie sua conta de Administrador.\n\n"
            "Esta conta terá acesso completo ao sistema. Escolha uma\n"
            "senha forte para proteger suas configurações."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)

        # Username field
        username_layout = QHBoxLayout()
        username_label = QLabel("Nome de Usuário:")
        username_label.setMinimumWidth(120)
        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("Ex: admin")
        self._username_edit.setMinimumWidth(200)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self._username_edit)
        layout.addLayout(username_layout)

        # Password field
        password_layout = QHBoxLayout()
        password_label = QLabel("Senha:")
        password_label.setMinimumWidth(120)
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("Mínimo 8 caracteres")
        self._password_edit.setMinimumWidth(200)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self._password_edit)
        layout.addLayout(password_layout)

        # Confirm password field
        confirm_layout = QHBoxLayout()
        confirm_label = QLabel("Confirmar Senha:")
        confirm_label.setMinimumWidth(120)
        self._confirm_edit = QLineEdit()
        self._confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_edit.setPlaceholderText("Digite a senha novamente")
        self._confirm_edit.setMinimumWidth(200)
        confirm_layout.addWidget(confirm_label)
        confirm_layout.addWidget(self._confirm_edit)
        layout.addLayout(confirm_layout)

        # Password strength indicator
        self._strength_bar = QProgressBar()
        self._strength_bar.setMaximum(100)
        self._strength_bar.setValue(0)
        self._strength_bar.setTextVisible(True)
        self._strength_bar.setFormat("Força da Senha")
        self._strength_bar.setStyleSheet("""
            QProgressBar::chunk { background-color: #d32f2f; }
        """)
        layout.addWidget(self._strength_bar)

        # Password requirements
        requirements = QLabel(
            "<b>Requisitos da Senha:</b><br>"
            "• Mínimo 8 caracteres<br>"
            "• Pelo menos uma letra maiúscula (A-Z)<br>"
            "• Pelo menos uma letra minúscula (a-z)<br>"
            "• Pelo menos um número (0-9)<br>"
            "• Recomendado: caracteres especiais (!@#$%...)"
        )
        requirements.setWordWrap(True)
        layout.addWidget(requirements)

        # Show password checkbox
        self._show_password_check = QCheckBox("Mostrar senha")
        layout.addWidget(self._show_password_check)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._create_button = QPushButton("Criar Conta")
        self._create_button.setMinimumWidth(120)
        self._create_button.setEnabled(False)
        button_layout.addWidget(self._create_button)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Conecta signals e slots."""
        self._username_edit.textChanged.connect(self._validate_inputs)
        self._password_edit.textChanged.connect(self._update_password_strength)
        self._confirm_edit.textChanged.connect(self._validate_inputs)
        self._show_password_check.toggled.connect(self._toggle_password_visibility)
        self._create_button.clicked.connect(self._create_credentials)

    def _toggle_password_visibility(self, show: bool):
        """
        Alterna visibilidade da senha.

        Args:
            show: True para mostrar senha, False para ocultar
        """
        if show:
            self._password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._confirm_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def _calculate_password_strength(self, password: str) -> int:
        """
        Calcula força da senha (0-100).

        Args:
            password: Senha a ser avaliada

        Returns:
            int: Pontuação de força (0-100)
        """
        if not password:
            return 0

        score = 0

        # Comprimento (até 40 pontos)
        length = len(password)
        if length >= 8:
            score += 20
        if length >= 12:
            score += 10
        if length >= 16:
            score += 10

        # Complexidade (até 60 pontos)
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>?]', password))

        if has_lower:
            score += 10
        if has_upper:
            score += 10
        if has_digit:
            score += 10
        if has_special:
            score += 15

        # Bônus por combinação
        if has_lower and has_upper:
            score += 5
        if has_lower and has_upper and has_digit:
            score += 5
        if has_lower and has_upper and has_digit and has_special:
            score += 5

        return min(score, 100)

    def _get_strength_color(self, strength: int) -> Tuple[str, str]:
        """
        Retorna cor baseada na força da senha.

        Args:
            strength: Pontuação de força (0-100)

        Returns:
            Tuple[str, str]: (cor_hex, cor_css)
        """
        if strength < 30:
            return "#d32f2f", "#d32f2f"  # Vermelho
        elif strength < 60:
            return "#f57c00", "#f57c00"  # Laranja
        elif strength < 80:
            return "#fbc02d", "#fbc02d"  # Amarelo
        else:
            return "#388e3c", "#388e3c"  # Verde

    def _get_strength_label(self, strength: int) -> str:
        """
        Retorna label descritivo da força da senha.

        Args:
            strength: Pontuação de força (0-100)

        Returns:
            str: Label descritivo
        """
        if strength < 30:
            return "Muito Fraca"
        elif strength < 60:
            return "Fraca"
        elif strength < 80:
            return "Média"
        elif strength < 95:
            return "Forte"
        else:
            return "Muito Forte"

    def _update_password_strength(self):
        """Atualiza indicador de força da senha."""
        password = self._password_edit.text()
        strength = self._calculate_password_strength(password)

        self._strength_bar.setValue(strength)
        self._strength_bar.setFormat(self._get_strength_label(strength))

        # Atualizar cor
        color = self._get_strength_color(strength)[1]
        self._strength_bar.setStyleSheet(f"""
            QProgressBar::chunk {{ background-color: {color}; }}
        """)

        self._validate_inputs()

    def _validate_inputs(self):
        """Valida os campos do formulário."""
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        confirm = self._confirm_edit.text()

        # Validar username
        if not username:
            self._create_button.setEnabled(False)
            return

        if len(username) < 3:
            self._create_button.setEnabled(False)
            return

        # Validar requisitos mínimos de senha
        if len(password) < 8:
            self._create_button.setEnabled(False)
            return

        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))

        if not (has_upper and has_lower and has_digit):
            self._create_button.setEnabled(False)
            return

        # Validar confirmação
        if password != confirm:
            self._create_button.setEnabled(False)
            return

        # Todos os checks passaram
        self._create_button.setEnabled(True)

    def _create_credentials(self):
        """Cria as credenciais do administrador."""
        username = self._username_edit.text().strip()
        password = self._password_edit.text()

        # Validação final
        if not username or not password:
            QMessageBox.warning(
                self,
                "Campos Obrigatórios",
                "Preencha todos os campos obrigatórios."
            )
            return

        if password != self._confirm_edit.text():
            QMessageBox.warning(
                self,
                "Senhas Não Conferem",
                "A senha e a confirmação não são iguais."
            )
            return

        # Confirmar criação
        reply = QMessageBox.question(
            self,
            "Confirmar Criação de Conta",
            f"Deseja criar a conta de administrador '{username}'?\n\n"
            "Esta ação não poderá ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._username = username
            self._password = password

            # Emitir signal com as credenciais
            self.credentials_created.emit(username, password)

            # Fechar wizard
            self.accept()

    def get_credentials(self) -> Tuple[str, str]:
        """
        Retorna as credenciais criadas.

        Returns:
            Tuple[str, str]: (username, password)

        Raises:
            ValueError: Se as credenciais não foram criadas ainda
        """
        if not self._username or not self._password:
            raise ValueError("Credentials not created yet")
        return self._username, self._password


def show_first_run_wizard(parent=None) -> Optional[Tuple[str, str]]:
    """
    Exibe o wizard de primeira execução de forma síncrona.

    Função de conveniência para mostrar o wizard e obter as credenciais.

    Args:
        parent: Widget pai (opcional)

    Returns:
        Tuple[str, str] com (username, password) se o wizard foi confirmado,
        None se foi cancelado

    Example:
        >>> credentials = show_first_run_wizard()
        >>> if credentials:
        >>>     username, password = credentials
        >>>     # Criar usuário admin com essas credenciais
    """
    wizard = FirstRunWizard(parent)
    result = wizard.exec()

    if result == QDialog.DialogCode.Accepted:
        try:
            return wizard.get_credentials()
        except ValueError:
            return None

    return None


if __name__ == "__main__":
    # Test standalone
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    wizard = FirstRunWizard()
    wizard.credentials_created.connect(lambda u, p: print(f"Created: {u}"))
    wizard.show()
    sys.exit(app.exec())
