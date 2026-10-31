/* Optional hardware probe: observe the last wallpaper packet and FatFs state.
 * SPDX-License-Identifier: Apache-2.0
 */
#define cs_init cs_logo_init
#define cs_draw_logo cs_logo_draw
#include "ps1_logo.c"
#undef cs_init
#undef cs_draw_logo

extern void draw_text(void *, const TextureInfo *, uint32_t, uint32_t, const char *);
static char packet_label[] = "R00000000 P00000000";
static char file_label[] = "S00000000 F00000000";
static char length_label[] = "L0000";

uint32_t diagnostic_crc(const uint32_t *words, uint32_t count) {
    uint32_t crc = 0xffffffffu;
    for (uint32_t i=0; i<count; ++i) {
        crc ^= words[i];
        for (uint32_t bit=0; bit<32; ++bit)
            crc = (crc >> 1) ^ (0xedb88320u & (0u-(crc & 1)));
    }
    return ~crc;
}
static void hex_label(char *out, uint32_t value, uint32_t digits) {
    for (uint32_t i=0; i<digits; ++i) {
        uint32_t digit = (value >> ((digits-1-i)*4)) & 15;
        out[i] = digit < 10 ? '0'+digit : 'A'+digit-10;
    }
}
void cs_init(uint32_t pal) {
    cs_logo_init(pal);
    hex_label(packet_label+1, diagnostic_crc((const uint32_t *)RIGHT,64*240/4),8);
    uint32_t length = *(uint16_t *)(PACKET+18);
    if (length > 2316) length = 0;
    hex_label(packet_label+11, diagnostic_crc((const uint32_t *)PAYLOAD,length/4),8);
    hex_label(length_label+1,length,4);
    /* The CD sector adds a 12-byte header before the Pico packet. */
    if (*(uint32_t *)(PACKET+2012)==0x31444742u) {
        hex_label(file_label+1,*(uint32_t *)(PACKET+2016),8);
        hex_label(file_label+11,*(uint32_t *)(PACKET+2024),8);
    }
}
void cs_draw_logo(void *chain, uint32_t x, uint32_t y) {
    cs_logo_draw(chain,x,y);
    uint32_t *p = allocate_packet(chain,3);
    p[0] = 0x60000000u;
    p[1] = 184 | (12u<<16);
    p[2] = 136 | (42u<<16);
    draw_text(chain,(const TextureInfo *)0x80051184u,185,14,packet_label);
    draw_text(chain,(const TextureInfo *)0x80051184u,185,27,file_label);
    draw_text(chain,(const TextureInfo *)0x80051184u,185,40,length_label);
}
