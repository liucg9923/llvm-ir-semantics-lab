"""Versioned, guarded runs. No formal data generation before both pilot gates pass."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,tempfile
from irsem.common import read_json,write_json,digest,text_digest,run_process
from irsem.models import HFModel
from irsem.gguf import GGUFModel
from irsem.prompts import make_prompt
from irsem.ir import contract_errors,extract_ir
from irsem.evaluate import tool
from irsem.toolchain import configure
from .dataset import tasks
from .prompts import native,source_facts
from .evaluate import evaluate
from .control import require_frozen,gate

def start(root,out,model,phase,items):
    frozen=require_frozen(root)
    if out.exists():raise ValueError('Run exists: preserve it and choose another name')
    out.mkdir(parents=True)
    meta={'schema_version':3,'model':model,'phase':phase,'created_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':frozen['sha256'],'config':read_json(root/'configs/experiment-v3.json'),'items':items,'status':'generating','parent_git_commit':run_process(['git','rev-parse','HEAD'],10,cwd=root).stdout.strip()}
    write_json(out/'manifest.json',meta);return meta

def save(out,key,prompt,result):
    p=out/'candidates'/key;p.mkdir(parents=True)
    data=dict(result);raw=data.pop('raw','');wire=data.pop('wire_prompt',None)
    (p/'raw.txt').write_text(raw);(p/'prompt.txt').write_text(prompt)
    if wire is not None:(p/'wire_prompt.txt').write_text(wire);data['wire_prompt_sha256']=text_digest(wire)
    data.update(raw_sha256=text_digest(raw),prompt_sha256=text_digest(prompt));write_json(p/'generation.json',data)

def evaluate_saved(root,out,meta,ts):
    rows=[];byid={t.id:t for t in ts}
    for item in meta['items']:
        p=out/'candidates'/item['key'];g=read_json(p/'generation.json');raw=(p/'raw.txt').read_text()
        if digest(p/'raw.txt')!=g['raw_sha256']:raise ValueError('Raw output modified')
        row=evaluate(root,byid[item['task_id']],raw,meta['config'],g.get('error'))
        row.update(key=item['key'],arm=item['arm'],model=meta['model'],phase=meta['phase'])
        # Structural legacy-admission contrast on the exact same candidate; not a new oracle score.
        try:row['legacy_contract_errors']=contract_errors(byid[item['task_id']].text(),extract_ir(raw))
        except ValueError as e:row['legacy_contract_errors']=[str(e)]
        write_json(out/'evaluations'/(item['key']+'.json'),row);rows.append(row)
        print('evaluated',item['key'],row['status'],flush=True)
    write_json(out/'results.json',rows);meta['status']='evaluated';write_json(out/'manifest.json',meta);return rows

def run(root,model,phase,out,profile='native_single_v1'):
    root=Path(root);configure(root);out=Path(out).resolve()
    split='dev' if phase in {'pilot','hint_pilot'} else 'test';ts=tasks(root,split);cfg=read_json(root/'configs/experiment-v3.json')
    if phase in {'formal','hint','hint_pilot'} and model not in {'opt','identity'}:
        from .selection import require_selection
        selected=require_selection(root,hint=phase=='hint')
        if profile!=selected['profile']:raise ValueError('Run profile differs from the accepted model adapters')
    if phase=='hint':ts=[t for t in ts if t.id in cfg['hint_ids']]
    if phase=='hint_pilot':ts=[t for t in ts if t.id in {'dev_l0_and_all','dev_l1_select_equal','dev_l2_forward'}]
    items=[{'key':t.id+'__'+arm,'task_id':t.id,'arm':arm} for t in ts for arm in (['legacy','native'] if phase=='pilot' and profile=='native_single_v1' else ['hint'] if phase in {'hint','hint_pilot'} else ['native'])]
    meta=start(root,out,model,phase,items);meta['profile']=profile
    facts={t.id:source_facts(root,t) for t in ts};write_json(out/'input-facts.json',facts)
    hints=read_json(root/'results/campaign-v3/hints.json') if phase in {'hint','hint_pilot'} else {}
    engine=None
    if model=='compiler-ftd':engine=GGUFModel(read_json(root/'configs/compiler-ftd.json'),cfg)
    elif model=='qwen':
        model_cfg={**cfg,**({'system_prompt':cfg['qwen_system_prompt']} if profile=='native_bounded_v1' else {})}
        engine=HFModel(read_json(root/'configs/models.json')['qwen'],model_cfg)
    if engine:meta['inference_environment']=engine.info;write_json(out/'manifest.json',meta)
    byid={t.id:t for t in ts}
    try:
        for item in items:
            t=byid[item['task_id']]
            prompt=make_prompt(t,read_json(root/'configs/experiment.json')) if item['arm']=='legacy' else native(t,facts[t.id],hints.get(t.id) if phase in {'hint','hint_pilot'} else None)
            if model=='identity':result={'raw':t.text(),'error':None,'seconds':0,'provenance':'identity_control'}
            elif model=='opt':
                with tempfile.TemporaryDirectory(prefix='irsem-v3-opt-') as td:
                    dst=Path(td)/'candidate.ll';p=run_process([tool('opt'),'-S','-verify-each','-passes='+t.spec['pipeline'],str(t.file('source')),'-o',str(dst)],cfg['tool_timeout_seconds'])
                    result={'raw':dst.read_text() if dst.exists() else '', 'error':None if p.returncode==0 and not p.timed_out else 'opt_failed','seconds':p.seconds,'tool_log':p.as_dict()}
            else:
                try:result=engine.generate(prompt)
                except (ValueError,OSError) as e:result={'raw':'','error':str(e)}
            save(out,item['key'],prompt,result);print('generated',item['key'],flush=True)
    finally:
        if isinstance(engine,GGUFModel):engine.close()
    meta['status']='generated';write_json(out/'manifest.json',meta)
    rows=evaluate_saved(root,out,meta,ts)
    if phase=='pilot':
        selected=[r for r in rows if r['arm']=='native'];gens=[read_json(out/'candidates'/r['key']/'generation.json') for r in selected]
        write_json(out/'gate.json',gate(root,selected,gens))
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['compiler-ftd','qwen','opt','identity'],required=True);p.add_argument('--phase',choices=['pilot','formal','hint','hint_pilot'],required=True);p.add_argument('--out',required=True,type=Path);p.add_argument('--profile',choices=['native_single_v1','native_bounded_v1'],default='native_single_v1');a=p.parse_args()
    rows=run(Path.cwd(),a.model,a.phase,a.out,a.profile);print(json.dumps({'n':len(rows),'statuses':{s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}}))
if __name__=='__main__':main()
