# Centralized Qt Imports (FASE 2.3 - Code Quality)
"""
Importações centralizadas de PySide6/Qt6 para o Hikvision Radar Pro V4.2.

Este módulo centraliza todas as importações de widgets e componentes Qt
usados na aplicação, facilitando manutenção e upgrades de versão.

Uso:
    from ui.qt_imports import (
        QPushButton, QVBoxLayout, QDialog,
        Qt, Signal, Slot
    )

Benefícios:
    - Reduz duplicação de imports em múltiplos arquivos
    - Facilita upgrades de versão do Qt
    - Permite easily mock para testes
    - Melhora compatibilidade entre diferentes versões do PySide6
"""

# ============================================================================
# PySide6 Core - Módulos fundamentais
# ============================================================================

from PySide6.QtCore import (
    # Classes essenciais
    Qt,
    QObject,
    Signal,
    Slot,
    Property,
    QAbstractListModel,
    QAbstractTableModel,

    # Tipos
    QSettings,
    QSize,
    QRect,
    QPoint,
    QUrl,

    # Funcionalidades
    QTimer,
    QDateTime,
    QDate,
    QTime,

    # Thread/Concurrency
    QThread,
    QMutex,
    QReadWriteLock,
    QWaitCondition,
    QThreadPool,
    QRunnable,

    # Arquivos e Paths
    QFile,
    QFileInfo,
    QDir,
    QFileSystemWatcher,

    # JSON e Variants
    QJsonDocument,
    QJsonObject,
    QJsonArray,
    QJsonValue,
    QVariant,

    # Meta-objetos e Reflexão
    pyqtSignal as Signal,  # Alias para compatibilidade
    pyqtSlot as Slot,      # Alias para compatibilidade
    QByteArray,
)


# ============================================================================
# PySide6 QtGui - Classes gráficas e recursos
# ============================================================================

from PySide6.QtGui import (
    # Pintura e Desenho
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QFontDatabase,

    # Imagens
    QImage,
    QPixmap,
    QIcon,
    QPicture,

    # Eventos
    QKeyEvent,
    QMouseEvent,
    QWheelEvent,
    QResizeEvent,
    QCloseEvent,
    QShowEvent,
    QHideEvent,
    QFocusEvent,

    # Cursor
    QCursor,

    # Texto e Documentos
    QTextDocument,
    QTextCursor,

    # Paleta e Estilo
    QPalette,
    QCursor,

    # Actions
    QAction,
    QActionGroup,

    # Clipboard
    QClipboard,

    # Screen e GUI
    QScreen,
    QGuiApplication,

    # Imagens
    QImageReader,
    QImageWriter,

    # Validadores
    QValidator,
    QIntValidator,
    QDoubleValidator,
    QRegExpValidator,
    QRegularExpressionValidator,
)


# ============================================================================
# PySide6 QtWidgets - Widgets da interface
# ============================================================================

from PySide6.QtWidgets import (
    # Application-level
    QApplication,

    # Janelas
    QMainWindow,
    QDialog,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QProgressDialog,
    QSplashScreen,

    # Layouts
    QLayout,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QStackedLayout,

    # Widgets Básicos
    QWidget,
    QLabel,
    QPushButton,
    QCheckBox,
    QRadioButton,
    QFrame,
    QSplitter,
    QButtonGroup,

    # Inputs de Texto
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,

    # Seleção e Lists
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QListView,

    # Abas e Containers
    QTabWidget,
    QGroupBox,
    QScrollArea,
    QToolBox,
    QStackedWidget,
    QDockWidget,

    # Barras
    QMenuBar,
    QMenu,
    QStatusBar,
    QToolBar,
    QProgressBar,
    QSlider,

    # Diálogos Específicos
    QColorDialog,
    QFontDialog,

    # Widgets de dados
    QTableView,
    QTreeView,
    QAbstractItemView,

    # System Tray
    QSystemTrayIcon,
)


# ============================================================================
# PySide6 QtNetwork - Funcionalidades de rede (se necessário)
# ============================================================================

try:
    from PySide6.QtNetwork import (
        QNetworkAccessManager,
        QNetworkRequest,
        QNetworkReply,
        QNetworkCookie,
        QNetworkCookieJar,
    )
    QTNETWORK_AVAILABLE = True
except ImportError:
    QTNETWORK_AVAILABLE = False


# ============================================================================
# Constantes e Enums úteis
# ============================================================================

# Alignment flags para simplificar código
from PySide6.QtCore import Qt

AlignLeft = Qt.AlignmentFlag.AlignLeft
AlignRight = Qt.AlignmentFlag.AlignRight
AlignCenter = Qt.AlignmentFlag.AlignCenter
AlignTop = Qt.AlignmentFlag.AlignTop
AlignBottom = Qt.AlignmentFlag.AlignBottom
AlignHCenter = Qt.AlignmentFlag.AlignHCenter
AlignVCenter = Qt.AlignmentFlag.AlignVCenter

# Window flags
Window = Qt.WindowType.Window
Dialog = Qt.WindowType.Dialog
Sheet = Qt.WindowType.Sheet
Drawer = Qt.WindowType.Drawer
Popup = Qt.WindowType.Popup
Tool = Qt.WindowType.Tool
ToolTip = Qt.WindowType.ToolTip
SplashScreen = Qt.WindowType.SplashScreen
Desktop = Qt.WindowType.Desktop
SubWindow = Qt.WindowType.SubWindow
ForeignWindow = Qt.WindowType.ForeignWindow
CoverWindow = Qt.WindowType.CoverWindow

# ItemDataRoles
DisplayRole = Qt.ItemDataRole.DisplayRole
DecorationRole = Qt.ItemDataRole.DecorationRole
EditRole = Qt.ItemDataRole.EditRole
ToolTipRole = Qt.ItemDataRole.ToolTipRole
StatusTipRole = Qt.ItemDataRole.StatusTipRole
WhatsThisRole = Qt.ItemDataRole.WhatsThisRole
UserRole = Qt.ItemDataRole.UserRole

# CheckStates
Unchecked = Qt.CheckState.Unchecked
PartiallyChecked = Qt.CheckState.PartiallyChecked
Checked = Qt.CheckState.Checked


# ============================================================================
# Funções auxiliares para compatibilidade
# ============================================================================

def is_pyside6() -> bool:
    """Verifica se está usando PySide6."""
    return True


def get_qt_version() -> str:
    """Retorna versão do Qt em uso."""
    from PySide6 import QtCore
    return QtCore.qVersion()


def get_pyside_version() -> str:
    """Retorna versão do PySide6."""
    from PySide6 import __version__ as pyside_version
    return pyside_version


# ============================================================================
# Exports para "from ui.qt_imports import *"
# ============================================================================

__all__ = [
    # Core
    'Qt', 'QObject', 'Signal', 'Slot', 'Property',
    'QSettings', 'QSize', 'QPoint', 'QTimer', 'QDateTime',
    'QThread', 'QMutex', 'QByteArray',

    # Gui
    'QPainter', 'QPen', 'QBrush', 'QColor', 'QFont', 'QIcon',
    'QPixmap', 'QImage', 'QAction', 'QCursor', 'QValidator',

    # Widgets
    'QApplication', 'QWidget', 'QMainWindow', 'QDialog',
    'QVBoxLayout', 'QHBoxLayout', 'QGridLayout', 'QFormLayout',
    'QLabel', 'QPushButton', 'QLineEdit', 'QCheckBox', 'QRadioButton',
    'QComboBox', 'QListWidget', 'QTableWidget', 'QTreeWidget',
    'QTabWidget', 'QGroupBox', 'QScrollArea', 'QFrame', 'QSplitter',
    'QMenuBar', 'QMenu', 'QStatusBar', 'QToolBar',
    'QMessageBox', 'QFileDialog', 'QInputDialog',
    'QProgressBar', 'QSlider', 'QSpinBox', 'QDoubleSpinBox',
    'QTextEdit', 'QPlainTextEdit',

    # Constants
    'AlignLeft', 'AlignRight', 'AlignCenter',
    'Window', 'Dialog', 'Tool', 'Popup',
    'Checked', 'Unchecked', 'PartiallyChecked',

    # Funções auxiliares
    'is_pyside6', 'get_qt_version', 'get_pyside_version',
]
