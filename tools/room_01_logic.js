/* 첫 방 HTML 배치 시연 전용. 공격·피해·Python/pico2d 전투는 구현하지 않는다. */
(function (root) {
  'use strict';
  function create(map) {
    return {map, player: {...map.playerSpawn, moving: false},
      enemies: map.enemies.map(e => ({...e, moving: false})),
      aggro: false, fall: 0, spike: false, safe: {...map.playerSpawn}, time: 0};
  }
  function tile(map, x, y) { return map.tiles[Math.floor(y)]?.[Math.floor(x)] ?? 4; }
  function inside(p, r) { return p.x >= r.x && p.x < r.x+r.width && p.y >= r.y && p.y < r.y+r.height; }
  function fits(map, x, y, safe) {
    const radius = .21;
    for (const dx of [-radius, radius]) for (const dy of [-radius, radius]) {
      const t = tile(map, x+dx, y+dy);
      if (t === 3 || (safe && t >= 3)) return false;
    }
    return true;
  }
  function move(state, actor, dx, dy, safe) {
    const before = {x: actor.x, y: actor.y};
    // 이동을 나눠 프레임 간 벽 관통을 막는다.
    const parts = Math.max(1, Math.ceil(Math.hypot(dx,dy)/.08));
    for (let i=0; i<parts; i++) {
      if (fits(state.map, actor.x+dx/parts, actor.y, safe)) actor.x += dx/parts;
      if (fits(state.map, actor.x, actor.y+dy/parts, safe)) actor.y += dy/parts;
    }
    actor.moving = Math.hypot(actor.x-before.x, actor.y-before.y) > .00001;
    if (actor.moving) actor.facing = Math.abs(dx)>Math.abs(dy) ? (dx>0?'right':'left') : (dy>0?'down':'up');
  }
  function field(map, player) {
    const gx=Math.floor(player.x), gy=Math.floor(player.y), distances=new Map();
    if (tile(map,gx,gy)>=3) return distances;
    const queue=[[gx,gy]];
    distances.set(`${gx},${gy}`,0);
    for (let i=0; i<queue.length; i++) {
      const [x,y]=queue[i], d=distances.get(`${x},${y}`);
      for (const [nx,ny] of [[x-1,y],[x+1,y],[x,y-1],[x,y+1]]) {
        const key=`${nx},${ny}`;
        if (tile(map,nx,ny)<3 && !distances.has(key)) {distances.set(key,d+1);queue.push([nx,ny]);}
      }
    }
    return distances;
  }
  function chase(state, enemy, distances, dt) {
    enemy.moving=false;
    if (Math.hypot(enemy.x-state.player.x,enemy.y-state.player.y)<.8) return;
    const x=Math.floor(enemy.x), y=Math.floor(enemy.y), d=distances.get(`${x},${y}`);
    if (d===undefined) return;
    let target;
    if (d===0) target=state.player;
    else {
      const options=[[x-1,y],[x+1,y],[x,y-1],[x,y+1]].filter(([nx,ny]) => distances.get(`${nx},${ny}`)===d-1);
      options.sort((a,b)=>Math.hypot(a[0]+.5-enemy.x,a[1]+.5-enemy.y)-Math.hypot(b[0]+.5-enemy.x,b[1]+.5-enemy.y));
      if (!options.length) return;
      const [nx,ny]=options[0];
      // 먼저 현재 칸의 진행 축 중앙에 맞춰 코너에 끼거나 대각선으로 벽을 가르지 않는다.
      target = nx!==x && Math.abs(enemy.y-(y+.5))>.035 ? {x:enemy.x,y:y+.5}
        : ny!==y && Math.abs(enemy.x-(x+.5))>.035 ? {x:x+.5,y:enemy.y}
        : {x:nx+.5,y:ny+.5};
    }
    const dx=target.x-enemy.x,dy=target.y-enemy.y,len=Math.hypot(dx,dy);
    if (len>0) {const step=Math.min(len,state.map.preview.meleeSpeed*dt);move(state,enemy,dx/len*step,dy/len*step,true);}
  }
  function update(state, input, dt) {
    if (!Number.isFinite(dt) || dt<=0) return state;
    dt=Math.min(dt,.05);state.time+=dt;
    const player=state.player;
    if (state.fall>0) {
      state.fall-=dt;player.moving=false;
      if (state.fall<=0) Object.assign(player,state.safe,{moving:false});
      return state;
    }
    let dx=(input.d?1:0)-(input.a?1:0),dy=(input.s?1:0)-(input.w?1:0);
    const len=Math.hypot(dx,dy)||1;
    move(state,player,dx/len*state.map.preview.playerSpeed*dt,dy/len*state.map.preview.playerSpeed*dt,false);
    const t=tile(state.map,player.x,player.y);
    state.spike=t===5;
    if(t===4) {state.fall=state.map.preview.fallSeconds;return state;}
    if(t<3 && fits(state.map,player.x,player.y,true)) state.safe={x:player.x,y:player.y,facing:player.facing};
    if(inside(player,state.map.aggroTrigger)) state.aggro=true;
    const distances=state.aggro?field(state.map,player):null;
    for(const enemy of state.enemies) {
      enemy.moving=false;
      if(state.aggro && enemy.behaviorType==='melee') chase(state,enemy,distances,dt);
    }
    return state;
  }
  const api={create,update,tile,inside};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  root.Room01Logic=api;
})(globalThis);
