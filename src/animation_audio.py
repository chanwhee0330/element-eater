"""시뮬레이션의 오브젝트 상태 전환에서 효과음을 발생시킨다."""

HAZARD_SOUNDS = {'spikes': 'lever', 'steam': 'steam', 'gust': 'gust',
                 'rock': 'stone', 'shock': 'electric'}
RELEASE_SOUNDS = {'descending': 'splash', 'igniting': 'flame', 'gathering': 'gust',
                  'charging': 'electric'}
CUES = (
    'footstep', 'enemy-step', 'enemy-attack', 'warning', 'impact', 'break',
    'orb', 'ingest', 'heal', 'gust', 'stone', 'electric', 'lever', 'gate',
    'steam', 'splash', 'flame', 'shockwave', 'transform', 'fall', 'land', 'defeat',
    'loop-rotor', 'loop-laser', 'loop-wheel',
    'prologue-smoke',
)


def mechanism_loops(room):
    motor = None
    if room.windmill and room.sources[-1].phase != 'sealed':
        motor = 'loop-rotor'
    elif room.active_lasers:
        motor = 'loop-laser'
    wheel = 'loop-wheel' if room.trial and room.trial_laser_locked else None
    return motor, wheel


def footsteps(actor, previous_time, *, player):
    if actor.active and actor.moving and not actor.falling:
        interval = .28 if player else .38
        if int(actor.animation_time / interval) > int(previous_time / interval):
            return 'footstep' if player else 'enemy-step'
    return None


def animated_objects(room):
    events = {}

    def add(key, active, cue):
        if active:
            events[key] = cue

    for index, hazard in enumerate(room.data.get('movingHazards', ())):
        state, _ = room.hazard_state(hazard)
        add(('trap-warning', index), state == 'warning', 'warning')
        add(('trap-motion', index), state == 'active', HAZARD_SOUNDS[hazard['kind']])
    for source in room.sources:
        cue = RELEASE_SOUNDS.get(source.phase)
        add(('source-release', source.id), cue, cue)
        add(('source-orb', source.id), source.phase == 'orb', 'orb')
        add(('source-reform', source.id), source.phase == 'intact', 'transform')

    add('vine-burning', room.vine_time >= 0, 'flame')
    add('conductor-vine-burning', room.conductor_vine_time >= 0, 'flame')
    add('counterweight', room.block_direction is not None, 'stone')
    add('pressure-plate', room.plate_pressed, 'lever')
    add('pressure-gate', room.gate_time > 0, 'gate')
    add('turret-stop', room.turrets_stopped, 'lever')
    add('relay', room.acquisition_relay_flash > 0, 'electric')
    add('power-switch', room.acquisition_power_elapsed >= 0, 'lever')
    add('bulkhead', room.powered_door_lift > 0, 'gate')
    add('garden-wheel', room.sluice_wheel, 'lever')
    add('garden-pump', room.sluice_pump, 'electric')
    add('garden-gate', room.garden_gate_time > 0, 'gate')
    add('trial-sluice', 0 in room.trial_returns, 'splash')
    add('trial-wheel', room.trial and room.trial_laser_locked, 'stone')
    add('trial-power', 1 in room.trial_returns, 'electric')
    add('power-gate', room.power_connected, 'gate')
    add('power-error', room.power_flash > 0, 'blocked')
    for index, time_left in enumerate(room.power_hits):
        add(('conductor', index), time_left > 0, 'electric')
    add('exit', room.exit_open and not room.guardian, 'gate')

    guardian = room.guardian
    if guardian and room.stage == 10:
        for index in range(guardian.ritual):
            add(('pedestal', index), True, 'orb')
        add('summoning', guardian.summoning, 'transform')
        add('boss-defeated', guardian.fall >= 0, 'shockwave')
        for index, cue in enumerate(('splash', 'flame', 'gust', 'stone', 'electric')):
            add(('gate-rune', index), index < guardian.gate_runes, cue)
        add('boss-exit', guardian.gate_progress > 0, 'gate')
        add('boss-exit-burst', guardian.gate_progress > 0, 'shockwave')
        add('reward-ingest', guardian.reward_scene_elapsed is not None, 'ingest')
    return events


def animation_state(room):
    actors = tuple((actor.animation_time, actor.falling) for actor in (room.player, *room.enemies))
    placed = len(room.guardian.placed) if room.guardian else 0
    return animated_objects(room), actors, len(room.extinguished), placed


def collect_animation_sounds(room, previous):
    previous_objects, previous_actors, previous_extinguished, previous_placed = previous
    room.sound_events.extend(cue for key, cue in animated_objects(room).items()
                             if key not in previous_objects)
    if len(room.extinguished) > previous_extinguished:
        room.sound_events.append('steam')
    if room.guardian and len(room.guardian.placed) < previous_placed:
        room.sound_events.append('orb')
    for index, (actor, (time, falling)) in enumerate(zip((room.player, *room.enemies), previous_actors)):
        if actor.falling and not falling:
            room.sound_events.append('fall')
        elif index == 0 and falling and not actor.falling:
            room.sound_events.append('land')
        if cue := footsteps(actor, time, player=index == 0):
            if cue == 'footstep' and room.standing_in_water(actor.x, actor.y):
                cue = 'footstep-water'
            room.sound_events.append(cue)
