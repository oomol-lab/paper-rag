from threading import Thread, Lock
from typing import Generator
from json import dumps
from index_package import Service
from .sources import Sources
from .progress_events import ProgressEvents


class ServiceRef:
  def __init__(self, workspace_path: str, embedding_model: str, sources: Sources):
    self._workspace_path: str = workspace_path
    self._embedding_model: str = embedding_model
    self._sources: Sources = sources
    self._lock: Lock = Lock()
    self._service: Service | None = None
    self._is_scanning: bool = False
    self._progress_events: ProgressEvents = ProgressEvents()

  @property
  def ref(self) -> Service:
    with self._lock:
      if self._service is None:
        raise Exception("Service is not ready")
      return self._service

  @property
  def sources(self) -> Sources:
    return self._sources

  def gen_scanning_sse_lines(self) -> Generator[str, None, None]:
    for event in self._progress_events.fetch_events():
      yield f"data: {dumps(event, ensure_ascii=False)}\n\n"

  def start_scanning(self):
    with self._lock:
      if self._is_scanning:
        return
      self._is_scanning = True
      self._service = None

    try:
      Thread(target=self._scan).start()

    except Exception as e:
      with self._lock:
        self._is_scanning = False
      raise e

  def _scan(self):
    self._progress_events.reset()
    service = Service(
      workspace_path=self._workspace_path,
      embedding_model_id=self._embedding_model,
    )
    scan_job = service.scan_job(
      progress_listeners=self._progress_events.listeners,
    )
    try:
      completed = scan_job.start({
        name: path
        for name, path in self._sources.items()
      })
    except Exception as e:
      self._progress_events.fail(str(e))
      raise e

    if not completed:
      self._progress_events.interrupt()
      return

    with self._lock:
      self._service = service
      self._is_scanning = False
    self._progress_events.complete()