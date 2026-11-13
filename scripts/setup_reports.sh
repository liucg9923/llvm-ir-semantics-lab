#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PYTHON=${IRSEM_PYTHON:-python3}
"$PYTHON" -m venv "$ROOT/.venv-report"
"$ROOT/.venv-report/bin/python" -m pip install --index-url "${IRSEM_PIP_INDEX_URL:-https://pypi.org/simple}" -e "$ROOT[report]"
"$ROOT/.venv-report/bin/python" -m pip freeze > "$ROOT/.toolchain/report-freeze.txt"

if [ "${IRSEM_USE_PROVIDER_PROXY:-0}" = 1 ] && [ -f /etc/network_turbo ]; then
 (source /etc/network_turbo >/dev/null 2>&1; "$ROOT/.venv-report/bin/python" "$ROOT/scripts/setup_report_fonts.py")
else
 "$ROOT/.venv-report/bin/python" "$ROOT/scripts/setup_report_fonts.py"
fi
