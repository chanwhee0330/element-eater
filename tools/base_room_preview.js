/* 기본 맵의 크기 비교·이동 미리보기. 본게임 전투 구현은 포함하지 않는다. */
(() => {
  'use strict';

  function canStand(map, x, y) {
    const half = map.player.heightUnits / 2;
    const epsilon = 1e-8;
    for (let row = Math.floor(y - half + epsilon); row <= Math.floor(y + half - epsilon); row++) {
      for (let col = Math.floor(x - half + epsilon); col <= Math.floor(x + half - epsilon); col++) {
        if (row < 0 || col < 0 || row >= map.rows || col >= map.columns || map.solidTileIds.includes(map.tiles[row][col])) return false;
      }
    }
    return true;
  }

  function initialPlayer(map) {
    return { ...map.player.spawnCenter, direction: 'down', moving: false,
      lastSafe: { ...map.player.spawnCenter }, fallElapsed: null, flash: 0, spikeCooldown: 0, event: '' };
  }

  function feetTile(map, player) {
    const offset = (map.player.spritePivotPixelsTopLeft.y - map.player.referenceCenterPixelsTopLeft.y)
      * map.player.heightUnits / map.player.referenceSolidHeightPixels;
    return map.tiles[Math.floor(player.y + offset)]?.[Math.floor(player.x)] ?? 3;
  }

  function safeGround(map, player) {
    const half = map.player.heightUnits / 2 + .12;
    for (let row = Math.floor(player.y - half); row <= Math.floor(player.y + half); row++) {
      for (let col = Math.floor(player.x - half); col <= Math.floor(player.x + half); col++) {
        if (![0, 1, 2].includes(map.tiles[row]?.[col])) return false;
      }
    }
    return true;
  }

  function advance(map, player, input, dt) {
    const delta = Math.min(Math.max(dt, 0), 0.05);
    const next = { ...player, moving: false, flash: Math.max(0, (player.flash || 0) - delta),
      spikeCooldown: Math.max(0, (player.spikeCooldown || 0) - delta) };
    if (map.previewHazards && next.fallElapsed != null) {
      next.fallElapsed += delta;
      if (next.fallElapsed >= map.previewHazards.fallSeconds) {
        return { ...next, ...(next.lastSafe || map.player.spawnCenter), fallElapsed: null, event: '구멍 · 안전한 바닥으로 복귀' };
      }
      return next;
    }
    let dx = Number(Boolean(input.right)) - Number(Boolean(input.left));
    let dy = Number(Boolean(input.down)) - Number(Boolean(input.up));
    const magnitude = Math.hypot(dx, dy);
    if (magnitude) {
      const distance = map.player.previewSpeedUnitsPerSecond * delta;
      dx = dx / magnitude * distance;
      dy = dy / magnitude * distance;
      next.moving = true;
      next.direction = input.facing || player.direction;
      if (canStand(map, next.x + dx, next.y)) next.x += dx;
      if (canStand(map, next.x, next.y + dy)) next.y += dy;
    }
    if (map.previewHazards) {
      const tile = feetTile(map, next);
      if (tile === map.tileIds.pit) {
        next.fallElapsed = 0; next.moving = false; next.event = '구멍 · 추락 중';
      } else if (tile === map.tileIds.spikes && !next.spikeCooldown) {
        next.flash = map.previewHazards.spikeFlashSeconds;
        next.spikeCooldown = map.previewHazards.spikeRepeatSeconds;
        next.event = '가시 · 접촉 점멸 예시 (체력 피해 미구현)';
      }
      if (safeGround(map, next)) next.lastSafe = { x: next.x, y: next.y };
    }
    return next;
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { canStand, advance, initialPlayer, feetTile, safeGround };
  if (typeof document === 'undefined') return;

  const map = MAP_DATA;
  const sources = IMAGE_DATA;
  const canvas = document.getElementById('map');
  const ctx = canvas.getContext('2d');
  const grid = document.getElementById('grid');
  const marker = document.getElementById('marker');
  const status = document.getElementById('position');
  const terrain = document.getElementById('terrain');
  const defaultTerrain = terrain.textContent;
  const error = document.getElementById('error');
  const keys = new Map();
  const keyDirections = { KeyW: 'up', ArrowUp: 'up', KeyS: 'down', ArrowDown: 'down', KeyA: 'left', ArrowLeft: 'left', KeyD: 'right', ArrowRight: 'right' };
  let player = initialPlayer(map);
  let order = 0;
  let time = 0;
  let last = 0;
  let movementTime = 0;
  let world;
  let images;
  let lastStatus = '';
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function loadImage(data) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('이미지를 읽지 못했습니다.'));
      image.src = 'data:image/png;base64,' + data;
    });
  }

  function reset() {
    keys.clear();
    player = initialPlayer(map);
    movementTime = 0;
    canvas.focus({ preventScroll: true });
  }
  document.getElementById('center').addEventListener('click', reset);
  canvas.addEventListener('pointerdown', () => canvas.focus({ preventScroll: true }));
  canvas.addEventListener('keydown', event => {
    const direction = keyDirections[event.code];
    if (!direction) return;
    event.preventDefault();
    if (!event.repeat) keys.set(event.code, { direction, order: ++order });
  });
  canvas.addEventListener('keyup', event => {
    if (!keyDirections[event.code]) return;
    event.preventDefault();
    keys.delete(event.code);
  });
  canvas.addEventListener('blur', () => keys.clear());
  window.addEventListener('blur', () => keys.clear());

  function draw(now) {
    const dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
    last = now;
    time += dt;
    const pressed = [...keys.values()];
    const facing = pressed.reduce((latest, key) => key.order > (latest?.order || -1) ? key : latest, null)?.direction;
    const input = Object.fromEntries(['up', 'down', 'left', 'right'].map(direction => [direction, pressed.some(key => key.direction === direction)]));
    player = advance(map, player, { ...input, facing }, dt);
    movementTime = player.moving ? movementTime + dt : 0;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const size = Math.min(width - 52, height - 66);
    const left = (width - size) / 2 + 10;
    const top = 34;
    const unit = size / map.columns;
    ctx.drawImage(world, left, top, size, size);

    if (grid.checked) {
      for (let i = 0; i <= 30; i++) {
        ctx.beginPath();
        ctx.strokeStyle = i % 5 === 0 ? 'rgba(255,246,209,.5)' : 'rgba(255,246,209,.14)';
        ctx.lineWidth = i % 5 === 0 ? 1 : .5;
        ctx.moveTo(left + i * unit, top); ctx.lineTo(left + i * unit, top + size);
        ctx.moveTo(left, top + i * unit); ctx.lineTo(left + size, top + i * unit);
        ctx.stroke();
      }
    }
    ctx.fillStyle = '#cbd8c7';
    ctx.font = '12px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('30', left + size / 2, 19);
    ctx.textAlign = 'right';
    ctx.fillText('30', left - 10, top + size / 2 + 4);
    for (let i = 0; i <= 30; i += 5) {
      ctx.textAlign = i === 0 ? 'left' : i === 30 ? 'right' : 'center';
      ctx.fillText(String(i), left + i * unit, top + size + 21);
    }

    const px = left + player.x * unit;
    const py = top + player.y * unit;
    ctx.fillStyle = 'rgba(22,24,18,.3)';
    if (player.fallElapsed == null) {
      ctx.beginPath(); ctx.ellipse(px, py + unit * .44, unit * .3, unit * .09, 0, 0, Math.PI * 2); ctx.fill();
    }
    const state = player.moving ? 'walk' : 'idle';
    const fps = state === 'walk' ? 10 : 4;
    const age = state === 'walk' ? movementTime : reducedMotion ? 0 : time;
    const frame = Math.floor(age * fps) % 8;
    const row = ['down', 'left', 'right', 'up'].indexOf(player.direction);
    const sourceSize = map.player.spriteFrameSize;
    const falling = player.fallElapsed == null ? 0 : player.fallElapsed / map.previewHazards.fallSeconds;
    const scale = unit * map.player.heightUnits / map.player.referenceSolidHeightPixels * (1 - falling * .9);
    const center = map.player.referenceCenterPixelsTopLeft;
    ctx.save();
    ctx.globalAlpha = falling ? 1 - falling : player.flash > 0 && Math.floor(player.flash * 15) % 2 ? .35 : 1;
    ctx.drawImage(images[state], frame * sourceSize, row * sourceSize, sourceSize, sourceSize,
      px - center.x * scale, py - center.y * scale + falling * unit * .3, sourceSize * scale, sourceSize * scale);
    ctx.restore();

    if (marker.checked) {
      ctx.strokeStyle = '#fff4c8'; ctx.lineWidth = 1.25;
      ctx.strokeRect(px - unit / 2, py - unit / 2, unit, unit);
      const tx = Math.min(left + size - 37, Math.max(left + 38, px + Math.min(62, unit * 2.7)));
      const ty = Math.max(top + 21, py - 25);
      ctx.beginPath(); ctx.moveTo(px + unit / 2, py - unit / 2); ctx.lineTo(tx - 3, ty + 5); ctx.stroke();
      ctx.font = '500 12px system-ui, sans-serif'; ctx.textAlign = 'center';
      ctx.fillStyle = '#24342b'; ctx.fillRect(tx - 37, ty - 12, 74, 21);
      ctx.fillStyle = '#fff4c8'; ctx.fillText('플레이어 1', tx, ty + 2);
      for (const annotation of map.previewLabels || []) {
        const ax = left + annotation.anchor.x * unit, ay = top + annotation.anchor.y * unit;
        const lx = left + annotation.label.x * unit, ly = top + annotation.label.y * unit;
        ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(lx, ly); ctx.stroke();
        ctx.fillStyle = '#24342b'; ctx.fillRect(lx - 24, ly - 12, 48, 23);
        ctx.fillStyle = '#fff4c8'; ctx.fillText(annotation.text, lx, ly + 4);
      }
    }
    const nextStatus = `중심 위치 (${player.x.toFixed(1)}, ${player.y.toFixed(1)})`;
    if (nextStatus !== lastStatus) { status.textContent = nextStatus; lastStatus = nextStatus; }
    const message = player.event || defaultTerrain;
    if (terrain.textContent !== message) terrain.textContent = message;
    requestAnimationFrame(draw);
  }

  Promise.all(Object.entries(sources).map(async ([key, value]) => [key, await loadImage(value)]))
    .then(entries => {
      images = Object.fromEntries(entries);
      world = images.world;
      requestAnimationFrame(draw);
    }).catch(reason => { error.hidden = false; error.textContent = reason.message; });
})();
