"""Resumable bounded parallel ranges for the pinned public GGUF, with final SHA-256.
No credentials are used. The ordinary downloader performs the metadata/report verification.
"""
import argparse,concurrent.futures,hashlib,json,os,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=16);a=p.parse_args()
if not 1<=a.workers<=16:raise SystemExit('workers must be 1..16')
spec=json.loads((root/'configs/compiler-ftd.json').read_text())
meta=json.loads((root/'results/model-downloads/compiler-ftd-source-manifest.json').read_text())
assert meta['model']==spec
blob=root/'.cache/huggingface/hub'/('models--'+spec['id'].replace('/','--'))/'blobs'/spec['sha256']
partial=Path(str(blob)+'.incomplete');state=Path(str(blob)+'.ranges.json')
size=spec['size'];chunk=16*1024**2
if blob.exists():raise SystemExit('Verified blob already present; run download_gguf.py to finalize receipt')
if state.exists():
 d=json.loads(state.read_text());assert d['sha256']==spec['sha256'] and d['size']==size and d['chunk']==chunk
else:
 prefix=partial.stat().st_size if partial.exists() else 0
 assert prefix<size
 d={'sha256':spec['sha256'],'size':size,'chunk':chunk,'prefix':prefix,'done':[]}
 state.write_text(json.dumps(d))
fd=os.open(partial,os.O_RDWR|os.O_CREAT,0o600);os.ftruncate(fd,size)
url=f"https://hf-mirror.com/{spec['id']}/resolve/{spec['revision']}/{spec['filename']}?download=true"
ranges=[(i,start,min(start+chunk,size)-1) for i,start in enumerate(range(d['prefix'],size,chunk))]
done=set(d['done']);start_time=time.monotonic()
def fetch(job):
 i,start,end=job
 for attempt in range(5):
  try:
   with requests.Session() as session:
    session.trust_env=False
    with session.get(url,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(20,90)) as r:
     if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':
      raise ValueError('Invalid range response '+str(r.status_code))
     offset=start
     for b in r.iter_content(1024**2):
      if offset+len(b)>end+1:raise ValueError('Range oversized')
      view=memoryview(b)
      while view:
       n=os.pwrite(fd,view,offset);offset+=n;view=view[n:]
     if offset!=end+1:raise ValueError('Range truncated')
   return i
  except (OSError,ValueError,requests.RequestException) as e:
   if attempt==4:raise RuntimeError(f'Range {i} failed: {type(e).__name__}') from None
   time.sleep(1+attempt)
print('Parallel public ranges:',a.workers,'remaining:',len(ranges)-len(done),flush=True)
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
  futures=[ex.submit(fetch,j) for j in ranges if j[0] not in done]
  for future in concurrent.futures.as_completed(futures):
   done.add(future.result());os.fsync(fd);d['done']=sorted(done)
   tmp=Path(str(state)+'.tmp');tmp.write_text(json.dumps(d));tmp.replace(state)
   if len(done)%16==0 or len(done)==len(ranges):
    print('Completed ranges',len(done),'/',len(ranges),'elapsed',round(time.monotonic()-start_time),flush=True)
finally:os.close(fd)
h=hashlib.sha256()
with partial.open('rb') as f:
 for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
if h.hexdigest()!=spec['sha256']:raise SystemExit('Final SHA-256 mismatch; nothing accepted')
partial.replace(blob)
(root/'results/model-downloads/compiler-ftd-range-transfer.json').write_text(json.dumps({'status':'verified','sha256':h.hexdigest(),'bytes':size,'workers':a.workers,'endpoint':'https://hf-mirror.com','seconds':time.monotonic()-start_time,'resumed_prefix_bytes':d['prefix']},indent=2)+'\n')
print('PARALLEL_CHECKPOINT_VERIFIED',flush=True)
