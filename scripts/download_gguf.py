"""Download only the pinned public community checkpoint; verify upstream hashes."""
import argparse,hashlib,json,os,shutil,time
from pathlib import Path
from datetime import datetime,timezone
import requests
from huggingface_hub import HfApi,hf_hub_download,configure_http_backend
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--public-mirror',action='store_true');a=p.parse_args()
spec=json.loads((root/'configs/compiler-ftd.json').read_text())
out=root/'results/model-downloads';out.mkdir(parents=True,exist_ok=True)
source=out/'compiler-ftd-source-manifest.json'
if source.exists():
 d=json.loads(source.read_text());assert d['model']==spec
else:
 info=HfApi(token=False).model_info(spec['id'],revision=spec['revision'],files_metadata=True)
 assert info.sha==spec['revision'] and info.gated is False
 files=[{'path':s.rfilename,'size':s.size,'lfs_sha256':getattr(s.lfs,'sha256',None),'git_blob_id':s.blob_id} for s in info.siblings if s.rfilename in {spec['filename'],'README.md','config.json'}]
 assert len(files)==3
 d={'model':spec,'metadata_endpoint':'https://huggingface.co','files':files}
 source.write_text(json.dumps(d,indent=2)+'\n')
files=d['files'];weight=next(f for f in files if f['path']==spec['filename'])
assert weight['lfs_sha256']==spec['sha256'] and weight['size']==spec['size']
cache=root/'.cache/huggingface/hub';blob=cache/('models--'+spec['id'].replace('/','--'))/'blobs'/spec['sha256']
have=blob.stat().st_size if blob.exists() else Path(str(blob)+'.incomplete').stat().st_size if Path(str(blob)+'.incomplete').exists() else 0
if shutil.disk_usage(root).free < max(0,spec['size']-have)+3*1024**3:raise SystemExit('Insufficient disk space plus 3GiB reserve')
endpoint='https://hf-mirror.com' if a.public_mirror else 'https://huggingface.co'
if a.public_mirror:
 def session():
  s=requests.Session();s.trust_env=False;return s
 configure_http_backend(backend_factory=session)
start=time.monotonic();verified=[]
print('Download endpoint:',endpoint,'revision:',spec['revision'],flush=True)
for f in files:
 path=Path(hf_hub_download(spec['id'],f['path'],revision=spec['revision'],cache_dir=cache,token=False,endpoint=endpoint))
 assert path.stat().st_size==f['size'],f['path']
 sha=hashlib.sha256() if f['lfs_sha256'] else hashlib.sha1(b'blob '+str(f['size']).encode()+b'\0')
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b''):sha.update(chunk)
 assert sha.hexdigest()==(f['lfs_sha256'] or f['git_blob_id']),f['path']
 verified.append({**f,'verified_hash':sha.hexdigest()})
 print('Verified:',f['path'],flush=True)
r={'status':'complete','model':spec,'endpoint':endpoint,'finished_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-start,'files':verified,'weights_uploaded_to_git':False}
(out/'compiler-ftd-verified.json').write_text(json.dumps(r,indent=2)+'\n')
print('CHECKPOINT_VERIFIED',flush=True)
