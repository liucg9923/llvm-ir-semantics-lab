"""Collect matched experiment results without dropping unsuccessful candidates."""
import argparse,csv,hashlib,json,statistics,tarfile
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter

p=argparse.ArgumentParser();p.add_argument('--campaign',default='campaign-v1')
p.add_argument('--qwen',default='qwen-v2');p.add_argument('--feedback',default='qwen-feedback-v2');p.add_argument('--dev',default='qwen-dev-v2')
p.add_argument('--baseline',default='opt-v2');p.add_argument('--identity',default='identity-v2');p.add_argument('--extra-run',action='append',default=[])
a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'results'/a.campaign/'analysis';out.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
lock=read(root/'tasks/dataset.lock.json');cfg=read(root/'configs/experiment.json')
runs={}
for name in [a.baseline,a.identity,a.qwen,a.feedback]:
 path=root/'results'/name;meta=read(path/'manifest.json');rows=read(path/'results.json')
 if meta['status']!='evaluated' or len(rows)!=len(meta['items']):raise RuntimeError('Incomplete run: '+name)
 if meta['dataset_sha256']!=lock['sha256']:raise RuntimeError('Dataset mismatch: '+name)
 runs[name]={'meta':meta,'rows':rows,'path':path}
code_hashes={v['meta'].get('evaluation_code_sha256') for v in runs.values()}
if len(code_hashes)!=1:raise RuntimeError('Evaluator source mismatch')
flat=[]
for name,v in runs.items():
 for row in v['rows']:
  gen=read(v['path']/'candidates'/row['key']/'generation.json')
  flat.append({'run':name,'task_id':row['task_id'],'level':row['level'],'role':row['role'],'arm':row['arm'],
    'status':row['status'],'syntax_valid':row['syntax_valid'],'verified':row['status']=='verified',
    'effective_optimization':row['effective_optimization'],'unchanged':row['unchanged'],
    'generation_seconds':gen.get('seconds'),'prompt_tokens':gen.get('prompt_tokens'),'output_tokens':gen.get('output_tokens'),
    'ir_instruction_count':row.get('candidate_metrics',{}).get('instruction_count'),
    'llvm_verify_seconds':row.get('syntax_log',{}).get('seconds'),
    'alive2_seconds':row.get('alive2_log',{}).get('seconds')})
with (out/'per_case.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(flat[0]),lineterminator='\n');w.writeheader();w.writerows(flat)
summary=[]
for name,v in runs.items():
 for arm in sorted({r['arm'] for r in v['rows']}):
  for level in ['ALL','L0','L1','L2']:
   rows=[r for r in v['rows'] if r['arm']==arm and (level=='ALL' or r['level']==level)]
   opp=[r for r in rows if r['role']=='opportunity']
   summary.append({'run':name,'arm':arm,'level':level,'n':len(rows),'opportunity_n':len(opp),
     'syntax_valid':sum(r['syntax_valid'] for r in rows),'verified':sum(r['status']=='verified' for r in rows),
     'effective':sum(r['effective_optimization'] for r in opp),'refuted':sum(r['status']=='refuted' for r in rows),
     'unchanged':sum(r['unchanged'] for r in rows),'statuses':dict(Counter(r['status'] for r in rows))})
parent={r['task_id']:r for r in runs[a.qwen]['rows']};repair={(r['task_id'],r['arm']):r for r in runs[a.feedback]['rows']}
paired=[]
for id in cfg['feedback_ids']:
 initial=parent[id]
 for arm in ['self_review','tool_feedback']:
  r=repair[id,arm]
  paired.append({'task_id':id,'level':r['level'],'role':r['role'],'arm':arm,'initial_status':initial['status'],'revised_status':r['status'],
    'initial_effective':initial['effective_optimization'],'revised_effective':r['effective_optimization'],
    'gained_verification':initial['status']!='verified' and r['status']=='verified',
    'lost_verification':initial['status']=='verified' and r['status']!='verified',
    'new_proven_error':initial['status']=='verified' and r['status']=='refuted'})
with (out/'paired_feedback.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(paired[0]),lineterminator='\n');w.writeheader();w.writerows(paired)
feedback=[]
matched=[parent[id] for id in cfg['feedback_ids']]
for arm in ['initial_matched','self_review','tool_feedback']:
 rows=matched if arm=='initial_matched' else [repair[id,arm] for id in cfg['feedback_ids']]
 opp=[r for r in rows if r['role']=='opportunity']
 group=[r for r in paired if r['arm']==arm]
 feedback.append({'arm':arm,'n':len(rows),'opportunity_n':len(opp),'verified':sum(r['status']=='verified' for r in rows),
  'effective':sum(r['effective_optimization'] for r in opp),'refuted':sum(r['status']=='refuted' for r in rows),
  'gained_verification':sum(r['gained_verification'] for r in group),'lost_verification':sum(r['lost_verification'] for r in group),
  'new_proven_error':sum(r['new_proven_error'] for r in group)})
timing=[]
for name in [a.baseline,a.qwen,a.feedback]:
 for arm in sorted({r['arm'] for r in flat if r['run']==name}):
  group=[r for r in flat if r['run']==name and r['arm']==arm]
  times=[r['generation_seconds'] for r in group if r['generation_seconds'] is not None]
  timing.append({'run':name,'arm':arm,'n':len(group),'timed_n':len(times),
    'median_generation_seconds':statistics.median(times) if times else None,
    'total_generation_seconds':sum(times),'input_tokens':sum(r['prompt_tokens'] or 0 for r in group) if any(r['prompt_tokens'] is not None for r in group) else None,
    'output_tokens':sum(r['output_tokens'] or 0 for r in group) if any(r['output_tokens'] is not None for r in group) else None})
report={'created_utc':datetime.now(timezone.utc).isoformat(),'dataset_sha256':lock['sha256'],
 'run_roles':{'baseline':a.baseline,'identity':a.identity,'qwen':a.qwen,'feedback':a.feedback},'evaluation_code_sha256':next(iter(code_hashes)),'summary':summary,'paired_feedback':feedback,'timing':timing,
 'compiler_model':{'status':'awaiting_authorization','scored':False,'reason':'Official request is awaiting model-owner review.'},
 'limits':['24 authored cases, not a broad model leaderboard.','Meta LLM Compiler has no measurements yet.','Feedback comparisons use the same 12 cases, not the entire 24-case initial set.','Only verified outputs that meet the declared goal count as effective optimizations.','Static IR instruction count is not a runtime speed measurement.','Generation latency excludes model loading and subsequent verification.']}
write(out/'summary.json',report)
lines=['# 当前可运行组的实验结果','',
 'Meta LLM Compiler 的官方访问申请仍待审核，未运行、未计分。以下不是完整三模型结论。','',
 '| 运行 | 分支 | 类别 | 合法 IR | 语义验证通过 | 有效优化 | 发现反例 |',
 '|---|---|---|---:|---:|---:|---:|']
for s in summary:
 lines.append(f"| {s['run']} | {s['arm']} | {s['level']} | {s['syntax_valid']}/{s['n']} | {s['verified']}/{s['n']} | {s['effective']}/{s['opportunity_n']} | {s['refuted']}/{s['n']} |")
lines+=['','## 同题配对的修订实验','','三种条件都只统计预先选定的 12 题，其中 6 题具有优化目标。','',
 '| 条件 | 验证通过 | 有效优化 | 新获验证通过 | 失去验证通过 | 新发现的不安全回归 |','|---|---:|---:|---:|---:|---:|']
for s in feedback:lines.append(f"| {s['arm']} | {s['verified']}/{s['n']} | {s['effective']}/{s['opportunity_n']} | {s['gained_verification']} | {s['lost_verification']} | {s['new_proven_error']} |")
lines+=['','## 可审查的数据','','- per_case.csv：每题结果、生成耗时和 token 数。','- paired_feedback.csv：每题修订前后的状态变化。','- summary.json：全部状态分布、汇总和范围限制。','','未知、非法 IR、约束失败和工具异常不会混称为已证明的不安全变换。生成 Token 用各模型自身 tokenizer 统计，不当作跨模型完全等价的计算单位。']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'summary':summary,'feedback':feedback,'timing':timing},ensure_ascii=False,indent=2))
# The archive is a bounded evidence bundle, never a cache or a model-weight backup.
bundle=root/'results'/a.campaign/'evidence';bundle.mkdir(exist_ok=True)
files=set()
for name in [*runs,a.dev,*a.extra_run]:
 files.update(p for p in (root/'results'/name).rglob('*') if p.is_file())
for name in ['qwen-source-manifest.json','qwen-verified.json']:
 path=root/'results/model-downloads'/name
 if path.exists():files.add(path)
for directory in [out,root/'results'/a.campaign/'stages',root/'results'/a.campaign/'figures']:
 if directory.exists():files.update(p for p in directory.rglob('*') if p.is_file())
for name in ['accepted.json','fixture-validation.json','sandbox-validation.json','inference-freeze.txt','core-freeze.txt','report-freeze.txt']:
 path=root/'.toolchain'/name
 if path.exists():files.add(path)
status=root/'results'/a.campaign/'status.json'
if status.exists():files.add(status)
files.update(p for p in (root/'results'/a.campaign).glob('*.md') if p.is_file())
for dirname in ['src','scripts','tools','configs','tasks','tests']:
 files.update(p for p in (root/dirname).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.json','.ll','.md','.sh'})
for name in ['README.md','pyproject.toml','Makefile','LICENSE','THIRD_PARTY_NOTICES.md']:
 files.add(root/name)
checks={str(p.relative_to(root)):sha(p) for p in sorted(files)}
write(bundle/'FILES.sha256.json',checks)
archive=bundle/'experiment-evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for path in sorted(files):tar.add(path,arcname=str(path.relative_to(root)),recursive=False)
 tar.add(bundle/'FILES.sha256.json',arcname='FILES.sha256.json')
(bundle/'ARCHIVE.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
print('EVIDENCE_ARCHIVE',str(archive),'bytes',archive.stat().st_size)
