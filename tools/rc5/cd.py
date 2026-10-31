"""CD Mode 2 Form 1 checksum generation, verified against the original RC5 disc."""
import struct
EDC = []
FORWARD = []
BACKWARD = [0] * 256
for value in range(256):
    remainder = value
    for _ in range(8): remainder = (remainder >> 1) ^ (0xD8018001 if remainder & 1 else 0)
    EDC.append(remainder)
    forward = (value << 1) ^ (0x11D if value & 0x80 else 0)
    FORWARD.append(forward)
    BACKWARD[value ^ forward] = value

def edc(data):
    value = 0
    for byte in data: value = (value >> 8) ^ EDC[(value ^ byte) & 255]
    return value

def ecc(data, major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    output = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            value = data[index]
            index = (index + minor_inc) % size
            a ^= value
            b ^= value
            a = FORWARD[a]
        a = BACKWARD[FORWARD[a] ^ b]
        output[major] = a
        output[major + major_count] = a ^ b
    return output

def rebuild_sector(original, payload):
    assert len(original) == 2352 and len(payload) == 2048
    sector = bytearray(original)
    assert sector[15] == 2 and not sector[18] & 32
    sector[24:2072] = payload
    struct.pack_into('<I', sector, 2072, edc(sector[16:2072]))
    address = sector[12:16]
    sector[12:16] = bytes(4)
    sector[2076:2248] = ecc(sector[12:2076], 86, 24, 2, 86)
    sector[2248:2352] = ecc(sector[12:2248], 52, 43, 86, 88)
    sector[12:16] = address
    return bytes(sector)
