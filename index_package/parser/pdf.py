from __future__ import annotations

import os
import json
import shutil
import sqlite3
import pikepdf

from typing import cast, Optional, Callable
from dataclasses import dataclass

from .pdf_extractor import extract_metadata_with_pdf, PdfExtractor, Annotation
from ..progress import Progress
from ..utils import hash_sha512, assert_continue, TempFolderHub, InterruptException

@dataclass
class Pdf:
  hash: str
  metadata: PdfMetadata
  pages: list[PdfPage]

@dataclass
class PdfMetadata:
  author: Optional[str]
  modified_at: Optional[str]
  producer: Optional[str]

class PdfPage:
  def __init__(self, parent, pdf_id: int, index: int, hash: str):
    self.index: int = index
    self.hash: str = hash
    self._parent = parent
    self._pdf_id = pdf_id
    self._annotations: Optional[list[Annotation]] = None
    self._snapshot: Optional[str] = None

  @property
  def page_file_path(self) -> str:
    return os.path.join(self._parent._pages_path, f"{self.hash}.pdf")

  @property
  def annotations(self) -> list[Annotation]:
    if self._annotations is None:
      extractor = cast(PdfExtractor, self._parent._extractor)
      self._annotations = extractor.read_annotations(self.hash)
    return self._annotations

  @property
  def snapshot(self) -> str:
    if self._snapshot is None:
      extractor = cast(PdfExtractor, self._parent._extractor)
      self._snapshot = extractor.read_snapshot(self.hash)
    return self._snapshot

  def load_pdf(self) -> Pdf:
    return cast(Pdf, self._parent._load_cached_pdf(self._pdf_id))

# it's just for test unit now.
@dataclass
class PdfParserListeners:
  on_page_added: Callable[[str], None] = lambda _: None
  on_page_removed: Callable[[str], None] = lambda _: None

class PdfParser:
  def __init__(
    self,
    cache_dir_path: str,
    temp_dir_path: str,
    listeners: PdfParserListeners = PdfParserListeners(),
  ) -> None:
    db_path = os.path.abspath(
      os.path.join(cache_dir_path, "pages.sqlite3"),
    )
    self._pages_path: str = os.path.abspath(
      os.path.join(cache_dir_path, "pages"),
    )
    self._temp_folders: TempFolderHub = TempFolderHub(temp_dir_path)
    self._conn: sqlite3.Connection = self._connect(db_path)
    self._extractor: PdfExtractor = PdfExtractor(self._pages_path)
    self._listeners: PdfParserListeners = listeners

    if not os.path.exists(self._pages_path):
      os.makedirs(self._pages_path, exist_ok=True)

  def _connect(self, db_path: str) -> sqlite3.Connection:
    is_first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path)

    if is_first_time:
      cursor = conn.cursor()
      try:
        cursor.execute("""
          CREATE TABLE pdfs (
            id INTEGER PRIMARY KEY,
            hash TEXT NOT NULL,
            meta TEXT NOT NULL
          )
        """)
        cursor.execute("""
          CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            pdf_id TEXT NOT NULL,
            hash TEXT NOT NULL,
            idx INTEGER NOT NULL
          )
        """)
        cursor.execute("""
          CREATE INDEX idx_pdfs ON pdfs (hash)
        """)
        cursor.execute("""
          CREATE INDEX idx_pdf_pages ON pages (pdf_id, idx)
        """)
        cursor.execute("""
          CREATE INDEX idx__hash_pages ON pages (hash)
        """)
        conn.commit()
      finally:
        cursor.close()

    return conn

  def close(self):
    self._conn.close()

  @property
  def name(self) -> str:
    return "pdf"

  def page(self, page_hash: str) -> Optional[PdfPage]:
    cursor = self._conn.cursor()
    try:
      cursor.execute("SELECT pdf_id, idx FROM pages WHERE hash = ? LIMIT 1", (page_hash,))
      row = cursor.fetchone()
      if row is not None:
        pdf_id, index = row
        return PdfPage(self, pdf_id, index, page_hash)
      else:
        return None
    finally:
      cursor.close()

  def pdf(self, hash: str, file_path: str, progress: Optional[Progress] = None) -> Pdf:
    cursor = self._conn.cursor()
    try:
      cursor.execute("SELECT id, meta FROM pdfs WHERE hash = ? LIMIT 1", (hash,))
      row = cursor.fetchone()

      if row is None:
        pdf_id, metadata = self._create_and_split_pdf(cursor, hash, file_path, progress)
      else:
        pdf_id, meta_json = row
        metadata = PdfMetadata(**json.loads(meta_json))

      return Pdf(
        hash=hash,
        metadata=metadata,
        pages=self._all_pages(cursor, pdf_id),
      )
    finally:
      cursor.close()

  def pdf_or_none(self, hash: str) -> Optional[Pdf]:
    cursor = self._conn.cursor()
    try:
      pdf_id = self._pdf_id(cursor, hash)
      if pdf_id is None:
        return None
      else:
        return self._load_cached_pdf(cursor, pdf_id)
    finally:
      cursor.close()

  def _load_cached_pdf(self, cursor: sqlite3.Cursor, pdf_id: int) -> Pdf:
    cursor.execute("SELECT hash, meta FROM pdfs WHERE id = ? LIMIT 1", (pdf_id,))
    row = cursor.fetchone()
    if row is None:
      raise ValueError(f"pdf_id {pdf_id} not found")

    hash, meta_json = row
    metadata = PdfMetadata(**json.loads(meta_json))

    return Pdf(
      hash=hash,
      metadata=metadata,
      pages=self._all_pages(cursor, pdf_id),
    )

  def pdf_has_cached(self, hash: str) -> bool:
    cursor = self._conn.cursor()
    try:
      pdf_id = self._pdf_id(cursor, hash)
      return pdf_id is not None
    finally:
      cursor.close()

  def _all_pages(self, cursor: sqlite3.Cursor, pdf_id: int) -> list[PdfPage]:
    pdf_pages: list[PdfPage] = []
    rows = cursor.execute(
      "SELECT idx, hash FROM pages WHERE pdf_id = ? ORDER BY idx",
      (pdf_id,),
    )
    for row in rows.fetchall():
      index, page_hash = row
      pdf_page = PdfPage(self, pdf_id, index, page_hash)
      pdf_pages.append(pdf_page)

    return pdf_pages

  def _create_and_split_pdf(self, cursor: sqlite3.Cursor, hash: str, file_path: str, progress: Optional[Progress]) -> tuple[int, PdfMetadata]:
    metadata = PdfMetadata(**extract_metadata_with_pdf(file_path))
    metadata_json = json.dumps(metadata.__dict__)
    added_page_hashes: list[str] = []
    try:
      cursor.execute("BEGIN TRANSACTION")
      cursor.execute("INSERT INTO pdfs (hash, meta) VALUES (?, ?)", (hash, metadata_json))
      pdf_id = cast(int, cursor.lastrowid)

      for index, page_hash in enumerate(self._extract_page_hashes(file_path)):
        cursor.execute(
          "INSERT INTO pages (pdf_id, hash, idx) VALUES (?, ?, ?)",
          (pdf_id, page_hash, index),
        )
        cursor.execute("SELECT COUNT(*) FROM pages WHERE hash = ?", (page_hash,))
        num_rows = cursor.fetchone()[0]
        if num_rows == 1:
          added_page_hashes.append(page_hash)

      for i, page_hash in enumerate(added_page_hashes):
        assert_continue()
        self._extractor.extract_page(page_hash)
        self._listeners.on_page_added(page_hash)
        if progress is not None:
          pages_count = len(added_page_hashes)
          progress.complete_handle_pdf_page(i, pages_count)

      self._conn.commit()
      return pdf_id, metadata

    except InterruptException as e:
      for page_hash in added_page_hashes:
        self._extractor.remove_page(page_hash)
      self._conn.rollback()
      raise e

  # to clean useless cache files
  def fire_file_removed(self, hash: str):
    cursor = self._conn.cursor()
    try:
      pdf_id = self._pdf_id(cursor, hash)
      if pdf_id is None:
        return

      rows = cursor.execute(
        "SELECT hash FROM pages WHERE pdf_id = ? ORDER BY idx",
        (pdf_id,),
      )
      page_hashes: list[str] = [row[0] for row in rows]
      removed_page_hashes: list[str] = []

      try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("DELETE FROM pdfs WHERE id = ?", (pdf_id,))
        cursor.execute("DELETE FROM pages WHERE pdf_id = ?", (pdf_id,))
        self._conn.commit()
      except Exception as e:
        self._conn.rollback()
        raise e

      for page_hash in page_hashes:
        cursor.execute("SELECT id FROM pages WHERE hash = ? LIMIT 1", (page_hash,))
        if cursor.fetchone() is None:
          removed_page_hashes.append(page_hash)

      for page_hash in removed_page_hashes:
        self._extractor.remove_page(page_hash)
        self._listeners.on_page_removed(page_hash)

    finally:
      cursor.close()

  def _extract_page_hashes(self, file_path: str) -> list[str]:
    page_hashes: list[str] = []

    with self._temp_folders.create() as folder:
      folder_path = folder.path
      pages_count: int = 0

      # https://pikepdf.readthedocs.io/en/latest/
      with pikepdf.Pdf.open(file_path) as pdf_file:
        for i, page in enumerate(pdf_file.pages):
          page_file = pikepdf.Pdf.new()
          page_file.pages.append(page)
          page_file_path = os.path.join(folder_path, f"{i}.pdf")
          page_file.save(
            page_file_path,
            # make sure hash of file never changes
            deterministic_id=True,
          )
        pages_count = len(pdf_file.pages)

      for i in range(pages_count):
        page_file_path = os.path.join(folder_path, f"{i}.pdf")
        page_hash = hash_sha512(page_file_path)
        page_hashes.append(page_hash)
        target_page_path = os.path.join(self._pages_path, f"{page_hash}.pdf")

        if os.path.exists(target_page_path):
          if os.path.isdir(target_page_path):
            shutil.rmtree(target_page_path)
          else:
            os.remove(target_page_path)

        shutil.move(page_file_path, target_page_path)

    return page_hashes

  def _pdf_id(self, cursor: sqlite3.Cursor, hash: str) -> Optional[int]:
    cursor.execute("SELECT id FROM pdfs WHERE hash = ? LIMIT 1", (hash,))
    row = cursor.fetchone()
    if row is None:
      return None
    else:
      return row[0]
