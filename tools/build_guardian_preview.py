"""본게임 수호자 시트로 오프라인 애니메이션 미리보기를 만든다."""

import base64
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/sprites/boss/animation'
OUTPUT = ROOT / 'outputs/previews/guardian/guardian-actions.html'
FORMS = ('fire', 'wind', 'earth', 'lightning', 'water')
SIZE, COLUMNS = 320, 12


def read_form(element):
    clips, sprites, slots = {}, [], {}
    for atlas, names in (('animations', ('idle', 'attack', 'transform')), ('walk', None)):
        stem = ASSETS / f'guardian-{element}-{atlas}'
        spec = json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
        image = Image.open(ASSETS / spec['image']).convert('RGBA')
        for name in names or spec['clips']:
            meta = spec['clips'][name]
            clip = clips[name] = {'frames': [], 'ends': []}
            elapsed = 0
            for key in meta['frames']:
                frame = spec['frames'][key]
                box = frame['pico2dClip']
                x, y = box['left'], image.height - box['bottom'] - SIZE
                sprite = image.crop((x, y, x + SIZE, y + SIZE))
                pixels = sprite.tobytes()
                if pixels not in slots:
                    slots[pixels] = len(sprites)
                    sprites.append(sprite)
                clip['frames'].append(slots[pixels])
                elapsed += frame['duration']
                clip['ends'].append(elapsed)
            clip['events'] = {event['name']: clip['ends'][event['frame'] - 1] if event['frame'] else 0
                              for event in meta.get('events', ())}
    sheet = Image.new('RGBA', (SIZE * COLUMNS, SIZE * ((len(sprites) + COLUMNS - 1) // COLUMNS)))
    for index, sprite in enumerate(sprites):
        sheet.paste(sprite, (index % COLUMNS * SIZE, index // COLUMNS * SIZE))
    buffer = BytesIO()
    sheet.save(buffer, 'WEBP', quality=94, method=4)
    return {'clips': clips, 'image': base64.b64encode(buffer.getvalue()).decode('ascii')}


def read_effects():
    spec = json.loads((ASSETS / 'guardian-cast-effects.json').read_text(encoding='utf-8'))
    spec['image'] = base64.b64encode((ASSETS / spec['image']).read_bytes()).decode('ascii')
    return spec


PAGE = """<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>오원 수호자 동작 미리보기</title>
<style>
  :root { color-scheme: dark; font-family: system-ui, sans-serif; color: #f5eadc; background: #161319; }
  * { box-sizing: border-box; }
  main { width: min(100% - 32px, 970px); margin: 32px auto 56px; }
  h1 { font-size: clamp(1.5rem, 4vw, 2.25rem); margin: 0 0 22px; letter-spacing: -.05em; }
  .surface { background: #211d26; border: 1px solid #423643; border-radius: 15px; padding: 16px; }
  .controls { display: grid; gap: 12px; margin-bottom: 16px; }
  .row { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; }
  .caption { min-width: 66px; color: #d2bdab; font-size: .9rem; }
  button, select { font: inherit; color: inherit; background: #302733; border: 1px solid #544350;
    border-radius: 7px; padding: 7px 12px; }
  button { cursor: pointer; }
  button[aria-pressed='true'] { color: #211a1a; background: #efbb83; border-color: #efbb83; }
  button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid #ffd2a5; outline-offset: 2px; }
  [hidden] { display: none !important; }
  .viewer { display: grid; grid-template-columns: minmax(0, 2.4fr) minmax(0, 1fr); gap: 13px; }
  canvas { display: block; width: 100%; height: auto; border-radius: 10px; background: #1a1720; }
  .steps { display: grid; align-content: start; gap: 7px; color: #d2bdab; font-size: .9rem; }
  .steps canvas { max-height: 165px; object-fit: contain; }
  .effect-panel { align-self: start; color: #dccbbb; padding: 14px; border-radius: 10px; background: #1a1720; }
  .effect-panel p { font-size: .9rem; line-height: 1.6; }
  .effect-panel output { display: block; margin: 15px 0 6px; color: #ffd0a2; }
  input[type='checkbox'] { vertical-align: middle; accent-color: #efbb83; }
  .transport { justify-content: space-between; margin: 15px 0 8px; }
  output { color: #dcc7b6; font-variant-numeric: tabular-nums; }
  input[type='range'] { width: 100%; accent-color: #efbb83; }
  #message { min-height: 1.4em; color: #ebcab0; }
  @media (max-width: 620px) {
    .viewer { grid-template-columns: 1fr; }
    .steps { grid-template-columns: 1fr 1fr; }
    .steps strong { grid-column: 1 / -1; }
    .steps span { grid-row: 3; }
  }
</style>
<main>
  <h1>오원 수호자 동작 미리보기</h1>
  <section class="surface" aria-label="애니메이션 조작">
    <div class="controls">
      <div id="forms" class="row"><span class="caption">원소</span></div>
      <div id="directions" class="row"><span class="caption">방향</span></div>
      <div id="modes" class="row"><span class="caption">동작</span></div>
      <div id="target-row" class="row" hidden><label class="caption" for="target">변신 대상</label><select id="target"></select></div>
    </div>
    <div class="viewer">
      <canvas id="stage" width="520" height="420" aria-label="수호자 애니메이션"></canvas>
      <aside id="contacts" class="steps" aria-label="발 교대 자세">
        <strong>발 교대 자세</strong>
        <canvas id="step-a" width="320" height="300" aria-label="첫 발 교대 자세"></canvas><span id="label-a"></span>
        <canvas id="step-b" width="320" height="300" aria-label="반대 발 교대 자세"></canvas><span id="label-b"></span>
      </aside>
      <aside id="effects" class="effect-panel" aria-label="공격·변신 이펙트">
        <label><input id="show-effects" type="checkbox" checked> 이펙트 표시</label>
        <output id="effect-stage"></output>
        <p id="effect-detail"></p>
        <p>게임과 같은 투명 프레임을 보스 뒤와 앞에 합성합니다. 재생 막대를 움직여 발동 시점을 확인할 수 있습니다.</p>
      </aside>
    </div>
    <div class="row transport">
      <div class="row"><button id="play" type="button">일시정지</button><button id="prev" type="button" aria-label="이전 프레임">◀</button><button id="next" type="button" aria-label="다음 프레임">▶</button></div>
      <output id="time" for="seek"></output>
      <div class="row"><label for="speed">속도</label><select id="speed"><option value=".25">0.25×</option><option value=".5">0.5×</option><option value="1" selected>1×</option></select></div>
    </div>
    <input id="seek" type="range" min="0" step="1" value="0" aria-label="재생 위치">
    <div id="message" role="status">스프라이트를 불러오는 중입니다.</div>
  </section>
</main>
<script id="guardian-data" type="application/json">__DATA__</script>
<script id="guardian-effects" type="application/json">__EFFECTS__</script>
<script>
'use strict';
const data = JSON.parse(document.getElementById('guardian-data').textContent);
const fx = JSON.parse(document.getElementById('guardian-effects').textContent);
const names = {fire:'불', wind:'바람', earth:'흙', lightning:'번개', water:'물'};
const directions = {up:'↑ 위쪽 (뒷모습)', down:'↓ 아래쪽 (정면)', left:'← 왼쪽', right:'→ 오른쪽'};
const headings = {up:[0, -1], down:[0, 1], left:[-1, 0], right:[1, 0]};
const modes = {idle:'대기', walk:'걷기', attack:'공격', transform:'변신'};
const attacks = {
  fire:'두 줄기의 불꽃이 솟고, 발동 순간 주황 불씨와 바닥 문양이 펼쳐집니다.',
  wind:'초록 바람 띠가 몸을 감싸고, 발동 순간 밝은 돌풍과 바람 결이 퍼집니다.',
  earth:'돌 조각이 몸 주변에 모였다가 석가루와 함께 바깥으로 흩어집니다.',
  lightning:'보라색 전기가 몸 옆에서 갈라지고, 발동 순간 하얀 전광이 번집니다.',
  water:'푸른 물결이 몸을 감싸고, 발동 순간 하얀 포말과 물방울이 흩어집니다.'
};
const $ = id => document.getElementById(id);
const stage = $('stage'), context = stage.getContext('2d');
const images = {};
const effectImage = new Image();
let form = 'fire', direction = 'down', mode = 'attack', target = 'water';
let age = 0, playing = true, previous = 0, ready = false;
const walkSpeed = 1.65 * 36.8 / 1000;

function key(state) { return direction === 'down' ? state : state + '_' + direction; }
function timeline() {
  return data[form].clips[mode === 'transform' ? 'transform' : key(mode)];
}
function playbackLength(clip) {
  return clip.ends.at(-1) * (mode === 'walk' ? 2 : 1);
}
function indexAt(clip, at) {
  const index = clip.ends.findIndex(end => end > at);
  return index < 0 ? clip.frames.length - 1 : index;
}
function sprite(ctx, element, clipName, index, x, y, scale = 1, opacity = 1) {
  const slot = data[element].clips[clipName].frames[index];
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  ctx.globalAlpha = opacity;
  ctx.drawImage(images[element], slot % 12 * 320, Math.floor(slot / 12) * 320, 320, 320,
    x - 160 * scale, y - 264 * scale, 320 * scale, 320 * scale);
  ctx.restore();
}
function effectFrame(at, event, duration) {
  if (at < event) return Math.min(fx.event - 1, Math.floor(at / event * fx.event));
  const tail = fx.count - fx.event;
  return fx.event + Math.min(tail - 1, Math.floor((at - event) / (duration - event) * tail));
}
function cast(element, layer, index, x, y) {
  if (!$('show-effects').checked) return;
  const slot = fx.clips[element][mode][layer] + index;
  const size = fx.cell, scale = fx.scale;
  context.imageSmoothingEnabled = false;
  context.drawImage(effectImage, slot % fx.columns * size, Math.floor(slot / fx.columns) * size, size, size,
    x - fx.pivot[0] * scale, y - fx.pivot[1] * scale, size * scale, size * scale);
}
function ground(ctx, canvas, x, y, large) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = '#443646';
  ctx.beginPath();
  if (large && mode === 'walk') {
    const [dx, dy] = headings[direction];
    const centerX = canvas.width / 2;
    const edge = dx ? 30 : 110;
    for (let offset = -84; offset <= 84; offset += 21) {
      const markX = centerX + offset * dx, markY = 315 + offset * dy;
      ctx.moveTo(markX - dy * edge, markY - dx * edge);
      ctx.lineTo(markX - dy * (edge - 12), markY - dx * (edge - 12));
      ctx.moveTo(markX + dy * (edge - 12), markY + dx * (edge - 12));
      ctx.lineTo(markX + dy * edge, markY + dx * edge);
    }
  } else {
    ctx.moveTo(x - 120, y); ctx.lineTo(x + 120, y);
  }
  ctx.stroke();
  ctx.fillStyle = '#100d16';
  ctx.beginPath(); ctx.ellipse(x, y + 1, large ? 72 : 45, large ? 10 : 6, 0, 0, Math.PI * 2); ctx.fill();
}
function ease(n) { const t = Math.max(0, Math.min(1, n)); return t * t * (3 - 2 * t); }
function draw() {
  if (!ready) return;
  const clip = timeline();
  const length = playbackLength(clip);
  const [dx, dy] = headings[direction];
  const movement = mode === 'walk' ? (age - length / 2) * walkSpeed : 0;
  const x = stage.width / 2 + dx * movement, y = 315 + dy * movement;
  ground(context, stage, x, y, true);
  const clipAge = mode === 'walk' ? age % clip.ends.at(-1) : age;
  const index = indexAt(clip, clipAge);
  const event = clip.events.elementChange ?? clip.events.release;
  const hasEffect = mode === 'attack' || mode === 'transform';
  const effectIndex = hasEffect ? effectFrame(age, event, length) : 0;
  const effectElement = mode === 'transform' && age >= event ? target : form;
  if (hasEffect) {
    cast(effectElement, 'behind', effectIndex, x, y);
    const phase = age < event ? '예고 · 에너지 모으기' : effectIndex < fx.event + 3
      ? (mode === 'transform' ? '원소 전환 · 섬광' : '공격 발동 · 방출') : '잔광 · 입자 흩어짐';
    $('effect-stage').value = `${phase} · ${(event / 1000).toFixed(2)}초에 발동`;
  }
  if (mode === 'transform') {
    const switchAt = clip.events.elementChange;
    const fade = ease((age - switchAt + 200) / 460);
    const charge = key('transform');
    const arriving = direction === 'down' ? 'idle' : key('arrive');
    const chargeAge = Math.min(age, clip.ends[5] - 1);
    const arrivalAge = Math.max(0, age - switchAt + (direction === 'down' ? 0 : 200));
    sprite(context, form, charge, indexAt(data[form].clips[charge], chargeAge), x, y, 1, 1 - fade);
    sprite(context, target, arriving, indexAt(data[target].clips[arriving], arrivalAge), x, y, 1, fade);
  } else {
    const opacity = playing && mode === 'walk' ? Math.min(1, age / 80, (length - age) / 80) : 1;
    sprite(context, form, key(mode), index, x, y, 1, opacity);
  }
  if (hasEffect) cast(effectElement, 'front', effectIndex, x, y);
  $('seek').value = Math.min(age, length - 1);
  $('time').value = `${index + 1} / ${clip.frames.length} 프레임 · ${(age / 1000).toFixed(2)}초`;
}
function drawContacts() {
  $('contacts').hidden = mode !== 'walk';
  if (!ready || mode !== 'walk') return;
  const side = direction === 'left' || direction === 'right';
  const poses = side ? [0, 6] : [3, 9];
  ['a', 'b'].forEach((id, index) => {
    const canvas = $('step-' + id), ctx = canvas.getContext('2d');
    ground(ctx, canvas, 160, 245, false);
    sprite(ctx, form, key('walk'), poses[index], 160, 245, .78);
    $('label-' + id).textContent = `${poses[index] + 1}프레임`;
  });
}
function update() {
  for (const id of ['forms', 'directions', 'modes']) {
    const value = id === 'forms' ? form : id === 'directions' ? direction : mode;
    for (const button of $(id).querySelectorAll('button')) button.setAttribute('aria-pressed', button.value === value);
  }
  $('target-row').hidden = mode !== 'transform';
  $('effects').hidden = mode !== 'attack' && mode !== 'transform';
  $('target').replaceChildren(...Object.keys(names).filter(value => value !== form).map(value => new Option(names[value], value)));
  if (target === form) target = Object.keys(names).find(value => value !== form);
  $('target').value = target;
  $('effect-detail').textContent = mode === 'transform'
    ? `${names[form]} 원소의 문양이 충전되고, 전환 순간 ${names[target]} 원소의 빛과 입자로 바뀝니다.` : attacks[form];
  $('seek').max = playbackLength(timeline()) - 1;
  age = 0;
  drawContacts();
  draw();
}
function buttons(id, options, change) {
  for (const [value, label] of Object.entries(options)) {
    const button = document.createElement('button');
    button.type = 'button'; button.value = value; button.textContent = label;
    button.onclick = () => { change(value); update(); };
    $(id).append(button);
  }
}
function play(value) { playing = value; $('play').textContent = value ? '일시정지' : '재생'; draw(); }
function step(offset) {
  const clip = timeline(), cycle = clip.ends.at(-1), count = clip.frames.length;
  const totalFrames = count * (mode === 'walk' ? 2 : 1);
  const index = Math.floor(age / cycle) * count + indexAt(clip, age % cycle);
  const next = (index + offset + totalFrames) % totalFrames;
  const nextFrame = next % count;
  age = Math.floor(next / count) * cycle + (nextFrame ? clip.ends[nextFrame - 1] : 0);
  play(false);
}
buttons('forms', names, value => form = value);
buttons('directions', directions, value => direction = value);
buttons('modes', modes, value => mode = value);
$('target').onchange = event => { target = event.target.value; update(); };
$('show-effects').onchange = draw;
$('play').onclick = () => play(!playing);
$('prev').onclick = () => step(-1);
$('next').onclick = () => step(1);
$('seek').oninput = event => { age = Number(event.target.value); play(false); };
function tick(now) {
  if (playing && previous) {
    age = (age + Math.min(now - previous, 50) * Number($('speed').value)) % playbackLength(timeline());
    draw();
  }
  previous = now;
  requestAnimationFrame(tick);
}
update();
function loadSprite(image, source) {
  return new Promise((resolve, reject) => {
    image.onload = resolve; image.onerror = reject;
    image.src = source;
  });
}
const loads = Object.entries(data).map(([element, entry]) => {
  const image = images[element] = new Image();
  return loadSprite(image, 'data:image/webp;base64,' + entry.image);
});
loads.push(loadSprite(effectImage, 'data:image/png;base64,' + fx.image));
Promise.all(loads).then(() => {
  ready = true; $('message').textContent = '';
  update(); requestAnimationFrame(tick);
}).catch(() => { $('message').textContent = '내장 스프라이트를 읽지 못했습니다.'; });
</script>
</html>
"""


def main():
    data = {element: read_form(element) for element in FORMS}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    page = PAGE.replace('__DATA__', json.dumps(data, separators=(',', ':')))
    OUTPUT.write_text(page.replace('__EFFECTS__', json.dumps(read_effects(), separators=(',', ':'))),
                      encoding='utf-8')


if __name__ == '__main__':
    main()
