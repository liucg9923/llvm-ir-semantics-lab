; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l1_live_on_path/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l1_live_on_path/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %v = mul i32 %x, 17
  %c = icmp eq i32 %x, 0
  br i1 %c, label %a, label %b

a:                                                ; preds = %entry
  ret i32 %x

b:                                                ; preds = %entry
  ret i32 %v
}
