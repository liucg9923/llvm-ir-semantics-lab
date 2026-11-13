target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x, i32 noundef %y) {
entry:
  %r = add i32 %x, %y
  ret i32 %r
}
