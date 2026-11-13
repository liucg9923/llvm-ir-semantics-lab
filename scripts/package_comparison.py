"""Package complete FTD comparison evidence. Never include weights, tokens or caches."""
import hashlib,json,re,tarfile
from pathlib import Path
from irsem.common import read_json,write_json,digest
root=Path(__file__).resolve().parents[1];campaign=root/'results/campaign-ftd-v1';summary=read_json(campaign/'analysis/summary.json')
assert read_json(campaign/'analysis/ANALYSIS_CHECKS.json')['passed']
files=set()
for name in [*summary['initial_runs'].values(),*summary['feedback_runs'].values(),'compiler-ftd-dev-v1','compiler-ftd-dev-noexamples-v1']:
 path=root/'results'/name
 assert read_json(path/'manifest.json')['status']=='evaluated'
 files.update(p for p in path.rglob('*') if p.is_file())
for name in ['opt-v2','identity-v2','qwen-v2','qwen-feedback-v2']:
 for filename in ['manifest.json','results.json']:files.add(root/'results'/name/filename)
for directory in ['analysis','figures','stages']:
 files.update(p for p in (campaign/directory).rglob('*') if p.is_file() and not p.name.endswith(('.preview.png','.alignment-audit.svg','.collision-audit.pdf')))
files.update(p for p in campaign.glob('*') if p.is_file() and p.suffix in {'.md','.json'})
for pattern in ['compiler-ftd-*.json','qwen-verified.json','qwen-source-manifest.json']:
 files.update((root/'results/model-downloads').glob(pattern))
for name in ['accepted.json','fixture-validation.json','sandbox-validation.json','inference-freeze.txt','core-freeze.txt','report-freeze.txt']:
 path=root/'.toolchain'/name
 if path.exists():files.add(path)
for directory in ['src','scripts','tools','configs','tasks','tests','docs']:
 files.update(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.json','.ll','.md','.sh','.txt'})
for name in ['README.md','pyproject.toml','Makefile','LICENSE','THIRD_PARTY_NOTICES.md','.github/workflows/ci.yml']:
 files.add(root/name)
for p in files:
 rel=p.relative_to(root)
 if any(x in {'.cache','models','.git','.venv','.venv-inference','.venv-report'} for x in rel.parts):raise ValueError('Forbidden path: '+str(rel))
 if p.stat().st_size>30*1024**2:raise ValueError('Unexpected large artifact: '+str(rel))
 try:text=p.read_text()
 except UnicodeDecodeError:continue
 for pattern in [r'-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----',r'\b(?:ghp|gho|github_pat|hf)_[A-Za-z0-9_]{20,}\b']:
  if re.search(pattern,text):raise ValueError('Potential secret: '+str(rel))
bundle=campaign/'evidence';bundle.mkdir(exist_ok=True)
checks={str(p.relative_to(root)):digest(p) for p in sorted(files)};write_json(bundle/'FILES.sha256.json',checks)
archive=bundle/'experiment-evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in sorted(files):tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
 tar.add(bundle/'FILES.sha256.json',arcname='FILES.sha256.json')
(bundle/'ARCHIVE.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
print(json.dumps({'files':len(checks),'archive_bytes':archive.stat().st_size,'sha256':digest(archive)}))
