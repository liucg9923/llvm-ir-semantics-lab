"""Illustrative concrete execution of exact selected raw candidates; no score changes."""
from pathlib import Path
from irsem.common import read_json,write_json,digest
from irsem.tasks import load_tasks
from irsem.ir import extract_ir
from irsem.differential import compare
from irsem.evaluate import tool
from irsem.toolchain import configure,require_receipt
root=Path(__file__).resolve().parents[1];configure(root);require_receipt(root)
tasks={t.id:t for t in load_tasks(root)};cfg=read_json(root/'configs/experiment.json')
out=root/'results/campaign-ftd-v1/analysis/illustrative_replay';records=[]
for label,id,run in [('formal_add_fold','l0_add_fold','compiler-ftd-v1'),('dev_and_with_examples','dev_l0_and_all','compiler-ftd-dev-v1'),('dev_and_without_examples','dev_l0_and_all','compiler-ftd-dev-noexamples-v1')]:
 t=tasks[id];candidate=extract_ir((root/'results'/run/'candidates'/id/'raw.txt').read_text())
 # These selected integer-only cases have one i32 parameter and no calls.
 import re
 assert len(re.findall(r'^define\b',candidate,re.M))==1
 assert re.search(r'define (?:dso_local )?i32 @f\(i32 noundef %\w+\)',candidate)
 assert not re.search(r'\b(?:call|invoke|callbr)\b',candidate)
 dest=out/label;dest.mkdir(parents=True,exist_ok=True)
 (dest/'source.ll').write_text(t.text());(dest/'candidate.ll').write_text(candidate)
 if label=='formal_add_fold' and (out/'l0_add_fold/replay.json').exists():
  old=out/'l0_add_fold';assert digest(old/'source.ll')==digest(dest/'source.ll') and digest(old/'candidate.ll')==digest(dest/'candidate.ll')
  result=read_json(old/'replay.json')['result']
 else:result=compare(t,candidate,tool('clang'),kind='diagnostic',allow_execution=True,timeout=cfg['execution_timeout_seconds'],random_count=cfg['random_inputs'])
 record={'kind':'posthoc_exact_candidate_native_diagnostic','run':run,'task_id':id,'candidate_modified':False,'formal_score_changed':False,
   'boundary':'Concrete diagnostic inputs only. Source/candidate attributes, metadata and targets are unmodified; output contract still fails. A finite match is not an all-input proof.',
   'source_sha256':digest(dest/'source.ll'),'candidate_sha256':digest(dest/'candidate.ll'),'result':result}
 write_json(dest/'replay.json',record);records.append({'label':label,**record})
write_json(out/'summary.json',records)
for r in records:print(r['label'],r['result'])
