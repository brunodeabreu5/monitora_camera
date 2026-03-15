# Dependency Injection Container (FASE 3.4 - Architecture)
"""
Container de Injeção de Dependências para o Hikvision Radar Pro.

Gerencia ciclo de vida de serviços e suas dependências, permitindo:
- Maior testabilidade (fácil mock de dependências)
- Desacoplamento entre componentes
- Configuração centralizada de serviços
- Ciclo de vida controlado (singleton/transient)

Usage:
    container = DIContainer()
    container.register_singleton(Database, lambda: Database(db_path))
    container.register_singleton(AppConfig, lambda: AppConfig())

    db = container.get(Database)
    config = container.get(AppConfig)
"""

import inspect
from typing import Type, TypeVar, Callable, Dict, Any, Optional, get_type_hints
from abc import ABC, abstractmethod


# Type variables
T = TypeVar('T')


class DIContainer:
    """
    Container de Injeção de Dependências simples.

    Implementa registro e resolução de dependências com suporte a:
    - Singletons (uma instância compartilhada)
    - Transients (nova instância a cada requisição)
    - Injeção por construtor
    - Factory functions

    Attributes:
        _singletons: Dicionário de singletons registrados
        _factories: Dicionário de factories registradas
        _instances: Dicionário de instâncias singletons criadas

    Example:
        >>> container = DIContainer()
        >>> container.register_singleton(Database, lambda: Database(":memory:"))
        >>> db = container.get(Database)
        >>> assert db is container.get(Database)  # Mesma instância
    """

    def __init__(self):
        """Inicializa container vazio."""
        self._singletons: Dict[Type, Callable] = {}
        self._factories: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}

    def register_singleton(self, interface: Type[T], factory: Callable[..., T]) -> None:
        """
        Registra serviço como singleton.

        A factory será chamada uma vez e a instância será reusada
        em todas as chamadas subsequentes a get().

        Args:
            interface: Tipo/classe do serviço
            factory: Factory function que cria a instância

        Example:
            >>> container.register_singleton(
            ...     Database,
            ...     lambda: Database("events.db")
            ... )
        """
        self._singletons[interface] = factory
        # Remover instância existente se houver (força recriação)
        if interface in self._instances:
            del self._instances[interface]

    def register_transient(self, interface: Type[T], factory: Callable[..., T]) -> None:
        """
        Registra serviço como transient.

        A factory será chamada a cada requisição get(), criando
        novas instâncias.

        Args:
            interface: Tipo/classe do serviço
            factory: Factory function que cria a instância

        Example:
            >>> container.register_transient(
            ...     HttpClient,
            ...     lambda: HttpClient()
            ... )
        """
        self._factories[interface] = factory

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Registra instância existente como singleton.

        Útil para registrar mocks em testes ou configurações
        pré-criadas.

        Args:
            interface: Tipo/classe do serviço
            instance: Instância a registrar

        Example:
            >>> mock_db = Mock(spec=Database)
            >>> container.register_instance(Database, mock_db)
        """
        self._instances[interface] = instance

    def get(self, interface: Type[T]) -> T:
        """
        Resolve e retorna instância do serviço.

        Se for singleton registrado, retorna instância existente ou cria nova.
        Se for transient, sempre cria nova instância.
        Se foi registrada instância, retorna a instância registrada.

        Args:
            interface: Tipo/classe do serviço desejado

        Returns:
            T: Instância do serviço

        Raises:
            ValueError: Se serviço não está registrado

        Example:
            >>> db = container.get(Database)
            >>> config = container.get(AppConfig)
        """
        # Verificar se há instância registrada
        if interface in self._instances:
            return self._instances[interface]

        # Verificar se é singleton
        if interface in self._singletons:
            if interface not in self._instances:
                factory = self._singletons[interface]
                instance = self._create_instance(factory)
                self._instances[interface] = instance
            return self._instances[interface]

        # Verificar se é transient
        if interface in self._factories:
            factory = self._factories[interface]
            return self._create_instance(factory)

        raise ValueError(f"Serviço não registrado: {interface.__name__}")

    def try_get(self, interface: Type[T]) -> Optional[T]:
        """
        Tenta resolver serviço, retornando None se não registrado.

        Args:
            interface: Tipo/classe do serviço

        Returns:
            Optional[T]: Instância do serviço ou None
        """
        try:
            return self.get(interface)
        except ValueError:
            return None

    def is_registered(self, interface: Type) -> bool:
        """
        Verifica se serviço está registrado.

        Args:
            interface: Tipo/classe do serviço

        Returns:
            bool: True se registrado, False caso contrário
        """
        return (
            interface in self._instances or
            interface in self._singletons or
            interface in self._factories
        )

    def clear(self) -> None:
        """
        Limpa todos os registros e instâncias.

        Útil principalmente em testes para resetar estado.
        """
        self._singletons.clear()
        self._factories.clear()
        self._instances.clear()

    def reset_singleton(self, interface: Type) -> None:
        """
        Reseta instância singleton, forçando recriação no próximo get().

        Args:
            interface: Tipo/classe do serviço
        """
        if interface in self._instances:
            del self._instances[interface]

    def _create_instance(self, factory: Callable) -> Any:
        """
        Cria instância usando factory, injetando dependências.

        Examina os parâmetros da factory e tenta resolver
        automaticamente as dependências registradas no container.

        Args:
            factory: Factory function ou classe

        Returns:
            Any: Nova instância criada
        """
        # Obter assinatura da factory
        sig = inspect.signature(factory if inspect.isfunction(factory) else factory.__init__)

        # Construir kwargs resolvendo dependências
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Tentar obter type hint
            param_type = param.annotation

            if param_type == inspect.Parameter.empty:
                # Sem type hint, tentar obter de get_type_hints
                try:
                    hints = get_type_hints(factory)
                    param_type = hints.get(param_name)
                except Exception:
                    continue

            if param_type and param_type != inspect.Parameter.empty:
                # Tentar resolver dependência
                if self.is_registered(param_type):
                    kwargs[param_name] = self.get(param_type)

        # Criar instância com dependências injetadas
        return factory(**kwargs)


# ============================================================================
# Container Global e Configuração
# ============================================================================

# Container global padrão
_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """
    Retorna container global de DI.

    Inicializa container se não existir.

    Returns:
        DIContainer: Container global

    Example:
        >>> container = get_container()
        >>> container.register_singleton(Database, lambda: create_db())
    """
    global _global_container
    if _global_container is None:
        _global_container = DIContainer()
    return _global_container


def reset_global_container() -> None:
    """
    Reseta container global.

    Útil principalmente em testes para isolar cenários.
    """
    global _global_container
    _global_container = None


# ============================================================================
# Configurador de Container
# ============================================================================

def configure_default_container(db_path: Any = None, config_path: Any = None) -> DIContainer:
    """
    Configura container com serviços padrão da aplicação.

    Registra todos os serviços principais: Database, AppConfig,
    Repositories, etc.

    Args:
        db_path: Caminho para banco de dados (opcional)
        config_path: Caminho para arquivo de config (opcional)

    Returns:
        DIContainer: Container configurado

    Example:
        >>> from pathlib import Path
        >>> container = configure_default_container(
        ...     db_path=Path("events.db"),
        ...     config_path=Path("config.json")
        ... )
        >>> db = container.get(Database)
    """
    from pathlib import Path
    from src.core.config import AppConfig, app_dir, DB_FILE
    from src.core.database import Database
    from src.repositories import EventRepository, CameraRepository, UserRepository

    container = get_container()

    # Caminhos padrão
    if db_path is None:
        default_output = Path(app_dir() / "output")
        default_output.mkdir(parents=True, exist_ok=True)
        db_path = default_output / DB_FILE

    # Registrar Database como singleton
    container.register_singleton(
        Database,
        lambda: db_path if isinstance(db_path, Database) else Database(db_path)
    )

    # Registrar AppConfig como singleton
    container.register_singleton(
        AppConfig,
        lambda: config_path if isinstance(config_path, AppConfig) else AppConfig(config_path)
    )

    # Registrar Repositories
    container.register_transient(
        EventRepository,
        lambda: EventRepository(container.get(Database))
    )

    container.register_transient(
        CameraRepository,
        lambda: CameraRepository(container.get(AppConfig))
    )

    container.register_transient(
        UserRepository,
        lambda: UserRepository(container.get(AppConfig))
    )

    return container


# ============================================================================
# Decoradores
# ============================================================================

def injectable(interface: Type[T]):
    """
    Decorador para marcar classe como injetável.

    Registra automaticamente a classe no container global
    como transient.

    Args:
        interface: Tipo/classe a registrar

    Example:
        >>> @injectable(MyService)
        >>> class MyService:
        ...     def __init__(self, db: Database):
        ...         self.db = db
    """
    def decorator(cls: Type[T]) -> Type[T]:
        container = get_container()
        container.register_transient(interface, cls)
        return cls
    return decorator


def singleton(interface: Type[T]):
    """
    Decorador para marcar classe como singleton injetável.

    Registra automaticamente a classe no container global
    como singleton.

    Args:
        interface: Tipo/classe a registrar

    Example:
        >>> @singleton(Database)
        >>> class Database:
        ...     pass
    """
    def decorator(cls: Type[T]) -> Type[T]:
        container = get_container()
        container.register_singleton(interface, cls)
        return cls
    return decorator


# ============================================================================
# Service Locator (alternativa ao container)
# ============================================================================

class ServiceLocator:
    """
    Service Locator para acesso a serviços.

    Fornece acesso estático ao container global, simplificando
    uso em código legado.

    Example:
        >>> db = ServiceLocator.get(Database)
        >>> config = ServiceLocator.get(AppConfig)
    """

    @staticmethod
    def get(interface: Type[T]) -> T:
        """
        Obtém serviço do container global.

        Args:
            interface: Tipo/classe do serviço

        Returns:
            T: Instância do serviço
        """
        container = get_container()
        return container.get(interface)

    @staticmethod
    def try_get(interface: Type[T]) -> Optional[T]:
        """
        Tenta obter serviço do container global.

        Args:
            interface: Tipo/classe do serviço

        Returns:
            Optional[T]: Instância do serviço ou None
        """
        container = get_container()
        return container.try_get(interface)

    @staticmethod
    def is_registered(interface: Type) -> bool:
        """
        Verifica se serviço está registrado no container global.

        Args:
            interface: Tipo/classe do serviço

        Returns:
            bool: True se registrado
        """
        container = get_container()
        return container.is_registered(interface)
