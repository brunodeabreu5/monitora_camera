# Event Repository (FASE 3.1 - Repository Pattern)
"""
Repository para operações de banco de dados relacionadas a eventos.

Encapsula toda a lógica de acesso a dados para eventos, fornecendo
uma interface limpa para a camada de negócio.
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.core.database import Database
from src.core.config import extract_speed_value


class EventRepository:
    """
    Repository para acesso e manipulação de eventos no banco de dados.

    Fornece métodos para CRUD de eventos e consultas especializadas,
    abstraindo a complexidade do SQL e do banco SQLite.

    Attributes:
        db: Instância do Database para acesso aos dados

    Example:
        >>> repo = EventRepository(database)
        >>> repo.insert({
        ...     "camera_name": "Camera 1",
        ...     "plate": "ABC1234",
        ...     "speed": "85 km/h",
        ...     "is_overspeed": True
        ... })
        >>> events = repo.find_recent_by_camera("Camera 1", limit=10)
    """

    def __init__(self, db: Database):
        """
        Inicializa repository com conexão de banco de dados.

        Args:
            db: Instância de Database para acesso aos dados
        """
        self.db = db

    def insert(self, data: Dict[str, Any]) -> int:
        """
        Insere um novo evento no banco de dados.

        Args:
            data: Dicionário com dados do evento. Suporta as mesmas chaves
                  de Database.insert_event()

        Returns:
            int: ID do evento inserido

        Raises:
            sqlite3.Error: Se houver erro na inserção
        """
        with self.db.lock:
            self.db.conn.execute("""
            INSERT INTO events (camera_name, ts, plate, speed, speed_value,
                              lane, direction, event_type, image_path,
                              xml_path, json_path, raw_xml,
                              applied_speed_limit, is_overspeed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("camera_name"),
                data.get("ts"),
                data.get("plate"),
                data.get("speed"),
                extract_speed_value(data.get("speed", "")),
                data.get("lane"),
                data.get("direction"),
                data.get("event_type"),
                data.get("image_path"),
                data.get("xml_path"),
                data.get("json_path"),
                data.get("raw_xml"),
                data.get("applied_speed_limit"),
                1 if data.get("is_overspeed") else 0
            ))
            self.db.conn.commit()
            # Retornar ID do último registro inserido
            cursor = self.db.conn.execute("SELECT last_insert_rowid()")
            return cursor.fetchone()[0]

    def find_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca evento por ID.

        Args:
            event_id: ID do evento

        Returns:
            Optional[Dict]: Dicionário com dados do evento ou None se não encontrado
        """
        with self.db.lock:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT id, camera_name, ts, plate, speed, speed_value,
                       lane, direction, event_type, image_path,
                       xml_path, json_path, raw_xml,
                       applied_speed_limit, is_overspeed
                FROM events
                WHERE id = ?
            """, (event_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(cursor, row)
            return None

    def find_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Busca todos os eventos com paginação.

        Args:
            limit: Máximo de registros a retornar (None = sem limite)
            offset: Número de registros a pular

        Returns:
            List[Dict]: Lista de eventos
        """
        with self.db.lock:
            cursor = self.db.conn.cursor()
            if limit is not None:
                cursor.execute("""
                    SELECT id, camera_name, ts, plate, speed, speed_value,
                           lane, direction, event_type, image_path,
                           xml_path, json_path, applied_speed_limit, is_overspeed
                    FROM events
                    ORDER BY id DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            else:
                cursor.execute("""
                    SELECT id, camera_name, ts, plate, speed, speed_value,
                           lane, direction, event_type, image_path,
                           xml_path, json_path, applied_speed_limit, is_overspeed
                    FROM events
                    ORDER BY id DESC
                """)
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def find_recent_by_camera(
        self,
        camera_name: str,
        date_text: str = "",
        limit: int = 1000
    ) -> List[Tuple]:
        """
        Busca eventos recentes de uma câmera específica.

        Inclui dados completos de velocidade para cálculos e exibição.

        Args:
            camera_name: Nome da câmera
            date_text: Filtro de data (opcional, busca parcial)
            limit: Máximo de eventos a retornar

        Returns:
            List[Tuple]: Lista de tuplas com dados completos do evento
        """
        with self.db.lock:
            query = """
                SELECT camera_name, ts, plate, speed, speed_value,
                       lane, direction, event_type, image_path,
                       json_path, applied_speed_limit, is_overspeed
                FROM events WHERE 1=1
            """
            params = []

            if camera_name:
                query += " AND camera_name = ?"
                params.append(camera_name)

            if date_text:
                query += " AND ts LIKE ?"
                params.append(f"%{date_text}%")

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor = self.db.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def find_filtered(
        self,
        camera_name: str = "",
        plate: str = "",
        date_text: str = "",
        min_speed: str = "",
        over_limit: Optional[float] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Tuple]:
        """
        Busca eventos com filtros múltiplos e paginação.

        Args:
            camera_name: Filtra por nome da câmera
            plate: Filtra por placa (busca parcial, case-insensitive)
            date_text: Filtra por data (busca parcial)
            min_speed: Velocidade mínima em km/h
            over_limit: Filtra velocidades acima deste limite
            limit: Máximo de eventos a retornar
            offset: Número de eventos a pular (paginação)

        Returns:
            List[Tuple]: Lista de tuplas com (camera_name, ts, plate, speed,
                         lane, direction, event_type, image_path, json_path)
        """
        from src.core.database import MAX_EVENTS_QUERY

        limit = limit if limit is not None else MAX_EVENTS_QUERY

        where, params = self._build_where_clause(
            camera_name, plate, date_text, min_speed, over_limit
        )

        params.extend([limit, offset])

        with self.db.lock:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT camera_name, ts, plate, speed, lane, direction,
                       event_type, image_path, json_path
                FROM events
            """ + where + " ORDER BY id DESC LIMIT ? OFFSET ?", params)
            return cursor.fetchall()

    def count_filtered(
        self,
        camera_name: str = "",
        plate: str = "",
        date_text: str = "",
        min_speed: str = "",
        over_limit: Optional[float] = None
    ) -> int:
        """
        Conta total de eventos que atendem aos filtros.

        Útil para implementar paginação.

        Args:
            camera_name: Filtra por nome da câmera
            plate: Filtra por placa (busca parcial)
            date_text: Filtra por data
            min_speed: Velocidade mínima em km/h
            over_limit: Filtra velocidades acima deste limite

        Returns:
            int: Número total de eventos que atendem aos filtros
        """
        where, params = self._build_where_clause(
            camera_name, plate, date_text, min_speed, over_limit
        )

        with self.db.lock:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events" + where, params)
            return cursor.fetchone()[0]

    def find_overspeed_events(
        self,
        camera_name: str = "",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Busca eventos de excesso de velocidade.

        Args:
            camera_name: Filtra por câmera (opcional)
            limit: Máximo de eventos a retornar

        Returns:
            List[Dict]: Lista de eventos com is_overspeed=True
        """
        with self.db.lock:
            cursor = self.db.conn.cursor()
            if camera_name:
                cursor.execute("""
                    SELECT id, camera_name, ts, plate, speed, speed_value,
                           lane, direction, event_type, image_path,
                           applied_speed_limit, is_overspeed
                    FROM events
                    WHERE camera_name = ? AND is_overspeed = 1
                    ORDER BY id DESC
                    LIMIT ?
                """, (camera_name, limit))
            else:
                cursor.execute("""
                    SELECT id, camera_name, ts, plate, speed, speed_value,
                           lane, direction, event_type, image_path,
                           applied_speed_limit, is_overspeed
                    FROM events
                    WHERE is_overspeed = 1
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))

            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas agregadas para o dashboard.

        Calcula total de eventos, eventos de hoje, dados de velocidade
        e última placa detectada.

        Returns:
            Dict[str, Any]: Dicionário com:
                - total: int, total de eventos
                - today: int, eventos de hoje
                - rows: List[Tuple], eventos com dados de velocidade
                - last_plate: str, última placa detectada
        """
        with self.db.lock:
            today = datetime.now().strftime("%d/%m/%Y")
            cursor = self.db.conn.cursor()

            total = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            today_count = cursor.execute(
                "SELECT COUNT(*) FROM events WHERE ts LIKE ?",
                (f"{today}%",)
            ).fetchone()[0]

            rows = cursor.execute("""
                SELECT camera_name, speed_value, applied_speed_limit, is_overspeed
                FROM events
            """).fetchall()

            last_plate_row = cursor.execute(
                "SELECT plate FROM events ORDER BY id DESC LIMIT 1"
            ).fetchone()

            return {
                "total": total,
                "today": today_count,
                "rows": rows,
                "last_plate": last_plate_row[0] if last_plate_row else "-"
            }

    def count_all(self) -> int:
        """
        Retorna número total de eventos no banco.

        Returns:
            int: Total de eventos armazenados
        """
        with self.db.lock:
            return self.db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def get_last_id(self) -> Optional[int]:
        """
        Retorna ID do último evento inserido.

        Returns:
            Optional[int]: ID do último evento ou None se vazio
        """
        with self.db.lock:
            row = self.db.conn.execute(
                "SELECT id FROM events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return row[0] if row else None

    def delete_by_id(self, event_id: int) -> bool:
        """
        Deleta um evento por ID.

        Args:
            event_id: ID do evento a deletar

        Returns:
            bool: True se deletou com sucesso, False se não encontrou
        """
        with self.db.lock:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.db.conn.commit()
            return cursor.rowcount > 0

    def delete_old_events(self, days: int) -> int:
        """
        Deleta eventos mais antigos que N dias.

        Útil para manutenção periódica do banco de dados.

        Args:
            days: Número de dias a manter (eventos mais antigos são deletados)

        Returns:
            int: Número de eventos deletados
        """
        with self.db.lock:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                DELETE FROM events
                WHERE date(ts) < date('now', '-' || ? || ' days')
            """, (days,))
            self.db.conn.commit()
            return cursor.rowcount

    def _build_where_clause(
        self,
        camera_name: str,
        plate: str,
        date_text: str,
        min_speed: str,
        over_limit: Optional[float]
    ) -> Tuple[str, List]:
        """
        Constrói cláusula WHERE e parâmetros para consultas filtradas.

        Args:
            camera_name: Filtra por nome da câmera
            plate: Filtra por placa
            date_text: Filtra por data
            min_speed: Velocidade mínima
            over_limit: Velocidade acima do limite

        Returns:
            Tuple[str, List]: (cláusula WHERE iniciando com " WHERE",
                               lista de parâmetros)
        """
        query = " WHERE 1=1"
        params = []

        if camera_name:
            query += " AND camera_name = ?"
            params.append(camera_name)

        if plate:
            query += " AND upper(plate) LIKE ?"
            params.append(f"%{plate.upper()}%")

        if date_text:
            query += " AND ts LIKE ?"
            params.append(f"%{date_text}%")

        if min_speed:
            try:
                query += " AND speed_value >= ?"
                params.append(float(min_speed))
            except (ValueError, TypeError):
                pass

        if over_limit is not None:
            query += " AND speed_value > ?"
            params.append(float(over_limit))

        return query, params

    def _row_to_dict(self, cursor, row: Tuple) -> Dict[str, Any]:
        """
        Converte uma linha do banco em dicionário.

        Args:
            cursor: Cursor do banco de dados
            row: Tupla com valores da linha

        Returns:
            Dict[str, Any]: Dicionário com nomes das colunas como chaves
        """
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def update_camera_name(self, old_name: str, new_name: str) -> int:
        """
        Atualiza o nome da câmera em todos os registros históricos.

        Atualiza as tabelas 'events' e 'snapshots' para manter a integridade
        referencial quando uma câmera é renomeada.

        Args:
            old_name: Nome atual da câmera
            new_name: Novo nome da câmera

        Returns:
            int: Número total de registros atualizados

        Raises:
            sqlite3.Error: Se houver erro na atualização
        """
        total_updated = 0

        with self.db.lock:
            cursor = self.db.conn.cursor()

            # Atualizar tabela events
            cursor.execute(
                "UPDATE events SET camera_name = ? WHERE camera_name = ?",
                (new_name, old_name)
            )
            total_updated += cursor.rowcount

            # Atualizar tabela snapshots
            cursor.execute(
                "UPDATE snapshots SET camera_name = ? WHERE camera_name = ?",
                (new_name, old_name)
            )
            total_updated += cursor.rowcount

            self.db.conn.commit()

        return total_updated
