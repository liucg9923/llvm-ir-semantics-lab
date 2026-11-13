#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
CONFIG=${IRSEM_INSPECT_LLVM_CONFIG:-/usr/lib/llvm-17/bin/llvm-config}
test "$("$CONFIG" --version)" = 17.0.6
mkdir -p .toolchain/bin
g++ $("$CONFIG" --cxxflags) -std=c++17 -O2 tools/v3_ir_inspect.cpp -o .toolchain/bin/irsem-inspect $("$CONFIG" --ldflags --libs core irreader analysis --system-libs)
