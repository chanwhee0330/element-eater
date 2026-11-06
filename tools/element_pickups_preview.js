/* PNG/JSON 프레임을 동일한 시간 기준으로 재생한다. 네트워크 요청 없음. */
function pickupFrame(element, seconds) {
  return Math.floor(Math.max(0, seconds) * element.fps + 1e-9) % element.frameCount;
}
function pickupSources(catalog, seconds, items) {
  const size = catalog.frameSize.w;
  return items.map(item => {
    const element = catalog.elements[item.element];
    return { ...item, elementData: element, sx: pickupFrame(element, seconds + item.phase) * size,
      sy: element.atlasRow * size, sourceSize: size };
  });
}
if (typeof module !== 'undefined') module.exports = { pickupFrame, pickupSources };
if (typeof document !== 'undefined') {
  (async () => {
    const data = JSON.parse(document.getElementById('assets').textContent);
    const images = {};
    await Promise.all(['atlas', 'background', 'hud', 'hero'].map(name => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => { images[name] = image; resolve(); };
      image.onerror = () => reject(new Error(`${name} 이미지를 읽지 못했습니다.`));
      image.src = data[name];
    })));
    const map = document.getElementById('map').getContext('2d');
    const gallery = document.getElementById('gallery').getContext('2d');
    const status = document.getElementById('status');
    const play = document.getElementById('play');
    const speed = document.getElementById('speed');
    let playing = true, seconds = 0, last = null;
    function shadow(ctx, x, y, radius) {
      ctx.fillStyle = 'rgba(26,27,20,0.294)';
      ctx.beginPath(); ctx.ellipse(x, y - 1, radius, 5, 0, 0, Math.PI * 2); ctx.fill();
    }
    function draw() {
      const size = data.catalog.frameSize.w;
      const hero = data.heroDraw;
      const items = pickupSources(data.catalog, seconds, data.items);
      map.clearRect(0, 0, 1280, 720);
      map.drawImage(images.background, 0, 0);
      for (const item of items) shadow(map, item.groundX, item.groundY, Math.min(29, 80 * item.elementData.heightUnits * .28));
      shadow(map, hero.groundX, hero.groundY, 25);
      const subjects = [...items, { element: 'hero', groundY: hero.groundY }].sort((a, b) => a.groundY - b.groundY);
      for (const item of subjects) {
        if (item.element === 'hero') {
          const frame = pickupFrame({ fps: 4, frameCount: 8 }, seconds);
          map.drawImage(images.hero, frame * hero.frameSize, hero.row * hero.frameSize, hero.frameSize, hero.frameSize,
            hero.at[0], hero.at[1], hero.size[0], hero.size[1]);
        } else {
          const destSize = Math.round(size * item.scale);
          map.drawImage(images.atlas, item.sx, item.sy, size, size, item.at[0], item.at[1], destSize, destSize);
        }
      }
      map.drawImage(images.hud, 0, 0);
      gallery.fillStyle = '#14251e'; gallery.fillRect(0, 0, 1280, 350);
      gallery.textBaseline = 'middle'; gallery.textAlign = 'left'; gallery.fillStyle = '#f3edd4';
      gallery.font = '22px "Malgun Gothic", sans-serif'; gallery.fillText('맵 원소 · 대기 애니메이션', 30, 32);
      Object.values(data.catalog.elements).forEach((element, index) => {
        const x = 20 + index * 252;
        gallery.fillStyle = '#23382d'; gallery.strokeStyle = '#526746';
        gallery.beginPath(); gallery.roundRect(x, 58, 232, 272, 16); gallery.fill(); gallery.stroke();
        gallery.textAlign = 'center'; gallery.fillStyle = '#f3edd4'; gallery.font = '21px "Malgun Gothic", sans-serif';
        gallery.fillText(`${element.name} · ${element.object}`, x + 116, 83);
        gallery.fillStyle = '#b4c7a5'; gallery.font = '15px "Malgun Gothic", sans-serif';
        gallery.fillText(`${element.frameCount}프레임 · ${element.fps}fps`, x + 116, 303);
        gallery.drawImage(images.atlas, pickupFrame(element, seconds) * size, element.atlasRow * size, size, size, x + 24, 98, 184, 184);
      });
      status.textContent = `${seconds.toFixed(2)}초 · ${playing ? '재생 중' : '정지'}`;
      play.textContent = playing ? '일시정지' : '재생';
      play.setAttribute('aria-pressed', String(!playing));
    }
    function tick(now) {
      if (last !== null && playing) seconds += Math.min(.1, (now - last) / 1000) * Number(speed.value);
      last = now; draw(); requestAnimationFrame(tick);
    }
    play.addEventListener('click', () => { playing = !playing; draw(); });
    document.getElementById('step').addEventListener('click', () => { playing = false; seconds += 1 / 12; draw(); });
    document.getElementById('reset').addEventListener('click', () => { seconds = 0; draw(); });
    document.addEventListener('visibilitychange', () => { last = null; });
    draw(); requestAnimationFrame(tick);
  })().catch(error => { document.getElementById('error').textContent = error.message; });
}
