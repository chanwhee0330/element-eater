"""로컬 이어하기 저장. 게임 데이터만 JSON으로 기록하고 유효한 첫 방 저장만 복원한다."""
from dataclasses import asdict, fields
from pathlib import Path
import json
import math
import os
from copy import deepcopy

from .room import ROOT, Room, Actor, STAGES
from .combat import Projectile
from .elements import Source, ELEMENTS

DEFAULT_SAVE = ROOT / 'saves/continue.json'
DIRECTIONS = {'up', 'down', 'left', 'right'}


def number(value, minimum=None, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('유효하지 않은 숫자')
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError('저장 수치 범위 초과')
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError('유효하지 않은 상태')
    return value


def actor_from_data(data, template, room):
    if not isinstance(data, dict) or set(data) != {f.name for f in fields(Actor)}:
        raise ValueError('캐릭터 저장 형식 불일치')
    if data['kind'] != template.kind or data['name'] != template.name:
        raise ValueError('캐릭터 종류 불일치')
    if data['element'] != template.element or data['attack_element'] not in ('neutral','water','fire'):
        raise ValueError('캐릭터 원소 불일치')
    if data['facing'] not in DIRECTIONS or data['attack_facing'] not in DIRECTIONS:
        raise ValueError('방향 불일치')
    if type(data['max_hp']) is not int or data['max_hp'] != template.max_hp:
        raise ValueError('체력 규격 불일치')
    if type(data['hp']) is not int:
        raise ValueError('체력 형식 불일치')
    number(data['hp'], 0, data['max_hp'])
    number(data['x'], -1, room.data['columns']+1)
    number(data['y'], -1, room.data['rows']+1)
    limits = {'animation_time': 1_000_000_000, 'falling': room.data['preview']['fallSeconds'],
              'hit_flash': .16, 'invulnerable': room.tuning.invulnerability,
              'attack_cooldown': max(room.tuning.player_interval, room.tuning.melee_interval, room.tuning.ranged_interval),
              'knockback_left': room.tuning.knockback_seconds}
    for key, maximum in limits.items():
        number(data[key], 0, maximum)
    number(data['attack_elapsed'], -1, room.tuning.attack_duration)
    for key in ('active', 'moving', 'attack_emitted'):
        boolean(data[key])
    for key in ('attack_direction', 'knockback'):
        vector = data[key]
        if not isinstance(vector, list) or len(vector) != 2:
            raise ValueError('벡터 형식 불일치')
        for value in vector:
            number(value, -1, 1)
    if data['active'] and data['hp'] == 0:
        raise ValueError('생존 상태 불일치')
    if template.kind == 'hero' and not data['active']:
        raise ValueError('사망한 저장은 재개 불가')
    if room.tile(data['x'], data['y']) == 3:
        raise ValueError('벽 내부 위치')
    data = dict(data)
    data['attack_direction'], data['knockback'] = tuple(data['attack_direction']), tuple(data['knockback'])
    return Actor(**data)


def restore(record, room):
    if not isinstance(record, dict) or type(record.get('version')) is not int or record['version'] not in (1,2) or type(record.get('stage')) is not int or record['stage'] not in STAGES:
        raise ValueError('지원하지 않는 저장')
    record = deepcopy(record)
    if record['version'] == 1:
        if record['stage'] != 1:
            raise ValueError('이전 저장 버전은 첫 방만 지원')
        state = record['state']
        for actor in [state['player'], *state['enemies']]:
            actor.setdefault('element','neutral')
            actor.setdefault('attack_element','neutral')
        state.update(inventory={e:0 for e in ELEMENTS},selected='neutral',sources=[],fire_aggro=False,
                     ingest_elapsed=-1,ingest_source=None,ingest_consumed=False,ingest_form='neutral')
    candidate = Room(stage=record['stage'])
    if record.get('room_id') != candidate.data['id']:
        raise ValueError('방 불일치')
    state = record['state']
    if not isinstance(state, dict) or not isinstance(state['enemies'], list) or len(state['enemies']) != len(candidate.enemies):
        raise ValueError('적 목록 불일치')
    player = actor_from_data(state['player'],candidate.player,candidate)
    enemies = [actor_from_data(saved,template,candidate) for saved,template in zip(state['enemies'],candidate.enemies)]
    sources = state['sources']
    if not isinstance(sources,list) or len(sources) != len(candidate.sources):
        raise ValueError('원천 목록 불일치')
    restored_sources = []
    for saved,template in zip(sources,candidate.sources):
        if not isinstance(saved,dict) or set(saved) != {f.name for f in fields(Source)}:
            raise ValueError('원천 형식 불일치')
        if any(saved[key] != getattr(template,key) for key in ('id','x','y','element')):
            raise ValueError('원천 종류/좌표 불일치')
        phases = {'intact':3,'damaged1':2,'damaged2':1,'breaking':0,'orb':0,'consumed':0}
        if saved['phase'] not in phases or type(saved['hp']) is not int or saved['hp'] != phases[saved['phase']]:
            raise ValueError('원천 내구도/상태 불일치')
        for key in ('age','break_elapsed','hit_time'):
            number(saved[key],0,2_000_000_000)
        restored_sources.append(Source(**saved))
    candidate.sources = restored_sources
    safe = state['safe']
    if not isinstance(safe, list) or len(safe) != 3 or safe[2] not in DIRECTIONS:
        raise ValueError('안전 위치 불일치')
    number(safe[0],0,candidate.data['columns'])
    number(safe[1],0,candidate.data['rows'])
    if not candidate.fits(safe[0],safe[1],safe=True):
        raise ValueError('위험한 복귀 위치')
    elapsed = number(state['elapsed'], 0, 1_000_000_000)
    aggro = boolean(state['aggro'])
    spike = boolean(state['spike_contact'])
    inventory = state['inventory']
    if not isinstance(inventory,dict) or set(inventory) != set(ELEMENTS):
        raise ValueError('보관함 형식 불일치')
    for element,count in inventory.items():
        if type(count) is not int or not 0 <= count <= 1_000_000 or (element != 'water' and count != 0):
            raise ValueError('지원하지 않는 보유 원소')
    selected = state['selected']
    if selected != ('water' if inventory['water'] else 'neutral'):
        raise ValueError('선택 원소 불일치')
    fire_aggro = boolean(state['fire_aggro'])
    ingest_elapsed = number(state['ingest_elapsed'],-1,candidate.tuning.ingest_duration)
    if ingest_elapsed < 0 and ingest_elapsed != -1:
        raise ValueError('섭취 시간 불일치')
    ingest_source,consumed,form = state['ingest_source'],boolean(state['ingest_consumed']),state['ingest_form']
    if form not in ('neutral','water'):
        raise ValueError('섭취 외형 불일치')
    if ingest_elapsed >= 0:
        source = next((s for s in restored_sources if s.id == ingest_source),None)
        if source is None or source.phase != ('consumed' if consumed else 'orb'):
            raise ValueError('섭취 대상 불일치')
    elif ingest_source is not None or consumed:
        raise ValueError('끝난 섭취 상태 불일치')
    shots = state['projectiles']
    if not isinstance(shots, list) or len(shots) > 256:
        raise ValueError('탄환 목록 불일치')
    projectiles = []
    for shot in shots:
        if not isinstance(shot, dict) or set(shot) != {f.name for f in fields(Projectile)}:
            raise ValueError('탄환 형식 불일치')
        if shot['owner'] not in ('hero','enemy') or shot['element'] not in ('neutral','water','fire'):
            raise ValueError('탄환 종류 불일치')
        for key in ('x', 'y', 'dx', 'dy', 'speed', 'remaining', 'age'):
            number(shot[key])
        number(shot['x'],0,candidate.data['columns'])
        number(shot['y'],0,candidate.data['rows'])
        number(shot['speed'], .01, 100)
        number(shot['remaining'], 0, 100)
        number(shot['age'], 0, 120)
        if type(shot['damage']) is not int or not 0 < shot['damage'] <= 100 or not boolean(shot['active']):
            raise ValueError('탄환 상태 불일치')
        if abs(math.hypot(shot['dx'], shot['dy'])-1) > .001:
            raise ValueError('탄환 방향 불일치')
        projectiles.append(Projectile(**shot))
    # 검사를 모두 통과한 뒤 한 번에 적용한다.
    candidate.player,candidate.enemies = player,enemies
    candidate.safe,candidate.elapsed,candidate.aggro = tuple(safe),elapsed,aggro
    candidate.spike_contact,candidate.projectiles = spike,projectiles
    candidate.inventory,candidate.selected,candidate.fire_aggro = inventory,selected,fire_aggro
    candidate.ingest_elapsed,candidate.ingest_source = ingest_elapsed,ingest_source
    candidate.ingest_consumed,candidate.ingest_form = consumed,form
    room.__dict__.update(candidate.__dict__)


class SaveStore:
    def __init__(self, path=DEFAULT_SAVE):
        self.path = Path(path)

    def load(self):
        try:
            if self.path.stat().st_size > 2_000_000:
                return None
            record = json.loads(self.path.read_text(encoding='utf-8'))
            restore(record, Room())
            return record
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
            return None

    def write(self, room):
        if room.outcome or not room.player.active:
            return
        record = {'version':2,'stage':room.stage,'room_id':room.data['id'],'state':{
            'player': asdict(room.player), 'enemies': [asdict(e) for e in room.enemies],
            'safe': list(room.safe), 'aggro': room.aggro, 'elapsed': room.elapsed,
            'spike_contact':room.spike_contact,'projectiles':[asdict(s) for s in room.projectiles],
            'inventory':dict(room.inventory),'selected':room.selected,'sources':[asdict(s) for s in room.sources],
            'fire_aggro':room.fire_aggro,'ingest_elapsed':room.ingest_elapsed,'ingest_source':room.ingest_source,
            'ingest_consumed':room.ingest_consumed,'ingest_form':room.ingest_form}}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        os.replace(temporary, self.path)

    def clear(self):
        self.path.unlink(missing_ok=True)
