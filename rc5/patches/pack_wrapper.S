/* RC5-compatible entry wrapper for a relocated packed menu. */
.set noreorder
.text
.global _start
_start:
    addu $t8,$ra,$zero
    lui $v1,0x1f80
    sw $zero,0x1074($v1)
    lui $a0,%hi(packed_start)
    addiu $a0,$a0,%lo(packed_start)
    lui $a1,0x8001
    bal nrv_decompressor
    addiu $a1,$a1,0
    addiu $t0,$zero,0xa0
    jalr $t0
    addiu $t1,$zero,0x44
    lui $t0,0x8002
    addiu $t0,$t0,0x294
    jr $t0
    addu $ra,$t8,$zero
