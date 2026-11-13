; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l0_signed_cmp/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l0_signed_cmp/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %c = icmp sgt i32 %x, -1
  %r = zext i1 %c to i32
  ret i32 %r
}
