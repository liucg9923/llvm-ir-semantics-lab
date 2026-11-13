from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,os
from .common import read_json,write_json,text_digest,run_process,digest,source_digest
from .tasks import load_tasks,check_lock
from .ir import extract_ir
from .prompts import make_prompt
from .models import HFModel
from .gguf import GGUFModel,check_supplement
from .evaluate import evaluate,tool
from .toolchain import configure,require_receipt,fingerprint
from .differential import compare


def _start(root,out,backend,model,split,smoke,items,parent=None):
    out=Path(out).resolve(); root=Path(root).resolve()
    lock=check_lock(root); config=read_json(root/'configs/experiment.json')
    fixture=backend in {'identity','reference','mutant'}
    if not smoke and not fixture: require_receipt(root,verify_binaries=backend=='opt')
    if out.exists(): raise ValueError('Run directory already exists; use a new name to preserve evidence')
    out.mkdir(parents=True)
    meta={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
          'backend':backend,'model':model,'split':split,'mode':'fixture' if fixture else 'smoke' if smoke else 'formal',
          'dataset_sha256':lock['sha256'],'config':config,'items':items,'parent':parent,
          'status':'generating','runner_version':'0.1.0'}
    git=run_process(['git','rev-parse','HEAD'],10,cwd=root)
    meta['source_code_sha256']=source_digest(root)
    meta['git_commit']=git.stdout.strip() if git.returncode==0 else None
    meta['git_dirty']=bool(run_process(['git','status','--porcelain'],10,cwd=root).stdout.strip())
    write_json(out/'manifest.json',meta)
    return meta


def _infer(engine,prompt):
    try:
        return engine.generate(prompt)
    except ValueError as exc:
        return {'raw':'','error':str(exc)}


def _save(out,key,prompt,result):
    p=out/'candidates'/key; p.mkdir(parents=True)
    (p/'prompt.txt').write_text(prompt); (p/'raw.txt').write_text(result.pop('raw',''))
    result['prompt_sha256']=text_digest(prompt)
    result['raw_sha256']=digest(p/'raw.txt')
    write_json(p/'generation.json',result)


def generate(root,out,backend,model=None,split='test',smoke=False):
    root=Path(root); out=Path(out).resolve(); configure(root)
    tasks=load_tasks(root,split)
    spec=(read_json(root/'configs/compiler-ftd.json') if model=='compiler-ftd' else read_json(root/'configs/models.json').get(model)) if model else None
    if backend=='gguf':
        check_supplement(root)
        if model!='compiler-ftd':raise ValueError('GGUF backend requires --model compiler-ftd')
    if backend=='hf' and model=='compiler-ftd':raise ValueError('FTD GGUF requires --backend gguf')
    if backend=='hf' and not spec: raise ValueError('Choose --model compiler or qwen')
    items=[{'key':t.id,'task_id':t.id,'arm':'initial'} for t in tasks]
    meta=_start(root,out,backend,spec,split,smoke,items)
    engine=(GGUFModel(spec,meta['config']) if backend=='gguf' else HFModel(spec,meta['config'])) if backend in {'hf','gguf'} else None
    if engine: meta['inference_environment']=engine.info
    for t in tasks:
        prompt=make_prompt(t,meta['config'])
        if backend in {'hf','gguf'}: result=_infer(engine,prompt)
        elif backend=='opt':
            dest=out/(t.id+'.tmp.ll')
            p=run_process([tool('opt'),'-S','-verify-each','-passes='+t.spec['pipeline'],str(t.file('source')),'-o',str(dest)],meta['config']['tool_timeout_seconds'])
            result={'raw':dest.read_text() if dest.exists() else '', 'seconds':p.seconds,
                    'error':None if p.returncode==0 and not p.timed_out else 'opt_failed','tool_log':p.as_dict()}
            if dest.exists(): dest.unlink()
        else: result={'raw':t.text('source' if backend=='identity' else backend),'error':None,'provenance':'authored_fixture_not_model_output'}
        _save(out,t.id,prompt,result)
        print('generated',t.id,flush=True)
    meta['status']='generated'; write_json(out/'manifest.json',meta)
    return meta


def evaluate_run(root,run):
    root=Path(root); run=Path(run); configure(root)
    meta=read_json(run/'manifest.json'); lock=check_lock(root)
    if (run/'results.json').exists(): raise ValueError('Run already evaluated; preserve it and use a new run directory')
    if meta['dataset_sha256']!=lock['sha256']: raise ValueError('Run/dataset version mismatch')
    if meta['mode']=='formal': require_receipt(root)
    byid={t.id:t for t in load_tasks(root)}; rows=[]
    for item in meta['items']:
        t=byid[item['task_id']]; p=run/'candidates'/item['key']
        if not (p/'generation.json').exists():
            raw=''; error='missing_generation'
        else:
            gen=read_json(p/'generation.json'); raw=(p/'raw.txt').read_text()
            if digest(p/'raw.txt')!=gen['raw_sha256']: raise ValueError('Raw output changed after generation')
            error=gen.get('error')
        row=evaluate(t,raw,meta['config'],allow_execution=True,generation_error=error)
        row.update(key=item['key'],arm=item['arm'],mode=meta['mode'],backend=meta['backend'])
        rows.append(row); write_json(run/'evaluations'/f'{item["key"]}.json',row)
        print('evaluated',item['key'],row['status'],flush=True)
    write_json(run/'results.json',rows)
    meta['status']='evaluated'; meta['evaluation_toolchain']=fingerprint(root)
    meta['evaluation_code_sha256']=source_digest(root)
    write_json(run/'manifest.json',meta)
    return rows


def feedback(root,parent,out):
    root=Path(root); parent=Path(parent); out=Path(out).resolve(); configure(root)
    pm=read_json(parent/'manifest.json')
    if pm['backend'] not in {'hf','gguf'} or pm['mode']!='formal' or pm['status']!='evaluated':
        raise ValueError('Feedback requires an evaluated formal model initial run')
    require_receipt(root)
    if pm['dataset_sha256']!=check_lock(root)['sha256']: raise ValueError('Parent dataset mismatch')
    if any(i['arm']!='initial' for i in pm['items']): raise ValueError('Do not repair a repair')
    cfg=pm['config']; byid={t.id:t for t in load_tasks(root)}
    if not set(cfg['feedback_ids']).issubset({i['task_id'] for i in pm['items']}):
        raise ValueError('Parent is missing predefined feedback tasks')
    items=[{'key':id+'__'+arm,'task_id':id,'arm':arm} for id in cfg['feedback_ids'] for arm in ['self_review','tool_feedback']]
    meta=_start(root,out,pm['backend'],pm['model'],'test',False,items,parent=parent.name)
    prepared={}
    # Prepare CPU diagnostics before loading the GPU model; never expose holdout results.
    for id in cfg['feedback_ids']:
        t=byid[id]; raw=(parent/'candidates'/id/'raw.txt').read_text()
        ev=read_json(parent/'evaluations'/f'{id}.json')
        diagnostic={'syntax':ev.get('syntax_log'), 'alive2':ev.get('alive2_log'), 'contract':ev.get('contract_errors')}
        try:
            candidate=extract_ir(raw)
            if ev.get('syntax_valid') and not ev.get('contract_errors'):
                diagnostic['diagnostic_tests']=compare(t,candidate,tool('clang'),kind='diagnostic',allow_execution=True,
                    timeout=cfg['execution_timeout_seconds'],random_count=cfg['random_inputs'])
        except ValueError as e: diagnostic['format_error']=str(e)
        write_json(out/'diagnostics'/f'{id}.json',diagnostic)
        for arm in ['self_review','tool_feedback']:
            prepared[id+'__'+arm]=make_prompt(t,cfg,{'candidate':raw,'arm':arm,
                'diagnostics':json.dumps(diagnostic,ensure_ascii=False)[:6000]})
    engine=(GGUFModel(pm['model'],cfg) if pm['backend']=='gguf' else HFModel(pm['model'],cfg)); meta['inference_environment']=engine.info
    for item in items:
        prompt=prepared[item['key']]; _save(out,item['key'],prompt,_infer(engine,prompt))
        print('generated',item['key'],flush=True)
    meta['status']='generated'; write_json(out/'manifest.json',meta)
    return meta
