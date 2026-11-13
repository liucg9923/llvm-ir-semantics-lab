"""Verify published tables against raw per-case scores and model-generation hashes."""
import argparse,csv,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();base=a.directory
with (base/'analysis/per_case.csv').open() as f:rows=list(csv.DictReader(f))
s=json.loads((base/'analysis/summary.json').read_text())
for group in s['summary']:
 subset=[r for r in rows if r['model']==group['model'] and r['arm']=='initial' and (group['level']=='ALL' or r['level']==group['level'])]
 opp=[r for r in subset if r['role']=='opportunity']
 actual={'n':len(subset),'opportunity_n':len(opp),'syntax_valid':sum(r['syntax_valid']=='True' for r in subset),'verified':sum(r['status']=='verified' for r in subset),'effective':sum(r['effective_optimization']=='True' for r in opp),'refuted':sum(r['status']=='refuted' for r in subset)}
 assert all(actual[k]==group[k] for k in actual),(group,actual)
for group in s['paired_feedback']:
 ids={r['task_id'] for r in rows if r['model']==group['model'] and r['arm']=='tool_feedback'}
 arm='initial' if group['arm']=='initial_matched' else group['arm']
 subset=[r for r in rows if r['model']==group['model'] and r['arm']==arm and r['task_id'] in ids]
 assert len(subset)==group['n']==12
 assert sum(r['status']=='verified' for r in subset)==group['verified']
 assert sum(r['effective_optimization']=='True' for r in subset if r['role']=='opportunity')==group['effective']
for run in (base/'raw').iterdir():
 meta=json.loads((run/'manifest.json').read_text());evaluations=json.loads((run/'results.json').read_text())
 assert len(meta['items'])==len(evaluations)
 for item in meta['items']:
  c=run/'candidates'/item['key'];g=json.loads((c/'generation.json').read_text())
  assert hashlib.sha256((c/'raw.txt').read_bytes()).hexdigest()==g['raw_sha256']
  assert hashlib.sha256((c/'prompt.txt').read_bytes()).hexdigest()==g['prompt_sha256']
print('PASS: summary counts, matched feedback denominators and all published FTD raw/prompt hashes')
