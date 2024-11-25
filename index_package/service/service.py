import os

from typing import Optional
from dataclasses import dataclass
from .scan_job import ServiceScanJob
from .trimmer import trim_nodes, QueryItem
from ..scanner import Scanner
from ..index import Index, VectorDB, FTS5DB
from ..parser import PdfParser
from ..segmentation.segmentation import Segmentation
from ..progress_events import ProgressEventListener
from ..utils import ensure_dir, ensure_parent_dir


@dataclass
class QueryResult:
  items: list[QueryItem]
  keywords: list[str]

class Service:
  def __init__(
    self,
    workspace_path: str,
    embedding_model_id: str,
  ):
    index_dir_path: str = ensure_dir(
      os.path.abspath(os.path.join(workspace_path, "vector_db")),
    )
    self._scanner: Scanner = Scanner(
      db_path=ensure_parent_dir(
        os.path.abspath(os.path.join(workspace_path, "scanner.sqlite3"))
      ),
    )
    self._pdf_parser: PdfParser = PdfParser(
        cache_dir_path=ensure_dir(
          os.path.abspath(os.path.join(workspace_path, "parser", "pdf_cache")),
        ),
        temp_dir_path=ensure_dir(
          os.path.abspath(os.path.join(workspace_path, "temp")),
        ),
      )
    self._index: Index = Index(
      scope=self._scanner.scope,
      index_dir_path=index_dir_path,
      segmentation=Segmentation(),
      pdf_parser=self._pdf_parser,
      vector_db=VectorDB(
        embedding_model_id=embedding_model_id,
        distance_space="l2",
        index_dir_path=index_dir_path,
      ),
      fts5_db=FTS5DB(
        db_path=ensure_parent_dir(
          os.path.abspath(os.path.join(workspace_path, "index_fts5.sqlite3"))
        ),
      ),
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
    scope_path = self._scanner.scope.scope_path(scope)
    if scope_path is None:
      return None

    path = os.path.join(scope_path, f"./{path}")
    path = os.path.abspath(path)
    return path

  def scan_job(self, max_workers: int = 1, progress_event_listener: Optional[ProgressEventListener] = None) -> ServiceScanJob:
    if progress_event_listener is None:
      progress_event_listener = lambda _: None

    return ServiceScanJob(
      max_workers=max_workers,
      progress_event_listener=progress_event_listener,
      scanner=self._scanner,
      handle_event=lambda event: self._index.handle_event(event, progress_event_listener),
    )