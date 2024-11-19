from threading import Lock
from typing import Generator
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
    self._progress_events: ProgressEvents = ProgressEvents()

  def fetch_events(self) -> Generator[dict, None, None]:
    return self._progress_events.fetch_events()

  def scan(self):
    with self._lock:
      self._service = None

    self._progress_events.reset()
    service = Service(
      workspace_path=self._workspace_path,
      embedding_model_id=self._embedding_model,
    )
    scan_job = service.scan_job(
      progress_listeners=self._progress_events.listeners,
    )
    try:
      not_interrupted = scan_job.start({
        name: path
        for name, path in self._sources.items()
      })
    except Exception as e:
      self._progress_events.fail(str(e))
      raise e

    if not_interrupted:
      self._progress_events.complete()
      with self._lock:
        self._service = service
    else:
      self._progress_events.interrupt()