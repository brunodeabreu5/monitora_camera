# Crypto module for password encryption/decryption (FASE 1 - Security)
"""
Módulo de criptografia para armazenamento seguro de senhas de câmeras.

Utiliza criptografia AES-256-GCM com chave derivada de credenciais do usuário
ou hardware ID para criptografar senhas de câmeras antes de armazená-las no
arquivo de configuração JSON.
"""

import base64
import hashlib
import os
import platform
import subprocess
from typing import Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.backends import default_backend
    import cryptography
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    AESGCM = None


class CryptoError(Exception):
    """Exceção levantada para erros de criptografia/descriptografia."""
    pass


def _get_hardware_id() -> str:
    """
    Gera um ID único baseado no hardware da máquina.

    Tenta múltiplas abordagens para obter um ID único:
    1. UUID da máquina (Windows)
    2. Machine ID (Linux)
    3. Combinação de hostname e CPU info

    Returns:
        str: String hexadecimal representando o hardware ID
    """
    try:
        system = platform.system()

        if system == "Windows":
            # Tentar obter UUID da máquina no Windows
            try:
                result = subprocess.check_output(
                    ['wmic', 'csproduct', 'get', 'uuid'],
                    text=True,
                    timeout=5
                )
                uuid_line = [line.strip() for line in result.split('\n') if line.strip()][0]
                if uuid_line and uuid_line != 'UUID':
                    return hashlib.sha256(uuid_line.encode()).hexdigest()[:32]
            except (subprocess.SubprocessError, IndexError, FileNotFoundError):
                pass

        elif system == "Linux":
            # Tentar obter machine-id do Linux
            try:
                for path in ['/etc/machine-id', '/var/lib/dbus/machine-id']:
                    try:
                        with open(path, 'r') as f:
                            machine_id = f.read().strip()
                            if machine_id:
                                return hashlib.sha256(machine_id.encode()).hexdigest()[:32]
                    except (FileNotFoundError, PermissionError):
                        continue
            except Exception:
                pass

        # Fallback: hostname + CPU info
        hostname = platform.node()
        cpu_info = platform.processor() or "unknown_cpu"
        combined = f"{hostname}-{cpu_info}-{platform.machine()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    except Exception:
        # Último fallback: valor constante (não recomendado, mas evita crash)
        return "fallback_hardware_id_1234567890abcdef"


def _derive_encryption_key(hardware_id: Optional[str] = None, salt: Optional[str] = None) -> bytes:
    """
    Deriva a chave de criptografia usando PBKDF2.

    Args:
        hardware_id: ID do hardware (obtido automaticamente se None)
        salt: Salt para derivação (gerado automaticamente se None)

    Returns:
        bytes: Chave de criptografia de 32 bytes (256 bits)

    Raises:
        CryptoError: Se cryptography não estiver instalado
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise CryptoError(
            "Biblioteca 'cryptography' não está instalada. "
            "Instale com: pip install cryptography"
        )

    if hardware_id is None:
        hardware_id = _get_hardware_id()

    if salt is None:
        # Usar hardware_id como salt para consistência
        salt = hardware_id

    # Derivar chave de 32 bytes (256 bits) usando PBKDF2
    # Usamos 100.000 iterações para segurança adequada
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        hardware_id.encode('utf-8'),
        salt.encode('utf-8'),
        100_000,
        dklen=32
    )
    return dk


def encrypt_password(password: str, hardware_id: Optional[str] = None) -> dict:
    """
    Criptografa uma senha usando AES-256-GCM.

    Args:
        password: Senha em texto claro a ser criptografada
        hardware_id: ID do hardware para derivar chave (opcional)

    Returns:
        dict: Dicionário com campos:
            - 'encrypted': Senha criptografada (base64)
            - 'nonce': Nonce usado (base64)
            - 'tag': Tag de autenticação (base64)

    Raises:
        CryptoError: Se cryptography não estiver instalado ou erro na criptografia

    Example:
        >>> result = encrypt_password("my_password")
        >>> encrypted_data = result['encrypted']
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise CryptoError(
            "Biblioteca 'cryptography' não está instalada. "
            "Instale com: pip install cryptography"
        )

    if not password:
        raise CryptoError("Password cannot be empty")

    try:
        key = _derive_encryption_key(hardware_id)
        aesgcm = AESGCM(key)

        # Gerar nonce aleatório de 12 bytes (96 bits) - padrão para GCM
        # NOTA: AESGCM.generate_nonce() foi removido em versões recentes
        # Usar os.urandom() ou secrets.token_bytes() para gerar nonce
        nonce = os.urandom(12)

        # Criptografar: AES-256-GCM adiciona tag de autenticação automaticamente
        # O nonce é passado junto com os dados
        password_bytes = password.encode('utf-8')
        ciphertext_with_tag = aesgcm.encrypt(nonce, password_bytes, None)

        # Retornar como dicionário com valores em base64 para armazenamento JSON
        return {
            'encrypted': base64.b64encode(ciphertext_with_tag).decode('ascii'),
            'nonce': base64.b64encode(nonce).decode('ascii'),
        }

    except Exception as e:
        raise CryptoError(f"Failed to encrypt password: {e}")


def decrypt_password(encrypted_data: dict, hardware_id: Optional[str] = None) -> str:
    """
    Descriptografa uma senha criptografada com encrypt_password().

    Args:
        encrypted_data: Dicionário com 'encrypted' e 'nonce' (base64)
        hardware_id: ID do hardware usado na criptografia (opcional)

    Returns:
        str: Senha em texto claro

    Raises:
        CryptoError: Se cryptography não estiver instalado, dados inválidos,
                     ou falha na descriptografia

    Example:
        >>> encrypted = {'encrypted': '...', 'nonce': '...'}
        >>> password = decrypt_password(encrypted)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise CryptoError(
            "Biblioteca 'cryptography' não está instalada. "
            "Instale com: pip install cryptography"
        )

    if not isinstance(encrypted_data, dict):
        raise CryptoError("Encrypted data must be a dictionary")

    if 'encrypted' not in encrypted_data or 'nonce' not in encrypted_data:
        raise CryptoError("Encrypted data must contain 'encrypted' and 'nonce' fields")

    try:
        key = _derive_encryption_key(hardware_id)
        aesgcm = AESGCM(key)

        # Decodificar base64
        ciphertext_with_tag = base64.b64decode(encrypted_data['encrypted'])
        nonce = base64.b64decode(encrypted_data['nonce'])

        # Descriptografar
        password_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return password_bytes.decode('utf-8')

    except (ValueError, KeyError) as e:
        raise CryptoError(f"Invalid encrypted data format: {e}")
    except Exception as e:
        raise CryptoError(f"Failed to decrypt password. Data may be corrupted or wrong hardware: {e}")


def is_encrypted_password(password_data: any) -> bool:
    """
    Verifica se os dados de senha representam uma senha criptografada.

    Args:
        password_data: Dados de senha (string ou dict)

    Returns:
        bool: True se for senha criptografada (dict com campos corretos),
              False caso contrário (texto claro ou formato inválido)
    """
    if not isinstance(password_data, dict):
        return False

    required_fields = {'encrypted', 'nonce'}
    return all(field in password_data for field in required_fields)


def migrate_plaintext_to_encrypted(plaintext_password: str, hardware_id: Optional[str] = None) -> dict:
    """
    Migra uma senha em texto claro para formato criptografado.

    Função auxiliar para uso em migração de configurações existentes.

    Args:
        plaintext_password: Senha em texto claro
        hardware_id: ID do hardware (opcional)

    Returns:
        dict: Dicionário criptografado pronto para armazenamento

    Raises:
        CryptoError: Se falhar a criptografia
    """
    if not plaintext_password:
        # Senha vazia - retornar dict vazio para representar "sem senha"
        return {}

    return encrypt_password(plaintext_password, hardware_id)


# Função de conveniência para verificar disponibilidade do módulo
def check_crypto_available() -> tuple[bool, str]:
    """
    Verifica se o módulo de criptografia está disponível.

    Returns:
        tuple[bool, str]: (True, "") se disponível,
                          (False, mensagem_erro) se não disponível
    """
    if CRYPTOGRAPHY_AVAILABLE:
        return True, ""
    return False, "Biblioteca 'cryptography' não instalada. Execute: pip install cryptography"
