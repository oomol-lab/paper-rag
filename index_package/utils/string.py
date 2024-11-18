def is_empty_string(text: str) -> bool:
  for char in text:
    if not char.isspace():
      return False
  return True