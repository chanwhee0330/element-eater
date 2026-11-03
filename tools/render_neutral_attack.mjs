// node tools/render_neutral_attack.mjs [--pixelfx ../pixelfx] [--draft DIR] [--check]
import { mkdirSync,writeFileSync,existsSync,rmSync } from 'node:fs';
import { resolve,dirname,join } from 'node:path';
import { pathToFileURL,fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { makeHeroAttack,ATTACK_TIMING,MUZZLES } from '../assets/sprites/hero/neutral/source/hero-attack.mjs';
import { makeNeutralFx } from '../assets/effects/neutral/source/neutral-fx.mjs';
import { DIRECTIONS } from '../assets/sprites/hero/neutral/source/hero-neutral.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..'), args=process.argv.slice(2);
const value=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const FX=resolve(ROOT,value('--pixelfx','../pixelfx'));
const DRAFT=args.includes('--draft')?resolve(ROOT,value('--draft')):null;
const HERO=DRAFT?join(DRAFT,'hero'):join(ROOT,'assets/sprites/hero/neutral');
const EFFECTS=DRAFT?join(DRAFT,'effects'):join(ROOT,'assets/effects/neutral');
const PREVIEW=DRAFT?join(DRAFT,'preview'):join(ROOT,'outputs/previews/neutral-attack');
if(!existsSync(join(FX,'tools/lib/fxlib.mjs')))throw new Error('pixelfx checkout not found');
const core=await import(pathToFileURL(join(FX,'src/core/index.js')));
const {renderFrames,canvas,upscale,contactSheet}=await import(pathToFileURL(join(FX,'tools/lib/fxlib.mjs')));
const {encodePNG}=await import(pathToFileURL(join(FX,'tools/lib/png.mjs')));
for(const dir of [HERO,EFFECTS,PREVIEW])mkdirSync(dir,{recursive:true});
const rendered={},modules=[];
function atlas(folder,name,kind,factory){
  const rs=DIRECTIONS.map(direction=>{
    const mod=factory(direction),fx={id:`element-eater/${name}-${direction}`,meta:mod.meta,mod};
    const r=renderFrames(fx,{bg:'none'});r.frames=r.frames.slice(0,8);r.n=8;
    rendered[`${kind}_${direction}`]=r;modules.push({name:`${kind}-${direction}`,kind,direction});
    if(args.includes('--contacts'))writeFileSync(join(PREVIEW,`${kind}-${direction}-contact.png`),contactSheet(fx,r,{max:8,zoom:3}));
    return r;
  });
  const S=rs[0].w,W=S*8,H=S*4,pivot=kind==='attack'?[32,58]:[S/2,S/2];
  const data=new Uint8ClampedArray(W*H*4),frames={},animations={};
  rs.forEach((r,row)=>{
    r.frames.forEach((f,i)=>{
      let x0=S,y0=S,x1=-1,y1=-1;
      for(let y=0;y<S;y++)for(let x=0;x<S;x++){
        const s=(y*S+x)*4,d=((row*S+y)*W+i*S+x)*4;
        data.set(f.clear.subarray(s,s+4),d);
        if(f.clear[s+3]){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
      }
      frames[`${DIRECTIONS[row]}_${i}`]={frame:{x:i*S,y:row*S,w:S,h:S},
        pivotPixelsTopLeft:{x:pivot[0],y:pivot[1]},opaqueBoundsInCell:x1<0?null:{x0,y0,x1,y1},
        pico2dClip:{left:i*S,bottom:H-(row+1)*S,width:S,height:S}};
    });
    animations[`${kind}_${DIRECTIONS[row]}`]={frames:Array.from({length:8},(_,i)=>`${DIRECTIONS[row]}_${i}`),fps:r.fps,loop:kind==='projectile'};
  });
  const png=encodePNG(W,H,data),json={schema:'element-eater.sprite-atlas.v1',image:`${name}.png`,
    imageSize:{width:W,height:H},state:'neutral',animationState:kind,layout:{rows:DIRECTIONS,columns:8},
    frameSize:{width:S,height:S},coordinateSystem:'frame and pivot use image top-left origin; pico2dClip uses bottom-left origin',
    recommendedDrawScale:1,frames,animations,sha256:createHash('sha256').update(png).digest('hex'),
    generator:{tool:'pixelfx',version:'0.3.0',command:'node tools/render_neutral_attack.mjs'}};
  if(kind==='attack'){
    json.timing=ATTACK_TIMING;json.muzzlePixelsTopLeft=Object.fromEntries(DIRECTIONS.map(d=>[d,{x:MUZZLES[d][0],y:MUZZLES[d][1]}]));
    json.drawProjectileBehindHero=['up'];json.damage=0;json.knockback={regularEnemyPixels:12,bossPixels:4,seconds:.1,status:'initial-proposal'};
    json.note='무속성은 피해 없이 약한 넉백만 준다. 모션 종료 뒤 idle로 전환한다. 실제 게임 판정은 미구현.';
  }
  if(kind==='projectile')json.staticImage='neutral-projectile.png';
  mkdirSync(folder,{recursive:true});writeFileSync(join(folder,`${name}.png`),png);writeFileSync(join(folder,`${name}.json`),JSON.stringify(json,null,2)+'\n');
  console.log(`${name}: ${W}x${H}, 4x8 frames, ${rs[0].fps} fps`);
}
atlas(HERO,'hero-neutral-attack','attack',d=>makeHeroAttack(core,d));
for(const kind of ['projectile','muzzle','impact'])atlas(join(EFFECTS,kind),`neutral-${kind}-sheet`,kind,d=>makeNeutralFx(core,kind,d));
const shot=rendered.projectile_right;
writeFileSync(join(EFFECTS,'projectile/neutral-projectile.png'),encodePNG(shot.w,shot.h,shot.frames[0].clear));

// All hero frames and the three effect strips on one labeled review image.
const pad=12,left=80,top=60,cell=128,gap=12;
const review=canvas(left+8*(cell+gap),top+4*158+3*122,[19,27,31,255]);
review.text('NEUTRAL ATTACK / RELEASE FRAME 3',16,12,3,[236,234,205]);
review.text('PREPARE - PUFF - WINDUP - SPIT - RECOIL - RECOVER',16,36,2,[135,171,147]);
DIRECTIONS.forEach((dir,row)=>{
  const r=rendered[`attack_${dir}`],y=top+row*158;review.text(dir,8,y+52,2,[159,190,163]);
  r.frames.forEach((f,i)=>{const x=left+i*(cell+gap);review.rect(x,y,cell,cell,[29,40,43,255]);review.paste(upscale(f.clear,64,64,2),128,128,x,y);review.text(`${i}${i===3?' SPIT':''}`,x+4,y+132,2,[159,190,163]);});
});
['projectile','muzzle','impact'].forEach((kind,row)=>{
  const r=rendered[`${kind}_right`],k=r.w===48?2:3,y=top+4*158+row*122;review.text(kind,8,y+48,1,[159,190,163]);
  r.frames.forEach((f,i)=>review.paste(upscale(f.clear,r.w,r.h,k),r.w*k,r.h*k,left+i*(cell+gap)+16,y));
});
writeFileSync(join(PREVIEW,'neutral-attack-contact.png'),review.png());
if(args.includes('--check')){
  const name='element-eater-attack-check-'+process.pid,folder=join(FX,'src/fx',name);mkdirSync(folder);
  try{
    const heroURL=pathToFileURL(join(ROOT,'assets/sprites/hero/neutral/source/hero-attack.mjs')).href;
    const fxURL=pathToFileURL(join(ROOT,'assets/effects/neutral/source/neutral-fx.mjs')).href;
    for(const {name:id,kind,direction} of modules){
      const factory=kind==='attack'?`makeHeroAttack(core,${JSON.stringify(direction)})`:`makeNeutralFx(core,${JSON.stringify(kind)},${JSON.stringify(direction)})`;
      writeFileSync(join(folder,`${id}.js`),`import * as core from '../../core/index.js';\nimport {makeHeroAttack} from ${JSON.stringify(heroURL)};\nimport {makeNeutralFx} from ${JSON.stringify(fxURL)};\nconst fx=${factory};\nexport const meta=fx.meta;export const draw=fx.draw;${kind==='attack'?'export const act=fx.act;':''}\n`);
    }
    const check=spawnSync(process.execPath,['tools/check.mjs',name],{cwd:FX,encoding:'utf8'});
    process.stdout.write(check.stdout??'');process.stderr.write(check.stderr??'');
    if(check.error||check.status!==0)throw check.error??new Error('pixelfx check failed');
  }finally{
    if(dirname(resolve(folder))!==resolve(FX,'src/fx'))throw new Error('Unsafe cleanup path');
    rmSync(folder,{recursive:true});
  }
}
