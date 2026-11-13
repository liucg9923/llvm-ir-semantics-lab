"""Run an experiment stage with persistent status, logs and optional GPU telemetry."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
from datetime import datetime,timezone

p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--name',required=True)
p.add_argument('--timeout',type=float,default=7200);p.add_argument('--profile-gpu',action='store_true')
p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
command=a.command[1:] if a.command and a.command[0]=='--' else a.command
if not command:raise SystemExit('Missing stage command')
root=Path(__file__).resolve().parents[1]; out=root/'results'/a.campaign/'stages'/a.name
out.mkdir(parents=True,exist_ok=False)
def utc():return datetime.now(timezone.utc).isoformat()
def save(data):
 tmp=out/'status.tmp';tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(out/'status.json')
status={'status':'running','name':a.name,'started_utc':utc(),'command':command,'timeout_seconds':a.timeout,
 'telemetry_scope':'device-wide GPU metrics; not a process-exclusive measurement'}
save(status);start=time.monotonic();samples=[]
with (out/'stdout.log').open('w') as log:
 proc=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 status['pid']=proc.pid;save(status)
 try:
  while proc.poll() is None:
   if time.monotonic()-start>a.timeout:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    status['status']='timeout';break
   if a.profile_gpu:
    try:
     r=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],text=True,capture_output=True,timeout=5)
     if r.returncode==0:
      vals=r.stdout.strip().splitlines()[0].split(',')
      sample={'utc':utc(),'elapsed_seconds':round(time.monotonic()-start,3),'memory_used_mib':int(vals[0]),'memory_total_mib':int(vals[1]),'gpu_util_percent':int(vals[2])}
      samples.append(sample)
      with (out/'gpu.jsonl').open('a') as f:f.write(json.dumps(sample)+'\n')
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
   time.sleep(2)
 except BaseException:
  try:os.killpg(proc.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  proc.wait();status['status']='interrupted';raise
 finally:
  status.update(finished_utc=utc(),seconds=round(time.monotonic()-start,3),exit_code=proc.returncode)
  if status['status']=='running':status['status']='completed' if proc.returncode==0 else 'failed'
  if samples:status['peak_device_memory_mib']=max(s['memory_used_mib'] for s in samples)
  save(status)
print(json.dumps(status,indent=2),flush=True)
raise SystemExit(0 if status['status']=='completed' else 1)
