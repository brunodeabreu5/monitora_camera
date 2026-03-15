# Unit tests for crypto module
"""
Testes unitários para o módulo de criptografia.
"""

import pytest
from src.core.crypto import (
    encrypt_password,
    decrypt_password,
    is_encrypted_password,
    migrate_plaintext_to_encrypted,
    check_crypto_available,
    CryptoError,
)


class TestPasswordEncryption:
    """Testes para criptografia/descriptografia de senhas."""

    def test_encrypt_decrypt_success(self):
        """Testa criptografia e descriptografia bem-sucedida."""
        password = "MySecurePassword123"

        # Criptografar
        encrypted = encrypt_password(password)
        assert isinstance(encrypted, dict)
        assert "encrypted" in encrypted
        assert "nonce" in encrypted
        assert encrypted["encrypted"] != password  # Não é texto claro

        # Descriptografar
        decrypted = decrypt_password(encrypted)
        assert decrypted == password

    def test_encrypt_with_custom_hardware_id(self):
        """Testa criptografia com hardware ID customizado."""
        password = "TestPassword456"
        hardware_id = "custom_hardware_id"

        encrypted = encrypt_password(password, hardware_id)
        decrypted = decrypt_password(encrypted, hardware_id)

        assert decrypted == password

    def test_encrypt_different_hardware_id_fails(self):
        """Testa que descriptografia falha com hardware ID diferente."""
        password = "TestPassword789"

        encrypted = encrypt_password(password, hardware_id="hardware_1")

        # Tentar descriptografar com hardware ID diferente deve falhar
        with pytest.raises(CryptoError):
            decrypt_password(encrypted, hardware_id="hardware_2")

    def test_encrypt_empty_password(self):
        """Testa criptografia de senha vazia."""
        with pytest.raises(CryptoError):
            encrypt_password("")

    def test_decrypt_invalid_format(self):
        """Testa descriptografia com formato inválido."""
        # Falta campos obrigatórios
        with pytest.raises(CryptoError):
            decrypt_password({"encrypted": "abc"})

        with pytest.raises(CryptoError):
            decrypt_password({"nonce": "abc"})

    def test_decrypt_corrupted_data(self):
        """Testa descriptografia de dados corrompidos."""
        encrypted = {
            "encrypted": "invalid_base64!!!",
            "nonce": "invalid_base64!!!",
        }

        with pytest.raises(CryptoError):
            decrypt_password(encrypted)

    def test_is_encrypted_password_true(self):
        """Testa detecção de senha criptografada."""
        encrypted = encrypt_password("TestPassword")
        assert is_encrypted_password(encrypted)

    def test_is_encrypted_password_false(self):
        """Testa detecção de senha não criptografada."""
        assert not is_encrypted_password("plaintext_password")
        assert not is_encrypted_password("")
        assert not is_encrypted_password(None)
        assert not is_encrypted_password({"incomplete": "dict"})


class TestPasswordMigration:
    """Testes para migração de senhas."""

    def test_migrate_plaintext_to_encrypted(self):
        """Testa migração de texto claro para criptografado."""
        plaintext = "OldPassword123"

        encrypted = migrate_plaintext_to_encrypted(plaintext)
        assert is_encrypted_password(encrypted)

        # Verificar que descriptografa corretamente
        decrypted = decrypt_password(encrypted)
        assert decrypted == plaintext

    def test_migrate_empty_password(self):
        """Testa migração de senha vazia."""
        encrypted = migrate_plaintext_to_encrypted("")
        assert encrypted == {}  # Dict vazio indica senha vazia


class TestCryptoAvailability:
    """Testes para verificação de disponibilidade do crypto."""

    def test_check_crypto_available(self):
        """Testa verificação de disponibilidade do módulo crypto."""
        # A biblioteca cryptography deve estar instalada para os testes
        is_available, message = check_crypto_available()
        assert is_available, f"Cryptography não disponível: {message}"

    def test_encrypt_without_cryptography(self, monkeypatch):
        """Testa erro quando cryptography não está disponível."""
        # Simular ausência da biblioteca
        import src.core.crypto as crypto_module
        monkeypatch.setattr(crypto_module, "CRYPTOGRAPHY_AVAILABLE", False)

        with pytest.raises(CryptoError, match="não está instalada"):
            encrypt_password("test")


class TestEncryptionFormat:
    """Testes para formato de criptografia."""

    def test_encrypted_data_is_dict(self):
        """Testa que dados criptografados são dicionário."""
        encrypted = encrypt_password("TestPassword")
        assert isinstance(encrypted, dict)

    def test_encrypted_data_has_required_fields(self):
        """Testa que dados criptografados têm campos obrigatórios."""
        encrypted = encrypt_password("TestPassword")
        assert "encrypted" in encrypted
        assert "nonce" in encrypted
        assert len(encrypted) == 2

    def test_encrypted_values_are_strings(self):
        """Testa que valores criptografados são strings."""
        encrypted = encrypt_password("TestPassword")
        assert isinstance(encrypted["encrypted"], str)
        assert isinstance(encrypted["nonce"], str)

    def test_different_passwords_different_encrypted(self):
        """Testa que senhas diferentes geram criptografias diferentes."""
        password1 = "Password1"
        password2 = "Password2"

        encrypted1 = encrypt_password(password1)
        encrypted2 = encrypt_password(password2)

        assert encrypted1["encrypted"] != encrypted2["encrypted"]

    def test_same_password_different_nonces(self):
        """Testa que mesma senha gera nonces diferentes (aleatoriedade)."""
        password = "SamePassword"

        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # Nonces devem ser diferentes (aleatórios)
        assert encrypted1["nonce"] != encrypted2["nonce"]

        # Mas ambas descriptografam para a mesma senha
        assert decrypt_password(encrypted1) == password
        assert decrypt_password(encrypted2) == password
