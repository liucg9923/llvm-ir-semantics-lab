"""Preserve generation evidence while re-binding unchanged scoring/data to revision B."""
from pathlib import Path
from datetime import datetime,timezone
import shutil,json
from irsem.common import read_json,write_json,digest
from irsem.v3.control import require_frozen,gate
from irsem.v3.runner import evaluate_saved
from irsem.v3.dataset import tasks
from irsem.v3.prompts import native
root=Path(__file__).resolve().parents[1];new=require_frozen(root);old=read_json(root/'results/campaign-v3/calibration-A/frozen.json')
critical=['src/irsem/v3/evaluate.py','src/irsem/v3/policy.py','src/irsem/v3/extract.py','src/irsem/differential.py','src/irsem/sandbox.py','src/irsem/evaluate.py','src/irsem/common.py','tools/v3_ir_inspect.cpp']
for name in critical+[n for n in old['files'] if n.startswith('tasks/')]:assert old['files'][name]==new['files'][name],name
assert old['inspector_sha256']==new['inspector_sha256']
oldcfg=read_json(root/'results/campaign-v3/calibration-A/snapshot/configs/experiment-v3.json');cfg=read_json(root/'configs/experiment-v3.json')
for k in ['seed','dtype','do_sample','num_beams','repetition_penalty','no_repeat_ngram_size','max_input_tokens','max_new_tokens','max_generation_seconds','alive2_args','tool_timeout_seconds','execution_timeout_seconds','random_inputs']:
 assert oldcfg[k]==cfg[k],k
mapping={'v3-pilot-compiler-ftd':'v3b-pilot-compiler-ftd','v3-pilot-qwen':'v3b-pilot-qwen-native','v3-formal-opt':'v3b-formal-opt','v3-formal-identity':'v3b-formal-identity'}
records=[]
for before,after in mapping.items():
 src=root/'results'/before;dst=root/'results'/after
 if dst.exists():raise ValueError('Refuse to overwrite revalidation')
 dst.mkdir();shutil.copytree(src/'candidates',dst/'candidates');shutil.copyfile(src/'input-facts.json',dst/'input-facts.json')
 m=read_json(src/'manifest.json');assert m['protocol_sha256']==old['sha256'];phase=m['phase']
 m['generation_provenance']={'original_run':before,'original_protocol_sha256':m['protocol_sha256'],'original_manifest_sha256':digest(src/'manifest.json'),'original_config':m['config'],'new_model_calls':0}
 m.update(protocol_sha256=new['sha256'],config=cfg,status='generated',revalidated_utc=datetime.now(timezone.utc).isoformat())
 m['profile']='native_single_v1' if m['model']=='qwen' else 'native_bounded_v1'
 write_json(dst/'manifest.json',m)
 rows=evaluate_saved(root,dst,m,tasks(root,'dev' if phase=='pilot' else 'test'))
 prior={r['key']:r for r in read_json(src/'results.json')}
 for r in rows:
  for field in ['status','syntax_valid','semantic_attempted','determinate','verified','goal_met','effective_optimization']:
   assert r[field]==prior[r['key']][field],(before,r['key'],field)
 if phase=='pilot':
  selected=[r for r in rows if r['arm']=='native'];gens=[read_json(dst/'candidates'/r['key']/'generation.json') for r in selected];write_json(dst/'gate.json',gate(root,selected,gens))
 if m['model']=='compiler-ftd':
  facts=read_json(dst/'input-facts.json')
  for t in tasks(root,'dev'):
   c=dst/'candidates'/(t.id+'__native');prompt=native(t,facts[t.id]);assert (c/'prompt.txt').read_text()==prompt
   assert (c/'wire_prompt.txt').read_text()=='<s>[INST] '+prompt+' [/INST]'
 records.append({'source':before,'destination':after,'n':len(rows),'all_outcomes_unchanged':True,'new_model_calls':0})
write_json(root/'results/campaign-v3/revalidation-B.json',{'passed':True,'unchanged_scoring_and_tasks':True,'unchanged_numeric_generation_settings':True,'records':records,'new_model_calls':0})
