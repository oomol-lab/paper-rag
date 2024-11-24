from __future__ import annotations
import sqlite3
import threading

from typing import Optional
from .format import get_format
from .session import get_thread_pool, SQLite3ConnectionSession


_LOCK = threading.Lock()

class SQLite3Pool:
  def __init__(self, format_name: str, path: str) -> None:
    global _LOCK
    with _LOCK:
      get_format(format_name).create_tables(path)
    self._format_name: str = format_name
    self._path: str = path

  def assert_format(self, format_name) -> SQLite3Pool:
    if format_name != self._format_name:
      raise ValueError(f"Expected format name {self._format_name}, but got {format_name}")
    return self

  def connect(self) -> SQLite3ConnectionSession:
    pool = get_thread_pool()
    conn: Optional[sqlite3.Connection] = None

    if pool is not None:
      conn = pool.get(self._format_name)

    if conn is None:
      conn = sqlite3.connect(self._path)

    return SQLite3ConnectionSession(
      conn,
      self._send_back,
    )

  def _send_back(self, conn: sqlite3.Connection) -> None:
    pool = get_thread_pool()
    if pool is not None:
      pool.send_back(self._format_name, conn)
    else:
      conn.close()

  @property
  def path(self) -> str:
    return self._path

  @property
  def table_names(self) -> list[str]:
    with self.connect() as (cursor, conn):
      table_names: list[str] = []
      cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
      tables = cursor.fetchall()
      for table in tables:
        table_names.append(table[0])
      return table_names
