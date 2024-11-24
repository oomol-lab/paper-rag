from dataclasses import dataclass
from sqlite3_pool import SQLite3Pool
from typing import Optional, Callable
from .events import EventKind, EventTarget

@dataclass
class Event:
  id: int
  kind: EventKind
  target: EventTarget
  scope: str
  path: str
  mtime: float
  _on_exit: Optional[Callable[[], None]] = None

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is None and self._on_exit is not None:
      self._on_exit()

class EventParser:
  def __init__(self, db: SQLite3Pool):
    self._db: SQLite3Pool = db

  def parse(self, event_id: int) -> Event:
    with self._db.connect() as (cursor, _):
      cursor.execute(
        "SELECT kind, target, path, scope, mtime FROM events WHERE id = ?",
        (event_id,)
      )
      row = cursor.fetchone()
      if row is None:
        raise Exception(f"Event not found: {event_id}")

      return Event(
        id=event_id,
        kind=EventKind(row[0]),
        target=EventTarget(row[1]),
        path=row[2],
        scope=row[3],
        mtime=row[4],
        _on_exit=lambda: self._remove_event(event_id),
      )

  def _remove_event(self, event_id: int):
    with self._db.connect() as (cursor, conn):
      cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
      conn.commit()