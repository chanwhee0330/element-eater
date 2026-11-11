"""원소 보관과 파괴 가능한 원천. 적 상성과 원천 내구도 규칙을 분리한다."""
from dataclasses import dataclass
import math

ELEMENTS = ('water', 'fire', 'wind', 'earth', 'lightning')
NAMES = {'neutral': '무속성', 'water': '물', 'fire': '불', 'wind': '바람', 'earth': '흙', 'lightning': '번개'}
BEATS = {'water': 'fire', 'fire': 'wind', 'wind': 'earth', 'earth': 'lightning', 'lightning': 'water'}
WEAKNESS = {target: attack for attack, target in BEATS.items()}
BREAK_TIMES = (.14, .17, .20)


@dataclass
class Source:
    id: str
    x: float
    y: float
    element: str = 'water'
    hp: int = 3
    phase: str = 'intact'
    age: float = 0
    break_elapsed: float = 0
    hit_time: float = 999

    @property
    def solid(self):
        return self.phase in ('intact', 'damaged1', 'damaged2', 'breaking')

    def hit(self, element):
        if self.phase not in ('intact', 'damaged1', 'damaged2'):
            return False
        self.hp = max(0, self.hp-(3 if WEAKNESS[self.element] == element else 1))
        self.hit_time = 0
        self.phase = 'breaking' if self.hp == 0 else 'damaged1' if self.hp == 2 else 'damaged2'
        return True

    def update(self, dt):
        if not math.isfinite(dt) or dt <= 0:
            return
        self.age += dt
        self.hit_time += dt
        if self.phase == 'breaking':
            self.break_elapsed += dt
            if self.break_elapsed >= sum(BREAK_TIMES):
                self.phase = 'orb'

    def frame(self):
        if self.phase in ('intact', 'damaged1', 'damaged2'):
            if self.element == 'wind':
                return int(self.age * 12) % 24 if self.phase == 'intact' else int(self.age * 4) % 8
            return int(self.age*8) % 8
        if self.phase == 'breaking':
            return 4 if self.break_elapsed < .14 else 5 if self.break_elapsed < .31 else 6
        return 7
