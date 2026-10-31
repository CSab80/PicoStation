import {DEFAULTS,COLORS,BUTTONS,checkPng,parseConfig,makeConfig,encodeLogo,decode555,rgb555,composePixel,zipFiles} from './core.mjs';
const $=id=>document.getElementById(id),labels={background:'Fond',frame:'Cadre',filelist:'Liste',cursor:'Curseur',text:'Texte'};
let config={...DEFAULTS},extra=[],selected='background',background=null,logo=null,busy={background:0,logo:0};
try {const stored=localStorage.getItem('picostation-menu-config-v1');if(stored)config=parseConfig(stored).config;}catch{}
const ctx=$('preview').getContext('2d',{willReadFrequently:true});ctx.imageSmoothingEnabled=false;
const font=new Image(),defaultLogo=new Image();let glyphs=[];
font.src='./assets/font.png';defaultLogo.src='./assets/logo-default.png';
Promise.all([font.decode(),defaultLogo.decode(),fetch('./assets/glyphs.json').then(r=>r.json()).then(data=>glyphs=data)]).then(render).catch(()=>status('Les ressources d’aperçu n’ont pas pu être chargées. Lance l’éditeur avec le lanceur local.',true));
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
function persist(){try{localStorage.setItem('picostation-menu-config-v1',makeConfig(config,extra));}catch{}}
function update(){persist();sync();render();}
function sync(){
  document.querySelectorAll('[name=style]').forEach(r=>r.checked=Number(r.value)===config.style);
  for(const key of COLORS){const button=$(`color-${key}`);button.classList.toggle('selected',key===selected);button.setAttribute('aria-pressed',String(key===selected));button.querySelector('.swatch').style.background='#'+config[key];}
  $('picker').value='#'+config[selected];$('hex').value='#'+config[selected];['red','green','blue'].forEach((id,i)=>$(id).value=parseInt(config[selected].slice(i*2,i*2+2),16));
  for(const action of ['actopen','actback'])document.querySelectorAll(`[name=${action}]`).forEach(r=>r.checked=r.value===config[action]);
  $('wallpaper').checked=!!config.wallpaper;$('logo-enabled').checked=!!config.logo;
  $('background-remove').hidden=!background;$('logo-remove').hidden=!logo;
  $('preview-style').textContent=config.style?'Classic':'Covers';
  $('background-info').textContent=background?`${background.name} · ${background.colors} couleurs · 77 312 octets`:'Une image PNG opaque.';
  $('logo-info').textContent=logo?`${logo.name} · transparence RGBA conservée · 10 240 octets`:'PNG avec transparence, ombres et contours adoucis.';
  $('config-preview').textContent=makeConfig(config,extra);
  const rows=[['config.ini',`${new TextEncoder().encode(makeConfig(config,extra)).length} octets`]];
  if(config.wallpaper)rows.push(['background.raw',background?'77 312 octets':'à importer ou déjà sur la SD']);
  if(config.logo)rows.push(['logo.raw',logo?'10 240 octets':'à importer ou déjà sur la SD']);
  $('file-list').replaceChildren(...rows.map(([name,detail])=>{const li=document.createElement('li');li.className='file-row';const span=document.createElement('span'),small=document.createElement('small');span.textContent=name;small.textContent=detail;li.append(span,small);return li;}));
}
for(const key of COLORS){const b=document.createElement('button');b.id=`color-${key}`;b.className='color-choice';b.innerHTML=`<span class="swatch"></span><span>${labels[key]}</span>`;b.addEventListener('click',()=>{selected=key;sync();});$('color-options').append(b);}
const symbols={E:'×',D:'○',F:'□',C:'△'},padColors={E:'#92b8f4',D:'#ef999e',F:'#d6a2d4',C:'#87d2bb'};
for(const [action,name]of [['actopen','Ouvrir'],['actback','Retour']]){const row=document.createElement('div');row.className='assignment';const title=document.createElement('span');title.textContent=name;const choices=document.createElement('div');choices.className='pad-choices';for(const [value,label]of Object.entries(BUTTONS)){const choice=document.createElement('label');choice.innerHTML=`<input type="radio" name="${action}" value="${value}" aria-label="${name} : ${label}"><span style="color:${padColors[value]}" aria-hidden="true">${symbols[value]}</span>`;choice.querySelector('input').addEventListener('change',()=>{config[action]=value;update();});choices.append(choice);}row.append(title,choices);$('buttons').append(row);}
function setColor(hex){if(!/^#[0-9a-f]{6}$/i.test(hex))return false;config[selected]=hex.slice(1).toUpperCase();update();return true;}
$('picker').addEventListener('input',e=>setColor(e.target.value));$('hex').addEventListener('change',e=>{if(!setColor(e.target.value.startsWith('#')?e.target.value:'#'+e.target.value)){status('Entre une couleur sur six chiffres hexadécimaux.',true);sync();}});
$('hex').addEventListener('input',e=>{const value=e.target.value.startsWith('#')?e.target.value:'#'+e.target.value;if(/^#[0-9a-f]{6}$/i.test(value))setColor(value);});
for(const id of ['red','green','blue'])$(id).addEventListener('change',()=>{const values=['red','green','blue'].map(id=>Number($(id).value));if(values.some(v=>!Number.isInteger(v)||v<0||v>255)){status('Chaque composante doit être comprise entre 0 et 255.',true);sync();return;}setColor('#'+values.map(v=>v.toString(16).padStart(2,'0')).join(''));});
document.querySelectorAll('[name=style]').forEach(r=>r.addEventListener('change',()=>{config.style=Number(r.value);update();}));
$('wallpaper').addEventListener('change',e=>{config.wallpaper=Number(e.target.checked);update();if(config.wallpaper&&!background)status('Importe le fond pour le voir ici, ou conserve background.raw déjà présent sur ta SD.');});
$('logo-enabled').addEventListener('change',e=>{config.logo=Number(e.target.checked);update();if(config.logo&&!logo)status('Importe le logo pour le voir ici, ou conserve logo.raw déjà présent sur ta SD.');});
$('reset').addEventListener('click',()=>{config={...DEFAULTS};extra=[];background=logo=null;for(const kind of ['background','logo'])$(`${kind}-input`).value='';update();status('Les réglages d’origine ont été rétablis.');});
for(const kind of ['background','logo']){
  $(`${kind}-input`).addEventListener('change',e=>{if(e.target.files[0])importImage(kind,e.target.files[0]);});
  $(`${kind}-remove`).addEventListener('click',()=>{if(kind==='background'){background=null;config.wallpaper=0;}else{logo=null;config.logo=0;}$(`${kind}-input`).value='';update();status(`${kind==='background'?'Fond':'Logo'} personnalisé retiré de l’export.`);});
  const zone=$(`${kind}-zone`);zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('dragover');});zone.addEventListener('dragleave',()=>zone.classList.remove('dragover'));zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('dragover');if(e.dataTransfer.files.length!==1){status('Dépose une seule image PNG à la fois.',true);return;}importImage(kind,e.dataTransfer.files[0]);});
}
async function importImage(kind,file){
  const token=++busy[kind];
  try{
    status('Conversion de l’image…');if(file.size>20*1024*1024)throw Error('Ce PNG dépasse la limite de 20 Mo.');
    const bytes=new Uint8Array(await file.arrayBuffer());const width=kind==='background'?320:128,height=kind==='background'?240:20;checkPng(bytes,width,height);
    const bitmap=await createImageBitmap(file),canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const context=canvas.getContext('2d');context.drawImage(bitmap,0,0);bitmap.close();const rgba=context.getImageData(0,0,width,height).data;
    let result;
    if(kind==='background')result=await new Promise((resolve,reject)=>{const worker=new Worker('./worker.mjs',{type:'module'});worker.onmessage=e=>{worker.terminate();e.data.error?reject(Error(e.data.error)):resolve(e.data);};worker.onerror=()=>{worker.terminate();reject(Error('La conversion du fond a échoué.'));};worker.postMessage(rgba);});
    else result={raw:encodeLogo(rgba),rgba};
    if(token!==busy[kind])return;
    if(kind==='background'){background={...result,name:file.name};config.wallpaper=1;}else{logo={...result,name:file.name};config.logo=1;}
    update();status(`${file.name} est prêt pour l’export.`);
  }catch(error){if(token===busy[kind])status(error.message,true);}
}
$('config-input').addEventListener('change',async e=>{try{const file=e.target.files[0];if(!file)return;const parsed=parseConfig(await file.text());config=parsed.config;extra=parsed.extra;update();status('Configuration importée. Les images déjà sur la SD restent utilisables.');}catch(error){status(error.message,true);}finally{e.target.value='';}});
function download(bytes,name,type){const url=URL.createObjectURL(new Blob([bytes],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
$('save-config').addEventListener('click',()=>{download(makeConfig(config,extra),'config.ini','text/plain');status('config.ini a été généré.');});
$('download').addEventListener('click',()=>{const files=[['config.ini',makeConfig(config,extra)]];if(config.wallpaper&&background)files.push(['background.raw',background.raw]);if(config.logo&&logo)files.push(['logo.raw',logo.raw]);download(zipFiles(files),'PicoStation-SD.zip','application/zip');status((config.wallpaper&&!background)||(config.logo&&!logo)?'Archive générée. Elle conserve les images déjà sur la SD ; importe-les ici si tu veux aussi les inclure.':'Archive générée : décompresse son contenu à la racine de la carte SD.');});
function text(value,x,y,color='#ffffff'){
  if(!glyphs.length)return;const scratch=document.createElement('canvas');scratch.width=320;scratch.height=16;const s=scratch.getContext('2d');s.imageSmoothingEnabled=false;let offset=0;
  for(const c of value){if(c===' '){offset+=4;continue;}const g=glyphs[c.charCodeAt(0)-33];if(g){s.drawImage(font,...g,offset,0,g[2],g[3]);offset+=g[2];}}
  s.globalCompositeOperation='source-in';s.fillStyle=color;s.fillRect(0,0,320,16);ctx.drawImage(scratch,x,y);
}
function render(){
  ctx.imageSmoothingEnabled=false;const native=decode555(rgb555(...[0,2,4].map(i=>parseInt(config.background.slice(i,i+2),16)),true));ctx.fillStyle=`rgb(${native.join(',')})`;ctx.fillRect(0,0,320,240);
  if(config.wallpaper&&background)ctx.putImageData(new ImageData(new Uint8ClampedArray(background.rgba),320,240),0,0);
  const classic=!!config.style,px=9,py=classic?33:15,pw=classic?302:172,ph=classic?177:195;
  ctx.strokeStyle='#'+config.frame;ctx.lineWidth=1;ctx.strokeRect(px-.5,py-.5,pw+1,ph+1);ctx.globalAlpha=(config.wallpaper&&background)?0.5:1;ctx.fillStyle='#'+config.filelist;ctx.fillRect(px,py,pw,ph);ctx.globalAlpha=1;
  const names=['  Ma collection','  Ridge Racer (NTSC-U)','  Crash Bandicoot','  Metal Gear Solid','  Wipeout 2097'];
  ctx.fillStyle='#'+config.cursor;ctx.fillRect(9,py+13,164,13);names.forEach((name,i)=>text(name,10,py+i*13,'#'+config.text));
  const lx=classic?100:185,ly=classic?10:14;
  if(config.logo&&logo){const under=ctx.getImageData(lx,ly,128,20),out=new Uint8ClampedArray(under.data);for(let i=0;i<2560;i++){const p=composePixel([...logo.rgba.slice(i*4,i*4+4)],[...under.data.slice(i*4,i*4+3)]);out.set([...p,255],i*4);}ctx.putImageData(new ImageData(out,128,20),lx,ly);}
  else if(defaultLogo.complete&&defaultLogo.naturalWidth)ctx.drawImage(defaultLogo,lx,ly);
  text('2 of 3',classic?16:186,classic?16:56,'#'+config.text);
  if(!classic){text('SCUS-94300',186,66,'#'+config.text);ctx.fillStyle='#111829';ctx.fillRect(185,82,128,128);ctx.strokeStyle='#9baabe';ctx.strokeRect(185.5,82.5,127,127);ctx.fillStyle='#29394e';ctx.fillRect(190,87,118,116);text('PLAYSTATION',197,93);text('TA COLLECTION',198,132,'#a1dac0');text('PicoStation',211,150,'#e4eaf3');ctx.fillStyle='#182334';ctx.fillRect(190,191,118,12);}
  const open=BUTTONS[config.actopen],back=BUTTONS[config.actback];text('Fast Boot',25,215,'#'+config.text);text('Regular Boot',177,215,'#'+config.text);ctx.font='10px sans-serif';ctx.fillStyle=padColors[config.actopen];ctx.fillText(symbols[config.actopen],12,223);ctx.fillStyle=padColors[config.actback];ctx.fillText(symbols[config.actback],163,223);$('preview').setAttribute('aria-label',`Menu ${classic?'Classic':'Covers'}, ouvrir avec ${open}, retour avec ${back}.`);
}
sync();render();
