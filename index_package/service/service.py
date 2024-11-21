import os
import threading

from typing import Optional
from .service_in_thread import ServiceInThread, QueryResult
from .scan_job import ServiceScanJob
from ..scanner import Scope, Scanner
from ..index import VectorDB
from ..segmentation.segmentation import Segmentation
from ..progress_events import ProgressEventListener
from ..utils import ensure_dir, ensure_parent_dir

_service_in_thread = threading.local()

class Service:
  def __init__(
    self,
    workspace_path: str,
    embedding_model_id: str,
  ):
    self._scan_db_path: str = ensure_parent_dir(
      os.path.abspath(os.path.join(workspace_path, "scanner.sqlite3"))
    )
    self._pdf_parser_cache_path = ensure_dir(
      os.path.abspath(os.path.join(workspace_path, "parser", "pdf_cache")),
    )
    self._pdf_parser_temp_path = ensure_dir(
      os.path.abspath(os.path.join(workspace_path, "temp")),
    )
    self._fts5_db_path = ensure_parent_dir(
      os.path.abspath(os.path.join(workspace_path, "index_fts5.sqlite3"))
    )
    self._index_dir_path = ensure_dir(
      os.path.abspath(os.path.join(workspace_path, "indexes")),
    )
    self._segmentation: Segmentation = Segmentation()
    self._vector_db=VectorDB(
      embedding_model_id=embedding_model_id,
      distance_space="l2",
      index_dir_path=ensure_dir(
        os.path.abspath(os.path.join(workspace_path, "vector_db")),
      ),
    )

  def query(self, text: str, results_limit: int) -> QueryResult:
    return self._get_service_in_thread().query(text, results_limit)

  def page_content(self, pdf_hash: str, page_index: int) -> str:
    return self._get_service_in_thread().page_content(pdf_hash, page_index)

  def device_path(self, scope: str, path: str) -> Optional[str]:
    return self._get_service_in_thread().device_path(scope, path)

  def scan_job(self, max_workers: int = 1, progress_event_listener: Optional[ProgressEventListener] = None) -> ServiceScanJob:
    if progress_event_listener is None:
      progress_event_listener = lambda _: None

    return ServiceScanJob(
      max_workers=max_workers,
      scan_db_path=self._scan_db_path,
      progress_event_listener=progress_event_listener,
      create_service=lambda scope: self._create_service_in_thread(scope),
    )

  # TODO: 这会导致无法释放。要彻底解决，需要迁移 sqlite pool 的逻辑。
  def _get_service_in_thread(self) -> ServiceInThread:
    service_in_thread = getattr(_service_in_thread, "value", None)
    if service_in_thread is None:
      scanner = Scanner(self._scan_db_path)
      service_in_thread = self._create_service_in_thread(scanner.scope)
      setattr(_service_in_thread, "value", service_in_thread)

    return service_in_thread

  def _create_service_in_thread(self, scope: Scope) -> ServiceInThread:
    return ServiceInThread(
      scope=scope,
      pdf_parser_cache_path=self._pdf_parser_cache_path,
      pdf_parser_temp_path=self._pdf_parser_temp_path,
      fts5_db_path=self._fts5_db_path,
      index_dir_path=self._index_dir_path,
      segmentation=self._segmentation,
      vector_db=self._vector_db,
    )