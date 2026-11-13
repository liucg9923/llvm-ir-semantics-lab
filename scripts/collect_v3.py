"""Source-checked v3 counts, matched development contrasts and shared-hint comparisons."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import csv,json,statistics
from irsem.common import read_json,write_json,digest
from irsem.v3.control import require_frozen
from irsem.v3.selection import require_selection
from irsem.v3.dataset import tasks
root=Path(__file__).resolve().parents[1];frozen=require_frozen(root);sel=require_selection(root)
out=root/'results/campaign-v3/analysis';out.mkdir(parents=True,exist_ok=True)
primary={m:'v3b-formal-'+m for m in ['opt','identity','compiler-ftd','qwen']}
pilots={'compiler-ftd':'v3b-pilot-compiler-ftd','qwen':'v3b-pilot-qwen-native' if (root/'results/v3b-pilot-qwen-native').exists() else 'v3b-pilot-qwen'}
hints={m:'v3b-hint-'+m for m in ['compiler-ftd','qwen']} if sel['hint_passed'] else {}
runs={}
for name in dict.fromkeys([*primary.values(),*pilots.values(),*hints.values(),'v3b-hintpilot-compiler-ftd','v3b-hintpilot-qwen','v3b-pilot-qwen']):
 p=root/'results'/name;m=read_json(p/'manifest.json');rows=read_json(p/'results.json')
 assert m['status']=='evaluated' and m['protocol_sha256']==frozen['sha256'] and len(rows)==len(m['items']),name
 assert len({r['key'] for r in rows})==len(rows)
 for r in rows:
  c=p/'candidates'/r['key'];g=read_json(c/'generation.json')
  assert digest(c/'raw.txt')==g['raw_sha256'] and digest(c/'prompt.txt')==g['prompt_sha256']
  if (c/'wire_prompt.txt').exists():assert digest(c/'wire_prompt.txt')==g['wire_prompt_sha256']
 runs[name]={'meta':m,'rows':rows,'path':p}
ids={t.id for t in tasks(root,'test')};assert len(ids)==18
for name in primary.values():assert {r['task_id'] for r in runs[name]['rows']}==ids
for id in ids:
 assert digest(runs[primary['qwen']]['path']/'candidates'/(id+'__native')/'prompt.txt')==digest(runs[primary['compiler-ftd']]['path']/'candidates'/(id+'__native')/'prompt.txt')
if hints:
 for id in read_json(root/'configs/experiment-v3.json')['hint_ids']:
  assert digest(runs[hints['qwen']]['path']/'candidates'/(id+'__hint')/'prompt.txt')==digest(runs[hints['compiler-ftd']]['path']/'candidates'/(id+'__hint')/'prompt.txt')

def stats(rows):
 opp=[r for r in rows if r['role']=='opportunity'];determinate=sum(r['determinate'] for r in rows);eligible=sum(r['semantic_attempted'] for r in rows);verified=sum(r['verified'] for r in rows)
 return {'n':len(rows),'opportunity_n':len(opp),'syntax_valid':sum(r['syntax_valid'] for r in rows),'semantic_attempted':eligible,'determinate':determinate,'verified':verified,
  'refuted':sum(r['status']=='refuted' for r in rows),'effective':sum(r['effective_optimization'] for r in opp),'statuses':dict(Counter(r['status'] for r in rows)),
  'verified_fraction_of_determinate':verified/determinate if determinate else None,'legacy_admission':sum(r['syntax_valid'] and not r['legacy_contract_errors'] for r in rows)}
summary=[];dev=[];paired=[];flat=[]
for model,name in primary.items():
 for level in ['ALL','L0','L1','L2']:
  a=[r for r in runs[name]['rows'] if level=='ALL' or r['level']==level];summary.append({'model':model,'level':level,**stats(a)})
for model,name in pilots.items():
 for arm in sorted({r['arm'] for r in runs[name]['rows']}):
  a=[r for r in runs[name]['rows'] if r['arm']==arm];label='bounded' if model=='qwen' and name=='v3b-pilot-qwen' else arm;dev.append({'model':model,'arm':label,**stats(a)})
if pilots['qwen']!='v3b-pilot-qwen':dev.append({'model':'qwen','arm':'bounded',**stats(runs['v3b-pilot-qwen']['rows'])})
for model,name in hints.items():
 h={r['task_id']:r for r in runs[name]['rows']};b={r['task_id']:r for r in runs[primary[model]]['rows']}
 for id in h:
  paired.append({'model':model,'task_id':id,'role':h[id]['role'],'initial_status':b[id]['status'],'hint_status':h[id]['status'],'initial_effective':b[id]['effective_optimization'],'hint_effective':h[id]['effective_optimization']})
for name,group in runs.items():
 for r in group['rows']:
  g=read_json(group['path']/'candidates'/r['key']/'generation.json')
  flat.append({'run':name,'model':r['model'],'phase':r['phase'],'arm':r['arm'],'task_id':r['task_id'],'level':r['level'],'role':r['role'],'status':r['status'],
   'syntax_valid':r['syntax_valid'],'semantic_attempted':r['semantic_attempted'],'determinate':r['determinate'],'verified':r['verified'],'effective':r['effective_optimization'],
   'seconds':g.get('seconds'),'prompt_tokens':g.get('prompt_tokens'),'output_tokens':g.get('output_tokens')})
for filename,rows in [('per_case.csv',flat),('paired_hints.csv',paired)]:
 if not rows:continue
 with (out/filename).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
hint_summary=[]
for model,name in hints.items():
 ids2={r['task_id'] for r in runs[name]['rows']}
 hint_summary += [{'model':model,'arm':'initial_matched',**stats([r for r in runs[primary[model]]['rows'] if r['task_id'] in ids2])},{'model':model,'arm':'shared_semantic_hint',**stats(runs[name]['rows'])}]
timing=[]
for model,name in primary.items():
 vals=[r for r in flat if r['run']==name];times=[r['seconds'] for r in vals if r['seconds'] is not None]
 timing.append({'model':model,'n':len(vals),'median_generation_seconds':statistics.median(times) if times else None,'generation_seconds':sum(times),'input_tokens':sum(r['prompt_tokens'] or 0 for r in vals),'output_tokens':sum(r['output_tokens'] or 0 for r in vals)})
report={'created_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':frozen['sha256'],'primary_runs':primary,'pilot_runs':pilots,'selected_pilot_runs':{'compiler-ftd':'v3b-pilot-compiler-ftd','qwen':'v3b-pilot-qwen'},'selected_arm_by_model':{'compiler-ftd':'native','qwen':'bounded'},'hint_runs':hints,'summary':summary,'development_contrasts':dev,'shared_hint_comparison':hint_summary,'timing':timing,'selection':sel,
 'scope':'18 newly authored tasks; fixed community FTD checkpoint and Qwen checkpoint. Coverage/verification/useful optimization are separate. No claim of a causal specialization effect or a population-wide ranking.',
 'hint_interpretation':'Identical semantic hints are generated from authored mutants; this is not self-review or repair of each model own prior output.',
 'normalization':'Context-only inheritance/equivalence conversion is logged; no instruction, flag or attribute repair is performed.'}
write_json(out/'summary.json',report)
write_json(out/'ANALYSIS_CHECKS.json',{'passed':True,'all_runs_evaluated':True,'same_frozen_protocol':True,'all_raw_and_prompt_hashes_match':True,'same_18_primary_task_ids':True,'identical_semantic_prompt_text_across_models':True,'same_hint_information_when_run':True,'empty_conditional_denominator_is_null':True})
names={'opt':'LLVM opt','identity':'原样返回','compiler-ftd':'社区 FTD F16','qwen':'Qwen FP16'}
lines=['# V3 受控实验结果','', '任务、提示、评分器和工具在模型实验前冻结；正式任务为新编写的 18 题，开发题不计分。','',
 '| 对象 | 合法 IR | 进入语义验证 | 验证通过 | 已证反例 | 有效优化 |','|---|---:|---:|---:|---:|---:|']
for r in summary:
 if r['level']=='ALL':lines.append(f"| {names[r['model']]} | {r['syntax_valid']}/{r['n']} | {r['semantic_attempted']}/{r['n']} | {r['verified']}/{r['n']} | {r['refuted']} | {r['effective']}/{r['opportunity_n']} |")
lines+=['','## 同一开发题上的提示方案对照','','两种提示在相同检查点、服务器、解码和新评分器下比较。旧准入一列只应用旧结构规则，不是旧实验的完整成绩。FTD 最终选用 native；Qwen 最终选用 bounded（相同原生语义任务加唯一输出格式的 system 消息）。Qwen 原生无额外格式约束的失败方案也保留在表中。','',
 '| 模型 | 提示 | 旧准入可继续 | 新版进入语义验证 | 新版验证通过 | 新版反例 |','|---|---|---:|---:|---:|---:|']
for r in dev:lines.append(f"| {names[r['model']]} | {r['arm']} | {r['legacy_admission']}/{r['n']} | {r['semantic_attempted']}/{r['n']} | {r['verified']}/{r['n']} | {r['refuted']} |")
lines+=['','## 统一语义提示条件','', '两款模型获得相同的人工错误程序所对应的诊断反例；只提供原程序和数值事实，不把另一个模型的答案交给它，也不把保留测试输入放进提示。','']
if hints:
 lines+=['| 模型 | 条件 | 进入语义验证 | 验证通过 | 有效优化 |','|---|---|---:|---:|---:|']
 for r in hint_summary:lines.append(f"| {names[r['model']]} | {r['arm']} | {r['semantic_attempted']}/{r['n']} | {r['verified']}/{r['n']} | {r['effective']}/{r['opportunity_n']} |")
else:lines+=['提示条件未通过共同预检，因此两模型均未进入该正式条件；不能将未运行记为零分。']
lines+=['','## 结论边界','','- “已证反例”与接口失败、不支持、未知分别保留；不能把未验证候选统称为语义错误。','- 验证通过要求 Alive2 证明以及 -O0、-O2 的独立执行一致；有限测试本身不构成全输入证明。','- 有效优化只在 9 个预定机会题上统计，原样返回不会得到优化分。','- 这些是固定任务的描述性计数，不能推广成所有 LLM 或所有编译任务的普遍能力排名。','- FTD 与 Qwen 的模型基座及推理后端不同，不能将差异单独归因于专用训练。','- 旧 24 题、旧提示和旧准入结果保留，不与新 18 题直接作进步率比较。','- 生成延迟排除加载与验证，不同 tokenizer 的 token 数不视为相同计算单位。']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'primary':[r for r in summary if r['level']=='ALL'],'development':dev,'hints':hint_summary},ensure_ascii=False,indent=2))
