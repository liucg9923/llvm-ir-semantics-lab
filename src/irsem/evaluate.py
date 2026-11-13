from __future__ import annotations
from pathlib import Path
import os,re,shutil,tempfile
from .common import run_process
from .ir import extract_ir,contract_errors,metrics,goal_met,clean,normalized_program
from .differential import compare


def tool(name):
    prefix=os.environ.get('LLVM_BIN','')
    if name=='alive-tv': path=os.environ.get('ALIVE_TV') or shutil.which(name)
    else: path=str(Path(prefix)/name) if prefix else shutil.which(name)
    return path if path and Path(path).is_file() and os.access(path,os.X_OK) else None


def alive_status(result):
    """Alive2 can exit zero for an incorrect transformation. Never use exit code alone."""
    if result.timed_out: return 'unknown'
    if result.returncode is None or result.truncated: return 'tool_error'
    text=result.stdout+'\n'+result.stderr
    labels=['correct transformations','incorrect transformations','failed-to-prove transformations','Alive2 errors']
    values=[]
    for label in labels:
        matches=re.findall(r'^\s*(\d+) '+re.escape(label)+r'\s*$',text,re.M)
        if len(matches)!=1: return 'tool_error'
        values.append(int(matches[0]))
    correct,incorrect,failed,errors=values
    if errors or result.returncode!=0: return 'tool_error'
    if incorrect: return 'refuted'
    if failed: return 'unknown'
    # Single-function tasks must have exactly one checked transformation.
    return 'verified' if correct==1 else 'tool_error'


def combine_status(proof,diff):
    if diff=='mismatch': return 'oracle_conflict' if proof=='verified' else 'refuted'
    if proof=='refuted': return 'refuted'  # Do not discard a formal counterexample.
    if diff=='tool_error': return 'tool_error'
    if diff in {'execution_error','compile_error'}:
        return 'oracle_conflict' if proof=='verified' else 'execution_error'
    if proof=='verified' and diff=='not_run': return 'verification_only'
    if proof=='unknown' and diff=='match': return 'tested_only'
    return proof


def evaluate(task,raw,config,allow_execution=False,generation_error=None):
    row={'task_id':task.id,'level':task.spec['level'],'role':task.spec['role'],
         'source_metrics':metrics(task.text()),'syntax_valid':False,'goal_met':False,
         'effective_optimization':False,'unchanged':False}
    if generation_error:
        return dict(row,status='generation_error',error=generation_error)
    try: candidate=extract_ir(raw)
    except ValueError as e: return dict(row,status='format_error',error=str(e))
    row.update(candidate_metrics=metrics(candidate),unchanged=clean(candidate)==clean(task.text()))
    opt=tool('opt'); alive=tool('alive-tv'); clang=tool('clang')
    if not opt: return dict(row,status='tool_error',error='opt not available')
    with tempfile.TemporaryDirectory(prefix='irsem-verify-') as tmp:
        p=Path(tmp); src=p/'source.ll'; dst=p/'candidate.ll'; canonical=p/'canonical.ll'
        src.write_text(task.text()); dst.write_text(candidate)
        syntax=run_process([opt,'-passes=verify','-S',str(dst),'-o',str(canonical)],config['tool_timeout_seconds'])
        row['syntax_log']=syntax.as_dict()
        if syntax.returncode is None or syntax.timed_out or syntax.truncated or syntax.returncode < 0: return dict(row,status='tool_error')
        if syntax.returncode!=0: return dict(row,status='invalid_ir')
        row['syntax_valid']=True
        if not canonical.is_file(): return dict(row,status='tool_error',error='Verifier did not emit canonical IR')
        candidate=canonical.read_text()
        dst=canonical
        row.update(canonical_ir=candidate,candidate_metrics=metrics(candidate),unchanged=normalized_program(candidate)==normalized_program(task.text()))
        errors=contract_errors(task.text(),candidate)
        if errors: return dict(row,status='contract_violation',contract_errors=errors)
        row['goal_met']=goal_met(task,candidate)
        if alive:
            proof=run_process([alive,*config['alive2_args'],str(src),str(dst)],config['tool_timeout_seconds'])
            status=alive_status(proof); row['alive2_log']=proof.as_dict()
        else:
            status='unknown'; row['alive2_log']={'reason':'alive-tv not installed'}
        diff=compare(task,candidate,clang,timeout=config['execution_timeout_seconds'],
                     random_count=config['random_inputs'],allow_execution=allow_execution) if clang else {'status':'not_run','reason':'clang missing'}
        row['differential']=diff
        status=combine_status(status,diff['status'])
        row['status']=status
        row['effective_optimization']=bool(status=='verified' and row['goal_met'] is True)
        return row
