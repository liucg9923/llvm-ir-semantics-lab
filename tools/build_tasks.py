"""Author-owned fixture generator; never derives cases from model outputs.

Re-running this script changes the working dataset only. `irsem freeze` is a
separate, explicit action; the runner rejects a stale dataset lock.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
HEADER = 'target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"\ntarget triple = "x86_64-pc-linux-gnu"\n\n'
TASKS = []

def module(body, abi='unary', noalias=False):
    args = {'unary':'i32 noundef %x', 'binary':'i32 noundef %x, i32 noundef %y',
            'memory':('ptr noalias noundef %p, ptr noalias noundef %q' if noalias else 'ptr noundef %p, ptr noundef %q')}[abi]
    return HEADER + f'define i32 @f({args}) {{\n' + body.strip() + '\n}\n'

def add(id, level, pair, role, source, reference, mutant, goal, description,
        pipeline='function(instcombine)', abi='unary', noalias=False, split='test', exhaustive=False):
    folder=ROOT/'tasks'/split/id
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in [('source',source),('reference',reference),('mutant',mutant)]:
        (folder/f'{name}.ll').write_text(module(body,abi,noalias),encoding='utf-8')
    TASKS.append(dict(id=id,level=level,pair_id=pair,role=role,split=split,
        directory=str(folder.relative_to(ROOT)),abi=abi,noalias=noalias,
        exhaustive_low_byte=exhaustive,pipeline=pipeline,goal=goal,description=description,
        input_domain=('Two valid aligned uint32 locations; alias allowed.' if abi=='memory' and not noalias else
                      'Two distinct valid aligned uint32 locations; no alias.' if abi=='memory' else
                      'All i32 bit patterns; integer operations use LLVM semantics.'),
        provenance='Original educational example, authored for this project; mutant is manually constructed.'))

# L0: four pairs. A guard reference is deliberately the source itself; this is
# not a claim that every other semantics-preserving improvement is impossible.
s='entry:\n  %c = add i32 4, 5\n  %r = add i32 %x, %c\n  ret i32 %r'
add('l0_add_fold','L0','add_constant','opportunity',s,'entry:\n  %r = add i32 %x, 9\n  ret i32 %r','entry:\n  ret i32 %x',{'opcode_max':{'add':1}},'Fold a constant expression without deleting its contribution.')
s='entry:\n  %c = add i32 %x, 5\n  %r = add i32 %x, %c\n  ret i32 %r'
add('l0_add_variable','L0','add_constant','guard',s,s,'entry:\n  %r = add i32 %x, 9\n  ret i32 %r',{},'The apparent constant now depends on an input.')
s='entry:\n  %v = trunc i32 %x to i8\n  %w = zext i8 %v to i16\n  %a = add i16 %w, 1\n  %c = icmp ugt i16 %a, %w\n  %r = zext i1 %c to i32\n  ret i32 %r'
add('l0_widened','L0','increment_width','opportunity',s,'entry:\n  ret i32 1','entry:\n  ret i32 0',{'instruction_max':1},'Increment after widening cannot wrap in this range.',exhaustive=True)
s='entry:\n  %v = trunc i32 %x to i8\n  %a = add i8 %v, 1\n  %c = icmp ugt i8 %a, %v\n  %r = zext i1 %c to i32\n  ret i32 %r'
add('l0_wrap','L0','increment_width','guard',s,s,'entry:\n  ret i32 1',{},'i8 wraps at 255; the comparison is not always true.',exhaustive=True)
s='entry:\n  %r = udiv i32 %x, 4\n  ret i32 %r'
add('l0_udiv','L0','division_sign','opportunity',s,'entry:\n  %r = lshr i32 %x, 2\n  ret i32 %r','entry:\n  %r = ashr i32 %x, 2\n  ret i32 %r',{'opcode_max':{'udiv':0}},'Unsigned division by four can use logical shift.')
s='entry:\n  %r = sdiv i32 %x, 4\n  ret i32 %r'
add('l0_sdiv','L0','division_sign','guard',s,s,'entry:\n  %r = ashr i32 %x, 2\n  ret i32 %r',{},'Signed division rounds toward zero, not toward negative infinity.')
s='entry:\n  %c = icmp uge i32 %x, 0\n  %r = zext i1 %c to i32\n  ret i32 %r'
add('l0_unsigned_cmp','L0','comparison_sign','opportunity',s,'entry:\n  ret i32 1','entry:\n  ret i32 0',{'instruction_max':1},'Unsigned values are always at least zero.')
s='entry:\n  %c = icmp sge i32 %x, 0\n  %r = zext i1 %c to i32\n  ret i32 %r'
add('l0_signed_cmp','L0','comparison_sign','guard',s,s,'entry:\n  ret i32 1',{},'The signed comparison depends on the sign bit.')

# L1: control-flow and value-dependency pairs.
branch='entry:\n  %c = icmp eq i32 %x, 0\n  br i1 COND, label %a, label %b\na:\n  %u = add i32 %x, 1\n  ret i32 %u\nb:\n  %v = sub i32 %x, 1\n  ret i32 %v'
good='entry:\n  %r = add i32 %x, 1\n  ret i32 %r'
add('l1_const_branch','L1','branch_condition','opportunity',branch.replace('COND','true'),good,'entry:\n  %r = sub i32 %x, 1\n  ret i32 %r',{'opcode_max':{'br':0}},'Only one branch is reachable.',pipeline='function(sccp,simplifycfg,dce)')
s=branch.replace('COND','%c')
add('l1_variable_branch','L1','branch_condition','guard',s,s,good,{},'A variable condition cannot be replaced by a constant.',pipeline='function(sccp,simplifycfg,dce)')
phi='entry:\n  %c = icmp eq i32 %x, 0\n  br i1 %c, label %a, label %b\na:\n  br label %merge\nb:\n  br label %merge\nmerge:\n  %r = phi i32 [7, %a], [VALUE, %b]\n  ret i32 %r'
add('l1_phi_equal','L1','phi_values','opportunity',phi.replace('VALUE','7'),'entry:\n  ret i32 7','entry:\n  ret i32 9',{'instruction_max':1},'All incoming phi values agree.',pipeline='function(simplifycfg,instcombine,dce)')
s=phi.replace('VALUE','9')
add('l1_phi_different','L1','phi_values','guard',s,s,'entry:\n  ret i32 7',{},'Different incoming values carry observable information.',pipeline='function(simplifycfg,instcombine,dce)')
s='entry:\n  %unused = mul i32 %x, 17\n  ret i32 %x'
add('l1_dead_value','L1','value_liveness','opportunity',s,'entry:\n  ret i32 %x','entry:\n  ret i32 0',{'opcode_max':{'mul':0}},'An unused pure computation can be removed.',pipeline='function(dce)')
s='entry:\n  %v = mul i32 %x, 17\n  %c = icmp eq i32 %x, 0\n  br i1 %c, label %a, label %b\na:\n  ret i32 %x\nb:\n  ret i32 %v'
add('l1_live_on_path','L1','value_liveness','guard',s,s,'entry:\n  ret i32 %x',{},'A value used on one reachable path is live.',pipeline='function(dce)')
cse='entry:\n  %a = add i32 %x, %y\n  %b = add i32 %x, VALUE\n  %r = add i32 %a, %b\n  ret i32 %r'
good='entry:\n  %a = add i32 %x, %y\n  %r = shl i32 %a, 1\n  ret i32 %r'
add('l1_cse_equal','L1','expression_operands','opportunity',cse.replace('VALUE','%y'),good,'entry:\n  %r = add i32 %x, %y\n  ret i32 %r',{'instruction_max':3},'Equivalent expressions can share a computed value.',pipeline='function(gvn,instcombine)',abi='binary')
s=cse.replace('VALUE','1')
add('l1_cse_different','L1','expression_operands','guard',s,s,good,{},'Similar-looking expressions have different operands.',pipeline='function(gvn,instcombine)',abi='binary')

# L2: externally observable memory, no volatile/atomic/concurrency.
s='entry:\n  %a = load i32, ptr %p, align 4\n  store i32 7, ptr %q, align 4\n  %b = load i32, ptr %p, align 4\n  %r = add i32 %a, %b\n  ret i32 %r'
good='entry:\n  %a = load i32, ptr %p, align 4\n  store i32 7, ptr %q, align 4\n  %r = add i32 %a, %a\n  ret i32 %r'
bad='entry:\n  %a = load i32, ptr %p, align 4\n  %r = add i32 %a, %a\n  ret i32 %r'
disjoint_s=s.replace('entry:\n','entry:\n  %separate = getelementptr i32, ptr %p, i64 1\n').replace('store i32 7, ptr %q','store i32 7, ptr %separate')
disjoint_good=good.replace('entry:\n','entry:\n  %separate = getelementptr i32, ptr %p, i64 1\n').replace('store i32 7, ptr %q','store i32 7, ptr %separate')
add('l2_disjoint','L2','pointer_alias','opportunity',disjoint_s,disjoint_good,bad,{'opcode_max':{'load':1}},'Adjacent aligned i32 locations cannot overlap; the store remains observable.',pipeline='function(gvn)',abi='memory')
TASKS[-1]['input_domain']='p points to the first of two adjacent valid aligned uint32 locations; q is valid and may equal p.'
add('l2_mayalias','L2','pointer_alias','guard',s,s,good,{},'With p==q and initial 3, source returns 10, mutant returns 6.',pipeline='function(gvn)',abi='memory')
s='entry:\n  store i32 3, ptr %p, align 4\n  store i32 7, ptr %p, align 4\n  ret i32 0'
good='entry:\n  store i32 7, ptr %p, align 4\n  ret i32 0'
add('l2_store_overwritten','L2','store_observation','opportunity',s,good,'entry:\n  ret i32 0',{'opcode_max':{'store':1}},'An overwritten store without an intervening observation can disappear.',pipeline='function(dse)',abi='memory')
s='entry:\n  store i32 3, ptr %p, align 4\n  %v = load i32, ptr %p, align 4\n  store i32 7, ptr %p, align 4\n  ret i32 %v'
bad='entry:\n  %v = load i32, ptr %p, align 4\n  store i32 7, ptr %p, align 4\n  ret i32 %v'
add('l2_store_observed','L2','store_observation','guard',s,s,bad,{},'A load observes the first store; deleting just that store is unsafe.',pipeline='function(dse)',abi='memory')
s='entry:\n  %local = alloca i32, align 4\n  store i32 7, ptr %local, align 4\n  ret i32 0'
add('l2_local_store','L2','store_escape','opportunity',s,'entry:\n  ret i32 0','entry:\n  store i32 7, ptr %p, align 4\n  ret i32 0',{'opcode_max':{'store':0}},'A nonescaping local store is unobservable.',pipeline='function(dse,dce)',abi='memory')
s='entry:\n  store i32 7, ptr %p, align 4\n  ret i32 0'
add('l2_escaped_store','L2','store_escape','guard',s,s,'entry:\n  ret i32 0',{},'A store through a caller-provided pointer is observable.',pipeline='function(dse,dce)',abi='memory')
s='entry:\n  store i32 7, ptr %p, align 4\n  store i32 7, ptr %p, align 4\n  ret i32 0'
good='entry:\n  store i32 7, ptr %p, align 4\n  ret i32 0'
add('l2_duplicate_store','L2','store_destination','opportunity',s,good,'entry:\n  ret i32 0',{'opcode_max':{'store':1}},'Repeated stores to the same location are redundant.',pipeline='function(dse)',abi='memory')
s='entry:\n  store i32 7, ptr %p, align 4\n  store i32 7, ptr %q, align 4\n  ret i32 0'
add('l2_distinct_store','L2','store_destination','guard',s,s,good,{},'Both locations may be observed, so one store cannot simply be deleted.',pipeline='function(dse)',abi='memory')

# Six development families, separate from the twelve formal families.
devs=[
 ('dev_l0_xor_self','L0','entry:\n  %r = xor i32 %x, %x\n  ret i32 %r','entry:\n  ret i32 0','entry:\n  ret i32 %x','unary',{'opcode_max':{'xor':0}},'function(instcombine)'),
 ('dev_l0_and_all','L0','entry:\n  %r = and i32 %x, -1\n  ret i32 %r','entry:\n  ret i32 %x','entry:\n  ret i32 0','unary',{'opcode_max':{'and':0}},'function(instcombine)'),
 ('dev_l1_select_equal','L1','entry:\n  %c = icmp eq i32 %x, 0\n  %r = select i1 %c, i32 11, i32 11\n  ret i32 %r','entry:\n  ret i32 11','entry:\n  ret i32 12','unary',{'instruction_max':1},'function(instcombine)'),
 ('dev_l1_unreachable','L1','entry:\n  ret i32 %x\ndead:\n  ret i32 99','entry:\n  ret i32 %x','entry:\n  ret i32 99','unary',{'instruction_max':1},'function(simplifycfg)'),
 ('dev_l2_forward','L2','entry:\n  store i32 11, ptr %p, align 4\n  %r = load i32, ptr %p, align 4\n  ret i32 %r','entry:\n  store i32 11, ptr %p, align 4\n  ret i32 11','entry:\n  ret i32 11','memory',{'opcode_max':{'load':0}},'function(gvn)'),
 ('dev_l2_alloca','L2','entry:\n  %a = alloca i32, align 4\n  store i32 13, ptr %a, align 4\n  %r = load i32, ptr %a, align 4\n  ret i32 %r','entry:\n  ret i32 13','entry:\n  ret i32 12','unary',{'instruction_max':1},'function(sroa,instcombine)')]
for id,level,s,r,m,abi,goal,pipe in devs:
    add(id,level,id,'opportunity',s,r,m,goal,'Development-only fixture; excluded from benchmark scores.',pipeline=pipe,abi=abi,split='dev')
(ROOT/'tasks/manifest.json').write_text(json.dumps({'schema_version':1,'tasks':TASKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Wrote {len(TASKS)} original tasks (6 dev, 24 test). Dataset lock NOT updated.')
