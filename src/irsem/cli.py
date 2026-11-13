from __future__ import annotations
import argparse,json,sys
from collections import Counter
from pathlib import Path
from .common import read_json,write_json,run_process
from .tasks import load_tasks,freeze,check_lock
from .ir import contract_errors,goal_met
from .toolchain import configure,fingerprint,fixtures,accept
from .evaluate import tool
from .runs import generate,evaluate_run,feedback
from .report import report


def check_dataset(root):
    tasks=load_tasks(root); issues=[]
    if len([t for t in tasks if t.spec['split']=='test'])!=24: issues.append('Expected 24 test tasks')
    if len([t for t in tasks if t.spec['split']=='dev'])!=6: issues.append('Expected 6 dev tasks')
    test_tasks=[t for t in tasks if t.spec['split']=='test']
    if Counter(t.spec['level'] for t in test_tasks)!={'L0':8,'L1':8,'L2':8}: issues.append('Unbalanced levels')
    if any(n!=2 for n in Counter(t.spec['pair_id'] for t in test_tasks).values()): issues.append('Each formal family must have two cases')
    cfg=read_json(Path(root)/'configs/experiment.json')
    if len(set(cfg['feedback_ids']))!=12 or not set(cfg['feedback_ids']).issubset({t.id for t in test_tasks}): issues.append('Invalid feedback subset')
    if not set(cfg['few_shot_ids']).issubset({t.id for t in tasks if t.spec['split']=='dev'}): issues.append('Few-shot example outside development split')
    devfamilies={t.spec['pair_id'] for t in tasks if t.spec['split']=='dev'}
    if devfamilies & {t.spec['pair_id'] for t in tasks if t.spec['split']=='test'}: issues.append('Dev/test family overlap')
    for t in tasks:
        for name in ['source','reference','mutant']:
            errors=contract_errors(t.text(),t.text(name))
            if errors: issues.append(f'{t.id}/{name}: {errors}')
            if tool('opt'):
                p=run_process([tool('opt'),'-passes=verify','-disable-output',str(t.file(name))],15)
                if p.returncode!=0 or p.timed_out: issues.append(f'{t.id}/{name}: {p.stderr}')
        if t.spec['role']=='opportunity':
            if goal_met(t,t.text()): issues.append(f'{t.id}: source already satisfies optimization goal')
            if not goal_met(t,t.text('reference')): issues.append(f'{t.id}: reference misses optimization goal')
    return {'passed':not issues,'task_count':len(tasks),'llvm_syntax_checked':bool(tool('opt')),'issues':issues}


def main(argv=None):
    p=argparse.ArgumentParser(description='Auditable LLVM IR transformation experiment')
    p.add_argument('--root',type=Path,default=Path.cwd())
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['doctor','check-dataset','freeze','check-lock','validate-fixtures','accept-toolchain']: sub.add_parser(name)
    g=sub.add_parser('generate'); g.add_argument('--backend',choices=['opt','hf','gguf','identity','reference','mutant'],required=True)
    g.add_argument('--model',choices=['compiler','qwen','compiler-ftd']); g.add_argument('--split',choices=['test','dev'],default='test')
    g.add_argument('--smoke',action='store_true'); g.add_argument('--out',type=Path,required=True)
    e=sub.add_parser('evaluate'); e.add_argument('--run',type=Path,required=True)
    f=sub.add_parser('feedback'); f.add_argument('--parent',type=Path,required=True); f.add_argument('--out',type=Path,required=True)
    r=sub.add_parser('report'); r.add_argument('--runs',type=Path,nargs='+',required=True); r.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv); root=a.root.resolve(); configure(root)
    try:
        if a.command=='doctor': result=fingerprint(root)
        elif a.command=='check-dataset': result=check_dataset(root)
        elif a.command=='freeze': result=freeze(root)
        elif a.command=='check-lock': result=check_lock(root)
        elif a.command=='validate-fixtures':
            result=fixtures(root); write_json(root/'.build/fixture-validation.json',result)
            result={k:v for k,v in result.items() if k!='records'}
        elif a.command=='accept-toolchain': result=accept(root)
        elif a.command=='generate': result=generate(root,a.out,a.backend,a.model,a.split,a.smoke)
        elif a.command=='evaluate': result=evaluate_run(root,a.run)
        elif a.command=='feedback': result=feedback(root,a.parent,a.out)
        else: result=report(a.runs,a.out)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 1 if isinstance(result,dict) and result.get('passed') is False else 0
    except (ValueError,OSError,KeyError) as exc:
        print('ERROR:',str(exc),file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
