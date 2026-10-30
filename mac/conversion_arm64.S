// Enter the native converter after its obsolete base-year cutoff, preserving
// the exact native frame and register state used by its unmodified remainder.
// No game machine code is copied or modified.
.text
.p2align 2
.globl _fm24_continue_award_conversion
.private_extern _fm24_continue_award_conversion
_fm24_continue_award_conversion:
    .cfi_startproc
    sub sp, sp, #0x130
    stp x28, x27, [sp, #0xd0]
    stp x26, x25, [sp, #0xe0]
    stp x24, x23, [sp, #0xf0]
    stp x22, x21, [sp, #0x100]
    stp x20, x19, [sp, #0x110]
    stp x29, x30, [sp, #0x120]
    add x29, sp, #0x120
    .cfi_def_cfa x29, 16
    .cfi_offset x30, -8
    .cfi_offset x29, -16
    .cfi_offset x19, -24
    .cfi_offset x20, -32
    .cfi_offset x21, -40
    .cfi_offset x22, -48
    .cfi_offset x23, -56
    .cfi_offset x24, -64
    .cfi_offset x25, -72
    .cfi_offset x26, -80
    .cfi_offset x27, -88
    .cfi_offset x28, -96
    // The original pre-cutoff path initializes this SI_DATE. The remaining
    // native converter reads it for player age; omitting it creates name-only
    // historical substitutes instead of keeping the real player reference.
    stur w3, [x29, #-0x68]
    mov x19, x2
    mov x21, x1
    adrp x8, _fm24_native_get_manager@GOTPAGE
    ldr x8, [x8, _fm24_native_get_manager@GOTPAGEOFF]
    ldr x8, [x8]
    blr x8
    mov x22, x0
    strb wzr, [x19]
    ldr x23, [x21, #0x18]
    ldr x26, [x23, #0x70]
    ldrh w20, [x21, #0x8c]
    adrp x8, _fm24_native_cache_address@GOTPAGE
    ldr x8, [x8, _fm24_native_cache_address@GOTPAGEOFF]
    ldr x8, [x8]
    ldr x25, [x8]
    adrp x8, _fm24_native_continuation@GOTPAGE
    ldr x8, [x8, _fm24_native_continuation@GOTPAGEOFF]
    ldr x8, [x8]
    br x8
    .cfi_endproc
