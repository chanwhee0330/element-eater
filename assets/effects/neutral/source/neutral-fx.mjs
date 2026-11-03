// Original neutral contact effects drawn with pixelfx; no elemental colors or stock sprites.
const PALETTE=['#655c50','#9a907d','#c5baa1','#e6dcc1','#fff5da','#ffffff'];
const VECTORS={right:[1,0],left:[-1,0],down:[0,1],up:[0,-1]};
export function makeNeutralFx(core,kind,direction='right') {
  if(!['projectile','muzzle','impact'].includes(kind)||!VECTORS[direction])throw new Error('Unknown neutral effect');
  const size=kind==='impact'?48:32, fps=kind==='projectile'?12:16, duration=8/fps;
  const meta={name:`Neutral ${kind} ${direction}`,desc:`A small ivory ${kind} with compact pixel clusters, a soft gray rim and a short rounded pop; no elemental magic.`,
    tags:['neutral',kind,direction],size:[size,size],origin:[size/2,size/2],duration,loop:kind==='projectile',fps,bg:'dark',options:{palette:PALETTE,seed:1}};
  function draw(p,time,o) {
    if(!meta.loop && time>=duration-1e-8)return;
    const frame=Math.min(7,Math.floor(time*fps+1e-6)),phase=frame/8*Math.PI*2;
    const C=core.fit(o.palette??PALETTE,6),[vx,vy]=VECTORS[direction];
    const map=(x,y)=>[Math.round(vx*x-vy*y),Math.round(vy*x+vx*y)];
    function dot(x,y,c){const [X,Y]=map(x,y);p.px(X,Y,c);}
    function oval(cx,cy,rx,ry,fill,outline=true) {
      for(let y=Math.floor(cy-ry);y<=Math.ceil(cy+ry);y++)for(let x=Math.floor(cx-rx);x<=Math.ceil(cx+rx);x++){
        const u=(x+.5-cx)/rx,v=(y+.5-cy)/ry;
        if(u*u+v*v>1)continue;
        const edge=((x+.5-cx)/Math.max(.5,rx-1))**2+((y+.5-cy)/Math.max(.5,ry-1))**2>1;
        const color=outline&&edge?C[0]:fill??(v>.4||u>.6?C[2]:u<-.1&&v<-.1?C[5]:C[4]);
        dot(x,y,color);
      }
    }
    if(kind==='projectile') {
      const pulse=Math.sin(phase);
      oval(0,0,5.2+pulse*.6,4.8-pulse*.6);
      oval(-8.5,Math.round(Math.sin(phase)*1.2),2,1.6,C[3]);
      oval(-12,Math.round(Math.sin(phase+1.1)*1.3),1.4,1.1,C[2]);
      return;
    }
    if(kind==='muzzle') {
      if(frame===7)return;
      const age=frame/7,spread=2+age*8;
      if(frame<3)oval(1+age*2,0,4-age*3,3.5-age*2,C[5],false);
      for(const s of [-1,1]){
        const rad=Math.max(.8,2.4-age*1.6);
        oval(2+age*7,s*(2+age*3),rad,rad,C[frame<3?4:2],false);
        if(frame<5){const [x0,y0]=map(3+age*3,s*2),[x1,y1]=map(5+age*6,s*(3+age));p.line(x0,y0,x1,y1,C[3]);}
      }
      return;
    }
    if(frame===7)return;
    if(frame<2){oval(0,0,3+frame*2,3+frame*2,C[5],false);}
    const r=3+frame*1.6;
    for(let i=0;i<6;i++){
      const a=i*Math.PI/3+.2,dr=r+(i%2)*1.5;
      const len=Math.max(1,3-frame*.4),x=Math.cos(a)*dr,y=Math.sin(a)*dr;
      const [x0,y0]=map(x,y),[x1,y1]=map(x+Math.cos(a)*len,y+Math.sin(a)*len);
      p.line(x0,y0,x1,y1,C[frame<3?4:2]);
      if(frame<3) {
        const [a,b]=map(x+1,y);p.px(a,b,C[3]);
      }
    }
    if(frame>0&&frame<5){
      for(let i=0;i<24;i++){
        const a=i/24*Math.PI*2;
        if((i+frame)%5===0)continue;
        dot(Math.cos(a)*r,Math.sin(a)*r*.8,C[frame<3?3:2]);
      }
    }
  }
  return {meta,draw};
}
