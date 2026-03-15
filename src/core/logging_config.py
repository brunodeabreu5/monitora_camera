# Structured Logging Configuration (FASE 2 - Code Quality)
"""
Configuração centralizada de logging estruturado para o Hikvision Radar Pro.

Substitui o uso de print() por logging com níveis apropriados, rotação
de arquivos por tamanho e data, e formato estruturado.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional

from .config import app_dir


# Formatters
class StructuredFormatter(logging.Formatter):
    """
    Formatter para logs estruturados com timestamp, nível, módulo e mensagem.

    Formato: [TIMESTAMP] [LEVEL] [MODULE] MESSAGE
    """

    # Cores ANSI para terminal (Windows 10+ suporta, Linux/Mac nativo)
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, use_colors: bool = True):
        """
        Inicializa formatter estruturado.

        Args:
            use_colors: Se True, usa cores no terminal (padrão: True)
        """
        super().__init__()
        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """Verifica se o terminal suporta cores."""
        # Windows 10+ com VT100 support
        if sys.platform == 'win32':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        # Linux/Mac geralmente suportam
        return True

    def format(self, record: logging.LogRecord) -> str:
        """
        Formata registro de log.

        Args:
            record: Registro de log a ser formatado

        Returns:
            str: Registro formatado
        """
        # Timestamp no formato brasileiro
        timestamp = datetime.fromtimestamp(record.created).strftime('%d/%m/%Y %H:%M:%S')

        # Nível com ou sem cor
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, '')
            level_colored = f"{color}{level}{self.RESET}"
        else:
            level_colored = level

        # Módulo e função
        module = record.name
        func = record.funcName

        # Construir mensagem
        message = record.getMessage()

        # Formato: [TIMESTAMP] [LEVEL] [MODULE:FUNCTION] MESSAGE
        formatted = f"[{timestamp}] [{level_colored}] [{module}:{func}] {message}"

        # Adicionar exception info se houver
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)

        return formatted


class SensitiveDataFilter(logging.Filter):
    """
    Filtro para remover dados sensíveis dos logs.

    Remove senhas, tokens e outras informações sensíveis que possam
    aparecer nos logs (URLs com credenciais, por exemplo).
    """

    SENSITIVE_PATTERNS = [
        (r':([^@\s]+)@', ':***@'),  # URLs com senha (http://user:pass@host)
        (r'password["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', 'password="***"'),  # password=valor
        (r'token["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', 'token="***"'),  # token=valor
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', 'api_key="***"'),  # api_key=valor
    ]

    def __init__(self):
        """Inicializa filtro de dados sensíveis."""
        super().__init__()
        import re
        self._patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in self.SENSITIVE_PATTERNS]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filtra registro removendo dados sensíveis.

        Args:
            record: Registro de log a ser filtrado

        Returns:
            bool: True (sempre permite o log após filtragem)
        """
        # Redact message
        message = record.getMessage()
        for pattern, replacement in self._patterns:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = ()  # Clear args to prevent re-formatting

        # Redact exception info if present
        if record.exc_text:
            for pattern, replacement in self._patterns:
                record.exc_text = pattern.sub(replacement, record.exc_text)

        return True


# ============================================================================
# Configuração
# ============================================================================

def setup_logging(
    log_level: str = 'INFO',
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_dir: Optional[Path] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    use_colors: bool = True
) -> logging.Logger:
    """
    Configura sistema de logging estruturado para a aplicação.

    Args:
        log_level: Nível de log ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_to_file: Se True, salva logs em arquivo
        log_to_console: Se True, exibe logs no console
        log_dir: Diretório para salvar logs (default: app_dir)
        max_file_size: Tamanho máximo do arquivo de log em bytes
        backup_count: Número de backups a manter
        use_colors: Se True, usa cores no console

    Returns:
        logging.Logger: Logger configurado para a aplicação

    Example:
        >>> logger = setup_logging('DEBUG')
        >>> logger.info("Aplicação iniciada")
    """
    # Obter logger raiz
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remover handlers existentes para evitar duplicação
    logger.handlers.clear()

    # Formatter estruturado
    formatter = StructuredFormatter(use_colors=use_colors)

    # Filtro de dados sensíveis
    sensitive_filter = SensitiveDataFilter()

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        logger.addHandler(console_handler)

    # File handler com rotação por tamanho
    if log_to_file:
        if log_dir is None:
            log_dir = app_dir()

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "hikvision_pro_v42.log"

        # RotatingFileHandler: rota quando atinge max_file_size
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(StructuredFormatter(use_colors=False))
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)

    # Adicionar file handler separado para erros críticos
    if log_to_file:
        error_log_file = log_dir / "hikvision_pro_v42_errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(use_colors=False))
        error_handler.addFilter(sensitive_filter)
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtém logger para um módulo específico.

    Args:
        name: Nome do módulo (geralmente __name__)

    Returns:
        logging.Logger: Logger configurado

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Mensagem do módulo")
    """
    return logging.getLogger(name)


# ============================================================================
# Funções de conveniência para compatibilidade
# ============================================================================

def log_runtime_error(context: str, exc: Exception):
    """
    Loga erro de runtime em contexto específico.

    Função de compatibilidade com código legado que usa log_runtime_error().

    Args:
        context: Contexto onde o erro ocorreu
        exc: Exceção capturada
    """
    logger = get_logger('runtime')
    logger.error(f"{context}: {exc}", exc_info=exc)


def log_debug(message: str, module: str = 'app'):
    """Loga mensagem de DEBUG."""
    get_logger(module).debug(message)


def log_info(message: str, module: str = 'app'):
    """Loga mensagem de INFO."""
    get_logger(module).info(message)


def log_warning(message: str, module: str = 'app'):
    """Loga mensagem de WARNING."""
    get_logger(module).warning(message)


def log_error(message: str, module: str = 'app', exc_info: bool = False):
    """
    Loga mensagem de ERROR.

    Args:
        message: Mensagem de erro
        module: Nome do módulo
        exc_info: Se True, inclui informações da exceção atual
    """
    get_logger(module).error(message, exc_info=exc_info)


def log_critical(message: str, module: str = 'app', exc_info: bool = False):
    """
    Loga mensagem de CRITICAL.

    Args:
        message: Mensagem crítica
        module: Nome do módulo
        exc_info: Se True, inclui informações da exceção atual
    """
    get_logger(module).critical(message, exc_info=exc_info)


# ============================================================================
# Context Managers para logging
# ============================================================================

class LogContext:
    """
    Context manager para logging de operações com início e fim.

    Example:
        >>> with LogContext('database', 'Conectando ao banco'):
        >>>     # operação de conexão
        >>>     pass
        # Loga: [TIMESTAMP] [INFO] [database] Iniciando: Conectando ao banco
        # Loga: [TIMESTAMP] [INFO] [database] Concluído: Conectando ao banco
    """

    def __init__(self, module: str, operation: str, level: str = 'INFO'):
        """
        Inicializa contexto de log.

        Args:
            module: Nome do módulo
            operation: Descrição da operação
            level: Nível de log (INFO, DEBUG, etc.)
        """
        self.module = module
        self.operation = operation
        self.level = level
        self.logger = get_logger(module)
        self.start_time = None

    def __enter__(self):
        """Inicia contexto e loga início da operação."""
        self.start_time = datetime.now()
        getattr(self.logger, self.level.lower())(f"Iniciando: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finaliza contexto e loga conclusão da operação."""
        duration = datetime.now() - self.start_time
        duration_str = f" ({duration.total_seconds():.2f}s)" if duration.total_seconds() > 0.1 else ""

        if exc_type is None:
            getattr(self.logger, self.level.lower())(f"Concluído: {self.operation}{duration_str}")
        else:
            self.logger.error(f"Falhou: {self.operation}{duration_str}", exc_info=True)
        return False  # Não suprimir exceções


class LogErrors:
    """
    Context manager para capturar e logar exceções automaticamente.

    Example:
        >>> with LogErrors('database', 'Salvando dados'):
        >>>     save_data()
        # Se save_data() levantar exceção, será logada automaticamente
    """

    def __init__(self, module: str, operation: str, reraise: bool = True):
        """
        Inicializa captura de erros.

        Args:
            module: Nome do módulo
            operation: Descrição da operação
            reraise: Se True, re-levanta a exceção após logar
        """
        self.module = module
        self.operation = operation
        self.reraise = reraise
        self.logger = get_logger(module)

    def __enter__(self):
        """Inicia contexto."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finaliza contexto capturando exceções."""
        if exc_type is not None:
            self.logger.error(
                f"Erro em '{self.operation}': {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )
            return not self.reraise  # Suprimir exceção se reraise=False
        return False


# Inicialização automática quando o módulo é importado
if not logging.getLogger().handlers:
    setup_logging()
