/* PicoStation RC5.CS01 — extension of the RC5 background file transport.
 * SPDX-License-Identifier: Apache-2.0
 * Address contract applies ONLY to the verified PU18 non-overclocked RC5.
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
    uint32_t offset = part * 2316u;
    for (uint32_t i = 0; i < 2324; ++i) PACKET[i] = 0;
    if (part >= 34) {
        if (part > 38) goto missing;
        if (part == 34) {
            if (FILE_VALID) CLOSE(FILE_OBJECT);
            if (!SD_PRESENT || OPEN(FILE_OBJECT, "logo.raw", 1)) goto missing;
            if (FILE_SIZE != 10240u) { CLOSE(FILE_OBJECT); goto missing; }
        }
        offset = (part - 34) * 2316u;
    }
    if (!FILE_VALID) goto missing;
    if (SEEK(FILE_OBJECT, offset) || READ(FILE_OBJECT, PACKET + 8, 2316, &bytes)) goto missing;
    *(uint32_t *)PACKET = 0x54524150u; /* PART */
    *(uint16_t *)(PACKET + 4) = (uint16_t)part;
    *(uint16_t *)(PACKET + 6) = (uint16_t)bytes;
    return PACKET;
missing:
    *(uint32_t *)PACKET = 0x44414544u; /* DEAD */
    return PACKET;
}
