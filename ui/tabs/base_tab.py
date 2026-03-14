# Base class for all tabs
from PySide6.QtWidgets import QWidget, QVBoxLayout


class BaseTab(QWidget):
    """Base class for all application tabs providing common functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None  # Reference to MainWindow, set by the window

    def set_main_window(self, main_window):
        """Set reference to main window for accessing shared resources."""
        self.main_window = main_window

    def build_ui(self):
        """Build the tab UI. Override this method in subclasses."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        return layout

    def refresh(self):
        """Refresh tab data. Override this method in subclasses."""
        pass

    def get_config(self):
        """Get application config from main window."""
        return self.main_window.config if self.main_window else None

    def get_database(self):
        """Get database from main window."""
        return self.main_window.db if self.main_window else None

    def get_logged_user(self):
        """Get logged user data from main window."""
        return self.main_window.logged_user if self.main_window else None
