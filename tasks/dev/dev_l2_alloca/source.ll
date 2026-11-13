target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %a = alloca i32, align 4
  store i32 13, ptr %a, align 4
  %r = load i32, ptr %a, align 4
  ret i32 %r
}
