#!/usr/bin/env python3
"""Rebuild verified RC5 PU18/PU8, then compile the shared CS logo extension."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from cd import rebuild_sector

ROOT = Path(__file__).resolve().parents[2]
BUILD_ID = 'CS02'
VERSION = f'RC5.{BUILD_ID}'
MANIFEST = json.loads((ROOT/'rc5/original/manifest.json').read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', choices=tuple(MANIFEST['boards']), default='PU18', help='Carte PS1 sans overclock (PU18 par défaut).')
parser.add_argument('--diagnostic-background', action='store_true', help='Relever le dernier paquet du fond et l’état FatFs sur console (diagnostic séparé).')
args = parser.parse_args()
BOARD = args.board
REFERENCE = MANIFEST['boards'][BOARD]
OUT = ROOT / 'build-cs' / BOARD
if args.diagnostic_background: OUT = OUT / f'background-diagnostic-{BUILD_ID}'
OUT.mkdir(parents=True, exist_ok=True)

def tool(name, alternate=None):
    result = shutil.which(name)
    if not result and alternate and Path(alternate).exists(): result = alternate
    if not result: raise RuntimeError(f'Outil manquant : {name}. Consulte rc5/README.md.')
    return result

AS=tool('arm-none-eabi-as','/opt/homebrew/bin/arm-none-eabi-as')
COPY=tool('arm-none-eabi-objcopy','/opt/homebrew/bin/arm-none-eabi-objcopy')
ARMCC=tool('arm-none-eabi-gcc','/opt/homebrew/bin/arm-none-eabi-gcc')
CLANG=tool('clang','/opt/homebrew/opt/llvm/bin/clang')
if Path('/opt/homebrew/opt/llvm/bin/clang').exists(): CLANG='/opt/homebrew/opt/llvm/bin/clang'
LLD=tool('ld.lld','/opt/homebrew/opt/lld/bin/ld.lld')
LLVMCOPY=tool('llvm-objcopy','/opt/homebrew/opt/llvm/bin/llvm-objcopy')
NM=tool('llvm-nm','/opt/homebrew/opt/llvm/bin/llvm-nm')
MIPS=['--target=mipsel-none-elf','-march=mips1','-mabi=32','-mno-abicalls','-fno-pic','-G0','-msoft-float']

def run(*args): subprocess.run([str(arg) for arg in args],cwd=ROOT,check=True)
def digest(data): return hashlib.sha256(data).hexdigest()
def symbols(path):
    result={}
    for line in subprocess.check_output([NM,str(path)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:
            try: result[fields[2]]=int(fields[0],16)
            except ValueError: pass
    return result
def assemble(name):
    run(AS,ROOT/f'rc5/original/{name}.S','-o',OUT/f'{name}.o')
    run(COPY,'-O','binary',OUT/f'{name}.o',OUT/f'{name}.bin')
    return (OUT/f'{name}.bin').read_bytes()
def uf2(image):
    padded=image+bytes((-len(image))%256)
    count=len(padded)//256
    return b''.join(struct.pack('<8I',0x0a324655,0x9e5d5157,0x2000,0x10000000+i*256,256,i,count,0xe48bff56)+padded[i*256:(i+1)*256]+bytes(220)+struct.pack('<I',0x0ab16f30) for i in range(count))

flash=assemble('pu18_rc5');menu=assemble('menu_rc5');decoder=assemble('unpacker')
assert digest(flash)==MANIFEST['flash_sha256'] and digest(menu)==MANIFEST['menu_sha256']
flash=bytearray(flash)
for change in REFERENCE['patches_from_pu18']:
    offset=int(change['offset'],16)
    expected=bytes.fromhex(change['expected']);replacement=bytes.fromhex(change['replacement'])
    assert len(expected)==len(replacement) and flash[offset:offset+len(expected)]==expected, 'Unexpected board reference bytes'
    flash[offset:offset+len(expected)]=replacement
flash=bytes(flash)
assert digest(flash)==REFERENCE['flash_sha256'], f'{BOARD} flash does not match official RC5'
(OUT/'reference-flash.bin').write_bytes(flash)
baseline=uf2(flash)
assert digest(baseline)==REFERENCE['original_uf2_sha256'], 'Baseline does not reproduce original UF2'
(OUT/f'picostation_{BOARD}_RC5-reconstruit.uf2').write_bytes(baseline)
print(f'RC5 {BOARD} reconstruite : identique octet pour octet à l’UF2 de référence.',flush=True)

arm_defines=['-DCS_BACKGROUND_DIAGNOSTIC'] if args.diagnostic_background else []
run(ARMCC,'-mcpu=cortex-m0plus','-mthumb','-Os','-ffreestanding','-fno-builtin','-fno-unwind-tables','-nostdlib',*arm_defines,'-T','rc5/patches/arm.ld','rc5/patches/arm_logo.c','-o',OUT/'arm_logo.elf')
run(COPY,'-O','binary',OUT/'arm_logo.elf',OUT/'arm_logo.bin')
ps1_source='rc5/patches/ps1_background_diagnostic.c' if args.diagnostic_background else 'rc5/patches/ps1_logo.c'
run(CLANG,*MIPS,'-Os','-ffreestanding','-fno-builtin','-c',ps1_source,'-o',OUT/'ps1_logo.o')
run(LLD,'-m','elf32ltsmip','-T','rc5/patches/ps1.ld',OUT/'ps1_logo.o','-o',OUT/'ps1_logo.elf')
run(LLVMCOPY,'-O','binary',OUT/'ps1_logo.elf',OUT/'ps1_logo.bin')
syms=symbols(OUT/'ps1_logo.elf')
patch=(OUT/'ps1_logo.bin').read_bytes()
patch=patch.ljust(syms['image_end']-0x8005c000,b'\0')
modified=bytearray(menu+patch)
hooks=[]
for old,name in [(0x80018c7c,'cs_init'),(0x80014fc4,'cs_load_config')]:
    original=0x0c000000|((old>>2)&0x03ffffff)
    replacement=0x0c000000|((syms[name]>>2)&0x03ffffff)
    matches=[]
    for off in range(0,0x14808,4):
        if struct.unpack_from('<I',modified,off)[0]==original:
            struct.pack_into('<I',modified,off,replacement);matches.append(hex(off+0x80010000))
    assert matches, f'Hook {name} absent'
    hooks.append({'function':name,'calls':matches,'destination':hex(syms[name])})
draw=0x80011900-0x80010000
assert modified[draw:draw+8]==menu[draw:draw+8]
struct.pack_into('<2I',modified,draw,0x08000000|((syms['cs_draw_logo']>>2)&0x03ffffff),0)
heap_start=(syms['image_end']+7)&~7
assert struct.unpack_from('<I',modified,0x27668)[0]==0x8005bcfc
struct.pack_into('<I',modified,0x27668,heap_start)
assert modified[0x14ae4:0x14ae4+16]==b'PicoStation RC5\0'
version=f'{VERSION}diag' if args.diagnostic_background else VERSION
modified[0x14ae4:0x14ae4+16]=(version+'\0').encode().ljust(16,b'\0')
(OUT/f'menu-{BUILD_ID}.bin').write_bytes(modified)

ucl=ROOT/'third_party/ucl'
if not (ucl/'src/n2e_99.c').exists(): raise RuntimeError('Initialise le sous-module third_party/ucl.')
sources=['n2e_99.c','n2e_ds.c','alloc.c','ucl_init.c','ucl_util.c','ucl_ptr.c','ucl_str.c']
run(CLANG,'-O2','-Wno-tautological-constant-out-of-range-compare','-Ithird_party/ucl/include','-Ithird_party/ucl','-Ithird_party/ucl/src','tools/rc5/ucl_pack.c',*[ucl/'src'/name for name in sources],'-o',OUT/'ucl-pack')
run(OUT/'ucl-pack',OUT/f'menu-{BUILD_ID}.bin',OUT/f'menu-{BUILD_ID}.n2e')
compressed=(OUT/f'menu-{BUILD_ID}.n2e').read_bytes()
load=0x80100000
packed=compressed+bytes((-len(compressed))%4)
decompressor=load+len(packed);packed+=decoder
packed+=bytes((-len(packed))%16)
entry=load+len(packed)
run(CLANG,*MIPS,'-c','rc5/patches/pack_wrapper.S','-o',OUT/'wrapper.o')
run(LLD,'-m','elf32ltsmip',f'-Ttext={hex(entry)}',f'--defsym=packed_start={hex(load)}',f'--defsym=nrv_decompressor={hex(decompressor)}','-e','_start',OUT/'wrapper.o','-o',OUT/'wrapper.elf')
run(LLVMCOPY,'-O','binary','--only-section=.text',OUT/'wrapper.elf',OUT/'wrapper.bin')
packed+=(OUT/'wrapper.bin').read_bytes()
packed+=bytes((-len(packed))%2048)
header=bytearray(2048);header[:8]=b'PS-X EXE';struct.pack_into('<4I',header,16,entry,0,load,len(packed))
exe=header+packed
(OUT/f'menu-{BUILD_ID}.ps-exe').write_bytes(exe)
disc_offset=0x12d18
disc=flash[disc_offset:disc_offset+50*2352]
sectors=[disc[i:i+2352] for i in range(0,len(disc),2352)]
iso=bytearray(b''.join(sector[24:2072] for sector in sectors))
root_sector=struct.unpack_from('<I',iso,16*2048+158)[0]
root_size=struct.unpack_from('<I',iso,16*2048+166)[0]
offset=root_sector*2048;end=offset+root_size;record=None
while offset<end:
    length=iso[offset]
    if not length:offset=(offset//2048+1)*2048;continue
    name=iso[offset+33:offset+33+iso[offset+32]]
    if name.startswith(b'SCES_313.37'):record=offset;break
    offset+=length
assert record is not None
extent=struct.unpack_from('<I',iso,record+2)[0];capacity=struct.unpack_from('<I',iso,record+10)[0]
assert len(exe)<=((capacity+2047)//2048)*2048, f'Packed menu exceeds original CD allocation: {len(exe)} > {capacity}'
struct.pack_into('<I',iso,record+10,len(exe));struct.pack_into('>I',iso,record+14,len(exe))
iso[extent*2048:extent*2048+len(exe)]=exe
changed_sectors=[];new_sectors=[]
for i,sector in enumerate(sectors):
    payload=bytes(iso[i*2048:(i+1)*2048])
    if payload!=sector[24:2072]:new_sectors.append(rebuild_sector(sector,payload));changed_sectors.append(i)
    else:new_sectors.append(sector)
new_disc=b''.join(new_sectors)
new_flash=bytearray(flash)
new_flash[disc_offset:disc_offset+len(new_disc)]=new_disc
runtime=lambda address:0x330b0+address-0x200000c0
bound=runtime(0x2000254e);assert new_flash[bound:bound+2]==bytes.fromhex('2128');new_flash[bound:bound+2]=bytes.fromhex('2628')
reader=runtime(0x20003fbc)
assert new_flash[reader:reader+4]==bytes.fromhex('f0b5124c')
new_flash[reader:reader+8]=struct.pack('<2HI',0x4b00,0x4718,0x1003d201)
assert len(new_flash)==0x3d200
arm_patch=(OUT/'arm_logo.bin').read_bytes();new_flash+=arm_patch
result=uf2(new_flash)
firmware_tag=f'{VERSION}-background-diagnostic' if args.diagnostic_background else f'{VERSION}-experimental'
(OUT/f'picostation_{BOARD}_{firmware_tag}.uf2').write_bytes(result)
(OUT/f'firmware-{BUILD_ID}.bin').write_bytes(new_flash)
report={'build_id':BUILD_ID,'version':version,'diagnostic_background':args.diagnostic_background,'board':BOARD,'overclocked':False,'baseline_bit_identical':True,'baseline_uf2_sha256':digest(baseline),'firmware_uf2_sha256':digest(result),'flash_size':len(new_flash),'arm_patch_bytes':len(arm_patch),'ps1_patch_bytes_including_zero_initialized_storage':len(patch),'heap_start':hex(heap_start),'menu_compressed_bytes':len(compressed),'exe_size':len(exe),'exe_capacity':capacity,'packed_load':hex(load),'packed_entry':hex(entry),'unpacker_entry':hex(decompressor),'menu_unpacked_size':len(modified),'menu_unpacked_sha256':digest(modified),'symbols':{k:hex(v) for k,v in syms.items()},'hooks':hooks,'changed_cd_sectors':changed_sectors,'board_reference_patches':REFERENCE['patches_from_pu18'],'arm_changed_ranges':[{'offset':hex(bound),'length':2},{'offset':hex(reader),'length':8},{'offset':'0x3d200','length':len(arm_patch)}],'hardware_validated':False}
report['tool_versions']={name:subprocess.check_output([compiler,'--version'],text=True).splitlines()[0] for name,compiler in [('arm_gcc',ARMCC),('clang',CLANG),('lld',LLD)]}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
