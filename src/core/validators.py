# Centralized Validators (FASE 3.3 - Architecture)
"""
Módulo de validação centralizado para o Hikvision Radar Pro.

Fornece validadores reutilizáveis para entrada de dados em todo
o sistema, garantindo consistência e facilitando manutenção.

Todos os validadores retornam tupla (bool, str) onde:
- bool: True se válido, False se inválido
- str: Mensagem de erro se inválido, string vazia se válido

Usage:
    >>> is_valid, error = validate_ip_address("192.168.1.1")
    >>> if not is_valid:
    >>>     show_error(error)
"""

import re
import ipaddress
from typing import Tuple, Optional, List, Any
from pathlib import Path


# ============================================================================
# Validadores de Rede
# ============================================================================

def validate_ip_address(ip: str) -> Tuple[bool, str]:
    """
    Valida formato de endereço IPv4.

    Aceita formatos:
    - 192.168.1.1
    - 10.0.0.1
    - 172.16.0.1

    Não aceita:
    - IPv6
    - Hostnames
    - Endereços inválidos (256.256.256.256)

    Args:
        ip: String com endereço IP a validar

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido

    Example:
        >>> is_valid, error = validate_ip_address("192.168.1.1")
        >>> assert is_valid
    """
    if not ip or not isinstance(ip, str):
        return False, "Endereço IP não pode ser vazio"

    ip = ip.strip()

    try:
        ipaddress.IPv4Address(ip)
        return True, ""
    except ipaddress.AddressValueError:
        return False, f"Endereço IP inválido: '{ip}'. Use formato IPv4 (ex: 192.168.1.1)"


def validate_port(port: Any) -> Tuple[bool, str]:
    """
    Valida número de porta TCP/UDP.

    Porta válida: 1-65535
    Portas comuns: 80 (HTTP), 443 (HTTPS), 554 (RTSP)

    Args:
        port: Número da porta (int ou string conversível para int)

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido

    Example:
        >>> is_valid, error = validate_port(80)
        >>> assert is_valid
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        return False, f"Porta deve ser um número inteiro, recebido: '{port}'"

    if port_int < 1:
        return False, "Porta deve ser maior que 0"

    if port_int > 65535:
        return False, "Porta deve ser menor que 65536"

    return True, ""


def validate_url(url: str, allow_empty: bool = True) -> Tuple[bool, str]:
    """
    Valida URL de HTTP/HTTPS/RTSP.

    Args:
        url: String com URL a validar
        allow_empty: Se True, URL vazia é considerada válida

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    if not url:
        return allow_empty, "" if allow_empty else "URL não pode ser vazia"

    url = url.strip()

    # Padrões básicos de URL - corrigido para não usar ://
    http_pattern = re.compile(
        r'^https?://'  # http:// ou https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domínio
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # porta opcional
        r'(?:/?|[/?]\S+)?$', re.IGNORECASE
    )

    rtsp_pattern = re.compile(
        r'^rtsp://'  # rtsp://
        r'[^\s/$.?#].[^\s]*'  # host + path
        r'(?::\d+)?'  # porta opcional
        r'(?:/?|[/?]\S+)?$', re.IGNORECASE
    )

    if http_pattern.match(url) or rtsp_pattern.match(url):
        return True, ""

    return False, f"URL inválida: '{url}'. Use formato completo (ex: http://192.168.1.1:80)"


# ============================================================================
# Validadores de Telefone
# ============================================================================

def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Valida formato de telefone brasileiro.

    Aceita formatos:
    - 1199999999 (apenas dígitos)
    - (11) 99999-9999
    - 11 99999-9999
    - +55 11 99999-9999

    Args:
        phone: String com número de telefone

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido

    Example:
        >>> is_valid, error = validate_phone_number("11999999999")
        >>> assert is_valid
    """
    if not phone or not isinstance(phone, str):
        return False, "Número de telefone não pode ser vazio"

    # Extrair apenas dígitos
    digits = re.sub(r'\D', '', phone)

    # Telefone brasileiro: 10 ou 11 dígitos (com DDD)
    # Com código do país (+55): 12 ou 13 dígitos
    if len(digits) in (10, 11, 12, 13):
        # Verificar se começa com 55 (código do Brasil)
        if len(digits) >= 12 and digits[:2] == '55':
            digits = digits[2:]

        # Deve ter 10 ou 11 dígitos agora
        if len(digits) in (10, 11):
            return True, ""

    return False, f"Telefone inválido: '{phone}'. Use formato brasileiro com DDD (ex: 11 99999-9999)"


# ============================================================================
# Validadores de Velocidade
# ============================================================================

def validate_speed_limit(speed: Any, min_speed: int = 10, max_speed: int = 200) -> Tuple[bool, str]:
    """
    Valida limite de velocidade em km/h.

    Args:
        speed: Valor da velocidade (int ou string conversível)
        min_speed: Velocidade mínima permitida (default: 10 km/h)
        max_speed: Velocidade máxima permitida (default: 200 km/h)

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido

    Example:
        >>> is_valid, error = validate_speed_limit(60)
        >>> assert is_valid
    """
    try:
        speed_int = int(speed)
    except (ValueError, TypeError):
        return False, f"Velocidade deve ser um número inteiro, recebido: '{speed}'"

    if speed_int < min_speed:
        return False, f"Velocidade deve ser maior que {min_speed} km/h"

    if speed_int > max_speed:
        return False, f"Velocidade deve ser menor que {max_speed} km/h"

    return True, ""


def validate_speed_threshold(threshold: Any) -> Tuple[bool, str]:
    """
    Valida threshold de detecção (0.0 a 1.0).

    Args:
        threshold: Valor de threshold (float ou string conversível)

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    try:
        threshold_float = float(threshold)
    except (ValueError, TypeError):
        return False, f"Threshold deve ser um número decimal, recebido: '{threshold}'"

    if threshold_float < 0.0:
        return False, "Threshold deve ser maior ou igual a 0.0"

    if threshold_float > 1.0:
        return False, "Threshold deve ser menor ou igual a 1.0"

    return True, ""


# ============================================================================
# Validadores de Usuário
# ============================================================================

def validate_username(username: str, min_length: int = 3, max_length: int = 32) -> Tuple[bool, str]:
    """
    Valida nome de usuário.

    Requisitos:
    - 3 a 32 caracteres
    - Apenas letras, números, underscore e hífen
    - Deve começar com letra

    Args:
        username: Nome de usuário a validar
        min_length: Comprimento mínimo (default: 3)
        max_length: Comprimento máximo (default: 32)

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    if not username or not isinstance(username, str):
        return False, "Nome de usuário não pode ser vazio"

    username = username.strip()

    if len(username) < min_length:
        return False, f"Nome de usuário deve ter pelo menos {min_length} caracteres"

    if len(username) > max_length:
        return False, f"Nome de usuário deve ter no máximo {max_length} caracteres"

    # Apenas letras, números, underscore e hífen
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', username):
        return False, "Nome de usuário deve começar com letra e conter apenas letras, números, underscore e hífen"

    return True, ""


def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False
) -> Tuple[bool, str]:
    """
    Valida força de senha.

    Requisitos configuráveis:
    - Comprimento mínimo
    - Letras maiúsculas
    - Letras minúsculas
    - Números
    - Caracteres especiais

    Args:
        password: Senha a validar
        min_length: Comprimento mínimo (default: 8)
        require_uppercase: Exigir maiúsculas (default: True)
        require_lowercase: Exigir minúsculas (default: True)
        require_digit: Exigir números (default: True)
        require_special: Exigir caracteres especiais (default: False)

    Returns:
        Tuple[bool, str]: (True, "") se válida, (False, mensagem_erro) se inválida

    Example:
        >>> is_valid, error = validate_password("Senha123")
        >>> assert is_valid
    """
    if not password or not isinstance(password, str):
        return False, "Senha não pode ser vazia"

    if len(password) < min_length:
        return False, f"Senha deve ter pelo menos {min_length} caracteres"

    if require_uppercase and not re.search(r'[A-Z]', password):
        return False, "Senha deve conter pelo menos uma letra maiúscula (A-Z)"

    if require_lowercase and not re.search(r'[a-z]', password):
        return False, "Senha deve conter pelo menos uma letra minúscula (a-z)"

    if require_digit and not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número (0-9)"

    if require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>?]', password):
        return False, "Senha deve conter pelo menos um caractere especial (!@#$%...)"

    return True, ""


def calculate_password_strength(password: str) -> int:
    """
    Calcula força da senha (0-100).

    Args:
        password: Senha a avaliar

    Returns:
        int: Pontuação de 0 (muito fraca) a 100 (muito forte)
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


# ============================================================================
# Validadores de Arquivo/Caminho
# ============================================================================

def validate_file_path(path: str, must_exist: bool = False, extension: Optional[str] = None) -> Tuple[bool, str]:
    """
    Valida caminho de arquivo.

    Args:
        path: Caminho do arquivo
        must_exist: Se True, arquivo deve existir
        extension: Extensão obrigatória (ex: ".jpg")

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    if not path or not isinstance(path, str):
        return False, "Caminho não pode ser vazio"

    path = path.strip()

    try:
        file_path = Path(path)

        if must_exist and not file_path.exists():
            return False, f"Arquivo não encontrado: '{path}'"

        if must_exist and not file_path.is_file():
            return False, f"Caminho não é um arquivo: '{path}'"

        if extension:
            if file_path.suffix.lower() != extension.lower():
                return False, f"Arquivo deve ter extensão '{extension}', recebido: '{file_path.suffix}'"

        return True, ""

    except Exception as e:
        return False, f"Caminho inválido: '{path}'. Erro: {e}"


def validate_directory_path(path: str, must_exist: bool = False, create_if_missing: bool = False) -> Tuple[bool, str]:
    """
    Valida caminho de diretório.

    Args:
        path: Caminho do diretório
        must_exist: Se True, diretório deve existir
        create_if_missing: Se True, cria diretório se não existir

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    if not path or not isinstance(path, str):
        return False, "Caminho não pode ser vazio"

    path = path.strip()

    try:
        dir_path = Path(path)

        if not dir_path.exists():
            if create_if_missing:
                dir_path.mkdir(parents=True, exist_ok=True)
            elif must_exist:
                return False, f"Diretório não encontrado: '{path}'"

        if dir_path.exists() and not dir_path.is_dir():
            return False, f"Caminho não é um diretório: '{path}'"

        return True, ""

    except Exception as e:
        return False, f"Caminho inválido: '{path}'. Erro: {e}"


# ============================================================================
# Validadores Genéricos
# ============================================================================

def validate_not_empty(value: Any, field_name: str = "Valor") -> Tuple[bool, str]:
    """
    Valida que valor não está vazio.

    Args:
        value: Valor a validar
        field_name: Nome do campo para mensagem de erro

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    if value is None:
        return False, f"{field_name} não pode ser nulo"

    if isinstance(value, str) and not value.strip():
        return False, f"{field_name} não pode ser vazio"

    if isinstance(value, (list, dict)) and len(value) == 0:
        return False, f"{field_name} não pode ser vazio"

    return True, ""


def validate_range(
    value: Any,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "Valor"
) -> Tuple[bool, str]:
    """
    Valida que número está em faixa especificada.

    Args:
        value: Valor a validar
        min_value: Valor mínimo (opcional)
        max_value: Valor máximo (opcional)
        field_name: Nome do campo para mensagem de erro

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return False, f"{field_name} deve ser um número, recebido: '{value}'"

    if min_value is not None and num_value < min_value:
        return False, f"{field_name} deve ser maior ou igual a {min_value}"

    if max_value is not None and num_value > max_value:
        return False, f"{field_name} deve ser menor ou igual a {max_value}"

    return True, ""


def validate_in_list(value: Any, valid_values: List[Any], field_name: str = "Valor") -> Tuple[bool, str]:
    """
    Valida que valor está em lista de valores permitidos.

    Args:
        value: Valor a validar
        valid_values: Lista de valores permitidos
        field_name: Nome do campo para mensagem de erro

    Returns:
        Tuple[bool, str]: (True, "") se válido, (False, mensagem_erro) se inválido
    """
    if value not in valid_values:
        values_str = ", ".join(str(v) for v in valid_values)
        return False, f"{field_name} deve ser um de: [{values_str}], recebido: '{value}'"

    return True, ""


# ============================================================================
# Validadores Compostos
# ============================================================================

def validate_camera_config(config: dict) -> Tuple[bool, List[str]]:
    """
    Valida configuração completa de câmera.

    Args:
        config: Dicionário com configuração da câmera

    Returns:
        Tuple[bool, List[str]]: (True, []) se válida, (False, lista_erros) se inválida
    """
    errors = []

    # Nome
    is_valid, error = validate_not_empty(config.get("name"), "Nome")
    if not is_valid:
        errors.append(error)

    # IP
    is_valid, error = validate_ip_address(config.get("camera_ip", ""))
    if not is_valid:
        errors.append(error)

    # Porta
    is_valid, error = validate_port(config.get("camera_port"))
    if not is_valid:
        errors.append(error)

    # Usuário
    is_valid, error = validate_not_empty(config.get("camera_user"), "Usuário")
    if not is_valid:
        errors.append(error)

    # Canal
    is_valid, error = validate_range(config.get("channel"), min_value=1, max_value=1000, field_name="Canal")
    if not is_valid:
        errors.append(error)

    # Timeout
    is_valid, error = validate_range(config.get("timeout"), min_value=1, max_value=300, field_name="Timeout")
    if not is_valid:
        errors.append(error)

    # Limite de velocidade (se habilitado)
    if config.get("speed_limit_enabled"):
        is_valid, error = validate_speed_limit(config.get("speed_limit_value"))
        if not is_valid:
            errors.append(error)

    # Threshold de detecção
    is_valid, error = validate_speed_threshold(config.get("detection_confidence_threshold"))
    if not is_valid:
        errors.append(error)

    return len(errors) == 0, errors


def validate_user_config(config: dict) -> Tuple[bool, List[str]]:
    """
    Valida configuração completa de usuário.

    Args:
        config: Dicionário com dados do usuário

    Returns:
        Tuple[bool, List[str]]: (True, []) se válido, (False, lista_erros) se inválido
    """
    errors = []

    # Username
    is_valid, error = validate_username(config.get("username", ""))
    if not is_valid:
        errors.append(error)

    # Senha (se fornecida)
    password = config.get("password")
    if password:
        is_valid, error = validate_password(password)
        if not is_valid:
            errors.append(error)

    # Cargo
    role = config.get("role", "")
    if role not in ("Administrador", "Operador"):
        errors.append(f"Cargo deve ser 'Administrador' ou 'Operador', recebido: '{role}'")

    return len(errors) == 0, errors
