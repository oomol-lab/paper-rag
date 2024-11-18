from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class IndexNodeMatching(Enum):
  Matched = "matched"
  MatchedPartial = "matched_partial"
  Similarity = "similarity"

@dataclass
class IndexNode:
  id: str
  type: str
  matching: IndexNodeMatching
  metadata: dict
  fts5_rank: float
  vector_distance: float
  segments: list[IndexSegment]

@dataclass
class IndexSegment:
  start: int
  end: int
  matched_tokens: list[str]

@dataclass
class PageRelativeToPDF:
  pdf_hash: str
  pdf_path: str
  page_index: int