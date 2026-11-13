"""Application-level accept-or-fallback replay. Never counts fallback as model success."""
from pathlib import Path
from irsem.common import read_json,write_json,ProcessResult
from irsem.evaluate import alive_status
from irsem.v3.dataset import tasks
from irsem.v3.evaluate import evaluate
from irsem.v3.control import require_frozen
root=Path(__file__).resolve().parents[1];require_frozen(root);cfg=read_json(root/'configs/experiment-v3.json');byid={t.id:t for t in tasks(root,'test')}
out=root/'results/campaign-v3/analysis/application';out.mkdir(parents=True,exist_ok=True)
for model in ['compiler-ftd','qwen']:
 rows=[]
 for r in read_json(root/'results'/('v3b-formal-'+model)/'results.json'):
  t=byid[r['task_id']];proof=r.get('alive2_log',{});accepted=bool(proof and 'returncode' in proof and not any(r.get('admission',{}).values()) and alive_status(ProcessResult(**proof))=='verified');ir=r['evaluation_ir'] if accepted else t.text()
  ev=evaluate(root,t,ir,cfg)
  d=out/model/t.id;d.mkdir(parents=True,exist_ok=True);(d/'selected.ll').write_text(ir);write_json(d/'evaluation.json',ev)
  rows.append({'task_id':t.id,'role':t.spec['role'],'selected_from':'model_candidate' if accepted else 'original_fallback','status':ev['status'],'effective':ev['effective_optimization']})
 result={'model':model,'kind':'application_replay_not_model_accuracy','selection_uses_holdout_results':False,'policy':'Accept only supported candidates with an Alive2 proof; otherwise use original. Selection does not read holdout outcomes. Validate the selected result afterwards.','n':len(rows),'accepted_model_candidates':sum(r['selected_from']=='model_candidate' for r in rows),'original_fallbacks':sum(r['selected_from']=='original_fallback' for r in rows),'verified':sum(r['status']=='verified' for r in rows),'effective':sum(r['effective'] for r in rows),'opportunity_n':sum(r['role']=='opportunity' for r in rows),'rows':rows}
 write_json(out/model/'summary.json',result);print({k:v for k,v in result.items() if k!='rows'})
