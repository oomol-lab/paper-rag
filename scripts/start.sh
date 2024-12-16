#!/bin/bash
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

if ! command -v conda >/dev/null 2>&1; then
  echo "Need Conda to setup the environment"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Need call ./scripts/setup.sh first"
  exit 1
fi

eval "$(conda shell.bash hook)"
conda activate ./.venv

python main.py