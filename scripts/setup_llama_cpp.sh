#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
REV=$(.venv/bin/python -c 'import json;print(json.load(open("configs/llama-cpp.json"))["revision"])')
TAG=$(.venv/bin/python -c 'import json;print(json.load(open("configs/llama-cpp.json"))["tag"])')
export PATH="${CUDA_HOME:-/usr/local/cuda}/bin:$PATH"
mkdir -p .build
if [ ! -d .build/llama.cpp/.git ]; then
  git clone --depth 1 --branch "$TAG" https://github.com/ggml-org/llama.cpp.git .build/llama.cpp
fi
test "$(git -C .build/llama.cpp rev-parse HEAD)" = "$REV"
cmake -S .build/llama.cpp -B .build/llama.cpp/build -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release
cmake --build .build/llama.cpp/build --target llama-server -j 4
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
root=Path.cwd();p=root/'.build/llama.cpp/build/bin/llama-server'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
libs={str(q.relative_to(root)):sha(q) for q in (root/'.build/llama.cpp/build').rglob('*.so') if q.is_file()}
r={'spec':json.loads((root/'configs/llama-cpp.json').read_text()),'binary_sha256':sha(p),'libraries':libs,'version':subprocess.run([str(p),'--version'],capture_output=True,text=True).stderr,'cuda_compiler':subprocess.run(['nvcc','--version'],capture_output=True,text=True).stdout}
out=root/'results/campaign-ftd-v1';out.mkdir(parents=True,exist_ok=True)
(out/'llama-build.json').write_text(json.dumps(r,indent=2)+'\n')
PY
