"""첫 방의 이동·추격·무속성 전투. 렌더러 없이도 검사 가능한 게임 상태."""
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import json
import math
from .combat import CombatTuning, Projectile, Feedback
from .elements import ELEMENTS, BEATS, Source

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / 'assets/maps/room-01/room-01.json'
STAGES = {n: ROOT / f'assets/maps/room-{n:02d}/room-{n:02d}.json' for n in (1, 2)}


@dataclass
class Actor:
    x: float
    y: float
    facing: str
    kind: str = 'hero'
    name: str = '플레이어'
    moving: bool = False
    animation_time: float = 0
    falling: float = 0
    active: bool = True
    hp: int = 100
    max_hp: int = 100
    hit_flash: float = 0
    invulnerable: float = 0
    attack_elapsed: float = -1
    attack_cooldown: float = 0
    attack_facing: str = 'up'
    attack_direction: tuple = (0, -1)
    attack_emitted: bool = False
    knockback: tuple = (0, 0)
    knockback_left: float = 0
    element: str = 'neutral'
    attack_element: str = 'neutral'

    def animate(self, dt, was_moving):
        self.animation_time = self.animation_time + dt if was_moving == self.moving else 0


class Room:
    radius = .21

    def __init__(self, path=MAP_PATH, *, stage=None):
        self.map_path = STAGES[stage] if stage is not None else Path(path)
        self.data = json.loads(self.map_path.read_text(encoding='utf-8'))
        self.stage = int(self.data['id'].split('-')[-1])
        self.tuning = CombatTuning()
        self.reset()

    def reset(self):
        spawn = self.data['playerSpawn']
        self.player = Actor(spawn['x'], spawn['y'], spawn['facing'])
        self.player.hp = self.player.max_hp = self.tuning.player_hp
        self.enemies = [Actor(e['x'], e['y'], e['facing'], e['behaviorType'],
                              ('근접 ' if e['behaviorType'] == 'melee' else '원거리 ') + e['id'].split('-')[-1])
                        for e in self.data['enemies']]
        for enemy in self.enemies:
            enemy.hp = enemy.max_hp = self.tuning.melee_hp if enemy.kind == 'melee' else self.tuning.ranged_hp
        for enemy, spec in zip(self.enemies, self.data['enemies']):
            enemy.element = spec['element']
        self.sources = [Source(s['id'], s['x'], s['y'], s['element']) for s in self.data.get('elementSources', [])]
        self.inventory = {element: 0 for element in ELEMENTS}
        self.selected = 'neutral'
        self.fire_aggro = False
        self.ingest_elapsed = -1
        self.ingest_source = None
        self.ingest_consumed = False
        self.ingest_form = 'neutral'
        self.safe = (self.player.x, self.player.y, self.player.facing)
        self.aggro = False
        self.spike_contact = False
        self.elapsed = 0
        self.projectiles = []
        self.feedback = []
        self.outcome = None

    def select_element(self, step):
        held = [e for e in ELEMENTS if self.inventory[e] > 0]
        if not held:
            self.selected = 'neutral'
        elif self.selected not in held:
            self.selected = held[0]
        else:
            self.selected = held[(held.index(self.selected)+step) % len(held)]

    def heal(self):
        if self.selected != 'water' or self.inventory['water'] < 1 or self.player.hp >= self.player.max_hp or self.player.falling or self.ingest_elapsed >= 0:
            return False
        amount = min(self.tuning.heal_amount, self.player.max_hp-self.player.hp)
        self.player.hp += amount
        self.inventory['water'] -= 1
        self.select_element(0)
        self.feedback.append(Feedback(self.player.x, self.player.y-1, f'+{amount}', True))
        return True

    def nearest_orb(self):
        candidates = [s for s in self.sources if s.phase == 'orb'
                      and math.hypot(s.x-self.player.x, s.y-self.player.y) <= self.tuning.ingest_range
                      and self.line_clear(self.player.x, self.player.y, s.x, s.y)]
        return min(candidates, key=lambda s: math.hypot(s.x-self.player.x, s.y-self.player.y), default=None)

    def start_ingest(self):
        source = self.nearest_orb()
        if source is None or self.ingest_elapsed >= 0 or self.player.attack_elapsed >= 0 or self.player.falling:
            return False
        self.ingest_source, self.ingest_elapsed = source.id, 0
        self.ingest_consumed, self.ingest_form = False, self.selected
        self.player.moving = False
        return True

    def ingest_tick(self, dt):
        if self.ingest_elapsed < 0:
            return
        self.ingest_elapsed += dt
        source = next(s for s in self.sources if s.id == self.ingest_source)
        if not self.ingest_consumed and self.ingest_elapsed >= self.tuning.ingest_event:
            source.phase, self.ingest_consumed = 'consumed', True
        if self.ingest_elapsed >= self.tuning.ingest_duration:
            self.inventory[source.element] += 1
            self.selected = source.element
            self.ingest_elapsed, self.ingest_source = -1, None
            self.ingest_consumed = False
            self.player.animation_time = 0

    def enemy_awake(self, enemy):
        return self.fire_aggro if self.stage == 2 and enemy.element == 'fire' else self.aggro

    @property
    def remaining_enemies(self):
        return sum(e.active for e in self.enemies)

    @property
    def exit_open(self):
        return self.remaining_enemies == 0

    @staticmethod
    def direction(facing):
        return {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[facing]

    @staticmethod
    def facing(dx, dy):
        return ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')

    def line_clear(self, x, y, tx, ty):
        steps = max(1, math.ceil(math.hypot(tx-x, ty-y) / .1))
        return all(self.tile(x+(tx-x)*i/steps, y+(ty-y)*i/steps) != 3 for i in range(steps+1))

    def start_attack(self, actor):
        if not actor.active or actor.falling or actor.attack_elapsed >= 0 or actor.attack_cooldown > 0 or (actor.kind == 'hero' and self.ingest_elapsed >= 0):
            return False
        if self.outcome or (actor.kind != 'hero' and not self.player.active):
            return False
        actor.attack_elapsed = 0
        actor.attack_emitted = False
        actor.attack_element = self.selected if actor.kind == 'hero' else actor.element
        if actor.kind == 'hero':
            actor.attack_facing = actor.facing
            actor.attack_direction = self.direction(actor.facing)
            actor.attack_cooldown = self.tuning.player_interval
        else:
            dx, dy = self.player.x-actor.x, self.player.y-actor.y
            length = math.hypot(dx, dy) or 1
            actor.attack_direction = dx/length, dy/length
            actor.attack_facing = self.facing(dx, dy)
            actor.attack_cooldown = self.tuning.melee_interval if actor.kind == 'melee' else self.tuning.ranged_interval
        return True

    def damage(self, actor, amount, direction=(0, 0)):
        if not actor.active or actor.falling or actor.invulnerable > 0:
            return False
        actor.hp = max(0, actor.hp - amount)
        actor.hit_flash = .16
        self.feedback.append(Feedback(actor.x, actor.y-1, str(amount), actor.kind != 'hero'))
        if actor.kind == 'hero':
            actor.invulnerable = self.tuning.invulnerability
        elif any(direction):
            actor.knockback = direction
            actor.knockback_left = self.tuning.knockback_seconds
        if actor.hp == 0:
            actor.active = False
            actor.attack_elapsed = -1
            self.feedback.append(Feedback(actor.x, actor.y-.5, '', actor.kind != 'hero', .3, .3))
            if actor.kind == 'hero':
                self.outcome = 'dead'
                self.projectiles.clear()
        return True

    def attack_tick(self, actor, dt):
        if actor.attack_elapsed < 0:
            return
        actor.attack_elapsed += dt
        if not actor.attack_emitted and actor.attack_elapsed >= self.tuning.attack_event:
            actor.attack_emitted = True
            dx, dy = actor.attack_direction
            if actor.kind == 'melee':
                distance = math.hypot(self.player.x-actor.x, self.player.y-actor.y)
                toward = (self.player.x-actor.x)*dx + (self.player.y-actor.y)*dy
                if distance <= self.tuning.melee_range and toward >= 0 and self.line_clear(actor.x, actor.y, self.player.x, self.player.y):
                    self.damage(self.player, self.tuning.enemy_damage)
                self.feedback.append(Feedback(actor.x+dx*.55, actor.y+dy*.55-.35, '', False, .18, .18))
            else:
                hero = actor.kind == 'hero'
                elemental = hero and actor.attack_element != 'neutral'
                # 루트에서부터 진행시켜 바로 앞의 벽·적도 건너뛰지 않게 한다.
                self.projectiles.append(Projectile(actor.x, actor.y, dx, dy, 'hero' if hero else 'enemy',
                    self.tuning.elemental_speed if elemental else self.tuning.neutral_speed if hero else self.tuning.enemy_shot_speed,
                    self.tuning.elemental_range if elemental else self.tuning.neutral_range if hero else self.tuning.enemy_shot_range,
                    self.tuning.elemental_damage if elemental else self.tuning.neutral_damage if hero else self.tuning.enemy_damage,
                    element=actor.attack_element))
        if actor.attack_elapsed >= self.tuning.attack_duration:
            actor.attack_elapsed = -1
            actor.animation_time = 0

    def update_projectiles(self, dt):
        # 작은 간격으로 벽과 캐릭터를 검사해 빠른 탄환의 관통을 막는다.
        for shot in list(self.projectiles):
            if self.outcome:
                break
            if not shot.active:
                continue
            distance = min(shot.speed*dt, shot.remaining)
            parts = max(1, math.ceil(distance/.06))
            shot.age += dt
            for _ in range(parts):
                shot.x += shot.dx * distance/parts
                shot.y += shot.dy * distance/parts
                shot.remaining -= distance/parts
                if self.tile(shot.x, shot.y) == 3 or not (0 <= shot.x < self.data['columns'] and 0 <= shot.y < self.data['rows']):
                    shot.active = False
                    self.feedback.append(Feedback(shot.x, shot.y-.4, '', shot.owner == 'hero', .16, .16))
                    break
                targets = self.enemies if shot.owner == 'hero' else [self.player]
                for source in self.sources:
                    if source.solid and math.hypot(source.x-shot.x, source.y-shot.y) <= .53:
                        if shot.owner == 'hero':
                            source.hit(shot.element)
                        shot.active = False
                        break
                if not shot.active:
                    break
                for actor in targets:
                    if actor.active and not actor.falling and math.hypot(actor.x-shot.x, actor.y-shot.y) <= .42:
                        neutral_target = shot.owner == 'hero' and actor.element == 'neutral'
                        allowed = shot.owner != 'hero' or shot.element == 'neutral' or BEATS.get(shot.element) == actor.element or neutral_target
                        if allowed:
                            self.damage(actor, self.tuning.neutral_target_damage if neutral_target else shot.damage,
                                        (shot.dx, shot.dy) if shot.owner == 'hero' and shot.element == 'neutral' else (0, 0))
                        else:
                            self.feedback.append(Feedback(actor.x, actor.y-1, '차단', False))
                        shot.active = False
                        break
                if not shot.active:
                    break
            if shot.remaining <= .00001:
                shot.active = False
        self.projectiles[:] = [s for s in self.projectiles if s.active]

    def tile(self, x, y):
        x, y = math.floor(x), math.floor(y)
        if 0 <= x < self.data['columns'] and 0 <= y < self.data['rows']:
            return self.data['tiles'][y][x]
        return 4

    def fits(self, x, y, safe=False):
        for dx in (-self.radius, self.radius):
            for dy in (-self.radius, self.radius):
                tile = self.tile(x + dx, y + dy)
                if tile == 3 or (safe and tile >= 3):
                    return False
        if any(s.solid and math.hypot(x-s.x, y-s.y) < .42+self.radius for s in self.sources):
            return False
        return True

    def move(self, actor, dx, dy, safe=False):
        old = actor.x, actor.y
        parts = max(1, math.ceil(math.hypot(dx, dy) / .08))
        for _ in range(parts):
            if self.fits(actor.x + dx / parts, actor.y, safe):
                actor.x += dx / parts
            if self.fits(actor.x, actor.y + dy / parts, safe):
                actor.y += dy / parts
        actor.moving = math.hypot(actor.x - old[0], actor.y - old[1]) > .00001
        if actor.moving:
            actor.facing = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')

    def in_arena(self):
        r = self.data['aggroTrigger']
        return r['x'] <= self.player.x < r['x'] + r['width'] and r['y'] <= self.player.y < r['y'] + r['height']

    def distance_field(self):
        goal = math.floor(self.player.x), math.floor(self.player.y)
        if self.tile(*goal) >= 3:
            return {}
        distances, queue = {goal: 0}, deque([goal])
        while queue:
            x, y = queue.popleft()
            for pos in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if pos not in distances and self.tile(*pos) < 3 and self.fits(pos[0]+.5,pos[1]+.5,safe=True):
                    distances[pos] = distances[(x, y)] + 1
                    queue.append(pos)
        return distances

    def chase(self, enemy, distances, dt):
        if math.hypot(enemy.x - self.player.x, enemy.y - self.player.y) < .8:
            return
        x, y = math.floor(enemy.x), math.floor(enemy.y)
        distance = distances.get((x, y))
        if distance is None:
            return
        if distance == 0:
            target = self.player.x, self.player.y
        else:
            options = [p for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                       if distances.get(p) == distance - 1]
            if not options:
                return
            nx, ny = min(options, key=lambda p: math.hypot(p[0] + .5 - enemy.x, p[1] + .5 - enemy.y))
            if nx != x and abs(enemy.y - (y + .5)) > .035:
                target = enemy.x, y + .5
            elif ny != y and abs(enemy.x - (x + .5)) > .035:
                target = x + .5, enemy.y
            else:
                target = nx + .5, ny + .5
        dx, dy = target[0] - enemy.x, target[1] - enemy.y
        length = math.hypot(dx, dy)
        if length:
            step = min(length, self.data['preview']['meleeSpeed'] * dt)
            self.move(enemy, dx / length * step, dy / length * step, safe=True)

    def update(self, keys, dt):
        if not math.isfinite(dt) or dt <= 0 or self.outcome:
            return
        dt = min(dt, .05)
        self.elapsed += dt
        player = self.player
        for source in self.sources:
            source.update(dt)
        for effect in self.feedback:
            effect.remaining -= dt
        self.feedback[:] = [f for f in self.feedback if f.remaining > 0]
        for actor in [player, *self.enemies]:
            actor.hit_flash = max(0, actor.hit_flash-dt)
            actor.invulnerable = max(0, actor.invulnerable-dt)
            actor.attack_cooldown = max(0, actor.attack_cooldown-dt)
        previous_movement = {id(e): e.moving for e in self.enemies}
        for enemy in self.enemies:
            enemy.moving = False
        if player.falling > 0:
            player.falling = max(0, player.falling - dt)
            player.moving = False
            self.spike_contact = False
            if player.falling == 0:
                player.x, player.y, player.facing = self.safe
                player.animation_time = 0
                player.invulnerable = self.tuning.invulnerability
            self.update_projectiles(dt)
            return
        if 'previous' in keys:
            self.select_element(-1)
        if 'next' in keys:
            self.select_element(1)
        if 'skill' in keys:
            self.heal()
        if 'ingest' in keys:
            self.start_ingest()
        ingesting = self.ingest_elapsed >= 0
        self.ingest_tick(dt)
        dx = int('d' in keys) - int('a' in keys)
        dy = int('s' in keys) - int('w' in keys)
        if ingesting:
            dx = dy = 0
        length = math.hypot(dx, dy) or 1
        was_moving = player.moving
        speed = self.data['preview']['playerSpeed']
        self.move(player, dx / length * speed * dt, dy / length * speed * dt)
        player.animate(dt, was_moving)
        tile = self.tile(player.x, player.y)
        self.spike_contact = tile == 5
        if tile == 4:
            player.falling = self.data['preview']['fallSeconds']
            player.attack_elapsed = -1
            return
        if tile < 3 and self.fits(player.x, player.y, safe=True):
            self.safe = player.x, player.y, player.facing
        self.aggro = self.aggro or self.in_arena()
        if self.stage == 2:
            r = self.data['fireAggroTrigger']
            self.fire_aggro = self.fire_aggro or (r['x'] <= player.x < r['x']+r['width'] and r['y'] <= player.y < r['y']+r['height'])
        if 'attack' in keys:
            self.start_attack(player)
        self.attack_tick(player, dt)
        distances = self.distance_field() if self.aggro or self.fire_aggro else {}
        for enemy in self.enemies:
            if not enemy.active:
                continue
            if enemy.falling > 0:
                enemy.falling = max(0, enemy.falling - dt)
                if enemy.falling == 0:
                    enemy.active = False
            elif self.tile(enemy.x, enemy.y) == 4:
                # AI 자발 이동은 구멍을 피한다. 강제 이동 등으로 떨어지면 낙하 가능.
                enemy.falling = self.data['preview']['fallSeconds']
                enemy.attack_elapsed = -1
            else:
                if enemy.knockback_left > 0:
                    step_time = min(dt, enemy.knockback_left)
                    step = self.tuning.knockback_distance*step_time/self.tuning.knockback_seconds
                    self.move(enemy, enemy.knockback[0]*step, enemy.knockback[1]*step)
                    enemy.knockback_left = max(0, enemy.knockback_left-dt)
                    if self.tile(enemy.x, enemy.y) == 4:
                        enemy.falling = self.data['preview']['fallSeconds']
                        enemy.attack_elapsed = -1
                elif self.enemy_awake(enemy) and enemy.kind == 'melee' and enemy.attack_elapsed < 0:
                    self.chase(enemy, distances, dt)
                if self.enemy_awake(enemy) and not player.falling and not enemy.falling:
                    distance = math.hypot(enemy.x-player.x, enemy.y-player.y)
                    attack_range = self.tuning.melee_range if enemy.kind == 'melee' else self.tuning.ranged_range
                    if distance <= attack_range and self.line_clear(enemy.x, enemy.y, player.x, player.y):
                        self.start_attack(enemy)
                    self.attack_tick(enemy, dt)
                    if self.outcome:
                        return
            enemy.animate(dt, previous_movement[id(enemy)])
        self.update_projectiles(dt)
        exit_pos = self.data['plannedExit']
        if self.exit_open and not self.outcome and math.hypot(player.x-exit_pos['x'], player.y-exit_pos['y']) < .7:
            self.outcome = 'clear'
            self.projectiles.clear()
