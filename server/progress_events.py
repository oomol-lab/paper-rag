from dataclasses import dataclass
from typing import Generator
from enum import IntEnum
from threading import Lock
from queue import Queue, Empty
from index_package import ProgressListeners


class ProgressPhase(IntEnum):
  SCANNING = 1
  HANDING_FILES = 2
  COMPLETED = 3
  FAILURE = 4

@dataclass
class HandingFile:
  path: str
  pdf_handing: tuple[int, int] | None = None
  pdf_indexing: tuple[int, int] | None = None

class ProgressEvents:
  def __init__(self):
    self._phase: ProgressPhase = ProgressPhase.SCANNING
    self._status_lock: Lock = Lock()
    self._scanned_count: int = 0
    self._handing_file: HandingFile | None = None
    self._error: str | None = None
    self._completed_files: list[str] = []
    self._fetcher_lock: Lock = Lock()
    self._fetcher_queues: list[Queue[dict | None]] = []

  @property
  def listeners(self) -> ProgressListeners:
    return ProgressListeners(
      after_scan=self._on_after_scan,
      on_start_handle_file=self._on_start_handle_file,
      on_complete_handle_pdf_page=self._on_complete_handle_pdf_page,
      on_complete_index_pdf_page=self._on_complete_index_pdf_page,
      on_complete_handle_file=self._on_complete_handle_file,
    )

  def reset(self):
    with self._status_lock:
      self._phase = ProgressPhase.SCANNING
      self._scanned_count = 0
      self._handing_file = None
      self._error = None
      self._completed_files.clear()

    self._emit_event({
      "kind": "reset",
    })

  def _init_events(self) -> list[dict]:
    with self._status_lock:
      if self._phase == ProgressPhase.SCANNING:
        return [{ "kind": "scanning" }]

      events: list[dict] = []
      events.append({
        "kind": "scanCompleted",
        "count": self._scanned_count,
      })
      for path in self._completed_files:
        events.append({
          "kind": "completeHandingFile",
          "path": path,
        })
      if self._phase == ProgressPhase.COMPLETED:
        events.append({ "kind": "completed" })

      elif self._phase == ProgressPhase.FAILURE:
        events.append({
          "kind": "failure",
          "error": self._error or "",
        })
      elif self._phase == ProgressPhase.HANDING_FILES and \
           self._handing_file is not None:
        events.append({
          "kind": "startHandingFile",
          "path": self._handing_file.path,
        })
        if self._handing_file.pdf_handing is not None:
          index, total = self._handing_file.pdf_handing
          events.append({
            "kind": "completeHandingPdfPage",
            "index": index,
            "total": total,
          })
        if self._handing_file.pdf_indexing is not None:
          index, total = self._handing_file.pdf_indexing
          events.append({
            "kind": "completeIndexPdfPage",
            "index": index,
            "total": total,
          })
      return events

  def _on_after_scan(self, count: int):
    with self._status_lock:
      self._phase = ProgressPhase.HANDING_FILES
      self._scanned_count = count

    self._emit_event({
      "kind": "scanCompleted",
      "count": count,
    })

  def _on_start_handle_file(self, path: str):
    with self._status_lock:
      self._handing_file = HandingFile(path=path)

    self._emit_event({
      "kind": "startHandingFile",
      "path": path,
    })

  def _on_complete_handle_file(self, path: str):
    with self._status_lock:
      self._completed_files.append(path)
      if self._handing_file is not None and self._handing_file.path == path:
        self._handing_file = None

    self._emit_event({
      "kind": "completeHandingFile",
      "path": path,
    })

  def _on_complete_handle_pdf_page(self, page_index: int, total_pages: int):
    with self._status_lock:
      if self._handing_file is not None:
        self._handing_file.pdf_handing = (page_index, total_pages)

    self._emit_event({
      "kind": "completeHandingPdfPage",
      "index": page_index,
      "total": total_pages,
    })

  def _on_complete_index_pdf_page(self, page_index: int, total_pages: int):
    with self._status_lock:
      if self._handing_file is not None:
        self._handing_file.pdf_indexing = (page_index, total_pages)

    self._emit_event({
      "kind": "completeIndexPdfPage",
      "index": page_index,
      "total": total_pages,
    })

  def complete(self):
    with self._status_lock:
      self._phase = ProgressPhase.COMPLETED
      self._completed_files.clear()
      self._handing_file = None

    self._emit_event({
      "kind": "completed",
    })

  def interrupt(self):
    self._emit_event(None)

  def fail(self, error: str):
    with self._status_lock:
      self._phase = ProgressPhase.FAILURE
      self._completed_files.clear()
      self._handing_file = None
      self._error = error

    self._emit_event({
      "kind": "failure",
      "error": error,
    })

  def fetch_events(self) -> Generator[dict, None, None]:
    queue: Queue[dict | None] = Queue()
    with self._fetcher_lock:
      init_events = self._init_events()
      self._fetcher_queues.append(queue)
    try:
      for event in init_events:
        yield event
      init_events.clear()
      while True:
        try:
          event = queue.get(timeout=5.0)
          if event is None:
            yield { "kind": "interrupted" }
            break
          yield event
        except Empty:
          yield { "kind": "heartbeat"}
    finally:
      with self._fetcher_lock:
        self._fetcher_queues.remove(queue)

  def _emit_event(self, event: dict | None) -> None:
    with self._fetcher_lock:
      for queue in self._fetcher_queues:
        queue.put(event)
