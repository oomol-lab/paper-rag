import os
import unittest

from typing import Optional
from index_package.parser import PdfParser
from index_package.scanner import Scope, Event, EventKind, EventTarget
from index_package.segmentation import Segment, Segmentation
from index_package.index import Index, IndexNode, VectorDB, FTS5DB, IndexNodeMatching
from index_package.index.index_db import IndexDB
from tests.utils import get_temp_path

class TestIndex(unittest.TestCase):
  def test_fts5_query(self):
    db = FTS5DB(
      db_path=os.path.abspath(os.path.join(get_temp_path("index-database/fts5"), "db.sqlite3")),
    )
    documents = {}
    documents["id1"] = [
      "Transference interpretations, like extratransference interpretations or indeed any behavior on the analyst’s part.",
      "the transference in the here and now are the core of the analytic work.",
    ]
    documents["id2"] = [
      "I am of the opinion that the range of settings.",
      "most  people  would  call  this  treatment \"psychotherapy.\"",
      "which the  technique  of  analysis  of  the  transference is appropriate",
    ]
    db.save(
      node_id="id1",
      segments=[
        Segment(start=0, end=100, text=documents["id1"][0]),
        Segment(start=100, end=250, text=documents["id1"][1]),
      ],
      metadata={},
    )
    db.save(
      node_id="id2",
      segments=[
        Segment(start=0, end=100, text=documents["id2"][0]),
        Segment(start=100, end=250, text=documents["id2"][1]),
        Segment(start=250, end=350, text=documents["id2"][2]),
      ],
      metadata={},
    )
    nodes: list[IndexNode] = []
    for node in db.query("Transference analysis"):
      nodes.append(node)

    self.assertEqual(len(nodes), 1)
    node = nodes[0]

    self.assertEqual(node.id, "id2")
    self.assertEqual(
      [(s.start, s.end, s.matched_tokens) for s in node.segments],
      [(250, 350, ["analysis", "transference"])],
    )

    nodes = []
    for node in db.query("Transference analysis", is_or_condition=True):
      nodes.append(node)

    self.assertEqual(len(nodes), 1)
    node = nodes[0]

    self.assertEqual(node.id, "id1")
    self.assertEqual(
      [(s.start, s.end) for s in node.segments],
      [(0, 100), (100, 250)],
    )

    db.remove("id2")
    nodes = []
    for node in db.query("Transference analysis"):
      nodes.append(node)

    self.assertEqual(len(nodes), 0)

  def test_vector_query(self):
    db = VectorDB(
      distance_space="l2",
      index_dir_path=get_temp_path("index-database/vector"),
      embedding_model_id="shibing624/text2vec-base-chinese"
    )
    db.save(
      node_id="index/db/id1",
      segments=[
        Segment(start=0, end=100, text="Transference interpretations, like extratransference interpretations or indeed any behavior on the analyst’s part."),
        Segment(start=100, end=250, text="the transference in the here and now are the core of the analytic work."),
      ],
      metadata={},
    )
    db.save(
      node_id="index/db/id2",
      segments=[
        Segment(start=0, end=100, text="I am of the opinion that the range of settings."),
        Segment(start=100, end=250, text="most  people  would  call  this  treatment \"psychotherapy.\""),
        Segment(start=250, end=350, text="which the  technique  of  analysis  of  the  transference is appropriate"),
      ],
      metadata={},
    )
    query_embedding = db.encode_embedding("the transference in the here and now are the core of the analytic work.")
    nodes = db.query(query_embedding, results_limit=1)
    self.assertEqual(len(nodes), 1)
    node = nodes[0]
    self.assertEqual(node.id, "index/db/id1")

  def test_database_query(self):
    fts5_db = FTS5DB(
      db_path=os.path.abspath(os.path.join(get_temp_path("index-database/database"), "db.sqlite3")),
    )
    vector_db = VectorDB(
      distance_space="l2",
      index_dir_path=get_temp_path("index-database/database/vector"),
      embedding_model_id="shibing624/text2vec-base-chinese"
    )
    db = IndexDB(
      fts5_db=fts5_db,
      vector_db= vector_db,
    )
    db.save(
      node_id="id1",
      segments=[Segment(start=0, end=200, text="which the technique  of  analysis  of  the  transference is appropriate")],
      metadata={},
    )
    db.save(
      node_id="id2",
      segments=[Segment(start=0, end=200, text="most  people  would  call  this  treatment \"psychotherapy.\"")],
      metadata={},
    )
    db.save(
      node_id="id3",
      segments=[Segment(start=0, end=200, text="the transference in the here and now are the core of the analytic work.")],
      metadata={},
    )
    db.save(
      node_id="id4",
      segments=[Segment(start=0, end=200, text="Transference interpretations, like extratransference interpretations or indeed any behavior on the analyst’s part.")],
      metadata={},
    )
    db.save(
      node_id="id5",
      segments=[Segment(start=0, end=200, text="the transference in the here and now are the core of the analytic work.")],
      metadata={},
    )
    results: list[tuple[str, IndexNodeMatching]] = []

    for node in db.query("Transference analysis", results_limit=100):
      results.append((node.id, node.matching))

    self.assertEqual(results, [
      ("id1", IndexNodeMatching.Matched),
      ("id4", IndexNodeMatching.MatchedPartial),
      ("id3", IndexNodeMatching.MatchedPartial),
      ("id5", IndexNodeMatching.MatchedPartial),
      ("id2", IndexNodeMatching.Similarity),
    ])

  def test_vector_index_for_pdf(self):
    segmentation = Segmentation()
    parser = PdfParser(
      cache_dir_path=get_temp_path("index_vector/parser_cache"),
      temp_dir_path=get_temp_path("index_vector/temp"),
    )
    fts5_db = FTS5DB(
      db_path=os.path.abspath(os.path.join(
        get_temp_path("index_fts5/fts5_db"),
        "db.sqlite3"
      )),
    )
    vector_db = VectorDB(
      distance_space="l2",
      index_dir_path=get_temp_path("index_vector/vector_db"),
      embedding_model_id="shibing624/text2vec-base-chinese",
    )
    index = Index(
      pdf_parser=parser,
      segmentation=segmentation,
      fts5_db=fts5_db,
      vector_db=vector_db,
      index_dir_path=get_temp_path("index_vector/index"),
      scope=_Scope({
        "assets": os.path.abspath(os.path.join(__file__, "../assets")),
      }),
    )
    added_event = Event(
      id=0,
      kind=EventKind.Added,
      target=EventTarget.File,
      scope="assets",
      path="/The Analysis of the Transference.pdf",
      mtime=0,
    )
    index.handle_event(added_event)
    nodes, _ = index.query("identify", results_limit=1)
    self.assertEqual(len(nodes), 1)
    node = nodes[0]
    self.assertEqual(node.id, "Ayy2i4OK41YmIejdNJYTfyl6SgC_7zd7q05vDUenDOBEmN3T6gtKTC5gP5a_-dxufdntkgR3f2agbwww5a3AsA==/anno/0/content")
    self.assertEqual(node.matching, IndexNodeMatching.Similarity)
    self.assertEqual(
      [(s.start, s.end) for s in node.segments],
      [(0, len("Identification"))],
    )

class _Scope(Scope):
  def __init__(self, sources: dict[str, str]) -> None:
    super().__init__()
    self._sources: dict[str, str] = sources

  @property
  def scopes(self) -> list[str]:
    return list(self._sources.keys())

  def scope_path(self, scope: str) -> Optional[str]:
    return self._sources.get(scope, None)