import { hex, rng } from "../../core/index.js";

const ramps = {
  garden: ["#282337", "#343047", "#454057", "#57536a", "#736e85", "#9b91a8"],
  quarry: ["#282234", "#393044", "#4b3f55", "#5c5066", "#796983", "#a98c70"],
};

export function hardware(room, part, active = false) {
  const isGate = part === "gate" || part === "exit";
  const size = part === "gate" ? [192, 42] : part === "exit" ? [80, 108] : [128, 96];
  const palette = ramps[room];
  const meta = {
    name: `${room} ${part}`,
    desc: "Stone and iron hardware for the garden sluice or quarry haulway.",
    tags: ["prop", "hardware"],
    size, origin: [0, 0],
    duration: active ? 4/3 : 1,
    loop: true, fps: active ? 9 : 1,
    options: { palette, seed: 7 },
  };

  function draw(p, t, o) {
    const c = o.palette.map(hex);
    const random = rng(o.seed);
    const rect = (x, y, w, h, level) => p.rect(x, y, w, h, c[level]);
    const line = (x, y, ex, ey, level) => p.line(x, y, ex, ey, c[level]);
    const poly = (points, level) => p.poly(points, c[level]);
    if (isGate) {
      const [w, h] = size;
      const arch = part === "exit";
      const start = arch ? 1 : 2;
      const end = h - (arch ? 1 : 2);
      const width = room === "garden" ? 29 : 42;
      for (let y = start; y < end; y++) {
        const radius = w/2-2;
        const inset = arch && y < radius ? Math.ceil(w/2-Math.sqrt(radius**2-(radius-y)**2)) : 0;
        const elevation = y < start+3 ? 4 : y >= end-6 ? 1 : 3;
        for (let x = inset; x < w-inset; x++) {
          const seam = (x + Math.floor(y/13)*11) % width;
          const tone = seam === 0 || y % 13 === 0 || x === w/2 ? elevation-1 : elevation;
          if (arch) {
            const bar = x % 9;
            if (bar < 3) p.px(x, y, hex(["#42333a", "#b08b64", "#7c5f56"][bar]));
          } else {
            p.px(x, y, c[random.next() < .018 && tone > 0 ? tone-1 : tone]);
          }
        }
      }
      const rails = arch ? [Math.round(h*.54), end-10]
        : room === "garden" ? [end-10] : [Math.round(h*.34), end-10];
      for (const y of rails) {
        rect(0, y, w, 5, 1);
        line(0, y, w-1, y, 4);
        for (let x = 7; x < w-1; x += 18) rect(x, y+2, 2, 2, 5);
      }
      return;
    }

    const garden = room === "garden";
    const pump = part === "pump";
    const x = pump ? 28 : garden ? 36 : 40;
    const r = 128-x;
    poly([[x-4,68],[r+4,68],[r+8,79],[r,87],[x,87],[x-8,79]],0);
    poly([[x+6,54],[r-6,54],[r,62],[r,78],[x,78],[x,62]],2);
    poly([[x+6,54],[r-6,54],[r,62],[r-5,71],[x+5,71],[x,62]],3);
    line(x+6,55,r-6,55,4);
    for (let i = 0; i < 18; i++) {
      const px = x+5 + Math.floor(random.next()*(r-x-10));
      const py = 57 + Math.floor(random.next()*12);
      line(px,py,px+2,py,random.next() < .5 ? 2 : 4);
    }

    if (pump) {
      rect(42,45,44,21,1);
      rect(53,42,22,19,2);
      rect(57,46,14,10,active ? 4 : 0);
      for (const [post, cap] of [[42,22],[86,25]]) {
        rect(post-4,cap,8,54-cap,1);
        for (let y = cap+4; y < 51; y += 5) {
          rect(post-6,y,12,3,3);
          line(post-6,y,post+5,y,5);
        }
        rect(post-5,cap,10,4,4);
      }
      const frame = Math.floor(t*9+1e-6)%12;
      if (active && frame % 4 !== 3) {
        const arc = [[42,23],[52,19+frame%3],[60,25],[71,19-frame%4],[86,26]];
        p.polyline(arc,hex("#78a8a1"));
        p.line(arc[1][0],arc[1][1],arc[2][0],arc[2][1],hex("#e2ece0"));
        p.px(42,23,hex("#d7e8dc"));
        p.px(86,26,hex("#d7e8dc"));
        p.px(62+frame%5,13+frame%4,hex("#82b8ae"));
        p.rect(59,47,10,7,hex("#93c9bb"));
      }
      return;
    }

    const hinge = garden ? 64 : 61;
    rect(hinge-10,49,20,20,1);
    line(hinge-9,50,hinge+8,50,4);
    const frame = Math.floor(t*9+1e-6)%12;
    const turn = active ? Math.min(1,frame/6) : 0;
    const hand = [hinge+Math.round(-18+36*turn), garden ? 29 : 32];
    p.beam(hinge,58,...hand,garden ? 5 : 6,c[0]);
    line(hinge,56,...hand,5);
    if (garden) {
      p.beam(hand[0]-5,hand[1],hand[0]+5,hand[1],4,c[3]);
      line(hand[0]-4,hand[1]-1,hand[0]+4,hand[1]-1,5);
    } else {
      rect(hand[0]-5,hand[1]-5,11,10,1);
      rect(hand[0]-4,hand[1]-4,9,2,5);
    }
    rect(hinge-3,55,7,6,4);
  }
  return { meta, draw };
}
