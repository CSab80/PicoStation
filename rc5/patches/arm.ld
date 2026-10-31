ENTRY(cs_read_background_part)
SECTIONS {
  . = 0x1003d200;
  .text : { *(.text.entry) *(.text*) *(.rodata*) }
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
