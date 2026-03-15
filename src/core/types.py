# Type Definitions (FASE 4.3 - Type Hints)
"""
Definições de tipos customizados para uso em type hints no projeto.

Facilita a manutenção e garante consistência nos type hints.
"""

from typing import (
    Any, Dict, List, Tuple, Optional, Union, Callable, TypeVar, Protocol,
    runtime_checkable
)
from pathlib import Path
from datetime import datetime


# ============================================================================
# Type Aliases para Tipos Comuns
# ============================================================================

# Tipos JSON
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]
JSONArray = List[JSONValue]

# Tipos de Caminho
PathLike = Union[str, Path]

# Tipos de Retorno de Validador
ValidationResult = Tuple[bool, str]
ValidationResults = Tuple[bool, List[str]]

# Tipos de Callback
Callback = Callable[..., None]
EventCallback = Callable[..., None]

# Tipos de Database
DatabaseRow = Tuple[Any, ...]
DatabaseRows = List[DatabaseRow]

# ============================================================================
# Type Aliases para Entidades
# ============================================================================

CameraConfig = Dict[str, Any]
"""
Dicionário com configuração de câmera.

Campos obrigatórios: name, camera_ip, camera_port, camera_user
Campos opcionais: camera_pass, channel, timeout, speed_limit_value, etc.
"""

UserData = Dict[str, Any]
"""
Dicionário com dados de usuário.

Campos: username, password_hash, password_salt, role, must_change_password
"""

EventData = Dict[str, Any]
"""
Dicionário com dados de evento de tráfego.

Campos: camera_name, ts, plate, speed, speed_value, lane, direction,
        event_type, image_path, is_overspeed, etc.
"""

# ============================================================================
# Type Variables para Generics
# ============================================================================

T = TypeVar('T')
"""Type variable genérico."""

TModel = TypeVar('TModel', bound='Model')
"""Type variable para modelos."""

TRepository = TypeVar('TRepository', bound='Repository')
"""Type variable para repositories."""

# ============================================================================
# Protocols (duck typing com type hints)
# ============================================================================

class Model(Protocol):
    """
    Protocolo para modelos de dados.

    Classes que implementam este protocolo devem ter métodos
    básicos de persistência.
    """

    def save(self) -> None:
        """Salva instância no armazenamento."""
        ...

    def delete(self) -> None:
        """Remove instância do armazenamento."""
        ...

    @classmethod
    def get(cls, id: int) -> Optional['Model']:
        """Retorna instância por ID."""
        ...


class Repository(Protocol):
    """
    Protocolo para repositories.

    Repositories devem implementar métodos CRUD básicos.
    """

    def find_all(self) -> List[Any]:
        """Retorna todos os registros."""
        ...

    def find_by_id(self, id: int) -> Optional[Any]:
        """Retorna registro por ID."""
        ...

    def insert(self, data: Dict[str, Any]) -> int:
        """Insere novo registro e retorna ID."""
        ...

    def update(self, data: Dict[str, Any]) -> None:
        """Atualiza registro existente."""
        ...

    def delete(self, id: int) -> bool:
        """Deleta registro por ID. Retorna True se deletou."""
        ...


class Validator(Protocol):
    """
    Protocolo para validadores.

    Validadores devem retornar tupla (is_valid, error_message).
    """

    def __call__(self, value: Any) -> ValidationResult:
        """
        Valida valor e retorna resultado.

        Returns:
            Tuple[bool, str]: (True, "") se válido, (False, erro) se inválido
        """
        ...


class EventHandler(Protocol):
    """
    Protocolo para handlers de eventos.
    """

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """
        Manipula evento.

        Args:
            *args: Argumentos posicionais do evento
            **kwargs: Argumentos nomeados do evento
        """
        ...


class CameraClient(Protocol):
    """
    Protocolo para clientes de câmera.
    """

    def test_connection(self) -> Tuple[bool, int, str]:
        """Testa conexão com câmera."""
        ...

    def download_snapshot(self) -> Tuple[bytes, str]:
        """Baixa snapshot da câmera."""
        ...


class DatabaseClient(Protocol):
    """
    Protocolo para clientes de banco de dados.
    """

    def execute(self, sql: str, params: Tuple = ()) -> Any:
        """Executa query SQL."""
        ...

    def commit(self) -> None:
        """Confirma transação."""
        ...

    def close(self) -> None:
        """Fecha conexão."""
        ...


# ============================================================================
# Tipos Específicos do Domínio
# ============================================================================

SpeedValue = Union[float, int, str]
"""
Tipo para valores de velocidade.

Pode ser:
- float: 85.5
- int: 85
- str: "85 km/h"
"""

PlateNumber = str
"""Tipo para número de placa."""

CameraName = str
"""Tipo para nome de câmera."""

Username = str
"""Tipo para nome de usuário."""

Password = str
"""Tipo para senha (texto claro)."""

PasswordHash = str
"""Tipo para hash de senha."""

EncryptedPassword = Dict[str, str]
"""
Tipo para senha criptografada.

Formato: {"encrypted": base64_string, "nonce": base64_string}
"""

# ============================================================================
# Tipos de Configuração
# ============================================================================

ServerConfig = Dict[str, Any]
"""
Configuração de servidor.

Campos: host, port, username, password, use_ssl, etc.
"""

DatabaseConfig = Dict[str, Any]
"""
Configuração de banco de dados.

Campos: path, pool_size, timeout, etc.
"""

LoggingConfig = Dict[str, Any]
"""
Configuração de logging.

Campos: level, file, max_size, backup_count, etc.
"""

# ============================================================================
# Tipos de UI
# ============================================================================

QWidget = Any
"""
Tipo genérico para widgets Qt.

Usar PySide6.QtWidgets.QWidget em type hints específicos quando necessário.
"""

QSignal = Any
"""
Tipo genérico para signals Qt.
"""

# ============================================================================
# Tipos de Resposta
# ============================================================================

class Response(Protocol):
    """
    Protocolo para respostas de operações.
    """

    @property
    def success(self) -> bool:
        """True se operação foi bem-sucedida."""
        ...

    @property
    def error(self) -> Optional[str]:
        """Mensagem de erro se falhou."""
        ...

    @property
    def data(self) -> Any:
        """Dados retornados pela operação."""
        ...


class ServiceResponse:
    """
    Implementação padrão de Response para serviços.

    Attributes:
        success: True se operação bem-sucedida
        error: Mensagem de erro se houve falha
        data: Dados retornados
    """

    def __init__(
        self,
        success: bool = True,
        error: Optional[str] = None,
        data: Any = None
    ):
        """
        Inicializa resposta.

        Args:
            success: Indica se operação foi bem-sucedida
            error: Mensagem de erro (se houve)
            data: Dados retornados
        """
        self._success = success
        self._error = error
        self._data = data

    @property
    def success(self) -> bool:
        """True se operação foi bem-sucedida."""
        return self._success

    @property
    def error(self) -> Optional[str]:
        """Mensagem de erro se falhou."""
        return self._error

    @property
    def data(self) -> Any:
        """Dados retornados pela operação."""
        return self._data

    @classmethod
    def ok(cls, data: Any = None) -> 'ServiceResponse':
        """Cria resposta de sucesso."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> 'ServiceResponse':
        """Cria resposta de falha."""
        return cls(success=False, error=error)

    def __bool__(self) -> bool:
        """Permite usar response como booleano."""
        return self._success


# ============================================================================
# Tipos para Enums
# ============================================================================

LogLevel = str
"""
Nível de log: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""

UserRole = str
"""
Papel de usuário: Administrador, Operador
"""

CameraMode = str
"""
Modo de câmera: auto, traffic, normal
"""

EventType = str
"""
Tipo de evento: normal, overspeed, error
"""

# ============================================================================
# Tipos de Timestamp
# ============================================================================

Timestamp = Union[str, datetime]
"""
Tipo para timestamp.

Pode ser string formatada ou objeto datetime.
"""

ISO8601 = str
"""
Timestamp em formato ISO 8601.

Exemplo: "2026-03-14T10:30:00-03:00"
"""

# ============================================================================
# Decorator Types
# ============================================================================

F = TypeVar('F', bound=Callable[..., Any])
"""Type variable para funções decoradas."""


def logged(func: F) -> F:
    """
    Decorator para logging de funções.

    Type hint preserva assinatura original da função.
    """
    return func  # Simplificado - implementação real faria logging
