# Pytest configuration and fixtures
"""
Fixtures e configuração compartilhada para todos os testes.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from PySide6.QtWidgets import QApplication

from src.core.config import AppConfig
from src.core.database import Database
from src.core.crypto import encrypt_password, decrypt_password
from src.repositories import EventRepository, CameraRepository, UserRepository


# ============================================================================
# Qt Application Fixture
# ============================================================================

@pytest.fixture(scope="session")
def qt_app():
    """
    Cria aplicação Qt para testes GUI.

    Scope: session (criada uma vez por sessão de testes)
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Cleanup não é necessário (Qt gerencia)


# ============================================================================
# Temporary Directory Fixture
# ============================================================================

@pytest.fixture
def temp_dir():
    """
    Cria diretório temporário para testes.

    Scope: function (criada e deletada para cada teste)

    Yields:
        Path: Caminho para diretório temporário
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db(temp_dir):
    """
    Cria banco de dados temporário em memória.

    Scope: function

    Yields:
        Database: Instância de banco temporário
    """
    db_path = temp_dir / "test_events.db"
    db = Database(db_path)
    yield db
    db.close()


@pytest.fixture
def populated_db(temp_db):
    """
    Cria banco de dados com eventos de teste.

    Scope: function

    Yields:
        Database: Instância de banco com dados populados
    """
    # Inserir eventos de teste
    test_events = [
        {
            "camera_name": "Camera 1",
            "ts": "14/03/2026 10:00:00",
            "plate": "ABC1234",
            "speed": "85 km/h",
            "speed_value": 85.0,
            "lane": "1",
            "direction": "Norte",
            "event_type": "overspeed",
            "image_path": "/tmp/test1.jpg",
            "xml_path": "/tmp/test1.xml",
            "json_path": "/tmp/test1.json",
            "raw_xml": "<event>test</event>",
            "applied_speed_limit": 60.0,
            "is_overspeed": True
        },
        {
            "camera_name": "Camera 2",
            "ts": "14/03/2026 10:05:00",
            "plate": "DEF5678",
            "speed": "55 km/h",
            "speed_value": 55.0,
            "lane": "2",
            "direction": "Sul",
            "event_type": "normal",
            "image_path": "/tmp/test2.jpg",
            "xml_path": "/tmp/test2.xml",
            "json_path": "/tmp/test2.json",
            "raw_xml": "<event>test2</event>",
            "applied_speed_limit": 60.0,
            "is_overspeed": False
        }
    ]

    for event in test_events:
        temp_db.insert_event(event)

    yield temp_db


# ============================================================================
# Config Fixtures
# ============================================================================

@pytest.fixture
def temp_config(temp_dir):
    """
    Cria configuração temporária.

    Scope: function

    Yields:
        AppConfig: Instância de configuração temporária
    """
    config_path = temp_dir / "test_config.json"
    config = AppConfig(config_path, skip_first_run_check=True)

    # Criar usuário admin padrão
    from src.core.config import hash_password
    pwd_hash, pwd_salt = hash_password("admin123")
    config.data["users"] = [{
        "username": "admin",
        "password_hash": pwd_hash,
        "password_salt": pwd_salt,
        "role": "Administrador",
        "must_change_password": False
    }]

    # Criar câmera de teste
    config.data["cameras"] = [{
        "name": "Camera 1",
        "enabled": True,
        "camera_ip": "192.168.1.100",
        "camera_port": 80,
        "camera_user": "admin",
        "camera_pass": "",
        "channel": 101,
        "timeout": 15,
        "output_dir": str(temp_dir / "output"),
        "speed_limit_value": 60,
        "verify_ssl": False
    }]

    config.save()
    yield config


# ============================================================================
# Repository Fixtures
# ============================================================================

@pytest.fixture
def event_repository(populated_db):
    """
    Cria repository de eventos com banco populado.

    Scope: function

    Yields:
        EventRepository: Instância configurada
    """
    repo = EventRepository(populated_db)
    yield repo


@pytest.fixture
def camera_repository(temp_config):
    """
    Cria repository de câmeras com config temporária.

    Scope: function

    Yields:
        CameraRepository: Instância configurada
    """
    repo = CameraRepository(temp_config)
    yield repo


@pytest.fixture
def user_repository(temp_config):
    """
    Cria repository de usuários com config temporária.

    Scope: function

    Yields:
        UserRepository: Instância configurada
    """
    repo = UserRepository(temp_config)
    yield repo


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_camera_client():
    """
    Cria mock de CameraClient.

    Scope: function

    Yields:
        Mock: Mock configurado de CameraClient
    """
    client = Mock()
    client.test_connection.return_value = (True, 200, "OK")
    client.download_snapshot.return_value = (b"fake_image_data", "http://test/snapshot")
    return client


@pytest.fixture
def mock_evolution_client():
    """
    Cria mock de EvolutionApiClient.

    Scope: function

    Yields:
        Mock: Mock configurado de EvolutionApiClient
    """
    client = Mock()
    client.test_connection.return_value = (True, "Conexão bem-sucedida")
    client.send_event_message.return_value = (True, "Mensagem enviada")
    return client


# ============================================================================
# Crypto Test Data
# ============================================================================

@pytest.fixture
def test_password():
    """Senha de teste padrão."""
    return "TestPassword123"


@pytest.fixture
def encrypted_password(test_password):
    """Senha criptografada de teste."""
    return encrypt_password(test_password)


# ============================================================================
# Qt Widget Fixtures
# ============================================================================

@pytest.fixture
def mock_main_window(qt_app):
    """
    Cria mock de MainWindow.

    Scope: function

    Yields:
        Mock: Mock de MainWindow com atributos básicos
    """
    main_window = Mock()
    main_window.config = Mock()
    main_window.logged_user = {"username": "admin", "role": "Administrador"}
    main_window.append_log = Mock()
    main_window.reload_camera_lists = Mock()
    return main_window


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Configura markers personalizados."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "gui: marks tests that require GUI")
    config.addinivalue_line("markers", "camera: marks tests that require real camera")
    config.addinivalue_line("markers", "network: marks tests that require network access")
