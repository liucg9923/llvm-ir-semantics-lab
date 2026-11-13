from pathlib import Path
from datetime import datetime,timezone
from irsem.common import read_json,write_json,digest,text_digest,run_process
from irsem.toolchain import fingerprint
from .dataset import tasks

CORE=['src/irsem/prompts.py','src/irsem/tasks.py','docs/REDESIGN_V3.md','src/irsem/common.py','src/irsem/ir.py','src/irsem/evaluate.py','src/irsem/differential.py','src/irsem/sandbox.py','src/irsem/models.py','src/irsem/gguf.py','src/irsem/toolchain.py','tools/v3_ir_inspect.cpp','scripts/accept_v3.py','scripts/build_v3_tasks.py','scripts/build_v3_hints.py']
def code_files(root):return CORE+[str(p.relative_to(root)) for p in sorted((root/'src/irsem/v3').glob('*.py'))]
def snapshot(root):
    root=Path(root);files=code_files(root)+['configs/experiment-v3.json','configs/models.json','configs/compiler-ftd.json','configs/llama-cpp.json','tasks/v3/manifest.json','tasks/manifest.json','configs/experiment.json','results/campaign-v3/hints.json']
    for split in ['dev','test']:
        for t in tasks(root,split):files += [str(t.file(n).relative_to(root)) for n in ['source','reference','mutant']]
    return {n:digest(root/n) for n in sorted(set(files))}
def freeze(root):
    root=Path(root);p=root/'results/campaign-v3/frozen.json'
    if p.exists():raise ValueError('Refuse to overwrite a frozen protocol')
    receipt=read_json(root/'results/campaign-v3/oracle-acceptance.json')
    files=snapshot(root)
    if receipt['files']!=files or not receipt['passed']:raise ValueError('Oracle acceptance is stale')
    x={'created_utc':datetime.now(timezone.utc).isoformat(),'files':files,'sha256':text_digest(str(sorted(files.items()))),'toolchain':fingerprint(root),'inspector_sha256':digest(root/'.toolchain/bin/irsem-inspect')}
    write_json(p,x)
    for n in files:
        dst=root/'results/campaign-v3/snapshot'/n;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((root/n).read_bytes())
    return x

def require_frozen(root):
    root=Path(root);x=read_json(root/'results/campaign-v3/frozen.json')
    if x['files']!=snapshot(root):raise ValueError('Protocol/code/data changed since freeze')
    if x['inspector_sha256']!=digest(root/'.toolchain/bin/irsem-inspect'):raise ValueError('Inspector changed')
    now=fingerprint(root)
    if {k:v.get('sha256') for k,v in now['tools'].items()}!={k:v.get('sha256') for k,v in x['toolchain']['tools'].items()}:raise ValueError('Toolchain binary changed')
    if {k:v['sha256'] for k,v in now['libraries'].items()}!={k:v['sha256'] for k,v in x['toolchain']['libraries'].items()}:raise ValueError('Toolchain dependency changed')
    return x

def gate(root,rows,gens):
    cfg=read_json(Path(root)/'configs/experiment-v3.json')['pilot_gate'];determinate=[r for r in rows if r['determinate']]
    bylevel={level:sum(r['level']==level for r in determinate) for level in ['L0','L1','L2']}
    memory_ids={t.id for t in tasks(root,'dev') if t.spec['abi']=='memory'}
    checks={'six_records':len(rows)==6 and len(gens)==6,'transport_complete':all(g.get('error') is None for g in gens),
      'determinate_coverage':len(determinate)>=cfg['min_determinate'],'all_levels':all(n>=cfg['min_per_level'] for n in bylevel.values()),
      'memory_abi_covered':any(r['task_id'] in memory_ids for r in determinate)}
    return {'passed':all(checks.values()),'checks':checks,'determinate':len(determinate),'verified':sum(r['verified'] for r in rows),'by_level':bylevel,'criterion':'Coverage/interpretability, not model correctness. A refuted answer satisfies the determinate-coverage gate.'}
