/* PicoStation RC5.CS02 — independent wallpaper/logo chunk reads.
 * SPDX-License-Identifier: Apache-2.0
 * Address contract verified for the non-overclocked RC5 PU18 and PU8.
 */
#include <stdint.h>
typedef uint32_t (*open_fn)(void *, const char *, uint8_t);
typedef uint32_t (*close_fn)(void *);
typedef uint32_t (*seek_fn)(void *, uint64_t);
typedef uint32_t (*read_fn)(void *, void *, uint32_t, uint32_t *);
#define FILE_OBJECT ((void *)0x2000a410u)
#define PACKET ((uint8_t *)0x2000cbd0u)
#define OPEN ((open_fn)0x20006ff9u)
#define CLOSE ((close_fn)0x20007631u)
#define SEEK ((seek_fn)0x20007665u)
#define READ ((read_fn)0x200070d5u)
#define SD_PRESENT (*(volatile uint8_t *)0x20033401u)
#define FILE_VALID (*(volatile uint32_t *)FILE_OBJECT)
#define FILE_SIZE (*(volatile uint64_t *)((uint8_t *)FILE_OBJECT + 16))

__attribute__((section(".text.entry")))
uint8_t *cs_read_background_part(uint32_t part) {
    uint32_t bytes = 0;
    for (uint32_t i = 0; i < 2324; ++i) PACKET[i] = 0;
    if (part > 38) goto missing;
    uint32_t is_logo = part >= 34;
    uint32_t size = is_logo ? 10240u : 77312u;
    uint32_t offset = (is_logo ? part-34 : part) * 2316u;
    uint32_t expected = size-offset;
    if (expected > 2316u) expected = 2316u;
    /* The CD drive reads ahead and can cross from wallpaper to logo before
     * earlier wallpaper requests have finished. Never rely on shared FIL state
     * or sequential request order, including when the logo is disabled. */
    if (FILE_VALID) CLOSE(FILE_OBJECT);
    if (!SD_PRESENT || OPEN(FILE_OBJECT, is_logo ? "logo.raw" : "background.raw", 1)) goto missing;
    if (FILE_SIZE != size) { CLOSE(FILE_OBJECT); goto missing; }
    if (SEEK(FILE_OBJECT, offset) || READ(FILE_OBJECT, PACKET + 8, 2316, &bytes) || bytes != expected) goto missing;
#ifdef CS_BACKGROUND_DIAGNOSTIC
    if (part == 33 && bytes <= 1992) {
        /* The final wallpaper payload is at most 884 bytes. Its padding
         * reports FatFs state without changing any wallpaper bytes. */
        uint64_t length = FILE_SIZE;
        uint64_t cursor = *(volatile uint64_t *)((uint8_t *)FILE_OBJECT + 56);
        *(uint32_t *)(PACKET + 2000) = 0x31444742u; /* BGD1 */
        *(uint32_t *)(PACKET + 2004) = (uint32_t)length;
        *(uint32_t *)(PACKET + 2008) = (uint32_t)(length >> 32);
        *(uint32_t *)(PACKET + 2012) = (uint32_t)cursor;
        *(uint32_t *)(PACKET + 2016) = (uint32_t)(cursor >> 32);
    }
#endif
    *(uint32_t *)PACKET = 0x54524150u; /* PART */
    *(uint16_t *)(PACKET + 4) = (uint16_t)part;
    *(uint16_t *)(PACKET + 6) = (uint16_t)bytes;
    return PACKET;
missing:
    *(uint32_t *)PACKET = 0x44414544u; /* DEAD */
    return PACKET;
}
