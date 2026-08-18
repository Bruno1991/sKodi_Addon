.text
.globl mbuc_secure_copy
.type mbuc_secure_copy,@function
# System V AMD64 ABI
# rdi=destination, rsi=capacity, rdx=source, rcx=count
# returns 0 success, -1 null pointer for nonzero count, -2 insufficient capacity
# This leaf function does not change rsp and therefore cannot overflow the stack.
mbuc_secure_copy:
    test %rcx, %rcx
    je .success
    test %rdi, %rdi
    je .null_pointer
    test %rdx, %rdx
    je .null_pointer
    cmp %rcx, %rsi
    jb .insufficient
    cmp %rdx, %rdi
    jbe .forward
    lea -1(%rdx,%rcx), %r8
    cmp %r8, %rdi
    ja .forward
    lea -1(%rdi,%rcx), %rdi
    lea -1(%rdx,%rcx), %rsi
    std
    rep movsb
    cld
    xor %eax, %eax
    ret
.forward:
    mov %rdx, %rsi
    rep movsb
.success:
    xor %eax, %eax
    ret
.null_pointer:
    mov $-1, %eax
    ret
.insufficient:
    mov $-2, %eax
    ret
.size mbuc_secure_copy, .-mbuc_secure_copy
.section .note.GNU-stack,"",@progbits
