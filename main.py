import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import server

if __name__ == "__main__":
  server.launch()