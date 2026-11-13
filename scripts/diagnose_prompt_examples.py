"""Post-hoc development-only prompt sensitivity probe; never replaces formal scores."""
from pathlib import Path
from irsem.common import read_json,write_json
from irsem.tasks import load_tasks
from irsem.prompts import RULES,task_request
from irsem.gguf import GGUFModel
from irsem.runs import _start,_save,_infer,evaluate_run
from irsem.toolchain import configure,require_receipt
root=Path(__file__).resolve().parents[1];configure(root);require_receipt(root)
out=root/'results/compiler-ftd-dev-noexamples-v1';tasks=load_tasks(root,'dev');spec=read_json(root/'configs/compiler-ftd.json')
items=[{'key':t.id,'task_id':t.id,'arm':'dev_noexamples'} for t in tasks]
meta=_start(root,out,'gguf',spec,'dev',True,items)
meta['diagnostic']={'kind':'posthoc_development_only','control_run':'compiler-ftd-dev-v1',
 'only_prompt_change':'Remove the few-shot example sections; retain RULES, Current task and task_request verbatim.',
 'selection':'All six existing dev cases, no formal cases and no new examples.',
 'score_boundary':'Not a tuned replacement of formal results; cannot establish a general model ranking.'}
engine=GGUFModel(spec,meta['config']);meta['inference_environment']=engine.info
for t in tasks:
 prompt=RULES+'\n\nCurrent task:\n'+task_request(t)
 _save(out,t.id,prompt,_infer(engine,prompt));print('generated diagnostic',t.id,flush=True)
engine.close();meta['status']='generated';write_json(out/'manifest.json',meta)
evaluate_run(root,out)
