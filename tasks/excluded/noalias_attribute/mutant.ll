target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(ptr noalias noundef %p, ptr noalias noundef %q) {
entry:
  %a = load i32, ptr %p, align 4
  %r = add i32 %a, %a
  ret i32 %r
}
