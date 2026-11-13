from __future__ import annotations
from pathlib import Path
import os,platform,re
from .common import digest,read_json,write_json,run_process,source_digest
from .tasks import check_lock,load_tasks
from .evaluate import tool,evaluate
from .sandbox import probe


def configure(root):
    if 'LLVM_BIN' not in os.environ:
        if (Path(root)/'.toolchain/bin/opt').is_file(): os.environ['LLVM_BIN']=str(Path(root)/'.toolchain/bin')
        elif Path('/usr/lib/llvm-17/bin/opt').is_file(): os.environ['LLVM_BIN']='/usr/lib/llvm-17/bin'
    candidate=Path(root)/'.toolchain/bin/alive-tv'
    if 'ALIVE_TV' not in os.environ and candidate.is_file(): os.environ['ALIVE_TV']=str(candidate)


def fingerprint(root):
    configure(root); result={'system':platform.system(),'machine':platform.machine(),'tools':{}}
    for name in ['opt','clang','alive-tv']:
        path=tool(name)
        if not path or not Path(path).is_file():
            result['tools'][name]={'available':False}; continue
        r=run_process([path,'--version'],10)
        result['tools'][name]={'available':r.returncode==0,'sha256':digest(Path(path)),
            'version':(r.stdout+r.stderr).strip(),'path':str(Path(path).resolve())}
    result['libraries']={}; cache={}
    for owner in ['opt','clang','alive-tv']:
        binary=tool(owner)
        if not binary: continue
        deps=run_process(['ldd',binary],10)
        for name,path in re.findall(r'^\s*(\S+)\s+=>\s+(/\S+)',deps.stdout,re.M):
            path=Path(path).resolve()
            if path.is_file():
                key=str(path)
                if key not in cache: cache[key]=digest(path)
                result['libraries'][owner+'::'+name]={'path':key,'sha256':cache[key]}
    return result


def fixtures(root):
    configure(root); config=read_json(Path(root)/'configs/experiment.json'); records=[]
    for t in load_tasks(root):
        for variant in ['source','reference','mutant']:
            row=evaluate(t,t.text(variant),config,allow_execution=True)
            expected='refuted' if variant=='mutant' else 'verified'
            ok=row['status']==expected
            if variant=='reference' and t.spec['role']=='opportunity': ok=ok and row['goal_met']
            records.append({'task_id':t.id,'variant':variant,'expected':expected,'passed':bool(ok),'evaluation':row})
    return {'passed':all(x['passed'] for x in records),'count':len(records),'records':records}


def accept(root):
    root=Path(root); lock=check_lock(root); fp=fingerprint(root)
    if fp['system']!='Linux' or fp['machine'] not in ['x86_64','AMD64']:
        raise ValueError('Formal v1 toolchain requires Linux x86_64')
    for name,info in fp['tools'].items():
        if not info['available'] or not re.search(r'\b17\.0\.6\b',info['version']):
            raise ValueError(f'{name}: LLVM 17.0.6 required, got {info}')
    sandbox=probe(tool('clang'))
    write_json(root/'.toolchain/sandbox-validation.json',sandbox)
    if not sandbox['passed']: raise ValueError('Execution sandbox acceptance failed')
    result=fixtures(root)
    write_json(root/'.toolchain/fixture-validation.json',result)
    if not result['passed']:
        raise ValueError('Fixture acceptance failed; inspect .toolchain/fixture-validation.json')
    receipt={'schema_version':1,'status':'accepted','dataset_sha256':lock['sha256'],'evaluator_code_sha256':source_digest(root),
             'fingerprint':fp,'fixture_count':result['count'],'sandbox':sandbox,
             'build_metadata':read_json(root/'.toolchain/build.json') if (root/'.toolchain/build.json').exists() else None,
             'claim':'Accepted on v1 authored fixtures only; not a proof that tools have no bugs.'}
    write_json(root/'.toolchain/accepted.json',receipt)
    return receipt


def require_receipt(root,verify_binaries=True):
    root=Path(root); lock=check_lock(root); p=root/'.toolchain/accepted.json'
    if not p.is_file(): raise ValueError('Formal execution requires irsem accept-toolchain')
    receipt=read_json(p)
    if receipt.get('status')!='accepted' or receipt['dataset_sha256']!=lock['sha256']:
        raise ValueError('Stale or invalid toolchain receipt')
    if receipt.get('evaluator_code_sha256')!=source_digest(root):
        raise ValueError('Evaluator code changed after acceptance; rerun accept-toolchain')
    if verify_binaries:
        now=fingerprint(root)
        for name in ['opt','clang','alive-tv']:
            if now['tools'][name].get('sha256')!=receipt['fingerprint']['tools'][name]['sha256']:
                raise ValueError('Tool binary changed after acceptance: '+name)
        if {k:v['sha256'] for k,v in now['libraries'].items()} != {k:v['sha256'] for k,v in receipt['fingerprint']['libraries'].items()}:
            raise ValueError('Dynamic library changed after acceptance')
    return receipt
