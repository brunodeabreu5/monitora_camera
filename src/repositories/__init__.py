# Repository Pattern Implementation (FASE 3.1 - Architecture)
"""
Padrão Repository para acesso a dados no Hikvision Radar Pro.

Separa a lógica de acesso a dados da lógica de negócio, permitindo:
- Maior testabilidade (mock fácil de repositories)
- Separação de responsabilidades
- Queries reutilizáveis
- Migração facilitada para outros bancos de dados

Usage:
    from src.repositories import EventRepository, CameraRepository

    event_repo = EventRepository(db)
    events = event_repo.find_all_by_camera("Camera 1")
"""

from .event_repository import EventRepository
from .camera_repository import CameraRepository
from .user_repository import UserRepository

__all__ = ['EventRepository', 'CameraRepository', 'UserRepository']
