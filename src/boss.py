"""오원 제단의 소환, 원소 전환과 공격 시점을 관리한다."""
import base64
from bisect import bisect_right
from functools import lru_cache
import json
import math
from pathlib import Path
import random

from .combat import Feedback, Projectile

FORMS = ('fire', 'wind', 'earth', 'lightning', 'water')
RITUAL = ('water', 'fire', 'wind', 'earth', 'lightning')
COLORS = {'water': (113, 218, 240), 'fire': (255, 137, 82), 'wind': (173, 226, 184),
          'earth': (218, 177, 126), 'lightning': (212, 162, 255)}
FIRE_FAN = (-.54, -.27, 0, .27, .54)
WATER_GAPS = (-.42, .42)
WATER_RING_DELAY = .29
EARTH_INTERVAL = .22
EARTH_PIT_RADIUS = (.92, .63)
STAGGER = .94
SUMMON_SECONDS = 1.92
SUMMON_SHOCK_AT = 1.34
SUMMON_SHOCK_SECONDS = .48
MIXED_INGEST_BITE = 2.70
MIXED_INGEST_SECONDS = 5.6
FALL_SECONDS = .94
DEFEAT_SECONDS = 2.85
SHATTER_AT = .35
GATE_SECONDS = .70
GATE_WATCH = .8
DASH_SECONDS = .64
DASH_DISTANCE = 12
LIGHTNING_BEAT = .12
LIGHTNING_REACH = 17
GUARDIAN_DRAW_UNIT = 36.8
GUARDIAN_SHOT_LIFT = .61
GUARDIAN_WALK_SPEED = 1.65
ATLAS_FOLDER = Path(__file__).resolve().parents[1] / 'assets/sprites/boss/animation'


def inside(bounds, x, y):
    left, top, right, bottom = bounds
    return left <= x < right and top <= y < bottom


def facing_for(dx, dy):
    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'
    return 'down' if dy >= 0 else 'up'


def angle_delta(a, b):
    return (a - b + math.pi) % math.tau - math.pi


class Clip:
    def __init__(self, spec, meta):
        self.frames = [spec['frames'][key] for key in meta['frames']]
        self.ends = []
        elapsed = 0
        for frame in self.frames:
            elapsed += frame['duration']
            self.ends.append(elapsed / 1000)
        self.duration = self.ends[-1]
        self.loop = meta['loop']
        self.events = {event['name']: (self.ends[event['frame']-1] if event['frame'] else 0)
                       for event in meta.get('events', ())}

    def frame_index(self, elapsed):
        age = elapsed % self.duration if self.loop else elapsed
        return min(len(self.frames)-1,bisect_right(self.ends,age))

    def frame(self, elapsed):
        return self.frames[self.frame_index(elapsed)]


@lru_cache(maxsize=1)
def guardian_atlases():
    atlases = {}
    for element in FORMS:
        spec = json.loads((ATLAS_FOLDER/f'guardian-{element}-animations.json').read_text(encoding='utf-8'))
        atlases[element] = ATLAS_FOLDER/spec['image'], {state:Clip(spec, meta) for state,meta in spec['clips'].items()}
    return atlases


@lru_cache(maxsize=1)
def guardian_walk_atlases():
    atlases = {}
    for element in FORMS:
        spec = json.loads((ATLAS_FOLDER/f'guardian-{element}-walk.json').read_text(encoding='utf-8'))
        atlases[element] = ATLAS_FOLDER/spec['image'], {
            state: Clip(spec, meta) for state, meta in spec['clips'].items()
        }
    return atlases


@lru_cache(maxsize=1)
def guardian_hit_masks():
    spec = json.loads((ATLAS_FOLDER/'guardian-hit-masks.json').read_text(encoding='utf-8'))
    masks = {form:{state:tuple(base64.b64decode(mask) for mask in frames)
                   for state,frames in poses.items()} for form,poses in spec['poses'].items()}
    walk = json.loads((ATLAS_FOLDER/'guardian-walk-hit-masks.json').read_text(encoding='utf-8'))
    for form, poses in walk.items():
        masks[form].update({state: tuple(base64.b64decode(mask) for mask in frames)
                            for state, frames in poses.items()})
    return spec['cellSize'],spec['frameSize']//spec['cellSize'],masks


class Guardian:
    def __init__(self, spec):
        self.spec = spec
        self.pits = []
        self.ritual = 0
        self.placed = set()
        self.placed_at = {}
        self.reward_orbs = set()
        self.reward_loaded = False
        self.reward_tasted = False
        self.reward_scene_elapsed = None
        self.summon = 0.0
        self.wind_y = spec['windStartY']
        self.wind_moving = False
        self.form = 'fire'
        self.next_form = None
        self.form_left = spec['formSeconds']
        self.swap = -1.0
        self.attack_age = -1.0
        self.target = None
        self.heading = 0.0
        self.cooldown = 1.0
        self.fall = -1.0
        self.clips = guardian_atlases()
        self.walk_clips = guardian_walk_atlases()

    @property
    def summoning(self):
        return self.ritual == len(RITUAL) and self.summon < SUMMON_SECONDS

    @property
    def battle(self):
        return self.ritual == len(RITUAL) and self.summon >= SUMMON_SECONDS and self.fall < 0

    @property
    def vulnerable(self):
        return self.battle and self.swap < 0

    @property
    def gate_progress(self):
        return max(0, min(1, (self.fall-FALL_SECONDS)/GATE_SECONDS))

    @property
    def collapsing(self):
        return 0 <= self.fall < FALL_SECONDS

    @property
    def element(self):
        if self.next_form and self.swap >= self.clip('transform').events['elementChange']:
            return self.next_form
        return self.form

    def clip(self, state, *, form=None):
        form = form or self.form
        if state in self.walk_clips[form][1]:
            return self.walk_clips[form][1][state]
        return self.clips[form][1][state]

    @staticmethod
    def directional_state(state, facing):
        return state if facing == 'down' else f'{state}_{facing}'

    def pose(self, actor):
        if self.attack_age >= 0:
            facing = facing_for(math.cos(self.heading), math.sin(self.heading))
            return self.directional_state('attack', facing), self.attack_age
        return self.directional_state('walk' if actor.moving else 'idle', actor.facing), actor.animation_time

    def hits(self, actor, x, y):
        state,age = self.pose(actor)
        clip = self.clip(state)
        index = clip.frame_index(age)
        pivot = clip.frames[index]['pivotPixelsTopLeft']
        cell,size,masks = guardian_hit_masks()
        col = math.floor((pivot['x']+(x-actor.x)*GUARDIAN_DRAW_UNIT)/cell)
        row = math.floor((pivot['y']+(y-actor.y-GUARDIAN_SHOT_LIFT)*GUARDIAN_DRAW_UNIT)/cell)
        if not (0 <= col < size and 0 <= row < size):
            return False
        bit = row*size+col
        return bool(masks[self.form][state][index][bit//8] & (1 << (bit%8)))

    def target_points(self, actor):
        for dx,dy in ((0,0),(-.9,0),(.9,0),(-2,-1.2),(2,-1.2),(0,-2)):
            x,y = actor.x+dx,actor.y+dy
            if self.hits(actor,x,y):
                yield x,y

    def orb_flight(self, element):
        x, y = self.spec['devices'][RITUAL.index(element)]
        cx, cy = self.spec['center']
        distance = math.hypot(x-cx, y-cy)
        phase = max(0, min(1, (self.summon-SUMMON_SHOCK_AT)/SUMMON_SHOCK_SECONDS))
        spread = 1.28 * (1-(1-phase)**2) / distance
        return x + (x-cx)*spread, y + (y-cy)*spread, phase

    def nearby_pedestal(self, player, *, retrieve=False):
        for index, pedestal in enumerate(self.spec['devices']):
            element = RITUAL[index]
            if retrieve and element not in self.placed:
                continue
            point = self.orb_flight(element)[:2] if retrieve else pedestal
            if math.dist((player.x, player.y), point) <= 1.1:
                return element
        return None

    def can_place_orb(self, room, element):
        return (self.ritual < len(RITUAL) and element not in self.placed
                and room.selected == element and room.inventory.get(element, 0) > 0)

    def interact_pedestal(self, room, *, retrieve):
        element = self.nearby_pedestal(room.player, retrieve=retrieve)
        if element is None:
            return
        if retrieve:
            if self.ritual == len(RITUAL) and not self.summoning and element in self.placed:
                self.placed.remove(element)
                room.inventory[element] = 1
                room.restore_selected_element(element)
        elif self.can_place_orb(room, element):
            self.placed.add(element)
            self.placed_at[element] = room.elapsed
            self.ritual = len(self.placed)
            if self.ritual >= 3:
                self.wind_y = self.spec['windPlateY']
            room.inventory[element] = 0
            room.restore_selected_element(room.selected)

    def tile(self, x, y):
        gate = self.spec['exitGate']
        left,right = self.spec['exitOpening']
        if inside(gate,x,y) and (self.gate_progress < 1 or not left <= x < right):
            return 3
        return None

    def pit_at(self, x, y):
        rx, ry = EARTH_PIT_RADIUS
        return any(((x - px) / rx)**2 + ((y - py) / ry)**2 < 1 for px, py in self.pits)

    @staticmethod
    def pit_bridge_bounds(x, y):
        rx, ry = EARTH_PIT_RADIUS
        return x - rx, y - ry, x + rx, y + ry

    def clear_attack(self, room):
        self.target = None
        self.attack_age = -1
        for shot in room.projectiles:
            if shot.owner == 'enemy':
                shot.active = False
        room.projectiles[:] = [shot for shot in room.projectiles if shot.active]

    def damaged(self, room, actor):
        if actor.hp != 0:
            return
        actor.burn_ticks = 0
        actor.burn_delay = 0
        actor.knockback_left = 0
        self.clear_attack(room)
        self.fall = 0

    def start_transform(self, room, actor):
        room.sound_events.append('transform')
        self.next_form = random.choice([form for form in FORMS if form != self.form])
        self.swap = 0
        self.clear_attack(room)
        actor.burn_ticks = 0
        actor.burn_delay = 0
        actor.knockback_left = 0

    def debug_prepare(self, room):
        if self.fall >= 0:
            return
        actor = room.enemies[0]
        self.ritual = len(RITUAL)
        self.summon = SUMMON_SECONDS
        self.wind_y = self.spec['windPlateY']
        self.wind_moving = False
        self.swap = -1
        self.next_form = None
        self.clear_attack(room)
        actor.element = self.form
        actor.active = True
        actor.hp = 1
        actor.attack_elapsed = -1
        actor.burn_ticks = 0
        actor.burn_delay = 0
        actor.knockback_left = 0
        actor.invulnerable = 0
        self.form_left = self.spec['formSeconds']
        self.cooldown = 1

    def advance_reward_scene(self, dt):
        prior = self.reward_scene_elapsed
        if prior is None:
            return False
        self.reward_scene_elapsed += dt
        bitten = prior < MIXED_INGEST_BITE <= self.reward_scene_elapsed
        if bitten:
            self.reward_tasted = True
        if self.reward_scene_elapsed >= MIXED_INGEST_SECONDS:
            self.reward_scene_elapsed = None
            return True
        return bitten

    def move(self, room, actor, dx, dy):
        left,top,right,bottom = self.spec['arena']
        x = min(right,max(left,actor.x+dx))
        y = min(bottom,max(top,actor.y+dy))
        old_x, old_y = actor.x, actor.y
        was_moving = actor.moving
        room.move(actor,x-old_x,y-old_y,safe=True)
        if actor.moving:
            dx, dy = actor.x-old_x, actor.y-old_y
            actor.facing = facing_for(dx, dy)
        actor.moving |= was_moving

    def dash_endpoint(self, room, x, y, distance):
        left, top, right, bottom = self.spec['arena']
        parts = max(1, math.ceil(distance / .08))
        dx = math.cos(self.heading) * distance / parts
        dy = math.sin(self.heading) * distance / parts
        for _ in range(parts):
            tx, ty = x + dx, y + dy
            if (not (left <= tx <= right and top <= ty <= bottom)
                    or room.blocked_by_wall(tx, ty, x, y)
                    or not room.fits(tx, ty, safe=True)):
                break
            x, y = tx, ty
        return x, y

    def push_from_altar(self, room, time):
        player = room.player
        cx, cy = self.spec['center']
        dx, dy = player.x-cx, player.y-cy
        if math.hypot(dx, dy) < .01:
            dx, dy = 0, 1
        distance = math.hypot(dx, dy)
        facing = player.facing
        speed = 5.5 * (1 - .68 * (self.summon-SUMMON_SHOCK_AT)/SUMMON_SHOCK_SECONDS)
        room.move(player, dx/distance * speed*time, dy/distance * speed*time, safe=True)
        player.facing = facing

    def step(self, room, dt):
        actor = room.enemies[0]
        was_moving, prior_facing = actor.moving, actor.facing
        old_x, old_y = actor.x, actor.y
        actor.moving = False
        if self.ritual < len(RITUAL):
            return
        if self.summoning:
            previous = self.summon
            self.summon = min(SUMMON_SECONDS,self.summon+dt)
            push_time = min(self.summon, SUMMON_SHOCK_AT+SUMMON_SHOCK_SECONDS) - max(previous, SUMMON_SHOCK_AT)
            if previous < SUMMON_SHOCK_AT <= self.summon:
                room.sound_events.append('shockwave')
            if push_time > 0 and not room.player.falling:
                self.push_from_altar(room, push_time)
            if not self.summoning:
                actor.active = True
            return
        if self.fall >= 0:
            if self.collapsing:
                previous = self.fall
                # 저장된 파쇄 진행 척도는 유지하고 실제 재생 시간만 늘린다.
                to_end = (FALL_SECONDS - self.fall) * DEFEAT_SECONDS / FALL_SECONDS
                if dt >= to_end:
                    self.fall = FALL_SECONDS + (dt - to_end)
                else:
                    self.fall += dt * FALL_SECONDS / DEFEAT_SECONDS
                if previous < SHATTER_AT <= self.fall:
                    room.sound_events.append('boss-shatter')
            else:
                self.fall = min(FALL_SECONDS+GATE_SECONDS+GATE_WATCH+1,self.fall+dt)
            return
        if self.swap >= 0:
            self.swap += dt
            actor.element = self.element
            if self.swap >= self.clip('transform').duration:
                self.form = self.next_form
                self.next_form = None
                self.swap = -1
                self.form_left = self.spec['formSeconds']
                self.cooldown = 1
            return
        self.form_left = max(0,self.form_left-dt)
        if self.form_left <= 1e-8:
            self.form_left = 0
            self.start_transform(room,actor)
            return
        if actor.knockback_left > 0:
            span = min(dt,actor.knockback_left)
            dx,dy = actor.knockback
            self.move(room,actor,dx*span,dy*span)
            actor.knockback_left -= span
        if self.attack_age >= 0:
            actor.facing = facing_for(math.cos(self.heading), math.sin(self.heading))
            self.update_attack(room, actor, dt)
            return
        player = room.player
        dx,dy = player.x-actor.x,player.y-actor.y
        distance = math.hypot(dx,dy)
        if not player.falling and self.cooldown <= 0 and distance < 11:
            self.target = (player.x, player.y)
            self.heading = math.atan2(dy,dx)
            if distance:
                actor.facing = facing_for(math.cos(self.heading), math.sin(self.heading))
            self.attack_age = 0
            room.sound_events.append('warning')
        elif distance > 5.5 and not player.falling:
            self.move(room, actor, dx / distance * GUARDIAN_WALK_SPEED * dt,
                      dy / distance * GUARDIAN_WALK_SPEED * dt)
        if actor.moving and self.attack_age < 0:
            if not was_moving or actor.facing != prior_facing:
                actor.animation_time = 0
            side = actor.facing in ('left', 'right')
            advance = abs(actor.x - old_x) if side else abs(actor.y - old_y)
            actor.animation_time += advance / GUARDIAN_WALK_SPEED
        elif was_moving:
            actor.animation_time = 0
        else:
            actor.animation_time += dt
        self.cooldown = max(0,self.cooldown-dt)

    def earth_points(self):
        x,y = self.target
        for dx,dy in ((0,0),(1.37,-.83),(-1.28,1.04)):
            yield max(.3,min(29.7,x+dx)),max(.3,min(23.7,y+dy))

    def shot(self, room, actor, angle, speed, reach, *, offset=0):
        dx,dy = math.cos(angle),math.sin(angle)
        room.projectiles.append(Projectile(actor.x+dx*offset,actor.y+dy*offset,dx,dy,
                                           'enemy',speed,reach,10,element=actor.element))

    def update_attack(self, room, actor, dt):
        prior = self.attack_age
        self.attack_age += dt
        age = self.attack_age
        clip = self.clip('attack')
        release = clip.events['release']
        player = room.player
        if actor.element == 'earth':
            for i,(x,y) in enumerate(self.earth_points()):
                if prior < release+i*EARTH_INTERVAL <= age:
                    room.sound_events.append('stone')
                    room.feedback.append(Feedback(x,y,'',False,.28,.28))
                    if math.hypot(player.x-x,player.y-y) <= 1.02:
                        room.damage(player,10)
                    spawn = room.data['playerSpawn']
                    if (room.tile(x,y,ignore_earth=True) < 3
                            and abs(y - spawn['y']) >= EARTH_PIT_RADIUS[1] + room.radius):
                        self.pits.append((x,y))
                        if not room.fits(*room.safe[:2], safe=True):
                            room.safe = spawn['x'], spawn['y'], spawn['facing']
        elif actor.element == 'wind':
            if prior < release <= age:
                room.sound_events.append('gust')
            duration = max(0,min(release+DASH_SECONDS,age)-max(release,prior))
            if duration:
                old = actor.x, actor.y
                actor.x, actor.y = self.dash_endpoint(room, *old, DASH_DISTANCE * duration / DASH_SECONDS)
                actor.moving = (actor.x, actor.y) != old
                if math.hypot(player.x-actor.x,player.y-actor.y) <= .72:
                    room.damage(player,10)
        elif actor.element == 'water':
            for i,gap in enumerate(WATER_GAPS):
                if prior < release+i*WATER_RING_DELAY <= age:
                    room.sound_events.append('splash')
                    gap += self.heading
                    for j in range(18):
                        angle = gap+j*math.tau/18
                        if abs(angle_delta(angle,gap)) >= .57:
                            self.shot(room,actor,angle,4.4,14,offset=.45)
        elif prior < release <= age:
            room.sound_events.append('flame' if actor.element == 'fire' else 'electric')
            offsets = FIRE_FAN if actor.element == 'fire' else (0,)
            for offset in offsets:
                self.shot(room,actor,self.heading+offset,8.7 if actor.element == 'fire' else 14,
                          17 if actor.element == 'fire' else LIGHTNING_REACH)
        if age >= clip.duration:
            self.attack_age = -1
            self.target = None
            self.cooldown = STAGGER

    def record(self):
        state = {key:getattr(self,key) for key in ('ritual','summon','wind_y','wind_moving',
                                                  'form','next_form','form_left','swap',
                                                  'attack_age','target','heading','cooldown','fall',
                                                  'reward_loaded','reward_tasted','reward_scene_elapsed')}
        state['placed'] = sorted(self.placed)
        state['reward_orbs'] = sorted(self.reward_orbs)
        state['pits'] = [list(point) for point in self.pits]
        return state
