from __future__ import annotations
from enum import Enum
from typing import cast, Optional, TypeVar, Generic, Callable
from sqlite3_pool import build_thread_pool, release_thread_pool

import traceback
import threading
import queue

E = TypeVar("E")
_interrupted_event_val = threading.local()

class _SemaphoreValue(Generic[E]):
  def __init__(self):
    self._element: Optional[E] = None
    self._did_release = False
    self._did_release_lock = threading.Lock()
    self._putter_lock = threading.Lock()
    self._getter_lock = threading.Lock()
    self._sem_element = threading.Semaphore(0)
    self._ack_queue = queue.Queue[bool](maxsize=0)

  def put(self, event: E) -> bool:
    with self._putter_lock:
      with self._did_release_lock:
        if self._did_release:
          return False

      self._element = event
      self._sem_element.release()
      ack_success = self._ack_queue.get()
    return ack_success

  def get(self) -> Optional[E]:
    with self._getter_lock:
      with self._did_release_lock:
        if self._did_release:
          return None
      self._sem_element.acquire()
      event = self._element
      self._element = None
      self._ack_queue.put(True)

    return event

  def release_putter(self):
    with self._did_release_lock:
      self._did_release = True
      self._sem_element.release()
      self._ack_queue.put(False)

class TasksPoolResultState(Enum):
  Success = 0,
  Interrupted = 1,
  RaisedException = 2,

# no thread safety
class TasksPool(Generic[E]):
  def __init__(
    self,
    max_workers: int,
    on_handle: Callable[[E, int], None],
    on_init: Optional[Callable[[int], None]] = None,
    print_error: bool = True,
  ):
    self._state: TasksPoolResultState = TasksPoolResultState.Success
    self._state_lock: threading.Lock = threading.Lock()
    self._max_workers = max_workers
    self._on_handle: Callable[[E, int], None] = on_handle
    self._on_init: Optional[Callable[[int], None]] = on_init
    self._print_error: bool = print_error
    self._semaphore_value: _SemaphoreValue[E] = _SemaphoreValue()
    self._threads: list[threading.Thread] = []
    self._interrupted_event: threading.Event = threading.Event()
    self._completed_event: threading.Event = threading.Event()

  @property
  def is_interrupted(self) -> bool:
    return self._interrupted_event.is_set()

  def start(self) -> TasksPool:
    for index in range(self._max_workers):
      thread = threading.Thread(
        target=lambda:self._start_thread_loop(index),
        daemon=True,
      )
      self._threads.append(thread)
    for thread in self._threads:
      thread.start()
    return self

  def push(self, event: E) -> bool:
    if self._interrupted_event.is_set() or \
       self._completed_event.is_set():
      return False
    return self._semaphore_value.put(event)

  # THREAD SAFE: fire interrupt event
  def interrupt(self):
    with self._state_lock:
      if self._state != TasksPoolResultState.RaisedException:
        self._state = TasksPoolResultState.Interrupted

    self._interrupted_event.set()
    self._semaphore_value.release_putter()

  # complete all threads and block until all stopped
  def complete(self) -> TasksPoolResultState:
    self._completed_event.set()
    self._semaphore_value.release_putter()
    for thread in self._threads:
      thread.join()
    return self._state

  # this function is running in daemon thread
  def _start_thread_loop(self, index: int):
    _interrupted_event_val.value = self._interrupted_event

    try:
      build_thread_pool()

      if self._on_init is not None:
        self._on_init(index)

      while True:
        event = self._semaphore_value.get()
        if event is None:
          break
        self._on_handle(event, index)

        if self._completed_event.is_set():
          break
        if self._interrupted_event.is_set():
          break

    except InterruptException:
      # For Debugging
      # traceback.print_exc()
      pass

    except Exception as _:
      with self._state_lock:
        self._state = TasksPoolResultState.RaisedException
      if self._print_error:
        traceback.print_exc()
      if not self._interrupted_event.is_set():
        self._interrupted_event.set()
        self._semaphore_value.release_putter()

    finally:
      release_thread_pool()

class InterruptException(Exception):
  def __init__(self):
    super().__init__("Interrupt")

def assert_continue():
  if not hasattr(_interrupted_event_val, "value"):
    return
  event = cast(threading.Event, _interrupted_event_val.value)
  if event.is_set():
    raise InterruptException()