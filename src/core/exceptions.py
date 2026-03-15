# Custom Exceptions Module (FASE 2 - Code Quality)
"""
Exceções customizadas para o Hikvision Radar Pro V4.2.

Fornece exceções específicas para diferentes categorias de erros,
permitindo tratamento granular e melhor debugging.
"""

from typing import Optional, Any


class HikvisionRadarError(Exception):
    """
    Classe base para todas as exceções da aplicação.

    Todas as exceções customizadas devem herdar desta classe,
    permitindo captura genérica quando necessário.
    """

    def __init__(self, message: str, details: Optional[Any] = None):
        """
        Inicializa exceção base.

        Args:
            message: Mensagem de erro descritiva
            details: Detalhes adicionais sobre o erro (opcional)
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Retorna representação em string do erro."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


# ============================================================================
# Exceções de Configuração
# ============================================================================

class ConfigurationError(HikvisionRadarError):
    """
    Erro relacionado à configuração da aplicação.

    Levantada quando há problemas ao carregar, salvar ou validar
    arquivos de configuração.
    """

    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Any] = None):
        """
        Inicializa erro de configuração.

        Args:
            message: Mensagem de erro descritiva
            config_key: Chave de configuração problemática (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, details)
        self.config_key = config_key


class InvalidConfigurationError(ConfigurationError):
    """Levantada quando a configuração é inválida ou malformada."""
    pass


class ConfigurationMigrationError(ConfigurationError):
    """Levantada quando falha a migração de configuração antiga para novo formato."""
    pass


class FirstRunRequiredError(ConfigurationError):
    """
    Levantada quando o sistema precisa ser configurado pela primeira vez.

    Esta exceção indica que não há usuários configurados e o wizard
    de primeira execução deve ser exibido.
    """
    pass


# ============================================================================
# Exceções de Câmera
# ============================================================================

class CameraError(HikvisionRadarError):
    """
    Classe base para erros relacionados a câmeras.

    Levantada em operações com câmeras Hikvision.
    """

    def __init__(self, message: str, camera_name: Optional[str] = None, details: Optional[Any] = None):
        """
        Inicializa erro de câmera.

        Args:
            message: Mensagem de erro descritiva
            camera_name: Nome da câmera relacionada ao erro (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, details)
        self.camera_name = camera_name


class CameraConnectionError(CameraError):
    """
    Erro de conexão com câmera.

    Levantada quando não é possível estabelecer conexão com a câmera,
    seja por timeout, rede indisponível, ou endereço incorreto.
    """

    def __init__(
        self,
        message: str,
        camera_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        details: Optional[Any] = None
    ):
        """
        Inicializa erro de conexão.

        Args:
            message: Mensagem de erro descritiva
            camera_name: Nome da câmera (opcional)
            host: Endereço IP da câmera (opcional)
            port: Porta de conexão (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, camera_name, details)
        self.host = host
        self.port = port


class AuthenticationError(CameraError):
    """
    Erro de autenticação com câmera.

    Levantada quando as credenciais fornecidas são inválidas ou
    a câmera recusa a autenticação.
    """

    def __init__(
        self,
        message: str,
        camera_name: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Any] = None
    ):
        """
        Inicializa erro de autenticação.

        Args:
            message: Mensagem de erro descritiva
            camera_name: Nome da câmera (opcional)
            username: Nome de usuário usado na tentativa (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, camera_name, details)
        self.username = username


class CameraNotSupportedError(CameraError):
    """
    Erro levantada quando a câmera não suporta a operação solicitada.

    Por exemplo, câmera não suporta modo de tráfego ou alertStream.
    """
    pass


class SnapshotError(CameraError):
    """Erro ao capturar snapshot da câmera."""
    pass


class RTSPStreamError(CameraError):
    """Erro ao abrir stream RTSP da câmera."""
    pass


class AlertStreamError(CameraError):
    """Erro ao conectar ao alert stream da câmera."""
    pass


class CameraRenameError(CameraError):
    """
    Erro ao renomear câmera.

    Levantada quando falha a operação de renomeação de câmera,
    seja por nome duplicado, erro de transação ou problema de migração.
    """

    def __init__(
        self,
        message: str,
        old_name: Optional[str] = None,
        new_name: Optional[str] = None,
        details: Optional[Any] = None
    ):
        """
        Inicializa erro de renomeação.

        Args:
            message: Mensagem de erro descritiva
            old_name: Nome antigo da câmera (opcional)
            new_name: Novo nome da câmera (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, old_name or new_name, details)
        self.old_name = old_name
        self.new_name = new_name


# ============================================================================
# Exceções de Criptografia
# ============================================================================

class CryptoError(HikvisionRadarError):
    """
    Erro relacionado à criptografia/descriptografia.

    Levantada quando há problemas no processo de criptografia de senhas.
    """

    def __init__(self, message: str, details: Optional[Any] = None):
        """
        Inicializa erro de criptografia.

        Args:
            message: Mensagem de erro descritiva
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, details)


class DecryptionError(CryptoError):
    """Erro específico ao descriptografar dados."""
    pass


class EncryptionError(CryptoError):
    """Erro específico ao criptografar dados."""
    pass


# ============================================================================
# Exceções de Banco de Dados
# ============================================================================

class DatabaseError(HikvisionRadarError):
    """
    Classe base para erros de banco de dados.

    Levantada em operações com o SQLite.
    """

    def __init__(self, message: str, query: Optional[str] = None, details: Optional[Any] = None):
        """
        Inicializa erro de banco de dados.

        Args:
            message: Mensagem de erro descritiva
            query: Query que causou o erro (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, details)
        self.query = query


class DatabaseConnectionError(DatabaseError):
    """Erro ao conectar ao banco de dados."""
    pass


class DatabaseQueryError(DatabaseError):
    """Erro ao executar query no banco de dados."""
    pass


class DatabaseMigrationError(DatabaseError):
    """Erro ao migrar esquema do banco de dados."""
    pass


# ============================================================================
# Exceções de Validação
# ============================================================================

class ValidationError(HikvisionRadarError):
    """
    Erro de validação de dados.

    Levantada quando dados de entrada não atendem aos requisitos.
    """

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        """
        Inicializa erro de validação.

        Args:
            message: Mensagem de erro descritiva
            field: Campo que falhou na validação (opcional)
            value: Valor que foi rejeitado (opcional)
        """
        super().__init__(message)
        self.field = field
        self.value = value


# ============================================================================
# Exceções de Evolução API
# ============================================================================

class EvolutionAPIError(HikvisionRadarError):
    """
    Classe base para erros da Evolution API.

    Levantada em operações de envio de mensagens WhatsApp.
    """

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        """
        Inicializa erro de Evolution API.

        Args:
            message: Mensagem de erro descritiva
            status_code: Código HTTP da resposta (opcional)
            details: Detalhes adicionais (opcional)
        """
        super().__init__(message, details)
        self.status_code = status_code


class EvolutionConnectionError(EvolutionAPIError):
    """Erro de conexão com Evolution API."""
    pass


class EvolutionAuthenticationError(EvolutionAPIError):
    """Erro de autenticação com Evolution API."""
    pass


class EvolutionMessageError(EvolutionAPIError):
    """Erro ao enviar mensagem via Evolution API."""
    pass


# ============================================================================
# Exceções de Detecção
# ============================================================================

class DetectionError(HikvisionRadarError):
    """
    Classe base para erros de detecção.

    Levantada durante processamento de detecção de veículos.
    """
    pass


class CarDetectorError(DetectionError):
    """Erro no detector de carros."""
    pass


class PlateRecognitionError(DetectionError):
    """Erro ao reconhecer placa."""
    pass


# ============================================================================
# Exceções de UI
# ============================================================================

class UIError(HikvisionRadarError):
    """
    Classe base para erros de interface do usuário.

    Levantada em operações relacionadas à UI Qt.
    """
    pass


class TabError(UIError):
    """Erro em abas da interface."""
    pass


class WorkerError(UIError):
    """Erro em worker threads da UI."""
    pass


# ============================================================================
# Funções auxiliares
# ============================================================================

def format_exception(exc: Exception) -> str:
    """
    Formata exceção para exibição amigável ao usuário.

    Args:
        exc: Exceção a ser formatada

    Returns:
        str: Mensagem formatada para exibição
    """
    if isinstance(exc, HikvisionRadarError):
        return str(exc)
    return f"Erro inesperado: {exc}"


def is_critical_error(exc: Exception) -> bool:
    """
    Verifica se uma exceção é crítica (requer intervenção do usuário).

    Args:
        exc: Exceção a ser verificada

    Returns:
        bool: True se erro é crítico, False caso contrário
    """
    critical_types = (
        ConfigurationError,
        DatabaseConnectionError,
        FirstRunRequiredError,
    )
    return isinstance(exc, critical_types)


def is_recoverable_error(exc: Exception) -> bool:
    """
    Verifica se uma exceção é recuperável (pode tentar novamente).

    Args:
        exc: Exceção a ser verificada

    Returns:
        bool: True se erro é recuperável, False caso contrário
    """
    recoverable_types = (
        CameraConnectionError,
        SnapshotError,
        AlertStreamError,
        EvolutionConnectionError,
    )
    return isinstance(exc, recoverable_types)
