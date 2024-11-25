from __future__ import annotations
from dataclasses import dataclass
from typing import Union, Optional

from ..parser import PdfParser, PdfMetadata
from ..index import Index, IndexNode, IndexSegment, IndexNodeMatching

@dataclass
class PdfQueryItem:
  pdf_files: list[str]
  distance: float
  metadata: PdfMetadata

@dataclass
class PageQueryItem:
  pdf_files: list[PagePDFFile]
  distance: float
  content: str
  segments: list[PageHighlightSegment]
  annotations: list[PageAnnoQueryItem]

QueryItem = Union[PdfQueryItem, PageQueryItem]

@dataclass
class PagePDFFile:
  scope: str
  path: str
  device_path: str
  page_index: int

@dataclass
class PageAnnoQueryItem:
  index: int
  distance: float
  content: str
  segments: list[PageHighlightSegment]

@dataclass
class PageHighlightSegment:
  start: int
  end: int
  main: bool
  highlights: list[tuple[int, int]]

def trim_nodes(index: Index, pdf_parser: PdfParser, nodes: list[IndexNode]) -> list[QueryItem]:
  page_items_dict: dict[str, PageQueryItem] = {}
  result_items: list[QueryItem] = []

  for node in nodes:
    if node.type == "pdf":
      pdf = pdf_parser.pdf_or_none(node.id)
      if pdf is not None:
        result_items.append(PdfQueryItem(
          pdf_files=index.get_paths(node.id),
          distance=node.vector_distance,
          metadata=pdf.metadata,
        ))
    else:
      page_item = _trim_page_and_child_type(node, index, pdf_parser, page_items_dict)
      if page_item is not None:
        result_items.append(page_item)

  for page_item in result_items:
    if isinstance(page_item, PageQueryItem):
      page_item.annotations.sort(key=lambda item: item.index)

  return result_items

def _trim_page_and_child_type(
  node: IndexNode,
  index: Index,
  pdf_parser: PdfParser,
  page_items_dict: dict[str, PageQueryItem]) -> Optional[PageQueryItem]:

  page = pdf_parser.page(node.id)
  page_item: Optional[PageQueryItem] = None

  if page is None:
    return page_item

  if node.type == "pdf.page.anno.content":
    id_cells = node.id.split("/")
    page_hash = id_cells[0]
    page_index = int(id_cells[2])
    anno_content = page.annotations[page_index].content
    page_item = page_items_dict.get(page_hash, None)
    if anno_content is not None and page_item is not None:
      anno_item = PageAnnoQueryItem(
        index=page_index,
        distance=node.vector_distance,
        content=anno_content,
        segments=_mark_highlights(
          content=anno_content,
          segments=node.segments,
          ignore_empty_segments=node.matching != IndexNodeMatching.Similarity,
        ),
      )
      page_item.annotations.append(anno_item)

  elif node.type == "pdf.page":
    content = page.snapshot
    page_item = PageQueryItem(
      pdf_files=[],
      distance=node.vector_distance,
      content=content,
      annotations=[],
      segments=_mark_highlights(
        content=content,
        segments=node.segments,
        ignore_empty_segments=node.matching != IndexNodeMatching.Similarity,
      ),
    )
    for relative_to in index.get_page_relative_to_pdf(page.hash):
      page_item.pdf_files.append(PagePDFFile(
        scope=relative_to.scope,
        path=relative_to.path,
        device_path=relative_to.device_path,
        page_index=relative_to.page_index,
      ))
    page_items_dict[page.hash] = page_item

  return page_item

def _mark_highlights(content: str, segments: list[IndexSegment], ignore_empty_segments: bool) -> list[PageHighlightSegment]:
  content = content.lower()
  min_rank: tuple[float, float] = (float("inf"), float("inf"))
  highlight_segments: list[PageHighlightSegment] = []

  for segment in segments:
    if segment.fts5_rank < min_rank[0] or (
      segment.fts5_rank == min_rank[0] and \
      segment.vector_distance < min_rank[1]
    ):
      min_rank = (
        segment.fts5_rank,
        segment.vector_distance,
      )

  for segment in segments:
    start = segment.start
    end = segment.end
    highlights: list[tuple[int, int]] = []
    for token in segment.matched_tokens:
      for highlight in _search_highlights(token, start, end, content):
        highlights.append(highlight)

    if not ignore_empty_segments or len(highlights) > 0:
      highlights.sort(key=lambda h: h[0])
      highlight_segments.append(PageHighlightSegment(
        start=start,
        end=end,
        highlights=highlights,
        main=(
          segment.fts5_rank == min_rank[0] and \
          segment.vector_distance == min_rank[1]
        ),
      ))
  return highlight_segments

def _search_highlights(token: str, start: int, end: int, content: str):
  finding_start = start
  while finding_start < end:
    index = content.find(token, finding_start, end)
    if index == -1:
      break
    offset = index - start
    finding_start = index + len(token)
    yield (offset, offset + len(token))