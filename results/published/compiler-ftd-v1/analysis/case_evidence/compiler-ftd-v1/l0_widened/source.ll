target datalayout = "e-p:64:64-i64:64-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @f(i32 noundef %x) {
entry:
  %v = trunc i32 %x to i8
  %w = zext i8 %v to i16
  %a = add i16 %w, 1
  %c = icmp ugt i16 %a, %w
  %r = zext i1 %c to i32
  ret i32 %r
}
