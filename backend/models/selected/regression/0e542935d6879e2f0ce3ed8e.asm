.intel_syntax noprefix
.section .text.f1,"ax",@progbits
.globl f1
.type f1,@function
f1:
.L94:
.cfi_startproc
.cfi_personality 0x9b,d6
.cfi_lsda 0x1b,d3
endbr64
push	rbp
.cfi_def_cfa_offset 16
.cfi_offset 6, -16
mov	rbp, rsp
.cfi_def_cfa_register 6
push	rbx
sub	rsp, 168
.cfi_offset 3, -24
mov	QWORD PTR -152[rbp], rdi
mov	QWORD PTR -160[rbp], rsi
mov	QWORD PTR -168[rbp], rdx
mov	rax, QWORD PTR fs:40
mov	QWORD PTR -24[rbp], rax
xor	eax, eax
mov	rax, QWORD PTR -152[rbp]
pxor	xmm0, xmm0
movups	XMMWORD PTR [rax], xmm0
movq	QWORD PTR 16[rax], xmm0
lea	rax, -96[rbp]
mov	rdi, rax
call	x16
mov	rax, QWORD PTR -168[rbp]
mov	QWORD PTR -128[rbp], rax
mov	rax, QWORD PTR -128[rbp]
mov	rdi, rax
call	x7
mov	QWORD PTR -144[rbp], rax
mov	rax, QWORD PTR -128[rbp]
mov	rdi, rax
call	x6
mov	QWORD PTR -136[rbp], rax
jmp	.L129
.L96:
mov	rax, QWORD PTR -144[rbp]
mov	QWORD PTR -120[rbp], rax
mov	rdx, QWORD PTR -120[rbp]
lea	rax, -64[rbp]
mov	rsi, rdx
mov	rdi, rax
.L102:
call	x15
.L103:
lea	rax, -64[rbp]
mov	rdi, rax
call	x13
nop
mov	rbx, rax
lea	rax, -64[rbp]
mov	rdi, rax
call	x14
nop
mov	rsi, rbx
mov	rdi, rax
.L112:
call	x19
lea	rax, -96[rbp]
mov	rdi, rax
call	x4
nop
xor	eax, 1
test	al, al
je	.L117
lea	rdx, -64[rbp]
lea	rax, -96[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x20
test	al, al
je	.L117
mov	eax, 1
jmp	.L118
.L117:
mov	eax, 0
.L118:
test	al, al
je	.L119
mov	ebx, 0
jmp	.L125
.L119:
lea	rdx, -64[rbp]
lea	rax, -96[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x18
mov	rdx, QWORD PTR -120[rbp]
mov	rax, QWORD PTR -152[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x5
.L124:
mov	ebx, 1
.L125:
lea	rax, -64[rbp]
mov	rdi, rax
call	x17
cmp	ebx, 1
mov	rax, QWORD PTR -144[rbp]
add	rax, 32
mov	QWORD PTR -144[rbp], rax
nop
.L129:
lea	rax, -144[rbp]
mov	QWORD PTR -112[rbp], rax
mov	rax, QWORD PTR -112[rbp]
mov	rdx, QWORD PTR [rax]
lea	rax, -136[rbp]
mov	QWORD PTR -104[rbp], rax
mov	rax, QWORD PTR -104[rbp]
mov	rax, QWORD PTR [rax]
cmp	rdx, rax
sete	al
xor	eax, 1
test	al, al
jne	.L96
lea	rax, -96[rbp]
mov	rdi, rax
call	x17
nop
mov	rax, QWORD PTR -24[rbp]
sub	rax, QWORD PTR fs:40
je	.L156
jmp	.L155
.L145:
endbr64
mov	rbx, rax
lea	rax, -64[rbp]
mov	rdi, rax
call	x17
jmp	.L151
.L148:
endbr64
mov	rbx, rax
.L151:
lea	rax, -96[rbp]
mov	rdi, rax
call	x17
mov	rax, QWORD PTR -152[rbp]
mov	rdi, rax
call	x8
mov	rax, rbx
mov	rdx, QWORD PTR -24[rbp]
sub	rdx, QWORD PTR fs:40
je	.L152
call	x23@PLT
.L152:
mov	rdi, rax
.L153:
call	x0@PLT
.L154:
.L155:
call	x23@PLT
.L156:
mov	rax, QWORD PTR -152[rbp]
mov	rbx, QWORD PTR -8[rbp]
leave
.cfi_def_cfa 7, 8
ret
.cfi_endproc
.size f1,.-f1
.section .gcc_except_table.lc3,"a",@progbits
d3:
.byte	0xff
.byte	0xff
.byte	0x1
.uleb128 d5-d4
d4:
.uleb128 .L102-.L94
.uleb128 .L103-.L102
.uleb128 .L148-.L94
.uleb128 0
.uleb128 .L112-.L94
.uleb128 .L124-.L112
.uleb128 .L145-.L94
.uleb128 0
.uleb128 .L153-.L94
.uleb128 .L154-.L153
.uleb128 0
.uleb128 0
d5:
.section .lcdata24,"aw",@progbits
.align 8
d6:
.quad	x22
.section .note.GNU-stack,"",@progbits
