# Camera Repository (FASE 3.1 - Repository Pattern)
"""
Repository para gerenciamento de configurações de câmeras.

Encapsula operações de CRUD de câmeras, abstraindo o acesso
ao arquivo de configuração JSON.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import shutil

from src.core.config import AppConfig


class CameraRepository:
    """
    Repository para acesso e manipulação de configurações de câmeras.

    Fornece interface limpa para gerenciar câmeras sem expor
    a complexidade do formato de configuração JSON.

    Attributes:
        config: Instância de AppConfig para acesso às configurações

    Example:
        >>> repo = CameraRepository(config)
        >>> camera = repo.find_by_name("Camera 1")
        >>> repo.update(camera)
    """

    def __init__(self, config: AppConfig):
        """
        Inicializa repository com configuração da aplicação.

        Args:
            config: Instância de AppConfig
        """
        self.config = config

    def find_all(self) -> List[Dict[str, Any]]:
        """
        Retorna todas as câmeras configuradas.

        Returns:
            List[Dict]: Lista de câmeras (dicionários com configuração)
        """
        return self.config.data.get("cameras", [])

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Busca câmera por nome.

        Args:
            name: Nome único da câmera

        Returns:
            Optional[Dict]: Dicionário com configuração da câmera ou None
        """
        return self.config.get_camera(name)

    def find_by_name_decrypted(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Busca câmera por nome com senha descriptografada.

        Retorna senha em texto claro para uso em tempo de execução.

        Args:
            name: Nome da câmera

        Returns:
            Optional[Dict]: Câmera com senha descriptografada ou None
        """
        return self.config.get_camera_decrypted(name)

    def find_enabled(self) -> List[Dict[str, Any]]:
        """
        Retorna apenas câmeras habilitadas.

        Returns:
            List[Dict]: Lista de câmeras com enabled=True
        """
        cameras = self.find_all()
        return [c for c in cameras if c.get("enabled", False)]

    def find_names(self) -> List[str]:
        """
        Retorna lista de nomes de todas as câmeras.

        Returns:
            List[str]: Lista de nomes de câmeras
        """
        return self.config.get_camera_names()

    def save(self, camera: Dict[str, Any]) -> None:
        """
        Salva ou atualiza uma câmera.

        Se a câmera já existe (mesmo nome), atualiza.
        Se não existe, insere nova câmera.

        Args:
            camera: Dicionário com configuração completa da câmera
        """
        self.config.upsert_camera(camera)
        self.config.save()

    def insert(self, camera: Dict[str, Any]) -> None:
        """
        Insere nova câmera.

        Args:
            camera: Dicionário com configuração da câmera

        Raises:
            ValueError: Se câmera com mesmo nome já existe
        """
        existing = self.find_by_name(camera.get("name", ""))
        if existing:
            raise ValueError(f"Câmera '{camera.get('name')}' já existe")

        self.save(camera)

    def update(self, camera: Dict[str, Any]) -> None:
        """
        Atualiza câmera existente.

        Args:
            camera: Dicionário com configuração da câmera

        Raises:
            ValueError: Se câmera não existe
        """
        if not self.find_by_name(camera.get("name", "")):
            raise ValueError(f"Câmera '{camera.get('name')}' não encontrada")

        self.save(camera)

    def delete(self, name: str) -> bool:
        """
        Deleta uma câmera por nome.

        Args:
            name: Nome da câmera a deletar

        Returns:
            bool: True se deletou com sucesso, False se não encontrou
        """
        if not self.find_by_name(name):
            return False

        self.config.delete_camera(name)
        self.config.save()
        return True

    def exists(self, name: str) -> bool:
        """
        Verifica se câmera existe.

        Args:
            name: Nome da câmera

        Returns:
            bool: True se câmera existe, False caso contrário
        """
        return self.find_by_name(name) is not None

    def count(self) -> int:
        """
        Retorna número total de câmeras.

        Returns:
            int: Total de câmeras configuradas
        """
        return len(self.find_all())

    def count_enabled(self) -> int:
        """
        Retorna número de câmeras habilitadas.

        Returns:
            int: Total de câmeras com enabled=True
        """
        return len(self.find_enabled())

    def get_password(self, camera_name: str) -> str:
        """
        Retorna senha descriptografada de uma câmera.

        Args:
            camera_name: Nome da câmera

        Returns:
            str: Senha em texto claro (string vazia se erro)

        Raises:
            ValueError: Se câmera não existe
        """
        camera = self.find_by_name_decrypted(camera_name)
        if not camera:
            raise ValueError(f"Câmera '{camera_name}' não encontrada")

        return camera.get("camera_pass", "")

    def test_connection(self, camera_name: str) -> tuple[bool, int, str]:
        """
        Testa conexão com uma câmera.

        Args:
            camera_name: Nome da câmera a testar

        Returns:
            tuple[bool, int, str]: (sucesso, status_code, mensagem)

        Raises:
            ValueError: Se câmera não existe
        """
        from src.core.camera_client import CameraClient

        camera = self.find_by_name_decrypted(camera_name)
        if not camera:
            raise ValueError(f"Câmera '{camera_name}' não encontrada")

        client = CameraClient(camera)
        return client.test_connection()

    def get_snapshot(self, camera_name: str) -> tuple[bytes, str]:
        """
        Baixa snapshot de uma câmera.

        Args:
            camera_name: Nome da câmera

        Returns:
            tuple[bytes, str]: (imagem_bytes, url_usada)

        Raises:
            ValueError: Se câmera não existe
            RuntimeError: Se falhar ao baixar snapshot
        """
        from src.core.camera_client import CameraClient

        camera = self.find_by_name_decrypted(camera_name)
        if not camera:
            raise ValueError(f"Câmera '{camera_name}' não encontrada")

        client = CameraClient(camera)
        return client.download_snapshot()

    def count_camera_events(self, camera_name: str, db: Any) -> Dict[str, int]:
        """
        Conta quantos registros históricos serão afetados pela renomeação.

        Args:
            camera_name: Nome da câmera a ser renomeada
            db: Instância do Database para acesso aos dados

        Returns:
            Dict[str, int]: Dicionário com contagens por tabela:
                {
                    "events": 150,
                    "snapshots": 300,
                    "total": 450
                }
        """
        counts = {"events": 0, "snapshots": 0, "total": 0}

        with db.lock:
            cursor = db.conn.cursor()

            # Contar eventos
            cursor.execute(
                "SELECT COUNT(*) FROM events WHERE camera_name = ?",
                (camera_name,)
            )
            counts["events"] = cursor.fetchone()[0]

            # Contar snapshots
            cursor.execute(
                "SELECT COUNT(*) FROM snapshots WHERE camera_name = ?",
                (camera_name,)
            )
            counts["snapshots"] = cursor.fetchone()[0]

        counts["total"] = counts["events"] + counts["snapshots"]
        return counts

    def rename_camera_events(
        self,
        old_name: str,
        new_name: str,
        user: str = "system",
        db: Any = None
    ) -> Dict[str, Any]:
        """
        Renomeia câmera migrando todos os registros históricos.

        Implementa transação atômica com rollback capability para garantir
        integridade dos dados durante a operação de renomeação.

        Args:
            old_name: Nome atual da câmera
            new_name: Novo nome da câmera
            user: Usuário que está realizando a operação
            db: Instância do Database (opcional)

        Returns:
            Dict[str, Any]: Dicionário com estatísticas da migração:
                {
                    "success": True,
                    "updated": {
                        "events": 150,
                        "snapshots": 300,
                        "total": 450
                    },
                    "old_name": "Camera 1",
                    "new_name": "Nova Camera"
                }

        Raises:
            ValueError: Se newName já existir ou camera não encontrada
            sqlite3.Error: Se houver erro na migração
        """
        from src.repositories.event_repository import EventRepository
        from src.core.exceptions import CameraRenameError

        # Validar que new_name não existe
        if self.exists(new_name):
            raise ValueError(
                f"Já existe uma câmera com o nome '{new_name}'. "
                f"Escolha outro nome."
            )

        # Validar que old_name existe
        if not self.exists(old_name):
            raise ValueError(
                f"Câmera '{old_name}' não encontrada."
            )

        # Usar db fornecido ou criar nova instância
        if db is None:
            from src.core.database import Database
            from src.core.config import app_dir
            db_path = app_dir() / "events.db"
            db = Database(db_path)

        try:
            # Obter contagem antes da migração
            counts_before = self.count_camera_events(old_name, db)

            # Criar backup do banco antes da migração
            backup_path = self._create_backup(db)

            # Atualizar eventos no banco de dados
            event_repo = EventRepository(db)
            total_updated = event_repo.update_camera_name(old_name, new_name)

            # Atualizar configuração da câmera
            camera = self.find_by_name(old_name)
            if camera:
                camera["name"] = new_name
                self.save(camera)
                # Deletar câmera antiga após criar a nova
                self.delete(old_name)

            # Registrar log de auditoria
            self._create_rename_log(old_name, new_name, user, total_updated, db)

            return {
                "success": True,
                "updated": {
                    "events": counts_before["events"],
                    "snapshots": counts_before["snapshots"],
                    "total": total_updated
                },
                "old_name": old_name,
                "new_name": new_name,
                "backup_file": backup_path
            }

        except Exception as e:
            # Se houver erro, tentar rollback do backup
            if backup_path and backup_path.exists():
                try:
                    self._restore_from_backup(db, backup_path)
                except Exception as rollback_error:
                    raise CameraRenameError(
                        f"Falha na renomeação e no rollback: {str(e)}. "
                        f"Erro do rollback: {str(rollback_error)}",
                        old_name=old_name,
                        new_name=new_name,
                        details=str(e)
                    )

            raise CameraRenameError(
                f"Falha ao renomear câmera: {str(e)}",
                old_name=old_name,
                new_name=new_name,
                details=str(e)
            )

    def _create_backup(self, db: Any) -> Path:
        """
        Cria um backup do banco de dados.

        Args:
            db: Instância do Database

        Returns:
            Path: Caminho para o arquivo de backup
        """
        from src.core.config import app_dir
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = app_dir() / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"events_backup_{timestamp}.db"

        # Fechar conexão atual para garantir consistência
        db.conn.commit()

        # Obter caminho do arquivo de banco
        src_path = Path(db.conn.execute("PRAGMA database_list").fetchone()[2])

        # Copiar arquivo
        shutil.copy2(src_path, backup_path)

        return backup_path

    def _restore_from_backup(self, db: Any, backup_path: Path) -> None:
        """
        Restaura banco de dados de um backup.

        Args:
            db: Instância do Database
            backup_path: Caminho para o arquivo de backup
        """
        # Fechar conexão atual
        db.conn.commit()

        # Restaurar do backup
        src_path = db.conn.execute("PRAGMA database_list").fetchone()[2]
        shutil.copy2(backup_path, src_path)

    def _create_rename_log(
        self,
        old_name: str,
        new_name: str,
        user: str,
        records_count: int,
        db: Any
    ) -> None:
        """
        Cria registro de auditoria para operação de renomeação.

        Args:
            old_name: Nome antigo da câmera
            new_name: Novo nome da câmera
            user: Usuário que realizou a operação
            records_count: Número de registros atualizados
            db: Instância do Database
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Verificar se tabela de audit_log existe
        with db.lock:
            cursor = db.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    event_type TEXT,
                    user TEXT,
                    details TEXT
                )
            """)

            # Inserir registro de auditoria
            cursor.execute("""
                INSERT INTO audit_log (ts, event_type, user, details)
                VALUES (?, ?, ?, ?)
            """, (
                timestamp,
                "camera_renamed",
                user,
                f"Renamed '{old_name}' to '{new_name}' ({records_count} records updated)"
            ))

            db.conn.commit()
