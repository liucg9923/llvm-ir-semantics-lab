"""Unambiguous formatting extraction, without selecting or repairing program contents."""
import re

def extract(raw):
    if len(raw)>262144:raise ValueError('Output exceeds byte budget')
    s=raw.strip();forms=[]
    if '```' in s:
        if s.count('```')!=2:raise ValueError('Multiple or unbalanced code fences')
        m=re.search(r'```(?:llvm|llvm-ir|ir)?[ \t]*\n(.*?)```',s,re.S)
        if not m:raise ValueError('Unsupported code fence')
        outside=s[:m.start()]+s[m.end():]
        if '<code>' in outside or '</code>' in outside or re.search(r'^\s*define\b',outside,re.M):raise ValueError('Multiple possible IR candidates')
        s=m[1].strip();forms.append('fence')
    if '<code>' in s or '</code>' in s:
        if s.count('<code>')!=1 or s.count('</code>')!=1:raise ValueError('Multiple or unbalanced code tags')
        m=re.search(r'<code>\s*(.*?)\s*</code>',s,re.S)
        if not m:raise ValueError('Invalid code-tag order')
        outside=s[:m.start()]+s[m.end():]
        if re.search(r'^\s*define\b',outside,re.M):raise ValueError('IR appears outside the unique code block')
        s=m[1].strip();forms.append('code_tag')
    if not re.match(r'(;|target\b|source_filename\b|define\b)',s):raise ValueError('No unique complete LLVM module')
    return s+'\n',forms or ['plain_ir']
