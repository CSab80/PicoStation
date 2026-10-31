ENTRY(cs_init)
original_init = 0x80018c7c;
original_config = 0x80014fc4;
config_hex = 0x8001b000;
send_command = 0x80011b88;
read_sector = 0x8001d34c;
upload_vram = 0x80010474;
wait_dma = 0x80010398;
allocate_packet = 0x80010668;
draw_text = 0x80012390;
SECTIONS {
  . = 0x8005c000;
  .text : { *(.text*) *(.rodata*) }
  .data : { *(.data*) *(.sdata*) *(.got*) }
  .bss : { *(.bss*) *(.sbss*) *(COMMON) }
  image_end = .;
  /DISCARD/ : { *(.MIPS.abiflags) *(.reginfo) *(.pdr) *(.comment*) *(.note*) *(.llvm_addrsig) }
}
