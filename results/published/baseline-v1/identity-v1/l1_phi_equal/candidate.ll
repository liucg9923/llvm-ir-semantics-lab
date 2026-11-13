target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %c = icmp eq i32 %x, 0
  br i1 %c, label %a, label %b
a:
  br label %merge
b:
  br label %merge
merge:
  %r = phi i32 [7, %a], [7, %b]
  ret i32 %r
}
