; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l1_cse_different/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l1_cse_different/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x, i32 noundef %y) {
entry:
  %a = add i32 %x, %y
  %b = add i32 %x, 1
  %r = add i32 %a, %b
  ret i32 %r
}
