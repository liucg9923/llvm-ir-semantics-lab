; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l2_disjoint/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l2_disjoint/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(ptr noundef %p, ptr noundef %q) {
entry:
  %separate = getelementptr i32, ptr %p, i64 1
  %a = load i32, ptr %p, align 4
  store i32 7, ptr %separate, align 4
  %r = add i32 %a, %a
  ret i32 %r
}
