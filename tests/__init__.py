# Test suite for Hikvision Radar Pro V4.2
"""
Módulo de testes para o Hikvision Radar Pro V4.2.

Estrutura de diretórios:
    tests/
    ├── unit/           # Testes unitários isolados
    ├── integration/    # Testes de integração
    ├── fixtures/       # Fixtures reutilizáveis
    └── helpers/        # Helpers e mocks para testes
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
