/* 실제 미리보기 갱신 함수를 사용한 구역 진입/추격/지형 회귀 검사. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const logic=require('./room_01_logic.js'),root=path.resolve(__dirname,'..');
const map=JSON.parse(fs.readFileSync(path.join(root,'assets/maps/room-01/room-01.json'),'utf8'));
function tick(s,input,n){for(let i=0;i<n;i++)logic.update(s,input,1/60);}
let s=logic.create(map),initial=JSON.stringify(s.enemies);
tick(s,{},120);assert.equal(s.aggro,false);assert.equal(JSON.stringify(s.enemies),initial);
tick(s,{w:true},140);assert.equal(s.aggro,false);assert.equal(JSON.stringify(s.enemies),initial);
tick(s,{w:true},20);assert.equal(s.aggro,true);assert(s.enemies.filter(e=>e.moving).length===2);
assert(s.enemies.filter(e=>e.behaviorType==='ranged').every(e=>e.x===map.enemies.find(a=>a.id===e.id).x));
// 위쪽 큰 영역에 한번 들어간 뒤 연결로로 물러나도 추격은 지속한다.
tick(s,{s:true},50);assert.equal(s.aggro,true);tick(s,{},450);
assert(s.enemies.filter(e=>e.behaviorType==='melee').every(e=>Math.hypot(e.x-s.player.x,e.y-s.player.y)<1));
// 중앙 벽 건너편으로 목표를 옮겨 두 근접 적이 벽을 우회하는지 검사한다.
s=logic.create(map);s.player.x=10;s.player.y=4.5;
for(let i=0;i<1800;i++){
  logic.update(s,{},1/60);
  for(const e of s.enemies)assert(logic.tile(map,e.x,e.y)<3,'적이 벽·구멍·가시를 통과함');
}
assert(s.enemies.filter(e=>e.behaviorType==='melee').every(e=>Math.hypot(e.x-s.player.x,e.y-s.player.y)<1));
// 플레이어에게 벽은 충돌, 낭떠러지는 낙하로 처리된다.
s=logic.create(map);s.player.x=10;s.player.y=8.5;tick(s,{w:true},60);assert(s.player.y>=8.2);
s=logic.create(map);s.player.y=14;s.safe={...map.playerSpawn};tick(s,{a:true},22);assert(s.fall>0);
tick(s,{},60);assert.equal(s.fall<=0,true);assert.equal(logic.tile(map,s.player.x,s.player.y)<3,true);
const before=JSON.stringify(s);for(const dt of [0,-1,NaN,Infinity])logic.update(s,{w:true},dt);assert.equal(JSON.stringify(s),before);
const html=fs.readFileSync(path.join(root,'outputs/previews/room-01/preview.html'),'utf8');
new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
assert(!/src="(?!data:)/.test(html),'상대 이미지 의존성');
console.log('PASS: entry trigger, idle before entry, latched chase, wall detour, wall collision, fall recovery, timestep guards, standalone HTML syntax');
