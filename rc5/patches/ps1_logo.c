/* PicoStation RC5.CS02 — optional RGBA logo, preserving RC5 menu functions.
 * SPDX-License-Identifier: Apache-2.0
 */
#include <stdint.h>
typedef struct { uint8_t u,v; uint16_t width,height,page,clut; } TextureInfo;
extern void original_init(uint32_t);
extern void original_config(void);
extern uint32_t config_hex(const void *, const char *, uint32_t *);
extern void send_command(uint32_t, uint32_t);
extern void read_sector(uint32_t, void *, uint32_t, uint32_t, uint32_t, uint32_t);
extern void upload_vram(const void *, uint32_t, uint32_t, uint32_t, uint32_t);
extern void wait_dma(void);
extern uint32_t *allocate_packet(void *, uint32_t);
#define PACKET ((uint8_t *)0x8003772cu)
#define PAYLOAD (PACKET + 20)
#define WALLPAPER (*(volatile uint8_t *)0x80037678u)
#define BACKGROUND ((const uint16_t *)0x8003e384u)
#define LEFT ((const uint8_t *)0x8003e584u)
#define RIGHT ((const uint8_t *)0x8004d584u)
#define STYLE (*(volatile uint32_t *)0x80037694u)
static uint16_t logo_pixels[128 * 20] __attribute__((aligned(4)));
static uint32_t logo_enabled, logo_ready;

static uint32_t expand5(uint32_t v) { return (v << 3) | (v >> 2); }
static uint16_t background_pixel(uint32_t x, uint32_t y) {
    if (WALLPAPER) return BACKGROUND[x < 256 ? LEFT[y*256+x] : RIGHT[y*64+x-256]];
    return ((*(uint8_t *)0x80037672u >> 3)) |
           ((*(uint8_t *)0x80037673u >> 3) << 5) |
           ((*(uint8_t *)0x80037620u >> 3) << 10);
}
static uint16_t composite(const uint8_t *rgba, uint16_t bg) {
    uint32_t a = rgba[3];
    if (!a) return 0;
    uint32_t out = 0x8000; /* opaque black remains visible with opaque sprite opcode */
    for (uint32_t c=0; c<3; ++c) {
        uint32_t back = expand5((bg >> (c*5)) & 31);
        uint32_t value = (rgba[c]*a + back*(255-a) + 127) / 255;
        out |= (value >> 3) << (c*5);
    }
    return (uint16_t)out;
}
void cs_load_config(void) {
    original_config();
    logo_enabled = 1;
    if (*(uint32_t *)(PACKET+12) == 0x31474643u) {
        uint32_t value;
        if (config_hex((void *)0x8003784cu, "logo", &value)) logo_enabled = value == 1;
    }
}
void cs_init(uint32_t pal) {
    logo_ready = 0;
    original_init(pal);
    if (!logo_enabled) return;
    uint32_t origin_x = STYLE == 0x80013ec0u ? 100 : 185;
    uint32_t origin_y = STYLE == 0x80013ec0u ? 10 : 14;
    uint32_t pixel = 0;
    send_command(8, 8);
    for (uint32_t part=34; part<=38; ++part) {
        uint32_t expected = part==38 ? 976 : 2316;
        uint32_t good=0;
        for (uint32_t attempt=0; attempt<20; ++attempt) {
            read_sector(300+part, PACKET, 1, 2340, 1, 1);
            if (*(uint32_t *)(PACKET+12) == 0x44414544u) goto done;
            if (*(uint32_t *)(PACKET+12) == 0x54524150u &&
                *(uint16_t *)(PACKET+16) == part && *(uint16_t *)(PACKET+18) == expected) { good=1; break; }
        }
        if (!good) goto done;
        for (uint32_t offset=0; offset<expected; offset+=4,++pixel)
            logo_pixels[pixel] = composite(PAYLOAD+offset, background_pixel(origin_x+pixel%128, origin_y+pixel/128));
    }
    upload_vram(logo_pixels, 768, 0, 128, 20);
    wait_dma();
    logo_ready = 1;
done:
    send_command(0,0);
}
void cs_draw_logo(void *chain, uint32_t x, uint32_t y) {
    TextureInfo *original = (TextureInfo *)0x80051190u;
    uint32_t *p = allocate_packet(chain, 5);
    p[0] = 0xe1000000u | (logo_ready ? 0x10c : original->page & 0x9ff);
    p[1] = logo_ready ? 0x65000000u : 0x67000000u;
    p[2] = (x & 0xffff) | (y << 16);
    p[3] = logo_ready ? 0 : original->u | (original->v << 8) | (original->clut << 16);
    p[4] = 128 | (20 << 16);
}
