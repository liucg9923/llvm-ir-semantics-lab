"""Recompute gates from immutable pilot evidence; never trust a bare passed flag."""
from pathlib import Path
from datetime import datetime,timezone
from irsem.common import read_json,write_json,digest
from .control import require_frozen,gate
from .dataset import tasks

def evidence(root,run,hint=False):
    root=Path(root);p=root/'results'/run;m=read_json(p/'manifest.json');rows=read_json(p/'results.json')
    frozen=require_frozen(root)
    if m['status']!='evaluated' or m['protocol_sha256']!=frozen['sha256']:raise ValueError('Pilot evidence is stale or incomplete')
    arm='hint' if hint else 'native';a=[r for r in rows if r['arm']==arm]
    expected={t.id for t in tasks(root,'dev')}
    if hint:expected={'dev_l0_and_all','dev_l1_select_equal','dev_l2_forward'}
    if len(a)!=len(expected) or {r['task_id'] for r in a}!=expected:raise ValueError('Missing or duplicate pilot task coverage')
    gens=[];files={str((p/'manifest.json').relative_to(root)):digest(p/'manifest.json'),str((p/'results.json').relative_to(root)):digest(p/'results.json')}
    for r in a:
        c=p/'candidates'/r['key'];g=read_json(c/'generation.json')
        if digest(c/'raw.txt')!=g['raw_sha256'] or digest(c/'prompt.txt')!=g['prompt_sha256']:raise ValueError('Pilot candidate changed')
        for n in ['generation.json','raw.txt','prompt.txt']:files[str((c/n).relative_to(root))]=digest(c/n)
        gens.append(g)
    if hint:
        checks={'three_records':len(a)==3,'complete_generation':all(g.get('error') is None for g in gens),'determinate_coverage':sum(r['determinate'] for r in a)>=2}
        result={'passed':all(checks.values()),'checks':checks,'determinate':sum(r['determinate'] for r in a),'verified':sum(r['verified'] for r in a),'criterion':'At least 2/3 determinate; correctness is not an acceptance criterion.'}
    else:result=gate(root,a,gens)
    return {'model':m['model'],'run':run,'gate':result,'files':files}

def select(root,pilot_runs,hint_runs=None,profile='native_bounded_v1'):
    root=Path(root);frozen=require_frozen(root)
    primary=[evidence(root,x) for x in pilot_runs]
    if {x['model'] for x in primary}!={'compiler-ftd','qwen'}:raise ValueError('Need both model pilot groups')
    hints=[evidence(root,x,True) for x in (hint_runs or [])]
    if hints and {x['model'] for x in hints}!={'compiler-ftd','qwen'}:raise ValueError('Need both hint pilots')
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':frozen['sha256'],'profile':profile,
      'primary_passed':all(x['gate']['passed'] for x in primary),'hint_passed':bool(hints) and all(x['gate']['passed'] for x in hints),
      'primary_evidence':primary,'hint_evidence':hints,'hint_data_sha256':digest(root/'results/campaign-v3/hints.json')}
    # Initial selection and the later hint decision are versioned separately.
    name='selection-with-hints.json' if hints else 'selection-primary.json'
    if (root/'results/campaign-v3'/name).exists():raise ValueError('Selection already exists; preserve it')
    write_json(root/'results/campaign-v3'/name,result);write_json(root/'results/campaign-v3/selected-profile.json',result)
    return result

def require_selection(root,hint=False):
    root=Path(root);s=read_json(root/'results/campaign-v3/selected-profile.json');f=require_frozen(root)
    if s['protocol_sha256']!=f['sha256'] or not s['primary_passed']:raise ValueError('Primary experiment gate is not accepted')
    if len(s.get('primary_evidence',[]))!=2 or {e['model'] for e in s['primary_evidence']}!={'compiler-ftd','qwen'}:raise ValueError('Both independently recorded model pilots are required')
    if hint and (len(s.get('hint_evidence',[]))!=2 or {e['model'] for e in s['hint_evidence']}!={'compiler-ftd','qwen'}):raise ValueError('Both hint pilots are required')
    if hint and not s['hint_passed']:raise ValueError('Shared-hint experiment gate is not accepted')
    if digest(root/'results/campaign-v3/hints.json')!=s['hint_data_sha256']:raise ValueError('Diagnostic hint data changed')
    for e in s['primary_evidence']+(s['hint_evidence'] if hint else []):
        for n,sha in e['files'].items():
            if digest(root/n)!=sha:raise ValueError('Pilot evidence changed: '+n)
        r=evidence(root,e['run'],e in s['hint_evidence'])
        if not r['gate']['passed']:raise ValueError('Recomputed pilot gate fails')
    return s
