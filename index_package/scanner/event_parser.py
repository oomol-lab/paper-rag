import sqlite3

from typing import Optional, Callable
from .events import EventKind, EventTarget

class Event:
  def __init__(
    self,
    id: int,
    kind: EventKind,
    target: EventTarget,
    scope: str,
    path: str,
    mtime: float,
    on_exit: Optional[Callable[[], None]] = None,
  ):
    self.id: int = id
    self.kind: EventKind = kind
    self.target: EventTarget = target
    self.scope: str = scope
    self.path: str = path
    self.mtime: float = mtime
    self._on_exit: Optional[Callable[[], None]] = on_exit

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is None and self._on_exit is not None:
      self._on_exit()

class EventParser:
  def __init__(self, conn: sqlite3.Connection):
    self._conn: sqlite3.Connection = conn
    self._cursor = self._conn.cursor()

  def parse(self, event_id: int) -> Event:
    self._cursor.execute(
      "SELECT kind, target, path, scope, mtime FROM events WHERE id = ?",
      (event_id,)
    )
    row = self._cursor.fetchone()
    if row is None:
      raise Exception(f"Event not found: {event_id}")

    return Event(
      id=event_id,
      kind=EventKind(row[0]),
      target=EventTarget(row[1]),
      path=row[2],
      scope=row[3],
      mtime=row[4],
      on_exit=lambda: self._remove_event(event_id),
    )

  def close(self):
    self._cursor.close()
    self._conn.close()

  def _remove_event(self, event_id: int):
    self._cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    self._conn.commit()