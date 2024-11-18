import os
import unittest

from typing import Optional
from index_package.utils.chunk import Chunk, ChunkHub
from tests.utils import get_temp_path

class TestChunk(unittest.TestCase):

  def test_chunk_operation(self):
    temp_path = get_temp_path("chunk")
    db_path = os.path.join(temp_path, "chunk2.sqlite3")
    chunks = ChunkHub(db_path)

    foo_chunk = chunks.add("foo")
    bar_chunk = chunks.add("bar")
    child1 = chunks.add_child(foo_chunk, "1", "child1")
    child2 = chunks.add_child(foo_chunk, "2", "child2")

    self._assert_chunks_equals(foo_chunk, chunks.get(foo_chunk.uid))
    self._assert_chunks_equals(bar_chunk, chunks.get(bar_chunk.uid))
    self._assert_chunks_equals(child1, chunks.get(child1.uid))
    self._assert_chunks_equals(child2, chunks.get(child2.uid))

    child_uids: list[str] = []
    child_paths: list[str] = []

    for ref in chunks.get_child_refs(foo_chunk):
      self.assertEqual(ref.parent.uid, foo_chunk.uid)
      child_uids.append(ref.uid)
      child_paths.append(ref.path)

    self.assertListEqual(child_uids, [child1.uid, child2.uid])
    self.assertListEqual(child_paths, [child1.path, child2.path])

    child3 = chunks.add_child(foo_chunk, "3", "child3")
    sub_child = chunks.add_child(child3, "sub", "sub_child")

    chunks.remove(bar_chunk)
    chunks.remove(child1)
    chunks.set_meta(child2, "child1-2")

    self._assert_chunks_equals(foo_chunk, chunks.get(foo_chunk.uid))
    self._assert_chunks_equals(child2, chunks.get(child2.uid))

    child_uids = []
    child_paths = []

    for ref in chunks.get_child_refs(foo_chunk):
      self.assertEqual(ref.parent.uid, foo_chunk.uid)
      child_uids.append(ref.uid)
      child_paths.append(ref.path)

    self.assertListEqual(child_uids, [child2.uid, child3.uid])
    self.assertListEqual(child_paths, [child2.path, child3.path])

    # will remove all it's children
    chunks.remove(foo_chunk)

    for chunk in [foo_chunk, child1, child2, child3, sub_child]:
      self.assertIsNone(chunks.get(chunk.uid))

  def _assert_chunks_equals(self, c1: Optional[Chunk], c2: Optional[Chunk]):
    if c1 is None:
      self.assertIsNone(c2)
    elif c2 is None:
      self.assertIsNone(c1)
    else:
      self.assertIsNotNone(c2)
      self.assertEqual(c1.uid, c2.uid)
      self.assertEqual(c1.path, c2.path)
      self.assertEqual(c1.meta, c2.meta)
      self.assertEqual(c1._parent_uid, c2._parent_uid)