// Element Eater original character; rendered with the pixelfx Painter API.
// No stock character or third-party sprite artwork is used.
export const DIRECTIONS = ['down', 'left', 'right', 'up'];
export const FRAME_SIZE = 64;
export const PIVOT = [32, 58];
export const FRAME_COUNT = 8;

// Small, hard-edged color clusters, lit from the upper left.
const BODY = ['#493628', '#a17a49', '#d8b774', '#f0d897', '#fff0bc', '#fff8db'];
const LEAF = ['#243d2c', '#35603b', '#508441', '#83b54b', '#bfd65b'];
const FACE = { dark: '#382922', tongue: '#d8674e', tongueLight: '#f18b66', blush: '#eda486' };
const TAU = Math.PI * 2;

function insidePoly(x, y, pts) {
  let hit = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[j];
    if ((ay > y) !== (by > y) && x < (bx - ax) * (y - ay) / (by - ay) + ax) hit = !hit;
  }
  return hit;
}

export function makeHero(core, state = 'walk', direction = 'down') {
  if (!['idle', 'walk'].includes(state) || !DIRECTIONS.includes(direction)) throw new Error('Unknown hero animation');
  const { hex, fit } = core;
  const fps = state === 'idle' ? 4 : 10;
  const meta = {
    name: `Element Eater ${state} ${direction}`,
    desc: `Ivory leaf-eared hero facing ${direction}: ${state === 'idle' ? 'gentle breathing and delayed leaf sway' : 'alternating planted feet, counter-swinging hands and springy leaves'}.`,
    tags: ['element-eater', 'hero', state, direction, 'loop'],
    size: [64, 64], origin: [...PIVOT], duration: FRAME_COUNT / fps,
    fps, loop: true, bg: 'dark', options: { palette: BODY, seed: 1 },
  };
  const L = LEAF.map(hex), F = Object.fromEntries(Object.entries(FACE).map(([k, v]) => [k, hex(v)]));

  function draw(p, time, o) {
    const C = fit(o.palette ?? BODY, 6);
    const frame = Math.floor(((time % meta.duration) / meta.duration) * 8 + 1e-6) % 8;
    const phase = frame / 8 * TAU, walking = state === 'walk';
    const stride = walking ? Math.sin(phase) : 0;
    const bob = walking ? [0, -1, -2, -1, 0, -1, -2, -1][frame] : [0, 0, -1, -1, -1, -1, 0, 0][frame];
    const sway = walking ? Math.round(Math.sin(phase) * 0.65) : 0;
    const side = direction === 'left' || direction === 'right';
    // Side silhouettes mirror; highlights remain in world-space upper-left.
    const facing = direction === 'left' ? -1 : 1;
    const tr = (x, y) => [Math.round(x * (side ? facing : 1) + sway), Math.round(y + bob)];
    const bodyRX = side ? 15.5 : 17.5;
    function insideBody(x, y) {
      const [X,Y] = tr(0,-20);
      return ((x+0.5-X)/bodyRX)**2 + ((y+0.5-Y)/16.5)**2 <= 1;
    }
    function shape(cx, cy, rx, ry, palette, shade = true, moving = true, clipBody = false) {
      const [X, Y] = moving ? tr(cx, cy) : [cx, cy];
      for (let y = Math.floor(Y - ry); y <= Math.ceil(Y + ry); y++) {
        for (let x = Math.floor(X - rx); x <= Math.ceil(X + rx); x++) {
          const dx = (x + 0.5 - X) / rx, dy = (y + 0.5 - Y) / ry;
          if (dx * dx + dy * dy > 1) continue;
          if (clipBody && !insideBody(x,y)) continue;
          const edge = ((x + 0.5 - X) / (rx - 1.2)) ** 2 + ((y + 0.5 - Y) / (ry - 1.2)) ** 2 > 1;
          let k = edge ? 0 : !shade ? palette.length - 1 : dy > 0.62 || dx > 0.72 ? 2 : dy > 0.22 || dx > 0.46 ? 3 : 4;
          if (!edge && shade && ((dx + 0.34) / 0.66) ** 2 + ((dy + 0.38) / 0.64) ** 2 < 1) k = 5;
          p.px(x, y, palette[Math.min(k, palette.length - 1)]);
        }
      }
    }
    function line(points, c, moving = true) {
      const v = moving ? points.map(([x, y]) => tr(x, y)) : points;
      p.polyline(v, c);
    }
    function block(x, y, w, h, c) {
      for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) {
        const [X, Y] = tr(x + xx, y + yy); p.px(X, Y, c);
      }
    }
    function leaf(pts, vein, bias = 0) {
      const v = pts.map(([x, y]) => tr(x, y));
      const minX = Math.floor(Math.min(...v.map(q => q[0]))), maxX = Math.ceil(Math.max(...v.map(q => q[0])));
      const minY = Math.floor(Math.min(...v.map(q => q[1]))), maxY = Math.ceil(Math.max(...v.map(q => q[1])));
      for (let y = minY; y <= maxY; y++) for (let x = minX; x <= maxX; x++) {
        if (!insidePoly(x + 0.5, y + 0.5, v)) continue;
        const edge = [[1,0],[-1,0],[0,1],[0,-1]].some(([a,b]) => !insidePoly(x + 0.5 + a, y + 0.5 + b, v));
        const u = (y - minY) / (maxY - minY), q = (x - minX) / (maxX - minX);
        p.px(x, y, L[edge ? 0 : u < 0.22 && q < 0.7 ? 4 : u < 0.52 + bias ? 3 : u < 0.78 ? 2 : 1]);
      }
      line(vein, L[1]);
      line(vein.map(([x,y]) => [x - 1, y - 1]), L[3]);
    }

    // Far limbs are drawn first, with grounded feet independent of body bounce.
    const foot = (x, y, near = true) => shape(x, y - 3, side ? 5 : 4.5, 4, near ? C : [C[0], C[1], C[2], C[2], C[3], C[4]], true, false);
    if (side) {
      foot(Math.round((-5 + stride * 4) * facing), -Math.round(Math.max(0, -stride) * 3), false);
      shape(-10, -14 - stride * 2, 4, 5, C);
    } else {
      foot(-7 + Math.round(stride), -Math.round(Math.max(0, stride) * 3));
      foot(7 + Math.round(stride), -Math.round(Math.max(0, -stride) * 3));
      shape(-17, -14 + stride * 2, 4.3, 5, C);
      shape(17, -14 - stride * 2, 4.3, 5, C);
    }

    // Two asymmetric leaves keep the silhouette identifiable at a glance.
    const lag = walking ? Math.round(Math.sin(phase - Math.PI / 3) * 2) : [0, 0, 1, 1, 1, 0, -1, -1][frame];
    const rear = direction === 'up';
    const left = [[-3,-32],[-10,-38],[-16+lag,-47],[-16+lag,-53],[-12+lag,-55],[-6,-52],[-1,-46],[-1,-38]];
    const right = [[-1,-33],[1,-41],[8,-47-lag],[17,-47-lag],[22,-43-lag],[22,-39],[17,-35],[7,-34]];
    leaf(left, [[-3,-34],[-5,-41],[-11+lag,-49]], 0.05);
    leaf(right, [[0,-34],[5,-40],[15,-43-lag]], -0.1);
    line([[-3,-34],[-2,-29]], L[1]);
    line([[0,-34],[0,-30]], L[2]);

    // Round body, creamy highlight and warm stepped lower-right shadow.
    shape(0, -20, bodyRX, 16.5, C);
    // Small forehead reflection, drawn as a cluster rather than scattered pixels.
    if (!rear) { block(-8, -29, 4, 1, C[5]); block(-9, -28, 3, 1, C[5]); }

    if (!rear) {
      if (side) {
        // Profile: one happy eye, a large mouth at the leading edge, near hand below the cheek.
        line([[6,-25],[7,-27],[9,-27],[10,-25]], F.dark);
        line([[6,-24],[6,-26],[8,-28],[10,-26],[10,-24]], F.dark);
        line([[7,-25],[8,-26],[9,-25]], F.dark);
        shape(8.5, -17, 4.8, 5.8, [F.dark], false, true, true);
        shape(9, -14, 2.8, 1.8, [F.tongue], false, true, true);
        block(7, -15, 3, 1, F.tongueLight);
        shape(1, -19, 2.8, 1.4, [F.blush], false);
      } else {
        for (const sx of [-1, 1]) {
          line([[sx*5,-25],[sx*6,-27],[sx*8,-27],[sx*10,-25]], F.dark);
          line([[sx*5,-24],[sx*5,-26],[sx*7,-28],[sx*9,-27],[sx*10,-25]], F.dark);
          line([[sx*6,-25],[sx*7,-26],[sx*9,-25]], F.dark);
          shape(sx * 12, -20, 2.8, 1.4, [F.blush], false);
        }
        const inhale = !walking && (frame===3 || frame===4) ? 1 : 0;
        shape(0, -16, 7.3, 6.3 + inhale, [F.dark], false);
        shape(0, -13 + inhale, 4, 2.2, [F.tongue], false);
        block(-2, -14 + inhale, 4, 1, F.tongueLight);
      }
    }
    if (side) {
      shape(-2 - stride * 2, -11 + stride, 4.6, 4.8, C);
      foot(Math.round((5 - stride * 4) * facing), -Math.round(Math.max(0, stride) * 3));
    }
  }
  return { meta, draw };
}
