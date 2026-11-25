"""첫 방의 이동·추격·무속성 전투. 렌더러 없이도 검사 가능한 게임 상태."""
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import json
import math
import random
from .combat import CombatTuning, Projectile, Feedback
from .elements import ELEMENTS, BEATS, Source
from .boss import FALL_SECONDS, GUARDIAN_SHOT_LIFT, Guardian
from .quarry import LaserField, Quarry, contains

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / 'assets/maps/room-01/room-01.json'
STAGES = {n: ROOT / f'assets/maps/room-{n:02d}/room-{n:02d}.json' for n in range(1, 11)}

TILE_WIDTH, TILE_HEIGHT = 48, 30
RIM_HALF_X, RIM_HALF_Y = 10 / TILE_WIDTH, 10 / TILE_HEIGHT
RESERVOIR_BED = (6.5, 12, 10.6, 17.65)


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
    burn_ticks: int = 0
    burn_delay: float = 0

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
    garden_gate_seconds = .72
    garden_exit_seconds = .4
    earth_seconds = 4
    relay_flash_seconds = .36
    trial_wheel_reveal_seconds = .54

    def __init__(self, path=MAP_PATH, *, stage=None):
        self.map_path = STAGES[10 if stage == 0 else stage] if stage is not None else Path(path)
        self.data = json.loads(self.map_path.read_text(encoding='utf-8'))
        self.stage = 0 if stage == 0 else int(self.data['id'].split('-')[-1])
        self.tuning = CombatTuning()
        self.reference_art = self.data.get('referenceArt')
        self.rear_edges = set()
        self.rim_half_x, self.rim_half_y = RIM_HALF_X, RIM_HALF_Y
        self.reference_door_sides = ()
        if self.reference_art and 'wallOpenings' in self.reference_art:
            art = self.reference_art
            unit = art['pixelsPerTile'] * art['minimumScale']
            self.rim_half_x = self.rim_half_y = 10 / unit
            self.rim_edges = self.build_reference_rim_edges(art)
            if 'doorWallPixels' in art:
                self.reference_door_sides = tuple(self.reference_door_wall_bounds(art))
        elif not self.reference_art and 'floorRegions' in self.data:
            openings = {tuple(edge) for edge in self.data.get('openRims', ())}
            self.rim_edges = [edge for edge in self.build_rim_edges() if (*edge[0], edge[2]) not in openings]
        else:
            self.rim_edges = []
        horizontal = {point for start, end, axis in self.rim_edges if axis == 'horizontal' for point in (start, end)}
        vertical = {point for start, end, axis in self.rim_edges if axis == 'vertical' for point in (start, end)}
        self.rim_corners = horizontal & vertical
        wall_bounds = {}
        for start, end, axis in self.rim_edges:
            x, y = start
            end_x, end_y = end
            if axis == 'horizontal':
                left = x - (self.rim_half_x if start in self.rim_corners else 0)
                right = end_x + (self.rim_half_x if end in self.rim_corners else 0)
                bounds = (left, y - self.rim_half_y, right, y + self.rim_half_y)
            else:
                top = y - (self.rim_half_y if start in self.rim_corners else 0)
                bottom = end_y + (self.rim_half_y if end in self.rim_corners else 0)
                bounds = (x - self.rim_half_x, top, x + self.rim_half_x, bottom)
            wall_bounds[x, y, axis] = bounds
        wall_bounds.update({(x, y, 'horizontal'): (x, y - .24, x + 1, y)
                                 for x, y in self.rear_edges})
        wall_bounds.update({('door', index): bounds
                                 for index, bounds in enumerate(self.reference_door_sides)})
        # 레퍼런스 방의 외벽은 이동을 막고, 기존 스킬의 배치 범위에는 관여하지 않는다.
        self.reference_movement_walls = tuple(wall_bounds.values()) if self.reference_art else ()
        self.wall_bounds = {} if self.reference_art else wall_bounds
        self.reset()

    def build_reference_rim_edges(self, art):
        cells = {(x, y) for left, top, right, bottom in art['walkable']
                 for y in range(top, bottom) for x in range(left, right)}
        openings = {(x, y) for y, left, right in art['wallOpenings'] for x in range(left, right)}
        open_banks = {(x, y) for left, top, right, bottom in art.get('openCliffs', ())
                      for y in range(top, bottom) for x in (left, right)}
        edges = []
        for x, y in sorted(cells, key=lambda point: (point[1], point[0])):
            if (x, y - 1) not in cells and (x, y - 2) not in cells and (x, y) not in openings:
                edges.append(((x, y), (x + 1, y), 'horizontal'))
            if (x, y + 1) not in cells and (x, y + 1) not in openings:
                edges.append(((x, y + 1), (x + 1, y + 1), 'horizontal'))
            for edge_x, neighbor in ((x, x - 1), (x + 1, x + 1)):
                if (neighbor, y) not in cells and (edge_x, y) not in open_banks:
                    edges.append(((edge_x, y), (edge_x, y + 1), 'vertical'))
        return edges

    def reference_door_wall_bounds(self, art):
        door_left, _, door_right, door_bottom = art['doorPixels']
        span_left, span_right = art['doorWallPixels']
        origin_x, origin_y = art['originPixels']
        unit = art['pixelsPerTile']
        base = (door_bottom - origin_y) / unit
        for start, end in ((span_left, door_left), (door_right, span_right)):
            for a in range(start, end, unit):
                yield (a - origin_x) / unit, base - .24, (min(a + unit, end) - origin_x) / unit, base

    def build_rim_edges(self):
        arena = self.data['floorRegions'][0]
        self.rear_edges = {(x, arena['y']) for x in range(arena['x'], arena['x'] + arena['width'])}
        decor_path = self.map_path.parent / self.data.get('decorations', 'source/decorations.json')
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
        if self.stage == 0:
            self.player.y = 16.8
        self.player.hp = self.player.max_hp = self.tuning.player_hp
        self.enemies = [Actor(e['x'], e['y'], e['facing'], e['behaviorType'],
                              ('근접 ' if e['behaviorType'] == 'melee' else '원거리 ') + e['id'].split('-')[-1])
                        for e in self.data['enemies']]
        for enemy in self.enemies:
            enemy.hp = enemy.max_hp = self.tuning.melee_hp if enemy.kind == 'melee' else self.tuning.ranged_hp
        for enemy, spec in zip(self.enemies, self.data['enemies']):
            enemy.element = spec['element']
        self.sources = [Source(s['id'], s['x'], s['y'], s['element']) for s in self.data.get('elementSources', [])]
        self.inventory = {element: int(stage < self.stage) for stage, element in enumerate(ELEMENTS, 2)}
        self.selected = next((element for element in reversed(ELEMENTS) if self.inventory[element]), 'neutral')
        self.acquisition = self.data.get('acquisition')
        self.reservoir = self.acquisition and self.acquisition.get('reservoir')
        self.forge = self.acquisition and self.acquisition.get('forge')
        self.windmill = self.acquisition and self.acquisition.get('windmill')
        self.capacitor = self.acquisition and self.acquisition.get('capacitor')
        self.power_circuit = self.acquisition and self.acquisition.get('powerCircuit')
        self.acquisition_relay = False
        self.acquisition_relay_flash = 0
        self.acquisition_power = False
        self.acquisition_power_elapsed = -1
        if self.acquisition:
            self.sources.append(Source('first-orb', *self.acquisition['orb'], self.acquisition['element'],
                                       hp=0, phase='sealed'))
        self.fire_aggro = False
        self.vine_gate = self.data.get('vineGate')
        self.vine_time = -1
        self.conductor_vine = self.data.get('conductorVine')
        self.conductor_vine_time = -1
        self.fire_barriers = self.data.get('fireBarriers', [])
        self.extinguished = set()
        self.steam = {}
        self.respawning_sources = set(self.data.get('respawningSources', []))
        self.puzzle = self.data.get('stonePuzzle')
        self.sluice = self.data.get('sluice')
        self.sluice_wheel = False
        self.sluice_pump = False
        self.garden = self.sluice.get('garden') if self.sluice else None
        self.quarry = Quarry(self.data['quarry'], self.reference_art) if 'quarry' in self.data else None
        self.garden_cells = self.index_garden_cells() if self.garden else None
        self.reference_path_cache = None
        self.garden_gate_time = 0.0
        self.garden_wheel_time = 0.0
        self.garden_exit_time = 0.0
        self.power_puzzle = self.data.get('powerPuzzle')
        self.trial = self.data.get('trial')
        self.trial_cells = self.index_trial_cells() if self.trial else None
        self.trial_lasers = LaserField(self.trial['lasers']) if self.trial else None
        self.trial_returns = set()
        self.trial_switch_times = [None, None]
        self.trial_wheel_time = 0.0
        self.trial_wrong = set()
        self.power_targets = (list(self.power_puzzle['targets']) if self.trial
                              else [random.randint(1, 3) for _ in range(3)] if self.power_puzzle else [])
        self.power_levels = [0] * len(self.power_targets)
        self.power_connected = False
        self.power_flash = 0
        self.power_hits = [0] * len(self.power_targets)
        self.block = tuple(self.puzzle['start']) if self.puzzle else None
        self.block_direction = None
        self.plate_pressed = False
        self.gate_time = 0
        self.power_gate_time = 0
        self.boss = self.data.get('boss')
        self.guardian = Guardian(self.boss, self.data['earthBridge']) if self.boss else None
        if self.boss:
            guardian = self.enemies[0]
            guardian.hp = guardian.max_hp = self.boss['hp']
            guardian.name = '오원 수호자'
            guardian.active = False
        self.navigation_cache = None
        self.earth_terrain = []
        self.bridge_crossed = False
        self.bridge_entry_side = None
        self.turret_room = self.data.get('turretRoom')
        self.earth_bridge = self.data.get('earthBridge')
        if self.turret_room:
            self.earth_bridge = self.turret_room['bridge']
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
        self.sound_events = []
        self.element_switch_started = None
        self.lightning_charged = False
        self.lightning_attack = False
        self.lightning_path = ()
        self.lightning_time = 0
        self.outcome = None
        self.debug_cleared = False

    def debug_clear(self):
        self.debug_cleared = True
        if self.guardian:
            if self.guardian.ritual < len(ELEMENTS):
                for element in ELEMENTS:
                    if self.inventory[element]:
                        self.guardian.placed.add(element)
                        self.inventory[element] = 0
                self.restore_selected_element(self.selected)
            self.guardian.debug_prepare(self)
            self.projectiles.clear()
            return
        for enemy in self.enemies:
            enemy.falling = 0
            enemy.invulnerable = 0
            if enemy.active:
                self.damage(enemy, enemy.hp)
            enemy.hp = 0
            enemy.burn_ticks = 0
            enemy.burn_delay = 0
            enemy.wind_sliding = False
            enemy.knockback_left = 0
        self.projectiles.clear()
        self.earth_terrain[:] = [terrain for terrain in self.earth_terrain if terrain.kind == 'floor']
        self.spike_contact = False

        for source in self.sources:
            if source.solid:
                source.hp, source.phase = 0, 'orb'
        if self.acquisition:
            source = self.sources[-1]
            if source.phase not in ('orb', 'consumed'):
                source.phase, source.age = 'orb', 0
            self.update_power_circuit(0)
        self.extinguished.update(range(len(self.fire_barriers)))
        self.steam.clear()
        if self.vine_gate:
            self.vine_time = self.vine_gate['burnDuration']
        if self.conductor_vine:
            self.conductor_vine_time = self.conductor_vine['burnDuration']
        if self.puzzle:
            self.block = tuple(self.puzzle['plate'])
            self.block_direction = None
            self.plate_pressed = True
            self.gate_time = self.gate_open_seconds
        if self.turret_room:
            if floor := self.turret_bridge_floor:
                self.earth_terrain.remove(floor)
            self.turrets_stopped = True
        if self.sluice:
            self.sluice_wheel = self.sluice_pump = True
            self.garden_wheel_time = .5
            self.garden_gate_time = self.garden_gate_seconds
            self.garden_exit_time = self.garden_exit_seconds
        if self.quarry:
            self.bridge_crossed = True
            self.bridge_entry_side = None
            self.quarry.exit_time = self.quarry.exit_seconds
            self.earth_terrain[:] = [terrain for terrain in self.earth_terrain
                                     if terrain.bounds != tuple(self.earth_bridge)]
        if self.trial:
            self.trial_returns.update((0, 1))
            self.trial_switch_times[:] = [None, None]
            self.trial_wheel_time = self.trial_wheel_reveal_seconds
        if self.power_puzzle:
            self.power_levels[:] = self.power_targets
            self.power_connected = True
            self.power_gate_time = self.gate_open_seconds
            self.power_flash = 0

    def select_element(self, step):
        if self.lightning_attack:
            return
        previous = self.selected
        held = [e for e in ELEMENTS if self.inventory[e] > 0]
        if not held:
            self.selected = 'neutral'
        elif self.selected not in held:
            self.selected = held[0]
        else:
            self.selected = held[(held.index(self.selected)+step) % len(held)]
        if self.selected != 'lightning':
            self.lightning_charged = False
        if step and self.selected != previous:
            self.element_switch_started = self.elapsed
            if self.selected in ELEMENTS:
                self.sound_events.append(f'switch-{self.selected}')

    def restore_selected_element(self, preferred):
        selected = preferred if self.inventory.get(preferred) else next(
            (element for element in ELEMENTS if self.inventory[element]), 'neutral')
        if selected != self.selected:
            self.player.attack_elapsed = -1
            self.lightning_attack = self.lightning_charged = False
            self.selected = selected

    def heal(self):
        if self.selected != 'water' or self.inventory['water'] < 1 or self.player.hp >= self.player.max_hp or self.player.falling or self.ingest_elapsed >= 0:
            return False
        amount = min(self.tuning.heal_amount, self.player.max_hp-self.player.hp)
        self.player.hp += amount
        self.sound_events.append('heal')
        self.select_element(0)
        self.feedback.append(Feedback(self.player.x, self.player.y-1, f'+{amount}', True))
        return True

    def skill(self):
        if self.selected == 'earth':
            return self.cast_earth()
        if self.selected == 'lightning':
            if not self.inventory['lightning'] or self.player.attack_elapsed >= 0 or self.ingest_elapsed >= 0 or self.player.falling:
                return False
            self.lightning_charged = not self.lightning_charged
            self.sound_events.append('electric' if self.lightning_charged else 'lever')
            return True
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

        if (self.block is not None and not self.plate_pressed
                and not (self.puzzle.get('centeredSlide') and self.block_direction)
                and in_gust(*self.block)
                and (not self.trial or (abs((self.block[0]-player.x)*dy - (self.block[1]-player.y)*dx) < .48
                                        and math.dist(self.block, (player.x, player.y)) <= 1.6))):
            self.block_direction = player.facing
        for enemy in self.enemies:
            if enemy.active and enemy.element == 'earth' and not enemy.falling and in_gust(enemy.x, enemy.y):
                if self.boss:
                    if self.boss_exposed:
                        enemy.knockback = dx, dy
                        enemy.knockback_left = self.tuning.knockback_seconds
                    continue
                enemy.wind_sliding = True
                enemy.knockback = dx, dy
                enemy.knockback_left = self.wind_enemy_push_seconds
                enemy.attack_elapsed = -1
        self.select_element(0)
        self.sound_events.append('gust')
        self.feedback.append(Feedback(player.x + dx, player.y + dy - .35, '돌풍', True, .3, .3))
        return True

    def cast_lightning(self):
        player = self.player
        unit = self.reference_art['pixelsPerTile'] if self.reference_art else TILE_WIDTH
        first_range = self.tuning.lightning_range / unit
        jump_range = self.tuning.lightning_jump_range / unit
        dx, dy = player.attack_direction
        candidates = [enemy for enemy in self.enemies if enemy.active and not enemy.falling
                      and not enemy.invulnerable and enemy.element in ('neutral', BEATS['lightning'])
                      and (not self.guardian or enemy is not self.enemies[0] or self.boss_exposed)]
        x, y = player.x, player.y
        path = [(x, y)]
        for _ in range(self.tuning.lightning_max_targets):
            nearest = None
            nearest_point = None
            nearest_distance = first_range if len(path) == 1 else jump_range
            for enemy in candidates:
                points = self.guardian.target_points(enemy) if self.guardian else ((enemy.x,enemy.y),)
                for px,py in points:
                    vx,vy = px-x,py-y
                    if len(path) == 1:
                        forward = vx * dx + vy * dy
                        if forward <= 0 or abs(vx * dy - vy * dx) > forward:
                            continue
                    distance = math.hypot(vx,vy)
                    if distance > nearest_distance or (nearest is not None and distance == nearest_distance):
                        continue
                    if self.line_clear(x,y,px,py,include_rim=True):
                        nearest,nearest_distance = enemy,distance
                        nearest_point = px,py
            if nearest is None:
                break
            candidates.remove(nearest)
            self.damage(nearest, self.tuning.lightning_damage, attack_element='lightning')
            x,y = nearest_point
            path.append((x, y))
        if len(path) == 1:
            return False
        self.sound_events.append('electric')
        self.lightning_path = tuple(path)
        self.lightning_time = .24
        return True

    def cast_earth(self):
        player = self.player
        if not self.inventory['earth'] or self.ingest_elapsed >= 0 or player.falling:
            return False
        dx, dy = self.direction(player.facing)
        x, y = player.x + dx * 1.65, player.y + dy * 1.65
        bridge = self.earth_bridge
        if bridge and not self.guardian and not self.turrets_stopped and not (self.quarry and self.debug_cleared):
            left, top, right, bottom = bridge
            if self.turret_room or self.data.get('bridgeAxis') == 'x':
                on_bank = (top <= player.y < bottom
                           and ((dx == 1 and left - 1 <= player.x < left)
                                or (dx == -1 and right <= player.x <= right + 1)))
            else:
                on_bank = (left <= player.x < right
                           and ((dy == 1 and top - 1 <= player.y < top)
                                or (dy == -1 and bottom <= player.y <= bottom + 1)))
            if on_bank:
                if any(terrain.kind == 'floor' for terrain in self.earth_terrain):
                    return False
                self.earth_terrain.append(EarthTerrain('floor', tuple(bridge), self.earth_seconds))
                return self.consume_earth(x, y, '흙 바닥')

        slot = self.quarry.wall_slot(player.x, player.y) if self.quarry else None
        if (self.trial_returns == {0} and self.trial_laser_locked and dy == -1
                and 31.4 < player.x < 34.3 and 17.2 < player.y < 19):
            slot = self.trial['wallSlot']
        if slot is not None:
            x, y = slot
        half_x, half_y = (.33, .9) if dx or slot is not None else (.9, .33)
        bounds = x - half_x, y - half_y, x + half_x, y + half_y
        if not self.line_clear(player.x, player.y, x, y):
            return False
        # 벽의 면 전체를 검사해 기존 바닥의 가장자리나 물체와 겹치지 않게 한다.
        if any(self.tile(x + half_x * i / 4, y + half_y * j / 4, ignore_earth=True) >= 3
               or self.tile(x + half_x * i / 4, y + half_y * j / 4) >= 3
               or self.blocked_by_wall(x + half_x * i / 4, y + half_y * j / 4, x, y, include_reference_rim=False)
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
        self.sound_events.append('stone')
        self.select_element(0)
        self.feedback.append(Feedback(x, y - .4, label, True, .55, .55))
        return True

    @property
    def turret_bridge_floor(self):
        if not self.turret_room:
            return None
        bridge = tuple(self.turret_room['bridge'])
        return next((terrain for terrain in self.earth_terrain
                     if terrain.kind == 'floor' and terrain.bounds == bridge and terrain.remaining > 0), None)

    @property
    def can_stop_turrets(self):
        if not self.turret_room or self.turrets_stopped or not self.learned_room_element or self.ingest_elapsed >= 0:
            return False
        player = self.player
        x, y = self.turret_room['switch']
        return (not player.falling and math.hypot(player.x - x, player.y - y) <= .78
                and self.fits(player.x, player.y, safe=True, ignore_earth=True))

    def stop_turrets(self):
        if not self.can_stop_turrets:
            return
        self.turrets_stopped = True
        bridge = self.turret_bridge_floor
        if bridge:
            self.earth_terrain.remove(bridge)
        x, y = self.turret_room['switch']
        self.feedback.append(Feedback(x, y - .45, '포대 정지', True, 1, 1))

    def update_turrets(self, dt):
        if not self.turret_room or self.turrets_stopped:
            return
        player = self.player
        if player.y >= self.turret_room['activateY']:
            return
        self.turret_timer = max(0, self.turret_timer - dt)
        if not self.turret_timer:
            x, y = self.turret_room['emitters'][self.next_turret]
            targets = self.turret_room.get('shotTargets')
            if targets:
                tx, ty = targets[self.next_turret]
                dx, dy = tx - x, ty - y
            elif 'directions' in self.turret_room:
                dx, dy = self.turret_room['directions'][self.next_turret]
            else:
                target_x = max(self.turret_room['emitters'][0][0],
                               min(self.turret_room['emitters'][1][0], player.x))
                dx, dy = target_x - x, max(3, player.y - y)
            length = math.hypot(dx, dy)
            self.projectiles.append(Projectile(x, y, dx / length, dy / length, 'enemy',
                                               8, length if targets else 12, 8, element='lightning'))
            self.sound_events.append('electric')
            self.next_turret = 1 - self.next_turret
            self.turret_timer = .85

    def update_puzzle(self, dt):
        if self.block_direction is None:
            return
        dx, dy = self.direction(self.block_direction)
        px, py = self.puzzle['plate']
        centered = self.puzzle.get('centeredSlide')
        distance = self.wind_push_speed * dt
        parts = math.ceil(distance / .06)
        step = distance / parts
        for _ in range(parts):
            bx, by = self.block
            look_ahead = step
            if centered:
                # 다음 칸이 막혔으면 벽 앞 칸의 중심에서 멈춘다.
                forward = bx * dx + by * dy
                look_ahead = math.floor(forward - .5) + 1.5 - forward
            travel = min(step, look_ahead)
            nx, ny = bx + dx * look_ahead, by + dy * look_ahead
            samples = max(1, math.ceil(look_ahead / .08))
            # 다음 칸까지 앞면이 지나가는 범위를 검사해 칸 사이의 얇은 벽도 막는다.
            blocked = any(
                self.tile(bx + dx * forward - dy * side, by + dy * forward + dx * side,
                          ignore_block=True) >= 3
                for index in range(samples + 1)
                for forward in (.49 + look_ahead * index / samples,)
                for side in (-.49, -.32, -.16, 0, .16, .32, .49)
            )
            if blocked or (self.trial and not contains(self.puzzle['yard'], nx, ny)) or any(
                    self.tile(nx + sx, ny + sy, ignore_block=True) >= 3
                    for sx in (-.49, .49) for sy in (-.49, .49)):
                self.block_direction = None
                break
            x, y = bx + dx * travel, by + dy * travel
            if centered and any(actor.active and not actor.falling
                                and abs(actor.x - x) < .49 + self.radius
                                and abs(actor.y - y) < .49 + self.radius
                                for actor in (self.player, *self.enemies)):
                break
            self.block = x, y
            tolerance = 1e-8 if centered else .36
            at_plate = abs(x - px) <= tolerance and abs(y - py) <= tolerance
            if at_plate:
                self.block = px, py
                self.plate_pressed = True
                self.block_direction = None
                label = {4: '석교 개방', 5: '정비실 개방', 9: '서쪽 수로 배수'}.get(self.stage, '석문 개방')
                self.feedback.append(Feedback(px, py - .5, label, True, .8, .8))
                break

    @property
    def sluice_ready(self):
        return not self.sluice or (self.sluice_wheel and self.sluice_pump and self.extinguished == {0})

    @property
    def sluice_open(self):
        return self.sluice_ready and (not self.garden or self.garden_gate_time >= self.garden_gate_seconds)

    @property
    def branches_open(self):
        if self.trial:
            return self.trial_flow(1) == 1
        return not self.data.get('requiresBranches') or (
            self.stone_gate_open and len(self.extinguished) == len(self.fire_barriers)
            and self.conductor_vine_time >= self.conductor_vine['burnDuration'])

    def turn_sluice_wheel(self):
        if self.sluice and self.vine_open and self.extinguished == {0}:
            x, y = self.sluice['wheel']
            if math.hypot(self.player.x-x, self.player.y-y) <= .9:
                self.sluice_wheel = True

    def connect_power(self):
        if not self.power_puzzle or self.power_connected or self.power_flash or self.ingest_elapsed >= 0:
            return
        x, y = self.power_puzzle['switch']
        if math.hypot(self.player.x - x, self.player.y - y) > .9:
            return
        if not self.branches_open:
            return
        if self.power_levels == self.power_targets:
            self.power_connected = True
        elif self.trial:
            self.trial_wrong = {i for i, (level, target) in enumerate(zip(self.power_levels, self.power_targets))
                                if level != target}
            self.power_flash = .8
        else:
            self.power_levels[:] = [0, 0, 0]
            self.power_flash = .35

    def trial_flow(self, index):
        if index not in self.trial_returns:
            return 0.0
        started = self.trial_switch_times[index]
        if started is None:
            # 이어하기는 이미 당긴 레버의 흐름이 도착한 상태로 재개한다.
            return 1.0
        duration = (1.8, 1.35)[index]
        return min(1.0, (self.elapsed - started) / duration)

    @property
    def trial_laser_locked(self):
        return self.trial_flow(0) == 1

    @property
    def trial_wheel_open(self):
        return self.trial_wheel_time >= self.trial_wheel_reveal_seconds

    def trial_wheel_obstacles(self):
        left, top, right, bottom = self.trial['wheelGate']
        if not self.trial_wheel_open:
            return ((left, top, right, bottom),)
        gap_left, gap_right = self.trial['wheelOpening']
        return ((left, top, gap_left, bottom), (gap_right, top, right, bottom))

    def trial_sweep_bounds(self):
        if not self.trial or self.trial_laser_locked:
            return ()
        amplitude, _ = self.trial['laserSweep']
        margin = amplitude + self.trial_lasers.beam_half_height
        return tuple((min(start, end), y-margin, max(start, end), y+margin)
                     for start, end, y in self.trial_lasers.lasers)

    def in_trial_sweep(self, x, y):
        r = self.radius
        return any(left-r < x < right+r and top-r < y < bottom+r
                   for left, top, right, bottom in self.trial_sweep_bounds())

    def conductor_powered(self, index):
        if not self.trial or index == 1:
            return True
        return self.branches_open if index == 0 else 1 in self.trial_returns

    def interact_trial(self):
        if not self.trial or not self.vine_open:
            return
        for i, point in enumerate(self.trial['switches']):
            if i not in self.trial_returns and (i == 0 or self.trial_laser_locked):
                if math.dist((self.player.x, self.player.y), point) <= .9:
                    self.trial_returns.add(i)
                    self.trial_switch_times[i] = self.elapsed
                    message = '물이 동쪽 물레로 흐른다' if i == 0 else '전력이 서쪽 단자로 흐른다'
                    self.feedback.append(Feedback(*point, message, True))

    @property
    def active_lasers(self):
        if self.debug_cleared:
            return None
        if self.trial:
            return self.trial_lasers if 1 not in self.trial_returns else None
        return self.quarry

    @property
    def boss_exposed(self):
        return self.guardian is not None and self.guardian.vulnerable

    def reset_stone_block(self):
        reset = self.puzzle and self.puzzle.get('reset')
        if not reset or self.plate_pressed or self.ingest_elapsed >= 0:
            return
        if math.hypot(self.player.x - reset[0], self.player.y - reset[1]) > .9:
            return
        x, y = self.puzzle['start']
        if any(actor.active and abs(actor.x - x) < .49 + self.radius
               and abs(actor.y - y) < .49 + self.radius for actor in (self.player, *self.enemies)):
            return
        if any(t.kind == 'wall' and t.bounds[0] < x + .49 and t.bounds[2] > x - .49
               and t.bounds[1] < y + .49 and t.bounds[3] > y - .49 for t in self.earth_terrain):
            return
        self.block = x, y
        self.block_direction = None
        self.feedback.append(Feedback(reset[0], reset[1] - .45, '돌 복귀', True))

    def update_sources(self, dt):
        for source in self.sources:
            source.update(dt)
            if source.id == 'first-orb':
                release = {'descending': self.reservoir, 'igniting': self.forge,
                           'gathering': self.windmill, 'charging': self.capacitor}.get(source.phase)
                if release and source.age >= release['releaseSeconds']:
                    source.phase = 'orb'
                continue
            respawn = (self.puzzle and source.element == 'wind') or (self.turret_room and source.element == 'earth') or (self.power_puzzle and source.element == 'lightning')
            if ((respawn or source.id in self.respawning_sources) and source.phase == 'consumed' and source.id != self.ingest_source
                    and self.inventory[source.element] < 2 and source.age >= (3 if self.boss else 8)
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
            self.sound_events.append('ingest')
            source.phase, self.ingest_consumed = 'consumed', True
            if not (self.windmill and source.id == 'first-orb'):
                source.age = 0
        if self.ingest_elapsed >= self.tuning.ingest_duration:
            self.sound_events.append(f'switch-{source.element}')
            self.inventory[source.element] += 1
            self.selected = source.element
            if self.selected != 'lightning':
                self.lightning_charged = False
            self.ingest_elapsed, self.ingest_source = -1, None
            self.ingest_consumed = False
            self.player.animation_time = 0
            if self.debug_cleared and source.id == 'first-orb':
                self.update_power_circuit(0)

    @property
    def reservoir_opening(self):
        if not self.reservoir:
            return 0
        source = self.sources[-1]
        if source.phase == 'sealed':
            return 0
        return min(1, source.age / .36) if source.phase == 'descending' else 1

    @property
    def reservoir_flooded(self):
        return self.reservoir_opening > .65

    def standing_in_water(self, x, y):
        return self.reservoir_flooded and contains(RESERVOIR_BED, x, y)

    def update_acquisition(self, interact=False):
        trial = self.acquisition
        if not trial or self.ingest_elapsed >= 0:
            return
        player = self.player
        source = self.sources[-1]
        final_switch = trial.get('finalSwitch')
        if (interact and final_switch and self.acquisition_relay and self.acquisition_power_elapsed < 0
                and math.hypot(player.x - final_switch[0], player.y - final_switch[1]) <= 1.1):
            self.acquisition_power_elapsed = 0
        if source.phase != 'sealed':
            return
        if (any(enemy.active for enemy in self.enemies[:trial['guards']])
                or not self.extinguished.issuperset(trial.get('preFire', ()))
                or trial.get('preVine') and not self.vine_open
                or trial.get('prePlate') and not self.plate_pressed):
            return
        switch = trial.get('switch')
        if switch and (not interact or math.hypot(player.x - switch[0], player.y - switch[1]) > 1.1):
            return
        if self.reservoir:
            source.phase = 'descending'
        elif self.forge:
            source.phase = 'igniting'
        elif self.windmill:
            source.phase = 'gathering'
        elif self.capacitor:
            source.phase = 'charging'
        else:
            source.phase = 'orb'
        source.age = 0

    def update_power_circuit(self, dt):
        if not self.power_circuit or self.acquisition_power:
            return
        if self.debug_cleared and self.learned_room_element:
            self.acquisition_relay = self.acquisition_power = True
            self.acquisition_power_elapsed = self.power_circuit['openAt']
            return
        if self.acquisition_power_elapsed < 0:
            return
        circuit = self.power_circuit
        next_stop = circuit['doorAt'] if self.remaining_enemies else circuit['openAt']
        self.acquisition_power_elapsed = min(next_stop, self.acquisition_power_elapsed + dt)
        self.acquisition_power = self.acquisition_power_elapsed >= circuit['openAt']

    @property
    def powered_door_lift(self):
        if not self.power_circuit or self.remaining_enemies:
            return 0
        start, end = self.power_circuit['doorAt'], self.power_circuit['openAt']
        return max(0, min(1, (self.acquisition_power_elapsed - start) / (end - start)))

    @property
    def learned_room_element(self):
        return self.acquisition and bool(self.inventory[self.acquisition['element']])

    @property
    def permanent_bridge(self):
        if self.quarry and self.debug_cleared:
            return self.earth_bridge
        if self.acquisition and (self.turrets_stopped if self.turret_room else self.plate_pressed
                                 and self.gate_time >= self.gate_open_seconds):
            return self.acquisition.get('bridge')
        return None

    def hazard_state(self, hazard):
        if self.debug_cleared or (hazard['kind'] == 'shock' and self.sources[-1].phase != 'sealed'):
            return 'idle', 0
        phase = (self.elapsed + hazard.get('offset', 0)) % 3.2
        if phase < 1.25:
            return 'idle', 0
        if phase < 2.2:
            return 'warning', (phase - 1.25) / .95
        if phase < 2.86:
            return 'active', (phase - 2.2) / .66
        return 'retract', (phase - 2.86) / .34

    def enemy_awake(self, enemy):
        if self.acquisition:
            guard = any(enemy is actor for actor in self.enemies[:self.acquisition['guards']])
            return ((guard or self.learned_room_element)
                    and (enemy.attack_elapsed >= 0
                         or math.hypot(self.player.x - enemy.x, self.player.y - enemy.y) < 7.5))
        if self.conductor_vine and self.vine_gate:
            return self.aggro and (enemy.y >= self.vine_gate['y'] or (
                self.vine_open and (enemy.y >= self.puzzle['gate'][3] or self.stone_gate_open)))
        if self.power_puzzle and enemy.y < self.power_puzzle['gate'][1]:
            return self.aggro and self.power_gate_open
        if self.data.get('fireAggroTrigger') and enemy.element == 'fire':
            return self.fire_aggro
        if self.fire_barriers and self.vine_gate:
            return self.aggro and (enemy.y >= self.vine_gate['y'] or self.vine_open)
        if self.vine_gate and enemy.element == 'wind':
            return self.vine_open and self.aggro
        if self.puzzle and self.puzzle.get('reset'):
            gate_bottom = self.puzzle['gate'][3]
            if enemy.y >= gate_bottom:
                return self.aggro
            return self.aggro and self.stone_gate_open and self.player.y < gate_bottom
        return self.aggro and self.stone_gate_open and (not self.turret_room or self.turrets_stopped)

    @property
    def remaining_enemies(self):
        return sum(e.active for e in self.enemies)

    @property
    def exit_open(self):
        if self.guardian:
            return self.guardian.gate_progress >= 1
        return (self.remaining_enemies == 0 and self.vine_open and self.stone_gate_open
                and len(self.extinguished) == len(self.fire_barriers)
                and self.power_gate_open and self.sluice_open and self.branches_open
                and (not self.acquisition or self.learned_room_element
                     and (not self.acquisition.get('finalSwitch') or self.acquisition_power))
                and (not self.data.get('requiredBridge') or self.bridge_crossed)
                and (not self.turret_room or self.turrets_stopped))

    @property
    def final_reward(self):
        if (self.guardian and self.guardian.fall >= FALL_SECONDS
                and self.guardian.reward_scene_elapsed is None
                and not self.guardian.reward_tasted and not self.outcome):
            guardian = self.enemies[0]
            return guardian.x, guardian.y
        return None

    @property
    def can_claim_final_reward(self):
        point = self.final_reward
        player = self.player
        return (point is not None and player.active and not player.falling
                and math.dist((player.x, player.y), point) < 1)

    def use_final_reward(self, keys):
        if not self.can_claim_final_reward:
            return
        guardian = self.guardian
        if guardian.reward_loaded:
            if 'ingest' in keys:
                guardian.reward_scene_elapsed = 0.0
                self.player.attack_elapsed = -1
                self.player.moving = False

    def insert_final_orb(self, element):
        if not self.can_claim_final_reward or not self.inventory.get(element):
            return False
        guardian = self.guardian
        if element in guardian.reward_orbs:
            return False
        guardian.reward_orbs.add(element)
        self.inventory[element] = 0
        self.restore_selected_element(self.selected)
        guardian.reward_loaded = len(guardian.reward_orbs) == len(ELEMENTS)
        return True

    @property
    def vine_open(self):
        return self.vine_gate is None or self.vine_time >= self.vine_gate['burnDuration']

    def vine_contains(self, x, y):
        gate = self.vine_gate
        return (not self.vine_open and gate['x'] <= x < gate['x'] + gate['width']
                and gate['y'] <= y < gate['y'] + gate['height'])

    def conductor_vine_contains(self, x, y):
        gate = self.conductor_vine
        return (gate and self.conductor_vine_time < gate['burnDuration']
                and gate['x'] <= x < gate['x'] + gate['width']
                and gate['y'] <= y < gate['y'] + gate['height'])

    def burning_barrier(self, x, y):
        return next((index for index, (left, top, right, bottom) in enumerate(self.fire_barriers)
                     if index not in self.extinguished and left <= x < right and top <= y < bottom), None)

    @staticmethod
    def direction(facing):
        return {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[facing]

    @staticmethod
    def facing(dx, dy):
        return ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')

    def line_clear(self, x, y, tx, ty, *, ignore_block=False, include_rim=False, airborne=False):
        steps = max(1, math.ceil(math.hypot(tx-x, ty-y) / .1))
        for i in range(steps + 1):
            px, py = x + (tx - x) * i / steps, y + (ty - y) * i / steps
            if self.tile(px, py, ignore_block=ignore_block, airborne=airborne) == 3:
                return False
            if include_rim and any(left <= px < right and top <= py < bottom
                                   for left, top, right, bottom in self.wall_bounds.values()):
                return False
        return True

    def start_attack(self, actor):
        if not actor.active or actor.falling or actor.attack_elapsed >= 0 or actor.attack_cooldown > 0 or (actor.kind == 'hero' and self.ingest_elapsed >= 0):
            return False
        if self.outcome or (actor.kind != 'hero' and not self.player.active):
            return False
        actor.attack_elapsed = 0
        actor.attack_emitted = False
        actor.attack_element = self.selected if actor.kind == 'hero' else actor.element
        if actor.kind == 'hero':
            self.lightning_attack = self.lightning_charged
            self.lightning_charged = False
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

    def damage(self, actor, amount, direction=(0, 0), *, attack_element=None):
        if not actor.active or actor.falling or actor.invulnerable > 0:
            return False
        guardian = self.guardian if self.guardian and actor is self.enemies[0] else None
        if guardian:
            if not self.boss_exposed:
                return False
            if any(direction):
                actor.knockback = direction
                actor.knockback_left = .05
            direction = (0, 0)
        actor.hp = max(0, actor.hp - amount)
        actor.hit_flash = .16
        self.feedback.append(Feedback(actor.x, actor.y-1, str(amount), actor.kind != 'hero'))
        if actor.kind == 'hero':
            actor.invulnerable = self.tuning.invulnerability
            self.sound_events.append('player-hit')
        elif any(direction) and not actor.wind_sliding:
            actor.knockback = direction
            actor.knockback_left = self.tuning.knockback_seconds
        if actor.kind != 'hero' and amount > 0:
            cue = 'weakness' if BEATS.get(attack_element) == actor.element else 'enemy-hit'
            self.sound_events.append(cue)
        if actor.hp == 0:
            self.sound_events.append('defeat')
            actor.active = False
            actor.attack_elapsed = -1
            self.feedback.append(Feedback(actor.x, actor.y-.5, '', actor.kind != 'hero', .3, .3))
            if actor.kind == 'hero':
                self.outcome = 'dead'
                self.projectiles.clear()
        if guardian:
            guardian.damaged(self, actor)
        return True

    def attack_tick(self, actor, dt):
        if actor.attack_elapsed < 0:
            return
        actor.attack_elapsed += dt
        if not actor.attack_emitted and actor.attack_elapsed >= self.tuning.attack_event:
            actor.attack_emitted = True
            if actor.kind == 'hero':
                self.sound_events.append('player-attack')
            dx, dy = actor.attack_direction
            if actor.kind != 'hero':
                self.sound_events.append('enemy-attack')
            if actor.kind == 'melee':
                distance = math.hypot(self.player.x-actor.x, self.player.y-actor.y)
                toward = (self.player.x-actor.x)*dx + (self.player.y-actor.y)*dy
                if distance <= self.tuning.melee_range and toward >= 0 and self.line_clear(actor.x, actor.y, self.player.x, self.player.y):
                    self.damage(self.player, self.tuning.enemy_damage)
                self.feedback.append(Feedback(actor.x+dx*.55, actor.y+dy*.55-.35, '', False, .18, .18))
            elif actor.kind != 'hero' or not self.lightning_attack or not self.cast_lightning():
                hero = actor.kind == 'hero'
                if hero and self.lightning_attack:
                    self.lightning_attack = False
                    self.lightning_charged = True
                elemental = hero and actor.attack_element != 'neutral'
                # 루트에서부터 진행시켜 바로 앞의 벽·적도 건너뛰지 않게 한다.
                if hero and self.guardian and self.guardian.reward_tasted:
                    self.projectiles.append(Projectile(actor.x, actor.y, dx, dy, 'hero', 6, 4.5,
                                                       self.tuning.elemental_damage, element='mixed'))
                else:
                    self.projectiles.append(Projectile(actor.x, actor.y, dx, dy, 'hero' if hero else 'enemy',
                        self.tuning.elemental_speed if elemental else self.tuning.neutral_speed if hero else self.tuning.enemy_shot_speed,
                        self.tuning.elemental_range if elemental else self.tuning.neutral_range if hero else self.tuning.enemy_shot_range,
                        self.tuning.elemental_damage if elemental else self.tuning.neutral_damage if hero else self.tuning.enemy_damage,
                        element=actor.attack_element))
        if actor.attack_elapsed >= self.tuning.attack_duration:
            actor.attack_elapsed = -1
            actor.animation_time = 0
            if actor.kind == 'hero' and self.lightning_attack:
                self.finish_lightning_attack()

    def finish_lightning_attack(self):
        self.lightning_attack = False
        self.selected = 'lightning' if self.inventory['lightning'] else 'neutral'

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
                        and (not self.trial or 0 in self.extinguished)
                        and shot.owner == 'hero' and shot.element == 'fire'):
                    self.vine_time = 0
                if (self.conductor_vine_contains(shot.x, shot.y) and self.conductor_vine_time < 0
                        and (not self.data.get('requiresBranches') or len(self.extinguished) == len(self.fire_barriers))
                        and shot.owner == 'hero' and shot.element == 'fire'):
                    self.conductor_vine_time = 0
                if self.fire_barriers and shot.owner == 'hero' and shot.element == 'water':
                    barrier = self.burning_barrier(shot.x, shot.y)
                    if barrier is not None:
                        if ((not self.trial or (self.stone_gate_open and contains(
                                self.trial['basin'], self.player.x, self.player.y)))
                                and (not self.data.get('orderedFireBarriers')
                                or all(index in self.extinguished for index in range(barrier)))):
                            self.extinguished.add(barrier)
                            self.steam[barrier] = self.elapsed
                        shot.active = False
                        break
                hits_rim = self.turret_room and any(left <= shot.x < right and top <= shot.y < bottom
                                                    for left, top, right, bottom in self.wall_bounds.values())
                if (self.tile(shot.x, shot.y, airborne=True) == 3 or hits_rim
                        or not (0 <= shot.x < self.data['columns'] and 0 <= shot.y < self.data['rows'])):
                    shot.active = False
                    self.sound_events.append('impact')
                    self.feedback.append(Feedback(shot.x, shot.y-.4, '', shot.owner == 'hero', .16, .16))
                    break
                relay = self.acquisition and self.acquisition.get('relay')
                if (relay and shot.owner == 'hero' and shot.element == 'lightning'
                        and math.hypot(shot.x - relay[0], shot.y - relay[1]) <= .55):
                    self.acquisition_relay = True
                    self.acquisition_relay_flash = self.relay_flash_seconds
                    self.feedback.append(Feedback(*relay, '전도체 충전', True))
                    shot.active = False
                    break
                if self.sluice and shot.owner == 'hero' and shot.element == 'lightning':
                    x, y = self.sluice['pump']
                    if self.extinguished == {0} and math.hypot(x-shot.x, y-shot.y) <= .65:
                        self.sluice_pump = True
                        shot.active = False
                        break
                if self.power_puzzle and shot.owner == 'hero' and shot.element == 'lightning':
                    for index, (x, y) in enumerate(self.power_puzzle['conductors']):
                        if math.hypot(x - shot.x, y - shot.y) <= .5:
                            if (not self.power_connected and not self.power_flash
                                    and not self.conductor_vine_contains(x, y)
                                    and self.conductor_powered(index)
                                    and (not self.data.get('requiresBranches') or index != 2 or self.stone_gate_open)):
                                self.power_levels[index] = (self.power_levels[index] + 1) % 4
                                self.power_hits[index] = .25
                                self.feedback.append(Feedback(x, y - .4, '', True, .16, .16))
                            shot.active = False
                            break
                if not shot.active:
                    break
                targets = self.enemies if shot.owner == 'hero' else [self.player]
                for source in self.sources:
                    if source.solid and math.hypot(source.x-shot.x, source.y-shot.y) <= .53:
                        if shot.owner == 'hero' and source.hit(shot.element):
                            self.sound_events.append('break' if source.phase == 'breaking' else 'impact')
                        elif shot.owner != 'hero' and self.boss:
                            continue
                        shot.active = False
                        break
                if not shot.active:
                    break
                for actor in targets:
                    if not actor.active or actor.falling:
                        continue
                    guardian = self.guardian if self.guardian and actor is self.enemies[0] else None
                    reaches = (guardian.hits(actor,shot.x,shot.y) if guardian
                               else math.hypot(actor.x-shot.x,actor.y-shot.y) <= .42)
                    if reaches:
                        neutral_target = shot.owner == 'hero' and actor.element == 'neutral'
                        allowed = shot.owner != 'hero' or shot.element == 'neutral' or BEATS.get(shot.element) == actor.element or neutral_target
                        if allowed:
                            hit = self.damage(actor, self.tuning.neutral_target_damage if neutral_target else shot.damage,
                                              (shot.dx, shot.dy) if shot.owner == 'hero' and shot.element == 'neutral' else (0, 0),
                                              attack_element=shot.element if shot.owner == 'hero' else None)
                            if hit and guardian:
                                self.feedback.append(Feedback(shot.x,shot.y-GUARDIAN_SHOT_LIFT,'',True,.17,.17))
                            elif not hit and guardian and not self.boss_exposed:
                                self.sound_events.append('blocked')
                            if (hit and actor.active and shot.owner == 'hero' and shot.element == 'fire'
                                    and actor.element == BEATS['fire']
                                    and (not self.guardian or self.guardian.vulnerable)):
                                if not actor.burn_ticks:
                                    actor.burn_delay = .6
                                actor.burn_ticks = 3
                        else:
                            self.feedback.append(Feedback(actor.x, actor.y-1, '차단', False))
                            self.sound_events.append('blocked')
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

    @property
    def power_gate_open(self):
        return not self.power_puzzle or (self.power_connected and self.power_gate_time >= self.gate_open_seconds)

    @staticmethod
    def inside_floor(x, y, polygon):
        inside = False
        for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                inside = not inside
        return inside

    def intersects_windmill_base(self, x, y, radius=0):
        if not self.windmill:
            return False
        left, top, right, bottom = self.windmill['base']
        return left - radius <= x < right + radius and top - radius <= y < bottom + radius

    def index_garden_cells(self):
        # The garden has rectangular fixtures and integer-aligned stone platforms.
        cells = {(x, y): [] for l, t, r, b in self.reference_art['walkable']
                 for x in range(l, r) for y in range(t, b)}
        vine = self.vine_gate
        vine_rect = (vine['x'], vine['y'], vine['x'] + vine['width'], vine['y'] + vine['height'])
        fixtures = [(bounds, 'cover') for bounds in self.reference_art['cover']]
        fixtures.append((vine_rect, 'vine'))
        fixtures.extend((bounds, 'gate') for bounds in (self.sluice['gate'], *self.sluice['returnGates']))
        fixtures.extend((bounds, i) for i, bounds in enumerate(self.fire_barriers))
        for bounds, kind in fixtures:
            left, top, right, bottom = bounds
            for x in range(math.floor(left), math.ceil(right)):
                for y in range(math.floor(top), math.ceil(bottom)):
                    if (x, y) in cells:
                        cells[x, y].append((bounds, kind))
        return cells

    def garden_tile(self, x, y, ignore_earth):
        fixtures = self.garden_cells.get((math.floor(x), math.floor(y)))
        if fixtures is None:
            return 4
        for (left, top, right, bottom), kind in fixtures:
            if left <= x < right and top <= y < bottom:
                if (kind == 'cover' or kind == 'vine' and not self.vine_open
                        or kind == 'gate' and not self.sluice_open
                        or isinstance(kind, int) and kind not in self.extinguished):
                    return 3
        if not ignore_earth:
            for terrain in self.earth_terrain:
                if terrain.contains(x, y):
                    return 3 if terrain.kind == 'wall' else 0
        return 0

    def index_trial_cells(self):
        cells = {(x, y): [] for left, top, right, bottom in self.reference_art['walkable']
                 for x in range(left, right) for y in range(top, bottom)}
        for left, top, right, bottom in self.reference_art['cover']:
            for x in range(math.floor(left), math.ceil(right)):
                for y in range(math.floor(top), math.ceil(bottom)):
                    if (x, y) in cells:
                        cells[x, y].append((left, top, right, bottom))
        return cells

    def tile(self, x, y, *, ignore_block=False, ignore_earth=False, airborne=False):
        if self.trial:
            if any(i not in self.trial_returns and contains(gate, x, y)
                   for i, gate in enumerate(self.trial['returns'])):
                return 3
            if not self.trial_laser_locked and contains(self.trial['serviceGate'], x, y):
                return 3
            if any(contains(bounds, x, y) for bounds in self.trial_wheel_obstacles()):
                return 3
        if self.garden_cells is not None:
            return self.garden_tile(x, y, ignore_earth)
        if self.quarry:
            if (not self.stone_gate_open or not self.bridge_crossed) and any(
                    contains(bounds, x, y) for bounds in self.quarry.gates):
                return 3
            if not ignore_earth:
                for terrain in self.earth_terrain:
                    if terrain.contains(x, y):
                        return 3 if terrain.kind == 'wall' else 0
            if self.vine_contains(x, y) or (not self.debug_cleared and not ignore_block and abs(x-self.block[0]) < .49
                                           and abs(y-self.block[1]) < .49):
                return 3
            if self.debug_cleared and contains(self.earth_bridge, x, y):
                return 0
            return self.quarry.ground(x, y, airborne)
        if self.intersects_windmill_base(x, y):
            return 3
        if self.acquisition and not self.learned_room_element:
            if any(left <= x < right and top <= y < bottom
                   for left, top, right, bottom in self.acquisition.get('passages', ())):
                return 3
        if self.fire_barriers and self.burning_barrier(x, y) is not None:
            return 3
        if not self.sluice_open:
            gates = (self.sluice['gate'], *self.sluice.get('returnGates', ()))
            if any(left <= x < right and top <= y < bottom for left, top, right, bottom in gates):
                return 3
        if not self.power_gate_open:
            x0, y0, x1, y1 = self.power_puzzle['gate']
            if x0 <= x < x1 and y0 <= y < y1:
                return 3
        if not ignore_earth:
            for terrain in self.earth_terrain:
                if terrain.contains(x, y):
                    return 3 if terrain.kind == 'wall' else 0
        if self.puzzle:
            x0, y0, x1, y1 = self.puzzle['gate']
            if (not self.stone_gate_open or self.data.get('requiredBridge') and not self.bridge_crossed) and x0 <= x < x1 and y0 <= y < y1:
                return 3
            if (not self.debug_cleared and not ignore_block
                    and abs(x - self.block[0]) < .49 and abs(y - self.block[1]) < .49):
                return 3
        if self.vine_contains(x, y) or self.conductor_vine_contains(x, y):
            return 3
        bridge = self.permanent_bridge
        if bridge and bridge[0] <= x < bridge[2] and bridge[1] <= y < bridge[3]:
            return 0
        if self.guardian:
            obstacle = self.guardian.tile(x, y)
            if obstacle is not None:
                return obstacle
        if self.trial_cells is not None:
            cover = self.trial_cells.get((math.floor(x), math.floor(y)))
            return 4 if cover is None else 3 if any(contains(bounds, x, y) for bounds in cover) else 0
        if self.reference_art:
            for x0, y0, x1, y1 in self.reference_art['cover']:
                if x0 <= x < x1 and y0 <= y < y1:
                    return 3
            for x0, y0, x1, y1 in self.reference_art['walkable']:
                if x0 <= x < x1 and y0 <= y < y1:
                    return 0
            if any(self.inside_floor(x, y, polygon)
                   for polygon in self.reference_art.get('floorPolygons', ())):
                return 0
            if self.reference_art.get('openCliffs'):
                if airborne and self.reference_art.get('shotsCrossAbyss'):
                    return 4
                if any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in self.reference_art['openCliffs']):
                    return 4
                return 3
            return 4
        x, y = math.floor(x), math.floor(y)
        if 0 <= x < self.data['columns'] and 0 <= y < self.data['rows']:
            return self.data['tiles'][y][x]
        return 4

    def fits(self, x, y, safe=False, *, ignore_earth=False, ignore_block=False):
        lasers = self.active_lasers
        if lasers and lasers.touches_beam(x, y, self.radius, () if ignore_earth else self.earth_terrain):
            return False
        if (self.reference_art and self.reference_art.get('walledBoundary')
                and self.tile(x, y, ignore_earth=ignore_earth, ignore_block=ignore_block) == 4):
            return False
        for dx in (-self.radius, self.radius):
            for dy in (-self.radius, self.radius):
                tile = self.tile(x + dx, y + dy, ignore_earth=ignore_earth, ignore_block=ignore_block)
                if tile == 3 or (safe and tile >= 3):
                    return False
        if any(s.solid and math.hypot(x-s.x, y-s.y) < .42+self.radius for s in self.sources):
            return False
        return True

    def blocked_by_wall(self, x, y, old_x, old_y, *, include_reference_rim=True):
        radius = self.radius
        # 세로 투영에서 발밑 충돌 폭도 함께 줄인다.
        depth = radius if self.reference_art else radius * TILE_HEIGHT / TILE_WIDTH
        walls = self.reference_movement_walls if include_reference_rim and self.reference_art else self.wall_bounds.values()
        for left, top, right, bottom in walls:
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
        if self.quarry:
            topology = self.quarry.obstacles(self)
        elif self.garden:
            topology = self.garden_obstacles()
        elif self.trial:
            topology = self.trial_obstacles()
        else:
            topology = (self.sluice_open, self.vine_open, self.stone_gate_open, self.power_gate_open, self.block,
                        self.turrets_stopped, tuple(s.solid for s in self.sources),
                        tuple((t.kind, t.bounds) for t in self.earth_terrain), frozenset(self.extinguished))
        key = goal, topology
        if self.navigation_cache and self.navigation_cache[0] == key:
            return self.navigation_cache[1]
        if self.garden or self.quarry or self.trial:
            distances = self.cached_reference_distances(goal, *self.reference_links(topology))
            self.navigation_cache = key, distances
            return distances
        distances, queue = {goal: 0}, deque([goal])
        while queue:
            x, y = queue.popleft()
            for nx, ny in self.neighbors(x, y):
                if (nx, ny) not in distances and self.reference_link(x / 2, y / 2, nx / 2, ny / 2):
                    distances[nx, ny] = distances[x, y] + 1
                    queue.append((nx, ny))
        self.navigation_cache = key, distances
        return distances

    def garden_obstacles(self):
        active = [t.bounds for t in self.earth_terrain]
        active.extend(bounds for i, bounds in enumerate(self.fire_barriers) if i not in self.extinguished)
        if not self.sluice_open:
            active.extend((self.sluice['gate'], *self.sluice['returnGates']))
        if not self.vine_open:
            vine = self.vine_gate
            active.append((vine['x'], vine['y'], vine['x'] + vine['width'], vine['y'] + vine['height']))
        return frozenset(map(tuple, active))

    def trial_obstacles(self):
        active = list(self.garden_obstacles())
        active.extend(gate for i, gate in enumerate(self.trial['returns']) if i not in self.trial_returns)
        active.extend(self.trial_wheel_obstacles())
        if not self.trial_laser_locked:
            active.append(self.trial['serviceGate'])
        if not self.stone_gate_open:
            active.append(self.puzzle['gate'])
        if not self.power_gate_open:
            active.append(self.power_puzzle['gate'])
        if self.active_lasers:
            if self.trial_laser_locked:
                active.extend(self.active_lasers.obstacle_bounds(self.earth_terrain))
            else:
                # 닫힌 회랑 전체의 빔 범위를 기록해 고정될 때 한 번만 다시 계산한다.
                active.extend(self.trial_sweep_bounds())
        x, y = self.block
        active.append((x-.49, y-.49, x+.49, y+.49))
        return frozenset(map(tuple, active))

    def reference_links(self, obstacles):
        if self.reference_path_cache is None:
            self.reference_path_cache = obstacles, {}, {}
        previous, links, samples = self.reference_path_cache
        for left, top, right, bottom in previous ^ obstacles:
            # A change can touch a sampled position or an edge leaving its neighbor.
            for cache, scale, margin in ((samples, 8, self.radius), (links, 2, self.radius + .5)):
                for x in range(math.floor((left-margin)*scale), math.ceil((right+margin)*scale)+1):
                    for y in range(math.floor((top-margin)*scale), math.ceil((bottom+margin)*scale)+1):
                        cache.pop((x, y), None)
        self.reference_path_cache = obstacles, links, samples
        return links, samples

    def preload_reference_paths(self):
        # Closed gates split the room into regions. Warm each region before the first frame.
        if self.garden:
            obstacles = self.garden_obstacles()
            left, _, right, bottom = self.sluice['gate']
            anchors = (((left+right)/2, bottom+.5), self.sluice['wheel'], self.sluice['pump'])
        elif self.trial:
            obstacles = self.trial_obstacles()
            anchors = self.trial['switches']
        else:
            obstacles = self.quarry.obstacles(self)
            anchors = self.quarry.config['navigationAnchors']
        links, samples = self.reference_links(obstacles)
        exit_point = self.data['plannedExit']
        for x, y in ((self.player.x, self.player.y), *anchors, (exit_point['x'], exit_point['y'])):
            goal = next((p for p in self.reference_anchors(x, y)
                         if self.fits(p[0]/2, p[1]/2, safe=True)), None)
            if goal is not None and goal not in links:
                self.cached_reference_distances(goal, links, samples)

    def cached_reference_distances(self, goal, links, safe_samples):
        distances, queue = {goal: 0}, deque([goal])
        while queue:
            cell = queue.popleft()
            if cell not in links:
                # Each lattice edge is half a tile long. Sample at the same spacing as reference_link.
                x, y = cell
                adjacent = []
                for nx, ny in self.neighbors(x, y):
                    for step in range(1, 5):
                        sample = (4*x + (nx-x)*step, 4*y + (ny-y)*step)
                        if sample not in safe_samples:
                            safe_samples[sample] = self.fits(sample[0]/8, sample[1]/8, safe=True)
                        if not safe_samples[sample]:
                            break
                    else:
                        adjacent.append((nx, ny))
                links[cell] = adjacent
            for neighbor in links[cell]:
                if neighbor not in distances:
                    distances[neighbor] = distances[cell] + 1
                    queue.append(neighbor)
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
        key = (goal, self.stone_gate_open, self.vine_open, self.turrets_stopped, self.block,
               self.learned_room_element, frozenset(self.extinguished),
               tuple(t.bounds for t in self.earth_terrain), self.conductor_vine_time >= 0
               and self.conductor_vine and self.conductor_vine_time >= self.conductor_vine['burnDuration'])
        if self.acquisition and self.navigation_cache and self.navigation_cache[0] == key:
            return self.navigation_cache[1]
        distances, queue = {goal: 0}, deque([goal])
        while queue:
            x, y = queue.popleft()
            for pos in self.neighbors(x, y):
                if pos not in distances and self.fits(pos[0]+.5,pos[1]+.5,safe=True):
                    distances[pos] = distances[(x, y)] + 1
                    queue.append(pos)
        if self.acquisition:
            self.navigation_cache = key, distances
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

    def track_bridge_crossing(self, previous_x, previous_y):
        left, top, right, bottom = self.earth_bridge
        x, y = self.player.x, self.player.y
        if not top <= y < bottom:
            self.bridge_entry_side = None
        elif any(t.kind == 'floor' and t.contains(x, y) for t in self.earth_terrain):
            if top <= previous_y < bottom:
                if previous_x < left:
                    self.bridge_entry_side = 'left'
                elif previous_x >= right:
                    self.bridge_entry_side = 'right'
        else:
            self.bridge_crossed = ((self.bridge_entry_side == 'left' and x >= right)
                                   or (self.bridge_entry_side == 'right' and x < left))
            self.bridge_entry_side = None

    def update(self, keys, dt):
        if not math.isfinite(dt) or dt <= 0 or self.outcome:
            return
        if self.guardian and self.guardian.collapsing:
            keys = ()
        if 'debug-clear' in keys:
            self.debug_clear()
        dt = min(dt, .05)
        if self.vine_gate and not self.vine_open and self.vine_time >= 0:
            self.vine_time = min(self.vine_time + dt, self.vine_gate['burnDuration'])
        if self.conductor_vine and self.conductor_vine_time >= 0:
            self.conductor_vine_time = min(self.conductor_vine_time + dt, self.conductor_vine['burnDuration'])
        self.elapsed += dt
        if self.trial_lasers and 1 not in self.trial_returns:
            amplitude, period = self.trial['laserSweep']
            self.trial_lasers.row_offset = (amplitude * (1 - self.trial_flow(0))
                                            * math.sin(math.tau * self.elapsed / period))
        if self.trial and self.trial_laser_locked:
            self.trial_wheel_time += dt
        if self.garden:
            if self.sluice_wheel:
                self.garden_wheel_time = min(.5, self.garden_wheel_time + dt)
            if self.sluice_ready:
                self.garden_gate_time = min(self.garden_gate_seconds, self.garden_gate_time + dt)
            if self.exit_open:
                self.garden_exit_time = min(self.garden_exit_seconds, self.garden_exit_time + dt)
        self.update_power_circuit(dt)
        for terrain in self.earth_terrain:
            terrain.remaining -= dt
        self.earth_terrain[:] = [terrain for terrain in self.earth_terrain if terrain.remaining > 0]
        lasers = self.active_lasers
        if lasers and lasers.touches_beam(self.player.x, self.player.y, self.radius, self.earth_terrain):
            self.player.x, self.player.y, self.player.facing = self.safe
            self.player.knockback_left = 0
            self.sound_events.append('electric')
            self.feedback.append(Feedback(self.player.x, self.player.y, '레이저 복구', False))
        self.power_flash = max(0, self.power_flash - dt)
        self.acquisition_relay_flash = max(0, self.acquisition_relay_flash - dt)
        for index, time_left in enumerate(self.power_hits):
            self.power_hits[index] = max(0, time_left - dt)
        self.lightning_time = max(0, self.lightning_time - dt)
        if self.plate_pressed:
            gate_dt = dt
            if self.trial:
                # 저장된 gate_time의 개방 기준(.3초)은 유지하고 배수 속도만 늦춘다.
                gate_dt *= self.gate_open_seconds / self.trial['drainSeconds']
            self.gate_time = min(self.gate_open_seconds, self.gate_time + gate_dt)
        if self.power_connected:
            self.power_gate_time = min(self.gate_open_seconds, self.power_gate_time + dt)
        player = self.player
        self.update_sources(dt)
        for effect in self.feedback:
            effect.remaining -= dt
        self.feedback[:] = [f for f in self.feedback if f.remaining > 0]
        for actor in [player, *self.enemies]:
            actor.hit_flash = max(0, actor.hit_flash-dt)
            actor.invulnerable = max(0, actor.invulnerable-dt)
            actor.attack_cooldown = max(0, actor.attack_cooldown-dt)
            if actor.active and actor.burn_ticks:
                actor.burn_delay -= dt
                if actor.burn_delay <= 0:
                    actor.burn_ticks -= 1
                    actor.burn_delay = .6 if actor.burn_ticks else 0
                    self.damage(actor, 3)
        previous_movement = {id(e): e.moving for e in self.enemies}
        for enemy in self.enemies:
            enemy.moving = False
        if player.falling > 0:
            if self.guardian:
                self.guardian.step(self, dt)
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
        if 'connect' in keys:
            self.stop_turrets()
            self.interact_trial()
            self.connect_power()
            self.turn_sluice_wheel()
            self.reset_stone_block()
            self.update_acquisition(interact=True)
            if self.guardian:
                self.guardian.interact_pedestal(self, retrieve=False)
        if 'skill' in keys:
            self.skill()
        self.update_puzzle(dt)
        if 'ingest' in keys:
            self.start_ingest()
            if self.guardian:
                self.guardian.interact_pedestal(self, retrieve=True)
        ingesting = self.ingest_elapsed >= 0
        self.ingest_tick(dt)
        dx = int('d' in keys) - int('a' in keys)
        dy = int('s' in keys) - int('w' in keys)
        if ingesting or (self.guardian and self.guardian.summoning):
            dx = dy = 0
        length = math.hypot(dx, dy) or 1
        was_moving = player.moving
        speed = self.data['preview']['playerSpeed']
        previous_x, previous_y = player.x, player.y
        self.move(player, dx / length * speed * dt, dy / length * speed * dt)
        if self.data.get('requiredBridge') and not self.bridge_crossed:
            self.track_bridge_crossing(previous_x, previous_y)
        player.animate(dt, was_moving)
        tile = self.tile(player.x, player.y)
        self.spike_contact = not self.debug_cleared and tile == self.data['tileIds']['spikes']
        if self.spike_contact:
            self.damage(player, self.tuning.spike_damage)
            if self.outcome:
                return
        for hazard in self.data.get('movingHazards', ()):
            left, top, right, bottom = hazard['bounds']
            if left <= player.x < right and top <= player.y < bottom and self.hazard_state(hazard)[0] == 'active':
                self.spike_contact |= hazard['kind'] == 'spikes'
                self.damage(player, self.tuning.spike_damage)
                if self.outcome:
                    return
        if tile == 4:
            player.falling = self.data['preview']['fallSeconds']
            if self.lightning_attack:
                self.lightning_charged = not player.attack_emitted
                self.finish_lightning_attack()
            player.attack_elapsed = -1
            return
        if (tile < 3 and self.fits(player.x, player.y, safe=True)
                and self.fits(player.x, player.y, safe=True, ignore_earth=True)
                and not self.in_trial_sweep(player.x, player.y)):
            self.safe = player.x, player.y, player.facing
        self.update_turrets(dt)
        self.aggro = self.aggro or self.in_arena()
        if self.data.get('fireAggroTrigger'):
            r = self.data['fireAggroTrigger']
            self.fire_aggro = self.fire_aggro or (r['x'] <= player.x < r['x']+r['width'] and r['y'] <= player.y < r['y']+r['height'])
        if 'attack' in keys:
            self.start_attack(player)
        self.attack_tick(player, dt)
        if self.guardian:
            self.guardian.step(self, dt)
        regular_enemies = () if self.boss else self.enemies
        distances = self.distance_field() if any(
            enemy.active and enemy.kind == 'melee' and self.enemy_awake(enemy) for enemy in regular_enemies
        ) else {}
        for enemy in regular_enemies:
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
                    if distance <= attack_range and self.line_clear(
                            enemy.x, enemy.y, player.x, player.y, airborne=enemy.kind == 'ranged'):
                        self.start_attack(enemy)
                    self.attack_tick(enemy, dt)
                    if self.outcome:
                        return
            enemy.animate(dt, previous_movement[id(enemy)])
        self.update_projectiles(dt)
        self.update_acquisition()
        if self.guardian:
            self.use_final_reward(keys)
        exit_pos = self.data['plannedExit']
        exit_ready = self.exit_open and (not self.garden or self.garden_exit_time >= self.garden_exit_seconds)
        if self.guardian:
            exit_ready = exit_ready and self.guardian.reward_tasted and player.y < self.guardian.spec['exitGate'][1]
        if self.quarry and exit_ready:
            self.quarry.exit_time = min(self.quarry.exit_seconds, self.quarry.exit_time + dt)
            exit_ready = self.quarry.exit_time >= self.quarry.exit_seconds
        if exit_ready and not self.outcome and math.hypot(player.x-exit_pos['x'], player.y-exit_pos['y']) < .7:
            self.outcome = 'clear'
            self.projectiles.clear()
