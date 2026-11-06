export const WEAKNESS = Object.freeze({water:'lightning',fire:'water',wind:'fire',earth:'wind',lightning:'earth'});
export const BREAK_DURATIONS = Object.freeze([140,170,200]);
export const ORB_DIAMETER = 96;

// A first rAF timestamp can predate script initialization. Never send a
// negative, non-finite or first-frame delta into the simulation.
export function frameDelta(previous, now) {
  if (previous === null || !Number.isFinite(previous) || !Number.isFinite(now)) return 0;
  return Math.max(0, Math.min(100, now - previous));
}

export class BreakableSource {
  constructor(element) {
    if (!(element in WEAKNESS)) throw new Error('Unknown source element');
    this.element = element;
    this.reset();
  }
  reset() {
    this.hp = 3;
    this.phase = 'intact';
    this.breakTime = 0;
    this.hitTime = 9999;
    this.age = 0;
    this.attackCount = 0;
    this.lastMatch = false;
  }
  attack(attackElement) {
    if (this.phase === 'breaking' || this.phase === 'orb') return false;
    this.lastMatch = WEAKNESS[this.element] === attackElement;
    this.hp = Math.max(0, this.hp - (this.lastMatch ? 3 : 1));
    this.hitTime = 0;
    this.attackCount++;
    if (this.hp === 0) {
      this.phase = 'breaking';
      this.breakTime = 0;
    } else {
      this.phase = this.hp === 2 ? 'damaged1' : 'damaged2';
    }
    return true;
  }
  update(dt) {
    if (!Number.isFinite(dt) || dt < 0) throw new Error('Invalid timestep');
    this.age += dt;
    this.hitTime += dt;
    if (this.phase === 'breaking') {
      this.breakTime += dt;
      if (this.breakTime >= BREAK_DURATIONS.reduce((a,b)=>a+b,0)) this.phase = 'orb';
    }
  }
  get frame() {
    if (this.phase === 'intact') return 0;
    if (this.phase === 'damaged1') return 1;
    if (this.phase === 'damaged2') return this.hitTime < 100 ? 2 : 3;
    if (this.phase === 'orb') return 7;
    let time = this.breakTime;
    for (let i=0;i<BREAK_DURATIONS.length;i++) {
      if (time < BREAK_DURATIONS[i]) return 4+i;
      time -= BREAK_DURATIONS[i];
    }
    return 7;
  }
}
