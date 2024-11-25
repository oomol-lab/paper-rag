import threading

from typing import Callable
from ..scanner import Event, Scanner
from ..progress_events import ProgressEventListener, ScanCompletedEvent
from ..utils import TasksPool, TasksPoolResultState

class ServiceScanJob:
  def __init__(
    self,
    scanner: Scanner,
    max_workers: int,
    progress_event_listener: ProgressEventListener,
    handle_event: Callable[[Event], None],
  ):
    self._scanner: Scanner = scanner
    self._listener: ProgressEventListener = progress_event_listener
    self._handle_event: Callable[[Event], None] = handle_event
    self._interrupter_lock: threading.Lock = threading.Lock()
    self._did_interrupted: bool = False
    self._pool: TasksPool[int] = TasksPool[int](
      max_workers=max_workers,
      print_error=True,
      on_handle=lambda id, i: self._on_handle_task(id, i),
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

  def _on_handle_task(self, event_id: int, _: int):
    event = self._scanner.parse_event(event_id)
    try:
      self._handle_event(event)
    finally:
      event.close()
