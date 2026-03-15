# Guia de Desenvolvimento - Hikvision Radar Pro

## Configuração do Ambiente de Desenvolvimento

### Pré-requisitos

- Python 3.10 ou superior
- Git
- pipenv ou venv

### Setup Inicial

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/hikvision-radar-pro.git
cd hikvision-radar-pro

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# Instalar dependências de desenvolvimento
pip install -e ".[dev]"

# Instalar pre-commit hooks
pre-commit install
```

### Estrutura de Ambientes

```
.venv/
├── Lib/              # Pacotes instalados
├── Scripts/          # Executáveis (Windows)
└── pyvenv.cfg        # Configuração do ambiente
```

## Convenções de Código

### Estilo de Código

O projeto segue as convenções:
- **PEP 8** para formatação
- **Black** para formatação automática
- **flake8** para linting
- **isort** para organização de imports
- **Google Style** para docstrings

### Exemplo de Código

```python
"""
Módulo exemplo seguindo convenções do projeto.
"""

from typing import Optional, Dict, Any
from pathlib import Path

from src.core.config import AppConfig
from src.core.exceptions import ValidationError
from src.core.validators import validate_ip_address


class ExampleService:
    """
    Serviço exemplo com documentação completa.

    Esta classe demonstra as convenções de código do projeto.

    Attributes:
        config: Configuração da aplicação
        data: Dicionário de dados internos
    """

    def __init__(self, config: AppConfig) -> None:
        """
        Inicializa serviço exemplo.

        Args:
            config: Instância de configuração da aplicação

        Raises:
            ValueError: Se config for None
        """
        if config is None:
            raise ValueError("config não pode ser None")

        self.config = config
        self.data: Dict[str, Any] = {}

    def process_camera(self, camera_name: str) -> Dict[str, Any]:
        """
        Processa dados de uma câmera.

        Args:
            camera_name: Nome único da câmera

        Returns:
            Dicionário com dados processados da câmera

        Raises:
            ValidationError: Se nome da câmera for inválido
            CameraNotFoundError: Se câmera não existe
        """
        # Validar entrada
        if not camera_name or not camera_name.strip():
            raise ValidationError("Nome da câmera não pode ser vazio")

        # Buscar câmera
        camera = self.config.get_camera(camera_name)
        if not camera:
            raise CameraNotFoundError(f"Câmera '{camera_name}' não encontrada")

        # Processar
        result = {
            "name": camera["name"],
            "ip": camera["camera_ip"],
            "enabled": camera.get("enabled", False)
        }

        return result
```

### Nomenclatura

- **Classes**: `PascalCase` (ex: `CameraClient`)
- **Funções/Métodos**: `snake_case` (ex: `get_camera`)
- **Constantes**: `UPPER_SNAKE_CASE` (ex: `MAX_EVENTS`)
- **Privados**: `_leading_underscore` (ex: `_internal_method`)

## Workflow de Desenvolvimento

### Branch Model

```
main          → Branch estável de produção
develop       → Branch de desenvolvimento
feature/*     → Branches de novas funcionalidades
bugfix/*      → Branches de correções de bugs
hotfix/*      → Branches de correções urgentes em produção
```

### Processo de Desenvolvimento

1. Criar branch a partir de `develop`
```bash
git checkout develop
git pull origin develop
git checkout -b feature/nova-funcionalidade
```

2. Fazer alterações seguindo convenções
```bash
# Formatar código
black src/ tests/

# Verificar lint
flake8 src/ tests/

# Organizar imports
isort src/ tests/

# Executar testes
pytest tests/
```

3. Commitar com mensagem descritiva
```bash
git add .
git commit -m "feat: adicionar suporte a TLS para câmeras"
```

4. Push e criar Pull Request
```bash
git push origin feature/nova-funcionalidade
# Criar PR no GitHub
```

### Mensagens de Commit

Seguir convenção Conventional Commits:

```
feat: adicionar nova funcionalidade
fix: corrigir bug na validação
docs: atualizar documentação
style: formatar código
refactor: refatorar sem mudar comportamento
test: adicionar testes
chore: atualizar dependências
perf: melhorar performance
security: corrigir vulnerabilidade
```

## Testes

### Estrutura de Testes

```
tests/
├── unit/                  # Testes unitários isolados
│   ├── test_validators.py
│   ├── test_crypto.py
│   └── test_repositories.py
├── integration/           # Testes de integração
│   ├── test_camera_integration.py
│   └── test_database_integration.py
├── fixtures/              # Fixtures reutilizáveis
│   ├── camera_fixtures.py
│   └── user_fixtures.py
└── conftest.py            # Configuração pytest
```

### Executando Testes

```bash
# Todos os testes
pytest

# Apenas testes unitários
pytest tests/unit/

# Testes específicos
pytest tests/unit/test_validators.py

# Com coverage
pytest --cov=src --cov-report=html

# Testes marcados como "slow"
pytest -m slow

# Excluir testes lentos
pytest -m "not slow"
```

### Escrevendo Testes

```python
"""Testes para módulo exemplo."""

import pytest
from src.core.example import ExampleService
from src.core.exceptions import ValidationError


class TestExampleService:
    """Testes para ExampleService."""

    def test_process_camera_valid(self, temp_config):
        """Testa processamento de câmera válida."""
        # Setup
        service = ExampleService(temp_config)

        # Execute
        result = service.process_camera("Camera 1")

        # Assert
        assert result["name"] == "Camera 1"
        assert "ip" in result

    def test_process_camera_invalid_name(self, temp_config):
        """Testa erro com nome inválido."""
        service = ExampleService(temp_config)

        with pytest.raises(ValidationError):
            service.process_camera("")

    def test_process_camera_not_found(self, temp_config):
        """Testa erro com câmera inexistente."""
        service = ExampleService(temp_config)

        with pytest.raises(CameraNotFoundError):
            service.process_camera("NonExistent")
```

## Debugging

### Logging

```python
from src.core.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Mensagem de debug")
logger.info("Mensagem informativa")
logger.warning("Aviso")
logger.error("Erro ocorreu", exc_info=True)
logger.critical("Erro crítico")
```

### Debugging no VS Code

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Python: Main App",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal"
        }
    ]
}
```

### Debugging de Threads

```python
import sys
from PyQt6.QtCore import QThread

def list_threads():
    """Lista todas as threads ativas."""
    for thread in threading.enumerate():
        print(f"Thread: {thread.name}, Alive: {thread.is_alive()}")

# Chamar no console de debug
list_threads()
```

## Performance

### Profiling

```bash
# Profiling de CPU
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats

# Profiling de memória
pip install memory_profiler
python -m memory_profiler main.py
```

### Otimização

```python
from src.core.cache import cached_camera, get_camera_cache

@cached_camera(ttl=300)
def expensive_operation(camera_name: str) -> dict:
    """Operação custosa com cache."""
    # ...
    return result

# Invalidar cache quando necessário
get_camera_cache().invalidate(camera_name)
```

## Deployment

### Build para Distribuição

```bash
# Usar PyInstaller
pip install pyinstaller
pyinstaller --onefile --windowed --icon=app.ico main.py

# Ou usar Nuitka para melhor performance
pip install nuitka
python -m nuitka --standalone --onefile --windows-disable-console main.py
```

### Checklist de Release

- [ ] Todos os testes passando
- [ ] Coverage > 60%
- [ ] Sem warnings de flake8
- [ ] Documentação atualizada
- [ ] Changelog atualizado
- [ ] Versão incrementada
- [ ] Tag criada no Git

## Troubleshooting Comum

### ImportError

```python
# Erro: ModuleNotFoundError: No module named 'src'

# Solução: Adicionar src ao PYTHONPATH
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### PyQt/Qt Errors

```bash
# Erro: Qt platform plugin errors

# Solução: Instalar dependências do sistema
# Ubuntu/Debian:
sudo apt-get install libxcb-xinerama0 libxcb-cursor0

# Windows: Reinstalar PySide6
pip uninstall PySide6
pip install PySide6
```

### Database Locked

```python
# Erro: sqlite3.OperationalError: database is locked

# Solução: Usar timeout maior
import sqlite3
conn = sqlite3.connect("db.sqlite3", timeout=30.0)
```

## Recursos Adicionais

### Documentação Útil

- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
- [Python Documentation](https://docs.python.org/3.10/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

### Ferramentas

- **pylint**: Análise estática avançada
- **bandit**: Verificação de segurança
- **mypy**: Verificação de tipos estáticos
- **pytest**: Framework de testes
- **black**: Formatação automática
- **coverage**: Medição de cobertura de testes

### Comunidade

- Python Brasil: https://python.org.br/
- Qt Brasil: https://qt-project.org/
