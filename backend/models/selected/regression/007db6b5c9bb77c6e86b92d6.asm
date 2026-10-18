.intel_syntax noprefix
.section .text.f1,"ax",@progbits
.globl f1
.type f1,@function
f1:
.cfi_startproc
endbr64
push	rbp
.cfi_def_cfa_offset 16
.cfi_offset 6, -16
mov	rbp, rsp
.cfi_def_cfa_register 6
push	r12
push	rbx
sub	rsp, 160
.cfi_offset 12, -24
.cfi_offset 3, -32
mov	QWORD PTR -168[rbp], rdi
mov	QWORD PTR -176[rbp], rsi
mov	rax, QWORD PTR fs:40
mov	QWORD PTR -24[rbp], rax
xor	eax, eax
mov	DWORD PTR -156[rbp], 0
mov	rax, QWORD PTR -176[rbp]
mov	QWORD PTR -104[rbp], rax
mov	rax, QWORD PTR -104[rbp]
mov	rdi, rax
call	x1
mov	QWORD PTR -120[rbp], rax
mov	rax, QWORD PTR -104[rbp]
mov	rdi, rax
call	x0
mov	QWORD PTR -112[rbp], rax
jmp	.L38
.L30:
mov	rax, QWORD PTR -120[rbp]
mov	QWORD PTR -96[rbp], rax
mov	rax, QWORD PTR -96[rbp]
mov	eax, DWORD PTR [rax]
test	eax, eax
je	.L35
mov	rax, QWORD PTR -96[rbp]
mov	ebx, DWORD PTR [rax]
mov	eax, DWORD PTR -156[rbp]
lea	edx, 1[rax]
mov	DWORD PTR -156[rbp], edx
movsxd	rdx, eax
mov	rax, QWORD PTR -176[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x2
mov	DWORD PTR [rax], ebx
.L35:
mov	rax, QWORD PTR -120[rbp]
add	rax, 4
mov	QWORD PTR -120[rbp], rax
nop
.L38:
lea	rax, -120[rbp]
mov	QWORD PTR -88[rbp], rax
mov	rax, QWORD PTR -88[rbp]
mov	rdx, QWORD PTR [rax]
lea	rax, -112[rbp]
mov	QWORD PTR -80[rbp], rax
mov	rax, QWORD PTR -80[rbp]
mov	rax, QWORD PTR [rax]
cmp	rdx, rax
sete	al
xor	eax, 1
test	al, al
jne	.L30
mov	DWORD PTR -160[rbp], 0
mov	rax, QWORD PTR -176[rbp]
mov	rdi, rax
call	x0
mov	rbx, rax
mov	eax, DWORD PTR -156[rbp]
movsxd	r12, eax
mov	rax, QWORD PTR -176[rbp]
mov	rdi, rax
call	x1
mov	QWORD PTR -112[rbp], rax
mov	QWORD PTR -72[rbp], r12
mov	rax, QWORD PTR -72[rbp]
mov	QWORD PTR -64[rbp], rax
mov	rax, QWORD PTR -64[rbp]
mov	QWORD PTR -56[rbp], rax
lea	rax, -112[rbp]
mov	QWORD PTR -48[rbp], rax
nop
mov	rdx, QWORD PTR -56[rbp]
lea	rax, -112[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x4
nop
mov	rax, QWORD PTR -112[rbp]
mov	QWORD PTR -152[rbp], rax
mov	QWORD PTR -144[rbp], rbx
mov	rax, QWORD PTR -152[rbp]
mov	QWORD PTR -136[rbp], rax
mov	rax, QWORD PTR -144[rbp]
mov	QWORD PTR -128[rbp], rax
lea	rax, -160[rbp]
mov	QWORD PTR -40[rbp], rax
mov	rax, QWORD PTR -136[rbp]
mov	QWORD PTR -120[rbp], rax
mov	rax, QWORD PTR -128[rbp]
mov	QWORD PTR -112[rbp], rax
mov	rax, QWORD PTR -40[rbp]
mov	QWORD PTR -32[rbp], rax
lea	rax, -112[rbp]
mov	rcx, QWORD PTR [rax]
lea	rax, -120[rbp]
mov	rax, QWORD PTR [rax]
mov	rdx, QWORD PTR -32[rbp]
mov	rsi, rcx
mov	rdi, rax
call	x5
nop
nop
nop
nop
mov	rax, QWORD PTR -24[rbp]
sub	rax, QWORD PTR fs:40
je	.L86
call	x6@PLT
.L86:
add	rsp, 160
pop	rbx
pop	r12
pop	rbp
.cfi_def_cfa 7, 8
ret
.cfi_endproc
.size f1,.-f1
.section .note.GNU-stack,"",@progbits
