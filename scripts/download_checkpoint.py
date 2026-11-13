"""Download a pinned checkpoint and verify its files against official Hub metadata.
Credentials are never written to reports or sent to the optional public Qwen mirror.
"""
import argparse,hashlib,json,os,shutil,time
from pathlib import Path
from datetime import datetime,timezone
import requests
from huggingface_hub import HfApi,snapshot_download,configure_http_backend

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--model',choices=['qwen','compiler'],required=True)
p.add_argument('--public-mirror',action='store_true');args=p.parse_args()
if args.public_mirror and args.model!='qwen': raise SystemExit('Only the public Qwen checkpoint may use the unauthenticated mirror')
spec=json.loads((root/'configs/models.json').read_text())[args.model]
reports=root/'results/model-downloads';reports.mkdir(parents=True,exist_ok=True)
source_path=reports/(args.model+'-source-manifest.json')
start=time.monotonic()
if source_path.exists():
 source=json.loads(source_path.read_text())
 if source['model']['id']!=spec['id'] or source['model']['revision']!=spec['revision']: raise SystemExit('Source metadata revision mismatch')
 files=source['files']
else:
 info=HfApi(token=False if args.model=='qwen' else None).model_info(spec['id'],revision=spec['revision'],files_metadata=True)
 if info.sha!=spec['revision']: raise SystemExit('Upstream revision mismatch')
 safe=[s.rfilename for s in info.siblings if s.rfilename.startswith('model') and s.rfilename.endswith('.safetensors')]
 weight_names=set(safe or [s.rfilename for s in info.siblings if s.rfilename.startswith('pytorch_model') and s.rfilename.endswith('.bin')])
 small={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','added_tokens.json','vocab.json','merges.txt','tokenizer.model'}
 small.add('model.safetensors.index.json' if safe else 'pytorch_model.bin.index.json')
 files=[{'path':s.rfilename,'size':s.size,'lfs_sha256':getattr(s.lfs,'sha256',None),'git_blob_id':s.blob_id} for s in info.siblings if s.rfilename in weight_names|small]
 source={'model':spec,'files':files}
 source_path.write_text(json.dumps(source,indent=2)+'\n')
cache=Path(os.environ.get('HF_HOME',root/'.cache/huggingface'))/'hub'
repo_cache=cache/('models--'+spec['id'].replace('/','--'))
remaining=0
for f in files:
 if not isinstance(f['size'],int): raise SystemExit('Missing upstream file size')
 key=f['lfs_sha256'] or f['git_blob_id']
 if not key: raise SystemExit('Missing upstream hash')
 blob=repo_cache/'blobs'/key; partial=repo_cache/'blobs'/(key+'.incomplete')
 have=blob.stat().st_size if blob.exists() else partial.stat().st_size if partial.exists() else 0
 remaining+=max(0,f['size']-have)
if shutil.disk_usage(root).free<remaining+1024**3: raise SystemExit('Insufficient space for the remaining checkpoint bytes plus 1GiB reserve')
endpoint='https://hf-mirror.com' if args.public_mirror else 'https://huggingface.co'
if args.public_mirror:
 def no_proxy_session():
  s=requests.Session();s.trust_env=False;return s
 configure_http_backend(backend_factory=no_proxy_session)
print('Downloading',spec['id'],spec['revision'],'expected_bytes',sum(f['size'] for f in files),'endpoint',endpoint,flush=True)
snapshot=Path(snapshot_download(spec['id'],revision=spec['revision'],allow_patterns=[f['path'] for f in files],
 cache_dir=cache,endpoint=endpoint,token=False if args.model=='qwen' else None,max_workers=4))
verified=[]
for f in files:
 path=snapshot/f['path'];size=path.stat().st_size
 if size!=f['size']: raise RuntimeError('Size mismatch: '+f['path'])
 sha=hashlib.sha256() if f['lfs_sha256'] else hashlib.sha1(b'blob '+str(size).encode()+b'\0')
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(4*1024*1024),b''):sha.update(chunk)
 expected=f['lfs_sha256'] or f['git_blob_id']
 if sha.hexdigest()!=expected:raise RuntimeError('Hash mismatch: '+f['path'])
 verified.append({**f,'verified_hash':sha.hexdigest()})
 print('Verified',f['path'],size,flush=True)
report={'status':'complete','model':spec,'endpoint':endpoint,'finished_utc':datetime.now(timezone.utc).isoformat(),
 'seconds':time.monotonic()-start,'snapshot':str(snapshot),'files':verified,'weights_uploaded_to_git':False}
(reports/(args.model+'-verified.json')).write_text(json.dumps(report,indent=2)+'\n')
print('CHECKPOINT_VERIFIED',spec['id'],flush=True)
