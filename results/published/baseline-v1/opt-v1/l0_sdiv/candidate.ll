; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l0_sdiv/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l0_sdiv/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %r = sdiv i32 %x, 4
  ret i32 %r
}
