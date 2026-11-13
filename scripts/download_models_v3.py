"""Pinned public checkpoints, parallel resumable byte ranges, complete hash verification."""
import argparse,concurrent.futures,hashlib,json,os,shutil,time
from pathlib import Path
import requests,threading,urllib.parse
from huggingface_hub import HfApi,hf_hub_download
from irsem.common import read_json,write_json
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--model',choices=['qwen','compiler-ftd'],required=True);p.add_argument('--workers',type=int,default=12);p.add_argument('--transport',choices=['auto','official'],default='auto');a=p.parse_args()
assert 1<=a.workers<=16
spec=read_json(root/'configs/compiler-ftd.json') if a.model=='compiler-ftd' else read_json(root/'configs/models.json')['qwen']
out=root/'results/model-downloads';out.mkdir(parents=True,exist_ok=True)
meta_path=out/(a.model+'-source-manifest.json')
if meta_path.exists():
 meta=read_json(meta_path);assert meta['model']==spec
else:
 info=HfApi(token=False).model_info(spec['id'],revision=spec['revision'],files_metadata=True)
 assert info.sha==spec['revision'] and info.gated is False
 names={spec['filename'],'README.md','config.json'} if a.model=='compiler-ftd' else {s.rfilename for s in info.siblings if s.rfilename.startswith('model') and (s.rfilename.endswith('.safetensors') or s.rfilename.endswith('.index.json'))}|{'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt'}
 files=[{'path':s.rfilename,'size':s.size,'lfs_sha256':getattr(s.lfs,'sha256',None),'git_blob_id':s.blob_id} for s in info.siblings if s.rfilename in names]
 meta={'model':spec,'metadata_endpoint':'https://huggingface.co','files':files};write_json(meta_path,meta)
# Optional alternate transport is accepted only when all frozen weight hashes match.
transport_receipt=out/'qwen-modelscope-transport.json'
if a.model=='qwen' and a.transport=='auto' and not transport_receipt.exists():
 try:
  with requests.Session() as session:
   session.trust_env=False
   response=session.get('https://modelscope.cn/api/v1/models/Qwen/Qwen2.5-Coder-7B-Instruct/repo/files',params={'Revision':'master','Recursive':'true'},timeout=(10,20));response.raise_for_status()
   ms={f['Path']:f for f in response.json()['Data']['Files']}
  matches=[]
  for f in meta['files']:
   if f['path'].endswith('.safetensors'):
    m=ms[f['path']]
    if m['Sha256']!=f['lfs_sha256'] or m['Size']!=f['size']:raise ValueError('Alternate transport does not match the frozen checkpoint')
    matches.append({'path':f['path'],'revision':m['Revision'],'sha256':m['Sha256'],'size':m['Size']})
  write_json(transport_receipt,{'source':'https://modelscope.cn/models/Qwen/Qwen2.5-Coder-7B-Instruct','purpose':'Transport only; all tensor hashes and sizes match frozen official Hub metadata.','files':matches})
 except (OSError,ValueError,KeyError,requests.RequestException):
  print('Alternate transport unavailable; using official Hub/CDN',flush=True)
cache=root/'.cache/huggingface/hub'/('models--'+spec['id'].replace('/','--'));blobs=cache/'blobs';snapshot=cache/'snapshots'/spec['revision'];blobs.mkdir(parents=True,exist_ok=True);snapshot.mkdir(parents=True,exist_ok=True)
chunk=8*1024**2;started=time.monotonic();records=[]
def get_hash(path,lfs):
 size=path.stat().st_size;h=hashlib.sha256() if lfs else hashlib.sha1(b'blob '+str(size).encode()+b'\0')
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
for item in meta['files']:
 expected=item['lfs_sha256'] or item['git_blob_id'];size=item['size'];assert isinstance(size,int) and expected
 blob=blobs/expected;partial=blobs/(expected+'.v3partial');state=blobs/(expected+'.v3ranges.json')
 if not blob.exists() and (size<1024*1024 or not item['lfs_sha256']):
  hf_hub_download(spec['id'],item['path'],revision=spec['revision'],cache_dir=cache.parent,token=False)
 if not blob.exists():
  if state.exists():d=read_json(state);assert d['size']==size and d['chunk']==chunk
  else:
   if shutil.disk_usage(root).free<size+2*1024**3:raise RuntimeError('Insufficient disk space for '+item['path'])
   d={'size':size,'chunk':chunk,'done':[]};write_json(state,d)
  fd=os.open(partial,os.O_RDWR|os.O_CREAT,0o600);os.ftruncate(fd,size);done=set(d['done'])
  jobs=[(i,start,min(size,start+chunk)-1) for i,start in enumerate(range(0,size,chunk))]
  # Resolve once through the official Hub, then reuse per-thread direct CDN sessions.
  official=f"https://huggingface.co/{spec['id']}/resolve/{spec['revision']}/{item['path']}?download=true"
  use_modelscope=a.model=='qwen' and a.transport=='auto' and item['path'].endswith('.safetensors') and transport_receipt.exists()
  if use_modelscope:
   table=read_json(out/'qwen-modelscope-transport.json');m=next(f for f in table['files'] if f['path']==item['path'])
   assert m['sha256']==item['lfs_sha256'] and m['size']==size
   official='https://modelscope.cn/api/v1/models/Qwen/Qwen2.5-Coder-7B-Instruct/repo?'+urllib.parse.urlencode({'Revision':m['revision'],'FilePath':m['path']})
  with requests.Session() as resolver:
   resolver.trust_env=not use_modelscope
   with resolver.get(official,headers={'Range':'bytes=0-1023'},stream=True,timeout=(15,45)) as response:
    response.raise_for_status();cdn_url=response.url;next(response.iter_content(1024))
  print('Direct public CDN',urllib.parse.urlsplit(cdn_url).hostname,flush=True)
  thread_local=threading.local()
  def fetch(job):
   i,start,end=job
   for attempt in range(6):
    try:
     if not hasattr(thread_local,'session'):
      thread_local.session=requests.Session();thread_local.session.trust_env=False
     if True:
      with thread_local.session.get(cdn_url,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(12,20)) as r:
       if r.status_code==200 and start==0 and end==size-1:pass
       elif r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':raise ValueError('Range response mismatch')
       at=start;t=time.monotonic()
       for b in r.iter_content(64*1024):
        if at+len(b)>end+1:raise ValueError('Oversized response')
        v=memoryview(b)
        while v:
         n=os.pwrite(fd,v,at);at+=n;v=v[n:]
        if at<end+1 and time.monotonic()-t>75:raise TimeoutError('Slow range')
       if at!=end+1:raise ValueError('Truncated response')
     return i
    except (OSError,ValueError,requests.RequestException):
     if attempt==5:raise RuntimeError('Range failed: '+item['path']+' '+str(i)) from None
     time.sleep(1+attempt)
  print('Downloading',item['path'],'bytes',size,'remaining_chunks',len(jobs)-len(done),flush=True)
  try:
   with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
    for future in concurrent.futures.as_completed([ex.submit(fetch,j) for j in jobs if j[0] not in done]):
     try:done.add(future.result())
     except RuntimeError as exc:
      print(str(exc),flush=True);continue
     os.fsync(fd);d['done']=sorted(done);write_json(state,d)
     if len(done)%64==0 or len(done)==len(jobs):print(item['path'],len(done),'/',len(jobs),flush=True)
  finally:os.close(fd)
  if get_hash(partial,bool(item['lfs_sha256']))!=expected:raise RuntimeError('Checkpoint hash mismatch: '+item['path'])
  partial.replace(blob)
 if blob.stat().st_size!=size or get_hash(blob,bool(item['lfs_sha256']))!=expected:raise RuntimeError('Existing checkpoint hash mismatch')
 link=snapshot/item['path'];link.parent.mkdir(parents=True,exist_ok=True)
 if not link.exists():link.symlink_to(os.path.relpath(blob,link.parent))
 records.append({**item,'verified_hash':expected});print('Verified',item['path'],flush=True)
write_json(out/(a.model+'-verified.json'),{'status':'complete','model':spec,'endpoint':'Public transport(s) with whole-file verification against the frozen official Hub hashes; see optional qwen-modelscope-transport.json. Partial bytes may be resumed across byte-identical sources.','metadata_endpoint':'https://huggingface.co','files':records,'seconds':time.monotonic()-started,'weights_uploaded_to_git':False})
print('CHECKPOINT_VERIFIED',a.model,flush=True)
