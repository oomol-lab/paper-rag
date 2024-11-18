import json
import os
import uuid
import sqlite3

from dataclasses import dataclass
from typing import Any, Union, Optional

@dataclass
class Chunk:
  uid: str
  path: str
  meta: Optional[Any]
  _parent_uid: str

@dataclass
class ChunkChildRef:
  parent: Chunk
  uid: str
  path: str

# it's useless now
class ChunkHub:
  def __init__(self, db_path: str):
    self._conn: sqlite3.Connection = self._connect(db_path)
    self._cursor: sqlite3.Cursor = self._conn.cursor()

  def _connect(self, db_path: str) -> sqlite3.Connection:
    is_first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    os.path.getmtime(db_path)

    if is_first_time:
      cursor = conn.cursor()
      cursor.execute("""
        CREATE TABLE chunks (
          uid TEXT PRIMARY KEY,
          parent_uid TEXT,
          path TEXT,
          meta TEXT
        )
      """)
      cursor.execute("""
        CREATE INDEX idx_chunks ON chunks (parent_uid, path)
      """)
      conn.commit()
      cursor.close()

    return conn

  def get(self, uid: str) -> Optional[Chunk]:
    self._cursor.execute(
      "SELECT parent_uid, path, meta FROM chunks WHERE uid = ?",
      (uid,),
    )
    row = self._cursor.fetchone()

    if row is None:
      return None

    parent_uid, path, meta_str = row
    meta: Optional[Any] = None

    if meta_str is not None:
      meta = json.loads(meta_str)

    return Chunk(
      uid=uid,
      meta=meta,
      _parent_uid=empty_str(parent_uid),
      path=empty_str(path),
    )

  def get_parent(self, chunk: Chunk) -> Optional[Chunk]:
    if chunk._parent_uid == "":
      return None
    return self.get(chunk._parent_uid)

  def get_child(self, parent: Chunk, path: str) -> Optional[Chunk]:
    self._cursor.execute(
      "SELECT uid, meta FROM chunks WHERE parent_uid = ? AND path = ?",
      (parent.uid, path),
    )
    row = self._cursor.fetchone()

    if row is None:
      return None

    uid, meta_str = row
    meta: Optional[Any] = None
    if meta_str is not None:
      meta = json.loads(meta_str)
    return Chunk(
      uid=uid,
      path=path,
      meta=meta,
      _parent_uid=parent.uid,
    )

  def get_child_refs(self, parent: Chunk) -> list[ChunkChildRef]:
    self._cursor.execute(
      "SELECT uid, path FROM chunks WHERE parent_uid = ?",
      (parent.uid,),
    )
    rows = self._cursor.fetchall()
    refs: list[ChunkChildRef] = []

    for row in rows:
      uid, path = row
      refs.append(ChunkChildRef(
        parent=parent,
        uid=uid,
        path=empty_str(path),
      ))
    return refs

  def add(self, meta: Optional[Any] = None) -> Chunk:
    return self._create(meta=meta)

  def add_child(
      self, parent: Chunk, path: str,
      meta: Optional[Any] = None) -> Chunk:
    return self._create(parent=parent, path=path, meta=meta)

  def _create(
      self,
      parent: Optional[Chunk] = None,
      path: Optional[str] = None,
      meta: Optional[Any] = None,
  ) -> Chunk:
    uid = str(uuid.uuid4()).replace("-", "")
    parent_uid: Optional[str] = None

    if parent is not None:
      parent_uid = parent.uid

    meta_str: Optional[str] = None
    if meta is not None:
      meta_str = json.dumps(meta)

    self._cursor.execute("INSERT INTO chunks VALUES (?, ?, ?, ?)", (
      uid,
      parent_uid,
      path,
      meta_str,
    ))
    chunk = Chunk(
      uid=uid,
      meta=meta,
      _parent_uid=empty_str(parent_uid),
      path=empty_str(path),
    )
    self._conn.commit()
    return chunk

  def set_meta(self, chunk: Union[str, Chunk], meta: Optional[Any]):
    meta_str: Optional[str] = None
    chunk_uid: str = chunk if isinstance(chunk, str) else chunk.uid

    if meta is not None:
      meta_str = json.dumps(meta)

    self._cursor.execute(
      "UPDATE chunks SET meta = ? WHERE uid = ?",
      (meta_str, chunk_uid),
    )
    self._conn.commit()

    if isinstance(chunk, Chunk):
      chunk.meta = meta

    return meta

  def remove(self, chunk: Union[str, Chunk]):
    chunk_uid: str = chunk if isinstance(chunk, str) else chunk.uid
    try:
      self._cursor.execute("BEGIN TRANSACTION")
      self._cursor.execute("DELETE FROM chunks WHERE uid = ?", (chunk_uid,))
      self._remove_children(chunk_uid)
      self._conn.commit()
    except Exception as e:
      self._conn.rollback()
      raise e

  def _remove_children(self, parent_uid: str):
    self._cursor.execute(
      "SELECT uid FROM chunks WHERE parent_uid = ?",
      (parent_uid,),
    )
    rows = self._cursor.fetchall()
    for row in rows:
      child_uid = row[0]
      self._remove_children(child_uid)

    self._cursor.execute("DELETE FROM chunks WHERE parent_uid = ?", (parent_uid,))

  def close(self):
    self._cursor.close()
    self._conn.close()

def empty_str(s: Optional[str]) -> str:
  if s is None:
    return ""
  else:
    return s