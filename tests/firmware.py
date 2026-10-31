#!/usr/bin/env python3
"""Execute the compiled ARM/MIPS extension with mocked SD and GPU boundaries.

The original drive engine and PS1 hardware are NOT emulated by these tests.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
from zipfile import ZipFile
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/rc5'))
from cd import rebuild_sector
from unicorn import *
from unicorn.arm_const import *
from unicorn.mips_const import *

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'rc5/original/manifest.json').read_text())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board',choices=tuple(manifest['boards']),default='PU18')
parser.add_argument('--diagnostic-background',action='store_true')
args=parser.parse_args()
OUT=ROOT/'build-cs'/args.board
if args.diagnostic_background: OUT=OUT/'background-diagnostic-CS02'
report=json.loads((OUT/'build-report.json').read_text())
assert report['board']==args.board and report['overclocked'] is False
build_id=report.get('build_id','CS01')
firmware_sha=report.get('firmware_uf2_sha256',report.get('cs01_uf2_sha256'))
flash=(OUT/f'firmware-{build_id}.bin').read_bytes()
menu=(OUT/f'menu-{build_id}.bin').read_bytes()
syms={key:int(value,16) for key,value in report['symbols'].items()}
checks=[]

baseline=(OUT/f'picostation_{args.board}_RC5-reconstruit.uf2').read_bytes()
assert hashlib.sha256(baseline).hexdigest()==manifest['boards'][args.board]['original_uf2_sha256']
original=(OUT/'reference-flash.bin').read_bytes()
assert hashlib.sha256(original).hexdigest()==manifest['boards'][args.board]['flash_sha256']
allowed=set(range(0x12d18,0x12d18+117600))|set(range(0x3553e,0x35540))|set(range(0x36fac,0x36fb4))
assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(original,flash)))
for image in (original,flash):
    disc=image[0x12d18:0x12d18+117600]
    for i in range(50):
        sector=disc[i*2352:(i+1)*2352]
        if not sector[18]&32:assert rebuild_sector(sector,sector[24:2072])==sector
checks.append('baseline identical; modifications confined to declared ranges; CD EDC/ECC valid')
original_menu=(OUT/'menu_rc5.bin').read_bytes()
ps1_allowed=set(range(0x1900,0x1908))|set(range(0x27668,0x2766c))|set(range(0x14ae4,0x14af4))
for hook in report['hooks']:
    for address in hook['calls']:
        offset=int(address,16)-0x80010000;ps1_allowed.update(range(offset,offset+4))
assert all(a==b or i in ps1_allowed for i,(a,b) in enumerate(zip(original_menu,menu)))

# Execute the actual relocated entry wrapper and original unpacker.
exe=(OUT/f'menu-{build_id}.ps-exe').read_bytes()
entry,_,load,length=struct.unpack_from('<4I',exe,16)
emu=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
emu.mem_map(0,0x200000);emu.mem_map(0x1f801000,0x1000)
emu.mem_write(load&0x1fffffff,exe[2048:2048+length])
emu.reg_write(UC_MIPS_REG_SP,0x801fff00)
def bios(uc,address,size,data):
    if address==0xa0:uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
emu.hook_add(UC_HOOK_CODE,bios)
emu.emu_start(entry,0x80020294,timeout=15_000_000,count=30_000_000)
assert emu.reg_read(UC_MIPS_REG_PC)==0x80020294
assert bytes(emu.mem_read(0x10000,len(menu)))==menu
checks.append('actual packed entry reaches original RC5 entry and unpacks exact modified menu')

# Run the original allocator against its relocated heap, not an allocation mock.
emu.reg_write(UC_MIPS_REG_GP,0x8003f5d0)
extension_before=bytes(emu.mem_read(0x5c000,len(menu)-0x4c000))
heap=int(report['heap_start'],16)
assert heap>=syms['image_end'] and heap%8==0
for length in (256,32768,8192,64):
    emu.reg_write(UC_MIPS_REG_A0,length);emu.reg_write(UC_MIPS_REG_RA,0x801f0000)
    emu.emu_start(0x80020500,0x801f0000,timeout=2_000_000,count=500000)
    pointer=emu.reg_read(UC_MIPS_REG_V0)
    assert heap<=pointer<0x80200000-length
    emu.mem_write(pointer&0x1fffffff,bytes([0xa5])*length)
assert bytes(emu.mem_read(0x5c000,len(menu)-0x4c000))==extension_before
checks.append('original allocator preserves extension code/storage across directory-sized allocations')

# Unicorn models MIPS32 rather than the PS1 load delay. Check this separately.
disassembler=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
disassembler.skipdata=True
code_end=min([value for name,value in syms.items() if 'str' in name and value>=0x8005c000] or [syms['image_end']])
instructions=list(disassembler.disasm(menu[0x4c000:code_end-0x80010000],0x8005c000))
writes_first={'lw','lbu','lhu','lb','lh','lui','addiu','addu','subu','and','andi','or','ori','xor','xori','slt','sltu','slti','sltiu','sll','srl','sra','move','mfhi','mflo','sllv','srlv','srav','nor'}
for first,second in zip(instructions,instructions[1:]):
    if first.mnemonic not in {'lw','lh','lhu','lb','lbu'}:continue
    target=first.op_str.split(',')[0].strip();operands=second.op_str
    if second.mnemonic in writes_first:operands=operands.split(',',1)[1] if ',' in operands else ''
    assert target not in operands.replace('(',' ').replace(')',' ').replace(',',' ').split(),f'MIPS I load hazard at {hex(first.address)}'
checks.append('compiled MIPS I extension has no immediate load-use hazards')

class SD:
    def __init__(self,files):
        self.files=files;self.current=None;self.cursor=0;self.failure=None
        self.uc=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.uc.mem_map(0x10000000,0x200000);self.uc.mem_map(0x20000000,0x42000)
        self.uc.mem_write(0x10000000,flash)
        self.uc.mem_write(0x200000c0,flash[0x330b0:0x3d1a0])
        self.uc.mem_write(0x20033401,b'\1')
        self.uc.hook_add(UC_HOOK_CODE,self.hook)
    def r(self,reg):return self.uc.reg_read(reg)
    def write32(self,address,value):self.uc.mem_write(address,struct.pack('<I',value))
    def reset(self):
        self.current='background.raw' if 'background.raw' in self.files else None;self.cursor=0
        self.write32(0x2000a410,1 if self.current else 0)
        self.uc.mem_write(0x2000a420,struct.pack('<Q',len(self.files[self.current]) if self.current else 0))
        self.uc.mem_write(0x2000a448,struct.pack('<Q',0))
    def hook(self,uc,address,size,data):
        result=0
        if address==0x20007630:
            self.current=None;self.write32(0x2000a410,0)
        elif address==0x20006ff8:
            name=bytes(uc.mem_read(self.r(UC_ARM_REG_R1),40)).split(b'\0')[0].decode()
            self.current=name if name in self.files else None;self.cursor=0
            self.write32(0x2000a410,1 if self.current else 0)
            uc.mem_write(0x2000a420,struct.pack('<Q',len(self.files[self.current]) if self.current else 0))
            result=0 if self.current else 4
        elif address==0x20007664:
            requested=self.r(UC_ARM_REG_R2)|(self.r(UC_ARM_REG_R3)<<32)
            self.cursor=min(requested,len(self.files.get(self.current,b'')))
            uc.mem_write(0x2000a448,struct.pack('<Q',self.cursor))
            result=int(self.failure=='seek')
        elif address==0x200070d4:
            content=self.files.get(self.current,b'')[self.cursor:self.cursor+self.r(UC_ARM_REG_R2)]
            if self.failure=='short':content=content[:-1]
            if content:uc.mem_write(self.r(UC_ARM_REG_R1),content)
            self.write32(self.r(UC_ARM_REG_R3),len(content));self.cursor+=len(content)
            uc.mem_write(0x2000a448,struct.pack('<Q',self.cursor))
            result=int(self.failure=='read')
        else:return
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,self.r(UC_ARM_REG_LR))
    def read(self,part):
        self.uc.reg_write(UC_ARM_REG_SP,0x20040000);self.uc.reg_write(UC_ARM_REG_LR,0x100f0001)
        self.uc.reg_write(UC_ARM_REG_R0,part)
        self.uc.emu_start(0x20003fbd,0x100f0000,timeout=2_000_000,count=200000)
        assert self.r(UC_ARM_REG_PC)==0x100f0000
        assert self.r(UC_ARM_REG_R0)==0x2000cbd0
        return bytes(self.uc.mem_read(0x2000cbd0,2324))

rgba=bytes([255,0,0,128,0,0,0,255,255,255,255,0,0,255,0,255])*640
bg=bytes((i*13)%256 for i in range(77312))
sd=SD({'background.raw':bg,'logo.raw':rgba});sd.reset()
assembled=bytearray()
for part in range(34):
    packet=sd.read(part);assert packet[:4]==b'PART';index,n=struct.unpack_from('<2H',packet,4);assert index==part;assembled+=packet[8:8+n]
assert assembled==bg
if args.diagnostic_background:
    assert struct.unpack_from('<5I',packet,2000)==(0x31444742,77312,0,77312,0)
assembled=bytearray()
for part in range(34,39):
    packet=sd.read(part);index,n=struct.unpack_from('<2H',packet,4);assert packet[:4]==b'PART' and index==part;assembled+=packet[8:8+n]
assert assembled==rgba
for part in (30,34,31,35,32,36,33,37,0,38,34,1,35):
    packet=sd.read(part)
    source=rgba if part>=34 else bg
    offset=(part-34 if part>=34 else part)*2316
    expected=source[offset:offset+2316]
    assert packet[:4]==b'PART' and struct.unpack_from('<HH',packet,4)==(part,len(expected))
    assert packet[8:8+len(expected)]==expected
checks.append('CD read-ahead regression: interleaved wallpaper/logo chunks reopen the correct asset, including wallpaper parts 31..33 after logo prefetch')
assert sd.read(34)==sd.read(34) # restart is idempotent
assert sd.read(39)[:4]==b'DEAD'
for files in ({},{'logo.raw':b'x'*10239},{'logo.raw':b'x'*10241}):
    invalid=SD(files);invalid.reset();assert invalid.read(34)[:4]==b'DEAD'
for size in (0,71796,77311,77313):
    invalid=SD({'background.raw':bytes(size),'logo.raw':rgba});invalid.reset()
    assert invalid.read(31)[:4]==b'DEAD'
    assert invalid.read(34)[8:8+2316]==rgba[:2316]
invalid=SD({'background.raw':bg});invalid.reset();invalid.uc.mem_write(0x20033401,b'\0')
assert invalid.read(0)[:4]==b'DEAD'
for failure in ('seek','read','short'):
    invalid=SD({'logo.raw':rgba});invalid.reset();invalid.failure=failure;assert invalid.read(34)[:4]==b'DEAD'
checks.append('compiled ARM reader: full wallpaper/RGBA, strict sizes and read lengths, missing SD/files, I/O failures, restart')

class PS1:
    def __init__(self,files,wallpaper=False,classic=False,logo_key='1',bad_packet=False,prefetch=False):
        self.prefetch=prefetch
        self.sd=SD(files);self.sd.reset();self.upload=None;self.gpu_uploads=[];self.commands=[];self.bad_packet=bad_packet;self.packet_calls=0
        self.uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);self.uc.mem_map(0,0x200000);self.uc.mem_map(0x1f801000,0x1000)
        self.uc.mem_write(0x10000,menu);self.uc.reg_write(UC_MIPS_REG_GP,0x8003f5d0)
        self.uc.mem_write(0x51190,struct.pack('<2B4H',0,0,128,20,11,0x52e))
        self.uc.mem_write(0x37678,bytes([int(wallpaper)]))
        self.uc.mem_write(0x37694,struct.pack('<I',0x80013ec0 if classic else 0x8001295c))
        self.uc.mem_write(0x37672,b'\0\0');self.uc.mem_write(0x37620,b'\x20')
        # Uniform blue background: same native RGB555 color as the flat default.
        self.uc.mem_write(0x3e384,struct.pack('<256H',*([0x1000]*256)))
        self.logo_key=logo_key;self.uc.hook_add(UC_HOOK_CODE,self.hook)
    def r(self,reg):return self.uc.reg_read(reg)
    def ret(self,value=0):self.uc.reg_write(UC_MIPS_REG_V0,value);self.uc.reg_write(UC_MIPS_REG_PC,self.r(UC_MIPS_REG_RA))
    def hook(self,uc,address,size,data):
        if address==0x80014fc4:
            packet=bytearray(2340);packet[12:16]=b'CFG1';packet[288:288+len(self.logo_key)+5]=('logo='+self.logo_key).encode()
            uc.mem_write(0x3772c,bytes(packet));self.ret()
        elif address==0x80018c7c:self.ret()
        elif address==0x80011b88:
            pair=(self.r(UC_MIPS_REG_A0),self.r(UC_MIPS_REG_A1));self.commands.append(pair)
            if pair==(8,8):self.sd.reset()
            self.ret()
        elif address==0x8001d34c:
            part=self.r(UC_MIPS_REG_A0)-300
            if self.prefetch and part==31:self.sd.read(34)
            if self.prefetch and part==35:self.sd.read(0)
            packet=self.sd.read(part);self.packet_calls+=1
            if self.bad_packet:packet=b'NOPE'+packet[4:]
            uc.mem_write(self.r(UC_MIPS_REG_A1)&0x1fffffff,bytes(12)+packet+bytes(4));self.ret()
        elif address==0x80010474:
            ptr=self.r(UC_MIPS_REG_A0);assert ptr%4==0,'GPU DMA pointer is not aligned'
            x,y,width=[self.r(reg) for reg in (UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3)]
            height=struct.unpack('<I',uc.mem_read((self.r(UC_MIPS_REG_SP)&0x1fffffff)+16,4))[0]
            content=bytes(uc.mem_read(ptr&0x1fffffff,width*height*2))
            self.gpu_uploads.append((x,y,width,height,content))
            if (x,y,width,height)==(768,0,128,20):self.upload=content
            self.ret()
        elif address==0x80010398:self.ret()
        elif address==0x80010668:self.ret(0x80090000)
    def call(self,name,args=()):
        self.uc.reg_write(UC_MIPS_REG_SP,0x801fff00);self.uc.reg_write(UC_MIPS_REG_RA,0x801f0000)
        for reg,value in zip((UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3),args):self.uc.reg_write(reg,value)
        for i,value in enumerate(args[4:]):self.uc.mem_write(0x1fff10+i*4,struct.pack('<I',value))
        self.uc.emu_start(syms[name] if isinstance(name,str) else name,0x801f0000,timeout=5_000_000,count=4000000)
        assert self.r(UC_MIPS_REG_PC)==0x801f0000
    def init(self):self.call('cs_load_config');self.call('cs_init',(0,))
    def draw(self):self.call('cs_logo_draw' if args.diagnostic_background else 'cs_draw_logo',(0,185,14));return struct.unpack('<5I',self.uc.mem_read(0x90000,20))

for wallpaper in (False,True):
    for classic in (False,True):
        ps=PS1({'logo.raw':rgba},wallpaper,classic);ps.init();assert ps.upload is not None
        pixels=struct.unpack('<2560H',ps.upload)
        assert pixels[:4]==(0x8810,0x8000,0,0x83e0),[hex(v) for v in pixels[:4]]
        assert ps.draw()==(0xe100010c,0x65000000,0x000e00b9,0,0x00140080)
        assert ps.commands[-1]==(0,0)
for files,logo_key,bad in [({},'1',False),({'logo.raw':b'x'},'1',False),({'logo.raw':rgba},'0',False),({'logo.raw':rgba},'1',True)]:
    ps=PS1(files,logo_key=logo_key,bad_packet=bad);ps.init();assert ps.upload is None;assert ps.draw()[1]==0x67000000
    if bad:assert ps.packet_calls==20
checks.append('compiled MIPS client + compiled ARM reader: both styles, flat/wallpaper backgrounds, exact alpha/black, DMA alignment, fallback/retry/disable')

archive=ROOT/'build-cs/editor-test-export.zip'
if archive.exists():
    with ZipFile(archive) as z:
        assert z.testzip() is None
        raw=z.read('background.raw');logo=z.read('logo.raw')
    for classic in (False,True):
        ps=PS1({'background.raw':raw,'logo.raw':logo},wallpaper=True,classic=classic,prefetch=True)
        # Execute the real RC5 background loader and both texture upload helpers.
        ps.call(0x80015b3c)
        assert bytes(ps.uc.mem_read(0x3e384,len(raw)))==raw
        if args.diagnostic_background:
            # Snapshot a real compiled ARM reply after the CD header was added.
            ps.call('cs_init',(0,))
            label=bytes(ps.uc.mem_read(syms['file_label']&0x1fffffff,20)).split(b'\0')[0]
            assert label==b'S00012E00 F00012E00',label
        ps.call(0x8001077c,(0x800511a8,0x8003e584,0x8003e384,256,256,256,496,256,240,1))
        ps.call(0x80010b24,(0x800511b2,0x800511a8,0x8004d584,512,256,64,240,1))
        assert ps.gpu_uploads==[(256,256,128,240,raw[512:61952]),(256,496,256,1,raw[:512]),(512,256,32,240,raw[61952:])]
        ps.init();assert ps.upload is not None
        pixels=struct.unpack('<2560H',ps.upload);palette=struct.unpack('<256H',raw[:512])
        for i,pixel in enumerate(pixels):
            x=(100 if classic else 185)+i%128;y=(10 if classic else 14)+i//128
            color=palette[raw[512+y*256+x if x<256 else 61952+y*64+x-256]]
            alpha=logo[i*4+3];expected=0
            if alpha:
                expected=0x8000
                for c in range(3):
                    v=(color>>(c*5))&31;back=(v<<3)|(v>>2)
                    channel=(logo[i*4+c]*alpha+back*(255-alpha)+127)//255
                    expected|=(channel>>3)<<(c*5)
            assert pixel==expected,(classic,i,hex(pixel),hex(expected))
    checks.append('JavaScript editor ZIP decoded by compiled ARM/MIPS code: every pixel, both styles and tile boundary')
    checks.append('real RC5 wallpaper loader and upload helpers preserve all 77312 bytes including the lower-right tile through the GPU transfer boundary')

result={'board':args.board,'checks':checks,'hardware_validated':False,'firmware_sha256':firmware_sha}
(OUT/'firmware-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
