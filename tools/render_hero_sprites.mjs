// Usage: node tools/render_hero_sprites.mjs [--pixelfx ../pixelfx] [--out DIR] [--check]
import { mkdirSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { makeHero, DIRECTIONS, FRAME_SIZE as S, PIVOT, FRAME_COUNT as N } from '../assets/sprites/hero/neutral/source/hero-neutral.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const value = (key, fallback) => args.includes(key) ? args[args.indexOf(key) + 1] : fallback;
const FX = resolve(ROOT, value('--pixelfx', '../pixelfx'));
const OUT = resolve(ROOT, value('--out', 'assets/sprites/hero/neutral'));
const PREVIEW = resolve(ROOT, value('--preview-out', args.includes('--out') ? OUT : 'outputs/previews/hero-neutral'));
if (!existsSync(join(FX, 'tools/lib/fxlib.mjs'))) throw new Error('pixelfx checkout not found; pass --pixelfx PATH');
const core = await import(pathToFileURL(join(FX, 'src/core/index.js')));
const { renderFrames, contactSheet, canvas, upscale } = await import(pathToFileURL(join(FX, 'tools/lib/fxlib.mjs')));
const { encodePNG } = await import(pathToFileURL(join(FX, 'tools/lib/png.mjs')));
mkdirSync(OUT, { recursive: true });
mkdirSync(PREVIEW, { recursive: true });
const all = {};
const sheets = {};

for (const state of ['idle', 'walk']) {
  const imageName = `hero-neutral-${state}.png`, width = N * S, height = DIRECTIONS.length * S;
  const data = new Uint8ClampedArray(width * height * 4), frames = {}, animations = {};
  for (const [row, dir] of DIRECTIONS.entries()) {
    const mod = makeHero(core, state, dir), fx = { id: `element-eater/${state}-${dir}`, meta: mod.meta, mod };
    const r = renderFrames(fx, { bg: 'none' });
    all[`${state}_${dir}`] = r;
    r.frames.forEach((f, i) => {
      let x0=S, y0=S, x1=-1, y1=-1;
      for (let y=0; y<S; y++) for (let x=0; x<S; x++) {
        const src=(y*S+x)*4, dst=((row*S+y)*width+i*S+x)*4;
        data.set(f.clear.subarray(src,src+4),dst);
        if (f.clear[src+3]) { x0=Math.min(x0,x); y0=Math.min(y0,y); x1=Math.max(x1,x); y1=Math.max(y1,y); }
      }
      const key=`${dir}_${i}`;
      frames[key]={ frame:{x:i*S,y:row*S,w:S,h:S}, pivotPixelsTopLeft:{x:PIVOT[0],y:PIVOT[1]},
        opaqueBoundsInCell:{x0,y0,x1,y1}, pico2dClip:{left:i*S,bottom:height-(row+1)*S,width:S,height:S} };
    });
    animations[`${state}_${dir}`]={frames:Array.from({length:N},(_,i)=>`${dir}_${i}`),fps:r.fps,loop:true};
    if (args.includes('--contacts')) writeFileSync(join(PREVIEW,`${state}-${dir}-contact.png`),contactSheet(fx,r,{max:8,zoom:3,width:1600}));
  }
  const png=encodePNG(width,height,data);
  sheets[state]=png.toString('base64');
  const json={schema:'element-eater.sprite-atlas.v1',image:imageName,imageSize:{width,height},state:'neutral',
    animationState:state,layout:{rows:DIRECTIONS,columns:N},frameSize:{width:S,height:S},
    coordinateSystem:'frame and pivot use image top-left origin; pico2dClip uses bottom-left origin',
    recommendedDrawScale:1,frames,animations,sha256:createHash('sha256').update(png).digest('hex'),
    generator:{tool:'pixelfx',version:'0.3.0',source:'source/hero-neutral.mjs',command:'node tools/render_hero_sprites.mjs'}};
  writeFileSync(join(OUT,imageName),png);
  writeFileSync(join(OUT,imageName.replace('.png','.json')),JSON.stringify(json,null,2)+'\n');
  console.log(`${imageName}: ${width}x${height}, ${N*4} frames, ${all[`${state}_down`].fps} fps`);
}

// A labeled review sheet (not a game texture), with identical per-frame scale.
const k=2,cw=S*k,pad=12,label=18,left=80,top=60;
const review=canvas(left+N*(cw+pad),top+8*(cw+label+pad),[19,27,31,255]);
review.text('ELEMENT EATER / NEUTRAL HERO',16,12,3,[236,234,205]);
review.text('64PX / 4 DIRECTIONS / 8 FRAMES EACH',16,36,2,[135,171,147]);
Object.entries(all).forEach(([key,r],row)=>{
  const yy=top+row*(cw+label+pad);
  const [state,dir]=key.split('_');
  review.text(state,8,yy+38,2,[219,219,192]);
  review.text(dir,8,yy+54,2,[135,171,147]);
  r.frames.forEach((f,i)=>{
    const xx=left+i*(cw+pad);
    review.rect(xx,yy,cw,cw,[28,38,40,255]);
    review.paste(upscale(f.clear,S,S,k),cw,cw,xx,yy);
    review.text(`${i}`,xx+4,yy+cw+4,2,[135,171,147]);
  });
});
writeFileSync(join(PREVIEW,'hero-neutral-contact.png'),review.png());

// Self-contained offline motion preview; the actual game uses the separate PNG/JSON files.
writeFileSync(join(PREVIEW,'hero-neutral-preview.html'), `<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>엘리먼트 이터 · 주인공 애니메이션</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#131b1f;color:#f2efd7;font:16px system-ui,sans-serif}
main{max-width:1050px;margin:44px auto;padding:0 24px}h1{font-size:28px;margin:0 0 8px}p{color:#a7bdab;line-height:1.6}
.controls{display:flex;align-items:center;gap:12px;margin:24px 0;flex-wrap:wrap}button,select{font:inherit;color:#f2efd7;background:#283a35;border:1px solid #50665a;border-radius:7px;padding:8px 12px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.card{background:#1d282b;border:1px solid #31423e;border-radius:12px;text-align:center;padding:14px 4px}
.card canvas{image-rendering:pixelated;width:192px;height:192px;max-width:100%;object-fit:contain}.card div{font-size:14px;color:#adc4b1;margin-top:8px}
small{color:#9bb59e}h2{font-size:18px;margin:28px 0 12px}@media(max-width:620px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}main{margin:24px auto}}
</style><main><h1>엘리먼트 이터</h1><p>무속성 주인공 · 4방향 대기와 걷기<br>아이보리 몸과 초록 잎 귀를 유지한 64 × 64px 픽셀 애니메이션</p>
<div class="controls"><button id="play">일시정지</button><label>속도 <select id="speed"><option value="0.5">0.5배</option><option value="1" selected>1배</option><option value="2">2배</option></select></label><label><input id="pivot" type="checkbox"> 발밑 기준점 표시</label><span id="time"></span></div>
<section id="animations"></section><p><small>대기: 방향마다 8프레임 · 4fps / 걷기: 방향마다 8프레임 · 10fps<br>투명 PNG 원본에는 배경과 표시선이 없습니다. 게임 연동 전 에셋 미리보기입니다.</small></p></main>
<script>
const directions=['아래 · 정면','왼쪽','오른쪽','위 · 뒷면'];
const sources={idle:'data:image/png;base64,${sheets.idle}',walk:'data:image/png;base64,${sheets.walk}'};
const views=[];let running=true,elapsed=0,last=performance.now();
for(const state of ['idle','walk']){
 const section=document.createElement('section'),heading=document.createElement('h2'),grid=document.createElement('div');
 heading.textContent=state==='idle'?'대기 · 숨쉬기와 잎 흔들림':'걷기 · 발 교차와 몸 반동';grid.className='grid';section.append(heading,grid);document.querySelector('#animations').append(section);
 const img=new Image();img.src=sources[state];
 for(let row=0;row<4;row++){const card=document.createElement('div'),c=document.createElement('canvas'),label=document.createElement('div');
 c.width=c.height=64;card.className='card';label.textContent=directions[row];card.append(c,label);grid.append(card);views.push({c,img,row,fps:state==='idle'?4:10});}
}
document.querySelector('#play').onclick=()=>{running=!running;document.querySelector('#play').textContent=running?'일시정지':'재생';};
function draw(now){const dt=(now-last)/1000;last=now;if(running)elapsed+=dt*Number(document.querySelector('#speed').value);
 for(const v of views){const ctx=v.c.getContext('2d');ctx.clearRect(0,0,64,64);ctx.imageSmoothingEnabled=false;if(v.img.complete&&v.img.naturalWidth)ctx.drawImage(v.img,(Math.floor(elapsed*v.fps)%8)*64,v.row*64,64,64,0,0,64,64);
 if(document.querySelector('#pivot').checked){ctx.fillStyle='#e8a66b';ctx.fillRect(29,58,7,1);ctx.fillRect(32,55,1,7);}}
 document.querySelector('#time').textContent=elapsed.toFixed(1)+'초';requestAnimationFrame(draw);}
requestAnimationFrame(draw);
</script></html>`);

// Feed the same original modules to upstream's check tool; wrappers are removed afterwards.
if(args.includes('--check')) {
  // allIds ignores underscore categories, so use a unique non-underscore category.
  const name='element-eater-check-'+process.pid, folder=join(FX,'src/fx',name);
  mkdirSync(folder);
  try {
    const heroURL=pathToFileURL(join(ROOT,'assets/sprites/hero/neutral/source/hero-neutral.mjs')).href;
    for(const state of ['idle','walk']) for(const dir of DIRECTIONS) {
      writeFileSync(join(folder,`${state}-${dir}.js`),`import * as core from '../../core/index.js';\nimport { makeHero } from ${JSON.stringify(heroURL)};\nconst hero=makeHero(core,${JSON.stringify(state)},${JSON.stringify(dir)});\nexport const meta=hero.meta;\nexport const draw=hero.draw;\n`);
    }
    const check=spawnSync(process.execPath,['tools/check.mjs',name],{cwd:FX,encoding:'utf8'});
    process.stdout.write(check.stdout ?? ''); process.stderr.write(check.stderr ?? '');
    if(check.error || check.status!==0) throw check.error ?? new Error('pixelfx check failed');
  } finally {
    // folder is a freshly created, unique direct child of FX/src/fx, never a caller path.
    if (dirname(resolve(folder)) !== resolve(FX,'src/fx')) throw new Error('Refusing cleanup outside pixelfx effect directory');
    rmSync(folder,{recursive:true});
  }
}
