import { makeHero, DIRECTIONS, PIVOT } from './hero-neutral.mjs';

export const ATTACK_FPS = 12;
export const ATTACK_FRAMES = 8;
export const ATTACK_TIMING = {
  windup: 0.25, releaseFrame: 3, releaseTime: 0.25, recoveryEnd: 8/12,
  phases: { prepare: [0,2], release: [3,3], recoil: [4,4], recover: [5,7] },
};
export const MUZZLES = { down:[32,47], left:[10,41], right:[54,41], up:[32,20] };
const POSES = [
  [1,1,0,'normal',0,0,0], [1.04,.97,-1,'puff',-1,1,0],
  [1.06,.95,-2,'puff',-2,2,1], [.97,1,2,'spit',6,3,-1],
  [1.02,.97,-2,'spit',5,1,1], [1.04,.95,-1,'normal',2,1,1],
  [1.01,.99,0,'normal',0,0,0], [1,1,0,'normal',0,0,0],
];

export function makeHeroAttack(core, direction) {
  if (!DIRECTIONS.includes(direction)) throw new Error('Unknown attack direction');
  const base = makeHero(core,'idle',direction);
  const meta = { ...base.meta, name:`Neutral spit ${direction}`,
    desc:'A plump leaf-eared hero squashes, puffs its cheeks, spits a neutral pellet, recoils and settles back on planted feet.',
    tags:['element-eater','hero','attack',direction], duration:8/12, fps:12, loop:false };
  // Stock-rig-compatible choreography is supplemental metadata; the PNG contains the original hero.
  const act = { target:false, poses:[
    [0,{...core.READY}], [2/12,{...core.READY,crouch:3,lean:-2}],
    [3/12,{...core.READY,crouch:0,lean:2},'snap'],
    [4/12,{...core.READY,crouch:2,lean:-2},'snap'], [8/12,{...core.READY}],
  ], hits:[] };
  function draw(p,time,o) {
    if(time>=meta.duration-1e-8) return;
    const fi=Math.min(7,Math.floor(Math.max(0,time)*12+1e-6));
    const [sx,sy,lean,expression,handReach,handLift,leafOffset]=POSES[fi];
    const dx=(direction==='right'?1:direction==='left'?-1:0)*lean;
    const dy=(direction==='down'?1:direction==='up'?-1:0)*lean*.5;
    // Draw through pixelfx into a local pixel buffer, then resample whole cells with nearest-neighbour.
    // The feet (0,0) remain the transformation origin, shared with idle and walk.
    const f=core.createFrame(64,64), bp=core.painterFor(f).place(...PIVOT);
    base.draw(bp,0,{...o,expression,handReach,handLift,leafOffset});
    for(let y=-58;y<6;y++) for(let x=-32;x<32;x++) {
      const weight=Math.max(0,Math.min(1,-y/18));
      const sourceX=Math.floor((x+.5-dx*weight)/sx)+32;
      const sourceY=Math.floor((y+.5-dy*weight)/sy)+58;
      if(sourceX<0||sourceY<0||sourceX>=64||sourceY>=64)continue;
      const color=f.color[sourceY*64+sourceX];
      if(color) p.px(x,y,color);
    }
  }
  return {meta,draw,act};
}
