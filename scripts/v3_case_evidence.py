"""Keep all failures plus exact-candidate illustrative diagnostic replays."""
from pathlib import Path
from irsem.common import read_json,write_json
from irsem.v3.dataset import tasks
from irsem.v3.evaluate import evaluate
from irsem.v3.control import require_frozen
root=Path(__file__).resolve().parents[1];require_frozen(root);cfg=read_json(root/'configs/experiment-v3.json');byid={t.id:t for t in tasks(root,'test')}
out=root/'results/campaign-v3/analysis/cases';out.mkdir(parents=True,exist_ok=True);index=[]
for model in ['compiler-ftd','qwen']:
 for phase in ['formal','hint']:
  run=root/'results'/('v3b-'+phase+'-'+model)
  if not (run/'results.json').exists():continue
  for row in read_json(run/'results.json'):
   if row['status']=='verified':continue
   id=row['task_id'];d=out/model/phase/id;d.mkdir(parents=True,exist_ok=True)
   raw=(run/'candidates'/row['key']/'raw.txt').read_text();(d/'source.ll').write_text(byid[id].text());(d/'raw.txt').write_text(raw)
   if row.get('canonical_ir'):(d/'candidate.parsed.ll').write_text(row['canonical_ir'])
   if row.get('evaluation_ir'):(d/'candidate.evaluated.ll').write_text(row['evaluation_ir'])
   write_json(d/'evaluation.json',row)
   entry={'model':model,'phase':phase,'task_id':id,'status':row['status'],'role':row['role'],'path':str(d.relative_to(out))}
   if row['status']=='refuted':
    replay=evaluate(root,byid[id],raw,cfg,kind='diagnostic');write_json(d/'illustrative-diagnostic-replay.json',{'label':'Post-score illustration; not added to the formal denominator and not supplied to models.','evaluation':replay})
    entry['diagnostic_counterexample']=replay.get('differential',{}).get('-O0',{}).get('counterexample')
    entry['holdout_counterexample']=row.get('differential',{}).get('-O0',{}).get('counterexample')
   index.append(entry)
write_json(out/'index.json',index)
print(index)
