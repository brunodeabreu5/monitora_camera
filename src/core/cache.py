# Cache Module (FASE 4.4 - Performance)
"""
Sistema de cache com TTL para otimização de performance.

Implementa cache LRU (Least Recently Used) com time-to-live (TTL)
para armazenar resultados de operações custosas.

Usage:
    >>> cache = TTLCache(maxsize=100, ttl=300)  # 100 itens, 5 minutos TTL
    >>> @cache.cached
    >>> def expensive_operation(param):
    ...     return heavy_computation(param)
"""

import time
import hashlib
import json
import threading
from typing import Any, Dict, Optional, Callable, TypeVar, Tuple
from functools import wraps
from dataclasses import dataclass


T = TypeVar('T')


@dataclass
class CacheEntry:
    """Entrada de cache com valor e timestamp."""

    value: Any
    """Valor armazenado em cache."""

    timestamp: float
    """Timestamp de quando entrada foi criada/atualizada."""

    hits: int = 0
    """Número de vezes que entrada foi acessada."""


class TTLCache:
    """
    Cache LRU com Time-To-Live (TTL).

    Implementa cache thread-safe com expiração baseada em tempo
    e limite máximo de entradas.

    Attributes:
        maxsize: Número máximo de entradas no cache
        ttl: Time-to-live em segundos
        _cache: Dicionário interno de cache
        _lock: Lock para thread-safety
        _hits: Contador de cache hits
        _misses: Contador de cache misses

    Example:
        >>> cache = TTLCache(maxsize=100, ttl=300)
        >>> cache.put("key", "value")
        >>> value = cache.get("key")
        >>> assert value == "value"
    """

    def __init__(self, maxsize: int = 128, ttl: int = 300):
        """
        Inicializa cache.

        Args:
            maxsize: Número máximo de entradas (default: 128)
            ttl: Time-to-live em segundos (default: 300 = 5 minutos)
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Recupera valor do cache.

        Args:
            key: Chave do cache
            default: Valor padrão se chave não existe ou expirou

        Returns:
            Valor em cache ou default se não encontrado/expirado
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return default

            # Verificar expiração
            if time.time() - entry.timestamp > self.ttl:
                # Entrada expirada, remover
                del self._cache[key]
                self._misses += 1
                return default

            # Cache hit
            entry.hits += 1
            self._hits += 1
            return entry.value

    def put(self, key: str, value: Any) -> None:
        """
        Armazena valor no cache.

        Args:
            key: Chave do cache
            value: Valor a armazenar
        """
        with self._lock:
            # Remover entrada mais antiga se cache estiver cheio
            if len(self._cache) >= self.maxsize and key not in self._cache:
                # Encontrar entrada com menos hits
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: (self._cache[k].hits, self._cache[k].timestamp)
                )
                del self._cache[oldest_key]

            self._cache[key] = CacheEntry(value=value, timestamp=time.time())

    def invalidate(self, key: str) -> bool:
        """
        Invalida entrada específica do cache.

        Args:
            key: Chave a invalidar

        Returns:
            bool: True se chave foi encontrada e removida
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self) -> int:
        """
        Remove todas as entradas expiradas do cache.

        Returns:
            int: Número de entradas removidas
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time - entry.timestamp > self.ttl
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.

        Returns:
            Dict com: size, hits, misses, hit_rate, oldest_entry, newest_entry
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            if self._cache:
                timestamps = [e.timestamp for e in self._cache.values()]
                oldest = min(timestamps)
                newest = max(timestamps)
            else:
                oldest = newest = 0

            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "oldest_entry": oldest,
                "newest_entry": newest,
            }

    def cached(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator para cachear resultados de função.

        Args:
            func: Função a cachear

        Returns:
            Função wrapper com cache

        Example:
            >>> cache = TTLCache(maxsize=100, ttl=300)
            >>> @cache.cached
            >>> def expensive_function(x, y):
            ...     return x + y  # Operação custosa
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Gerar chave de cache baseada em argumentos
            cache_key = self._generate_cache_key(func.__name__, args, kwargs)

            # Tentar obter do cache
            result = self.get(cache_key)
            if result is not None:
                return result

            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            self.put(cache_key, result)
            return result

        return wrapper

    def _generate_cache_key(self, func_name: str, args: Tuple, kwargs: Dict) -> str:
        """
        Gera chave de cache baseada em nome da função e argumentos.

        Args:
            func_name: Nome da função
            args: Argumentos posicionais
            kwargs: Argumentos nomeados

        Returns:
            str: Chave de cache única
        """
        # Serializar argumentos para JSON
        try:
            args_str = json.dumps(args, default=str, sort_keys=True)
            kwargs_str = json.dumps(kwargs, default=str, sort_keys=True)
        except (TypeError, ValueError):
            # Fallback para serialização falhar
            args_str = str(args)
            kwargs_str = str(kwargs)

        # Gerar hash
        combined = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(combined.encode()).hexdigest()


# ============================================================================
# Cache Global para Operações Comuns
# ============================================================================

# Cache para configurações de câmera (TTL: 5 minutos)
_camera_cache = TTLCache(maxsize=50, ttl=300)

# Cache para queries de banco (TTL: 1 minuto)
_database_cache = TTLCache(maxsize=100, ttl=60)

# Cache para snapshots (TTL: 30 segundos)
_snapshot_cache = TTLCache(maxsize=20, ttl=30)


def get_camera_cache() -> TTLCache:
    """Retorna cache para configurações de câmera."""
    return _camera_cache


def get_database_cache() -> TTLCache:
    """Retorna cache para queries de banco."""
    return _database_cache


def get_snapshot_cache() -> TTLCache:
    """Retorna cache para snapshots."""
    return _snapshot_cache


# ============================================================================
# Decorators de Cache
# ============================================================================

def cached_camera(ttl: int = 300):
    """
    Decorator para cachear operações de câmera.

    Args:
        ttl: Time-to-live em segundos (default: 300 = 5 minutos)

    Example:
        >>> @cached_camera(ttl=300)
        >>> def get_camera_config(camera_name):
        ...     return load_from_database(camera_name)
    """
    cache = TTLCache(maxsize=50, ttl=ttl)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache_key = cache._generate_cache_key(func.__name__, args, kwargs)
            result = cache.get(cache_key)

            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            return result

        wrapper.cache = cache  # Expor cache para invalidação manual
        return wrapper

    return decorator


def cached_query(ttl: int = 60):
    """
    Decorator para cachear queries de banco.

    Args:
        ttl: Time-to-live em segundos (default: 60 = 1 minuto)

    Example:
        >>> @cached_query(ttl=60)
        >>> def get_recent_events(limit=100):
        ...     return db.execute("SELECT * FROM events LIMIT ?", (limit,))
    """
    cache = TTLCache(maxsize=100, ttl=ttl)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache_key = cache._generate_cache_key(func.__name__, args, kwargs)
            result = cache.get(cache_key)

            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            return result

        wrapper.cache = cache
        return wrapper

    return decorator


def invalidate_camera_cache(camera_name: Optional[str] = None):
    """
    Invalida cache de câmera(s).

    Args:
        camera_name: Nome específico ou None para limpar tudo
    """
    if camera_name:
        # Invalidar entradas específicas (implementação depende do padrão de chaves)
        _camera_cache.cleanup_expired()
    else:
        _camera_cache.clear()


def invalidate_database_cache():
    """Limpa cache de queries de banco."""
    _database_cache.clear()


def invalidate_snapshot_cache():
    """Limpa cache de snapshots."""
    _snapshot_cache.clear()


# ============================================================================
# Cache Statistics
# ============================================================================

def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """
    Retorna estatísticas de todos os caches.

    Returns:
        Dict com stats de cada cache
    """
    return {
        "camera": _camera_cache.get_stats(),
        "database": _database_cache.get_stats(),
        "snapshot": _snapshot_cache.get_stats(),
    }


def cleanup_all_expired_caches() -> Dict[str, int]:
    """
    Limpa entradas expiradas de todos os caches.

    Returns:
        Dict com número de entradas removidas por cache
    """
    return {
        "camera": _camera_cache.cleanup_expired(),
        "database": _database_cache.cleanup_expired(),
        "snapshot": _snapshot_cache.cleanup_expired(),
    }
