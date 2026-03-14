# Banco de dados de eventos
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from .config import extract_speed_value


class Database:
    def __init__(self, db_path: Path):
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
        self._ensure_event_columns()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_camera_ts ON events(camera_name, ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_speed_value ON events(speed_value)")
        self.conn.commit()

    def close(self):
        with self.lock:
            self.conn.close()

    def _ensure_event_columns(self):
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(events)").fetchall()}
        if "applied_speed_limit" not in existing:
            self.conn.execute("ALTER TABLE events ADD COLUMN applied_speed_limit REAL")
        if "is_overspeed" not in existing:
            self.conn.execute("ALTER TABLE events ADD COLUMN is_overspeed INTEGER")

    def insert_event(self, data: dict):
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

    def filtered_events(self, camera_name="", plate="", date_text="", min_speed="", over_limit=None):
        with self.lock:
            query = """SELECT camera_name, ts, plate, speed, lane, direction, event_type, image_path, json_path FROM events WHERE 1=1"""
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
            query += " ORDER BY id DESC LIMIT 1000"
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def recent_events_with_speed(self, camera_name="", date_text=""):
        with self.lock:
            query = """SELECT camera_name, ts, plate, speed, speed_value, lane, direction, event_type, image_path, json_path, applied_speed_limit, is_overspeed FROM events WHERE 1=1"""
            params = []
            if camera_name:
                query += " AND camera_name = ?"; params.append(camera_name)
            if date_text:
                query += " AND ts LIKE ?"; params.append(f"%{date_text}%")
            query += " ORDER BY id DESC LIMIT 1000"
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def count_events(self) -> int:
        """Retorna o número total de eventos no banco (para verificação)."""
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def last_event_id(self) -> int | None:
        """Retorna o id do último evento inserido (None se tabela vazia)."""
        with self.lock:
            row = self.conn.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1").fetchone()
            return row[0] if row else None

    def dashboard_event_speeds(self):
        with self.lock:
            today = datetime.now().strftime("%Y-%m-%d")
            cur = self.conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            today_count = cur.execute("SELECT COUNT(*) FROM events WHERE ts LIKE ?", (f"{today}%",)).fetchone()[0]
            rows = cur.execute("SELECT camera_name, speed_value, applied_speed_limit, is_overspeed FROM events").fetchall()
            last_plate = cur.execute("SELECT plate FROM events ORDER BY id DESC LIMIT 1").fetchone()
            return {"total": total, "today": today_count, "rows": rows, "last_plate": last_plate[0] if last_plate else "-"}
