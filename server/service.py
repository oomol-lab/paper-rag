from threading import Lock
from index_package import Service, ProgressListeners
from .sources import Sources


class ServiceRef:
  def __init__(self, workspace_path: str, embedding_model: str, sources: Sources):
    self._workspace_path: str = workspace_path
    self._embedding_model: str = embedding_model
    self._sources: Sources = sources
    self._lock: Lock = Lock()
    self._service: Service | None = None

  def scan(self):
    with self._lock:
      self._service = None

    service = Service(
      workspace_path=self._workspace_path,
      embedding_model_id=self._embedding_model,
    )
    listeners = ProgressListeners()
    scan_job = service.scan_job(progress_listeners=listeners)
    success = scan_job.start({
      name: path
      for name, path in self._sources.items()
    })
    if success:
      with self._lock:
        self._service = service
    else:
      print("Complete Interrupted.")