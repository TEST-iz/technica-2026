.intel_syntax noprefix
.section .text.f1,"ax",@progbits
.globl f1
.type f1,@function
f1:
.L52:
.cfi_startproc
.cfi_personality 0x9b,d12
.cfi_lsda 0x1b,d3
endbr64
push	rbp
.cfi_def_cfa_offset 16
.cfi_offset 6, -16
mov	rbp, rsp
.cfi_def_cfa_register 6
push	rbx
sub	rsp, 152
.cfi_offset 3, -24
mov	QWORD PTR -136[rbp], rdi
mov	QWORD PTR -144[rbp], rsi
mov	QWORD PTR -152[rbp], rdx
mov	QWORD PTR -160[rbp], rcx
mov	rax, QWORD PTR fs:40
mov	QWORD PTR -24[rbp], rax
xor	eax, eax
mov	rax, QWORD PTR -152[rbp]
mov	rdi, rax
call	x4
mov	rbx, rax
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x4
cmp	rax, rbx
setb	al
test	al, al
je	.L54
mov	rax, QWORD PTR -136[rbp]
mov	rcx, QWORD PTR -152[rbp]
mov	rdx, QWORD PTR -160[rbp]
mov	rsi, QWORD PTR -144[rbp]
mov	rdi, rax
.L53:
call	f1
jmp	.L109
.L54:
mov	rax, QWORD PTR -152[rbp]
mov	rdi, rax
call	x12
mov	rbx, rax
mov	rax, QWORD PTR -152[rbp]
mov	rdi, rax
call	x14
mov	rsi, rbx
mov	rdi, rax
call	x22
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x12
mov	rbx, rax
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x14
mov	rsi, rbx
mov	rdi, rax
call	x22
.L55:
pxor	xmm0, xmm0
movaps	XMMWORD PTR -48[rbp], xmm0
movq	QWORD PTR -32[rbp], xmm0
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x7
mov	QWORD PTR -128[rbp], rax
mov	rax, QWORD PTR -152[rbp]
mov	QWORD PTR -96[rbp], rax
mov	rax, QWORD PTR -96[rbp]
mov	rdi, rax
call	x14
mov	QWORD PTR -120[rbp], rax
mov	rax, QWORD PTR -96[rbp]
mov	rdi, rax
call	x12
mov	QWORD PTR -112[rbp], rax
jmp	.L89
.L57:
mov	rax, QWORD PTR -120[rbp]
mov	QWORD PTR -88[rbp], rax
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x3
mov	rcx, rax
mov	rdx, QWORD PTR -88[rbp]
mov	rax, QWORD PTR -128[rbp]
mov	rsi, rcx
mov	rdi, rax
.L62:
call	x18
mov	QWORD PTR -128[rbp], rax
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x12
mov	QWORD PTR -104[rbp], rax
lea	rax, -128[rbp]
mov	QWORD PTR -80[rbp], rax
mov	rax, QWORD PTR -80[rbp]
mov	rdx, QWORD PTR [rax]
lea	rax, -104[rbp]
mov	QWORD PTR -72[rbp], rax
mov	rax, QWORD PTR -72[rbp]
mov	rax, QWORD PTR [rax]
cmp	rdx, rax
sete	al
xor	eax, 1
test	al, al
je	.L79
mov	rax, QWORD PTR -128[rbp]
mov	edx, DWORD PTR [rax]
mov	rax, QWORD PTR -88[rbp]
mov	eax, DWORD PTR [rax]
cmp	edx, eax
jne	.L79
mov	eax, 1
jmp	.L80
.L79:
mov	eax, 0
.L80:
test	al, al
je	.L86
mov	rdx, QWORD PTR -128[rbp]
lea	rax, -48[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x11
mov	rax, QWORD PTR -160[rbp]
mov	rdi, rax
call	x3
mov	rcx, rax
mov	rdx, QWORD PTR -88[rbp]
mov	rax, QWORD PTR -128[rbp]
mov	rsi, rcx
mov	rdi, rax
call	x19
.L85:
mov	QWORD PTR -128[rbp], rax
.L86:
mov	rax, QWORD PTR -120[rbp]
add	rax, 4
mov	QWORD PTR -120[rbp], rax
nop
.L89:
lea	rax, -120[rbp]
mov	QWORD PTR -64[rbp], rax
mov	rax, QWORD PTR -64[rbp]
mov	rdx, QWORD PTR [rax]
lea	rax, -112[rbp]
mov	QWORD PTR -56[rbp], rax
mov	rax, QWORD PTR -56[rbp]
mov	rax, QWORD PTR [rax]
cmp	rdx, rax
sete	al
xor	eax, 1
test	al, al
jne	.L57
lea	rdx, -48[rbp]
mov	rax, QWORD PTR -136[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x16
lea	rax, -48[rbp]
mov	rdi, rax
call	x17
jmp	.L109
.L105:
endbr64
mov	rbx, rax
lea	rax, -48[rbp]
mov	rdi, rax
call	x17
mov	rax, rbx
mov	rdx, QWORD PTR -24[rbp]
sub	rdx, QWORD PTR fs:40
je	.L106
call	x25@PLT
.L106:
mov	rdi, rax
.L107:
call	x0@PLT
.L108:
.L109:
mov	rax, QWORD PTR -24[rbp]
sub	rax, QWORD PTR fs:40
je	.L110
call	x25@PLT
.L110:
mov	rax, QWORD PTR -136[rbp]
mov	rbx, QWORD PTR -8[rbp]
leave
.cfi_def_cfa 7, 8
ret
.cfi_endproc
.size f1,.-f1
.section .gcc_except_table.lc2,"a",@progbits
d3:
.byte	0xff
.byte	0xff
.byte	0x1
.uleb128 d5-d4
d4:
.uleb128 .L53-.L52
.uleb128 .L55-.L53
.uleb128 0
.uleb128 0
.uleb128 .L62-.L52
.uleb128 .L85-.L62
.uleb128 .L105-.L52
.uleb128 0
.uleb128 .L107-.L52
.uleb128 .L108-.L107
.uleb128 0
.uleb128 0
d5:
.section .lcdata19,"aw",@progbits
.align 8
d12:
.quad	x24
.section .note.GNU-stack,"",@progbits
