# Unit tests for validators module
"""
Testes unitários para o módulo de validação.
"""

import pytest
from src.core.validators import (
    validate_ip_address,
    validate_port,
    validate_url,
    validate_phone_number,
    validate_speed_limit,
    validate_speed_threshold,
    validate_username,
    validate_password,
    calculate_password_strength,
    validate_not_empty,
    validate_range,
    validate_camera_config,
    validate_user_config,
)


class TestNetworkValidators:
    """Testes para validadores de rede."""

    def test_validate_ip_address_valid(self):
        """Testa validação de IPs válidos."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "255.255.255.255",
            "0.0.0.0",
        ]

        for ip in valid_ips:
            is_valid, error = validate_ip_address(ip)
            assert is_valid, f"IP {ip} deveria ser válido: {error}"
            assert error == ""

    def test_validate_ip_address_invalid(self):
        """Testa validação de IPs inválidos."""
        invalid_ips = [
            "256.256.256.256",
            "192.168.1",
            "192.168.1.1.1",
            "not_an_ip",
            "",
            None,
        ]

        for ip in invalid_ips:
            is_valid, error = validate_ip_address(ip)
            assert not is_valid, f"IP {ip} deveria ser inválido"
            assert error != ""

    def test_validate_port_valid(self):
        """Testa validação de portas válidas."""
        valid_ports = [1, 80, 443, 554, 8080, 65535, "80", "443"]

        for port in valid_ports:
            is_valid, error = validate_port(port)
            assert is_valid, f"Porta {port} deveria ser válida: {error}"
            assert error == ""

    def test_validate_port_invalid(self):
        """Testa validação de portas inválidas."""
        invalid_ports = [0, -1, 65536, 99999, "abc", None, ""]

        for port in invalid_ports:
            is_valid, error = validate_port(port)
            assert not is_valid, f"Porta {port} deveria ser inválida"
            assert error != ""

    def test_validate_url_valid(self):
        """Testa validação de URLs válidas."""
        valid_urls = [
            "http://192.168.1.1:80",
            "https://example.com",
            "http://localhost:8080",
            "rtsp://192.168.1.64:554/stream",
        ]

        for url in valid_urls:
            is_valid, error = validate_url(url)
            assert is_valid, f"URL {url} deveria ser válida: {error}"

    def test_validate_url_empty_allowed(self):
        """Testa que URL vazia é permitida quando configurado."""
        is_valid, error = validate_url("", allow_empty=True)
        assert is_valid, "URL vazia deveria ser permitida"

        is_valid, error = validate_url("", allow_empty=False)
        assert not is_valid, "URL vazia não deveria ser permitida quando allow_empty=False"


class TestPhoneValidators:
    """Testes para validadores de telefone."""

    def test_validate_phone_valid(self):
        """Testa validação de telefones válidos (Brasil)."""
        valid_phones = [
            "11999999999",  # 11 dígitos (celular com DDD)
            "11 99999-9999",  # Formatado
            "(11) 99999-9999",  # Com parênteses
            "21988888888",  # 10 dígitos
            "+55 11 99999-9999",  # Com código do país
        ]

        for phone in valid_phones:
            is_valid, error = validate_phone_number(phone)
            assert is_valid, f"Telefone {phone} deveria ser válido: {error}"

    def test_validate_phone_invalid(self):
        """Testa validação de telefones inválidos."""
        invalid_phones = [
            "123",  # Muito curto
            "12345678901234567890",  # Muito longo
            "abc",  # Não numérico
            "",
            None,
        ]

        for phone in invalid_phones:
            is_valid, error = validate_phone_number(phone)
            assert not is_valid, f"Telefone {phone} deveria ser inválido"


class TestSpeedValidators:
    """Testes para validadores de velocidade."""

    def test_validate_speed_limit_valid(self):
        """Testa validação de limites de velocidade válidos."""
        valid_speeds = [10, 60, 100, 200, "80"]

        for speed in valid_speeds:
            is_valid, error = validate_speed_limit(speed)
            assert is_valid, f"Velocidade {speed} deveria ser válida: {error}"

    def test_validate_speed_limit_invalid(self):
        """Testa validação de limites de velocidade inválidos."""
        invalid_speeds = [5, 9, 201, 300, "abc", None]

        for speed in invalid_speeds:
            is_valid, error = validate_speed_limit(speed)
            assert not is_valid, f"Velocidade {speed} deveria ser inválida"

    def test_validate_speed_threshold_valid(self):
        """Testa validação de threshold válido."""
        valid_thresholds = [0.0, 0.5, 0.99, 1.0, "0.75"]

        for threshold in valid_thresholds:
            is_valid, error = validate_speed_threshold(threshold)
            assert is_valid, f"Threshold {threshold} deveria ser válido: {error}"

    def test_validate_speed_threshold_invalid(self):
        """Testa validação de threshold inválido."""
        invalid_thresholds = [-0.1, 1.1, 2.0, "abc", None]

        for threshold in invalid_thresholds:
            is_valid, error = validate_speed_threshold(threshold)
            assert not is_valid, f"Threshold {threshold} deveria ser inválido"


class TestUserValidators:
    """Testes para validadores de usuário."""

    def test_validate_username_valid(self):
        """Testa validação de nomes de usuário válidos."""
        valid_usernames = ["admin", "user123", "test_user", "User-1"]

        for username in valid_usernames:
            is_valid, error = validate_username(username)
            assert is_valid, f"Username {username} deveria ser válido: {error}"

    def test_validate_username_invalid(self):
        """Testa validação de nomes de usuário inválidos."""
        invalid_usernames = ["ab", "123", "ab" * 20, "", None]

        for username in invalid_usernames:
            is_valid, error = validate_username(username)
            assert not is_valid, f"Username {username} deveria ser inválido"

    def test_validate_password_valid(self):
        """Testa validação de senhas válidas."""
        valid_passwords = [
            "Senha123",
            "Password1",
            "MySecurePass456",
        ]

        for password in valid_passwords:
            is_valid, error = validate_password(password)
            assert is_valid, f"Senha deveria ser válida: {error}"

    def test_validate_password_invalid(self):
        """Testa validação de senhas inválidas."""
        invalid_passwords = [
            "short",  # Muito curta
            "nouppercase123",  # Sem maiúscula
            "NOLOWERCASE123",  # Sem minúscula
            "NoNumbers",  # Sem números
            "",
            None,
        ]

        for password in invalid_passwords:
            is_valid, error = validate_password(password)
            assert not is_valid, f"Senha deveria ser inválida: {error}"

    def test_calculate_password_strength(self):
        """Testa cálculo de força de senha."""
        # Senha muito fraca
        strength = calculate_password_strength("abc")
        assert strength < 30

        # Senha fraca
        strength = calculate_password_strength("abcdef12")
        assert 30 <= strength < 60

        # Senha média
        strength = calculate_password_strength("Abcdef12")
        assert 60 <= strength < 80

        # Senha forte
        strength = calculate_password_strength("Abcdef123!")
        assert strength >= 80


class TestGenericValidators:
    """Testes para validadores genéricos."""

    def test_validate_not_empty_valid(self):
        """Testa validação de valores não vazios."""
        valid_values = ["text", 123, ["a", "b"], {"key": "value"}, 0, False]

        for value in valid_values:
            is_valid, error = validate_not_empty(value)
            assert is_valid, f"Valor {value} deveria ser válido: {error}"

    def test_validate_not_empty_invalid(self):
        """Testa validação de valores vazios."""
        invalid_values = ["", "   ", None, [], {}]

        for value in invalid_values:
            is_valid, error = validate_not_empty(value)
            assert not is_valid, f"Valor {value} deveria ser inválido"

    def test_validate_range_valid(self):
        """Testa validação de faixa válida."""
        is_valid, error = validate_range(50, min_value=0, max_value=100)
        assert is_valid

    def test_validate_range_invalid(self):
        """Testa validação de faixa inválida."""
        is_valid, error = validate_range(150, min_value=0, max_value=100)
        assert not is_valid

        is_valid, error = validate_range(-10, min_value=0, max_value=100)
        assert not is_valid


class TestCompositeValidators:
    """Testes para validadores compostos."""

    def test_validate_camera_config_valid(self):
        """Testa validação de configuração de câmera válida."""
        config = {
            "name": "Camera 1",
            "camera_ip": "192.168.1.100",
            "camera_port": 80,
            "camera_user": "admin",
            "channel": 101,
            "timeout": 15,
            "speed_limit_enabled": True,
            "speed_limit_value": 60,
            "detection_confidence_threshold": 0.5,
        }

        is_valid, errors = validate_camera_config(config)
        assert is_valid, f"Config deveria ser válida: {errors}"
        assert len(errors) == 0

    def test_validate_camera_config_invalid(self):
        """Testa validação de configuração de câmera inválida."""
        config = {
            "name": "",  # Inválido: vazio
            "camera_ip": "invalid_ip",  # Inválido
            "camera_port": 99999,  # Inválido
            "camera_user": "",  # Inválido
            "channel": 2000,  # Inválido
            "timeout": 500,  # Inválido
            "speed_limit_enabled": True,
            "speed_limit_value": 300,  # Inválido
            "detection_confidence_threshold": 1.5,  # Inválido
        }

        is_valid, errors = validate_camera_config(config)
        assert not is_valid, "Config deveria ser inválida"
        assert len(errors) > 0

    def test_validate_user_config_valid(self):
        """Testa validação de configuração de usuário válida."""
        config = {
            "username": "testuser",
            "password": "Password123",
            "role": "Operador",
        }

        is_valid, errors = validate_user_config(config)
        assert is_valid, f"Config deveria ser válida: {errors}"
        assert len(errors) == 0

    def test_validate_user_config_invalid(self):
        """Testa validação de configuração de usuário inválida."""
        config = {
            "username": "ab",  # Inválido: muito curto
            "password": "weak",  # Inválido
            "role": "InvalidRole",  # Inválido
        }

        is_valid, errors = validate_user_config(config)
        assert not is_valid, "Config deveria ser inválida"
        assert len(errors) > 0
