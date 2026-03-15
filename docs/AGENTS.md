# AGENTS.md - Guidelines for AI Agents

## Project Overview

Hikvision Radar Pro V4.2 is a Windows desktop application for monitoring speed violations using Hikvision radar cameras. It connects to cameras via RTSP streams and XML event notifications, stores events in SQLite, and can send WhatsApp alerts via the Evolution API.

**Important v4.2 Change**: Uses `/ISAPI/Event/notification/alertStream` instead of `/ISAPI/Traffic/channels/1/vehicleDetect/alertStream` to fix bytes/str decoding issues.

## Project Structure

```
monitora_camera/
├── src/                    # Main application source code
│   ├── core/              # Core business logic
│   │   ├── camera_client.py
│   │   ├── config.py
│   │   ├── crypto.py
│   │   ├── database.py
│   │   ├── event_manager.py
│   │   ├── exceptions.py
│   │   ├── parsing.py
│   │   ├── validators.py
│   │   └── ...
│   ├── repositories/      # Data access layer
│   │   ├── camera_repository.py
│   │   ├── event_repository.py
│   │   └── user_repository.py
│   └── detection/         # YOLO-based car detection
├── ui/                    # PySide6 UI components
│   ├── tabs/              # Tab widgets
│   ├── workers.py         # Background threads
│   └── widgets.py
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── conftest.py        # Pytest fixtures
│   └── test_hikvision_pro_v42_app.py
├── docs/                  # Documentation
├── configs/               # Configuration examples
└── scripts/               # Build scripts
```

---

## Build, Test, and Development Commands

### Installation

```bat
python -m pip install -r configs/requirements_hikvision_pro_v4.txt
```

Or for development with all dev dependencies:

```bat
python -m pip install -e ".[dev]"
```

### Running the Application

```bat
python src/app.py
```

Or from project root:

```bat
python hikvision_pro_v42_app.py
```

### Running Tests

**Run all tests:**
```bat
python -m pytest tests/
```

**Run a specific test file:**
```bat
python -m pytest tests/unit/test_validators.py
```

**Run a specific test (single test):**
```bat
python -m pytest tests/unit/test_validators.py::TestNetworkValidators::test_validate_ip_address_valid
```

**Run tests with specific marker:**
```bat
python -m pytest -m unit        # Run only unit tests
python -m pytest -m "not slow" # Skip slow tests
python -m pytest -m integration # Run integration tests
```

**Run with coverage:**
```bat
python -m pytest --cov=src --cov-report=term-missing
```

### Linting and Code Quality

**Black (formatting):**
```bat
python -m black src/ ui/ tests/
```

**isort (imports):**
```bat
python -m isort src/ ui/ tests/
```

**Flake8 (linting):**
```bat
python -m flake8 src/ ui/ tests/
```

**mypy (type checking):**
```bat
python -m mypy src/
```

**Run all checks:**
```bat
python -m black --check src/ ui/ tests/
python -m isort --check src/ ui/ tests/
python -m flake8 src/ ui/ tests/
python -m mypy src/
```

### Building Windows Executable

```bat
build_hikvision_pro_v42_windows.bat
```

Output: `dist/HikvisionRadarProV42.exe`

---

## Code Style Guidelines

### General Principles

- **Language**: Python (>=3.10)
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Maximum 100 characters
- **Strings**: Use double quotes for user-facing strings, single quotes for internal strings
- **Localization**: Portuguese (Brazilian) for all UI strings and error messages

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Functions | snake_case | `validate_ip_address` |
| Variables | snake_case | `camera_ip`, `event_list` |
| Classes | PascalCase | `CameraClient`, `Database` |
| Constants | UPPER_CASE | `APP_NAME`, `MAX_RETRIES` |
| Private methods | _snake_case | `_internal_method` |
| Enums | PascalCase | `EventType.OverSpeed` |

### Type Hints

Always add type hints to new functions:

```python
def validate_ip_address(ip: str) -> Tuple[bool, str]:
    ...

def process_events(events: List[Event], config: Config) -> Dict[str, Any]:
    ...

class CameraClient:
    def __init__(self, cfg: dict) -> None:
        ...
```

### Import Organization

Use isort with the following order:

1. Standard library
2. Third-party libraries
3. Local application imports

```python
# Standard library
import re
import json
from typing import Tuple, Optional, List
from pathlib import Path

# Third-party
import requests
from PySide6.QtWidgets import QMainWindow

# Local
from src.core.config import AppConfig
from src.core.crypto import encrypt_password
from src.repositories import EventRepository
```

### Error Handling

**Use custom exceptions** from `src/core/exceptions.py`:

```python
from src.core.exceptions import (
    HikvisionRadarError,
    CameraConnectionError,
    ValidationError,
)

def connect_camera(cfg: dict) -> CameraClient:
    try:
        client = CameraClient(cfg)
        is_connected, status, _ = client.test_connection()
        if not is_connected:
            raise CameraConnectionError(
                f"Failed to connect: {status}",
                camera_name=cfg.get("name"),
                host=cfg.get("camera_ip"),
                port=cfg.get("camera_port")
            )
        return client
    except requests.Timeout as e:
        raise CameraConnectionError(
            "Connection timeout",
            camera_name=cfg.get("name"),
            details=str(e)
        ) from e
```

**Validation pattern** - return tuple (bool, str):

```python
def validate_speed_limit(speed: Any) -> Tuple[bool, str]:
    try:
        speed_int = int(speed)
    except (ValueError, TypeError):
        return False, f"Speed must be an integer, got: '{speed}'"
    
    if speed_int < 10:
        return False, "Speed must be at least 10 km/h"
    
    return True, ""
```

### Docstrings

Use Google-style docstrings for all public functions:

```python
def validate_ip_address(ip: str) -> Tuple[bool, str]:
    """
    Validate IPv4 address format.

    Args:
        ip: IP address string to validate

    Returns:
        Tuple[bool, str]: (True, "") if valid, (False, error_message) if invalid

    Example:
        >>> is_valid, error = validate_ip_address("192.168.1.1")
        >>> assert is_valid
    """
```

### Database Operations

- Use repositories in `src/repositories/` for data access
- Follow the existing repository pattern
- Use transactions for multi-step operations

### UI Components (PySide6)

- Use signals/slots for thread-safe communication
- Run long operations in background workers
- Use the existing tab pattern from `ui/tabs/base_tab.py`

### Testing Guidelines

- Place tests in `tests/unit/` for unit tests
- Name test files as `test_*.py`
- Use pytest fixtures from `tests/conftest.py`
- Mark tests with appropriate markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.gui`

```python
@pytest.mark.unit
def test_validate_ip_address_valid():
    is_valid, error = validate_ip_address("192.168.1.1")
    assert is_valid
    assert error == ""
```

---

## Security Guidelines

- **NEVER commit** real camera IPs, usernames, passwords, Evolution API tokens, or generated event data
- Use `configs/hikvision_pro_v42_config.example.json` as template
- Config files (`hikvision_pro_v42_config.json`) are in `.gitignore`
- Passwords are encrypted using Fernet from `cryptography` library
- Use environment variables for sensitive configuration when possible
- Validate all user input using validators in `src/core/validators.py`

---

## Configuration

### Main Config File
`hikvision_pro_v42_config.json` - Runtime configuration (NOT versioned)

### Example Config
`configs/hikvision_pro_v42_config.example.json` - Template with all options

### Database
SQLite: `output/events_v42.db`

---

## Key Modules

| Module | Responsibility |
|--------|----------------|
| `src/core/camera_client.py` | HTTP/RTSP client for Hikvision cameras |
| `src/core/database.py` | SQLite persistence layer |
| `src/core/config.py` | JSON configuration management |
| `src/core/crypto.py` | Password encryption/decryption |
| `src/core/validators.py` | Input validation functions |
| `src/core/parsing.py` | XML event parsing |
| `src/core/evolution_client.py` | WhatsApp Evolution API client |
| `src/repositories/` | Data access layer |

---

## Key Dependencies

- **PySide6** (>=6.6, <7): Qt6 GUI framework
- **requests** (>=2.31, <3): HTTP client
- **cryptography** (>=41.0.0): Password encryption
- **pytest** (>=7.4.0): Testing framework
- **pytest-cov**: Code coverage
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking
