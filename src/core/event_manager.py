# Event Manager (FASE 3.2 - Architecture)
"""
Sistema de gerenciamento de eventos para desacoplamento de componentes.

Implementa padrão Observer/Pub-Sub usando Qt signals, permitindo que
componentes se comuniquem sem acoplamento direto.

Benefits:
- Desacoplamento: Componentes não se referenciam diretamente
- Testabilidade: Fácil mock de eventos para testes
- Flexibilidade: Fácil adicionar/remover subscribers
- Manutenibilidade: Comunicação explícita e documentada

Usage:
    # Publisher (MainWindow)
    event_manager = EventManager()
    event_manager.camera_added.emit(camera_data)

    # Subscriber (HistoryTab)
    event_manager.camera_added.connect(self.on_camera_added)
"""

from PySide6.QtCore import QObject, Signal
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


class EventManager(QObject):
    """
    Gerenciador central de eventos da aplicação.

    Fornece signals para todos os eventos significativos que ocorrem
    no sistema, permitindo que diferentes componentes (abas, workers)
    se comuniquem sem acoplamento direto.

    Implementa padrão Singleton através de referência compartilhada
    passada pelo construtor.

    Example:
        >>> events = EventManager()
        >>> events.camera_updated.connect(lambda cam: print(f"Updated: {cam['name']}"))
        >>> events.camera_updated.emit({"name": "Camera 1"})
    """

    # ========================================================================
    # Camera Events
    # ========================================================================

    camera_added = Signal(dict)  # Emitido quando nova câmera é adicionada
    """Signal(dict): Emitido quando nova câmera é adicionada.

    Args:
        dict: Dados completos da câmera adicionada
    """

    camera_updated = Signal(dict)  # Emitido quando câmera é modificada
    """Signal(dict): Emitido quando configuração de câmera é atualizada.

    Args:
        dict: Novos dados da câmera
    """

    camera_deleted = Signal(str)  # Emitido quando câmera é removida
    """Signal(str): Emitido quando câmera é deletada.

    Args:
        str: Nome da câmera deletada
    """

    camera_enabled = Signal(str, bool)  # Emitido quando câmera é habilitada/desabilitada
    """Signal(str, bool): Emitido quando status de câmera muda.

    Args:
        str: Nome da câmera
        bool: Novo estado (True=habilitada, False=desabilitada)
    """

    camera_connection_changed = Signal(str, bool, str)  # Status de conexão
    """Signal(str, bool, str): Emitido quando status de conexão muda.

    Args:
        str: Nome da câmera
        bool: True=conectada, False=desconectada
        str: Mensagem de status ou erro
    """

    camera_renamed = Signal(str, str)  # Câmera renomeada
    """Signal(str, str): Emitido quando câmera é renomeada.

    Args:
        str: Nome antigo da câmera
        str: Novo nome da câmera
    """

    # ========================================================================
    # Monitor/Detection Events
    # ========================================================================

    monitoring_started = Signal(str)  # Monitoramento iniciado para câmera
    """Signal(str): Emitido quando monitoramento inicia.

    Args:
        str: Nome da câmera
    """

    monitoring_stopped = Signal(str)  # Monitoramento parado para câmera
    """Signal(str): Emitido quando monitoramento para.

    Args:
        str: Nome da câmera
    """

    event_detected = Signal(dict)  # Novo evento de tráfego detectado
    """Signal(dict): Emitido quando novo evento de tráfego é detectado.

    Args:
        dict: Dados completos do evento (camera_name, plate, speed, etc.)
    """

    overspeed_detected = Signal(dict)  # Excesso de velocidade detectado
    """Signal(dict): Emitido quando excesso de velocidade é detectado.

    Args:
        dict: Dados do evento com overspeed
    """

    snapshot_captured = Signal(str, str)  # Snapshot capturado
    """Signal(str, str): Emitido quando snapshot é capturado.

    Args:
        str: Nome da câmera
        str: Caminho para imagem do snapshot
    """

    # ========================================================================
    # User Events
    # ========================================================================

    user_logged_in = Signal(dict)  # Usuário fez login
    """Signal(dict): Emitido quando usuário faz login.

    Args:
        dict: Dados do usuário (username, role, etc.)
    """

    user_logged_out = Signal(str)  # Usuário fez logout
    """Signal(str): Emitido quando usuário faz logout.

    Args:
        str: Nome do usuário
    """

    user_added = Signal(dict)  # Novo usuário adicionado
    """Signal(dict): Emitido quando novo usuário é criado.

    Args:
        dict: Dados do usuário criado
    """

    user_updated = Signal(dict)  # Usuário atualizado
    """Signal(dict): Emitido quando usuário é modificado.

    Args:
        dict: Novos dados do usuário
    """

    user_deleted = Signal(str)  # Usuário deletado
    """Signal(str): Emitido quando usuário é deletado.

    Args:
        str: Nome do usuário deletado
    """

    password_changed = Signal(str)  # Senha alterada
    """Signal(str): Emitido quando usuário altera senha.

    Args:
        str: Nome do usuário
    """

    # ========================================================================
    # Configuration Events
    # ========================================================================

    config_reloaded = Signal()  # Configuração recarregada
    """Signal(): Emitido quando arquivo de configuração é recarregado."""

    config_saved = Signal()  # Configuração salva
    """Signal(): Emitido quando configuração é salva no disco."""

    speed_limit_changed = Signal(str, float)  # Limite de velocidade alterado
    """Signal(str, float): Emitido quando limite de velocidade muda.

    Args:
        str: Nome da câmera ou "global" para limite global
        float: Novo limite de velocidade
    """

    # ========================================================================
    # Database Events
    # ========================================================================

    database_event_inserted = Signal(int)  # Evento inserido
    """Signal(int): Emitido quando evento é inserido no banco.

    Args:
        int: ID do evento inserido
    """

    database_events_cleared = Signal()  # Eventos deletados
    """Signal(): Emitido quando eventos são deletados do banco."""

    database_backup_created = Signal(str)  # Backup criado
    """Signal(str): Emitido quando backup do banco é criado.

    Args:
        str: Caminho para arquivo de backup
    """

    # ========================================================================
    # Evolution API Events
    # ========================================================================

    evolution_message_sent = Signal(dict, bool)  # Mensagem enviada
    """Signal(dict, bool): Emitido quando mensagem WhatsApp é enviada.

    Args:
        dict: Dados do evento associado
        bool: True se enviada com sucesso, False se falhou
    """

    evolution_test_result = Signal(bool, str)  # Teste de conexão
    """Signal(bool, str): Emitido quando teste de Evolution API termina.

    Args:
        bool: True se sucesso, False se falhou
        str: Mensagem de resultado
    """

    evolution_settings_changed = Signal()  # Configuração alterada
    """Signal(): Emitido quando configurações da Evolution API mudam."""

    # ========================================================================
    # UI Events
    # ========================================================================

    tab_changed = Signal(str)  # Aba alterada
    """Signal(str): Emitido quando aba ativa muda.

    Args:
        str: Nome da nova aba ativa
    """

    refresh_requested = Signal(str)  # Refresh solicitado
    """Signal(str): Emitido quando aba solicita refresh de dados.

    Args:
        str: Nome da aba que solicitou refresh
    """

    data_exported = Signal(str, str)  # Dados exportados
    """Signal(str, str): Emitido quando exportação de dados completa.

    Args:
        str: Tipo de exportação (csv, json, etc.)
        str: Caminho do arquivo exportado
    """

    # ========================================================================
    # System Events
    # ========================================================================

    application_closing = Signal()  # Aplicação fechando
    """Signal(): Emitido quando aplicação está iniciando fechamento."""

    application_closing_cancelled = Signal()  # Fechamento cancelado
    """Signal(): Emitido quando fechamento é cancelado."""

    monitoring_all_started = Signal()  # Todos monitores iniciados
    """Signal(): Emitido quando todos os monitoramentos são iniciados."""

    monitoring_all_stopped = Signal()  # Todos monitores parados
    """Signal(): Emitido quando todos os monitoramentos são parados."""

    # ========================================================================
    # Logging Events
    # ========================================================================

    log_message = Signal(str, str)  # Mensagem de log
    """Signal(str, str): Emitido quando mensagem deve ser logada.

    Args:
        str: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        str: Mensagem de log
    """

    # ========================================================================
    # Error Events
    # ========================================================================

    error_occurred = Signal(str, str, Exception)  # Erro ocorreu
    """Signal(str, str, Exception): Emitido quando erro ocorre.

    Args:
        str: Contexto onde erro ocorreu (ex: "camera", "database")
        str: Descrição do erro
        Exception: Exceção capturada (opcional)
    """

    critical_error = Signal(str, Exception)  # Erro crítico
    """Signal(str, Exception): Emitido quando erro crítico ocorre.

    Args:
        str: Descrição do erro crítico
        Exception: Exceção capturada
    """

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def __init__(self, parent: Optional[QObject] = None):
        """
        Inicializa gerenciador de eventos.

        Args:
            parent: Objeto pai Qt (opcional)
        """
        super().__init__(parent)

    def emit_log(self, level: str, message: str):
        """
        Emite evento de log de forma padronizada.

        Args:
            level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Mensagem de log
        """
        self.log_message.emit(level, message)

    def emit_error(self, context: str, description: str, exception: Optional[Exception] = None):
        """
        Emite evento de erro de forma padronizada.

        Args:
            context: Contexto onde erro ocorreu
            description: Descrição do erro
            exception: Exceção capturada (opcional)
        """
        if exception:
            self.error_occurred.emit(context, description, exception)
        else:
            self.error_occurred.emit(context, description, Exception(description))

    def emit_camera_update(self, camera_name: str, enabled: Optional[bool] = None):
        """
        Emite eventos de atualização de câmera de forma padronizada.

        Args:
            camera_name: Nome da câmera
            enabled: Novo estado habilitada/desabilitada (opcional)
        """
        if enabled is not None:
            self.camera_enabled.emit(camera_name, enabled)
        self.camera_updated.emit({"name": camera_name})


# ============================================================================
# Event Data Classes (para tipagem forte)
# ============================================================================

@dataclass
class CameraEventData:
    """Dados para eventos de câmera."""
    name: str
    enabled: bool
    ip: str
    port: int


@dataclass
class TrafficEventData:
    """Dados para eventos de tráfego."""
    camera_name: str
    plate: str
    speed: float
    lane: str
    direction: str
    timestamp: str
    is_overspeed: bool
    image_path: Optional[str] = None


@dataclass
class UserEventData:
    """Dados para eventos de usuário."""
    username: str
    role: str


# ============================================================================
# Funções auxiliares
# ============================================================================

def create_event_manager() -> EventManager:
    """
    Factory function para criar EventManager.

    Permite facilmente substituir por mock em testes.

    Returns:
        EventManager: Nova instância do gerenciador de eventos
    """
    return EventManager()
