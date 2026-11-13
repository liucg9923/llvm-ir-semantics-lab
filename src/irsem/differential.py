from __future__ import annotations
from pathlib import Path
from itertools import product
import hashlib,random,tempfile,sys
from .sandbox import C_SETUP
from .common import run_process

BOUNDARY=[0,1,2,3,4,7,8,15,16,31,63,127,128,254,255,256,257,65535,2147483647,2147483648,4294967291,4294967294,4294967295]


def input_cases(task,kind='holdout',random_count=256):
    """Diagnostic and holdout inputs are disjoint. Audit is their union."""
    seed=int(hashlib.sha256(task.id.encode()).hexdigest()[:12],16)
    abi=task.spec['abi']
    def generate(which):
        rng=random.Random(seed+(0 if which=='diagnostic' else 20261112))
        values=BOUNDARY[:9] if which=='diagnostic' else BOUNDARY
        if abi=='unary':
            cases=[(x,) for x in values]
            if which!='diagnostic' and task.spec['exhaustive_low_byte']: cases += [(x,) for x in range(256)]
            cases += [(rng.getrandbits(32),) for _ in range(8 if which=='diagnostic' else random_count)]
        elif abi=='binary':
            cases=list(product(values[:8],repeat=2))
            cases += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(8 if which=='diagnostic' else random_count)]
        else:
            aliases=[0] if task.spec['noalias'] else [0,1]
            cases=[(a,b,k) for a,b in product(values[:8],repeat=2) for k in aliases]
            cases += [(rng.getrandbits(32),rng.getrandbits(32),rng.choice(aliases)) for _ in range(8 if which=='diagnostic' else random_count)]
        return list(dict.fromkeys(cases))
    diagnostic=generate('diagnostic')
    holdout=[x for x in generate('holdout') if x not in set(diagnostic)]
    return diagnostic if kind=='diagnostic' else list(dict.fromkeys(diagnostic+holdout)) if kind=='audit' else holdout


def driver(abi):
    common='#include <stdint.h>\n#include <stdio.h>\n#include <inttypes.h>\n'
    if abi=='memory':
        return common+'''extern uint32_t f(uint32_t*,uint32_t*);
int main(void) { uint32_t a,b,k; while(scanf("%" SCNu32 " %" SCNu32 " %" SCNu32,&a,&b,&k)==3) {
  _Alignas(8) uint32_t v[2]={a,b}; uint32_t r=f(&v[0],&v[k?0:1]);
  printf("%" PRIu32 " %" PRIu32 " %" PRIu32 "\\n",r,v[0],v[1]); } return 0; }
'''
    if abi=='binary':
        return common+'''extern uint32_t f(uint32_t,uint32_t);
int main(void) { uint32_t a,b; while(scanf("%" SCNu32 " %" SCNu32,&a,&b)==2)
 printf("%" PRIu32 "\\n",f(a,b)); return 0; }
'''
    return common+'''extern uint32_t f(uint32_t);
int main(void) { uint32_t a; while(scanf("%" SCNu32,&a)==1)
 printf("%" PRIu32 "\\n",f(a)); return 0; }
'''


def compare(task,candidate,clang,kind='holdout',timeout=5,random_count=256,allow_execution=False,retain_cases=False,optimization='-O0'):
    if not allow_execution:
        return {'status':'not_run','reason':'Native candidate execution requires the isolated evaluation workflow.'}
    cases=input_cases(task,kind,random_count)
    # Input comes from a file; candidate code runs as a separate process.
    with tempfile.TemporaryDirectory(prefix='irsem-diff-') as tmp:
        p=Path(tmp)
        code=driver(task.spec['abi']).replace('int main(void) {','int main(void) { irsem_sandbox();')
        (p/'driver.c').write_text(C_SETUP+code)
        (p/'inputs.txt').write_text(''.join(' '.join(map(str,x))+'\n' for x in cases))
        outcomes=[]; logs={}
        for name,ir in [('source',task.text()),('candidate',candidate)]:
            (p/f'{name}.ll').write_text(ir)
            build=run_process([clang,optimization,'-Wno-override-module',str(p/f'{name}.ll'),str(p/'driver.c'),'-lseccomp','-o',str(p/name)],60)
            logs[name+'_compile']=build.as_dict()
            if build.returncode!=0 or build.timed_out:
                return {'status':'tool_error' if name=='source' else 'compile_error','stage':name,'logs':logs}
            # stdin redirection is performed by a trusted tiny Python wrapper, never a shell.
            run=run_process([sys.executable,'-c',
                'import os,sys,resource; resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824)); resource.setrlimit(resource.RLIMIT_CPU,(6,6)); resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608)); f=open(sys.argv[2],"rb"); os.dup2(f.fileno(),0); os.execve(sys.argv[1],[sys.argv[1]],{"LANG":"C","PATH":"/usr/bin:/bin"})',
                str(p/name),str(p/'inputs.txt')],timeout)
            logs[name+'_run']=run.as_dict()
            if run.timed_out or run.returncode!=0 or run.truncated:
                return {'status':'tool_error' if name=='source' else 'execution_error','stage':name,'logs':logs}
            lines=run.stdout.splitlines()
            if len(lines)!=len(cases): return {'status':'tool_error','reason':'Unexpected result count','logs':logs}
            outcomes.append(lines)
        differences=[i for i,(a,b) in enumerate(zip(*outcomes)) if a!=b]
        result={'status':'mismatch' if differences else 'match','input_kind':kind,'case_count':len(cases),
                'mismatch_count':len(differences)}
        if differences:
            i=differences[0]
            result['counterexample']={'input':list(cases[i]),'source':outcomes[0][i],'candidate':outcomes[1][i]}
        if retain_cases:
            result.update(inputs=[list(x) for x in cases],source_outputs=outcomes[0],candidate_outputs=outcomes[1],logs=logs,optimization=optimization)
        return result
