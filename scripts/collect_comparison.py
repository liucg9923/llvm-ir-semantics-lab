"""Assemble all three entrants from complete, matched, same-oracle run records."""
import argparse,csv,json,statistics
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from irsem.common import read_json,write_json,digest
from irsem.tasks import check_lock
p=argparse.ArgumentParser();p.add_argument('--campaign',default='campaign-ftd-v1');a=p.parse_args()
root=Path(__file__).resolve().parents[1];out=root/'results'/a.campaign/'analysis';out.mkdir(parents=True,exist_ok=True)
lock=check_lock(root);cfg=read_json(root/'configs/experiment.json')
initial={'opt':'opt-v2-rechecked-ftd','identity':'identity-v2-rechecked-ftd','qwen':'qwen-v2-rechecked-ftd','compiler_ftd':'compiler-ftd-v1'}
feedback={'qwen':'qwen-feedback-v2-rechecked-ftd','compiler_ftd':'compiler-ftd-feedback-v1'}
runs={}
for name in [*initial.values(),*feedback.values()]:
 path=root/'results'/name;meta=read_json(path/'manifest.json');rows=read_json(path/'results.json')
 assert meta['status']=='evaluated' and len(rows)==len(meta['items']),name
 assert meta['dataset_sha256']==lock['sha256'] and meta['config']==cfg,name
 assert len({r['key'] for r in rows})==len(rows),name
 runs[name]={'meta':meta,'rows':rows,'path':path}
eval_hashes={v['meta']['evaluation_code_sha256'] for v in runs.values()}
assert len(eval_hashes)==1, 'All results must be evaluated by the same oracle code'
ids={r['task_id'] for r in runs[initial['opt']]['rows']}
assert len(ids)==24
for name in initial.values():assert {r['task_id'] for r in runs[name]['rows']}==ids
for name in feedback.values():assert {(r['task_id'],r['arm']) for r in runs[name]['rows']}=={(id,arm) for id in cfg['feedback_ids'] for arm in ['self_review','tool_feedback']}
# Require the same task-prompt body; model-specific wire templates are recorded separately.
for id in ids:
 assert digest(runs[initial['qwen']]['path']/'candidates'/id/'prompt.txt')==digest(runs[initial['compiler_ftd']]['path']/'candidates'/id/'prompt.txt'),id

def stats(rows):
 opp=[r for r in rows if r['role']=='opportunity']
 return {'n':len(rows),'opportunity_n':len(opp),'syntax_valid':sum(bool(r['syntax_valid']) for r in rows),
  'semantic_checks_attempted':sum('alive2_log' in r for r in rows),'verified':sum(r['status']=='verified' for r in rows),'effective':sum(bool(r['effective_optimization']) for r in opp),
  'refuted':sum(r['status']=='refuted' for r in rows),'unchanged':sum(bool(r['unchanged']) for r in rows),'statuses':dict(Counter(r['status'] for r in rows))}
summary=[];flat=[];paired=[];matched=[];timing=[]
for model,name in initial.items():
 for level in ['ALL','L0','L1','L2']:
  rows=[r for r in runs[name]['rows'] if level=='ALL' or r['level']==level]
  summary.append({'model':model,'run':name,'arm':'initial','level':level,**stats(rows)})
for model,name in feedback.items():
 parent={r['task_id']:r for r in runs[initial[model]]['rows']}
 revised={(r['task_id'],r['arm']):r for r in runs[name]['rows']}
 matched.append({'model':model,'arm':'initial_matched',**stats([parent[id] for id in cfg['feedback_ids']])})
 for arm in ['self_review','tool_feedback']:
  rs=[revised[id,arm] for id in cfg['feedback_ids']]
  group=[]
  for r in rs:
   b=parent[r['task_id']]
   q={'model':model,'task_id':r['task_id'],'level':r['level'],'role':r['role'],'arm':arm,
      'initial_status':b['status'],'revised_status':r['status'],'initial_effective':b['effective_optimization'],
      'revised_effective':r['effective_optimization'],'revised_unchanged':r['unchanged'],
      'gained_verification':b['status']!='verified' and r['status']=='verified',
      'lost_verification':b['status']=='verified' and r['status']!='verified',
      'new_proven_error':b['status']=='verified' and r['status']=='refuted'}
   paired.append(q);group.append(q)
  matched.append({'model':model,'arm':arm,**stats(rs),**{k:sum(r[k] for r in group) for k in ['gained_verification','lost_verification','new_proven_error']}})
for model,name in [*initial.items(),*feedback.items()]:
 for r in runs[name]['rows']:
  gen=read_json(runs[name]['path']/'candidates'/r['key']/'generation.json')
  raw=runs[name]['path']/'candidates'/r['key']/'raw.txt'
  assert digest(raw)==gen['raw_sha256'],str(raw)
  flat.append({'model':model,'run':name,'task_id':r['task_id'],'key':r['key'],'arm':r['arm'],'level':r['level'],'role':r['role'],
   'status':r['status'],'syntax_valid':r['syntax_valid'],'effective_optimization':r['effective_optimization'],'unchanged':r['unchanged'],
   'generation_seconds':gen.get('seconds'),'prompt_tokens':gen.get('prompt_tokens'),'output_tokens':gen.get('output_tokens'),
   'instruction_count':r.get('candidate_metrics',{}).get('instruction_count')})
 for arm in sorted({r['arm'] for r in runs[name]['rows']}):
  group=[r for r in flat if r['run']==name and r['arm']==arm];times=[r['generation_seconds'] for r in group if r['generation_seconds'] is not None]
  timing.append({'model':model,'arm':arm,'n':len(group),'timed_n':len(times),'median_generation_seconds':statistics.median(times) if times else None,
   'total_generation_seconds':sum(times),'input_tokens':sum(r['prompt_tokens'] or 0 for r in group),'output_tokens':sum(r['output_tokens'] or 0 for r in group)})
for filename,rows in [('per_case.csv',flat),('paired_feedback.csv',paired)]:
 with (out/filename).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
write_json(out/'summary.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'dataset_sha256':lock['sha256'],
 'evaluation_code_sha256':next(iter(eval_hashes)),'initial_runs':initial,'feedback_runs':feedback,'summary':summary,'paired_feedback':matched,'timing':timing,
 'compiler_model':read_json(root/'configs/compiler-ftd.json'),'runtime':read_json(root/'configs/llama-cpp.json'),
 'limits':['24 authored no-loop single-function cases; not a broad leaderboard.','FTD community F16 conversion and Qwen HF FP16 use different inference implementations.','Upstream conversion identity is attributed by the publisher, not independently bitwise verified.','Direct-IR task transfer, not the FTD paper pass-selection benchmark.','Feedback compares the same 12 predeclared tasks, not 24 initial versus 12 repaired.','Identity is a control, not a fourth competitor.','Original v2 outputs were revalidated, not regenerated.']})
write_json(out/'ANALYSIS_CHECKS.json',{'passed':True,'same_dataset_and_config':True,'same_evaluator_hash':True,'same_initial_prompt_text_for_both_llms':True,'all_24_initial_cases_per_group':True,'all_12_matched_feedback_cases_per_model':True,'all_raw_hashes_match':True,'prior_output_revalidation':read_json(root/'results/campaign-ftd-v1/revalidation.json')})
lines=['# 三方同题比较','', '专用组使用社区 LLM Compiler 7B-FTD F16 GGUF；它不同于原计划的官方基础模型，且与 Qwen 的推理后端不同。所有原始输出保留。','',
 '| 组别 | 层级 | 合法 IR | 验证通过 | 有效优化 | 已证反例 |','|---|---|---:|---:|---:|---:|']
for r in summary:lines.append(f"| {r['model']} | {r['level']} | {r['syntax_valid']}/{r['n']} | {r['verified']}/{r['n']} | {r['effective']}/{r['opportunity_n']} | {r['refuted']} |")
lines+=['','## 同题反馈（每组 12 题，其中 6 个优化机会）','','| 模型 | 条件 | 验证通过 | 有效优化 | 已证反例 |','|---|---|---:|---:|---:|']
for r in matched:lines.append(f"| {r['model']} | {r['arm']} | {r['verified']}/{r['n']} | {r['effective']}/{r['opportunity_n']} | {r['refuted']} |")
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'initial':[r for r in summary if r['level']=='ALL'],'paired_feedback':matched,'timing':timing},ensure_ascii=False,indent=2))
