#!/usr/bin/env python3
"""Validate CRCs and the wallpaper file-state diagnostic display."""
from pathlib import Path
import argparse,json,struct,zlib
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3,UC_MIPS_REG_SP,UC_MIPS_REG_RA,UC_MIPS_REG_V0,UC_MIPS_REG_PC,UC_MIPS_REG_GP
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board',choices=['PU18','PU8'],default='PU18')
args=parser.parse_args()
OUT=ROOT/'build-cs'/args.board/'background-diagnostic-CS02'
report=json.loads((OUT/'build-report.json').read_text())
syms={name:int(value,16) for name,value in report['symbols'].items()}
menu=(OUT/f'menu-{report["build_id"]}.bin').read_bytes()
class Probe:
    def __init__(self,raw,length=884,file_size=77312,cursor=77312):
        self.lines=[];self.payload=bytes((i*17)%256 for i in range(length))
        self.uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
        self.uc.mem_map(0,0x200000);self.uc.mem_write(0x10000,menu)
        self.uc.mem_write(0x4d584,raw);self.uc.mem_write(0x37678,bytes([1]))
        self.uc.mem_write(0x37738,b'PART'+struct.pack('<HH',33,length)+self.payload)
        self.uc.mem_write(0x3772c+12+2000,struct.pack('<5I',0x31444742,file_size,0,cursor,0))
        self.uc.reg_write(UC_MIPS_REG_GP,0x8003f5d0)
        self.uc.hook_add(UC_HOOK_CODE,self.code)
    def ret(self,value=0):
        self.uc.reg_write(UC_MIPS_REG_V0,value)
        self.uc.reg_write(UC_MIPS_REG_PC,self.uc.reg_read(UC_MIPS_REG_RA))
    def code(self,uc,address,size,data):
        if address in (syms['cs_logo_init'],syms['cs_logo_draw']):self.ret()
        elif address==0x80010668:self.ret(0x80090000)
        elif address==0x80012390:
            sp=uc.reg_read(UC_MIPS_REG_SP)&0x1fffffff
            ptr=struct.unpack('<I',uc.mem_read(sp+16,4))[0]&0x1fffffff
            self.lines.append(bytes(uc.mem_read(ptr,30)).split(bytes([0]))[0].decode())
            assert uc.reg_read(UC_MIPS_REG_A2)==185
            assert uc.reg_read(UC_MIPS_REG_A3) in (14,27,40)
            self.ret()
    def call(self,name,args=()):
        uc=self.uc;uc.reg_write(UC_MIPS_REG_SP,0x801fff00);uc.reg_write(UC_MIPS_REG_RA,0x801f0000)
        for reg,value in zip((UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3),args):uc.reg_write(reg,value)
        uc.emu_start(syms[name],0x801f0000,timeout=10_000_000,count=30000000)
        assert uc.reg_read(UC_MIPS_REG_PC)==0x801f0000
        return uc.reg_read(UC_MIPS_REG_V0)
checks=[]
for raw in (bytes(64*240),bytes((i*37+i//64)%256 for i in range(64*240))):
    expected=zlib.crc32(raw);p=Probe(raw)
    assert p.call('diagnostic_crc',(0x8004d584,len(raw)//4))==expected
    p.call('cs_init',(0,));p.call('cs_draw_logo',(0,185,14))
    assert p.lines==[f'R{expected:08X} P{zlib.crc32(p.payload):08X}','S00012E00 F00012E00','L0374']
checks.append('compiled MIPS CRC matches independent zlib CRC; last-packet CRC, length, size and file cursor displayed correctly')
p=Probe(bytes(64*240),length=0,file_size=71796,cursor=71796)
p.call('cs_init',(0,));p.call('cs_draw_logo',(0,185,14))
assert p.lines==[f'R{zlib.crc32(bytes(64*240)):08X} P00000000','S00011874 F00011874','L0000']
checks.append('zero-length final read remains distinguishable from a complete read')
print(json.dumps({'board':args.board,'checks':checks,'hardware_validated':False},indent=2))
