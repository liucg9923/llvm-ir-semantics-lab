"""Recover missing transport extents, accepting only the complete pinned SHA-256."""
from pathlib import Path
import os,json,hashlib,requests,threading,concurrent.futures,time
from irsem.common import read_json,write_json
root=Path(__file__).resolve().parents[1];spec=read_json(root/'configs/compiler-ftd.json')
b=root/'.cache/huggingface/hub'/('models--'+spec['id'].replace('/','--'))/'blobs';partial=b/(spec['sha256']+'.v3partial');blob=b/spec['sha256']
if blob.exists():raise SystemExit('Final blob already exists')
fd=os.open(partial,os.O_RDWR);os.fsync(fd);size=spec['size'];pos=0;gaps=[]
while pos<size:
 start=os.lseek(fd,pos,os.SEEK_HOLE)
 if start>=size:break
 try:end=os.lseek(fd,start,os.SEEK_DATA)
 except OSError:end=size
 lo=max(0,start-65536);hi=min(size,end+65536)
 if gaps and lo<=gaps[-1][1]:gaps[-1][1]=max(hi,gaps[-1][1])
 else:gaps.append([lo,hi])
 pos=end
jobs=[(a,min(z,a+1024**2)) for lo,z in gaps for a in range(lo,z,1024**2)]
print('Missing/adjacent transport bytes',sum(y-x for x,y in gaps),'requests',len(jobs),flush=True)
u=f"https://huggingface.co/{spec['id']}/resolve/{spec['revision']}/{spec['filename']}?download=true"
with requests.Session() as s:
 with s.get(u,headers={'Range':'bytes=0-1023','Cache-Control':'no-cache'},stream=True,timeout=(15,45)) as r:r.raise_for_status();cdn=r.url;next(r.iter_content(1024))
local=threading.local();failures=[];done=0;t=time.monotonic()
def fetch(job):
 start,end=job
 if not hasattr(local,'session'):local.session=requests.Session();local.session.trust_env=False
 for attempt in range(5):
  try:
   with local.session.get(cdn,headers={'Range':f'bytes={start}-{end-1}'},stream=True,timeout=(12,20)) as r:
    if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end-1}/{size}':raise ValueError('Range mismatch')
    at=start;begin=time.monotonic()
    for chunk in r.iter_content(65536):
     if at+len(chunk)>end:raise ValueError('Oversized response')
     v=memoryview(chunk)
     while v:n=os.pwrite(fd,v,at);at+=n;v=v[n:]
     if at<end and time.monotonic()-begin>60:raise TimeoutError('slow response')
    if at!=end:raise ValueError('Incomplete response')
   return None
  except (OSError,ValueError,requests.RequestException):
   if attempt==4:return [start,end]
   time.sleep(1+attempt)
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
  for future in concurrent.futures.as_completed([pool.submit(fetch,j) for j in jobs]):
   failed=future.result();done+=1
   if failed:failures.append(failed)
   if done%32==0 or done==len(jobs):print('completed',done,'/',len(jobs),'failed_requests',len(failures),flush=True)
 os.fsync(fd)
finally:os.close(fd)
h=hashlib.sha256()
with partial.open('rb') as f:
 for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
report={'bytes_requested':sum(y-x for x,y in gaps),'request_count':len(jobs),'failed_requests':failures,'sha256':h.hexdigest(),'expected_sha256':spec['sha256'],'seconds':time.monotonic()-t,'method':'Missing sparse extents plus 64KiB boundary margins; full-file hash is mandatory.'}
write_json(root/'results/model-downloads/compiler-ftd-sparse-recovery.json',report)
if h.hexdigest()!=spec['sha256']:raise SystemExit('Whole-file SHA-256 does not match; nothing accepted')
partial.replace(blob);print('FULL_CHECKPOINT_HASH_VERIFIED',flush=True)
