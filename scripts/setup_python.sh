#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PYTHON=${IRSEM_PYTHON:-python3}
"$PYTHON" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --index-url "${IRSEM_PIP_INDEX_URL:-https://pypi.org/simple}" -e "$ROOT[dev]"
