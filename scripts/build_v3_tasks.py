"""Author and lock fresh v3 programs before observing model outputs."""
from pathlib import Path
import json
from irsem.common import write_json
root=Path(__file__).resolve().parents[1];base=root/'tasks/v3'
if (base/'manifest.json').exists():raise SystemExit('Refuse to overwrite a versioned task set')
header='''source_filename = "irsem-v3.ll"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"
'''
suffix='''
attributes #0 = { minsize nounwind optsize uwtable "min-legal-vector-width"="0" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cmov,+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
!llvm.module.flags = !{!0, !1, !2, !3}
!llvm.ident = !{!4}
!0 = !{i32 1, !"wchar_size", i32 4}
!1 = !{i32 8, !"PIC Level", i32 2}
!2 = !{i32 7, !"PIE Level", i32 2}
!3 = !{i32 7, !"uwtable", i32 2}
!4 = !{!"irsem authored LLVM 17.0.6 tasks"}
'''
params={'unary':'i32 noundef %x','binary':'i32 noundef %x, i32 noundef %y','memory':'ptr noundef %p, ptr noundef %q'}
pipe='function(instcombine,simplifycfg,early-cse,gvn,dse,instcombine,simplifycfg)'
records=[]
def module(body,abi):return header+'\ndefine dso_local i32 @f('+params[abi]+') #0 {\n'+body.strip()+'\n}\n'+suffix
def add(id,level,pair,role,abi,body,reference,mutant,goal=None,desc=''):
 d=base/'test'/id;d.mkdir(parents=True)
 for name,text in [('source',body),('reference',reference or body),('mutant',mutant)]:
  (d/(name+'.ll')).write_text(module(text,abi))
 records.append({'id':id,'level':level,'pair_id':pair,'role':role,'split':'test','directory':str(d.relative_to(root)),'abi':abi,'noalias':False,'exhaustive_low_byte':False,'pipeline':pipe,'goal':goal or {},'description':desc,'input_domain':'Source LLVM-defined executions; differential tests sample initialized aligned cells and both alias patterns.','provenance':'Newly authored v3 program; not selected from model outputs. Reference and mutant are authored oracle fixtures.'})
add('v3_mask_partition','L0','mask_union','opportunity','unary','''entry:
 %lo = and i32 %x, 255
 %hi = and i32 %x, -256
 %r = or i32 %lo, %hi
 ret i32 %r''','entry:\n ret i32 %x','entry:\n %r = and i32 %x, 255\n ret i32 %r',{'instruction_max':1},'Complementary masks cover all bits.')
add('v3_mask_gap','L0','mask_union','guard','unary','''entry:
 %lo = and i32 %x, 255
 %hi = and i32 %x, -512
 %r = or i32 %lo, %hi
 ret i32 %r''',None,'entry:\n ret i32 %x',desc='Bit 8 is excluded; do not replace by identity.')
add('v3_xor_cancel','L0','xor_operands','opportunity','binary','''entry:
 %a = xor i32 %x, %y
 %r = xor i32 %a, %y
 ret i32 %r''','entry:\n ret i32 %x','entry:\n ret i32 %y',{'instruction_max':1})
add('v3_xor_changed','L0','xor_operands','guard','binary','''entry:
 %a = xor i32 %x, %y
 %r = xor i32 %a, %x
 ret i32 %r''',None,'entry:\n ret i32 %x')
add('v3_mask_bound','L0','bounded_value','opportunity','unary','''entry:
 %a = and i32 %x, 31
 %c = icmp ult i32 %a, 32
 %r = zext i1 %c to i32
 ret i32 %r''','entry:\n ret i32 1','entry:\n ret i32 0',{'instruction_max':1})
add('v3_mask_boundary','L0','bounded_value','guard','unary','''entry:
 %a = and i32 %x, 31
 %c = icmp ult i32 %a, 31
 %r = zext i1 %c to i32
 ret i32 %r''',None,'entry:\n ret i32 1')
add('v3_select_correlated','L1','select_path_fact','opportunity','unary','''entry:
 %c = icmp eq i32 %x, 0
 %r = select i1 %c, i32 %x, i32 0
 ret i32 %r''','entry:\n ret i32 0','entry:\n ret i32 %x',{'instruction_max':1})
add('v3_select_changed','L1','select_path_fact','guard','unary','''entry:
 %c = icmp eq i32 %x, 0
 %r = select i1 %c, i32 %x, i32 1
 ret i32 %r''',None,'entry:\n ret i32 0')
add('v3_branch_fact','L1','correlated_predicates','opportunity','unary','''entry:
 %c = icmp slt i32 %x, 5
 br i1 %c, label %a, label %b
a:
 %d = icmp slt i32 %x, 5
 %u = zext i1 %d to i32
 ret i32 %u
b:
 ret i32 0''','entry:\n %c = icmp slt i32 %x, 5\n %r = zext i1 %c to i32\n ret i32 %r','entry:\n ret i32 1',{'instruction_max':3})
add('v3_branch_stricter','L1','correlated_predicates','guard','unary','''entry:
 %c = icmp slt i32 %x, 5
 br i1 %c, label %a, label %b
a:
 %d = icmp slt i32 %x, 3
 %u = zext i1 %d to i32
 ret i32 %u
b:
 ret i32 0''',None,'entry:\n %c = icmp slt i32 %x, 5\n %r = zext i1 %c to i32\n ret i32 %r')
add('v3_phi_arithmetic','L1','phi_expression_equivalence','opportunity','unary','''entry:
 %bit = and i32 %x, 1
 %c = icmp eq i32 %bit, 0
 br i1 %c, label %a, label %b
a:
 %u = add i32 %x, 1
 br label %merge
b:
 %v = sub i32 %x, -1
 br label %merge
merge:
 %r = phi i32 [ %u, %a ], [ %v, %b ]
 ret i32 %r''','entry:\n %r = add i32 %x, 1\n ret i32 %r','entry:\n ret i32 %x',{'instruction_max':2})
add('v3_phi_changed','L1','phi_expression_equivalence','guard','unary','''entry:
 %bit = and i32 %x, 1
 %c = icmp eq i32 %bit, 0
 br i1 %c, label %a, label %b
a:
 %u = add i32 %x, 1
 br label %merge
b:
 %v = sub i32 %x, 1
 br label %merge
merge:
 %r = phi i32 [ %u, %a ], [ %v, %b ]
 ret i32 %r''',None,'entry:\n %r = add i32 %x, 1\n ret i32 %r')
add('v3_write_forward','L2','read_after_second_write','opportunity','memory','''entry:
 store i32 13, ptr %p, align 4
 store i32 29, ptr %p, align 4
 %r = load i32, ptr %p, align 4
 ret i32 %r''','entry:\n store i32 29, ptr %p, align 4\n ret i32 29','entry:\n store i32 13, ptr %p, align 4\n ret i32 13',{'opcode_max':{'load':0,'store':1}})
add('v3_write_alias','L2','read_after_second_write','guard','memory','''entry:
 store i32 13, ptr %p, align 4
 store i32 29, ptr %q, align 4
 %r = load i32, ptr %p, align 4
 ret i32 %r''',None,'entry:\n store i32 13, ptr %p, align 4\n store i32 29, ptr %q, align 4\n ret i32 13')
add('v3_narrow_forward','L2','narrow_load_alias','opportunity','memory','''entry:
 store i32 305397846, ptr %p, align 4
 %lo = load i16, ptr %p, align 2
 %r = zext i16 %lo to i32
 ret i32 %r''','entry:\n store i32 305397846, ptr %p, align 4\n ret i32 86','entry:\n store i32 305397846, ptr %p, align 4\n ret i32 4660',{'opcode_max':{'load':0}})
add('v3_narrow_alias','L2','narrow_load_alias','guard','memory','''entry:
 store i32 305397846, ptr %p, align 4
 %lo = load i16, ptr %q, align 2
 %r = zext i16 %lo to i32
 ret i32 %r''',None,'entry:\n store i32 305397846, ptr %p, align 4\n ret i32 86')
add('v3_store_back','L2','store_loaded_value','opportunity','memory','''entry:
 %a = load i32, ptr %p, align 4
 store i32 %a, ptr %p, align 4
 ret i32 %a''','entry:\n %a = load i32, ptr %p, align 4\n ret i32 %a','entry:\n store i32 0, ptr %p, align 4\n ret i32 0',{'opcode_max':{'store':0}})
add('v3_store_copy','L2','store_loaded_value','guard','memory','''entry:
 %a = load i32, ptr %p, align 4
 store i32 %a, ptr %q, align 4
 ret i32 %a''',None,'entry:\n %a = load i32, ptr %p, align 4\n ret i32 %a')
write_json(base/'manifest.json',{'schema_version':3,'tasks':records})
print('Authored',len(records),'fresh formal programs; none selected from model outputs')
