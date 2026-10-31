// SPDX-License-Identifier: Apache-2.0
export const DEFAULTS = Object.freeze({ background:'000020', frame:'FFFFFF', filelist:'000040', cursor:'800000', text:'FFFFFF', style:0, wallpaper:0, actopen:'E', actback:'D', logo:0 });
export const COLORS = ['background','frame','filelist','cursor','text'];
export const BUTTONS = { E:'Croix', D:'Rond', F:'Carré', C:'Triangle' };
export const PNG_SIGNATURE = [137,80,78,71,13,10,26,10];
export function checkPng(bytes,width,height) {
  if(bytes.length<33 || !PNG_SIGNATURE.every((v,i)=>bytes[i]===v)) throw Error('Choisis une image PNG valide.');
  const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  if(String.fromCharCode(...bytes.slice(12,16))!=='IHDR') throw Error('En-tête PNG invalide.');
  const w=view.getUint32(16),h=view.getUint32(20);
  if(w!==width||h!==height) throw Error(`Dimensions attendues : ${width} × ${height} px. Ton image fait ${w} × ${h} px.`);
}
export function parseConfig(text) {
  if(new TextEncoder().encode(text).length>2048) throw Error('Le fichier config.ini dépasse 2 048 octets.');
  const config={...DEFAULTS},extra=[];
  for(const line of text.replace(/^\uFEFF/,'').split(/\r?\n/)) {
    if(!line.trim()||/^[;#]/.test(line.trim()))continue;
    const match=/^\s*([a-zA-Z][a-zA-Z0-9_]*)\s*=\s*#?([0-9a-fA-F]+)\s*(?:[;#].*)?$/.exec(line);
    if(!match)throw Error(`Ligne de configuration non reconnue : ${line}`);
    const [,key,raw]=match;
    if(key==='lang')continue;
    if(COLORS.includes(key)) { if(raw.length>6)throw Error(`Couleur ${key} invalide.`);config[key]=raw.padStart(6,'0').toUpperCase(); }
    else if(key==='actopen'||key==='actback') { const val=parseInt(raw,16).toString(16).toUpperCase();if(!BUTTONS[val])throw Error(`Bouton ${key} non proposé par cet éditeur.`);config[key]=val; }
    else if(key==='style'||key==='wallpaper'||key==='logo') { const value=parseInt(raw,16);if(value!==0&&value!==1)throw Error(`Valeur ${key} attendue : 0 ou 1.`);config[key]=value; }
    else extra.push(`${key}=${raw.toUpperCase()}`);
  }
  return {config,extra};
}
export function makeConfig(config,extra=[]) {
  for(const key of COLORS)if(!/^[0-9a-f]{6}$/i.test(config[key]))throw Error(`Couleur ${key} invalide.`);
  for(const key of ['actopen','actback'])if(!BUTTONS[config[key]])throw Error(`Bouton ${key} invalide.`);
  for(const key of ['style','wallpaper','logo'])if(config[key]!==0&&config[key]!==1)throw Error(`Valeur ${key} invalide.`);
  const text=Object.keys(DEFAULTS).map(key=>`${key}=${typeof config[key]==='string'?config[key].toUpperCase():config[key]}`).concat(extra).join('\r\n')+'\r\n';
  if(new TextEncoder().encode(text).length>2048)throw Error('La configuration dépasse 2 048 octets.');
  return text;
}
export function rgb555(r,g,b,opaqueBlack=false) {
  const word=(r>>3)|((g>>3)<<5)|((b>>3)<<10);
  return word|| (opaqueBlack?0x8000:0x0421);
}
export function decode555(word) { return [0,5,10].map(s=>{const v=(word>>s)&31;return (v<<3)|(v>>2);}); }
function quantize(rgba) {
  const histogram=new Map();
  for(let i=0;i<rgba.length;i+=4) {
    if(rgba[i+3]!==255)throw Error('Le fond doit être entièrement opaque. Aplatis sa transparence avant de l’importer.');
    const word=rgb555(rgba[i],rgba[i+1],rgba[i+2]);histogram.set(word,(histogram.get(word)||0)+1);
  }
  let boxes=[[...histogram].map(([word,count])=>({word,count,r:word&31,g:(word>>5)&31,b:(word>>10)&31}))];
  function stats(box) { const ranges=['r','g','b'].map(k=>Math.max(...box.map(p=>p[k]))-Math.min(...box.map(p=>p[k])));return {ranges,score:Math.max(...ranges)*box.reduce((n,p)=>n+p.count,0)}; }
  if(histogram.size>256) while(boxes.length<256) {
    let index=-1,best=-1,channel;
    boxes.forEach((box,i)=>{if(box.length>1){const s=stats(box);if(s.score>best){index=i;best=s.score;channel=['r','g','b'][s.ranges.indexOf(Math.max(...s.ranges))];}}});
    if(index<0)break;
    const box=boxes[index].sort((a,b)=>a[channel]-b[channel]||a.word-b.word), total=box.reduce((n,p)=>n+p.count,0);let n=0,cut=1;
    for(let i=0;i<box.length-1;i++){n+=box[i].count;if(n>=total/2){cut=i+1;break;}cut=i+1;}
    boxes.splice(index,1,box.slice(0,cut),box.slice(cut));
  }
  let words;
  if(histogram.size<=256)words=[...histogram.keys()].sort((a,b)=>a-b);
  else words=boxes.map(box=>{const total=box.reduce((n,p)=>n+p.count,0);const c=['r','g','b'].map(k=>Math.round(box.reduce((n,p)=>n+p[k]*p.count,0)/total));return c[0]|(c[1]<<5)|(c[2]<<10)||0x421;});
  words=[...new Set(words)];
  const cache=new Map(),indices=new Uint8Array(rgba.length/4);
  for(const word of histogram.keys()) {
    const c=decode555(word);let index=0,best=Infinity;
    words.forEach((value,i)=>{const p=decode555(value),d=2*(c[0]-p[0])**2+4*(c[1]-p[1])**2+(c[2]-p[2])**2;if(d<best){best=d;index=i;}});cache.set(word,index);
  }
  for(let i=0;i<indices.length;i++)indices[i]=cache.get(rgb555(rgba[i*4],rgba[i*4+1],rgba[i*4+2]));
  return {words,indices};
}
export function encodeBackground(rgba) {
  if(rgba.length!==320*240*4)throw Error('Fond attendu : 320 × 240 pixels.');
  const {words,indices}=quantize(rgba),raw=new Uint8Array(77312),view=new DataView(raw.buffer);
  words.forEach((word,i)=>view.setUint16(i*2,word,true));
  for(let y=0;y<240;y++) {raw.set(indices.subarray(y*320,y*320+256),512+y*256);raw.set(indices.subarray(y*320+256,(y+1)*320),61952+y*64);}
  return {raw,rgba:decodeBackground(raw),colors:words.length};
}
export function decodeBackground(raw) {
  if(raw.length!==77312)throw Error('background.raw doit faire 77 312 octets.');
  const view=new DataView(raw.buffer,raw.byteOffset,raw.byteLength),rgba=new Uint8ClampedArray(320*240*4);
  for(let y=0;y<240;y++)for(let x=0;x<320;x++) {const index=raw[x<256?512+y*256+x:61952+y*64+x-256],color=decode555(view.getUint16(index*2,true)),off=(y*320+x)*4;rgba.set([...color,255],off);}
  return rgba;
}
export function encodeLogo(rgba) {if(rgba.length!==128*20*4)throw Error('Logo attendu : 128 × 20 pixels.');return new Uint8Array(rgba);}
export function composePixel(rgba,bg) {
  if(!rgba[3])return bg;
  return decode555(rgb555(...rgba.slice(0,3).map((c,i)=>Math.floor((c*rgba[3]+bg[i]*(255-rgba[3])+127)/255)),true));
}
export function zipFiles(files) {
  const encoder=new TextEncoder(),parts=[],directory=[];let offset=0;
  const crc=bytes=>{let c=0xffffffff;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;};
  for(const [name,data]of files){const n=encoder.encode(name),bytes=typeof data==='string'?encoder.encode(data):data,head=new Uint8Array(30+n.length),h=new DataView(head.buffer),checksum=crc(bytes);h.setUint32(0,0x04034b50,true);h.setUint16(4,20,true);h.setUint16(12,33,true);h.setUint32(14,checksum,true);h.setUint32(18,bytes.length,true);h.setUint32(22,bytes.length,true);h.setUint16(26,n.length,true);head.set(n,30);parts.push(head,bytes);const central=new Uint8Array(46+n.length),v=new DataView(central.buffer);v.setUint32(0,0x02014b50,true);v.setUint16(4,20,true);v.setUint16(6,20,true);v.setUint16(14,33,true);v.setUint32(16,checksum,true);v.setUint32(20,bytes.length,true);v.setUint32(24,bytes.length,true);v.setUint16(28,n.length,true);v.setUint32(42,offset,true);central.set(n,46);directory.push(central);offset+=head.length+bytes.length;}
  const centralSize=directory.reduce((n,p)=>n+p.length,0),end=new Uint8Array(22),e=new DataView(end.buffer);e.setUint32(0,0x06054b50,true);e.setUint16(8,files.length,true);e.setUint16(10,files.length,true);e.setUint32(12,centralSize,true);e.setUint32(16,offset,true);const result=new Uint8Array(offset+centralSize+22);let pos=0;for(const p of [...parts,...directory,end]){result.set(p,pos);pos+=p.length;}return result;
}
