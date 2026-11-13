"""Independent release checks using compact rows, CSVs and immutable generation hashes."""
from pathlib import Path
import argparse,csv,json,hashlib
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();base=a.directory
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=read(base/'analysis/summary.json');keys=set();raw_count=0
for run in (base/'raw').iterdir():
 if not run.is_dir():continue
 m=read(run/'manifest.json')
 for item in m['items']:
  c=run/'candidates'/item['key'];g=read(c/'generation.json')
  assert sha(c/'raw.txt')==g['raw_sha256'] and sha(c/'prompt.txt')==g['prompt_sha256']
  if (c/'wire_prompt.txt').exists():assert sha(c/'wire_prompt.txt')==g['wire_prompt_sha256']
  assert (run.name,item['key']) not in keys;keys.add((run.name,item['key']));raw_count+=1
for model,run in s['primary_runs'].items():
 rows=read(base/'evaluations'/f'{run}.json')['rows'];assert len(rows)==18 and len({r['task_id'] for r in rows})==18
 for level in ['ALL','L0','L1','L2']:
  r=[x for x in rows if level=='ALL' or x['level']==level];op=[x for x in r if x['role']=='opportunity'];d=next(x for x in s['summary'] if x['model']==model and x['level']==level)
  actual={'n':len(r),'opportunity_n':len(op),'syntax_valid':sum(x['syntax_valid'] for x in r),'semantic_attempted':sum(x['semantic_attempted'] for x in r),'determinate':sum(x['determinate'] for x in r),'verified':sum(x['verified'] for x in r),'refuted':sum(x['status']=='refuted' for x in r),'effective':sum(x['effective_optimization'] for x in op)}
  assert all(actual[k]==d[k] for k in actual),(model,level,actual,d)
  if not d['determinate']:assert d['verified_fraction_of_determinate'] is None
for model,run in s['hint_runs'].items():
 rows=read(base/'evaluations'/f'{run}.json')['rows'];ids={r['task_id'] for r in rows};assert len(ids)==len(rows)==6
 initial=read(base/'evaluations'/f"{s['primary_runs'][model]}.json")['rows']
 for arm,rs in [('initial_matched',[r for r in initial if r['task_id'] in ids]),('shared_semantic_hint',rows)]:
  d=next(r for r in s['shared_hint_comparison'] if r['model']==model and r['arm']==arm)
  assert sum(r['verified'] for r in rs)==d['verified'] and sum(r['effective_optimization'] for r in rs)==d['effective']
with (base/'analysis/per_case.csv').open() as f:rows=list(csv.DictReader(f))
assert len(rows)==len({(r['run'],r['task_id'],r['arm']) for r in rows})
sel=read(base/'protocol/selected-profile.json');assert sel['primary_passed'] and all(x['gate']['passed'] for x in sel['primary_evidence'])
assert {e['model'] for e in sel['primary_evidence']}=={'compiler-ftd','qwen'}
for e in sel['primary_evidence']:
 record=read(base/'evaluations'/f"{e['run']}.json");rs=[r for r in record['rows'] if r['arm']=='native']
 assert len(rs)==6 and len({r['task_id'] for r in rs})==6
 origin=record['generation_origin_run']
 gs=[read(base/'raw'/origin/'candidates'/r['key']/'generation.json') for r in rs]
 assert all(g.get('error') is None for g in gs)
 det=[r for r in rs if r['determinate']]
 assert len(det)>=4 and all(any(r['level']==level for r in det) for level in ['L0','L1','L2'])
 assert any(r['task_id']=='dev_l2_forward' for r in det)
 assert sum(r['verified'] for r in rs)==e['gate']['verified']

for model,run in s['primary_runs'].items():
 if model in {'opt','identity'}:continue
 m=read(base/'raw'/run/'manifest.json');assert m['created_utc']>=read(base/'protocol/selection-primary.json')['created_utc']
for id in {r['task_id'] for r in read(base/'evaluations'/f"{s['primary_runs']['qwen']}.json")['rows']}:
 p1=base/'raw'/s['primary_runs']['qwen']/'candidates'/(id+'__native')/'prompt.txt';p2=base/'raw'/s['primary_runs']['compiler-ftd']/'candidates'/(id+'__native')/'prompt.txt';assert sha(p1)==sha(p2)
print(f'PASS: {raw_count} published generation records, all primary/paired counts, unique CSV rows, shared task prompts and gate ordering')
