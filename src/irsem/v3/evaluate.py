from pathlib import Path
import json,tempfile
from irsem.common import run_process,read_json
from .extract import extract
from irsem.evaluate import alive_status,combine_status,tool
from irsem.differential import compare
from irsem.toolchain import configure
from .policy import errors

def inspect(root,src,canonical,source=None,normalize_target=False):
    cmd=[str(Path(root)/'.toolchain/bin/irsem-inspect'),str(src),str(canonical)]
    if source:cmd.append(str(source))
    if normalize_target:cmd.append('--normalize-equivalent-target')
    p=run_process(cmd,30)
    if p.returncode!=0 or p.timed_out or p.truncated:return None,p.as_dict()
    try:return json.loads(p.stdout),p.as_dict()
    except ValueError:return None,p.as_dict()

def evaluate(root,task,raw,cfg,generation_error=None,kind='holdout'):
    root=Path(root);configure(root)
    row={'task_id':task.id,'level':task.spec['level'],'role':task.spec['role'],'syntax_valid':False,'semantic_attempted':False,'determinate':False,'verified':False,'effective_optimization':False,'goal_met':False}
    if generation_error:return {**row,'status':'generation_error','error':generation_error}
    try:candidate,form=extract(raw);row['extraction']=form
    except ValueError as e:return {**row,'status':'format_error','error':str(e)}
    with tempfile.TemporaryDirectory(prefix='irsem-v3-') as td:
        p=Path(td);src=p/'source.ll';dst=p/'candidate.ll';src.write_text(task.text());dst.write_text(candidate)
        s,sl=inspect(root,src,p/'source.canonical.ll')
        if s is None:return {**row,'status':'tool_error','error':'Invalid source','source_inspection':sl}
        c,cl=inspect(root,dst,p/'candidate.canonical.ll',src)
        row['syntax_log']=cl
        if c is None:
            return {**row,'status':'invalid_ir' if cl['returncode']==1 else 'tool_error'}
        row['syntax_valid']=True;row['source_structure']=s;row['candidate_structure']=c
        cand=(p/'candidate.canonical.ll').read_text();row['canonical_ir']=cand
        checks=errors(s,c);row['admission']=checks
        if checks['interface']:return {**row,'status':'interface_mismatch'}
        if checks['assumptions']:return {**row,'status':'unproved_input_assumption'}
        if checks['unsupported']:return {**row,'status':'unsupported_ir'}
        row['context_inheritance']={k:c[k] for k in ['inherited_target_triple','inherited_data_layout']}
        row['canonical_ir_before_context_normalization']=cand
        normalized,nlog=inspect(root,p/'candidate.canonical.ll',p/'candidate.proof.ll',src,normalize_target=True)
        if normalized is None:return {**row,'status':'tool_error','normalization_log':nlog}
        cand=(p/'candidate.proof.ll').read_text();row['evaluation_ir']=cand
        row['context_normalization']={k:normalized.get(k,False) for k in ['equivalent_triple_canonicalized','equivalent_layout_canonicalized']}
        row['semantic_attempted']=True
        pr=run_process([tool('alive-tv'),*cfg['alive2_args'],str(p/'source.canonical.ll'),str(p/'candidate.proof.ll')],cfg['tool_timeout_seconds'])
        row['alive2_log']=pr.as_dict();proof=alive_status(pr)
        diffs={level:compare(task,cand,tool('clang'),kind=kind,allow_execution=True,timeout=cfg['execution_timeout_seconds'],random_count=cfg['random_inputs'],retain_cases=True,optimization=level) for level in ['-O0','-O2']}
        row['differential']=diffs
        native='match'
        for level in ['-O0','-O2']:
            if diffs[level]['status']!='match':native=diffs[level]['status'];break
        status=combine_status(proof,native)
        if status=='tool_error' and ('Unsupported' in pr.stdout+pr.stderr or 'unsupported' in pr.stdout+pr.stderr):status='verifier_unsupported'
        row['status']=status;row['determinate']=status in {'verified','refuted'};row['verified']=status=='verified'
        if task.spec['role']=='opportunity':
            g=task.spec['goal'];row['goal_met']=c['instructions']<=g.get('instruction_max',10**9) and all(c['opcodes'].get(k,0)<=v for k,v in g.get('opcode_max',{}).items())
            row['effective_optimization']=bool(row['verified'] and row['goal_met'])
        return row
