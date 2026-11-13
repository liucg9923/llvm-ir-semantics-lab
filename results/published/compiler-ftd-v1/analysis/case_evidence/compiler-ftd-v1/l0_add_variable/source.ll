target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %c = add i32 %x, 5
  %r = add i32 %x, %c
  ret i32 %r
}
