.intel_syntax noprefix
.section .text.f1,"ax",@progbits
.globl f1
.type f1,@function
f1:
.L130:
.cfi_startproc
.cfi_personality 0x9b,d11
.cfi_lsda 0x1b,d7
endbr64
push	rbp
.cfi_def_cfa_offset 16
.cfi_offset 6, -16
mov	rbp, rsp
.cfi_def_cfa_register 6
push	r14
push	r13
push	r12
push	rbx
sub	rsp, 368
.cfi_offset 14, -24
.cfi_offset 13, -32
.cfi_offset 12, -40
.cfi_offset 3, -48
mov	QWORD PTR -376[rbp], rdi
mov	QWORD PTR -384[rbp], rsi
mov	DWORD PTR -388[rbp], edx
mov	rax, QWORD PTR fs:40
mov	QWORD PTR -40[rbp], rax
xor	eax, eax
movzx	eax, BYTE PTR d6[rip]
test	al, al
sete	al
test	al, al
je	.L145
lea	rax, d6[rip]
mov	rdi, rax
call	x40@PLT
test	eax, eax
setne	al
test	al, al
je	.L145
mov	r14d, 0
lea	r12, d10[rip]
mov	r13d, 4
lea	rax, -80[rbp]
mov	QWORD PTR -264[rbp], rax
nop
nop
lea	rax, -80[rbp]
mov	rsi, r12
mov	rdx, r13
lea	rdi, d5[rip]
mov	rcx, rax
.L141:
call	x24
.L142:
lea	rdx, x42[rip]
lea	rcx, d5[rip]
lea	rax, x25[rip]
mov	rsi, rcx
mov	rdi, rax
call	x38@PLT
lea	rax, d6[rip]
mov	rdi, rax
call	x41@PLT
nop
.L145:
lea	rax, -356[rbp]
mov	QWORD PTR -232[rbp], rax
nop
nop
lea	rax, -360[rbp]
mov	QWORD PTR -240[rbp], rax
nop
nop
lea	rax, -364[rbp]
mov	QWORD PTR -248[rbp], rax
nop
nop
lea	rax, -365[rbp]
mov	QWORD PTR -256[rbp], rax
nop
nop
lea	rsi, d4[rip]
lea	rdx, -365[rbp]
lea	rax, -144[rbp]
mov	rcx, rdx
mov	rdx, rsi
mov	esi, 4
mov	rdi, rax
.L188:
call	x27
.L189:
mov	eax, DWORD PTR -388[rbp]
add	eax, 1
movsxd	rsi, eax
lea	rcx, -364[rbp]
lea	rdx, -144[rbp]
lea	rax, -112[rbp]
mov	rdi, rax
.L190:
call	x20
.L191:
mov	rax, QWORD PTR -384[rbp]
mov	esi, 0
mov	rdi, rax
call	x23
mov	QWORD PTR -224[rbp], rax
mov	rax, QWORD PTR -224[rbp]
mov	rdi, rax
call	x6
mov	rsi, rax
nop
lea	rcx, -360[rbp]
lea	rdx, -112[rbp]
lea	rax, -80[rbp]
mov	rdi, rax
.L196:
call	x15
.L197:
mov	rax, QWORD PTR -384[rbp]
mov	QWORD PTR -216[rbp], rax
mov	rax, QWORD PTR -216[rbp]
mov	rdi, rax
call	x3
mov	rsi, rax
nop
lea	rcx, -356[rbp]
lea	rdx, -80[rbp]
lea	rax, -176[rbp]
mov	rdi, rax
.L202:
call	x12
.L203:
lea	rax, -80[rbp]
mov	rdi, rax
call	x16
lea	rax, -112[rbp]
mov	rdi, rax
call	x21
lea	rax, -144[rbp]
mov	rdi, rax
call	x28
nop
nop
nop
nop
lea	rax, -80[rbp]
mov	rdi, rax
call	x10
mov	DWORD PTR -112[rbp], -1
mov	DWORD PTR -144[rbp], -1
mov	DWORD PTR -356[rbp], 0
mov	DWORD PTR -360[rbp], 0
mov	rax, QWORD PTR -384[rbp]
mov	esi, 0
mov	rdi, rax
call	x23
mov	esi, 0
mov	rdi, rax
call	x29
mov	rsi, rax
lea	r8, -112[rbp]
lea	rdi, -144[rbp]
lea	rcx, -356[rbp]
lea	rdx, -360[rbp]
lea	rax, -80[rbp]
mov	r9, r8
mov	r8, rdi
mov	rdi, rax
.L220:
call	x9
jmp	.L263
.L221:
lea	rax, -80[rbp]
mov	rdi, rax
call	x1
mov	rcx, rax
mov	rax, QWORD PTR [rcx]
mov	rdx, QWORD PTR 8[rcx]
mov	QWORD PTR -112[rbp], rax
mov	QWORD PTR -104[rbp], rdx
mov	eax, DWORD PTR 16[rcx]
mov	DWORD PTR -96[rbp], eax
lea	rax, -112[rbp]
mov	rdi, rax
call	x30
mov	QWORD PTR -352[rbp], rax
lea	rax, -112[rbp]
mov	rdi, rax
call	x32
mov	QWORD PTR -344[rbp], rax
lea	rax, -112[rbp]
mov	rdi, rax
call	x34
mov	QWORD PTR -336[rbp], rax
lea	rax, -112[rbp]
mov	rdi, rax
call	x35
mov	QWORD PTR -328[rbp], rax
lea	rax, -112[rbp]
mov	rdi, rax
call	x36
mov	QWORD PTR -320[rbp], rax
lea	rax, -80[rbp]
mov	rdi, rax
call	x7
mov	rax, QWORD PTR -328[rbp]
mov	eax, DWORD PTR [rax]
cmp	eax, -1
je	.L223
mov	rax, QWORD PTR -352[rbp]
mov	ebx, DWORD PTR [rax]
mov	rax, QWORD PTR -344[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rdx, eax
lea	rax, -176[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x14
mov	rdx, rax
mov	rax, QWORD PTR -336[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x17
mov	rdx, rax
mov	rax, QWORD PTR -320[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x23
mov	rdx, rax
mov	rax, QWORD PTR -328[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x29
mov	eax, DWORD PTR [rax]
cmp	ebx, eax
je	.L223
mov	eax, 1
jmp	.L224
.L223:
mov	eax, 0
.L224:
test	al, al
jne	.L261
mov	rax, QWORD PTR -344[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rbx, eax
mov	rax, QWORD PTR -384[rbp]
mov	QWORD PTR -208[rbp], rax
mov	rax, QWORD PTR -208[rbp]
mov	rdi, rax
call	x3
nop
sub	rax, 1
cmp	rbx, rax
jne	.L233
mov	rax, QWORD PTR -336[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rbx, eax
mov	rax, QWORD PTR -384[rbp]
mov	esi, 0
mov	rdi, rax
call	x23
mov	QWORD PTR -200[rbp], rax
mov	rax, QWORD PTR -200[rbp]
mov	rdi, rax
call	x6
nop
sub	rax, 1
cmp	rbx, rax
jne	.L233
mov	eax, 1
jmp	.L234
.L233:
mov	eax, 0
.L234:
test	al, al
je	.L235
mov	rax, QWORD PTR -352[rbp]
mov	ebx, DWORD PTR [rax]
jmp	.L265
.L235:
mov	DWORD PTR -364[rbp], 0
jmp	.L256
.L237:
mov	eax, DWORD PTR -364[rbp]
cdqe
lea	rdx, d5[rip]
mov	rsi, rax
mov	rdi, rdx
call	x5
mov	QWORD PTR -312[rbp], rax
mov	rax, QWORD PTR -312[rbp]
mov	rdi, rax
call	x31
mov	QWORD PTR -304[rbp], rax
mov	rax, QWORD PTR -312[rbp]
mov	rdi, rax
call	x33
mov	QWORD PTR -296[rbp], rax
mov	rax, QWORD PTR -344[rbp]
mov	edx, DWORD PTR [rax]
mov	rax, QWORD PTR -304[rbp]
mov	eax, DWORD PTR [rax]
add	eax, edx
mov	DWORD PTR -360[rbp], eax
lea	rax, -360[rbp]
mov	QWORD PTR -288[rbp], rax
mov	rax, QWORD PTR -336[rbp]
mov	edx, DWORD PTR [rax]
mov	rax, QWORD PTR -296[rbp]
mov	eax, DWORD PTR [rax]
add	eax, edx
mov	DWORD PTR -356[rbp], eax
lea	rax, -356[rbp]
mov	QWORD PTR -280[rbp], rax
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
test	eax, eax
js	.L247
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rbx, eax
mov	rax, QWORD PTR -384[rbp]
mov	QWORD PTR -192[rbp], rax
mov	rax, QWORD PTR -192[rbp]
mov	rdi, rax
call	x3
nop
cmp	rbx, rax
jnb	.L247
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
test	eax, eax
js	.L247
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rbx, eax
mov	rax, QWORD PTR -384[rbp]
mov	esi, 0
mov	rdi, rax
call	x23
mov	QWORD PTR -184[rbp], rax
mov	rax, QWORD PTR -184[rbp]
mov	rdi, rax
call	x6
nop
cmp	rbx, rax
jb	.L248
.L247:
mov	eax, 1
jmp	.L249
.L248:
mov	eax, 0
.L249:
test	al, al
jne	.L251
mov	rax, QWORD PTR -320[rbp]
mov	edx, DWORD PTR [rax]
mov	rax, QWORD PTR -328[rbp]
mov	ecx, DWORD PTR [rax]
mov	eax, DWORD PTR -364[rbp]
cmp	ecx, eax
setne	al
movzx	eax, al
add	eax, edx
mov	DWORD PTR -144[rbp], eax
lea	rax, -144[rbp]
mov	QWORD PTR -272[rbp], rax
mov	rax, QWORD PTR -272[rbp]
mov	eax, DWORD PTR [rax]
cmp	DWORD PTR -388[rbp], eax
jl	.L252
mov	rax, QWORD PTR -352[rbp]
mov	ebx, DWORD PTR [rax]
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rdx, eax
mov	rax, QWORD PTR -384[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x23
mov	rdx, rax
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x29
mov	eax, DWORD PTR [rax]
add	ebx, eax
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rdx, eax
lea	rax, -176[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x14
mov	rdx, rax
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x17
mov	rdx, rax
mov	rax, QWORD PTR -272[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x23
mov	rdx, rax
mov	eax, DWORD PTR -364[rbp]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x29
mov	eax, DWORD PTR [rax]
cmp	ebx, eax
setge	al
test	al, al
jne	.L253
mov	rax, QWORD PTR -352[rbp]
mov	ebx, DWORD PTR [rax]
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rdx, eax
mov	rax, QWORD PTR -384[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x23
mov	rdx, rax
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x29
mov	eax, DWORD PTR [rax]
add	ebx, eax
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rdx, eax
lea	rax, -176[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x14
mov	rdx, rax
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x17
mov	rdx, rax
mov	rax, QWORD PTR -272[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x23
mov	rdx, rax
mov	eax, DWORD PTR -364[rbp]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x29
mov	DWORD PTR [rax], ebx
mov	rax, QWORD PTR -288[rbp]
mov	eax, DWORD PTR [rax]
movsxd	rdx, eax
lea	rax, -176[rbp]
mov	rsi, rdx
mov	rdi, rax
call	x14
mov	rdx, rax
mov	rax, QWORD PTR -280[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x17
mov	rdx, rax
mov	rax, QWORD PTR -272[rbp]
mov	eax, DWORD PTR [rax]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x23
mov	rdx, rax
mov	eax, DWORD PTR -364[rbp]
cdqe
mov	rsi, rax
mov	rdi, rdx
call	x29
mov	rsi, rax
mov	r8, QWORD PTR -272[rbp]
lea	rdi, -364[rbp]
mov	rcx, QWORD PTR -280[rbp]
mov	rdx, QWORD PTR -288[rbp]
lea	rax, -80[rbp]
mov	r9, r8
mov	r8, rdi
mov	rdi, rax
call	x8
.L250:
jmp	.L254
.L251:
nop
jmp	.L254
.L252:
nop
jmp	.L254
.L253:
nop
.L254:
mov	eax, DWORD PTR -364[rbp]
add	eax, 1
mov	DWORD PTR -364[rbp], eax
.L256:
mov	eax, DWORD PTR -364[rbp]
movsxd	rbx, eax
lea	rax, d5[rip]
mov	rdi, rax
call	x4
nop
cmp	rbx, rax
setb	al
test	al, al
jne	.L237
jmp	.L263
.L261:
nop
.L263:
lea	rax, -80[rbp]
mov	rdi, rax
call	x2
xor	eax, 1
test	al, al
jne	.L221
mov	ebx, -1
.L265:
lea	rax, -80[rbp]
mov	rdi, rax
call	x11
lea	rax, -176[rbp]
mov	rdi, rax
call	x13
mov	eax, ebx
mov	rdx, QWORD PTR -40[rbp]
sub	rdx, QWORD PTR fs:40
je	.L298
jmp	.L297
.L266:
endbr64
mov	rbx, rax
test	r14b, r14b
jne	.L267
lea	rax, d6[rip]
mov	rdi, rax
call	x39@PLT
.L267:
mov	rax, rbx
mov	rdx, QWORD PTR -40[rbp]
sub	rdx, QWORD PTR fs:40
je	.L268
call	x44@PLT
.L268:
mov	rdi, rax
.L269:
call	x0@PLT
.L270:
endbr64
mov	rbx, rax
lea	rax, -80[rbp]
mov	rdi, rax
call	x16
jmp	.L272
.L271:
endbr64
mov	rbx, rax
.L272:
lea	rax, -112[rbp]
mov	rdi, rax
call	x21
jmp	.L274
.L273:
endbr64
mov	rbx, rax
.L274:
lea	rax, -144[rbp]
mov	rdi, rax
call	x28
mov	rax, rbx
jmp	.L278
.L277:
endbr64
.L278:
nop
nop
nop
nop
mov	rdx, QWORD PTR -40[rbp]
sub	rdx, QWORD PTR fs:40
je	.L291
call	x44@PLT
.L291:
mov	rdi, rax
call	x0@PLT
.L292:
endbr64
mov	rbx, rax
lea	rax, -80[rbp]
mov	rdi, rax
call	x11
lea	rax, -176[rbp]
mov	rdi, rax
call	x13
mov	rax, rbx
mov	rdx, QWORD PTR -40[rbp]
sub	rdx, QWORD PTR fs:40
je	.L295
call	x44@PLT
.L295:
mov	rdi, rax
call	x0@PLT
.L296:
.L297:
call	x44@PLT
.L298:
add	rsp, 368
pop	rbx
pop	r12
pop	r13
pop	r14
pop	rbp
.cfi_def_cfa 7, 8
ret
.cfi_endproc
.size f1,.-f1
.section .lcdata7,"a",@progbits
.align 4
d4:
.long	2147483647
.section .lcdata8,"aw",@nobits
.align 16
d5:
.zero	24
.section .lcdata12,"aw",@nobits
.align 8
d6:
.zero	8
.section .gcc_except_table.lc13,"a",@progbits
d7:
.byte	0xff
.byte	0xff
.byte	0x1
.uleb128 d9-d8
d8:
.uleb128 .L141-.L130
.uleb128 .L142-.L141
.uleb128 .L266-.L130
.uleb128 0
.uleb128 .L188-.L130
.uleb128 .L189-.L188
.uleb128 .L277-.L130
.uleb128 0
.uleb128 .L190-.L130
.uleb128 .L191-.L190
.uleb128 .L273-.L130
.uleb128 0
.uleb128 .L196-.L130
.uleb128 .L197-.L196
.uleb128 .L271-.L130
.uleb128 0
.uleb128 .L202-.L130
.uleb128 .L203-.L202
.uleb128 .L270-.L130
.uleb128 0
.uleb128 .L220-.L130
.uleb128 .L250-.L220
.uleb128 .L292-.L130
.uleb128 0
.uleb128 .L269-.L130
.uleb128 .L296-.L269
.uleb128 0
.uleb128 0
d9:
.section .lcdata69,"a",@progbits
.align 32
d10:
.long	1
.long	0
.long	0
.long	1
.long	-1
.long	0
.long	0
.long	-1
.section .lcdata70,"aw",@progbits
.align 8
d11:
.quad	x43
.section .note.GNU-stack,"",@progbits
