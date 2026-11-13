"""Archive complete controlled-experiment evidence, excluding credentials and weights."""
from pathlib import Path
import re,tarfile,json
from irsem.common import read_json,write_json,digest
from irsem.v3.control import require_frozen
root=Path(__file__).resolve().parents[1];require_frozen(root);campaign=root/'results/campaign-v3'
assert read_json(campaign/'flow-state.json')['status']=='model_runs_complete'
assert read_json(campaign/'analysis/ANALYSIS_CHECKS.json')['passed']
files=set()
for p in (root/'results').iterdir():
 if p.is_dir() and (p.name.startswith('v3-') or p.name.startswith('v3b-')):
  files.update(x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
for p in campaign.rglob('*'):
 if p.is_file() and 'evidence' not in p.relative_to(campaign).parts and not p.name.endswith(('.alignment-audit.svg','.collision-audit.pdf','.preview.png')):files.add(p)
files.update(p for p in (root/'results/model-downloads').glob('*.json'))
for directory in ['src','scripts','tools','configs','tasks','tests','docs']:
 files.update(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.cpp','.json','.ll','.md','.sh','.txt'})
for name in ['README.md','LICENSE','THIRD_PARTY_NOTICES.md','pyproject.toml','Makefile','.gitattributes','.gitignore','.github/workflows/ci.yml']:
 files.add(root/name)
for name in ['build.json','inference-freeze.txt','core-freeze.txt','report-freeze.txt']:
 p=root/'.toolchain'/name
 if p.exists():files.add(p)
for p in files:
 rel=p.relative_to(root)
 if any(n in {'.cache','models','.git','.venv','.venv-inference','.venv-report'} for n in rel.parts):raise ValueError('Forbidden archive path')
 if p.stat().st_size>100*1024**2:raise ValueError('Unexpected large artifact: '+str(rel))
 try:s=p.read_text()
 except UnicodeDecodeError:continue
 for pat in [r'-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----',r'\b(?:ghp|gho|github_pat|hf)_[A-Za-z0-9_]{20,}\b',r'connect\.(?:westc|weste)\.seetacloud\.com']:
  if re.search(pat,s):raise ValueError('Potential sensitive content: '+str(rel))
checks={str(p.relative_to(root)):digest(p) for p in sorted(files)}
out=campaign/'evidence';out.mkdir(exist_ok=True);write_json(out/'FILES.sha256.json',checks)
archive=out/'controlled-v3-evidence.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as t:
 for p in sorted(files):t.add(p,arcname=str(p.relative_to(root)),recursive=False)
 t.add(out/'FILES.sha256.json',arcname='FILES.sha256.json')
(out/'ARCHIVE.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
print(json.dumps({'files':len(files),'uncompressed_bytes':sum(p.stat().st_size for p in files),'archive_bytes':archive.stat().st_size,'archive_sha256':digest(archive)}))
