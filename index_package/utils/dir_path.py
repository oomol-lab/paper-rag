import os

def ensure_dir(path: str) -> str:
  if not os.path.exists(path):
    os.makedirs(path)
  return path

def ensure_parent_dir(path: str) -> str:
  parent = os.path.dirname(path)
  ensure_dir(parent)
  return path