"""Conservative checks for the intentionally small v1 task language.
LLVM's verifier remains responsible for parsing/types/SSA. This is not a full IR parser.
"""
from __future__ import annotations
import re
from collections import Counter


def extract_ir(raw):
    if len(raw)>262144: raise ValueError('Output exceeds v1 size limit')
    if '<code>' in raw and (raw.count('<code>')!=1 or raw.count('</code>')!=1):
        raise ValueError('Unbalanced or multiple code tags')
    if '```' in raw and raw.count('```')!=2: raise ValueError('Unbalanced or multiple code fences')
    tagged=re.findall(r'<code>\s*(.*?)\s*</code>',raw,re.S)
    fenced=re.findall(r'```(?:llvm|llvm-ir|ir)?[ \t]*\n(.*?)```',raw,re.S)
    if tagged and fenced: raise ValueError('Mixed output containers')
    blocks=tagged or fenced
    if blocks:
        if len(blocks)!=1: raise ValueError('Expected exactly one IR block')
        return blocks[0].strip()+'\n'
    text=raw.strip()
    if not re.match(r'(;|target\b|source_filename\b|define\b)',text):
        raise ValueError('No unambiguous IR output')
    if '```' in text or '<code>' in text or '</code>' in text:
        raise ValueError('Unclosed code container')
    return text+'\n'


def clean(ir):
    return '\n'.join(line.split(';',1)[0].strip() for line in ir.splitlines() if line.split(';',1)[0].strip())


def normalized_program(ir):
    return ''.join(''.join(line.split()) for line in clean(ir).splitlines() if not line.startswith('source_filename'))


def instructions(ir):
    inside=False; ops=[]
    for line in clean(ir).splitlines():
        if line.startswith('define '): inside=True; continue
        if line=='}': inside=False; continue
        if not inside or re.match(r'^[\w.$-]+:',line): continue
        line=re.sub(r'^%[\w.$-]+\s*=\s*','',line)
        word=line.split()[0]
        if word in {'tail','musttail','notail'}: word='call'
        ops.append(word)
    return ops


def metrics(ir):
    ops=instructions(ir)
    return {'instruction_count':len(ops),'opcodes':dict(Counter(ops))}


def goal_met(task,ir):
    if task.spec['role']!='opportunity': return None
    goal=task.spec['goal']; m=metrics(ir)
    return (m['instruction_count']<=goal.get('instruction_max',10**9)
            and all(m['opcodes'].get(k,0)<=v for k,v in goal.get('opcode_max',{}).items()))


def _header(ir):
    headers=re.findall(r'^define\s+(.+?)\{',clean(ir),re.M|re.S)
    if len(headers)!=1: raise ValueError('Exactly one function definition required')
    h=' '.join(headers[0].split())
    # Strip local argument names, but preserve every type/attribute/calling convention.
    h=re.sub(r'%[\w.$-]+','%ARG',h)
    m=re.fullmatch(r'(.+?)@([\w.$-]+)\((.*?)\)(.*)',h)
    if not m: raise ValueError('Unsupported function signature')
    params=tuple(tuple(sorted(arg.split())) for arg in m[3].split(','))
    return (m[1].strip(),m[2],params,m[4].strip())


def contract_errors(source,candidate):
    errors=[]
    try:
        if _header(source)!=_header(candidate): errors.append('Function signature/attributes changed')
    except ValueError as e: errors.append(str(e))
    if not re.search(r'@f\s*\(',candidate): errors.append('Required function f missing')
    for key in ('target datalayout','target triple'):
        get=lambda s: re.findall(r'^'+key+r'\s*=\s*"([^"]+)"',clean(s),re.M)
        if get(source)!=get(candidate): errors.append(key+' changed or removed')
    c=clean(candidate)
    if re.search(r'[%@]\"',c): errors.append('Quoted identifiers are outside the v1 CFG checker')
    semantic_lines='\n'.join(x for x in c.splitlines() if not x.startswith('source_filename'))
    if re.search(r'!\w|^!',semantic_lines,re.M): errors.append('Additional metadata is outside v1')
    if re.search(r'^(declare\b|@|module\s+asm\b|attributes\b)',c,re.M):
        errors.append('Declarations, globals, inline asm or new attribute groups are outside v1')
    ops=set(instructions(candidate))
    allowed={'add','sub','mul','udiv','sdiv','urem','srem','shl','lshr','ashr','and','or','xor',
             'icmp','select','phi','br','ret','unreachable','trunc','zext','sext',
             'load','store','alloca','getelementptr','bitcast','freeze'}
    if ops-allowed: errors.append('Unsupported instructions: '+','.join(sorted(ops-allowed)))
    if re.search(r'\b(volatile|atomic|asm|llvm\.assume)\b',c): errors.append('Unsupported effects/assumptions')
    # Reject cycles in the small label-based CFG; first iteration contains no loops.
    graph={}; block='entry'; graph[block]=set()
    for line in c.splitlines():
        label=re.match(r'^([\w.$-]+):',line)
        if label: block=label[1]; graph.setdefault(block,set())
        if line.startswith('br '): graph[block].update(re.findall(r'label %([\w.$-]+)',line))
    visiting=set(); seen=set()
    def visit(v):
        if v in visiting: return True
        if v in seen: return False
        visiting.add(v)
        for w in graph.get(v,()):
            if visit(w): return True
        visiting.remove(v); seen.add(v); return False
    if any(visit(v) for v in list(graph)): errors.append('Loops are outside the v1 contract')
    return errors
