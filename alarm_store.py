import sqlite3
import json
import os
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "alarms.db")


@dataclass
class AlarmRecord:
    id: int
    trip_id: str
    timestamp: str
    local_time: str
    address: str
    organization: str
    incoming_helicopter: bool
    distance: float
    raw_json: str
    status: str = "active"
    source: str = "production"


class AlarmStore:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT UNIQUE,
                    timestamp TEXT NOT NULL,
                    local_time TEXT NOT NULL,
                    address TEXT NOT NULL DEFAULT '',
                    organization TEXT NOT NULL DEFAULT '',
                    incoming_helicopter INTEGER NOT NULL DEFAULT 0,
                    distance REAL NOT NULL DEFAULT 0,
                    raw_json TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active'
                )
            """)
            conn.commit()
            # Migration for existing DBs without status column
            try:
                conn.execute("ALTER TABLE alarms ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists
            # Migration for source column
            try:
                conn.execute("ALTER TABLE alarms ADD COLUMN source TEXT NOT NULL DEFAULT 'production'")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists
        finally:
            conn.close()

    def insert_alarm(self, payload: dict, raw: str, source: str = "production") -> AlarmRecord | None:
        trip = payload.get("trip", {})
        trip_id = trip.get("id", "")
        if not trip_id:
            trip_id = f"unknown_{datetime.now().timestamp()}"

        # Parse timestamp
        created_at = trip.get("createdAt", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                local_dt = dt.astimezone()
                local_time = local_dt.strftime("%d.%m.%Y %H:%M")
                timestamp = dt.isoformat()
            except Exception:
                local_time = datetime.now().strftime("%d.%m.%Y %H:%M")
                timestamp = datetime.now(timezone.utc).isoformat()
        else:
            local_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            timestamp = datetime.now(timezone.utc).isoformat()

        # Extract address, strip ", Deutschland"
        end_location = trip.get("endLocation", {})
        address = end_location.get("address", "")
        if address.endswith(", Deutschland"):
            address = address[:-len(", Deutschland")]

        organization = trip.get("organization", {}).get("name", "")
        incoming_helicopter = bool(trip.get("incomingHelicopter", False))
        distance = float(trip.get("distance", 0))

        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO alarms
                   (trip_id, timestamp, local_time, address, organization, incoming_helicopter, distance, raw_json, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trip_id, timestamp, local_time, address, organization,
                 int(incoming_helicopter), distance, raw, source),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM alarms WHERE trip_id = ?", (trip_id,)).fetchone()
            if row:
                return self._row_to_record(row)
            return None
        except Exception as e:
            log.error(f"Failed to insert alarm: {e}")
            return None
        finally:
            conn.close()

    def get_all(self, limit: int = 200) -> list[AlarmRecord]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM alarms ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_record(r) for r in rows]
        finally:
            conn.close()

    def count_today(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM alarms WHERE date(local_time) = ? OR timestamp LIKE ?",
                (today, f"{today}%"),
            ).fetchone()
            # Use local_time for date matching - stored as HH:MM:SS so we need timestamp
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM alarms WHERE date(timestamp) = ?",
                (today,),
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def count_this_week(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM alarms WHERE timestamp >= date('now', 'weekday 1', '-7 days')"
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def count_this_month(self) -> int:
        month_start = datetime.now().strftime("%Y-%m-01")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM alarms WHERE timestamp >= ?",
                (month_start,),
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def top_organizations(self, limit: int = 3) -> list[tuple[str, int]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT organization, COUNT(*) as cnt FROM alarms
                   WHERE organization != ''
                   GROUP BY organization ORDER BY cnt DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [(r["organization"], r["cnt"]) for r in rows]
        finally:
            conn.close()

    def update_trip_helicopter(self, trip_id: str, incoming: bool) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "UPDATE alarms SET incoming_helicopter = ? WHERE trip_id = ?",
                (int(incoming), trip_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to update helicopter status: {e}")
            return False
        finally:
            conn.close()

    def update_trip_status(self, trip_id: str, status: str) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "UPDATE alarms SET status = ? WHERE trip_id = ?",
                (status, trip_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to update trip status: {e}")
            return False
        finally:
            conn.close()

    def delete_alarm(self, trip_id: str) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute("DELETE FROM alarms WHERE trip_id = ?", (trip_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Failed to delete alarm: {e}")
            return False
        finally:
            conn.close()

    def clear_all(self):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM alarms")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_record(row) -> AlarmRecord:
        return AlarmRecord(
            id=row["id"],
            trip_id=row["trip_id"],
            timestamp=row["timestamp"],
            local_time=row["local_time"],
            address=row["address"],
            organization=row["organization"],
            incoming_helicopter=bool(row["incoming_helicopter"]),
            distance=row["distance"],
            raw_json=row["raw_json"],
            status=row["status"],
            source=row["source"] if "source" in row.keys() else "production",
        )
