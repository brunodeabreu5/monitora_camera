# Banco de dados de eventos
"""
Módulo de persistência de dados para Hikvision Radar Pro V4.2.

Gerencia armazenamento e recuperação de eventos de tráfego detectados
pelas câmeras, incluindo informações de velocidade, placas, imagens e metadados.

Example:
    >>> db = Database(Path("events.db"))
    >>> db.insert_event({
    ...     "camera_name": "Camera 1",
    ...     "plate": "ABC1234",
    ...     "speed": "85 km/h",
    ...     "is_overspeed": True
    ... })
    >>> events = db.filtered_events(plate="ABC")
"""
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from .config import extract_speed_value

# Limite de linhas nas consultas de Histórico e Relatório (evita travamento com muitos eventos)
MAX_EVENTS_QUERY = 1000


class Database:
    """
    Gerenciador de banco de dados SQLite para eventos de tráfego.

    Fornece interface thread-safe para armazenamento e consulta de eventos
    detectados por câmeras Hikvision, incluindo dados de velocidade, placas,
    imagens e metadados.

    Attributes:
        conn: Conexão SQLite com check_same_thread=False para multi-threading
        lock: Lock threading para garantir acesso thread-safe aos dados

    Example:
        >>> db = Database(Path("events_v42.db"))
        >>> events = db.recent_events_with_speed(camera_name="Camera 1")
        >>> db.close()
    """

    def __init__(self, db_path: Path):
        """
        Inicializa banco de dados e cria esquema se necessário.

        Cria tabela 'events' e 'snapshots' com índices para consultas eficientes.
        Garante compatibilidade com versões anteriores através de
        migração automática de colunas.

        Args:
            db_path: Caminho para arquivo do banco de dados SQLite

        Raises:
            sqlite3.Error: Se houver erro ao criar ou abrir o banco
        """
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT,
            ts TEXT,
            plate TEXT,
            speed TEXT,
            speed_value REAL,
            lane TEXT,
            direction TEXT,
            event_type TEXT,
            image_path TEXT,
            xml_path TEXT,
            json_path TEXT,
            raw_xml TEXT,
            applied_speed_limit REAL,
            is_overspeed INTEGER
        )""")
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT,
            ts TEXT,
            image_path TEXT,
            event_id INTEGER,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )""")
        self._ensure_event_columns()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_camera_ts ON events(camera_name, ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_speed_value ON events(speed_value)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_camera_ts ON snapshots(camera_name, ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_event_id ON snapshots(event_id)")
        self.conn.commit()

    def close(self):
        """
        Fecha conexão com o banco de dados.

        Deve ser chamado quando o Database não for mais necessário.
        Após fechado, o objeto não pode mais ser usado.
        """
        with self.lock:
            self.conn.close()

    def _ensure_event_columns(self):
        """
        Garante que colunas necessárias existam na tabela events.

        Adiciona colunas que podem faltar em versões antigas do banco,
        permitindo migração transparente sem perda de dados.

        Colunas verificadas:
            - applied_speed_limit: REAL, limite de velocidade aplicado
            - is_overspeed: INTEGER, flag se velocidade excedeu limite
        """
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(events)").fetchall()}
        if "applied_speed_limit" not in existing:
            self.conn.execute("ALTER TABLE events ADD COLUMN applied_speed_limit REAL")
        if "is_overspeed" not in existing:
            self.conn.execute("ALTER TABLE events ADD COLUMN is_overspeed INTEGER")

    def insert_event(self, data: Dict[str, Any]):
        """
        Insere um novo evento de tráfego no banco de dados.

        Args:
            data: Dicionário com dados do evento. Chaves suportadas:
                - camera_name: Nome da câmera que detectou
                - ts: Timestamp do evento (string)
                - plate: Placa do veículo detectada
                - speed: Velocidade como texto (ex: "85 km/h")
                - lane: Faixa da via
                - direction: Direção do veículo
                - event_type: Tipo de evento
                - image_path: Caminho para imagem capturada
                - xml_path: Caminho para arquivo XML
                - json_path: Caminho para arquivo JSON
                - raw_xml: XML raw da câmera
                - applied_speed_limit: Limite de velocidade aplicado
                - is_overspeed: Boolean indicando excesso de velocidade

        Raises:
            sqlite3.Error: Se houver erro na inserção
            KeyError: Se dados obrigatórios estiverem faltando

        Note:
            speed_value é extraído automaticamente do campo speed
            is_overspeed é convertido para INTEGER (0 ou 1)
        """
        with self.lock:
            self.conn.execute("""
            INSERT INTO events (camera_name, ts, plate, speed, speed_value, lane, direction, event_type, image_path, xml_path, json_path, raw_xml, applied_speed_limit, is_overspeed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("camera_name"), data.get("ts"), data.get("plate"), data.get("speed"),
                extract_speed_value(data.get("speed", "")), data.get("lane"), data.get("direction"),
                data.get("event_type"), data.get("image_path"), data.get("xml_path"),
                data.get("json_path"), data.get("raw_xml"), data.get("applied_speed_limit"),
                1 if data.get("is_overspeed") else 0
            ))
            self.conn.commit()

    def _filtered_events_where(self, camera_name: str, plate: str, date_text: str, min_speed: str, over_limit: Optional[float]) -> Tuple[str, List]:
        """
        Constrói cláusula WHERE e parâmetros para consultas filtradas.

        Args:
            camera_name: Filtra por nome da câmera (string vazia = ignora)
            plate: Filtra por placa (busca parcial, case-insensitive)
            date_text: Filtra por data (busca parcial em timestamp)
            min_speed: Velocidade mínima em km/h
            over_limit: Filtra velocidades acima deste limite

        Returns:
            Tuple[str, List]: (cláusula WHERE iniciando com " WHERE",
                               lista de parâmetros para query)
        """
        query = " WHERE 1=1"
        params = []
        if camera_name:
            query += " AND camera_name = ?"; params.append(camera_name)
        if plate:
            query += " AND upper(plate) LIKE ?"; params.append(f"%{plate.upper()}%")
        if date_text:
            query += " AND ts LIKE ?"; params.append(f"%{date_text}%")
        if min_speed:
            try:
                query += " AND speed_value >= ?"; params.append(float(min_speed))
            except Exception:
                pass
        if over_limit is not None:
            query += " AND speed_value > ?"; params.append(float(over_limit))
        return query, params

    def count_filtered_events(self, camera_name: str = "", plate: str = "", date_text: str = "", min_speed: str = "", over_limit: Optional[float] = None) -> int:
        """
        Conta total de eventos que atendem aos filtros especificados.

        Útil para implementar paginação de resultados.

        Args:
            camera_name: Filtra por nome da câmera
            plate: Filtra por placa (busca parcial)
            date_text: Filtra por data
            min_speed: Velocidade mínima em km/h
            over_limit: Filtra velocidades acima deste limite

        Returns:
            int: Número total de eventos que atendem aos filtros
        """
        with self.lock:
            where, params = self._filtered_events_where(camera_name, plate, date_text, min_speed, over_limit)
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM events" + where, params)
            return cur.fetchone()[0]

    def filtered_events(self, camera_name: str = "", plate: str = "", date_text: str = "", min_speed: str = "", over_limit: Optional[float] = None, limit: Optional[int] = None, offset: int = 0) -> List[Tuple]:
        """
        Retorna eventos filtrados com suporte a paginação.

        Args:
            camera_name: Filtra por nome da câmera
            plate: Filtra por placa (busca parcial)
            date_text: Filtra por data
            min_speed: Velocidade mínima em km/h
            over_limit: Filtra velocidades acima deste limite
            limit: Máximo de eventos a retornar (default: MAX_EVENTS_QUERY)
            offset: Número de eventos a pular (para paginação)

        Returns:
            List[Tuple]: Lista de tuplas com (camera_name, ts, plate, speed,
                         lane, direction, event_type, image_path, json_path)

        Note:
            Usa MAX_EVENTS_QUERY como limite padrão para evitar
            travamentos com grandes volumes de dados
        """
        limit = limit if limit is not None else MAX_EVENTS_QUERY
        with self.lock:
            where, params = self._filtered_events_where(camera_name, plate, date_text, min_speed, over_limit)
            params.append(limit)
            params.append(offset)
            cur = self.conn.cursor()
            cur.execute(
                "SELECT camera_name, ts, plate, speed, lane, direction, event_type, image_path, json_path FROM events"
                + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                params
            )
            return cur.fetchall()

    def recent_events_with_speed(self, camera_name: str = "", date_text: str = "") -> List[Tuple]:
        """
        Retorna eventos recentes com dados completos de velocidade.

        Inclui colunas speed_value, applied_speed_limit e is_overspeed
        que são necessárias para cálculos e exibição na interface.

        Args:
            camera_name: Filtra por nome da câmera (opcional)
            date_text: Filtra por data (busca parcial, opcional)

        Returns:
            List[Tuple]: Lista de tuplas com (camera_name, ts, plate, speed,
                         speed_value, lane, direction, event_type, image_path,
                         json_path, applied_speed_limit, is_overspeed)

        Note:
            Limitado a MAX_EVENTS_QUERY eventos para performance
        """
        with self.lock:
            query = """SELECT camera_name, ts, plate, speed, speed_value, lane, direction, event_type, image_path, json_path, applied_speed_limit, is_overspeed FROM events WHERE 1=1"""
            params = []
            if camera_name:
                query += " AND camera_name = ?"; params.append(camera_name)
            if date_text:
                query += " AND ts LIKE ?"; params.append(f"%{date_text}%")
            query += " ORDER BY id DESC LIMIT ?"
            params.append(MAX_EVENTS_QUERY)
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def count_events(self) -> int:
        """
        Retorna número total de eventos no banco de dados.

        Returns:
            int: Total de eventos armazenados
        """
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def last_event_id(self) -> Optional[int]:
        """
        Retorna ID do último evento inserido.

        Returns:
            Optional[int]: ID do último evento ou None se tabela vazia
        """
        with self.lock:
            row = self.conn.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1").fetchone()
            return row[0] if row else None

    def dashboard_event_speeds(self) -> Dict[str, Any]:
        """
        Retorna dados agregados para o dashboard.

        Calcula estatísticas de eventos incluindo total, eventos de hoje,
        dados de velocidade e última placa detectada.

        Returns:
            Dict[str, Any]: Dicionário com:
                - total: int, número total de eventos
                - today: int, número de eventos hoje
                - rows: List[Tuple], todos os eventos com dados de velocidade
                - last_plate: str, última placa detectada ou "-"
        """
        with self.lock:
            today = datetime.now().strftime("%d/%m/%Y")
            cur = self.conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            today_count = cur.execute("SELECT COUNT(*) FROM events WHERE ts LIKE ?", (f"{today}%",)).fetchone()[0]
            rows = cur.execute("SELECT camera_name, speed_value, applied_speed_limit, is_overspeed FROM events").fetchall()
            last_plate = cur.execute("SELECT plate FROM events ORDER BY id DESC LIMIT 1").fetchone()
            return {"total": total, "today": today_count, "rows": rows, "last_plate": last_plate[0] if last_plate else "-"}
