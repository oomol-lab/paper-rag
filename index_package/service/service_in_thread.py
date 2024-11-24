import os

from typing import Optional
from dataclasses import dataclass

from ..progress_events import ProgressEventListener
from .trimmer import trim_nodes, QueryItem
from ..scanner import Event, Scope
from ..parser import PdfParser
from ..segmentation import Segmentation
from ..index import Index, VectorDB, FTS5DB


@dataclass
class QueryResult:
  items: list[QueryItem]
  keywords: list[str]

# sqlite3 can only be used in the same thread it was created
class ServiceInThread:
  def __init__(
    self,
    scope: Scope,
    pdf_parser_cache_path: str,
    pdf_parser_temp_path: str,
    fts5_db_path: str,
    index_dir_path: str,
    segmentation: Segmentation,
    vector_db: VectorDB,
  ):
    self._scope: Scope = scope
    self._pdf_parser: PdfParser = PdfParser(
      cache_dir_path=pdf_parser_cache_path,
      temp_dir_path=pdf_parser_temp_path,
    )
    self._index: Index = Index(
      scope=scope,
      pdf_parser=self._pdf_parser,
      fts5_db=FTS5DB(db_path=fts5_db_path),
      vector_db=vector_db,
      index_dir_path=index_dir_path,
      segmentation=segmentation,
    )

  def query(self, text: str, results_limit: int) -> QueryResult:
    nodes, keywords = self._index.query(text, results_limit)
    trimmed_nodes = trim_nodes(self._index, self._pdf_parser, nodes)
    return QueryResult(trimmed_nodes, keywords)

  def page_content(self, pdf_hash: str, page_index: int) -> str:
    pdf = self._pdf_parser.pdf_or_none(pdf_hash)
    if pdf is None:
      return ""
    return pdf.pages[page_index].snapshot

  def device_path(self, scope: str, path: str) -> Optional[str]:
    scope_path = self._scope.scope_path(scope)
    if scope_path is None:
      return None

    path = os.path.join(scope_path, f"./{path}")
    path = os.path.abspath(path)
    return path

  def handle_event(self, event: Event, listener: ProgressEventListener):
    self._index.handle_event(event, listener)