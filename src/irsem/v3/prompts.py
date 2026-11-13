from pathlib import Path
import re,tempfile
from irsem.common import run_process
from irsem.evaluate import tool
from .evaluate import inspect

def source_facts(root,task):
    with tempfile.TemporaryDirectory(prefix='irsem-v3-size-') as td:
        p=Path(td);s,log=inspect(root,task.file('source'),p/'source.ll')
        if s is None:raise ValueError('Source LLVM parsing failed')
        b=run_process([tool('clang'),'-Wno-override-module','-c',str(task.file('source')),'-o',str(p/'source.o')],60)
        if b.returncode or b.timed_out:raise ValueError('Input object-size measurement failed')
        r=run_process(['/usr/lib/llvm-17/bin/llvm-size','--format=sysv','--radix=10',str(p/'source.o')],15)
        if r.returncode:raise ValueError('llvm-size unavailable')
        sections={m[1]:int(m[2]) for line in r.stdout.splitlines() if (m:=re.match(r'\s*(\.\S+)\s+(\d+)\s+',line))}
        if '.text' not in sections:raise ValueError('No text section measured')
        return {'instruction_count':s['instructions'],'binary_size_bytes':sections.get('.text',0)+sections.get('.data',0),'sections':sections,'measurement':'clang -c default optimization; sum .text + .data only','clang_log':b.as_dict(),'size_log':r.as_dict()}

def native(task,facts,hint=None):
    text=(f"Give the LLVM-IR for the following code when optimized using opt -p '{task.spec['pipeline']}':\n"
      f"<code>\n{task.text()}</code>\n"
      f"The input code has instruction count {facts['instruction_count']} and binary size {facts['binary_size_bytes']} bytes.")
    if hint:
        text+='\n\nSemantic check for this task: '+hint['text']+' Preserve the original behavior; the example is a diagnostic constraint, not the complete specification.'
    return text
