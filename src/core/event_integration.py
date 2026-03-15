# Event Integration (FASE 3.5 - Architecture)
"""
Integração do EventManager com MainWindow e Tabs.

Este módulo fornece a base para reduzir acoplamento entre componentes
através do uso do EventManager para comunicação em vez de referências
diretas.

Arquitetura:
    MainWindow
        ├── Gerencia EventManager central
        ├── Publica eventos (camera_updated, event_detected, etc.)
        └── Subscribe a eventos das tabs

    Tabs (Dashboard, History, Monitor, etc.)
        ├── Recebem referência ao EventManager
        ├── Publicam seus eventos
        └── Subscribe a eventos de outros componentes

Benefits:
    - Tabs não precisam de referência direta ao MainWindow
    - Testabilidade: Fácil mock de eventos
    - Flexibilidade: Fácil adicionar novos subscribers
    - Manutenibilidade: Comunicação explícita e documentada
"""

from typing import Optional
from PySide6.QtCore import QObject

from src.core.event_manager import EventManager


class EventAwareMixin:
    """
    Mixin para componentes que precisam interagir com o EventManager.

    Fornece métodos helpers para publicar e subscribe a eventos
    de forma padronizada.

    Attributes:
        event_manager: Referência ao EventManager central

    Example:
        >>> class MyTab(QWidget, EventAwareMixin):
        ...     def __init__(self, event_manager):
        ...         super().__init__()
        ...         self.event_manager = event_manager
        ...         self.connect_events()
        ...
        ...     def connect_events(self):
        ...         self.event_manager.camera_updated.connect(
        ...             self.on_camera_updated
        ...         )
    """

    def __init__(self):
        """Inicializa mixin (deve ser chamado por classes filhas)."""
        self.event_manager: Optional[EventManager] = None

    def set_event_manager(self, event_manager: EventManager):
        """
        Define referência ao EventManager.

        Args:
            event_manager: Instância do EventManager
        """
        self.event_manager = event_manager
        self.connect_events()

    def connect_events(self):
        """
        Conecta signals do EventManager aos slots locais.

        Override este método para conectar eventos específicos.

        Example:
            def connect_events(self):
                self.event_manager.camera_updated.connect(
                    self.on_camera_updated
                )
                self.event_manager.event_detected.connect(
                    self.on_event_detected
                )
        """
        pass

    def disconnect_events(self):
        """
        Desconecta todos os signals do EventManager.

        Deve ser chamado ao destruir o componente para evitar memory leaks.
        """
        if self.event_manager:
            self.event_manager.disconnect(self)


# ============================================================================
# Integrador para MainWindow
# ============================================================================

class MainWindowEventIntegrator(QObject):
    """
    Integrador do EventManager com MainWindow.

    Gerencia a inicialização e coordenação de eventos entre
    MainWindow e suas abas, reduzindo acoplamento direto.

    Attributes:
        event_manager: Instância central do EventManager
        main_window: Referência à MainWindow

    Example:
        >>> integrator = MainWindowEventIntegrator(main_window)
        >>> integrator.setup_connections()
        >>> # Agora MainWindow usa events em vez de chamadas diretas
    """

    def __init__(self, main_window):
        """
        Inicializa integrador.

        Args:
            main_window: Instância da MainWindow
        """
        super().__init__(main_window)
        self.main_window = main_window
        self.event_manager = EventManager(parent=main_window)
        self._setup_main_window_connections()
        self._setup_tab_connections()

    def _setup_main_window_connections(self):
        """
        Conecta signals da MainWindow ao EventManager.

        publica eventos da MainWindow para que tabs possam escutar.
        """
        # Camera events
        self._connect_camera_events()

        # Monitor events
        self._connect_monitor_events()

        # User events
        self._connect_user_events()

        # Database events
        self._connect_database_events()

    def _connect_camera_events(self):
        """Conecta eventos relacionados a câmeras."""
        # Quando câmera é adicionada/atualizada/deletada no CamerasTab
        if hasattr(self.main_window, 'tab_cameras'):
            # CamerasTab publica eventos -> EventManager
            cameras_tab = self.main_window.tab_cameras
            if hasattr(cameras_tab, 'camera_added'):
                cameras_tab.camera_added.connect(
                    lambda cam: self.event_manager.camera_added.emit(cam)
                )
            if hasattr(cameras_tab, 'camera_updated'):
                cameras_tab.camera_updated.connect(
                    lambda cam: self.event_manager.camera_updated.emit(cam)
                )
            if hasattr(cameras_tab, 'camera_deleted'):
                cameras_tab.camera_deleted.connect(
                    lambda name: self.event_manager.camera_deleted.emit(name)
                )

        # MainWindow publica eventos -> EventManager
        # (ex: quando reload_camera_lists é chamado)
        if hasattr(self.main_window, 'reload_camera_lists'):
            # Wrap para publicar evento
            original_reload = self.main_window.reload_camera_lists
            def wrapped_reload():
                original_reload()
                self.event_manager.config_reloaded.emit()
            self.main_window.reload_camera_lists = wrapped_reload

    def _connect_monitor_events(self):
        """Conecta eventos relacionados a monitoramento."""
        if hasattr(self.main_window, 'start_all_monitors'):
            # Publicar evento quando todos monitores iniciam
            original_start = self.main_window.start_all_monitors
            def wrapped_start():
                result = original_start()
                if result:
                    self.event_manager.monitoring_all_started.emit()
            self.main_window.start_all_monitors = wrapped_start

        if hasattr(self.main_window, 'stop_all_monitors'):
            # Publicar evento quando todos monitores param
            original_stop = self.main_window.stop_all_monitors
            def wrapped_stop():
                result = original_stop()
                if result:
                    self.event_manager.monitoring_all_stopped.emit()
            self.main_window.stop_all_monitors = wrapped_stop

    def _connect_user_events(self):
        """Conecta eventos relacionados a usuários."""
        if hasattr(self.main_window, 'tab_users'):
            users_tab = self.main_window.tab_users
            if hasattr(users_tab, 'user_added'):
                users_tab.user_added.connect(
                    lambda user: self.event_manager.user_added.emit(user)
                )
            if hasattr(users_tab, 'user_updated'):
                users_tab.user_updated.connect(
                    lambda user: self.event_manager.user_updated.emit(user)
                )
            if hasattr(users_tab, 'user_deleted'):
                users_tab.user_deleted.connect(
                    lambda username: self.event_manager.user_deleted.emit(username)
                )
            if hasattr(users_tab, 'password_changed'):
                users_tab.password_changed.connect(
                    lambda username: self.event_manager.password_changed.emit(username)
                )

    def _connect_database_events(self):
        """Conecta eventos relacionados a banco de dados."""
        # Eventos de database são publicados por repositories
        # MainWindow subscribe se necessário
        pass

    def _setup_tab_connections(self):
        """
        Conecta abas para escutar eventos do EventManager.

        Substitui referências diretas entre abas por pub/sub.
        """
        # HistoryTab escuta eventos de câmera
        if hasattr(self.main_window, 'tab_history'):
            history_tab = self.main_window.tab_history
            self.event_manager.camera_added.connect(
                lambda cam: history_tab.set_camera_list(
                    self.main_window.config.get_camera_names()
                ) if hasattr(history_tab, 'set_camera_list') else None
            )
            self.event_manager.camera_deleted.connect(
                lambda name: history_tab.set_camera_list(
                    self.main_window.config.get_camera_names()
                ) if hasattr(history_tab, 'set_camera_list') else None
            )

        # ReportTab escuta eventos de câmera
        if hasattr(self.main_window, 'tab_report'):
            report_tab = self.main_window.tab_report
            self.event_manager.camera_added.connect(
                lambda cam: report_tab.set_camera_list(
                    self.main_window.config.get_camera_names()
                ) if hasattr(report_tab, 'set_camera_list') else None
            )
            self.event_manager.camera_deleted.connect(
                lambda name: report_tab.set_camera_list(
                    self.main_window.config.get_camera_names()
                ) if hasattr(report_tab, 'set_camera_list') else None
            )

        # MonitorTab escuta eventos de câmera
        if hasattr(self.main_window, 'tab_monitor'):
            monitor_tab = self.main_window.tab_monitor
            self.event_manager.camera_added.connect(
                lambda cam: self._update_monitor_camera_list(monitor_tab)
            )
            self.event_manager.camera_deleted.connect(
                lambda name: self._update_monitor_camera_list(monitor_tab)
            )

        # Dashboard escuta eventos de detecção
        if hasattr(self.main_window, 'tab_dashboard'):
            dashboard_tab = self.main_window.tab_dashboard
            self.event_manager.event_detected.connect(
                lambda event: self._handle_event_detected(dashboard_tab, event)
            )
            self.event_manager.overspeed_detected.connect(
                lambda event: self._handle_overspeed_detected(dashboard_tab, event)
            )

    def _update_monitor_camera_list(self, monitor_tab):
        """Atualiza lista de câmeras no MonitorTab."""
        if hasattr(monitor_tab, 'set_camera_list'):
            camera_names = self.main_window.config.get_camera_names()
            monitor_tab.set_camera_list(camera_names)

    def _handle_event_detected(self, dashboard_tab, event_data):
        """Lida com evento de detecção no Dashboard."""
        if hasattr(dashboard_tab, 'update_event_stats'):
            dashboard_tab.update_event_stats(event_data)
        if hasattr(dashboard_tab, 'append_log'):
            plate = event_data.get('plate', '-')
            speed = event_data.get('speed', '-')
            camera = event_data.get('camera_name', '-')
            dashboard_tab.append_log(
                f"Evento: {plate} - {speed} km/h ({camera})"
            )

    def _handle_overspeed_detected(self, dashboard_tab, event_data):
        """Lida com evento de excesso de velocidade no Dashboard."""
        if hasattr(dashboard_tab, 'update_overspeed_alert'):
            dashboard_tab.update_overspeed_alert(event_data)
        if hasattr(self.main_window, 'append_log'):
            plate = event_data.get('plate', '-')
            speed = event_data.get('speed', '-')
            limit = event_data.get('applied_speed_limit', '-')
            self.main_window.append_log(
                f"⚠️ EXCESSO: {plate} - {speed} km/h (limite: {limit} km/h)"
            )

    def publish_camera_update(self, camera_name: str, enabled: Optional[bool] = None):
        """
        Publica atualização de câmera de forma padronizada.

        Args:
            camera_name: Nome da câmera atualizada
            enabled: Novo estado (opcional)
        """
        self.event_manager.emit_camera_update(camera_name, enabled)

    def publish_event_detected(self, event_data: dict):
        """
        Publica evento de tráfego detectado.

        Args:
            event_data: Dicionário com dados do evento
        """
        self.event_manager.event_detected.emit(event_data)

        if event_data.get('is_overspeed'):
            self.event_manager.overspeed_detected.emit(event_data)

    def publish_error(self, context: str, description: str, exception: Optional[Exception] = None):
        """
        Publica erro de forma padronizada.

        Args:
            context: Contexto do erro
            description: Descrição do erro
            exception: Exceção (opcional)
        """
        self.event_manager.emit_error(context, description, exception)

    def get_event_manager(self) -> EventManager:
        """
        Retorna referência ao EventManager.

        Returns:
            EventManager: Instância do gerenciador de eventos
        """
        return self.event_manager


# ============================================================================
# Funções auxiliares para integração
# ============================================================================

def setup_event_integration(main_window) -> MainWindowEventIntegrator:
    """
    Configura integração de eventos para MainWindow.

    Função de conveniência para inicializar o integrador.

    Args:
        main_window: Instância da MainWindow

    Returns:
        MainWindowEventIntegrator: Integrador configurado

    Example:
        >>> in __init__ de MainWindow:
        >>> self.event_integrator = setup_event_integration(self)
    """
    integrator = MainWindowEventIntegrator(main_window)
    return integrator


def publish_to_tabs(event_manager: EventManager, event_name: str, *args):
    """
    Publica evento para todas as abas interessadas.

    Função auxiliar para publicar eventos sem conhecer
    quais abas estão listening.

    Args:
        event_manager: Instância do EventManager
        event_name: Nome do evento (atributo do EventManager)
        *args: Argumentos para o signal

    Example:
        >>> publish_to_tabs(
        ...     self.event_manager,
        ...     'camera_updated',
        ...     camera_data
        ... )
    """
    if hasattr(event_manager, event_name):
        signal = getattr(event_manager, event_name)
        signal.emit(*args)
