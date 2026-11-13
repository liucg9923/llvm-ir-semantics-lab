"""Explicit bounded-function admission policy over LLVM-parsed structure."""
import re
ALLOWED_OPS={'add','sub','mul','udiv','sdiv','urem','srem','shl','lshr','ashr','and','or','xor','icmp','select','phi','br','switch','ret','unreachable','trunc','zext','sext','load','store','alloca','getelementptr','bitcast','freeze'}
# Valid for the accepted acyclic, call-free, non-atomic, integer-only functions.
STRUCTURAL_FACTS={'mustprogress','nofree','norecurse','nosync','nounwind','willreturn'}
HINTS={'minsize','optsize','optnone','noinline','alwaysinline','inlinehint','uwtable','uwtable(sync)','uwtable(async)','nocallback'}
STRING_HINTS={'min-legal-vector-width':{'0'},'no-trapping-math':{'true'},'stack-protector-buffer-size':{'8'},'target-cpu':{'x86-64','generic'},'target-features':{'+cmov,+cx8,+fxsr,+mmx,+sse,+sse2,+x87'},'tune-cpu':{'generic'},'frame-pointer':{'all','none','non-leaf'}}
KNOWN_FLAGS={'wchar_size':{4},'PIC Level':{0,1,2},'PIE Level':{0,1,2},'uwtable':{0,1,2}}

def errors(source,candidate):
    interface=[];unsupported=[];assumptions=[]
    if candidate['definitions']!=1:interface.append('Expected exactly one defined function')
    if candidate['declarations'] or candidate['globals'] or candidate['aliases'] or candidate['ifuncs'] or candidate['module_asm']:
        unsupported.append('The supported object is one defined function without externals/globals/inline asm')
    if len(candidate['functions'])!=1:return {'interface':interface,'unsupported':unsupported,'assumptions':assumptions}
    s=source['functions'][0];c=candidate['functions'][0]
    for k in ['name','return_type','vararg','calling_convention','linkage','visibility','address_space']:
        if s[k]!=c[k]:interface.append(k+' changed')
    if [p['type'] for p in s['params']]!=[p['type'] for p in c['params']]:interface.append('parameter types changed')
    if source['abi_target_key']!=candidate['abi_target_key']:interface.append('target ABI changed')
    if source['target_vendor']!=candidate['target_vendor'] and not {source['target_vendor'],candidate['target_vendor']} <= {'pc','unknown'}:interface.append('unvalidated vendor change')
    if not candidate['layout_equivalent_for_used_types']:interface.append('data-layout properties for used types changed')
    if any(c[k] for k in ['personality','prefix_data','prologue_data','gc','address_taken']):unsupported.append('Unsupported execution context')
    unsupported+=candidate['scope_errors']
    if candidate['cycles']:unsupported.append('Loops are outside this experiment')
    extra=set(candidate['opcodes'])-ALLOWED_OPS
    if extra:unsupported.append('Unsupported opcodes: '+','.join(sorted(extra)))
    if candidate['instruction_metadata']:unsupported.append('Instruction metadata requires a separately validated semantic model: '+','.join(sorted(set(candidate['instruction_metadata']))))
    for n in candidate['named_metadata']:
        if n not in {'llvm.ident','llvm.module.flags'}:unsupported.append('Unsupported named metadata: '+n)
    for flag in candidate['module_flags']:
        if flag['name'] not in KNOWN_FLAGS or flag.get('value') not in KNOWN_FLAGS[flag['name']]:unsupported.append('Unsupported module flag: '+flag['name'])
    accesses=candidate['memory_accesses']
    if any(a['roots']&(1<<17) for a in accesses):unsupported.append('Memory pointers outside supported argument/alloca roots')
    reads=[a for a in accesses if a['op']=='load'];writes=[a for a in accesses if a['op']=='store']
    # Capture/argument effect guarantees are checked from the accepted body; input preconditions may not be strengthened.
    for i,(sp,cp) in enumerate(zip(s['params'],c['params'])):
        old=set(sp['attrs'])
        for at in set(cp['attrs'])-old:
            if at=='nocapture' and not candidate['pointer_compare']:continue
            if at=='readonly' and not any(a['roots']&(1<<i) for a in writes):continue
            if at=='writeonly' and not any(a['roots']&(1<<i) for a in reads):continue
            if at=='readnone' and not any(a['roots']&(1<<i) for a in accesses):continue
            if at in {'nocapture','readonly','writeonly','readnone'}:unsupported.append(f'Parameter effect/capture claim not proved: {i} {at}')
            else:assumptions.append(f'Unproved new parameter {i} attribute: {at}')
    if set(c['return_attrs'])-set(s['return_attrs']):unsupported.append('New return guarantees need a separate validator')
    source_strings={a.split('=',1)[0]:a for a in s['function_attrs'] if a.startswith('"')}
    for at in c['function_attrs']:
        if at in STRUCTURAL_FACTS or at in HINTS:continue
        if at.startswith('"'):
            key=at.split('=',1)[0];name=key.strip('"')
            # Only familiar code-generation hints for this integer-only task; target feature strings must match the source if provided there.
            if name in STRING_HINTS and ((key in source_strings and source_strings[key]==at) or (key not in source_strings and '=' in at and at.split('=',1)[1].strip('\"') in STRING_HINTS[name])):continue
            unsupported.append('Unvalidated string attribute: '+at);continue
        if at.startswith('memory('):
            compact=at.replace(' ','')
            ok=(compact=='memory(none)' and not accesses) or (compact=='memory(read)' and not writes) or (compact=='memory(write)' and not reads) or compact=='memory(readwrite)'
            argonly=all(not (a['roots']&((1<<16)|(1<<17))) for a in accesses)
            ok=ok or (argonly and ((compact=='memory(argmem:read)' and not writes) or (compact=='memory(argmem:write)' and not reads) or compact=='memory(argmem:readwrite)'))
            if not ok:unsupported.append('Memory-effects claim not justified by the accepted body: '+at)
            continue
        unsupported.append('Unvalidated function attribute: '+at)
    return {'interface':interface,'unsupported':unsupported,'assumptions':assumptions}
