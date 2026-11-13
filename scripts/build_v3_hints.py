"""Matched diagnostic hints from authored mistakes, not from any model output."""
from pathlib import Path
from irsem.common import read_json,write_json,digest
from irsem.v3.dataset import tasks
from irsem.v3.evaluate import evaluate
root=Path(__file__).resolve().parents[1]
if (root/'results/campaign-v3/hints.json').exists():raise SystemExit('Refuse to overwrite diagnostic hint evidence')
cfg=read_json(root/'configs/experiment-v3.json')
ids=cfg['hint_ids']+['dev_l0_and_all','dev_l1_select_equal','dev_l2_forward'];alltasks={t.id:t for s in ['dev','test'] for t in tasks(root,s)}
result={}
fmt=lambda x:f'0x{int(x):08x}'
for id in ids:
 t=alltasks[id];ev=evaluate(root,t,t.text('mutant'),cfg,kind='diagnostic')
 if ev['status']!='refuted':raise ValueError('Authored mutant is not refuted: '+id)
 d=ev['differential']['-O0']
 if d['status']!='mismatch' or ev['differential']['-O2']['status']!='mismatch':raise ValueError('Need concrete diagnostic counterexample at both optimization levels')
 ex=d['counterexample'];inp=ex['input'];src=ex['source'].split();bad=ex['candidate'].split()
 if t.spec['abi']=='memory':
  text=f"Initial uint32 cells are [{fmt(inp[0])}, {fmt(inp[1])}]; p points to cell 0 and q points to cell {0 if inp[2] else 1}. The original returns {fmt(src[0])} with final cells [{fmt(src[1])}, {fmt(src[2])}]. An authored incorrect transformation returns {fmt(bad[0])} with final cells [{fmt(bad[1])}, {fmt(bad[2])}]."
 else:
  names=['x','y'];text='For i32 bit-pattern inputs '+', '.join(names[i]+'='+fmt(x) for i,x in enumerate(inp))+f", the original returns {fmt(src[0])}; an authored incorrect transformation returns {fmt(bad[0])}."
 result[id]={'text':text,'task_id':id,'provenance':'authored_mutant_not_model_output','source_sha256':digest(t.file('source')),'mutant_sha256':digest(t.file('mutant')),'counterexample':ex,'input_set':'diagnostic_only','evaluation':ev}
 print('shared hint',id,ex,flush=True)
write_json(root/'results/campaign-v3/hints.json',result)
