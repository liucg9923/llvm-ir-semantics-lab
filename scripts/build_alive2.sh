#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX=${IRSEM_TOOLCHAIN_PREFIX:-$ROOT/.toolchain}
BUILD=${IRSEM_BUILD_DIR:-$ROOT/.build}
JOBS=${IRSEM_BUILD_JOBS:-4}
LLVM_CMAKE=${1:-/usr/lib/llvm-17/lib/cmake/llvm}
REV=e031ebd9c18be1a4fc7f37ab193b4b158b92dd9a
if [ "${IRSEM_USE_PROVIDER_PROXY:-0}" = 1 ] && [ -f /etc/network_turbo ]; then
 source /etc/network_turbo >/dev/null 2>&1
fi
mkdir -p "$BUILD" "$PREFIX/bin"
if [ ! -d "$BUILD/alive2/.git" ]; then
 git init "$BUILD/alive2"
 git -C "$BUILD/alive2" remote add origin https://github.com/AliveToolkit/alive2.git
fi
git -C "$BUILD/alive2" fetch --depth 1 origin "$REV"
git -C "$BUILD/alive2" checkout --detach "$REV"
[ "$(git -C "$BUILD/alive2" rev-parse HEAD)" = "$REV" ]
cmake -S "$BUILD/alive2" -B "$BUILD/alive2-build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_LLVM_UTILS=ON -DLLVM_DIR="$LLVM_CMAKE" -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$BUILD/alive2-build" --target alive-tv alive --parallel "$JOBS"
cp "$BUILD/alive2-build/alive-tv" "$PREFIX/bin/alive-tv"
LLVM_TOOLS=$(cd "$LLVM_CMAKE/../../.." && pwd)/bin
for name in opt llvm-config llvm-as llvm-dis; do
 ln -sfn "$LLVM_TOOLS/$name" "$PREFIX/bin/$name"
done
if [ -x "$LLVM_TOOLS/clang" ]; then
 ln -sfn "$LLVM_TOOLS/clang" "$PREFIX/bin/clang"
else
 ln -sfn /usr/lib/llvm-17/bin/clang "$PREFIX/bin/clang"
fi
python3 - "$ROOT" "$REV" "$LLVM_CMAKE" <<'PY'
import json,sys,subprocess
from pathlib import Path
root=Path(sys.argv[1]); data={'alive2_revision':sys.argv[2],'llvm_cmake':sys.argv[3],
'z3_packages':subprocess.run(['dpkg-query','-W','libz3-dev'],capture_output=True,text=True).stdout.strip(),
'status':'built_not_yet_accepted'}
(root/'.toolchain/build.json').write_text(json.dumps(data,indent=2)+'\n')
PY
"$PREFIX/bin/alive-tv" --version
