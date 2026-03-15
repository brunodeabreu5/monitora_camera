# AGENTS.md - Instructions for AI Coding Agents

## Project Overview

**Hikvision Radar Pro V4.2** - Traffic monitoring system with camera detection, speed violation alerts via WhatsApp.

**Tech Stack:** Python 3.10+, PySide6/Qt6, SQLite, AES-256-GCM encryption

## Build, Lint, and Test Commands

### Running Tests
```bash
# All tests with coverage
pytest --cov=src --cov-report=html

# Single test file
pytest tests/unit/test_validators.py -v

# Unit tests only
pytest tests/unit/ -v -m "not slow"

# Integration tests
pytest tests/integration/ -v

# GUI tests
pytest -m "gui" -v

# Exclude slow tests
pytest -m "not slow" -v
```

### Code Quality
```bash
# Format code (Black)
black src/ tests/

# Sort imports (isort)
isort src/ tests/

# Lint with Flake8
flake8 src/ tests/

# Type checking (mypy)
mypy src/

# Security scan
bandit -r src/

# Pre-commit hooks
pre-commit run --all-files
```

### Build Executable
```bash
# PyInstaller (standard)
python -m PyInstaller --onefile --windowed --icon=app.ico main.py

# Nuitka (recommended for better performance)
python -m nuitka --standalone --onefile main.py
```

## Code Style Guidelines

### Formatting
- **Line length:** 100 characters (Black default)
- **Formatting tool:** Black 23.7.0
- **Import sorting:** isort with Black profile

### Python Version
- Minimum: Python 3.10
- Supported versions: 3.10, 3.11, 3.12

### Import Organization
```python
# Standard library imports first
import sys
import json
from pathlib import Path

# Third-party imports second
import cv2
from PySide6.QtWidgets import QWidget

# Local application imports last
from src.core.config import AppConfig
from src.core.database import Database
```

### Naming Conventions
- **Functions/variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private methods:** `_leading_underscore`
- **Protected methods:** `__leading_underscore`

### Type Hints
```python
def validate_speed_limit(speed: int | str) -> tuple[bool, str]:
    """Validate speed limit value."""
    is_valid, error = validate_speed_limit(speed)
    return is_valid, error
```

- Use Python 3.10+ union syntax (`int | str`)
- Optional return types: `Optional[Dict[str, Any]]`
- Complex types: `Dict[str, Any]`, `List[str]`, `Tuple[int, int]`

### Error Handling
```python
try:
    camera = self.get_camera_decrypted(camera_name)
except Exception as exc:
    log_runtime_error(f"Camera {camera_name} failed", exc)
    return None
```

- Use specific exceptions when possible
- Log errors with context using `log_runtime_error()`
- Return `None` or empty values on failure (not exceptions)
- Never catch `Exception` in production code without logging

### Docstrings
```python
def validate_ip_address(ip: str) -> tuple[bool, str]:
    """Validate IP address format.

    Args:
        ip: IP address string to validate

    Returns:
        Tuple of (is_valid, error_message). Empty error message if valid.

    Raises:
        TypeError: If ip is not a string
    """
    pass
```

- Docstring first: `check-docstring-first` pre-commit hook
- Format: Google-style docstrings
- Include Args, Returns, and Raises sections
- Keep summaries under 100 characters

### Code Organization
```python
# src/app.py - Main application window
# src/core/config.py - Configuration management
# src/core/database.py - Database operations
# src/core/crypto.py - Encryption utilities
# src/core/event_manager.py - Event pub/sub
# src/core/validators.py - Input validation
# src/repositories/ - Repository pattern for data access
# src/detection/car_detector.py - Object detection
# ui/tabs/ - UI tab implementations
# tests/unit/ - Unit tests
# tests/integration/ - Integration tests
```

## Testing Guidelines

### Test Structure
```python
class TestClassName:
    """Test class with descriptive name."""

    def test_specific_feature(self):
        """Test description with expected behavior."""
        result = function_under_test()
        assert result == expected_value

    def test_edge_case(self):
        """Test edge cases and error conditions."""
        with pytest.raises(ValueError):
            function_under_test("invalid_input")
```

### Test Markers
- `slow`: Long-running tests (exclude with `-m "not slow"`)
- `integration`: Integration tests
- `unit`: Unit tests (default, fast and isolated)
- `gui`: GUI/Qt tests
- `camera`: Tests requiring real camera access
- `network`: Tests requiring network access

### Test Coverage
- Minimum: 60%
- Coverage file: `coverage.xml`, `htmlcov/index.html`
- Report: `pytest --cov=src --cov-report=term-missing`

## Security Best Practices

### Password Handling
```python
# Never store plain text passwords
password_hash, password_salt = hash_password(password)

# Store only hashes
user["password_hash"] = password_hash
user["password_salt"] = password_salt

# Cryptographically secure operations
from .crypto import encrypt_password, decrypt_password
encrypted_pass = encrypt_password(password)
```

### Configuration Security
- Never commit `hikvision_pro_v42_config.json` with real credentials
- Use `.gitignore` to exclude config files
- Always encrypt camera passwords (AES-256-GCM)
- Validate SSL/TLS certificates when possible

### Secret Management
- Use secrets module for non-cryptographic secrets
- Never hardcode API tokens or passwords
- Use environment variables when appropriate
- Enable security linters (Bandit)

## Pre-Commit Hooks

### Hook Configuration
```yaml
# .pre-commit-config.yaml
repos:
  # Code formatting
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black

  # Import sorting
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort

  # Linting
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  # Type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.0
    hooks:
      - id: mypy
```

### Install and Use
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```

## Common Patterns

### Configuration Loading
```python
# Load with default values
config = AppConfig(filepath, skip_first_run_check=True)
config.load()

# Get camera with decrypted password
camera_config = config.get_camera_decrypted(camera_name)
password = config.load_camera_password(camera_config)
```

### Event Handling
```python
# Subscribe to events
event_manager.subscribe("event_type", handler_function)

# Publish events
event_manager.publish("event_type", data_payload)
```

### Repository Pattern
```python
# Create repository instance
repo = CameraRepository()

# CRUD operations
cameras = repo.get_all()
camera = repo.get_by_name("Camera 1")
repo.create(camera_dict)
repo.update("Camera 1", updated_dict)
repo.delete("Camera 1")
```

### Logging
```python
from src.core.logging_config import setup_logging, log_runtime_error

setup_logging()

try:
    # Your code here
    pass
except Exception as exc:
    log_runtime_error("Operation failed", exc)
```

## Project Architecture

### Core Layers
1. **Configuration:** `src/core/config.py` - AppConfig class, helpers
2. **Database:** `src/core/database.py` - SQLite operations, Repository pattern
3. **Security:** `src/core/crypto.py` - Encryption/decryption
4. **Events:** `src/core/event_manager.py` - Pub/sub system
5. **Validation:** `src/core/validators.py` - Input validation
6. **Detection:** `src/detection/car_detector.py` - Object detection
7. **Repositories:** `src/repositories/` - Data access layer

### UI Structure
- `ui/tabs/` - Tab implementations (Dashboard, Cameras, Monitor, History, etc.)
- `ui/widgets.py` - Reusable Qt widgets
- `ui/workers.py` - Background workers for long operations
- `ui/qt_imports.py` - Centralized Qt imports

### Data Flow
```
Event Stream → Parser → Database → UI Updates
                ↓
            Event Manager → Validators → Alerts
```

## Troubleshooting

### Common Issues

**Camera connection timeout:**
```bash
# Test camera connection manually
python scripts/test_alertstream.py --url http://IP:PORT
```

**Video playback issues:**
- Use RTSP over TCP (`rtsp_transport = "tcp"`)
- Enable fallback to snapshot mode
- Check FFmpeg logging level: `set AV_LOG_LEVEL=-8` (Windows) or `export AV_LOG_LEVEL=quiet` (Linux)

**Test failures:**
```bash
# Reinstall dependencies
pip install -e ".[dev]"
pre-commit install
```

### Debug Mode
```python
# Enable debug logging in tests
os.environ["PYTEST_DEBUG"] = "1"
```

## Additional Resources

- **Main Entry:** `main.py`
- **Configuration:** `hikvision_pro_v42_config.json` (runtime)
- **Template:** `configs/hikvision_pro_v42_config.example.json`
- **Logs:** `hikvision_pro_v42.log`
- **Database:** `events_v42.db`
- **Output Images:** `output/images/`
- **Coverage Report:** `htmlcov/index.html`

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new camera feature
fix: resolve camera connection issue
docs: update API documentation
style: code formatting changes
refactor: improve code structure
test: add unit tests
chore: dependency updates
security: fix security vulnerability
```
