# Unit tests for repositories
"""
Testes unitários para repositories.
"""

import pytest
from src.repositories import EventRepository, CameraRepository, UserRepository
from src.core.database import Database
from pathlib import Path


class TestEventRepository:
    """Testes para EventRepository."""

    def test_insert_event(self, event_repository):
        """Testa inserção de evento."""
        event_data = {
            "camera_name": "Camera Test",
            "ts": "14/03/2026 15:30:00",
            "plate": "XYZ9999",
            "speed": "90 km/h",
            "lane": "1",
            "direction": "Leste",
            "event_type": "overspeed",
            "image_path": "/tmp/test.jpg",
            "applied_speed_limit": 60.0,
            "is_overspeed": True
        }

        event_id = event_repository.insert(event_data)
        assert event_id > 0
        assert isinstance(event_id, int)

    def test_find_by_id(self, event_repository):
        """Testa busca de evento por ID."""
        # Inserir evento de teste
        event_data = {
            "camera_name": "Camera Test",
            "ts": "14/03/2026 15:30:00",
            "plate": "XYZ9999",
            "speed": "90 km/h",
            "lane": "1",
            "direction": "Leste",
            "event_type": "normal"
        }
        event_id = event_repository.insert(event_data)

        # Buscar por ID
        found = event_repository.find_by_id(event_id)
        assert found is not None
        assert found["camera_name"] == "Camera Test"
        assert found["plate"] == "XYZ9999"

    def test_find_all(self, event_repository):
        """Testa busca de todos os eventos."""
        events = event_repository.find_all(limit=10)
        assert len(events) > 0  # populated_db tem 2 eventos

    def test_find_filtered_by_camera(self, event_repository):
        """Testa filtro por câmera."""
        events = event_repository.find_filtered(camera_name="Camera 1")
        assert len(events) > 0
        assert all(e[0] == "Camera 1" for e in events)  # camera_name é índice 0

    def test_find_filtered_by_plate(self, event_repository):
        """Testa filtro por placa."""
        events = event_repository.find_filtered(plate="ABC")
        assert len(events) > 0

    def test_find_filtered_by_speed(self, event_repository):
        """Testa filtro por velocidade mínima."""
        events = event_repository.find_filtered(min_speed="70")
        assert len(events) == 1  # Apenas o evento de 85 km/h

    def test_count_filtered(self, event_repository):
        """Testa contagem de eventos filtrados."""
        count = event_repository.count_filtered(camera_name="Camera 1")
        assert count == 1

    def test_find_overspeed_events(self, event_repository):
        """Testa busca de eventos de excesso."""
        events = event_repository.find_overspeed_events()
        assert len(events) == 1  # Apenas 1 evento com is_overspeed=True
        assert events[0]["is_overspeed"] == 1

    def test_get_dashboard_stats(self, event_repository):
        """Testa obtenção de estatísticas do dashboard."""
        stats = event_repository.get_dashboard_stats()

        assert "total" in stats
        assert "today" in stats
        assert "rows" in stats
        assert "last_plate" in stats

        assert stats["total"] == 2
        assert len(stats["rows"]) == 2

    def test_delete_by_id(self, event_repository):
        """Testa deleção de evento por ID."""
        # Inserir evento
        event_data = {
            "camera_name": "Camera Test",
            "ts": "14/03/2026 15:30:00",
            "plate": "DEL1234",
            "speed": "50 km/h",
            "lane": "1",
            "direction": "Norte",
            "event_type": "normal"
        }
        event_id = event_repository.insert(event_data)

        # Deletar
        result = event_repository.delete_by_id(event_id)
        assert result is True

        # Verificar que foi deletado
        found = event_repository.find_by_id(event_id)
        assert found is None

    def test_count_all(self, event_repository):
        """Testa contagem total de eventos."""
        count = event_repository.count_all()
        assert count == 2  # populated_db tem 2 eventos


class TestCameraRepository:
    """Testes para CameraRepository."""

    def test_find_all(self, camera_repository):
        """Testa busca de todas as câmeras."""
        cameras = camera_repository.find_all()
        assert len(cameras) > 0
        assert cameras[0]["name"] == "Camera 1"

    def test_find_by_name(self, camera_repository):
        """Testa busca de câmera por nome."""
        camera = camera_repository.find_by_name("Camera 1")
        assert camera is not None
        assert camera["camera_ip"] == "192.168.1.100"

    def test_find_by_name_not_found(self, camera_repository):
        """Testa busca de câmera inexistente."""
        camera = camera_repository.find_by_name("NonExistent")
        assert camera is None

    def test_find_names(self, camera_repository):
        """Testa busca de nomes de câmeras."""
        names = camera_repository.find_names()
        assert "Camera 1" in names

    def test_find_enabled(self, camera_repository):
        """Testa busca de câmeras habilitadas."""
        cameras = camera_repository.find_enabled()
        assert len(cameras) > 0
        assert all(c.get("enabled", False) for c in cameras)

    def test_save_new_camera(self, camera_repository):
        """Testa salvamento de nova câmera."""
        new_camera = {
            "name": "Camera Test",
            "enabled": True,
            "camera_ip": "192.168.1.200",
            "camera_port": 80,
            "camera_user": "admin",
            "camera_pass": "",
            "channel": 101,
            "timeout": 15,
            "speed_limit_value": 80,
        }

        camera_repository.save(new_camera)
        found = camera_repository.find_by_name("Camera Test")
        assert found is not None

    def test_update_camera(self, camera_repository):
        """Testa atualização de câmera existente."""
        camera = camera_repository.find_by_name("Camera 1")
        camera["camera_port"] = 443

        camera_repository.update(camera)

        updated = camera_repository.find_by_name("Camera 1")
        assert updated["camera_port"] == 443

    def test_delete_camera(self, camera_repository):
        """Testa deleção de câmera."""
        # Criar câmera temporária
        temp_camera = {
            "name": "Temp Camera",
            "enabled": False,
            "camera_ip": "10.0.0.1",
            "camera_port": 80,
            "camera_user": "admin",
            "camera_pass": "",
        }
        camera_repository.insert(temp_camera)

        # Deletar
        result = camera_repository.delete("Temp Camera")
        assert result is True

        # Verificar
        found = camera_repository.find_by_name("Temp Camera")
        assert found is None

    def test_exists(self, camera_repository):
        """Testa verificação de existência de câmera."""
        assert camera_repository.exists("Camera 1")
        assert not camera_repository.exists("NonExistent")

    def test_count(self, camera_repository):
        """Testa contagem de câmeras."""
        count = camera_repository.count()
        assert count >= 1


class TestUserRepository:
    """Testes para UserRepository."""

    def test_find_all(self, user_repository):
        """Testa busca de todos os usuários."""
        users = user_repository.find_all()
        assert len(users) > 0
        assert users[0]["username"] == "admin"


class TestCameraRename:
    """Testes para funcionalidade de renomeação de câmeras."""

    def test_count_camera_events(self, camera_repository, event_repository):
        """Testa contagem de eventos por câmera."""
        # Criar eventos de teste
        event_repository.insert({
            "camera_name": "Camera 1",
            "ts": "14/03/2026 15:30:00",
            "plate": "ABC1234",
            "speed": "85 km/h",
            "lane": "1",
            "direction": "Leste",
            "event_type": "overspeed",
            "image_path": "/tmp/test.jpg",
            "applied_speed_limit": 60.0,
            "is_overspeed": True
        })

        event_repository.insert({
            "camera_name": "Camera 1",
            "ts": "14/03/2026 15:35:00",
            "plate": "XYZ5678",
            "speed": "70 km/h",
            "lane": "2",
            "direction": "Oeste",
            "event_type": "normal",
            "image_path": "/tmp/test2.jpg",
            "applied_speed_limit": 60.0,
            "is_overspeed": False
        })

        # Criar snapshot de teste
        event_repository.insert({
            "camera_name": "Camera 1",
            "ts": "14/03/2026 15:40:00",
            "plate": "DEF9999",
            "speed": "65 km/h",
            "lane": "1",
            "direction": "Norte",
            "event_type": "normal",
            "image_path": "/tmp/test3.jpg",
            "applied_speed_limit": 60.0,
            "is_overspeed": False
        })

        # Inserir snapshot
        event_id = event_repository.db.last_event_id()
        with event_repository.db.lock:
            event_repository.db.conn.execute("""
                INSERT INTO snapshots (camera_name, ts, image_path, event_id)
                VALUES (?, ?, ?, ?)
            """, ("Camera 1", "14/03/2026 15:40:00", "/tmp/snapshot.jpg", event_id))
            event_repository.db.conn.commit()

        # Contar eventos
        counts = camera_repository.count_camera_events("Camera 1", event_repository.db)
        assert counts["events"] >= 3
        assert counts["snapshots"] >= 1
        assert counts["total"] >= 4

    def test_update_camera_name(self, event_repository):
        """Testa atualização de nome de câmera nos eventos."""
        # Criar evento de teste
        event_id = event_repository.insert({
            "camera_name": "Camera Rename Test",
            "ts": "14/03/2026 15:30:00",
            "plate": "REN1234",
            "speed": "80 km/h",
            "lane": "1",
            "direction": "Sul",
            "event_type": "normal",
            "image_path": "/tmp/rename_test.jpg",
            "applied_speed_limit": 60.0,
            "is_overspeed": True
        })

        # Verificar que evento foi criado com nome antigo
        event = event_repository.find_by_id(event_id)
        assert event["camera_name"] == "Camera Rename Test"

        # Renomear
        updated_count = event_repository.update_camera_name(
            "Camera Rename Test",
            "Camera Renomeada"
        )
        assert updated_count >= 1

        # Verificar que evento foi atualizado
        event = event_repository.find_by_id(event_id)
        assert event["camera_name"] == "Camera Renomeada"

        # Tentar buscar com nome antigo - não deve encontrar
        events = event_repository.find_filtered(camera_name="Camera Rename Test")
        assert len(events) == 0

        # Buscar com novo nome - deve encontrar
        events = event_repository.find_filtered(camera_name="Camera Renomeada")
        assert len(events) >= 1

    def test_update_camera_name_with_snapshots(self, event_repository):
        """Testa atualização de nome de câmera incluindo snapshots."""
        # Criar evento e snapshot
        event_id = event_repository.insert({
            "camera_name": "Camera Snap Test",
            "ts": "14/03/2026 15:30:00",
            "plate": "SNP1234",
            "speed": "75 km/h",
            "lane": "1",
            "direction": "Leste",
            "event_type": "normal",
            "image_path": "/tmp/snap_test.jpg",
            "applied_speed_limit": 60.0,
            "is_overspeed": True
        })

        with event_repository.db.lock:
            event_repository.db.conn.execute("""
                INSERT INTO snapshots (camera_name, ts, image_path, event_id)
                VALUES (?, ?, ?, ?)
            """, ("Camera Snap Test", "14/03/2026 15:30:00", "/tmp/snapshot.jpg", event_id))
            event_repository.db.conn.commit()

        # Contar snapshots antes
        cursor = event_repository.db.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM snapshots WHERE camera_name = ?",
            ("Camera Snap Test",)
        )
        snap_count_before = cursor.fetchone()[0]
        assert snap_count_before == 1

        # Renomear
        updated_count = event_repository.update_camera_name(
            "Camera Snap Test",
            "Camera Snapshot Renomeada"
        )
        assert updated_count >= 2  # evento + snapshot

        # Verificar snapshots foram atualizados
        cursor.execute(
            "SELECT COUNT(*) FROM snapshots WHERE camera_name = ?",
            ("Camera Snapshot Renomeada",)
        )
        snap_count_after = cursor.fetchone()[0]
        assert snap_count_after == 1

        # Verificar que não há mais com nome antigo
        cursor.execute(
            "SELECT COUNT(*) FROM snapshots WHERE camera_name = ?",
            ("Camera Snap Test",)
        )
        snap_count_old = cursor.fetchone()[0]
        assert snap_count_old == 0

    def test_rename_camera_events_full_workflow(self, camera_repository, event_repository):
        """Testa workflow completo de renomeação de câmera."""
        # Criar câmera temporária
        temp_camera = {
            "name": "Camera Temp Rename",
            "enabled": False,
            "camera_ip": "192.168.1.250",
            "camera_port": 80,
            "camera_user": "admin",
            "camera_pass": "",
        }
        camera_repository.insert(temp_camera)

        # Criar eventos para a câmera
        for i in range(3):
            event_repository.insert({
                "camera_name": "Camera Temp Rename",
                "ts": f"14/03/2026 15:{30 + i}:00",
                "plate": f"TEM{i}34",
                "speed": f"{70 + i * 5} km/h",
                "lane": "1",
                "direction": "Norte",
                "event_type": "normal",
                "image_path": f"/tmp/test{i}.jpg",
                "applied_speed_limit": 60.0,
                "is_overspeed": i >= 2
            })

        # Criar snapshots
        with event_repository.db.lock:
            for i in range(2):
                event_repository.db.conn.execute("""
                    INSERT INTO snapshots (camera_name, ts, image_path)
                    VALUES (?, ?, ?)
                """, ("Camera Temp Rename", f"14/03/2026 15:{30 + i}:00", f"/tmp/snapshot{i}.jpg"))
            event_repository.db.conn.commit()

        # Renomear câmera com migração
        result = camera_repository.rename_camera_events(
            "Camera Temp Rename",
            "Camera Final Renomeada",
            user="test_user",
            db=event_repository.db
        )

        # Verificar resultado
        assert result["success"] is True
        assert result["updated"]["total"] >= 5  # 3 eventos + 2 snapshots
        assert result["old_name"] == "Camera Temp Rename"
        assert result["new_name"] == "Camera Final Renomeada"

        # Verificar que câmera foi renomeada no config
        camera = camera_repository.find_by_name("Camera Final Renomeada")
        assert camera is not None
        assert camera["camera_ip"] == "192.168.1.250"

        # Verificar que nome antigo não existe mais no config
        camera = camera_repository.find_by_name("Camera Temp Rename")
        assert camera is None

        # Verificar que eventos foram atualizados no banco
        events = event_repository.find_filtered(camera_name="Camera Final Renomeada")
        assert len(events) >= 3

        # Verificar que eventos com nome antigo não existem
        events = event_repository.find_filtered(camera_name="Camera Temp Rename")
        assert len(events) == 0

        # Verificar snapshots
        cursor = event_repository.db.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM snapshots WHERE camera_name = ?",
            ("Camera Final Renomeada",)
        )
        snap_count = cursor.fetchone()[0]
        assert snap_count >= 2

        # Cleanup
        camera_repository.delete("Camera Final Renomeada")

    def test_rename_camera_duplicate_name(self, camera_repository, event_repository):
        """Testa erro ao renomear para nome duplicado."""
        # Criar segunda câmera para testar duplicidade
        second_camera = {
            "name": "Camera 2",
            "enabled": True,
            "camera_ip": "192.168.1.101",
            "camera_port": 80,
            "camera_user": "admin",
            "camera_pass": "",
        }
        camera_repository.insert(second_camera)

        # Tentar renomear para nome que já existe
        with pytest.raises(ValueError):
            camera_repository.rename_camera_events(
                "Camera 1",
                "Camera 2",  # Já existe
                user="test_user",
                db=event_repository.db
            )

    def test_rename_camera_nonexistent(self, camera_repository, event_repository):
        """Testa erro ao renomear câmera inexistente."""
        with pytest.raises(ValueError, match="não encontrada"):
            camera_repository.rename_camera_events(
                "Camera Inexistente",
                "Nova Camera",
                user="test_user",
                db=event_repository.db
            )

    def test_find_by_username(self, user_repository):
        """Testa busca de usuário por nome."""
        user = user_repository.find_by_username("admin")
        assert user is not None
        assert user["role"] == "Administrador"

    def test_authenticate_valid(self, user_repository):
        """Testa autenticação válida."""
        user = user_repository.authenticate("admin", "admin123")
        assert user is not None
        assert user["username"] == "admin"

    def test_authenticate_invalid(self, user_repository):
        """Testa autenticação inválida."""
        user = user_repository.authenticate("admin", "wrong_password")
        assert user is None

    def test_create_user(self, user_repository):
        """Testa criação de novo usuário."""
        new_user = {
            "username": "testuser",
            "password": "TestPass123",
            "role": "Operador",
        }

        user_repository.create(new_user)

        found = user_repository.find_by_username("testuser")
        assert found is not None

        # Cleanup
        user_repository.delete("testuser")

    def test_create_duplicate_username(self, user_repository):
        """Testa erro ao criar usuário com nome duplicado."""
        new_user = {
            "username": "admin",  # Já existe
            "password": "TestPass123",
            "role": "Operador",
        }

        with pytest.raises(ValueError, match="já existe"):
            user_repository.create(new_user)

    def test_update_user(self, user_repository):
        """Testa atualização de usuário."""
        user = user_repository.find_by_username("admin")
        user["role"] = "Operador"

        user_repository.update(user)

        updated = user_repository.find_by_username("admin")
        assert updated["role"] == "Operador"

    def test_delete_user(self, user_repository):
        """Testa deleção de usuário."""
        # Criar usuário temporário
        temp_user = {
            "username": "tempuser",
            "password": "TempPass123",
            "role": "Operador",
        }
        user_repository.create(temp_user)

        # Deletar
        result = user_repository.delete("tempuser")
        assert result is True

        # Verificar
        found = user_repository.find_by_username("tempuser")
        assert found is None

    def test_change_password(self, user_repository):
        """Testa mudança de senha."""
        result = user_repository.change_password("admin", "NewPass456", "admin123")
        assert result is True

        # Verificar nova senha funciona
        user = user_repository.authenticate("admin", "NewPass456")
        assert user is not None

        # Reverter para senha original
        user_repository.change_password("admin", "admin123", "NewPass456")

    def test_get_admins(self, user_repository):
        """Testa busca de administradores."""
        admins = user_repository.get_admins()
        assert len(admins) > 0
        assert all(u["role"] == "Administrador" for u in admins)
