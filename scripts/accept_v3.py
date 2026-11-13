"""Oracle validation before any model pilot or formal generation."""
from pathlib import Path
import tempfile,re,json
from datetime import datetime,timezone
from irsem.common import read_json,write_json,run_process,digest
from irsem.tasks import Task
from irsem.toolchain import configure,fingerprint
from irsem.evaluate import tool
from irsem.sandbox import probe
from irsem.v3.dataset import tasks
from irsem.v3.evaluate import evaluate
from irsem.v3.control import snapshot
root=Path(__file__).resolve().parents[1];configure(root);cfg=read_json(root/'configs/experiment-v3.json');records=[]
for split in ['dev','test']:
 for t in tasks(root,split):
  for variant in ['source','reference','mutant']:
   row=evaluate(root,t,t.text(variant),cfg)
   expected='refuted' if variant=='mutant' else 'verified'
   passed=row['status']==expected
   if variant=='reference' and t.spec['role']=='opportunity':passed=passed and row['effective_optimization']
   records.append({'id':t.id+'/'+variant,'passed':bool(passed),'expected':expected,'evaluation':row})
   print(t.id,variant,row['status'],'PASS' if passed else 'FAIL',flush=True)
  if split=='test':
   with tempfile.TemporaryDirectory() as td:
    dst=Path(td)/'opt.ll';p=run_process([tool('opt'),'-S','-verify-each','-passes='+t.spec['pipeline'],str(t.file('source')),'-o',str(dst)],60)
    if p.returncode:raise RuntimeError('Baseline pass failed')
    raw=dst.read_text();row=evaluate(root,t,raw,cfg)
    passed=row['status']=='verified' and (t.spec['role']!='opportunity' or row['effective_optimization'])
    records.append({'id':t.id+'/opt','passed':bool(passed),'expected':'verified_and_declared_goal','raw':raw,'evaluation':row})
    print(t.id,'opt',row['status'],row['effective_optimization'],'PASS' if passed else 'FAIL',flush=True)
# Format/context/attribute fixtures use the same sources and the exact evaluator, never LLM output repair.
u=next(t for t in tasks(root,'dev') if t.id=='dev_l0_and_all')
x=next(t for t in tasks(root,'dev') if t.id=='dev_l0_xor_self')
m=next(t for t in tasks(root,'test') if t.id=='v3_store_copy')
fixtures=[]
fixtures.append(('alpha_rename',u,u.text('reference').replace('%x','%value'),'verified'))
fixtures.append(('nested_single_container',u,'```llvm\n<code>\n'+u.text('reference')+'</code>\n```','verified'))
fixtures.append(('two_candidates',u,'<code>'+u.text('reference')+'</code>\n<code>'+u.text('source')+'</code>','format_error'))
fixtures.append(('missing_target_inherits_declared_context',u,re.sub(r'^target[^\n]*\n','',u.text('reference'),flags=re.M),'verified'))
fixtures.append(('wrong_target_arch',u,u.text('reference').replace('x86_64-pc-linux-gnu','aarch64-unknown-linux-gnu'),'interface_mismatch'))
fixtures.append(('wrong_endianness',u,u.text('reference').replace('"e-p:','"E-p:'),'interface_mismatch'))
fixtures.append(('false_memory_none',m,m.text().replace('minsize nounwind','memory(none) minsize nounwind'),'unsupported_ir'))
fixtures.append(('new_noalias_assumption',m,m.text().replace('ptr noundef %p','ptr noalias noundef %p'),'unproved_input_assumption'))
fixtures.append(('pure_memory_none',u,u.text('reference').replace(') {',') memory(none) {'),'verified'))
fixtures.append(('missing_function',u,'target triple = "x86_64-pc-linux-gnu"\n','interface_mismatch'))
fixtures.append(('wrong_return',u,u.text('reference').replace('ret i32 %x','ret i32 0'),'refuted'))
# Retain instruction flags: a new nsw on a wrapping increment must be refuted.
with tempfile.TemporaryDirectory() as td:
 d=Path(td);d.joinpath('source.ll').write_text(u.text('reference').replace('ret i32 %x','%sum = add i32 %x, 1\n ret i32 %sum'))
 spec={**u.spec,'id':'fixture_nsw','directory':str(d),'role':'guard','goal':{}}
 t=Task(root,spec);fixtures.append(('new_nsw_is_not_removed',t,t.text().replace('add i32','add nsw i32'),'refuted'))
 for name,task,raw,expected in fixtures:
  row=evaluate(root,task,raw,cfg);records.append({'id':name,'passed':row['status']==expected,'expected':expected,'raw':raw,'source':task.text(),'evaluation':row});print(name,row['status'],expected,flush=True)
for id,run,expected in [('dev_l0_xor_self','compiler-ftd-dev-v1','verified'),('dev_l0_and_all','compiler-ftd-dev-v1','refuted'),('dev_l0_and_all','compiler-ftd-dev-noexamples-v1','verified')]:
 t=next(t for t in tasks(root,'dev') if t.id==id);p=root/'results/published/compiler-ftd-v1/raw'/run/'candidates'/id/'raw.txt';raw=p.read_text()
 row=evaluate(root,t,raw,cfg);records.append({'id':'archived/'+run+'/'+id,'passed':row['status']==expected,'expected':expected,'raw_sha256':digest(p),'evaluation':row});print('archived',id,row['status'],expected,flush=True)
sandbox=probe(tool('clang'))
result={'passed':all(r['passed'] for r in records) and sandbox['passed'],'created_utc':datetime.now(timezone.utc).isoformat(),'count':len(records),'files':snapshot(root),'toolchain':fingerprint(root),'inspector_sha256':digest(root/'.toolchain/bin/irsem-inspect'),'sandbox':sandbox,'records':records}
write_json(root/'results/campaign-v3/oracle-acceptance.json',result)
print(json.dumps({'passed':result['passed'],'count':len(records),'failures':[{'id':r['id'],'status':r['evaluation']['status']} for r in records if not r['passed']]}),flush=True)
raise SystemExit(0 if result['passed'] else 1)
