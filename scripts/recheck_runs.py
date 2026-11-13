"""Revalidate immutable v2 raw outputs after an adapter-only code change; no model calls."""
from pathlib import Path
import json,shutil
from irsem.common import read_json,write_json,digest
from irsem.runs import evaluate_run
from irsem.toolchain import require_receipt
root=Path(__file__).resolve().parents[1];require_receipt(root)
records=[]
for name in ['opt-v2','identity-v2','qwen-v2','qwen-feedback-v2']:
 src=root/'results'/name;dest=root/'results'/(name+'-rechecked-ftd')
 if dest.exists():raise SystemExit('Refuse to overwrite revalidation: '+str(dest))
 dest.mkdir();shutil.copytree(src/'candidates',dest/'candidates')
 meta=read_json(src/'manifest.json');meta['status']='generated'
 meta['revalidation']={'original_run':name,'original_manifest_sha256':digest(src/'manifest.json'),
   'original_results_sha256':digest(src/'results.json'),'new_model_calls':0,
   'reason':'Revalidate the exact existing outputs under the current receipt after adding the GGUF adapter.'}
 write_json(dest/'manifest.json',meta)
 rows=evaluate_run(root,dest);before={r['key']:r for r in read_json(src/'results.json')}
 fields=['status','syntax_valid','contract_errors','goal_met','effective_optimization','unchanged']
 diff=[{'key':r['key'],'field':k,'old':before[r['key']].get(k),'new':r.get(k)} for r in rows for k in fields if before[r['key']].get(k)!=r.get(k)]
 records.append({'original':name,'rechecked':dest.name,'n':len(rows),'state_differences':diff,'raw_files_identical':all(digest(p)==digest(dest/'candidates'/p.relative_to(src/'candidates')) for p in (src/'candidates').rglob('*') if p.is_file())})
 if diff:raise RuntimeError('Revalidation disagreement: '+json.dumps(diff))
write_json(root/'results/campaign-ftd-v1/revalidation.json',{'passed':all(x['raw_files_identical'] for x in records),'records':records,'new_model_calls':0})
