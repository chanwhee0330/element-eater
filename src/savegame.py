"""로컬 이어하기 저장. 게임 데이터만 JSON으로 기록하고 유효한 첫 방 저장만 복원한다."""
from dataclasses import asdict, fields
from pathlib import Path
import json
import math
import os
from copy import deepcopy

from .room import ROOT, Room, Actor, EarthTerrain, STAGES
from .combat import Projectile
from .elements import Source, ELEMENTS
from .boss import (FALL_SECONDS, FORMS, GATE_SECONDS, GATE_WATCH, MIXED_INGEST_BITE,
                   MIXED_INGEST_SECONDS, RITUAL, SUMMON_SECONDS)

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


def restore_guardian(room, stored, actor):
    guardian = room.guardian
    ritual = stored['ritual']
    if type(ritual) is not int or not 0 <= ritual <= len(RITUAL):
        raise ValueError('오원 제단 단계 불일치')
    guardian.ritual = ritual
    interval = guardian.spec['formSeconds']
    if 'form' not in stored:
        # 같은 맵의 코어 방식 저장은 체력, 의식과 진행 중이던 변신을 이어받는다.
        core = stored['core']
        if type(core) is not int or not 0 <= core < len(FORMS):
            raise ValueError('이전 수호자 형태 불일치')
        changing = number(stored['swap'],-1) >= 0
        if changing and core == len(FORMS)-1:
            raise ValueError('이전 수호자 변신 불일치')
        stored = dict(stored,form=FORMS[core],next_form=FORMS[core+1] if changing else None,
                      form_left=0 if changing else interval)
    form,next_form = stored['form'],stored['next_form']
    if form not in FORMS or (next_form is not None and (next_form not in FORMS or next_form == form)):
        raise ValueError('수호자 원소 불일치')
    guardian.form,guardian.next_form = form,next_form
    guardian.form_left = number(stored['form_left'],0,interval)
    for key, end in (('summon',SUMMON_SECONDS),('swap',guardian.clip('transform').duration),
                     ('attack_age',guardian.clip('attack').duration),
                     ('fall',FALL_SECONDS+GATE_SECONDS+GATE_WATCH+1)):
        start = 0 if key == 'summon' else -1
        value = number(stored[key],start,end)
        if -1 < value < 0:
            raise ValueError('오원 제단 시간 불일치')
        setattr(guardian,key,value)
    spec = guardian.spec
    guardian.wind_y = number(stored['wind_y'],spec['windPlateY'],spec['windStartY'])
    guardian.wind_moving = boolean(stored['wind_moving'])
    guardian.heading = number(stored['heading'],-math.pi,math.pi)
    guardian.cooldown = number(stored['cooldown'],0,2)
    target = stored['target']
    if target is not None:
        if not isinstance(target,list) or len(target) != 2:
            raise ValueError('수호자 조준 위치 불일치')
        guardian.target = (number(target[0],0,room.data['columns']),number(target[1],0,room.data['rows']))
    if (guardian.wind_moving and guardian.ritual != 2
            or guardian.ritual >= 3 and guardian.wind_y != spec['windPlateY']
            or guardian.ritual < 2 and guardian.wind_y != spec['windStartY']
            or guardian.ritual < len(RITUAL) and guardian.summon
            or (guardian.target is None) != (guardian.attack_age < 0)
            or guardian.attack_age >= 0 and not guardian.vulnerable
            or (guardian.next_form is not None) != (guardian.swap >= 0)
            or guardian.swap >= 0 and (not guardian.battle or guardian.form_left != 0)
            or guardian.fall >= 0 and guardian.summon < SUMMON_SECONDS):
        raise ValueError('수호자 진행 상태 불일치')
    actor_expected = guardian.battle
    hp, maximum = actor['hp'],room.enemies[0].max_hp
    if (actor['active'] != actor_expected
            or guardian.fall >= 0 and hp != 0
            or guardian.summon < SUMMON_SECONDS and (guardian.form != 'fire' or hp != maximum)
            or guardian.battle and not 0 < hp <= maximum):
        raise ValueError('수호자 체력 불일치')
    placed = stored.get('placed')
    if placed is None and ritual < len(RITUAL):
        # 이전 저장의 장치 작동 진행은 보유 구슬을 유지한 채 새 배치로 재개한다.
        guardian.ritual = 0
        guardian.wind_y = spec['windStartY']
        guardian.wind_moving = False
    elif placed is not None:
        if (not isinstance(placed, list) or any(e not in RITUAL for e in placed)
                or len(set(placed)) != len(placed)
                or len(placed) > ritual or ritual < len(RITUAL) and len(placed) != ritual
                or any(room.inventory[e] for e in placed)):
            raise ValueError('제단 구슬 상태 불일치')
        guardian.placed = set(placed)
    guardian.reward_loaded = boolean(stored.get('reward_loaded', False))
    guardian.reward_tasted = boolean(stored.get('reward_tasted', False))
    reward_orbs = stored.get('reward_orbs', list(RITUAL) if guardian.reward_loaded else [])
    if (not isinstance(reward_orbs, list) or any(e not in RITUAL for e in reward_orbs)
            or len(set(reward_orbs)) != len(reward_orbs)
            or any(room.inventory[e] or e in guardian.placed for e in reward_orbs)
            or reward_orbs and guardian.fall < FALL_SECONDS
            or guardian.reward_loaded != (len(reward_orbs) == len(RITUAL))
            or guardian.reward_tasted and not guardian.reward_loaded):
        raise ValueError('혼합 구슬 상태 불일치')
    guardian.reward_orbs = set(reward_orbs)
    if (scene_elapsed := stored.get('reward_scene_elapsed')) is not None:
        scene_elapsed = number(scene_elapsed, 0, MIXED_INGEST_SECONDS)
        if (not guardian.reward_loaded or scene_elapsed >= MIXED_INGEST_SECONDS
                or guardian.reward_tasted != (scene_elapsed >= MIXED_INGEST_BITE)):
            raise ValueError('혼합 구슬 섭취 연출 상태 불일치')
        guardian.reward_scene_elapsed = scene_elapsed
    room.enemies[0].element = guardian.element


def trial_wheel_resume_position(room, x, y):
    if not room.trial:
        return None
    left, top, right, bottom = room.trial['wheelGate']
    radius = room.radius
    trapped = (not room.trial_laser_locked and left <= x < right
               and room.trial['serviceGate'][3] <= y < bottom)
    overlaps = any(wall_left-radius < x < wall_right+radius and wall_top-radius < y < wall_bottom+radius
                   for wall_left, wall_top, wall_right, wall_bottom in room.trial_wheel_obstacles())
    if not (trapped or overlaps):
        return None
    center = sum(room.trial['wheelOpening']) / 2
    north = not trapped and y < (top+bottom)/2
    return center, top-radius-.06 if north else bottom+radius+.06


def actor_from_data(data, template, room, *, recover_puzzle_layout=False):
    if isinstance(data, dict):
        data = {'wind_sliding': False, 'burn_ticks': 0, 'burn_delay': 0, **data}
    if not isinstance(data, dict) or set(data) != {f.name for f in fields(Actor)}:
        raise ValueError('캐릭터 저장 형식 불일치')
    if data['kind'] != template.kind or data['name'] != template.name:
        raise ValueError('캐릭터 종류 불일치')
    if data['element'] != template.element or data['attack_element'] not in ('neutral','water','fire','wind','earth','lightning'):
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
              'knockback_left': room.wind_enemy_push_seconds if data['wind_sliding'] else room.tuning.knockback_seconds}
    for key, maximum in limits.items():
        number(data[key], 0, maximum)
    if type(data['burn_ticks']) is not int or not 0 <= data['burn_ticks'] <= 3:
        raise ValueError('화상 상태 불일치')
    number(data['burn_delay'], 0, .6 if data['burn_ticks'] else 0)
    number(data['attack_elapsed'], -1, room.tuning.attack_duration)
    for key in ('active', 'moving', 'attack_emitted', 'wind_sliding'):
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
    wheel_position = trial_wheel_resume_position(room, data['x'], data['y'])
    if wheel_position:
        # 이전 저장에서는 화로 주변 바닥 전체를 걸을 수 있었다.
        x, y = wheel_position
        data.update(x=x, y=y, moving=False, falling=0, knockback_left=0)
    if room.intersects_windmill_base(data['x'], data['y'], room.radius):
        # 받침대 충돌이 없던 저장은 풍차 앞 바닥에서 이어간다.
        x, y = room.acquisition['orb'] if template.kind == 'hero' else (template.x, template.y)
        data.update(x=x, y=y, moving=False, knockback_left=0)
    elif recover_puzzle_layout and not room.fits(data['x'], data['y'], safe=not data['falling']):
        # 새 석벽이나 평형추와 겹치면 마당의 빈 위치로 옮긴다.
        x, y = room.puzzle['reset'] if template.kind == 'hero' else (template.x, template.y)
        if template.kind == 'hero' and room.turret_room and data['x'] >= room.earth_bridge[0]:
            _, top, right, bottom = room.earth_bridge
            x, y = right + 1.5, (top + bottom) / 2
        data.update(x=x, y=y, moving=False, falling=0, knockback_left=0)
    if room.tile(data['x'], data['y'], ignore_block=True) == 3:
        raise ValueError('벽 내부 위치')
    data = dict(data)
    if data['wind_sliding'] and not data['knockback_left']:
        data['wind_sliding'] = False
    data['attack_direction'], data['knockback'] = tuple(data['attack_direction']), tuple(data['knockback'])
    return Actor(**data)


def restore(record, room):
    if not isinstance(record, dict) or type(record.get('version')) is not int or record['version'] not in (1,2,3) or type(record.get('stage')) is not int or record['stage'] not in STAGES:
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
    if record['version'] < 3 and not candidate.sources:
        selected = state['selected']
        state.update(inventory=dict(candidate.inventory), sources=[], ingest_elapsed=-1,
                     ingest_source=None, ingest_consumed=False, ingest_form='neutral',
                     selected=selected if candidate.inventory.get(selected) else candidate.selected)
        if state['selected'] != 'lightning':
            state.update(lightning_charged=False, lightning_attack=False)
    revision = candidate.data.get('layoutRevision')
    saved_revision = state.get('map_revision')
    previous_revisions = candidate.data.get('previousLayoutRevisions')
    if previous_revisions is None:
        previous_revision = candidate.data.get('previousLayoutRevision')
        previous_revisions = () if previous_revision is None else (previous_revision,)
    remap_positions = saved_revision in previous_revisions
    remap_wind_room = remap_positions and candidate.windmill
    remap_puzzle = remap_positions and candidate.puzzle and candidate.puzzle.get('centeredSlide')
    if revision and saved_revision != revision and not remap_positions:
        # 이전 방의 위치와 전투는 새 지도에서 초기화하고 체력과 해금 진행을 이어간다.
        candidate.player.hp = number(state['player']['hp'], 1, candidate.player.max_hp)
        selected = state.get('selected')
        if selected in candidate.inventory and candidate.inventory[selected]:
            candidate.selected = selected
        room.__dict__.update(candidate.__dict__)
        return
    if remap_positions or (candidate.reference_art and isinstance(state, dict) and 'reference_layout' not in state):
        # 이전 배치의 좌표는 각 지점에서 다시 잡고 체력과 퍼즐 상태는 이어간다.
        if not isinstance(state['enemies'], list) or not isinstance(state['sources'], list):
            raise ValueError('저장 목록 형식 불일치')
        if not all(isinstance(saved, dict) for saved in [state['player'], *state['enemies'], *state['sources']]):
            raise ValueError('저장 항목 형식 불일치')
        if remap_wind_room:
            # 풍차 섬을 넓히고 세 번째 적을 석교 앞에 옮긴 배치를 적용한다.
            for saved, template in zip(state['enemies'], candidate.enemies):
                if (saved_revision == 5 and template.kind == 'ranged'
                        or saved['element'] == 'earth' and template.element == 'neutral'):
                    saved.update(x=template.x, y=template.y, element=template.element,
                                 attack_element=template.element, attack_elapsed=-1, moving=False,
                                 falling=0, wind_sliding=False, knockback_left=0)
            # 섭취 전의 옛 자동 출현은 새 버튼으로 다시 시작한다.
            if saved_revision in (5, 6) and state['sources'] and state.get('ingest_source') != 'first-orb':
                orb = state['sources'][-1]
                if orb['phase'] in ('gathering', 'orb'):
                    orb.update(phase='sealed', age=0)
        elif not remap_puzzle:
            for saved, template in zip([state['player'], *state['enemies']], [candidate.player, *candidate.enemies]):
                saved.update(x=template.x, y=template.y, falling=0, moving=False,
                             attack_elapsed=-1, knockback_left=0)
            for saved, template in zip(state['sources'], candidate.sources):
                saved.update(x=template.x, y=template.y)
            state.update(safe=list(candidate.safe), projectiles=[])
            if remap_positions and state.get('ingest_source') == 'first-orb':
                orb = candidate.sources[-1]
                state['player'].update(x=orb.x, y=orb.y + .82, facing='up')
    if not isinstance(state, dict) or not isinstance(state['enemies'], list) or len(state['enemies']) != len(candidate.enemies):
        raise ValueError('적 목록 불일치')
    inventory = state['inventory']
    if not isinstance(inventory, dict) or set(inventory) != set(ELEMENTS):
        raise ValueError('보관함 형식 불일치')
    if any(type(count) is not int or not 0 <= count <= 1_000_000 for count in inventory.values()):
        raise ValueError('지원하지 않는 보유 원소')
    candidate.inventory = inventory
    candidate.debug_cleared = boolean(state.get('debug_cleared', False))
    if candidate.quarry and candidate.debug_cleared:
        candidate.quarry.exit_time = candidate.quarry.exit_seconds
    if candidate.acquisition:
        progress = state['acquisition']
        candidate.acquisition_relay = boolean(progress['relay'])
        candidate.acquisition_power = boolean(progress['power'])
        if candidate.acquisition_power and not candidate.acquisition_relay:
            raise ValueError('전력 장치 상태 불일치')
        if candidate.power_circuit:
            end = candidate.power_circuit['openAt']
            power_elapsed = number(progress.get('powerElapsed', end if candidate.acquisition_power else -1), -1, end)
            if ((power_elapsed != -1 and (power_elapsed < 0 or not candidate.acquisition_relay))
                    or candidate.acquisition_power != (power_elapsed == end)):
                raise ValueError('전력 복구 진행 불일치')
            candidate.acquisition_power_elapsed = power_elapsed
    if candidate.vine_gate:
        candidate.vine_time = number(state.get('vine_time', -1), -1, candidate.vine_gate['burnDuration'])
        if -1 < candidate.vine_time < 0:
            raise ValueError('덤불 소각 시간 불일치')
    if candidate.conductor_vine:
        candidate.conductor_vine_time = number(state['conductor_vine_time'], -1,
                                               candidate.conductor_vine['burnDuration'])
        if -1 < candidate.conductor_vine_time < 0:
            raise ValueError('전도체 덩굴 상태 불일치')
    if candidate.guardian:
        restore_guardian(candidate,state['boss'],state['enemies'][0])
    if candidate.data.get('requiredBridge'):
        candidate.bridge_crossed = boolean(state['bridge_crossed'])
        candidate.bridge_entry_side = state.get('bridge_entry_side')
        if candidate.bridge_entry_side not in (None, 'left', 'right'):
            raise ValueError('흙 발판 진입 방향 불일치')
    if candidate.sluice:
        candidate.sluice_wheel = boolean(state['sluice_wheel'])
        candidate.sluice_pump = boolean(state['sluice_pump'])
        if candidate.garden:
            candidate.garden_wheel_time = number(state.get('garden_wheel_time', 0), 0, .5)
            candidate.garden_gate_time = number(state.get('garden_gate_time', 0), 0, candidate.garden_gate_seconds)
            candidate.garden_exit_time = number(state.get('garden_exit_time', 0), 0, candidate.garden_exit_seconds)
    if candidate.fire_barriers:
        extinguished = state['extinguished']
        if (not isinstance(extinguished, list)
                or any(type(index) is not int or not 0 <= index < len(candidate.fire_barriers) for index in extinguished)
                or len(set(extinguished)) != len(extinguished)):
            raise ValueError('불길 진화 상태 불일치')
        candidate.extinguished = set(extinguished)
    if candidate.trial:
        returns = state['trial_returns']
        if returns not in ([], [0], [0, 1]) or (returns and not candidate.vine_open):
            raise ValueError('삼중 성문 귀환문 상태 불일치')
        candidate.trial_returns = set(returns)
        reveal = candidate.trial_wheel_reveal_seconds
        candidate.trial_wheel_time = number(
            state.get('trial_wheel_time', reveal if 1 in returns else 0),
            0, reveal if 0 in returns else 0)
    if candidate.power_puzzle:
        power = state['power_puzzle']
        targets, levels = power['targets'], power['levels']
        for values, minimum in ((targets, 1), (levels, 0)):
            if not isinstance(values, list) or len(values) != 3 or any(
                type(value) is not int or not minimum <= value <= 3 for value in values
            ):
                raise ValueError('전도체 단계 불일치')
        candidate.power_connected = boolean(power['connected'])
        if candidate.power_connected and targets != levels:
            raise ValueError('전도체 연결 상태 불일치')
        candidate.power_gate_time = number(power['gate_time'], 0,
                                     candidate.gate_open_seconds if candidate.power_connected else 0)
        candidate.power_targets, candidate.power_levels = targets, levels
        if candidate.trial and (targets != candidate.power_puzzle['targets']
                                or candidate.power_connected and not candidate.branches_open):
            raise ValueError('삼중 성문 회로 상태 불일치')
    if candidate.puzzle:
        puzzle = state['stone_puzzle']
        candidate.plate_pressed = boolean(puzzle['pressed'])
        gate_default = candidate.gate_open_seconds if candidate.plate_pressed else 0
        candidate.gate_time = number(puzzle.get('gate_time', gate_default), 0, gate_default)
        candidate.block_direction = puzzle['direction']
        if candidate.block_direction is not None and candidate.block_direction not in DIRECTIONS:
            raise ValueError('퍼즐 이동 방향 불일치')
        block = puzzle['block']
        if not isinstance(block, list) or len(block) != 2:
            raise ValueError('퍼즐 위치 형식 불일치')
        x = number(block[0], 0, candidate.data['columns'])
        y = number(block[1], 0, candidate.data['rows'])
        if remap_puzzle and (candidate.stage != 5 or saved_revision == 5):
            block = candidate.puzzle['plate' if candidate.plate_pressed else 'start']
            x, y = block
            candidate.block_direction = None
        if candidate.plate_pressed and (block != candidate.puzzle['plate'] or candidate.block_direction):
            raise ValueError('발판 상태 불일치')
        if candidate.tile(x, y, ignore_block=True) >= 3:
            raise ValueError('퍼즐 바닥 위치 불일치')
        candidate.block = x, y
    terrain = state.get('earth_terrain', [])
    if not isinstance(terrain, list) or len(terrain) > 256:
        raise ValueError('임시 지형 목록 불일치')
    for entry in terrain:
        kind, bounds = entry['kind'], entry['bounds']
        if kind not in ('wall', 'floor') or not isinstance(bounds, list) or len(bounds) != 4:
            raise ValueError('임시 지형 형식 불일치')
        left, top, right, bottom = bounds
        number(left, 0, candidate.data['columns'])
        number(right, left, candidate.data['columns'])
        number(top, 0, candidate.data['rows'])
        number(bottom, top, candidate.data['rows'])
        if left == right or top == bottom:
            raise ValueError('임시 지형 면적 불일치')
        if kind == 'floor':
            previous = candidate.turret_room and candidate.turret_room.get('previousBridge')
            if not candidate.earth_bridge or bounds not in (candidate.earth_bridge, previous):
                raise ValueError('임시 바닥 위치 불일치')
            bounds = candidate.earth_bridge
        remaining = number(entry['remaining'], 0, candidate.earth_seconds)
        candidate.earth_terrain.append(EarthTerrain(kind, tuple(bounds), remaining))
    if candidate.turret_room:
        turret = state['turret_room']
        candidate.turrets_stopped = boolean(turret['stopped'])
        if candidate.turrets_stopped and candidate.turret_bridge_floor:
            candidate.earth_terrain.remove(candidate.turret_bridge_floor)
        candidate.turret_timer = number(turret['timer'], 0, .85)
        candidate.next_turret = turret['next']
        if type(candidate.next_turret) is not int or candidate.next_turret not in (0, 1):
            raise ValueError('포대 순서 불일치')
    player = actor_from_data(state['player'], candidate.player, candidate, recover_puzzle_layout=remap_puzzle)
    enemies = [actor_from_data(saved, template, candidate, recover_puzzle_layout=remap_puzzle)
               for saved, template in zip(state['enemies'], candidate.enemies)]
    sources = state['sources']
    if not isinstance(sources,list) or len(sources) != len(candidate.sources):
        raise ValueError('원천 목록 불일치')
    restored_sources = []
    previous_reservoir_layout = False
    for saved,template in zip(sources,candidate.sources):
        if not isinstance(saved,dict) or set(saved) != {f.name for f in fields(Source)}:
            raise ValueError('원천 형식 불일치')
        if (template.id == 'first-orb' and candidate.reservoir
                and [saved['x'],saved['y']] == candidate.reservoir.get('previousOrb')):
            saved = dict(saved, x=template.x, y=template.y)
            previous_reservoir_layout = True
        if any(saved[key] != getattr(template,key) for key in ('id','x','y','element')):
            raise ValueError('원천 종류/좌표 불일치')
        phases = ({'sealed':0,'orb':0,'consumed':0} if template.id == 'first-orb' else
                  {'intact':3,'damaged1':2,'damaged2':1,'breaking':0,'orb':0,'consumed':0})
        release = {'descending': candidate.reservoir, 'igniting': candidate.forge,
                   'gathering': candidate.windmill, 'charging': candidate.capacitor}
        if template.id == 'first-orb':
            phases.update(dict.fromkeys((phase for phase, details in release.items() if details), 0))
        if saved['phase'] not in phases or type(saved['hp']) is not int or saved['hp'] != phases[saved['phase']]:
            raise ValueError('원천 내구도/상태 불일치')
        for key in ('age','break_elapsed','hit_time'):
            number(saved[key],0,2_000_000_000)
        if details := release.get(saved['phase']):
            number(saved['age'], 0, details['releaseSeconds'])
        restored_sources.append(Source(**saved))
    candidate.sources = restored_sources
    safe = state['safe']
    if not isinstance(safe, list) or len(safe) != 3 or safe[2] not in DIRECTIONS:
        raise ValueError('안전 위치 불일치')
    number(safe[0],0,candidate.data['columns'])
    number(safe[1],0,candidate.data['rows'])
    if wheel_position := trial_wheel_resume_position(candidate, *safe[:2]):
        safe = [*wheel_position, safe[2]]
    if candidate.intersects_windmill_base(*safe[:2], candidate.radius):
        safe = [*candidate.acquisition['orb'], safe[2]]
    if (remap_puzzle and not candidate.fits(*safe[:2], safe=True)
            and candidate.fits(player.x, player.y, safe=True, ignore_earth=True)):
        safe = [player.x, player.y, player.facing]
    if previous_reservoir_layout:
        # 사라진 옆길 또는 아직 꺼지지 않은 불길 뒤에서 재개하지 않는다.
        north = candidate.data['floorRegions'][0]
        def accessible(x, y):
            return candidate.fits(x, y, safe=True) and not any(
                index not in candidate.extinguished and y < top
                and (x >= left or y < north['y'] + north['height'])
                for index, (left, top, _, _) in enumerate(candidate.fire_barriers))

        if not accessible(*safe[:2]):
            safe = list(candidate.safe)
        if not accessible(player.x, player.y):
            player.x, player.y, player.facing = safe
            player.falling = 0
            player.moving = False
            player.attack_elapsed = -1
        for enemy, template in zip(enemies, candidate.enemies):
            if enemy.active and not enemy.falling and candidate.tile(enemy.x, enemy.y) == 4:
                enemy.x, enemy.y = template.x, template.y
    if candidate.reference_art and state.get('reference_layout') == 1:
        # 이전 바닥 경계에 걸쳐 저장된 위치를 새 바닥 안으로 옮긴다.
        if not candidate.fits(safe[0], safe[1], safe=True):
            safe = list(candidate.safe)
        if candidate.tile(player.x, player.y) == 4 and not player.falling:
            player.x, player.y = safe[:2]
        for enemy, template in zip(enemies, candidate.enemies):
            if enemy.active and not enemy.falling and candidate.tile(enemy.x, enemy.y) == 4:
                enemy.x, enemy.y = template.x, template.y
    if ((candidate.puzzle or candidate.earth_terrain) and not candidate.fits(safe[0], safe[1], safe=True)
            or candidate.in_trial_sweep(*safe[:2])):
        safe = list(candidate.safe)
    if not candidate.fits(safe[0],safe[1],safe=True):
        raise ValueError('위험한 복귀 위치')
    elapsed = number(state['elapsed'], 0, 1_000_000_000)
    aggro = boolean(state['aggro'])
    spike = boolean(state['spike_contact'])
    selected = state['selected']
    lightning_charged = boolean(state.get('lightning_charged', False))
    lightning_attack = boolean(state.get('lightning_attack', False))
    if selected != 'neutral' and not lightning_attack and (selected not in inventory or not inventory[selected]):
        raise ValueError('선택 원소 불일치')
    if lightning_charged and (selected != 'lightning' or lightning_attack):
        raise ValueError('번개 충전 상태 불일치')
    if lightning_attack:
        if (selected != 'lightning' or player.attack_element != 'lightning' or player.attack_elapsed < 0
                or (not player.attack_emitted and not inventory['lightning'])):
            raise ValueError('번개 공격 상태 불일치')
    fire_aggro = boolean(state['fire_aggro'])
    ingest_elapsed = number(state['ingest_elapsed'],-1,candidate.tuning.ingest_duration)
    if ingest_elapsed < 0 and ingest_elapsed != -1:
        raise ValueError('섭취 시간 불일치')
    ingest_source,consumed,form = state['ingest_source'],boolean(state['ingest_consumed']),state['ingest_form']
    if form not in ('neutral', *ELEMENTS):
        raise ValueError('섭취 외형 불일치')
    if ingest_elapsed >= 0:
        source = next((s for s in restored_sources if s.id == ingest_source),None)
        if source is None or source.phase != ('consumed' if consumed else 'orb'):
            raise ValueError('섭취 대상 불일치')
    elif ingest_source is not None or consumed:
        raise ValueError('끝난 섭취 상태 불일치')
    if candidate.acquisition:
        orb = restored_sources[-1]
        eaten = orb.phase == 'consumed' and not (ingest_source == orb.id and consumed)
        if bool(inventory[orb.element]) != eaten or candidate.acquisition_relay and not eaten:
            raise ValueError('첫 원소 습득 상태 불일치')
    shots = state['projectiles']
    if not isinstance(shots, list) or len(shots) > 256:
        raise ValueError('탄환 목록 불일치')
    projectiles = []
    for shot in shots:
        if not isinstance(shot, dict) or set(shot) != {f.name for f in fields(Projectile)}:
            raise ValueError('탄환 형식 불일치')
        if shot['owner'] not in ('hero','enemy') or shot['element'] not in ('neutral','water','fire','wind','earth','lightning'):
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
    candidate.lightning_charged, candidate.lightning_attack = lightning_charged, lightning_attack
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
        record = {'version':3,'stage':room.stage,'room_id':room.data['id'],'state':{
            'player': asdict(room.player), 'enemies': [asdict(e) for e in room.enemies],
            'safe': list(room.safe), 'aggro': room.aggro, 'elapsed': room.elapsed,
            'spike_contact':room.spike_contact,
            'projectiles':[asdict(s) for s in room.projectiles if s.element != 'mixed'],
            'inventory':dict(room.inventory),'selected':room.selected,'sources':[asdict(s) for s in room.sources],
            'lightning_charged': room.lightning_charged, 'lightning_attack': room.lightning_attack,
            'fire_aggro':room.fire_aggro,'ingest_elapsed':room.ingest_elapsed,'ingest_source':room.ingest_source,
            'ingest_consumed':room.ingest_consumed,'ingest_form':room.ingest_form}}
        if room.debug_cleared:
            record['state']['debug_cleared'] = True
        if room.data.get('requiredBridge'):
            record['state']['bridge_crossed'] = room.bridge_crossed
            record['state']['bridge_entry_side'] = room.bridge_entry_side
        if room.acquisition:
            record['state']['acquisition'] = {'relay': room.acquisition_relay, 'power': room.acquisition_power}
            if room.power_circuit:
                record['state']['acquisition']['powerElapsed'] = room.acquisition_power_elapsed
        if room.sluice:
            record['state'].update(sluice_wheel=room.sluice_wheel, sluice_pump=room.sluice_pump)
            if room.garden:
                record['state'].update(garden_wheel_time=room.garden_wheel_time,
                                       garden_gate_time=room.garden_gate_time,
                                       garden_exit_time=room.garden_exit_time)
        if room.fire_barriers:
            record['state']['extinguished'] = sorted(room.extinguished)
        if room.power_puzzle:
            record['state']['power_puzzle'] = {
                'targets': room.power_targets, 'levels': room.power_levels,
                'connected': room.power_connected, 'gate_time': room.power_gate_time}
        if room.trial:
            record['state']['trial_returns'] = sorted(room.trial_returns)
            record['state']['trial_wheel_time'] = min(room.trial_wheel_time, room.trial_wheel_reveal_seconds)
        if room.conductor_vine:
            record['state']['conductor_vine_time'] = room.conductor_vine_time
        if room.guardian:
            record['state']['boss'] = room.guardian.record()
        if room.puzzle:
            record['state']['stone_puzzle'] = {
                'block': list(room.block), 'direction': room.block_direction, 'pressed': room.plate_pressed,
                'gate_time': room.gate_time}
        if room.earth_terrain:
            record['state']['earth_terrain'] = [asdict(terrain) for terrain in room.earth_terrain]
        if room.turret_room:
            record['state']['turret_room'] = {
                'stopped': room.turrets_stopped, 'timer': room.turret_timer, 'next': room.next_turret}
        if room.vine_gate:
            record['state']['vine_time'] = room.vine_time
        if room.reference_art:
            record['state']['reference_layout'] = 2
        if room.data.get('layoutRevision'):
            record['state']['map_revision'] = room.data['layoutRevision']
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        os.replace(temporary, self.path)

    def clear(self):
        self.path.unlink(missing_ok=True)
