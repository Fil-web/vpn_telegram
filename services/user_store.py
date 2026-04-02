import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram.types import User

from loader import config


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StoredUser:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    was_subscribed: bool
    is_banned_forever: bool
    created_at: str
    updated_at: str
    banned_reason: str | None
    xui_email: str | None
    xui_client_id: str | None
    xui_sub_id: str | None
    xui_inbound_id: int | None


class UserStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    was_subscribed INTEGER NOT NULL DEFAULT 0,
                    is_banned_forever INTEGER NOT NULL DEFAULT 0,
                    banned_reason TEXT,
                    xui_email TEXT,
                    xui_client_id TEXT,
                    xui_sub_id TEXT,
                    xui_inbound_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "users", "xui_email", "TEXT")
            self._ensure_column(conn, "users", "xui_client_id", "TEXT")
            self._ensure_column(conn, "users", "xui_sub_id", "TEXT")
            self._ensure_column(conn, "users", "xui_inbound_id", "INTEGER")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def upsert_user(self, user: User) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    telegram_id, username, first_name, last_name, language_code,
                    was_subscribed, is_banned_forever, banned_reason,
                    xui_email, xui_client_id, xui_sub_id, xui_inbound_id,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 0, 0, NULL, NULL, NULL, NULL, NULL, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    language_code=excluded.language_code,
                    updated_at=excluded.updated_at
                """,
                (
                    user.id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.language_code,
                    now,
                    now,
                ),
            )

    def get_user(self, telegram_id: int) -> StoredUser | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        if not row:
            return None
        return StoredUser(
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            language_code=row["language_code"],
            was_subscribed=bool(row["was_subscribed"]),
            is_banned_forever=bool(row["is_banned_forever"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            banned_reason=row["banned_reason"],
            xui_email=row["xui_email"],
            xui_client_id=row["xui_client_id"],
            xui_sub_id=row["xui_sub_id"],
            xui_inbound_id=row["xui_inbound_id"],
        )

    def mark_subscribed(self, telegram_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET was_subscribed = 1, updated_at = ?
                WHERE telegram_id = ?
                """,
                (_utc_now(), telegram_id),
            )

    def ban_forever(self, telegram_id: int, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_banned_forever = 1,
                    banned_reason = ?,
                    updated_at = ?
                WHERE telegram_id = ?
                """,
                (reason, _utc_now(), telegram_id),
            )

    def unban(self, telegram_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_banned_forever = 0,
                    banned_reason = NULL,
                    updated_at = ?
                WHERE telegram_id = ?
                """,
                (_utc_now(), telegram_id),
            )

    def set_xui_mapping(
        self,
        telegram_id: int,
        *,
        email: str,
        client_id: str,
        sub_id: str,
        inbound_id: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET xui_email = ?,
                    xui_client_id = ?,
                    xui_sub_id = ?,
                    xui_inbound_id = ?,
                    updated_at = ?
                WHERE telegram_id = ?
                """,
                (email, client_id, sub_id, inbound_id, _utc_now(), telegram_id),
            )

    def list_users(self) -> list[StoredUser]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY updated_at DESC"
            ).fetchall()
        return [self.get_user(int(row["telegram_id"])) for row in rows if row]

    def list_banned(self) -> list[StoredUser]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE is_banned_forever = 1 ORDER BY updated_at DESC"
            ).fetchall()
        return [self.get_user(int(row["telegram_id"])) for row in rows if row]


user_store = UserStore(config.database.path)
