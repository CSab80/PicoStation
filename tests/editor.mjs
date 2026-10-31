import assert from 'node:assert/strict';
import {DEFAULTS,parseConfig,makeConfig,encodeBackground,decodeBackground,encodeLogo,composePixel,checkPng,zipFiles} from '../PicoStation Menu Editor/core.mjs';
export function runTests(){
  const checks=[];
  const config=makeConfig(DEFAULTS);
  assert(config.includes('actopen=E\r\nactback=D\r\n'));
  assert(!config.includes('lang'));
  assert.deepEqual(parseConfig(config).config,DEFAULTS);
  assert.equal(parseConfig('text=ff00ff\nactopen=C\nlang=3\nother=AB').extra[0],'other=AB');
  assert.throws(()=>parseConfig('actopen=14'));
  assert.throws(()=>parseConfig('style=2'));
  assert.throws(()=>parseConfig('x'.repeat(2049)));
  assert.throws(()=>makeConfig({...DEFAULTS,logo:2}));checks.push('config defaults, hexadecimal buttons, import validation, language omitted');
  const rgba=new Uint8ClampedArray(320*240*4);
  for(let y=0;y<240;y++)for(let x=0;x<320;x++){const i=(y*320+x)*4;rgba.set([x<256?248:0,y<120?0:248,x<256?0:248,255],i);}
  const encoded=encodeBackground(rgba);
  assert.equal(encoded.raw.length,77312);assert.equal(encoded.colors,4);
  const decoded=decodeBackground(encoded.raw);
  assert.deepEqual([...decoded.slice((239*320+255)*4,(239*320+255)*4+4)],[255,255,0,255]);
  assert.deepEqual([...decoded.slice((239*320+256)*4,(239*320+256)*4+4)],[0,255,255,255]);
  assert.deepEqual(decoded,encoded.rgba);
  const transparent=rgba.slice();transparent[3]=0;assert.throws(()=>encodeBackground(transparent));
  checks.push('background 77312 bytes, palette, left/right tile boundary and last row');
  for(let i=0;i<rgba.length;i+=4){rgba[i]=(i*37)%256;rgba[i+1]=(i>>4)%256;rgba[i+2]=(i>>8)%256;}
  const many=encodeBackground(rgba);assert(many.colors<=256);assert.equal(many.raw.length,77312);assert.deepEqual(many.raw,encodeBackground(rgba).raw);checks.push('deterministic quantization beyond 256 colors');
  const logo=new Uint8Array(128*20*4);for(let i=0;i<2560;i++)logo.set([255,(i*7)%256,(i*11)%256,i%256],i*4);logo.set([255,0,0,128]);logo.set([12,34,56,0],4);
  assert.deepEqual(encodeLogo(logo),logo);assert.equal(encodeLogo(logo).length,10240);
  assert.deepEqual(composePixel([255,0,0,128],[0,0,255]),[132,0,123]);
  assert.deepEqual(composePixel([255,0,0,0],[12,34,56]),[12,34,56]);
  assert.deepEqual(composePixel([0,0,0,255],[255,255,255]),[0,0,0]);checks.push('logo RGBA including half alpha, transparent pixels, opaque black');
  const png=new Uint8Array(33);png.set([137,80,78,71,13,10,26,10]);png.set([73,72,68,82],12);new DataView(png.buffer).setUint32(16,128);new DataView(png.buffer).setUint32(20,20);checkPng(png,128,20);assert.throws(()=>checkPng(png,320,240));assert.throws(()=>checkPng(new Uint8Array(40),128,20));checks.push('PNG signature and exact dimensions');
  const zip=zipFiles([['config.ini',config],['background.raw',encoded.raw],['logo.raw',logo]]);assert.equal(new DataView(zip.buffer).getUint32(0,true),0x04034b50);checks.push('ZIP generation with three root files');
  return {checks,zip,background:encoded.raw,logo};
}
