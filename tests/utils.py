import os
import shutil

def _setup():
  temp_path = os.path.abspath(os.path.join(__file__, "../test_temp"))
  if os.path.exists(temp_path):
    shutil.rmtree(temp_path)
  os.makedirs(temp_path, exist_ok=True)
  return temp_path

_TEMP_PATH: str = _setup()

def get_temp_path(path: str) -> str:
  global _TEMP_PATH
  temp_path = os.path.join(_TEMP_PATH, path)
  if not os.path.exists(temp_path):
    os.makedirs(temp_path)
  return temp_path