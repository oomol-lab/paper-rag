import os
import sqlite3

from dataclasses import dataclass
from typing import cast, Optional, Generator
from .scope import Scope, ScopeManager
from .events import scan_events, record_added_event, record_updated_event, record_removed_event
from .event_parser import EventTarget, EventParser
from ..utils import assert_continue

@dataclass
class _File:
  scope: str
  path: str
  mtime: float
  children: Optional[list[str]]

  @property
  def is_dir(self) -> bool:
    return self.children is not None

  @property
  def event_target(self) -> EventTarget:
    if self.children is None:
      return EventTarget.File
    else:
      return EventTarget.Directory

class Scanner:
  def __init__(self, db_path: str) -> None:
    self._db_path: str = db_path
    self._conn: sqlite3.Connection = self._connect()
    self._scope_manager: ScopeManager = ScopeManager(self._conn)

  def event_parser(self) -> EventParser:
    return EventParser(self._connect())

  @property
  def scope(self) -> Scope:
    return self._scope_manager

  def _connect(self) -> sqlite3.Connection:
    is_first_time = not os.path.exists(self._db_path)
    conn = sqlite3.connect(self._db_path)

    if is_first_time:
      cursor = conn.cursor()
      try:
        cursor.execute('''
          CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            scope TEXT NOT NULL,
            path TEXT NOT NULL,
            mtime REAL NOT NULL,
            children TEXT
          )
        ''')
        cursor.execute('''
          CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            kind INTEGER NOT NULL,
            target INTEGER NOT NULL,
            path TEXT NOT NULL,
            scope TEXT NOT NULL,
            mtime REAL NOT NULL
          )
        ''')
        cursor.execute('''
          CREATE TABLE scopes (
            name TEXT PRIMARY KEY,
            path TEXT NOT NULL
          )
        ''')
        cursor.execute("""
          CREATE UNIQUE INDEX idx_files ON events (scope, path)
        """)
        cursor.execute("""
          CREATE UNIQUE INDEX idx_events ON events (scope, path, target)
        """)
        conn.commit()

      finally:
        cursor.close()

    return conn

  def close(self):
    self._conn.close()

  @property
  def events_count(self) -> int:
    cursor = self._conn.cursor()
    try:
      cursor.execute("SELECT COUNT(*) FROM events")
      row = cursor.fetchone()
      return row[0]
    finally:
      cursor.close

  def scan(self) -> Generator[int, None, None]:
    cursor = self._conn.cursor()
    try:
      for scope in self._scope_manager.scopes:
        self._scan_scope(self._conn, cursor, scope)
    finally:
      cursor.close()

    return scan_events(self._conn)

  def commit_sources(self, sources: dict[str, str]):
    self._scope_manager.commit_sources(self._conn, sources)

  def _scan_scope(
    self,
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    scope: str,
  ):
    next_relative_paths: list[str] = [os.path.sep]

    while len(next_relative_paths) > 0:
      assert_continue()
      relative_path = next_relative_paths.pop()
      children = self._scan_and_report(conn, cursor, scope, relative_path)
      if children is not None:
        for child in children:
          next_relative_path = os.path.join(relative_path, child)
          next_relative_paths.insert(0, next_relative_path)

  def _scan_and_report(
    self,
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    scope: str,
    relative_path: str
  ) -> Optional[list[str]]:

    scan_path = cast(str, self._scope_manager.scope_path(scope))
    abs_path = os.path.join(scan_path, f".{relative_path}")
    abs_path = os.path.abspath(abs_path)
    old_file = self._select_file(cursor, scope, relative_path)
    new_file: Optional[_File] = None
    file_never_change = False

    if os.path.exists(abs_path):
      is_dir = os.path.isdir(abs_path)
      mtime = os.path.getmtime(abs_path)
      children: Optional[list[str]] = None

      if old_file is not None and \
         old_file.mtime == mtime and \
         is_dir == old_file.is_dir:

        children = old_file.children
        file_never_change = True

      elif is_dir:
        children = os.listdir(abs_path)

      new_file = _File(scope, relative_path, mtime, children)

    elif old_file is None:
      return

    if not file_never_change:
      try:
        cursor.execute("BEGIN TRANSACTION")
        self._commit_file_self_events(cursor, scope, old_file, new_file)
        self._commit_children_events(cursor, scope, old_file, new_file)
        conn.commit()
      except Exception as e:
        conn.rollback()
        raise e

    if new_file is None:
      return None

    if new_file.children is None:
      return None

    return new_file.children

  def _commit_file_self_events(
    self,
    cursor: sqlite3.Cursor,
    scope: str,
    old_file: Optional[_File],
    new_file: Optional[_File]
  ):
    if new_file is not None:
      new_path = new_file.path
      new_mtime = new_file.mtime
      new_children, new_target = self._file_inserted_children_and_target(new_file)

      if old_file is None:
        cursor.execute(
          "INSERT INTO files (scope, path, mtime, children) VALUES (?, ?, ?, ?)",
          (scope, new_path, new_mtime, new_children),
        )
        record_added_event(cursor, new_target, new_path, scope, new_mtime)

      else:
        cursor.execute(
          "UPDATE files SET mtime = ?, children = ? WHERE scope = ? AND path = ?",
          (new_mtime, new_children, scope, new_path),
        )
        if old_file.is_dir == new_file.is_dir:
          record_updated_event(cursor, new_target, new_path, scope, new_mtime)
        else:
          old_path = old_file.path
          old_mtime = old_file.mtime
          old_target = old_file.event_target
          record_removed_event(cursor, old_target, old_path, scope, old_mtime)
          record_added_event(cursor, new_target, new_path, scope, new_mtime)

    elif old_file is not None:
      old_path = old_file.path
      old_mtime = old_file.mtime
      old_target = old_file.event_target

      cursor.execute("DELETE FROM files WHERE scope = ? AND path = ?", (scope, old_path))
      record_removed_event(cursor, old_target, old_path, scope, old_mtime)

      if old_file.is_dir:
        self._handle_removed_folder(cursor, old_file)

  def _commit_children_events(
    self,
    cursor: sqlite3.Cursor,
    scope: str,
    old_file: Optional[_File],
    new_file: Optional[_File]):

    if old_file is None or not old_file.is_dir:
      return

    to_remove = set(cast(list[str], old_file.children))

    if new_file is not None and new_file.children is not None:
      for child in new_file.children:
        if child in to_remove:
          to_remove.remove(child)

    for removed_file in to_remove:
      child_path = os.path.join(old_file.path, removed_file)
      child_file = self._select_file(cursor, scope, child_path)

      if child_file is None:
        continue

      if child_file.is_dir:
        self._handle_removed_folder(cursor, child_file)

      cursor.execute("DELETE FROM files WHERE scope = ? AND path = ?", (scope, child_file.path))
      record_removed_event(cursor, child_file.event_target, child_path, scope, child_file.mtime)

  def _file_inserted_children_and_target(self, file: _File) -> tuple[Optional[str], EventTarget]:
    children: Optional[str] = None
    target: EventTarget = EventTarget.File

    if file.children is not None:
      # "/" is disabled in unix & windows file system, so it's safe to use it as separator
      children = "/".join(file.children)
      target = EventTarget.Directory

    return children, target

  def _handle_removed_folder(self, cursor: sqlite3.Cursor, folder: _File):
    assert folder.children is not None

    for child in folder.children:
      path = os.path.join(folder.path, child)
      file = self._select_file(cursor, folder.scope, path)
      if file is None:
        continue

      if file.is_dir:
        self._handle_removed_folder(cursor, file)

      cursor.execute("DELETE FROM files WHERE id = ?", (file.path,))
      record_removed_event(cursor, file.event_target, file.path, file.scope, file.mtime)

  def _select_file(self, cursor: sqlite3.Cursor, scope: str, relative_path: str) -> Optional[_File]:
    cursor.execute("SELECT mtime, children FROM files WHERE scope = ? AND path = ?", (scope, relative_path,))
    row = cursor.fetchone()
    if row is None:
      return None
    mtime, children_str = row
    children: Optional[list[str]] = None

    if children_str is not None:
      # "/" is disabled in unix & windows file system, so it's safe to use it as separator
      children = children_str.split("/")

    return _File(scope, relative_path, mtime, children)