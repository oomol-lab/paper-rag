import os
import threading

from typing import cast, Optional, Callable

from .service_in_thread import ServiceInThread
from ..scanner import Scope, EventParser, Scanner
from ..progress_events import ProgressEventListener, ScanCompletedEvent
from ..utils import TasksPool, TasksPoolResultState

_JobContext = tuple[ServiceInThread, EventParser]

class ServiceScanJob:
  def __init__(
    self,
    scan_db_path: str,
    max_workers: int,
    create_service: Callable[[Scope], ServiceInThread],
    progress_event_listener: ProgressEventListener,
  ):
    self._job_contexts: list[Optional[_JobContext]] = [None for _ in range(max_workers)]
    self._create_service: Callable[[Scope], ServiceInThread] = create_service
    self._listener: ProgressEventListener = progress_event_listener
    self._interrupter_lock: threading.Lock = threading.Lock()
    self._did_interrupted: bool = False
    self._scanner: Scanner = Scanner(
      db_path=scan_db_path,
    )
    self._pool: TasksPool[int] = TasksPool[int](
      max_workers=max_workers,
      print_error=True,
      on_init=self._init_context,
      on_handle=lambda id, i: self._handle_event(id, i),
    )

  # @return True if scan completed, False if scan interrupted
  def start(self, sources: dict[str, str]) -> bool:
    self._scanner.commit_sources(sources)

    event_ids = self._scanner.scan()
    self._pool.start()

    self._listener(ScanCompletedEvent(
      updated_files=self._scanner.events_count,
    ))

    for event_id in event_ids:
      success = self._pool.push(event_id)
      if not success:
        break

    state = self._pool.complete()
    if state == TasksPoolResultState.RaisedException:
      raise RuntimeError("scan failed with Exception")
    elif state == TasksPoolResultState.Interrupted:
      return False
    else:
      return True

  # could be called in another thread safely
  def interrupt(self):
    with self._interrupter_lock:
      if self._did_interrupted:
        raise RuntimeError("already interrupted")
      self._did_interrupted = True

    self._pool.interrupt()

  def _init_context(self, index: int):
    self._job_contexts[index] = (
      self._create_service(self._scanner.scope),
      self._scanner.event_parser(),
    )

  def _handle_event(self, event_id: int, index: int):
    service, parser = cast(_JobContext, self._job_contexts[index])
    scope = self._scanner.scope

    with parser.parse(event_id) as event:
      display_path = event.path
      scope_path = scope.scope_path(event.scope)
      if scope_path is not None:
        display_path = os.path.join(scope_path, f".{event.path}")
        display_path = os.path.abspath(display_path)
      else:
        display_path = f"[removed]:{display_path}"

      service.handle_event(event, self._listener)
