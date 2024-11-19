from typing import Callable, Optional
from dataclasses import dataclass

@dataclass
class ProgressListeners:
  after_scan: Optional[Callable[[int], None]] = None
  on_start_handle_file: Optional[Callable[[str], None]] = None
  on_complete_handle_pdf_page: Optional[Callable[[int, int], None]] = None
  on_complete_index_pdf_page: Optional[Callable[[int, int], None]] = None
  on_complete_handle_file: Optional[Callable[[str], None]] = None

class Progress:
  def __init__(self, listeners: ProgressListeners = ProgressListeners()) -> None:
    self.after_scan: Callable[[int], None] = listeners.after_scan or (lambda _: None)
    self.start_handle_file: Callable[[str], None] = listeners.on_start_handle_file or (lambda _: None)
    self.complete_handle_pdf_page: Callable[[int, int], None] = listeners.on_complete_handle_pdf_page or (lambda _1, _2: None)
    self.complete_index_pdf_page: Callable[[int, int], None] = listeners.on_complete_index_pdf_page or (lambda _1, _2: None)
    self.complete_handle_file: Callable[[str], None] = listeners.on_complete_handle_file or (lambda _: None)