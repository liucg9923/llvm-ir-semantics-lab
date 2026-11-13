; ModuleID = '/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l1_phi_different/source.ll'
source_filename = "/root/autodl-tmp/llvm-ir-semantics-lab/tasks/test/l1_phi_different/source.ll"
target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %c = icmp eq i32 %x, 0
  %. = select i1 %c, i32 7, i32 9
  ret i32 %.
}
