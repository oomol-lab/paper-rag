import signal
import time
import sys
import threading

from typing import Optional
from index_package import ServiceScanJob

class SignalHandler:
  def __init__(self):
    self._scan_job: Optional[ServiceScanJob] = None
    self._first_interrupted_at: Optional[float] = None
    self._lock: threading.Lock = threading.Lock()
    signal.signal(signal.SIGINT, self._on_sigint)

  @property
  def is_interrupting(self) -> bool:
    with self._lock:
      return self._first_interrupted_at is not None

  def notify_scanning_done(self):
    time.sleep(0.5)
    sys.exit()

  # return False when is interrupting
  def bind_scan_job(self, scan_job: ServiceScanJob) -> bool:
    with self._lock:
      if self._scan_job is not None:
        raise Exception("SignalHandler already watching a scan job")
      if self._first_interrupted_at is not None:
        return False
      self._scan_job = scan_job
      return True

  def unbind_scan_job(self):
    with self._lock:
      self._scan_job = None

  def _on_sigint(self, sig, frame):
    with self._lock:
      limit_seconds = 12.0
      if self._scan_job is not None and \
        self._first_interrupted_at is None:
        print("\nInterrupting...")
        self._first_interrupted_at = time.time()
        self._scan_job.interrupt()

      elif self._first_interrupted_at is None:
        print("\nExiting...")
        sys.exit(130)

      else:
        duration_seconds = time.time() - self._first_interrupted_at
        if duration_seconds <= limit_seconds:
          str_seconds = "{:.2f}".format(limit_seconds - duration_seconds)
          print(f"\nForce stopping... (press again to force stop after {str_seconds}s)")
        else:
          print("\nForce stopping...")
          print("It may corrupt the data structure of the database")
          # TODO: 因为强制退出导致数据结构损坏，此处需要冻结数据库并重新开始
          sys.exit(1)