"""Preserve every non-verified FTD case as inspectable evidence, without rerunning a model."""
from pathlib import Path
import json
from irsem.common import read_json,write_json
from irsem.tasks import load_tasks
from irsem.ir import extract_ir
root=Path(__file__).resolve().parents[1];tasks={t.id:t for t in load_tasks(root)}
out=root/'results/campaign-ftd-v1/analysis/case_evidence';out.mkdir(parents=True,exist_ok=True)
index=[]
for name in ['compiler-ftd-v1','compiler-ftd-feedback-v1']:
 for r in read_json(root/'results'/name/'results.json'):
  if r['status']=='verified':continue
  raw=(root/'results'/name/'candidates'/r['key']/'raw.txt').read_text()
  dest=out/name/r['key'];dest.mkdir(parents=True,exist_ok=True)
  (dest/'source.ll').write_text(tasks[r['task_id']].text());(dest/'raw.txt').write_text(raw)
  try:(dest/'candidate.ll').write_text(extract_ir(raw))
  except ValueError:pass
  write_json(dest/'evaluation.json',r)
  index.append({'run':name,'task_id':r['task_id'],'key':r['key'],'arm':r['arm'],'status':r['status'],'directory':str(dest.relative_to(out))})
write_json(out/'index.json',index)
print(json.dumps({'saved_nonverified_cases':len(index)}))
