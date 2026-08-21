"""
Database Connection Manager for SQLite
Provides thread-safe connections with foreign keys and WAL mode enabled.
"""

import os
import sqlite3
from typing import Optional, Generator
from contextlib import contextmanager

DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "attendance_system.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


class DatabaseManager:
    """Manages SQLite database connections and schema initialization."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Creates and returns a new configured SQLite connection."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        
        # Configure PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for transactional database operations."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self, schema_file: Optional[str] = None) -> None:
        """Initializes the database schema using schema.sql."""
        target_schema = schema_file or SCHEMA_PATH
        with open(target_schema, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        with self.connection() as conn:
            conn.executescript(ddl_script)


# Singleton instance for standard use
db_manager = DatabaseManager()


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Utility function to obtain a configured database connection."""
    if db_path:
        return DatabaseManager(db_path).get_connection()
    return db_manager.get_connection()


@contextmanager
def get_db_context(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager utility for transactional operations."""
    mgr = DatabaseManager(db_path) if db_path else db_manager
    with mgr.connection() as conn:
        yield conn
