.text
.global _start
.type _start, %function
_start:
    bl w2jb_aarch64_abi_smoke
    mov x8, #93
    svc #0
.size _start, .-_start
