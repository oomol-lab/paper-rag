import base64
import hashlib

def hash_sha512(file_path, chunk_size: int = 4096) -> str:
  sha512_hash = hashlib.sha512()
  with open(file_path, "rb") as file:
    while chunk := file.read(chunk_size):
      sha512_hash.update(chunk)

  bytes = sha512_hash.digest()
  base64_data = base64.urlsafe_b64encode(bytes)

  return base64_data.decode()