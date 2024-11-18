from __future__ import annotations

import os
import io
import sqlite3

from typing import Optional

from .fts5_db import FTS5DB
from .vector_db import VectorDB
from .index_db import IndexDB
from .types import IndexNode, PageRelativeToPDF
from ..parser import PdfParser, PdfMetadata, PdfPage
from ..scanner import Scope, Event, EventKind, EventTarget
from ..segmentation import Segment, Segmentation
from ..progress import Progress
from ..utils import hash_sha512, ensure_parent_dir, is_empty_string, assert_continue, InterruptException

class Index:
  def __init__(
    self,
    scope: Scope,
    index_dir_path: str,
    pdf_parser: PdfParser,
    segmentation: Segmentation,
    fts5_db: FTS5DB,
    vector_db: VectorDB,
  ):
    self._scope: Scope = scope
    self._pdf_parser: PdfParser = pdf_parser
    self._segmentation: Segmentation = segmentation
    self._index_db: IndexDB = IndexDB(fts5_db, vector_db)
    self._conn: sqlite3.Connection = self._connect(
      ensure_parent_dir(os.path.join(index_dir_path, "index.sqlite3"))
    )

  def _connect(self, db_path: str) -> sqlite3.Connection:
    is_first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    os.path.getmtime(db_path)

    if is_first_time:
      cursor = conn.cursor()
      try:
        cursor.execute("""
          CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            scope TEXT NOT NULL,
            path TEXT NOT NULL,
            hash TEXT NOT NULL
          )
        """)
        cursor.execute("""
          CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            pdf_hash TEXT NOT NULL,
            page_index INTEGER NOT NULL,
            hash TEXT NOT NULL
          )
        """)
        cursor.execute("""
          CREATE INDEX idx_files ON files (hash)
        """)
        cursor.execute("""
          CREATE INDEX idx_pages ON pages (hash)
        """)
        cursor.execute("""
          CREATE INDEX idx_parent_pages ON pages (pdf_hash, page_index)
        """)
        conn.commit()

      finally:
        cursor.close()

    return conn

  def close(self):
    self._index_db.close()
    self._conn.close()

  def get_paths(self, file_hash: str) -> list[str]:
    cursor = self._conn.cursor()
    try:
      cursor.execute("SELECT scope, path FROM files WHERE hash = ?", (file_hash,))
      paths: list[str] = []

      for row in cursor.fetchall():
        scope, path = row
        scope_path = self._get_abs_path(scope, path)
        if scope_path is not None:
          paths.append(scope_path)
      return paths

    finally:
      cursor.close()

  def get_page_relative_to_pdf(self, page_hash: str) -> list[PageRelativeToPDF]:
    cursor = self._conn.cursor()
    cursor.execute("SELECT pdf_hash, page_index FROM pages WHERE hash = ?", (page_hash,))
    page_infos: list[tuple[str, int]] = []
    pages: list[PageRelativeToPDF] = []

    for row in cursor.fetchall():
      pdf_hash, page_index = row
      page_infos.append((pdf_hash, page_index))

    for pdf_hash, page_index in page_infos:
      cursor.execute("SELECT scope, path FROM files WHERE hash = ?", (pdf_hash,))
      for row in cursor.fetchall():
        scope, path = row
        scope_path = self._get_abs_path(scope, path)
        if scope_path is not None:
          pages.append(PageRelativeToPDF(
            pdf_hash=pdf_hash,
            pdf_path=scope_path,
            page_index=page_index,
          ))

    return pages

  def _get_abs_path(self, scope: str, path: str) -> Optional[str]:
    scope_path = self._scope.scope_path(scope)
    if scope_path is None:
      return None
    path = os.path.join(scope_path, f".{path}")
    path = os.path.abspath(path)
    return path

  def query(
    self,
    query_text: str,
    results_limit: Optional[int] = None,
    to_keywords: bool = True) -> tuple[list[IndexNode], list[str]]:

    if results_limit is None:
      results_limit = 10

    if to_keywords:
      keywords = self._segmentation.to_keywords(query_text)
      query_text = " ".join(keywords)
    else:
      keywords = [query_text]

    if is_empty_string(query_text):
      query_nodes = []
    else:
      query_nodes = self._index_db.query(query_text, results_limit)

    return query_nodes, keywords

  def handle_event(self, event: Event, progress: Optional[Progress] = None):
    path = self._filter_and_get_abspath(event)
    if path is None:
      return

    cursor = self._conn.cursor()
    try:
      cursor.execute("BEGIN TRANSACTION")
      new_hash, origin_id_hash = self._update_file_with_event(cursor, path, event)

      # process that commit new pages is breakable.
      # we need to commit added records of index first, so we can rollback the transaction.
      # if we commit deleted records of index, we can't rollback the transaction.
      if new_hash is not None:
        cursor.execute("SELECT COUNT(*) FROM files WHERE hash = ?", (new_hash,))
        num_rows = cursor.fetchone()[0]
        if num_rows == 1:
          self._handle_found_pdf_hash(cursor, new_hash, path, progress)

      # process that commit deleted pages is not breakable.
      if origin_id_hash is not None:
        _, origin_hash = origin_id_hash
        cursor.execute("SELECT * FROM files WHERE hash = ? LIMIT 1", (origin_hash,))
        if cursor.fetchone() is None:
          self._handle_lost_pdf_hash(cursor, origin_hash)

      self._conn.commit()
      cursor.close()

    except Exception as e:
      self._conn.rollback()
      raise e

    finally:
      cursor.close()

  def _filter_and_get_abspath(self, event: Event) -> Optional[str]:
    if event.target == EventTarget.Directory:
      return

    scope_path = self._scope.scope_path(event.scope)
    if scope_path is None:
      return

    _, ext_name = os.path.splitext(event.path)
    if ext_name.lower() != ".pdf":
      return

    path = os.path.join(scope_path, f".{event.path}")
    path = os.path.abspath(path)

    return path

  def _update_file_with_event(self, cursor: sqlite3.Cursor, path: str, event: Event) -> tuple[Optional[str], Optional[tuple[int, str]]]:
    cursor.execute("SELECT id, hash FROM files WHERE scope = ? AND path = ?", (event.scope, event.path,))
    row = cursor.fetchone()
    new_hash: Optional[str] = None
    origin_id_hash: Optional[tuple[int, str]] = None
    did_update = False

    if row is not None:
      id, hash = row
      origin_id_hash = (id, hash)

    if event.kind != EventKind.Removed:
      new_hash = hash_sha512(path)
      if origin_id_hash is None:
        cursor.execute(
          "INSERT INTO files (type, scope, path, hash) VALUES (?, ?, ?, ?)",
          ("pdf", event.scope, event.path, new_hash),
        )
        did_update = True
      else:
        origin_id, origin_hash = origin_id_hash
        if new_hash != origin_hash:
          cursor.execute("UPDATE files SET hash = ? WHERE id = ?", (new_hash, origin_id,))
          did_update = True

    elif origin_id_hash is not None:
      origin_id, _ = origin_id_hash
      cursor.execute("DELETE FROM files WHERE id = ?", (origin_id,))
      did_update = True

    if not did_update:
      return None, None

    return new_hash, origin_id_hash

  def _handle_found_pdf_hash(self, cursor: sqlite3.Cursor, hash: str, path: str, progress: Optional[Progress]):
    pdf = self._pdf_parser.pdf(hash, path, progress)
    for page in pdf.pages:
      cursor.execute(
        "INSERT INTO pages (pdf_hash, page_index, hash) VALUES (?, ?, ?)",
        (hash, page.index, page.hash),
      )
    index_context = _IndexContext(self._segmentation, self._index_db)
    index_context.save(hash, "pdf", self._pdf_metadata_to_document(pdf.metadata))

    try:
      for page in pdf.pages:
        cursor.execute("SELECT COUNT(*) FROM pages WHERE hash = ?", (page.hash,))
        num_rows = cursor.fetchone()[0]
        if num_rows == 1:
          self._save_page_content_into_index(index_context, page)
          assert_continue()

        if progress is not None:
          progress.on_complete_index_pdf_page(page.index, len(pdf.pages))

    except InterruptException as e:
      index_context.rollback()
      raise e

  def _handle_lost_pdf_hash(self, cursor: sqlite3.Cursor, hash: str):
    cursor.execute(
      "SELECT hash FROM pages WHERE pdf_hash = ? ORDER BY page_index", (hash,),
    )
    page_hashes: list[str] = []
    for row in cursor.fetchall():
      page_hashes.append(row[0])

    cursor.execute("DELETE FROM pages WHERE pdf_hash = ?", (hash,))
    self._index_db.remove(hash)

    for page_hash in page_hashes:
      cursor.execute("SELECT * FROM pages WHERE hash = ? LIMIT 1", (page_hash,))
      if cursor.fetchone() is None:
        page = self._pdf_parser.page(page_hash)
        if page is not None:
          for index, anno in enumerate(page.annotations):
            if anno.content is not None:
              self._index_db.remove(f"{page.hash}/anno/{index}/content")
            if anno.extracted_text is not None:
              self._index_db.remove(f"{page.hash}/anno/{index}/extracted")
          self._index_db.remove(page.hash)

    self._pdf_parser.fire_file_removed(hash)

  def _pdf_metadata_to_document(self, metadata: PdfMetadata) -> str:
    buffer = io.StringIO()
    if metadata.author is not None:
      buffer.write(f"Author: {metadata.author}\n")
    if metadata.modified_at is not None:
      buffer.write(f"Modified At: {metadata.modified_at}\n")
    if metadata.producer is not None:
      buffer.write(f"Producer: {metadata.producer}\n")
    return buffer.getvalue()

  def _save_page_content_into_index(self, index_context: _IndexContext, page: PdfPage):
    index_context.save(
      id=page.hash,
      type="pdf.page",
      text=page.snapshot,
    )
    for index, annotation in enumerate(page.annotations):
      if annotation.content is not None:
        index_context.save(
          id=f"{page.hash}/anno/{index}/content",
          type="pdf.page.anno.content",
          text=annotation.content,
        )
      if annotation.extracted_text is not None:
        index_context.save(
          id=f"{page.hash}/anno/{index}/extracted",
          type="pdf.page.anno.extracted",
          text=annotation.extracted_text,
        )

class _IndexContext:
  def __init__(self, segmentation: Segmentation, index_db: IndexDB):
    self._segmentation: Segmentation = segmentation
    self._index_db: IndexDB = index_db
    self._added_ids: list[str] = []

  def save(self, id: str, type: str, text: str, properties: Optional[dict] = None):
    segments: list[Segment] = []
    for segment in self._segmentation.split(text):
      if is_empty_string(segment.text):
        continue
      segments.append(segment)
    if len(segments) == 0:
      return
    if properties is None:
      properties = { "type": type }
    else:
      properties.copy()
      properties["type"] = type

    self._index_db.save(id, segments, properties)
    self._added_ids.append(id)

  def rollback(self):
    for id in self._added_ids:
      self._index_db.remove(id)
    self._added_ids.clear()