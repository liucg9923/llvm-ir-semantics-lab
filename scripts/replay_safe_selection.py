"""Post-hoc application replay. Not an additional model-accuracy experiment.
Select using syntax/contracts, Alive2 proof and the declared optimization goal;
never inspect holdout test outputs when deciding which candidate to select.
"""
import json
from pathlib import Path
from irsem.common import read_json,write_json,ProcessResult
from irsem.tasks import load_tasks
from irsem.toolchain import configure,require_receipt
from irsem.evaluate import alive_status,evaluate
from irsem.ir import extract_ir
root=Path(__file__).resolve().parents[1];configure(root);require_receipt(root)
cfg=read_json(root/'configs/experiment.json');tasks={t.id:t for t in load_tasks(root)}
initial={r['task_id']:r for r in read_json(root/'results/qwen-v2/results.json')}
feedback={r['task_id']:r for r in read_json(root/'results/qwen-feedback-v2/results.json') if r['arm']=='tool_feedback'}
out=root/'results/campaign-v1/analysis/application_replay';out.mkdir(parents=True,exist_ok=True)
rows=[]
for id in cfg['feedback_ids']:
 choices=[]
 for name,row,path in [('initial',initial[id],root/'results/qwen-v2/candidates'/id/'raw.txt'),
                       ('tool_feedback',feedback[id],root/'results/qwen-feedback-v2/candidates'/(id+'__tool_feedback')/'raw.txt')]:
  proof=row.get('alive2_log',{})
  if not row.get('syntax_valid') or row.get('contract_errors') or 'returncode' not in proof:continue
  if alive_status(ProcessResult(**proof))!='verified':continue
  rank=(int(row.get('goal_met') is True),-row['candidate_metrics']['instruction_count'],int(name=='initial'))
  choices.append((rank,name,extract_ir(path.read_text())))
 if choices:
  _,choice,candidate=max(choices,key=lambda x:x[0])
 else:choice='original_fallback';candidate=tasks[id].text()
 # Selection above never reads differential/holdout fields. Validate the chosen program afterwards.
 evaluation=evaluate(tasks[id],candidate,cfg,allow_execution=True)
 p=out/id;p.mkdir(exist_ok=True);(p/'selected.ll').write_text(candidate);write_json(p/'evaluation.json',evaluation)
 rows.append({'task_id':id,'selected_from':choice,'status':evaluation['status'],
              'role':tasks[id].spec['role'],'effective_optimization':evaluation['effective_optimization']})
summary={'kind':'posthoc_application_replay_not_model_accuracy','task_n':len(rows),
 'candidate_acceptances':sum(r['selected_from']!='original_fallback' for r in rows),
 'original_fallbacks':sum(r['selected_from']=='original_fallback' for r in rows),
 'verified':sum(r['status']=='verified' for r in rows),
 'effective_optimizations':sum(r['effective_optimization'] for r in rows),
 'opportunity_n':sum(r['role']=='opportunity' for r in rows),
 'policy':'Reject candidates without a valid supported-domain Alive2 proof; prefer goal completion, then fewer IR instructions, then initial candidate; fall back to original if no candidate is accepted. Selection does not inspect holdout test outputs.',
 'boundary':'This combines a deterministic verifier/selector with existing model outputs. It is not a new Qwen success rate and is not evidence that tool feedback alone guarantees correctness.',
 'rows':rows}
write_json(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
