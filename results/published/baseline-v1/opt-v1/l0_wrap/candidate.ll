; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l0_wrap/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l0_wrap/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %0 = and i32 %x, 255
  %c = icmp ne i32 %0, 255
  %r = zext i1 %c to i32
  ret i32 %r
}
