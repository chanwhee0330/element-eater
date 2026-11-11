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
STAGES = {n: ROOT / f'assets/maps/room-{n:02d}/room-{n:02d}.json' for n in (1, 2, 3, 4, 5)}

TILE_WIDTH, TILE_HEIGHT = 48, 30
RIM_HALF_X, RIM_HALF_Y = 10 / TILE_WIDTH, 10 / TILE_HEIGHT


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
    wind_sliding: bool = False

    def animate(self, dt, was_moving):
        self.animation_time = self.animation_time + dt if was_moving == self.moving else 0


@dataclass
class EarthTerrain:
    kind: str
    bounds: tuple
    remaining: float

    def contains(self, x, y):
        left, top, right, bottom = self.bounds
        return left <= x < right and top <= y < bottom


class Room:
    radius = .21
    wind_push_speed = 8
    wind_enemy_push_seconds = .6
    gate_open_seconds = .3
    earth_seconds = 4

    def __init__(self, path=MAP_PATH, *, stage=None):
        self.map_path = STAGES[stage] if stage is not None else Path(path)
        self.data = json.loads(self.map_path.read_text(encoding='utf-8'))
        self.stage = int(self.data['id'].split('-')[-1])
        self.tuning = CombatTuning()
        self.reference_art = self.data.get('referenceArt')
        self.rear_edges = set()
        self.rim_edges = self.build_rim_edges() if not self.reference_art and 'floorRegions' in self.data else []
        horizontal = {point for start, end, axis in self.rim_edges if axis == 'horizontal' for point in (start, end)}
        vertical = {point for start, end, axis in self.rim_edges if axis == 'vertical' for point in (start, end)}
        self.rim_corners = horizontal & vertical
        self.wall_bounds = {}
        for start, end, axis in self.rim_edges:
            x, y = start
            end_x, end_y = end
            if axis == 'horizontal':
                left = x - (RIM_HALF_X if start in self.rim_corners else 0)
                right = end_x + (RIM_HALF_X if end in self.rim_corners else 0)
                bounds = (left, y - RIM_HALF_Y, right, y + RIM_HALF_Y)
            else:
                top = y - (RIM_HALF_Y if start in self.rim_corners else 0)
                bottom = end_y + (RIM_HALF_Y if end in self.rim_corners else 0)
                bounds = (x - RIM_HALF_X, top, x + RIM_HALF_X, bottom)
            self.wall_bounds[x, y, axis] = bounds
        self.wall_bounds.update({(x, y, 'horizontal'): (x, y - .24, x + 1, y)
                                 for x, y in self.rear_edges})
        self.reset()

    def build_rim_edges(self):
        arena = self.data['floorRegions'][0]
        self.rear_edges = {(x, arena['y']) for x in range(arena['x'], arena['x'] + arena['width'])}
        decor_path = self.map_path.parent / 'source/decorations.json'
        if decor_path.is_file():
            decor = json.loads(decor_path.read_text(encoding='utf-8'))
            for run in decor.get('wallRuns', []):
                self.rear_edges.update((x, run['y']) for x in range(run['x'], run['x'] + run['width']))
        tiles = self.data['tiles']
        pit = self.data['tileIds']['pit']
        rows, columns = len(tiles), len(tiles[0])
        edges = []
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if tile == pit:
                    continue
                # 한 칸 너머의 앞쪽 절벽이 이미 이 경계를 구분한다.
                cliff_behind = y >= 2 and tiles[y - 2][x] != pit
                if (y == 0 or tiles[y - 1][x] == pit) and not cliff_behind and (x, y) not in self.rear_edges:
                    edges.append(((x, y), (x + 1, y), 'horizontal'))
                if y + 1 == rows or tiles[y + 1][x] == pit:
                    edges.append(((x, y + 1), (x + 1, y + 1), 'horizontal'))
                if x == 0 or row[x - 1] == pit:
                    edges.append(((x, y), (x, y + 1), 'vertical'))
                if x + 1 == columns or row[x + 1] == pit:
                    edges.append(((x + 1, y), (x + 1, y + 1), 'vertical'))
        return edges

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
        self.vine_gate = self.data.get('vineGate')
        self.vine_time = -1
        self.puzzle = self.data.get('stonePuzzle')
        self.block = tuple(self.puzzle['start']) if self.puzzle else None
        self.block_direction = None
        self.plate_pressed = False
        self.gate_time = 0
        self.navigation_cache = None
        self.earth_terrain = []
        self.turret_room = self.data.get('turretRoom')
        self.turrets_stopped = False
        self.turret_timer = 0
        self.next_turret = 0
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

    def skill(self):
        if self.selected == 'earth':
            return self.cast_earth()
        if self.selected != 'wind':
            return self.heal()
        if not self.inventory['wind'] or self.ingest_elapsed >= 0 or self.player.falling:
            return False
        player = self.player
        dx, dy = self.direction(player.facing)

        def in_gust(x, y):
            vx, vy = x - player.x, y - player.y
            forward = vx * dx + vy * dy
            return (forward > 0 and abs(vx * dy - vy * dx) <= forward
                    and math.hypot(vx, vy) <= 160 / 42
                    and self.line_clear(player.x, player.y, x, y, ignore_block=True))

        if self.block is not None and not self.plate_pressed and in_gust(*self.block):
            self.block_direction = player.facing
        for enemy in self.enemies:
            if enemy.active and enemy.element == 'earth' and not enemy.falling and in_gust(enemy.x, enemy.y):
                enemy.wind_sliding = True
                enemy.knockback = dx, dy
                enemy.knockback_left = self.wind_enemy_push_seconds
                enemy.attack_elapsed = -1
        self.inventory['wind'] -= 1
        self.select_element(0)
        self.feedback.append(Feedback(player.x + dx, player.y + dy - .35, '돌풍', True, .3, .3))
        return True

    def cast_earth(self):
        player = self.player
        if not self.inventory['earth'] or self.ingest_elapsed >= 0 or player.falling:
            return False
        dx, dy = self.direction(player.facing)
        x, y = player.x + dx * 1.65, player.y + dy * 1.65
        bridge = self.turret_room and self.turret_room['bridge']
        if bridge:
            left, top, right, bottom = bridge
            on_bank = ((dx == 1 and left - 1 <= player.x < left)
                       or (dx == -1 and right <= player.x <= right + 1))
            if on_bank and top <= player.y < bottom:
                if any(terrain.kind == 'floor' for terrain in self.earth_terrain):
                    return False
                self.earth_terrain.append(EarthTerrain('floor', tuple(bridge), self.earth_seconds))
                return self.consume_earth(x, y, '흙 바닥')

        half_x, half_y = (.33, .9) if dx else (.9, .33)
        bounds = x - half_x, y - half_y, x + half_x, y + half_y
        if not self.line_clear(player.x, player.y, x, y):
            return False
        # 벽의 면 전체를 검사해 기존 바닥의 가장자리나 물체와 겹치지 않게 한다.
        if any(self.tile(x + half_x * i / 4, y + half_y * j / 4, ignore_earth=True) != 0
               or self.tile(x + half_x * i / 4, y + half_y * j / 4) != 0
               or self.blocked_by_wall(x + half_x * i / 4, y + half_y * j / 4, x, y)
               for i in range(-4, 5) for j in range(-4, 5)):
            return False
        occupants = [(actor.x, actor.y, self.radius) for actor in (player, *self.enemies) if actor.active]
        occupants.extend((source.x, source.y, .53) for source in self.sources if source.phase != 'consumed')
        exit_point = self.data['plannedExit']
        occupants.append((exit_point['x'], exit_point['y'], .7))
        if self.turret_room:
            occupants.append((*self.turret_room['switch'], .65))
        if any(abs(ox - x) < half_x + radius and abs(oy - y) < half_y + radius
               for ox, oy, radius in occupants):
            return False
        self.earth_terrain.append(EarthTerrain('wall', bounds, self.earth_seconds))
        return self.consume_earth(x, y, '흙벽')

    def consume_earth(self, x, y, label):
        self.inventory['earth'] -= 1
        self.select_element(0)
        self.feedback.append(Feedback(x, y - .4, label, True, .55, .55))
        return True

    def update_turrets(self, dt):
        if not self.turret_room or self.turrets_stopped:
            return
        player = self.player
        sx, sy = self.turret_room['switch']
        if not player.falling and math.hypot(player.x - sx, player.y - sy) < .64:
            self.turrets_stopped = True
            self.feedback.append(Feedback(sx, sy - .45, '포대 정지', True, 1, 1))
            return
        if player.y >= self.turret_room['activateY']:
            return
        self.turret_timer = max(0, self.turret_timer - dt)
        if not self.turret_timer:
            x, y = self.turret_room['emitters'][self.next_turret]
            target_x = max(self.turret_room['emitters'][0][0],
                           min(self.turret_room['emitters'][1][0], player.x))
            dx, dy = target_x - x, max(3, player.y - y)
            length = math.hypot(dx, dy)
            self.projectiles.append(Projectile(x, y, dx / length, dy / length, 'enemy',
                                               8, 12, 8, element='lightning'))
            self.next_turret = 1 - self.next_turret
            self.turret_timer = .85

    def update_puzzle(self, dt):
        if self.block_direction is None:
            return
        dx, dy = self.direction(self.block_direction)
        px, py = self.puzzle['plate']
        distance = self.wind_push_speed * dt
        parts = math.ceil(distance / .06)
        for _ in range(parts):
            x = self.block[0] + dx * distance / parts
            y = self.block[1] + dy * distance / parts
            # 블록 외곽 전체가 바닥 위에 있을 때만 이동한다.
            if any(self.tile(x + sx, y + sy, ignore_block=True) >= 3
                   for sx in (-.49, .49) for sy in (-.49, .49)):
                self.block_direction = None
                break
            self.block = x, y
            if abs(x - px) <= .36 and abs(y - py) <= .36:
                self.block = px, py
                self.plate_pressed = True
                self.block_direction = None
                self.feedback.append(Feedback(px, py - .5, '석문 개방', True, .8, .8))
                break

    def update_sources(self, dt):
        for source in self.sources:
            source.update(dt)
            respawn = (self.puzzle and source.element == 'wind') or (self.turret_room and source.element == 'earth')
            if (respawn and source.phase == 'consumed' and source.id != self.ingest_source
                    and self.inventory[source.element] < 2 and source.age >= 8
                    and all(not actor.active or math.hypot(actor.x - source.x, actor.y - source.y) >= .7
                            for actor in (self.player, *self.enemies))):
                source.hp, source.phase, source.age = 3, 'intact', 0
                source.break_elapsed, source.hit_time = 0, 999

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
            source.age = 0
        if self.ingest_elapsed >= self.tuning.ingest_duration:
            self.inventory[source.element] += 1
            self.selected = source.element
            self.ingest_elapsed, self.ingest_source = -1, None
            self.ingest_consumed = False
            self.player.animation_time = 0

    def enemy_awake(self, enemy):
        if self.stage == 2 and enemy.element == 'fire':
            return self.fire_aggro
        if self.vine_gate and enemy.element == 'wind':
            return self.vine_open and self.aggro
        return self.aggro and self.stone_gate_open and (not self.turret_room or self.turrets_stopped)

    @property
    def remaining_enemies(self):
        return sum(e.active for e in self.enemies)

    @property
    def exit_open(self):
        return (self.remaining_enemies == 0 and self.vine_open and self.stone_gate_open
                and (not self.turret_room or self.turrets_stopped))

    @property
    def vine_open(self):
        return self.vine_gate is None or self.vine_time >= self.vine_gate['burnDuration']

    def vine_contains(self, x, y):
        gate = self.vine_gate
        return (not self.vine_open and gate['x'] <= x < gate['x'] + gate['width']
                and gate['y'] <= y < gate['y'] + gate['height'])

    @staticmethod
    def direction(facing):
        return {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[facing]

    @staticmethod
    def facing(dx, dy):
        return ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')

    def line_clear(self, x, y, tx, ty, *, ignore_block=False):
        steps = max(1, math.ceil(math.hypot(tx-x, ty-y) / .1))
        return all(self.tile(x+(tx-x)*i/steps, y+(ty-y)*i/steps, ignore_block=ignore_block) != 3 for i in range(steps+1))

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
        elif any(direction) and not actor.wind_sliding:
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
                if (self.vine_contains(shot.x, shot.y) and self.vine_time < 0
                        and shot.owner == 'hero' and shot.element == 'fire'):
                    self.vine_time = 0
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

    @property
    def stone_gate_open(self):
        return self.puzzle is None or self.gate_time >= self.gate_open_seconds

    def tile(self, x, y, *, ignore_block=False, ignore_earth=False):
        if not ignore_earth:
            for terrain in self.earth_terrain:
                if terrain.contains(x, y):
                    return 3 if terrain.kind == 'wall' else 0
        if self.puzzle:
            x0, y0, x1, y1 = self.puzzle['gate']
            if not self.stone_gate_open and x0 <= x < x1 and y0 <= y < y1:
                return 3
            if not ignore_block and abs(x - self.block[0]) < .49 and abs(y - self.block[1]) < .49:
                return 3
        if self.vine_contains(x, y):
            return 3
        if self.reference_art:
            for x0, y0, x1, y1 in self.reference_art['cover']:
                if x0 <= x < x1 and y0 <= y < y1:
                    return 3
            for x0, y0, x1, y1 in self.reference_art['walkable']:
                if x0 <= x < x1 and y0 <= y < y1:
                    return 0
            if self.reference_art.get('openCliffs'):
                if any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in self.reference_art['openCliffs']):
                    return 4
                return 3
            return 4
        x, y = math.floor(x), math.floor(y)
        if 0 <= x < self.data['columns'] and 0 <= y < self.data['rows']:
            return self.data['tiles'][y][x]
        return 4

    def fits(self, x, y, safe=False, *, ignore_earth=False):
        if self.reference_art and self.reference_art.get('walledBoundary') and self.tile(x, y, ignore_earth=ignore_earth) == 4:
            return False
        for dx in (-self.radius, self.radius):
            for dy in (-self.radius, self.radius):
                tile = self.tile(x + dx, y + dy, ignore_earth=ignore_earth)
                if tile == 3 or (safe and tile >= 3):
                    return False
        if any(s.solid and math.hypot(x-s.x, y-s.y) < .42+self.radius for s in self.sources):
            return False
        return True

    def blocked_by_wall(self, x, y, old_x, old_y):
        radius = self.radius
        # 세로 투영에서 발밑 충돌 폭도 함께 줄인다.
        depth = radius * TILE_HEIGHT / TILE_WIDTH
        for left, top, right, bottom in self.wall_bounds.values():
            if not (left - radius < x < right + radius and top - depth < y < bottom + depth):
                continue
            if not (left - radius < old_x < right + radius and top - depth < old_y < bottom + depth):
                return True
            # 이전 저장에서 벽과 겹쳐도 벽 안쪽으로 더 들어가지 않고 빠져나올 수 있다.
            center_x = (left + right) / 2
            center_y = (top + bottom) / 2
            if (x - old_x) * (old_x - center_x) < 0 or (y - old_y) * (old_y - center_y) < 0:
                return True
        return False

    def move(self, actor, dx, dy, safe=False):
        old = actor.x, actor.y
        parts = max(1, math.ceil(math.hypot(dx, dy) / .08))
        for _ in range(parts):
            x = actor.x + dx / parts
            if not self.blocked_by_wall(x, actor.y, actor.x, actor.y) and self.fits(x, actor.y, safe):
                actor.x = x
            y = actor.y + dy / parts
            if not self.blocked_by_wall(actor.x, y, actor.x, actor.y) and self.fits(actor.x, y, safe):
                actor.y = y
        actor.moving = math.hypot(actor.x - old[0], actor.y - old[1]) > .00001
        if actor.moving:
            actor.facing = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')

    def in_arena(self):
        r = self.data['aggroTrigger']
        return r['x'] <= self.player.x < r['x'] + r['width'] and r['y'] <= self.player.y < r['y'] + r['height']

    @staticmethod
    def neighbors(x, y):
        return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))

    def reference_link(self, x, y, tx, ty):
        parts = max(1, math.ceil(math.hypot(tx - x, ty - y) / .125))
        return all(self.fits(x + (tx - x) * i / parts, y + (ty - y) * i / parts, safe=True)
                   for i in range(1, parts + 1))

    def reference_anchors(self, x, y):
        gx, gy = round(x * 2), round(y * 2)
        cells = [(col, row) for col in range(gx - 1, gx + 2) for row in range(gy - 1, gy + 2)]
        return sorted(cells, key=lambda p: math.hypot(p[0] / 2 - x, p[1] / 2 - y))

    def reference_distances(self):
        player = self.player
        goal = next((p for p in self.reference_anchors(player.x, player.y)
                     if self.fits(p[0] / 2, p[1] / 2, safe=True)), None)
        if goal is None:
            return {}
        key = (goal, self.vine_open, self.stone_gate_open, self.block, self.turrets_stopped,
               tuple(s.solid for s in self.sources), tuple(t.bounds for t in self.earth_terrain))
        if self.navigation_cache and self.navigation_cache[0] == key:
            return self.navigation_cache[1]
        distances, queue = {goal: 0}, deque([goal])
        while queue:
            x, y = queue.popleft()
            for nx, ny in self.neighbors(x, y):
                if (nx, ny) not in distances and self.reference_link(x / 2, y / 2, nx / 2, ny / 2):
                    distances[nx, ny] = distances[x, y] + 1
                    queue.append((nx, ny))
        self.navigation_cache = key, distances
        return distances

    def reference_target(self, enemy, distances):
        player = self.player
        if self.reference_link(enemy.x, enemy.y, player.x, player.y):
            return player.x, player.y
        # 이미지 맵의 통로는 타일 격자 중심과 어긋날 수 있다.
        for x, y in self.reference_anchors(enemy.x, enemy.y):
            if (x, y) not in distances or not self.reference_link(enemy.x, enemy.y, x / 2, y / 2):
                continue
            for nx, ny in self.neighbors(x, y):
                if (distances.get((nx, ny)) == distances[x, y] - 1
                        and self.reference_link(enemy.x, enemy.y, nx / 2, ny / 2)):
                    return nx / 2, ny / 2
            return x / 2, y / 2
        return enemy.x, enemy.y

    def distance_field(self):
        if self.reference_art:
            return self.reference_distances()
        goal = math.floor(self.player.x), math.floor(self.player.y)
        if self.tile(self.player.x, self.player.y) >= 3:
            return {}
        distances, queue = {goal: 0}, deque([goal])
        while queue:
            x, y = queue.popleft()
            for pos in self.neighbors(x, y):
                if pos not in distances and self.fits(pos[0]+.5,pos[1]+.5,safe=True):
                    distances[pos] = distances[(x, y)] + 1
                    queue.append(pos)
        return distances

    def chase(self, enemy, distances, dt):
        if math.hypot(enemy.x - self.player.x, enemy.y - self.player.y) < .8:
            return
        target = self.reference_target(enemy, distances) if self.reference_art else self.tile_target(enemy, distances)
        if target is None:
            return
        dx, dy = target[0] - enemy.x, target[1] - enemy.y
        length = math.hypot(dx, dy)
        if length:
            step = min(length, self.data['preview']['meleeSpeed'] * dt)
            self.move(enemy, dx / length * step, dy / length * step, safe=True)

    def tile_target(self, enemy, distances):
        x, y = math.floor(enemy.x), math.floor(enemy.y)
        distance = distances.get((x, y))
        if distance is None:
            return
        if distance == 0:
            target = self.player.x, self.player.y
        else:
            options = [p for p in self.neighbors(x, y)
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
        return target

    def update(self, keys, dt):
        if not math.isfinite(dt) or dt <= 0 or self.outcome:
            return
        dt = min(dt, .05)
        if self.vine_gate and not self.vine_open and self.vine_time >= 0:
            self.vine_time = min(self.vine_time + dt, self.vine_gate['burnDuration'])
        self.elapsed += dt
        for terrain in self.earth_terrain:
            terrain.remaining -= dt
        self.earth_terrain[:] = [terrain for terrain in self.earth_terrain if terrain.remaining > 0]
        if self.plate_pressed:
            self.gate_time = min(self.gate_open_seconds, self.gate_time + dt)
        player = self.player
        self.update_sources(dt)
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
            self.skill()
        self.update_puzzle(dt)
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
        self.spike_contact = tile == self.data['tileIds']['spikes']
        if self.spike_contact:
            self.damage(player, self.tuning.spike_damage)
            if self.outcome:
                return
        if tile == 4:
            player.falling = self.data['preview']['fallSeconds']
            player.attack_elapsed = -1
            return
        if (tile < 3 and self.fits(player.x, player.y, safe=True)
                and self.fits(player.x, player.y, safe=True, ignore_earth=True)):
            self.safe = player.x, player.y, player.facing
        self.update_turrets(dt)
        self.aggro = self.aggro or self.in_arena()
        if self.stage == 2:
            r = self.data['fireAggroTrigger']
            self.fire_aggro = self.fire_aggro or (r['x'] <= player.x < r['x']+r['width'] and r['y'] <= player.y < r['y']+r['height'])
        if 'attack' in keys:
            self.start_attack(player)
        self.attack_tick(player, dt)
        distances = self.distance_field() if any(
            enemy.active and enemy.kind == 'melee' and self.enemy_awake(enemy) for enemy in self.enemies
        ) else {}
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
                if enemy.wind_sliding:
                    distance = self.wind_push_speed * min(dt, enemy.knockback_left)
                    self.move(enemy, enemy.knockback[0] * distance, enemy.knockback[1] * distance)
                    enemy.knockback_left = max(0, enemy.knockback_left - dt)
                    if self.tile(enemy.x, enemy.y) == 4:
                        enemy.falling = self.data['preview']['fallSeconds']
                    if enemy.falling or not enemy.moving or not enemy.knockback_left:
                        enemy.wind_sliding = False
                        enemy.knockback_left = 0
                elif enemy.knockback_left > 0:
                    step_time = min(dt, enemy.knockback_left)
                    step = self.tuning.knockback_distance*step_time/self.tuning.knockback_seconds
                    self.move(enemy, enemy.knockback[0]*step, enemy.knockback[1]*step)
                    enemy.knockback_left = max(0, enemy.knockback_left-dt)
                    if self.tile(enemy.x, enemy.y) == 4:
                        enemy.falling = self.data['preview']['fallSeconds']
                        enemy.attack_elapsed = -1
                elif self.enemy_awake(enemy) and enemy.kind == 'melee' and enemy.attack_elapsed < 0:
                    self.chase(enemy, distances, dt)
                if self.enemy_awake(enemy) and not player.falling and not enemy.falling and not enemy.wind_sliding:
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
